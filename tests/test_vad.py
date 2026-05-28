import numpy as np

from app.services.vad import EnergyVADState


def frame(amplitude: float, ms: int = 100, sample_rate: int = 16000) -> bytes:
    count = int(sample_rate * ms / 1000)
    samples = (np.ones(count, dtype=np.float32) * amplitude * 32767).astype(np.int16)
    return samples.tobytes()


def test_energy_vad_detects_speech_end_after_silence():
    vad = EnergyVADState(silence_ms=300, min_speech_ms=200)
    assert vad.accept_pcm16(frame(0.1)).speech_started
    assert not vad.accept_pcm16(frame(0.1)).speech_ended
    assert not vad.accept_pcm16(frame(0.0)).speech_ended
    assert not vad.accept_pcm16(frame(0.0)).speech_ended
    assert vad.accept_pcm16(frame(0.0)).speech_ended
    assert len(vad.pop_utterance()) > 0
