"""
Sistema de logging
"""

import logging
import os
from pathlib import Path
from datetime import datetime

class Logger:
    """Gerenciador de logs"""
    
    def __init__(self, name='big-remoteplay'):
        self.name = name
        
        # Diretório de logs
        self.log_dir = Path.home() / '.config' / 'big-remoteplay' / 'logs'
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Arquivo de log
        log_file = self.log_dir / f'{name}_{datetime.now().strftime("%Y%m%d")}.log'
        
        # Configurar logger
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
        
        # File handler
        fh = logging.FileHandler(log_file)
        fh.setLevel(logging.DEBUG)
        
        # Console handler
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)
        
        self.logger.addHandler(fh)
        self.logger.addHandler(ch)
        
    def info(self, message):
        """Log info"""
        self.logger.info(message)
        
    def warning(self, message):
        """Log warning"""
        self.logger.warning(message)
        
    def error(self, message):
        """Log error"""
        self.logger.error(message)
        
    def debug(self, message):
        """Log debug"""
        self.logger.debug(message)
        
    def set_verbose(self, enabled):
        """Ativa/desativa modo verbose"""
        if enabled:
            self.logger.setLevel(logging.DEBUG)
        else:
            self.logger.setLevel(logging.INFO)
