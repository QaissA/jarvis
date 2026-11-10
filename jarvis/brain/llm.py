from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class ToolCall:
    name: str
    arguments: dict


@dataclass
class Response:
    text: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)


class LLMClient(Protocol):
    def chat(self, messages: list[dict], tools: list[dict]) -> Response: ...


class OllamaClient:
    def __init__(self, host: str, model: str):
        import ollama

        self.client, self.model = ollama.Client(host=host), model

    def chat(self, messages: list[dict], tools: list[dict]) -> Response:
        # think=False: reasoning tokens would blow the 2 s voice latency budget
        m = self.client.chat(model=self.model, messages=messages, tools=tools, think=False).message
        calls = [ToolCall(c.function.name, dict(c.function.arguments)) for c in m.tool_calls or []]
        return Response(m.content or "", calls)
