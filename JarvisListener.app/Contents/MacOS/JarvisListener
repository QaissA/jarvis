#!/bin/zsh
# Lives in the project root next to Jarvis.app; a separate app so macOS grants it the microphone and hides it from the Dock.
cd "${0:A:h}/../../.." || exit 1
export PATH="$HOME/.local/bin:$PATH"
mkdir -p data
exec uv run -q --extra voice python -m jarvis.listener > data/listener.log 2>&1
