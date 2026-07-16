# VideoGenAI Launcher (PowerShell)
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  VideoGenAI Launcher" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Set-Location $PSScriptRoot

# Check Python
try {
    $pythonVersion = python --version 2>&1
    Write-Host "Python: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "ERROR: Python not found" -ForegroundColor Red
    Write-Host "Please install Python 3.10+ from https://www.python.org/downloads/"
    Read-Host "Press Enter to exit"
    exit 1
}

# Check/Create venv
if (-not (Test-Path ".venv")) {
    Write-Host "First run, initializing environment..." -ForegroundColor Yellow
    Write-Host ""
    
    Write-Host "Creating virtual environment..." -ForegroundColor Yellow
    python -m venv .venv
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Failed to create virtual environment" -ForegroundColor Red
        Read-Host "Press Enter to exit"
        exit 1
    }
    
    & ".venv\Scripts\Activate.ps1"
    
    Write-Host "Installing dependencies..." -ForegroundColor Yellow
    pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Failed to install dependencies" -ForegroundColor Red
        Read-Host "Press Enter to exit"
        exit 1
    }
    
    Write-Host ""
    Write-Host "Initialization complete!" -ForegroundColor Green
    Write-Host ""
} else {
    & ".venv\Scripts\Activate.ps1"
}

Write-Host "Starting VideoGenAI..." -ForegroundColor Green
Write-Host ""
python main.py

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "Program exited with error" -ForegroundColor Red
    Read-Host "Press Enter to exit"
}
