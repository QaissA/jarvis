from typing import Callable

from jarvis.config import Config
from jarvis.memory.context import build_messages
from jarvis.memory.store import Store
from jarvis.tools import registry

from .llm import LLMClient


class Agent:
    def __init__(self, llm: LLMClient, cfg: Config, store: Store, confirm: Callable[[str], bool]):
        self.llm, self.cfg, self.store, self.confirm = llm, cfg, store, confirm

    def reply(self, user_text: str) -> str:
        messages = build_messages(self.cfg, self.store, user_text)
        text = "Sorry, I got stuck on that one."
        for _ in range(self.cfg.max_tool_rounds):  # hard cap: a confused model can't loop forever
            try:
                r = self.llm.chat(messages, registry.schemas())
            except Exception:  # Ollama down or restarting must not kill the voice loop
                text = "Sorry, I can't reach my local model."
                break
            if not r.tool_calls:
                text = r.text.strip() or text
                break
            messages.append({"role": "assistant", "content": r.text, "tool_calls": [
                {"function": {"name": c.name, "arguments": c.arguments}} for c in r.tool_calls]})
            for c in r.tool_calls:
                messages.append({"role": "tool", "tool_name": c.name,
                                 "content": registry.call(c.name, c.arguments, self.confirm)})
        self.store.add_turn("user", user_text)
        self.store.add_turn("assistant", text)
        return text
