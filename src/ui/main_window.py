"""
Janela principal do Big Remote Play Together
"""

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, Adw, GLib, Gio
import subprocess
import threading

from .host_view import HostView
from .guest_view import GuestView
from .installer_window import InstallerWindow
from utils.network import NetworkDiscovery
from utils.system_check import SystemCheck

class MainWindow(Adw.ApplicationWindow):
    """Janela principal da aplicação"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        self.set_title('Big Remote Play Together')
        self.set_default_size(900, 600)
        
        self.system_check = SystemCheck()
        self.network = NetworkDiscovery()
        
        self.setup_ui()
        self.check_system()
        
        # Conectar sinal de fechamento
        self.connect('close-request', self.on_close_request)
        
    def on_close_request(self, window):
        """Chamado ao fechar a janela"""
        try:
            # Limpar recursos das views
            if hasattr(self, 'host_view'):
                self.host_view.cleanup()
            
            if hasattr(self, 'guest_view'):
                self.guest_view.cleanup()
                
            print("Recursos limpos com sucesso.")
        except Exception as e:
            print(f"Erro ao limpar recursos: {e}")
            
        return False # Permitir fechamento
        
    def setup_ui(self):
        """Configura interface do usuário"""
        # Header Bar
        header = Adw.HeaderBar()
        
        # Menu Button
        menu_button = Gtk.MenuButton()
        menu_button.set_icon_name('open-menu-symbolic')
        menu_button.set_menu_model(self.create_menu())
        header.pack_end(menu_button)
        
        # Status indicator
        self.status_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.status_icon = Gtk.Image.new_from_icon_name('network-idle-symbolic')
        self.status_label = Gtk.Label(label='Verificando...')
        self.status_label.add_css_class('dim-label')
        
        self.status_box.append(self.status_icon)
        self.status_box.append(self.status_label)
        header.pack_start(self.status_box)
        
        # Tool bar view (tabs)
        self.toolbar_view = Adw.ToolbarView()
        self.toolbar_view.add_top_bar(header)
        
        # View Stack
        self.stack = Adw.ViewStack()
        self.stack.set_vexpand(True)
        
        # View Switcher
        switcher = Adw.ViewSwitcher()
        switcher.set_stack(self.stack)
        switcher.set_policy(Adw.ViewSwitcherPolicy.WIDE)
        header.set_title_widget(switcher)
        
        # Views
        self.host_view = HostView()
        self.guest_view = GuestView()
        
        self.stack.add_titled_with_icon(
            self.host_view,
            'host',
            'Hospedar Jogo',
            'network-server-symbolic'
        )
        
        self.stack.add_titled_with_icon(
            self.guest_view,
            'guest',
            'Conectar',
            'network-workgroup-symbolic'
        )
        
        # Status Page (welcome)
        status_page = self.create_welcome_page()
        self.stack.add_titled_with_icon(
            status_page,
            'welcome',
            'Início',
            'go-home-symbolic'
        )
        
        self.stack.set_visible_child_name('welcome')
        
        self.toolbar_view.set_content(self.stack)
        
        # Toast overlay para notificações
        self.toast_overlay = Adw.ToastOverlay()
        self.toast_overlay.set_child(self.toolbar_view)
        
        self.set_content(self.toast_overlay)
        
    def create_menu(self):
        """Cria menu do aplicativo"""
        menu = Gio.Menu()
        
        menu.append('Preferências', 'app.preferences')
        menu.append('Sobre', 'app.about')
        menu.append('Sair', 'app.quit')
        
        return menu
        
    def create_welcome_page(self):
        """Cria página de boas-vindas"""
        status_page = Adw.StatusPage()
        status_page.set_icon_name('big-remoteplay')
        status_page.set_title('Bem-vindo ao Big Remote Play Together')
        status_page.set_description(
            'Jogue cooperativamente através da rede\n'
            'Escolha hospedar um jogo ou conectar a um host'
        )
        
        # Buttons box
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        button_box.set_halign(Gtk.Align.CENTER)
        button_box.set_margin_top(24)
        
        # Host button
        host_btn = Gtk.Button(label='Hospedar Jogo')
        host_btn.add_css_class('pill')
        host_btn.add_css_class('suggested-action')
        host_btn.set_size_request(200, -1)
        host_btn.connect('clicked', lambda b: self.stack.set_visible_child_name('host'))
        
        # Guest button  
        guest_btn = Gtk.Button(label='Conectar a Host')
        guest_btn.add_css_class('pill')
        guest_btn.set_size_request(200, -1)
        guest_btn.connect('clicked', lambda b: self.stack.set_visible_child_name('guest'))
        
        button_box.append(host_btn)
        button_box.append(guest_btn)
        
        # Container
        container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        container.append(status_page)
        container.append(button_box)
        
        return container
        
    def check_system(self):
        """Verifica componentes do sistema"""
        def check():
            has_sunshine = self.system_check.has_sunshine()
            has_moonlight = self.system_check.has_moonlight()
            
            GLib.idle_add(self.update_status, has_sunshine, has_moonlight)
            
        thread = threading.Thread(target=check, daemon=True)
        thread.start()
        
    def update_status(self, has_sunshine, has_moonlight):
        """Atualiza status na UI"""
        if has_sunshine and has_moonlight:
            self.status_icon.set_from_icon_name('emblem-ok-symbolic')
            self.status_label.set_text('Sistema pronto')
            self.status_label.add_css_class('success')
        elif has_sunshine or has_moonlight:
            self.status_icon.set_from_icon_name('dialog-warning-symbolic')
            missing = []
            if not has_sunshine:
                missing.append('Sunshine')
            if not has_moonlight:
                missing.append('Moonlight')
            self.status_label.set_text(f'Faltando: {", ".join(missing)}')
            self.status_label.add_css_class('warning')
        else:
            self.status_icon.set_from_icon_name('dialog-error-symbolic')
            self.status_label.set_text('Componentes não encontrados')
            self.status_label.add_css_class('error')
            
            # Show error dialog
            self.show_missing_components_dialog()
            
    def show_missing_components_dialog(self):
        """Mostra diálogo de componentes faltando"""
        dialog = Adw.MessageDialog.new(self)
        dialog.set_heading('Componentes Necessários Não Encontrados')
        dialog.set_body(
            'O Big Remote Play Together requer:\n\n'
            '• Sunshine (para hospedar jogos)\n'
            '• Moonlight (para conectar)\n\n'
            'Deseja instalar agora?'
        )
        
        dialog.add_response('cancel', 'Cancelar')
        dialog.add_response('install', 'Instalar')
        dialog.set_response_appearance('install', Adw.ResponseAppearance.SUGGESTED)
        
        dialog.connect('response', self.on_install_components)
        dialog.present()
        
    def on_install_components(self, dialog, response):
        """Instala componentes faltando"""
        if response == 'install':
            installer = InstallerWindow(parent=self, on_success=self.check_system)
            installer.present()
    
    def show_toast(self, message):
        """Mostra toast notification"""
        toast = Adw.Toast.new(message)
        toast.set_timeout(3)  # 3 segundos
        self.toast_overlay.add_toast(toast)
