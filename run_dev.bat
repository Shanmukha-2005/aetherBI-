@echo off
echo ===================================================
echo   Starting AetherBI - AI Business Intelligence Agent
echo ===================================================

echo [1/2] Launching FastAPI Backend on http://localhost:8000 ...
start "AetherBI Backend" cmd /k "cd /d %~dp0 && .\venv\Scripts\uvicorn app.main:app --app-dir backend --reload --port 8000"

echo [2/2] Launching React Vite Frontend on http://localhost:5173 ...
start "AetherBI Frontend" cmd /k "cd /d %~dp0\frontend && npm run dev"

echo.
echo Both servers started!
echo Frontend: http://localhost:5173
echo Backend API Docs: http://localhost:8000/docs
echo.
