import subprocess
from pathlib import Path

from .registry import tool

allowed_folders: list[Path] = []  # set from config.yaml by main.py; empty means no file access


@tool()
def search_files(query: str) -> str:
    """Find files whose name contains the query. Returns up to five paths."""
    hits: list[str] = []
    for folder in allowed_folders:
        out = subprocess.run(["mdfind", "-onlyin", str(folder), "-name", query], capture_output=True, text=True)
        hits += out.stdout.splitlines()
    return "\n".join(hits[:5]) or "No files found"


@tool()
def open_file(path: str) -> str:
    """Open a file with its default application. Use a path returned by search_files."""
    p = Path(path).expanduser().resolve()  # resolve first so ../ and symlinks can't escape the allow-list
    if not any(p.is_relative_to(f) for f in allowed_folders):
        raise PermissionError("that file is outside the allowed folders")
    subprocess.run(["open", str(p)], check=True, capture_output=True)
    return f"Opened {p.name}"
