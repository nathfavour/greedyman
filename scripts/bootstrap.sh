#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ ! -d "$ROOT_DIR/brain/venv" ]]; then
  python3 -m venv "$ROOT_DIR/brain/venv"
fi

# shellcheck disable=SC1091
source "$ROOT_DIR/brain/venv/bin/activate"

python -m pip install --upgrade pip >/dev/null 2>&1 || true
python -m pip install -r "$ROOT_DIR/brain/requirements.txt" || true

if [[ ! -d "$ROOT_DIR/body/node_modules" ]]; then
  echo "Run 'cd body && pnpm install' to install TypeScript dependencies."
else
  echo "TypeScript dependencies already installed."
fi

echo "Bootstrap complete."

