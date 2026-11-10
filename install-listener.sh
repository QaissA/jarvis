#!/bin/zsh
# Start the "Hey Jarvis" listener at login.  ./install-listener.sh  |  ./install-listener.sh uninstall
# Re-run after moving the project folder: the login item stores this folder's path.
set -e
plist="$HOME/Library/LaunchAgents/local.jarvis.listener.plist"
launchctl bootout "gui/$UID/local.jarvis.listener" 2>/dev/null || true
pkill -f "jarvis.listener" || true
rm -f "$plist"
[[ "$1" == uninstall ]] && { echo "Listener removed."; exit 0; }
cat > "$plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>local.jarvis.listener</string>
  <key>ProgramArguments</key><array><string>/usr/bin/open</string><string>-g</string><string>${0:A:h}/JarvisListener.app</string></array>
  <key>RunAtLoad</key><true/>
</dict></plist>
PLIST
launchctl bootstrap "gui/$UID" "$plist"
echo "Listener installed and started."
