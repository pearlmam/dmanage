# -*- coding: utf-8 -*-
import sys
import time
import json
import numpy as np
import pandas as pd
import panel as pn
import param
import holoviews as hv
import hvplot.pandas
from bokeh.models import ColumnDataSource, CustomJS, Legend, LegendItem

from panel.io.server import get_server
from tornado.ioloop import IOLoop
import weakref
import threading
import asyncio
hv.extension('bokeh')

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
# BASE PANEL SERVER CLASS
# =============================================================================

# Persistent registry attached to Python process state (survives module reloads)
if not hasattr(sys, "_panel_server_registry"):
    sys._panel_server_registry = {}


class BasePanelServer:
    def __init__(self, port=5006):
        self.port = port
        self.thread = None

    @staticmethod
    def _stop_container(container):
        """Synchronously unbinds socket and kills thread."""
        if not container:
            return
        server = container.get("server")
        io_loop = container.get("io_loop")
        thread = container.get("thread")

        if io_loop:

            def _cleanup():
                if server:
                    try:
                        server.unlisten()  # Releases OS port immediately
                        server.stop()
                    except Exception:
                        pass
                io_loop.stop()

            io_loop.add_callback(_cleanup)

        if thread and thread.is_alive():
            thread.join(timeout=2.0)

    def start(self):
        if self.thread and self.thread.is_alive():
            return

        # 1. Reclaim port using process-wide sys registry
        if self.port in sys._panel_server_registry:
            old_container = sys._panel_server_registry.pop(self.port)
            BasePanelServer._stop_container(old_container)

        container = {}
        ready_event = threading.Event()
        self_ref = weakref.ref(self)

        def app_factory():
            instance = self_ref()
            if instance is not None:
                return instance.get_app()
            return pn.pane.Markdown("App instance replaced.")

        def _thread_target():
            async_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(async_loop)
            io_loop = IOLoop.current()

            server = get_server(
                app_factory,
                port=self.port,
                loop=io_loop,
                start=False,
                show=False,
            )
            server.start()

            container["server"] = server
            container["io_loop"] = io_loop
            ready_event.set()

            io_loop.start()

        self.thread = threading.Thread(target=_thread_target, daemon=True)
        container["thread"] = self.thread

        # 2. Store server container in sys-level registry
        sys._panel_server_registry[self.port] = container

        self.thread.start()
        ready_event.wait()

    def stop(self):
        """Explicit stop method."""
        container = sys._panel_server_registry.pop(self.port, None)
        BasePanelServer._stop_container(container)

    def get_app(self):
        raise NotImplementedError

# # =============================================================================
# # BASE PANEL SERVER CLASS
# # =============================================================================
# class BasePanelServer:
#     """Base class managing background server lifecycle via pn.serve Context Manager."""

#     _ACTIVE_SERVERS = {}

#     def __init__(self, port: int = 5006):
#         self.port = port
#         self._server = None

#     def __enter__(self):
#         self.start(show=True)
#         return self

#     def __exit__(self, exc_type, exc_val, exc_tb):
#         self.stop()

#     @classmethod
#     def stop_port(cls, port: int):
#         if port in cls._ACTIVE_SERVERS:
#             server_instance = cls._ACTIVE_SERVERS.pop(port)
#             server_instance.stop()

#     def create_app(self) -> pn.viewable.Viewable:
#         raise NotImplementedError("Subclasses must implement create_app().")

#     def start(self, show: bool = True):
#         BasePanelServer.stop_port(self.port)
#         pn.extension()

#         self._server = pn.serve(
#             self.create_app,
#             port=self.port,
#             show=show,
#             threaded=True,
#             websocket_origin="*",
#         )
#         BasePanelServer._ACTIVE_SERVERS[self.port] = self
#         print(f"Background explorer running on port {self.port}")
#         return self

#     def stop(self):
#         BasePanelServer._ACTIVE_SERVERS.pop(self.port, None)
#         if self._server is not None:
#             try:
#                 self._server.stop()
#                 print(f"Server on port {self.port} stopped cleanly.")
#             except Exception as e:
#                 print(f"Error stopping server on port {self.port}: {e}")
#             finally:
#                 self._server = None


