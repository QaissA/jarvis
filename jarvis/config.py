from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel


class Config(BaseModel, extra="forbid"):  # forbid: a typo in config.yaml fails at startup
    ollama_host: str = "http://localhost:11434"
    brain: Literal["claude", "ollama"] = "claude"  # claude falls back to the Ollama model when it fails
    claude_model: str = "sonnet"
    claude_timeout: float = 300  # seconds for one whole request, tool use included
    claude_chrome: bool = False  # drive Chrome through the Claude in Chrome extension
    model: str = "qwen3:8b"
    user_name: str = "sir"
    history_turns: int = 10
    max_tool_rounds: int = 5
    db_path: str = "data/jarvis.db"
    allowed_folders: list[str] = ["~/Documents", "~/Desktop", "~/Downloads"]
    tool_modules: list[str] = ["system", "apps", "timers", "web", "memory_tools", "files", "claude"]
    whisper_model: str = "small"
    language: str = "en"
    piper_voice: str = "models/en_GB-alan-medium.onnx"
    wake_threshold: float = 0.5
    silence_seconds: float = 0.8
    max_record_seconds: float = 15
    followup_seconds: float = 5


def load(path: str = "config.yaml") -> Config:
    p = Path(path)
    return Config(**(yaml.safe_load(p.read_text()) or {} if p.exists() else {}))
