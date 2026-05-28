$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$DefaultLlm = Join-Path $Root "models\Qwen3-4B-Q4_K_M.gguf"
$LlamaExe = "C:\Work25\Avalin\llama-b9090-bin-win-cuda-13.1-x64\llama-server.exe"

[PSCustomObject]@{
  LlamaServer = Test-Path $LlamaExe
  LlmModel = Test-Path $DefaultLlm
  LlmModelPath = $DefaultLlm
  AsrRepo = "mobiuslabsgmbh/faster-whisper-large-v3-turbo"
} | ConvertTo-Json

if (Test-Path (Join-Path $Root ".venv\Scripts\python.exe")) {
  @'
from faster_whisper.utils import _MODELS
print("faster_whisper_large_v3_turbo_repo", _MODELS.get("large-v3-turbo"))
'@ | & (Join-Path $Root ".venv\Scripts\python.exe") -
}
