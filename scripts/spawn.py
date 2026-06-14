"""Python wrapper for mavis spawn (stdin JSON)"""
import sys, json, subprocess
config = json.loads(sys.stdin.read())
result = subprocess.run([
    "C:\\Users\\15088\\.mavis\\bin\\mavis.cmd", "communication", "send",
    "--command", "spawn",
    "--content", json.dumps(config, ensure_ascii=False),
    "--from", "mvs_4db12fd4091c443ba2e1028b739ddad2",
    "--to", "mvs_4db12fd4091c443ba2e1028b739ddad2",
], capture_output=True, text=True, encoding="utf-8", errors="replace")
print("STDOUT:", result.stdout)
print("STDERR:", result.stderr)
print("RC:", result.returncode)
