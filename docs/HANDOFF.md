# МедЖарвис Handoff

## Current State

Greenfield MVP scaffolded in `C:\ai26\Med_Zapolnenie`:

- FastAPI backend with SQLite audit trail.
- WebSocket PCM16 realtime endpoint.
- Faster-Whisper and Silero wrappers with GPU-required startup.
- Local `llama-server` client and deterministic dental extraction overlay.
- KR stub provider for `KR 1021_1`.
- Quality checker for profile-specific lower-limb and dental requirements.
- React/Vite UI with AudioWorklet PCM streaming.
- UI map in `docs/UI_MAP.md`.
- JSON/HTML/1C/DOCX exports after doctor confirmation.

## Commands

```powershell
scripts\setup.ps1
scripts\download_model.ps1 -Profile qwen3-4b
scripts\download_asr.ps1
scripts\start_llama.ps1
scripts\start_backend.ps1
scripts\start_frontend.ps1
```

Tests:

```powershell
$env:MEDJARVIS_GPU_REQUIRED='0'
.venv\Scripts\python -m pytest
cd frontend
npm run build
```

## Open Risks

- Real KR database is not connected yet; provider returns visible stubs.
- The UI no longer seeds dental text by default; `НК пример` is an explicit manual test helper.
- `llama-server` model must be downloaded before LLM extraction is live.
- ASR model download and first load can take time and VRAM; use `scripts\download_asr.ps1`.
- Browser AudioContext sample rate is requested as 16 kHz; verify target Chrome honors it on the workstation.

## Next Chat Checklist

1. Read this file and `AGENTS.md`.
2. Run `git status --short --branch`.
3. Run tests and frontend build.
4. Check `/api/health` with backend and llama-server running.
5. Continue from the next concrete missing feature or failing check.
