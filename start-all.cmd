@echo off
start "backend" cmd /k "cd /d D:\workbuddy\ai-data-analysis-assistant\backend && call C:\Users\Œ‚≤©—≈\.workbuddy\binaries\python\envs\ada-venv\Scripts\activate.bat && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"
start "frontend" cmd /k "cd /d D:\workbuddy\ai-data-analysis-assistant\frontend && npm run dev"
echo Starting backend and frontend... open http://localhost:3000 in a few seconds
pause
