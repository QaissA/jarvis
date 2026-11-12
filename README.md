# Jarvis

Jarvis is a voice assistant for macOS. You say "Hey Jarvis", speak a request, and it answers aloud in a dry, polite British voice. It can run commands, read and open files, search the web, drive your browser, set timers and remember facts about you.

Speech recognition, speech synthesis and wake-word detection all run on your own machine. Only the reasoning step needs the internet: by default it is handled by Claude through your Claude Code login. If Claude cannot be reached, Jarvis falls back to a local model served by Ollama, so it keeps working offline.

## Contents

- [What it can do](#what-it-can-do)
- [How it works](#how-it-works)
- [Requirements](#requirements)
- [Installation](#installation)
- [Running Jarvis](#running-jarvis)
- [Configuration](#configuration)
- [Tools](#tools)
- [Safety and confirmations](#safety-and-confirmations)
- [Project layout](#project-layout)
- [Development](#development)
- [Troubleshooting](#troubleshooting)

## What it can do

- Hands-free activation with the "Hey Jarvis" wake word, or push-to-talk and typed input.
- Spoken answers kept short on purpose, addressed to you as "sir" (configurable).
- Shell, file, web search and web page access through Claude's own tools.
- Browser control through the Claude in Chrome extension.
- Jarvis's own tools: time and date, system information, opening and closing apps, opening URLs and files, searching files, timers and long-term memory.
- Long-term memory in a local SQLite database, so it can remember facts about you between sessions.
- A frameless desktop dashboard with a live transcript, a clock, system meters, a text box and inline images.
- A small always-on-top status pill showing whether Jarvis is idle, listening, thinking or speaking.
- A background listener that starts at login and opens the app when it hears "Hey Jarvis".

## How it works

One request goes through these stages:

1. **Wake word.** openWakeWord listens continuously to the microphone for "Hey Jarvis". A chime confirms it heard you.
2. **Recording.** A Silero voice-activity detector records until you stop speaking. Silence of 0.8 seconds ends the recording by default.
3. **Transcription.** faster-whisper converts the audio to text on the device.
4. **Thinking.** The text goes to the brain. With `brain: claude`, the Claude Agent SDK handles it, using Jarvis's tools and Claude's built-in ones. With `brain: ollama`, or if Claude fails, a local model answers and calls Jarvis's tools directly.
5. **Speaking.** Piper synthesizes the reply sentence by sentence, so the first sentence plays while the rest is still being generated.
6. **Follow-up.** If the reply ends with a question, Jarvis listens again without needing the wake word.

Replies can contain markdown images. These are shown on the dashboard and never read aloud.

### The brains

| Brain | Module | Needs internet | Notes |
| --- | --- | --- | --- |
| Claude | `jarvis/brain/claude.py` | Yes | Uses your Claude Code login. Keeps conversation context within a session. Gates risky tool calls. |
| Ollama | `jarvis/brain/agent.py`, `jarvis/brain/llm.py` | No | Local model with a capped tool-call loop. Also the automatic fallback when Claude fails or times out. |

Both brains store each exchange in the history table, and the last ten turns plus remembered facts are added to the system prompt.

### Memory

`jarvis/memory/store.py` keeps two SQLite tables in `data/jarvis.db`: `facts`, which holds what you asked Jarvis to remember, and `history`, which holds past turns. The `remember` and `recall` tools read and write facts.

## Requirements

- macOS. The desktop app, the launcher and the login item use macOS-only APIs.
- Python 3.11 or 3.12.
- [uv](https://docs.astral.sh/uv/) for dependency management.
- Xcode command line tools, to compile the app launchers.
- A Claude Code login, for the default brain.
- [Ollama](https://ollama.com) with a model pulled, for offline use and as the fallback.
- A microphone.
- Optional: Chrome with the Claude in Chrome extension, for browser control.

## Installation

```sh
git clone https://github.com/QaissA/jarvis.git
cd jarvis
uv sync --extra voice
```

On first run Jarvis downloads what it needs:

- The wake-word and voice-activity models, through openWakeWord.
- The Piper voice `en_GB-alan-medium` into `models/`.
- The Whisper model, on first transcription.

To use the local fallback brain, pull a model, for example:

```sh
ollama pull qwen3:8b
```

### Desktop app

Compile the launchers and sign them locally:

```sh
./build-apps.sh
open Jarvis.app
```

macOS asks for microphone access the first time. It asks again after every rebuild of the launcher.

### "Hey Jarvis" at login

```sh
./install-listener.sh             # install and start
./install-listener.sh uninstall   # remove
```

The login item stores the folder's path, so run the script again if you move the project.

## Running Jarvis

| Mode | Command |
| --- | --- |
| Desktop app | `open Jarvis.app` |
| Voice with wake word | `uv run python -m jarvis.main` |
| Push to talk | `uv run python -m jarvis.main --ptt` |
| Typing only | `uv run python -m jarvis.main --text` |
| Typing, spoken replies | `uv run python -m jarvis.main --text --speak` |
| Custom config file | `uv run python -m jarvis.main --config path/to/config.yaml` |

## Configuration

Settings live in `config.yaml`. Every key is optional, and unknown keys are rejected at startup so a typo cannot go unnoticed.

| Key | Default | Meaning |
| --- | --- | --- |
| `brain` | `claude` | `claude` or `ollama`. |
| `claude_model` | `sonnet` | `haiku` is faster, `opus` thinks harder and uses more of your plan. |
| `claude_timeout` | `300` | Seconds allowed for one whole request, tool use included. |
| `claude_chrome` | `false` | Browser control through the Claude in Chrome extension. |
| `model` | `qwen3:8b` | Ollama model. Suggested: `gemma4:e4b` on 8 GB of RAM, `gpt-oss:20b` on 32 GB or more. |
| `ollama_host` | `http://localhost:11434` | Where Ollama is running. |
| `user_name` | `sir` | How Jarvis addresses you. |
| `whisper_model` | `small` | `base.en` is faster, `small` is more accurate. |
| `language` | `en` | Speech recognition language. |
| `piper_voice` | `models/en_GB-alan-medium.onnx` | Text-to-speech voice. |
| `wake_threshold` | `0.5` | Raise it if a TV wakes Jarvis, lower it if Jarvis ignores you. |
| `silence_seconds` | `0.8` | Quiet time that ends your sentence. |
| `max_record_seconds` | `15` | Longest single recording. |
| `followup_seconds` | `5` | How long to wait for a reply after Jarvis asks a question. |
| `history_turns` | `10` | Past exchanges included in each request. |
| `max_tool_rounds` | `5` | Tool-call cap for the Ollama brain. |
| `allowed_folders` | Documents, Desktop, Downloads | Folders the file tools may touch. |
| `tool_modules` | all | Tool modules to load. Small local models get confused past about eight tools, so trim the list for them. |
| `db_path` | `data/jarvis.db` | Memory database. |

## Tools

Every tool is a typed Python function with a docstring that returns a string. The docstring and type hints become the schema the model sees.

| Module | Tools |
| --- | --- |
| `system` | `get_time`, `get_date`, `system_info` |
| `apps` | `open_app`, `close_app` (asks for confirmation) |
| `web` | `open_url`, `web_search` |
| `files` | `search_files`, `open_file`, limited to `allowed_folders` |
| `timers` | `set_timer`, which announces itself aloud when it fires |
| `memory_tools` | `remember`, `recall` |
| `claude` | `ask_claude`, which sends hard questions to Claude when the local model is in charge |

To add a tool, write a function in `jarvis/tools/`, decorate it with `@tool`, add the module to `tool_modules`, and write a test. Destructive tools use `@tool(confirm=True)`. The registry catches exceptions so a failing tool returns an error message instead of crashing the voice loop.

## Safety and confirmations

- Read-only actions run without asking: reading and searching files, web search and fetch, safe shell commands such as `ls`, `cat`, `date` and `open`, and Jarvis's own tools.
- Anything else Claude wants to do, such as other shell commands, file edits and browser actions, goes through a gate that asks you aloud. The exact command or file is shown on screen while only the question is spoken.
- A new file in your home folder is allowed without asking, because it cannot destroy anything.
- One yes covers the browser steps of a single request.
- Answers are checked strictly: a reply counts as approval only if it contains a yes word and no no word. Unclear means no.
- If the microphone hears nothing, you can answer a confirmation by typing.
- Claude runs without your user or project settings, hooks or CLAUDE.md, so Jarvis behaves as its own assistant.

## Project layout

```
jarvis/
  main.py            entry point, builds the brain and the tool registry
  orchestrator.py    the voice loop: wake, listen, think, speak
  app.py             desktop window, status pill and UI events
  ui.html            the dashboard
  listener.py        background "Hey Jarvis" listener
  config.py          validated settings
  audio/             mic, wake word, voice-activity detection, speech to text, text to speech
  brain/             Claude brain, Ollama brain, prompts
  memory/            SQLite store and prompt context
  tools/             tool registry and tool modules
tests/               pytest suite
launcher.c           native launcher compiled into the two app bundles
build-apps.sh        compiles and signs Jarvis.app and JarvisListener.app
install-listener.sh  installs or removes the login item
config.yaml          your settings
```

Design rules the code follows:

- One responsibility per module.
- `audio/` never imports `brain/`, and `brain/` never imports `audio/`. Only the orchestrator connects them.
- Every tool has type hints, a docstring and a string return value.
- Every new function gets a pytest test.

## Development

```sh
uv run pytest
```

After editing `launcher.c`, run `./build-apps.sh`. macOS will ask for microphone access again.

The `models/` and `data/` folders and the virtual environment are not in the repository. Models are downloaded on first run, and `data/` holds your private memory database.

## Troubleshooting

- **"I can't hear anything."** Allow Jarvis, or JarvisListener for the login item, under System Settings, Privacy and Security, Microphone, then reopen it. Typing in the dashboard still works.
- **Jarvis wakes up by itself.** Raise `wake_threshold`.
- **Jarvis ignores "Hey Jarvis".** Lower `wake_threshold` and check the microphone.
- **Answers are slow.** Set `claude_model: haiku` or use a smaller `whisper_model`.
- **Claude is unavailable.** Jarvis answers with the local Ollama model instead. Make sure Ollama is running.
- **The login listener stopped working after moving the folder.** Run `./install-listener.sh` again.
