#!/usr/bin/env python3
"""
Performance chart widget using Cairo drawing.
Replaces the old text-based monitor with a modern visual chart.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
import time
import random
import threading

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, GLib

# Import cairo
try:
    import cairo
except ImportError:
    cairo = None

CHART_MAX_HISTORY = 60  # 60 seconds of history

@dataclass
class PerformanceDataPoint:
    """Single data point for performance chart."""
    latency: float       # ms
    fps: float           # frames
    bandwidth: float     # Mbps
    
    # Text representations
    latency_text: str
    fps_text: str
    bandwidth_text: str

class PerformanceChartWidget(Gtk.DrawingArea):
    """
    Modern chart widget for network/video performance.
    """

    def __init__(self) -> None:
        super().__init__()

        self._history: deque[PerformanceDataPoint] = deque(maxlen=CHART_MAX_HISTORY)
        
        # Max values for normalization (auto-adjusting or fixed)
        self.max_latency = 100.0
        self.max_fps = 120.0
        self.max_bandwidth = 50.0

        # Current values for display
        self._cur_latency_text = "--"
        self._cur_fps_text = "--"
        self._cur_bw_text = "--"

        # Hover state
        self._hover_x: float | None = None
        self._hover_index: int | None = None

        # Sizing
        self.set_size_request(300, 160)
        self.set_vexpand(False)
        self.set_hexpand(True)

        # Connect draw signal
        self.set_draw_func(self._on_draw)

        # Mouse tracking
        motion_controller = Gtk.EventControllerMotion()
        motion_controller.connect("motion", self._on_motion)
        motion_controller.connect("leave", self._on_leave)
        self.add_controller(motion_controller)
        
    def add_data_point(self, latency: float, fps: float, bandwidth: float):
        """Add new data point."""
        # Auto-scale max values if exceeded (dynamic scaling)
        if latency > self.max_latency: self.max_latency = latency * 1.2
        if fps > self.max_fps: self.max_fps = fps * 1.2
        if bandwidth > self.max_bandwidth: self.max_bandwidth = bandwidth * 1.2
        
        # Slowly decay max values if current is much lower (optional, maybe skip for stability)
        
        point = PerformanceDataPoint(
            latency=latency,
            fps=fps,
            bandwidth=bandwidth,
            latency_text=f"{latency:.0f} ms",
            fps_text=f"{fps:.0f} FPS",
            bandwidth_text=f"{bandwidth:.1f} Mbps"
        )
        
        self._history.append(point)
        self._cur_latency_text = point.latency_text
        self._cur_fps_text = point.fps_text
        self._cur_bw_text = point.bandwidth_text
        
        self.queue_draw()

    def _on_motion(self, controller, x, y):
        self._hover_x = x
        self._update_hover_index()
        self.queue_draw()

    def _on_leave(self, controller):
        self._hover_x = None
        self._hover_index = None
        self.queue_draw()

    def _update_hover_index(self) -> None:
        if self._hover_x is None or not self._history:
            self._hover_index = None
            return

        width = self.get_width()
        margin_left = 40
        margin_right = 10
        chart_width = width - margin_left - margin_right

        if chart_width <= 0:
            self._hover_index = None
            return

        if self._hover_x < margin_left or self._hover_x > width - margin_right:
            self._hover_index = None
            return

        num_points = len(self._history)
        x_step = chart_width / max(CHART_MAX_HISTORY - 1, 1)
        start_x = margin_left + chart_width - (num_points - 1) * x_step

        relative_x = self._hover_x - start_x
        index = round(relative_x / x_step) if x_step > 0 else 0
        index = max(0, min(num_points - 1, index))
        self._hover_index = index

    def _on_draw(self, area, cr, width, height):
        # Background - Dark Modern Style
        cr.set_source_rgba(0.12, 0.12, 0.12, 1.0)
        cr.rectangle(0, 0, width, height)
        cr.fill()

        margin_left = 40
        margin_right = 10
        margin_top = 20
        margin_bottom = 30

        chart_width = width - margin_left - margin_right
        chart_height = height - margin_top - margin_bottom

        if chart_width <= 0 or chart_height <= 0:
            return

        # Grid lines (draw 4 lines: 0%, 33%, 66%, 100%)
        cr.set_source_rgba(0.3, 0.3, 0.3, 0.3)
        cr.set_line_width(1)
        
        # We don't have a single scale, so grid lines are just visual guides (High/Mid/Low)
        for i in range(4):
            y = margin_top + (chart_height * i / 3)
            cr.move_to(margin_left, y)
            cr.line_to(margin_left + chart_width, y)
            cr.stroke()

        if not self._history:
            cr.set_source_rgba(0.5, 0.5, 0.5, 1)
            cr.set_font_size(14)
            text = "Aguardando dados..."
            extents = cr.text_extents(text)
            cr.move_to(margin_left + (chart_width - extents.width)/2, margin_top + chart_height/2)
            cr.show_text(text)
            return

        # Prepare normalized data lists
        lat_vals = [p.latency for p in self._history]
        fps_vals = [p.fps for p in self._history]
        bw_vals = [p.bandwidth for p in self._history]
        
        # Normalize 0..1 based on current maxes
        lat_norm = [v / max(1, self.max_latency) for v in lat_vals]
        fps_norm = [v / max(1, self.max_fps) for v in fps_vals]
        bw_norm = [v / max(1, self.max_bandwidth) for v in bw_vals]

        # Draw Lines
        # Bandwidth: Blue (Bottom layer)
        self._draw_line(cr, chart_width, chart_height, margin_left, margin_top, bw_norm, (0.0, 0.6, 1.0, 1.0)) # Cyan/Blue
        
        # FPS: Green
        self._draw_line(cr, chart_width, chart_height, margin_left, margin_top, fps_norm, (0.0, 0.8, 0.2, 1.0)) # Green

        # Latency: Orange/Red (Top layer)
        self._draw_line(cr, chart_width, chart_height, margin_left, margin_top, lat_norm, (1.0, 0.4, 0.0, 1.0)) # Orange

        # Legend
        self._draw_legend(cr, width, height, margin_left)
        
        # Tooltip / Hover Indicator
        if self._hover_index is not None and 0 <= self._hover_index < len(self._history):
            self._draw_tooltip(cr, width, height, margin_left, margin_top, chart_width, chart_height)

    def _draw_line(self, cr, w, h, mx, my, values, color):
        if not values: return
        
        cr.set_source_rgba(*color)
        cr.set_line_width(2)
        
        num = len(values)
        x_step = w / max(CHART_MAX_HISTORY - 1, 1)
        start_x = mx + w - (num - 1) * x_step
        
        for i, val in enumerate(values):
            x = start_x + i * x_step
            # Invert Y because 0 is top
            # Normalized val 1.0 = Max value (Top of chart)
            # Cairo Y: 0 is top. So 1.0 val should be at my. 0.0 val at my + h.
            y = my + h * (1 - val)
            if i == 0:
                cr.move_to(x, y)
            else:
                cr.line_to(x, y)
        
        cr.stroke()
        
        # Fill area
        cr.set_source_rgba(color[0], color[1], color[2], 0.15)
        for i, val in enumerate(values):
            x = start_x + i * x_step
            y = my + h * (1 - val)
            if i == 0:
                cr.move_to(x, y)
            else:
                cr.line_to(x, y)
        
        cr.line_to(start_x + (num - 1) * x_step, my + h)
        cr.line_to(start_x, my + h)
        cr.close_path()
        cr.fill()

    def _draw_legend(self, cr, w, h, margin_left):
        legend_y = h - 10
        
        # Helper to draw dot + text
        def draw_item(label, val_text, color, x_offset):
            cr.set_source_rgba(*color)
            cr.arc(margin_left + x_offset, legend_y - 4, 4, 0, 2*3.14159)
            cr.fill()
            
            cr.set_source_rgba(0.9, 0.9, 0.9, 1)
            cr.set_font_size(11)
            cr.move_to(margin_left + x_offset + 10, legend_y)
            text = f"{label}: {val_text}"
            cr.show_text(text)
            return cr.text_extents(text).width + 30

        offset = 0
        offset += draw_item("Latência", self._cur_latency_text, (1.0, 0.4, 0.0, 1.0), offset)
        offset += draw_item("FPS", self._cur_fps_text, (0.0, 0.8, 0.2, 1.0), offset)
        offset += draw_item("Banda", self._cur_bw_text, (0.0, 0.6, 1.0, 1.0), offset)

    def _draw_tooltip(self, cr, w, h, mx, my, cw, ch):
        point = list(self._history)[self._hover_index]
        num_points = len(self._history)
        x_step = cw / max(CHART_MAX_HISTORY - 1, 1)
        start_x = mx + cw - (num_points - 1) * x_step
        hover_x = start_x + self._hover_index * x_step

        # Vertical line
        cr.set_source_rgba(1, 1, 1, 0.4)
        cr.set_line_width(1)
        cr.move_to(hover_x, my)
        cr.line_to(hover_x, my + ch)
        cr.stroke()

        # Tooltip box
        msg = f"Lat: {point.latency_text}\nFPS: {point.fps_text}\nBanda: {point.bandwidth_text}"
        cr.set_font_size(10)
        ext = cr.text_extents(msg) # This gives single line extents usually, need manual splits
        
        # Simple drawing
        tooltip_x = w - 100
        tooltip_y = my + 10
        
        cr.set_source_rgba(0.1, 0.1, 0.1, 0.9)
        cr.rectangle(tooltip_x, tooltip_y, 90, 45)
        cr.fill()
        
        cr.set_source_rgba(1, 1, 1, 1)
        cr.move_to(tooltip_x + 5, tooltip_y + 12)
        cr.show_text(f"Lat: {point.latency_text}")
        cr.move_to(tooltip_x + 5, tooltip_y + 24)
        cr.show_text(f"FPS: {point.fps_text}")
        cr.move_to(tooltip_x + 5, tooltip_y + 36)
        cr.show_text(f"Banda: {point.bandwidth_text}")


class PerformanceMonitor(Gtk.Box):
    """
    Wrapper para o chart de performance.
    Substitui a caixa de texto antiga.
    """
    
    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.add_css_class('card')
        self.set_margin_top(12)
        self.set_margin_bottom(12)
        self.set_margin_start(12)
        self.set_margin_end(12)
        
        # Header
        self._header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        self._header.set_margin_start(12)
        self._header.set_margin_end(12)
        self._header.set_margin_top(8)
        self._header.set_margin_bottom(4)
        
        # Title (Host Name)
        self._title_label = Gtk.Label(label="Monitoramento em Tempo Real")
        self._title_label.add_css_class("heading")
        self._title_label.set_halign(Gtk.Align.START)
        self._title_label.set_hexpand(True)
        self._header.append(self._title_label)
        
        # Status (Icon + Text)
        self._status_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        
        self._status_icon = Gtk.Image.new_from_icon_name("network-idle-symbolic")
        self._status_icon.set_pixel_size(16)
        
        self._status_label = Gtk.Label(label="Desconectado")
        self._status_label.add_css_class("dim-label")
        
        self._status_box.append(self._status_icon)
        self._status_box.append(self._status_label)
        
        self._header.append(self._status_box)
        self.append(self._header)
        
        # Chart
        self.chart = PerformanceChartWidget()
        self.append(self.chart)
        
        self.update_timer = None

    def start_monitoring(self):
        if self.update_timer: return
        
        def update():
            # TODO: Obter dados reais. Por enquanto simulamos.
            l = random.uniform(5, 50)
            f = random.uniform(58, 62)
            b = random.uniform(10, 40)
            self.chart.add_data_point(l, f, b)
            return True
            
        self.update_timer = GLib.timeout_add(1000, update)
        
    def stop_monitoring(self):
        if self.update_timer:
            GLib.source_remove(self.update_timer)
            self.update_timer = None

    def set_connection_status(self, host_name, status_text, is_connected=True):
        """Atualiza informações de conexão no cabeçalho"""
        if is_connected:
            self._title_label.set_label(f"Conectado a {host_name}")
            self._status_label.set_label(status_text)
            self._status_icon.set_from_icon_name("network-transmit-receive-symbolic")
            self._status_icon.add_css_class("success")
        else:
            self._title_label.set_label("Monitoramento em Tempo Real")
            self._status_label.set_label("Desconectado")
            self._status_icon.set_from_icon_name("network-idle-symbolic")
            self._status_icon.remove_css_class("success")
