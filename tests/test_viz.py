import gc
import socket
import time
import pandas as pd
import pytest

# Skip the entire test module if hvplot or panel are not installed
hvplot = pytest.importorskip("hvplot")
panel = pytest.importorskip("panel")

# Import module under test after importorskip checks
from dmanage.viz import HvPlotExplorer, launch_explorer, sanitize_df


def is_port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    """Helper socket check to verify background server status."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex((host, port)) == 0


@pytest.fixture
def sample_df():
    return pd.DataFrame({
        "x": [1, 2, 3],
        "y": [10.0, 20.0, 30.0],
        "flag": [True, False, True]
    })


def test_sanitize_df(sample_df):
    """Verifies that boolean columns are converted to integers for Bokeh safety."""
    cleaned = sanitize_df(sample_df)
    assert cleaned["flag"].dtype in ["int64", "int32"]
    assert list(cleaned["flag"]) == [1, 0, 1]


def test_explorer_server_lifecycle(sample_df):
    """Tests starting and manually stopping the isolated Panel server."""
    port = 5099
    explorer = HvPlotExplorer(sample_df, port=port)
    
    # Always set show=False in automated tests to prevent browser pop-ups
    explorer.start(show=False)
    
    # Allow background thread loop to bind socket
    time.sleep(0.5)
    assert is_port_in_use(port) is True

    # Stop server and check port release
    explorer.stop()
    time.sleep(0.5)
    assert is_port_in_use(port) is False


def test_explorer_garbage_collection_finalizer(sample_df):
    """Verifies that weakref.finalize cleans up the server when instance is deleted."""
    port = 5098
    explorer = launch_explorer(sample_df, port=port, show=False)
    time.sleep(0.5)
    assert is_port_in_use(port) is True

    # Delete instance reference and trigger garbage collector
    del explorer
    gc.collect()
    time.sleep(0.5)

    assert is_port_in_use(port) is False


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--pdb"])