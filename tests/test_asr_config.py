from types import SimpleNamespace

import numpy as np

from app.services.asr import FasterWhisperASR


class FakeWhisperModel:
    def __init__(self) -> None:
        self.kwargs = {}

    def transcribe(self, _audio, **kwargs):
        self.kwargs = kwargs
        return [SimpleNamespace(text=" тест")], SimpleNamespace()


def test_asr_passes_medical_prompt_and_fast_decoding_options():
    fake_model = FakeWhisperModel()
    asr = FasterWhisperASR()
    asr._model = fake_model

    pcm = np.zeros(1600, dtype=np.int16).tobytes()
    assert asr.transcribe_pcm16(pcm) == "тест"

    assert fake_model.kwargs["language"] == "ru"
    assert fake_model.kwargs["beam_size"] == 1
    assert fake_model.kwargs["best_of"] == 1
    assert fake_model.kwargs["temperature"] == 0.0
    assert fake_model.kwargs["vad_filter"] is False
    assert fake_model.kwargs["condition_on_previous_text"] is False
    assert "Медицинский прием" in fake_model.kwargs["initial_prompt"]
    assert "стоматология" in fake_model.kwargs["hotwords"]
