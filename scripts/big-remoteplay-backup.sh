#!/bin/bash
set -e

CONFIG_DIR="$HOME/.config/big-remoteplay"
BACKUP_DIR="$CONFIG_DIR/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo "╔════════════════════════════════════════════════╗"
echo "║   Big Remote Play Together - Backup            ║"
echo "╚════════════════════════════════════════════════╝"
echo ""

# Criar diretório de backup
mkdir -p "$BACKUP_DIR"

BACKUP_FILE="$BACKUP_DIR/backup_$TIMESTAMP.tar.gz"

echo "📦 Criando backup..."
echo "   Destino: $BACKUP_FILE"
echo ""

# Arquivos para backup
cd "$CONFIG_DIR"

tar -czf "$BACKUP_FILE" \
    --exclude='backups' \
    --exclude='logs' \
    --exclude='*.pid' \
    --exclude='*.lock' \
    . 2>/dev/null || true

if [ -f "$BACKUP_FILE" ]; then
    SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    echo "✅ Backup criado com sucesso!"
    echo "   Tamanho: $SIZE"
    echo "   Arquivo: $BACKUP_FILE"
    echo ""
    
    # Limpar backups antigos (manter últimos 5)
    BACKUP_COUNT=$(ls -1 "$BACKUP_DIR"/backup_*.tar.gz 2>/dev/null | wc -l)
    
    if [ "$BACKUP_COUNT" -gt 5 ]; then
        echo "🗑️  Removendo backups antigos..."
        ls -1t "$BACKUP_DIR"/backup_*.tar.gz | tail -n +6 | xargs rm -f
        echo "   Mantidos os 5 backups mais recentes"
    fi
    
else
    echo "❌ Erro ao criar backup"
    exit 1
fi

echo ""
echo "════════════════════════════════════════════════"
echo "Para restaurar este backup:"
echo "  cd $CONFIG_DIR"
echo "  tar -xzf $BACKUP_FILE"
echo "════════════════════════════════════════════════"
