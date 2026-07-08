"""ChartFactory: declarative, validated Plotly chart builder.

Charts are built only from a structured chart_spec (type + columns + aggregation)
produced by the model's schema-forced visual plan. There is deliberately NO
arbitrary-code execution path: the model never runs Python here, so an uploaded
dataset or chat message can't trigger code execution / file reads.
"""
import logging
from typing import Any, Dict

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from app.models.enums import ChartType

logger = logging.getLogger(__name__)

# Project branding palette applied to every generated figure (indigo/amber instrument theme).
COLOR_SEQUENCE = ["#6366F1", "#F0A92B", "#9098FB", "#34D399", "#F472B6", "#22D3EE", "#98A2B3"]


def _apply_aesthetic(fig: go.Figure) -> go.Figure:
    """Apply the shared aesthetic overrides to a Plotly figure."""
    # Detect if the figure is a Heatmap to apply larger margins for labels
    is_heatmap = any(trace.type == "heatmap" for trace in fig.data)
    margin = dict(l=110, r=20, t=44, b=110) if is_heatmap else dict(l=20, r=20, t=44, b=24)

    fig.update_layout(
        template="plotly_dark",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        margin=margin,
        font=dict(color="#C7CEDA"),
        colorway=COLOR_SEQUENCE,
    )
    return fig


def _apply_filters(df: pd.DataFrame, filters: list[dict]) -> pd.DataFrame:
    """Safely apply declarative filters to the DataFrame using Pandas boolean indexing."""
    if not isinstance(filters, list) or not filters:
        return df
    filtered_df = df.copy()
    for f in filters:
        col = f.get("column")
        op = f.get("operator")
        val = f.get("value")
        if col not in filtered_df.columns or not op:
            continue
        op = op.lower().strip()
        try:
            if op == "eq":
                filtered_df = filtered_df[filtered_df[col] == val]
            elif op == "ne":
                filtered_df = filtered_df[filtered_df[col] != val]
            elif op == "gt":
                filtered_df = filtered_df[filtered_df[col] > val]
            elif op == "ge":
                filtered_df = filtered_df[filtered_df[col] >= val]
            elif op == "lt":
                filtered_df = filtered_df[filtered_df[col] < val]
            elif op == "le":
                filtered_df = filtered_df[filtered_df[col] <= val]
            elif op == "contains":
                filtered_df = filtered_df[filtered_df[col].astype(str).str.contains(str(val), case=False, na=False)]
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to apply filter %s: %s", f, exc)
    return filtered_df


