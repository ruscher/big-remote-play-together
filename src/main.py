#!/usr/bin/env python3
"""
Big Remote Play Together
Sistema integrado de jogo cooperativo remoto para BigLinux

Autor: Rafael Ruscher <rruscher@gmail.com>
Licença: GPLv3
Projeto: BigLinux
"""

import sys
import os
import gi

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, Adw, Gio, GLib
from pathlib import Path

from ui.main_window import MainWindow
from utils.config import Config
from utils.logger import Logger

class BigRemotePlayApp(Adw.Application):
    """Aplicativo principal"""
    
    def __init__(self):
        super().__init__(
            application_id='br.com.biglinux.remoteplay',
            flags=Gio.ApplicationFlags.FLAGS_NONE
        )
        
        self.config = Config()
        self.logger = Logger()
        self.window = None
        
    def do_activate(self):
        """Ativa o aplicativo"""
        if not self.window:
            self.window = MainWindow(application=self)
        
        self.window.present()
        
    def do_startup(self):
        """Inicializa o aplicativo"""
        Adw.Application.do_startup(self)
        
        # Configurar ações
        self.setup_actions()
        
        # Aplicar estilo
        self.setup_theme()
        
    def setup_actions(self):
        """Configura ações do aplicativo"""
        actions = [
            ('quit', lambda *_: self.quit()),
            ('about', self.show_about),
            ('preferences', self.show_preferences),
        ]
        
        for name, callback in actions:
            action = Gio.SimpleAction.new(name, None)
            action.connect('activate', callback)
            self.add_action(action)
            
    def setup_theme(self):
        """Configura tema do aplicativo"""
        style_manager = Adw.StyleManager.get_default()
        
        # Preferência de tema do usuário
        if self.config.get('theme', 'auto') == 'dark':
            style_manager.set_color_scheme(Adw.ColorScheme.FORCE_DARK)
        elif self.config.get('theme', 'auto') == 'light':
            style_manager.set_color_scheme(Adw.ColorScheme.FORCE_LIGHT)
        else:
            style_manager.set_color_scheme(Adw.ColorScheme.DEFAULT)
            
    def show_about(self, *args):
        """Mostra diálogo sobre"""
        about = Adw.AboutWindow(
            transient_for=self.window,
            application_name='Big Remote Play Together',
            application_icon='big-remoteplay',
            developer_name='Rafael Ruscher',
            version='1.0.0',
            developers=['Rafael Ruscher <rruscher@gmail.com>'],
            copyright='© 2024 BigLinux',
            license_type=Gtk.License.GPL_3_0,
            website='https://www.biglinux.com.br',
            issue_url='https://github.com/biglinux/big-remoteplay-together/issues',
            comments='Sistema integrado de jogo cooperativo remoto\nInspirado no Steam Remote Play Together',
        )
        about.present()
        
    def show_preferences(self, *args):
        """Mostra diálogo de preferências"""
        from ui.preferences import PreferencesWindow
        prefs = PreferencesWindow(transient_for=self.window)
        prefs.present()
        
    def do_shutdown(self):
        """Limpeza ao encerrar"""
        try:
            Adw.Application.do_shutdown(self)
        except Exception:
            pass
            
        # Forçar encerramento para garantir liberação do terminal
        # Isso mata threads pendentes e processos filhos
        # Forçar encerramento para garantir liberação do terminal
        # Isso mata threads pendentes 
        os._exit(0)

def main():
    """Função principal"""
    # Configurar tratamento de interrupção (Ctrl+C)
    import signal
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    
    app = BigRemotePlayApp()
    return app.run(sys.argv)

if __name__ == '__main__':
    sys.exit(main())
