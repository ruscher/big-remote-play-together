#!/bin/bash
# ==============================================================================
# HEADSCALE ULTIMATE MANAGER - Rafael Ruscher Edition
# Com Caddy Proxy para resolver erro de CORS (Failed to Fetch)
# ==============================================================================

set -e

# Cores
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
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

setup_host() {
    header
    read -p "Domínio (ex: vpn.ruscher.org): " DOMAIN
    read -p "Cloudflare Zone ID: " ZONE_ID
    read -p "Cloudflare API Token: " API_TOKEN

    mkdir -p ~/headscale-server/{config,data}
    cd ~/headscale-server

    # 1. Criando Caddyfile para matar o erro de CORS
    echo -e "${YELLOW}Gerando configuração do Proxy Reverso (Caddy)...${NC}"
    cat <<EOF > Caddyfile
:80 {
    # Rota para a Interface
    handle /web* {
        reverse_proxy headscale-ui:8080
    }
    # Rota para a API e Tailscale
    handle /api* {
        reverse_proxy headscale:8080
    }
    handle / {
        reverse_proxy headscale:8080
    }
}
EOF

    # 2. Docker Compose com Caddy incluído
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
      - "80:80"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile
    restart: unless-stopped
EOF

    # 3. Configuração do Headscale
    if [ ! -f ./config/config.yaml ]; then
        curl -s https://raw.githubusercontent.com/juanfont/headscale/main/config-example.yaml -o ./config/config.yaml
        sed -i "s|server_url: .*|server_url: http://$DOMAIN|" ./config/config.yaml
        sed -i 's|listen_addr: 127.0.0.1:8080|listen_addr: 0.0.0.0:8080|' ./config/config.yaml
        sed -i 's|db_path: .*|db_path: /var/lib/headscale/db.sqlite|' ./config/config.yaml
    fi
    sudo chmod -R 777 config data

    # 4. DNS Cloudflare
    CURRENT_IP=$(curl -s https://api.ipify.org)
    RECORD_ID=$(curl -s -X GET "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/dns_records?name=$DOMAIN" \
        -H "Authorization: Bearer $API_TOKEN" -H "Content-Type: application/json" | jq -r '.result[0].id')
    if [ "$RECORD_ID" != "null" ]; then
        curl -s -X PUT "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/dns_records/$RECORD_ID" \
            -H "Authorization: Bearer $API_TOKEN" -H "Content-Type: application/json" \
            --data "{\"type\":\"A\",\"name\":\"$DOMAIN\",\"content\":\"$CURRENT_IP\",\"ttl\":120,\"proxied\":false}"
    fi

    # 5. Subindo containers e Portas
    docker-compose down || true
    docker-compose up -d

    IP_LOCAL=$(ip route get 1 | awk '{print $7;exit}')
    upnpc -d 80 TCP 2>/dev/null || true
    upnpc -e "Headscale Proxy" -a $IP_LOCAL 80 80 TCP || true
    upnpc -e "Headscale Data" -a $IP_LOCAL 41641 41641 UDP || true

    echo -e "${YELLOW}Finalizando e gerando credenciais...${NC}"
    sleep 10

    # Criar Usuário e API Key
    docker exec headscale headscale users create amigos || true
    USER_ID=$(docker exec headscale headscale users list -o json | jq -r '.[] | select(.name=="amigos") | .id')
    AUTH_KEY=$(docker exec headscale headscale preauthkeys create --user "$USER_ID" --reusable --expiration 24h)
    API_KEY=$(docker exec headscale headscale apikeys create)

    header
    echo -e "${GREEN}TUDO PRONTO COM PROXY REVERSO!${NC}"
    echo -e "Acesse a UI em: ${YELLOW}http://$IP_LOCAL/web${NC}"
    echo -e "Headscale URL na UI: ${CYAN}http://$IP_LOCAL${NC}"
    echo -e "Sua API Key: ${CYAN}$API_KEY${NC}"
    echo -e "Chave da VPN (Auth): ${GREEN}$AUTH_KEY${NC}"
    echo -e "${BLUE}====================================================${NC}"
}

check_deps
setup_host
