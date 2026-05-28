$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

function Invoke-Step {
  param([scriptblock]$Command)
  & $Command
  if ($LASTEXITCODE -ne 0) {
    throw "Command failed with exit code $LASTEXITCODE"
  }
}

if (!(Test-Path ".venv")) {
  Invoke-Step { python -m venv .venv }
}

Invoke-Step { & ".\.venv\Scripts\python.exe" -m pip install --upgrade pip setuptools wheel }
Invoke-Step { & ".\.venv\Scripts\python.exe" -m pip install -r requirements-gpu.txt }
Invoke-Step { & ".\.venv\Scripts\python.exe" -m pip install -r requirements.txt }

Push-Location "frontend"
Invoke-Step { npm install }
Pop-Location

Write-Host "Setup complete."
