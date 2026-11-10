from typing import Callable

import numpy as np
from openwakeword.utils import download_models
from openwakeword.vad import VAD

from .mic import RATE


def ensure_models() -> None:
    download_models(["hey_jarvis"])  # one-time: wake word + the Silero VAD it bundles; skips existing files


class EndOfSpeech:
    def __init__(self):
        ensure_models()
        self.vad = VAD()

    def record(self, read: Callable[[], np.ndarray], silence_s: float, max_s: float,
               start_timeout_s: float) -> np.ndarray:
        """Record until silence_s of quiet follows speech. Empty if nobody speaks in time."""
        frames, started, quiet, t = [], False, 0.0, 0.0
        while t < max_s:
            frame = read()
            frames.append(frame)
            dt = len(frame) / RATE
            t += dt
            if self.vad.predict(frame, frame_size=640) > 0.5:
                started, quiet = True, 0.0
            elif started:
                quiet += dt
                if quiet >= silence_s:
                    break
            elif t >= start_timeout_s:
                return np.zeros(0, np.int16)
        return np.concatenate(frames)
