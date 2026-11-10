"""Background listener: opens Jarvis.app when it hears "Hey Jarvis". Started at login by install-listener.sh."""
import logging
import subprocess
import time
from pathlib import Path

from jarvis import config
from jarvis.audio.mic import Mic
from jarvis.audio.wakeword import WakeWord

log = logging.getLogger("jarvis.listener")
APP = Path(__file__).resolve().parents[1] / "Jarvis.app"


def app_running() -> bool:
    return subprocess.run(["pgrep", "-f", "jarvis.app"], capture_output=True).returncode == 0


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S")
    mic, wake = Mic(), WakeWord(config.load().wake_threshold)
    if mic.is_silent():
        log.warning("microphone is silent: allow JarvisListener under System Settings > Privacy & Security > Microphone")
    log.info("listening for Hey Jarvis")
    while True:
        # while the app is open it handles the wake word itself; don't yank its window to the front
        if wake.heard(mic.read()) and not app_running():
            log.info("wake word heard: opening Jarvis")
            subprocess.run(["open", str(APP)])
            time.sleep(5)  # let the app start before listening again
            mic.flush()
            wake.reset()


if __name__ == "__main__":
    main()
