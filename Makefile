# Makefile para Big Remote Play Together

PREFIX ?= /usr/local
INSTALL_DIR = $(PREFIX)/share/big-remoteplay
BIN_DIR = $(PREFIX)/bin
DESKTOP_DIR = $(PREFIX)/share/applications
ICON_DIR = $(PREFIX)/share/icons/hicolor

.PHONY: all install uninstall clean run dev help

all: help

help:
	@echo "Big Remote Play Together - Makefile"
	@echo ""
	@echo "Alvos disponíveis:"
	@echo "  install     - Instala o aplicativo no sistema"
	@echo "  uninstall   - Remove o aplicativo do sistema"
	@echo "  run         - Executa o aplicativo em modo desenvolvimento"
	@echo "  dev         - Executa em modo desenvolvimento com verbose"
	@echo "  clean       - Limpa arquivos temporários"
	@echo "  test        - Executa testes"
	@echo "  docker      - Inicia serviços Docker"
	@echo "  help        - Mostra esta ajuda"
	@echo ""

install:
	@echo "Instalando Big Remote Play Together..."
	
	# Criar diretórios
	install -d $(INSTALL_DIR)
	install -d $(INSTALL_DIR)/src
	install -d $(INSTALL_DIR)/scripts
	install -d $(INSTALL_DIR)/data
	install -d $(BIN_DIR)
	install -d $(DESKTOP_DIR)
	install -d $(ICON_DIR)/scalable/apps
	
	# Copiar arquivos Python
	cp -r src/* $(INSTALL_DIR)/src/
	
	# Copiar scripts
	cp -r scripts/* $(INSTALL_DIR)/scripts/
	chmod +x $(INSTALL_DIR)/scripts/*.sh
	
	# Copiar dados
	cp -r data/* $(INSTALL_DIR)/data/
	
	# Criar executável
	echo '#!/bin/bash' > $(BIN_DIR)/big-remoteplay
	echo 'cd $(INSTALL_DIR)/src' >> $(BIN_DIR)/big-remoteplay
	echo 'exec python3 main.py "$$@"' >> $(BIN_DIR)/big-remoteplay
	chmod +x $(BIN_DIR)/big-remoteplay
	
	# Instalar desktop file
	install -m 644 data/big-remoteplay.desktop $(DESKTOP_DIR)/
	
	# Instalar ícone
	install -m 644 data/icons/big-remoteplay.svg $(ICON_DIR)/scalable/apps/
	
	# Atualizar cache de ícones e desktop
	-gtk-update-icon-cache -f -t $(ICON_DIR) 2>/dev/null || true
	-update-desktop-database $(DESKTOP_DIR) 2>/dev/null || true
	
	@echo "Instalação concluída!"
	@echo "Execute: big-remoteplay"

uninstall:
	@echo "Removendo Big Remote Play Together..."
	
	rm -rf $(INSTALL_DIR)
	rm -f $(BIN_DIR)/big-remoteplay
	rm -f $(DESKTOP_DIR)/big-remoteplay.desktop
	rm -f $(ICON_DIR)/scalable/apps/big-remoteplay.svg
	
	-gtk-update-icon-cache -f -t $(ICON_DIR) 2>/dev/null || true
	-update-desktop-database $(DESKTOP_DIR) 2>/dev/null || true
	
	@echo "Desinstalação concluída!"

run:
	cd src && python3 main.py

dev:
	cd src && python3 main.py --verbose

clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -delete
	rm -rf build/ dist/

test:
	@echo "Executando testes..."
	python3 -m pytest tests/ -v

docker:
	@echo "Iniciando serviços Docker..."
	cd docker && docker-compose up -d
	@echo "Serviços iniciados!"
	@echo "  Sunshine Web UI: http://localhost:47989"

docker-stop:
	@echo "Parando serviços Docker..."
	cd docker && docker-compose down

docker-logs:
	cd docker && docker-compose logs -f

check-deps:
	@echo "Verificando dependências..."
	@command -v python3 >/dev/null 2>&1 || { echo "Python 3 não encontrado!"; exit 1; }
	@python3 -c "import gi" 2>/dev/null || { echo "PyGObject não encontrado!"; exit 1; }
	@python3 -c "import gi; gi.require_version('Gtk', '4.0')" 2>/dev/null || { echo "GTK 4 não encontrado!"; exit 1; }
	@python3 -c "import gi; gi.require_version('Adw', '1')" 2>/dev/null || { echo "LibAdwaita não encontrado!"; exit 1; }
	@echo "✅ Todas as dependências básicas OK!"

configure:
	@echo "Configurando Big Remote Play..."
	./scripts/big-remoteplay-configure.sh

service-start:
	@echo "Iniciando Sunshine..."
	./scripts/big-remoteplay-service.sh start

service-stop:
	@echo "Parando Sunshine..."
	./scripts/big-remoteplay-service.sh stop

firewall:
	@echo "Configurando firewall..."
	sudo ./scripts/big-remoteplay-firewall.sh configure
