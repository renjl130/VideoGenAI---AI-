# VideoGenAI PowerShell launcher. Uses the same CUDA readiness gate as start.bat.
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$python = Get-Command python -ErrorAction SilentlyContinue
if ($null -eq $python) {
    Write-Host "Python was not found on PATH. Install Python 3.10-3.14 (64-bit) and retry." -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

& $python.Source launcher.py
$exitCode = $LASTEXITCODE
if ($exitCode -ne 0) {
    Write-Host "VideoGenAI did not start. Run setup_cuda.bat to repair the environment." -ForegroundColor Red
    Read-Host "Press Enter to exit"
}
exit $exitCode
