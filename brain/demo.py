from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

from scraper import ProtocolQuote


@dataclass(slots=True)
class DemoOverride:
    cycle: int
    quotes: list[ProtocolQuote]


def load_demo_overrides(path: Path | None) -> list[DemoOverride]:
    if path is None or not path.exists():
        return []

    raw = json.loads(path.read_text(encoding="utf-8"))
    overrides: list[DemoOverride] = []
    for item in raw.get("cycle_overrides", []):
        cycle = int(item.get("cycle", 0))
        quotes: list[ProtocolQuote] = []
        for quote in item.get("quotes", []):
            if isinstance(quote, dict) and "name" in quote and "apy" in quote:
                quotes.append(
                    ProtocolQuote(
                        name=str(quote["name"]),
                        apy=float(quote["apy"]),
                        source=str(quote.get("source", f"demo:{path.name}")),
                        raw=quote,
                    )
                )
        if quotes:
            overrides.append(DemoOverride(cycle=cycle, quotes=quotes))
    return sorted(overrides, key=lambda override: override.cycle)


def apply_demo_profile(quotes: list[ProtocolQuote], cycle: int, override_file: str | None = None) -> list[ProtocolQuote]:
    path = Path(override_file) if override_file else _env_path("GREEDYMAN_DEMO_PROFILE_FILE")
    overrides = load_demo_overrides(path)
    selected = None
    for override in overrides:
        if override.cycle == cycle:
            selected = override
            break
    return selected.quotes if selected else quotes


def _env_path(name: str) -> Path | None:
    value = os.getenv(name)
    return Path(value) if value else None

