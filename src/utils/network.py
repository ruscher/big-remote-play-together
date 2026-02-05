"""
Descoberta de hosts na rede
"""

import socket
import subprocess
import re
from typing import List, Dict

from utils.logger import Logger

class NetworkDiscovery:
    """Descoberta de hosts Sunshine na rede"""
    
    def __init__(self):
        self.hosts = []
        self.logger = Logger()
        
    def discover_hosts(self, callback=None):
        """Descobre hosts Sunshine na rede local usando Avahi/mDNS"""
        import threading
        
        def discover_thread():
            hosts = []
            
            try:
                # Tentar usar avahi-browse
                result = subprocess.run(
                    ['avahi-browse', '-t', '-r', '_sunshine._tcp'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                if result.returncode == 0:
                    # Parser do output do avahi-browse
                    for line in result.stdout.split('\n'):
                        if 'address' in line.lower():
                            # Extrair host do output
                            # TODO: Parser mais robusto
                            parts = line.split()
                            if len(parts) >= 2:
                                hosts.append({
                                    'name': 'Sunshine Host',
                                    'ip': parts[-1],
                                    'port': 47989,
                                    'status': 'online'
                                })
                else:
                    self.logger.warning("avahi-browse falhou, tentando scan manual")
                    hosts = self.manual_scan()
                    
            except FileNotFoundError:
                self.logger.warning("avahi-browse não encontrado, usando scan manual")
                hosts = self.manual_scan()
            except subprocess.TimeoutExpired:
                self.logger.warning("avahi-browse timeout, usando scan manual")
                hosts = self.manual_scan()
            except Exception as e:
                self.logger.error(f"Erro na descoberta: {e}")
                hosts = []
            
            # Chamar callback se fornecido
            if callback:
                from gi.repository import GLib
                GLib.idle_add(callback, hosts)
            
            return hosts
        
        # Iniciar thread de descoberta
        thread = threading.Thread(target=discover_thread, daemon=True)
        thread.start()
        
        return thread
        
    def parse_avahi_output(self, output: str) -> List[Dict[str, str]]:
        """Parse saída do avahi-browse"""
        hosts = []
        
        # Regex para extrair informações
        pattern = r'hostname\s*=\s*\[([^\]]+)\].*?address\s*=\s*\[([^\]]+)\]'
        matches = re.finditer(pattern, output, re.DOTALL)
        
        for match in matches:
            hostname = match.group(1)
            ip = match.group(2)
            
            hosts.append({
                'name': hostname,
                'ip': ip,
                'port': 47989,
                'status': 'online'
            })
            
        return hosts
        
    def manual_scan(self) -> List[Dict[str, str]]:
        """
        Scan manual da rede local (fallback)
        Procura por portas Sunshine abertas
        """
        hosts = []
        
        try:
            # Obter próprio IP
            local_ip = self.get_local_ip()
            if not local_ip:
                return hosts
                
            # Extrair subnet
            subnet = '.'.join(local_ip.split('.')[:-1])
            
            # Scan rápido das primeiras 254 IPs
            # TODO: Implementar scan paralelo para performance
            for i in range(1, 255):
                ip = f"{subnet}.{i}"
                
                if self.check_sunshine_port(ip):
                    # Tentar obter hostname
                    try:
                        hostname = socket.gethostbyaddr(ip)[0]
                    except:
                        hostname = f"Host-{i}"
                        
                    hosts.append({
                        'name': hostname,
                        'ip': ip,
                        'port': 47989,
                        'status': 'online'
                    })
                    
        except Exception as e:
            print(f"Erro no scan manual: {e}")
            
        return hosts
        
    def check_sunshine_port(self, ip: str, port: int = 47989, timeout: float = 0.5) -> bool:
        """Verifica se porta Sunshine está aberta"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((ip, port))
            sock.close()
            return result == 0
        except:
            return False
            
    def get_local_ip(self) -> str:
        """Obtém IP local"""
        try:
            # Conectar a um servidor externo para obter IP local
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            return local_ip
        except:
            return ""
            
    def resolve_pin(self, pin: str) -> str:
        """
        Resolve código PIN para endereço IP
        TODO: Implementar servidor de descoberta central
        """
        # Por enquanto, retorna vazio
        # Futuramente: consultar servidor de matchmaking
        return ""
