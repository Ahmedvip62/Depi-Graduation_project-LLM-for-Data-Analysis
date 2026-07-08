import logging
from typing import List

logger = logging.getLogger(__name__)

_model = None


def _get_model():
    """Lazy-load the sentence-transformers model on first use."""
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer

        from app.config import settings

        model_name = settings.embedding_model
        logger.info("Loading sentence-transformers model (%s)...", model_name)
        _model = SentenceTransformer(model_name)
        logger.info("Model loaded successfully.")
    return _model


class Embedder:
    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        model = _get_model()
        embeddings = model.encode(texts, show_progress_bar=False)
        return [embedding.tolist() for embedding in embeddings]


def get_embedder() -> Embedder:
    """Factory function — avoids triggering model download at import time."""
    return Embedder()
