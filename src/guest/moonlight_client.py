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
            if not kw.get('audio', True): cmd.append('--audio-on-host')
            if kw.get('hw_decode', True): cmd.extend(['--video-decoder', 'hardware'])
            else: cmd.extend(['--video-decoder', 'software'])
            print(f"DEBUG: Connecting with options: resolution={kw.get('width')}x{kw.get('height')}, fps={kw.get('fps')}, audio={kw.get('audio', True)}")
            print(f"DEBUG: Full command: {' '.join(cmd)}")
            # AVOID PIPE BLOCKING: Use DEVNULL or None (inherit) for long running process!
            # Using PIPE without reading loop causes "Starting Desktop..." freeze when buffer fills (64K).
            # We want to wait 1 sec to check for immediate crash, but we can't do that easily with DEVNULL/None 
            # and verify output.
            # Compromise: Use a temporary check or just let it run.
            # If we want to see logs in terminal, use None. If we want silence, DEVNULL.
            # The User runs from terminal usually, so None is better for debugging.
            
            self.process = subprocess.Popen(cmd, stdout=None, stderr=None, text=True)
            self.connected_host = ip
            
            # Simple check if it stays alive for a moment
            try:
                exit_code = self.process.wait(timeout=1.0)
                # If we are here, it exited immediately
                print(f"Moonlight terminou prematuramente (Code {exit_code})")
                return False
            except subprocess.TimeoutExpired: 
                # Still running, good!
                pass
            
            print(f"Conectado a {ip} (PID: {self.process.pid})"); return True
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
