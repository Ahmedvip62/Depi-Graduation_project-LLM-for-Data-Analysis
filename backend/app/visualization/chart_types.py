"""Chart type detection and recommendation based on data profile + user intent."""
import logging
from typing import Any, Dict, Optional

from app.models.enums import ChartType

logger = logging.getLogger(__name__)

# Keywords that suggest specific chart types
CHART_KEYWORDS = {
    ChartType.BAR: ["bar", "compare", "comparison", "category", "group"],
    ChartType.LINE: ["line", "trend", "time", "over time", "series", "growth"],
    ChartType.SCATTER: ["scatter", "relationship", "correlation", "vs", "versus"],
    ChartType.PIE: ["pie", "proportion", "share", "percentage", "distribution of"],
    ChartType.HISTOGRAM: ["histogram", "distribution", "frequency", "spread"],
    ChartType.HEATMAP: ["heatmap", "heat", "correlation matrix", "correlations"],
    ChartType.BOX: ["box", "boxplot", "outlier", "quartile", "spread"],
    ChartType.VIOLIN: ["violin", "violinplot", "probability density"],
    ChartType.STRIP: ["strip", "stripplot", "jitter"],
    ChartType.FUNNEL: ["funnel", "pipeline", "conversion funnel"],
    ChartType.FUNNEL_AREA: ["funnel area"],
    ChartType.TREEMAP: ["treemap", "hierarchical rectangle"],
    ChartType.SUNBURST: ["sunburst", "hierarchical ring"],
    ChartType.ICICLE: ["icicle"],
    ChartType.WATERFALL: ["waterfall", "cumulative change"],
    ChartType.AREA: ["area chart", "stacked area"],
    ChartType.RADAR: ["radar", "spider chart", "polar grid"],
    ChartType.DENSITY_HEATMAP: ["density heatmap"],
    ChartType.DENSITY_CONTOUR: ["density contour"],
    ChartType.SCATTER_GEOMAP: ["scatter map", "geo scatter"],
    ChartType.CHOROPLETH: ["choropleth", "world map", "country map", "heat map of countries"],
    ChartType.SCATTER_MATRIX: ["scatter matrix", "pairplot", "pairs"],
    ChartType.PARALLEL_COORDINATES: ["parallel coordinates"],
    ChartType.PARALLEL_CATEGORIES: ["parallel categories"],
    ChartType.SCATTER_3D: ["3d scatter", "scatter 3d", "3d plot"],
    ChartType.GAUGE: ["gauge", "dial indicator", "speedometer"],
    ChartType.TIMELINE: ["timeline", "gantt", "schedule chart"],
}

# Generic words that imply the user wants a visual artifact.
VISUAL_KEYWORDS = [
    "chart", "plot", "graph", "visual", "visualize", "visualise",
    "draw", "show me", "diagram", "figure", "dashboard", "map", "maps",
]

_NUMERIC_DTYPE_SET = {
    "int", "int8", "int16", "int32", "int64",
    "uint8", "uint16", "uint32", "uint64",
    "float", "float16", "float32", "float64",
    "Int8", "Int16", "Int32", "Int64",
    "UInt8", "UInt16", "UInt32", "UInt64",
    "Float32", "Float64",
    "number",
}


def is_numeric_dtype(dtype: Any) -> bool:
    """Unified numeric dtype detection covering int/float 32/64 and nullable types."""
    if dtype is None:
        return False
    dtype_str = str(dtype).strip()
    if dtype_str in _NUMERIC_DTYPE_SET:
        return True
    lowered = dtype_str.lower()
    return lowered.startswith("int") or lowered.startswith("float") or lowered.startswith("uint")


def query_implies_visual(query: str) -> bool:
    """Keyword-based heuristic for routing: does the query want a chart?"""
    if not query:
        return False
    query_lower = query.lower()
    if any(kw in query_lower for kw in VISUAL_KEYWORDS):
        return True
    for keywords in CHART_KEYWORDS.values():
        if any(kw in query_lower for kw in keywords):
            return True
    return False


def detect_chart_type(
    query: str, profile: dict, explicit_type: Optional[str] = None
) -> Dict[str, Any]:
    """Detect the best chart type from user query + data profile."""

    # If user explicitly requested a type, use it
    if explicit_type and explicit_type in [t.value for t in ChartType]:
        return {"type": explicit_type}

    query_lower = query.lower()

    # Keyword matching
    for chart_type, keywords in CHART_KEYWORDS.items():
        if any(kw in query_lower for kw in keywords):
            logger.info("Detected chart type '%s' from keywords", chart_type.value)
            return {"type": chart_type.value}

    # Heuristic based on data profile
    columns = profile.get("columns", {})
    numeric_cols = [c for c, i in columns.items() if is_numeric_dtype(i.get("dtype"))]
    cat_cols = [
        c for c, i in columns.items() if not is_numeric_dtype(i.get("dtype"))
    ]

    if len(numeric_cols) >= 2 and not cat_cols:
        return {"type": ChartType.SCATTER.value}
    elif cat_cols and numeric_cols:
        return {"type": ChartType.BAR.value}
    elif len(numeric_cols) == 1:
        return {"type": ChartType.HISTOGRAM.value}

    return {"type": ChartType.BAR.value}
