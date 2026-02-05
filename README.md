# Big Remote Play Together

**Sistema integrado de jogo cooperativo remoto para BigLinux**

Inspirado no Steam Remote Play Together e Parsec, utilizando Sunshine (host) e Moonlight (guest).

Baseado no vídeo: https://www.youtube.com/watch?v=D2l9o_wXW5M

## 🎮 Características

- ✨ Interface moderna GTK 4 com Adwaita
- 🖥️ Modo Host (Sunshine) com configuração automática
- 🎯 Modo Guest (Moonlight) com descoberta automática
- 🔒 Gerenciamento de PINs e permissões
- 📊 Monitor de performance (latência, FPS, banda)
- 🎛️ Configuração simplificada de jogos cooperativos
- 🌐 Suporte UPNP IPv4/IPv6
- 🐳 Containerização Docker opcional

## 📋 Requisitos

### Sistema
- BigLinux, Manjaro ou Arch Linux
- Python 3.10+
- GTK 4 e LibAdwaita
- Docker (opcional)

### Dependências Principais
```bash
sunshine
moonlight-qt
python-gobject
gtk4
libadwaita
avahi
```

## 🚀 Instalação

### Instalação Automática (Recomendado)
```bash
cd /home/ruscher/Documentos/Git/big-remoteplay/big-remote-play-together
chmod +x scripts/big-remoteplay-install.sh
./scripts/big-remoteplay-install.sh
```

### Instalação Manual
```bash
# Instalar dependências
sudo pacman -S python-gobject gtk4 libadwaita python-dbus avahi

# Instalar Sunshine (AUR)
yay -S sunshine

# Instalar Moonlight
yay -S moonlight-qt

# Instalar o aplicativo
sudo python setup.py install
```

## 📖 Uso

### Como Host (Hospedar Jogo)
1. Abra o aplicativo
2. Selecione **"Hospedar Jogo"**
3. Escolha o jogo da lista (Steam/Lutris detectados automaticamente)
4. Configure opções (máx. jogadores, qualidade de streaming)
5. Compartilhe o código PIN com amigos
6. Gerencie a sessão via interface

### Como Guest (Conectar)
1. Abra o aplicativo
2. Selecione **"Conectar a Host"**
3. Insira IP ou código PIN do host
4. Configure controles (teclado/gamepad)
5. Conecte e jogue!

## 🏗️ Estrutura do Projeto

```
big-remote-play-together/
├── bin/                    # Executáveis
│   └── big-remoteplay
├── src/                    # Código-fonte Python
│   ├── main.py
│   ├── ui/                 # Interface GTK 4
│   ├── host/               # Módulo Sunshine
│   ├── guest/              # Módulo Moonlight
│   └── utils/              # Utilitários
├── scripts/                # Shell scripts
│   ├── big-remoteplay-install.sh
│   ├── big-remoteplay-configure.sh
│   ├── big-remoteplay-service.sh
│   └── big-remoteplay-firewall.sh
├── docker/                 # Configurações Docker
├── config/                 # Arquivos de configuração
├── data/                   # Dados do aplicativo
│   ├── icons/
│   └── ui/                 # Arquivos .ui GTK
└── docs/                   # Documentação
```

## 🔧 Configuração de Rede

O aplicativo configura automaticamente:
- **UPNP**: Habilitado para abertura automática de portas
- **Portas Sunshine**: 47984-47990, 48010
- **Porta Web UI**: 47989
- **Firewall**: Configuração automática (ufw/iptables)
- **Suporte IPv6**: Habilitado

## 📦 Distribuição

O projeto será distribuído como:
- Pacote Arch Linux (PKGBUILD)
- Flatpak (futuro)
- AppImage (futuro)

## 👨‍💻 Desenvolvimento

### Executar em Modo Desenvolvimento
```bash
cd /home/ruscher/Documentos/Git/big-remoteplay/big-remote-play-together
python src/main.py
```

### Estrutura de Desenvolvimento
- **Python 3**: Lógica principal
- **GTK 4 + Adwaita**: Interface
- **Shell Script**: Automação e configuração
- **Docker**: Isolamento de serviços (opcional)

## 📄 Licença

GPLv3 - Software Livre

## 👤 Autor

**Rafael Ruscher**
- Email: rruscher@gmail.com
- Projeto: BigLinux

## 🔗 Links Úteis

- [Sunshine](https://github.com/LizardByte/Sunshine)
- [Moonlight](https://github.com/moonlight-stream)
- [BigLinux](https://www.biglinux.com.br)

## 🤝 Contribuindo

Contribuições são bem-vindas! Por favor, abra uma issue ou pull request.

---

**Big Remote Play Together** - Jogue junto, jogue em qualquer lugar! 🎮✨
