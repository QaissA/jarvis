import numpy as np
from faster_whisper import WhisperModel


class STT:
    def __init__(self, model: str, language: str):
        self.model = WhisperModel(model, compute_type="int8")  # downloads on first use
        self.language = language

    def transcribe(self, audio: np.ndarray) -> str:
        """16 kHz int16 mono in, text out. Empty string if there was no speech."""
        if not len(audio):
            return ""
        segments, _ = self.model.transcribe(audio.astype(np.float32) / 32768, language=self.language,
                                            vad_filter=True)  # vad_filter stops Whisper inventing words in silence
        return " ".join(s.text.strip() for s in segments).strip()
