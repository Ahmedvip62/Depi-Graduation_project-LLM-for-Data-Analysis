@echo off
REM ============================================================================
REM  05 - Maimamoon  (GitHub: maimamoon)
REM  SPLIT: Visualization & Reporting
REM  Owns the chart engine (validated model-driven Plotly plans -> figures),
REM  chart export (Kaleido), the PDF report skill + narrative generator, and the
REM  /visualize API route, plus the visualization tests.
REM ============================================================================
set "SPLIT=Visualization ^& Reporting"
set "OWNER_NAME=maimamoon"
set "OWNER_EMAIL=maimamoon548@gmail.com"
set "COMMIT_MSG=feat(viz): Plotly chart factory/types/export, PDF report skill + narrative, /visualize route and tests"

REM Files owned by this split
set "FILES=backend/app/visualization/chart_factory.py backend/app/visualization/chart_types.py backend/app/visualization/export.py backend/app/visualization/__init__.py backend/app/skills/report.py backend/app/skills/report_narrative.py backend/app/skills/__init__.py backend/app/api/visualizations.py backend/tests/test_visualization.py"

call "%~dp0_common.cmd"
exit /b %errorlevel%
