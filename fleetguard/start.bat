@echo off
setlocal
cd /d "%~dp0"
title Fleetguard

echo Fleetguard - starting...
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python was not found. Install Python 3 and add it to PATH, then run this script again.
    pause
    exit /b 1
)

REM The bundled "venv" folder may point to Python on another machine and fail here.
REM Use the Python from PATH and ensure dependencies (including click for Flask) are installed.
python -m pip install -r "%~dp0requirements.txt"
if errorlevel 1 (
    echo ERROR: Could not install dependencies. Check the messages above.
    pause
    exit /b 1
)

echo.
echo Server: http://127.0.0.1:5000  ^(press Ctrl+C to stop^)
echo.
python "%~dp0app.py"
echo.
if errorlevel 1 pause