class ChartFactory:
    @staticmethod
    def generate_chart(df: pd.DataFrame, chart_spec: Dict[str, Any]) -> str:
        """Build a chart declaratively from a model-produced chart_spec dict.

        chart_spec keys: type, x, y, color, title, aggregate, top_n, sort, filters.
        type in {bar, line, scatter, pie, histogram, heatmap, box}.

        Coercion policy: the chart's spine (a valid type + a usable x, where the
        type needs one) must be present or we raise. But a single off field the
        model got wrong — an invalid `color`, a non-numeric `y` under an
        aggregate, a `y` that doesn't exist — is corrected or dropped rather than
        aborting the whole chart. We never substitute a different/static chart;
        we render the model's intent as closely as the columns allow.
        """
        if not isinstance(chart_spec, dict):
            raise ValueError("chart_spec must be an object.")

        # Apply declarative filters first
        filters = chart_spec.get("filters") or []
        df = _apply_filters(df, filters)

        chart_type = str(chart_spec.get("type", "")).lower().strip()
        if not chart_type:
            raise ValueError("chart_spec.type is required.")
        supported_types = {t.value for t in ChartType}
        if chart_type not in supported_types:
            raise ValueError(
                f"Unsupported chart type '{chart_type}'. Supported: "
                f"{', '.join(sorted(supported_types))}"
            )

        x = chart_spec.get("x")
        y = chart_spec.get("y")
        color = chart_spec.get("color")
        title = chart_spec.get("title")
        aggregate = str(
            chart_spec.get("aggregate") or chart_spec.get("aggregation") or ""
        ).lower().strip()
        top_n = chart_spec.get("top_n")
        sort = str(chart_spec.get("sort") or "desc").lower().strip()
        if aggregate in {"none", "null", "-"}:
            aggregate = ""

        def _valid(col: Any) -> bool:
            return col is not None and col in df.columns

        def _is_numeric(col: Any) -> bool:
            return _valid(col) and pd.api.types.is_numeric_dtype(df[col])

        # Auto-aggregate if there are duplicate values on the x-axis to prevent vertical scribbling.
        if chart_type in {"bar", "line", "pie"} and not aggregate and x is not None and _valid(x) and not df.empty:
            if df[x].duplicated().any():
                if y and _is_numeric(y):
                    aggregate = "sum"
                    logger.info("Auto-aggregating duplicated x='%s' using sum.", x)
                else:
                    aggregate = "count"
                    logger.info("Auto-aggregating duplicated x='%s' using count.", x)

        # x is the chart's spine for every type except heatmap; it must be real.
        if chart_type != "heatmap":
            if x is not None and not _valid(x):
                raise ValueError(
                    f"Column '{x}' (x) not found in dataset. "
                    f"Available columns: {list(df.columns)}"
                )

        # y / color are secondary: drop a wrong one instead of failing the chart.
        if y is not None and not _valid(y):
            logger.info("Dropping unknown y column '%s' from chart spec.", y)
            y = None
        if color is not None and not _valid(color):
            logger.info("Dropping unknown color column '%s' from chart spec.", color)
            color = None
        # A color identical to x adds nothing and can break grouping; drop it.
        if color is not None and color == x:
            color = None

        # An aggregate over a non-numeric (or missing) measure means "count" —
        # that's the model's evident intent, not a fabricated chart.
        if aggregate in {"sum", "mean", "median", "min", "max"} and not _is_numeric(y):
            logger.info(
                "Aggregate '%s' requested on non-numeric/absent y='%s'; using count.",
                aggregate, y,
            )
            aggregate = "count"
            y = None

        VALUE = "__chart_value__"  # internal; never collides with a real column

        def _display_label(default: str) -> str:
            label = chart_spec.get("value_label")
            return str(label) if label else default

        def _top(frame: pd.DataFrame, value_col: str | None) -> pd.DataFrame:
            if not top_n:
                return frame
            try:
                limit = max(1, min(int(top_n), 50))
            except (TypeError, ValueError):
                return frame
            if value_col and value_col in frame.columns:
                return frame.sort_values(value_col, ascending=sort == "asc").head(limit)
            return frame.head(limit)

        def _aggregate(frame: pd.DataFrame) -> tuple[pd.DataFrame, str | None]:
            """Return (plot_frame, value_column). Aggregates into a distinct
            internal column so y==x / y==color can never collide on reset_index."""
            if not x:
                return frame, y
            group_keys = [x] + ([color] if color else [])

            wants_count = aggregate == "count" or (not y and chart_type in {"bar", "pie", "line"})
            if wants_count:
                grouped = (
                    frame.groupby(group_keys, dropna=False)
                    .size()
                    .reset_index(name=VALUE)
                    .rename(columns={VALUE: _display_label("count")})
                )
                value_col = _display_label("count")
                return _top(grouped, value_col), value_col

            if not aggregate or not y:
                return frame, y

            grouped = (
                frame.groupby(group_keys, dropna=False)[y]
                .agg(aggregate)
                .reset_index(name=VALUE)
                .rename(columns={VALUE: y})
            )
            return _top(grouped, y), y

        if chart_type == "bar":
            if x is None:
                raise ValueError("Bar chart requires 'x'.")
            plot_df, value_col = _aggregate(df)
            barmode = chart_spec.get("barmode") or "group"
            fig = px.bar(plot_df, x=x, y=value_col, color=color, barmode=barmode, title=title)
        elif chart_type == "line":
            if x is None:
                raise ValueError("Line chart requires 'x'.")
            plot_df, value_col = _aggregate(df)
            if x in plot_df.columns:
                parsed_x = pd.to_datetime(plot_df[x], errors="coerce", format="mixed")
                if parsed_x.notna().mean() > 0.8:
                    plot_df = plot_df.assign(**{x: parsed_x}).sort_values(x)
            fig = px.line(plot_df, x=x, y=value_col, color=color, title=title)
        elif chart_type == "scatter":
            if x is None or y is None:
                raise ValueError("Scatter chart requires numeric 'x' and 'y'.")
            size_col = chart_spec.get("size") if _valid(chart_spec.get("size")) else None
            fig = px.scatter(df, x=x, y=y, color=color, size=size_col, title=title)
        elif chart_type == "pie":
            if x is None:
                raise ValueError("Pie chart requires 'x' (names).")
            plot_df, value_col = _aggregate(df)
            # Pie slices are meaningless for negative/zero values; drop them.
            if value_col and value_col in plot_df.columns:
                plot_df = plot_df[plot_df[value_col] > 0]
                if plot_df.empty:
                    raise ValueError("Pie chart has no positive values to display.")
            fig = px.pie(plot_df, names=x, values=value_col, title=title)
        elif chart_type == "histogram":
            if x is None:
                raise ValueError("Histogram requires 'x'.")
            # Plotly histogram with a categorical y errors; only pass numeric y.
            hist_y = y if _is_numeric(y) else None
            fig = px.histogram(df, x=x, y=hist_y, color=color, title=title)
        elif chart_type == "box":
            if y is None and x is None:
                raise ValueError("Box plot requires 'x' or 'y'.")
            fig = px.box(df, x=x, y=y, color=color, title=title)
        elif chart_type == "violin":
            if y is None and x is None:
                raise ValueError("Violin plot requires 'x' or 'y'.")
            fig = px.violin(df, x=x, y=y, color=color, box=True, points="outliers", title=title)
        elif chart_type == "strip":
            if y is None and x is None:
                raise ValueError("Strip plot requires 'x' or 'y'.")
            fig = px.strip(df, x=x, y=y, color=color, title=title)
        elif chart_type == "funnel":
            if x is None or y is None:
                raise ValueError("Funnel chart requires 'x' (stages) and 'y' (values).")
            plot_df, value_col = _aggregate(df)
            fig = px.funnel(plot_df, x=value_col, y=x, color=color, title=title)
        elif chart_type == "funnel_area":
            if x is None:
                raise ValueError("Funnel Area requires 'x' (names).")
            plot_df, value_col = _aggregate(df)
            fig = px.funnel_area(plot_df, names=x, values=value_col, title=title)
        elif chart_type in {"treemap", "sunburst", "icicle"}:
            path_cols = chart_spec.get("path")
            if not path_cols or not isinstance(path_cols, list):
                path_cols = [x] if x else []
                if color and color not in path_cols:
                    path_cols.append(color)
            path_cols = [p for p in path_cols if _valid(p)]
            if not path_cols:
                raise ValueError(f"{chart_type.capitalize()} requires a valid hierarchy 'path' or 'x' column.")
            
            # Aggregate if values are requested
            value_col = y if y and _is_numeric(y) else None
            
            if chart_type == "treemap":
                fig = px.treemap(df, path=path_cols, values=value_col, color=color, title=title)
            elif chart_type == "sunburst":
                fig = px.sunburst(df, path=path_cols, values=value_col, color=color, title=title)
            else:
                fig = px.icicle(df, path=path_cols, values=value_col, color=color, title=title)
        elif chart_type == "waterfall":
            if x is None or y is None:
                raise ValueError("Waterfall chart requires 'x' (categories) and 'y' (values).")
            plot_df, value_col = _aggregate(df)
            fig = go.Figure(go.Waterfall(
                name="Waterfall",
                orientation="v",
                x=plot_df[x].astype(str).tolist(),
                y=plot_df[value_col].tolist(),
                connector={"line": {"color": "rgb(63, 63, 63)"}},
            ))
            fig.update_layout(title=title)
        elif chart_type == "area":
            if x is None:
                raise ValueError("Area chart requires 'x'.")
            plot_df, value_col = _aggregate(df)
            if x in plot_df.columns:
                parsed_x = pd.to_datetime(plot_df[x], errors="coerce", format="mixed")
                if parsed_x.notna().mean() > 0.8:
                    plot_df = plot_df.assign(**{x: parsed_x}).sort_values(x)
            fig = px.area(plot_df, x=x, y=value_col, color=color, title=title)
        elif chart_type == "radar":
            if x is None or y is None:
                raise ValueError("Radar chart requires 'x' (categories) and 'y' (values).")
            plot_df, value_col = _aggregate(df)
            fig = go.Figure()
            if color and color in plot_df.columns:
                for name, group in plot_df.groupby(color):
                    fig.add_trace(go.Scatterpolar(
                        r=group[value_col].tolist(),
                        theta=group[x].astype(str).tolist(),
                        fill='toself',
                        name=str(name)
                    ))
            else:
                fig.add_trace(go.Scatterpolar(
                    r=plot_df[value_col].tolist(),
                    theta=plot_df[x].astype(str).tolist(),
                    fill='toself',
                    name=y
                ))
            fig.update_layout(polar=dict(radialaxis=dict(visible=True)), showlegend=True, title=title)
        elif chart_type == "density_heatmap":
            if x is None or y is None:
                raise ValueError("Density Heatmap requires 'x' and 'y'.")
            fig = px.density_heatmap(df, x=x, y=y, title=title)
        elif chart_type == "density_contour":
            if x is None or y is None:
                raise ValueError("Density Contour requires 'x' and 'y'.")
            fig = px.density_contour(df, x=x, y=y, title=title)
            fig.update_traces(contours_coloring="fill", contours_showlabels=True)
        elif chart_type == "scatter_geo":
            size_col = chart_spec.get("size") if _valid(chart_spec.get("size")) else None
            # If coordinates, use lat/lon. If labels, use location mode.
            if _is_numeric(x) and _is_numeric(y):
                fig = px.scatter_geo(df, lat=x, lon=y, size=size_col, color=color, title=title)
            else:
                fig = px.scatter_geo(df, locations=x, locationmode="country names", size=size_col, color=color, title=title)
        elif chart_type == "choropleth":
            if x is None or y is None:
                raise ValueError("Choropleth map requires 'x' (locations) and 'y' (values).")
            plot_df, value_col = _aggregate(df)
            sample_val = str(plot_df[x].dropna().iloc[0]) if not plot_df[x].dropna().empty else ""
            mode = "ISO-3" if len(sample_val) == 3 else "country names"
            fig = px.choropleth(plot_df, locations=x, locationmode=mode, color=value_col, title=title)
        elif chart_type == "scatter_matrix":
            numeric_cols = list(df.select_dtypes(include="number").columns)[:5]
            if not numeric_cols:
                raise ValueError("Scatter matrix requires numeric columns.")
            fig = px.scatter_matrix(df, dimensions=numeric_cols, color=color, title=title)
        elif chart_type == "parallel_coordinates":
            numeric_cols = list(df.select_dtypes(include="number").columns)[:5]
            if not numeric_cols:
                raise ValueError("Parallel coordinates require numeric columns.")
            color_col = color if color and _is_numeric(color) else None
            fig = px.parallel_coordinates(df, dimensions=numeric_cols, color=color_col, title=title)
        elif chart_type == "parallel_categories":
            cat_cols = list(df.select_dtypes(include=["object", "category", "bool"]).columns)[:4]
            if not cat_cols:
                raise ValueError("Parallel categories require categorical columns.")
            fig = px.parallel_categories(df, dimensions=cat_cols, color=color if color and _is_numeric(color) else None, title=title)
        elif chart_type == "scatter_3d":
            z = chart_spec.get("z")
            if x is None or y is None or z is None or not _valid(z):
                num_cols = list(df.select_dtypes(include="number").columns)
                if len(num_cols) < 3:
                    raise ValueError("3D Scatter chart requires three numeric columns.")
                x, y, z = num_cols[0], num_cols[1], num_cols[2]
            fig = px.scatter_3d(df, x=x, y=y, z=z, color=color, title=title)
        elif chart_type == "gauge":
            if y is None or not _is_numeric(y):
                raise ValueError("Gauge indicator requires a numeric 'y' column.")
            val = float(df[y].mean())
            max_val = float(df[y].max()) if not pd.isna(df[y].max()) else val * 2
            fig = go.Figure(go.Indicator(
                mode="gauge+number",
                value=val,
                title={'text': title or y},
                gauge={'axis': {'range': [None, max_val]},
                       'bar': {'color': "#6366F1"},
                       'bgcolor': "rgba(0,0,0,0)"},
                domain={'x': [0, 1], 'y': [0, 1]}
            ))
            fig.update_layout(title=title)
        elif chart_type == "timeline":
            if x is None or y is None:
                raise ValueError("Timeline chart requires start time (x) and end time (y).")
            timeline_df = df.copy()
            timeline_df[x] = pd.to_datetime(timeline_df[x], errors="coerce", format="mixed")
            timeline_df[y] = pd.to_datetime(timeline_df[y], errors="coerce", format="mixed")
            task_col = color if color else timeline_df.columns[0]
            fig = px.timeline(timeline_df, x_start=x, x_end=y, y=task_col, color=color, title=title)
            fig.update_yaxes(autorange="reversed")
        elif chart_type == "heatmap":
            numeric_df = df.select_dtypes(include="number")
            if numeric_df.shape[1] < 2:
                raise ValueError("Heatmap requires at least two numeric columns.")
            corr = numeric_df.corr()
            fig = px.imshow(
                corr,
                text_auto=".2f",
                title=title or "Correlation Matrix",
                color_continuous_scale="RdBu_r",
                aspect="auto",
            )
        else:
            raise ValueError(f"Unknown chart type '{chart_type}'.")

        return _apply_aesthetic(fig).to_json()
