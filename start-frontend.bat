@echo off
REM Starts the AI-ForenSight frontend dev server.
REM Expects the backend at http://127.0.0.1:8000 (see frontend\forensics-workflow-main\.env).
cd /d "%~dp0frontend\forensics-workflow-main"
if not exist node_modules (
    echo Installing frontend dependencies (first run only)...
    call npm install
)
call npm run dev
pause
