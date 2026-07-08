"""Prompt templates for the agentic data-analyst loop."""

from app.visualization.chart_types import is_numeric_dtype

SYSTEM_PROMPT_BASE = (
    "You are Universal Analyst, a senior data analysis assistant. "
    "Answer accurately using the provided data profile and retrieved context. "
    "If retrieved chunks are sparse, use the data profile directly instead of refusing. "
    "If a requested metric is not present in the profile or context, say exactly what is missing. "
    "Cite concrete fields, counts, types, percentages, and values whenever available."
)

DATA_QA_TEMPLATE = """{system}

## Data Profile
{profile_summary}

## Retrieved Context
{context}

## User Query
{query}

Answer the user from the dataset context above. For generic questions such as
"what is this dataset about", infer the dataset's likely subject from file name,
column names, data types, sample/top values, and summary statistics. Be direct,
numeric, and useful. Never refuse a generic overview when a Data Profile is present;
use the profile as the authoritative source and state uncertainty only where the
profile truly does not identify business meaning."""

PROFILING_TEMPLATE = """{system}

## Data Profile
{profile_summary}

Summarize this dataset for the user. Cover:
1. Size (rows x columns)
2. Column groups and what they likely represent
3. Notable quality signals (missingness, cardinality, skew, outliers)
4. Analyses the user can run next"""

CHART_RECOMMENDATION_TEMPLATE = """{system}

## Data Profile
{profile_summary}

## User Request
{query}

Recommend the best validated chart spec for this request. Respond with ONLY a JSON object:
{{
  "type": "bar|line|scatter|pie|histogram|heatmap|box",
  "x": "exact column name or null",
  "y": "exact column name or null",
  "color": "exact column name or null",
  "aggregate": "sum|mean|median|min|max|count|null",
  "top_n": 10,
  "sort": "asc|desc",
  "title": "descriptive title",
  "description": "one short sentence explaining why this chart fits"
}}

Rules:
- Use only exact column names from the Data Profile.
- Use aggregate="count" for record counts.
- Use top_n between 5 and 20 for high-cardinality category axes.
- Use null, not the string "null", for omitted fields."""


SKILL_VISUALIZATION = "visualization"
SKILL_ANALYSIS_WITH_VISUAL = "analysis_with_visual"
SKILL_GENERAL_QA = "general_qa"
SKILL_REPORT = "report"
SKILL_PREDICTION = "prediction"

ROUTER_SKILLS = (
    SKILL_VISUALIZATION,
    SKILL_ANALYSIS_WITH_VISUAL,
    SKILL_GENERAL_QA,
    SKILL_REPORT,
    SKILL_PREDICTION,
)

SKILL_LABELS = {
    SKILL_VISUALIZATION: "Visualization",
    SKILL_ANALYSIS_WITH_VISUAL: "Deep Analysis",
    SKILL_GENERAL_QA: "Data Q&A",
    SKILL_REPORT: "PDF Report",
    SKILL_PREDICTION: "Predictive Analytics",
}

SKILL_REASONS = {
    SKILL_VISUALIZATION: "The request needs one or more generated Plotly visuals.",
    SKILL_ANALYSIS_WITH_VISUAL: "The request needs analytical reasoning with supporting visuals.",
    SKILL_GENERAL_QA: "The request can be answered directly from the dataset profile and retrieved context.",
    SKILL_REPORT: "The user wants a downloadable PDF report from this session.",
    SKILL_PREDICTION: "The request asks to predict, forecast, or build regression/classification models on the dataset.",
}

SKILL_ROUTER_SYSTEM = (
    "You are an intent router for a data-analysis assistant. "
    "Classify the user's message into EXACTLY ONE category."
)

