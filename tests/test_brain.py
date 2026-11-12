import pytest

from jarvis.brain.agent import Agent
from jarvis.brain.llm import Response, ToolCall
from jarvis.config import Config
from jarvis.memory.store import Store
from jarvis.tools import files, memory_tools, registry

registry.load(Config().tool_modules)


class FakeLLM:
    """Replays scripted responses and records what it was sent."""
    def __init__(self, *script):
        self.script, self.seen = list(script), []

    def chat(self, messages, tools):
        self.seen.append([dict(m) for m in messages])
        return self.script.pop(0) if len(self.script) > 1 else self.script[0]


def agent(llm, store=None, confirm=lambda q: True):
    store = store or Store(":memory:")
    memory_tools.store = store
    return Agent(llm, Config(), store, confirm)


def test_schema_from_hints_and_docstring():
    f = registry.TOOLS["set_timer"].schema["function"]
    assert f["description"].startswith("Set a timer")
    assert f["parameters"]["properties"] == {"minutes": {"type": "number"}, "label": {"type": "string"}}
    assert f["parameters"]["required"] == ["minutes"]


def test_tool_result_is_fed_back():
    llm = FakeLLM(Response(tool_calls=[ToolCall("get_time", {})]), Response("It is noon."))
    assert agent(llm).reply("time?") == "It is noon."
    tool_msg = llm.seen[1][-1]
    assert tool_msg["role"] == "tool" and ":" in tool_msg["content"]


def test_five_round_limit():
    llm = FakeLLM(Response(tool_calls=[ToolCall("get_time", {})]))  # never stops calling tools
    assert "stuck" in agent(llm).reply("loop")
    assert len(llm.seen) == 5


def test_errors_and_unknown_tools_do_not_crash():
    assert registry.call("nope", {}, None).startswith("Error")
    assert registry.call("set_timer", {"minutes": -1}, None).startswith("Error")
    assert registry.call("open_url", {"url": "file:///etc/passwd"}, None).startswith("Error")


def test_confirm_tools_ask_first(monkeypatch):
    ran = []
    monkeypatch.setattr("subprocess.run", lambda *a, **k: ran.append(a))
    asked = []
    assert registry.call("close_app", {"name": "Spotify"}, lambda q: asked.append(q)) == "Cancelled by the user."
    assert asked == ["Should I close app Spotify?"] and not ran
    assert registry.call("close_app", {"name": "Spotify"}, lambda q: True) == "Closed Spotify"


def test_file_allow_list(tmp_path, monkeypatch):
    monkeypatch.setattr(files, "allowed_folders", [tmp_path.resolve()])
    assert "outside" in registry.call("open_file", {"path": str(tmp_path / ".." / "x")}, None)
    assert "outside" in registry.call("open_file", {"path": "/etc/passwd"}, None)


def test_memory_survives_restart(tmp_path):
    db = str(tmp_path / "j.db")
    llm = FakeLLM(Response(tool_calls=[ToolCall("remember", {"fact": "Sister is Salma"})]), Response("Noted."))
    agent(llm, Store(db)).reply("my sister's name is Salma")

    llm2 = FakeLLM(Response("Salma."))
    agent(llm2, Store(db)).reply("who is my sister?")  # new Store = a restart
    sent = llm2.seen[0]
    assert "Sister is Salma" in sent[0]["content"]           # fact injected into the system prompt
    assert sent[1]["content"] == "my sister's name is Salma"  # history carried over
    assert registry.call("recall", {"query": "sister"}, None) == "Sister is Salma"


def test_ask_claude_sends_question_on_stdin_with_no_tools(monkeypatch):
    from types import SimpleNamespace
    seen = {}

    def fake_run(cmd, **kw):
        seen.update(cmd=cmd, **kw)
        return SimpleNamespace(returncode=0, stdout="Forty-two.\n", stderr="")

    monkeypatch.setattr("subprocess.run", fake_run)
    assert registry.call("ask_claude", {"question": "--help; meaning of life?"}, None) == "Forty-two."
    assert seen["input"] == "--help; meaning of life?" and "--help; meaning of life?" not in seen["cmd"]
    assert seen["cmd"][seen["cmd"].index("--tools") + 1] == ""

    monkeypatch.setattr("subprocess.run", lambda *a, **k: SimpleNamespace(returncode=1, stdout="", stderr="not logged in"))
    assert registry.call("ask_claude", {"question": "hi"}, None) == "Error: not logged in"


def test_local_model_failure_is_an_apology_not_a_crash():
    class Down:
        def chat(self, messages, tools):
            raise ConnectionError("ollama is down")
    assert "local model" in agent(Down()).reply("hi")


def claude_brain(confirm, fallback=None):
    from jarvis.brain.claude import ClaudeBrain
    return ClaudeBrain(Config(), Store(":memory:"), confirm, fallback)


def test_claude_gate_asks_before_risky_actions(tmp_path, monkeypatch):
    import asyncio
    from pathlib import Path
    asked = []
    brain = claude_brain(lambda q, detail="": asked.append((q, detail)) or False)
    gate = lambda name, args: asyncio.run(brain.gate(name, args)).behavior
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    assert gate("Write", {"file_path": str(tmp_path / "new.txt")}) == "allow" and not asked  # new file at home
    (tmp_path / "old.txt").write_text("keep me")
    assert gate("Write", {"file_path": str(tmp_path / "old.txt")}) == "deny"  # overwrite: asked, user said no
    assert gate("Write", {"file_path": "/etc/new.txt"}) == "deny"  # outside home
    assert gate("Bash", {"command": "rm -rf x", "description": "delete x"}) == "deny"
    assert asked[-1] == ("I want to delete x. Shall I go ahead?", "rm -rf x")
    brain.confirm = lambda q, detail="": True
    assert gate("Bash", {"command": "rm -rf x"}) == "allow"
    assert gate("mcp__claude-in-chrome__computer", {}) == "allow" and brain.browser_ok


def test_claude_failure_falls_back_to_local_model(monkeypatch):
    brain = claude_brain(lambda q: True, fallback=agent(FakeLLM(Response("local answer"))))
    async def boom(text):
        raise RuntimeError("offline")
    monkeypatch.setattr(brain, "_ask", boom)
    assert brain.reply("hi") == "local answer"


def test_registry_tools_are_offered_to_claude_except_ask_claude():
    from jarvis.brain.claude import _jarvis_tools
    names = [t.name for t in _jarvis_tools(lambda q: True)]
    assert "set_timer" in names and "remember" in names and "ask_claude" not in names


def test_image_src(tmp_path):
    from jarvis.app import image_src
    (tmp_path / "a.png").write_bytes(b"png")
    assert image_src("https://x.org/a.png") == "https://x.org/a.png"
    assert image_src(str(tmp_path / "a.png")) == "data:image/png;base64,cG5n"
    assert image_src(str(tmp_path / "missing.png")) == "" and image_src("/etc/hosts") == ""
