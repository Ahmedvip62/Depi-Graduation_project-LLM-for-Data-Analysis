import base64
import binascii
import json
import logging
import re
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.config import settings
from app.core.session_manager import session_manager
from app.llm.ollama_client import get_ollama_client
from app.llm.prompt_templates import (
    SKILL_ANALYSIS_WITH_VISUAL,
    SKILL_GENERAL_QA,
    SKILL_LABELS,
    SKILL_REASONS,
    SKILL_REPORT,
    SKILL_VISUALIZATION,
    SKILL_PREDICTION,
    build_chart_plan_context,
    build_thinking_prompt,
    should_use_thinking_mode,
)
from app.rag.context_builder import ContextBuilder
from app.visualization.chart_factory import ChartFactory
from app.visualization.chart_types import query_implies_visual

logger = logging.getLogger(__name__)
router = APIRouter()

SKILLS_DIR = Path(__file__).parent.parent / "skills_registry"
MAX_CHARTS = 4
ALLOWED_IMAGE_MIME_TYPES = {"image/png", "image/jpeg", "image/webp"}
SUPPORTED_CHART_TYPES = {
    "bar", "line", "scatter", "pie", "histogram", "heatmap", "box",
    "violin", "strip", "funnel", "funnel_area", "treemap", "sunburst",
    "icicle", "waterfall", "area", "radar", "density_heatmap", "density_contour",
    "scatter_geo", "choropleth", "scatter_matrix", "parallel_coordinates",
    "parallel_categories", "scatter_3d", "gauge", "timeline"
}
SUPPORTED_AGGREGATIONS = {"sum", "mean", "median", "min", "max", "count"}

def get_chart_plan_schema(columns: list[str]) -> dict[str, Any]:
    valid_cols = list(columns)
    col_type: dict[str, Any] = {"type": ["string", "null"]}
    if valid_cols:
        col_type["enum"] = [*valid_cols, None]

    path_type: dict[str, Any] = {
        "type": "array",
        "items": {"type": "string"}
    }
    if valid_cols:
        path_type["items"]["enum"] = valid_cols

    filter_item: dict[str, Any] = {
        "type": "object",
        "properties": {
            "column": {"type": "string"},
            "operator": {"type": "string", "enum": ["eq", "ne", "gt", "ge", "lt", "le", "contains"]},
            "value": {"type": ["string", "number", "boolean"]},
        },
        "required": ["column", "operator", "value"],
    }
    if valid_cols:
        filter_item["properties"]["column"]["enum"] = valid_cols

    layout_item: dict[str, Any] = {
        "type": "object",
        "properties": {
            "chart_index": {"type": "integer"},
            "col_span": {"type": "integer", "minimum": 1, "maximum": 4},
            "row_span": {"type": "integer", "minimum": 1, "maximum": 3},
            "visual_priority": {"type": "string", "enum": ["kpi", "standard", "full-width"]}
        },
        "required": ["chart_index"]
    }

    return {
        "type": "object",
        "properties": {
            "charts": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "type": {"type": "string", "enum": sorted(SUPPORTED_CHART_TYPES)},
                        "x": col_type,
                        "y": col_type,
                        "z": col_type,
                        "size": col_type,
                        "path": path_type,
                        "barmode": {"type": ["string", "null"], "enum": ["group", "stack", "overlay", "relative", None]},
                        "color": col_type,
                        "aggregate": {"type": ["string", "null"], "enum": [*sorted(SUPPORTED_AGGREGATIONS), None]},
                        "top_n": {"type": ["integer", "null"]},
                        "sort": {"type": ["string", "null"], "enum": ["asc", "desc", None]},
                        "title": {"type": "string"},
                        "description": {"type": "string"},
                        "filters": {
                            "type": "array",
                            "items": filter_item,
                        },
                    },
                    "required": ["type", "title"],
                },
            },
            "layout": {
                "type": "object",
                "properties": {
                    "grid_cols": {"type": "integer", "enum": [2, 3, 4], "default": 3},
                    "positions": {
                        "type": "array",
                        "items": layout_item
                    }
                }
            }
        },
        "required": ["charts"],
    }


