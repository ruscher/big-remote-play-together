
import subprocess
import re
from typing import List, Dict, Tuple, Optional

class AudioManager:
    """Gerenciador de Áudio (PulseAudio/PipeWire)"""
    
    def __init__(self):
        self.active_modules = [] # [(id, type)]
        
    def get_output_devices(self) -> List[Dict[str, str]]:
        """Lista dispositivos de saída (Sinks)"""
        devices = []
        try:
            # pactl list sinks short: id name driver sample_spec state
            # Mas names podem ser longos, melhor usar formato completo ou json se disponivel (pactl -f json list sinks é moderno)
            # Vamos tentar output normal e regex para compatibilidade
            res = subprocess.run(['pactl', 'list', 'sinks'], capture_output=True, text=True)
            if res.returncode != 0:
                print("Erro ao listar sinks")
                return []
                
            # Parse simples
            current_device = {}
            for line in res.stdout.splitlines():
                line = line.strip()
                if line.startswith('Sink #'):
                    if current_device:
                        devices.append(current_device)
                    current_device = {'id': line.split('#')[1]}
                elif line.startswith('Name:'):
                    current_device['name'] = line.split(':', 1)[1].strip()
                elif line.startswith('Description:'):
                    current_device['description'] = line.split(':', 1)[1].strip()
                    
            if current_device:
                devices.append(current_device)
                
            return devices
        except Exception as e:
            print(f"Erro ao obter devices: {e}")
            return []
            
    def enable_dual_audio(self, target_sink_name: str) -> bool:
        """
        Cria sink virtual GameSink e loopback para o target
        Retorna True se sucesso
        """
        try:
            # 1. Check if already exists to avoid duplicates
            if self.is_module_loaded("sink_name=GameSink"):
                 print("GameSink já existe.")
                 # Remove antogs se necessário ou reutiliza? Melhor limpar.
                 self.cleanup()
            
            # 2. Add Null Sink
            print("Criando GameSink...")
            cmd = [
                'pactl', 'load-module', 'module-null-sink',
                'sink_name=GameSink',
                'sink_properties=device.description=GameSink'
            ]
            res = subprocess.run(cmd, capture_output=True, text=True)
            if res.returncode != 0:
                print(f"Falha ao criar sink: {res.stderr}")
                return False
            sink_mod_id = res.stdout.strip()
            self.active_modules.append(sink_mod_id)
            
            # 3. Add Loopback
            print(f"Criando loopback para {target_sink_name}...")
            cmd = [
                'pactl', 'load-module', 'module-loopback',
                'source=GameSink.monitor',
                f'sink={target_sink_name}'
            ]
            res = subprocess.run(cmd, capture_output=True, text=True)
            if res.returncode != 0:
                print(f"Falha ao criar loopback: {res.stderr}")
                # Rollback
                self.cleanup()
                return False
            loopback_mod_id = res.stdout.strip()
            self.active_modules.append(loopback_mod_id)
            
            return True
            
        except Exception as e:
            print(f"Erro no setup dual audio: {e}")
            self.cleanup()
            return False
            
    def cleanup(self):
        """Remove módulos criados"""
        for mod_id in reversed(self.active_modules):
            try:
                print(f"Removendo módulo {mod_id}...")
                subprocess.run(['pactl', 'unload-module', mod_id], capture_output=True)
            except Exception as e:
                print(f"Erro ao remover módulo {mod_id}: {e}")
        self.active_modules = []
        
    def is_module_loaded(self, grep_term: str) -> bool:
        try:
            res = subprocess.run(['pactl', 'list', 'short', 'modules'], capture_output=True, text=True)
            return grep_term in res.stdout
        except:
            return False
