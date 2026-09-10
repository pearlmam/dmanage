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

    proc = subprocess.Popen(
        [sys.executable, "-m", "dmanage.rstrata.server", "--test"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True,
    )

    start_time = time.time()
    timeout = 15.0  # Accounts for Windows process spawn overhead

    while not is_port_open():
        if proc.poll() is not None:
            stdout, stderr = proc.communicate()
            pytest.fail(
                f"`dmanage-factory --test` exited prematurely (code {proc.returncode}).\n"
                f"STDOUT:\n{stdout}\n"
                f"STDERR:\n{stderr}"
            )
            
        if time.time() - start_time > timeout:
            proc.kill()
            stdout, stderr = proc.communicate()
            pytest.fail(
                f"Timed out after {timeout}s waiting for `dmanage-factory` to open port 44444.\n"
                f"STDOUT:\n{stdout}\n"
                f"STDERR:\n{stderr}"
            )
            
        time.sleep(0.2)

    yield proc

    proc.terminate()
    try:
        proc.wait(timeout=2)
    except subprocess.TimeoutExpired:
        proc.kill()