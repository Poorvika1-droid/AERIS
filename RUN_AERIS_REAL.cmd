@echo off
cd /d "%~dp0"
rem No validated operational dataset/model is registered yet. Keep the UI explicitly demo-mode.
set AERIS_DATA_MODE=demonstration
set DATABASE_URL=sqlite:///%cd%/data/aeris.db
set NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
cd apps\api
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
