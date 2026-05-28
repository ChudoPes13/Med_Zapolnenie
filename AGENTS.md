# МедЖарвис Agent Rules

## Goal

Build a local, production-oriented assistant for Russian dental visits. The first vertical is стоматология 043/у: realtime transcript, EMK sections, quality findings, KR evidence, doctor confirmation, and export.

## Hard Rules

- Keep PHI local. Do not add cloud LLM or telemetry paths.
- ASR and LLM production profiles are GPU-only. Startup must fail when GPU is required and unavailable.
- Live-write to MIS stays disabled until explicit doctor confirmation.
- Every export and confirmation records an audit event.
- Real KR retrieval is behind `GuidelinesProvider`; the v1 stub must stay visibly marked as `is_stub=true`.

## Commit Policy

Use milestone commits:

1. scaffold and environment
2. ASR/VAD realtime backend
3. clinical extraction, quality, KR
4. UI and exports
5. tests and docs

Push to `origin main` when credentials allow.

## Common Errors

- `torch.cuda.is_available() is false`: reinstall GPU requirements with `scripts\setup.ps1`.
- `llama-server returned invalid JSON`: lower temperature to 0 and keep deterministic rule overlay enabled.
- `doctor confirmation required before export`: press confirm in UI or call `/api/visits/{id}/confirm`.
- `Silero VAD could not move to CUDA`: check CUDA build and current VRAM pressure.

## New Chat Handoff

Read `docs/HANDOFF.md`, then run `git status --short --branch`, `scripts\gpu_health.ps1`, backend tests, and frontend build before editing.
