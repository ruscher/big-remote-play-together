#!/bin/bash
# ==============================================================================
# HEADSCALE CLOUD-TUNNEL EDITION - Rafael Ruscher
# Sem necessidade de abrir portas no roteador (Bye Bye CGNAT)
# ==============================================================================

set -e
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

header() {
    clear
    echo -e "${GREEN}      HEADSCALE CLOUD-TUNNEL (ANTI-CGNAT)           ${NC}"
}

setup_host() {
    header
    read -p "Domínio (ex: ruscher.dpdns.org): " DOMAIN
    read -p "Cloudflare Tunnel Token: " TUNNEL_TOKEN

    mkdir -p ~/headscale-server/{config,data}
    cd ~/headscale-server

    # Caddyfile (Fica interno agora, o Túnel chama ele)
    cat <<EOF > Caddyfile
:8085 {
    handle /web* { reverse_proxy headscale-ui:80 }
    handle /api* { reverse_proxy headscale:8080 }
    handle / { reverse_proxy headscale:8080 }
}
EOF

    # Docker Compose com Cloudflared
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
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile
    restart: unless-stopped

  tunnel:
    image: cloudflare/cloudflared:latest
    container_name: cloudflared
    command: tunnel --no-autoupdate run --token $TUNNEL_TOKEN
    restart: unless-stopped
EOF

    # Ajuste do config.yaml (Sem porta 8085 na URL externa, pois o túnel usa a 80)
    if [ ! -f ./config/config.yaml ]; then
        curl -s https://raw.githubusercontent.com/juanfont/headscale/main/config-example.yaml -o ./config/config.yaml
        sed -i "s|server_url: .*|server_url: http://$DOMAIN|" ./config/config.yaml
        sed -i 's|listen_addr: 127.0.0.1:8080|listen_addr: 0.0.0.0:8080|' ./config/config.yaml
    fi
    sudo chown -R 1000:1000 config data && sudo chmod -R 777 config data

    docker-compose down || true
    docker-compose up -d

    echo -e "${YELLOW}Túnel estabelecido. Gerando chaves...${NC}"
    sleep 10
    docker exec headscale headscale users create amigos || true
    USER_ID=$(docker exec headscale headscale users list -o json | jq -r '.[] | select(.name=="amigos") | .id')
    AUTH_KEY=$(docker exec headscale headscale preauthkeys create --user "$USER_ID" --reusable --expiration 24h)

    echo -e "${GREEN}HOST ONLINE VIA CLOUDFLARE TUNNEL!${NC}"
    echo -e "Domínio: ${YELLOW}http://$DOMAIN${NC}"
    echo -e "Chave Auth: ${GREEN}$AUTH_KEY${NC}"
    echo -e "Acesse o Painel em: ${YELLOW}http://$DOMAIN/web${NC}"
}

setup_guest() {
    header
    read -p "Domínio do Host: " HOST_DOMAIN
    read -p "Chave de Acesso: " AUTH_KEY

    sudo systemctl stop tailscaled || true
    sudo rm -rf /var/lib/tailscale/tailscaled.state
    sudo systemctl enable --now tailscaled
    
    echo -e "${YELLOW}Conectando via Túnel Cloudflare...${NC}"
    # Removida a porta 8085 pois o túnel Cloudflare responde na 80/443 padrão
    if sudo tailscale up --login-server http://$HOST_DOMAIN --authkey $AUTH_KEY --accept-dns=false --timeout 45s; then
        echo -e "${GREEN}CONECTADO!${NC}"
        tailscale status
    else
        echo -e "${RED}ERRO! Verifique se o Túnel Cloudflare está ATIVO no Host.${NC}"
    fi
}

echo "1) HOST  2) GUEST"
read -p "Opção: " OPT
[[ $OPT == 1 ]] && setup_host || setup_guest
