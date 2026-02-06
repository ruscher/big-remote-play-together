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
        import threading
        def run():
            hosts = []
            try:
                res = subprocess.run(['avahi-browse', '-t', '-r', '-p', '_nvstream._tcp'], capture_output=True, text=True, timeout=5)
                if res.returncode == 0 and res.stdout: hosts = self.parse_avahi_output(res.stdout)
                if not hosts: hosts = self.manual_scan()
            except: hosts = self.manual_scan()
            if callback:
                from gi.repository import GLib
                GLib.idle_add(callback, hosts)
        threading.Thread(target=run, daemon=True).start()
        
    def parse_avahi_output(self, output: str) -> List[Dict]:
        hosts = []; seen = set()
        for line in output.split('\n'):
            p = line.split(';')
            if len(p) > 7 and p[0] == '=':
                ip = p[7]
                if ip not in seen:
                    dip = f"[{ip}]" if ":" in ip and not ip.startswith("[") else ip
                    hosts.append({'name': p[3], 'ip': dip, 'port': int(p[8]), 'status': 'online', 'hostname': p[6]})
                    seen.add(ip)
        return hosts
        
    def manual_scan(self) -> List[Dict]:
        import concurrent.futures
        from concurrent.futures import ThreadPoolExecutor
        hosts = []; local_ip = self.get_local_ip()
        targets = ['127.0.0.1']
        if local_ip:
            subnet = '.'.join(local_ip.split('.')[:-1])
            for i in range(1, 255): targets.append(f"{subnet}.{i}")
        def check(ip):
            if self.check_sunshine_port(ip):
                try: name = socket.gethostbyaddr(ip)[0]
                except: name = ip
                return {'name': name, 'ip': ip, 'port': 47989, 'status': 'online'}
            return None
        with ThreadPoolExecutor(max_workers=50) as ex:
            for r in ex.map(check, targets):
                if r: hosts.append(r)
        return hosts
        
    def check_sunshine_port(self, ip: str, port: int = 47989, timeout: float = 0.5) -> bool:
        try:
            with socket.create_connection((ip, port), timeout=timeout) as s: return True
        except: return False
            
    def get_local_ip(self) -> str:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80)); return s.getsockname()[0]
        except: return ""

    def resolve_pin(self, pin: str, timeout: int = 3) -> str:
        if not pin or len(pin) != 6: return ""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1); s.settimeout(timeout)
                s.sendto(f"WHO_HAS_PIN {pin}".encode(), ('<broadcast>', 48011))
                try:
                    data, addr = s.recvfrom(1024)
                    if data.decode().startswith("I_HAVE_PIN"): return addr[0]
                except: pass
        except: pass
        return ""

    def start_pin_listener(self, pin: str, name: str):
        import threading
        running = [True]
        def run():
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1); s.bind(('', 48011)); s.settimeout(1)
                    while running[0]:
                        try:
                            data, addr = s.recvfrom(1024)
                            if data.decode().strip() == f"WHO_HAS_PIN {pin}": s.sendto(f"I_HAVE_PIN {name}".encode(), addr)
                        except: pass
            except: pass
        threading.Thread(target=run, daemon=True).start()
        return lambda: running.__setitem__(0, False)

    def get_global_ipv4(self) -> str:
        for url in ['ipinfo.io/ip', 'checkip.amazonaws.com']:
            try:
                res = subprocess.run(['curl', '-s', '-4', '--connect-timeout', '3', url], capture_output=True, text=True)
                if res.returncode == 0 and res.stdout.strip(): return res.stdout.strip()
            except: pass
        return "None"
        
    def get_global_ipv6(self) -> str:
        for url in ['ifconfig.me', 'icanhazip.com']:
            try:
                res = subprocess.run(['curl', '-s', '-6', '--connect-timeout', '3', url], capture_output=True, text=True)
                if res.returncode == 0 and res.stdout.strip(): return res.stdout.strip()
            except: pass
        return "None"
