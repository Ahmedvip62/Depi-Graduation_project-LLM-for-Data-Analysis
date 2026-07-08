import uuid
import logging
import threading
from typing import Any, Dict, List, Optional

from app.rag.store import get_chroma_store

logger = logging.getLogger(__name__)


class SessionManager:
    def __init__(self):
        self._sessions: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    def create_session(self) -> str:
        session_id = str(uuid.uuid4())
        with self._lock:
            self._sessions[session_id] = {
                "df": None,
                "profile": None,
                "eda": None,
                "chat_history": [],
                "charts": [],
                "dashboard_layout": None,
            }
        logger.info("Created session %s", session_id)
        return session_id

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            return self._sessions.get(session_id)

    def update_session(self, session_id: str, key: str, value: Any) -> None:
        with self._lock:
            if session_id not in self._sessions:
                raise KeyError(f"Session {session_id} does not exist")
            self._sessions[session_id][key] = value

    def append_chat(self, session_id: str, role: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Append a message to the session chat history."""
        with self._lock:
            if session_id not in self._sessions:
                raise KeyError(f"Session {session_id} does not exist")
            entry: Dict[str, Any] = {"role": role, "content": content}
            if metadata:
                entry.update(metadata)
            self._sessions[session_id]["chat_history"].append(entry)

    def append_chart(self, session_id: str, chart: Dict[str, Any]) -> Dict[str, Any]:
        """Persist a generated chart artifact in the session."""
        with self._lock:
            if session_id not in self._sessions:
                raise KeyError(f"Session {session_id} does not exist")
            self._sessions[session_id].setdefault("charts", []).append(chart)
            return chart

    def list_sessions(self) -> List[str]:
        with self._lock:
            return list(self._sessions.keys())

    def delete_session(self, session_id: str) -> bool:
        with self._lock:
            removed = self._sessions.pop(session_id, None) is not None
        if removed:
            # Clean up the ChromaDB embedding collection outside the lock
            # (network I/O should not hold the session lock).
            try:
                get_chroma_store().delete_collection(session_id)
            except Exception:  # noqa: BLE001
                logger.warning(
                    "Failed to delete ChromaDB collection for session %s",
                    session_id,
                )
        return removed


session_manager = SessionManager()