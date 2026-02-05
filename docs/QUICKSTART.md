# 🚀 Quick Start - Big Remote Play Together

Guia rápido para começar a usar em **5 minutos**!

## 📦 Instalação Rápida

```bash
cd /home/ruscher/Documentos/Git/big-remoteplay/big-remote-play-together

# Opção 1: Setup automatizado (RECOMENDADO)
./setup.sh

# Opção 2: Instalação manual
sudo ./scripts/big-remoteplay-install.sh
```

## 🎮 Uso Básico

### Como HOST (Hospedar um Jogo)

1. **Abra o aplicativo**
   ```bash
   big-remoteplay
   ```

2. **Vá para aba "Hospedar Jogo"**

3. **Configure:**
   - Selecione jogo (ou Desktop Completo)
   - Escolha qualidade (recomendado: Alta - 1080p 60fps)
   - Defina número máximo de jogadores

4. **Clique em "Iniciar Servidor"**

5. **Compartilhe com amigos:**
   - Código PIN (6 dígitos)
   - OU seu endereço IP

### Como GUEST (Conectar a um Jogo)

1. **Abra o aplicativo**
   ```bash
   big-remoteplay
   ```

2. **Vá para aba "Conectar"**

3. **Escolha método de conexão:**

   **🔍 Descobrir (Rede Local)**
   - Veja hosts disponíveis automaticamente
   - Clique em "Conectar"

   **📝 Manual (Qualquer Rede)**
   - Digite IP do host (ex: 192.168.1.100)
   - Digite porta (padrão: 47989)
   - Clique em "Conectar"

   **🔢 Código PIN**
   - Digite PIN de 6 dígitos fornecido pelo host
   - Clique em "Conectar com PIN"

4. **Aproveite o jogo!**

## ⚡ Comandos Rápidos

```bash
# Iniciar aplicativo
big-remoteplay

# Iniciar Sunshine manualmente
big-remoteplay-service.sh start

# Ver status do Sunshine
big-remoteplay-service.sh status

# Configurar firewall
sudo big-remoteplay-firewall.sh configure

# Fazer backup de configs
big-remoteplay-backup.sh

# Abrir web UI do Sunshine
firefox http://localhost:47989
```

## 🔧 Solução Rápida de Problemas

### "Componentes não encontrados"
```bash
# Instalar Sunshine
yay -S sunshine

# Instalar Moonlight
yay -S moonlight-qt
```

### "Não consigo descobrir hosts"
```bash
# Ativar Avahi
sudo systemctl enable --now avahi-daemon

# Testar descoberta
avahi-browse -t -r _sunshine._tcp
```

### "Conexão bloqueada"
```bash
# Configurar firewall
sudo big-remoteplay-firewall.sh configure

# Ou manualmente (UFW)
sudo ufw allow 47984:47990/tcp
sudo ufw allow 48010/tcp
sudo ufw allow 47998:48000/udp
```

### "Performance ruim"
1. Reduza qualidade de streaming
2. Use cabo ethernet ao invés de WiFi
3. Habilite decodificação por hardware
4. Feche programas em background

## 📊 Configurações Recomendadas

### Para Rede Local (LAN)
- **Qualidade**: Ultra (1440p 60fps) ou Máxima (4K 60fps)
- **Bitrate**: 20-30 Mbps
- **Codec**: H.264/H.265

### Para Internet (WAN)
- **Qualidade**: Alta (1080p 60fps)
- **Bitrate**: 10-15 Mbps
- **Codec**: H.264
- **Habilitar**: UPNP

### Para WiFi
- **Qualidade**: Média (1080p 30fps)
- **Bitrate**: 10 Mbps
- **Usar**: Banda 5GHz se disponível

## 🎯 Casos de Uso

### 1. Jogar Jogo Local com Amigo Remoto
```
Host: Inicia jogo → Compartilha PIN
Guest: Conecta via PIN → Controla jogo junto
```

### 2. Compartilhar Desktop
```
Host: Seleciona "Desktop Completo" → Inicia servidor
Guest: Conecta → Vê e controla desktop do host
```

### 3. LAN Party Virtual
```
Hosts: Múltiplos na mesma rede
Guests: Descobrem automaticamente e escolhem qual conectar
```

## 📚 Próximos Passos

1. **Explore Preferências** (`Ctrl+,`)
   - Ajuste tema
   - Configure rede
   - Ative logs detalhados

2. **Configure Jogos Favoritos**
   - Steam: Detectado automaticamente
   - Lutris: Detectado automaticamente
   - Outros: Adicione manualmente

3. **Leia Documentação Completa**
   - [README.md](README.md) - Visão geral
   - [docs/INSTALL.md](docs/INSTALL.md) - Instalação detalhada
   - [PROJECT_SUMMARY.md](PROJECT_SUMMARY.md) - Técnico

## 💡 Dicas

- **PIN**: Mude regularmente para segurança
- **Firewall**: Configure uma vez, funciona sempre
- **Backup**: Use `big-remoteplay-backup.sh` antes de mudanças grandes
- **Docker**: Use se tiver problemas com instalação nativa

## 🆘 Ajuda

- **Logs**: `~/.config/big-remoteplay/logs/`
- **Configuração**: `~/.config/big-remoteplay/`
- **Email**: rruscher@gmail.com
- **Issues**: GitHub (quando disponível)

---

**Dica Final**: Para melhor experiência, use conexão cabeada e habilite aceleração por hardware! 🚀
