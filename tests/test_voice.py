"""Round trip without a microphone: Piper speaks, then wake word, VAD and Whisper hear it.
Skipped unless the voice extra is installed. Downloads the models on first run."""
import numpy as np
import pytest

pytest.importorskip("piper")
pytest.importorskip("openwakeword")

from jarvis.audio.mic import FRAME, RATE
from jarvis.audio.stt import STT
from jarvis.audio.tts import TTS
from jarvis.audio.vad import EndOfSpeech
from jarvis.audio.wakeword import WakeWord
from jarvis.config import Config

cfg = Config()


def spoken(text: str) -> list[np.ndarray]:
    """Synthesise text, resample to mic rate, pad with silence, cut into mic-sized frames."""
    chunks = list(TTS(cfg.piper_voice).voice.synthesize(text))
    audio = np.concatenate([c.audio_int16_array for c in chunks]).astype(np.float32)
    n = int(len(audio) * RATE / chunks[0].sample_rate)
    audio = np.interp(np.linspace(0, len(audio) - 1, n), np.arange(len(audio)), audio).astype(np.int16)
    audio = np.concatenate([np.zeros(RATE, np.int16), audio, np.zeros(RATE * 2, np.int16)])
    return [audio[i:i + FRAME] for i in range(0, len(audio) - FRAME, FRAME)]


def test_wake_word_fires_on_hey_jarvis_only():
    wake = WakeWord(cfg.wake_threshold)
    assert any(wake.heard(f) for f in spoken("Hey Jarvis."))
    wake.reset()
    assert not any(wake.heard(f) for f in spoken("What a lovely day for a walk."))


def test_record_stops_on_silence_and_transcribes():
    frames = spoken("What time is it?")
    it = iter(frames)
    audio = EndOfSpeech().record(lambda: next(it), cfg.silence_seconds, cfg.max_record_seconds, 5)
    assert 0 < len(audio) < len(frames) * FRAME  # stopped before the trailing silence ran out
    assert "time" in STT("base.en", "en").transcribe(audio).lower()


def test_silence_times_out_empty():
    vad = EndOfSpeech()
    assert len(vad.record(lambda: np.zeros(FRAME, np.int16), 0.8, 15, 1)) == 0
