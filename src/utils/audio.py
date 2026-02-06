
import subprocess
import re
from typing import List, Dict, Tuple, Optional

class AudioManager:
    """Gerenciador de Áudio (PulseAudio/PipeWire)"""
    
    def __init__(self):
        self.active_modules = []
        self.original_sink = None
        
    def get_output_devices(self) -> List[Dict[str, str]]:
        """Lista dispositivos de saída (Sinks)"""
        devices = []
        try:
            res = subprocess.run(['pactl', 'list', 'sinks'], capture_output=True, text=True)
            if res.returncode != 0: return []
            current_device = {}
            for line in res.stdout.splitlines():
                line = line.strip()
                if line.startswith('Sink #'):
                    if current_device: devices.append(current_device)
                    current_device = {'id': line.split('#')[1]}
                elif line.startswith('Name:'):
                    current_device['name'] = line.split(':', 1)[1].strip()
                elif line.startswith('Description:'):
                    current_device['description'] = line.split(':', 1)[1].strip()
            if current_device: devices.append(current_device)
            return devices
        except: return []

    def get_default_sink(self) -> Optional[str]:
        try:
            res = subprocess.run(['pactl', 'get-default-sink'], capture_output=True, text=True)
            return res.stdout.strip() if res.returncode == 0 else None
        except: return None

    def set_default_sink(self, name: str):
        try: subprocess.run(['pactl', 'set-default-sink', name])
        except: pass

    def cleanup_legacy(self):
        """Remove sinks antigos criados por versões anteriores"""
        try:
            res = subprocess.run(['pactl', 'list', 'short', 'modules'], capture_output=True, text=True)
            for line in res.stdout.splitlines():
                if 'sink_name=GameSink' in line or 'sink_name=Sunshine-Audio' in line:
                    mod_id = line.split()[0]
                    subprocess.run(['pactl', 'unload-module', mod_id], capture_output=True)
        except: pass

    def save_state(self):
        """Salva o estado atual do áudio (sink padrão) tentando garantir um dispositivo real"""
        current = self.get_default_sink()
        
        def is_virtual(name):
             name_lower = name.lower()
             return "sunshine" in name_lower or "virtual" in name_lower or "null" in name_lower or "easyeffects" in name_lower

        if current and not is_virtual(current):
            self.original_sink = current
        else:
            # Fallback: Find first hardware device
            print("Default sink seems virtual or invalid, searching for hardware sink...")
            for dev in self.get_output_devices():
                name = dev.get('name', '')
                if name and not is_virtual(name):
                    self.original_sink = name
                    break
        
        print(f"Estado de áudio salvo para restauração: {self.original_sink}")

    def setup_sunshine_audio(self, dual_output: Optional[str] = None):
        """Configura áudio usando os sinks nativos do Sunshine"""
        self.cleanup() # Limpa modulos anteriores desta sessão
        self.cleanup_legacy() # Limpa lixo antigo
        
        # Se não salvou estado explicitamente antes, tenta salvar agora
        if not self.original_sink: self.save_state()
        
        # Tenta encontrar o sink do Sunshine (Stereo preferido)
        sunshine_sink = "sink-sunshine-stereo"
        
        try:
            # Se Dual Audio, usamos module-combine-sink em vez de loopback
            # O combine-sink divide o áudio na saída, evitando o "ciclo de gravação" que causa microfonia
            if dual_output:
                cmd = [
                    'pactl', 'load-module', 'module-combine-sink',
                    'sink_name=Sunshine-Hybrid',
                    f'slaves={sunshine_sink},{dual_output}',
                    'sink_properties=device.description=Sunshine-Híbrido'
                ]
                res = subprocess.run(cmd, capture_output=True, text=True)
                if res.returncode == 0:
                    self.active_modules.append(res.stdout.strip())
                    self.set_default_sink('Sunshine-Hybrid')
                    return

            # Se não tem dual audio, ou se falhar, joga direto pro Sunshine
            self.set_default_sink(sunshine_sink)
                
        except: pass
            
    def cleanup(self):
        """Remove módulos de loopback e restaura sink padrão"""
        if self.original_sink:
            self.set_default_sink(self.original_sink)
            self.original_sink = None
            
        for mod_id in reversed(self.active_modules):
            try: subprocess.run(['pactl', 'unload-module', mod_id], capture_output=True)
            except: pass
        self.active_modules = []
