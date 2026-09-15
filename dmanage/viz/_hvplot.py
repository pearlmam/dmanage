
import asyncio
import functools
import threading
import time
import weakref
import webbrowser
from bokeh.models import ColumnDataSource, CustomJS, Legend, LegendItem
import holoviews as hv
import hvplot.pandas
import numpy as np
import pandas as pd
import panel as pn
from panel.io.server import get_server

__all__ = ["BasePanelServer","HvPlotExplorer","HvPlotExplorer2","sanitize_df"]
# =============================================================================
# BASE SERVER CLASS (Thread, GC & Socket Lifecycle Management)
# =============================================================================

class BasePanelServer:
    """Base class managing thread lifecycle, socket teardown, and auto-GC for multiple Panel servers."""

    # Keyed by port -> (server_box, loop_box) to support multiple concurrent servers
    _ACTIVE_SERVERS = {}

    def __init__(self, port: int = 5006):
        self.port = port
        self._server_box = [None]
        self._loop_box = [None]
        self._finalizer = None

    @classmethod
    def stop_port(cls, port: int):
        """Stops any active server running specifically on the given port."""
        if port in cls._ACTIVE_SERVERS:
            server_box, loop_box = cls._ACTIVE_SERVERS.pop(port)
            cls._stop_server(server_box, loop_box, port)

    @classmethod
    def _stop_server(cls, server_box: list, loop_box: list, port: int):
        """Teardown routine completely decoupled from 'self' so GC can fire cleanly."""
        cls._ACTIVE_SERVERS.pop(port, None)

        server = server_box[0]
        loop = loop_box[0] if loop_box else None

        if server is not None:
            try:
                server.unlisten()
                server.stop()
                if hasattr(server, "io_loop") and server.io_loop is not None:
                    try:
                        server.io_loop.add_callback(server.io_loop.stop)
                    except Exception:
                        pass
                print(f"Port {port} sockets unbound.")
            except Exception as e:
                print(f"Error releasing port {port}: {e}")
            finally:
                server_box[0] = None

        if loop is not None and loop.is_running():
            try:
                loop.call_soon_threadsafe(loop.stop)
                print(f"Thread event loop on port {port} halted.")
            except Exception as e:
                print(f"Error stopping event loop: {e}")
            finally:
                if loop_box:
                    loop_box[0] = None

    def stop(self):
        """Manual stop method for this specific instance."""
        BasePanelServer._stop_server(self._server_box, self._loop_box, self.port)

    def create_app(self) -> pn.viewable.Viewable:
        """Override in subclasses to build and return the Panel layout."""
        raise NotImplementedError("Subclasses must implement create_app().")

    def start(self, show: bool = True):
        """Launches the Panel app non-blockingly in a dedicated background thread."""
        # 1. Stop any existing server ONLY if it is occupying this specific port
        BasePanelServer.stop_port(self.port)

        # 2. Extract local variables & weak reference to prevent reference cycles
        server_box = self._server_box
        loop_box = self._loop_box
        port = self.port
        ready_event = threading.Event()
        self_ref = weakref.ref(self)

        def app_factory():
            inst = self_ref()
            if inst is not None:
                return inst.create_app()
            return pn.pane.Markdown("Server stopped.")

        pn.extension()

        # 3. Background thread execution
        def _run_server():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop_box[0] = loop

            server = get_server(
                app_factory,
                port=port,
                start=False,
                show=False,
                websocket_origin="*",
            )

            server_box[0] = server
            BasePanelServer._ACTIVE_SERVERS[port] = (server_box, loop_box)

            server.start()
            ready_event.set()
            loop.run_forever()

        thread = threading.Thread(target=_run_server, daemon=True)
        thread.start()

        # 4. Wait for server instantiation
        ready_event.wait(timeout=2.0)

        # 5. Attach weakref finalizer for auto-GC
        self._finalizer = weakref.finalize(
            self,
            BasePanelServer._stop_server,
            self._server_box,
            self._loop_box,
            self.port,
        )

        url = f"http://localhost:{self.port}"
        if show:
            time.sleep(0.1)
            webbrowser.open(url)

        print(f"Background explorer running at {url}")
        return self


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
# IMPLEMENTATION 1: CUSTOM INTERACTIVE EXPLORER
# =============================================================================
class HvPlotExplorer(BasePanelServer):
    """Custom Panel server with click-to-toggle Color/Marker legends and GroupBy aggregation."""

    MARKER_PALETTE = [
        "circle",
        "square",
        "triangle",
        "diamond",
        "star",
        "cross",
        "hex",
        "asterisk",
    ]

    def __init__(self, df: pd.DataFrame, port: int = 5006):
        super().__init__(port=port)
        self.df = df

    @classmethod
    def _add_category_callback(
        cls,
        event,
        df_box: list,
        cat_col_widget: pn.widgets.Select,
        bins_widget: pn.widgets.IntInput,
        status_pane: pn.pane.Markdown,
        x_widget: pn.widgets.Select,
        y_widget: pn.widgets.Select,
        by_widget: pn.widgets.Select,
        marker_by_widget: pn.widgets.Select,
        groupby_widget: pn.widgets.Select,
    ):
        target_col = cat_col_widget.value
        n_bins = bins_widget.value

        if target_col == "None" or not n_bins or n_bins < 2:
            status_pane.object = "*Select a column and valid bins (>1).*"
            return

        try:
            df_curr = df_box[0]
            new_col_name = f"{target_col}_bin{n_bins}"

            counter = 1
            base_name = new_col_name
            while new_col_name in df_curr.columns:
                new_col_name = f"{base_name}_{counter}"
                counter += 1

            binned = pd.cut(df_curr[target_col], bins=n_bins)
            df_curr[new_col_name] = binned.astype(str)

            all_cols = list(df_curr.columns)
            num_cols = list(df_curr.select_dtypes(include=[np.number]).columns)
            cat_cols = list(
                df_curr.select_dtypes(
                    include=["object", "category", "string"]
                ).columns
            )

            x_widget.options = all_cols
            y_widget.options = all_cols
            by_widget.options = ["None"] + all_cols
            groupby_widget.options = ["None"] + all_cols
            marker_by_widget.options = ["None"] + cat_cols
            cat_col_widget.options = ["None"] + num_cols

            by_widget.value = new_col_name
            status_pane.object = f"✓ Added **{new_col_name}**"

        except Exception as e:
            status_pane.object = f"*Error:* {e}"

    @staticmethod
    def _add_marker_legend_hook(plot, element, marker_by: str, shape_map: dict):
        if not plot or "plot" not in plot.handles:
            return

        bokeh_fig = plot.handles["plot"]

        main_renderers = []
        for r in bokeh_fig.renderers:
            if hasattr(r, "hover_glyph"):
                r.hover_glyph = None
            if hasattr(r, "data_source") and r.data_source is not None:
                if marker_by and marker_by in r.data_source.data:
                    main_renderers.append(r)

        main_sources = []
        for r in main_renderers:
            ds = r.data_source
            main_sources.append(ds)

            n_pts = len(next(iter(ds.data.values()))) if ds.data else 0
            if n_pts == 0 or getattr(ds, "_alpha_initialized", False):
                continue

            base_size = (
                float(r.glyph.size)
                if isinstance(r.glyph.size, (int, float))
                else 10.0
            )
            ds.data["_alpha"] = np.ones(n_pts, dtype=float)
            ds.data["_orig_size"] = np.full(n_pts, base_size, dtype=float)
            ds.data["_size"] = np.full(n_pts, base_size, dtype=float)
            ds._alpha_initialized = True

            r.glyph.fill_alpha = "_alpha"
            r.glyph.line_alpha = "_alpha"
            r.glyph.size = "_size"

        all_legends = []
        for loc in [
            bokeh_fig.right,
            bokeh_fig.left,
            bokeh_fig.above,
            bokeh_fig.below,
            bokeh_fig.center,
        ]:
            for layout_item in loc:
                if (
                    isinstance(layout_item, Legend)
                    and layout_item not in all_legends
                ):
                    all_legends.append(layout_item)

        for legend in all_legends:
            for item in legend.items:
                if not item.renderers:
                    continue

                main_r = item.renderers[0]
                if getattr(main_r, "_is_legend_dummy", False):
                    continue

                fc = getattr(main_r.glyph, "fill_color", "#555555")
                fill_color = (
                    fc.value
                    if hasattr(fc, "value")
                    else (fc if isinstance(fc, str) else "#555555")
                )

                lc = getattr(main_r.glyph, "line_color", "#222222")
                line_color = (
                    lc.value
                    if hasattr(lc, "value")
                    else (lc if isinstance(lc, str) else "#222222")
                )

                mk = getattr(main_r.glyph, "marker", "circle")
                marker_shape = (
                    mk.value
                    if hasattr(mk, "value")
                    else (mk if isinstance(mk, str) else "circle")
                )

                dummy_ds = ColumnDataSource(data=dict(x=[np.nan], y=[np.nan]))
                dummy_r = bokeh_fig.scatter(
                    x="x",
                    y="y",
                    source=dummy_ds,
                    marker=marker_shape,
                    fill_color=fill_color,
                    line_color=line_color,
                    size=10,
                    fill_alpha=1.0,
                    line_alpha=1.0,
                )
                dummy_r._is_legend_dummy = True

                item.renderers = [dummy_r] + item.renderers

        if marker_by and marker_by != "None" and shape_map and main_renderers:
            legend_items = []
            for val, shape in shape_map.items():
                dummy_ds = ColumnDataSource(data=dict(x=[np.nan], y=[np.nan]))
                dummy_r = bokeh_fig.scatter(
                    x="x",
                    y="y",
                    source=dummy_ds,
                    marker=shape,
                    fill_color="#555555",
                    line_color="#222222",
                    size=10,
                    fill_alpha=0.8,
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
                        if (modified) {
                            src.change.emit();
                        }
                    }
                """

                toggle_cb = CustomJS(
                    args=dict(
                        sources=main_sources,
                        val=str(val),
                        marker_by=marker_by,
                    ),
                    code=js_code,
                )
                dummy_r.js_on_change("visible", toggle_cb)

                legend_items.append(
                    LegendItem(label=str(val), renderers=[dummy_r])
                )

            marker_legend = Legend(
                items=legend_items,
                title=f"Marker: {marker_by}",
                background_fill_alpha=0.8,
                margin=5,
                location="top_left",
                click_policy="hide",
            )
            bokeh_fig.add_layout(marker_legend, "right")

        for item in bokeh_fig.right:
            if isinstance(item, Legend):
                item.location = "top_left"

    @classmethod
    def _create_plot(
        cls,
        df_box,
        palette,
        x,
        y,
        by,
        marker_by,
        groupby_col,
        agg_func,
        tap_stream,
    ):
        temp_df = df_box[0].copy()

        # Handle GroupBy Aggregation
        if groupby_col != "None":
            group_keys = [groupby_col]
            # Retain non-numeric X or Color dimensions as grouping keys if present
            if (
                x != groupby_col
                and x in temp_df.columns
                and not pd.api.types.is_numeric_dtype(temp_df[x])
            ):
                group_keys.append(x)
            if (
                by != "None"
                and by != groupby_col
                and by not in group_keys
                and not pd.api.types.is_numeric_dtype(temp_df[by])
            ):
                group_keys.append(by)

            try:
                if agg_func == "count":
                    temp_df = temp_df.groupby(
                        group_keys, as_index=False
                    ).size()
                    temp_df = temp_df.rename(columns={"size": y})
                else:
                    temp_df = temp_df.groupby(group_keys, as_index=False).agg(
                        agg_func, numeric_only=True
                    )
            except Exception as e:
                print(f"Aggregation error: {e}")

        plot_kwargs = dict(
            x=x,
            y=y,
            size=120,
            height=420,
            responsive=True,
            tools=["tap", "box_select"],
        )

        if by != "None" and by in temp_df.columns:
            if pd.api.types.is_numeric_dtype(temp_df[by]):
                plot_kwargs.update(c=by, cmap="viridis", colorbar=True)
            else:
                plot_kwargs.update(by=by, legend="right")

        if marker_by != "None" and marker_by in temp_df.columns:
            unique_vals = [v for v in temp_df[marker_by].dropna().unique()]
            shape_map = {
                val: palette[i % len(palette)]
                for i, val in enumerate(unique_vals)
            }
            temp_df["_marker_shape"] = temp_df[marker_by].map(shape_map)
            plot_kwargs["marker"] = "_marker_shape"
            plot_kwargs["hover_cols"] = [marker_by]
        else:
            shape_map = {}
            plot_kwargs["marker"] = "circle"

        hook = lambda plot, element: cls._add_marker_legend_hook(
            plot, element, marker_by, shape_map
        )

        plot = temp_df.hvplot.scatter(**plot_kwargs).opts(hooks=[hook])
        tap_stream.source = plot
        return plot

    @staticmethod
    def _find_closest_record(
        df_clean: pd.DataFrame, x_col: str, y_col: str, x: float, y: float
    ) -> pd.DataFrame:
        x_vals = pd.to_numeric(df_clean[x_col], errors="coerce")
        y_vals = pd.to_numeric(df_clean[y_col], errors="coerce")

        if x_vals.notna().any() and y_vals.notna().any():
            x_scale = (
                x_vals.std()
                if (pd.notna(x_vals.std()) and x_vals.std() > 0)
                else 1.0
            )
            y_scale = (
                y_vals.std()
                if (pd.notna(y_vals.std()) and y_vals.std() > 0)
                else 1.0
            )

            dist = np.sqrt(
                ((x_vals - x) / x_scale) ** 2 + ((y_vals - y) / y_scale) ** 2
            )
            closest_idx = dist.idxmin()
            return df_clean.loc[[closest_idx]]

        return df_clean[(df_clean[x_col] == x) & (df_clean[y_col] == y)]

    @classmethod
    def _render_details(cls, df_box, x_col, y_col, x, y):
        df_clean = df_box[0]
        if x is None or y is None:
            return pn.pane.Markdown(
                "### Details Panel\n*Click any point on the plot above to display details here.*"
            )

        selected_rows = cls._find_closest_record(df_clean, x_col, y_col, x, y)
        if selected_rows.empty:
            return pn.pane.Markdown("*No record found for click location.*")

        records = selected_rows.to_dict(orient="records")
        return pn.Column(
            pn.pane.Markdown(
                f"### Selected Record Details (Index {selected_rows.index[0]})"
            ),
            pn.pane.JSON(records[0], depth=3, theme="light"),
        )

    def create_app(self) -> pn.viewable.Viewable:
        df_clean = sanitize_df(self.df)
        palette = list(self.MARKER_PALETTE)
        df_box = [df_clean.copy()]
        WIDGET_WIDTH = 180

        all_cols = list(df_clean.columns)
        num_cols = list(df_clean.select_dtypes(include=[np.number]).columns)
        cat_cols = list(
            df_clean.select_dtypes(
                include=["object", "category", "string"]
            ).columns
        )

        # Controls
        x_widget = pn.widgets.Select(
            name="X Axis",
            options=all_cols,
            value=num_cols[0] if num_cols else all_cols[0],
            width=WIDGET_WIDTH,
        )
        y_widget = pn.widgets.Select(
            name="Y Axis",
            options=all_cols,
            value=num_cols[1] if len(num_cols) > 1 else all_cols[0],
            width=WIDGET_WIDTH,
        )
        by_widget = pn.widgets.Select(
            name="Color By",
            options=["None"] + all_cols,
            value="None",
            width=WIDGET_WIDTH,
        )
        marker_by_widget = pn.widgets.Select(
            name="Marker By Column",
            options=["None"] + cat_cols,
            value="None",
            width=WIDGET_WIDTH,
        )

        # GroupBy & Aggregation Widgets
        groupby_widget = pn.widgets.Select(
            name="Group By",
            options=["None"] + all_cols,
            value="None",
            width=WIDGET_WIDTH,
        )
        agg_widget = pn.widgets.Select(
            name="Aggregation",
            options=["mean", "sum", "count", "min", "max", "std"],
            value="mean",
            width=WIDGET_WIDTH,
        )

        # Binning Widgets
        cat_col_widget = pn.widgets.Select(
            name="Categorize Numeric",
            options=["None"] + num_cols,
            value="None",
            width=WIDGET_WIDTH,
        )
        bins_widget = pn.widgets.IntInput(
            name="Number of Bins",
            value=4,
            start=2,
            end=20,
            width=WIDGET_WIDTH,
        )
        add_cat_btn = pn.widgets.Button(
            name="Create Category",
            button_type="primary",
            width=WIDGET_WIDTH,
        )
        status_pane = pn.pane.Markdown("", width=WIDGET_WIDTH)

        add_cat_btn.on_click(
            functools.partial(
                HvPlotExplorer._add_category_callback,
                df_box=df_box,
                cat_col_widget=cat_col_widget,
                bins_widget=bins_widget,
                status_pane=status_pane,
                x_widget=x_widget,
                y_widget=y_widget,
                by_widget=by_widget,
                marker_by_widget=marker_by_widget,
                groupby_widget=groupby_widget,
            )
        )

        tap_stream = hv.streams.Tap()

        plot_pane = pn.bind(
            HvPlotExplorer._create_plot,
            df_box=df_box,
            palette=palette,
            x=x_widget,
            y=y_widget,
            by=by_widget,
            marker_by=marker_by_widget,
            groupby_col=groupby_widget,
            agg_func=agg_widget,
            tap_stream=tap_stream,
        )

        details_pane = pn.bind(
            HvPlotExplorer._render_details,
            df_box=df_box,
            x_col=x_widget,
            y_col=y_widget,
            x=tap_stream.param.x,
            y=tap_stream.param.y,
        )

        # Tabbed Sidebar Layout
        controls_tab = pn.Column(
            x_widget,
            y_widget,
            by_widget,
            marker_by_widget,
            pn.layout.Divider(),
            groupby_widget,
            agg_widget,
            margin=(10, 5),
        )

        binning_tab = pn.Column(
            cat_col_widget,
            bins_widget,
            add_cat_btn,
            status_pane,
            margin=(10, 5),
        )

        sidebar_tabs = pn.Tabs(
            ("Controls", controls_tab),
            ("Bin Numeric", binning_tab),
            width=210,
        )

        top_row = pn.Row(
            sidebar_tabs,
            pn.Column(plot_pane, sizing_mode="stretch_width"),
            sizing_mode="stretch_width",
        )

        bottom_row = pn.Column(
            pn.layout.Divider(),
            details_pane,
            sizing_mode="stretch_width",
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
# USAGE EXAMPLE & DEL PROOF
# =============================================================================
if __name__ == "__main__":
    pass