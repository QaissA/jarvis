import numpy as np
from openwakeword.model import Model

from .vad import ensure_models


class WakeWord:
    def __init__(self, threshold: float):
        ensure_models()
        self.model = Model(wakeword_models=["hey_jarvis"], inference_framework="onnx")
        self.threshold = threshold

    def heard(self, frame: np.ndarray) -> bool:
        return max(self.model.predict(frame).values()) > self.threshold

    def reset(self) -> None:
        self.model.reset()