# =============================================================================
# PARAMETERIZED EXPLORER WITH IMMUTABLE MARKERS
# =============================================================================
class HvPlotExplorer(BasePanelServer, param.Parameterized):
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

    def __init__(self, df: pd.DataFrame, port: int = 5006, **params):
        BasePanelServer.__init__(self, port=port)
        param.Parameterized.__init__(self, **params)

        self.df = sanitize_df(df)
        self.tap_stream = hv.streams.Tap()
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

        # 1. Neutralize all Bokeh selection tools so clicks never trigger visual selection state changes
        for t in bokeh_fig.tools:
            if hasattr(t, "renderers"):
                t.renderers = []

        # 2. Clean up old custom marker legends across all layout containers
        valid_containers = [
            bokeh_fig.above,
            bokeh_fig.below,
            bokeh_fig.left,
            bokeh_fig.right,
            bokeh_fig.center,
        ]
        for container in valid_containers:
            for layout_item in list(container):
                if isinstance(layout_item, Legend) and getattr(layout_item, "name", None) == "marker_legend":
                    container.remove(layout_item)

        # 3. Force scatter renderers to lock their selection/nonselection glyphs to the base glyph
        main_sources = []
        main_renderers = []
        for r in bokeh_fig.renderers:
            if hasattr(r, "glyph") and hasattr(r.glyph, "marker") and hasattr(r, "data_source"):
                main_renderers.append(r)
                if r.data_source not in main_sources:
                    main_sources.append(r.data_source)

                # Direct assignment prevents Bokeh JS from substituting default Circle glyphs on click
                r.selection_glyph = r.glyph
                r.nonselection_glyph = r.glyph
                r.hover_glyph = None

                ds = r.data_source
                if ds and ds.data:
                    first_col = next(iter(ds.data.values()), [])
                    n_pts = len(first_col)
                    if n_pts > 0 and ("_alpha" not in ds.data or len(ds.data["_alpha"]) != n_pts):
                        ds.data["_alpha"] = np.ones(n_pts, dtype=float)

                    r.glyph.fill_alpha = {"field": "_alpha"}
                    r.glyph.line_alpha = {"field": "_alpha"}

        # 4. Construct Custom Marker Legend if marker columns are active
        if marker_cols and shape_map and main_renderers:
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
                        const markers = data['marker_composite'] || data['_marker_composite'];
                        if (!markers) continue;

                        const alpha = data['_alpha'];
                        if (!alpha) continue;

                        let modified = false;
                        for (let i = 0; i < markers.length; i++) {
                            if (String(markers[i]) === target_val) {
                                alpha[i] = is_visible ? 1.0 : 0.15;
                                modified = true;
                            }
                        }
                        if (modified) {
                            src.change.emit();
                        }
                    }
                """
                custom_js = CustomJS(args=dict(sources=main_sources, val=str(val)), code=js_code)

                item = LegendItem(label=str(val), renderers=[dummy_r])
                item.js_on_change("visible", custom_js)
                dummy_r.js_on_change("visible", custom_js)

                legend_items.append(item)

            title_str = ", ".join(marker_cols)
            marker_legend = Legend(
                items=legend_items,
                title=f"Marker: {title_str}",
                orientation="vertical",
                background_fill_alpha=0.8,
                margin=5,
                click_policy="hide",
                name="marker_legend",
            )
            bokeh_fig.add_layout(marker_legend, "right")

        # 5. Consolidate ALL legends into bokeh_fig.right and pin them to top_left
        all_legends = []
        for container in [bokeh_fig.above, bokeh_fig.below, bokeh_fig.left, bokeh_fig.center, bokeh_fig.right]:
            for item in list(container):
                if isinstance(item, Legend):
                    all_legends.append((container, item))

        for orig_container, leg in all_legends:
            leg.location = "top_left"
            if orig_container is not bokeh_fig.right:
                orig_container.remove(leg)
                bokeh_fig.add_layout(leg, "right")

    @param.depends("x", "y", "color_by", "marker_by", "group_by", "aggregation")
    def make_plot(self):
        temp_df = self._prepare_data()

        plot_kwargs = dict(
            x=self.x,
            y=self.y,
            size=120,
            height=420,
            responsive=True,
            tools=["hover", "pan", "wheel_zoom", "reset"],
        )

        color_cols = [c for c in (self.color_by or []) if c in temp_df.columns]
        marker_cols = [c for c in (self.marker_by or []) if c in temp_df.columns]

        # ColorBy setup
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

        # MarkerBy setup
        hover_cols = []
        shape_map = {}
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
        
    def get_app(self) -> pn.viewable.Viewable:
        """Connects BasePanelServer's setup call to your Panel layout."""
        return self.create_app()

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
        "num_val": np.random.uniform(10, 100, size=100),
        "cat1": np.random.choice(["A", "B"], size=100),
        "cat2": np.random.choice(["X", "Y"], size=100),
        "shape1": np.random.choice(["Circle", "Square"], size=100),
        "shape2": np.random.choice(["High", "Low"], size=100),
    })

    with HvPlotExplorer(df, port=5006) as exp:
        while True:
            time.sleep(2)