#!/bin/zsh
set -euo pipefail

LABEL="com.george.stockrecommender.bot"
PLIST_PATH="$HOME/Library/LaunchAgents/${LABEL}.plist"

launchctl bootout "gui/$(id -u)" "$PLIST_PATH" >/dev/null 2>&1 || true
rm -f "$PLIST_PATH"

echo "Uninstalled ${LABEL}"
