import subprocess
import signal
import sys
import os
import time
import requests

def signal_handler(sig, frame):
    print('\nShutting down "set" development environment...')
    # Kill backend and frontend processes
    subprocess.run(["pkill", "-f", "uvicorn"], stderr=subprocess.DEVNULL)
    subprocess.run(["pkill", "-f", "vite"], stderr=subprocess.DEVNULL)
    # Stop DynamoDB container
    print("Stopping DynamoDB container...")
    subprocess.run(["podman", "stop", "dynamodb-local"], stderr=subprocess.DEVNULL)
    print('Cleaned up. Goodbye!')
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

def wait_for_service(url, timeout=15):
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            requests.get(url)
            return True
        except:
            time.sleep(1)
    return False

def run():
    print('Starting "set" development environment...')
    
    # 1. Start DynamoDB
    print('-> Starting DynamoDB Local (Podman)...')
    subprocess.run(["podman", "start", "dynamodb-local"], stderr=subprocess.DEVNULL)
    
    # Check if it exists, if not run it
    res = subprocess.run(["podman", "inspect", "dynamodb-local"], capture_output=True)
    if res.returncode != 0:
        print('-> Container not found, creating new one...')
        subprocess.run([
            "podman", "run", "-d", "--name", "dynamodb-local", 
            "-p", "8001:8000", "docker.io/amazon/dynamodb-local"
        ])
    
    # Wait for DynamoDB
    print('Waiting for DynamoDB to be ready...')
    # DynamoDB local usually doesn't have a /health, but we can try to hit the port
    time.sleep(3)

    # 2. Start Backend
    print('-> Starting Backend (http://localhost:8000)...')
    env = os.environ.copy()
    env["DYNAMODB_ENDPOINT_URL"] = "http://localhost:8001"
    env["AWS_ACCESS_KEY_ID"] = "local"
    env["AWS_SECRET_ACCESS_KEY"] = "local"
    env["MOCK_AUTH"] = "true"
    env["PYTHONPATH"] = os.getcwd() + "/backend"
    
    backend_proc = subprocess.Popen(
        ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"],
        cwd="backend",
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )

    # 3. Start Frontend
    print('-> Starting Frontend (http://localhost:5173)...')
    frontend_proc = subprocess.Popen(
        ["npm", "run", "dev", "--", "--host", "0.0.0.0"],
        cwd="frontend",
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    print('\nWaiting for services to initialize...')
    if wait_for_service("http://localhost:8000/health"):
        print('\n✅ Environment is UP!')
        print('Frontend: http://localhost:5173')
        print('Backend:  http://localhost:8000')
        print('Press Ctrl+C to shut down all services safely.\n')
    else:
        print('\n❌ Backend failed to start. Check logs.')
        backend_proc.terminate()
        frontend_proc.terminate()
        sys.exit(1)
    
    try:
        while True:
            line = backend_proc.stdout.readline()
            if line:
                print(f"[Backend] {line.strip()}")
            if backend_proc.poll() is not None:
                print("Backend process died.")
                break
    except KeyboardInterrupt:
        pass
    
    signal_handler(None, None)

if __name__ == "__main__":
    run()
