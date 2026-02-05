# Guia de Instalação - Big Remote Play Together

## 📋 Pré-requisitos

### Sistema Operacional
- BigLinux, Manjaro ou Arch Linux
- Kernel 5.15 ou superior (recomendado)

### Hardware Mínimo
- **CPU**: Intel Core i5 / AMD Ryzen 5 ou superior
- **RAM**: 4GB (8GB recomendado)
- **GPU**: Suporte a aceleração de vídeo (Intel/AMD/NVIDIA)
- **Rede**: 100Mbps LAN (1Gbps recomendado para 4K)

## 🚀 Instalação Rápida

### Método 1: Script de Instalação (Recomendado)

```bash
cd /home/ruscher/Documentos/Git/big-remoteplay/big-remote-play-together
chmod +x scripts/*.sh
sudo ./scripts/big-remoteplay-install.sh
```

### Método 2: Makefile

```bash
cd /home/ruscher/Documentos/Git/big-remoteplay/big-remote-play-together
make check-deps  # Verificar dependências
sudo make install
```

### Método 3: PKGBUILD (Arch Linux)

```bash
cd /home/ruscher/Documentos/Git/big-remoteplay/big-remote-play-together
makepkg -si
```

## 📦 Dependências

### Pacotes Essenciais
```bash
sudo pacman -S python python-gobject gtk4 libadwaita python-dbus avahi
```

### Sunshine (Host)
```bash
yay -S sunshine-bin
```

### Moonlight (Guest)
```bash
yay -S moonlight-qt
```

### Docker (Opcional)
```bash
sudo pacman -S docker docker-compose
sudo systemctl enable --now docker
sudo usermod -aG docker $USER
```

## ⚙️ Configuração Inicial

### 1. Configurar Aplicativo
```bash
big-remoteplay-configure.sh
```

### 2. Configurar Firewall
```bash
sudo big-remoteplay-firewall.sh configure
```

### 3. Habilitar Avahi (descoberta de rede)
```bash
sudo systemctl enable --now avahi-daemon
```

## 🎮 Uso

### Iniciar Aplicativo
```bash
big-remoteplay
```

Ou procure por "Big Remote Play Together" no menu de aplicativos.

### Modo Host (Hospedar Jogo)
1. Abra o aplicativo
2. Vá para aba "Hospedar Jogo"
3. Selecione o jogo ou aplicativo
4. Configure qualidade e opções
5. Clique em "Iniciar Servidor"
6. Compartilhe o PIN ou IP com amigos

### Modo Guest (Conectar)
1. Abra o aplicativo
2. Vá para aba "Conectar"
3. Escolha método de conexão:
   - **Descobrir**: Veja hosts na rede local
   - **Manual**: Digite IP do host
   - **PIN**: Use código de 6 dígitos
4. Clique em "Conectar"

## 🔧 Solução de Problemas

### Sunshine não inicia
```bash
# Verificar logs
journalctl -u big-remoteplay-sunshine --no-pager -n 50

# Testar manualmente
sunshine --config ~/.config/big-remoteplay/sunshine/sunshine.conf
```

### Firewall bloqueando conexões
```bash
# UFW
sudo ufw status
sudo ufw allow 47984:47990/tcp
sudo ufw allow 48010/tcp
sudo ufw allow 47998:48000/udp

# iptables
sudo iptables -L INPUT -n
```

### Não consegue descobrir hosts
```bash
# Verificar Avahi
systemctl status avahi-daemon

# Escanear manualmente
avahi-browse -t -r _sunshine._tcp
```

### Performance ruim
1. Reduza qualidade de streaming
2. Use conexão cabeada ao invés de WiFi
3. Habilite decodificação por hardware
4. Feche aplicativos em background

## 📚 Comandos Úteis

### Gerenciar Serviço
```bash
big-remoteplay-service.sh start   # Iniciar Sunshine
big-remoteplay-service.sh stop    # Parar Sunshine
big-remoteplay-service.sh status  # Ver status
big-remoteplay-service.sh enable  # Habilitar auto-start
```

### Backup de Configurações
```bash
big-remoteplay-backup.sh
```

### Docker
```bash
cd docker
docker-compose up -d        # Iniciar serviços
docker-compose down         # Parar serviços
docker-compose logs -f      # Ver logs
```

## 🌐 Portas Utilizadas

| Serviço | Porta | Protocolo | Descrição |
|---------|-------|-----------|-----------|
| Sunshine Web UI | 47989 | TCP | Interface web |
| Sunshine Control | 47984-47990 | TCP | Controle |
| Sunshine Video | 48010 | TCP | Streaming de vídeo |
| Sunshine Data | 47998-48000 | UDP | Dados de streaming |
| STUN | 3478 | UDP/TCP | NAT traversal |

## 📖 Próximos Passos

1. Configure jogos para compartilhar
2. Teste qualidade de rede
3. Ajuste configurações de performance
4. Explore opções avançadas nas preferências

Para mais informações, consulte a [Documentação Completa](README.md).
