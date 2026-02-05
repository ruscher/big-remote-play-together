
import subprocess
import sys

target_ip = "2804:30c:1b4a:d00:58e4:a452:64b2:8975"

def run_test(name, cmd):
    print(f"--- TEST: {name} ---")
    print(f"Command: {' '.join(cmd)}")
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        print(f"Exit Code: {res.returncode}")
        if res.stdout.strip():
            print(f"STDOUT: {res.stdout[:500]}...")
        if res.stderr.strip():
            print(f"STDERR: {res.stderr[:500]}...")
    except subprocess.TimeoutExpired:
        print("RESULT: TIMEOUT")
    except Exception as e:
        print(f"RESULT: ERROR {e}")
    print("\n")

# 1. Ping
run_test("Ping IPv6", ["ping", "-6", "-c", "2", target_ip])

# 2. Moonlight List (No Brackets)
run_test("Moonlight List (Raw IP)", ["moonlight-qt", "list", target_ip])

# 3. Moonlight List (Brackets)
run_test("Moonlight List (Brackets)", ["moonlight-qt", "list", f"[{target_ip}]"])

# 4. Check capabilities
run_test("Moonlight Help", ["moonlight-qt", "--help"])
