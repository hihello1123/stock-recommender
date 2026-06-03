#!/bin/zsh
set -euo pipefail

BOT_LABEL="com.george.stockrecommender.bot"
WORKER_LABEL="com.george.stockrecommender.worker"
DAILY_NEWS_LABEL="com.george.stockrecommender.daily-news"

for LABEL in "$BOT_LABEL" "$WORKER_LABEL" "$DAILY_NEWS_LABEL"; do
  PLIST_PATH="$HOME/Library/LaunchAgents/${LABEL}.plist"
  launchctl bootout "gui/$(id -u)" "$PLIST_PATH" >/dev/null 2>&1 || true
  rm -f "$PLIST_PATH"

  echo "Uninstalled ${LABEL}"
done
