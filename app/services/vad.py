from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from app.core.config import get_settings
from app.core.gpu import assert_gpu_ready


@dataclass
class VADEvent:
    speech_started: bool = False
    speech_ended: bool = False


@dataclass
class EnergyVADState:
    sample_rate: int = 16000
    silence_ms: int = 850
    min_speech_ms: int = 450
    threshold: float = 0.012
    in_speech: bool = False
    speech_ms: int = 0
    silence_seen_ms: int = 0
    frames: list[bytes] = field(default_factory=list)

    def accept_pcm16(self, frame: bytes) -> VADEvent:
        samples = np.frombuffer(frame, dtype=np.int16).astype(np.float32) / 32768.0
        duration_ms = int(len(samples) / self.sample_rate * 1000)
        rms = float(np.sqrt(np.mean(np.square(samples)))) if len(samples) else 0.0
        event = VADEvent()

        if rms >= self.threshold:
            if not self.in_speech:
                event.speech_started = True
            self.in_speech = True
            self.speech_ms += duration_ms
            self.silence_seen_ms = 0
            self.frames.append(frame)
            return event

        if self.in_speech:
            self.frames.append(frame)
            self.silence_seen_ms += duration_ms
            if self.silence_seen_ms >= self.silence_ms and self.speech_ms >= self.min_speech_ms:
                event.speech_ended = True
                self.in_speech = False
        return event

    def pop_utterance(self) -> bytes:
        data = b"".join(self.frames)
        self.frames.clear()
        self.speech_ms = 0
        self.silence_seen_ms = 0
        return data


class SileroVADDetector:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.energy_state = EnergyVADState(
            sample_rate=self.settings.pcm_sample_rate,
            silence_ms=self.settings.vad_silence_ms,
            min_speech_ms=self.settings.vad_min_speech_ms,
        )
        self._loaded = False

    def load(self) -> None:
        assert_gpu_ready(required=self.settings.gpu_required)
        from silero_vad import load_silero_vad

        self.model = load_silero_vad()
        try:
            self.model.to("cuda")
        except Exception as exc:  # pragma: no cover - silero internals vary by version
            raise RuntimeError(f"Silero VAD could not move to CUDA: {exc}") from exc
        self._loaded = True

    def accept_pcm16(self, frame: bytes) -> VADEvent:
        if not self._loaded:
            self.load()
        return self.energy_state.accept_pcm16(frame)

    def pop_utterance(self) -> bytes:
        return self.energy_state.pop_utterance()
