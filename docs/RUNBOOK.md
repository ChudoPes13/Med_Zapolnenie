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
scripts\download_asr.ps1
```

`setup.ps1` creates `.venv`, installs PyTorch CUDA 13.0 wheels, backend dependencies, and frontend packages.

## Start

Recommended single command:

```powershell
scripts\start_medjarvis.ps1 -Restart
```

This starts `llama-server`, backend, and frontend in hidden PowerShell processes and writes logs to `logs\`.
Use `-Restart` after code changes so an old backend process on port 8000 cannot keep serving stale code.

Manual three-terminal mode is still available:

```powershell
scripts\start_llama.ps1
scripts\start_backend.ps1
scripts\start_frontend.ps1
```

Then open http://127.0.0.1:5173.

## Health Checks

```powershell
scripts\gpu_health.ps1
scripts\model_check.ps1
Invoke-RestMethod http://127.0.0.1:8000/api/health
```

Backend startup uses `MEDJARVIS_GPU_REQUIRED=1` by default in `scripts\start_backend.ps1`.
Backend startup also uses `MEDJARVIS_REQUIRE_LLM=1`; if `llama-server` is not reachable at `http://127.0.0.1:8080/v1`, FastAPI fails on startup instead of silently running without LLM.
Backend startup preloads Faster-Whisper with `MEDJARVIS_ASR_PRELOAD=true` so the first dictated segment does not pay model load time.
For tests only, set `MEDJARVIS_REQUIRE_LLM=0`.

## ASR Tuning

Current Faster-Whisper decode settings are configured in `app\core\config.py` and can be overridden through `MEDJARVIS_ASR_*` environment variables:

- `ASR_MODEL=large-v3-turbo`
- `ASR_LANGUAGE=ru`
- `ASR_DEVICE=cuda`
- `ASR_COMPUTE_TYPE=int8_float16`
- `ASR_BEAM_SIZE=1`
- `ASR_BEST_OF=1`
- `ASR_TEMPERATURE=0.0`
- `ASR_CONDITION_ON_PREVIOUS_TEXT=false`
- `ASR_INITIAL_PROMPT` contains a Russian medical-context prompt.
- `ASR_HOTWORDS` contains EMK, dental, and lower-limb terms.

Keep `beam_size=1` and `best_of=1` for realtime latency. Raise them only for offline quality benchmarking.

## Lower-Limb Acceptance Scenario

1. Send: `Болит зуб, нижняя челюсть, боль при накусывании.`
2. The first line above is the old dental demo and should only activate dentistry because it says `зуб`.
3. Send: `У пациента боль в нижних конечностях. Ему 17 лет.`
4. Confirm that `17 лет` becomes patient age, not FDI tooth 17, and the dental panel is not shown.
5. Send: `Правая голень отечна, стопа холодная, пульс на тыльной артерии стопы не определяется.`
6. Confirm that lower-limb fields fill and profile-specific checks update.
7. Press `Завершить`; final summary appears and final checks run.
8. Press confirm, then export JSON/HTML/1C/DOCX.

## Dental Acceptance Scenario

1. Send: `Болит зуб 36, боль при накусывании, ЭОД 8 мкА.`
2. Confirm that the dental panel appears only because dental context is explicit.
3. Send allergy, BP, percussion, thermal test, and diagnosis confirmation.
4. Press `Завершить`, confirm, then export.

## Production Notes

- Keep model files in `models/`; they are gitignored.
- Faster-Whisper maps `large-v3-turbo` to `mobiuslabsgmbh/faster-whisper-large-v3-turbo`.
- SQLite runtime DB lives in `data/medjarvis.db`; it is gitignored.
- The KR provider is a stub for v1. Replace it by implementing `GuidelinesProvider.search()`.
- `Qwen3-4B-Q4_K_M.gguf` is the realtime default. Use `Qwen3-8B-Q4_K_M.gguf` only when ASR is not competing for VRAM or after local benchmarks.
