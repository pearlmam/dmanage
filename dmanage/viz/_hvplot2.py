import asyncio
import functools
import threading
import time
import webbrowser
import numpy as np
import pandas as pd
import panel as pn
import holoviews as hv
import hvplot.pandas
from bokeh.models import ColumnDataSource, CustomJS, Legend, LegendItem
from panel.io.server import get_server

__all__ = ["BasePanelServer", "HvPlotExplorer", "HvPlotExplorer2", "sanitize_df"]


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

# =============================================================================
# BASE SERVER CLASS (Context Manager & Thread Management)
# =============================================================================
class BasePanelServer:
    """Base class managing background thread lifecycle and sockets via Context Manager."""

    _ACTIVE_SERVERS = {}

    def __init__(self, port: int = 5006):
        self.port = port
        self._server = None
        self._loop = None
        self._thread = None

    def __enter__(self):
        """Context manager entry point."""
        self.start(show=True)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit point to guarantee clean teardown."""
        self.stop()

    @classmethod
    def stop_port(cls, port: int):
        """Stops any active server running on the target port."""
        if port in cls._ACTIVE_SERVERS:
            server_instance = cls._ACTIVE_SERVERS.pop(port)
            server_instance.stop()

    def create_app(self) -> pn.viewable.Viewable:
        """Override in subclasses to build and return the Panel layout."""
        raise NotImplementedError("Subclasses must implement create_app().")

    def _run_server_thread(self, ready_event: threading.Event):
        """Initializes and runs the event loop in a background thread."""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)

        self._server = get_server(
            self.create_app,
            port=self.port,
            start=False,
            show=False,
            websocket_origin="*",
        )

        BasePanelServer._ACTIVE_SERVERS[self.port] = self
        self._server.start()
        ready_event.set()
        self._loop.run_forever()

    def start(self, show: bool = True):
        """Starts the Panel app non-blockingly in a background thread."""
        BasePanelServer.stop_port(self.port)
        pn.extension()

        ready_event = threading.Event()
        self._thread = threading.Thread(
            target=self._run_server_thread, args=(ready_event,), daemon=True
        )
        self._thread.start()

        ready_event.wait(timeout=2.0)

        url = f"http://localhost:{self.port}"
        if show:
            time.sleep(0.1)
            webbrowser.open(url)

        print(f"Background explorer running at {url}")
        return self

    def stop(self):
        """Explicitly unbinds sockets and stops the background thread loop."""
        BasePanelServer._ACTIVE_SERVERS.pop(self.port, None)

        if self._server is not None:
            try:
                self._server.unlisten()
                self._server.stop()
                if hasattr(self._server, "io_loop") and self._server.io_loop:
                    self._server.io_loop.add_callback(self._server.io_loop.stop)
                print(f"Port {self.port} sockets unbound.")
            except Exception as e:
                print(f"Error releasing port {self.port}: {e}")
            finally:
                self._server = None

        if self._loop is not None and self._loop.is_running():
            try:
                self._loop.call_soon_threadsafe(self._loop.stop)
                print(f"Thread event loop on port {self.port} halted.")
            except Exception as e:
                print(f"Error stopping event loop: {e}")
            finally:
                self._loop = None

# =============================================================================
# IMPLEMENTATION 1: MODULAR INSTANCE-BASED HVPLOT EXPLORER
# =============================================================================
class HvPlotExplorer(BasePanelServer):
    """Interactive Panel Explorer using instance methods and context management."""

    MARKER_PALETTE = [
        "circle", "square", "triangle", "diamond", 
        "star", "cross", "hex", "asterisk"
    ]

    def __init__(self, df: pd.DataFrame, port: int = 5006):
        super().__init__(port=port)
        self.df = sanitize_df(df)
        self.tap_stream = hv.streams.Tap()

        # Cache column groups
        self._all_cols = list(self.df.columns)
        self._num_cols = list(self.df.select_dtypes(include=[np.number]).columns)
        self._cat_cols = list(
            self.df.select_dtypes(include=["object", "category", "string"]).columns
        )

        self._init_widgets()

    def _init_widgets(self):
        """Initializes all control widgets as instance attributes."""
        WIDGET_WIDTH = 180

        self.x_widget = pn.widgets.Select(
            name="X Axis",
            options=self._all_cols,
            value=self._num_cols[0] if self._num_cols else self._all_cols[0],
            width=WIDGET_WIDTH,
        )
        self.y_widget = pn.widgets.Select(
            name="Y Axis",
            options=self._all_cols,
            value=self._num_cols[1] if len(self._num_cols) > 1 else self._all_cols[0],
            width=WIDGET_WIDTH,
        )
        self.by_widget = pn.widgets.Select(
            name="Color By",
            options=["None"] + self._all_cols,
            value="None",
            width=WIDGET_WIDTH,
        )
        self.marker_by_widget = pn.widgets.Select(
            name="Marker By Column",
            options=["None"] + self._cat_cols,
            value="None",
            width=WIDGET_WIDTH,
        )
        self.groupby_widget = pn.widgets.Select(
            name="Group By",
            options=["None"] + self._all_cols,
            value="None",
            width=WIDGET_WIDTH,
        )
        self.agg_widget = pn.widgets.Select(
            name="Aggregation",
            options=["mean", "sum", "count", "min", "max", "std"],
            value="mean",
            width=WIDGET_WIDTH,
        )
        self.cat_col_widget = pn.widgets.Select(
            name="Categorize Numeric",
            options=["None"] + self._num_cols,
            value="None",
            width=WIDGET_WIDTH,
        )
        self.bins_widget = pn.widgets.IntInput(
            name="Number of Bins",
            value=4,
            start=2,
            end=20,
            width=WIDGET_WIDTH,
        )
        self.add_cat_btn = pn.widgets.Button(
            name="Create Category",
            button_type="primary",
            width=WIDGET_WIDTH,
        )
        self.status_pane = pn.pane.Markdown("", width=WIDGET_WIDTH)

        # Wire up instance callbacks
        self.add_cat_btn.on_click(self._on_add_category)

    def _on_add_category(self, event):
        """Instance handler for dynamic binning."""
        target_col = self.cat_col_widget.value
        n_bins = self.bins_widget.value

        if target_col == "None" or not n_bins or n_bins < 2:
            self.status_pane.object = "*Select a column and valid bins (>1).*"
            return

        try:
            new_col_name = f"{target_col}_bin{n_bins}"
            counter = 1
            base_name = new_col_name
            while new_col_name in self.df.columns:
                new_col_name = f"{base_name}_{counter}"
                counter += 1

            self.df[new_col_name] = pd.cut(self.df[target_col], bins=n_bins).astype(str)

            # Refresh local column lists
            self._all_cols = list(self.df.columns)
            self._num_cols = list(self.df.select_dtypes(include=[np.number]).columns)
            self._cat_cols = list(
                self.df.select_dtypes(include=["object", "category", "string"]).columns
            )

            # Update widget choices
            self.x_widget.options = self._all_cols
            self.y_widget.options = self._all_cols
            self.by_widget.options = ["None"] + self._all_cols
            self.groupby_widget.options = ["None"] + self._all_cols
            self.marker_by_widget.options = ["None"] + self._cat_cols
            self.cat_col_widget.options = ["None"] + self._num_cols

            self.by_widget.value = new_col_name
            self.status_pane.object = f"✓ Added **{new_col_name}**"
        except Exception as e:
            self.status_pane.object = f"*Error:* {e}"

    def _add_marker_legend_hook(self, plot, element, marker_by: str, shape_map: dict):
        """Bokeh JS hook for interactive marker legend toggling."""
        if not plot or "plot" not in plot.handles:
            return

        bokeh_fig = plot.handles["plot"]
        main_renderers = [
            r for r in bokeh_fig.renderers
            if hasattr(r, "data_source") and r.data_source and marker_by in r.data_source.data
        ]
        main_sources = [r.data_source for r in main_renderers]

        for r in main_renderers:
            ds = r.data_source
            n_pts = len(next(iter(ds.data.values()))) if ds.data else 0
            if n_pts == 0 or getattr(ds, "_alpha_initialized", False):
                continue

            base_size = float(r.glyph.size) if isinstance(r.glyph.size, (int, float)) else 10.0
            ds.data["_alpha"] = np.ones(n_pts, dtype=float)
            ds.data["_orig_size"] = np.full(n_pts, base_size, dtype=float)
            ds.data["_size"] = np.full(n_pts, base_size, dtype=float)
            ds._alpha_initialized = True

            r.glyph.fill_alpha = "_alpha"
            r.glyph.line_alpha = "_alpha"
            r.glyph.size = "_size"

        if marker_by and marker_by != "None" and shape_map and main_renderers:
            legend_items = []
            for val, shape in shape_map.items():
                dummy_ds = ColumnDataSource(data=dict(x=[np.nan], y=[np.nan]))
                dummy_r = bokeh_fig.scatter(
                    x="x", y="y", source=dummy_ds, marker=shape,
                    fill_color="#555555", line_color="#222222", size=10, fill_alpha=0.8
                )

                js_code = """
                    const is_visible = cb_obj.visible;
                    const target_val = String(val);
                    for (let src of sources) {
                        const data = src.data;
                        if (!data[marker_by]) continue;
                        const markers = data[marker_by];
                        const alpha = data['_alpha'];
                        const size = data['_size'];
                        const orig_size = data['_orig_size'];
                        let modified = false;
                        for (let i = 0; i < markers.length; i++) {
                            if (String(markers[i]) === target_val) {
                                alpha[i] = is_visible ? 1.0 : 0.15;
                                size[i] = orig_size[i];
                                modified = true;
                            }
                        }
                        if (modified) src.change.emit();
                    }
                """
                toggle_cb = CustomJS(
                    args=dict(sources=main_sources, val=str(val), marker_by=marker_by),
                    code=js_code,
                )
                dummy_r.js_on_change("visible", toggle_cb)
                legend_items.append(LegendItem(label=str(val), renderers=[dummy_r]))

            marker_legend = Legend(
                items=legend_items, title=f"Marker: {marker_by}",
                background_fill_alpha=0.8, margin=5, location="top_left", click_policy="hide"
            )
            bokeh_fig.add_layout(marker_legend, "right")

    def _prepare_data(self, x: str, y: str, by: str, groupby_col: str, agg_func: str) -> pd.DataFrame:
        """Applies grouping and aggregation logic to the active dataset."""
        temp_df = self.df.copy()
        if groupby_col == "None":
            return temp_df

        group_keys = [groupby_col]
        if x != groupby_col and x in temp_df.columns and not pd.api.types.is_numeric_dtype(temp_df[x]):
            group_keys.append(x)
        if by != "None" and by != groupby_col and by not in group_keys and not pd.api.types.is_numeric_dtype(temp_df[by]):
            group_keys.append(by)

        try:
            if agg_func == "count":
                temp_df = temp_df.groupby(group_keys, as_index=False).size().rename(columns={"size": y})
            else:
                temp_df = temp_df.groupby(group_keys, as_index=False).agg(agg_func, numeric_only=True)
        except Exception as e:
            print(f"Aggregation error: {e}")

        return temp_df

    def _create_plot(self, x, y, by, marker_by, groupby_col, agg_func):
        """Generates the main hvPlot instance."""
        temp_df = self._prepare_data(x, y, by, groupby_col, agg_func)

        plot_kwargs = dict(
            x=x, y=y, size=120, height=420, responsive=True, tools=["tap", "box_select"]
        )

        if by != "None" and by in temp_df.columns:
            if pd.api.types.is_numeric_dtype(temp_df[by]):
                plot_kwargs.update(c=by, cmap="viridis", colorbar=True)
            else:
                plot_kwargs.update(by=by, legend="right")

        shape_map = {}
        if marker_by != "None" and marker_by in temp_df.columns:
            unique_vals = list(temp_df[marker_by].dropna().unique())
            shape_map = {val: self.MARKER_PALETTE[i % len(self.MARKER_PALETTE)] for i, val in enumerate(unique_vals)}
            temp_df["_marker_shape"] = temp_df[marker_by].map(shape_map)
            plot_kwargs["marker"] = "_marker_shape"
            plot_kwargs["hover_cols"] = [marker_by]
        else:
            plot_kwargs["marker"] = "circle"

        hook = lambda plot, element: self._add_marker_legend_hook(plot, element, marker_by, shape_map)
        plot = temp_df.hvplot.scatter(**plot_kwargs).opts(hooks=[hook])
        self.tap_stream.source = plot
        return plot

    def _find_closest_record(self, x_col: str, y_col: str, x: float, y: float) -> pd.DataFrame:
        """Finds closest row to user tap coordinates."""
        x_vals = pd.to_numeric(self.df[x_col], errors="coerce")
        y_vals = pd.to_numeric(self.df[y_col], errors="coerce")

        if x_vals.notna().any() and y_vals.notna().any():
            x_scale = x_vals.std() if (pd.notna(x_vals.std()) and x_vals.std() > 0) else 1.0
            y_scale = y_vals.std() if (pd.notna(y_vals.std()) and y_vals.std() > 0) else 1.0
            dist = np.sqrt(((x_vals - x) / x_scale) ** 2 + ((y_vals - y) / y_scale) ** 2)
            return self.df.loc[[dist.idxmin()]]

        return self.df[(self.df[x_col] == x) & (self.df[y_col] == y)]

    def _render_details(self, x_col, y_col, x, y):
        """Displays selected point details."""
        if x is None or y is None:
            return pn.pane.Markdown("### Details Panel\n*Click any point on the plot above to display details here.*")

        selected_rows = self._find_closest_record(x_col, y_col, x, y)
        if selected_rows.empty:
            return pn.pane.Markdown("*No record found for click location.*")

        records = selected_rows.to_dict(orient="records")
        return pn.Column(
            pn.pane.Markdown(f"### Selected Record Details (Index {selected_rows.index[0]})"),
            pn.pane.JSON(records[0], depth=3, theme="light"),
        )

    def create_app(self) -> pn.viewable.Viewable:
        """Assembles layout with bound instance methods."""
        plot_pane = pn.bind(
            self._create_plot,
            x=self.x_widget,
            y=self.y_widget,
            by=self.by_widget,
            marker_by=self.marker_by_widget,
            groupby_col=self.groupby_widget,
            agg_func=self.agg_widget,
        )

        details_pane = pn.bind(
            self._render_details,
            x_col=self.x_widget,
            y_col=self.y_widget,
            x=self.tap_stream.param.x,
            y=self.tap_stream.param.y,
        )

        controls_tab = pn.Column(
            self.x_widget, self.y_widget, self.by_widget, self.marker_by_widget,
            pn.layout.Divider(), self.groupby_widget, self.agg_widget, margin=(10, 5)
        )
        binning_tab = pn.Column(
            self.cat_col_widget, self.bins_widget, self.add_cat_btn, self.status_pane, margin=(10, 5)
        )
        sidebar_tabs = pn.Tabs(("Controls", controls_tab), ("Bin Numeric", binning_tab), width=210)

        top_row = pn.Row(sidebar_tabs, pn.Column(plot_pane, sizing_mode="stretch_width"), sizing_mode="stretch_width")
        bottom_row = pn.Column(pn.layout.Divider(), details_pane, sizing_mode="stretch_width")

        return pn.Column(top_row, bottom_row, sizing_mode="stretch_width")


# =============================================================================
# IMPLEMENTATION 2: NATIVE HVPLOT EXPLORER
# =============================================================================
class HvPlotExplorer2(BasePanelServer):
    """Wrapper managing native `df.hvplot.explorer()` inside an isolated Panel server."""

    def __init__(self, df: pd.DataFrame, port: int = 5006, **explorer_kwargs):
        super().__init__(port=port)
        self.df = df
        self.explorer_kwargs = explorer_kwargs

    def create_app(self) -> pn.viewable.Viewable:
        df_clean = sanitize_df(self.df)
        return df_clean.hvplot.explorer(**self.explorer_kwargs)


# =============================================================================
# USAGE EXAMPLE
# =============================================================================
if __name__ == "__main__":
    df = pd.DataFrame({
        "x": np.random.randn(100),
        "y": np.random.randn(100),
        "category": np.random.choice(["A", "B", "C"], size=100),
    })

    # Guaranteed socket cleanup & thread termination on block exit:
    with HvPlotExplorer(df, port=5006) as exp:
        time.sleep(5)  # Keep running while inspecting in the browser