"""Desktop window for Jarvis: `python -m jarvis.app`. Voice mode plus a transcript and a text box."""
import json
import queue
import threading
import traceback
from pathlib import Path

import webview

from jarvis import config
from jarvis.main import build_agent
from jarvis.orchestrator import run

_inbox: queue.Queue[str] = queue.Queue()  # module-level: pywebview walks the Api object's attributes


class Api:
    """Methods the page can call as window.pywebview.api.*"""

    def say(self, text: str) -> None:
        if text := str(text).strip()[:500]:
            _inbox.put(text)

    def listen(self) -> None:
        _inbox.put("")


def main() -> None:
    window = webview.create_window("Jarvis", str(Path(__file__).with_name("ui.html")), js_api=Api(),
                                   width=420, height=680, min_size=(340, 480), background_color="#0b0f14")

    def emit(kind: str, text: str) -> None:
        window.evaluate_js(f"onEvent({json.dumps(kind)}, {json.dumps(text)})")

    def worker() -> None:
        window.events.loaded.wait()
        try:
            run(config.load(), build_agent, emit=emit, inbox=_inbox)
        except Exception as e:  # show startup failures (Ollama down, no mic) in the window, not just a log
            traceback.print_exc()
            emit("state", "ERROR")
            emit("jarvis", f"I could not start: {e}")

    threading.Thread(target=worker, daemon=True).start()
    webview.start()  # blocks on the main thread until the window closes


if __name__ == "__main__":
    main()
