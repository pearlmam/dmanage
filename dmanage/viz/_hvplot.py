import asyncio
import time
import weakref
import threading
import webbrowser
import pandas as pd
import panel as pn
import numpy as np
import hvplot.pandas
from panel.io.server import get_server

__all__ = ["HvPlotExplorer","HvPlotExplorer2", "launch_explorer","sanitize_df","check_threads"]


class HvPlotExplorer:
    """Class wrapper managing an isolated Panel server with auto-garbage collection."""
    
    _ACTIVE_BOX = [None]
    _ACTIVE_PORT = [None]

    def __init__(self, df: pd.DataFrame, port: int = 5006, **explorer_kwargs):
        self.df = df
        self.port = port
        self.explorer_kwargs = explorer_kwargs
        self._server_box = [None]
        self._finalizer = None
        print(f'these servers are active: {self._ACTIVE_BOX}')

    @staticmethod
    def _stop_server(server_box: list, port: int):
        """Static teardown routine. Decoupled from 'self' so GC can fire."""
        server = server_box[0]
        if server is not None:
            try:
                # Force OS socket release
                server.unlisten()
                server.stop()
                
                # Halt isolated event loop safely
                if hasattr(server, 'io_loop') and server.io_loop is not None:
                    server.io_loop.add_callback(server.io_loop.stop)
                    
                print(f"Port {port} cleanly released.")
            except Exception as e:
                print(f"Error releasing port {port}: {e}")
            finally:
                server_box[0] = None

    def stop(self):
        """Manual stop method."""
        self._stop_server(self._server_box, self.port)

    def start(self, show: bool = True):
        # 1. Clear prior active instances across the session
        self._stop_server(self._ACTIVE_BOX, self._ACTIVE_PORT[0] or self.port)
        # 2. Sanitize booleans for Bokeh slider safety
        df_clean = sanitize_df(self.df)
    
        pn.extension()

        # 3. Extract local variables to avoid capturing 'self' in the thread closure
        server_box = self._server_box
        port = self.port
        kwargs = self.explorer_kwargs
        ready_event = threading.Event()

        # 4. Background thread runner (Only references local variables!)
        def _run_server():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            app_factory = lambda: df_clean.hvplot.explorer(**kwargs)

            server = get_server(
                app_factory,
                port=port,
                start=False,
                show=False,
                websocket_origin="*"
            )

            server_box[0] = server
            HvPlotExplorer._ACTIVE_BOX[0] = server
            HvPlotExplorer._ACTIVE_PORT[0] = port

            server.start()
            ready_event.set()
            loop.run_forever()

        thread = threading.Thread(target=_run_server, daemon=True)
        thread.start()

        # 5. Wait for server object instantiation
        ready_event.wait(timeout=0.5)

        # 6. Attach weakref finalizer to self
        self._finalizer = weakref.finalize(
            self,
            self._stop_server,
            self._server_box,
            self.port
        )

        url = f"http://localhost:{self.port}"
        if show:
            time.sleep(0.1)
            webbrowser.open(url)

        print(f"Background explorer running at {url}")
        return self

def launch_explorer(df: pd.DataFrame, port: int = 5006, show: bool = True, **kwargs):
    """Functional helper returning a managed HvPlotExplorer instance."""
    explorer = HvPlotExplorer(df, port=port, **kwargs)
    return explorer.start(show=show)



def sanitize_df(df):
    df_clean = df.copy()
    bool_cols = df_clean.select_dtypes(include=['bool', 'boolean']).columns
    if len(bool_cols) > 0:
        df_clean[bool_cols] = df_clean[bool_cols].astype(int)
    return df_clean

def check_threads():
    import threading
    for i,t in enumerate(threading.enumerate()):
        print(f"thread {i}:{t}, has stop: {hasattr(t, "stop")}")
        
        
class HvPlotExplorer2:
    """Class wrapper managing an isolated Panel server with auto-garbage collection."""

    _ACTIVE_BOX = [None]
    _ACTIVE_PORT = [None]

    def __init__(self, df: pd.DataFrame, port: int = 5006, **explorer_kwargs):
        self.df = df
        self.port = port
        self.explorer_kwargs = explorer_kwargs
        self._server_box = [None]
        self._finalizer = None

    @staticmethod
    def _stop_server(server_box: list, port: int):
        """Static teardown routine decoupled from 'self' so GC can fire."""
        server = server_box[0]
        if server is not None:
            try:
                # Force OS socket release
                server.unlisten()
                server.stop()

                # Halt isolated event loop safely
                if hasattr(server, "io_loop") and server.io_loop is not None:
                    server.io_loop.add_callback(server.io_loop.stop)

                print(f"Port {port} cleanly released.")
            except Exception as e:
                print(f"Error releasing port {port}: {e}")
            finally:
                server_box[0] = None

    def stop(self):
        """Manual stop method to tear down server thread explicitly."""
        self._stop_server(self._server_box, self.port)

    def start(self, show: bool = True):
        # 1. Clear prior active instances across the session
        self._stop_server(self._ACTIVE_BOX, self._ACTIVE_PORT[0] or self.port)

        # 2. Sanitize data types and auto-detect columns
        df_clean = sanitize_df(self.df)

        # Automatically inspect column metadata for default fallback parameters
        all_cols = list(df_clean.columns)
        numeric_cols = list(df_clean.select_dtypes(include=[np.number]).columns)
        categorical_cols = list(df_clean.select_dtypes(include=["object", "category"]).columns)

        # Inject default selections if not provided in explorer_kwargs
        kwargs = self.explorer_kwargs.copy()
        if "x" not in kwargs and numeric_cols:
            kwargs["x"] = numeric_cols[0]
        if "y" not in kwargs and len(numeric_cols) > 1:
            kwargs["y"] = numeric_cols[1]
        if "by" not in kwargs and categorical_cols:
            kwargs["by"] = categorical_cols[0]

        pn.extension()

        # 3. Extract local variables to avoid capturing 'self' in thread closure
        server_box = self._server_box
        port = self.port
        ready_event = threading.Event()

        # 4. Non-blocking background thread runner
        def _run_server():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            # hvplot.explorer dynamically maps controls for all numeric and categorical columns
            app_factory = lambda: df_clean.hvplot.explorer(**kwargs)

            server = get_server(
                app_factory,
                port=port,
                start=False,
                show=False,
                websocket_origin="*",
            )

            server_box[0] = server
            HvPlotExplorer2._ACTIVE_BOX[0] = server
            HvPlotExplorer2._ACTIVE_PORT[0] = port

            server.start()
            ready_event.set()
            loop.run_forever()

        thread = threading.Thread(target=_run_server, daemon=True)
        thread.start()

        # 5. Wait for server object instantiation
        ready_event.wait(timeout=2.0)

        # 6. Attach weakref finalizer for auto-garbage collection teardown
        self._finalizer = weakref.finalize(
            self, self._stop_server, self._server_box, self.port
        )

        url = f"http://localhost:{self.port}"
        if show:
            time.sleep(0.2)
            webbrowser.open(url)

        print(f"Background explorer running non-blockingly at {url}")
        return self
        
        

