"""
Janela de preferências do aplicativo
"""

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, Adw

class PreferencesWindow(Adw.PreferencesWindow):
    """Janela de preferências"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        self.set_title('Preferências')
        self.set_default_size(600, 500)
        self.set_modal(True)
        
        self.setup_ui()
        
    def setup_ui(self):
        """Configura interface"""
        # General page
        general_page = Adw.PreferencesPage()
        general_page.set_title('Geral')
        general_page.set_icon_name('preferences-system-symbolic')
        
        # Appearance group
        appearance_group = Adw.PreferencesGroup()
        appearance_group.set_title('Aparência')
        
        # Theme
        theme_row = Adw.ComboRow()
        theme_row.set_title('Tema')
        theme_row.set_subtitle('Escolha o esquema de cores')
        
        theme_model = Gtk.StringList()
        theme_model.append('Automático')
        theme_model.append('Claro')
        theme_model.append('Escuro')
        
        theme_row.set_model(theme_model)
        theme_row.set_selected(0)
        
        appearance_group.add(theme_row)
        general_page.add(appearance_group)
        
        # Network page
        network_page = Adw.PreferencesPage()
        network_page.set_title('Rede')
        network_page.set_icon_name('network-wired-symbolic')
        
        # Network group
        network_group = Adw.PreferencesGroup()
        network_group.set_title('Configurações de Rede')
        network_group.set_description('Configure como o aplicativo se comporta na rede')
        
        # UPNP
        upnp_row = Adw.SwitchRow()
        upnp_row.set_title('Habilitar UPNP')
        upnp_row.set_subtitle('Configurar portas automaticamente no roteador')
        upnp_row.set_active(True)
        network_group.add(upnp_row)
        
        # IPv6
        ipv6_row = Adw.SwitchRow()
        ipv6_row.set_title('Habilitar IPv6')
        ipv6_row.set_subtitle('Usar IPv6 quando disponível')
        ipv6_row.set_active(True)
        network_group.add(ipv6_row)
        
        # Discovery
        discovery_row = Adw.SwitchRow()
        discovery_row.set_title('Descoberta Automática')
        discovery_row.set_subtitle('Permitir que outros usuários descubram este dispositivo')
        discovery_row.set_active(True)
        network_group.add(discovery_row)
        
        # Port configuration
        port_group = Adw.PreferencesGroup()
        port_group.set_title('Portas')
        port_group.set_description('Configuração avançada de portas')
        
        sunshine_port_row = Adw.EntryRow()
        sunshine_port_row.set_title('Porta do Sunshine')
        sunshine_port_row.set_text('47989')
        port_group.add(sunshine_port_row)
        
        streaming_port_row = Adw.EntryRow()
        streaming_port_row.set_title('Porta de Streaming')
        streaming_port_row.set_text('48010')
        port_group.add(streaming_port_row)
        
        network_page.add(network_group)
        network_page.add(port_group)
        
        # Advanced page
        advanced_page = Adw.PreferencesPage()
        advanced_page.set_title('Avançado')
        advanced_page.set_icon_name('preferences-other-symbolic')
        
        # Paths group
        paths_group = Adw.PreferencesGroup()
        paths_group.set_title('Caminhos')
        
        config_row = Adw.ActionRow()
        config_row.set_title('Diretório de Configuração')
        config_row.set_subtitle('~/.config/big-remoteplay')
        
        open_config_btn = Gtk.Button(icon_name='folder-open-symbolic')
        open_config_btn.add_css_class('flat')
        open_config_btn.set_valign(Gtk.Align.CENTER)
        config_row.add_suffix(open_config_btn)
        
        paths_group.add(config_row)
        
        # Logs group
        logs_group = Adw.PreferencesGroup()
        logs_group.set_title('Logs e Depuração')
        
        verbose_row = Adw.SwitchRow()
        verbose_row.set_title('Logs Detalhados')
        verbose_row.set_subtitle('Ativar logging verbose para depuração')
        verbose_row.set_active(False)
        logs_group.add(verbose_row)
        
        clear_logs_row = Adw.ActionRow()
        clear_logs_row.set_title('Limpar Logs')
        clear_logs_row.set_subtitle('Remover arquivos de log antigos')
        
        clear_btn = Gtk.Button(label='Limpar')
        clear_btn.add_css_class('destructive-action')
        clear_btn.set_valign(Gtk.Align.CENTER)
        clear_logs_row.add_suffix(clear_btn)
        
        logs_group.add(clear_logs_row)
        
        advanced_page.add(paths_group)
        advanced_page.add(logs_group)
        
        # Add pages
        self.add(general_page)
        self.add(network_page)
        self.add(advanced_page)
