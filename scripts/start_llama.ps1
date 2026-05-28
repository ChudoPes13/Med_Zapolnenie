param(
  [string]$ModelPath = "",
  [int]$Port = 8080
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$LlamaDir = "C:\Work25\Avalin\llama-b9090-bin-win-cuda-13.1-x64"
$Exe = Join-Path $LlamaDir "llama-server.exe"

if (!(Test-Path $Exe)) {
  throw "llama-server not found: $Exe"
}

if (!$ModelPath) {
  $ModelPath = Join-Path $Root "models\Qwen3-4B-Q4_K_M.gguf"
}

if (!(Test-Path $ModelPath)) {
  throw "Model not found: $ModelPath. Run scripts\download_model.ps1 -Profile qwen3-4b"
}

Set-Location $LlamaDir
& $Exe `
  --host 127.0.0.1 `
  --port $Port `
  --model $ModelPath `
  --device CUDA0 `
  --gpu-layers all `
  --ctx-size 8192 `
  --parallel 1 `
  --flash-attn on
