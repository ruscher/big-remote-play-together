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

class HostView(Gtk.Box):
    """Interface para hospedar jogos"""
    
    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        
        self.is_hosting = False
        self.pin_code = None
        
        self.setup_ui()
        
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
        self.append(clamp)
        
    def create_status_card(self):
        """Cria card de status do servidor"""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.add_css_class('card')
        box.set_margin_top(12)
        box.set_margin_bottom(12)
        box.set_margin_start(12)
        box.set_margin_end(12)
        
        # Status header
        status_header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        status_header.set_margin_top(12)
        status_header.set_margin_start(12)
        
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
        
        # Connection info (hidden by default)
        self.connection_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.connection_box.set_margin_top(12)
        self.connection_box.set_margin_bottom(12)
        self.connection_box.set_margin_start(12)
        self.connection_box.set_margin_end(12)
        self.connection_box.set_visible(False)
        
        # PIN code
        pin_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        pin_label = Gtk.Label(label='Código PIN:')
        pin_label.add_css_class('dim-label')
        
        self.pin_display = Gtk.Label()
        self.pin_display.add_css_class('title-1')
        self.pin_display.add_css_class('accent')
        
        copy_pin_btn = Gtk.Button(icon_name='edit-copy-symbolic')
        copy_pin_btn.add_css_class('flat')
        copy_pin_btn.set_tooltip_text('Copiar PIN')
        copy_pin_btn.connect('clicked', self.copy_pin)
        
        pin_box.append(pin_label)
        pin_box.append(self.pin_display)
        pin_box.append(copy_pin_btn)
        pin_box.set_halign(Gtk.Align.CENTER)
        
        # IP address
        ip_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        ip_label = Gtk.Label(label='Endereço IP:')
        ip_label.add_css_class('dim-label')
        
        self.ip_display = Gtk.Label()
        self.ip_display.add_css_class('monospace')
        
        copy_ip_btn = Gtk.Button(icon_name='edit-copy-symbolic')
        copy_ip_btn.add_css_class('flat')
        copy_ip_btn.set_tooltip_text('Copiar IP')
        copy_ip_btn.connect('clicked', self.copy_ip)
        
        ip_box.append(ip_label)
        ip_box.append(self.ip_display)
        ip_box.append(copy_ip_btn)
        ip_box.set_halign(Gtk.Align.CENTER)
        
        self.connection_box.append(pin_box)
        self.connection_box.append(ip_box)
        
        box.append(status_header)
        box.append(self.connection_box)
        
        return box
        
    def toggle_hosting(self, button):
        """Inicia ou para o servidor"""
        if self.is_hosting:
            self.stop_hosting()
        else:
            self.start_hosting()
            
    def start_hosting(self):
        """Inicia servidor Sunshine"""
        from host.sunshine_manager import SunshineHost
        
        # Gerar PIN
        self.pin_code = ''.join(random.choices(string.digits, k=6))
        
        # Get IP
        import socket
        hostname = socket.gethostname()
        ip_address = socket.gethostbyname(hostname)
        
        # Inicializar Sunshine se necessário
        if not hasattr(self, 'sunshine'):
            from pathlib import Path
            config_dir = Path.home() / '.config' / 'big-remoteplay' / 'sunshine'
            self.sunshine = SunshineHost(config_dir)
        
        # Configurar Sunshine com as opções da UI
        quality_map = {
            0: {'bitrate': 5000, 'fps': 30},   # Baixa
            1: {'bitrate': 10000, 'fps': 30},  # Média
            2: {'bitrate': 20000, 'fps': 60},  # Alta
            3: {'bitrate': 30000, 'fps': 60},  # Ultra
            4: {'bitrate': 40000, 'fps': 60},  # Máxima
        }
        
        quality_settings = quality_map.get(self.quality_row.get_selected(), {'bitrate': 20000, 'fps': 60})
        
        # Tentar iniciar Sunshine
        try:
            success = self.sunshine.start()
            
            if not success:
                self.show_error_dialog('Erro ao Iniciar Sunshine', 
                    'Não foi possível iniciar o servidor Sunshine.\n'
                    'Verifique se o Sunshine está instalado e as permissões estão corretas.')
                return
            
            # Update UI
            self.is_hosting = True
            self.status_icon.set_from_icon_name('network-server-symbolic')
            self.status_label.set_text('Servidor Ativo')
            self.status_sublabel.set_text(f'Aguardando conexões em {ip_address}')
            
            self.pin_display.set_text(self.pin_code)
            self.ip_display.set_text(ip_address)
            self.connection_box.set_visible(True)
            
            self.start_button.set_label('Parar Servidor')
            self.start_button.remove_css_class('suggested-action')
            self.start_button.add_css_class('destructive-action')
            
            # Mostrar e iniciar monitor de performance
            self.perf_monitor.set_visible(True)
            self.perf_monitor.start_monitoring()
            
            # Mostrar toast de sucesso
            self.show_toast(f'Servidor iniciado em {ip_address}')
            
        except Exception as e:
            self.show_error_dialog('Erro Inesperado', 
                f'Ocorreu um erro ao iniciar o servidor:\n{str(e)}')
        
    def stop_hosting(self):
        """Para o servidor"""
        if hasattr(self, 'sunshine'):
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
        self.status_icon.set_from_icon_name('network-idle-symbolic')
        self.status_label.set_text('Servidor Inativo')
        self.status_sublabel.set_text('Inicie o servidor para aceitar conexões')
        
        self.connection_box.set_visible(False)
        
        self.start_button.set_label('Iniciar Servidor')
        self.start_button.remove_css_class('destructive-action')
        self.start_button.add_css_class('suggested-action')
        
        # Parar e ocultar monitor de performance
        self.perf_monitor.stop_monitoring()
        self.perf_monitor.set_visible(False)
        
        self.show_toast('Servidor parado')
        
    def copy_pin(self, button):
        """Copia PIN para clipboard"""
        clipboard = self.get_clipboard()
        clipboard.set(self.pin_code)
        
    def copy_ip(self, button):
        """Copia IP para clipboard"""
        clipboard = self.get_clipboard()
        clipboard.set(self.ip_display.get_text())
    
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
        webbrowser.open('http://localhost:47989')

    def cleanup(self):
        """Limpa recursos ao fechar"""
        # Parar monitoramento
        if hasattr(self, 'perf_monitor'):
            self.perf_monitor.stop_monitoring()
            
        # Parar servidor se estiver rodando
        if self.is_hosting:
            self.stop_hosting()
