"""
Widget de monitoramento de performance
"""

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, Adw, GLib
import time

class PerformanceMonitor(Gtk.Box):
    """Widget para mostrar estatísticas de performance"""
    
    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=24)
        
        self.add_css_class('card')
        self.set_margin_top(12)
        self.set_margin_bottom(12)
        self.set_margin_start(12)
        self.set_margin_end(12)
        
        self.latency = 0
        self.fps = 0
        self.bandwidth = 0
        
        self.setup_ui()
        
        # Timer para atualização (a cada 1 segundo)
        self.update_timer = None
        
    def setup_ui(self):
        """Configura interface do monitor"""
        # Latência
        latency_box = self.create_stat_box(
            'network-idle-symbolic',
            'Latência',
            '-- ms',
            'latency_value'
        )
        
        # FPS
        fps_box = self.create_stat_box(
            'video-display-symbolic',
            'FPS',
            '-- fps',
            'fps_value'
        )
        
        # Bandwidth
        bandwidth_box = self.create_stat_box(
            'network-transmit-receive-symbolic',
            'Banda',
            '-- Mbps',
            'bandwidth_value'
        )
        
        self.append(latency_box)
        self.append(fps_box)
        self.append(bandwidth_box)
        
    def create_stat_box(self, icon_name, label_text, value_text, value_id):
        """Cria caixa para uma estatística"""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.set_hexpand(True)
        box.set_halign(Gtk.Align.CENTER)
        
        # Ícone
        icon = Gtk.Image.new_from_icon_name(icon_name)
        icon.set_pixel_size(32)
        icon.add_css_class('dim-label')
        
        # Label
        label = Gtk.Label(label=label_text)
        label.add_css_class('dim-label')
        
        # Valor
        value = Gtk.Label(label=value_text)
        value.add_css_class('title-2')
        value.set_name(value_id)
        setattr(self, value_id, value)
        
        box.append(icon)
        box.append(label)
        box.append(value)
        
        return box
        
    def update_stats(self, latency=None, fps=None, bandwidth=None):
        """Atualiza estatísticas"""
        if latency is not None:
            self.latency = latency
            self.latency_value.set_text(f'{latency:.0f} ms')
            
            # Mudar cor baseado na latência
            if latency < 50:
                self.latency_value.remove_css_class('warning')
                self.latency_value.remove_css_class('error')
                self.latency_value.add_css_class('success')
            elif latency < 100:
                self.latency_value.remove_css_class('success')
                self.latency_value.remove_css_class('error')
                self.latency_value.add_css_class('warning')
            else:
                self.latency_value.remove_css_class('success')
                self.latency_value.remove_css_class('warning')
                self.latency_value.add_css_class('error')
                
        if fps is not None:
            self.fps = fps
            self.fps_value.set_text(f'{fps:.0f} fps')
            
            # Mudar cor baseado no FPS
            if fps >= 55:
                self.fps_value.remove_css_class('warning')
                self.fps_value.remove_css_class('error')
                self.fps_value.add_css_class('success')
            elif fps >= 30:
                self.fps_value.remove_css_class('success')
                self.fps_value.remove_css_class('error')
                self.fps_value.add_css_class('warning')
            else:
                self.fps_value.remove_css_class('success')
                self.fps_value.remove_css_class('warning')
                self.fps_value.add_css_class('error')
                
        if bandwidth is not None:
            self.bandwidth = bandwidth
            self.bandwidth_value.set_text(f'{bandwidth:.1f} Mbps')
            
    def start_monitoring(self):
        """Inicia monitoramento contínuo"""
        if self.update_timer:
            return  # Já está monitorando
            
        def update_callback():
            # TODO: Coletar estatísticas reais do Sunshine/Moonlight
            # Por enquanto, simula valores
            import random
            
            # Simular latência (10-150ms)
            latency = random.uniform(10, 150)
            
            # Simular FPS (30-60)
            fps = random.uniform(30, 60)
            
            # Simular bandwidth (5-30 Mbps)
            bandwidth = random.uniform(5, 30)
            
            self.update_stats(latency, fps, bandwidth)
            
            return GLib.SOURCE_CONTINUE  # Continuar timer
            
        # Atualizar a cada 1 segundo (1000ms)
        self.update_timer = GLib.timeout_add(1000, update_callback)
        
    def stop_monitoring(self):
        """Para monitoramento"""
        if self.update_timer:
            GLib.source_remove(self.update_timer)
            self.update_timer = None
            
        # Resetar valores
        self.latency_value.set_text('-- ms')
        self.fps_value.set_text('-- fps')
        self.bandwidth_value.set_text('-- Mbps')
        
        # Remover classes de cor
        for widget in [self.latency_value, self.fps_value, self.bandwidth_value]:
            widget.remove_css_class('success')
            widget.remove_css_class('warning')
            widget.remove_css_class('error')
