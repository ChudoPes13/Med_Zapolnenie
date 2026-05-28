from __future__ import annotations

import numpy as np

from app.core.config import get_settings
from app.core.gpu import assert_gpu_ready


class ASRError(RuntimeError):
    pass


def pcm16_to_float32(pcm: bytes) -> np.ndarray:
    if len(pcm) % 2 != 0:
        raise ASRError("PCM16 buffer length must be even")
    samples = np.frombuffer(pcm, dtype=np.int16)
    return samples.astype(np.float32) / 32768.0


class FasterWhisperASR:
    def __init__(self) -> None:
        self.settings = get_settings()
        self._model = None

    def load(self) -> None:
        assert_gpu_ready(required=self.settings.gpu_required)
        from faster_whisper import WhisperModel

        self._model = WhisperModel(
            self.settings.asr_model,
            device=self.settings.asr_device,
            compute_type=self.settings.asr_compute_type,
        )

    def transcribe_pcm16(self, pcm: bytes) -> str:
        if self._model is None:
            self.load()
        audio = pcm16_to_float32(pcm)
        segments, _info = self._model.transcribe(
            audio,
            language=self.settings.asr_language,
            beam_size=1,
            vad_filter=False,
            condition_on_previous_text=False,
        )
        return " ".join(segment.text.strip() for segment in segments).strip()
