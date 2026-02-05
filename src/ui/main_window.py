"""
Janela principal do Big Remote Play Together
Interface moderna com navegação lateral seguindo padrões Adwaita
"""

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, Adw, GLib, Gio
import threading

from .host_view import HostView
from .guest_view import GuestView
from .installer_window import InstallerWindow
from utils.network import NetworkDiscovery
from utils.system_check import SystemCheck

# Categorias de navegação
NAVIGATION_PAGES = {
    'welcome': {
        'name': 'Início',
        'icon': 'go-home-symbolic',
        'description': 'Página inicial'
    },
    'host': {
        'name': 'Hospedar Servidor',
        'icon': 'network-server-symbolic',
        'description': 'Compartilhe seus jogos'
    },
    'guest': {
        'name': 'Conectar Servidor',
        'icon': 'network-workgroup-symbolic',
        'description': 'Conecte-se a um host'
    }
}

class MainWindow(Adw.ApplicationWindow):
    """Janela principal com navegação lateral moderna"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        self.set_title('Big Remote Play Together')
        self.set_default_size(950, 650)
        
        self.system_check = SystemCheck()
        self.network = NetworkDiscovery()
        
        # Estado atual
        self.current_page = 'welcome'
        
        self.setup_ui()
        self.check_system()
        
        # Conectar sinal de fechamento
        self.connect('close-request', self.on_close_request)
        
    def on_close_request(self, window):
        """Chamado ao fechar a janela"""
        try:
            if hasattr(self, 'host_view'):
                self.host_view.cleanup()
            
            if hasattr(self, 'guest_view'):
                self.guest_view.cleanup()
                
            print("Recursos limpos com sucesso.")
        except Exception as e:
            print(f"Erro ao limpar recursos: {e}")
            
        return False
        
    def setup_ui(self):
        """Configura interface moderna com NavigationSplitView"""
        # Toast overlay para notificações
        self.toast_overlay = Adw.ToastOverlay()
        self.set_content(self.toast_overlay)
        
        # NavigationSplitView - layout moderno com sidebar
        self.split_view = Adw.NavigationSplitView()
        self.toast_overlay.set_child(self.split_view)
        
        # === SIDEBAR ===
        self.setup_sidebar()
        
        # === CONTENT ===
        self.setup_content()
        
        # Configurar split view
        self.split_view.set_min_sidebar_width(220)
        self.split_view.set_max_sidebar_width(280)
        
    def setup_sidebar(self):
        """Configura sidebar de navegação"""
        sidebar_toolbar = Adw.ToolbarView()
        
        # Header da sidebar
        sidebar_header = Adw.HeaderBar()
        
        # Ícone do app (clicável para About)
        app_icon_btn = Gtk.Button()
        app_icon_btn.add_css_class('flat')
        app_icon = Gtk.Image.new_from_icon_name('big-remote-play-together')
        app_icon.set_pixel_size(20)
        app_icon_btn.set_child(app_icon)
        app_icon_btn.set_tooltip_text('Sobre Big Remote Play Together')
        app_icon_btn.connect('clicked', lambda btn: self.get_application().activate_action('about', None))
        sidebar_header.pack_start(app_icon_btn)
        
        # Título da sidebar
        sidebar_title = Adw.WindowTitle.new('Remote Play', '')
        sidebar_header.set_title_widget(sidebar_title)
        
        sidebar_toolbar.add_top_bar(sidebar_header)
        
        # Container principal da sidebar (lista + status)
        sidebar_main = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        sidebar_main.set_vexpand(True)
        
        # Lista de navegação
        sidebar_scroll = Gtk.ScrolledWindow()
        sidebar_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        sidebar_scroll.set_vexpand(True)
        
        self.nav_list = Gtk.ListBox()
        self.nav_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.nav_list.add_css_class('navigation-sidebar')
        self.nav_list.connect('row-selected', self.on_nav_selected)
        
        # Adicionar páginas de navegação
        for page_id, page_info in NAVIGATION_PAGES.items():
            row = self.create_nav_row(page_id, page_info)
            self.nav_list.append(row)
        
        # Selecionar primeira página
        first_row = self.nav_list.get_row_at_index(0)
        if first_row:
            self.nav_list.select_row(first_row)
        
        sidebar_scroll.set_child(self.nav_list)
        sidebar_main.append(sidebar_scroll)
        
        # Status box na parte inferior
        self.status_footer = self.create_status_footer()
        sidebar_main.append(self.status_footer)
        
        sidebar_toolbar.set_content(sidebar_main)
        
        # Criar página de navegação da sidebar
        sidebar_page = Adw.NavigationPage.new(sidebar_toolbar, 'Navigation')
        self.split_view.set_sidebar(sidebar_page)
        
    def create_nav_row(self, page_id: str, page_info: dict) -> Gtk.ListBoxRow:
        """Cria linha de navegação na sidebar"""
        row = Gtk.ListBoxRow()
        row.page_id = page_id
        row.add_css_class('category-row')
        
        # Box do conteúdo
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        box.set_margin_start(8)
        box.set_margin_end(8)
        box.set_margin_top(6)
        box.set_margin_bottom(6)
        
        # Ícone
        icon = Gtk.Image.new_from_icon_name(page_info['icon'])
        icon.set_pixel_size(20)
        icon.add_css_class('category-icon')
        box.append(icon)
        
        # Label
        label = Gtk.Label(label=page_info['name'])
        label.set_halign(Gtk.Align.START)
        label.set_hexpand(True)
        label.add_css_class('category-label')
        box.append(label)
        
        row.set_child(box)
        return row
    
    def create_status_footer(self):
        """Cria footer com status dos servidores"""
        # Container principal
        footer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        footer.set_margin_start(12)
        footer.set_margin_end(12)
        footer.set_margin_top(8)
        footer.set_margin_bottom(12)
        footer.set_spacing(8)
        
        # Separador
        separator = Gtk.Separator()
        separator.set_margin_bottom(8)
        footer.append(separator)
        
        # Label "Status dos Servidores"
        status_title = Gtk.Label(label='Status dos Servidores')
        status_title.add_css_class('caption')
        status_title.add_css_class('dim-label')
        status_title.set_halign(Gtk.Align.START)
        status_title.set_margin_bottom(4)
        footer.append(status_title)
        
        # Status Sunshine
        sunshine_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        sunshine_box.set_margin_start(4)
        
        self.sunshine_dot = Gtk.Image.new_from_icon_name('media-record-symbolic')
        self.sunshine_dot.set_pixel_size(12)
        self.sunshine_dot.add_css_class('status-dot')
        self.sunshine_dot.add_css_class('status-offline')  # Inicialmente offline
        sunshine_box.append(self.sunshine_dot)
        
        sunshine_label = Gtk.Label(label='Sunshine')
        sunshine_label.add_css_class('caption')
        sunshine_label.set_halign(Gtk.Align.START)
        sunshine_box.append(sunshine_label)
        
        footer.append(sunshine_box)
        
        # Status Moonlight
        moonlight_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        moonlight_box.set_margin_start(4)
        
        self.moonlight_dot = Gtk.Image.new_from_icon_name('media-record-symbolic')
        self.moonlight_dot.set_pixel_size(12)
        self.moonlight_dot.add_css_class('status-dot')
        self.moonlight_dot.add_css_class('status-offline')  # Inicialmente offline
        moonlight_box.append(self.moonlight_dot)
        
        moonlight_label = Gtk.Label(label='Moonlight')
        moonlight_label.add_css_class('caption')
        moonlight_label.set_halign(Gtk.Align.START)
        moonlight_box.append(moonlight_label)
        
        footer.append(moonlight_box)
        
        return footer
        
    def update_server_status(self, has_sunshine: bool, has_moonlight: bool):
        """Atualiza indicadores de status dos servidores"""
        # Atualizar Sunshine
        if has_sunshine:
            self.sunshine_dot.remove_css_class('status-offline')
            self.sunshine_dot.add_css_class('status-online')
        else:
            self.sunshine_dot.remove_css_class('status-online')
            self.sunshine_dot.add_css_class('status-offline')
        
        # Atualizar Moonlight
        if has_moonlight:
            self.moonlight_dot.remove_css_class('status-offline')
            self.moonlight_dot.add_css_class('status-online')
        else:
            self.moonlight_dot.remove_css_class('status-online')
            self.moonlight_dot.add_css_class('status-offline')

        
    def setup_content(self):
        """Configura área de conteúdo"""
        content_toolbar = Adw.ToolbarView()
        
        # Header do conteúdo
        content_header = Adw.HeaderBar()
        
        # Menu button
        menu = Gio.Menu()
        menu.append('Preferências', 'app.preferences')
        menu.append('Sobre', 'app.about')
        menu_btn = Gtk.MenuButton(icon_name='open-menu-symbolic', menu_model=menu)
        content_header.pack_end(menu_btn)
        
        content_toolbar.add_top_bar(content_header)
        
        # Stack para as páginas
        self.content_stack = Gtk.Stack()
        self.content_stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.content_stack.set_transition_duration(200)
        self.content_stack.set_vexpand(True)
        
        # Criar páginas
        self.content_stack.add_named(self.create_welcome_page(), 'welcome')
        
        self.host_view = HostView()
        self.content_stack.add_named(self.host_view, 'host')
        
        self.guest_view = GuestView()
        self.content_stack.add_named(self.guest_view, 'guest')
        
        content_toolbar.set_content(self.content_stack)
        
        # Criar página de navegação do conteúdo
        content_page = Adw.NavigationPage.new(content_toolbar, 'Big Remote Play Together')
        self.split_view.set_content(content_page)
        
    def create_welcome_page(self):
        """Cria página de boas-vindas moderna"""
        # Container principal
        container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        container.set_vexpand(True)
        
        # ScrolledWindow para conteúdo
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_vexpand(True)
        
        # Box central
        center_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        center_box.set_halign(Gtk.Align.CENTER)
        center_box.set_valign(Gtk.Align.CENTER)
        center_box.set_spacing(32)
        center_box.set_margin_start(48)
        center_box.set_margin_end(48)
        center_box.set_margin_top(48)
        center_box.set_margin_bottom(48)
        
        # Status page
        status_page = Adw.StatusPage()
        status_page.set_icon_name('big-remote-play-together')
        status_page.set_title('Big Remote Play Together')
        status_page.set_description(
            'Jogue cooperativamente através da rede local\n'
            'Compartilhe seus jogos ou conecte-se a um servidor'
        )
        center_box.append(status_page)
        
        # Cards de ação
        cards_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=24)
        cards_box.set_halign(Gtk.Align.CENTER)
        
        # Card Hospedar
        host_card = self.create_action_card(
            'Hospedar Servidor',
            'Compartilhe seus jogos com outros jogadores na rede',
            'network-server-symbolic',
            'suggested-action',
            lambda: self.navigate_to('host')
        )
        cards_box.append(host_card)
        
        # Card Conectar
        guest_card = self.create_action_card(
            'Conectar Servidor',
            'Conecte-se a um servidor de jogos na rede',
            'network-workgroup-symbolic',
            '',
            lambda: self.navigate_to('guest')
        )
        cards_box.append(guest_card)
        
        center_box.append(cards_box)
        
        # Informações adicionais
        info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        info_box.set_halign(Gtk.Align.CENTER)
        info_box.set_margin_top(24)
        
        info_label = Gtk.Label()
        info_label.set_markup(
            '<span size="small">Baseado em <b>Sunshine</b> e <b>Moonlight</b></span>'
        )
        info_label.add_css_class('dim-label')
        info_box.append(info_label)
        
        center_box.append(info_box)
        
        scroll.set_child(center_box)
        container.append(scroll)
        
        return container
        
    def create_action_card(self, title: str, description: str, icon: str, 
                          css_class: str, callback) -> Gtk.Widget:
        """Cria card de ação moderna"""
        # Card usando Adwaita Clamp
        clamp = Adw.Clamp()
        clamp.set_maximum_size(320)
        
        # Button como card
        card_btn = Gtk.Button()
        card_btn.add_css_class('card')
        if css_class:
            card_btn.add_css_class(css_class)
        card_btn.set_size_request(300, 180)
        card_btn.connect('clicked', lambda b: callback())
        
        # Conteúdo do card
        card_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        card_box.set_margin_start(24)
        card_box.set_margin_end(24)
        card_box.set_margin_top(24)
        card_box.set_margin_bottom(24)
        
        # Ícone
        icon_widget = Gtk.Image.new_from_icon_name(icon)
        icon_widget.set_pixel_size(48)
        icon_widget.add_css_class('accent')
        card_box.append(icon_widget)
        
        # Título
        title_label = Gtk.Label(label=title)
        title_label.add_css_class('title-3')
        title_label.set_wrap(True)
        title_label.set_justify(Gtk.Justification.CENTER)
        card_box.append(title_label)
        
        # Descrição
        desc_label = Gtk.Label(label=description)
        desc_label.add_css_class('caption')
        desc_label.add_css_class('dim-label')
        desc_label.set_wrap(True)
        desc_label.set_justify(Gtk.Justification.CENTER)
        desc_label.set_max_width_chars(35)
        card_box.append(desc_label)
        
        card_btn.set_child(card_box)
        clamp.set_child(card_btn)
        
        return clamp
        
    def on_nav_selected(self, listbox, row):
        """Navega para a página selecionada"""
        if row is None:
            return
        
        # Verificar se content_stack já foi criado
        if not hasattr(self, 'content_stack'):
            return
            
        # Atualizar CSS das categorias
        current = self.nav_list.get_first_child()
        while current:
            current.remove_css_class('active-category')
            current = current.get_next_sibling()
        
        row.add_css_class('active-category')
        
        # Navegar para a página
        self.navigate_to(row.page_id)
        
    def navigate_to(self, page_id: str):
        """Navega para uma página específica"""
        self.current_page = page_id
        self.content_stack.set_visible_child_name(page_id)
        
        # Atualizar seleção na sidebar
        row = self.nav_list.get_first_child()
        while row:
            if hasattr(row, 'page_id') and row.page_id == page_id:
                self.nav_list.select_row(row)
                break
            row = row.get_next_sibling()
        
    def check_system(self):
        """Verifica componentes do sistema"""
        def check():
            # Verificar se estão instalados
            has_sunshine = self.system_check.has_sunshine()
            has_moonlight = self.system_check.has_moonlight()
            
            # Verificar se estão rodando
            sunshine_running = self.system_check.is_sunshine_running()
            moonlight_running = self.system_check.is_moonlight_running()
            
            GLib.idle_add(self.update_status, has_sunshine, has_moonlight)
            GLib.idle_add(self.update_server_status, sunshine_running, moonlight_running)
            
        thread = threading.Thread(target=check, daemon=True)
        thread.start()
        
        # Verificar periodicamente (a cada 3 segundos)
        GLib.timeout_add_seconds(3, self.periodic_status_check)
    
    def periodic_status_check(self):
        """Verificação periódica do status dos servidores"""
        def check():
            sunshine_running = self.system_check.is_sunshine_running()
            moonlight_running = self.system_check.is_moonlight_running()
            GLib.idle_add(self.update_server_status, sunshine_running, moonlight_running)
        
        thread = threading.Thread(target=check, daemon=True)
        thread.start()
        
        return True  # Continuar verificando

        
    def update_status(self, has_sunshine, has_moonlight):
        """Verifica status de instalação e mostra diálogo se necessário"""
        # Apenas mostrar diálogo se nenhum componente estiver instalado
        if not has_sunshine and not has_moonlight:
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
        toast.set_timeout(3)
        self.toast_overlay.add_toast(toast)
