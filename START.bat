@echo off
cd /d "%~dp0"

title Video Subtitle Translator

echo Starting server...
echo Open: http://localhost:8000
echo Press Ctrl+C to stop
echo.

venv\Scripts\python.exe -m uvicorn src.main:app --host 127.0.0.1 --port 8000

pause
