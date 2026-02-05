
import sys
import socket
import subprocess

target_ip = "2804:30c:1b4a:d00:58e4:a452:64b2:8975"
port = 47989

print(f"Testing connection to {target_ip}:{port}...")

# Test 1: Socket
try:
    sock = socket.create_connection((target_ip, port), timeout=5)
    print("SUCCESS: Socket connected!")
    sock.close()
except Exception as e:
    print(f"FAILURE: Socket connection failed: {e}")

# Test 2: Moonlight List (With Brackets)
formatted_ip_brackets = f"[{target_ip}]"
print(f"\nTesting 'moonlight-qt list {formatted_ip_brackets}'...")
try:
    res = subprocess.run(['moonlight-qt', 'list', formatted_ip_brackets], capture_output=True, text=True, timeout=10)
    print(f"Return Code: {res.returncode}")
    print(f"STDOUT: {res.stdout}")
    print(f"STDERR: {res.stderr}")
except Exception as e:
    print(f"FAILURE: Moonlight list failed: {e}")

# Test 3: Moonlight List (Without Brackets)
print(f"\nTesting 'moonlight-qt list {target_ip}'...")
try:
    res = subprocess.run(['moonlight-qt', 'list', target_ip], capture_output=True, text=True, timeout=10)
    print(f"Return Code: {res.returncode}")
    print(f"STDOUT: {res.stdout}")
    print(f"STDERR: {res.stderr}")
except Exception as e:
    print(f"FAILURE: Moonlight list failed: {e}")
