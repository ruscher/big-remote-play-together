"""
View para modo Guest (conectar a hosts)
"""

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, Adw, GLib
import subprocess
import threading

class GuestView(Gtk.Box):
    """Interface para conectar a hosts"""
    
    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        
        self.discovered_hosts = []
        self.is_connected = False
        
        self.setup_ui()
        self.discover_hosts()
        
    def setup_ui(self):
        """Configura interface"""
        # Clamp para centralizar
        clamp = Adw.Clamp()
        clamp.set_maximum_size(800)
        clamp.set_margin_top(24)
        clamp.set_margin_bottom(24)
        clamp.set_margin_start(24)
        clamp.set_margin_end(24)
        
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=24)
        
        # Header
        header = Adw.PreferencesGroup()
        header.set_title('Conectar a Host')
        header.set_description('Descubra hosts na rede ou conecte via IP/PIN')
        
        # Connection status
        self.status_card = self.create_status_card()
        header.add(self.status_card)
        
        # Performance monitor
        from .performance_monitor import PerformanceMonitor
        self.perf_monitor = PerformanceMonitor()
        self.perf_monitor.set_visible(False)  # Oculto até conectar
        header.add(self.perf_monitor)
        
        # Connection method tabs
        connection_group = Adw.PreferencesGroup()
        connection_group.set_title('Método de Conexão')
        connection_group.set_margin_top(12)
        
        # Stack for connection methods
        self.method_stack = Gtk.Stack()
        self.method_stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
        
        # Method 1: Discover
        discover_page = self.create_discover_page()
        self.method_stack.add_titled(discover_page, 'discover', 'Descobrir')
        
        # Method 2: Manual
        manual_page = self.create_manual_page()
        self.method_stack.add_titled(manual_page, 'manual', 'Manual')
        
        # Method 3: PIN
        pin_page = self.create_pin_page()
        self.method_stack.add_titled(pin_page, 'pin', 'Código PIN')
        
        # Stack switcher
        switcher = Gtk.StackSwitcher()
        switcher.set_stack(self.method_stack)
        switcher.set_halign(Gtk.Align.CENTER)
        
        switcher_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        switcher_box.append(switcher)
        switcher_box.append(self.method_stack)
        
        connection_group.add(switcher_box)
        
        # Client settings
        settings_group = Adw.PreferencesGroup()
        settings_group.set_title('Configurações do Cliente')
        settings_group.set_margin_top(12)
        
        # Quality preference
        quality_row = Adw.ComboRow()
        quality_row.set_title('Qualidade de Vídeo')
        quality_row.set_subtitle('Ajustar automaticamente conforme a rede')
        
        quality_model = Gtk.StringList()
        quality_model.append('Automática (Recomendado)')
        quality_model.append('720p 30fps')
        quality_model.append('1080p 30fps')
        quality_model.append('1080p 60fps')
        quality_model.append('1440p 60fps')
        quality_model.append('4K 60fps')
        
        quality_row.set_model(quality_model)
        quality_row.set_selected(0)
        
        settings_group.add(quality_row)
        
        # Audio
        audio_row = Adw.SwitchRow()
        audio_row.set_title('Áudio')
        audio_row.set_subtitle('Receber streaming de áudio')
        audio_row.set_active(True)
        settings_group.add(audio_row)
        
        # Hardware decode
        hw_decode_row = Adw.SwitchRow()
        hw_decode_row.set_title('Decodificação por Hardware')
        hw_decode_row.set_subtitle('Usar GPU para decodificar (recomendado)')
        hw_decode_row.set_active(True)
        settings_group.add(hw_decode_row)
        
        # Fullscreen
        fullscreen_row = Adw.SwitchRow()
        fullscreen_row.set_title('Tela Cheia')
        fullscreen_row.set_subtitle('Iniciar em modo tela cheia')
        fullscreen_row.set_active(False)
        settings_group.add(fullscreen_row)
        
        # Add to content
        content.append(header)
        content.append(connection_group)
        content.append(settings_group)
        
        clamp.set_child(content)
        self.append(clamp)
        
    def create_status_card(self):
        """Cria card de status da conexão"""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.add_css_class('card')
        box.set_margin_top(12)
        box.set_margin_bottom(12)
        box.set_margin_start(12)
        box.set_margin_end(12)
        
        status_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        status_box.set_margin_top(12)
        status_box.set_margin_bottom(12)
        status_box.set_margin_start(12)
        
        self.status_icon = Gtk.Image.new_from_icon_name('network-offline-symbolic')
        self.status_icon.set_pixel_size(32)
        
        status_text = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.status_label = Gtk.Label(label='Desconectado')
        self.status_label.set_halign(Gtk.Align.START)
        self.status_label.add_css_class('title-3')
        
        self.status_sublabel = Gtk.Label(label='Selecione um host para conectar')
        self.status_sublabel.set_halign(Gtk.Align.START)
        self.status_sublabel.add_css_class('dim-label')
        
        status_text.append(self.status_label)
        status_text.append(self.status_sublabel)
        
        status_box.append(self.status_icon)
        status_box.append(status_text)
        
        box.append(status_box)
        return box
        
    def create_discover_page(self):
        """Cria página de descoberta automática"""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_margin_top(12)
        box.set_margin_bottom(12)
        
        # Refresh button
        refresh_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        refresh_box.set_halign(Gtk.Align.END)
        
        refresh_btn = Gtk.Button(label='Atualizar')
        refresh_btn.set_icon_name('view-refresh-symbolic')
        refresh_btn.connect('clicked', lambda b: self.discover_hosts())
        
        refresh_box.append(refresh_btn)
        
        # Hosts list
        self.hosts_list = Gtk.ListBox()
        self.hosts_list.add_css_class('boxed-list')
        self.hosts_list.set_selection_mode(Gtk.SelectionMode.NONE)
        
        # Placeholder
        placeholder = Adw.StatusPage()
        placeholder.set_icon_name('network-workgroup-symbolic')
        placeholder.set_title('Buscando hosts...')
        placeholder.set_description('Procurando servidores Sunshine na rede local')
        
        self.hosts_list.set_placeholder(placeholder)
        
        box.append(refresh_box)
        box.append(self.hosts_list)
        
        return box
        
    def create_manual_page(self):
        """Cria página de conexão manual"""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_margin_top(12)
        box.set_margin_bottom(12)
        
        # IP entry
        ip_row = Adw.EntryRow()
        ip_row.set_title('Endereço IP ou Hostname')
        ip_row.set_text('192.168.')
        
        # Port entry
        port_row = Adw.EntryRow()
        port_row.set_title('Porta')
        port_row.set_text('47989')
        
        # Connect button
        connect_btn = Gtk.Button(label='Conectar')
        connect_btn.add_css_class('suggested-action')
        connect_btn.add_css_class('pill')
        connect_btn.set_halign(Gtk.Align.CENTER)
        connect_btn.set_size_request(200, -1)
        connect_btn.set_margin_top(12)
        connect_btn.connect('clicked', lambda b: self.connect_manual(ip_row.get_text(), port_row.get_text()))
        
        box.append(ip_row)
        box.append(port_row)
        box.append(connect_btn)
        
        return box
        
    def create_pin_page(self):
        """Cria página de conexão por PIN"""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_margin_top(12)
        box.set_margin_bottom(12)
        
        # Info
        info_label = Gtk.Label()
        info_label.set_markup(
            '<span size="large">Digite o código PIN de 6 dígitos\n'
            'fornecido pelo host</span>'
        )
        info_label.set_justify(Gtk.Justification.CENTER)
        info_label.add_css_class('dim-label')
        
        # PIN entry
        pin_entry = Gtk.Entry()
        pin_entry.set_placeholder_text('000000')
        pin_entry.set_max_length(6)
        pin_entry.set_halign(Gtk.Align.CENTER)
        pin_entry.set_size_request(200, -1)
        pin_entry.add_css_class('title-1')
        pin_entry.set_alignment(0.5)
        
        # Connect button
        connect_btn = Gtk.Button(label='Conectar com PIN')
        connect_btn.add_css_class('suggested-action')
        connect_btn.add_css_class('pill')
        connect_btn.set_halign(Gtk.Align.CENTER)
        connect_btn.set_size_request(200, -1)
        connect_btn.set_margin_top(12)
        connect_btn.connect('clicked', lambda b: self.connect_pin(pin_entry.get_text()))
        
        box.append(info_label)
        box.append(pin_entry)
        box.append(connect_btn)
        
        return box
        
    def discover_hosts(self):
        """Descobre hosts na rede"""
        from utils.network import NetworkDiscovery
        import gi
        gi.require_version('Gtk', '4.0')
        gi.require_version('Adw', '1')
        from gi.repository import Gtk, Adw, GLib
        
        # Limpar lista atual
        while self.hosts_list.get_first_child():
            self.hosts_list.remove(self.hosts_list.get_first_child())
        
        # Adicionar placeholder de carregando
        loading_row = Adw.ActionRow()
        loading_row.set_title('Procurando hosts...')
        spinner = Gtk.Spinner()
        spinner.start()
        loading_row.add_suffix(spinner)
        self.hosts_list.append(loading_row)
        
        # Descobrir hosts em thread separada
        def on_hosts_discovered(hosts):
            # Remover placeholder
            while self.hosts_list.get_first_child():
                self.hosts_list.remove(self.hosts_list.get_first_child())
            
            if not hosts:
                # Nenhum host encontrado
                no_hosts_row = Adw.ActionRow()
                no_hosts_row.set_title('Nenhum host encontrado')
                no_hosts_row.set_subtitle('Tente conexão manual')
                icon = Gtk.Image.new_from_icon_name('network-offline-symbolic')
                no_hosts_row.add_prefix(icon)
                self.hosts_list.append(no_hosts_row)
            else:
                # Adicionar hosts encontrados
                for host in hosts:
                    self.hosts_list.append(self.create_host_row(host))
            
            return False  # Remove GLib.idle_add callback
        
        discovery = NetworkDiscovery()
        discovery.discover_hosts(callback=lambda hosts: GLib.idle_add(on_hosts_discovered, hosts))

        
    def update_hosts_list(self, hosts):
        """Atualiza lista de hosts descobertos"""
        # Clear list
        while True:
            row = self.hosts_list.get_row_at_index(0)
            if row is None:
                break
            self.hosts_list.remove(row)
            
        # Add hosts
        for host in hosts:
            row = self.create_host_row(host)
            self.hosts_list.append(row)
            
    def create_host_row(self, host):
        """Cria linha para um host"""
        row = Gtk.ListBoxRow()
        
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        box.set_margin_top(12)
        box.set_margin_bottom(12)
        box.set_margin_start(12)
        box.set_margin_end(12)
        
        # Icon
        icon = Gtk.Image.new_from_icon_name('computer-symbolic')
        icon.set_pixel_size(32)
        
        # Info
        info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        info_box.set_hexpand(True)
        
        name_label = Gtk.Label(label=host['name'])
        name_label.set_halign(Gtk.Align.START)
        name_label.add_css_class('title-4')
        
        ip_label = Gtk.Label(label=host['ip'])
        ip_label.set_halign(Gtk.Align.START)
        ip_label.add_css_class('dim-label')
        ip_label.add_css_class('monospace')
        
        info_box.append(name_label)
        info_box.append(ip_label)
        
        # Connect button
        connect_btn = Gtk.Button(label='Conectar')
        connect_btn.add_css_class('suggested-action')
        connect_btn.connect('clicked', lambda b: self.connect_to_host(host))
        
        box.append(icon)
        box.append(info_box)
        box.append(connect_btn)
        
        row.set_child(box)
        return row
        
    def connect_to_host(self, host):
        """Conecta a um host"""
        from guest.moonlight_client import MoonlightClient
        
        # Inicializar cliente se necessário
        if not hasattr(self, 'moonlight'):
            self.moonlight = MoonlightClient()
        
        # Obter configurações da UI
        quality_map = {
            0: 'auto',
            1: '720p30',
            2: '1080p30',
            3: '1080p60',
            4: '1440p60',
            5: '4k60',
        }
        
        # TODO: Pegar índice selecionado do quality_row
        # Por enquanto usa padrão
        quality = '1080p60'
        
        try:
            # Conectar ao host
            success = self.moonlight.connect(
                host['ip'],
                quality=quality,
                fullscreen=False,  # TODO: Pegar da UI
                audio=True,        # TODO: Pegar da UI
                hw_decode=True     # TODO: Pegar da UI
            )
            
            if success:
                self.status_icon.set_from_icon_name('network-transmit-receive-symbolic')
                self.status_label.set_text(f'Conectado a {host["name"]}')
                self.status_sublabel.set_text(f'Streaming de {host["ip"]}')
                
                # Mostrar e iniciar monitor de performance
                self.perf_monitor.set_visible(True)
                self.perf_monitor.start_monitoring()
                
                self.show_toast(f'Conectado a {host["name"]}')
            else:
                self.show_error_dialog('Erro de Conexão',
                    f'Não foi possível conectar a {host["name"]}.\n'
                    'Verifique se o host está acessível e o Moonlight está configurado.')
                    
        except Exception as e:
            self.show_error_dialog('Erro Inesperado',
                f'Ocorreu um erro ao conectar:\n{str(e)}')
        
    def connect_manual(self, ip, port):
        """Conecta manualmente via IP"""
        # Criar host dict e chamar connect_to_host
        host = {
            'name': ip,
            'ip': ip,
            'port': int(port) if port else 47989,
            'status': 'online'
        }
        self.connect_to_host(host)
        
    def connect_pin(self, pin):
        """Conecta via PIN"""
        # TODO: Implementar servidor de matchmaking para resolver PIN→IP
        if len(pin) != 6 or not pin.isdigit():
            self.show_error_dialog('PIN Inválido',
                'O PIN deve conter exatamente 6 dígitos.')
            return
        
        # Por enquanto, mostra mensagem
        self.show_error_dialog('Funcionalidade em Desenvolvimento',
            'O sistema de conexão por PIN ainda não está implementado.\n'
            'Use conexão manual ou descoberta automática.')
    
    def show_error_dialog(self, title, message):
        """Mostra diálogo de erro"""
        dialog = Adw.MessageDialog.new(self.get_root())
        dialog.set_heading(title)
        dialog.set_body(message)
        dialog.add_response('ok', 'OK')
        dialog.set_response_appearance('ok', Adw.ResponseAppearance.DEFAULT)
        dialog.present()
    
    def show_toast(self, message):
        """Mostra toast notification"""
        window = self.get_root()
        if hasattr(window, 'show_toast'):
            window.show_toast(message)
        else:
            print(f"Toast: {message}")

    def cleanup(self):
        """Limpa recursos ao fechar"""
        # Parar monitoramento
        if hasattr(self, 'perf_monitor'):
            self.perf_monitor.stop_monitoring()
            
        # Desconectar Moonlight se estiver rodando quit() ou disconnect()
        if hasattr(self, 'moonlight'):
            # TODO: Implementar disconnect no moonlight_client
            pass
