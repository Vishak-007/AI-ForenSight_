@echo off
REM Starts the AI-ForenSight FastAPI backend on http://127.0.0.1:8000
REM Requires Postgres and Qdrant already running (see README.md "Setup").
cd /d "%~dp0"
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
pause
