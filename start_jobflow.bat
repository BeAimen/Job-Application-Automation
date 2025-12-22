@echo off
REM JobFlow Windows Launcher
REM Double-click this file to start JobFlow

title JobFlow - Starting...

echo.
echo ========================================
echo   Starting JobFlow...
echo ========================================
echo.

REM Change to script directory
cd /d "%~dp0"

REM Check if virtual environment exists
if exist ".venv\Scripts\activate.bat" (
    echo Activating virtual environment...
    call .venv\Scripts\activate.bat
) else (
    echo Warning: Virtual environment not found!
    echo Please run: python -m venv .venv
    echo Then run: .venv\Scripts\activate.bat
    echo Then run: pip install -r requirements.txt
    pause
    exit /b 1
)

REM Start the launcher
python launcher.py

REM Keep window open if there was an error
if errorlevel 1 (
    echo.
    echo Press any key to close...
    pause >nul
)