ROUTER_TEMPLATE = """{system}

Categories:
- visualization: the user wants a chart, plot, graph, visual, EDA dashboard, or visual dashboard.
- analysis_with_visual: the user wants deep statistical analysis, comparisons,
  trends, correlations, or reasoning that benefits from supporting charts.
- general_qa: the user asks a direct factual or explanatory question about the data.
- report: the user asks to generate, export, download, or create a PDF report.

User message: "{message}"

Reply with ONLY one token: visualization OR analysis_with_visual OR general_qa OR report."""


def build_router_prompt(message: str) -> str:
    """Terse classification prompt for the small router model."""
    return ROUTER_TEMPLATE.format(system=SKILL_ROUTER_SYSTEM, message=message)


THINKING_TRIGGER_KEYWORDS = [
    "compare", "trend", "correlat", "predict", "why", "explain",
    "relationship", "anomal", "outlier", "pattern", "across", "dashboard",
    "eda", "visual", "chart", "plot",
]

THINKING_TEMPLATE = """You are planning how to answer a data-analysis question.

## Context
{context}

## Question
{question}

Write a SHORT reasoning plan (3-6 concise lines) describing the steps you will
take to answer. Reference relevant columns or metrics. Do not answer the
question yet; only outline the plan."""


def should_use_thinking_mode(query: str) -> bool:
    """Heuristic: enable the thinking pass for complex analytical queries."""
    query_lower = query.lower()
    return any(kw in query_lower for kw in THINKING_TRIGGER_KEYWORDS)


def build_thinking_prompt(question: str, context: str) -> str:
    """Prompt for the dedicated short reasoning pass before the final answer."""
    return THINKING_TEMPLATE.format(question=question, context=context or "(none)")


def _fmt_num(value) -> str:
    """Format a numeric value compactly, tolerating None / non-numeric."""
    if value is None:
        return "?"
    if isinstance(value, (int,)) and not isinstance(value, bool):
        return f"{value:,}"
    if isinstance(value, float):
        return f"{value:,.2f}"
    return str(value)


