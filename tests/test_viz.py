import gc
import sys
import urllib.request
from unittest.mock import patch
import pytest

# Skip the entire test module if hvplot or panel are not installed
hvplot = pytest.importorskip("hvplot")
panel = pytest.importorskip("panel")
hv = pytest.importorskip("holoviews")
pd = pytest.importorskip("pandas")


# Ensure sys._panel_server_registry exists prior to test execution
if not hasattr(sys, "_panel_server_registry"):
    sys._panel_server_registry = {}

# Import your class and helper function here
from dmanage.viz import HvPlotExplorer,launch_server

@pytest.fixture(autouse=True)
def prevent_browser_open():
    """Globally prevents tests from opening real web browser tabs."""
    with patch("webbrowser.open"):
        yield


@pytest.fixture
def sample_df():
    """Provides a deterministic DataFrame for testing."""
    return pd.DataFrame({
        "x_num": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0],
        "y_num": [10.0, 20.0, 15.0, 25.0, 30.0, 35.0],
        "cat_group": ["A", "A", "B", "B", "C", "C"],
        "cat_subgroup": ["Low", "High", "Low", "High", "Low", "High"]
    })


# ==============================================================================
# 1. CLASS UNIT & MODEL HOOK TESTS
# ==============================================================================

def test_explorer_logic_and_binning(sample_df):
    explorer = HvPlotExplorer(df=sample_df)
    
    explorer.cat_col = "x_num"
    explorer.n_bins = 2
    explorer._add_category_action()

    assert "x_num_bin2" in explorer.df.columns
    assert explorer.color_by == ["x_num_bin2"]


def test_bokeh_model_hook_and_cds(sample_df):
    explorer = HvPlotExplorer(df=sample_df)
    explorer.color_by = ["cat_group"]
    explorer.marker_by = ["cat_subgroup"]

    hv_plot = explorer.make_plot()
    bokeh_fig = hv.render(hv_plot, backend="bokeh")

    # Inspect right legend layouts
    right_legends = [
        layout for layout in bokeh_fig.right 
        if getattr(layout, "name", None) == "marker_legend"
    ]
    assert len(right_legends) == 1

    # Confirm injected CDS columns
    main_renderer = [
        r for r in bokeh_fig.renderers 
        if getattr(r, "name", None) != "dummy_legend_renderer"
    ][0]
    cds_data = main_renderer.data_source.data
    assert "_alpha" in cds_data
    assert "marker_composite" in cds_data


# ==============================================================================
# 2. PANELSERVER LIFECYCLE & THREAD KILL TESTS
# ==============================================================================

def test_panel_server_manual_stop(sample_df):
    explorer = HvPlotExplorer(df=sample_df)
    server = launch_server(explorer, port=5007)
    
    # 1. Verify thread is running and server responds to HTTP requests
    assert server.thread is not None
    assert server.thread.is_alive()
    
    res = urllib.request.urlopen("http://localhost:5007/")
    assert res.status == 200

    # 2. Stop server manually
    server.stop()
    server.thread.join(timeout=2.0)

    # 3. Assert thread is terminated and port is removed from registry
    assert not server.thread.is_alive()
    assert 5007 not in sys._panel_server_registry

    # 4. Confirm socket is dead
    with pytest.raises(Exception):
        urllib.request.urlopen("http://localhost:5007/", timeout=1)


def test_panel_server_garbage_collection_del(sample_df):
    explorer = HvPlotExplorer(df=sample_df)
    server = launch_server(explorer, port=5008)
    
    thread_ref = server.thread
    assert thread_ref.is_alive()

    # Deleting object triggers weakref.finalize container cleanup
    del server
    gc.collect()

    thread_ref.join(timeout=2.0)

    assert not thread_ref.is_alive()
    assert 5008 not in sys._panel_server_registry


def test_panel_server_context_manager(sample_df):
    explorer = HvPlotExplorer(df=sample_df)
    
    with launch_server(explorer, port=5009) as server:
        assert server.thread.is_alive()
        res = urllib.request.urlopen("http://localhost:5009/")
        assert res.status == 200

    # Thread should be stopped upon exit of context manager block
    server.thread.join(timeout=2.0)
    assert not server.thread.is_alive()


def test_panel_server_port_reclaim(sample_df):
    explorer = HvPlotExplorer(df=sample_df)

    # Start first instance on 5010
    server_1 = launch_server(explorer, port=5010)
    thread_1 = server_1.thread
    assert thread_1.is_alive()

    # Launch second instance on same port; PanelServer should clean up server_1
    server_2 = launch_server(explorer, port=5010)
    thread_2 = server_2.thread

    thread_1.join(timeout=2.0)

    assert not thread_1.is_alive()
    assert thread_2.is_alive()
    assert sys._panel_server_registry[5010]["thread"] is thread_2

    server_2.stop()
    
if __name__ == "__main__":
    # Runs the test suite directly with pytest
    pytest.main([__file__, "-v", "-s"])