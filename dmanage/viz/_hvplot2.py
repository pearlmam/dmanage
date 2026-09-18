# -*- coding: utf-8 -*-
import json
import numpy as np
import pandas as pd
import panel as pn
import param
import holoviews as hv
import hvplot.pandas

from ._base import launch_server,sanitize_df,_to_numeric_coords

__all__ = ["HvPlotExplorer","HvPlotExplorer2",]

hv.extension('bokeh')

# =============================================================================
# PARAMETERIZED EXPLORER WITH IMMUTABLE MARKERS
# =============================================================================

class HvPlotExplorer(param.Parameterized):
    """Lean Explorer with right-side Filter/Legend panel and continuous colorbar support."""

    x = param.Selector(doc="X Axis Column")
    y = param.Selector(doc="Y Axis Column")
    color_by = param.ListSelector(default=[], doc="Color By Column(s)")
    marker_by = param.ListSelector(default=[], doc="Marker Shape Column(s)")

    color_filter = param.ListSelector(default=[], doc="Filter Colors (Discrete)")
    color_range = param.Parameter(default=None, doc="Filter Colors (Continuous)")
    marker_filter = param.ListSelector(default=[], doc="Filter Markers")

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

    MARKER_PALETTE = ["circle","square","triangle","diamond","hexagon","star",
                      "inverted_triangle","cross"]
    MARKER_SYMBOLS = {
        "circle": "●",
        "square": "■",
        "triangle": "▲",
        "diamond": "◆",
        "hexagon": "⬢",
        "star": "★",
        "inverted_triangle": "▼",
        "cross": "✖",
    }
    COLOR_PALETTE = ["#e41a1c","#377eb8","#4daf4a","#ff7f00","#984ea3","#00bed6",
                     "#e6ab02","#f781bf","#a65628","#2d3748"]

    def __init__(self, df: pd.DataFrame, **params):
        super().__init__(**params)
        self.df = sanitize_df(df)
        self.tap_stream = hv.streams.Tap()

        self._update_column_options()
        all_cols = self.param.x.objects
        num_cols = list(self.df.select_dtypes(include=[np.number]).columns)
        self.x = num_cols[0] if num_cols else all_cols[0]
        self.y = num_cols[1] if len(num_cols) > 1 else all_cols[0]

    def _has_continuous_col(self, df: pd.DataFrame, cols: list) -> bool:
        return any(
            c in df.columns
            and pd.api.types.is_numeric_dtype(df[c])
            and not pd.api.types.is_bool_dtype(df[c])
            and not pd.api.types.is_categorical_dtype(df[c])
            for c in cols
        )

    def _is_continuous_color(self, df: pd.DataFrame, color_cols: list) -> bool:
        return len(color_cols) == 1 and self._has_continuous_col(df, color_cols)

    def _update_column_options(self):
        all_cols = list(self.df.columns)
        num_cols = list(self.df.select_dtypes(include=[np.number]).columns)
        cat_dtypes = ["object","category","string","datetime","datetimetz","bool"]
        cat_cols = list(self.df.select_dtypes(include=cat_dtypes).columns)

        self.param.x.objects = all_cols
        self.param.y.objects = all_cols
        self.param.color_by.objects = all_cols
        self.param.marker_by.objects = cat_cols
        self.param.group_by.objects = ["None"] + all_cols
        self.param.cat_col.objects = ["None"] + num_cols

    @param.depends("color_by", watch=True)
    def _update_color_filters(self):
        color_cols = [c for c in (self.color_by or []) if c in self.df.columns]

        if len(color_cols) > 1 and self._has_continuous_col(self.df, color_cols):
            self.color_filter = []
            self.color_range = None
            return

        if self._is_continuous_color(self.df, color_cols):
            s = self.df[color_cols[0]].dropna()
            if not s.empty:
                self.color_range = (float(s.min()), float(s.max()))
            else:
                self.color_range = (0.0, 1.0)
            self.color_filter = []
        else:
            self.color_range = None
            _, c_cats = self._get_composite_series(self.df, color_cols)
            self.param.color_filter.objects = c_cats
            self.color_filter = list(c_cats)

    @param.depends("marker_by", watch=True)
    def _update_marker_filters(self):
        marker_cols = [c for c in (self.marker_by or []) if c in self.df.columns]
        _, m_cats = self._get_composite_series(self.df, marker_cols)
        self.param.marker_filter.objects = m_cats
        self.marker_filter = list(m_cats)

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

            self.df[new_col_name] = pd.cut(
                self.df[self.cat_col], bins=self.n_bins
            ).astype(str)
            self._update_column_options()
            self.color_by = [new_col_name]
            self.status_msg = f"✓ Added **{new_col_name}**"
        except Exception as e:
            self.status_msg = f"*Error:* {e}"

    def _get_composite_series(self, df: pd.DataFrame, cols: list):
        valid = [c for c in (cols or []) if c in df.columns]
        if not valid:
            return None, []
        series = df[valid].astype(str).agg(" | ".join, axis=1)
        all_cats = sorted(
            self.df[valid]
            .drop_duplicates()
            .astype(str)
            .agg(" | ".join, axis=1)
            .tolist()
        )
        return series, all_cats

    def _prepare_data(self) -> pd.DataFrame:
        temp_df = self.df.copy()

        # 1. Filter out empty/invalid/None values from color and marker selectors
        color_cols = [
            c
            for c in (self.color_by or [])
            if c in temp_df.columns and c not in ("None", None, "")
        ]
        marker_cols = [
            c
            for c in (self.marker_by or [])
            if c in temp_df.columns and c not in ("None", None, "")
        ]

        group_col = self.group_by
        if (
            group_col
            and group_col not in ("None", None, "")
            and group_col in temp_df.columns
        ):
            # 2. Build group keys strictly from active columns
            group_keys = [group_col]
            for c in color_cols + marker_cols:
                if c not in group_keys:
                    group_keys.append(c)

            try:
                # 3. Round float group keys to prevent micro-precision group splits
                if pd.api.types.is_float_dtype(temp_df[group_col]):
                    temp_df[group_col] = temp_df[group_col].round(6)

                if self.aggregation == "count":
                    agg_df = (
                        temp_df.groupby(group_keys, as_index=False)
                        .size()
                        .rename(columns={"size": self.y})
                    )
                else:
                    agg_df = temp_df.groupby(group_keys, as_index=False).agg(
                        self.aggregation, numeric_only=True
                    )

                # 4. Retain x for plotting if it was omitted during numeric aggregation
                if self.x in temp_df.columns and self.x not in agg_df.columns:
                    if pd.api.types.is_numeric_dtype(temp_df[self.x]):
                        x_vals = temp_df.groupby(group_keys, as_index=False)[
                            self.x
                        ].mean()
                    else:
                        x_vals = temp_df.groupby(group_keys, as_index=False)[
                            self.x
                        ].first()
                    agg_df[self.x] = x_vals[self.x]

                temp_df = agg_df

            except Exception as e:
                print(f"Aggregation error: {e}")

        # Compute composite helper columns AFTER aggregation
        if color_cols and not self._is_continuous_color(temp_df, color_cols):
            c_series, _ = self._get_composite_series(temp_df, color_cols)
            if c_series is not None:
                temp_df["_c_val"] = c_series

        if marker_cols:
            m_series, _ = self._get_composite_series(temp_df, marker_cols)
            if m_series is not None:
                temp_df["_m_val"] = m_series

        return temp_df

    def _get_axis_limits(self, series: pd.Series):
        if (
            series is None
            or series.empty
            or not pd.api.types.is_numeric_dtype(series)
            or pd.api.types.is_bool_dtype(series)
        ):
            return None

        s_clean = series.dropna()
        if s_clean.empty:
            return None

        s_min, s_max = float(s_clean.min()), float(s_clean.max())
        if s_min == s_max:
            pad = 1.0 if s_min == 0 else abs(s_min) * 0.1
            return (s_min - pad, s_max + pad)

        margin = (s_max - s_min) * 0.05
        return (s_min - margin, s_max + margin)

    def _create_filter_rows(
        self,
        cats: list,
        active_filter: list,
        filter_attr: str,
        palette: list,
        symbol_map: dict = None,
    ):
        rows = []
        for i, cat in enumerate(cats):
            cb = pn.widgets.Checkbox(
                value=cat in active_filter,
                width=20,
                margin=(2, 2, 2, 0),
            )

            def _on_change(event, c=cat):
                cur = list(getattr(self, filter_attr))
                if event.new and c not in cur:
                    cur.append(c)
                elif not event.new and c in cur:
                    cur.remove(c)
                setattr(self, filter_attr, cur)

            cb.param.watch(_on_change, "value")

            if symbol_map:
                symbol = symbol_map.get(palette[i % len(palette)], "●")
                badge = (
                    f'<span style="color:#4A5568; font-size:14px; '
                    f'font-weight:bold; margin-right:6px;">{symbol}</span>'
                )
            else:
                hex_color = palette[i % len(palette)]
                badge = (
                    f'<span style="color:{hex_color}; font-size:16px; '
                    f'margin-right:6px;">●</span>'
                )

            label = pn.pane.HTML(
                f'<div style="display:flex; align-items:center;">{badge}'
                f'<span style="font-size:13px; word-break:break-word;">{cat}</span>'
                f"</div>",
                margin=(2, 0, 2, 0),
            )
            rows.append(pn.Row(cb, label, margin=(0, 0, 2, 0)))
        return rows

    @param.depends("color_by", "marker_by")
    def _render_legend_panel(self):
        color_cols = [c for c in (self.color_by or []) if c in self.df.columns]
        marker_cols = [c for c in (self.marker_by or []) if c in self.df.columns]
        is_continuous = self._is_continuous_color(self.df, color_cols)
        has_invalid_color = len(color_cols) > 1 and self._has_continuous_col(
            self.df, color_cols
        )

        items = [pn.pane.Markdown("### Legend & Filters")]

        # 1. Color Section
        if has_invalid_color:
            items.extend(
                [
                    pn.pane.Markdown("**Color:** *Invalid Selection*"),
                    pn.pane.Markdown(
                        "⚠️ *Multiple selections are not possible when a "
                        "continuous (colorbar) column is selected.*"
                    ),
                    pn.layout.Spacer(height=10),
                ]
            )
        elif color_cols:
            c_str = ", ".join(color_cols)
            if is_continuous:
                s = self.df[color_cols[0]].dropna()
                if not s.empty:
                    min_v, max_v = float(s.min()), float(s.max())
                else:
                    min_v, max_v = 0.0, 1.0

                step_val = (max_v - min_v) / 100 if max_v > min_v else 0.01
                rs = pn.widgets.RangeSlider(
                    name="Range Filter",
                    start=min_v,
                    end=max_v,
                    value=self.color_range or (min_v, max_v),
                    step=step_val,
                    width=170,
                )
                rs.param.watch(
                    lambda e: setattr(self, "color_range", e.new), "value"
                )
                items.extend(
                    [
                        pn.pane.Markdown(f"**Color:** {c_str} *(Continuous)*"),
                        rs,
                        pn.layout.Spacer(height=10),
                    ]
                )
            else:
                _, c_cats = self._get_composite_series(self.df, color_cols)
                c_rows = self._create_filter_rows(
                    c_cats,
                    self.color_filter,
                    "color_filter",
                    self.COLOR_PALETTE,
                )
                items.extend(
                    [
                        pn.pane.Markdown(f"**Color:** {c_str}"),
                        pn.Column(*c_rows, margin=(0, 0, 0, 4)),
                        pn.layout.Spacer(height=10),
                    ]
                )

        # 2. Marker Section
        if marker_cols:
            m_str = ", ".join(marker_cols)
            _, m_cats = self._get_composite_series(self.df, marker_cols)
            m_rows = self._create_filter_rows(
                m_cats,
                self.marker_filter,
                "marker_filter",
                self.MARKER_PALETTE,
                self.MARKER_SYMBOLS,
            )
            items.extend(
                [
                    pn.pane.Markdown(f"**Marker:** {m_str}"),
                    pn.Column(*m_rows, margin=(0, 0, 0, 4)),
                ]
            )

        if not color_cols and not marker_cols:
            items.append(
                pn.pane.Markdown(
                    "*Select **Color By** or **Marker By** to see categories.*"
                )
            )

        return pn.Card(
            pn.Column(*items, sizing_mode="stretch_width"),
            collapsible=False,
            margin=(0, 0, 0, 10),
            width=210,
        )

    @param.depends(
        "x",
        "y",
        "color_by",
        "marker_by",
        "color_filter",
        "color_range",
        "marker_filter",
        "group_by",
        "aggregation",
    )
    def make_plot(self):
        temp_df = self._prepare_data()
        color_cols = [
            c
            for c in (self.color_by or [])
            if c in temp_df.columns and c not in ("None", None, "")
        ]
        marker_cols = [
            c
            for c in (self.marker_by or [])
            if c in temp_df.columns and c not in ("None", None, "")
        ]

        if len(color_cols) > 1 and self._has_continuous_col(temp_df, color_cols):
            return hv.Scatter([]).opts(
                title=(
                    "Error: Multiple selections are not possible when a "
                    "continuous (colorbar) column is selected in 'Color By'."
                ),
                height=420,
                responsive=True,
            )

        # Collect active color and marker columns for hover tooltips
        hover_cols = [
            c
            for c in list(dict.fromkeys(color_cols + marker_cols))
            if c in temp_df.columns and not str(c).startswith("_")
        ]

        hvplot_opts = dict(
            x=self.x,
            y=self.y,
            xlabel=str(self.x),
            ylabel=str(self.y),
            size=120,
            height=420,
            responsive=True,
            tools=["hover"],
        )
        if hover_cols:
            hvplot_opts["hover_cols"] = hover_cols

        hv_element_opts = dict(height=420, responsive=True, tools=["hover"])

        if self.x in temp_df.columns and (
            x_lim := self._get_axis_limits(temp_df[self.x])
        ):
            hvplot_opts["xlim"] = x_lim
            hv_element_opts["xlim"] = x_lim

        if self.y in temp_df.columns and (
            y_lim := self._get_axis_limits(temp_df[self.y])
        ):
            hvplot_opts["ylim"] = y_lim
            hv_element_opts["ylim"] = y_lim

        is_continuous = self._is_continuous_color(self.df, color_cols)
        has_color = bool(color_cols and ("_c_val" in temp_df.columns or is_continuous))
        has_marker = bool(marker_cols and "_m_val" in temp_df.columns)

        if has_color and not is_continuous:
            _, all_c_cats = self._get_composite_series(self.df, color_cols)
        else:
            all_c_cats = []

        if has_marker:
            _, all_m_cats = self._get_composite_series(self.df, marker_cols)
        else:
            all_m_cats = []

        color_map = {
            cat: self.COLOR_PALETTE[i % len(self.COLOR_PALETTE)]
            for i, cat in enumerate(all_c_cats)
        }
        shape_map = {
            cat: self.MARKER_PALETTE[i % len(self.MARKER_PALETTE)]
            for i, cat in enumerate(all_m_cats)
        }

        # Apply Filters
        if is_continuous and color_cols and self.color_range:
            c_min, c_max = self.color_range
            temp_df = temp_df[
                (temp_df[color_cols[0]] >= c_min) & (temp_df[color_cols[0]] <= c_max)
            ]
        elif color_cols and "_c_val" in temp_df.columns:
            active_c_filter = self.color_filter if self.color_filter else all_c_cats
            temp_df = temp_df[temp_df["_c_val"].isin(active_c_filter)]

        if marker_cols and "_m_val" in temp_df.columns:
            active_m_filter = self.marker_filter if self.marker_filter else all_m_cats
            temp_df = temp_df[temp_df["_m_val"].isin(active_m_filter)]

        if temp_df.empty:
            return hv.Scatter([]).opts(
                title="No Data Matches Selected Filters", **hv_element_opts
            )

        sub_plots = []
        m_cats = all_m_cats if has_marker else [None]

        # Subplot Loop
        if is_continuous:
            col_name = color_cols[0]
            s = self.df[col_name].dropna()
            c_min, c_max = (
                (float(s.min()), float(s.max())) if not s.empty else (0.0, 1.0)
            )

            for m_val in m_cats:
                if m_val is None:
                    sub_df = temp_df
                else:
                    sub_df = temp_df[temp_df["_m_val"] == m_val]

                if sub_df.empty:
                    continue

                opts = dict(
                    c=col_name,
                    cmap="Viridis",
                    clim=(c_min, c_max),
                    colorbar=(len(sub_plots) == 0),
                    clabel=col_name,
                    **hvplot_opts,
                )
                if m_val:
                    opts["marker"] = shape_map[m_val]
                sub_plots.append(sub_df.hvplot.scatter(**opts))
        else:
            c_cats = all_c_cats if has_color else [None]
            for c_val in c_cats:
                for m_val in m_cats:
                    sub_df = temp_df
                    if c_val:
                        sub_df = sub_df[sub_df["_c_val"] == c_val]
                    if m_val:
                        sub_df = sub_df[sub_df["_m_val"] == m_val]

                    if sub_df.empty:
                        continue

                    opts = dict(**hvplot_opts)
                    opts["color"] = color_map[c_val] if c_val else "#377eb8"
                    if m_val:
                        opts["marker"] = shape_map[m_val]
                    sub_plots.append(sub_df.hvplot.scatter(**opts))

        plot = hv.Overlay(sub_plots) if len(sub_plots) > 1 else sub_plots[0]
        plot = plot.opts(show_legend=False)

        if hasattr(self, "tap_stream") and self.tap_stream is not None:
            self.tap_stream.source = plot

        return plot

    def _render_details(self, x, y):
        if x is None or y is None:
            return pn.pane.Markdown(
                "### Details Panel\n"
                "*Click any point on the plot above to display details here.*"
            )

        temp_df = self._prepare_data()
        has_required_cols = (
            self.x in temp_df.columns and self.y in temp_df.columns
        )
        if temp_df.empty or not has_required_cols:
            return pn.pane.Markdown("*No matching data found.*")

        try:
            x_series, target_x = _to_numeric_coords(temp_df[self.x], x)
            y_series, target_y = _to_numeric_coords(temp_df[self.y], y)

            has_valid_x_std = pd.notna(x_series.std()) and x_series.std() > 0
            x_std = x_series.std() if has_valid_x_std else 1.0

            has_valid_y_std = pd.notna(y_series.std()) and y_series.std() > 0
            y_std = y_series.std() if has_valid_y_std else 1.0

            dist = np.sqrt(
                ((x_series - target_x) / x_std) ** 2
                + ((y_series - target_y) / y_std) ** 2
            )
            best_idx = dist.idxmin()

            # Filter out hidden/internal helper columns starting with '_'
            display_cols = [
                c for c in temp_df.columns if not str(c).startswith("_")
            ]
            selected_row = temp_df.loc[[best_idx], display_cols]

            json_data = json.loads(
                selected_row.to_json(orient="records", date_format="iso")
            )[0]

            return pn.Column(
                pn.pane.Markdown(f"### Selected Record Details (Index {best_idx})"),
                pn.pane.JSON(json_data, depth=3, theme="light"),
            )
        except Exception as e:
            return pn.pane.Markdown(f"*Error matching selected point: {e}*")

    @param.depends(
        "x",
        "y",
        "color_by",
        "marker_by",
        "color_filter",
        "color_range",
        "marker_filter",
        "group_by",
        "aggregation",
    )
    def _render_plot(self):
        return pn.pane.HoloViews(self.make_plot(), sizing_mode="stretch_width")

    def create_app(self) -> pn.viewable.Viewable:
        control_width = 180

        controls_widgets = {
            c: {"width": control_width}
            for c in ["x", "y", "group_by", "aggregation"]
        }
        controls_widgets.update(
            {
                "color_by": {"width": control_width, "height": 80},
                "marker_by": {"width": control_width, "height": 80},
            }
        )

        binning_widgets = {
            "cat_col": {"width": control_width},
            "n_bins": {"width": control_width},
            "create_category": {"width": control_width, "color": "primary"},
        }

        controls_ui = pn.Param(
            self.param,
            parameters=["x", "y", "color_by", "marker_by", "group_by", "aggregation"],
            widgets=controls_widgets,
            name="Controls",
            width=control_width + 20,
        )
        binning_ui = pn.Column(
            pn.Param(
                self.param,
                parameters=["cat_col", "n_bins", "create_category"],
                widgets=binning_widgets,
                name="Binning",
                width=control_width + 20,
            ),
            pn.pane.Markdown(self.param.status_msg, width=control_width + 20),
        )

        sidebar_tabs = pn.Tabs(
            ("Controls", controls_ui),
            ("Bin Numeric", binning_ui),
            width=control_width + 30,
        )
        details_pane = pn.bind(
            self._render_details,
            x=self.tap_stream.param.x,
            y=self.tap_stream.param.y,
        )

        top_row = pn.Row(
            sidebar_tabs,
            pn.Column(self._render_plot, sizing_mode="stretch_width"),
            self._render_legend_panel,
            sizing_mode="stretch_width",
        )
        bottom_row = pn.Column(
            pn.layout.Divider(),
            details_pane,
            sizing_mode="stretch_width",
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