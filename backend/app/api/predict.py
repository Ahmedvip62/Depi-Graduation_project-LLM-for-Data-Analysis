"""Prediction API endpoint — SSE stream of the full prediction pipeline."""

import json
import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.config import settings
from app.core.session_manager import session_manager
from app.llm.ollama_client import get_ollama_client
from app.skills.prediction import run_prediction_pipeline

logger = logging.getLogger(__name__)
router = APIRouter()


class PredictRequest(BaseModel):
    session_id: str


def _sse(event: str, payload: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


@router.post("/predict")
async def predict_endpoint(request: PredictRequest):
    session = session_manager.get_session(request.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found.")

    async def event_generator():
        try:
            client = get_ollama_client(settings.model_name)
            async for event in run_prediction_pipeline(session, client):
                event_type = event.pop("type", "prediction_status")
                yield _sse(event_type, event)

            yield _sse("prediction_done", {"status": "complete"})

        except Exception as exc:
            logger.exception("Prediction stream failed")
            yield _sse("prediction_error", {"message": str(exc)})
            yield _sse("prediction_done", {"status": "error"})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
