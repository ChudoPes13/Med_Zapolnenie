# MedJarvis Next Chat Context

Last updated: 2026-05-28.

## Repository

- Workspace: `C:\ai26\Med_Zapolnenie`
- GitHub remote: `https://github.com/ChudoPes13/Med_Zapolnenie.git`
- Branch: `main`
- Runtime target: Windows 11, Python 3.12, Node.js 22+, RTX 3070 8 GB, 16 GB RAM.
- Production rule: local-only PHI, GPU-only for ASR/LLM, no cloud calls.

## Current Architecture

- Backend: FastAPI + Uvicorn.
- Frontend: React/Vite.
- Runtime DB: SQLite `data/medjarvis.db`, gitignored.
- Audit trail: visits, transcript segments, EMK snapshots/findings/evidence/confirmations/exports.
- Realtime audio path: browser `AudioWorklet` -> PCM16 mono frames -> WebSocket `/ws/visits/{visit_id}/audio`.
- VAD: wrapper named `SileroVADDetector`, but current speech-end logic is energy-based after Silero loads on CUDA.
- ASR: `faster-whisper` with `large-v3-turbo`, language `ru`, CUDA, CTranslate2.
- Clinical extraction: deterministic rules first, optional local LLM proposal second.
- LLM: OpenAI-compatible local `llama-server` at `http://127.0.0.1:8080/v1`.
- Default LLM model file: `models\Qwen3-4B-Q4_K_M.gguf`.
- KR layer: stub provider for visible evidence contract; real BM25 KR DB is not connected yet.

## Startup

Preferred command after code changes:

```powershell
scripts\start_medjarvis.ps1 -Restart
```

This starts/restarts:

- `llama-server` on `127.0.0.1:8080`
- FastAPI backend on `127.0.0.1:8000`
- Vite frontend on `127.0.0.1:5173`

Logs are written to `logs\*.out.log` and `logs\*.err.log`.

Manual mode still exists:

```powershell
scripts\start_llama.ps1
scripts\start_backend.ps1
scripts\start_frontend.ps1
```

Important: refreshing the browser does not restart backend code. If UI shows stale behavior, run `scripts\start_medjarvis.ps1 -Restart`.

## Health

