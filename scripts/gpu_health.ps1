$ErrorActionPreference = "Stop"

nvidia-smi --query-gpu=name,memory.total,memory.free,driver_version --format=csv,noheader

if (Test-Path ".venv\Scripts\python.exe") {
  @'
import torch
print("torch", torch.__version__)
print("cuda_available", torch.cuda.is_available())
if torch.cuda.is_available():
    print("device", torch.cuda.get_device_name(0))
'@ | & ".\.venv\Scripts\python.exe" -
} else {
  Write-Host ".venv not found"
}
