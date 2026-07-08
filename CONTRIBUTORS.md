# Contributors & Work Split

**Project:** Universal Analyst — LLM-Driven Data Analysis
**Team:** DEPI Graduation Project (6 members)
**Repository:** https://github.com/Ahmedvip62/Depi-Graduation_project-LLM-for-Data-Analysis

Each member owns a coherent, self-contained slice of the system so work — and the
git history — stays cleanly attributable.

| # | Member | GitHub | Split | Primary paths |
|---|--------|--------|-------|---------------|
| 1 | Ahmed | [@Ahmedvip62](https://github.com/Ahmedvip62) | **Frontend — React UI** | `frontend/` |
| 2 | Amir | [@amiressam777](https://github.com/amiressam777) | **Backend Core & API + LLM integration** | `backend/app/main.py`, `config.py`, `models/`, `api/` (chat, sessions, upload, health, router, skills_api), `core/session_manager.py`, `llm/ollama_client.py` |
| 3 | Shahenda | [@Shahendawael](https://github.com/Shahendawael) | **AI — Prompting & RAG** | `backend/app/llm/prompt_templates.py`, `token_counter.py`, `rag/`, `skills_registry/` |
| 4 | Doaa | [@doaa186](https://github.com/doaa186) | **Data Engineering** | `backend/app/core/ingestion.py`, `chunker.py`, `profiler.py`, `eda/`, `skills/cleaning.py`, `api/clean.py`, `data/samples/` |
| 5 | Maimamoon | [@maimamoon](https://github.com/maimamoon) | **Visualization & Reporting** | `backend/app/visualization/`, `skills/report.py`, `report_narrative.py`, `api/visualizations.py` |
| 6 | Hesham | — | **ML Prediction + DevOps/Infra + Docs** | `backend/app/skills/prediction.py`, `api/predict.py`, Docker/compose, `Makefile`, `.github/`, `scripts/`, `main.ipynb`, docs |

## Shared contracts

Two files define the boundary between people and should change by agreement:

- **`backend/app/models/schemas.py`** (Amir) — the API request/response shapes.
- **`frontend/src/lib/api.js`** (Ahmed) — the client that calls those endpoints.

## Uploading your split

Windows Command Prompt scripts live in [`scripts/upload/`](scripts/upload/). One
person runs `00_setup.cmd` once; then each member runs their own `.cmd` to commit
and push only their split under their own GitHub identity. See
[`scripts/upload/README.md`](scripts/upload/README.md).
