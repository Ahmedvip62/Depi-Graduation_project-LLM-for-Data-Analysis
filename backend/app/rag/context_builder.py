"""Context builder: assembles the final prompt with profile, retrieved chunks, and token budget."""
import logging

from app.core.session_manager import session_manager
from app.llm.prompt_templates import build_data_qa_prompt, build_profile_summary
from app.llm.token_counter import count_tokens
from app.rag.retriever import Retriever

logger = logging.getLogger(__name__)

MAX_CONTEXT_TOKENS = 6000  # Leave room for system prompt + response


class ContextBuilder:
    @staticmethod
    def build_context(session_id: str, query: str) -> str:
        """Build the full prompt: system + profile + chunks + query, respecting token budget."""

        session = session_manager.get_session(session_id)
        profile = session.get("profile", {}) if session else {}

        chunks = Retriever.retrieve(session_id, query)

        profile_text = build_profile_summary(profile)
        budget = MAX_CONTEXT_TOKENS - count_tokens(profile_text) - count_tokens(query) - 200

        trimmed_chunks = []
        used_tokens = 0
        for chunk in chunks:
            chunk_tokens = count_tokens(chunk)
            if used_tokens + chunk_tokens > budget:
                logger.info("Token budget reached, stopping at %d chunks", len(trimmed_chunks))
                break
            trimmed_chunks.append(chunk)
            used_tokens += chunk_tokens

        context_str = "\n---\n".join(trimmed_chunks)
        return build_data_qa_prompt(query, context_str, profile)