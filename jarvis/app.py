"""Desktop window for Jarvis: `python -m jarvis.app`. Voice mode plus a transcript and a text box."""
import base64
import json
import mimetypes
import queue
import threading
import traceback
from pathlib import Path

import AppKit
import webview
from PyObjCTools import AppHelper

from jarvis import config
from jarvis.main import build_agent
from jarvis.orchestrator import run
from jarvis.tools.system import stats

_inbox: queue.Queue[str] = queue.Queue()  # module-level: pywebview walks the Api object's attributes
_pill: list = []  # the status pill window, once it exists

# The pill: a small always-on-top status light for when the dashboard is not on screen.
PILL_W, PILL_H = 176, 36
PILL = """<body style="margin:0;background:transparent;overflow:hidden">
<div style="height:36px;border-radius:18px;background:#05090fea;color:#d9ecf7;display:flex;align-items:center;gap:10px;
            padding:0 16px;font:600 11px ui-monospace,Menlo,monospace;letter-spacing:.22em">
  <i id="dot" style="width:9px;height:9px;border-radius:50%;flex:none"></i><span id="state"></span></div>
<script>
  const COLORS = { IDLE: "#5ad7ff", LISTENING: "#3dffb0", TRANSCRIBING: "#3dffb0", THINKING: "#ffc247",
                   SPEAKING: "#c9a0ff", ERROR: "#ff5d6c" };
  function set(state) {
    document.getElementById("state").textContent = state;
    const dot = document.getElementById("dot");
    dot.style.background = COLORS[state] || "#6b7f90";
    dot.style.boxShadow = "0 0 8px " + dot.style.background;
  }
  set("STARTING");
</script>"""


def make_pill():
    """Create the status pill: bottom right of the screen, on every Space, above full-screen apps, click-through."""
    pill = webview.create_window("Jarvis status", html=PILL, width=PILL_W, height=PILL_H, frameless=True, on_top=True,
                                 transparent=True, focus=False, resizable=False, shadow=False, min_size=(PILL_W, PILL_H))

    def dock() -> None:
        area = AppKit.NSScreen.mainScreen().visibleFrame()  # excludes the Dock and menu bar
        native = pill.native
        native.setFrameOrigin_((area.origin.x + area.size.width - PILL_W - 16, area.origin.y + 16))
        native.setIgnoresMouseEvents_(True)
        native.setCollectionBehavior_(AppKit.NSWindowCollectionBehaviorCanJoinAllSpaces
                                      | AppKit.NSWindowCollectionBehaviorStationary
                                      | AppKit.NSWindowCollectionBehaviorFullScreenAuxiliary)

    pill.events.shown += lambda: AppHelper.callAfter(dock)
    return pill


class Api:
    """Methods the page can call as window.pywebview.api.*"""

    def say(self, text: str) -> None:
        if text := str(text).strip()[:500]:
            _inbox.put(text)

    def listen(self) -> None:
        _inbox.put("")

    def stats(self) -> dict:
        cfg = config.load()
        return {**stats(), "model": f"claude · {cfg.claude_model}" if cfg.brain == "claude" else f"local · {cfg.model}"}

    def focused(self, yes: bool) -> None:
        """The dashboard gained or lost focus: the pill is only needed while it is out of sight."""
        for pill in _pill:
            AppHelper.callAfter(pill.native.setAlphaValue_, 0.0 if yes else 1.0)

    def close(self) -> None:
        webview.windows[0].destroy()


def image_src(src: str) -> str:
    """What the page can load: web addresses as they are, a local picture as a data URI. Empty if it is neither."""
    if src.startswith(("http://", "https://")):
        return src
    p = Path(src.removeprefix("file://")).expanduser()
    mime = mimetypes.guess_type(p.name)[0] or ""
    if not mime.startswith("image/") or not p.is_file() or p.stat().st_size > 8_000_000:
        return ""
    return f"data:{mime};base64,{base64.b64encode(p.read_bytes()).decode()}"


def main() -> None:
    window = webview.create_window("Jarvis", str(Path(__file__).with_name("ui.html")), js_api=Api(),
                                   width=1000, height=620, min_size=(760, 500), background_color="#05090f",
                                   fullscreen=True)  # native full screen: no title bar, menu bar or Dock

    pill = make_pill()
    _pill.append(pill)
    window.events.closed += pill.destroy  # or the hidden pill would keep the app alive

    def emit(kind: str, text: str) -> None:
        if kind == "state":
            pill.evaluate_js(f"set({json.dumps(text)})")
        if kind == "image" and not (text := image_src(text)):
            return
        window.evaluate_js(f"onEvent({json.dumps(kind)}, {json.dumps(text)})")

    def worker() -> None:
        window.events.loaded.wait()
        pill.events.loaded.wait()
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
