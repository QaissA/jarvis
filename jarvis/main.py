import argparse
from pathlib import Path

from jarvis import config
from jarvis.brain.agent import Agent
from jarvis.brain.llm import OllamaClient
from jarvis.memory.store import Store
from jarvis.tools import files, memory_tools, registry


def build_agent(cfg: config.Config, confirm) -> Agent:
    store = Store(cfg.db_path)
    memory_tools.store = store
    files.allowed_folders = [Path(f).expanduser().resolve() for f in cfg.allowed_folders]
    registry.load(cfg.tool_modules)
    return Agent(OllamaClient(cfg.ollama_host, cfg.model), cfg, store, confirm)


def main() -> None:
    ap = argparse.ArgumentParser(description="Jarvis, a local voice assistant")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--text", action="store_true", help="type instead of talking")
    mode.add_argument("--ptt", action="store_true", help="press Enter to talk, no wake word")
    ap.add_argument("--speak", action="store_true", help="with --text: speak the replies")
    ap.add_argument("--config", default="config.yaml")
    args = ap.parse_args()
    cfg = config.load(args.config)

    if not args.text:
        from jarvis.orchestrator import run
        return run(cfg, build_agent, ptt=args.ptt)

    agent = build_agent(cfg, lambda q: input(f"Jarvis: {q} (y/n) ").strip().lower().startswith("y"))
    speak = print
    if args.speak:
        from jarvis.audio.tts import TTS
        tts = TTS(cfg.piper_voice)
        speak = lambda text: (print(text), tts.speak(text))
    try:
        while True:
            if text := input("You: ").strip():
                print("Jarvis: ", end="")
                speak(agent.reply(text))
    except (EOFError, KeyboardInterrupt):
        print()


if __name__ == "__main__":
    main()
