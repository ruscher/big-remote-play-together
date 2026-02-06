import subprocess, shutil
class MoonlightClient:
    def __init__(self):
        self.process = None; self.connected_host = None
        self.moonlight_cmd = next((c for c in ['moonlight-qt', 'moonlight'] if shutil.which(c)), None)
    def connect(self, ip, **kw):
        if not self.moonlight_cmd or self.is_connected(): return False
        try:
            cmd = [self.moonlight_cmd, 'stream', ip, 'Desktop']
            if kw.get('width') and kw.get('height') and kw.get('width') != 'custom': cmd.extend(['--resolution', f"{kw['width']}x{kw['height']}"])
            if kw.get('fps') and kw.get('fps') != 'custom': cmd.extend(['--fps', str(kw['fps'])])
            if kw.get('bitrate'): cmd.extend(['--bitrate', str(kw['bitrate'])])
            cmd.extend(['--display-mode', kw.get('display_mode', 'borderless')])
            cmd.append('--no-audio-on-host' if kw.get('audio', True) else '--audio-on-host')
            if kw.get('hw_decode', True): cmd.extend(['--video-decoder', 'hardware'])
            else: cmd.extend(['--video-decoder', 'software'])
            print(f"DEBUG: Connecting with options: resolution={kw.get('width')}x{kw.get('height')}, fps={kw.get('fps')}, audio={kw.get('audio', True)}")
            print(f"DEBUG: Full command: {' '.join(cmd)}")
            self.process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            self.connected_host = ip
            try:
                exit_code = self.process.wait(timeout=1.0)
                stdout, stderr = self.process.communicate()
                print(f"Moonlight terminou (Code {exit_code})\nSTDOUT: {stdout}\nSTDERR: {stderr}")
                return False
            except subprocess.TimeoutExpired: pass
            print(f"Conectado a {ip}"); return True
        except Exception as e: print(f"Erro ao conectar: {e}"); return False
    def is_connected(self): return self.process and self.process.poll() is None
    def disconnect(self):
        if not self.is_connected(): return False
        try:
            if self.process: self.process.terminate(); self.process.wait(timeout=5)
            self.process = None; self.connected_host = None; return True
        except:
            if self.process: self.process.kill(); self.process = None; self.connected_host = None
            return False
    def probe_host(self, host_ip):
        try: return subprocess.run([self.moonlight_cmd, 'list', host_ip], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=2).returncode == 0
        except: return False
    def pair(self, host_ip, on_pin_callback=None):
        try:
            p = subprocess.Popen([self.moonlight_cmd, 'pair', host_ip], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
            while p.poll() is None:
                line = p.stdout.readline()
                if not line: break
                if "PIN" in line and "target PC" in line:
                    pin = ''.join(filter(str.isdigit, line.strip().split()[-1]))
                    if pin and on_pin_callback: on_pin_callback(pin)
                if "successfully paired" in line.lower() or "already paired" in line.lower(): p.terminate(); return True
            return p.returncode == 0
        except: return False
    def list_apps(self, host_ip):
        if not self.moonlight_cmd: return []
        try:
            r = subprocess.run([self.moonlight_cmd, 'list', host_ip], capture_output=True, text=True, timeout=5)
            return [l.strip() for l in r.stdout.splitlines() if l.strip()] if r.returncode == 0 else []
        except: return []
    def get_status(self): return {'connected': self.is_connected(), 'host': self.connected_host, 'moonlight_cmd': self.moonlight_cmd}
