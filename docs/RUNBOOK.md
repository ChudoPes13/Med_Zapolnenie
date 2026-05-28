# МедЖарвис Runbook

## Workstation

- Windows 11
- Python 3.12
- Node.js 22+
- NVIDIA RTX 3070 8GB
- CUDA Toolkit 13.0 and driver runtime 13.x
- `llama-server.exe`: `C:\Work25\Avalin\llama-b9090-bin-win-cuda-13.1-x64\llama-server.exe`

## Setup

```powershell
scripts\setup.ps1
scripts\download_model.ps1 -Profile qwen3-4b
```

`setup.ps1` creates `.venv`, installs PyTorch CUDA 13.0 wheels, backend dependencies, and frontend packages.

## Start

Open three PowerShell terminals:

```powershell
scripts\start_llama.ps1
scripts\start_backend.ps1
scripts\start_frontend.ps1
```

Then open http://127.0.0.1:5173.

## Health Checks

```powershell
scripts\gpu_health.ps1
Invoke-RestMethod http://127.0.0.1:8000/api/health
```

Backend startup uses `MEDJARVIS_GPU_REQUIRED=1` by default in `scripts\start_backend.ps1`.

## Acceptance Scenario

1. Send: `Болит зуб, нижняя челюсть, боль при накусывании.`
2. Confirm that complaints fill and red findings include FDI, odontogram, EOD/percussion/thermal, allergy, BP, ICD confirmation.
3. Send: `Зуб 36, перкуссия отрицательная, ЭОД 8 мкА, аллергии нет, АД 120/80, подтверждаю K02.1 кариес.`
4. Confirm that FDI, odontogram, percussion, EOD, allergy, BP, and diagnosis confirmation improve quality state.
5. Press confirm, then export JSON/HTML/1C/DOCX.

## Production Notes

- Keep model files in `models/`; they are gitignored.
- SQLite runtime DB lives in `data/medjarvis.db`; it is gitignored.
- The KR provider is a stub for v1. Replace it by implementing `GuidelinesProvider.search()`.
- `Qwen3-4B-Q4_K_M.gguf` is the realtime default. Use `Qwen3-8B-Q4_K_M.gguf` only when ASR is not competing for VRAM or after local benchmarks.
