import gi
gi.require_version('Gtk', '4.0'); gi.require_version('Adw', '1')
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
        try:
            if hasattr(self, 'host_view'): self.host_view.cleanup()
            if hasattr(self, 'guest_view'): self.guest_view.cleanup()
        except: pass
        return False
        
    def setup_ui(self):
        self.toast_overlay = Adw.ToastOverlay(); self.set_content(self.toast_overlay)
        self.split_view = Adw.NavigationSplitView(); self.toast_overlay.set_child(self.split_view)
        self.setup_sidebar(); self.setup_content()
        self.split_view.set_min_sidebar_width(220); self.split_view.set_max_sidebar_width(280)
        
    def setup_sidebar(self):
        tb = Adw.ToolbarView(); hb = Adw.HeaderBar()
        btn = Gtk.Button(icon_name='big-remote-play-together'); btn.add_css_class('flat')
        btn.connect('clicked', lambda b: self.get_application().activate_action('about', None))
        hb.pack_start(btn); hb.set_title_widget(Adw.WindowTitle.new('Remote Play', ''))
        tb.add_top_bar(hb); main = Gtk.Box(orientation=Gtk.Orientation.VERTICAL); main.set_vexpand(True)
        scroll = Gtk.ScrolledWindow(); scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC); scroll.set_vexpand(True)
        self.nav_list = Gtk.ListBox(); self.nav_list.add_css_class('navigation-sidebar')
        self.nav_list.connect('row-selected', self.on_nav_selected)
        for pid, info in NAVIGATION_PAGES.items(): self.nav_list.append(self.create_nav_row(pid, info))
        if r := self.nav_list.get_row_at_index(0): self.nav_list.select_row(r)
        scroll.set_child(self.nav_list); main.append(scroll); main.append(self.create_status_footer())
        tb.set_content(main); self.split_view.set_sidebar(Adw.NavigationPage.new(tb, 'Navigation'))
        
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
        
        # Label "Status dos Serviços"
        status_title = Gtk.Label(label='Status dos Serviços')
        status_title.add_css_class('caption')
        status_title.add_css_class('dim-label')
        status_title.set_halign(Gtk.Align.START)
        status_title.set_margin_bottom(4)
        footer.append(status_title)
        
        # Card container
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        card.add_css_class("info-card")
        
        # Sunshine Row
        row_sun = Gtk.Box(spacing=10)
        row_sun.add_css_class("info-row")
        
        box_key_sun = Gtk.Box(spacing=8)
        box_key_sun.set_hexpand(True)
        
        self.sunshine_dot = Gtk.Image.new_from_icon_name('media-record-symbolic')
        self.sunshine_dot.set_pixel_size(10)
        self.sunshine_dot.add_css_class('status-dot')
        self.sunshine_dot.add_css_class('status-offline')
        box_key_sun.append(self.sunshine_dot)
        
        lbl_key_sun = Gtk.Label(label='SUNSHINE')
        lbl_key_sun.add_css_class('info-key')
        box_key_sun.append(lbl_key_sun)
        
        row_sun.append(box_key_sun)
        
        self.lbl_sunshine_status = Gtk.Label(label='Verificando...')
        self.lbl_sunshine_status.add_css_class('info-value')
        self.lbl_sunshine_status.set_halign(Gtk.Align.END)
        row_sun.append(self.lbl_sunshine_status)
        
        card.append(row_sun)
        
        # Moonlight Row
        row_moon = Gtk.Box(spacing=10)
        row_moon.add_css_class("info-row")
        
        box_key_moon = Gtk.Box(spacing=8)
        box_key_moon.set_hexpand(True)
        
        self.moonlight_dot = Gtk.Image.new_from_icon_name('media-record-symbolic')
        self.moonlight_dot.set_pixel_size(10)
        self.moonlight_dot.add_css_class('status-dot')
        self.moonlight_dot.add_css_class('status-offline')
        box_key_moon.append(self.moonlight_dot)
        
        lbl_key_moon = Gtk.Label(label='MOONLIGHT')
        lbl_key_moon.add_css_class('info-key')
        box_key_moon.append(lbl_key_moon)
        
        row_moon.append(box_key_moon)
        
        self.lbl_moonlight_status = Gtk.Label(label='Verificando...')
        self.lbl_moonlight_status.add_css_class('info-value')
        self.lbl_moonlight_status.set_halign(Gtk.Align.END)
        row_moon.append(self.lbl_moonlight_status)
        
        card.append(row_moon)
        
        footer.append(card)
        return footer
        
    def update_server_status(self, has_sun, has_moon):
        for dot, has in [(self.sunshine_dot, has_sun), (self.moonlight_dot, has_moon)]:
            dot.remove_css_class('status-online' if not has else 'status-offline')
            dot.add_css_class('status-online' if has else 'status-offline')

    def update_dependency_ui(self, has_sun, has_moon):
        for lbl, card, has, name in [(self.lbl_sunshine_status, self.host_card, has_sun, 'Sunshine'), (self.lbl_moonlight_status, self.guest_card, has_moon, 'Moonlight')]:
            lbl.set_markup(f'<span color="{"#2ec27e" if has else "#e01b24"}">{"Instalado" if has else "Falta Instalar"}</span>')
            card.set_sensitive(has); card.set_tooltip_text('' if has else f'Necessário instalar {name} para {"hospedar" if name=="Sunshine" else "conectar"}')

        
    def setup_content(self):
        ct = Adw.ToolbarView(); hb = Adw.HeaderBar(); m = Gio.Menu()
        m.append('Preferências', 'app.preferences'); m.append('Sobre', 'app.about')
        hb.pack_end(Gtk.MenuButton(icon_name='open-menu-symbolic', menu_model=m))
        ct.add_top_bar(hb); self.content_stack = Gtk.Stack()
        self.content_stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE); self.content_stack.set_transition_duration(200)
        self.content_stack.add_named(self.create_welcome_page(), 'welcome')
        self.host_view = HostView(); self.content_stack.add_named(self.host_view, 'host')
        self.guest_view = GuestView(); self.content_stack.add_named(self.guest_view, 'guest')
        ct.set_content(self.content_stack); self.split_view.set_content(Adw.NavigationPage.new(ct, 'Big Remote Play Together'))
        
    def create_welcome_page(self):
        scroll = Gtk.ScrolledWindow(); scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC); scroll.set_vexpand(True)
        sp = Adw.StatusPage(icon_name='big-remote-play-together', title='Big Remote Play Together', description='Jogue cooperativamente através da rede local\nCompartilhe seus jogos ou conecte-se a um servidor')
        cb = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=32); cb.set_halign(Gtk.Align.CENTER); cb.set_margin_bottom(24)
        cards = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=24); cards.set_halign(Gtk.Align.CENTER)
        self.host_card = self.create_action_card('Hospedar Servidor', 'Compartilhe seus jogos com outros jogadores na rede', 'network-server-symbolic', 'suggested-action', lambda: self.navigate_to('host'))
        self.guest_card = self.create_action_card('Conectar Servidor', 'Conecte-se a um servidor de jogos na rede', 'network-workgroup-symbolic', '', lambda: self.navigate_to('guest'))
        for c in [self.host_card, self.guest_card]: cards.append(c)
        cb.append(cards); il = Gtk.Label(); il.set_markup('<span size="small">Baseado em <b>Sunshine</b> e <b>Moonlight</b></span>'); il.add_css_class('dim-label')
        cb.append(il); sp.set_child(cb); scroll.set_child(sp); return scroll
        
    def create_action_card(self, title, desc, icon, cls, cb):
        clamp = Adw.Clamp(); clamp.set_maximum_size(320); btn = Gtk.Button(); btn.add_css_class('card')
        if cls: btn.add_css_class(cls)
        btn.set_size_request(300, 180); btn.connect('clicked', lambda b: cb())
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        for m in ['top', 'bottom', 'start', 'end']: getattr(box, f'set_margin_{m}')(24)
        img = Gtk.Image.new_from_icon_name(icon); img.set_pixel_size(48); img.add_css_class('accent'); box.append(img)
        tl = Gtk.Label(label=title, css_classes=['title-3'], wrap=True, justify=Gtk.Justification.CENTER); box.append(tl)
        dl = Gtk.Label(label=desc, css_classes=['caption', 'dim-label'], wrap=True, justify=Gtk.Justification.CENTER, max_width_chars=35); box.append(dl)
        btn.set_child(box); clamp.set_child(btn); return clamp
        
    def on_nav_selected(self, lb, row):
        if not row or not hasattr(self, 'content_stack'): return
        c = self.nav_list.get_first_child()
        while c: (c.remove_css_class('active-category'), setattr(c, 'active', False), c := c.get_next_sibling())
        row.add_css_class('active-category'); self.navigate_to(row.page_id)
    def navigate_to(self, pid):
        self.current_page = pid; self.content_stack.set_visible_child_name(pid)
        r = self.nav_list.get_first_child()
        while r:
            if getattr(r, 'page_id', None) == pid: self.nav_list.select_row(r); break
            r = r.get_next_sibling()
        
    def check_system(self):
        def check():
            h_sun, h_moon = self.system_check.has_sunshine(), self.system_check.has_moonlight()
            r_sun, r_moon = self.system_check.is_sunshine_running(), self.system_check.is_moonlight_running()
            GLib.idle_add(lambda: (self.update_status(h_sun, h_moon), self.update_server_status(r_sun, r_moon), self.update_dependency_ui(h_sun, h_moon)))
        threading.Thread(target=check, daemon=True).start()
        GLib.timeout_add_seconds(3, self.p_check)
    def p_check(self):
        threading.Thread(target=lambda: GLib.idle_add(self.update_server_status, self.system_check.is_sunshine_running(), self.system_check.is_moonlight_running()), daemon=True).start()
        return True

        
    def update_status(self, h_sun, h_moon): (self.show_missing_dialog() if not h_sun and not h_moon else None)
    def show_missing_dialog(self):
        d = Adw.MessageDialog.new(self); d.set_heading('Componentes Faltando'); d.set_body('Sunshine e Moonlight são necessários. Instalar agora?')
        d.add_response('cancel', 'Cancelar'); d.add_response('install', 'Instalar'); d.set_response_appearance('install', Adw.ResponseAppearance.SUGGESTED)
        d.connect('response', lambda dlg, r: (InstallerWindow(parent=self, on_success=self.check_system).present() if r == 'install' else None)); d.present()
    def show_toast(self, m): (self.toast_overlay.add_toast(Adw.Toast.new(m)) if hasattr(self, 'toast_overlay') else print(m))
