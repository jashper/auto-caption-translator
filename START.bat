@echo off
cd /d "%~dp0"

title Video Subtitle Translator

echo Starting server...
echo Open: http://localhost:8000
echo Press Ctrl+C to stop
echo.

REM 修復 PyTorch 2.6+ weights_only 問題
set TORCH_FORCE_WEIGHTS_ONLY_LOAD=0

venv\Scripts\python.exe -m uvicorn src.main:app --host 127.0.0.1 --port 8000

pause
