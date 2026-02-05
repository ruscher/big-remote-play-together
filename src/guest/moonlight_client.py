"""
Módulo Guest - Gerenciamento do Moonlight
"""

import subprocess
import signal
from typing import Optional, Dict

class MoonlightClient:
    """Gerenciador do cliente Moonlight"""
    
    def __init__(self):
        self.process = None
        self.connected_host = None
        
        # Detectar comando moonlight disponível
        self.moonlight_cmd = self.detect_moonlight()
        
    def detect_moonlight(self) -> Optional[str]:
        """Detecta qual comando Moonlight usar"""
        import shutil
        
        for cmd in ['moonlight-qt', 'moonlight']:
            if shutil.which(cmd):
                return cmd
                
        return None
        
    def connect(self, host_ip: str, **kwargs) -> bool:
        """
        Conecta a um host Sunshine
        
        Args:
            host_ip: Endereço IP do host
            **kwargs: Opções adicionais
        """
        if not self.moonlight_cmd:
            print("Moonlight não está instalado")
            return False
            
        if self.is_connected():
            print("Já conectado a um host")
            return False
            
        try:
            # Construir comando
            cmd = [self.moonlight_cmd]
            
            # Adicionar host
            cmd.append(host_ip)
            
            # Opções
            if kwargs.get('quality'):
                quality_map = {
                    '720p30': ['-width', '1280', '-height', '720', '-fps', '30'],
                    '1080p30': ['-width', '1920', '-height', '1080', '-fps', '30'],
                    '1080p60': ['-width', '1920', '-height', '1080', '-fps', '60'],
                    '1440p60': ['-width', '2560', '-height', '1440', '-fps', '60'],
                    '4k60': ['-width', '3840', '-height', '2160', '-fps', '60'],
                }
                
                if kwargs['quality'] in quality_map:
                    cmd.extend(quality_map[kwargs['quality']])
                    
            if kwargs.get('bitrate'):
                cmd.extend(['-bitrate', str(kwargs['bitrate'])])
                
            if kwargs.get('fullscreen', False):
                cmd.append('-fullscreen')
                
            if not kwargs.get('audio', True):
                cmd.append('-noaudio')
                
            if kwargs.get('hw_decode', True):
                cmd.append('-codec', 'auto')
                
            # Iniciar processo
            self.process = subprocess.Popen(cmd)
            self.connected_host = host_ip
            
            print(f"Conectado a {host_ip}")
            return True
            
        except Exception as e:
            print(f"Erro ao conectar: {e}")
            return False
            
    def disconnect(self) -> bool:
        """Desconecta do host"""
        if not self.is_connected():
            print("Não está conectado")
            return False
            
        try:
            if self.process:
                self.process.terminate()
                self.process.wait(timeout=5)
                
            self.process = None
            self.connected_host = None
            
            print("Desconectado")
            return True
            
        except Exception as e:
            print(f"Erro ao desconectar: {e}")
            # Forçar kill
            try:
                if self.process:
                    self.process.kill()
                    self.process = None
                    self.connected_host = None
            except:
                pass
            return False
            
    def is_connected(self) -> bool:
        """Verifica se está conectado"""
        if self.process and self.process.poll() is None:
            return True
        return False
        
    def get_status(self) -> Dict:
        """Obtém status da conexão"""
        return {
            'connected': self.is_connected(),
            'host': self.connected_host,
            'moonlight_cmd': self.moonlight_cmd,
        }
        
    def pair(self, host_ip: str, pin: Optional[str] = None) -> bool:
        """
        Pareia com um host
        
        Args:
            host_ip: Endereço IP do host
            pin: PIN de pareamento (se necessário)
        """
        if not self.moonlight_cmd:
            return False
            
        try:
            cmd = [self.moonlight_cmd, 'pair', host_ip]
            
            if pin:
                # Moonlight geralmente pede PIN interativamente
                # Pode ser necessário usar subprocess.PIPE e enviar PIN
                process = subprocess.Popen(
                    cmd,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                
                stdout, stderr = process.communicate(input=f"{pin}\n")
                return process.returncode == 0
            else:
                result = subprocess.run(cmd, capture_output=True)
                return result.returncode == 0
                
        except Exception as e:
            print(f"Erro ao parear: {e}")
            return False
            
    def list_apps(self, host_ip: str) -> list:
        """
        Lista aplicativos disponíveis no host
        
        Args:
            host_ip: Endereço IP do host
        """
        if not self.moonlight_cmd:
            return []
            
        try:
            result = subprocess.run(
                [self.moonlight_cmd, 'list', host_ip],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                # Parse output
                apps = []
                for line in result.stdout.splitlines():
                    if line.strip():
                        apps.append(line.strip())
                return apps
            else:
                return []
                
        except Exception as e:
            print(f"Erro ao listar apps: {e}")
            return []
