import sys
import os
from pathlib import Path
import subprocess
import time
import pytest
import dmanage.config

def is_port_open(host="127.0.0.1", port=44444):
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex((host, port)) == 0

def pytest_configure(config):
    """Executes before test collection or imports begin."""
    start_method = os.getenv("PARALLEL_START_METHOD", "fork")
    
    # Windows does not support fork; fall back to spawn on Windows
    if start_method == "fork" and sys.platform == "win32":
        start_method = "spawn"
        
    dmanage.config.PARALLEL_START_METHOD = start_method

@pytest.fixture(autouse=True)
def check_rpc_server_marker(request):
    """Dynamically skips tests marked with @requires_rpc_server if port 44444 is closed."""
    if request.node.get_closest_marker("requires_rpc_server"):
        if not is_port_open():
            pytest.skip("RPC Factory server is not running on port 44444.")

@pytest.fixture(scope="session")
def rpc_factory_daemon():
    """Launches dmanage-factory daemon using active Python environment."""
    if is_port_open():
        yield
        return

    log_path = Path("server_debug.log")
    log_file = open(log_path, "w", encoding="utf-8")

    # Inherit system environment variables (CRITICAL for Windows winsock/DLL paths)
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"

    proc = subprocess.Popen(
        [sys.executable, "-m", "dmanage.rstrata.cli", "--test"],
        stdout=log_file,
        stderr=subprocess.STDOUT,  # Combined into log_file
        env=env,
    )

    start_time = time.time()
    timeout = 15.0

    while not is_port_open():
        if proc.poll() is not None:
            log_file.flush()
            log_file.close()
            logs = log_path.read_text(encoding="utf-8")
            pytest.fail(
                f"`dmanage-factory --test` exited prematurely (code {proc.returncode}).\n"
                f"SERVER LOGS:\n{logs}"
            )

        if time.time() - start_time > timeout:
            proc.kill()
            proc.wait()
            log_file.flush()
            log_file.close()
            logs = log_path.read_text(encoding="utf-8")
            pytest.fail(
                f"Timed out after {timeout}s waiting for `dmanage-factory` to open port 44444.\n"
                f"SERVER LOGS:\n{logs}"
            )

        time.sleep(0.2)

    yield proc

    # Teardown
    proc.terminate()
    try:
        proc.wait(timeout=2)
    except subprocess.TimeoutExpired:
        proc.kill()
    finally:
        if not log_file.closed:
            log_file.close()