
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
        """Configura áudio criando um Null Sink e um Combine Sink para áudio Híbrido"""
        self.cleanup() # Limpa modulos anteriores desta sessão
        self.cleanup_legacy() # Limpa lixo antigo
        
        # Se não salvou estado explicitamente antes, tenta salvar agora
        if not self.original_sink: self.save_state()
        
        # 1. Cria um Null Sink que servirá como destino "puro" para captura (se desejado)
        # e como um dos destinos do áudio compartilhado.
        sunshine_null_sink = "Sunshine-Stereo"
        try:
            cmd = [
                'pactl', 'load-module', 'module-null-sink',
                f'sink_name={sunshine_null_sink}',
                'sink_properties=device.description=Sunshine-Input'
            ]
            res = subprocess.run(cmd, capture_output=True, text=True)
            if res.returncode == 0:
                self.active_modules.append(res.stdout.strip())
            else:
                print(f"Erro ao criar null sink: {res.stderr}")
                # Fallback? Se falhar null sink, sistema fica instavel.
                
        except Exception as e:
            print(f"Exceção criando null sink: {e}")

        # Nome do sink final que será o padrão
        target_default_sink = sunshine_null_sink
        
        # 2. Se Dual Audio, cria o Combine Sink
        if dual_output:
            hybrid_name = "Sunshine-Hybrid"
            # Combine o Null Sink (para isolamento) com a Saída Física (para ouvir localmente)
            try:
                cmd = [
                    'pactl', 'load-module', 'module-combine-sink',
                    f'sink_name={hybrid_name}',
                    f'slaves={sunshine_null_sink},{dual_output}',
                    'sink_properties=device.description=Sunshine-Híbrido'
                ]
                res = subprocess.run(cmd, capture_output=True, text=True)
                if res.returncode == 0:
                    self.active_modules.append(res.stdout.strip())
                    target_default_sink = hybrid_name
                else:
                    print(f"Erro ao criar combine sink: {res.stderr}")
            except Exception as e:
                print(f"Exceção criando combine sink: {e}")

        # 3. Define como padrão
        self.set_default_sink(target_default_sink)

            
    def get_audio_applications(self) -> List[Dict]:
        """Lista aplicativos reproduzindo áudio"""
        apps = []
        try:
            # First, get sink names map
            sinks = {}
            res_sinks = subprocess.run(['pactl', 'list', 'short', 'sinks'], capture_output=True, text=True)
            for line in res_sinks.stdout.splitlines():
                parts = line.split('\t')
                if len(parts) >= 2:
                    sinks[parts[0]] = parts[1] # ID -> Name

            # List inputs
            res = subprocess.run(['pactl', 'list', 'sink-inputs'], capture_output=True, text=True)
            current_app = {}
            
            for line in res.stdout.splitlines():
                line = line.strip()
                if line.startswith('Sink Input #'):
                    if current_app: apps.append(current_app)
                    current_app = {'id': line.split('#')[1], 'name': 'Unknown', 'icon': 'audio-x-generic-symbolic'}
                elif line.startswith('Sink:'):
                    sink_id = line.split(':')[1].strip()
                    current_app['sink_index'] = sink_id
                    current_app['sink_name'] = sinks.get(sink_id, "")
                elif 'application.name = ' in line:
                    current_app['name'] = line.split('=')[1].strip().strip('"')
                elif 'application.icon_name = ' in line:
                    current_app['icon'] = line.split('=')[1].strip().strip('"')
                elif 'media.name = ' in line and current_app.get('name') == 'Unknown':
                    current_app['name'] = line.split('=')[1].strip().strip('"')
                    
            if current_app: apps.append(current_app)
            
            # Filter out non-apps (like monitors/loopbacks if they appear as inputs)
            return [a for a in apps if a.get('name') not in ['Sunshine', 'Simultaneous output to', 'Unknown']]
        except: return []

    def move_app_to_sink(self, app_id: str, sink_name: str):
        try:
            subprocess.run(['pactl', 'move-sink-input', str(app_id), sink_name], capture_output=True)
            return True
        except: return False

    def cleanup(self):
        """Remove módulos de loopback e restaura sink padrão"""
        if self.original_sink:
            self.set_default_sink(self.original_sink)
            self.original_sink = None
            
        for mod_id in reversed(self.active_modules):
            try: subprocess.run(['pactl', 'unload-module', mod_id], capture_output=True)
            except: pass
        self.active_modules = []
