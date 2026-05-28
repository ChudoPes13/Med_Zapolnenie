# Dialog Processing Instructions

## Purpose

This file defines how MedJarvis must process medical dialogue so it fills EMK fields truthfully, avoids hallucinated profile data, and separates realtime checks from final visit summarization.

## Core Rules

- Never invent data. If the dialogue does not contain a fact, leave the field empty and create a quality finding.
- Treat every VAD speech end as one segment. A segment updates facts and runs current quality checks.
- Treat recording stop or `finalize` as the end of the visit. Finalization builds a summary from all segments and runs full quality checks.
- Classify the visit profile from explicit context:
  - `general`: default profile.
  - `lower_limb`: words like `нижние конечности`, `нога`, `голень`, `стопа`, `бедро`, `колено`.
  - `dental`: explicit words like `зуб`, `кариес`, `ЭОД`, `FDI`, `одонтограмма`.
- Do not infer dental fields from numbers without dental context. `17 лет`, `36 лет`, `размер обуви 36`, dates, blood pressure, dose, and room numbers are not FDI teeth.
- Filler phrases such as `привет`, `как меня слышно`, `спасибо`, `ну ладно`, `медленно` must not create complaints or diagnoses.
- LLM output is treated as a proposal. Rule-based context guards can remove unsafe fields from it.

## Segment Processing

1. Receive PCM16 mono 16 kHz audio from the browser.
2. VAD detects speech start/end.
3. On speech end, ASR returns a text segment.
4. The segment is appended to transcript history.
5. Deterministic extractors run first:
   - general complaints and age,
   - lower-limb fields,
   - dental fields only with explicit dental context.
6. Local LLM may propose additional structure through `llama-server`.
7. Sanitizer removes profile-inconsistent fields, especially dental hallucinations.
8. EMK patch is merged into the visit state.
9. Quality checker runs with `final=false`.
10. UI updates EMK sections, risks, and evidence stubs.

## Final Processing

1. Doctor stops recording or presses `Завершить`.
2. Backend calls `finalize_visit`.
3. The system builds `final_summary` from all transcript segments and current EMK facts.
4. Quality checker runs with `final=true`.
5. Summary and final findings are stored in audit trail.
6. Doctor reviews and confirms.
7. Export is enabled only after doctor confirmation.

## Three Ideal Scenarios

### Scenario A: Segment-First Realtime Assistant

This is the recommended MVP path.

- Every VAD segment updates the EMK immediately.
- Missing fields appear while the doctor is still speaking.
- Finalization only summarizes and validates the complete visit.
- Best for live clinical support and low-friction doctor workflow.

### Scenario B: Final-Only Protocol Generator

This is the classic dictation workflow.

- Audio is collected during the visit.
- EMK is generated only after stop.
- Lower realtime complexity, but no live prompts.
- Best as fallback when realtime ASR or VAD is unstable.

### Scenario C: Form-Locked Clinical Interview

This is a strict checklist mode.

- The form drives the dialogue.
- The system asks or highlights one required field at a time.
- Highest legal completeness, but most intrusive for the doctor.
- Best for narrow protocols, high-risk visits, or training.

## Scenario Comparison

| Metric | A: Segment-First | B: Final-Only | C: Form-Locked |
|---|---:|---:|---:|
| Realtime field latency target | 1.5-4.0 s after VAD end | not applicable | 1.0-3.0 s |
| Final document latency target | 5-20 s | 15-60 s | 5-25 s |
| Doctor interruption level | low | none during visit | medium-high |
| Missing-field detection during visit | high | none | very high |
| Risk of premature wrong field | medium | low | low-medium |
| Risk of missed urgent clarification | low | high | very low |
| UI complexity | medium | low | high |
| Backend complexity | high | medium | high |
| Best first release fit | high | medium | medium |
| Best fallback fit | medium | high | low |
| Legal completeness potential | high | medium | very high |

## Detailed Test Statistics

Current synthetic coverage after the profile-aware fix:

| Test Group | Count | Purpose |
|---|---:|---|
| ASR configuration | 1 | Medical prompt, hotwords, and fast decode options are passed to Faster-Whisper |
| API lifecycle | 2 | Visit creation, segment processing, confirmation, export, finalize |
| Dialogue processing API | 1 | Segment-level complaint extraction, filler filtering, final summary |
| Synthetic truthfulness extraction | 8 | General, lower-limb, dental, age-vs-FDI, shoe-size-vs-FDI |
| Truthfulness guards | 4 | Profile-specific findings, LLM hallucination guard, non-object LLM output, rule precedence over LLM variants |
| Dental acceptance quality | 1 | Core dental findings turn resolved after required facts arrive |
| VAD state machine | 1 | Speech start/end behavior |
| Export/guidelines | 1 | Stub evidence and export content |
| Total pytest cases | 19 | Regression suite for current MVP behavior |

Truthfulness cases covered:

| Input Type | Expected Behavior |
|---|---|
| `жалуются на боли в животе` | complaint becomes `Боли в животе` |
| filler speech | no complaint created |
| `17 лет` | age is 17, no tooth |
| `36 лет` | age is 36, no tooth |
| `размер обуви 36` | no tooth |
| explicit `зуб 36` | tooth FDI 36 |
| lower-limb pulse phrase | lower-limb vascular field filled |
| LLM proposes tooth without context | dental patch is removed |
| LLM returns non-object JSON | LLM patch is ignored, deterministic extraction remains live |
| LLM returns lowercase duplicate complaint | normalized rule complaint stays first |

## Improvement Backlog

### Extraction Quality

- Add a medical phrase normalizer for Russian inflections: `боли`, `болей`, `болезненность`, `жалуется`, `жалобы`.
- Add negation scopes: `нет боли`, `отека нет`, `аллергию отрицает`.
- Add entity provenance: every field should store the source transcript segment id and confidence.
- Add conflict handling: if later speech contradicts earlier data, mark field as `needs_confirmation`.
- Add profile detector with confidence instead of hard switches.

### Realtime Pipeline

- Split ASR and clinical extraction into queues so ASR never blocks WebSocket reads.
- Add backpressure: drop or defer low-priority LLM tasks if GPU memory is tight.
- Keep deterministic extraction synchronous and run LLM refinement asynchronously.
- Add segment ids and timings from VAD to every transcript item.

### LLM and Prompting

- Use JSON schema constrained output for `llama-server` when supported.
- Add a two-pass LLM prompt: first extract facts, then map facts to EMK fields.
- Keep domain guardrails outside the LLM, as code, for high-risk fields.
- Benchmark `Qwen3-4B-Q4_K_M` versus `Qwen3-8B-Q4_K_M` on the synthetic truthfulness suite.

### Quality Checker

- Make required fields profile-specific through declarative form configs.
- Add severity policy: realtime hints are warnings, final missing legal fields are critical.
- Add age-specific filters and contraindication checks.
- Add KR evidence requirement per recommendation, not just per visit.

### UI

- Show field provenance on hover: transcript segment, timestamp, extractor source.
- Add a dedicated `Служебные фразы` lane so audio tests do not pollute EMK.
- Add explicit `Не относится к приему` action for transcript cleanup.
- Add final review mode that groups only unresolved blockers.

### Testing and Monitoring

- Expand synthetic dialogues to at least 100 cases per profile.
- Add mutation tests for misleading numbers: ages, doses, dates, room numbers, blood pressure.
- Add golden JSON snapshots for EMK states.
- Add latency metrics: VAD end -> transcript, transcript -> EMK patch, finalization duration.
- Add GPU memory metrics around ASR and LLM calls.
