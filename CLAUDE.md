# Jarvis project rules
- Local voice assistant in Python 3.11+. Runs fully offline.
- LLM: Ollama (model from config.yaml) via brain/llm.py only.
- One responsibility per module.
- audio/ must never import brain/, and brain/ must never import audio/.
- Every tool: type hints, docstring, returns str. registry.call catches errors.
- Destructive tools use @tool(confirm=True).
- Add a pytest test for every new function.
- Keep replies spoken-style: short, no markdown.
- Run: `uv run python -m jarvis.main --text` · Test: `uv run pytest`
