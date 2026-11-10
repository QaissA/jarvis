import importlib
import inspect
from typing import Callable, get_type_hints

TOOLS: dict[str, Callable] = {}
_JSON = {str: "string", int: "integer", float: "number", bool: "boolean"}


def tool(confirm: bool = False):
    """Register a function as a tool; its schema comes from the type hints and docstring."""
    def deco(fn):
        hints = get_type_hints(fn)
        params = inspect.signature(fn).parameters
        fn.confirm = confirm
        fn.schema = {"type": "function", "function": {
            "name": fn.__name__,
            "description": inspect.getdoc(fn),
            "parameters": {
                "type": "object",
                "properties": {n: {"type": _JSON[hints[n]]} for n in params},
                "required": [n for n, p in params.items() if p.default is p.empty],
            }}}
        TOOLS[fn.__name__] = fn
        return fn
    return deco


def load(modules: list[str]) -> None:
    for m in modules:
        importlib.import_module(f"jarvis.tools.{m}")


def schemas() -> list[dict]:
    return [fn.schema for fn in TOOLS.values()]


def call(name: str, args: dict, confirm: Callable[[str], bool]) -> str:
    fn = TOOLS.get(name)
    if fn is None:
        return f"Error: unknown tool {name}"
    if fn.confirm:
        what = " ".join([name.replace("_", " "), *map(str, args.values())])
        if not confirm(f"Should I {what}?"):
            return "Cancelled by the user."
    try:
        return str(fn(**args))
    except Exception as e:  # a bad tool call must never crash the agent loop
        return f"Error: {e}"
