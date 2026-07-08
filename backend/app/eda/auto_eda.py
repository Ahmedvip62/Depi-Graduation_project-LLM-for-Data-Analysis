import logging
from typing import Any, Dict, List

import pandas as pd

logger = logging.getLogger(__name__)


def _human_bytes(num: int) -> str:
    value = float(num)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < 1024.0 or unit == "TB":
            if unit == "B":
                return f"{int(value)} {unit}"
            return f"{value:.1f} {unit}"
        value /= 1024.0
    return f"{value:.1f} TB"


def _unique(items: List[str]) -> List[str]:
    seen: set[str] = set()
    result: List[str] = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            result.append(item)
    return result


def generate_auto_eda(df: pd.DataFrame, profile_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Return upload-time profile metadata without static chart generation.

    Visuals are intentionally left empty. Chart and dashboard requests are handled
    later by the LLM-driven visualization path in api/chat.py so the UI does not
    substitute rigid charts for model-generated analysis.
    """
    numeric_columns: List[str] = list(profile_dict.get("numeric_columns", []) or [])
    categorical_columns: List[str] = list(profile_dict.get("categorical_columns", []) or [])
    datetime_columns: List[str] = list(profile_dict.get("datetime_columns", []) or [])

    summary = {
        "row_count": int(profile_dict.get("row_count", len(df)) or 0),
        "column_count": int(profile_dict.get("column_count", len(df.columns)) or 0),
        "missing_pct": float(profile_dict.get("missing_pct", 0.0) or 0.0),
        "memory_human": _human_bytes(int(profile_dict.get("memory_bytes", 0) or 0)),
        "numeric_count": len(numeric_columns),
        "categorical_count": len(categorical_columns),
        "datetime_count": len(datetime_columns),
    }

    suggestions: List[str] = []
    if datetime_columns and numeric_columns:
        suggestions.append(f"What is the trend of {numeric_columns[0]} over {datetime_columns[0]}?")
    if categorical_columns and numeric_columns:
        suggestions.append(f"Which {categorical_columns[0]} has the highest {numeric_columns[0]}?")
        suggestions.append(f"Compare the average {numeric_columns[0]} across {categorical_columns[0]}.")
    if numeric_columns:
        suggestions.append(f"Are there outliers in {numeric_columns[0]}?")
    if len(numeric_columns) >= 2:
        suggestions.append(f"Show the correlation between {numeric_columns[0]} and {numeric_columns[1]}.")
    if categorical_columns:
        suggestions.append(f"What is the distribution of records across {categorical_columns[0]}?")

    if not suggestions:
        suggestions = [
            "What are the key summary statistics of this dataset?",
            "Which columns have the most missing values?",
            "Generate a dashboard for this dataset.",
            "What patterns can you find in this dataset?",
        ]

    return {
        "summary": summary,
        "charts": [],
        "suggestions": _unique(suggestions)[:6],
    }