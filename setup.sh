#!/bin/bash

echo "╔════════════════════════════════════════════════╗"
echo "║   Big Remote Play Together                     ║"
echo "║   Setup Inicial Rápido                         ║"
echo "╚════════════════════════════════════════════════╝"
echo ""
echo "Este script irá:"
echo "  1. Verificar dependências"
echo "  2. Configurar o aplicativo"
echo "  3. Configurar firewall (opcional)"
echo "  4. Testar a instalação"
echo ""
read -p "Continuar? [S/n]: " -n 1 -r
echo
if [[ $REPLY =~ ^[Nn]$ ]]; then
    exit 0
fi

echo ""
echo "═══ 1. Verificando Dependências ═══"
echo ""

# Python packages
python3 -c "import gi" 2>/dev/null || {
    echo "❌ PyGObject não encontrado"
    echo "   Instalando: sudo pacman -S python-gobject"
    sudo pacman -S --needed --noconfirm python-gobject
}

python3 -c "import gi; gi.require_version('Gtk', '4.0')" 2>/dev/null || {
    echo "❌ GTK 4 não encontrado"
    echo "   Instalando: sudo pacman -S gtk4"
    sudo pacman -S --needed --noconfirm gtk4
}

python3 -c "import gi; gi.require_version('Adw', '1')" 2>/dev/null || {
    echo "❌ LibAdwaita não encontrado"
    echo "   Instalando: sudo pacman -S libadwaita"
    sudo pacman -S --needed --noconfirm libadwaita
}

# Sunshine
if ! command -v sunshine &> /dev/null; then
    echo "⚠️  Sunshine não encontrado"
    read -p "   Instalar via yay? [s/N]: " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Ss]$ ]]; then
        yay -S sunshine-bin
    fi
fi

# Moonlight
if ! command -v moonlight &> /dev/null && ! command -v moonlight-qt &> /dev/null; then
    echo "⚠️  Moonlight não encontrado"
    read -p "   Instalar via yay? [s/N]: " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Ss]$ ]]; then
        yay -S moonlight-qt
    fi
fi

# Avahi
if ! systemctl is-active --quiet avahi-daemon; then
    echo "⚠️  Avahi não está ativo"
    read -p "   Ativar agora? [s/N]: " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Ss]$ ]]; then
        sudo systemctl enable --now avahi-daemon
    fi
fi

echo ""
echo "✅ Dependências verificadas!"
echo ""
echo "═══ 2. Configurando Aplicativo ═══"
echo ""

./scripts/big-remoteplay-configure.sh

echo ""
echo "═══ 3. Configurar Firewall ═══"
echo ""

read -p "Configurar firewall automaticamente? [S/n]: " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Nn]$ ]]; then
    sudo ./scripts/big-remoteplay-firewall.sh configure
fi

echo ""
echo "═══ 4. Teste de Instalação ═══"
echo ""

echo "Verificando componentes..."
echo ""

# Check Sunshine
if command -v sunshine &> /dev/null; then
    VERSION=$(sunshine --version 2>/dev/null || echo "Desconhecida")
    echo "✅ Sunshine: $VERSION"
else
    echo "⚠️  Sunshine: Não instalado"
fi

# Check Moonlight
if command -v moonlight-qt &> /dev/null; then
    VERSION=$(moonlight-qt --version 2>/dev/null || echo "Desconhecida")
    echo "✅ Moonlight: $VERSION"
elif command -v moonlight &> /dev/null; then
    VERSION=$(moonlight --version 2>/dev/null || echo "Desconhecida")
    echo "✅ Moonlight: $VERSION"
else
    echo "⚠️  Moonlight: Não instalado"
fi

# Check Avahi
if systemctl is-active --quiet avahi-daemon; then
    echo "✅ Avahi: Ativo"
else
    echo "⚠️  Avahi: Inativo"
fi

# Check Config
if [ -d "$HOME/.config/big-remoteplay" ]; then
    echo "✅ Configuração: OK"
else
    echo "⚠️  Configuração: Não encontrada"
fi

echo ""
echo "════════════════════════════════════════════════"
echo "✅ Setup concluído!"
echo "════════════════════════════════════════════════"
echo ""
echo "🚀 Para iniciar o aplicativo:"
echo "   big-remoteplay"
echo ""
echo "📚 Documentação:"
echo "   README.md - Visão geral"
echo "   docs/INSTALL.md - Instalação detalhada"
echo "   PROJECT_SUMMARY.md - Resumo técnico"
echo ""
echo "🔧 Comandos úteis:"
echo "   make run             - Executar em modo dev"
echo "   make configure       - Reconfigurar"
echo "   make service-start   - Iniciar Sunshine"
echo "   make docker          - Usar Docker"
echo ""
echo "Divirta-se! 🎮✨"