CHART_PLAN_SCHEMA = get_chart_plan_schema([])

SKILL_FILES = {
    SKILL_VISUALIZATION: ["visualization.md"],
    SKILL_ANALYSIS_WITH_VISUAL: ["analysis.md", "visualization.md"],
    SKILL_GENERAL_QA: ["general_qa.md"],
    SKILL_REPORT: ["report.md"],
    SKILL_PREDICTION: ["prediction.md"],
}

DASHBOARD_TERMS = (
    "dashboard",
    "visual dashboard",
    "visual overview",
    "eda",
    "exploratory",
    "generate visuals",
    "generate charts",
)

REPORT_TERMS = (
    "pdf report",
    "download report",
    "export report",
    "generate report",
    "create report",
    "make report",
    "report pdf",
)


class ChatAttachment(BaseModel):
    type: str = "image"
    mime_type: str
    data: str
    name: str | None = None
    size: int | None = None


class ChatRequest(BaseModel):
    session_id: str
    message: str
    enable_thinking: bool = False
    attachments: list[ChatAttachment] = Field(default_factory=list)


def _sse(event: str, payload: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _is_dashboard_request(message: str) -> bool:
    text = message.lower()
    # Broaden detection for plural terms, dashboard references, and explicit request for multiple visuals.
    multi_indicators = (
        "dashboard", "overview", "eda", "charts", "visuals", "plots", "graphs",
        "multiple", "more than one", "several", "different aspects"
    )
    if any(term in text for term in multi_indicators):
        return True
    return ("generate" in text or "show" in text or "make" in text or "create" in text) and any(
        word in text for word in ("chart", "plot", "visual", "graph", "map", "maps")
    )


def _is_report_request(message: str) -> bool:
    text = message.lower()
    return any(term in text for term in REPORT_TERMS) or (
        "report" in text and any(word in text for word in ("pdf", "download", "export", "generate", "create"))
    )


def _is_prediction_request(message: str) -> bool:
    text = message.lower()
    prediction_indicators = (
        "predict", "prediction", "forecast", "regression", "classification",
        "model", "train", "machine learning", "sklearn", "rmse", "r2",
        "correlation strength", "predictive"
    )
    return any(term in text for term in prediction_indicators)


def _select_skill(message: str) -> str:
    if _is_report_request(message):
        return SKILL_REPORT
    if _is_prediction_request(message):
        return SKILL_PREDICTION
    wants_dashboard = _is_dashboard_request(message)
    wants_visual = query_implies_visual(message) or wants_dashboard
    is_complex = should_use_thinking_mode(message)
    if wants_dashboard:
        return SKILL_ANALYSIS_WITH_VISUAL
    if wants_visual and is_complex:
        return SKILL_ANALYSIS_WITH_VISUAL
    if wants_visual:
        return SKILL_VISUALIZATION
    return SKILL_GENERAL_QA



def _load_skill_text(skill_name: str) -> str:
    parts: list[str] = []
    for filename in SKILL_FILES.get(skill_name, ["general_qa.md"]):
        path = SKILLS_DIR / filename
        try:
            if path.exists():
                parts.append(path.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            logger.warning("Could not load skill file %s: %s", filename, exc)
    return "\n\n---\n\n".join(parts)


def _strip_data_url(data: str) -> str:
    stripped = data.strip()
    if stripped.startswith("data:") and "," in stripped:
        return stripped.split(",", 1)[1]
    return stripped


def _validate_image_attachments(attachments: list[ChatAttachment]) -> list[dict[str, Any]]:
    if not attachments:
        return []
    if not settings.image_chat_enabled:
        raise HTTPException(status_code=400, detail="Image chat is disabled.")
    if len(attachments) > settings.max_chat_images:
        raise HTTPException(
            status_code=400,
            detail=f"Attach at most {settings.max_chat_images} images per turn.",
        )

    max_bytes = settings.max_chat_image_mb * 1024 * 1024
    validated: list[dict[str, Any]] = []
    for idx, attachment in enumerate(attachments, start=1):
        if attachment.type != "image":
            raise HTTPException(status_code=400, detail="Only image attachments are supported.")
        if attachment.mime_type not in ALLOWED_IMAGE_MIME_TYPES:
            allowed = ", ".join(sorted(ALLOWED_IMAGE_MIME_TYPES))
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported image type '{attachment.mime_type}'. Allowed: {allowed}.",
            )

        clean_data = "".join(_strip_data_url(attachment.data).split())
        try:
            raw = base64.b64decode(clean_data, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise HTTPException(status_code=400, detail="Invalid base64 image data.") from exc

        if len(raw) > max_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"Image {idx} is too large. Maximum is {settings.max_chat_image_mb}MB.",
            )

        validated.append(
            {
                "type": "image",
                "mime_type": attachment.mime_type,
                "data": clean_data,
                "name": attachment.name or f"image-{idx}",
                "size": len(raw),
            }
        )
    return validated


def _attachment_prompt(attachments: list[dict[str, Any]]) -> str:
    if not attachments:
        return ""
    lines = [
        "## Attached Images",
        "The user attached image(s) to this turn. Use the visual content together with the dataset profile and retrieved context. If the image conflicts with the dataset, explain the mismatch.",
    ]
    for idx, image in enumerate(attachments, start=1):
        lines.append(f"- Image {idx}: {image['name']} ({image['mime_type']}, {image['size']:,} bytes)")
    return "\n".join(lines)


def _persisted_user_message(message: str, attachments: list[dict[str, Any]]) -> str:
    if not attachments:
        return message
    names = ", ".join(str(a["name"]) for a in attachments)
    return f"{message}\n\n[Attached images: {names}]"


def _usage_event(phase: str, usage: dict[str, Any]) -> dict[str, Any]:
    return {"phase": phase, "source": "ollama", **usage}


def _extract_chart_title(fig_spec: dict, index: int) -> str:
    try:
        title = fig_spec.get("layout", {}).get("title", {})
        if isinstance(title, dict):
            text = title.get("text")
            if text:
                return str(text)
        if isinstance(title, str) and title:
            return title
    except Exception:  # noqa: BLE001
        pass
    return f"Figure {index + 1}"


def _store_chart(session: dict[str, Any], chart: dict[str, Any]) -> dict[str, Any]:
    charts = session.setdefault("charts", [])
    stored = {
        "id": chart.get("id") or f"chart-{uuid.uuid4().hex[:12]}",
        "title": chart.get("title"),
        "description": chart.get("description"),
        "chart_spec": chart.get("chart_spec"),
        "source": "chat",
    }
    charts.append(stored)
    return stored


def _skill_prompt(base_prompt: str, user_message: str, skill_name: str, skill_text: str) -> str:
    if skill_name == SKILL_VISUALIZATION:
        instruction = (
            "You are in visualization mode. Give a short, useful answer that explains what visual will be generated "
            "and why it fits the request. Do not include Python code or JSON in this user-facing answer; "
            "the backend will request a separate strict visual plan after this response."
        )
    elif _is_dashboard_request(user_message):
        instruction = (
            "The user asked for a dashboard/EDA view. Give a short executive summary of the dataset profile and "
            "the most useful angles to visualize. Do not include Python code or JSON in this user-facing answer; "
            "the backend will request a separate strict visual plan after this response."
        )
    else:
        instruction = (
            "If a visual materially helps, explain what it should show in plain language. Do not include Python code "
            "or JSON in this user-facing answer; the backend will request a separate strict visual plan when needed."
        )

    # Force the instructions to the absolute bottom and reinforce the "NO CODE BLOCK" rule.
    return f"{base_prompt}\n\n## AI SKILL GUIDELINES\n{skill_text}\n\n## TURN INSTRUCTION\n{instruction}\nCRITICAL: You MUST NOT output any JSON, code blocks, or python code. Output only clean prose. Do not start any markdown code blocks."




def _visual_plan_prompt(
    user_message: str,
    plan_context: str,
    chart_errors: list[str] | None = None,
    is_dashboard: bool = False,
    existing_charts: list[dict[str, Any]] | None = None,
    chat_history: list[dict[str, Any]] | None = None,
) -> str:
    error_text = "\n".join(f"- {err}" for err in (chart_errors or [])[:8])
    repair_note = f"\n## Fix These Validation Errors\n{error_text}\n" if error_text else ""

    supported_types_str = ", ".join(sorted(SUPPORTED_CHART_TYPES))

    chat_context = ""
    if chat_history:
        context_turns = []
        # Grab last 4 messages (excluding system messages)
        for msg in chat_history[-4:]:
            role = msg.get("role")
            content = msg.get("content", "")
            if not content or role == "system":
                continue
            # Strip large JSON code blocks to prevent pollution
            clean_content = re.sub(r"```(?:json)?\s*[\s\S]*?```", "", content).strip()
            clean_content = re.sub(r"```[\s\S]*?```", "", clean_content).strip()
            if clean_content:
                context_turns.append(f"{role.upper()}: {clean_content[:300]}")
        if context_turns:
            chat_context = "\n## Recent Conversation History (for context/pronouns)\n" + "\n".join(context_turns) + "\n"

    if is_dashboard:
        count_instruction = (
            f"This is a DASHBOARD request. You MUST produce 3 to 4 different charts that "
            f"together give a comprehensive overview of the dataset. Use a MIX of chart types "
            f"from the supported list: {supported_types_str}. "
            f"Do NOT repeat the same chart type. Each chart should explore a DIFFERENT aspect of the data "
            f"(distribution, comparison, composition, correlation, trends)."
        )
    else:
        count_instruction = (
            f"Produce 1 focused chart that directly answers the user's request. "
            f"Choose the most appropriate chart type from the supported list: {supported_types_str}."
        )

    # Tell the model what charts already exist so it doesn't repeat the same KPI/type.
    already_note = ""
    if existing_charts:
        items = []
        for ch in existing_charts[-8:]:  # last 8 charts max
            title = ch.get("title") or "Untitled"
            spec = ch.get("chart_spec") or {}
            ctype = str(spec.get("type") or spec.get("chart_spec", {}).get("type") or "unknown").lower()
            items.append(f"  - {title} (type: {ctype})")
        already_note = (
            "\n## Already Generated in Session (do NOT repeat these chart types/metrics)\n"
            + "\n".join(items)
            + "\nSelect DIFFERENT columns, insights, and chart types than the ones listed above to provide variety.\n"
        )

    return f"""You plan data visualizations. Output JSON only: an object with a "charts" array and optionally a "layout" configuration for dashboard layouts.

## User Request
{user_message}
{chat_context}

## Chart Count
{count_instruction}
{already_note}
## Available Columns
{plan_context}

## Rules
- Use only the EXACT column names listed above. Never invent a column.
- **Supported Chart Types**: {supported_types_str}
- **Chart Selection Guidelines**:
  - **violin**: Use `violin` instead of `box` when looking for kernel distribution density of a numeric column across categories.
  - **funnel** / **funnel_area**: Use if columns represent sequential progression stages (e.g. Sales Funnel, conversions).
  - **treemap** / **sunburst** / **icicle**: Use for nested group compositions. Specify category columns in the `"path"` array.
  - **waterfall**: Use for cumulative sequential gains and losses arriving at a net total.
  - **radar**: Use for multi-attribute comparative polar grids (like ratings or multi-metric scores).
  - **density_heatmap** / **density_contour**: Use for 2D distribution density of two numeric columns when there are many overlapping points.
  - **parallel_coordinates** / **parallel_categories**: Use to plot multi-dimensional trend paths across 4+ columns.
  - **scatter_3d**: Use for relationships between three numeric columns simultaneously.
  - **scatter_matrix**: Use when exploring pairwise correlation grids across all numeric columns.
  - **area**: Use for stacked numeric accumulations over time.
  - **strip**: Use to show individual data points along category axes.
  - **timeline**: Use for scheduling, Gantt views, or durations (must specify start date on `x` and end date on `y`).
  - **gauge**: Use for single-value metrics or KPI progress.
- **Maps**: If the request mentions country, city, coordinates, location, or global overview, you MUST use `choropleth` (fill countries) or `scatter_geo` (points on map). Set locations/region columns on `x`.
- **Hierarchies**: Use `treemap` or `sunburst` for nested groups. Specify category columns in the `"path"` array.
- **Gantt/Timelines**: Use `timeline` for date durations. Set start date on `x` and end date on `y`.
- **KPI Gauges**: Use `gauge` for single-value metrics or KPIs.
- **Bar Mode**: Specify `"barmode": "group"` or `"barmode": "stack"` for segmented comparisons.
- **Dashboard Layout**: If this is a dashboard request (multiple charts), add a `"layout"` object at the top level with `"grid_cols"` (integer) and `"positions"` array mapping chart indices to `"col_span"` (1-4) and `"row_span"` (1-3). Place single KPIs / Gauges in small spans, and wide trendlines / Maps in full-width spans.
- **Filtering**: Add filters if the request targets a subset of the dataset.
{repair_note}"""


def _extract_json_payload(text: str) -> Any:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        first = cleaned.find("{")
        last = cleaned.rfind("}")
        if first == -1 or last <= first:
            raise ValueError("The model did not return a JSON object.")
        try:
            return json.loads(cleaned[first : last + 1])
        except json.JSONDecodeError as exc:
            raise ValueError(f"The model returned invalid visual-plan JSON: {exc}") from exc


def _empty_to_none(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, str) and value.strip().lower() in {"", "none", "null", "n/a", "-"}:
        return None
    return value


def _normalize_chart_spec(raw: Any, index: int) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError(f"Chart {index + 1} is not an object.")

    chart_type = str(raw.get("type") or "").lower().strip()
    if chart_type not in SUPPORTED_CHART_TYPES:
        raise ValueError(
            f"Chart {index + 1} has unsupported type '{chart_type}'. "
            f"Supported types: {', '.join(sorted(SUPPORTED_CHART_TYPES))}."
        )

    aggregate = _empty_to_none(raw.get("aggregate") or raw.get("aggregation"))
    if isinstance(aggregate, str):
        aggregate = aggregate.lower().strip()
    if aggregate and aggregate not in SUPPORTED_AGGREGATIONS:
        raise ValueError(
            f"Chart {index + 1} has unsupported aggregate '{aggregate}'. "
            f"Supported aggregates: {', '.join(sorted(SUPPORTED_AGGREGATIONS))}."
        )

    top_n = raw.get("top_n")
    if top_n is not None:
        try:
            top_n = max(1, min(int(top_n), 50))
        except (TypeError, ValueError):
            top_n = None

    sort = str(raw.get("sort") or "desc").lower().strip()
    if sort not in {"asc", "desc"}:
        sort = "desc"

    # Safely parse filters
    raw_filters = raw.get("filters") or []
    valid_filters = []
    if isinstance(raw_filters, list):
        for f in raw_filters:
            if isinstance(f, dict) and f.get("column") and f.get("operator") and f.get("value") is not None:
                valid_filters.append({
                    "column": str(f["column"]),
                    "operator": str(f["operator"]).lower().strip(),
                    "value": f["value"]
                })

    raw_path = raw.get("path")
    normalized_path = None
    if isinstance(raw_path, str):
        normalized_path = [raw_path]
    elif isinstance(raw_path, list):
        normalized_path = [str(p) for p in raw_path]

    return {
        "type": chart_type,
        "x": _empty_to_none(raw.get("x")),
        "y": _empty_to_none(raw.get("y")),
        "z": _empty_to_none(raw.get("z")),
        "size": _empty_to_none(raw.get("size")),
        "path": normalized_path,
        "barmode": _empty_to_none(raw.get("barmode")),
        "color": _empty_to_none(raw.get("color")),
        "aggregate": aggregate,
        "top_n": top_n,
        "sort": sort,
        "title": raw.get("title") or f"Figure {index + 1}",
        "description": raw.get("description") or raw.get("rationale") or "",
        "filters": valid_filters,
    }


def _chart_payloads_from_plan_text(
    session: dict[str, Any],
    plan_text: str,
) -> tuple[list[dict[str, Any]], dict[str, Any] | None, list[str]]:
    df = session.get("df")
    if df is None:
        return [], None, ["No dataset is loaded; charts cannot be generated."]

    try:
        payload = _extract_json_payload(plan_text)
    except ValueError as exc:
        return [], None, [str(exc)]

    layout = None
    if isinstance(payload, dict):
        raw_charts = payload.get("charts")
        layout = payload.get("layout")
    else:
        raw_charts = payload

    if not isinstance(raw_charts, list) or not raw_charts:
        return [], None, ["The model visual plan did not include any charts."]

    charts: list[dict[str, Any]] = []
    errors: list[str] = []
    for index, raw_spec in enumerate(raw_charts[:MAX_CHARTS]):
        try:
            spec = _normalize_chart_spec(raw_spec, index)
            fig_json = ChartFactory.generate_chart(df, spec)
            fig_spec = json.loads(fig_json)
        except Exception as exc:  # noqa: BLE001
            logger.error("Visual-plan chart %s failed: %s", index + 1, exc)
            errors.append(f"Chart {index + 1} failed: {exc}")
            continue

        charts.append(
            {
                "chart_spec": fig_spec,
                "title": spec.get("title") or _extract_chart_title(fig_spec, len(charts)),
                "description": spec.get("description") or "",
                "index": len(charts),
            }
        )

    return charts, layout, errors


@router.post("/chat")
async def chat_endpoint(request: ChatRequest):
    session = session_manager.get_session(request.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found.")

    image_attachments = _validate_image_attachments(request.attachments)
    user_message = request.message.strip() or "Please analyze the attached image."
    session_manager.append_chat(
        request.session_id,
        "user",
        _persisted_user_message(user_message, image_attachments),
    )

    async def event_generator():
        answer_text = ""
        stored_chart_refs: list[dict[str, Any]] = []
        model_error: str | None = None
        try:
            skill_name = _select_skill(user_message)
            wants_charts = skill_name in (SKILL_VISUALIZATION, SKILL_ANALYSIS_WITH_VISUAL, SKILL_PREDICTION)
            wants_dashboard = _is_dashboard_request(user_message)

            yield _sse(
                "skill",
                {
                    "skill": skill_name,
                    "label": SKILL_LABELS.get(skill_name, "Data Q&A"),
                    "reason": SKILL_REASONS.get(skill_name, ""),
                },
            )
            if wants_dashboard:
                yield _sse("command", {"command": "show_dashboard", "session_id": request.session_id})

            if skill_name == SKILL_REPORT:
                answer_text = (
                    "Preparing a PDF report from this session's dataset profile, "
                    "model-generated visuals, and recent analysis transcript."
                )
                session_manager.append_chat(request.session_id, "assistant", answer_text)
                yield _sse("action", {"action": "report", "label": "Preparing PDF report"})
                yield _sse("token", {"token": answer_text, "agent_name": "PDF Report"})
                yield _sse("command", {"command": "download_report", "session_id": request.session_id})
                yield _sse("done", {"status": "complete"})
                return

            # Pure chart requests skip the prose answer and its RAG context build;
            # the schema-forced plan call only needs the column manifest.
            viz_only = skill_name == SKILL_VISUALIZATION

            main_client = get_ollama_client(settings.model_name)
            base_context = ""
            final_prompt = ""

            if not viz_only:
                yield _sse("action", {"action": "context", "label": "Building dataset context"})
                context_query = user_message
                if image_attachments:
                    context_query = f"{user_message}\n\nUser attached {len(image_attachments)} image(s)."
                base_context = ContextBuilder.build_context(request.session_id, context_query)

                skill_text = _load_skill_text(skill_name)
                final_prompt = base_context
                if skill_text:
                    final_prompt = _skill_prompt(base_context, user_message, skill_name, skill_text)
                attachment_text = _attachment_prompt(image_attachments)
                if attachment_text:
                    final_prompt = f"{final_prompt}\n\n{attachment_text}"

            if request.enable_thinking and not viz_only:
                yield _sse("action", {"action": "thinking", "label": "Planning analysis"})
                thinking_prompt = build_thinking_prompt(user_message, base_context)
                async for event in main_client.generate_stream_events(
                    thinking_prompt,
                    num_predict=180,
                    temperature=0.25,
                ):
                    if event.get("type") == "token":
                        yield _sse("thinking", {"token": event.get("token", "")})
                    elif event.get("type") == "usage":
                        yield _sse("usage", _usage_event("thinking", event["usage"]))
                    elif event.get("type") == "error":
                        yield _sse("error", {"message": f"Thinking pass failed: {event.get('message')}"})
                        break

            # Pure chart requests skipped the prose answer above; analysis and Q&A
            # requests stream their answer here.
            answer_parts: list[str] = []
            images = [img["data"] for img in image_attachments] or None

            if viz_only:
                yield _sse("action", {"action": "visualize", "label": "Planning charts"})
            else:
                if wants_charts:
                    yield _sse("action", {"action": "visualize", "label": "Analyzing with visuals"})
                else:
                    yield _sse("action", {"action": "answer", "label": "Streaming answer"})

                async for event in main_client.generate_stream_events(
                    final_prompt,
                    images=images,
                    num_predict=2200 if wants_charts else 900,
                    temperature=0.2,
                ):
                    if event.get("type") == "token":
                        tok = str(event.get("token", ""))
                        answer_parts.append(tok)
                        yield _sse(
                            "token",
                            {"token": tok, "agent_name": SKILL_LABELS.get(skill_name, "Analyst")},
                        )
                    elif event.get("type") == "usage":
                        yield _sse("usage", _usage_event("answer", event["usage"]))
                    elif event.get("type") == "error":
                        model_error = str(event.get("message") or "Model generation failed.")
                        yield _sse("error", {"message": model_error})
                        break

            answer_text = "".join(answer_parts).strip()
            if model_error:
                if answer_text:
                    session_manager.append_chat(request.session_id, "assistant", answer_text)
                yield _sse("done", {"status": "error"})
                return

            if not answer_text and not wants_charts:
                yield _sse(
                    "error",
                    {
                        "message": (
                            "The model returned no output. Check the Ollama model name, model availability, "
                            "and Lightning runtime logs."
                        )
                    },
                )
                yield _sse("done", {"status": "error"})
                return

            if wants_charts:
                charts: list[dict[str, Any]] = []
                chart_errors: list[str] = []
                profile = session.get("profile") or {}
                plan_context = build_chart_plan_context(profile)
                session_charts = session.get("charts") or []

                columns = list(profile.get("columns", {}).keys())
                dynamic_schema = get_chart_plan_schema(columns) if columns else CHART_PLAN_SCHEMA

                yield _sse("action", {"action": "visual_plan", "label": "Planning validated charts"})
                plan_text = ""
                repair_text = ""
                plan_parts: list[str] = []
                plan_prompt = _visual_plan_prompt(
                    user_message, plan_context,
                    is_dashboard=wants_dashboard,
                    existing_charts=session_charts,
                    chat_history=session.get("chat_history", []),
                )
                async for event in main_client.generate_stream_events(
                    plan_prompt,
                    num_predict=2400 if wants_dashboard else 1400,
                    temperature=0.4,
                    format=dynamic_schema,
                ):
                    if event.get("type") == "token":
                        plan_parts.append(str(event.get("token", "")))
                    elif event.get("type") == "usage":
                        yield _sse("usage", _usage_event("visual_plan", event["usage"]))
                    elif event.get("type") == "error":
                        chart_errors.append(str(event.get("message") or "Visual plan generation failed."))
                        break

                plan_text = "".join(plan_parts).strip()
                layout = None
                if plan_text:
                    charts, layout, plan_errors = _chart_payloads_from_plan_text(session, plan_text)
                    chart_errors.extend(plan_errors)

                if not charts:
                    yield _sse("action", {"action": "repair", "label": "Repairing visual plan"})
                    repair_parts: list[str] = []
                    repair_prompt = _visual_plan_prompt(
                        user_message, plan_context, chart_errors,
                        is_dashboard=wants_dashboard,
                        existing_charts=session_charts,
                        chat_history=session.get("chat_history", []),
                    )
                    async for event in main_client.generate_stream_events(
                        repair_prompt,
                        num_predict=1400,
                        temperature=0.02,
                        format=dynamic_schema,
                    ):
                        if event.get("type") == "token":
                            repair_parts.append(str(event.get("token", "")))
                        elif event.get("type") == "usage":
                            yield _sse("usage", _usage_event("visual_repair", event["usage"]))
                        elif event.get("type") == "error":
                            chart_errors.append(str(event.get("message") or "Visual plan repair failed."))
                            break

                    repair_text = "".join(repair_parts).strip()
                    if repair_text:
                        repair_charts, repair_layout, repair_errors = _chart_payloads_from_plan_text(session, repair_text)
                        charts = repair_charts
                        if repair_layout:
                            layout = repair_layout
                        chart_errors.extend(repair_errors)

                if layout:
                    session_manager.update_session(request.session_id, "dashboard_layout", layout)
                    yield _sse("dashboard_layout", {"layout": layout, "session_id": request.session_id})

                if charts and not answer_text:
                    answer_text = "Generated dynamic visuals from a validated model chart plan."
                    yield _sse("token", {"token": answer_text, "agent_name": "Visualization"})

                for chart in charts:
                    stored = _store_chart(session, chart)
                    stored_chart_refs.append(stored)
                    yield _sse("chart", {**chart, "id": stored["id"], "source": stored["source"], "session_id": request.session_id})

                if not charts:
                    if not plan_text and not repair_text:
                        chart_errors.append(
                            "The model returned no chart plan (check the model name and "
                            "that the Ollama build supports structured output)."
                        )
                    if answer_text:
                        # A real analysis answer already streamed; the missing chart is
                        # a soft failure, not a failed turn. Surface why, then finish ok.
                        detail = chart_errors[0] if chart_errors else "No chart could be generated for this request."
                        yield _sse(
                            "error",
                            {"message": f"Charts unavailable: {detail} The written analysis above still applies."},
                        )
                        session_manager.append_chat(request.session_id, "assistant", answer_text)
                        yield _sse("done", {"status": "complete"})
                        return
                    for message in chart_errors:
                        yield _sse("error", {"message": message})
                    yield _sse(
                        "error",
                        {
                            "message": (
                                "The model did not produce a valid chart plan after repair. "
                                "No static dashboard charts were substituted."
                            )
                        },
                    )
                    yield _sse("done", {"status": "error"})
                    return

            session_manager.append_chat(
                request.session_id,
                "assistant",
                answer_text,
                {"charts": stored_chart_refs} if stored_chart_refs else None,
            )
            yield _sse("done", {"status": "complete"})

        except Exception as exc:  # noqa: BLE001
            logger.exception("Chat stream failed")
            yield _sse("error", {"message": str(exc)})
            yield _sse("done", {"status": "error"})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
