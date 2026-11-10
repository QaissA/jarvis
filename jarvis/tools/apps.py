import subprocess

from .registry import tool


@tool()
def open_app(name: str) -> str:
    """Open an application by name, for example Safari or Spotify."""
    subprocess.run(["open", "-a", name], check=True, capture_output=True)
    return f"Opened {name}"


@tool(confirm=True)
def close_app(name: str) -> str:
    """Close a running application by name."""
    # name goes in as argv, never spliced into the script
    subprocess.run(["osascript", "-e", "on run argv", "-e", "tell application (item 1 of argv) to quit",
                    "-e", "end run", name], check=True, capture_output=True)
    return f"Closed {name}"
