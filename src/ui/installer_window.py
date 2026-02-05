
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

try:
    # Try to load VTE for GTK4 (usually version 3.91)
    gi.require_version('Vte', '3.91')
    from gi.repository import Vte
    HAS_VTE = True
except (ValueError, ImportError):
    HAS_VTE = False

from gi.repository import Gtk, Adw, GLib, Gio
import subprocess
import os

import shutil

class InstallerWindow(Adw.Window):
    """Janela de instalação de dependências"""
    
    def __init__(self, parent=None, on_success=None):
        super().__init__(transient_for=parent)
        
        self.on_success_callback = on_success
        
        self.set_title('Instalação de Dependências')
        self.set_default_size(700, 500)
        self.set_modal(True)
        
        # Main content
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_margin_top(12)
        box.set_margin_bottom(12)
        box.set_margin_start(12)
        box.set_margin_end(12)
        self.set_content(box)
        
        # Header
        header = Gtk.Label(label='Instalando componentes necessários...')
        header.add_css_class('title-2')
        box.append(header)
        
        # Terminal/Log area frame
        frame = Gtk.Frame()
        frame.set_vexpand(True)
        box.append(frame)
        
        if HAS_VTE:
            self.terminal = Vte.Terminal()
            self.terminal.set_scrollback_lines(1000)
            self.terminal.connect('child-exited', self.on_process_exit)
            frame.set_child(self.terminal)
            
            # Start installation directly
            GLib.idle_add(self.start_installation)
        else:
            # Fallback text view
            scrolled = Gtk.ScrolledWindow()
            self.textview = Gtk.TextView()
            self.textview.set_editable(False)
            self.textview.set_monospace(True)
            self.textview.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
            
            buffer = self.textview.get_buffer()
            buffer.set_text("Terminal integrado não disponível (vte4 não encontrado).\n"
                          "Abrindo terminal externo para instalação...\n"
                          "Por favor, aguarde o fim da instalação na outra janela.")
            
            scrolled.set_child(self.textview)
            frame.set_child(scrolled)
            
            # Start external installation
            GLib.idle_add(self.start_external_installation)
        
        # Status/Action area
        self.status_label = Gtk.Label(label='Iniciando...')
        box.append(self.status_label)
        
        self.close_btn = Gtk.Button(label='Cancelar')
        self.close_btn.add_css_class('destructive-action')
        self.close_btn.connect('clicked', lambda b: self.close())
        box.append(self.close_btn)

    def start_external_installation(self):
        install_cmd = "yay -S --noconfirm --needed sunshine moonlight-qt vte4"
        shell_cmd = f"{install_cmd}; echo ''; echo 'Instalação concluída! Pressione Enter para fechar...'; read"
        
        terminals = [
            ['konsole', '-e', 'bash', '-c', shell_cmd],
            ['gnome-terminal', '--', 'bash', '-c', shell_cmd],
            ['xfce4-terminal', '-x', 'bash', '-c', shell_cmd],
            ['xterm', '-e', 'bash', '-c', shell_cmd]
        ]
        
        started = False
        for term_cmd in terminals:
            if shutil.which(term_cmd[0]):
                try:
                    subprocess.Popen(term_cmd)
                    started = True
                    break
                except:
                    continue
                    
        if started:
            self.status_label.set_text('Instalação rodando em terminal externo. Reinicie o app após concluir.')
            self.close_btn.set_label('Fechar')
            self.close_btn.remove_css_class('destructive-action')
            self.close_btn.add_css_class('suggested-action')
        else:
            self.status_label.set_text('Erro: Nenhum terminal detectado.')
            buffer = self.textview.get_buffer()
            buffer.set_text(f"Não foi possível abrir terminal.\nExecute manualmente:\n{install_cmd}")
        
    def start_installation(self):
        # Command to run
        cmd = ['yay', '-S', '--noconfirm', '--needed', 'sunshine', 'moonlight-qt']
        
        self.status_label.set_text('Executando instalação... (Pode pedir senha de sudo)')
        
        try:
            # Create a cancellable
            cancellable = Gio.Cancellable()
            
            def spawn_callback(terminal, pid, error, user_data):
                if error:
                    print(f"Spawn error: {error}")
                    GLib.idle_add(lambda: self.status_label.set_text(f"Erro ao iniciar: {error}"))
                    GLib.idle_add(self.start_external_installation)

            # Vte spawn_async arguments:
            # pty_flags, working_directory, argv, envv, spawn_flags, child_setup, timeout, cancellable, callback, user_data
            self.terminal.spawn_async(
                Vte.PtyFlags.DEFAULT,
                None,  # working directory
                cmd,
                None,  # env (None = inherit)
                GLib.SpawnFlags.SEARCH_PATH,
                None,  # child_setup
                -1,    # timeout
                cancellable,
                spawn_callback,
                None   # user_data
            )
        except Exception as e:
            print(f"Erro VTE spawn_async: {e}")
            self.status_label.set_text(f'Erro no terminal integrado: {e}. Tentando externo...')
            
            # Fallback to external terminal
            GLib.idle_add(self.start_external_installation)

    def on_process_exit(self, terminal, status):
        # status is the exit code
        # VTE usage might return a complex status, need to extract exit code
        # Usually it matches waitpid status
        
        if os.WIFEXITED(status):
            exit_code = os.WEXITSTATUS(status)
            if exit_code == 0:
                self.on_success()
            else:
                self.on_failure(exit_code)
        else:
            self.on_failure(-1)
            
    def on_success(self):
        self.status_label.set_text('Instalação concluída com sucesso!')
        self.status_label.remove_css_class('error')
        self.status_label.add_css_class('success')
        
        self.close_btn.set_label('Concluir')
        self.close_btn.remove_css_class('destructive-action')
        self.close_btn.add_css_class('suggested-action')
        
        # Update behavior: Close button now just closes, functionality is done
        
        # Trigger parent update
        if self.on_success_callback:
            self.on_success_callback()
            
    def on_failure(self, code):
        self.status_label.set_text(f'Falha na instalação. Código de saída: {code}')
        self.status_label.add_css_class('error')
        self.close_btn.set_label('Fechar')
