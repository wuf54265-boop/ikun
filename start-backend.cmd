@echo off
cd /d D:\workbuddy\ai-data-analysis-assistant\backend
call C:\Users\Œ‚≤©—≈\.workbuddy\binaries\python\envs\ada-venv\Scripts\activate.bat
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
