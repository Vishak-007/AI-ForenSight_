@echo off
REM Launches the backend and frontend each in their own window.
REM Postgres + Qdrant must already be running -- see README.md "Setup":
REM   docker run -d --name ufdr-postgres -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=123456 -e POSTGRES_DB=ufdr_forensics -p 5432:5432 postgres:16
REM   docker run -d --name ufdr-qdrant -p 6333:6333 qdrant/qdrant
cd /d "%~dp0"
start "AI-ForenSight Backend" cmd /k start-backend.bat
start "AI-ForenSight Frontend" cmd /k start-frontend.bat
