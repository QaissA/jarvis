from jarvis.brain.prompts import SYSTEM_PROMPT
from jarvis.config import Config

from .store import Store


def build_messages(cfg: Config, store: Store, user_text: str) -> list[dict]:
    system = SYSTEM_PROMPT.format(name=cfg.user_name)
    # shortcut: injects the 30 newest facts instead of matching by relevance,
    # switch to embeddings (ChromaDB) past ~100 facts
    if facts := store.facts():
        system += "\n\nThings you know about the user:\n" + "\n".join(f"- {f}" for f in facts)
    return [{"role": "system", "content": system}, *store.recent(cfg.history_turns),
            {"role": "user", "content": user_text}]
