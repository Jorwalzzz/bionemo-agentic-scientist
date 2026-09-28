#!/usr/bin/env pwsh
# Agentic BioNeMo - PowerShell Automated Setup Script
# Run with: irm https://raw.githubusercontent.com/Jorwalzzz/bionemo-agentic-scientist/main/install.ps1 | iex

$ErrorActionPreference = 'Stop'

Write-Host "`n============================================================" -ForegroundColor Green
Write-Host " NVIDIA BioNeMo - Agentic AI Drug Discovery Scientist" -ForegroundColor Green  
Write-Host " Automated PowerShell Setup" -ForegroundColor Green
Write-Host "============================================================`n" -ForegroundColor Green

# Check Python
try {
    $pyVersion = (python --version 2>&1).ToString()
    Write-Host " [OK] $pyVersion found." -ForegroundColor Green
} catch {
    Write-Host " [ERROR] Python 3.10+ not found. Download from https://www.python.org/downloads/" -ForegroundColor Red
    exit 1
}

# Clone or update repo
$targetDir = "$env:USERPROFILE\bionemo-agentic-scientist"
if (-not (Test-Path $targetDir)) {
    Write-Host " [INFO] Cloning repository..." -ForegroundColor Cyan
    git clone https://github.com/Jorwalzzz/bionemo-agentic-scientist.git $targetDir
} else {
    Write-Host " [OK] Repository exists at $targetDir - pulling updates..." -ForegroundColor Green
    git -C $targetDir pull origin main
}

Set-Location $targetDir

# Create virtual environment
if (-not (Test-Path ".venv")) {
    Write-Host " [INFO] Creating virtual environment..." -ForegroundColor Cyan
    python -m venv .venv
}

# Activate and install
Write-Host " [INFO] Installing dependencies (this may take 2-3 minutes)..." -ForegroundColor Cyan
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip -q
pip install -r requirements.txt -q
Write-Host " [OK] Dependencies installed." -ForegroundColor Green

# Create .env
if (-not (Test-Path ".env")) {
    if (Test-Path ".env.example") {
        Copy-Item .env.example .env
    } else {
        "NVIDIA_API_KEY=`nMOCK_MODE=true" | Out-File .env -Encoding utf8
    }
    Write-Host " [OK] Config created - free Mock Mode active by default." -ForegroundColor Green
    Write-Host " OPTIONAL: Edit .env and add NVIDIA_API_KEY for live GPU inference." -ForegroundColor Yellow
}

Write-Host "`n============================================================" -ForegroundColor Green
Write-Host " Launching Agentic BioNeMo on http://localhost:8000" -ForegroundColor Green
Write-Host "============================================================`n" -ForegroundColor Green

Start-Process powershell -ArgumentList "-Command", "Start-Sleep 2; Start-Process http://localhost:8000" -WindowStyle Hidden
python serve_cockpit.py
