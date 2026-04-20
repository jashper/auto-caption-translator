@echo off
echo Starting storage cleanup tool...
echo.
cd /d "%~dp0"
powershell -ExecutionPolicy Bypass -File "tools\CLEAN_STORAGE.ps1"
pause
