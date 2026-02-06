"""
Verificação de componentes do sistema
"""

import subprocess
import shutil
from typing import Tuple

class SystemCheck:
    """Verificador de componentes do sistema"""
    
    def __init__(self):
        pass
        
    def has_sunshine(self) -> bool:
        """Verifica se Sunshine está instalado"""
        return shutil.which('sunshine') is not None
        
    def has_moonlight(self) -> bool:
        """Verifica se Moonlight está instalado"""
        # Moonlight pode ter diferentes nomes
        return (
            shutil.which('moonlight') is not None or
            shutil.which('moonlight-qt') is not None
        )
        
    def has_avahi(self) -> bool:
        """Verifica se Avahi está instalado"""
        return shutil.which('avahi-browse') is not None
        
    def has_docker(self) -> bool:
        """Verifica se Docker está instalado"""
        return shutil.which('docker') is not None
        
    def check_all(self) -> dict:
        """Verifica todos os componentes"""
        return {
            'sunshine': self.has_sunshine(),
            'moonlight': self.has_moonlight(),
            'avahi': self.has_avahi(),
            'docker': self.has_docker(),
        }
    
    def is_sunshine_running(self) -> bool:
        """Verifica se o processo Sunshine está rodando"""
        try:
            result = subprocess.run(
                ['pgrep', '-x', 'sunshine'],
                capture_output=True,
                timeout=2
            )
            return result.returncode == 0
        except:
            return False
    
    def is_moonlight_running(self) -> bool:
        """Verifica se o processo Moonlight está rodando (ignora zumbis)"""
        try:
            for process_name in ['moonlight', 'moonlight-qt']:
                # Pega os PIDs
                result = subprocess.run(
                    ['pgrep', '-x', process_name],
                    capture_output=True,
                    text=True, # Importante para ler a saída como texto
                    timeout=2
                )
                
                if result.returncode == 0 and result.stdout:
                    pids = result.stdout.strip().split()
                    for pid in pids:
                        # Verifica o estado do processo
                        try:
                            state_check = subprocess.run(
                                ['ps', '-o', 'state=', '-p', pid],
                                capture_output=True,
                                text=True,
                                timeout=1
                            )
                            if state_check.returncode == 0:
                                state = state_check.stdout.strip()
                                # Se estado não for Z (Zombie) ou T (Stopped), considera rodando
                                if state and state not in ['Z', 'T', 'Z+']:
                                    return True
                        except:
                            continue
                            
            return False
        except:
            return False

        
    def get_sunshine_version(self) -> str:
        """Obtém versão do Sunshine"""
        try:
            result = subprocess.run(
                ['sunshine', '--version'],
                capture_output=True,
                text=True,
                timeout=2
            )
            
            if result.returncode == 0:
                return result.stdout.strip()
            else:
                return "Desconhecida"
                
        except:
            return "Desconhecida"
            
    def get_moonlight_version(self) -> str:
        """Obtém versão do Moonlight"""
        try:
            # Tentar diferentes variantes
            for cmd in ['moonlight-qt', 'moonlight']:
                result = subprocess.run(
                    [cmd, '--version'],
                    capture_output=True,
                    text=True,
                    timeout=2
                )
                
                if result.returncode == 0:
                    return result.stdout.strip()
                    
            return "Desconhecida"
            
        except:
            return "Desconhecida"
            
    def check_firewall(self) -> Tuple[bool, str]:
        """
        Verifica status do firewall
        Retorna (tem_firewall, tipo)
        """
        if shutil.which('ufw'):
            try:
                result = subprocess.run(
                    ['ufw', 'status'],
                    capture_output=True,
                    text=True,
                    timeout=2
                )
                
                if result.returncode == 0:
                    active = 'Status: active' in result.stdout
                    return (active, 'ufw')
                    
            except:
                pass
                
        if shutil.which('iptables'):
            return (True, 'iptables')
            
        return (False, 'none')
        
    def check_network_connectivity(self) -> bool:
        """Verifica conectividade de rede"""
        try:
            # Ping Google DNS
            result = subprocess.run(
                ['ping', '-c', '1', '-W', '2', '8.8.8.8'],
                capture_output=True,
                timeout=3
            )
            
            return result.returncode == 0
            
        except:
            return False
