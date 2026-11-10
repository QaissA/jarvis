import queue

import numpy as np
import sounddevice as sd

RATE = 16000
FRAME = 1280  # 80 ms, the chunk size openWakeWord expects


class Mic:
    def __init__(self):
        self.q: queue.Queue[np.ndarray] = queue.Queue()
        self.stream = sd.InputStream(samplerate=RATE, channels=1, dtype="int16", blocksize=FRAME,
                                     callback=lambda data, *_: self.q.put(data[:, 0].copy()))
        self.stream.start()

    def read(self) -> np.ndarray:
        return self.q.get()

    def flush(self) -> None:
        """Drop everything heard so far, e.g. Jarvis's own voice."""
        while not self.q.empty():
            self.q.get_nowait()
