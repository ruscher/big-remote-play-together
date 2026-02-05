import os
import json
import re
from pathlib import Path

class GameDetector:
    """Detecta jogos instalados em diversas plataformas"""
    
    def __init__(self):
        self.home = Path.home()
        
    def detect_all(self):
        """Detecta todos os jogos suportados"""
        games = []
        games.extend(self.detect_steam())
        games.extend(self.detect_lutris())
        games.extend(self.detect_heroic())
        return sorted(games, key=lambda x: x['name'])

    def detect_steam(self):
        """Detecta jogos da Steam"""
        games = []
        steam_root = self.home / '.local/share/Steam'
        if not steam_root.exists():
            steam_root = self.home / '.steam/steam'
            
        if not steam_root.exists():
            return []
            
        library_folders = [steam_root / 'steamapps']
        
        # Tentar ler libraryfolders.vdf para encontrar outras bibliotecas
        vdf_path = steam_root / 'steamapps' / 'libraryfolders.vdf'
        if vdf_path.exists():
            try:
                content = vdf_path.read_text()
                # Extração simples via regex
                paths = re.findall(r'"path"\s+"([^"]+)"', content)
                for p in paths:
                    lib_path = Path(p) / 'steamapps'
                    # Evitar duplicatas
                    if lib_path.resolve() != (steam_root / 'steamapps').resolve():
                        library_folders.append(lib_path)
            except Exception as e:
                print(f"Erro ao ler biblioteca Steam: {e}")
                pass
                
        for lib in library_folders:
            if not lib.exists(): continue
            for acf in lib.glob('appmanifest_*.acf'):
                try:
                    content = acf.read_text()
                    name_match = re.search(r'"name"\s+"([^"]+)"', content)
                    id_match = re.search(r'"appid"\s+"(\d+)"', content)
                    
                    if name_match and id_match:
                        name = name_match.group(1)
                        # Filtrar "Steamworks Common Redistributables" e "Proton"
                        if "Steamworks" in name or "Proton" in name or "Runtime" in name:
                            continue
                            
                        games.append({
                            'name': name,
                            'id': id_match.group(1),
                            'platform': 'Steam',
                            'cmd': f'steam steam://rungameid/{id_match.group(1)}',
                            'icon': 'steam' # Placeholder
                        })
                except:
                    pass
        return games

    def detect_lutris(self):
        """Detecta jogos do Lutris via arquivos YAML de configuração"""
        games = []
        games_dir = self.home / '.config/lutris/games'
        
        if games_dir.exists():
            for p in games_dir.glob('*.yml'):
                try:
                    content = p.read_text()
                    name = None
                    slug = p.stem
                    
                    # Parser simples de YAML linewise
                    for line in content.splitlines():
                        if line.strip().startswith('name:'):
                            name = line.split(':', 1)[1].strip().strip('"\'')
                            break
                    
                    if name:
                        games.append({
                            'name': name,
                            'id': slug,
                            'platform': 'Lutris',
                            'cmd': f'lutris lutris:rungame/{slug}',
                            'icon': 'lutris'
                        })
                except:
                    pass
        return games

    def detect_heroic(self):
        """Detecta jogos do Heroic Launcher"""
        games = []
        
        # Caminhos possíveis para configurações do Heroic
        # v2.5+ structure vs older versions
        heroic_config = self.home / '.config/heroic'
        
        if not heroic_config.exists():
            # Tentar flatpak
            flatpak_config = self.home / '.var/app/com.heroicgameslauncher.hgl/config/heroic'
            if flatpak_config.exists():
                heroic_config = flatpak_config
            else:
                return []

        # Lista de arquivos para verificar
        possible_files = []
        
        # 1. GOG
        possible_files.append(heroic_config / 'gog_store' / 'library.json')
        possible_files.append(heroic_config / 'gog_store' / 'installed.json')
        
        # 2. Epic (Legendary)
        possible_files.append(heroic_config / 'legendary' / 'library.json')
        possible_files.append(heroic_config / 'legendary' / 'installed.json')
        
        # 3. Amazon (Nile)
        possible_files.append(heroic_config / 'nile' / 'library.json')
        possible_files.append(heroic_config / 'nile' / 'installed.json')
        
        # 4. Sideloaded / Other
        possible_files.append(heroic_config / 'GamesConfig' / 'installed.json')
        
        # 5. Store Cache (Newer versions often store game data here)
        store_cache = heroic_config / 'store_cache'
        if store_cache.exists():
             for f in store_cache.glob('*_library.json'):
                 possible_files.append(f)

        processed_ids = set()

        for p in possible_files:
            if p.exists():
                try:
                    content = p.read_text()
                    if not content: continue
                    
                    data = json.loads(content)
                    items = []
                    
                    if isinstance(data, dict):
                        if 'library' in data: 
                             items = data['library']
                        elif 'installed' in data:
                             items = data['installed']
                        else:
                             # Tentar iterar valores se for dicionário de jogos
                             # Ex: {'AppName': {...}, ...}
                             items = data.values()
                    elif isinstance(data, list):
                        items = data
                        
                    for item in items:
                        if not isinstance(item, dict): continue
                        
                        # Tentar extrair info
                        app_name = item.get('app_name') or item.get('appName') or item.get('id')
                        title = item.get('title') or item.get('appName') # Fallback
                        
                        # Verificar se está instalado (alguns jsons mostram biblioteca toda)
                        is_installed = item.get('is_installed', True) # Assumir true se não tiver flag
                        if not is_installed:
                             continue

                        if app_name and title and app_name not in processed_ids:
                             games.append({
                                'name': title,
                                'id': app_name,
                                'platform': 'Heroic',
                                'cmd': f'heroic://launch/{app_name}', # Protocol handler
                                'icon': 'heroic' 
                            })
                             processed_ids.add(app_name)
                             
                except Exception as e:
                    print(f"Erro ao ler Heroic {p}: {e}")
                    pass
                    
        return games
