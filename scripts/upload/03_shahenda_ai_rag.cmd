@echo off
REM ============================================================================
REM  03 - Shahenda  (GitHub: Shahendawael)
REM  SPLIT: AI - LLM Prompting & RAG (Retrieval-Augmented Generation)
REM  Owns the intelligence layer: prompt templates, token accounting, the vector
REM  store (ChromaDB), embeddings (sentence-transformers), retriever, context
REM  builder, and the skill/intent registry that steers the model.
REM ============================================================================
set "SPLIT=AI - Prompting ^& RAG"
set "OWNER_NAME=Shahendawael"
set "OWNER_EMAIL=wi055515@gmail.com"
set "COMMIT_MSG=feat(ai): prompt templates, token counter, ChromaDB RAG (store/embed/retrieve/context) and skill registry"

REM Files owned by this split
set "FILES=backend/app/llm/prompt_templates.py backend/app/llm/token_counter.py backend/app/rag/store.py backend/app/rag/embedder.py backend/app/rag/retriever.py backend/app/rag/context_builder.py backend/app/rag/__init__.py backend/app/skills_registry"

call "%~dp0_common.cmd"
exit /b %errorlevel%
