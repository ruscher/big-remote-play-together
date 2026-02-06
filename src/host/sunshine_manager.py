import subprocess, signal, os, shutil
from pathlib import Path
class SunshineHost:
    def __init__(self, cdir: Path = None):
        self.config_dir = cdir or (Path.home() / '.config' / 'big-remoteplay' / 'sunshine')
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.process = None
        self.pid = None
        
    def start(self, **kwargs):
        if self.is_running(): return False
        sc = shutil.which('sunshine')
        if not sc: return False
        try:
            config_file = self.config_dir / 'sunshine.conf'
            # Preparar ambiente
            env = os.environ.copy()
            if 'DISPLAY' not in env:
                env['DISPLAY'] = ':0'
            
            if 'XAUTHORITY' not in env:
                home = os.path.expanduser('~')
                xauth = os.path.join(home, '.Xauthority')
                if os.path.exists(xauth):
                    env['XAUTHORITY'] = xauth
            
            if 'XDG_RUNTIME_DIR' not in env:
                uid = os.getuid()
                runtime_dir = f'/run/user/{uid}'
                if os.path.exists(runtime_dir):
                    env['XDG_RUNTIME_DIR'] = runtime_dir
            
            # Repassar WAYLAND_DISPLAY se existir
            if 'WAYLAND_DISPLAY' in os.environ:
                env['WAYLAND_DISPLAY'] = os.environ['WAYLAND_DISPLAY']

            cmd = [
                sc,
                str(config_file)
            ]
            
            # Iniciar processo em uma nova sessão para facilitar o gerenciamento de grupo de processos
            self.process = subprocess.Popen(
                cmd,
                text=True,
                env=env,
                cwd=str(self.config_dir), # Forçar diretório de trabalho para configs locais
                start_new_session=True # Criar novo group ID
            )
            
            self.pid = self.process.pid
            
            # Verificar se o processo morreu imediatamente (ex: erro de biblioteca)
            try:
                # Esperar um pouco para ver se falha na inicialização
                exit_code = self.process.wait(timeout=1.0)
                
                # Se chegou aqui, o processo terminou (falhou)
                print(f"Sunshine falhou ao iniciar (Exit code {exit_code}). Verifique os logs acima.")
                
                self.process = None
                self.pid = None
                return False
                
            except subprocess.TimeoutExpired:
                # Processo continua rodando após o timeout, sucesso!
                pass            
            
            # Salvar PID
            pid_file = self.config_dir / 'sunshine.pid'
            with open(pid_file, 'w') as f:
                f.write(str(self.pid))
                
            print(f"Sunshine iniciado (PID: {self.pid})")
            return True
            
        except Exception as e:
            print(f"Erro ao iniciar Sunshine: {e}")
            return False
            
    def stop(self) -> bool:
        """Para o servidor Sunshine"""
        if not self.is_running():
            print("Sunshine não está em execução")
            return False
            
        try:
            if self.process:
                # Enviar SIGTERM
                print(f"Parando processo filho {self.process.pid}...")
                os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
                try:
                    self.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    print("Timeout, forçando kill...")
                    os.killpg(os.getpgid(self.process.pid), signal.SIGKILL)
                
            else:
                # Usar PID salvo
                pid_file = self.config_dir / 'sunshine.pid'
                if pid_file.exists():
                    try:
                        with open(pid_file, 'r') as f:
                            pid = int(f.read().strip())
                        print(f"Parando PID {pid} do arquivo...")
                        os.kill(pid, signal.SIGTERM)
                    except Exception as e:
                        print(f"Erro ao matar PID do arquivo: {e}")
            
            # Fallback: garantir que não sobrou nada rodando via pkill
            # Isso resolve casos onde o processo foi iniciado externamente ou PID file perdeu sync
            subprocess.run(['pkill', '-x', 'sunshine'], stderr=subprocess.DEVNULL)
                    
            # Remover PID file
            pid_file = self.config_dir / 'sunshine.pid'
            if pid_file.exists():
                pid_file.unlink()
                
            self.process = None
            self.pid = None
            
            print("Sunshine parado")
            return True
            
        except Exception as e:
            print(f"Erro ao parar Sunshine: {e}")
            # Tentar matar de qualquer jeito
            subprocess.run(['pkill', '-x', 'sunshine'], stderr=subprocess.DEVNULL)
            return False
            
    def restart(self) -> bool:
        """Reinicia o servidor"""
        self.stop()
        return self.start()
        
    def is_running(self) -> bool:
        """Verifica se Sunshine está em execução"""
        # Verificar processo direto
        if self.process and self.process.poll() is None:
            return True
            
        # Verificar PID file
        pid_file = self.config_dir / 'sunshine.pid'
        if pid_file.exists():
            try:
                with open(pid_file, 'r') as f:
                    pid = int(f.read().strip())
                    
                # Verificar se processo existe
                os.kill(pid, 0)
                return True
                
            except (OSError, ValueError):
                # Processo não existe, limpar PID file
                pid_file.unlink()
                return False
                
        # Verificar via pgrep
        try:
            result = subprocess.run(
                ['pgrep', '-x', 'sunshine'],
                capture_output=True
            )
            return result.returncode == 0
        except:
            return False
            
    def get_status(self) -> dict:
        """Obtém status do servidor"""
        return {
            'running': self.is_running(),
            'pid': self.pid,
            'config_dir': str(self.config_dir),
        }
        
    def update_apps(self, apps_list: list) -> bool:
        """
        Atualiza a lista de aplicativos (apps.json)
        
        Args:
            apps_list: Lista de dicionários descrevendo os apps
                       Ex: [{'name': 'Steam', 'cmd': 'steam', ...}]
        """
        try:
            import json
            apps_file = self.config_dir / 'apps.json'
            
            # Formato do apps.json do Sunshine
            data = {
                "env": {
                    "PATH": "$(PATH):$(HOME)/.local/bin"
                },
                "apps": apps_list
            }
            
            with open(apps_file, 'w') as f:
                json.dump(data, f, indent=4)
                
            return True
        except Exception as e:
            print(f"Erro ao salvar apps.json: {e}")
            return False

    def configure(self, settings: dict) -> bool:
        """
        Configura Sunshine
        
        Args:
            settings: Dicionário com configurações
        """
        try:
            config_file = self.config_dir / 'sunshine.conf'
            
            # Garantir que apontamos para o apps.json
            if 'apps_file' not in settings:
                settings['apps_file'] = 'apps.json'
            
            with open(config_file, 'w') as f:
                for key, value in settings.items():
                    f.write(f"{key} = {value}\n")
                    
            return True
            
        except Exception as e:
            print(f"Erro ao configurar Sunshine: {e}")
            return False

    def send_pin(self, pin: str, auth: tuple[str, str] = None) -> tuple[bool, str]:
        """Envia PIN para o Sunshine via API"""
        import urllib.request, ssl, json, base64
        
        url = "https://localhost:47990/api/pin"
        headers = {
            "Content-Type": "application/json",
        }
        
        if auth:
            username, password = auth
            auth_str = f"{username}:{password}"
            b64_auth = base64.b64encode(auth_str.encode()).decode()
            headers["Authorization"] = f"Basic {b64_auth}"
        
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        
        try:
            data = json.dumps({"pin": pin}).encode('utf-8')
            req = urllib.request.Request(url, data=data, headers=headers, method='POST')
            
            with urllib.request.urlopen(req, context=ctx, timeout=5) as response:
                if response.status == 200:
                    return True, "PIN enviado com sucesso"
                return False, f"Status HTTP {response.status}"
                
        except urllib.error.HTTPError as e:
            if e.code == 401:
                return False, "Falha de Autenticação. Configure um usuário no Sunshine."
            return False, f"Erro API: {e.code} - {e.reason}"
        except Exception as e:
            return False, f"Erro de Conexão: {e}"

    def create_user(self, username, password) -> tuple[bool, str]:
        """Cria um novo usuário administrativo no Sunshine via API"""
        import urllib.request, ssl, json
        
        url = "https://localhost:47990/api/users"
        headers = {
            "Content-Type": "application/json",
        }
        
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        
        try:
            # Tentar enviar confirmação de senha também, pois o erro 400 sugere campos faltando.
            # Baseado no formulário web que exige confirmação.
            # E nos IDs dos campos: usernameInput, passwordInput, confirmPasswordInput
            data_dict = {
                "usernameInput": username, 
                "passwordInput": password,
                "confirmPasswordInput": password 
            }
            data = json.dumps(data_dict).encode('utf-8')
            req = urllib.request.Request(url, data=data, headers=headers, method='POST')
            
            with urllib.request.urlopen(req, context=ctx, timeout=5) as response:
                if response.status == 200:
                    return True, "Usuário criado com sucesso"
                return False, f"Status HTTP {response.status}"
                
        except urllib.error.HTTPError as e:
            msg = e.read().decode('utf-8') if e.fp else e.reason
            return False, f"Erro API: {e.code} - {msg}"
        except Exception as e:
            return False, f"Erro de Conexão: {e}"
