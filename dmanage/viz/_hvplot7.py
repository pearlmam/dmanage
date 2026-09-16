# -*- coding: utf-8 -*-
import sys
import time
import json
import asyncio
import threading
import weakref
import numpy as np
import pandas as pd
import panel as pn
import param
import holoviews as hv
import hvplot.pandas
from bokeh.models import ColumnDataSource, CustomJS, Legend, LegendItem,Slider
from panel.io.server import get_server
from tornado.ioloop import IOLoop
import webbrowser

hv.extension('bokeh')

__all__ = [
    "PanelServer",
    "launch_server",
    "HvPlotExplorer",
    "HvPlotExplorer2",
    "sanitize_df",
]


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


# =============================================================================
# PARAMETERIZED EXPLORER WITH IMMUTABLE MARKERS
# =============================================================================


class HvPlotExplorer(param.Parameterized):
    """Declarative Interactive Explorer supporting multi-column Color and Marker grouping."""

    x = param.Selector(doc="X Axis Column")
    y = param.Selector(doc="Y Axis Column")
    color_by = param.ListSelector(default=[], doc="Color By Column(s)")
    marker_by = param.ListSelector(default=[], doc="Marker Shape Column(s)")
    group_by = param.Selector(default="None", doc="Group By Column")
    aggregation = param.Selector(
        default="mean",
        objects=["mean", "sum", "count", "min", "max", "std"],
        doc="Aggregation Function",
    )

    cat_col = param.Selector(default="None", doc="Column to Bin")
    n_bins = param.Integer(default=4, bounds=(2, 20), doc="Number of Bins")
    create_category = param.Action(
        lambda self: self._add_category_action(), label="Create Category"
    )
    status_msg = param.String(default="", doc="Status Message")

    MARKER_PALETTE = [
        "circle", "square", "triangle", "diamond", "star",
        "cross", "hex", "asterisk", "inverted_triangle", "plus"
    ]

    def __init__(self, df: pd.DataFrame, **params):
        super().__init__(**params)
        self.df = sanitize_df(df)
        self.tap_stream = hv.streams.Tap()
        self._main_sources = []

        # 1. Initialize Options Widgets persistent instances
        self.opacity_slider = Slider(
            start=0.0, end=1.0, value=0.15, step=0.05,
            title="Deselected Opacity", width=160,
            name="deselected_opacity_slider"
        )

        # 2. Assemble Plot Options Layout once
        self._options_layout = pn.Column(
            pn.pane.Markdown("### Plot Options"),
            pn.pane.Bokeh(self.opacity_slider),
            width=180,
        )

        self._update_column_options()

        all_cols = self.param.x.objects
        num_cols = list(self.df.select_dtypes(include=[np.number]).columns)
        self.x = num_cols[0] if num_cols else all_cols[0]
        self.y = num_cols[1] if len(num_cols) > 1 else all_cols[0]

    def _update_column_options(self):
        all_cols = list(self.df.columns)
        num_cols = list(self.df.select_dtypes(include=[np.number]).columns)
        cat_cols = list(
            self.df.select_dtypes(
                include=["object", "category", "string", "datetime", "datetimetz", "bool"]
            ).columns
        )

        self.param.x.objects = all_cols
        self.param.y.objects = all_cols
        self.param.color_by.objects = all_cols
        self.param.marker_by.objects = cat_cols
        self.param.group_by.objects = ["None"] + all_cols
        self.param.cat_col.objects = ["None"] + num_cols

    def _add_category_action(self):
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
            self.color_by = [new_col_name]
            self.status_msg = f"✓ Added **{new_col_name}**"
        except Exception as e:
            self.status_msg = f"*Error:* {e}"

    def _prepare_data(self) -> pd.DataFrame:
        temp_df = self.df.copy()
        if self.group_by == "None":
            return temp_df

        color_cols = [c for c in (self.color_by or []) if c in temp_df.columns]
        marker_cols = [c for c in (self.marker_by or []) if c in temp_df.columns]

        group_keys = [self.group_by]
        for c in [self.x] + color_cols + marker_cols:
            if c in temp_df.columns and c not in group_keys:
                if not pd.api.types.is_numeric_dtype(temp_df[c]):
                    group_keys.append(c)

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

    def _add_marker_legend_hook(self, plot, element, shape_map, marker_cols):
        bokeh_fig = plot.handles["plot"]

        # Shared JavaScript helper string to calculate alpha and emit changes
        JS_UPDATE_ALPHA = """
        function updateSourceAlpha(src, inactiveAlpha) {
            const d = src.data;
            if (!d || !d['_alpha']) return;
            const ca = d['_color_active'], ma = d['_marker_active'];
            const calpha = d['_color_alpha'], malpha = d['_marker_alpha'], alpha = d['_alpha'];
            for (let i = 0; i < alpha.length; i++) {
                calpha[i] = ca[i] ? 1.0 : inactiveAlpha;
                malpha[i] = ma[i] ? 1.0 : inactiveAlpha;
                alpha[i] = Math.min(calpha[i], malpha[i]);
            }
            src.data = Object.assign({}, src.data);
            src.change.emit();
        }
        """

        # 1. Deduplicate & configure tools
        seen_tools = set()
        unique_tools = []
        wheel_zoom, hover_tool = None, None

        for t in bokeh_fig.tools:
            ttype = type(t).__name__
            if ttype == "WheelZoomTool":
                wheel_zoom = t
            elif ttype == "HoverTool":
                hover_tool = t

            if ttype in {"ResetTool", "PanTool", "WheelZoomTool", "BoxZoomTool", "SaveTool", "HoverTool"}:
                if ttype in seen_tools:
                    continue
                seen_tools.add(ttype)

            if ttype in {"TapTool", "BoxSelectTool", "LassoSelectTool", "PolySelectTool"}:
                if hasattr(t, "renderers"):
                    t.renderers = []

            unique_tools.append(t)

        bokeh_fig.tools = unique_tools
        if wheel_zoom:
            bokeh_fig.toolbar.active_scroll = wheel_zoom

        # 2. Collect renderers & initialize CDS arrays
        main_sources, main_renderers = [], []
        self._main_sources = main_sources

        for r in bokeh_fig.renderers:
            if hasattr(r, "glyph") and hasattr(r.glyph, "marker") and hasattr(r, "data_source"):
                if getattr(r, "name", None) == "dummy_legend_renderer":
                    continue
                main_renderers.append(r)
                if r.data_source not in main_sources:
                    main_sources.append(r.data_source)

                r.selection_glyph = r.glyph
                r.nonselection_glyph = r.glyph
                r.hover_glyph = None

                ds = r.data_source
                if ds and ds.data:
                    n_pts = len(next(iter(ds.data.values()), []))
                    if n_pts > 0:
                        for col, default_val in [
                            ("_color_active", 1), ("_marker_active", 1),
                            ("_color_alpha", 1.0), ("_marker_alpha", 1.0), ("_alpha", 1.0)
                        ]:
                            if col not in ds.data or len(ds.data[col]) != n_pts:
                                ds.data[col] = np.full(n_pts, default_val)

                    r.glyph.fill_alpha = {"field": "_alpha"}
                    r.glyph.line_alpha = {"field": "_alpha"}

        # Filter out internal/composite columns from HoverTool tooltips UI
        if hover_tool and main_renderers:
            hover_tool.renderers = main_renderers
            if isinstance(hover_tool.tooltips, list):
                exclude_fields = {
                    "marker_composite", "_marker_shape", "color_composite",
                    "_color_active", "_marker_active", "_color_alpha",
                    "_marker_alpha", "_alpha"
                }
                hover_tool.tooltips = [
                    item for item in hover_tool.tooltips
                    if item[0] not in exclude_fields and not str(item[0]).startswith("_")
                ]

        # 3. Bind Opacity Slider JS Callback
        self.opacity_slider.js_property_callbacks.clear()
        self.opacity_slider.js_on_change("value", CustomJS(
            args=dict(sources=main_sources, slider=self.opacity_slider),
            code=JS_UPDATE_ALPHA + """
                for (let src of sources) {
                    updateSourceAlpha(src, slider.value);
                }
            """
        ))

        containers = [bokeh_fig.above, bokeh_fig.below, bokeh_fig.left, bokeh_fig.right, bokeh_fig.center]

        # 4. Remove existing custom marker legend
        for c in containers:
            for item in list(c):
                if isinstance(item, Legend) and getattr(item, "name", None) == "marker_legend":
                    c.remove(item)

        # 5. Decouple Color Legend items
        for c in containers:
            for legend in list(c):
                if isinstance(legend, Legend) and getattr(legend, "name", None) != "marker_legend":
                    legend.click_policy = "hide"
                    for item in legend.items:
                        reals = [r for r in item.renderers if r in main_renderers]
                        if not reals:
                            continue

                        target_r = reals[0]
                        target_src = target_r.data_source

                        fill_c = getattr(target_r.glyph, "fill_color", "#555555")
                        line_c = getattr(target_r.glyph, "line_color", "#222222")
                        m_shape = getattr(target_r.glyph, "marker", "circle")

                        fill_c = fill_c if isinstance(fill_c, (str, tuple, list)) else "#555555"
                        line_c = line_c if isinstance(line_c, (str, tuple, list)) else "#222222"
                        m_shape = m_shape if isinstance(m_shape, str) else "circle"

                        dummy_ds = ColumnDataSource(data=dict(x=[np.nan], y=[np.nan]))
                        dummy_r = bokeh_fig.scatter(
                            x="x", y="y", source=dummy_ds, marker=m_shape,
                            fill_color=fill_c, line_color=line_c, size=10,
                            name="dummy_legend_renderer"
                        )
                        dummy_r.visible = True
                        item.renderers = [dummy_r]

                        cb = CustomJS(
                            args=dict(target_src=target_src, slider=self.opacity_slider),
                            code=JS_UPDATE_ALPHA + """
                                const is_vis = cb_obj.visible;
                                const data = target_src.data;
                                if (!data || !data['_color_active']) return;
                                for (let i = 0; i < data['_color_active'].length; i++) {
                                    data['_color_active'][i] = is_vis ? 1 : 0;
                                }
                                updateSourceAlpha(target_src, slider.value);
                            """
                        )
                        dummy_r.js_on_change("visible", cb)

        # 6. Construct Custom Marker Legend
        if marker_cols and shape_map and main_renderers:
            legend_items = []
            for val, shape in shape_map.items():
                dummy_ds = ColumnDataSource(data=dict(x=[np.nan], y=[np.nan]))
                dummy_r = bokeh_fig.scatter(
                    x="x", y="y", source=dummy_ds, marker=shape,
                    fill_color="#555555", line_color="#222222", size=10,
                    name="dummy_legend_renderer"
                )

                cb = CustomJS(
                    args=dict(sources=main_sources, val=str(val), slider=self.opacity_slider),
                    code=JS_UPDATE_ALPHA + """
                        const is_vis = cb_obj.visible;
                        const target = String(val);
                        for (let src of sources) {
                            const d = src.data;
                            const markers = d['marker_composite'] || d['_marker_composite'];
                            if (!markers || !d['_marker_active']) continue;

                            let mod = false;
                            for (let i = 0; i < markers.length; i++) {
                                if (String(markers[i]) === target) {
                                    d['_marker_active'][i] = is_vis ? 1 : 0;
                                    mod = true;
                                }
                            }
                            if (mod) {
                                updateSourceAlpha(src, slider.value);
                            }
                        }
                    """
                )
                item = LegendItem(label=str(val), renderers=[dummy_r])
                item.js_on_change("visible", cb)
                dummy_r.js_on_change("visible", cb)
                legend_items.append(item)

            marker_legend = Legend(
                items=legend_items, title=f"Marker: {', '.join(marker_cols)}",
                orientation="vertical", background_fill_alpha=0.8,
                margin=5, click_policy="hide", name="marker_legend"
            )
            bokeh_fig.add_layout(marker_legend, "right")

        # 7. Consolidate ALL legends to the right layout panel
        for c in containers:
            for item in list(c):
                if isinstance(item, Legend):
                    item.location = "top_left"
                    if c is not bokeh_fig.right:
                        c.remove(item)
                        bokeh_fig.add_layout(item, "right")

    @param.depends("x", "y", "color_by", "marker_by", "group_by", "aggregation")
    def make_plot(self):
        temp_df = self._prepare_data()

        plot_kwargs = dict(
            x=self.x,
            y=self.y,
            size=120,
            height=420,
            responsive=True,
            tools=["hover"],
        )

        color_cols = [c for c in (self.color_by or []) if c in temp_df.columns]
        marker_cols = [c for c in (self.marker_by or []) if c in temp_df.columns]

        if color_cols:
            if len(color_cols) == 1 and pd.api.types.is_numeric_dtype(temp_df[color_cols[0]]):
                plot_kwargs.update(c=color_cols[0], cmap="viridis", colorbar=True)
            elif len(color_cols) == 1:
                plot_kwargs.update(by=color_cols[0])
            else:
                temp_df["color_composite"] = temp_df[color_cols].apply(
                    lambda col: col.astype(str)
                ).agg(" | ".join, axis=1)
                plot_kwargs.update(by="color_composite")

        shape_map = {}
        hover_cols = []
        if marker_cols:
            if len(marker_cols) == 1:
                temp_df["marker_composite"] = temp_df[marker_cols[0]].astype(str)
            else:
                temp_df["marker_composite"] = temp_df[marker_cols].apply(
                    lambda col: col.astype(str)
                ).agg(" | ".join, axis=1)

            unique_vals = list(temp_df["marker_composite"].dropna().unique())
            shape_map = {
                val: self.MARKER_PALETTE[i % len(self.MARKER_PALETTE)]
                for i, val in enumerate(unique_vals)
            }
            temp_df["_marker_shape"] = temp_df["marker_composite"].map(shape_map)
            plot_kwargs["marker"] = "_marker_shape"
            # Include marker_composite so hvplot creates the column in the Bokeh DataSource
            hover_cols.extend(["marker_composite"] + marker_cols)

        if hover_cols:
            plot_kwargs["hover_cols"] = list(set(hover_cols))

        hook = lambda plot, element: self._add_marker_legend_hook(
            plot, element, shape_map, marker_cols
        )

        plot = temp_df.hvplot.scatter(**plot_kwargs).opts(
            hooks=[hook],
            legend_position="right",
        )
        self.tap_stream.source = plot
        return plot

    def _render_details(self, x, y):
        if x is None or y is None:
            return pn.pane.Markdown(
                "### Details Panel\n*Click any point on the plot above to display details here.*"
            )

        temp_df = self._prepare_data()
        if temp_df.empty or self.x not in temp_df.columns or self.y not in temp_df.columns:
            return pn.pane.Markdown("*No matching data found.*")

        try:
            x_series, target_x = _to_numeric_coords(temp_df[self.x], x)
            y_series, target_y = _to_numeric_coords(temp_df[self.y], y)

            x_std = x_series.std() if (pd.notna(x_series.std()) and x_series.std() > 0) else 1.0
            y_std = y_series.std() if (pd.notna(y_series.std()) and y_series.std() > 0) else 1.0

            dist = np.sqrt(((x_series - target_x) / x_std) ** 2 + ((y_series - target_y) / y_std) ** 2)
            best_idx = dist.idxmin()
            selected_row = temp_df.loc[[best_idx]]

            json_data = json.loads(selected_row.to_json(orient="records", date_format="iso"))[0]

            return pn.Column(
                pn.pane.Markdown(f"### Selected Record Details (Index {best_idx})"),
                pn.pane.JSON(json_data, depth=3, theme="light"),
            )
        except Exception as e:
            return pn.pane.Markdown(f"*Error matching selected point: {e}*")

    def create_app(self) -> pn.viewable.Viewable:
        CONTROL_WIDTH = 160

        controls_widgets = {
            "x": {"width": CONTROL_WIDTH},
            "y": {"width": CONTROL_WIDTH},
            "color_by": {"width": CONTROL_WIDTH, "height": 90},
            "marker_by": {"width": CONTROL_WIDTH, "height": 90},
            "group_by": {"width": CONTROL_WIDTH},
            "aggregation": {"width": CONTROL_WIDTH},
        }

        binning_widgets = {
            "cat_col": {"width": CONTROL_WIDTH},
            "n_bins": {"width": CONTROL_WIDTH},
            "create_category": {"width": CONTROL_WIDTH, "button_type": "primary"},
        }

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
            ("Plot Options", self._options_layout),
            width=CONTROL_WIDTH + 30,
        )

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
# NATIVE HVPLOT EXPLORER WRAPPER
# =============================================================================
class HvPlotExplorer2:
    """Wrapper managing native `df.hvplot.explorer()` layout."""

    def __init__(self, df: pd.DataFrame, **explorer_kwargs):
        self.df = df
        self.explorer_kwargs = explorer_kwargs

    def create_app(self) -> pn.viewable.Viewable:
        df_clean = sanitize_df(self.df)
        return df_clean.hvplot.explorer(**self.explorer_kwargs)


# =============================================================================
# USAGE PATTERNS
# =============================================================================
if __name__ == "__main__":
    df = pd.DataFrame({
        "x": np.random.randn(100),
        "y": np.random.randn(100),
        "num_val": np.random.uniform(10, 100, size=100),
        "cat1": np.random.choice(["A", "B"], size=100),
        "cat2": np.random.choice(["X", "Y"], size=100),
        "shape1": np.random.choice(["Circle", "Square"], size=100),
        "shape2": np.random.choice(["High", "Low"], size=100),
    })

    # Option 1: Standard top-level non-blocking launcher (for interactive terminal scripts)
    explorer = HvPlotExplorer(df)
    server = launch_server(explorer, port=5006)

    # Option 2: Context manager usage
    # with launch_server(explorer, port=5006):
    #     time.sleep(10)