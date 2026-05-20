#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$ROOT_DIR"

PORT="${PORT:-5001}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
VENV_DIR="$ROOT_DIR/.venv"

if lsof -nP -iTCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1; then
  echo "HomeHunter is already running on http://127.0.0.1:$PORT/"
  echo "Use app_run_scripts/macos/stop_app.sh first if you want to restart it."
  exit 0
fi

if [ ! -x "$VENV_DIR/bin/python" ]; then
  echo "Creating local Python environment in .venv..."
  "$PYTHON_BIN" -m venv "$VENV_DIR"
fi

if ! "$VENV_DIR/bin/python" - <<'PY' >/dev/null 2>&1
import duckdb
import flask
import flask_cors
PY
then
  echo "Installing Python dependencies into .venv..."
  "$VENV_DIR/bin/python" -m pip install --upgrade pip
  "$VENV_DIR/bin/python" -m pip install -r requirements.txt
fi

echo "Starting HomeHunter at http://127.0.0.1:$PORT/"
exec "$VENV_DIR/bin/python" src/main/backend/app.py
