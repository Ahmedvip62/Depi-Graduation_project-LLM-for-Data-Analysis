@echo off
REM ============================================================================
REM  01 - Ahmed  (GitHub: Ahmedvip62)
REM  SPLIT: Frontend - React + Vite + TailwindCSS UI
REM  Owns the entire user-facing app: chat, dashboard, upload flow, chart
REM  gallery, session sidebar, command palette, report controls, hooks & lib.
REM ============================================================================
set "SPLIT=Frontend - React UI"
set "OWNER_NAME=Ahmedvip62"
set "OWNER_EMAIL=ahmed192r22@gmail.com"
set "COMMIT_MSG=feat(frontend): React + Vite + Tailwind workspace (chat, dashboard, upload, charts, reports)"

REM Files owned by this split
set "FILES=frontend"

call "%~dp0_common.cmd"
exit /b %errorlevel%
