#!/bin/zsh
set -euo pipefail

SCRIPT_DIR=${0:A:h}
REPO_ROOT=${SCRIPT_DIR:h}

export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

UV_BIN="${UV_BIN:-$(command -v uv)}"

cd "$REPO_ROOT"
exec "$UV_BIN" run python manage.py run_telegram_bot
