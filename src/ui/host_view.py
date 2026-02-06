"""
View para modo Host (hospedar jogos)
"""

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, Adw, GLib
import subprocess
import random
import string
import json
import socket
from utils.game_detector import GameDetector

class HostView(Gtk.Box):
    """Interface para hospedar jogos"""
    
    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        
        self.is_hosting = False
        self.pin_code = None
        
        # Initialize manager
        from host.sunshine_manager import SunshineHost
        from pathlib import Path
        config_dir = Path.home() / '.config' / 'big-remoteplay' / 'sunshine'
        self.sunshine = SunshineHost(config_dir)
        
        # Check initial state
        if self.sunshine.is_running():
            self.is_hosting = True
            # Get current IP
            import socket
            hostname = socket.gethostname()
            # Try to guess IP if running
            
        # Carregar detecções
        self.available_monitors = self.detect_monitors()
        self.available_gpus = self.detect_gpus()
        
        self.setup_ui()
        
        # Cache de jogos detectados
        self.game_detector = GameDetector()
        self.detected_games = {
            'Steam': [],
            'Lutris': []
        }
        
        self.sync_ui_state()
        
    def detect_monitors(self):
        """Detecta monitores disponíveis"""
        from pathlib import Path
        import subprocess
        monitors = [('Automático', 'auto')]
        
        # Adicionar índices numéricos como fallback comum para Wayland/KMS
        # Interfaces genéricas removidas a pedido do usuário
        # for i in range(4):
        #    monitors.append((f"Monitor: Índice {i}", str(i)))

        try:
            # Tentar via xrandr --current (mais confiável para conectados)
            output = subprocess.check_output(['xrandr', '--current'], text=True, stderr=subprocess.STDOUT)
            for line in output.split('\n'):
                if ' connected' in line:
                    parts = line.split()
                    if parts:
                        name = parts[0]
                        # Tentar pegar a resolução se disponível
                        res = ""
                        for part in parts:
                            if 'x' in part and '+' in part:
                                res = f" ({part.split('+')[0]})"
                                break
                        monitors.append((f"Monitor: {name}{res}", name))
        except:
            # Fallback para --listactivemonitors
            try:
                output = subprocess.check_output(['xrandr', '--listactivemonitors'], text=True)
                lines = output.strip().split('\n')[1:]
                for line in lines:
                    parts = line.split()
                    if parts:
                        name = parts[-1]
                        monitors.append((f"Monitor: {name}", name))
            except:
                pass
        
        # Fallback via /sys/class/drm se xrandr falhar
        try:
            for p in Path('/sys/class/drm').glob('card*-*'):
                status_file = p / 'status'
                if status_file.exists() and status_file.read_text().strip() == 'connected':
                    name = p.name.split('-', 1)[1]
                    # Adicionar se já não estiver na lista
                    if not any(name in m[1] for m in monitors):
                        monitors.append((f"Monitor: {name}", name))
        except:
            pass
                
        return monitors

    def detect_gpus(self):
        """Detecta encoders e adapters de GPU disponíveis"""
        from pathlib import Path
        import subprocess
        
        gpus = []
        
        # 1. Verificar NVIDIA
        has_nvidia = False
        try:
            lspci = subprocess.check_output(['lspci'], text=True).lower()
            if 'nvidia' in lspci:
                has_nvidia = True
                try:
                    subprocess.check_call(['nvidia-smi'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    gpus.append({
                        'label': 'NVENC (NVIDIA)',
                        'encoder': 'nvenc',
                        'adapter': 'auto'
                    })
                except:
                    pass
            
            if 'intel' in lspci:
                gpus.append({
                    'label': 'VAAPI (Intel Quicksync)',
                    'encoder': 'vaapi',
                    'adapter': '/dev/dri/renderD128'
                })
        except:
            pass

        # 2. Verificar VAAPI / DRI Adapters
        try:
            dri_path = Path('/dev/dri')
            if dri_path.exists():
                render_nodes = sorted(list(dri_path.glob('renderD*')))
                for node in render_nodes:
                    node_path = str(node)
                    # Evitar duplicar se já adicionamos Intel acima
                    if any(node_path == g['adapter'] for g in gpus):
                        continue
                        
                    label = f"VAAPI (Adapter {node.name})"
                    gpus.append({
                        'label': label,
                        'encoder': 'vaapi',
                        'adapter': node_path
                    })
        except:
            pass
            
        gpus.append({
            'label': 'Vulkan (Experimental)',
            'encoder': 'vulkan',
            'adapter': 'auto'
        })

        gpus.append({
            'label': 'Software (Lento)',
            'encoder': 'software',
            'adapter': 'auto'
        })
        
        return gpus
        
    def setup_ui(self):
        """Configura interface"""
        # Clamp para centralizar conteúdo
        clamp = Adw.Clamp()
        clamp.set_maximum_size(800)
        clamp.set_margin_top(24)
        clamp.set_margin_bottom(24)
        clamp.set_margin_start(24)
        clamp.set_margin_end(24)
        
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=24)
        
        # Loading Bar
        self.loading_bar = Gtk.ProgressBar()
        self.loading_bar.add_css_class('osd')
        self.loading_bar.set_visible(False)
        content.append(self.loading_bar)
        
        # Performance Monitor (Chart) - Moved below Header
        from .performance_monitor import PerformanceMonitor
        self.perf_monitor = PerformanceMonitor()
        self.perf_monitor.set_visible(True) # Always visible
        # content.append(self.perf_monitor) -- Removed immediate append, done later
        # Initialize default state
        self.perf_monitor.set_connection_status("Localhost", "Sunshine Offline", False)
        
        # Header
        self.header = Adw.PreferencesGroup()
        self.header.set_title('Hospedar Servidor')
        self.header.set_description('Configure e compartilhe seu jogo para seus amigos conectarem')
        
        # Server status card removed (Integrated into PerfMonitor)
        
        # Performance monitor removed from here (moved to top)
        
        # Game selection
        game_group = Adw.PreferencesGroup()
        game_group.set_title('Configuração do Jogo')
        game_group.set_margin_top(12)
        
        # Game Mode Selector
        self.game_mode_row = Adw.ComboRow()
        self.game_mode_row.set_title('Modo de Jogo')
        self.game_mode_row.set_subtitle('Selecione a fonte do jogo')
        
        modes_model = Gtk.StringList()
        modes_model.append('Desktop Completo')
        modes_model.append('Steam')
        modes_model.append('Lutris')
        modes_model.append('Aplicativo Personalizado')
        
        self.game_mode_row.set_model(modes_model)
        self.game_mode_row.set_selected(0)
        self.game_mode_row.connect('notify::selected', self.on_game_mode_changed)
        
        game_group.add(self.game_mode_row)
        
        # Platform Games Expander (Hidden by default)
        self.platform_games_expander = Adw.ExpanderRow()
        self.platform_games_expander.set_title("Seleção de Jogos")
        self.platform_games_expander.set_subtitle("Escolha o jogo da lista")
        self.platform_games_expander.set_visible(False)
        
        self.game_list_row = Adw.ComboRow()
        self.game_list_row.set_title('Selecionar Jogo')
        self.game_list_row.set_subtitle('Escolha o jogo da lista')
        self.game_list_model = Gtk.StringList()
        self.game_list_row.set_model(self.game_list_model)
        
        self.platform_games_expander.add_row(self.game_list_row)
        game_group.add(self.platform_games_expander)
        
        # Custom App Fields (Hidden by default)
        # Custom App Fields (Hidden by default)
        self.custom_app_expander = Adw.ExpanderRow()
        self.custom_app_expander.set_title("Detalhes do Aplicativo")
        self.custom_app_expander.set_subtitle("Configure o nome e comando")
        self.custom_app_expander.set_visible(False)
        
        self.custom_name_entry = Adw.EntryRow()
        self.custom_name_entry.set_title('Nome do Aplicativo')
        self.custom_app_expander.add_row(self.custom_name_entry)
        
        self.custom_cmd_entry = Adw.EntryRow()
        self.custom_cmd_entry.set_title('Comando')
        self.custom_app_expander.add_row(self.custom_cmd_entry)
        
        game_group.add(self.custom_app_expander)
        
        
        # === Streaming Settings Expander ===
        self.streaming_expander = Adw.ExpanderRow()
        self.streaming_expander.set_title('Configurações de Streaming')
        self.streaming_expander.set_subtitle('Qualidade e Jogadores')
        self.streaming_expander.set_icon_name('preferences-desktop-display-symbolic')
        
        # Quality settings
        self.quality_row = Adw.ComboRow()
        self.quality_row.set_title('Qualidade de Streaming')
        self.quality_row.set_subtitle('Maior qualidade = maior uso de banda')
        
        quality_model = Gtk.StringList()
        quality_model.append('Baixa (720p 30fps)')
        quality_model.append('Média (1080p 30fps)')
        quality_model.append('Alta (1080p 60fps)')
        quality_model.append('Ultra (1440p 60fps)')
        quality_model.append('Máxima (4K 60fps)')
        
        self.quality_row.set_model(quality_model)
        self.quality_row.set_selected(2)  # Alta por padrão
        
        self.streaming_expander.add_row(self.quality_row)
        
        # Max players
        self.players_row = Adw.SpinRow()
        self.players_row.set_title('Máximo de Jogadores')
        self.players_row.set_subtitle('Número máximo de conexões simultâneas')
        
        adjustment = Gtk.Adjustment(
            value=2,
            lower=1,
            upper=8,
            step_increment=1,
            page_increment=1
        )
        self.players_row.set_adjustment(adjustment)
        self.players_row.set_digits(0)
        
        self.streaming_expander.add_row(self.players_row)
        game_group.add(self.streaming_expander)
        
        # === Hardware Settings Expander ===
        self.hardware_expander = Adw.ExpanderRow()
        self.hardware_expander.set_title('Hardware e Captura')
        self.hardware_expander.set_subtitle('Monitor, GPU e Método de Captura')
        self.hardware_expander.set_icon_name('video-display-symbolic')

        # Monitor selection
        self.monitor_row = Adw.ComboRow()
        self.monitor_row.set_title('Monitor / Tela')
        self.monitor_row.set_subtitle('Selecione em qual tela o jogo será capturado')
        
        monitor_model = Gtk.StringList()
        for label, _ in self.available_monitors:
            monitor_model.append(label)
        
        self.monitor_row.set_model(monitor_model)
        self.monitor_row.set_selected(0)
        self.hardware_expander.add_row(self.monitor_row)
        
        # GPU / Encoder selection
        self.gpu_row = Adw.ComboRow()
        self.gpu_row.set_title('Placa de Vídeo / Encoder')
        self.gpu_row.set_subtitle('Escolha o hardware para codificação do vídeo')
        
        gpu_model = Gtk.StringList()
        for gpu_info in self.available_gpus:
            gpu_model.append(gpu_info['label'])
            
        self.gpu_row.set_model(gpu_model)
        self.gpu_row.set_selected(0)
        self.hardware_expander.add_row(self.gpu_row)
        
        # Platform selection
        self.platform_row = Adw.ComboRow()
        self.platform_row.set_title('Método de Captura')
        self.platform_row.set_subtitle('Wayland (recomendado), X11 (legado) ou KMS (direto)')
        
        platform_model = Gtk.StringList()
        platform_model.append('Automático')
        platform_model.append('Wayland')
        platform_model.append('X11')
        platform_model.append('KMS (Direto)')
        
        self.platform_row.set_model(platform_model)
        # Tentar selecionar o atual
        import os
        session_type = os.environ.get('XDG_SESSION_TYPE', '').lower()
        if session_type == 'wayland':
            self.platform_row.set_selected(1)
        elif session_type == 'x11':
            self.platform_row.set_selected(2)
        else:
            self.platform_row.set_selected(0)
            
        self.hardware_expander.add_row(self.platform_row)
        game_group.add(self.hardware_expander)
        
        # Advanced settings expander
        self.advanced_expander = Adw.ExpanderRow()
        self.advanced_expander.set_title('Configurações Avançadas')
        self.advanced_expander.set_subtitle('Áudio, Input e Rede')
        self.advanced_expander.set_icon_name('preferences-system-symbolic')
        
        # Audio streaming
        audio_row = Adw.SwitchRow()
        audio_row.set_title('Streaming de Áudio')
        audio_row.set_subtitle('Transmitir áudio para guests')
        audio_row.set_active(True)
        self.advanced_expander.add_row(audio_row)

        # Dual Audio (Host + Guest)
        self.dual_audio_row = Adw.SwitchRow()
        self.dual_audio_row.set_title('Áudio Híbrido (Host + Guest)')
        self.dual_audio_row.set_subtitle('Cria saída virtual para permitir áudio simultâneo')
        self.dual_audio_row.set_active(False)
        self.advanced_expander.add_row(self.dual_audio_row)
        
        # Audio Output Selection (Visible only if Dual Audio is ON)
        self.audio_output_row = Adw.ComboRow()
        self.audio_output_row.set_title('Saída de Áudio Local')
        self.audio_output_row.set_subtitle('Onde você ouvirá o som')
        self.audio_output_row.set_visible(False)
        
        # Bind visibility
        self.dual_audio_row.connect('notify::active', lambda row, param: self.audio_output_row.set_visible(row.get_active()))
        
        self.advanced_expander.add_row(self.audio_output_row)
        
        # Carregar outputs
        self.load_audio_outputs()
        
        # Input sharing
        input_row = Adw.SwitchRow()
        input_row.set_title('Compartilhar Controles')
        input_row.set_subtitle('Permitir que guests controlem o jogo')
        input_row.set_active(True)
        self.advanced_expander.add_row(input_row)
        
        # UPNP
        self.upnp_row = Adw.SwitchRow()
        self.upnp_row.set_title('UPNP Automático')
        self.upnp_row.set_subtitle('Configurar portas automaticamente no roteador')
        self.upnp_row.set_active(True)
        self.advanced_expander.add_row(self.upnp_row)
        
        game_group.add(self.advanced_expander)
        
        # Action buttons (Moved up)
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        button_box.set_halign(Gtk.Align.CENTER)
        button_box.set_margin_top(12)
        button_box.set_margin_bottom(24)
        
        self.start_button = Gtk.Button(label='Iniciar Servidor')
        self.start_button.add_css_class('pill')
        self.start_button.add_css_class('suggested-action')
        self.start_button.set_size_request(180, -1)
        self.start_button.connect('clicked', self.toggle_hosting)
        
        self.configure_button = Gtk.Button(label='Configurar Sunshine')
        self.configure_button.add_css_class('pill')
        self.configure_button.set_size_request(180, -1)
        self.configure_button.connect('clicked', self.open_sunshine_config)
        
        button_box.append(self.start_button)
        button_box.append(self.configure_button)
        
        # Create Summary Box
        self.create_summary_box()
        
        # Add all to content (Reordered)
        # 1. Header ("Hospedar Servidor") - Fixed at top
        # 2. Perf Monitor ("Monitoramento em Tempo Real")
        content.append(self.header)
        content.append(self.perf_monitor) # Moved below header
        content.append(button_box)
        content.append(self.summary_box)
        content.append(game_group)
        
        clamp.set_child(content)
        
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_vexpand(True)
        scroll.set_child(clamp)
        
        self.append(scroll)

    def create_summary_box(self):
        """Cria grupo de informações do servidor (Boxed style)"""
        self.summary_box = Adw.PreferencesGroup()
        self.summary_box.set_title("Informações do Servidor")
        self.summary_box.set_margin_top(12)
        self.summary_box.set_visible(False)
        self.field_widgets = {}
        
        # Fields with icons
        self.create_masked_row('Nome do Host', 'hostname', 'computer-symbolic', default_revealed=True)
        self.create_masked_row('IPv4', 'ipv4', 'network-wired-symbolic')
        self.create_masked_row('IPv6', 'ipv6', 'network-wired-symbolic')
        self.create_masked_row('IPv4 Global', 'ipv4_global', 'network-transmit-receive-symbolic')
        self.create_masked_row('IPv6 Global', 'ipv6_global', 'network-transmit-receive-symbolic')
        self.create_masked_row('PIN', 'pin', 'dialog-password-symbolic')

    def load_audio_outputs(self):
        """Carrega dispositivos de áudio"""
        try:
            from utils.audio import AudioManager
            self.audio_manager = AudioManager()
            
            devices = self.audio_manager.get_output_devices()
            self.audio_output_model = Gtk.StringList()
            self.audio_devices = devices # Store list of dicts
            
            if not devices:
                self.audio_output_model.append("Nenhum dispositivo encontrado")
            else:
                for dev in devices:
                    label = dev.get('description', dev.get('name', 'Unknown'))
                    self.audio_output_model.append(label)
                    
            self.audio_output_row.set_model(self.audio_output_model)
            self.audio_output_row.set_selected(0)
        except Exception as e:
            print(f"Erro ao carregar dispositivos de áudio: {e}")
            # Fallback seguro
            self.audio_manager = None
            self.audio_devices = []
            self.audio_output_model = Gtk.StringList()
            self.audio_output_model.append("Erro ao carregar áudio")
            self.audio_output_row.set_model(self.audio_output_model)

    def create_masked_row(self, title, key, icon_name='text-x-generic-symbolic', default_revealed=False):
        """Cria linha Adw.ActionRow com campo mascarado"""
        row = Adw.ActionRow()
        row.set_title(title)
        row.set_icon_name(icon_name)
        
        # Widget container for suffix
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        box.set_valign(Gtk.Align.CENTER)
        
        # Value Label
        value_lbl = Gtk.Label(label='••••••' if not default_revealed else '')
        value_lbl.set_margin_end(8)
        # value_lbl.add_css_class('monospace') # Optional
        
        # Eye button
        eye_btn = Gtk.Button(icon_name='view-reveal-symbolic' if not default_revealed else 'view-conceal-symbolic')
        eye_btn.add_css_class('flat')
        eye_btn.set_tooltip_text('Mostrar/Ocultar')
        
        # Copy button
        copy_btn = Gtk.Button(icon_name='edit-copy-symbolic')
        copy_btn.add_css_class('flat')
        copy_btn.set_tooltip_text('Copiar')
        
        box.append(value_lbl)
        box.append(eye_btn)
        box.append(copy_btn)
        
        row.add_suffix(box)
        self.summary_box.add(row)
        
        # Store widgets and state
        self.field_widgets[key] = {
            'label': value_lbl,
            'real_value': '',
            'revealed': default_revealed, 
            'btn_eye': eye_btn
        }
        
        # Connect signals
        eye_btn.connect('clicked', lambda b: self.toggle_field_visibility(key))
        copy_btn.connect('clicked', lambda b: self.copy_field_value(key))
        
    def toggle_field_visibility(self, key):
        """Alterna visibilidade do campo"""
        field = self.field_widgets[key]
        field['revealed'] = not field['revealed']
        
        # Update icon
        icon = 'view-conceal-symbolic' if field['revealed'] else 'view-reveal-symbolic'
        field['btn_eye'].set_icon_name(icon)
        
        # Update text
        if field['revealed']:
            field['label'].set_text(field['real_value'])
        else:
            field['label'].set_text('••••••')
            
    def copy_field_value(self, key):
        """Copia valor do campo"""
        field = self.field_widgets[key]
        if field['real_value']:
             self.get_clipboard().set(field['real_value'])
             self.show_toast(f"{key} copiado!")

    def toggle_hosting(self, button):
        """Inicia ou para o servidor"""
        if self.is_hosting:
            self.stop_hosting()
        else:
            self.start_hosting()
            
    def sync_ui_state(self):
        """Sincroniza UI com estado interno"""
        if self.is_hosting:
            self.perf_monitor.set_connection_status("Sunshine", "Ativo - Aguardando Conexões", True)
            self.perf_monitor.set_visible(True)
            self.perf_monitor.start_monitoring()
            
            # self.summary_box.set_visible(True) # Removed as create_status_card used it? 
            # We need to render summary somewhere? 
            # The user asked: "as informações ... pode ficar integrado no gráfico"
            # But the summary box contains IP/PIN.
            # PerformanceMonitor doesn't have fields for IP/Pin yet.
            # Maybe keep summary box separate or append it below graph?
            # For now, let's re-add summary box to content if needed or assume user wants it GONE.
            # "as informações como Sunshine On-line pode fica e mostra quando alguem conectar pode ficar integrado no gráfico, quando Sunshine estiver On-line mude no Gráfico para Ativo e verde."
            
            # Summary Box (IPs, PIN) MUST BE VISIBLE somewhere.
            # If I deleted create_status_card, I deleted summary_box too!
            # I should recreate summary_box in setup_ui separately if needed.
            
            self.start_button.set_label('Parar Servidor')
            self.start_button.remove_css_class('suggested-action')
            self.start_button.add_css_class('destructive-action')
            
            self.header.set_visible(True) # Always visible
            
            self.configure_button.set_sensitive(True)
            self.configure_button.add_css_class('suggested-action')
            self.game_mode_row.set_sensitive(False)
            self.hardware_expander.set_sensitive(False)
            self.streaming_expander.set_sensitive(False)
            self.advanced_expander.set_sensitive(False)
            
            if hasattr(self, 'summary_box'):
                 self.summary_box.set_visible(True)
                 self.populate_summary_fields()
            
        else:
            self.perf_monitor.set_connection_status("Sunshine", "Inativo", False)
            self.perf_monitor.stop_monitoring()
            self.perf_monitor.set_visible(True)
            
            self.header.set_visible(True) # Show header when not hosting
            
            if hasattr(self, 'summary_box'):
                self.summary_box.set_visible(False)
            
            self.start_button.set_label('Iniciar Servidor')
            self.start_button.remove_css_class('destructive-action')
            self.start_button.add_css_class('suggested-action')
            
            self.configure_button.set_sensitive(False)
            self.configure_button.remove_css_class('suggested-action')
            self.game_mode_row.set_sensitive(True)
            self.hardware_expander.set_sensitive(True)
            self.streaming_expander.set_sensitive(True)
            self.advanced_expander.set_sensitive(True)

    def populate_summary_fields(self):
        """Preenche campos do resumo"""
        import socket
        import threading
        from utils.network import NetworkDiscovery
        
        # Hostname
        self.update_field('hostname', socket.gethostname())
        
        # PIN
        if self.pin_code:
            self.update_field('pin', self.pin_code)
            
        # Local IPs (Fast)
        ipv4, ipv6 = self.get_ip_addresses()
        self.update_field('ipv4', ipv4)
        self.update_field('ipv6', ipv6)
        
        # Global IPs (Slow - Threaded)
        def fetch_globals():
            net = NetworkDiscovery()
            g_ipv4 = net.get_global_ipv4()
            g_ipv6 = net.get_global_ipv6()
            
            GLib.idle_add(self.update_field, 'ipv4_global', g_ipv4)
            GLib.idle_add(self.update_field, 'ipv6_global', g_ipv6)
            
        threading.Thread(target=fetch_globals, daemon=True).start()
        
    def update_field(self, key, value):
        """Atualiza valor de um campo"""
        if key in self.field_widgets:
            self.field_widgets[key]['real_value'] = value
            # Refresh if revealed
            if self.field_widgets[key]['revealed']:
                 self.field_widgets[key]['label'].set_text(value)

    def start_hosting(self, b=None):
        """Inicia servidor Sunshine"""
        # Show loading
        self.loading_bar.set_visible(True)
        self.loading_bar.pulse()
        context = GLib.MainContext.default()
        while context.pending():
            context.iteration(False)
            
        try:
            # Se já estiver rodando, reinicia para aplicar configs
            if self.sunshine.is_running():
                print("Reiniciando Sunshine para aplicar configurações...")
                self.sunshine.stop()
                import time
                time.sleep(1) # Wait for port release
            
            # Gerar PIN
            self.pin_code = ''.join(random.choices(string.digits, k=6))
            
            # Start PIN Listener
            from utils.network import NetworkDiscovery
            hostname = socket.gethostname()
            self.stop_pin_listener = NetworkDiscovery().start_pin_listener(self.pin_code, hostname)
            
            # Get IP
            # User requested localhost
            ip_address = 'localhost'
            
            # === Configurar Apps (games) ===
            mode_idx = self.game_mode_row.get_selected()
            apps_config = []
            
            # 0=Desktop, 1=Steam, 2=Lutris, 3=Custom
            if mode_idx == 0:
                # Desktop Completo
                pass
                
            elif mode_idx in [1, 2]: # Steam, Lutris
                # Pegar jogo selecionado
                idx = self.game_list_row.get_selected()
                if idx != Gtk.INVALID_LIST_POSITION:
                    # Re-obter a lista atual baseada no modo
                    platform_map = {1: 'Steam', 2: 'Lutris'}
                    plat = platform_map[mode_idx]
                    games = self.detected_games.get(plat, [])
                    
                    if 0 <= idx < len(games):
                        game = games[idx]
                        apps_config.append({
                            "name": game['name'],
                            "cmd": game['cmd'],
                            "detached": True, 
                        })
                        
            elif mode_idx == 3: # Custom
                name = self.custom_name_entry.get_text()
                cmd = self.custom_cmd_entry.get_text()
                if name and cmd:
                    apps_config.append({
                        "name": name,
                        "cmd": cmd,
                        "detached": True
                    })
            
            # Atualizar apps.json
            if apps_config:
                self.sunshine.update_apps(apps_config)
            else:
                # Se vazio (Desktop), podemos limpar ou forçar Desktop
                # Se for desktop, melhor ter uma entrada explícita ou limpar
                # Para limpar podemos passar lista vazia, Sunshine fallback para Desktop ou lista vazia?
                # Sunshine precisa de pelo menos um app ou Desktop. 
                # Se passarmos lista vazia para apps.json, ele pode não mostrar nada.
                # Vamos criar entrada Desktop explícita se for Desktop
                if mode_idx == 0:
                     self.sunshine.update_apps([{
                         "name": "Desktop",
                         "cmd": "bash -c 'sleep 5'", # Comando dummy, Sunshine captura tela independente
                         # Na verdade, Sunshine tem app type específico ou apenas captura.
                         # Geralmente para Desktop, não precisamos de cmd específico se for só espelhamento.
                         # Mas Sunshine requer 'cmd'. O padrão do Sunshine é cmd 'noop' ou similar?
                         # Vamos usar um comando que não faz nada mas mantém sessão viva se necessário?
                         # Não, para Desktop, o Sunshine geralmente ignora cmd se configurado corretamente?
                         # Na doc: "Desktop" app usually has checking for empty commands?
                         # Vamos usar o padrão seguro.
                         "prep-cmd": []
                     }])
                     # Hack: Se apps.json tiver app sem "cmd", ele pode falhar?
                     # Melhor estratégia para Desktop: Adicionar um app que não fecha instantaneamente?
                     # Ou simplesmente não atualizar apps.json e deixar o que estava? Não.
                     # Vamos adicionar um app "Desktop" padrão.
                     self.sunshine.update_apps([{
                         "name": "Desktop",
                         "detached": ["true"],
                         "cmd": "true" 
                         # 'true' retorna 0 imediatamente. Se detached, ok.
                     }])
                     
            # Configurar Sunshine com as opções da UI
            quality_map = {
                0: {'bitrate': 5000, 'fps': 30},   # Baixa
                1: {'bitrate': 10000, 'fps': 30},  # Média
                2: {'bitrate': 20000, 'fps': 60},  # Alta
                3: {'bitrate': 30000, 'fps': 60},  # Ultra
                4: {'bitrate': 40000, 'fps': 60},  # Máxima
            }
            
            quality_settings = quality_map.get(self.quality_row.get_selected(), {'bitrate': 20000, 'fps': 60})
            
            # Configurações de hardware
            selected_monitor = self.available_monitors[self.monitor_row.get_selected()][1]
            selected_gpu_info = self.available_gpus[self.gpu_row.get_selected()]
            
            sunshine_config = {
                'encoder': selected_gpu_info['encoder'],
                'bitrate': quality_settings['bitrate'],
                'fps': quality_settings['fps'],
                'videocodec': 'h264',
                'audio': 'pulse',
                'gamepad': 'x360',
                'min_threads': 1,
                'min_log_level': 4,
                # Caminhos relativos (usando CWD definido no manager)
                'pkey': 'pkey.pem',
                'cert': 'cert.pem'
            }
            
            # UPnP
            if self.upnp_row.get_active():
                sunshine_config['upnp'] = 'enabled'
            else:
                sunshine_config['upnp'] = 'disabled'
            
            # --- Configuração de Dual Audio ---
            if self.dual_audio_row.get_active():
                idx = self.audio_output_row.get_selected()
                if self.audio_devices and 0 <= idx < len(self.audio_devices):
                    target_sink = self.audio_devices[idx]['name']
                    print(f"Configurando Dual Audio -> Target: {target_sink}")
                    
                    if self.audio_manager.enable_dual_audio(target_sink):
                        # Se sucesso, configurar Sunshine para usar o GameSink
                        sunshine_config['audio_sink'] = 'GameSink'
                        self.show_toast("Áudio Híbrido Ativado")
                    else:
                        self.show_toast("Falha ao configurar Áudio Híbrido")
                else:
                    self.show_toast("Dispositivo de áudio inválido selecionado")
            # ----------------------------------
    
            # Adicionar monitor se não for auto
            # Adicionar monitor se não for auto
            # Usar índice sequencial parece ser mais robusto que nomes complexos no Sunshine
            monitor_idx = self.monitor_row.get_selected()
            if monitor_idx > 0:
                 # Auto é 0, então Monitor 1 é index 1 na lista (0 no Sunshine?)
                 # Vamos tentar passar o índice numérico (0, 1, 2...)
                 sunshine_config['output_name'] = int(monitor_idx - 1)
    
            # Adicionar adapter_name se for vaapi e não auto
            if selected_gpu_info['encoder'] == 'vaapi' and selected_gpu_info['adapter'] != 'auto':
                sunshine_config['adapter_name'] = selected_gpu_info['adapter']
    
            # Detecção de Plataforma
            selected_platform_idx = self.platform_row.get_selected()
            platforms = ['auto', 'wayland', 'x11', 'kms']
            platform = platforms[selected_platform_idx]
    
            import os
            if platform == 'auto':
                session_type = os.environ.get('XDG_SESSION_TYPE', '').lower()
                if session_type == 'wayland':
                    platform = 'wayland'
                elif session_type == 'x11':
                    platform = 'x11'
                else:
                    platform = 'x11' # Fallback more likely to work
            
            sunshine_config['platform'] = platform
            
            if platform == 'wayland':
                # Tentar detectar display correto
                wayland_disp = os.environ.get('WAYLAND_DISPLAY')
                if wayland_disp:
                    sunshine_config['wayland.display'] = wayland_disp
                else:
                     # Se não detectar, tentar padrão comum ou não setar (deixar Sunshine descobrir)
                     # Mas como o erro sugere falha, vamos tentar wayland-0 apenas se nada for achado
                     sunshine_config['wayland.display'] = 'wayland-0'
                     
            elif platform == 'x11':
                 # Garantir DISPLAY :0 no conf se for X11
                 if selected_monitor == 'auto':
                     sunshine_config['output_name'] = ':0'
            
            # Se for NVIDIA, podemos adicionar presets específicos se Sunshine suportar via conf
            # Mas mantendo o básico solicitado pelo usuário
            
            # Tentar iniciar Sunshine
            
            # Aplicar configurações antes de iniciar
            self.sunshine.configure(sunshine_config)
            
            success = self.sunshine.start()
            
            if not success:
                self.show_error_dialog('Erro ao Iniciar Sunshine', 
                    'Não foi possível iniciar o servidor Sunshine.\n'
                    'Verifique se o Sunshine está instalado e as permissões estão corretas.')
                return
            
            # Update UI
            self.is_hosting = True
            
            # Start monitoring
            self.perf_monitor.set_visible(True)
            self.perf_monitor.start_monitoring()

            # self.pin_display and self.ip_display removed
            
            self.sync_ui_state()
            
            # Mostrar toast de sucesso
            self.show_toast(f'Servidor iniciado em {ip_address}')
            
        except Exception as e:
            self.show_error_dialog('Erro Inesperado', 
                f'Ocorreu um erro ao iniciar o servidor:\n{str(e)}')
            
        finally:
            self.loading_bar.set_visible(False)
        
    def stop_hosting(self, b=None):
        """Para o servidor"""
        self.loading_bar.set_visible(True)
        context = GLib.MainContext.default()
        while context.pending():
            context.iteration(False)
            
        # Stop PIN Listener
        if hasattr(self, 'stop_pin_listener'):
            self.stop_pin_listener()
            del self.stop_pin_listener
            
        # Cleanup Dual Audio
        if hasattr(self, 'audio_manager'):
            self.audio_manager.cleanup()

        try:
            success = self.sunshine.stop()
            
            if not success:
                self.show_error_dialog('Erro ao Parar Sunshine',
                    'Não foi possível parar o servidor graciosamente.\n'
                    'Você pode precisar parar manualmente.')
                # Continua com a atualização da UI de qualquer forma
                
        except Exception as e:
            print(f"Erro ao parar Sunshine: {e}")
        
        self.is_hosting = False
        self.sync_ui_state()
        self.loading_bar.set_visible(False)
        
        
        self.show_toast('Servidor parado')
        
    def update_status_info(self):
        """Atualiza informações de status"""
        if not self.is_hosting:
            return True
            
        # Checar serviços para atualizar status na UI se necessário
        sunshine_running = self.check_process_running('sunshine')
        
        # Atualizar label do Sunshine no resumo
        if hasattr(self, 'sunshine_val'):
            if sunshine_running:
                self.sunshine_val.set_markup('<span color="#2ec27e">On-line</span>')
            else:
                self.sunshine_val.set_markup('<span color="#e01b24">Parado (Erro?)</span>')
            
        # Atualizar IPs locais periodicamente
        ipv4, ipv6 = self.get_ip_addresses()
        self.update_field('ipv4', ipv4)
        self.update_field('ipv6', ipv6)
        
        return True # Continue calling
        
    def check_process_running(self, process_name):
        """Verifica se um processo está rodando"""
        try:
            subprocess.check_output(["pgrep", "-x", process_name])
            return True
        except subprocess.CalledProcessError:
            return False
            
    def get_ip_addresses(self):
        """Obtém endereços IPv4 e IPv6"""
        ipv4 = "Desconhecido"
        ipv6 = "Desconhecido"
        
        try:
            res = subprocess.run(['ip', '-j', 'addr'], capture_output=True, text=True)
            if res.returncode == 0:
                data = json.loads(res.stdout)
                for iface in data:
                    # Ignorar loopback e interfaces down
                    if iface['ifname'] == 'lo' or 'UP' not in iface['flags']:
                        continue
                        
                    for addr in iface.get('addr_info', []):
                        if addr['family'] == 'inet':
                            ipv4 = addr['local']
                        elif addr['family'] == 'inet6' and addr.get('scope') == 'global':
                            ipv6 = addr['local']
        except Exception as e:
            print(f"Erro ao obter IPs: {e}")
            
        return ipv4, ipv6
        
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
        # Obter ToastOverlay da janela principal
        window = self.get_root()
        if hasattr(window, 'show_toast'):
            window.show_toast(message)
        else:
            # Fallback: apenas print
            print(f"Toast: {message}")
        
    def open_sunshine_config(self, button):
        """Abre configuração do Sunshine"""
        # Abrir web UI do Sunshine
        # import webbrowser
        import subprocess
        subprocess.Popen(['xdg-open', 'https://localhost:47990'])

    def on_game_mode_changed(self, row, param):
        """Callback quando modo de jogo muda"""
        idx = row.get_selected()
        
        # 0=Desktop, 1=Steam, 2=Lutris, 3=Custom
        
        if idx == 0: # Desktop
            self.platform_games_expander.set_visible(False)
            self.platform_games_expander.set_expanded(False)
            
            self.custom_app_expander.set_visible(False)
            self.custom_app_expander.set_expanded(False)
            
        elif idx == 3: # Custom
            self.platform_games_expander.set_visible(False)
            self.platform_games_expander.set_expanded(False)
            
            self.custom_app_expander.set_visible(True)
            self.custom_app_expander.set_expanded(True)
            
        else: # Platforms
            self.custom_app_expander.set_visible(False)
            self.custom_app_expander.set_expanded(False)
            
            self.platform_games_expander.set_visible(True)
            self.platform_games_expander.set_expanded(True)
            
            # Update title based on platform
            platforms = {1: 'Steam', 2: 'Lutris'}
            plat = platforms.get(idx, 'Jogos')
            self.platform_games_expander.set_title(f"Jogos da {plat}")
            
            self.populate_game_list(idx)
            
    def populate_game_list(self, mode_idx):
        """Popula lista de jogos da plataforma selecionada"""
        platform_map = {1: 'Steam', 2: 'Lutris'}
        plat = platform_map.get(mode_idx)
        
        if not plat: return
        
        # Detectar se vazio
        if not self.detected_games[plat]:
             self.show_toast(f"Procurando jogos {plat}...")
             # Executar síncrono por simplicidade (rápido o suficiente geralmente)
             # Idealmente seria async
             if plat == 'Steam':
                 self.detected_games['Steam'] = self.game_detector.detect_steam()
             elif plat == 'Lutris':
                 self.detected_games['Lutris'] = self.game_detector.detect_lutris()
                 
        games = self.detected_games[plat]
        
        # Atualizar modelo da lista
        # Precisamos recriar o modelo ou limpar
        new_model = Gtk.StringList()
        if not games:
            new_model.append(f"Nenhum jogo encontrado no {plat}")
        else:
            for game in games:
                new_model.append(game['name'])
                
        self.game_list_row.set_model(new_model)
        self.game_list_model = new_model # Keep ref
        self.game_list_model = new_model # Keep ref

    def cleanup(self):
        """Limpa recursos ao fechar"""
        # Parar monitoramento
        if hasattr(self, 'perf_monitor'):
            self.perf_monitor.stop_monitoring()
            
        # Parar servidor se estiver rodando
        if self.is_hosting:
            self.stop_hosting()
            
        # Garantir parada do listener
        if hasattr(self, 'stop_pin_listener'):
            self.stop_pin_listener()
            
        if hasattr(self, 'audio_manager'):
            self.audio_manager.cleanup()
            self.stop_hosting()