def build_profile_summary(profile: dict, query: str = "") -> str:
    """Build a concise text summary of a DataProfile dict.

    If the dataset has >25 columns, detailed stats are only rendered for the first
    15 columns plus any columns mentioned in the query. Other columns are listed compactly.
    """
    if not profile:
        return "No data profile available."

    lines = [
        f"Dataset: {profile.get('file_name', 'unknown')} "
        f"({profile.get('row_count', '?')} rows x "
        f"{profile.get('column_count', '?')} columns)",
    ]

    overall_missing = profile.get("missing_pct")
    if overall_missing is not None:
        lines.append(f"Overall missing: {_fmt_num(overall_missing)}%")

    numeric = profile.get("numeric_columns") or []
    categorical = profile.get("categorical_columns") or []
    datetime_cols = profile.get("datetime_columns") or []
    if numeric or categorical or datetime_cols:
        lines.append(
            "Column groups: "
            f"numeric={', '.join(numeric[:12]) or 'none'}; "
            f"categorical={', '.join(categorical[:12]) or 'none'}; "
            f"datetime={', '.join(datetime_cols[:8]) or 'none'}"
        )

    lines.append("")
    lines.append("Columns:")

    columns = profile.get("columns", {})
    query_lower = query.lower()
    query_cols = {c for c in columns if c.lower() in query_lower}

    compress = len(columns) > 25
    compact_cols = []

    for idx, (col_name, col_info) in enumerate(columns.items()):
        dtype = col_info.get("dtype", "unknown")
        semantic = col_info.get("semantic_type")
        type_label = f"{dtype}"
        if semantic:
            type_label = f"{dtype}/{semantic}"

        # If compressing, only show full stats for the first 15 columns or columns mentioned in query.
        if compress and idx >= 15 and col_name not in query_cols:
            compact_cols.append(f"{col_name} ({type_label})")
            continue

        nulls = col_info.get("null_count", 0)
        uniques = col_info.get("unique_count", 0)
        line = f"  - {col_name} ({type_label}): {uniques} unique, {nulls} nulls"

        missing_pct = col_info.get("missing_pct")
        if missing_pct is not None:
            line += f", missing={_fmt_num(missing_pct)}%"

        if col_info.get("mean_value") is not None:
            line += f", mean={_fmt_num(col_info.get('mean_value'))}"
        if col_info.get("median_value") is not None:
            line += f", median={_fmt_num(col_info.get('median_value'))}"
        if col_info.get("std_value") is not None:
            line += f", std={_fmt_num(col_info.get('std_value'))}"
        if col_info.get("skewness") is not None:
            line += f", skew={_fmt_num(col_info.get('skewness'))}"
        if col_info.get("outlier_count") is not None and col_info.get("outlier_count") > 0:
            line += f", outliers={col_info.get('outlier_count')}"
        if col_info.get("min_value") is not None:
            line += (
                f", range=[{_fmt_num(col_info.get('min_value'))}, "
                f"{_fmt_num(col_info.get('max_value'))}]"
            )

        top_values = col_info.get("top_values")
        if top_values:
            if isinstance(top_values, dict):
                pairs = list(top_values.items())[:3]
                top_str = ", ".join(f"{k}={v}" for k, v in pairs)
            elif isinstance(top_values, (list, tuple)):
                rendered_values = []
                for item in list(top_values)[:3]:
                    if isinstance(item, dict):
                        value = item.get("value")
                        count = item.get("count")
                        rendered_values.append(
                            f"{value}={count}" if count is not None else str(value)
                        )
                    else:
                        rendered_values.append(str(item))
                top_str = ", ".join(rendered_values)
            else:
                top_str = str(top_values)
            if top_str:
                line += f", top: {top_str}"

        sample_values = col_info.get("sample_values")
        if sample_values:
            sample = ", ".join(str(v) for v in list(sample_values)[:3])
            if sample:
                line += f", sample: {sample}"

        lines.append(line)

    if compact_cols:
        lines.append("")
        lines.append(f"  - Other columns (name [type]): {', '.join(compact_cols)}")

    correlations = profile.get("correlations")
    if correlations:
        lines.append("")
        lines.append("Notable correlations:")
        rendered = 0
        if isinstance(correlations, dict):
            for key, val in correlations.items():
                if rendered >= 8:
                    break
                if isinstance(val, dict):
                    for inner_key, inner_val in val.items():
                        if rendered >= 8:
                            break
                        if key == inner_key:
                            continue
                        lines.append(f"  - {key} ~ {inner_key}: {_fmt_num(inner_val)}")
                        rendered += 1
                else:
                    lines.append(f"  - {key}: {_fmt_num(val)}")
                    rendered += 1

    return "\n".join(lines)


def _chart_role(col_info: dict) -> str:
    """Map a column's profile to a planner-facing role label."""
    semantic = (col_info.get("semantic_type") or "").lower()
    if semantic == "datetime":
        return "datetime"
    if semantic == "continuous":
        return "numeric"
    if semantic == "id":
        return "id"
    if semantic == "boolean":
        return "categorical"
    if semantic in ("categorical", "text"):
        return semantic
    # Fall back to dtype when semantic type is absent.
    return "numeric" if is_numeric_dtype(col_info.get("dtype")) else "categorical"


