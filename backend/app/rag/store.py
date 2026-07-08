import logging
from typing import List

logger = logging.getLogger(__name__)

_client = None


def _get_chroma_client():
    """Lazy-load ChromaDB client on first use."""
    global _client
    if _client is None:
        import chromadb
        from app.config import settings
        logger.info("Initializing ChromaDB at %s", settings.chroma_persist_directory)
        _client = chromadb.PersistentClient(path=settings.chroma_persist_directory)
    return _client


class ChromaStore:
    def get_or_create_collection(self, session_id: str):
        client = _get_chroma_client()
        return client.get_or_create_collection(name=f"session_{session_id}")

    def add_chunks(
        self, session_id: str, chunks: List[str], embeddings: List[List[float]]
    ):
        if not chunks:
            logger.warning("No chunks to store for session %s", session_id)
            return
        collection = self.get_or_create_collection(session_id)
        ids = [f"chunk_{i}" for i in range(len(chunks))]
        collection.add(documents=chunks, embeddings=embeddings, ids=ids)
        logger.info(
            "Stored %d chunks for session %s", len(chunks), session_id
        )

    def delete_collection(self, session_id: str) -> None:
        """Delete a session's embedding collection from ChromaDB."""
        client = _get_chroma_client()
        collection_name = f"session_{session_id}"
        try:
            client.delete_collection(collection_name)
            logger.info("Deleted ChromaDB collection for session %s", session_id)
        except Exception:  # noqa: BLE001
            # Collection may not exist if no data was ever uploaded.
            logger.debug("No ChromaDB collection to delete for session %s", session_id)


def get_chroma_store() -> ChromaStore:
    """Factory function — avoids creating ChromaDB client at import time."""
    return ChromaStore()
