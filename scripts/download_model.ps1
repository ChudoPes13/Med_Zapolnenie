param(
  [ValidateSet("qwen3-4b", "qwen3-8b")]
  [string]$Profile = "qwen3-4b"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$ModelDir = Join-Path $Root "models"
New-Item -ItemType Directory -Force -Path $ModelDir | Out-Null

if ($Profile -eq "qwen3-4b") {
  $Repo = "Qwen/Qwen3-4B-GGUF"
  $File = "Qwen3-4B-Q4_K_M.gguf"
} else {
  $Repo = "Qwen/Qwen3-8B-GGUF"
  $File = "Qwen3-8B-Q4_K_M.gguf"
}

$Target = Join-Path $ModelDir $File
if (Test-Path $Target) {
  Write-Host "Model already exists: $Target"
  exit 0
}

if (!(Test-Path (Join-Path $Root ".venv\Scripts\python.exe"))) {
  throw ".venv is missing. Run scripts\setup.ps1 first."
}

& (Join-Path $Root ".venv\Scripts\python.exe") -c "from huggingface_hub import hf_hub_download; hf_hub_download(repo_id='$Repo', filename='$File', local_dir=r'$ModelDir', local_dir_use_symlinks=False)"
Write-Host "Downloaded: $Target"
