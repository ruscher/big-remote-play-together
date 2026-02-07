import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, Adw, GLib
import subprocess, random, string, json, socket, os
from pathlib import Path
from utils.game_detector import GameDetector

from utils.config import Config
class HostView(Gtk.Box):
    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.config = Config()
        self.is_hosting = False
        self.pin_code = None
        
        from host.sunshine_manager import SunshineHost
        self.sunshine = SunshineHost(Path.home() / '.config' / 'big-remoteplay' / 'sunshine')
        
        if self.sunshine.is_running():
            self.is_hosting = True
            
        self.available_monitors = self.detect_monitors()
        self.available_gpus = self.detect_gpus()
        self.setup_ui()
        
        self.game_detector = GameDetector()
        self.detected_games = {'Steam': [], 'Lutris': []}
        self.load_settings()
        self.connect_settings_signals()
        self.sync_ui_state()
        
    def detect_monitors(self):
        monitors = [('Automático', 'auto')]
        try:
            out = subprocess.check_output(['xrandr', '--current'], text=True, stderr=subprocess.STDOUT)
            for l in out.split('\n'):
                if ' connected' in l:
                    p = l.split()
                    if p:
                        name = p[0]; res = ""
                        for x in p:
                            if 'x' in x and '+' in x: res = f" ({x.split('+')[0]})"; break
                        monitors.append((f"Monitor: {name}{res}", name))
        except:
            try:
                out = subprocess.check_output(['xrandr', '--listactivemonitors'], text=True)
                for l in out.strip().split('\n')[1:]:
                    p = l.split()
                    if p: monitors.append((f"Monitor: {p[-1]}", p[-1]))
            except: pass
        try:
            from pathlib import Path
            for p in Path('/sys/class/drm').glob('card*-*'):
                if (p/'status').exists() and (p/'status').read_text().strip() == 'connected':
                    n = p.name.split('-', 1)[1]
                    if not any(n in m[1] for m in monitors): monitors.append((f"Monitor: {n}", n))
        except: pass
        return monitors

    def detect_gpus(self):
        gpus = []
        try:
            lspci = subprocess.check_output(['lspci'], text=True).lower()
            if 'nvidia' in lspci:
                try:
                    subprocess.check_call(['nvidia-smi'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    gpus.append({'label': 'NVENC (NVIDIA)', 'encoder': 'nvenc', 'adapter': 'auto'})
                except: pass
            if 'intel' in lspci: gpus.append({'label': 'VAAPI (Intel Quicksync)', 'encoder': 'vaapi', 'adapter': '/dev/dri/renderD128'})
        except: pass
        try:
            from pathlib import Path
            if Path('/dev/dri').exists():
                for node in sorted(list(Path('/dev/dri').glob('renderD*'))):
                    if not any(str(node) == g['adapter'] for g in gpus):
                        gpus.append({'label': f"VAAPI (Adapter {node.name})", 'encoder': 'vaapi', 'adapter': str(node)})
        except: pass
        gpus.extend([{'label':'Vulkan (Exp)', 'encoder':'vulkan', 'adapter':'auto'}, {'label':'Software', 'encoder':'software', 'adapter':'auto'}])
        return gpus
        
    def setup_ui(self):
        clamp = Adw.Clamp()
        clamp.set_maximum_size(800)
        for margin in ['top', 'bottom', 'start', 'end']:
            getattr(clamp, f'set_margin_{margin}')(24)
        
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=24)
        
        self.loading_bar = Gtk.ProgressBar()
        self.loading_bar.add_css_class('osd')
        self.loading_bar.set_visible(False)
        content.append(self.loading_bar)
        
        from .performance_monitor import PerformanceMonitor
        self.perf_monitor = PerformanceMonitor()
        self.perf_monitor.set_visible(True)
        self.perf_monitor.set_connection_status("Localhost", "Sunshine Offline", False)
        
        self.header = Adw.PreferencesGroup()
        self.header.set_title('Hospedar Servidor')
        self.header.set_description('Configure e compartilhe seu jogo para seus amigos conectarem')
        
        game_group = Adw.PreferencesGroup()
        game_group.set_title('Configuração do Jogo')
        game_group.set_margin_top(12)
        
        reset_btn = Gtk.Button(icon_name="edit-undo-symbolic")
        reset_btn.add_css_class("flat")
        reset_btn.set_tooltip_text("Restaurar Padrão")
        reset_btn.connect("clicked", self.on_reset_clicked)
        game_group.set_header_suffix(reset_btn)
        
        self.game_mode_row = Adw.ComboRow(); self.game_mode_row.set_title('Modo de Jogo'); self.game_mode_row.set_subtitle('Selecione a fonte do jogo')
        modes = Gtk.StringList()
        for m in ['Desktop Completo', 'Steam', 'Lutris', 'App Personalizado']: modes.append(m)
        self.game_mode_row.set_model(modes); self.game_mode_row.set_selected(0); self.game_mode_row.connect('notify::selected', self.on_game_mode_changed); game_group.add(self.game_mode_row)
        
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
        
        self.streaming_expander = Adw.ExpanderRow()
        self.streaming_expander.set_title('Configurações de Streaming')
        self.streaming_expander.set_subtitle('Qualidade e Jogadores')
        self.streaming_expander.set_icon_name('preferences-desktop-display-symbolic')
        
        self.quality_row = Adw.ComboRow()
        self.quality_row.set_title('Qualidade de Streaming')
        self.quality_row.set_subtitle('Maior qualidade = maior uso de banda')
        
        quality_model = Gtk.StringList()
        for q in ['Baixa (720p 30fps)', 'Média (1080p 30fps)', 'Alta (1080p 60fps)', 'Ultra (1440p 60fps)', 'Máxima (4K 60fps)']:
            quality_model.append(q)
        self.quality_row.set_model(quality_model)
        self.quality_row.set_selected(2)
        self.streaming_expander.add_row(self.quality_row)
        
        self.players_row = Adw.SpinRow()
        self.players_row.set_title('Máximo de Jogadores')
        self.players_row.set_subtitle('Número máximo de conexões simultâneas')
        self.players_row.set_adjustment(Gtk.Adjustment(value=2, lower=1, upper=8, step_increment=1, page_increment=1))
        self.players_row.set_digits(0)
        self.streaming_expander.add_row(self.players_row)
        game_group.add(self.streaming_expander)
        
        self.hardware_expander = Adw.ExpanderRow()
        self.hardware_expander.set_title('Hardware e Captura')
        self.hardware_expander.set_subtitle('Monitor, GPU e Método de Captura')
        self.hardware_expander.set_icon_name('video-display-symbolic')

        self.monitor_row = Adw.ComboRow()
        self.monitor_row.set_title('Monitor / Tela')
        self.monitor_row.set_subtitle('Selecione em qual tela o jogo será capturado')
        monitor_model = Gtk.StringList()
        for label, _ in self.available_monitors: monitor_model.append(label)
        self.monitor_row.set_model(monitor_model)
        self.monitor_row.set_selected(0)
        self.hardware_expander.add_row(self.monitor_row)
        
        self.gpu_row = Adw.ComboRow()
        self.gpu_row.set_title('Placa de Vídeo / Encoder')
        self.gpu_row.set_subtitle('Escolha o hardware para codificação do vídeo')
        gpu_model = Gtk.StringList()
        for gpu_info in self.available_gpus: gpu_model.append(gpu_info['label'])
        self.gpu_row.set_model(gpu_model)
        self.gpu_row.set_selected(0)
        self.hardware_expander.add_row(self.gpu_row)
        
        self.platform_row = Adw.ComboRow()
        self.platform_row.set_title('Método de Captura')
        self.platform_row.set_subtitle('Wayland (recomendado), X11 (legado) ou KMS (direto)')
        platform_model = Gtk.StringList()
        for p in ['Automático', 'Wayland', 'X11', 'KMS (Direto)']: platform_model.append(p)
        self.platform_row.set_model(platform_model)
        import os
        session_type = os.environ.get('XDG_SESSION_TYPE', '').lower()
        self.platform_row.set_selected(1 if session_type == 'wayland' else 2 if session_type == 'x11' else 0)
        self.hardware_expander.add_row(self.platform_row)
        game_group.add(self.hardware_expander)
        
        # --- Audio Group ---
        audio_group = Adw.PreferencesGroup()
        audio_group.set_title('Áudio')
        audio_group.set_description('Configurações de som e microfonia')
        audio_group.set_margin_top(12)
        
        self.audio_row = Adw.SwitchRow()
        self.audio_row.set_title('Streaming de Áudio')
        self.audio_row.set_subtitle('Transmitir áudio para guests')
        self.audio_row.set_active(True)
        audio_group.add(self.audio_row)

        self.dual_audio_row = Adw.SwitchRow()
        self.dual_audio_row.set_title('Áudio Híbrido (Host + Guest)')
        self.dual_audio_row.set_subtitle('Cria saída virtual para permitir áudio simultâneo.\n⚠️ CUIDADO: Pode causar microfonia severa!')
        self.dual_audio_row.set_active(False)
        self.dual_audio_row.connect('notify::active', self.on_dual_audio_toggled)
        audio_group.add(self.dual_audio_row)
        
        self.audio_output_row = Adw.ComboRow()
        self.audio_output_row.set_title('Saída de Áudio Local')
        self.audio_output_row.set_subtitle('Onde você ouvirá o som')
        self.audio_output_row.set_visible(False)
        self.dual_audio_row.connect('notify::active', lambda row, param: self.audio_output_row.set_visible(row.get_active()))
        audio_group.add(self.audio_output_row)
        
        self.audio_mixer_expander = Adw.ExpanderRow()
        self.audio_mixer_expander.set_title("Mixer de Áudio (Fontes)")
        self.audio_mixer_expander.set_subtitle("Escolha quais aplicativos o Client pode ouvir")
        self.audio_mixer_expander.set_icon_name('audio-volume-high-symbolic')
        self.audio_mixer_expander.set_visible(False)
        # Ensure mixer enables if dual audio is active
        self.dual_audio_row.connect('notify::active', lambda r, p: self.audio_mixer_expander.set_visible(r.get_active()))
        self.dual_audio_row.connect('notify::active', lambda r, p: self.start_audio_mixer_refresh() if r.get_active() else self.stop_audio_mixer_refresh())
        
        audio_group.add(self.audio_mixer_expander)
        
        self.load_audio_outputs()
        
        self.advanced_expander = Adw.ExpanderRow()
        self.advanced_expander.set_title('Configurações Avançadas')
        self.advanced_expander.set_subtitle('Input, Rede e Acesso')
        self.advanced_expander.set_icon_name('preferences-system-symbolic')
        
        self.input_row = Adw.SwitchRow()
        self.input_row.set_title('Compartilhar Controles')
        self.input_row.set_subtitle('Permitir que guests controlem o jogo')
        self.input_row.set_active(True)
        self.advanced_expander.add_row(self.input_row)
        
        self.upnp_row = Adw.SwitchRow()
        self.upnp_row.set_title('UPNP Automático')
        self.upnp_row.set_subtitle('Configurar portas automaticamente no roteador')
        self.upnp_row.set_active(True)
        self.advanced_expander.add_row(self.upnp_row)

        self.ipv6_row = Adw.SwitchRow()
        self.ipv6_row.set_title('Address Family (IPv4 + IPv6)')
        self.ipv6_row.set_subtitle('Ativa suporte simultâneo para IPv4 e IPv6 no servidor')
        self.ipv6_row.set_active(True)
        self.advanced_expander.add_row(self.ipv6_row)
        
        self.webui_anyone_row = Adw.SwitchRow()
        self.webui_anyone_row.set_title('Origin Web UI Allowed (WAN)')
        self.webui_anyone_row.set_subtitle('Permite que qualquer pessoa acesse a interface web (Anyone may access Web UI)')
        self.webui_anyone_row.set_active(False)
        self.advanced_expander.add_row(self.webui_anyone_row)
        
        game_group.add(self.advanced_expander)
        
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
        
        self.pin_button = Gtk.Button(label='Inserir PIN')
        self.pin_button.add_css_class('pill')
        self.pin_button.set_size_request(180, -1)
        self.pin_button.set_visible(False)
        self.pin_button.connect('clicked', self.open_pin_dialog)
        button_box.append(self.pin_button)
        
        self.create_summary_box()
        
        content.append(self.header)
        content.append(self.perf_monitor)
        content.append(button_box)
        content.append(self.summary_box)
        content.append(game_group)
        content.append(audio_group)
        
        clamp.set_child(content)
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_vexpand(True)
        scroll.set_child(clamp)
        self.append(scroll)
        
        self.start_audio_watchdog()

    def start_audio_watchdog(self):
        self.audio_hijack_counter = 0
        GLib.timeout_add(1000, self._check_audio_state)
        
    def _check_audio_state(self):
        # Apenas monitora se estiver hospedando e com gerenciador de áudio ativo
        if not self.is_hosting or not hasattr(self, 'audio_manager') or not self.audio_manager.original_sink:
            self.audio_hijack_counter = 0
            return True 
            
        current = self.audio_manager.get_default_sink()
        # Se detectar que o Sunshine roubou o foco para o sink virtual dele
        if current and 'sink-sunshine-stereo' in current:
            self.audio_hijack_counter += 1
            if self.audio_hijack_counter >= 5:
                # Se persistir por 5 segundos, força a volta para o original
                self.audio_manager.set_default_sink(self.audio_manager.original_sink)
                self.show_toast(f"Áudio restaurado: {self.audio_manager.original_sink}")
                self.audio_hijack_counter = 0 
        else:
            self.audio_hijack_counter = 0
            
        return True

    def open_pin_dialog(self, _):
        dialog = Adw.MessageDialog(heading="Inserir PIN", body="Digite o PIN exibido no dispositivo cliente (Moonlight).")
        dialog.set_transient_for(self.get_root())
        
        # Grupo de preferências para conter os campos
        grp = Adw.PreferencesGroup()
        
        pin_row = Adw.EntryRow(title="PIN")
        # pin_row.set_input_purpose(Gtk.InputPurpose.NUMBER) # Gtk 4.10+
        
        name_row = Adw.EntryRow(title="Nome do Dispositivo (Opcional)")
        
        grp.add(pin_row)
        grp.add(name_row)
        
        dialog.set_extra_child(grp)
        
        dialog.add_response("cancel", "Cancelar")
        dialog.add_response("ok", "Enviar")
        dialog.set_response_appearance("ok", Adw.ResponseAppearance.SUGGESTED)
        
        def on_response(d, r):
            if r == "ok":
                pin = pin_row.get_text().strip()
                if not pin: return
                
                success, msg = self.sunshine.send_pin(pin)
                if success:
                    self.show_toast("PIN enviado com sucesso")
                elif "Falha de Autenticação" in msg:
                    # Se falhar autenticação, pedir credenciais
                    self.open_sunshine_auth_dialog(pin)
                elif "307" in msg:
                    # Se retornar Redirect 307, significa que não tem usuário criado
                    self.prompt_create_user(pin)
                else:
                    self.show_error_dialog("Erro no PIN", msg)
                
        dialog.connect("response", on_response)
        dialog.present()
        
    def prompt_create_user(self, pin_retry):
        dialog = Adw.MessageDialog(heading="Usuário Não Encontrado", body="Nenhum usuário foi criado no Sunshine. É necessário configurar um usuário pelo navegador.")
        dialog.set_transient_for(self.get_root())
        dialog.add_response("cancel", "Cancelar")
        dialog.add_response("open", "Abrir Configuração")
        dialog.set_response_appearance("open", Adw.ResponseAppearance.SUGGESTED)
        
        def on_resp(d, r):
            if r == "open":
                import webbrowser
                webbrowser.open("https://localhost:47990")
        
        dialog.connect("response", on_resp)
        dialog.present()
        
    def open_create_user_dialog(self, pin_retry):
        dialog = Adw.MessageDialog(heading="Criar Usuário Sunshine", body="Defina um nome de usuário e senha para o Sunshine.")
        dialog.set_transient_for(self.get_root())
        
        grp = Adw.PreferencesGroup()
        user_row = Adw.EntryRow(title="Novo Usuário")
        user_row.set_text("admin")
        pass_row = Adw.PasswordEntryRow(title="Nova Senha")
        
        grp.add(user_row); grp.add(pass_row)
        dialog.set_extra_child(grp)
        
        dialog.add_response("cancel", "Cancelar")
        dialog.add_response("save", "Salvar e Continuar")
        dialog.set_response_appearance("save", Adw.ResponseAppearance.SUGGESTED)
        
        def on_create(d, r):
            if r == "save":
                user = user_row.get_text().strip()
                pwd = pass_row.get_text().strip()
                if not user or not pwd: return
                
                # Criar usuário
                success, msg = self.sunshine.create_user(user, pwd)
                if success:
                    self.show_toast("Usuário criado!")
                    # Tentar enviar PIN novamente com o novo usuario
                    ok, p_msg = self.sunshine.send_pin(pin_retry, auth=(user, pwd))
                    if ok: self.show_toast("PIN enviado com sucesso")
                    else: self.show_error_dialog("Erro ao enviar PIN pós-criação", p_msg)
                else:
                    self.show_error_dialog("Erro ao criar usuário", msg)
                    
        dialog.connect("response", on_create)
        dialog.present()
        
    def open_sunshine_auth_dialog(self, pin_to_retry: str):
        dialog = Adw.MessageDialog(heading="Autenticação Sunshine", body="O Sunshine requer login. Digite suas credenciais (padrão: admin / senha criada na instalação).")
        dialog.set_transient_for(self.get_root())
        
        grp = Adw.PreferencesGroup()
        user_row = Adw.EntryRow(title="Usuário")
        user_row.set_text("admin")
        pass_row = Adw.PasswordEntryRow(title="Senha")
        
        grp.add(user_row); grp.add(pass_row)
        dialog.set_extra_child(grp)
        
        dialog.add_response("cancel", "Cancelar")
        dialog.add_response("login", "Confirmar")
        dialog.set_response_appearance("login", Adw.ResponseAppearance.SUGGESTED)
        
        def on_auth_resp(d, r):
            if r == "login":
                user = user_row.get_text().strip()
                pwd = pass_row.get_text().strip()
                if not user or not pwd: return
                
                # Tentar novamente com credenciais
                success, msg = self.sunshine.send_pin(pin_to_retry, auth=(user, pwd))
                if success: self.show_toast("PIN enviado com sucesso")
                else: self.show_error_dialog("Falha com credenciais", msg)
                
        dialog.connect("response", on_auth_resp)
        dialog.present()

    def create_summary_box(self):
        self.summary_box = Adw.PreferencesGroup(); self.summary_box.set_title("Informações do Servidor")
        self.summary_box.set_margin_top(12); self.summary_box.set_visible(False); self.field_widgets = {}
        for l, k, i, r in [('Host', 'hostname', 'computer-symbolic', True), ('IPv4', 'ipv4', 'network-wired-symbolic', False), ('IPv6', 'ipv6', 'network-wired-symbolic', False), ('IPv4 Global', 'ipv4_global', 'network-transmit-receive-symbolic', False), ('IPv6 Global', 'ipv6_global', 'network-transmit-receive-symbolic', False), ('PIN', 'pin', 'dialog-password-symbolic', False)]: self.create_masked_row(l, k, i, r)

    def on_dual_audio_toggled(self, row, param):
        if getattr(self, 'loading_settings', False):
            return

        if row.get_active():
            dialog = Adw.MessageDialog(heading="Risco de Microfonia", body="Ativar o Áudio Híbrido reproduzirá o som do jogo no Host E no Guest simultaneamente.\n\n⚠️ Se o dispositivo cliente estiver no mesmo ambiente físico, isso causará eco e microfonia insuportável.\n\nDeseja continuar?")
            dialog.set_transient_for(self.get_root())
            dialog.add_response("cancel", "Cancelar")
            dialog.add_response("ok", "Continuar")
            dialog.set_response_appearance("ok", Adw.ResponseAppearance.DESTRUCTIVE)
            
            def on_resp(d, r):
                if r != "ok":
                    row.set_active(False)
                else:
                    self.audio_output_row.set_visible(True)
                    self.save_host_settings()
            
            dialog.connect("response", on_resp)
            dialog.present()
        else:
            self.audio_output_row.set_visible(False)
            self.save_host_settings()

    def load_audio_outputs(self):
        try:
            from utils.audio import AudioManager
            self.audio_manager = AudioManager()
            devices = self.audio_manager.get_output_devices()
            self.audio_output_model = Gtk.StringList()
            self.audio_devices = devices
            
            if not devices:
                self.audio_output_model.append("Nenhum dispositivo encontrado")
            else:
                for dev in devices:
                    self.audio_output_model.append(dev.get('description', dev.get('name', 'Unknown')))
            self.audio_output_row.set_model(self.audio_output_model)
            self.audio_output_row.set_selected(0)
        except:
            self.audio_manager = None
            self.audio_devices = []
            self.audio_output_model = Gtk.StringList()
            self.audio_output_model.append("Erro ao carregar áudio")
            self.audio_output_row.set_model(self.audio_output_model)

    def create_masked_row(self, title, key, icon_name='text-x-generic-symbolic', default_revealed=False):
        row = Adw.ActionRow()
        row.set_title(title)
        row.set_icon_name(icon_name)
        
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        box.set_valign(Gtk.Align.CENTER)
        
        value_lbl = Gtk.Label(label='••••••' if not default_revealed else '')
        value_lbl.set_margin_end(8)
        
        eye_btn = Gtk.Button(icon_name='view-reveal-symbolic' if not default_revealed else 'view-conceal-symbolic')
        eye_btn.add_css_class('flat')
        copy_btn = Gtk.Button(icon_name='edit-copy-symbolic')
        copy_btn.add_css_class('flat')
        
        box.append(value_lbl); box.append(eye_btn); box.append(copy_btn)
        row.add_suffix(box)
        self.summary_box.add(row)
        
        self.field_widgets[key] = {'label': value_lbl, 'real_value': '', 'revealed': default_revealed, 'btn_eye': eye_btn}
        eye_btn.connect('clicked', lambda b: self.toggle_field_visibility(key))
        copy_btn.connect('clicked', lambda b: self.copy_field_value(key))
        
    def toggle_field_visibility(self, key):
        field = self.field_widgets[key]
        field['revealed'] = not field['revealed']
        field['btn_eye'].set_icon_name('view-conceal-symbolic' if field['revealed'] else 'view-reveal-symbolic')
        field['label'].set_text(field['real_value'] if field['revealed'] else '••••••')
            
    def copy_field_value(self, key):
        if val := self.field_widgets[key]['real_value']:
             self.get_root().get_clipboard().set(val); self.show_toast(f"Copiado!")

    def toggle_hosting(self, button):
        if self.is_hosting: self.stop_hosting()
        else: self.start_hosting()
            
    def sync_ui_state(self):
        if self.is_hosting:
            self.header.set_description('Servidor Ativo - Os guests já podem se conectar')
            self.perf_monitor.set_connection_status("Sunshine", "Ativo - Aguardando Conexões", True)
            self.perf_monitor.start_monitoring()
            self.start_button.set_label('Parar Servidor')
            self.start_button.remove_css_class('suggested-action')
            self.start_button.add_css_class('destructive-action')
            self.header.set_visible(True)
            self.configure_button.set_sensitive(True)
            self.configure_button.add_css_class('suggested-action')
            for r in [self.game_mode_row, self.hardware_expander, self.streaming_expander, self.advanced_expander]: r.set_sensitive(False)
            if hasattr(self, 'pin_button'): self.pin_button.set_visible(True)
            if hasattr(self, 'summary_box'):
                 self.summary_box.set_visible(True)
                 self.populate_summary_fields()
        else:
            self.header.set_description('Configure e compartilhe seu jogo para seus amigos conectarem')
            self.perf_monitor.set_connection_status("Sunshine", "Inativo", False)
            self.perf_monitor.stop_monitoring()
            self.header.set_visible(True)
            if hasattr(self, 'summary_box'): self.summary_box.set_visible(False)
            if hasattr(self, 'pin_button'): self.pin_button.set_visible(False)
            self.start_button.set_label('Iniciar Servidor')
            self.start_button.remove_css_class('destructive-action')
            self.start_button.add_css_class('suggested-action')
            self.configure_button.set_sensitive(False)
            self.configure_button.remove_css_class('suggested-action')
            for r in [self.game_mode_row, self.hardware_expander, self.streaming_expander, self.advanced_expander]: r.set_sensitive(True)

    def populate_summary_fields(self):
        import socket, threading
        from utils.network import NetworkDiscovery
        self.update_field('hostname', socket.gethostname())
        if self.pin_code: self.update_field('pin', self.pin_code)
        ipv4, ipv6 = self.get_ip_addresses()
        self.update_field('ipv4', ipv4); self.update_field('ipv6', ipv6)
        
        def fetch_globals():
            net = NetworkDiscovery()
            g_ipv4 = net.get_global_ipv4(); g_ipv6 = net.get_global_ipv6()
            GLib.idle_add(self.update_field, 'ipv4_global', g_ipv4)
            GLib.idle_add(self.update_field, 'ipv6_global', g_ipv6)
        threading.Thread(target=fetch_globals, daemon=True).start()
        
    def update_field(self, key, value):
        if key in self.field_widgets:
            self.field_widgets[key]['real_value'] = value
            if self.field_widgets[key]['revealed']: self.field_widgets[key]['label'].set_text(value)

    def start_audio_mixer_refresh(self):
        self.stop_audio_mixer_refresh()
        self.mixer_source_id = GLib.timeout_add(3000, self._refresh_audio_mixer_ui)
        self._refresh_audio_mixer_ui()
        return True

    def stop_audio_mixer_refresh(self):
        if hasattr(self, 'mixer_source_id'):
            GLib.source_remove(self.mixer_source_id)
            del self.mixer_source_id

    def _refresh_audio_mixer_ui(self):
        # Allow refresh if visible, regardless of hosting state (per request)
        if not self.audio_mixer_expander.get_visible(): return True
        if not hasattr(self, 'audio_manager'): return True
        
        # If dual_audio_target is not set yet (e.g. before start), try to get from UI selection or config?
        # But we need the ACTUAL sink name to know what is "Private" vs "Shared".
        # If not set, we can't reliably determine "Private".
        # However, before hosting, apps are likely on Default Sink (Hardware).
        # We can assume "Hardware" is "Private".
        
        target_sink = getattr(self, 'dual_audio_target', None)
        if not target_sink:
             # Try to get from UI selection if possible without committing
             idx = self.audio_output_row.get_selected()
             if hasattr(self, 'audio_devices') and 0 <= idx < len(self.audio_devices):
                 target_sink = self.audio_devices[idx]['name']

        if not target_sink: return True # Can't mix without target

        apps = self.audio_manager.get_audio_applications()
        
        # Remove old rows that are not in new list
        current_rows = {} # id -> row
        
        # Adw.ExpanderRow doesn't have get_rows easily accessible in Python bindings sometimes, depending on version.
        # We can iterate children.
        # But removing specific children is tricky if we don't track them.
        # Simplest approach: Clear all and rebuild if count changes, or track IDs.
        
        # Let's try to track existing widgets to avoid flickering
        if not hasattr(self, 'mixer_rows'): self.mixer_rows = {}
        
        # Key: app_id
        seen_ids = set()
        
        for app in apps:
            app_id = app['id']
            seen_ids.add(app_id)
            
            # Check if sink is NOT the hardware sink (meaning it is Shared)
            is_shared = (app.get('sink_name') != target_sink)
            
            if app_id in self.mixer_rows:
                row = self.mixer_rows[app_id]
                # Update state silently
                if row.get_active() != is_shared:
                    row.disconnect_by_func(self._on_app_toggled) # Block signal
                    row.set_active(is_shared)
                    row.connect('notify::active', self._on_app_toggled, app_id)
                
                # Update subtitle always for existing rows
                status_text = "🔊 Compartilhado (Host + Guest)" if is_shared else "🔒 Privado (Apenas Host)"
                row.set_subtitle(status_text)
            else:
                row = Adw.SwitchRow()
                row.set_title(app['name'])
                status_text = "🔊 Compartilhado (Host + Guest)" if is_shared else "🔒 Privado (Apenas Host)"
                row.set_subtitle(status_text)
                row.set_icon_name(app['icon'] or 'audio-x-generic-symbolic')
                row.set_active(is_shared)
                row.connect('notify::active', self._on_app_toggled, app_id)
                self.audio_mixer_expander.add_row(row)
                self.mixer_rows[app_id] = row
                
        # Remove stale
        to_remove = []
        for aid, row in self.mixer_rows.items():
            if aid not in seen_ids:
                self.audio_mixer_expander.remove(row)
                to_remove.append(aid)
        for aid in to_remove: del self.mixer_rows[aid]
            
        return True

    def _on_app_toggled(self, row, param, app_id):
        # Resolve target sink again (hardware)
        target_hw = getattr(self, 'dual_audio_target', None)
        if not target_hw:
             idx = self.audio_output_row.get_selected()
             if hasattr(self, 'audio_devices') and 0 <= idx < len(self.audio_devices):
                 target_hw = self.audio_devices[idx]['name']
        
        if not target_hw:
            self.show_toast("Hardware de áudio não detectado")
            row.set_active(False) # Revert
            return

        is_shared = row.get_active()
        target_sink = "SunshineHybrid" if is_shared else target_hw
        
        # Verify if SunshineHybrid exists before trying to move
        if is_shared:
            sinks = [s['name'] for s in self.audio_manager.get_output_devices()]
            # Actually get_output_devices parses `pactl list sinks`.
            # Sunshine-Hybrid is a module-combine-sink, it appears as a sink.
            # But get_output_devices logic might miss it if description varies?
            # It looks for "Sink #", "Name:", "Description:".
            # It should find it.
            
            # Or just try to move and check result.
            pass

        success = self.audio_manager.move_app_to_sink(app_id, target_sink)
        if success:
             self.show_toast(f"Áudio {'Compartilhado' if is_shared else 'Privado (Local)'}")
        else:
             if is_shared and not self.is_hosting:
                 self.show_toast("Inicie o Servidor para habilitar o compartilhamento")
                 # We allow the switch to stay ON visually? Or revert?
                 # Reverting is better to reflect reality.
                 row.disconnect_by_func(self._on_app_toggled)
                 row.set_active(False)
                 row.connect('notify::active', self._on_app_toggled, app_id)
             else:
                 self.show_toast("Falha ao mover áudio")
             
    def start_hosting(self, b=None):
        self.loading_bar.set_visible(True); self.loading_bar.pulse()
        context = GLib.MainContext.default()
        while context.pending(): context.iteration(False)
            
        try:
            if self.sunshine.is_running():
                self.sunshine.stop()
                import time; time.sleep(1)
            
            self.pin_code = ''.join(random.choices(string.digits, k=6))
            from utils.network import NetworkDiscovery
            self.stop_pin_listener = NetworkDiscovery().start_pin_listener(self.pin_code, socket.gethostname())
            
            mode_idx = self.game_mode_row.get_selected()
            apps_config = []
            
            if mode_idx in [1, 2]:
                idx = self.game_list_row.get_selected()
                if idx != Gtk.INVALID_LIST_POSITION:
                    plat = {1: 'Steam', 2: 'Lutris'}[mode_idx]
                    games = self.detected_games.get(plat, [])
                    if 0 <= idx < len(games):
                        apps_config.append({"name": games[idx]['name'], "cmd": games[idx]['cmd'], "detached": True})
            elif mode_idx == 3:
                name = self.custom_name_entry.get_text(); cmd = self.custom_cmd_entry.get_text()
                if name and cmd: apps_config.append({"name": name, "cmd": cmd, "detached": True})
            
            if apps_config: self.sunshine.update_apps(apps_config)
            else:
                if mode_idx == 0: self.sunshine.update_apps([{"name": "Desktop", "detached": ["true"], "cmd": "true"}])
                     
            quality_map = {0: (5000, 30), 1: (10000, 30), 2: (20000, 60), 3: (30000, 60), 4: (40000, 60)}
            bitrate, fps = quality_map.get(self.quality_row.get_selected(), (20000, 60))
            
            selected_gpu_info = self.available_gpus[self.gpu_row.get_selected()]
            sunshine_config = {
                'encoder': selected_gpu_info['encoder'], 'bitrate': bitrate, 'fps': fps,
                'videocodec': 'h264', 'gamepad': 'x360', 'min_threads': 1, 'min_log_level': 4,
                'pkey': 'pkey.pem', 'cert': 'cert.pem', 'upnp': 'enabled' if self.upnp_row.get_active() else 'disabled',
                'address_family': 'both' if self.ipv6_row.get_active() else 'ipv4',
                'origin_web_ui_allowed': 'wan' if self.webui_anyone_row.get_active() else 'lan'
            }
            

            # Unified Audio Configuration
            self.dual_audio_target = None
            
            if self.audio_row.get_active():
                sunshine_config['audio'] = 'pulse'
                
                # Setup Audio Isolation Sinks BEFORE starting Sunshine
                if self.dual_audio_row.get_active():
                    idx = self.audio_output_row.get_selected()
                    if self.audio_devices and 0 <= idx < len(self.audio_devices):
                         self.dual_audio_target = self.audio_devices[idx]['name']
                         # Show Audio Mixer if dual audio is active
                         self.audio_mixer_expander.set_visible(True)

                # Save state first
                if self.audio_manager: self.audio_manager.save_state()
                
                # Setup sinks (Null + Hybrid)
                if self.audio_manager:
                    # capture_sink is "SunshineStereo" (Null Sink)
                    capture_sink = self.audio_manager.setup_sunshine_audio(self.dual_audio_target)
                    
                    # We pass the Sink Name to Sunshine. 
                    # Sunshine (Pulse) should automatically find the Monitor Source for this Sink.
                    sunshine_config['audio_sink'] = capture_sink
            else:
                sunshine_config['audio'] = 'none'
                self.audio_manager.cleanup()
                self.audio_mixer_expander.set_visible(False)

            platforms = ['auto', 'wayland', 'x11', 'kms']
            platform = platforms[self.platform_row.get_selected()]
            if platform == 'auto':
                session = os.environ.get('XDG_SESSION_TYPE', '').lower()
                platform = 'wayland' if session == 'wayland' else 'x11'
            sunshine_config['platform'] = platform


            if platform != 'wayland':
                monitor_idx = self.monitor_row.get_selected()
                # Se selecionado um monitor especifico (não Auto), tenta usar o nome
                if 0 < monitor_idx < len(self.available_monitors):
                    mon_name = self.available_monitors[monitor_idx][1]
                    if mon_name != 'auto':
                        sunshine_config['output_name'] = mon_name
            
            # Se for Wayland, NÃO definimos output_name. 
            # O Sunshine usa Portals (Pipewire) que pede pro usuário escolher ou usa o padrão.
            # Definir output_name no Wayland frequentemente causa erros de "Monitor not found".
            if selected_gpu_info['encoder'] == 'vaapi' and selected_gpu_info['adapter'] != 'auto':
                sunshine_config['adapter_name'] = selected_gpu_info['adapter']
            
            if platform == 'wayland':
                sunshine_config['wayland.display'] = os.environ.get('WAYLAND_DISPLAY', 'wayland-0')
            if platform == 'x11' and self.monitor_row.get_selected() == 0:
                sunshine_config['output_name'] = ':0'
            
            self.sunshine.configure(sunshine_config)
            if not self.sunshine.start():
                self.show_error_dialog('Erro ao Iniciar', 'Não foi possível iniciar o Sunshine.')
                return
            
            if self.audio_row.get_active() and self.dual_audio_row.get_active():
                GLib.timeout_add(1000, lambda: (self.start_audio_mixer_refresh(), True)[1])

            
            self.is_hosting = True
            self.perf_monitor.start_monitoring()
            self.sync_ui_state()
            self.show_toast(f'Servidor iniciado')
        except Exception as e:
            self.show_error_dialog('Erro', str(e))
        finally: self.loading_bar.set_visible(False)
        
    def stop_hosting(self, b=None):
        self.loading_bar.set_visible(True)
        self.audio_mixer_expander.set_visible(False)
        self.stop_audio_mixer_refresh()
        
        context = GLib.MainContext.default()
        while context.pending(): context.iteration(False)
        if hasattr(self, 'stop_pin_listener'):
            self.stop_pin_listener(); del self.stop_pin_listener
            
        try:
            if not self.sunshine.stop(): self.show_error_dialog('Erro', 'Falha ao parar Sunshine.')
        except Exception as e: print(f"Erro: {e}")
        
        # Delay audio cleanup to ensure Sunshine releases resources first
        if hasattr(self, 'audio_manager'):
            GLib.timeout_add(15000, lambda: (self.audio_manager.cleanup(), self.show_toast("Áudio Restaurado"))[1])
            
        self.is_hosting = False; self.sync_ui_state(); self.loading_bar.set_visible(False)
        self.show_toast('Parando servidor...')
        
    def update_status_info(self):
        if not self.is_hosting: return True
        sunshine_running = self.check_process_running('sunshine')
        if hasattr(self, 'sunshine_val'):
            self.sunshine_val.set_markup('<span color="#2ec27e">On-line</span>' if sunshine_running else '<span color="#e01b24">Parado</span>')
        ipv4, ipv6 = self.get_ip_addresses()
        self.update_field('ipv4', ipv4); self.update_field('ipv6', ipv6)
        return True
        
    def check_process_running(self, process_name):
        try:
            subprocess.check_output(["pgrep", "-x", process_name])
            return True
        except: return False
            
    def get_ip_addresses(self):
        ipv4 = ipv6 = "None"
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("1.1.1.1", 80)); ipv4 = s.getsockname()[0]
        except: pass
        try:
            res = subprocess.run(['ip', '-j', 'addr'], capture_output=True, text=True)
            if res.returncode == 0:
                for iface in json.loads(res.stdout):
                    name = iface['ifname']
                    # Pular interfaces de loopback, desligadas ou virtuais conhecidas
                    if name == 'lo' or 'UP' not in iface['flags']: continue
                    if any(x in name for x in ['docker', 'veth', 'virbr', 'vboxnet', 'tailscale', 'zerotier', 'br-']): continue
                    for addr in iface.get('addr_info', []):
                        if addr['family'] == 'inet' and ipv4 == "None": ipv4 = addr['local']
                        elif addr['family'] == 'inet6' and addr.get('scope') == 'global' and ipv6 == "None": ipv6 = addr['local']
        except: pass
        return ipv4, ipv6
        
    def show_error_dialog(self, title, message):
        dialog = Adw.MessageDialog.new(self.get_root(), title, message)
        dialog.add_response('ok', 'OK')
        dialog.present()
    
    def show_toast(self, message):
        window = self.get_root()
        if hasattr(window, 'show_toast'): window.show_toast(message)
        else: print(f"Toast: {message}")
        
    def open_sunshine_config(self, button):
        subprocess.Popen(['xdg-open', 'https://localhost:47990'])

    def on_game_mode_changed(self, row, param):
        idx = row.get_selected()
        self.platform_games_expander.set_visible(idx in [1, 2])
        self.platform_games_expander.set_expanded(idx in [1, 2])
        self.custom_app_expander.set_visible(idx == 3)
        self.custom_app_expander.set_expanded(idx == 3)
        if idx in [1, 2]:
            plat = {1: 'Steam', 2: 'Lutris'}[idx]
            self.platform_games_expander.set_title(f"Jogos da {plat}")
            self.populate_game_list(idx)
            
    def populate_game_list(self, mode_idx):
        plat = {1: 'Steam', 2: 'Lutris'}.get(mode_idx)
        if not plat: return
        if not self.detected_games[plat]:
             if plat == 'Steam': self.detected_games['Steam'] = self.game_detector.detect_steam()
             elif plat == 'Lutris': self.detected_games['Lutris'] = self.game_detector.detect_lutris()
        games = self.detected_games[plat]
        new_model = Gtk.StringList()
        if not games: new_model.append(f"Nenhum jogo encontrado no {plat}")
        else:
            for game in games: new_model.append(game['name'])
        self.game_list_row.set_model(new_model)

    def save_host_settings(self, *args):
        h = self.config.get('host', {})
        h.update({
            'mode_idx': self.game_mode_row.get_selected(),
            'custom_name': self.custom_name_entry.get_text(),
            'custom_cmd': self.custom_cmd_entry.get_text(),
            'quality_idx': self.quality_row.get_selected(),
            'players': int(self.players_row.get_value()),
            'monitor_idx': self.monitor_row.get_selected(),
            'gpu_idx': self.gpu_row.get_selected(),
            'platform_idx': self.platform_row.get_selected(),
            'audio': self.audio_row.get_active(),
            'dual_audio': self.dual_audio_row.get_active(),
            'audio_output_idx': self.audio_output_row.get_selected(),
            'input_sharing': self.input_row.get_active(),
            'upnp': self.upnp_row.get_active(),
            'ipv6': self.ipv6_row.get_active(),
            'webui_anyone': self.webui_anyone_row.get_active()
        })
        self.config.set('host', h)

    def load_settings(self):
        self.loading_settings = True
        try:
            h = self.config.get('host', {})
            if not h: return
            self.game_mode_row.set_selected(h.get('mode_idx', 0))
            self.custom_name_entry.set_text(h.get('custom_name', ''))
            self.custom_cmd_entry.set_text(h.get('custom_cmd', ''))
            self.quality_row.set_selected(h.get('quality_idx', 2))
            self.players_row.set_value(h.get('players', 2))
            self.monitor_row.set_selected(h.get('monitor_idx', 0))
            self.gpu_row.set_selected(h.get('gpu_idx', 0))
            self.platform_row.set_selected(h.get('platform_idx', 0))
            self.audio_row.set_active(h.get('audio', True))
            
            dual_audio_active = h.get('dual_audio', False)
            self.dual_audio_row.set_active(dual_audio_active)
            if dual_audio_active:
                self.audio_mixer_expander.set_visible(True)
                self.start_audio_mixer_refresh()
            
            self.audio_output_row.set_selected(h.get('audio_output_idx', 0))
            self.input_row.set_active(h.get('input_sharing', True))
            self.upnp_row.set_active(h.get('upnp', True))
            self.ipv6_row.set_active(h.get('ipv6', True))
            self.webui_anyone_row.set_active(h.get('webui_anyone', False))
        finally:
            self.loading_settings = False

    def connect_settings_signals(self):
        for r in [self.game_mode_row, self.quality_row, self.monitor_row, self.gpu_row, self.platform_row, self.audio_output_row]:
            r.connect('notify::selected', self.save_host_settings)
        for r in [self.audio_row, self.dual_audio_row, self.input_row, self.upnp_row, self.ipv6_row, self.webui_anyone_row]:
            r.connect('notify::active', self.save_host_settings)
        for r in [self.custom_name_entry, self.custom_cmd_entry]:
            r.connect('notify::text', self.save_host_settings)
        self.players_row.get_adjustment().connect('value-changed', self.save_host_settings)

    def on_reset_clicked(self, button):
        diag = Adw.MessageDialog(heading='Restaurar Padrões', body='Deseja restaurar as configurações padrões?')
        diag.add_response('cancel', 'Cancelar'); diag.add_response('reset', 'Restaurar')
        diag.set_response_appearance('reset', Adw.ResponseAppearance.DESTRUCTIVE)
        def on_resp(d, r):
            if r == 'reset': self.reset_to_defaults()
        diag.connect('response', on_resp); diag.present()

    def reset_to_defaults(self):
        self.config.set('host', self.config.default_config()['host'])
        self.load_settings(); self.show_toast("Configurações restauradas")

    def cleanup(self):
        if hasattr(self, 'perf_monitor'): self.perf_monitor.stop_monitoring()
        if self.is_hosting: self.stop_hosting()
        if hasattr(self, 'stop_pin_listener'): self.stop_pin_listener()
        if hasattr(self, 'audio_manager'): self.audio_manager.cleanup()
