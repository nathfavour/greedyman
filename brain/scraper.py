from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from typing import Any

import httpx


@dataclass(slots=True)
class ProtocolQuote:
    name: str
    apy: float
    source: str
    raw: dict[str, Any] | None = None


def _fallback_apy(name: str) -> float:
    fallback_map = {
        "kamino": 8.15,
        "drift": 7.45,
        "jupiter": 7.9,
    }
    return fallback_map.get(name.lower(), 0.0)


def _extract_numeric_apy(payload: Any) -> float | None:
    if isinstance(payload, (int, float)):
        return float(payload)
    if isinstance(payload, dict):
        for key in ("apy", "supplyApy", "supply_apy", "depositApy", "deposit_apy", "rate"):
            value = payload.get(key)
            if isinstance(value, (int, float)):
                return float(value)
        for value in payload.values():
            extracted = _extract_numeric_apy(value)
            if extracted is not None:
                return extracted
    if isinstance(payload, list):
        for item in payload:
            extracted = _extract_numeric_apy(item)
            if extracted is not None:
                return extracted
    return None


async def fetch_protocol_quote(
    client: httpx.AsyncClient,
    name: str,
    url: str | None,
) -> ProtocolQuote:
    if not url:
        return ProtocolQuote(name=name, apy=_fallback_apy(name), source="fallback")

    try:
        response = await client.get(url, timeout=10.0)
        response.raise_for_status()
        payload = response.json()
    except (httpx.HTTPError, ValueError):
        return ProtocolQuote(name=name, apy=_fallback_apy(name), source="fallback-error")

    apy = _extract_numeric_apy(payload)
    if apy is None:
        return ProtocolQuote(name=name, apy=_fallback_apy(name), source="fallback-parsed")

    return ProtocolQuote(
        name=name,
        apy=apy,
        source=url,
        raw=payload if isinstance(payload, dict) else None,
    )


async def fetch_all_quotes() -> list[ProtocolQuote]:
    urls = {
        "Kamino": os.getenv("KAMINO_APY_URL"),
        "Drift": os.getenv("DRIFT_APY_URL"),
        "Jupiter": os.getenv("JUPITER_APY_URL"),
    }

    async with httpx.AsyncClient(headers={"user-agent": "greedyman/0.1"}) as client:
        tasks = [fetch_protocol_quote(client, name, url) for name, url in urls.items()]
        return await asyncio.gather(*tasks)

