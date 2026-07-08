@echo off
REM ============================================================================
REM  00_setup.cmd  -  RUN THIS FIRST, once, on YOUR copy of the project.
REM
REM  Every teammate runs this on their own machine before uploading their split.
REM  It is SAFE: it never deletes your project files. It only:
REM     * removes any stale local git metadata (.git folder)
REM     * initializes git and points it at the graduation repo
REM     * adopts the repo's current clean history as the base
REM       (so your later push is a simple fast-forward, not a conflict)
REM
REM  After this, run your own upload script (e.g. 06_hesham_ml_devops.cmd).
REM ============================================================================
setlocal
set "REPO_URL=https://github.com/Ahmedvip62/Depi-Graduation_project-LLM-for-Data-Analysis.git"
set "BRANCH=main"

pushd "%~dp0..\.." || (echo [X] Could not locate repo root & exit /b 1)

echo.
echo ====================================================
echo   DEPI - Universal Analyst : One-time Setup
echo   (safe - your project files are NOT touched)
echo ====================================================
echo.

where git >nul 2>&1
if errorlevel 1 (
  echo [X] Git is not installed or not on PATH.
  echo     Install Git for Windows: https://git-scm.com/download/win
  popd & exit /b 1
)

if exist ".git" (
  echo [!] Removing stale local git metadata ^(.git folder only - your files stay^).
  rmdir /s /q ".git"
)

echo [ Initializing git and connecting to the graduation repo ]
git init -q
git branch -M %BRANCH%
git remote add origin "%REPO_URL%"
echo [+] origin -^> %REPO_URL%

echo.
echo [ Adopting the repo's current history as your base ]
git fetch -q origin
git rev-parse -q --verify origin/%BRANCH% >nul 2>&1
if errorlevel 1 (
  echo [!] Remote has no '%BRANCH%' branch yet - you'll create it on first push.
) else (
  git reset -q origin/%BRANCH%
  echo [+] Local base set to the latest remote commit. Your files are preserved.
)

echo.
echo  --------------------------------------------------------------
echo   Setup complete. Now run YOUR upload script from this folder:
echo.
echo     Ahmed     (Frontend) ....  01_ahmed_frontend.cmd
echo     Amir      (Backend)  ....  02_amir_backend.cmd
echo     Shahenda  (AI/RAG)   ....  03_shahenda_ai_rag.cmd
echo     Doaa      (Data Eng) ....  04_doaa_data.cmd
echo     Maimamoon (Viz)      ....  05_maimamoon_visualization.cmd
echo     Hesham    (ML+DevOps)....  06_hesham_ml_devops.cmd
echo.
echo   Order does NOT matter - you do not need to wait for anyone.
echo  --------------------------------------------------------------
echo.
popd
endlocal
pause
exit /b 0
