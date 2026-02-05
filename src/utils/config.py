"""
Gerenciamento de configuração do aplicativo
"""

import json
import os
from pathlib import Path

class Config:
    """Gerenciador de configuração"""
    
    def __init__(self):
        self.config_dir = Path.home() / '.config' / 'big-remoteplay'
        self.config_file = self.config_dir / 'config.json'
        
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        self.config = self.load()
        
    def load(self):
        """Carrega configuração"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Erro ao carregar configuração: {e}")
                return self.default_config()
        else:
            return self.default_config()
            
    def save(self):
        """Salva configuração"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            print(f"Erro ao salvar configuração: {e}")
            
    def get(self, key, default=None):
        """Obtém valor de configuração"""
        return self.config.get(key, default)
        
    def set(self, key, value):
        """Define valor de configuração"""
        self.config[key] = value
        self.save()
        
    def default_config(self):
        """Retorna configuração padrão"""
        return {
            'theme': 'auto',
            'network': {
                'upnp': True,
                'ipv6': True,
                'discovery': True,
                'sunshine_port': 47989,
                'streaming_port': 48010,
            },
            'host': {
                'max_players': 2,
                'quality': 'high',
                'audio': True,
                'input_sharing': True,
            },
            'guest': {
                'quality': 'auto',
                'audio': True,
                'hw_decode': True,
                'fullscreen': False,
            },
            'advanced': {
                'verbose_logging': False,
                'auto_start_sunshine': False,
            }
        }
