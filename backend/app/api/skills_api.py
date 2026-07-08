import logging
import os
import tempfile
import uuid
from typing import Any, List, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from starlette.background import BackgroundTask

from app.core.session_manager import session_manager
from app.skills.report import ReportSkill
from app.skills.report_narrative import generate_report_narrative

logger = logging.getLogger(__name__)
router = APIRouter()

TEMP_REPORT_DIR = os.getenv(
    "UA_TEMP_REPORT_DIR",
    os.path.join(tempfile.gettempdir(), "universal_analyst_reports"),
)

SKILL_MANIFEST = [
    {
        "id": "general_qa",
        "label": "Data Q&A",
        "kind": "llm_prompt_skill",
        "description": "Answers grounded questions from the data profile and retrieved context.",
        "inputs": ["session_id", "message", "optional_images"],
        "outputs": ["streamed_markdown", "usage"],
    },
    {
        "id": "analysis_with_visual",
        "label": "Deep Analysis",
        "kind": "llm_prompt_skill",
        "description": "Performs deeper reasoning and can trigger validated model-planned visuals.",
        "inputs": ["session_id", "message", "optional_images"],
        "outputs": ["streamed_markdown", "plotly_charts", "usage"],
    },
    {
        "id": "visualization",
        "label": "Visualization",
        "kind": "llm_visual_plan_skill",
        "description": "Generates strict model chart plans that are validated and rendered as Plotly artifacts.",
        "inputs": ["session_id", "message"],
        "outputs": ["plotly_charts", "chart_errors", "usage"],
    },
    {
        "id": "report",
        "label": "PDF Report",
        "kind": "llm_narrative_export_skill",
        "description": "The model writes a grounded narrative (executive summary, key findings, per-chart readings, recommendations); ReportLab renders it with the dataset profile, data-quality signals, and generated Plotly charts into a professional PDF.",
        "inputs": ["session_id", "profile", "stored_plotly_charts", "chat_history"],
        "outputs": ["application/pdf", "llm_narrative", "professional_report"],
    },
]


class ReportRequest(BaseModel):
    charts: Optional[List[Any]] = None


@router.get("")
def list_skills():
    """Return the active, extensible skill manifest used by agents and UI."""
    return {"skills": SKILL_MANIFEST}


def _cleanup_file(path: str) -> None:
    try:
        if os.path.exists(path):
            os.remove(path)
    except OSError as exc:
        logger.warning("Failed to remove temp report %s: %s", path, exc)


@router.post("/report")
async def export_report(session_id: str, body: Optional[ReportRequest] = None):
    """Generate and return a PDF report based on the session analytics.

    The model writes a structured narrative (executive summary, findings,
    per-chart readings, recommendations); ReportLab renders it alongside the
    real profile tables and Plotly charts. If the model is unavailable, the
    deterministic sections render on their own.
    """
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")

    charts = body.charts if body and body.charts else None
    if not charts:
        charts = session.get("charts") or []

    profile = session.get("profile")
    eda = session.get("eda")
    chat_history = session.get("chat_history", [])

    insights = [
        m.get("content", "")
        for m in chat_history
        if m.get("role") == "assistant" and m.get("content")
    ][-6:]
    narrative = await generate_report_narrative(profile, eda, charts, insights)

    pdf_path: str | None = None
    try:
        os.makedirs(TEMP_REPORT_DIR, exist_ok=True)
        pdf_path = os.path.join(
            TEMP_REPORT_DIR, f"report_{uuid.uuid4().hex[:8]}.pdf"
        )

        ReportSkill.generate_pdf(
            report_path=pdf_path,
            profile=profile,
            eda=eda,
            chat_history=chat_history,
            charts=charts,
            narrative=narrative,
            df=session.get("df"),
        )

        return FileResponse(
            path=pdf_path,
            filename=f"Universal_Analyst_Report_{session_id[:8]}.pdf",
            media_type="application/pdf",
            background=BackgroundTask(_cleanup_file, pdf_path),
        )
    except Exception as e:  # noqa: BLE001
        if pdf_path:
            _cleanup_file(pdf_path)
        logger.exception("Report generation failed")
        raise HTTPException(status_code=500, detail=str(e))
