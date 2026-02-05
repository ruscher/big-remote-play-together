# Maintainer: Rafael Ruscher <rruscher@gmail.com>
pkgname=big-remoteplay-together
pkgver=1.0.0
pkgrel=1
pkgdesc="Sistema integrado de jogo cooperativo remoto para BigLinux"
arch=('x86_64')
url="https://www.biglinux.com.br"
license=('GPL3')
depends=(
    'python'
    'python-gobject'
    'gtk4'
    'libadwaita'
    'python-dbus'
    'avahi'
    'sunshine'
    'moonlight-qt'
)
optdepends=(
    'docker: Para executar serviços containerizados'
    'docker-compose: Gerenciamento de containers'
    'ufw: Configuração simplificada de firewall'
)
makedepends=('git')
source=("git+https://github.com/biglinux/$pkgname.git")
sha256sums=('SKIP')

package() {
    cd "$pkgname"
    
    # Criar diretórios
    install -d "$pkgdir/opt/$pkgname"
    install -d "$pkgdir/usr/bin"
    install -d "$pkgdir/usr/share/applications"
    install -d "$pkgdir/usr/share/icons/hicolor/scalable/apps"
    
    # Copiar código fonte
    cp -r src/* "$pkgdir/opt/$pkgname/"
    
    # Copiar scripts
    install -d "$pkgdir/opt/$pkgname/scripts"
    install -Dm755 scripts/*.sh "$pkgdir/opt/$pkgname/scripts/"
    
    # Copiar dados
    install -d "$pkgdir/opt/$pkgname/data"
    cp -r data/* "$pkgdir/opt/$pkgname/data/"
    
    # Copiar Docker
    install -d "$pkgdir/opt/$pkgname/docker"
    cp -r docker/* "$pkgdir/opt/$pkgname/docker/"
    
    # Criar executável
    cat > "$pkgdir/usr/bin/$pkgname" << EOF
#!/bin/bash
cd /opt/$pkgname
exec python3 main.py "\$@"
EOF
    chmod +x "$pkgdir/usr/bin/$pkgname"
    
    # Symlink
    ln -sf "/usr/bin/$pkgname" "$pkgdir/usr/bin/big-remoteplay"
    
    # Desktop file
    install -Dm644 data/big-remoteplay.desktop \
        "$pkgdir/usr/share/applications/big-remoteplay.desktop"
    
    # Ícone
    install -Dm644 data/icons/big-remoteplay.svg \
        "$pkgdir/usr/share/icons/hicolor/scalable/apps/big-remoteplay.svg"
    
    # Documentação
    install -Dm644 README.md "$pkgdir/usr/share/doc/$pkgname/README.md"
}

post_install() {
    echo ""
    echo "════════════════════════════════════════════════"
    echo "  Big Remote Play Together instalado!"
    echo "════════════════════════════════════════════════"
    echo ""
    echo "Para iniciar: big-remoteplay"
    echo ""
    echo "Configuração inicial recomendada:"
    echo "  1. Execute: big-remoteplay-configure.sh"
    echo "  2. Configure firewall: sudo big-remoteplay-firewall.sh configure"
    echo ""
    echo "Documentação: /usr/share/doc/$pkgname/"
    echo ""
}

post_upgrade() {
    post_install
}
