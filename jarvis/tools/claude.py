import subprocess
import tempfile
from typing import Callable

from .registry import tool

announce: Callable[[str], None] = lambda text: None  # voice mode swaps in speech: Claude takes several seconds

_STYLE = ("Your answer will be read aloud by a voice assistant. "
          "Answer in one to three short spoken sentences, with no markdown, lists or emoji.")


@tool()
def ask_claude(question: str) -> str:
    """Ask Claude, a far smarter online AI, a question that needs deep reasoning or knowledge you lack.
    Slow and limited: use it only for hard questions, never for small talk or things another tool does."""
    announce("Let me ask Claude.")
    # Question goes in on stdin; no tools, no user settings or hooks, no saved session, neutral folder:
    # a plain question-and-answer call on the Claude Code login (Pro plan), not the paid API.
    out = subprocess.run(
        ["claude", "-p", "--model", "sonnet", "--tools", "", "--strict-mcp-config", "--setting-sources", "",
         "--no-session-persistence", "--system-prompt", _STYLE],
        input=question, capture_output=True, text=True, timeout=120, cwd=tempfile.gettempdir())
    if out.returncode:
        raise RuntimeError(out.stderr.strip() or out.stdout.strip() or "Claude did not answer")
    return out.stdout.strip()
