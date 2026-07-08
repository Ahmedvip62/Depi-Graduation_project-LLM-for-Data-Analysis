from typing import List
from app.rag.store import get_chroma_store
from app.rag.embedder import get_embedder


class Retriever:
    @staticmethod
    def retrieve(session_id: str, query: str, top_k: int = 5) -> List[str]:
        store = get_chroma_store()
        emb = get_embedder()

        collection = store.get_or_create_collection(session_id)

        # Guard: if the collection is empty, return nothing
        if collection.count() == 0:
            return []

        query_embedding = emb.embed_texts([query])[0]
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=min(top_k, collection.count()),
        )
        if results["documents"] and results["documents"][0]:
            return results["documents"][0]
        return []
