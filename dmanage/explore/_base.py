# -*- coding: utf-8 -*-

# -*- coding: utf-8 -*-
import sys
import asyncio
import threading
import weakref
import pandas as pd

from panel.io.server import get_server
from tornado.ioloop import IOLoop
import webbrowser

__all__ = ["PanelServer","launch_server","sanitize_df"]


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================
def sanitize_df(df: pd.DataFrame) -> pd.DataFrame:
    """Sanitizes boolean columns to string categories for Bokeh safety."""
    df_clean = df.copy()
    for col in df_clean.columns:
        if df_clean[col].dtype == "bool":
            df_clean[col] = df_clean[col].astype(str)
    return df_clean


def _to_numeric_coords(series: pd.Series, raw_val):
    """Converts Numeric, Datetime, or Categorical values to unified float coordinates."""
    if pd.api.types.is_numeric_dtype(series):
        return pd.to_numeric(series, errors="coerce"), float(raw_val)
    elif pd.api.types.is_datetime64_any_dtype(series):
        s_ms = pd.to_datetime(series).astype("int64") // 10**6
        val_ms = (
            float(raw_val)
            if isinstance(raw_val, (int, float))
            else float(pd.Timestamp(raw_val).value // 10**6)
        )
        return s_ms, val_ms
    else:
        s_str = series.astype(str)
        uniques = list(s_str.unique())
        mapping = {cat: idx for idx, cat in enumerate(uniques)}

        if isinstance(raw_val, (int, float)):
            target_idx = float(raw_val)
        else:
            target_idx = float(mapping.get(str(raw_val), 0))
        return s_str.map(mapping).astype(float), target_idx


# =============================================================================
# BASE PANEL SERVER & LAUNCHER
# =============================================================================

# Persistent registry attached to Python process state (survives module reloads)
if not hasattr(sys, "_panel_server_registry"):
    sys._panel_server_registry = {}


class PanelServer:
    """Lightweight server wrapper with zero UI callback references."""

    def __init__(self, app_factory, port=5006):
        self.app_factory = app_factory
        self.port = port
        self.thread = None
        self._finalizer = None

    @staticmethod
    def _stop_container(container):
        if not container or container.get("stopped"):
            return
        container["stopped"] = True

        server = container.get("server")
        io_loop = container.get("io_loop")
        port = container.get("port")

        if io_loop:
            def _in_thread_shutdown():
                if server:
                    try:
                        server.unlisten()  # Unbinds OS socket immediately
                        server.stop()
                    except Exception:
                        pass
                io_loop.stop()

            try:
                io_loop.add_callback(_in_thread_shutdown)
            except Exception:
                pass

        if port and sys._panel_server_registry.get(port) is container:
            sys._panel_server_registry.pop(port, None)

        if port:
            print(f"Server on port {port} stopped cleanly.")

    @staticmethod
    def _thread_target(app_factory, port, container, ready_event):
        async_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(async_loop)
        io_loop = IOLoop.current()

        server = get_server(
            app_factory,
            port=port,
            loop=io_loop,
            start=False,
            show=False,
        )
        server.start()

        container["server"] = server
        container["io_loop"] = io_loop
        ready_event.set()

        io_loop.start()

    def start(self,show=True):
        if self.thread and self.thread.is_alive():
            return

        # Reclaim port if a previous server container exists
        if self.port in sys._panel_server_registry:
            old_container = sys._panel_server_registry.get(self.port)
            PanelServer._stop_container(old_container)

        container = {"port": self.port}
        ready_event = threading.Event()

        # Finalizer is bound ONLY to this wrapper instance
        self._finalizer = weakref.finalize(
            self, PanelServer._stop_container, container
        )

        self.thread = threading.Thread(
            target=PanelServer._thread_target,
            args=(self.app_factory, self.port, container, ready_event),
            daemon=True,
        )
        container["thread"] = self.thread

        sys._panel_server_registry[self.port] = container
        
        url = f"http://localhost:{self.port}"
        self.thread.start()
        ready_event.wait()
        print(f"Background explorer running at {url}")
        webbrowser.open(url)

    def stop(self):
        if self._finalizer and self._finalizer.alive:
            self._finalizer()
        else:
            container = sys._panel_server_registry.get(self.port)
            PanelServer._stop_container(container)

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()


def launch_server(app_or_factory, port: int = 5006) -> PanelServer:
    """Helper function to construct, start, and return a non-blocking PanelServer."""
    if hasattr(app_or_factory, "create_app"):
        factory = app_or_factory.create_app
    elif hasattr(app_or_factory, "get_app"):
        factory = app_or_factory.get_app
    elif callable(app_or_factory):
        factory = app_or_factory
    else:
        factory = lambda: app_or_factory

    server = PanelServer(factory, port=port)
    server.start()
    return server