def build_chart_plan_context(profile: dict) -> str:
    """Compact, planner-only column manifest.

    Deliberately omits the Q&A system prompt and "answer the user" framing so the
    chart planner sees ONLY the column facts it needs to choose axes. Keeps exact
    column names so the "use only exact column names" rule stays grounded.
    """
    if not profile:
        return "No dataset is loaded."

    lines = [
        f"Dataset: {profile.get('file_name', 'unknown')} "
        f"({_fmt_num(profile.get('row_count'))} rows x "
        f"{_fmt_num(profile.get('column_count'))} columns)",
        "",
        "Columns (use these EXACT names; role tells you valid axes):",
    ]

    for col_name, col_info in (profile.get("columns") or {}).items():
        role = _chart_role(col_info)
        parts = [f"  - \"{col_name}\" [{role}]"]
        uniques = col_info.get("unique_count")
        if uniques is not None:
            parts.append(f"{_fmt_num(uniques)} unique")
        if role == "numeric":
            if col_info.get("min_value") is not None:
                parts.append(
                    f"range {_fmt_num(col_info.get('min_value'))}..{_fmt_num(col_info.get('max_value'))}"
                )
            if col_info.get("mean_value") is not None:
                parts.append(f"mean {_fmt_num(col_info.get('mean_value'))}")
        top_values = col_info.get("top_values")
        if top_values and role in ("categorical", "id"):
            rendered = []
            for item in list(top_values)[:3]:
                if isinstance(item, dict):
                    rendered.append(str(item.get("value")))
                else:
                    rendered.append(str(item))
            if rendered:
                parts.append("top: " + ", ".join(rendered))
        lines.append(", ".join(parts))

    numeric = profile.get("numeric_columns") or []
    if len(numeric) >= 2:
        lines.append("")
        lines.append(f"Numeric columns available for heatmap/scatter: {', '.join(numeric[:12])}")

    return "\n".join(lines)


def build_data_qa_prompt(query: str, context: str, profile: dict) -> str:
    """Build a prompt for data Q&A with profile context."""
    return DATA_QA_TEMPLATE.format(
        system=SYSTEM_PROMPT_BASE,
        profile_summary=build_profile_summary(profile, query),
        context=context or "No retrieved chunks matched. Use the Data Profile above.",
        query=query,
    )


def build_profiling_prompt(profile: dict) -> str:
    return PROFILING_TEMPLATE.format(
        system=SYSTEM_PROMPT_BASE,
        profile_summary=build_profile_summary(profile),
    )


def build_chart_prompt(query: str, profile: dict) -> str:
    return CHART_RECOMMENDATION_TEMPLATE.format(
        system=SYSTEM_PROMPT_BASE,
        profile_summary=build_profile_summary(profile, query),
        query=query,
    )


def build_prompt(query: str, context: str) -> str:
    return build_data_qa_prompt(query, context, {})


