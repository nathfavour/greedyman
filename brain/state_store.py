from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any

from engine import EngineState


def load_state(path: Path) -> EngineState:
    if not path.exists():
        return EngineState()

    raw = json.loads(path.read_text(encoding="utf-8"))
    state = EngineState(
        last_target_protocol=raw.get("last_target_protocol"),
        total_yield_earned_usdc=float(raw.get("total_yield_earned_usdc", 0.0)),
        event_log=list(raw.get("event_log", [])),
    )
    last_rebalance_at = raw.get("last_rebalance_at")
    if isinstance(last_rebalance_at, str) and last_rebalance_at:
        state.last_rebalance_at = datetime.fromisoformat(last_rebalance_at)
    return state


def save_state(path: Path, state: EngineState) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = asdict(state)
    payload["last_rebalance_at"] = state.last_rebalance_at.isoformat() if state.last_rebalance_at else None
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

