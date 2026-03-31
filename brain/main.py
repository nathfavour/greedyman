from __future__ import annotations

import argparse
import asyncio
import json
import os
import subprocess
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.table import Table

from config import load_runtime_config
from engine import EngineConfig, EngineState, choose_rebalance, record_rebalance
from scraper import fetch_all_quotes
from state_store import load_state, save_state


console = Console()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Greedyman off-chain brain daemon")
    parser.add_argument("--once", action="store_true", help="Run a single evaluation cycle")
    parser.add_argument("--max-cycles", type=int, default=None, help="Limit the number of cycles")
    parser.add_argument(
        "--interval",
        type=int,
        default=None,
        help="Polling interval in seconds",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=None,
        help="Do not invoke the on-chain adapter",
    )
    parser.add_argument(
        "--body-cwd",
        default=None,
        help="Working directory for the TypeScript adapter",
    )
    parser.add_argument("--fixture-file", default=None, help="Load quotes from a JSON fixture instead of HTTP")
    parser.add_argument("--state-file", default=None, help="Persist daemon state to this JSON file")
    parser.add_argument("--json-logs", action="store_true", default=None, help="Emit structured JSON logs to stdout")
    return parser.parse_args()


def build_status_panel(quotes, state: EngineState, last_message: str, config: EngineConfig) -> Panel:
    table = Table(title="Greedyman")
    table.add_column("Protocol", style="cyan", no_wrap=True)
    table.add_column("APY", justify="right")
    table.add_column("Source", overflow="fold")

    for quote in quotes:
        table.add_row(quote.name, f"{quote.apy:.2f}%", quote.source)

    summary = Table.grid(padding=(0, 1))
    summary.add_row("Last Target", state.last_target_protocol or "-")
    summary.add_row("Total Yield", f"{state.total_yield_earned_usdc:.2f} USDC")
    summary.add_row("Threshold", f"{config.threshold_apy:.2f}%")
    summary.add_row("Cooldown", f"{config.cooldown_seconds}s")
    summary.add_row("Last Event", last_message)
    summary.add_row("Events", str(len(state.event_log)))
    if state.event_log:
        summary.add_row("Recent", "\n".join(state.event_log[-3:]))

    group = Table.grid(expand=True)
    group.add_row(table)
    group.add_row(Panel(summary, title="State"))
    return Panel(group, title=f"Greedyman Brain @ {datetime.now(timezone.utc).isoformat()}")


async def invoke_body(target_protocol: str, amount_label: str, body_cwd: str) -> tuple[int, str]:
    command = [
        "pnpm",
        "exec",
        "tsx",
        "index.ts",
        "--target",
        target_protocol,
        "--amount",
        amount_label,
    ]

    completed = await asyncio.to_thread(
        subprocess.run,
        command,
        cwd=body_cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    output = (completed.stdout or "") + (completed.stderr or "")
    return completed.returncode, output.strip()


async def evaluate_once(
    state: EngineState,
    config: EngineConfig,
    dry_run: bool,
    body_cwd: str,
) -> tuple[str, list]:
    quotes = await fetch_all_quotes()
    decision = choose_rebalance(quotes, state, config)
    message = decision.reason or "No action taken"

    if decision.should_rebalance and decision.target_protocol:
        if dry_run:
            message = f"[dry-run] would rebalance into {decision.target_protocol} ({decision.spread:.2f}%)"
        else:
            code, output = await invoke_body(decision.target_protocol, decision.amount_label, body_cwd)
            if code == 0:
                record_rebalance(state, decision.target_protocol, estimated_yield_delta=max(decision.spread, 0.0))
                message = f"Executed rebalance to {decision.target_protocol}: {output or 'success'}"
            else:
                message = f"Adapter failed with exit code {code}: {output or 'no output'}"

    return message, quotes


async def run_loop(args: argparse.Namespace) -> int:
    runtime = load_runtime_config(
        threshold_apy=None,
        cooldown_seconds=None,
        poll_interval_seconds=args.interval,
        dry_run=args.dry_run,
        body_cwd=args.body_cwd,
        fixture_path=args.fixture_file,
        state_path=args.state_file,
        max_cycles=args.max_cycles,
        json_logs=args.json_logs,
    )
    state = load_state(runtime.state_path)
    config = EngineConfig(threshold_apy=runtime.threshold_apy, cooldown_seconds=runtime.cooldown_seconds)

    last_message = "Waiting for first evaluation"
    cycles = 0
    with Live(refresh_per_second=2, console=console) as live:
        while True:
            message, quotes = await evaluate_once(state, config, runtime.dry_run, str(runtime.body_cwd))
            last_message = message
            state.event_log.append(message)
            live.update(build_status_panel(quotes, state, last_message, config))
            save_state(runtime.state_path, state)

            if runtime.json_logs:
                console.print(
                    json.dumps(
                        {
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "message": message,
                            "quotes": [asdict(quote) for quote in quotes],
                            "state": {
                                "last_target_protocol": state.last_target_protocol,
                                "total_yield_earned_usdc": state.total_yield_earned_usdc,
                            },
                        }
                    )
                )

            cycles += 1
            if args.once or (runtime.max_cycles is not None and cycles >= runtime.max_cycles):
                break

            await asyncio.sleep(max(1, runtime.poll_interval_seconds))

    return 0


def main() -> int:
    load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")
    args = parse_args()
    try:
        return asyncio.run(run_loop(args))
    except KeyboardInterrupt:
        console.print("\n[yellow]Greedyman stopped by user.[/yellow]")
        return 130


if __name__ == "__main__":
    raise SystemExit(main())

