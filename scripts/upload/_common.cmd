@echo off
REM ============================================================================
REM  _common.cmd  -  shared routine for the per-person upload scripts.
REM  NOT run directly. Each teammate's .cmd sets a few variables then CALLs this.
REM
REM  Expects these variables to be set by the caller before CALL:
REM     SPLIT        - human-readable split name
REM     OWNER_NAME   - GitHub username (used as git author name)
REM     OWNER_EMAIL  - git author email
REM     COMMIT_MSG   - commit message
REM     FILES        - space-separated list of paths owned by this split
REM ============================================================================
setlocal EnableDelayedExpansion

REM --- Target repository (the graduation repo) -------------------------------
set "REPO_URL=https://github.com/Ahmedvip62/Depi-Graduation_project-LLM-for-Data-Analysis.git"
set "REPO_HOST=github.com/Ahmedvip62/Depi-Graduation_project-LLM-for-Data-Analysis.git"
set "BRANCH=main"
set "REPO_WEB=https://github.com/Ahmedvip62/Depi-Graduation_project-LLM-for-Data-Analysis"

REM --- Resolve repo root (two levels up from scripts\upload\) -----------------
pushd "%~dp0..\.." || (echo [X] Could not locate repo root & exit /b 1)
set "REPO_ROOT=%CD%"

echo.
echo ===================================================
echo   DEPI - Universal Analyst : Split Upload
echo   Split : %SPLIT%
echo   Owner : %OWNER_NAME% ^<%OWNER_EMAIL%^>
echo ===================================================

REM --- Make sure git is available --------------------------------------------
where git >nul 2>&1
if errorlevel 1 (
  echo [X] Git is not installed or not on PATH.
  echo     Install Git for Windows: https://git-scm.com/download/win
  popd & pause & exit /b 1
)

REM --- Ensure a repo exists and origin points at the graduation repo ----------
if not exist ".git" (
  echo [X] No git repo found. Run 00_setup.cmd first, then re-run this script.
  popd & pause & exit /b 1
)
git remote get-url origin >nul 2>&1
if errorlevel 1 (
  git remote add origin "%REPO_URL%"
  echo [+] Added origin -^> %REPO_URL%
) else (
  for /f "delims=" %%U in ('git remote get-url origin') do set "CUR_ORIGIN=%%U"
  if not "!CUR_ORIGIN!"=="%REPO_URL%" (
    git remote set-url origin "%REPO_URL%"
    echo [+] Repointed origin -^> %REPO_URL%
  )
)

REM --- Commit identity for THIS person ---------------------------------------
git config user.name  "%OWNER_NAME%"
git config user.email "%OWNER_EMAIL%"
echo [+] Commit identity: %OWNER_NAME% ^<%OWNER_EMAIL%^>

REM --- Authentication --------------------------------------------------------
REM  Git for Windows ships Git Credential Manager, so a login popup usually
REM  handles this. If no credential helper is configured, ask for a PAT.
set "AUTH_URL="
for /f "delims=" %%H in ('git config --get credential.helper 2^>nul') do set "CRED_HELPER=%%H"
if defined CRED_HELPER (
  echo [+] Credential helper detected ^(%CRED_HELPER%^) - GitHub login handled for you.
) else (
  echo [!] No git credential helper found on this PC.
  echo     Enter your GitHub username and a Personal Access Token ^(PAT^).
  echo     Create one at: https://github.com/settings/tokens   ^(scope: repo^)
  set /p "GH_USER=  GitHub username: "
  for /f "usebackq delims=" %%T in (`powershell -NoProfile -Command "$s=Read-Host -AsSecureString '  Personal Access Token (hidden)'; [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($s))"`) do set "GH_TOKEN=%%T"
  set "AUTH_URL=https://!GH_USER!:!GH_TOKEN!@%REPO_HOST%"
)

REM --- Detect a stale/unrelated local history (setup not run) ----------------
git rev-parse -q --verify origin/%BRANCH% >nul 2>&1
if not errorlevel 1 (
  git merge-base HEAD origin/%BRANCH% >nul 2>&1
  if errorlevel 1 (
    echo [X] Your local history is unrelated to the remote.
    echo     Please run 00_setup.cmd first, then re-run this script.
    popd & pause & exit /b 1
  )
)

REM --- Stage only this split's files -----------------------------------------
echo.
echo [ Staging files for this split ]
set /a COUNT=0
for %%F in (%FILES%) do (
  if exist "%%F" (
    git add -- "%%F"
    set /a COUNT+=1
    echo     + %%F
  ) else (
    echo     [!] missing, skipped: %%F
  )
)
echo [+] Staged !COUNT! path^(s^).

REM --- Commit (skip cleanly if nothing changed) ------------------------------
git diff --cached --quiet
if not errorlevel 1 (
  echo [!] Nothing new to commit - this split is already up to date locally.
) else (
  git commit -q -m "%COMMIT_MSG%"
  echo [+] Committed: %COMMIT_MSG%
)

REM --- Sync with remote so the push isn't rejected ---------------------------
echo.
echo [ Syncing with remote ]
git fetch -q origin
git rev-parse -q --verify origin/%BRANCH% >nul 2>&1
if not errorlevel 1 (
  git pull --rebase --autostash origin %BRANCH%
  if errorlevel 1 (
    echo [X] Rebase conflict. Fix the files, then run:  git rebase --continue ^&^& git push
    popd & pause & exit /b 1
  )
)

REM --- Push ------------------------------------------------------------------
echo.
echo [ Pushing to GitHub (%BRANCH%) ]
if defined AUTH_URL (
  git push "%AUTH_URL%" HEAD:%BRANCH%
) else (
  git push -u origin %BRANCH%
)
if errorlevel 1 (
  echo [X] Push failed. Check your GitHub access / token and try again.
  popd & pause & exit /b 1
)

echo.
echo [DONE] Your split is live at:
echo    %REPO_WEB%
echo.
popd
endlocal
pause
exit /b 0
