
import subprocess
import socket
import sys

def run_cmd(cmd):
    try:
        res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=5)
        return res.stdout.strip(), res.stderr.strip(), res.returncode
    except Exception as e:
        return "", str(e), -1

def check_ipv6_interfaces():
    print("=== Interfaces IPv6 ===")
    out, err, code = run_cmd("ip -6 addr show")
    print(out)
    print("=======================")

def check_sunshine_listening():
    print("\n=== Sunshine Listening Ports (IPv6) ===")
    out, err, code = run_cmd("ss -tuln6 | grep -E '47989|47984|48010'")
    if not out:
        print("❌ Sunshine não parece estar ouvindo em portas IPv6 (ou permissão negada).")
    else:
        print(out)
    print("=======================================")

def check_avahi_discovery():
    print("\n=== Avahi Discovery (IPv6) ===")
    out, err, code = run_cmd("avahi-browse -t -r -p _nvstream._tcp")
    print(f"Raw Output:\n{out}")
    
    hosts = []
    for line in out.split('\n'):
        if not line: continue
        parts = line.split(';')
        if len(parts) > 7 and parts[0] == '=':
            ip = parts[7]
            iface = parts[1]
            if ':' in ip: # IPv6
                hosts.append((ip, iface))
                print(f"Found IPv6 Host: {ip} on {iface}")
    
    print("==============================")
    return hosts

def connectivity_test(hosts):
    print("\n=== Connectivity Test ===")
    for ip, iface in hosts:
        print(f"\n--- Testing Host: {ip} on {iface} ---")
        
        # 1. Ping Test
        target = f"{ip}%{iface}" if ip.startswith("fe80:") else ip
        print(f"1. IP Reachability (Ping): Pinging {target}...")
        # Try both ping6 and ping -6
        out, err, code = run_cmd(f"ping -6 -c 3 -W 1 {target}")
        if code != 0:
             out, err, code = run_cmd(f"ping6 -c 3 -W 1 {target}")
             
        if code == 0:
            print(f"   ✅ Ping success: {target} is reachable.")
        else:
            print(f"   ❌ Ping failed: {target} is unreachable.")
            print(f"   Output: {out[:200]}")

        # 2. Port Test (TCP)
        print(f"2. Service Reachability (TCP 47989): Connecting to {ip} port 47989...")
        try:
            # Parse scope ID for getaddrinfo
            scope_id = 0
            addr_ip = ip
            if '%' in ip:
                addr_ip, scope_str = ip.split('%')
                # Scope ID is tricky in Python socket, usually requires interface index.
                # However, getaddrinfo handles it if we pass the full string with % if supported,
                # OR we need to find the interface index.
                # Simplest way: use socket.getaddrinfo with the scope string attached if the OS supports it (Linux usually does).
                pass
            
            # Using socket.create_connection is high level
            # For IPv6 link-local, we really need the detailed address info
            res = socket.getaddrinfo(ip + '%' + iface if ip.startswith('fe80') and '%' not in ip else ip, 47989, socket.AF_INET6, socket.SOCK_STREAM)
            family, socktype, proto, canonname, sockaddr = res[0]
            
            with socket.socket(family, socktype, proto) as s:
                s.settimeout(3)
                s.connect(sockaddr)
                print(f"   ✅ TCP Port 47989 is OPEN and accepting connections.")
        except Exception as e:
            print(f"   ❌ TCP Port 47989 Connection Failed: {e}")
            print(f"   (This usually indicates a FIREWALL is blocking the port on the host)")
            
        # 3. Port Test (TCP 48010 - RTSP)
        print(f"3. RTSP Reachability (TCP 48010): Connecting to {ip} port 48010...")
        try:
            res = socket.getaddrinfo(ip + '%' + iface if ip.startswith('fe80') and '%' not in ip else ip, 48010, socket.AF_INET6, socket.SOCK_STREAM)
            family, socktype, proto, canonname, sockaddr = res[0]
            
            with socket.socket(family, socktype, proto) as s:
                s.settimeout(3)
                s.connect(sockaddr)
                print(f"   ✅ TCP Port 48010 is OPEN and accepting connections.")
        except Exception as e:
            print(f"   ❌ TCP Port 48010 Connection Failed: {e}")
            print(f"   (RTSP Handshake port is blocked. Connection will fail.)")
            
    print("=================================")

def main():
    print("Iniciando diagnóstico IPv6...\n")
    check_ipv6_interfaces()
    check_sunshine_listening()
    hosts = check_avahi_discovery()
    if hosts:
        connectivity_test(hosts)
    else:
        print("Nenhum host IPv6 encontrado via Avahi.")

if __name__ == "__main__":
    main()
