#!/usr/bin/env python3
import sys, os, gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, Gio, GLib, Gdk
from pathlib import Path
from ui.main_window import MainWindow
from utils.config import Config
from utils.logger import Logger

class BigRemotePlayApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id='br.com.biglinux.remoteplay', flags=Gio.ApplicationFlags.FLAGS_NONE)
        self.config = Config()
        self.logger = Logger()
        self.window = None
        
    def do_activate(self):
        if not self.window: self.window = MainWindow(application=self)
        self.window.present()
        
    def do_startup(self):
        Adw.Application.do_startup(self)
        self.setup_icon()
        self.setup_actions()
        self.setup_theme()
        
    def setup_actions(self):
        actions = [('quit', lambda *_: self.quit()), ('about', self.show_about), ('preferences', self.show_preferences)]
        for name, callback in actions:
            action = Gio.SimpleAction.new(name, None)
            action.connect('activate', callback)
            self.add_action(action)
            
    def setup_theme(self):
        sm = Adw.StyleManager.get_default(); theme = self.config.get('theme', 'auto')
        sm.set_color_scheme(Adw.ColorScheme.FORCE_DARK if theme == 'dark' else Adw.ColorScheme.FORCE_LIGHT if theme == 'light' else Adw.ColorScheme.DEFAULT)
        self.load_custom_css()
    
    def setup_icon(self):
        ip = Path(__file__).parent.parent / 'data' / 'icons'
        if ip.exists():
            it = Gtk.IconTheme.get_for_display(Gdk.Display.get_default()); it.add_search_path(str(ip)); self.logger.info("Ícone carregado")
            
    def load_custom_css(self):
        cp = Gtk.CssProvider(); cp_path = Path(__file__).parent / 'ui' / 'style.css'
        if cp_path.exists(): cp.load_from_path(str(cp_path)); Gtk.StyleContext.add_provider_for_display(self.window.get_display() if self.window else Gdk.Display.get_default(), cp, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    def show_about(self, *args):
        about = Adw.AboutWindow(
            transient_for=self.window,
            application_name='Big Remote Play Together',
            application_icon='big-remote-play-together',
            developer_name='Rafael Ruscher',
            version='1.0.0',
            developers=['Rafael Ruscher <rruscher@gmail.com>', 'Alexasandro Pacheco Feliciano <@pachecogameroficial>', 'Alessandro e Silva Xavier <@alessandro741>'],
            copyright='© 2026 BigLinux',
            license_type=Gtk.License.GPL_3_0,
            website='https://www.biglinux.com.br',
            issue_url='https://github.com/biglinux/big-remoteplay-together/issues',
            comments='Sistema integrado de jogo cooperativo remoto\nInspirado no Steam Remote Play Together',
        )
        about.add_link("Youtube", "https://www.youtube.com/watch?v=D2l9o_wXW5M")
        about.present()
        
    def show_preferences(self, *args):
        from ui.preferences import PreferencesWindow
        PreferencesWindow(transient_for=self.window).present()
        
    def do_shutdown(self):
        try: Adw.Application.do_shutdown(self)
        except: pass
        os._exit(0)

def main():
    import signal
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    return BigRemotePlayApp().run(sys.argv)

if __name__ == '__main__':
    sys.exit(main())
