from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Iterable

from scraper import ProtocolQuote


@dataclass(slots=True)
class RebalanceDecision:
    should_rebalance: bool
    source_protocol: str | None = None
    target_protocol: str | None = None
    spread: float = 0.0
    reason: str = ""
    amount_label: str = "100%"
    action: str = "hold"


@dataclass(slots=True)
class EngineState:
    last_rebalance_at: datetime | None = None
    last_target_protocol: str | None = None
    last_best_protocol: str | None = None
    total_yield_earned_usdc: float = 0.0
    event_log: list[str] = field(default_factory=list)


@dataclass(slots=True)
class EngineConfig:
    threshold_apy: float = 1.5
    cooldown_seconds: int = 900
    switchback_buffer_apy: float = 0.25


def _cooldown_ready(state: EngineState, config: EngineConfig, now: datetime) -> bool:
    if state.last_rebalance_at is None:
        return True
    return now - state.last_rebalance_at >= timedelta(seconds=config.cooldown_seconds)


def choose_rebalance(
    quotes: Iterable[ProtocolQuote],
    state: EngineState,
    config: EngineConfig,
    now: datetime | None = None,
) -> RebalanceDecision:
    now = now or datetime.now(timezone.utc)
    ordered_quotes = sorted(quotes, key=lambda quote: quote.apy, reverse=True)
    if len(ordered_quotes) < 2:
        return RebalanceDecision(False, reason="Need at least two protocol quotes")

    best = ordered_quotes[0]
    runner_up = ordered_quotes[1]
    spread = best.apy - runner_up.apy
    previous_target = state.last_target_protocol

    if previous_target == best.name:
        state.last_best_protocol = best.name
        return RebalanceDecision(
            should_rebalance=False,
            source_protocol=runner_up.name,
            target_protocol=best.name,
            spread=spread,
            reason=f"Already allocated to {best.name}",
            action="hold",
        )

    if spread < config.threshold_apy:
        state.last_best_protocol = best.name
        return RebalanceDecision(
            should_rebalance=False,
            source_protocol=runner_up.name,
            target_protocol=best.name,
            spread=spread,
            reason=f"Spread {spread:.2f}% is below threshold {config.threshold_apy:.2f}%",
        )

    if not _cooldown_ready(state, config, now):
        state.last_best_protocol = best.name
        return RebalanceDecision(
            should_rebalance=False,
            source_protocol=runner_up.name,
            target_protocol=best.name,
            spread=spread,
            reason="Cooldown active",
            action="cooldown",
        )

    if previous_target and previous_target != best.name and spread < (config.threshold_apy + config.switchback_buffer_apy):
        state.last_best_protocol = best.name
        return RebalanceDecision(
            should_rebalance=False,
            source_protocol=previous_target,
            target_protocol=best.name,
            spread=spread,
            reason=f"Switchback buffer active for {previous_target} -> {best.name}",
            action="hysteresis",
        )

    state.last_best_protocol = best.name
    return RebalanceDecision(
        should_rebalance=True,
        source_protocol=runner_up.name,
        target_protocol=best.name,
        spread=spread,
        reason=f"{best.name} leads by {spread:.2f}%",
        action="rebalance",
    )


def record_rebalance(state: EngineState, target_protocol: str, estimated_yield_delta: float) -> None:
    state.last_rebalance_at = datetime.now(timezone.utc)
    state.last_target_protocol = target_protocol
    state.last_best_protocol = target_protocol
    state.total_yield_earned_usdc += estimated_yield_delta
    state.event_log.append(
        f"{state.last_rebalance_at.isoformat()} rebalance -> {target_protocol} (+{estimated_yield_delta:.2f} USDC)"
    )

