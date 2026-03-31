from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class RuntimeConfig:
    threshold_apy: float = 1.5
    cooldown_seconds: int = 900
    switchback_buffer_apy: float = 0.25
    poll_interval_seconds: int = 60
    dry_run: bool = True
    body_cwd: Path = Path(__file__).resolve().parent.parent / "body"
    fixture_path: Path | None = None
    state_path: Path = Path(__file__).resolve().parent.parent / ".greedyman_state.json"
    max_cycles: int | None = None
    json_logs: bool = False


def load_runtime_config(
    *,
    threshold_apy: float | None = None,
    cooldown_seconds: int | None = None,
    switchback_buffer_apy: float | None = None,
    poll_interval_seconds: int | None = None,
    dry_run: bool | None = None,
    body_cwd: str | None = None,
    fixture_path: str | None = None,
    state_path: str | None = None,
    max_cycles: int | None = None,
    json_logs: bool | None = None,
) -> RuntimeConfig:
    return RuntimeConfig(
        threshold_apy=threshold_apy if threshold_apy is not None else float(os.getenv("GREEDYMAN_THRESHOLD_APY", "1.5")),
        cooldown_seconds=cooldown_seconds if cooldown_seconds is not None else int(os.getenv("GREEDYMAN_COOLDOWN_SECONDS", "900")),
        switchback_buffer_apy=switchback_buffer_apy
        if switchback_buffer_apy is not None
        else float(os.getenv("GREEDYMAN_SWITCHBACK_BUFFER_APY", "0.25")),
        poll_interval_seconds=poll_interval_seconds
        if poll_interval_seconds is not None
        else int(os.getenv("GREEDYMAN_POLL_INTERVAL_SECONDS", "60")),
        dry_run=dry_run if dry_run is not None else os.getenv("GREEDYMAN_DRY_RUN", "1") == "1",
        body_cwd=Path(body_cwd) if body_cwd else Path(__file__).resolve().parent.parent / "body",
        fixture_path=Path(fixture_path) if fixture_path else _env_path("GREEDYMAN_FIXTURE_FILE"),
        state_path=Path(state_path) if state_path else _env_path("GREEDYMAN_STATE_FILE") or Path(__file__).resolve().parent.parent / ".greedyman_state.json",
        max_cycles=max_cycles if max_cycles is not None else _env_int("GREEDYMAN_MAX_CYCLES"),
        json_logs=json_logs if json_logs is not None else os.getenv("GREEDYMAN_JSON_LOGS", "0") == "1",
    )


def _env_path(name: str) -> Path | None:
    value = os.getenv(name)
    return Path(value) if value else None


def _env_int(name: str) -> int | None:
    value = os.getenv(name)
    return int(value) if value else None

