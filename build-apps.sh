#!/bin/zsh
# Compile launcher.c into both app bundles and sign them locally. Needs Xcode command line tools.
# macOS forgets the microphone permission after a rebuild; it will ask again.
set -e
cd "${0:A:h}"
for app in Jarvis JarvisListener; do
  cc -O2 -o "$app.app/Contents/MacOS/$app" launcher.c
  codesign -s - --force "$app.app"
done
echo "Built Jarvis.app and JarvisListener.app"
