@echo off
title VideoGenAI Launcher

echo ========================================
echo   VideoGenAI Launcher
echo ========================================
echo.

cd /d "%~dp0"

python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Please install Python 3.10+
    echo Download: https://www.python.org/downloads/
    pause
    exit /b 1
)

if not exist ".venv" (
    echo First run, initializing environment...
    echo.
    
    echo Creating virtual environment...
    python -m venv .venv
    if errorlevel 1 (
        echo Failed to create virtual environment
        pause
        exit /b 1
    )
    
    call .venv\Scripts\activate.bat
    
    echo Installing dependencies...
    pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
    if errorlevel 1 (
        echo Failed to install dependencies
        pause
        exit /b 1
    )
    
    echo.
    echo Initialization complete!
    echo.
) else (
    call .venv\Scripts\activate.bat
)

echo Starting VideoGenAI...
echo.
python main.py

if errorlevel 1 (
    echo.
    echo Program exited with error
    pause
)
