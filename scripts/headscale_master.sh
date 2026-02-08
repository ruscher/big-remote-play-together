#!/bin/bash
# ==============================================================================
# HEADSCALE ULTIMATE MANAGER - Rafael Ruscher Edition
# Versão com Porta Alternativa (8085) e Guest Blindado
# ==============================================================================

set -e

# Cores
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

header() {
    clear
    echo -e "${BLUE}====================================================${NC}"
    echo -e "${GREEN}      HEADSCALE & CLOUDFLARE - REDE PRIVADA         ${NC}"
    echo -e "${BLUE}====================================================${NC}"
}

check_deps() {
    echo -e "${YELLOW}Verificando dependências...${NC}"
    for pkg in docker docker-compose jq curl miniupnpc; do
        command -v $pkg &> /dev/null || sudo pacman -S $pkg --noconfirm
    done
}

# --- FUNÇÃO PARA O SERVIDOR (HOST) ---
setup_host() {
    header
    echo -e "${YELLOW}CONFIGURAÇÃO DE HOST (SERVIDOR)${NC}"
    read -p "Domínio (ex: vpn.ruscher.org): " DOMAIN
    read -p "Cloudflare Zone ID: " ZONE_ID
    read -p "Cloudflare API Token: " API_TOKEN

    mkdir -p ~/headscale-server/{config,data}
    cd ~/headscale-server

    # 1. Caddyfile (Porta 8085 para evitar bloqueio de operadora)
    cat <<EOF > Caddyfile
:8085 {
    handle /web* {
        reverse_proxy headscale-ui:80
    }
    handle /api* {
        reverse_proxy headscale:8080
    }
    handle / {
        reverse_proxy headscale:8080
    }
}
EOF

    # 2. Docker Compose
    cat <<EOF > docker-compose.yml
services:
  headscale:
    image: headscale/headscale:latest
    container_name: headscale
    volumes:
      - ./config:/etc/headscale
      - ./data:/var/lib/headscale
    command: serve
    restart: unless-stopped

  headscale-ui:
    image: ghcr.io/gurucomputing/headscale-ui:latest
    container_name: headscale-ui
    restart: unless-stopped

  caddy:
    image: caddy:latest
    container_name: caddy
    ports:
      - "8085:8085"
      - "41641:41641/udp"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile
    restart: unless-stopped
EOF

    # 3. Configuração do Headscale
    if [ ! -f ./config/config.yaml ]; then
        curl -s https://raw.githubusercontent.com/juanfont/headscale/main/config-example.yaml -o ./config/config.yaml
        sed -i "s|server_url: .*|server_url: http://$DOMAIN:8085|" ./config/config.yaml
        sed -i 's|listen_addr: 127.0.0.1:8080|listen_addr: 0.0.0.0:8080|' ./config/config.yaml
        sed -i 's|db_path: .*|db_path: /var/lib/headscale/db.sqlite|' ./config/config.yaml
    fi
    sudo chmod -R 777 config data

    # 4. DNS Cloudflare
    CURRENT_IP=$(curl -s https://api.ipify.org)
    RECORD_ID=$(curl -s -X GET "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/dns_records?name=$DOMAIN" \
        -H "Authorization: Bearer $API_TOKEN" -H "Content-Type: application/json" | jq -r '.result[0].id')
    
    if [ "$RECORD_ID" != "null" ] && [ -n "$RECORD_ID" ]; then
        curl -s -X PUT "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/dns_records/$RECORD_ID" \
            -H "Authorization: Bearer $API_TOKEN" -H "Content-Type: application/json" \
            --data "{\"type\":\"A\",\"name\":\"$DOMAIN\",\"content\":\"$CURRENT_IP\",\"ttl\":120,\"proxied\":false}"
    fi

    docker-compose down || true
    docker-compose up -d

    IP_LOCAL=$(ip route get 1 | awk '{print $7;exit}')
    upnpc -e "Headscale Proxy" -a $IP_LOCAL 8085 8085 TCP 2>/dev/null || true
    upnpc -e "Headscale Data" -a $IP_LOCAL 41641 41641 UDP 2>/dev/null || true

    sleep 10
    docker exec headscale headscale users create amigos || true
    USER_ID=$(docker exec headscale headscale users list -o json | jq -r '.[] | select(.name=="amigos") | .id')
    AUTH_KEY=$(docker exec headscale headscale preauthkeys create --user "$USER_ID" --reusable --expiration 24h)
    API_KEY=$(docker exec headscale headscale apikeys create)

    header
    echo -e "${GREEN}TUDO PRONTO!${NC}"
    echo -e "Acesse a UI em: ${YELLOW}http://$DOMAIN:8085/web${NC}"
    echo -e "API Key: ${CYAN}$API_KEY${NC}"
    echo -e "Chave da VPN (Para o Guest): ${GREEN}$AUTH_KEY${NC}"
    echo -e "Porta utilizada: ${YELLOW}8085${NC}"
}

# --- FUNÇÃO PARA O CLIENTE (GUEST) ---
setup_guest() {
    header
    echo -e "${YELLOW}CONFIGURAÇÃO DE CLIENTE (GUEST)${NC}"
    read -p "Domínio do Servidor (ex: vpn.ruscher.org): " HOST_DOMAIN
    read -p "Chave de Acesso (Auth Key): " AUTH_KEY

    echo -e "${YELLOW}Preparando Tailscale...${NC}"
    sudo pacman -S tailscale --noconfirm
    sudo systemctl enable --now tailscaled

    echo -e "${YELLOW}Conectando à rede privada (aguarde)...${NC}"
    
    # Adicionado timeout, desabilitado DNS que trava e forçada a porta 8085
    if sudo tailscale up --login-server http://$HOST_DOMAIN:8085 --authkey $AUTH_KEY --accept-dns=false --timeout 30s; then
        echo -e "${GREEN}SUCESSO! Conectado.${NC}"
        tailscale status
    else
        echo -e "${RED}ERRO AO CONECTAR!${NC}"
        echo -e "Diagnóstico rápido:"
        echo -e "1. Tente acessar no navegador: http://$HOST_DOMAIN:8085/api/v1/status"
        echo -e "2. Se não abrir, o Host não abriu a porta 8085 no roteador."
        echo -e "3. Verifique se a Chave de Acesso não expirou."
        exit 1
    fi
}

# --- MENU ---
header
check_deps
echo "1) Ser o HOST"
echo "2) Ser o GUEST"
read -p "Opção: " OPT
case $OPT in
    1) setup_host ;;
    2) setup_guest ;;
    *) exit 0 ;;
esac
