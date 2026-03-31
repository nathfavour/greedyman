#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="${GREEDYMAN_LOG_DIR:-$ROOT_DIR/logs}"
mkdir -p "$LOG_DIR"

while true; do
  "$ROOT_DIR/scripts/run_greedyman.sh" >>"$LOG_DIR/greedyman.log" 2>&1 || true
  sleep 5
done

