@echo off
REM ============================================================================
REM  04 - Doaa  (GitHub: doaa186)
REM  SPLIT: Data Engineering - Ingestion, Profiling & Cleaning
REM  Owns everything that turns a raw upload into analyzable data: multi-format
REM  ingestion, chunking, statistical profiling, automated EDA, the cleaning
REM  skill + its API route, sample datasets, and the related tests.
REM ============================================================================
set "SPLIT=Data Engineering - Ingestion/Profiling/Cleaning"
set "OWNER_NAME=doaa186"
set "OWNER_EMAIL=dm1862004@gmail.com"
set "COMMIT_MSG=feat(data): ingestion, chunker, profiler, auto-EDA, cleaning skill + tests and sample datasets"

REM Files owned by this split
set "FILES=backend/app/core/ingestion.py backend/app/core/chunker.py backend/app/core/profiler.py backend/app/core/__init__.py backend/app/eda/auto_eda.py backend/app/eda/__init__.py backend/app/skills/cleaning.py backend/app/api/clean.py backend/tests/test_ingestion.py backend/tests/test_profiler.py data/samples"

call "%~dp0_common.cmd"
exit /b %errorlevel%
