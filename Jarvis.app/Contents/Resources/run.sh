#!/bin/zsh
# Jarvis.app lives in the project root, so the project is three folders up: moving the folder keeps this working.
cd "${0:A:h}/../../.." || exit 1   # started by the launcher binary in ../MacOS
export PATH="$HOME/.local/bin:$PATH"   # apps get a bare PATH; uv and claude live here
mkdir -p data
curl -sf localhost:11434/api/version >/dev/null || open -gja Ollama   # start Ollama if it is not running
exec uv run -q --extra voice python -m jarvis.app >> data/app.log 2>&1
