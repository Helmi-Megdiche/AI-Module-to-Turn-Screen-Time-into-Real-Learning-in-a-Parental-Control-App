# Start the AI service using this folder's .venv Python (avoids wrong interpreter when multiple Pythons exist).
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
if (-not (Test-Path ".\.venv\Scripts\python.exe")) {
    Write-Error "Missing ai-service\.venv — run: python -m venv .venv && .\.venv\Scripts\Activate.ps1 && pip install -r requirements.txt"
}
& .\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
