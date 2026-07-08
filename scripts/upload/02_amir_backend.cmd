@echo off
REM ============================================================================
REM  02 - Amir  (GitHub: amiressam777)
REM  SPLIT: Backend Core & API + LLM integration
REM  Owns the FastAPI backbone: app bootstrap, config, request/response models,
REM  the streaming /chat brain, sessions, upload & health routes, the session
REM  manager, and the Ollama LLM client (the model connection).
REM ============================================================================
set "SPLIT=Backend Core ^& API + LLM integration"
set "OWNER_NAME=amiressam777"
set "OWNER_EMAIL=amir2003easam@gmail.com"
set "COMMIT_MSG=feat(backend): FastAPI core, API layer, models, session manager and Ollama LLM client"

REM Files owned by this split
set "FILES=backend/app/main.py backend/app/config.py backend/app/__init__.py backend/app/models/schemas.py backend/app/models/enums.py backend/app/models/__init__.py backend/app/api/__init__.py backend/app/api/chat.py backend/app/api/sessions.py backend/app/api/upload.py backend/app/api/health.py backend/app/api/router.py backend/app/api/skills_api.py backend/app/core/session_manager.py backend/app/llm/ollama_client.py backend/app/llm/__init__.py backend/requirements.txt backend/pyproject.toml backend/tests/conftest.py backend/tests/__init__.py"

call "%~dp0_common.cmd"
exit /b %errorlevel%
