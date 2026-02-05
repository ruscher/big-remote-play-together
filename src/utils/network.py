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
            
            # 1. Tentar Avahi (mDNS)
            try:
                # Sunshine usa _nvstream._tcp (compatibilidade Nvidia) e as vezes _sunshine._tcp
                # Vamos buscar _nvstream._tcp
                cmd = ['avahi-browse', '-t', '-r', '-p', '_nvstream._tcp']
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                if result.returncode == 0 and result.stdout:
                    hosts = self.parse_avahi_output(result.stdout)
                
                # Se não encontrou nada, tenta manual
                if not hosts:
                    self.logger.info("Avahi não encontrou hosts, iniciando scan manual")
                    hosts = self.manual_scan()
                else:
                    self.logger.info(f"Avahi encontrou {len(hosts)} hosts")
                    
            except Exception as e:
                self.logger.warning(f"Falha no Avahi: {e}. Usando scan manual.")
                hosts = self.manual_scan()
            
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
        """Parse saída do avahi-browse -p"""
        hosts = []
        seen_ips = set()
        
        # Formato parsable: =;eth0;IPv4;NomeDoServico;_nvstream._tcp;local;hostname.local;192.168.X.X;47989;...
        for line in output.split('\n'):
            parts = line.split(';')
            if len(parts) > 7 and parts[0] == '=':
                service_name = parts[3]
                hostname = parts[6]
                ip = parts[7]
                port = parts[8]
                
                if ip not in seen_ips:
                    hosts.append({
                        'name': service_name,
                        'ip': ip,
                        'port': int(port),
                        'status': 'online',
                        'hostname': hostname
                    })
                    seen_ips.add(ip)
                    
        return hosts
        
    def manual_scan(self) -> List[Dict[str, str]]:
        """
        Scan manual da rede local (rápido com threads)
        """
        import concurrent.futures
        from concurrent.futures import ThreadPoolExecutor
        
        hosts = []
        local_ip = self.get_local_ip()
        
        targets = ['127.0.0.1']
        if local_ip:
            subnet = '.'.join(local_ip.split('.')[:-1])
            # Adicionar IPs da subnet (1-254)
            for i in range(1, 255):
                targets.append(f"{subnet}.{i}")
                
        def check_host(ip):
            if self.check_sunshine_port(ip):
                try:
                    # Tentar resolver nome
                    name = socket.gethostbyaddr(ip)[0]
                except:
                    name = ip
                return {
                    'name': name,
                    'ip': ip,
                    'port': 47989,
                    'status': 'online'
                }
            return None

        # Scan paralelo
        with ThreadPoolExecutor(max_workers=50) as executor:
            futures = [executor.submit(check_host, ip) for ip in targets]
            for future in concurrent.futures.as_completed(futures):
                result = future.result()
                if result:
                    hosts.append(result)
                    
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
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            return local_ip
        except:
            return ""

    def resolve_pin(self, pin: str, timeout: int = 3) -> str:
        """
        Tenta resolver um PIN para um endereço IP broadcasting
        Retorna o IP se encontrado, ou string vazia
        """
        if not pin or len(pin) != 6:
            return ""
            
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.settimeout(timeout)
            
            msg = f"WHO_HAS_PIN {pin}"
            # Broadcast para 255.255.255.255
            sock.sendto(msg.encode(), ('<broadcast>', 48011))
            
            # Esperar resposta
            try:
                data, addr = sock.recvfrom(1024)
                response = data.decode()
                if response.startswith("I_HAVE_PIN"):
                    # addr[0] é o IP do host
                    return addr[0]
            except socket.timeout:
                pass
            finally:
                sock.close()
        except Exception as e:
            self.logger.warning(f"Erro ao resolver PIN: {e}")
            
        return ""

    def start_pin_listener(self, valid_pin: str, host_name: str):
        """
        Inicia listener para responder a queries de PIN
        Retorna função para parar o listener
        """
        import threading
        
        running = True
        sock = None
        
        def listener_thread():
            nonlocal sock
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.bind(('', 48011))
                
                while running:
                    try:
                        data, addr = sock.recvfrom(1024)
                        msg = data.decode().strip()
                        
                        if msg == f"WHO_HAS_PIN {valid_pin}":
                            response = f"I_HAVE_PIN {host_name}"
                            sock.sendto(response.encode(), addr)
                    except OSError:
                        pass # Socket closed
                    except Exception as e:
                        print(f"Erro no listener PIN: {e}")
                        
            except Exception as e:
                print(f"Erro ao iniciar listener PIN: {e}")
            finally:
                if sock:
                    sock.close()

        t = threading.Thread(target=listener_thread, daemon=True)
        t.start()
        
        def stop():
            nonlocal running, sock
            running = False
            if sock:
                sock.close()
                
        return stop

    def get_global_ipv4(self) -> str:
        """Obtém IPv4 global"""
        try:
            # Tentar ipinfo.io com flag -4 explícita
            cmd = ['curl', '-s', '-4', '--connect-timeout', '3', 'ipinfo.io/ip']
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
                
            # Fallback para checkip.amazonaws.com
            cmd = ['curl', '-s', '-4', '--connect-timeout', '3', 'checkip.amazonaws.com']
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
        except Exception:
            pass
        return "Não disponível"
        
    def get_global_ipv6(self) -> str:
        """Obtém IPv6 global"""
        try:
            # Tentar ifconfig.me com flag -6 explícita
            cmd = ['curl', '-s', '-6', '--connect-timeout', '3', 'ifconfig.me']
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
                
            # Fallback para icanhazip.com
            cmd = ['curl', '-s', '-6', '--connect-timeout', '3', 'icanhazip.com']
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
        except Exception:
            pass
        return "Não disponível"
