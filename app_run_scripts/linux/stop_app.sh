#!/usr/bin/env bash
set -euo pipefail

PORT="${PORT:-5001}"

if command -v lsof >/dev/null 2>&1; then
  PIDS="$(lsof -tiTCP:"$PORT" -sTCP:LISTEN || true)"
else
  PIDS="$(fuser "$PORT/tcp" 2>/dev/null || true)"
fi

if [ -z "$PIDS" ]; then
  echo "No app process is listening on port $PORT."
  exit 0
fi

echo "Stopping app process(es) on port $PORT: $PIDS"
kill $PIDS

sleep 1
if command -v lsof >/dev/null 2>&1; then
  REMAINING="$(lsof -tiTCP:"$PORT" -sTCP:LISTEN || true)"
else
  REMAINING="$(fuser "$PORT/tcp" 2>/dev/null || true)"
fi

if [ -n "$REMAINING" ]; then
  echo "Some process(es) did not stop; forcing: $REMAINING"
  kill -9 $REMAINING
fi

echo "Stopped app on port $PORT."
