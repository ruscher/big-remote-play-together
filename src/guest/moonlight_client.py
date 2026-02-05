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
            # Moonlight QT exige o verbo 'stream' seguido do IP e App
            cmd = [self.moonlight_cmd, 'stream', host_ip, 'Desktop']
            
            # Opções
            if kwargs.get('quality'):
                # Mapeamento para resolução e FPS
                # Formato: --resolution WxH --fps N
                quality_map = {
                    '720p30': ['--resolution', '1280x720', '--fps', '30'],
                    '1080p30': ['--resolution', '1920x1080', '--fps', '30'],
                    '1080p60': ['--resolution', '1920x1080', '--fps', '60'],
                    '1440p60': ['--resolution', '2560x1440', '--fps', '60'],
                    '4k60': ['--resolution', '3840x2160', '--fps', '60'],
                }
                
                if kwargs['quality'] in quality_map:
                    cmd.extend(quality_map[kwargs['quality']])
                    
            if kwargs.get('bitrate'):
                cmd.extend(['--bitrate', str(kwargs['bitrate'])])
                
            if kwargs.get('fullscreen', False):
                cmd.extend(['--display-mode', 'fullscreen'])
            else:
                cmd.extend(['--display-mode', 'windowed'])
                
            # Audio (moonlight-qt não tem flag simples de no-audio explicita no help,
            # assumindo padrão ligado. Se quiser desligar, teria que configurar sistema)
            
            if kwargs.get('hw_decode', True):
                cmd.extend(['--video-decoder', 'hardware'])
            else:
                cmd.extend(['--video-decoder', 'software'])
                
            # Iniciar processo
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            self.connected_host = host_ip
            
            # Verificar se falhou imediatamente
            try:
                exit_code = self.process.wait(timeout=1.0)
                # Se chegou aqui, falhou
                stdout, stderr = self.process.communicate()
                print(f"Moonlight terminou imediatamente (Code {exit_code})")
                print(f"STDOUT: {stdout}")
                print(f"STDERR: {stderr}")
                return False
            except subprocess.TimeoutExpired:
                # Continua rodando
                pass
            
            print(f"Conectado a {host_ip}")
            return True
            
        except Exception as e:
            print(f"Erro ao conectar: {e}")
            return False
            
    def probe_host(self, host_ip: str) -> bool:
        """Verifica se o host é acessível e está pareado (usando list)"""
        try:
             # Tenta listar apps. Se funcionar, está pareado.
             # Se falhar, provavelmente precisa parear.
             # Timeout curto pois pode travar se o host não responder
             cmd = [self.moonlight_cmd, 'list', host_ip]
             result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=2)
             return result.returncode == 0
        except:
             return False

    def pair(self, host_ip: str, on_pin_callback=None) -> bool:
        """
        Inicia processo de pareamento.
        Chama on_pin_callback(pin) quando o PIN for detectado.
        Bloqueia até parear ou falhar.
        """
        try:
            cmd = [self.moonlight_cmd, 'pair', host_ip]
            # Precisamos ler stdout em tempo real
            process = subprocess.Popen(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.STDOUT, 
                text=True, 
                bufsize=1
            )
            
            pin_found = False
            
            while process.poll() is None:
                line = process.stdout.readline()
                if not line:
                    break
                    
                print(f"PAIR: {line.strip()}") # Debug
                
                # Detectar PIN
                # Ex: "Please enter the following PIN on the target PC: 1234"
                if "PIN" in line and "target PC" in line:
                    parts = line.strip().split()
                    if parts:
                        pin = parts[-1]
                        # Remover pontuação se houver
                        pin = ''.join(filter(str.isdigit, pin))
                        if pin and on_pin_callback:
                            on_pin_callback(pin)
                            pin_found = True
                            
                # Detectar sucesso
                if "successfully paired" in line.lower() or "already paired" in line.lower():
                    process.terminate()
                    return True
                    
            return process.returncode == 0
            
        except Exception as e:
            print(f"Erro no pareamento: {e}")
            return False

    def disconnect(self) -> bool:
        """Desconecta do host"""
        if not self.is_connected():
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
