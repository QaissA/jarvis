import subprocess
import sys
import tempfile
import threading
from pathlib import Path

import sounddevice as sd
from piper import PiperVoice
from piper.phonemize_espeak import ESPEAK_DATA_DIR


class TTS:
    def __init__(self, voice_path: str):
        p = Path(voice_path)
        if not p.exists():  # one-time voice download
            subprocess.run([sys.executable, "-m", "piper.download_voices", p.stem,
                            "--download-dir", str(p.parent)], check=True)
        data = ESPEAK_DATA_DIR
        if len(str(data)) > 150:  # espeak-ng keeps this path in a 160-char buffer and aborts the process past it
            data = Path(tempfile.gettempdir()) / "jarvis-espeak"
            if not data.exists():
                data.symlink_to(ESPEAK_DATA_DIR)
        self.voice = PiperVoice.load(p, espeak_data_dir=data)
        self.lock = threading.Lock()  # a timer firing mid-reply must not talk over it

    def speak(self, text: str) -> None:
        with self.lock:
            # Piper yields one chunk per sentence, so the first sentence plays while the rest synthesises
            for chunk in self.voice.synthesize(text):
                sd.play(chunk.audio_int16_array, chunk.sample_rate)
                sd.wait()
