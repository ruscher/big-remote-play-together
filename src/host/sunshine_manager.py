"""
Módulo Host - Gerenciamento do Sunshine
"""

import subprocess
import signal
import os
from pathlib import Path
from typing import Optional

class SunshineHost:
    """Gerenciador do servidor Sunshine"""
    
    def __init__(self, config_dir: Optional[Path] = None):
        if config_dir is None:
            self.config_dir = Path.home() / '.config' / 'big-remoteplay' / 'sunshine'
        else:
            self.config_dir = config_dir
            
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        self.process = None
        self.pid = None
        
    def start(self, **kwargs) -> bool:
        """
        Inicia o servidor Sunshine
        
        Args:
            **kwargs: Argumentos opcionais para configuração
        """
        if self.is_running():
            print("Sunshine já está em execução")
            return False
            
        try:
            config_file = self.config_dir / 'sunshine.conf'
            
            # O arquivo de configuração é gerado pelo HostView antes de chamar start()
            pass
            
            # Verificar comando
            import shutil
            sunshine_cmd = shutil.which('sunshine')
            if not sunshine_cmd:
                print("Sunshine não encontrado no PATH")
                return False

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
                sunshine_cmd,
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
        
    def configure(self, settings: dict) -> bool:
        """
        Configura Sunshine
        
        Args:
            settings: Dicionário com configurações
        """
        try:
            config_file = self.config_dir / 'sunshine.conf'
            
            with open(config_file, 'w') as f:
                for key, value in settings.items():
                    f.write(f"{key} = {value}\n")
                    
            return True
            
        except Exception as e:
            print(f"Erro ao configurar Sunshine: {e}")
            return False
