"""Claude as the brain, through the Claude Code login (Agent SDK). It brings its own shell, file and web tools;
Jarvis adds its registry tools and answers the permission prompts by asking the user."""
import asyncio
import logging
import warnings
from pathlib import Path
from typing import Callable

from claude_agent_sdk import (ClaudeAgentOptions, ClaudeSDKClient, PermissionResultAllow, PermissionResultDeny,
                              ResultMessage, create_sdk_mcp_server, tool)

from jarvis.config import Config
from jarvis.memory.context import build_messages
from jarvis.memory.store import Store
from jarvis.tools import registry

from .prompts import CLAUDE_PROMPT

log = logging.getLogger("jarvis.claude")
warnings.filterwarnings("ignore", message="can_use_tool will not be invoked")  # the SAFE list skips it on purpose

# Run without asking: reading, searching, opening things, Jarvis's own tools (the registry confirms its destructive ones).
# Everything else (other shell commands, edits, browser actions) goes through ClaudeBrain.gate.
_READ_ONLY = "ls cat head tail wc file stat pwd date whoami which open mdfind mdls df ps pmset sw_vers"
SAFE = ["Read", "Glob", "Grep", "WebSearch", "WebFetch", "mcp__jarvis", *(f"Bash({c}:*)" for c in _READ_ONLY.split()),
        *(f"mcp__claude-in-chrome__{t}" for t in ("tabs_context_mcp", "tabs_create_mcp", "navigate", "read_page",
                                                  "get_page_text", "find"))]


def _jarvis_tools(confirm: Callable[..., bool]) -> list:
    def wrap(f: dict):
        @tool(f["name"], f["description"], f["parameters"])
        async def run(args: dict) -> dict:
            text = await asyncio.to_thread(registry.call, f["name"], args, confirm)
            return {"content": [{"type": "text", "text": text}]}
        return run
    return [wrap(fn.schema["function"]) for name, fn in registry.TOOLS.items() if name != "ask_claude"]


class ClaudeBrain:
    def __init__(self, cfg: Config, store: Store, confirm: Callable[..., bool], fallback):
        self.cfg, self.store, self.confirm, self.fallback = cfg, store, confirm, fallback
        self.session: str | None = None  # shortcut: the conversation is forgotten on restart, persist the id if that bites
        self.browser_ok = False

    def reply(self, user_text: str) -> str:
        self.browser_ok = False
        try:
            text = asyncio.run(asyncio.wait_for(self._ask(user_text), self.cfg.claude_timeout))
        except Exception:  # offline, plan limit reached, timeout: the local model answers instead
            log.exception("Claude failed, falling back to the local model")
            return self.fallback.reply(user_text)
        self.store.add_turn("user", user_text)
        self.store.add_turn("assistant", text)
        return text

    async def gate(self, name: str, args: dict, _ctx=None):
        """Called for every tool call the SAFE list does not cover: allow it, or ask the user first."""
        path = Path(args.get("file_path") or "/")
        if name == "Write" and not path.exists() and path.resolve().is_relative_to(Path.home()):
            return PermissionResultAllow()  # a new file in the home folder destroys nothing
        browser = name.startswith("mcp__claude-in-chrome__")
        if browser and self.browser_ok:
            return PermissionResultAllow()  # one yes covers the browser steps of this request
        if name == "Bash":
            what, detail = args.get("description") or "run a command", args.get("command", "")
        elif browser:
            what, detail = "control your browser", ""
        else:
            what, detail = f"use {name}", str(args.get("file_path") or args)
        if await asyncio.to_thread(self.confirm, f"I want to {what}. Shall I go ahead?", detail[:300]):
            self.browser_ok = self.browser_ok or browser
            return PermissionResultAllow()
        return PermissionResultDeny(message="The user said no. Do not retry it another way.")

    async def _ask(self, user_text: str) -> str:
        options = ClaudeAgentOptions(
            model=self.cfg.claude_model,
            system_prompt=build_messages(self.cfg, self.store, "")[0]["content"] + CLAUDE_PROMPT,
            allowed_tools=SAFE, can_use_tool=self.gate, resume=self.session,
            mcp_servers={"jarvis": create_sdk_mcp_server("jarvis", tools=_jarvis_tools(self.confirm))},
            setting_sources=[],  # no user or project settings, hooks or CLAUDE.md: Jarvis is its own assistant
            extra_args={"chrome": None} if self.cfg.claude_chrome else {},
            cwd=str(Path.home()))
        async with ClaudeSDKClient(options) as client:
            await client.query(user_text)
            async for msg in client.receive_response():
                if isinstance(msg, ResultMessage):
                    if msg.is_error:
                        raise RuntimeError(msg.result or msg.subtype)
                    self.session = msg.session_id
                    return (msg.result or "").strip() or "Done."
        raise RuntimeError("Claude ended without an answer")
