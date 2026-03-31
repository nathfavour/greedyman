#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BRAINDIR="$ROOT_DIR/brain"

if [[ ! -f "$ROOT_DIR/.env" ]]; then
  echo "Missing .env. Copy .env.example to .env and configure it first." >&2
  exit 1
fi

cd "$BRAINDIR"

if [[ -d "venv" ]]; then
  # shellcheck disable=SC1091
  source "venv/bin/activate"
fi

python main.py "$@"

