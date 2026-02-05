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
        self.pin_dialog = None
        
        # Initialize client
        from guest.moonlight_client import MoonlightClient
        self.moonlight = MoonlightClient()
        
        self.setup_ui()
        self.discover_hosts()
        
        # Start monitoring
        GLib.timeout_add(1000, self.monitor_connection)
        
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
        
        # Stack for connection methods
        self.method_stack = Gtk.Stack()
        self.method_stack.set_transition_type(Gtk.StackTransitionType.NONE)
        
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
        
        self.switcher_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.switcher_box.append(switcher)
        self.switcher_box.append(self.method_stack)
        
        # Client settings
        settings_group = Adw.PreferencesGroup()
        settings_group.set_title('Configurações do Cliente')
        settings_group.set_margin_top(12)
        
        # Quality preference
        self.quality_row = Adw.ComboRow()
        self.quality_row.set_title('Qualidade de Vídeo')
        self.quality_row.set_subtitle('Ajustar automaticamente conforme a rede')
        
        quality_model = Gtk.StringList()
        quality_model.append('Automática (Recomendado)')
        quality_model.append('720p 30fps')
        quality_model.append('1080p 30fps')
        quality_model.append('1080p 60fps')
        quality_model.append('1440p 60fps')
        quality_model.append('4K 60fps')
        
        self.quality_row.set_model(quality_model)
        self.quality_row.set_selected(0)
        
        settings_group.add(self.quality_row)
        
        # Audio
        self.audio_row = Adw.SwitchRow()
        self.audio_row.set_title('Áudio')
        self.audio_row.set_subtitle('Receber streaming de áudio')
        self.audio_row.set_active(True)
        settings_group.add(self.audio_row)
        
        # Hardware decode
        self.hw_decode_row = Adw.SwitchRow()
        self.hw_decode_row.set_title('Decodificação por Hardware')
        self.hw_decode_row.set_subtitle('Usar GPU para decodificar (recomendado)')
        self.hw_decode_row.set_active(True)
        settings_group.add(self.hw_decode_row)
        
        # Fullscreen
        self.fullscreen_row = Adw.SwitchRow()
        self.fullscreen_row.set_title('Tela Cheia')
        self.fullscreen_row.set_subtitle('Iniciar em modo tela cheia')
        self.fullscreen_row.set_active(False)
        settings_group.add(self.fullscreen_row)
        
        # Add to content
        content.append(header)
        content.append(self.switcher_box)
        content.append(settings_group)
        
        clamp.set_child(content)
        
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_vexpand(True)
        scroll.set_child(clamp)
        
        self.append(scroll)
        
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
        
        # Process Status
        process_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        process_box.set_margin_start(12)
        process_box.set_margin_bottom(12)
        
        proc_label = Gtk.Label(label="Status do Moonlight:")
        proc_label.add_css_class('dim-label')
        
        self.process_status_label = Gtk.Label(label="Aguardando...")
        
        process_box.append(proc_label)
        process_box.append(self.process_status_label)
        
        box.append(process_box)
        
        return box

    def monitor_connection(self):
        """Monitora o estado da conexão Moonlight"""
        if hasattr(self, 'moonlight'):
            is_running = self.moonlight.is_connected()
            
            if is_running:
                self.process_status_label.set_markup('<span color="green">Executando (Janela Aberta)</span>')
                if not self.is_connected:
                     # Atualizar state se estava desmarcado
                     self.is_connected = True
                     self.status_icon.set_from_icon_name('network-transmit-receive-symbolic')
                     if self.moonlight.connected_host:
                        self.status_label.set_text(f'Conectado a {self.moonlight.connected_host}')
            else:
                self.process_status_label.set_markup('<span color="gray">Parado</span>')
                if self.is_connected:
                    # Detectou que fechou
                    self.is_connected = False
                    self.status_label.set_text('Desconectado')
                    self.status_sublabel.set_text('Sessão encerrada')
                    self.status_icon.set_from_icon_name('network-offline-symbolic')
                    self.perf_monitor.stop_monitoring()
                    self.perf_monitor.set_visible(False)
                    self.show_toast("Moonlight encerrado")

        return True # Continue polling
        
    def create_discover_page(self):
        """Cria página de descoberta automática"""
        self.selected_host_card_data = None
        self.first_radio_in_list = None
        
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0) # Spacing 0 for tight layout
        
        # Header / Refresh
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        header_box.set_margin_top(12)
        header_box.set_margin_bottom(12)
        header_box.set_margin_start(12)
        header_box.set_margin_end(12)
        
        lbl = Gtk.Label(label="Hosts Descobertos")
        lbl.add_css_class("heading")
        lbl.set_halign(Gtk.Align.START)
        lbl.set_hexpand(True)
        
        refresh_btn = Gtk.Button(icon_name='view-refresh-symbolic')
        refresh_btn.set_tooltip_text("Atualizar Lista")
        refresh_btn.connect('clicked', lambda b: self.discover_hosts())
        
        header_box.append(lbl)
        header_box.append(refresh_btn)
        
        # Hosts list
        self.hosts_list = Gtk.ListBox()
        self.hosts_list.add_css_class('boxed-list')
        self.hosts_list.set_selection_mode(Gtk.SelectionMode.NONE)
        self.hosts_list.set_margin_start(12)
        self.hosts_list.set_margin_end(12)
        
        # scroll = Gtk.ScrolledWindow()
        # scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        # scroll.set_vexpand(True)
        # scroll.set_child(self.hosts_list)
        
        # Main Connect Button (External)
        action_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        action_box.set_margin_top(12)
        action_box.set_margin_bottom(12)
        action_box.set_margin_start(12)
        action_box.set_margin_end(12)
        
        self.main_connect_btn = Gtk.Button(label='Conectar ao Host Selecionado')
        self.main_connect_btn.add_css_class('suggested-action')
        self.main_connect_btn.add_css_class('pill')
        self.main_connect_btn.set_size_request(-1, 50)
        self.main_connect_btn.set_sensitive(False) # Starts disabled
        
        def on_main_connect(b):
            if self.selected_host_card_data:
                h = self.selected_host_card_data
                self.connect_manual(h['ip'], str(h.get('port', 47989)))
        
        self.main_connect_btn.connect('clicked', on_main_connect)
        action_box.append(self.main_connect_btn)
        
        box.append(header_box)
        # box.append(scroll)
        box.append(self.hosts_list)
        box.append(action_box)
        
        return box

    def discover_hosts(self):
        """Descobre hosts na rede e popula a lista"""
        from utils.network import NetworkDiscovery
        import gi
        from gi.repository import Gtk, GLib
        
        # Reset state
        self.first_radio_in_list = None
        self.selected_host_card_data = None
        self.main_connect_btn.set_sensitive(False)
        self.main_connect_btn.set_label('Conectar')
        
        # Limpar lista
        while True:
            row = self.hosts_list.get_row_at_index(0)
            if row is None:
                break
            self.hosts_list.remove(row)
        
        # Placeholder de carregando
        self.loading_row = Gtk.ListBoxRow()
        self.loading_row.set_selectable(False)
        self.loading_row.set_activatable(False)
        
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        box.set_margin_top(12)
        box.set_margin_bottom(12)
        box.set_halign(Gtk.Align.CENTER)
        
        spinner = Gtk.Spinner()
        spinner.start()
        label = Gtk.Label(label='Procurando hosts...')
        
        box.append(spinner)
        box.append(label)
        self.loading_row.set_child(box)
        self.hosts_list.append(self.loading_row)
        
        def on_hosts_discovered(hosts):
            # Limpar placeholder de loading
            if self.loading_row.get_parent():
                self.hosts_list.remove(self.loading_row)
            
            # Resetar novamente o grupo de radio buttons
            self.first_radio_in_list = None
            
            if not hosts:
                row = Gtk.ListBoxRow()
                row.set_selectable(False)
                row.set_activatable(False)
                
                box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
                box.set_margin_top(24)
                box.set_margin_bottom(24)
                box.set_halign(Gtk.Align.CENTER)
                
                icon = Gtk.Image.new_from_icon_name('network-offline-symbolic')
                icon.set_pixel_size(48)
                icon.add_css_class('dim-label')
                
                lbl = Gtk.Label(label='Nenhum host encontrado')
                lbl.add_css_class('title-2')
                
                box.append(icon)
                box.append(lbl)
                
                row.set_child(box)
                self.hosts_list.append(row)
            else:
                for host in hosts:
                    self.hosts_list.append(self.create_host_row_custom(host))
            
            return False

        discovery = NetworkDiscovery()
        # Fix: Passar on_hosts_discovered diretamente. 
        # A lambda anterior retornava o ID do idle_add (True), causando loop infinito no idle_add do network.py
        discovery.discover_hosts(callback=on_hosts_discovered)

    def update_hosts_list(self, hosts):
        # Limpar
        self.first_radio_in_list = None
        self.selected_host_card_data = None
        self.main_connect_btn.set_sensitive(False)
        
        while True:
            row = self.hosts_list.get_row_at_index(0)
            if row is None:
                break
            self.hosts_list.remove(row)
            
        for host in hosts:
            self.hosts_list.append(self.create_host_row_custom(host))

    def create_host_row_custom(self, host):
        """Cria uma linha com RadioButton para seleção"""
        row = Gtk.ListBoxRow()
        row.set_activatable(False)
        row.set_selectable(False)
        
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        box.set_margin_start(12)
        box.set_margin_end(12)
        box.set_margin_top(12)
        box.set_margin_bottom(12)
        
        # Radio Button (CheckButton in group)
        radio = Gtk.CheckButton()
        radio.set_valign(Gtk.Align.CENTER)
        
        # Adicionar o radio button primeiro antes de configurar o grupo
        if self.first_radio_in_list is None:
            self.first_radio_in_list = radio
        else:
            radio.set_group(self.first_radio_in_list)
        
        def on_toggled(btn):
            if btn.get_active():
                self.selected_host_card_data = host
                self.main_connect_btn.set_sensitive(True)
                self.main_connect_btn.set_label(f"Conectar a {host['name']}")
                print(f"DEBUG: Host selecionado: {host['name']}")
        
        radio.connect('toggled', on_toggled)
        
        # Ícone
        icon = Gtk.Image.new_from_icon_name('computer-symbolic')
        icon.set_pixel_size(32)
        
        # Info Box (Nome e IP)
        info = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        info.set_valign(Gtk.Align.CENTER)
        
        name_lbl = Gtk.Label(label=host['name'])
        name_lbl.set_halign(Gtk.Align.START)
        name_lbl.add_css_class('heading')
        
        ip_lbl = Gtk.Label(label=host['ip'])
        ip_lbl.set_halign(Gtk.Align.START)
        ip_lbl.add_css_class('dim-label')
        
        info.append(name_lbl)
        info.append(ip_lbl)
        
        # Appends
        box.append(radio)
        box.append(icon)
        box.append(info)
        
        row.set_child(box)
        
        # Adicionar GestureClick à linha inteira
        gesture = Gtk.GestureClick()
        gesture.connect("pressed", lambda gesture, n, x, y: self.on_row_clicked(gesture, radio, row, x, y))
        row.add_controller(gesture)
        
        return row

    def on_row_clicked(self, gesture, radio_button, row, x, y):
        """Handler para clique na linha"""
        # Ativar o radio button quando a linha for clicada
        radio_button.set_active(True)
        return True
        
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
        

    def show_loading(self, show=True, message=""):
        """Mostra/Oculta diálogo de carregamento"""
        if show:
            if not hasattr(self, 'loading_dialog') or not self.loading_dialog:
                self.loading_dialog = Adw.MessageDialog(
                    heading='Aguarde',
                    body=message
                )
                spinner = Gtk.Spinner()
                spinner.start()
                spinner.set_halign(Gtk.Align.CENTER)
                spinner.set_size_request(32, 32)
                spinner.set_margin_top(12)
                self.loading_dialog.set_extra_child(spinner)
                self.loading_dialog.present()
            else:
                self.loading_dialog.set_body(message)
        else:
            if hasattr(self, 'loading_dialog') and self.loading_dialog:
                self.loading_dialog.close()
                self.loading_dialog = None
                
    def show_pin_dialog(self, pin):
        """Mostra o diálogo com o PIN e instruções"""
        if self.pin_dialog:
            self.pin_dialog.close()
            
        self.pin_dialog = Adw.MessageDialog(
            heading='Pareamento Necessário',
            body=(
                f'O Moonlight precisa ser pareado com o servidor.\n\n'
                f'<span size="xx-large" weight="bold" color="accent-color">{pin}</span>\n\n'
                f'<b>Próximos Passos:</b>\n'
                f'1. Clique em "Abrir Painel Sunshine" abaixo (ou acesse https://localhost:47990)\n'
                f'2. No menu superior do site, clique em <b>PIN</b>\n'
                f'3. Digite o código acima e clique em Send'
            )
        )
        self.pin_dialog.set_body_use_markup(True)
        
        self.pin_dialog.add_response('cancel', 'Cancelar')
        self.pin_dialog.add_response('open_url', 'Abrir Painel Sunshine')
        
        self.pin_dialog.set_response_appearance('open_url', Adw.ResponseAppearance.SUGGESTED)
        
        def on_response(dialog, response):
            if response == 'open_url':
                # Reabrir dialogo já que ele fecha ao responder
                # Mas espera, se fechar perde o PIN? 
                # AdwMessageDialog fecha auto. Vamos abrir a URL e tentar manter ou não.
                # Melho: Apenas abrir URL e o usuario reabre se precisar (mas o pairing background continua)
                import webbrowser
                webbrowser.open('https://localhost:47990/pin')
                # O ideal seria não fechar, mas MessageDialog é modal simples.
                # Vamos re-exibir o dialogo se clicar em abrir?
                # Ou usar um CustomDialog... Para simplificar, vamos instruir.
                # Como o processo de fundo espera, se o dialogo fechar, o usuario pode perder o PIN visualmente.
                # Hack: Emitir signal para reabrir? 
                # Na verdade, se clicar em Open URL, ele fecha. Vamos impedir isso? 
                # AdwMessageDialog nao permite impedir fechamento facil no response.
                # Workaround: Re-mostrar imediatamente.
                self.show_pin_dialog(pin)
            
        self.pin_dialog.connect('response', on_response)
        
        self.pin_dialog.present()
        
    def close_pin_dialog(self):
        if self.pin_dialog:
            self.pin_dialog.close()
            self.pin_dialog = None

    def show_pairing_dialog(self, host_ip, pin=None, on_confirm=None):
        """Mostra diálogo para pareamento (Manual ou Automático)"""
        if hasattr(self, 'pairing_dialog') and self.pairing_dialog:
            # Se já existe, apenas atualiza o corpo senao fecha e recria (pra simplificar)
            if pin:
                # Atualizar texto com o PIN
                body_text = (
                    f'O Moonlight precisa ser pareado com o servidor.\n\n'
                    f'<span size="xx-large" weight="bold" color="accent-color">{pin}</span>\n\n'
                    f'<b>Passos:</b>\n'
                    f'1. Abra o Painel Sunshine\n'
                    f'2. Vá na aba PIN\n'
                    f'3. Digite o código acima e clique em Send'
                )
                self.pairing_dialog.set_body(body_text)
                return

        # Fechar anteriores
        if hasattr(self, 'pairing_dialog') and self.pairing_dialog:
             self.pairing_dialog.close()
             
        # Texto inicial (sem PIN ainda)
        body_text = (
            f'Pareamento Iniciado.\n\n'
            f'Uma janela do Moonlight deve abrir com o código <b>PIN</b>.\n'
            f'Se o código aparecer aqui, nós o mostraremos.\n\n'
            f'<b>Passos:</b>\n'
            f'1. Pegue o PIN (aqui ou na janela do Moonlight)\n'
            f'2. Clique em "Abrir Painel Sunshine" abaixo\n'
            f'3. Digite o PIN e confirme.'
        )
        
        if pin:
             body_text = (
                f'O Moonlight precisa ser pareado com o servidor.\n\n'
                f'<span size="xx-large" weight="bold" color="accent-color">{pin}</span>\n\n'
                f'<b>Passos:</b>\n'
                f'1. Abra o Painel Sunshine\n'
                f'2. Vá na aba PIN\n'
                f'3. Digite o código acima e clique em Send'
            )

        self.pairing_dialog = Adw.MessageDialog(
            heading='Pareamento',
            body=body_text
        )
        self.pairing_dialog.set_body_use_markup(True)
        
        self.pairing_dialog.add_response('cancel', 'Cancelar')
        self.pairing_dialog.add_response('open_url', 'Abrir Painel Sunshine')
        self.pairing_dialog.add_response('continue', 'Continuar')
        
        self.pairing_dialog.set_response_appearance('continue', Adw.ResponseAppearance.SUGGESTED)
        
        def on_response(dialog, response):
            if response == 'open_url':
                import webbrowser
                webbrowser.open('https://localhost:47990/pin')
                # Reabrir diálogo pois ele fecha
                # Hack: usar GLib idle para reabrir
                GLib.idle_add(lambda: self.show_pairing_dialog(host_ip, pin, on_confirm))
            elif response == 'continue':
                if on_confirm:
                    on_confirm()
            elif response == 'cancel':
                 # User cancelling
                 pass
            
        self.pairing_dialog.connect('response', on_response)
        self.pairing_dialog.present()
        
    def close_pairing_dialog(self):
        if hasattr(self, 'pairing_dialog') and self.pairing_dialog:
            self.pairing_dialog.close()
            self.pairing_dialog = None

    def connect_to_host(self, host):
        """Conecta a um host (Threaded Flow)"""
        from guest.moonlight_client import MoonlightClient
        import threading
        from gi.repository import GLib

        def connection_flow():
            try:
                GLib.idle_add(lambda: self.show_loading(True, "Verificando host..."))
                
                # 1. Verificar se Host precisa parear
                print(f"DEBUG: Probing host {host['ip']}...")
                is_paired = self.moonlight.probe_host(host['ip'])
                print(f"DEBUG: Host paired status: {is_paired}")
                
                if not is_paired:
                    GLib.idle_add(lambda: self.show_loading(True, "Iniciando pareamento..."))
                    print(f"Host {host['ip']} não pareado. Iniciando pareamento...")
                    
                    # Definir ação de continuação (quando usuario clicar em Continuar)
                    def on_user_confirmed():
                        threading.Thread(target=do_connect).start()
                    
                    # Mostrar diálogo IMEDIATAMENTE (antes do pair bloquear)
                    GLib.idle_add(lambda: self.show_pairing_dialog(host['ip'], None, on_user_confirmed))
                    
                    # Callback para atualizar PIN se capturado
                    def on_pin(pin):
                        GLib.idle_add(lambda: self.show_pairing_dialog(host['ip'], pin, on_user_confirmed))
                    
                    # Executa pareamento (Bloqueante)
                    success = self.moonlight.pair(host['ip'], on_pin)
                    
                    if success:
                        GLib.idle_add(self.close_pairing_dialog)
                        GLib.idle_add(lambda: self.show_loading(True, "Pareamento concluído. Conectando..."))
                        do_connect()
                    else:
                        GLib.idle_add(lambda: self.show_error_dialog("Falha no Pareamento", 
                            "O processo de pareamento falhou ou foi cancelado."))
                        GLib.idle_add(self.close_pairing_dialog)
                        GLib.idle_add(lambda: self.show_loading(False))
                    
                    return

                # Se já estava pareado
                GLib.idle_add(lambda: self.show_loading(True, "Iniciando streaming..."))
                do_connect()
                
            except Exception as e:
                print(f"ERROR: Exception in connection_flow: {e}")
                import traceback
                traceback.print_exc()
                GLib.idle_add(lambda: self.show_error_dialog("Erro Interno", f"Erro ao conectar: {str(e)}"))
                GLib.idle_add(lambda: self.show_loading(False))

        def do_connect():
            GLib.idle_add(safe_connect_step)
            
        def safe_connect_step():
            self.show_loading(True, "Conectando...")
            
            # Obter configurações da UI
            quality_map = {
                0: 'auto',
                1: '720p30',
                2: '1080p30',
                3: '1080p60',
                4: '1440p60',
                5: '4k60',
            }
            
            selected_quality_idx = self.quality_row.get_selected()
            quality = quality_map.get(selected_quality_idx, 'auto')
            fullscreen = self.fullscreen_row.get_active()
            audio = self.audio_row.get_active()
            hw_decode = self.hw_decode_row.get_active()

            # Executar lógica de conexão
            try:
                # Verificar instalação
                if not self.moonlight.moonlight_cmd:
                     self.show_error_dialog('Moonlight Não Encontrado', 'Moonlight não instalado.')
                     self.show_loading(False)
                     return

                # Connect
                self.close_pairing_dialog() # Garantir fechamento
                
                success = self.moonlight.connect(
                    host['ip'],
                    quality=quality,
                    fullscreen=fullscreen,
                    audio=audio,
                    hw_decode=hw_decode
                )
                
                if success:
                    self.show_toast(f'Conectando a {host["name"]}...')
                    self.is_connected = True
                    self.status_label.set_text(f'Conectado a {host["name"]}')
                    self.status_sublabel.set_text('Sessão ativa')
                    self.status_icon.set_from_icon_name('network-transmit-receive-symbolic')
                    
                    self.perf_monitor.set_visible(True)
                    self.perf_monitor.start_monitoring()
                else:
                    self.show_error_dialog('Falha na Conexão', 'Não foi possível iniciar o Moonlight.')
                        
            except Exception as e:
                self.show_error_dialog('Erro', f'Ocorreu um erro: {e}')
                
            self.show_loading(False)

        # Iniciar thread
        threading.Thread(target=connection_flow).start()
        
    def connect_manual(self, ip, port):
        """Conecta manualmente via IP"""
        if not ip:
            return
            
        host = {
            'name': ip,
            'ip': ip,
            'port': int(port) if port else 47989,
            'status': 'unknown'
        }
        self.connect_to_host(host)
        
    def connect_pin(self, pin):
        """Conecta via PIN"""
        if len(pin) != 6 or not pin.isdigit():
            self.show_error_dialog('PIN Inválido',
                'O PIN deve conter exatamente 6 dígitos.')
            return
        
        self.show_loading(True, "Procurando host com este PIN...")
        
        def resolve_thread():
             from utils.network import NetworkDiscovery
             ip = NetworkDiscovery().resolve_pin(pin)
             
             if ip:
                 GLib.idle_add(lambda: self._on_pin_resolved(ip, pin))
             else:
                 GLib.idle_add(lambda: self._on_pin_failed())
                 
        threading.Thread(target=resolve_thread, daemon=True).start()
        
    def _on_pin_resolved(self, ip, pin):
        """Callback quando PIN é resolvido"""
        self.show_loading(False)
        self.show_toast(f"Host encontrado: {ip}")
        # Conectar manualmente usando o IP encontrado
        # Usamos porta padrão 47989
        self.connect_manual(ip, '47989')
        
    def _on_pin_failed(self):
        """Callback quando falha resolver PIN"""
        self.show_loading(False)
        self.show_error_dialog('Host Não Encontrado',
            'Não foi possível encontrar um host com este PIN na rede local.\n'
            'Verifique se o host está rodando e na mesma rede.')
    
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
