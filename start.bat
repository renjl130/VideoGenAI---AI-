@echo off
setlocal
cd /d "%~dp0"
python launcher.py
if errorlevel 1 (
    echo.
    echo VideoGenAI did not start. Run setup_cuda.bat to repair the environment.
    pause
)
