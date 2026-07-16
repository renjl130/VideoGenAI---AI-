@echo off
setlocal
cd /d "%~dp0"
python scripts\setup_environment.py --backend cuda --venv .venv --force-torch
if errorlevel 1 (
    echo.
    echo CUDA environment setup failed.
    pause
    exit /b 1
)
echo.
echo CUDA environment is ready.
pause
