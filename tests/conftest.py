import sys
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

@pytest.fixture(autouse=True, scope="session")
def configure_test_parallelism():
    """Force fast process forking during tests."""
    dmanage.config.PARALLEL_START_METHOD = "fork"

@pytest.fixture(autouse=True)
def check_rpc_server_marker(request):
    """Dynamically skips tests marked with @requires_rpc_server if port 44444 is closed."""
    if request.node.get_closest_marker("requires_rpc_server"):
        if not is_port_open():
            pytest.skip("RPC Factory server is not running on port 44444.")

@pytest.fixture(scope="session")
def rpc_factory_daemon():
    """Launches dmanage-factory daemon using Spyder's active Python environment."""
    if is_port_open():
        yield
        return

    # Target dmanage-factory inside the exact bin folder running pytest/Spyder
    active_env_bin = Path(sys.executable).parent
    factory_bin = str(active_env_bin / "dmanage-factory")

    proc = subprocess.Popen(
        [factory_bin, "--test"],
        stderr=subprocess.PIPE,
        text=True,
    )

    start_time = time.time()
    while not is_port_open():
        if proc.poll() is not None:
            _, stderr = proc.communicate()
            pytest.fail(
                f"`dmanage-factory --test` crashed on startup (code {proc.returncode}).\n"
                f"Daemon Error Output:\n{stderr}"
            )
        if time.time() - start_time > 5.0:
            proc.kill()
            pytest.fail("Timed out waiting for `dmanage-factory` to open port 44444.")
        time.sleep(0.1)

    yield proc

    proc.terminate()
    try:
        proc.wait(timeout=2)
    except subprocess.TimeoutExpired:
        proc.kill()