Check:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/health | ConvertTo-Json -Depth 5
```

Expected production state:

- `gpu.ok=true`
- `llm.ok=true`
- `llm.required=true`
- `asr.device="cuda"`
- `asr.preload=true`

The UI header also shows `GPU online` and `LLM online`.

## Current ASR / Whisper Settings

Config source: `app\core\config.py`, env prefix `MEDJARVIS_`.

Current defaults:

- `MEDJARVIS_ASR_MODEL=large-v3-turbo`
- `MEDJARVIS_ASR_LANGUAGE=ru`
- `MEDJARVIS_ASR_DEVICE=cuda`
- `MEDJARVIS_ASR_COMPUTE_TYPE=int8_float16`
- `MEDJARVIS_ASR_PRELOAD=true`
- `MEDJARVIS_ASR_BEAM_SIZE=1`
- `MEDJARVIS_ASR_BEST_OF=1`
- `MEDJARVIS_ASR_TEMPERATURE=0.0`
- `MEDJARVIS_ASR_CONDITION_ON_PREVIOUS_TEXT=false`
- `MEDJARVIS_ASR_INITIAL_PROMPT` defaults to a Russian medical visit prompt.
- `MEDJARVIS_ASR_HOTWORDS` defaults to medical, dental, lower-limb, and EMK terms.

Current `initial_prompt`:

```text
Медицинский прием на русском языке. Термины: жалобы, анамнез, объективно, диагноз, МКБ-10, артериальное давление, аллергия, стоматология, зуб, FDI, одонтограмма, перкуссия, термопроба, ЭОД, нижние конечности, стопа, голень, отек, пульс.
```

Current `hotwords`:

```text
жалобы анамнез объективно диагноз МКБ аллергия давление стоматология зуб FDI одонтограмма перкуссия термопроба ЭОД нижние конечности стопа голень отек пульс
```

Why these settings:

- `beam_size=1`, `best_of=1`, `temperature=0.0` prioritize latency and deterministic output.
- `condition_on_previous_text=false` avoids previous segment hallucinations bleeding into the next VAD segment.
- `initial_prompt` and `hotwords` bias Whisper toward Russian medical vocabulary.
- `vad_filter=false` because external VAD already segments audio.

## Current Realtime Issue

Observed by user: ASR/Whisper or downstream processing reacts slowly; first dictated text may not appear in `Диалог` until recording is stopped and a new recording starts.

Likely causes found in code:

- Whisper model was lazily loaded on the first `speech_ended`, so the first segment paid model load time.
- WebSocket sent transcript only after `processor.process_text`, which includes clinical extraction and may wait for local LLM.
- LLM can be slow on RTX 3070 when `llama-server` and Whisper share 8 GB VRAM.
- VAD waits `MEDJARVIS_VAD_SILENCE_MS=850` after speech stops before ASR begins.
- Chrome DevTools errors like `Unchecked runtime.lastError... message channel closed` are likely browser extension noise, not MedJarvis app errors.

Changes made for this issue:

- Backend preloads ASR model at startup with `MEDJARVIS_ASR_PRELOAD=true`.
- WebSocket now emits `transcript_segment` immediately after Whisper returns text, before LLM/quality processing finishes.
- Frontend appends `transcript_segment` to `Диалог` optimistically; later `segment_checked` replaces state with authoritative backend state.
- LLM non-object JSON is ignored instead of causing a 500.

Next fixes if latency remains high:

- Add timestamps/metrics for `speech_ended -> ASR text`, `ASR text -> LLM patch`, `LLM patch -> UI state`.
- Move clinical extraction/LLM into an async queue so ASR and UI transcript updates never wait for LLM.
- Consider lowering `MEDJARVIS_VAD_SILENCE_MS` from `850` to `500-650` after testing false splits.
- If VRAM is tight, benchmark `MEDJARVIS_ASR_COMPUTE_TYPE=int8` and reduce llama context/cache before reducing ASR quality.
- Add partial ASR mode only after stable segment-level behavior; partials increase complexity and false text churn.

## Clinical Logic Nuances

- Default profile is `general`.
- Dental profile activates only with explicit dental terms like `зуб`, `ЭОД`, `FDI`, `одонтограмма`, `кариес`.
- Lower-limb profile activates with terms like `нижние конечности`, `нога`, `голень`, `стопа`, `бедро`, `колено`.
- Numbers are not treated as FDI teeth without dental context. `17 лет`, `36 лет`, `размер обуви 36`, dates, BP, doses, and room numbers must not create `tooth_fdi`.
- Filler phrases such as `привет`, `как меня слышно`, `спасибо`, `ну ладно`, `медленно` should not create complaints.
- General complaint extraction supports phrases like `жалуется/жалуются/жалобы на ...`.
- LLM output is only a proposal. Code-level guards remove profile-inconsistent dental hallucinations.
- Deterministic rule values take precedence over duplicate LLM variants for list fields.

## UI Nuances

- Header focus label is derived from `emk.clinical_focus`.
- Right panel shows active and resolved quality findings.
- Exports are blocked until doctor confirmation.
- `НК пример` is a manual lower-limb test helper.
- `Завершить` calls finalization and final quality check.
- `WS offline` only means the audio WebSocket is not recording; manual text can still work.

## Tests

Use:

```powershell
$env:MEDJARVIS_GPU_REQUIRED='0'
$env:MEDJARVIS_REQUIRE_LLM='0'
.venv\Scripts\python.exe -m ruff check app tests
.venv\Scripts\python.exe -m pytest -q
cd frontend
npm run build
```

Current test areas:

- ASR config passes medical prompt, hotwords, and fast decode options.
- API lifecycle, confirmation, export lock.
- Dialogue processing: general complaint, filler ignore, finalize.
- Truthfulness: lower limbs, dentistry, age vs FDI, shoe size vs FDI.
- LLM guards: hallucinated dental patch removal, non-object JSON ignored, rule precedence.
- VAD state machine.
- KR stub and exports.

## Files To Read First In A New Chat

1. `AGENTS.md`
2. `docs\NEXT_CHAT_CONTEXT.md`
3. `docs\DIALOG_PROCESSING.md`
4. `docs\RUNBOOK.md`
5. `app\api\ws.py`
6. `app\services\asr.py`
7. `app\services\clinical.py`
8. `frontend\src\App.tsx`

## Latest Practical Acceptance Checks

Manual text:

- `жалуется на боли в передней челюсти.` should fill `Жалобы` and resolve `complaints.required`.
- `У пациента боль в нижних конечностях. Ему 17 лет.` should set age `17`, lower-limb focus, and no tooth.
- `Болит зуб 36, боль при накусывании, ЭОД 8 мкА.` should activate dental profile and set tooth `36`.

Realtime audio:

- Start with `scripts\start_medjarvis.ps1 -Restart`.
- Confirm UI shows `GPU online` and `LLM online`.
- Start mic, speak one short medical phrase, stop speaking.
- Expected event order: `speech_started`, `transcribing`, `transcript_segment`, then `segment_checked`.
- `Диалог` should update at `transcript_segment`, before EMK/quality finishes.
