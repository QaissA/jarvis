from jarvis.memory.store import Store

from .registry import tool

store: Store | None = None  # set by main.py


@tool()
def remember(fact: str) -> str:
    """Save a fact about the user for future conversations."""
    store.add_fact(fact)
    return "Saved"


@tool()
def recall(query: str) -> str:
    """Look up saved facts about the user matching the query."""
    return "\n".join(store.search(query)) or "Nothing saved about that"
