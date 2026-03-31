from __future__ import annotations

import argparse
import asyncio
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.table import Table

from engine import EngineConfig, EngineState, choose_rebalance, record_rebalance
from scraper import fetch_all_quotes


console = Console()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Greedyman off-chain brain daemon")
    parser.add_argument("--once", action="store_true", help="Run a single evaluation cycle")
    parser.add_argument(
        "--interval",
        type=int,
        default=int(os.getenv("GREEDYMAN_POLL_INTERVAL_SECONDS", "60")),
        help="Polling interval in seconds",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=os.getenv("GREEDYMAN_DRY_RUN", "1") == "1",
        help="Do not invoke the on-chain adapter",
    )
    parser.add_argument(
        "--body-cwd",
        default=str(Path(__file__).resolve().parent.parent / "body"),
        help="Working directory for the TypeScript adapter",
    )
    return parser.parse_args()


def build_status_panel(quotes, state: EngineState, last_message: str) -> Panel:
    table = Table(title="Greedyman")
    table.add_column("Protocol", style="cyan", no_wrap=True)
    table.add_column("APY", justify="right")
    table.add_column("Source", overflow="fold")

    for quote in quotes:
        table.add_row(quote.name, f"{quote.apy:.2f}%", quote.source)

    summary = Table.grid(padding=(0, 1))
    summary.add_row("Last Target", state.last_target_protocol or "-")
    summary.add_row("Total Yield", f"{state.total_yield_earned_usdc:.2f} USDC")
    summary.add_row("Last Event", last_message)

    group = Table.grid(expand=True)
    group.add_row(table)
    group.add_row(Panel(summary, title="State"))
    return Panel(group, title=f"Greedyman Brain @ {datetime.now(timezone.utc).isoformat()}")


def invoke_body(target_protocol: str, amount_label: str, body_cwd: str) -> tuple[int, str]:
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

    completed = subprocess.run(
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
            code, output = invoke_body(decision.target_protocol, decision.amount_label, body_cwd)
            if code == 0:
                record_rebalance(state, decision.target_protocol, estimated_yield_delta=max(decision.spread, 0.0))
                message = f"Executed rebalance to {decision.target_protocol}: {output or 'success'}"
            else:
                message = f"Adapter failed with exit code {code}: {output or 'no output'}"

    return message, quotes


async def run_loop(args: argparse.Namespace) -> int:
    state = EngineState()
    config = EngineConfig(
        threshold_apy=float(os.getenv("GREEDYMAN_THRESHOLD_APY", "1.5")),
        cooldown_seconds=int(os.getenv("GREEDYMAN_COOLDOWN_SECONDS", "900")),
    )

    last_message = "Waiting for first evaluation"
    with Live(refresh_per_second=2, console=console) as live:
        while True:
            message, quotes = await evaluate_once(state, config, args.dry_run, args.body_cwd)
            last_message = message
            state.event_log.append(message)
            live.update(build_status_panel(quotes, state, last_message))

            if args.once:
                break

            await asyncio.sleep(max(1, args.interval))

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

