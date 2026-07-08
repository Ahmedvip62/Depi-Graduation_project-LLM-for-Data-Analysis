"""LLM-authored narrative for the PDF report.

The model writes the *words* (executive summary, per-section interpretation,
key findings, recommendations) as strict JSON. ReportLab renders those words
deterministically in report.py. The model never emits layout or PDF code, so a
malformed narrative degrades to "no narrative" rather than a broken document.
"""
import json
import logging
import re
from typing import Any, Optional

from app.config import settings
from app.llm.ollama_client import get_ollama_client
from app.llm.prompt_templates import build_profile_summary

logger = logging.getLogger(__name__)

# Keys the renderer knows how to place. Anything else from the model is ignored.
NARRATIVE_SHAPE = {
    "title": "str — a specific report title naming the dataset's subject",
    "executive_summary": "str — 2-4 sentences a stakeholder reads first",
    "key_findings": "list[str] — 3-6 concrete, numeric findings",
    "data_quality_note": "str — one paragraph on completeness/caveats",
    "chart_readings": "list[str] — one sentence per generated chart, in order",
    "dashboard_summary": "str — 2-3 sentences summarizing the overall dashboard layout findings",
    "anomalies": "list[str] — 2-4 detected anomalies, outliers, or warnings in the data",
    "recommendations": "list[str] — 2-5 next analytical steps",
}

# Ollama structured-output schema for the report narrative. Forces the model to
# emit an object with the right field shapes (strings / arrays of strings). Older
# Ollama builds that don't support schema `format` ignore it, so _extract_json +
# _validate remain the safety net.
REPORT_NARRATIVE_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "executive_summary": {"type": "string"},
        "key_findings": {
            "type": "array",
            "items": {"type": "string"},
        },
        "data_quality_note": {"type": "string"},
        "chart_readings": {
            "type": "array",
            "items": {"type": "string"},
        },
        "dashboard_summary": {"type": "string"},
        "anomalies": {
            "type": "array",
            "items": {"type": "string"},
        },
        "recommendations": {
            "type": "array",
            "items": {"type": "string"},
        },
    },
    "required": [
        "title",
        "executive_summary",
        "key_findings",
        "data_quality_note",
        "chart_readings",
        "dashboard_summary",
        "anomalies",
        "recommendations",
    ],
}


def _chart_titles(charts: list[Any]) -> list[str]:
    titles: list[str] = []
    for i, chart in enumerate(charts or []):
        title = None
        if isinstance(chart, dict):
            title = chart.get("title")
            if not title:
                spec = chart.get("chart_spec") or chart.get("config") or {}
                layout = spec.get("layout", {}) if isinstance(spec, dict) else {}
                t = layout.get("title") if isinstance(layout, dict) else None
                title = t.get("text") if isinstance(t, dict) else t
        titles.append(str(title) if title else f"Figure {i + 1}")
    return titles


def _extract_json(text: str) -> Any:
    cleaned = (text or "").strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        first, last = cleaned.find("{"), cleaned.rfind("}")
        if first == -1 or last <= first:
            raise ValueError("No JSON object found in narrative response.")
        return json.loads(cleaned[first : last + 1])


def _as_str(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _as_str_list(value: Any, limit: int) -> list[str]:
    if not isinstance(value, list):
        return []
    out = [v.strip() for v in value if isinstance(v, str) and v.strip()]
    return out[:limit]


def _build_prompt(profile: dict, eda: dict, chart_titles: list[str], insights: list[str]) -> str:
    summary = build_profile_summary(profile or {})
    charts_block = "\n".join(f"- {t}" for t in chart_titles) or "(no charts were generated)"
    insights_block = "\n".join(f"- {s}" for s in insights[:6]) or "(none)"
    shape = json.dumps(NARRATIVE_SHAPE, indent=2)
    return f"""You are Universal Analyst writing the narrative for a professional PDF report.

Return ONLY valid JSON. No markdown fences, no prose outside the JSON.

## Dataset Profile
{summary}

## Generated Charts (in order)
{charts_block}

## Analyst Insights From This Session
{insights_block}

## Required JSON Shape
{shape}

## Rules
- Ground every statement in the profile above. Use real column names, counts, and values.
- Do not invent metrics or columns that are not in the profile.
- "chart_readings" must have exactly one entry per generated chart, in the same order. If there are no charts, use an empty list.
- Be specific and quantitative. No filler, no hedging, no restating the rules.
- Keep the executive_summary readable by a non-technical stakeholder.
"""


def _validate(raw: Any, chart_count: int) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError("Narrative response was not a JSON object.")
    readings = _as_str_list(raw.get("chart_readings"), max(chart_count, 0))
    return {
        "title": _as_str(raw.get("title")),
        "executive_summary": _as_str(raw.get("executive_summary")),
        "key_findings": _as_str_list(raw.get("key_findings"), 6),
        "data_quality_note": _as_str(raw.get("data_quality_note")),
        "chart_readings": readings,
        "dashboard_summary": _as_str(raw.get("dashboard_summary")),
        "anomalies": _as_str_list(raw.get("anomalies"), 4),
        "recommendations": _as_str_list(raw.get("recommendations"), 5),
    }


async def generate_report_narrative(
    profile: Optional[dict],
    eda: Optional[dict],
    charts: Optional[list[Any]],
    insights: Optional[list[str]] = None,
) -> Optional[dict[str, Any]]:
    """Ask the model for a structured report narrative.

    Returns the validated narrative dict, or None if the model is unavailable or
    returns unusable output. None means the PDF renders its deterministic
    sections without an LLM narrative — never a fabricated one.
    """
    if not profile:
        return None

    chart_titles = _chart_titles(charts or [])
    prompt = _build_prompt(profile, eda or {}, chart_titles, insights or [])
    client = get_ollama_client(settings.model_name)

    try:
        text = await client.generate_text(
            prompt,
            num_predict=1400,
            temperature=0.3,
            format=REPORT_NARRATIVE_SCHEMA,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("Report narrative generation failed: %s", exc)
        return None

    try:
        narrative = _validate(_extract_json(text), len(chart_titles))
    except (ValueError, json.JSONDecodeError) as exc:
        logger.warning("Report narrative was not usable JSON: %s", exc)
        return None

    # Require at least a summary or findings to be worth rendering.
    if not narrative["executive_summary"] and not narrative["key_findings"]:
        return None
    return narrative
