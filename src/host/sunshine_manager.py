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
            
            cmd = [
                'sunshine',
                f'--config={config_file}'
            ]
            
            # Iniciar processo
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=os.setsid  # Criar novo grupo de processos
            )
            
            self.pid = self.process.pid
            
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
                os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
                self.process.wait(timeout=5)
                
            else:
                # Usar PID salvo
                pid_file = self.config_dir / 'sunshine.pid'
                if pid_file.exists():
                    with open(pid_file, 'r') as f:
                        pid = int(f.read().strip())
                        
                    os.kill(pid, signal.SIGTERM)
                    
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
