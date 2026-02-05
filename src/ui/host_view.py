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
        self.sync_ui_state()
        
    def detect_monitors(self):
        """Detecta monitores disponíveis"""
        from pathlib import Path
        import subprocess
        monitors = [('Automático', 'auto')]
        
        # Adicionar índices numéricos como fallback comum para Wayland/KMS
        for i in range(4):
            monitors.append((f"Monitor: Índice {i}", str(i)))

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
        
        # Header
        header = Adw.PreferencesGroup()
        header.set_title('Hospedar Jogo')
        header.set_description('Configure e compartilhe seu jogo com amigos')
        
        # Server status card
        self.status_card = self.create_status_card()
        header.add(self.status_card)
        
        # Performance monitor
        from .performance_monitor import PerformanceMonitor
        self.perf_monitor = PerformanceMonitor()
        self.perf_monitor.set_visible(False)  # Oculto até servidor iniciar
        header.add(self.perf_monitor)
        
        # Game selection
        game_group = Adw.PreferencesGroup()
        game_group.set_title('Configuração do Jogo')
        game_group.set_margin_top(12)
        
        # Game selector
        self.game_row = Adw.ComboRow()
        self.game_row.set_title('Jogo')
        self.game_row.set_subtitle('Selecione o jogo para compartilhar')
        
        games_model = Gtk.StringList()
        games_model.append('Desktop Completo')
        games_model.append('Steam (detectar jogos)')
        games_model.append('Lutris (detectar jogos)')
        games_model.append('Aplicativo Personalizado...')
        
        self.game_row.set_model(games_model)
        self.game_row.set_selected(0)
        
        game_group.add(self.game_row)
        
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
        
        game_group.add(self.quality_row)
        
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
        
        game_group.add(self.players_row)
        
        # Monitor selection
        self.monitor_row = Adw.ComboRow()
        self.monitor_row.set_title('Monitor / Tela')
        self.monitor_row.set_subtitle('Selecione em qual tela o jogo será capturado')
        
        monitor_model = Gtk.StringList()
        for label, _ in self.available_monitors:
            monitor_model.append(label)
        
        self.monitor_row.set_model(monitor_model)
        self.monitor_row.set_selected(0)
        game_group.add(self.monitor_row)
        
        # GPU / Encoder selection
        self.gpu_row = Adw.ComboRow()
        self.gpu_row.set_title('Placa de Vídeo / Encoder')
        self.gpu_row.set_subtitle('Escolha o hardware para codificação do vídeo')
        
        gpu_model = Gtk.StringList()
        for gpu_info in self.available_gpus:
            gpu_model.append(gpu_info['label'])
            
        self.gpu_row.set_model(gpu_model)
        self.gpu_row.set_selected(0)
        game_group.add(self.gpu_row)
        
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
            
        game_group.add(self.platform_row)
        
        # Advanced settings expander
        advanced_group = Adw.PreferencesGroup()
        advanced_group.set_title('Configurações Avançadas')
        advanced_group.set_margin_top(12)
        
        # Audio streaming
        audio_row = Adw.SwitchRow()
        audio_row.set_title('Streaming de Áudio')
        audio_row.set_subtitle('Transmitir áudio para guests')
        audio_row.set_active(True)
        advanced_group.add(audio_row)
        
        # Input sharing
        input_row = Adw.SwitchRow()
        input_row.set_title('Compartilhar Controles')
        input_row.set_subtitle('Permitir que guests controlem o jogo')
        input_row.set_active(True)
        advanced_group.add(input_row)
        
        # UPNP
        upnp_row = Adw.SwitchRow()
        upnp_row.set_title('UPNP Automático')
        upnp_row.set_subtitle('Configurar portas automaticamente no roteador')
        upnp_row.set_active(True)
        advanced_group.add(upnp_row)
        
        # Action buttons
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        button_box.set_halign(Gtk.Align.CENTER)
        button_box.set_margin_top(24)
        
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
        
        # Add all to content
        content.append(header)
        content.append(game_group)
        content.append(advanced_group)
        content.append(button_box)
        
        clamp.set_child(content)
        
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_vexpand(True)
        scroll.set_child(clamp)
        
        self.append(scroll)
        
    def create_status_card(self):
        """Cria card de status do servidor"""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.add_css_class('card')
        box.set_margin_top(12)
        box.set_margin_bottom(12)
        box.set_margin_start(12)
        box.set_margin_end(12)
        
        # Status header (Icon + Status Text)
        status_header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        status_header.set_margin_top(12)
        status_header.set_margin_start(12)
        status_header.set_margin_bottom(12)
        
        self.status_icon = Gtk.Image.new_from_icon_name('network-idle-symbolic')
        self.status_icon.set_pixel_size(32)
        
        status_text_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.status_label = Gtk.Label(label='Servidor Inativo')
        self.status_label.set_halign(Gtk.Align.START)
        self.status_label.add_css_class('title-3')
        
        self.status_sublabel = Gtk.Label(label='Inicie o servidor para aceitar conexões')
        self.status_sublabel.set_halign(Gtk.Align.START)
        self.status_sublabel.add_css_class('dim-label')
        
        status_text_box.append(self.status_label)
        status_text_box.append(self.status_sublabel)
        
        status_header.append(self.status_icon)
        status_header.append(status_text_box)
        
        box.append(status_header)
        
        # === Summary Box (Active Mode) ===
        self.summary_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.summary_box.set_margin_bottom(16)
        self.summary_box.set_margin_start(12)
        self.summary_box.set_margin_end(12)
        self.summary_box.set_visible(False)
        
        # Sunshine Status
        sunshine_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        sunshine_lbl = Gtk.Label(label='Sunshine:')
        sunshine_lbl.add_css_class('dim-label')
        sunshine_lbl.set_halign(Gtk.Align.START)
        
        self.sunshine_val = Gtk.Label(label='On-line')
        self.sunshine_val.add_css_class('success')
        self.sunshine_val.set_halign(Gtk.Align.START)
        
        sunshine_row.append(sunshine_lbl)
        sunshine_row.append(self.sunshine_val)
        self.summary_box.append(sunshine_row)
        
        # Field widgets storage
        self.field_widgets = {}
        
        # Fields to display
        self.create_masked_row('Nome do Host', 'hostname')
        self.create_masked_row('IPv4', 'ipv4')
        self.create_masked_row('IPv6', 'ipv6')
        self.create_masked_row('IPv4 Global', 'ipv4_global')
        self.create_masked_row('IPv6 Global', 'ipv6_global')
        
        # PIN needs to be visible mostly
        self.create_masked_row('PIN', 'pin')
        
        box.append(self.summary_box)
        
        # Start periodic check
        GLib.timeout_add_seconds(5, self.update_status_info)
        # self.update_status_info() # Initial check - Removed to avoid early calls

        return box
        
    def create_masked_row(self, title, key):
        """Cria linha com campo mascarado (olho) e copy"""
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        
        # Title
        label = Gtk.Label(label=f"{title}:")
        label.add_css_class('dim-label')
        label.set_halign(Gtk.Align.START)
        label.set_width_chars(15) 
        label.set_xalign(0)
        
        # Value
        value_lbl = Gtk.Label(label='••••••')
        value_lbl.set_halign(Gtk.Align.START)
        value_lbl.set_hexpand(True)
        value_lbl.set_xalign(0)
        value_lbl.set_selectable(True)
        
        # Eye button
        eye_btn = Gtk.Button(icon_name='find-location-symbolic') # Eye icon equivalent
        eye_btn.set_icon_name('view-reveal-symbolic') # Better eye icon
        eye_btn.add_css_class('flat')
        eye_btn.set_tooltip_text('Mostrar/Ocultar')
        
        # Copy button
        copy_btn = Gtk.Button(icon_name='edit-copy-symbolic')
        copy_btn.add_css_class('flat')
        copy_btn.set_tooltip_text('Copiar')
        
        row.append(label)
        row.append(value_lbl)
        row.append(eye_btn)
        row.append(copy_btn)
        
        self.summary_box.append(row)
        
        # Store widgets and state
        self.field_widgets[key] = {
            'label': value_lbl,
            'real_value': '',
            'revealed': False, 
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
            self.status_icon.set_from_icon_name('network-server-symbolic')
            self.status_label.set_text('Servidor Ativo')
            self.status_sublabel.set_text('Servidor rodando e pronto para conexões')
            
            self.summary_box.set_visible(True)
            
            self.start_button.set_label('Parar Servidor')
            self.start_button.remove_css_class('suggested-action')
            self.start_button.add_css_class('destructive-action')
            
            self.perf_monitor.set_visible(True)
            self.perf_monitor.start_monitoring()
            
            # Populate fields
            self.populate_summary_fields()
            
        else:
            self.status_icon.set_from_icon_name('network-idle-symbolic')
            self.status_label.set_text('Servidor Inativo')
            self.status_sublabel.set_text('Inicie o servidor para aceitar conexões')
            
            self.summary_box.set_visible(False)
            
            self.start_button.set_label('Iniciar Servidor')
            self.start_button.remove_css_class('destructive-action')
            self.start_button.add_css_class('suggested-action')
            
            self.perf_monitor.stop_monitoring()
            self.perf_monitor.set_visible(False)

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

    def start_hosting(self):
        """Inicia servidor Sunshine"""
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

        # Adicionar monitor se não for auto
        if selected_monitor != 'auto':
            sunshine_config['output_name'] = selected_monitor

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
        try:
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
            # self.pin_display and self.ip_display removed
            
            self.sync_ui_state()
            
            # Mostrar toast de sucesso
            self.show_toast(f'Servidor iniciado em {ip_address}')
            
        except Exception as e:
            self.show_error_dialog('Erro Inesperado', 
                f'Ocorreu um erro ao iniciar o servidor:\n{str(e)}')
        
    def stop_hosting(self):
        """Para o servidor"""
        # Stop PIN Listener
        if hasattr(self, 'stop_pin_listener'):
            self.stop_pin_listener()
            del self.stop_pin_listener

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
        import webbrowser
        # Sunshine uses HTTPS on port 47990 by default for Web UI
        webbrowser.open('https://localhost:47990')

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
            self.stop_hosting()
