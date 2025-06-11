import os
import signal
import subprocess
import sys
import time

processes = []


def shutdown(signum, frame):
    print("Shutting down server and clients...")
    for p in processes:
        p.terminate()
    for p in processes:
        p.wait()
    sys.exit(0)


signal.signal(signal.SIGINT, shutdown)
signal.signal(signal.SIGTERM, shutdown)

# Launch Rust server
server_proc = subprocess.Popen(
    ["cargo", "run"], cwd=os.path.join(os.path.dirname(__file__), "server")
)
processes.append(server_proc)

# Launch 4 Python client windows
client_dir = os.path.join(os.path.dirname(__file__), "client")
env_path = os.path.join(client_dir, "env", "bin", "activate_this.py")
activate_script = os.path.join(client_dir, "env", "bin", "python")

for i in range(4):
    p = subprocess.Popen([activate_script, "src/main.py"], cwd=client_dir)
    processes.append(p)

# Wait for all processes
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    shutdown(None, None)
