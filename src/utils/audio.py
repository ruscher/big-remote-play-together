import subprocess
from typing import List, Dict, Optional

class AudioManager:
    """
    Gerenciador de Áudio simplificado e robusto para o Big Remote Play Together.
    Foca em duas configurações principais:
    1. Host Only (Padrão)
    2. Host + Guest (Streaming Ativo)
    """

    def is_virtual(self, name: str, description: str = "") -> bool:
        """Verifica se um sink é virtual"""
        n = name.lower()
        d = description.lower()
        # Filtra nomes de sinks conhecidamente virtuais ou nossos
        virtual_patterns = ['sunshine', 'null-sink', 'module-combine-sink', 'combined', 'easyeffects']
        return any(x in n or x in d for x in virtual_patterns) or n.endswith('.monitor')

    def get_passive_sinks(self) -> List[Dict[str, str]]:
        """
        Lista dispositivos de saída física (Hardware).
        Filtra agressivamente sinks virtuais para evitar loops.
        """
        sinks = []
        try:
            # Pegar sinks com pactl
            res = subprocess.run(['pactl', 'list', 'sinks'], capture_output=True, text=True)
            if res.returncode != 0: return []
            
            current = {}
            for line in res.stdout.splitlines():
                line = line.strip()
                if line.startswith('Sink #'):
                    if current: sinks.append(current)
                    current = {'id': line.split('#')[1]}
                elif line.startswith('Name:'):
                    current['name'] = line.split(':', 1)[1].strip()
                elif line.startswith('Description:'):
                    current['description'] = line.split(':', 1)[1].strip()
            if current: sinks.append(current)
            
            # Filtrar
            valid_sinks = []
            for s in sinks:
                if not self.is_virtual(s.get('name', ''), s.get('description', '')):
                    valid_sinks.append(s)
            
            return valid_sinks
        except Exception as e:
            print(f"Erro ao listar sinks: {e}")
            return []

    def get_default_sink(self) -> Optional[str]:
        try:
            res = subprocess.run(['pactl', 'get-default-sink'], capture_output=True, text=True)
            return res.stdout.strip() if res.returncode == 0 else None
        except: return None

    def set_default_sink(self, sink_name: str):
        try:
            subprocess.run(['pactl', 'set-default-sink', sink_name], check=False)
        except: pass

    def enable_streaming_audio(self, host_sink: str) -> bool:
        """
        Ativa o modo Streaming (Host + Guest) usando estratégia RADICAL: Combine Sink.
        Em vez de Null Sink + Loopback (que falha e muta), usamos um Combine Sink.
        SunshineGameSink -> [Hardware Sink]
        O Sunshine captura do SunshineGameSink.monitor.
        O Host escuta porque o Hardware Sink é um slave.
        """
        # Se o host_sink for virtual ou nulo, tenta achar o primeiro hardware real
        if not host_sink or self.is_virtual(host_sink):
            hardware_devices = self.get_passive_sinks()
            if hardware_devices:
                host_sink = hardware_devices[0]['name']
                print(f"Host sink era virtual ou nulo, selecionado fallback hardware: {host_sink}")
            else:
                print("ERRO: Nenhum dispositivo de hardware encontrado para áudio.")
                return False

        # Limpar antes de criar para evitar duplicatas
        self.disable_streaming_audio(None) 
        
        try:
            print(f"Habilitando Áudio Isolado (Radical) -> Combine Sink 'SunshineGameSink' -> Slave: {host_sink}")
            
            # 1. Combine Sink 'SunshineGameSink'
            # Isso cria uma saída virtual que repassa o áudio para o host_sink (Hardware)
            # E disponibiliza um .monitor para o Sunshine gravar.
            subprocess.run([
                'pactl', 'load-module', 'module-combine-sink',
                'sink_name=SunshineGameSink',
                f'slaves={host_sink}',
                'sink_properties=device.description=SunshineGameSink'
            ], check=True)
            
            # 2. Pequeno delay e garantir volumes
            import time; time.sleep(0.5)
            subprocess.run(['pactl', 'set-sink-mute', 'SunshineGameSink', '0'], check=False)
            subprocess.run(['pactl', 'set-sink-volume', 'SunshineGameSink', '100%'], check=False)

            # 3. Definir SunshineGameSink como padrão
            self.set_default_sink("SunshineGameSink")

            # 4. Verificar criação
            time.sleep(0.2)
            sinks = subprocess.run(['pactl', 'list', 'short', 'sinks'], capture_output=True, text=True).stdout
            if 'SunshineGameSink' not in sinks:
                print("ERRO CRÍTICO: SunshineGameSink (Combine) não foi criado!")
                self.disable_streaming_audio(host_sink)
                return False
                
            print(f"Áudio Radical Ativado: SunshineGameSink combinando para {host_sink}")
            return True
            
        except Exception as e:
            print(f"Falha ao ativar streaming de áudio (Combine): {e}")
            self.disable_streaming_audio(host_sink) 
            return False

    def get_sink_monitor_source(self, sink_name: str) -> Optional[str]:
        """
        Retorna o nome correto da fonte de monitoramento para um sink.
        Isso evita problemas onde o nome do monitor não é simplesmente .monitor
        """
        try:
            # pactl list sources short returns: ID Name ...
            res = subprocess.run(['pactl', 'list', 'short', 'sources'], capture_output=True, text=True)
            candidate = f"{sink_name}.monitor"
            
            for line in res.stdout.splitlines():
                parts = line.split()
                if len(parts) > 1:
                    source_name = parts[1]
                    # Exata correspondência ou monitor padrão
                    if source_name == candidate:
                        return source_name
            
            # Se não encontrou exato, tenta achar um que contenha o nome do sink e 'monitor'
            # Isso é arriscado, mas melhor que falhar
            for line in res.stdout.splitlines():
                 parts = line.split()
                 if len(parts) > 1:
                     nm = parts[1]
                     if sink_name in nm and 'monitor' in nm:
                         return nm
                         
            return candidate # Fallback
        except:
             return f"{sink_name}.monitor"

    def disable_streaming_audio(self, host_sink: str):
        """
        Desativa modo Streaming.
        Restaura o sink padrão e remove módulos virtuais.
        """
        # 1. Restaurar padrão (se não for virtual)
        if host_sink and not self.is_virtual(host_sink):
            self.set_default_sink(host_sink)
            
        # 2. Descarregar módulos específicos
        try:
            res = subprocess.run(['pactl', 'list', 'short', 'modules'], capture_output=True, text=True)
            if res.returncode == 0:
                for line in res.stdout.splitlines():
                    # Critérios de busca para descarregar:
                    # - Módulo de null-sink com nosso nome (GameSink)
                    # - Loopbacks nossos
                    if 'sink_name=SunshineGameSink' in line or \
                       'sink_name=SunshineStereo' in line or \
                       'sink_name=SunshineHybrid' in line or \
                       'source=SunshineGameSink.monitor' in line or \
                       'SunshineLoopback' in line:
                        
                        mod_id = line.split()[0]
                        print(f"Limpando módulo de áudio: {mod_id}")
                        subprocess.run(['pactl', 'unload-module', mod_id], check=False)
        except Exception as e:
            print(f"Erro ao limpar módulos: {e}")

    def get_apps(self) -> List[Dict]:
        """
        Lista aplicativos que estão tocando áudio (Sink Inputs).
        """
        apps = []
        try:
            # Mapeamento ID -> Nome do Sink para referência
            sinks_map = {}
            res_s = subprocess.run(['pactl', 'list', 'short', 'sinks'], capture_output=True, text=True)
            for l in res_s.stdout.splitlines():
                p = l.split()
                if len(p) > 1: sinks_map[p[0]] = p[1]

            res = subprocess.run(['pactl', 'list', 'sink-inputs'], capture_output=True, text=True)
            current = {}
            
            for line in res.stdout.splitlines():
                line = line.strip()
                if line.startswith('Sink Input #'):
                    if current: apps.append(current)
                    current = {'id': line.split('#')[1], 'name': 'Desconhecido', 'icon': 'audio-x-generic-symbolic'}
                elif line.startswith('Sink:'):
                    sid = line.split(':')[1].strip()
                    current['sink_id'] = sid
                    current['sink_name'] = sinks_map.get(sid, sid)
                elif 'application.name = ' in line:
                    val = line.split('=', 1)[1].strip().strip('"')
                    if val: current['name'] = val
                elif 'application.icon_name = ' in line:
                    val = line.split('=', 1)[1].strip().strip('"')
                    if val: current['icon'] = val
                elif 'media.name = ' in line and current.get('name') == 'Desconhecido':
                    val = line.split('=', 1)[1].strip().strip('"')
                    if val: current['name'] = val
                    
            if current: apps.append(current)
            
            # Filter internal streams if necessary
            # Ignorar streams internos do PulseAudio/Pipewire que causam loops se movidos
            def is_internal(name):
                n = name.lower()
                return any(x in n for x in ['sunshine', 'monitor', 'loopback', 'simultaneous', 'combine', 'output to'])
            
            return [a for a in apps if not is_internal(a.get('name', ''))]
            
        except Exception: 
            return []

    def move_app(self, app_id: str, sink_name: str):
        try:
            subprocess.run(['pactl', 'move-sink-input', str(app_id), sink_name], check=False)
        except: pass

    def cleanup(self):
        """Limpia tudo e tenta restaurar o som original"""
        # Tenta achar um hardware real para restaurar
        hardware = self.get_passive_sinks()
        target = hardware[0]['name'] if hardware else None
        self.disable_streaming_audio(target)
