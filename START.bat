@echo off
cd /d "%~dp0"

title Video Subtitle Translator

echo ============================================
echo   Video Subtitle Translator
echo ============================================
echo.
echo Starting server...
echo Open: http://localhost:8000
echo Press Ctrl+C to stop
echo.

REM 修復 PyTorch 2.6+ weights_only 問題
set TORCH_FORCE_WEIGHTS_ONLY_LOAD=0

venv\Scripts\python.exe -m uvicorn src.main:app --host 127.0.0.1 --port 8000

if %errorlevel% neq 0 (
    echo.
    echo ============================================
    echo   ERROR: Server exited with error code %errorlevel%
    echo   Please check the error messages above.
    echo ============================================
)

echo.
echo Server has stopped. Press any key to close...
pause >nul
