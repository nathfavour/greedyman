from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from config import load_runtime_config
from engine import EngineState
from scraper import load_quotes_from_fixture
from state_store import load_state


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a Greedyman status report")
    parser.add_argument("--state-file", default=None, help="Path to the persisted state JSON")
    parser.add_argument("--fixture-file", default=None, help="Optional quote fixture used for current APY snapshot")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of markdown")
    return parser.parse_args()


def build_report(state: EngineState, quotes: list[dict]) -> dict:
    top_quote = max(quotes, key=lambda quote: quote["apy"], default=None) if quotes else None
    spread = None
    if len(quotes) >= 2:
        ordered = sorted(quotes, key=lambda quote: quote["apy"], reverse=True)
        spread = round(ordered[0]["apy"] - ordered[1]["apy"], 4)

    return {
        "last_target_protocol": state.last_target_protocol,
        "last_best_protocol": state.last_best_protocol,
        "total_yield_earned_usdc": state.total_yield_earned_usdc,
        "event_count": len(state.event_log),
        "top_quote": top_quote,
        "spread": spread,
        "recent_events": state.event_log[-5:],
    }


def render_markdown(report: dict) -> str:
    lines = [
        "# Greedyman Report",
        "",
        f"- Last target: `{report['last_target_protocol'] or '-'}`",
        f"- Last best: `{report['last_best_protocol'] or '-'}`",
        f"- Total yield earned: `{report['total_yield_earned_usdc']:.2f} USDC`",
        f"- Event count: `{report['event_count']}`",
        f"- Spread: `{report['spread'] if report['spread'] is not None else '-'}`",
    ]
    top_quote = report.get("top_quote")
    if top_quote:
        lines.extend(
            [
                "",
                "## Top Quote",
                f"- Protocol: `{top_quote['name']}`",
                f"- APY: `{top_quote['apy']:.2f}%`",
            ]
        )

    if report["recent_events"]:
        lines.extend(["", "## Recent Events"])
        lines.extend(f"- {event}" for event in report["recent_events"])

    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    runtime = load_runtime_config(state_path=args.state_file)
    state = load_state(runtime.state_path)
    quotes = []
    if args.fixture_file:
        quotes = [asdict(quote) for quote in load_quotes_from_fixture(Path(args.fixture_file))]

    report = build_report(state, quotes)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(render_markdown(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

