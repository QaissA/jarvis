import subprocess
import threading
from typing import Callable

from .registry import tool


def _notify(message: str) -> None:
    subprocess.run(["osascript", "-e", "on run argv", "-e",
                    'display notification (item 1 of argv) with title "Jarvis" sound name "Glass"',
                    "-e", "end run", message])


on_fire: Callable[[str], None] = _notify  # voice mode swaps in a function that also speaks


@tool()
def set_timer(minutes: float, label: str = "timer") -> str:
    """Set a timer that alerts the user after the given number of minutes."""
    if minutes <= 0:
        raise ValueError("minutes must be positive")
    # shortcut: timers live in memory and die with the process, persist to SQLite if that bites
    t = threading.Timer(minutes * 60, lambda: on_fire(f"Your {label} is done."))
    t.daemon = True
    t.start()
    return f"Timer set for {minutes:g} minutes"
