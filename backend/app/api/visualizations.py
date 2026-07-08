import logging
from typing import Any, Dict

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.session_manager import session_manager
from app.visualization.chart_factory import ChartFactory

logger = logging.getLogger(__name__)
router = APIRouter()


class VizRequest(BaseModel):
    session_id: str
    chart_spec: Dict[str, Any]


@router.post("/visualize")
def generate_visualization(request: VizRequest):
    session = session_manager.get_session(request.session_id)
    if session is None or session["df"] is None:
        raise HTTPException(
            status_code=404, detail="Session not found or no data uploaded."
        )

    df = session["df"]

    try:
        chart_json = ChartFactory.generate_chart(df, request.chart_spec)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.exception("Chart generation failed")
        raise HTTPException(status_code=500, detail=f"Chart generation error: {exc}")

    return {"chart": chart_json}
