$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$env:MEDJARVIS_GPU_REQUIRED = "1"
$env:MEDJARVIS_REQUIRE_LLM = "1"
$env:MEDJARVIS_LLAMA_SERVER_URL = "http://127.0.0.1:8080/v1"
$env:MEDJARVIS_ASR_PRELOAD = "1"

& ".\.venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
