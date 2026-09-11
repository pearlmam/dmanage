import asyncio
import threading
import time
import weakref
import webbrowser
from bokeh.models import ColumnDataSource, Legend, LegendItem
import holoviews as hv
import hvplot.pandas
import numpy as np
import pandas as pd
import panel as pn
from panel.io.server import get_server


def sanitize_df(df: pd.DataFrame) -> pd.DataFrame:
    """Sanitizes boolean columns to string categories for Bokeh safety."""
    df_clean = df.copy()
    for col in df_clean.columns:
        if df_clean[col].dtype == "bool":
            df_clean[col] = df_clean[col].astype(str)
    return df_clean


class HvPlotExplorer:
    """Modular non-blocking Panel server with garbage-collection safe thread control."""

    _ACTIVE_BOX = [None]
    _ACTIVE_PORT = [None]
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
        self.df = df
        self.port = port
        self._server_box = [None]
        self._loop_box = [None]
        self._finalizer = None

    # -------------------------------------------------------------------------
    # Server Teardown & Lifecycle
    # -------------------------------------------------------------------------
    @staticmethod
    def _stop_server(server_box: list, loop_box: list, port: int):
        """Static teardown routine containing zero references to 'self'."""
        server = server_box[0]
        loop = loop_box[0]

        if server is not None:
            try:
                server.unlisten()
                server.stop()
                print(f"Port {port} sockets unbound.")
            except Exception as e:
                print(f"Error stopping server on port {port}: {e}")
            finally:
                server_box[0] = None

        if loop is not None and loop.is_running():
            try:
                loop.call_soon_threadsafe(loop.stop)
                print(f"Thread event loop on port {port} halted.")
            except Exception as e:
                print(f"Error stopping event loop: {e}")
            finally:
                loop_box[0] = None

    def stop(self):
        """Explicitly stops server and event loop thread."""
        self._stop_server(self._server_box, self._loop_box, self.port)

    # -------------------------------------------------------------------------
    # Visualization & UI Component Helpers
    # -------------------------------------------------------------------------
    @staticmethod
    def _add_marker_legend_hook(plot, element, marker_by: str, shape_map: dict):
        """Bokeh hook to attach top-aligned marker legend to the plot."""
        if not marker_by or marker_by == "None" or not shape_map:
            return

        bokeh_fig = plot.handles["plot"]
        legend_items = []

        for val, shape in shape_map.items():
            ds = ColumnDataSource(data=dict(x=[np.nan], y=[np.nan]))
            renderer = bokeh_fig.scatter(
                x="x",
                y="y",
                source=ds,
                marker=shape,
                fill_color="#555555",
                line_color="#222222",
                size=10,
                fill_alpha=0.8,
            )
            legend_items.append(LegendItem(label=str(val), renderers=[renderer]))

        marker_legend = Legend(
            items=legend_items,
            title=f"Marker: {marker_by}",
            background_fill_alpha=0.8,
            margin=5,
            location="top_left",
        )
        bokeh_fig.add_layout(marker_legend, "right")

        # Top-align all legends attached to the right panel layout
        for item in bokeh_fig.right:
            if isinstance(item, Legend):
                item.location = "top_left"

    @classmethod
    def _create_plot(cls, df_clean, palette, x, y, by, marker_by, tap_stream):
        """Generates the main scatter plot and attaches interaction streams."""
        temp_df = df_clean.copy()
        by_arg = None if by == "None" else by

        if marker_by == "None":
            marker_arg = "circle"
            shape_map = {}
        else:
            unique_vals = temp_df[marker_by].unique()
            shape_map = {
                val: palette[i % len(palette)]
                for i, val in enumerate(unique_vals)
            }
            temp_df["_marker_shape"] = temp_df[marker_by].map(shape_map)
            marker_arg = "_marker_shape"

        hook = lambda plot, element: cls._add_marker_legend_hook(
            plot, element, marker_by, shape_map
        )

        plot = temp_df.hvplot.scatter(
            x=x,
            y=y,
            by=by_arg,
            marker=marker_arg,
            size=120,
            height=420,
            responsive=True,
            legend="right" if by_arg else False,
            tools=["tap", "box_select", "reset"],
        ).opts(hooks=[hook])

        tap_stream.source = plot
        return plot

    @staticmethod
    def _find_closest_record(
        df_clean: pd.DataFrame, x_col: str, y_col: str, x: float, y: float
        ) -> pd.DataFrame:
        """Finds nearest matching dataframe row for a clicked coordinate."""
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
    def _render_details(cls, df_clean, x_col, y_col, x, y):
        """Renders the details JSON panel for a selected point."""
        if x is None or y is None:
            return pn.pane.Markdown(
                "### Details Panel\n*Click any point on the plot above to display row details here.*"
            )

        selected_rows = cls._find_closest_record(df_clean, x_col, y_col, x, y)
        if selected_rows.empty:
            return pn.pane.Markdown("*No record found for click location.*")

        records = selected_rows.to_dict(orient="records")
        return pn.Column(
            pn.pane.Markdown(
                f"### Selected Record Details (Row Index {selected_rows.index[0]})"
            ),
            pn.pane.JSON(records[0], depth=3, theme="light"),
        )

    # -------------------------------------------------------------------------
    # Application Assembly & Runner
    # -------------------------------------------------------------------------
    @classmethod
    def _create_app(cls, df_clean: pd.DataFrame, palette: list):
        """Assembles widgets, dynamic bindings, and overall layout."""
        columns = list(df_clean.columns)
        num_cols = list(df_clean.select_dtypes(include=[np.number]).columns)
        cat_cols = list(
            df_clean.select_dtypes(
                include=["object", "category", "string"]
            ).columns
        )

        by_options = ["None"] + cat_cols
        marker_by_options = ["None"] + cat_cols
        WIDGET_WIDTH = 180

        x_widget = pn.widgets.Select(
            name="X Axis",
            options=columns,
            value=num_cols[0] if num_cols else columns[0],
            width=WIDGET_WIDTH,
        )
        y_widget = pn.widgets.Select(
            name="Y Axis",
            options=columns,
            value=num_cols[1] if len(num_cols) > 1 else columns[0],
            width=WIDGET_WIDTH,
        )
        by_widget = pn.widgets.Select(
            name="Color By",
            options=by_options,
            value=cat_cols[0] if cat_cols else "None",
            width=WIDGET_WIDTH,
        )
        marker_by_widget = pn.widgets.Select(
            name="Marker By Column",
            options=marker_by_options,
            value=cat_cols[1] if len(cat_cols) > 1 else "None",
            width=WIDGET_WIDTH,
        )

        tap_stream = hv.streams.Tap()

        # Dynamic Reactive Bindings
        plot_pane = pn.bind(
            cls._create_plot,
            df_clean=df_clean,
            palette=palette,
            x=x_widget,
            y=y_widget,
            by=by_widget,
            marker_by=marker_by_widget,
            tap_stream=tap_stream,
        )

        details_pane = pn.bind(
            cls._render_details,
            df_clean=df_clean,
            x_col=x_widget,
            y_col=y_widget,
            x=tap_stream.param.x,
            y=tap_stream.param.y,
        )

        top_row = pn.Row(
            pn.Column(
                "### Controls",
                x_widget,
                y_widget,
                by_widget,
                marker_by_widget,
                width=200,
            ),
            pn.Column(plot_pane, sizing_mode="stretch_width"),
            sizing_mode="stretch_width",
        )

        bottom_row = pn.Column(
            pn.layout.Divider(),
            details_pane,
            sizing_mode="stretch_width",
        )

        return pn.Column(top_row, bottom_row, sizing_mode="stretch_width")

    def start(self, show: bool = True):
        """Starts the server thread and opens browser window."""
        self._stop_server(self._ACTIVE_BOX, [None], self._ACTIVE_PORT[0] or self.port)

        df_clean = sanitize_df(self.df)
        palette = list(self.MARKER_PALETTE)
        server_box = self._server_box
        loop_box = self._loop_box
        port = self.port
        ready_event = threading.Event()

        pn.extension()

        def _run_server():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop_box[0] = loop

            # App creation factory
            app_factory = lambda: HvPlotExplorer._create_app(df_clean, palette)

            server = get_server(
                app_factory,
                port=port,
                start=False,
                show=False,
                websocket_origin="*",
            )

            server_box[0] = server
            HvPlotExplorer._ACTIVE_BOX[0] = server
            HvPlotExplorer._ACTIVE_PORT[0] = port

            server.start()
            ready_event.set()
            loop.run_forever()

        thread = threading.Thread(target=_run_server, daemon=True)
        thread.start()
        ready_event.wait(timeout=2.0)

        self._finalizer = weakref.finalize(
            self,
            HvPlotExplorer._stop_server,
            self._server_box,
            self._loop_box,
            self.port,
        )

        url = f"http://localhost:{self.port}"
        if show:
            time.sleep(0.2)
            webbrowser.open(url)

        print(f"Interactive explorer running non-blockingly at {url}")
        return self


if __name__ == "__main__":
    df = pd.DataFrame(
        {
            "x": [1, 2, 3, 4, 5, 6],
            "y": [10, 15, 13, 17, 20, 25],
            "category": ["Alpha", "Beta", "Alpha", "Beta", "Alpha", "Beta"],
            "region": ["East", "East", "West", "West", "East", "West"],
            "notes": [
                "Passed check A",
                "Flagged B",
                "Passed check C",
                "Variance high D",
                "Passed check E",
                "Follow-up F",
            ],
        }
    )

    app = HvPlotExplorer(df, port=5006)
    app.start(show=True)