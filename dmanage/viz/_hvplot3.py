import asyncio
import threading
import time
import webbrowser
import numpy as np
import pandas as pd
import panel as pn
import param
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
# REFACTORED PARAMETERIZED EXPLORER
# =============================================================================
class HvPlotExplorer(BasePanelServer, param.Parameterized):
    """Declarative Interactive Explorer powered by param.Parameterized."""

    # Plotting Controls
    x = param.Selector(doc="X Axis Column")
    y = param.Selector(doc="Y Axis Column")
    color_by = param.Selector(default="None", doc="Color By Column")
    marker_by = param.Selector(default="None", doc="Marker Shape Column")
    group_by = param.Selector(default="None", doc="Group By Column")
    aggregation = param.Selector(
        default="mean",
        objects=["mean", "sum", "count", "min", "max", "std"],
        doc="Aggregation Function",
    )

    # Dynamic Binning Controls
    cat_col = param.Selector(default="None", doc="Column to Bin")
    n_bins = param.Integer(default=4, bounds=(2, 20), doc="Number of Bins")
    create_category = param.Action(
        lambda self: self._add_category_action(), label="Create Category"
    )
    status_msg = param.String(default="", doc="Status Message")

    MARKER_PALETTE = ["circle", "square", "triangle", "diamond", "star", "cross", "hex", "asterisk"]

    def __init__(self, df: pd.DataFrame, port: int = 5006, **params):
        BasePanelServer.__init__(self, port=port)
        param.Parameterized.__init__(self, **params)

        self.df = sanitize_df(df)
        self.tap_stream = hv.streams.Tap()
        self._update_column_options()

        # Set sensible default axis choices
        all_cols = self.param.x.objects
        num_cols = list(self.df.select_dtypes(include=[np.number]).columns)
        self.x = num_cols[0] if num_cols else all_cols[0]
        self.y = num_cols[1] if len(num_cols) > 1 else all_cols[0]

    def _update_column_options(self):
        """Updates Parameter options dynamically when columns change."""
        all_cols = list(self.df.columns)
        num_cols = list(self.df.select_dtypes(include=[np.number]).columns)
        cat_cols = list(self.df.select_dtypes(include=["object", "category", "string"]).columns)

        self.param.x.objects = all_cols
        self.param.y.objects = all_cols
        self.param.color_by.objects = ["None"] + all_cols
        self.param.group_by.objects = ["None"] + all_cols
        self.param.marker_by.objects = ["None"] + cat_cols
        self.param.cat_col.objects = ["None"] + num_cols

    def _add_category_action(self):
        """Action handler to bin numeric columns into discrete string categories."""
        if self.cat_col == "None" or self.n_bins < 2:
            self.status_msg = "*Select a valid column and bins (>1).*"
            return
        try:
            new_col_name = f"{self.cat_col}_bin{self.n_bins}"
            counter = 1
            base_name = new_col_name
            while new_col_name in self.df.columns:
                new_col_name = f"{base_name}_{counter}"
                counter += 1

            self.df[new_col_name] = pd.cut(self.df[self.cat_col], bins=self.n_bins).astype(str)
            self._update_column_options()
            self.color_by = new_col_name
            self.status_msg = f"✓ Added **{new_col_name}**"
        except Exception as e:
            self.status_msg = f"*Error:* {e}"

    def _prepare_data(self) -> pd.DataFrame:
        """Applies grouping and aggregation state to dataset."""
        temp_df = self.df.copy()
        if self.group_by == "None":
            return temp_df
    
        group_keys = [self.group_by]
    
        # Include categorical X axis
        if (
            self.x != self.group_by
            and self.x in temp_df.columns
            and not pd.api.types.is_numeric_dtype(temp_df[self.x])
        ):
            group_keys.append(self.x)
    
        # Include categorical Color By
        if (
            self.color_by != "None"
            and self.color_by not in group_keys
            and self.color_by in temp_df.columns
            and not pd.api.types.is_numeric_dtype(temp_df[self.color_by])
        ):
            group_keys.append(self.color_by)
    
        # Include categorical Marker By
        if (
            self.marker_by != "None"
            and self.marker_by not in group_keys
            and self.marker_by in temp_df.columns
            and not pd.api.types.is_numeric_dtype(temp_df[self.marker_by])
        ):
            group_keys.append(self.marker_by)
    
        try:
            if self.aggregation == "count":
                temp_df = (
                    temp_df.groupby(group_keys, as_index=False)
                    .size()
                    .rename(columns={"size": self.y})
                )
            else:
                temp_df = temp_df.groupby(group_keys, as_index=False).agg(
                    self.aggregation, numeric_only=True
                )
        except Exception as e:
            print(f"Aggregation error: {e}")
    
        return temp_df

    def _add_marker_legend_hook(self, plot, element, shape_map):
        bokeh_fig = plot.handles["plot"]
    
        # 1. Align existing right-panel items (ColorBy legend/colorbar) to top
        for item in bokeh_fig.right:
            if hasattr(item, "location"):
                item.location = "top_right" if item.__class__.__name__ == "ColorBar" else "top"
    
        # 2. Identify scatter renderers
        main_sources = []
        main_renderers = []
        for r in bokeh_fig.renderers:
            if hasattr(r, "data_source") and r.data_source:
                ds_data = r.data_source.data
                if ds_data and ("_marker_shape" in ds_data or (self.marker_by != "None" and self.marker_by in ds_data)):
                    main_sources.append(r.data_source)
                    main_renderers.append(r)
    
        # 3. Shield native ColorBy legend swatches from vector _alpha changes
        for legend in list(bokeh_fig.right) + list(bokeh_fig.center):
            if isinstance(legend, Legend):
                for item in legend.items:
                    if item.renderers and item.renderers[0] in main_renderers:
                        orig_r = item.renderers[0]
                        fc = getattr(orig_r.glyph, "fill_color", "#555555")
                        lc = getattr(orig_r.glyph, "line_color", fc)
    
                        # Create dummy renderer with scalar fill_alpha=1.0 for swatch drawing
                        dummy_ds = ColumnDataSource(data=dict(x=[np.nan], y=[np.nan]))
                        dummy_r = bokeh_fig.scatter(
                            x="x", y="y", source=dummy_ds,
                            fill_color=fc, line_color=lc,
                            fill_alpha=1.0, line_alpha=1.0, size=10
                        )
                        # Prepending ensures Bokeh uses dummy_r to render the legend swatch
                        item.renderers = [dummy_r] + list(item.renderers)
    
        # 4. Bind glyph attributes to vector fields for scatter renderers
        for r in main_renderers:
            ds = r.data_source
            n_pts = len(next(iter(ds.data.values()))) if ds.data else 0
            if n_pts == 0:
                continue
    
            base_size = float(r.glyph.size) if isinstance(r.glyph.size, (int, float)) else 12.0
    
            if "_alpha" not in ds.data:
                ds.data["_alpha"] = np.ones(n_pts, dtype=float)
            if "_size" not in ds.data:
                ds.data["_size"] = np.full(n_pts, base_size, dtype=float)
            if "_orig_size" not in ds.data:
                ds.data["_orig_size"] = np.full(n_pts, base_size, dtype=float)
    
            r.glyph.fill_alpha = "_alpha"
            r.glyph.line_alpha = "_alpha"
            r.glyph.size = "_size"
    
        # 5. Construct Marker legend
        if self.marker_by != "None" and shape_map and main_renderers:
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
                dummy_r.js_on_change(
                    "visible",
                    CustomJS(args=dict(sources=main_sources, val=str(val), marker_by=self.marker_by), code=js_code)
                )
                legend_items.append(LegendItem(label=str(val), renderers=[dummy_r]))
    
            marker_legend = Legend(
                items=legend_items,
                title=f"Marker: {self.marker_by}",
                background_fill_alpha=0.8,
                margin=5,
                location="top",
                click_policy="hide"
            )
    
            bokeh_fig.add_layout(marker_legend, "right")
        
    
    @param.depends("x", "y", "color_by", "marker_by", "group_by", "aggregation")
    def make_plot(self):
        temp_df = self._prepare_data()

        plot_kwargs = dict(
            x=self.x, y=self.y, size=120, height=420, responsive=True, tools=["tap", "box_select"]
        )

        if self.color_by != "None" and self.color_by in temp_df.columns:
            if pd.api.types.is_numeric_dtype(temp_df[self.color_by]):
                # Pass colorbar_position inside hvplot kwargs for numeric colorbars
                plot_kwargs.update(
                    c=self.color_by,
                    cmap="viridis",
                    colorbar=True,
                    colorbar_position="right",
                )
            else:
                plot_kwargs.update(by=self.color_by)

        hover_cols = []
        shape_map = {}
        if self.marker_by != "None" and self.marker_by in temp_df.columns:
            unique_vals = list(temp_df[self.marker_by].dropna().unique())
            shape_map = {
                val: self.MARKER_PALETTE[i % len(self.MARKER_PALETTE)]
                for i, val in enumerate(unique_vals)
            }
            temp_df["_marker_shape"] = temp_df[self.marker_by].map(shape_map)
            plot_kwargs["marker"] = "_marker_shape"
            hover_cols.append(self.marker_by)

        if hover_cols:
            plot_kwargs["hover_cols"] = hover_cols

        hook = lambda plot, element: self._add_marker_legend_hook(plot, element, shape_map)

        # Only pass options valid for NdOverlay containers here
        plot = temp_df.hvplot.scatter(**plot_kwargs).opts(
            hooks=[hook],
            legend_position="right",
        )
        self.tap_stream.source = plot
        return plot

    def _render_details(self, x, y):
        """Renders click selection details using current axis parameter state."""
        if x is None or y is None:
            return pn.pane.Markdown("### Details Panel\n*Click any point on the plot above to display details here.*")

        x_vals = pd.to_numeric(self.df[self.x], errors="coerce")
        y_vals = pd.to_numeric(self.df[self.y], errors="coerce")

        if x_vals.notna().any() and y_vals.notna().any():
            x_scale = x_vals.std() if (pd.notna(x_vals.std()) and x_vals.std() > 0) else 1.0
            y_scale = y_vals.std() if (pd.notna(y_vals.std()) and y_vals.std() > 0) else 1.0
            dist = np.sqrt(((x_vals - x) / x_scale) ** 2 + ((y_vals - y) / y_scale) ** 2)
            selected_rows = self.df.loc[[dist.idxmin()]]
        else:
            selected_rows = self.df[(self.df[self.x] == x) & (self.df[self.y] == y)]

        if selected_rows.empty:
            return pn.pane.Markdown("*No record found for click location.*")

        records = selected_rows.to_dict(orient="records")
        return pn.Column(
            pn.pane.Markdown(f"### Selected Record Details (Index {selected_rows.index[0]})"),
            pn.pane.JSON(records[0], depth=3, theme="light"),
        )

    def create_app(self) -> pn.viewable.Viewable:
        """Assembles user interface declarative components with compact widgets."""
        CONTROL_WIDTH = 150  # Target width for all dropdowns and inputs

        # Custom widget overrides for Param
        controls_widgets = {
            p: {"width": CONTROL_WIDTH}
            for p in ["x", "y", "color_by", "marker_by", "group_by", "aggregation"]
        }
        
        binning_widgets = {
            "cat_col": {"width": CONTROL_WIDTH},
            "n_bins": {"width": CONTROL_WIDTH},
            "create_category": {"width": CONTROL_WIDTH, "button_type": "primary"},
        }

        # Auto-generated parameter controls with custom width
        controls_ui = pn.Param(
            self.param,
            parameters=["x", "y", "color_by", "marker_by", "group_by", "aggregation"],
            widgets=controls_widgets,
            name="Controls",
            width=CONTROL_WIDTH + 20,
        )

        binning_ui = pn.Column(
            pn.Param(
                self.param,
                parameters=["cat_col", "n_bins", "create_category"],
                widgets=binning_widgets,
                name="Binning",
                width=CONTROL_WIDTH + 20,
            ),
            pn.pane.Markdown(self.param.status_msg, width=CONTROL_WIDTH + 20),
        )

        sidebar_tabs = pn.Tabs(
            ("Controls", controls_ui),
            ("Bin Numeric", binning_ui),
            width=CONTROL_WIDTH + 30,
        )

        # Bind HoloViews tap coordinates to detail pane renderer
        details_pane = pn.bind(
            self._render_details,
            x=self.tap_stream.param.x,
            y=self.tap_stream.param.y,
        )

        top_row = pn.Row(
            sidebar_tabs,
            pn.Column(self.make_plot, sizing_mode="stretch_width"),
            sizing_mode="stretch_width",
        )
        bottom_row = pn.Column(
            pn.layout.Divider(), details_pane, sizing_mode="stretch_width"
        )

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

    with HvPlotExplorer(df, port=5006) as exp:
        while True:
            time.sleep(2)