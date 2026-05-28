param(
  [string]$Repo = "mobiuslabsgmbh/faster-whisper-large-v3-turbo"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot

if (!(Test-Path (Join-Path $Root ".venv\Scripts\python.exe"))) {
  throw ".venv is missing. Run scripts\setup.ps1 first."
}

@"
from huggingface_hub import snapshot_download

path = snapshot_download(
    repo_id="$Repo",
    allow_patterns=["*.bin", "*.json", "*.txt", "*.model", "vocabulary.*"],
)
print(path)
"@ | & (Join-Path $Root ".venv\Scripts\python.exe") -