def build_cleaning_quality_report(profile: dict) -> str:
    """Build a detailed quality report for the cleaning LLM.

    Analyses each column for skewness, outliers, missing values, type
    mismatches, text inconsistencies, and low-cardinality numerics so
    the LLM can pick the most appropriate cleaning strategy.
    """
    if not profile:
        return "No data profile available for quality analysis."

    columns = profile.get("columns", {})
    row_count = profile.get("row_count", 0)
    if not columns or not row_count:
        return "Dataset is empty or has no columns."

    warnings: list[str] = []
    clean_cols: list[str] = []

    # Check for duplicate rows hint
    warnings.append("## Dataset Overview")
    warnings.append(
        f"- Rows: {row_count}, Columns: {len(columns)}, "
        f"Overall missing: {_fmt_num(profile.get('missing_pct', 0))}%"
    )
    warnings.append("")
    warnings.append("## Column-Level Quality Warnings")

    for col_name, col_info in columns.items():
        if isinstance(col_info, dict):
            info = col_info
        else:
            # Pydantic model
            info = col_info.model_dump() if hasattr(col_info, "model_dump") else dict(col_info)

        dtype = info.get("dtype", "unknown")
        semantic = info.get("semantic_type", "")
        null_count = info.get("null_count", 0)
        missing_pct = info.get("missing_pct", 0.0)
        unique_count = info.get("unique_count", 0)
        mean_val = info.get("mean_value")
        median_val = info.get("median_value")
        std_val = info.get("std_value")
        skewness = info.get("skewness")
        outlier_count = info.get("outlier_count")

        col_warnings: list[str] = []

        # --- Missing values ---
        if null_count > 0:
            severity = "HIGH" if missing_pct > 50 else ("MEDIUM" if missing_pct > 10 else "LOW")
            col_warnings.append(
                f"MISSING ({severity}): {null_count} nulls ({_fmt_num(missing_pct)}%)"
            )
            # Suggest strategy based on type and distribution
            is_numeric = semantic in ("continuous",)
            if is_numeric and skewness is not None:
                if abs(skewness) > 1.0:
                    col_warnings.append(
                        f"  -> Data is SKEWED (skewness={_fmt_num(skewness)}), "
                        f"recommend strategy='median' (median={_fmt_num(median_val)})"
                    )
                else:
                    col_warnings.append(
                        f"  -> Data is roughly symmetric (skewness={_fmt_num(skewness)}), "
                        f"strategy='mean' is appropriate (mean={_fmt_num(mean_val)})"
                    )
            elif semantic in ("categorical", "boolean", "text"):
                col_warnings.append(
                    "  -> Categorical/text column, recommend strategy='mode' or strategy='value'"
                )

        # --- Outliers ---
        if outlier_count is not None and outlier_count > 0:
            outlier_pct = (outlier_count / row_count) * 100 if row_count else 0
            severity = "HIGH" if outlier_pct > 5 else ("MEDIUM" if outlier_pct > 1 else "LOW")
            col_warnings.append(
                f"OUTLIERS ({severity}): {outlier_count} outlier rows ({_fmt_num(outlier_pct)}%)"
            )
            if outlier_pct > 10:
                col_warnings.append(
                    "  -> High outlier %, consider cap_outliers instead of remove_outliers"
                )

        # --- Skewness without missing (distribution warning) ---
        if skewness is not None and null_count == 0 and abs(skewness) > 2.0:
            col_warnings.append(
                f"DISTRIBUTION: Highly skewed (skewness={_fmt_num(skewness)})"
            )

        # --- Type mismatch detection ---
        if dtype == "object" and semantic == "continuous":
            col_warnings.append(
                "TYPE MISMATCH: stored as object but detected as numeric, consider convert_type to float"
            )
        if dtype == "object" and semantic == "datetime":
            col_warnings.append(
                "TYPE MISMATCH: stored as object but looks like datetime, consider convert_type to datetime"
            )

        # --- Low cardinality numeric (might be categorical) ---
        if semantic == "continuous" and unique_count <= 5 and row_count > 50:
            col_warnings.append(
                f"LOW CARDINALITY: only {unique_count} unique values in numeric column, "
                f"might be categorical"
            )

        # --- Column entirely empty ---
        if missing_pct >= 100.0:
            col_warnings.append(
                "EMPTY: Column is 100% null, consider drop_column"
            )
        # --- Single-value column ---
        elif unique_count <= 1 and null_count == 0:
            col_warnings.append(
                "CONSTANT: Column has only 1 unique value, consider drop_column"
            )

        # --- Text inconsistency ---
        sample_values = info.get("sample_values", [])
        if semantic in ("categorical", "text") and sample_values:
            has_mixed_case = False
            has_spaces = False
            for v in sample_values:
                s = str(v)
                if s != s.lower() and s != s.upper():
                    has_mixed_case = True
                if s != s.strip():
                    has_spaces = True
            if has_mixed_case or has_spaces:
                issues = []
                if has_mixed_case:
                    issues.append("mixed casing")
                if has_spaces:
                    issues.append("leading/trailing spaces")
                col_warnings.append(
                    f"TEXT INCONSISTENCY: detected {', '.join(issues)}, "
                    f"consider standardize_text"
                )

        # --- Column name issues ---
        if " " in col_name or any(c in col_name for c in "()$%&/\\"):
            col_warnings.append(
                f"NAMING: column name has special characters/spaces, consider normalize_column"
            )

        if col_warnings:
            warnings.append(f"\n### {col_name} ({dtype}, {semantic})")
            for w in col_warnings:
                warnings.append(f"  {w}")
        else:
            clean_cols.append(col_name)

    if clean_cols:
        warnings.append(f"\n## Clean Columns (no issues detected)")
        warnings.append(f"  {', '.join(clean_cols)}")

    return "\n".join(warnings)

