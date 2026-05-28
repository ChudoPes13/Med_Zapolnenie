$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

if (!(Test-Path ".venv")) {
  python -m venv .venv
}

& ".\.venv\Scripts\python.exe" -m pip install --upgrade pip setuptools wheel
& ".\.venv\Scripts\python.exe" -m pip install -r requirements-gpu.txt
& ".\.venv\Scripts\python.exe" -m pip install -r requirements.txt

Push-Location "frontend"
npm install
Pop-Location

Write-Host "Setup complete."
