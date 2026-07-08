"""Sessions API: list, create, get, and delete conversations."""
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException

from app.core.session_manager import session_manager

router = APIRouter()


def _derive_title(session: Dict[str, Any], profile: Dict[str, Any]) -> str:
    """Title from file_name, else first user message, else default."""
    file_name = profile.get("file_name") if profile else None
    if file_name:
        return str(file_name)
    for msg in session.get("chat_history", []):
        if msg.get("role") == "user" and msg.get("content"):
            text = str(msg["content"]).strip()
            return text[:60] + ("..." if len(text) > 60 else "")
    return "New Analysis"


@router.get("/sessions")
def list_sessions() -> List[Dict[str, Any]]:
    """Return all sessions as objects with title + dataset metadata."""
    result: List[Dict[str, Any]] = []
    for session_id in session_manager.list_sessions():
        session = session_manager.get_session(session_id)
        if session is None:
            continue
        profile = session.get("profile") or {}
        result.append(
            {
                "id": session_id,
                "title": _derive_title(session, profile),
                "file_name": profile.get("file_name"),
                "row_count": profile.get("row_count"),
                "chart_count": len(session.get("charts") or []),
                "message_count": len(session.get("chat_history") or []),
            }
        )
    return result


@router.post("/sessions")
def create_session() -> Dict[str, str]:
    """Create a new empty session."""
    session_id = session_manager.create_session()
    return {"session_id": session_id}


@router.get("/sessions/{session_id}")
def get_session(session_id: str) -> Dict[str, Any]:
    """Get session metadata, chat history, and generated chart artifacts."""
    session = session_manager.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found.")
    return {
        "session_id": session_id,
        "has_data": session.get("df") is not None,
        "profile": session.get("profile"),
        "eda": session.get("eda"),
        "chat_history": session.get("chat_history", []),
        "charts": session.get("charts", []),
        "dashboard_layout": session.get("dashboard_layout"),
    }


@router.delete("/sessions/{session_id}")
def delete_session(session_id: str) -> Dict[str, str]:
    """Delete a session and its data (in-memory state + on-disk RAG collection)."""
    if not session_manager.delete_session(session_id):
        raise HTTPException(status_code=404, detail="Session not found.")
    return {"status": "deleted", "session_id": session_id}