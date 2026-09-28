@echo off
setlocal enabledelayedexpansion
title Agentic BioNeMo - 1-Click Installer

echo.
echo  ============================================================
echo   NVIDIA BioNeMo - Agentic AI Drug Discovery Scientist
echo   Automated Local Setup and Launcher
echo  ============================================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Python 3.10+ is required but not found.
    echo  Please download from: https://www.python.org/downloads/
    echo  Check "Add Python to PATH" during installation.
    pause
    exit /b 1
)

echo  [OK] Python found.

if exist "src\orchestrator.py" (
    echo  [OK] Repository already present. Pulling latest updates...
    git pull origin main >nul 2>&1
) else (
    echo  [INFO] Cloning repository from GitHub...
    git clone https://github.com/Jorwalzzz/bionemo-agentic-scientist.git .
)

if not exist ".venv" (
    echo  [INFO] Creating Python virtual environment...
    python -m venv .venv
)

call .venv\Scripts\activate.bat
echo  [INFO] Installing dependencies (this may take 2-3 minutes)...
python -m pip install --upgrade pip -q
pip install -r requirements.txt -q

if not exist ".env" (
    if exist ".env.example" (
        copy .env.example .env >nul 2>&1
    ) else (
        echo NVIDIA_API_KEY= > .env
        echo MOCK_MODE=true >> .env
    )
    echo  [OK] Config created - running in free Mock Mode by default.
    echo  OPTIONAL: Edit .env and add your NVIDIA_API_KEY for live inference.
)

echo.
echo  ============================================================
echo   Launching Agentic BioNeMo on http://localhost:8000
echo  ============================================================
echo.

start "" cmd /c "timeout /t 2 >nul && start http://localhost:8000"
python serve_cockpit.py
pause
