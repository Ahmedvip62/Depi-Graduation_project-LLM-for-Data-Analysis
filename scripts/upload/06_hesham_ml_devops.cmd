@echo off
REM ============================================================================
REM  06 - Hesham  (GitHub: kiradata3 / repo integrator)
REM  SPLIT: ML Prediction + DevOps / Infrastructure + Docs
REM  Owns the predictive-modeling skill and its API route, plus all deployment
REM  glue: Docker, compose files, Makefile, CI workflow, setup scripts, the
REM  cloud setup notebook, and the project documentation (README/PRODUCT/docs).
REM ============================================================================
set "SPLIT=ML Prediction + DevOps/Infra + Docs"
set "OWNER_NAME=Hesham Ahmed"
set "OWNER_EMAIL=kiradata3@gmail.com"
set "COMMIT_MSG=feat(ml+infra): prediction skill + route, Docker/compose/CI/Makefile, setup notebook and docs"

REM Files owned by this split
set "FILES=backend/app/skills/prediction.py backend/app/api/predict.py backend/Dockerfile docker-compose.yml docker-compose.prod.yml Makefile .github .env.example .gitignore scripts/setup_ollama.sh scripts/serve_frontend.sh scripts/upload main.ipynb README.md PRODUCT.md docs CONTRIBUTORS.md"

call "%~dp0_common.cmd"
exit /b %errorlevel%
