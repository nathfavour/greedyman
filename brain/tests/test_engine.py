from __future__ import annotations

import json
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from engine import EngineConfig, EngineState, choose_rebalance, record_rebalance
from scraper import ProtocolQuote, load_quotes_from_fixture
from state_store import load_state, save_state


class EngineTests(unittest.TestCase):
    def test_choose_rebalance_triggers_when_spread_exceeds_threshold(self) -> None:
        quotes = [
            ProtocolQuote("Kamino", 8.5, "fixture"),
            ProtocolQuote("Drift", 6.4, "fixture"),
            ProtocolQuote("Jupiter", 7.0, "fixture"),
        ]
        decision = choose_rebalance(quotes, EngineState(), EngineConfig(threshold_apy=1.5, cooldown_seconds=900))
        self.assertTrue(decision.should_rebalance)
        self.assertEqual(decision.target_protocol, "Kamino")
        self.assertEqual(decision.source_protocol, "Jupiter")

    def test_choose_rebalance_respects_cooldown(self) -> None:
        state = EngineState(last_rebalance_at=datetime.now(timezone.utc))
        quotes = [
            ProtocolQuote("Kamino", 8.5, "fixture"),
            ProtocolQuote("Drift", 6.7, "fixture"),
        ]
        decision = choose_rebalance(quotes, state, EngineConfig(threshold_apy=1.0, cooldown_seconds=900))
        self.assertFalse(decision.should_rebalance)
        self.assertIn("Cooldown", decision.reason)

    def test_record_rebalance_updates_state(self) -> None:
        state = EngineState()
        record_rebalance(state, "Kamino", 1.7)
        self.assertEqual(state.last_target_protocol, "Kamino")
        self.assertGreater(state.total_yield_earned_usdc, 0)
        self.assertTrue(state.event_log)

    def test_fixture_quotes_load(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fixture_path = Path(tmp) / "quotes.json"
            fixture_path.write_text(
                json.dumps({"quotes": [{"name": "Kamino", "apy": 8.2}, {"name": "Drift", "apy": 7.4}]}),
                encoding="utf-8",
            )
            quotes = load_quotes_from_fixture(fixture_path)
            self.assertEqual(len(quotes), 2)
            self.assertEqual(quotes[0].name, "Kamino")

    def test_state_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state_path = Path(tmp) / "state.json"
            state = EngineState(last_target_protocol="Drift", total_yield_earned_usdc=3.5)
            state.last_rebalance_at = datetime.now(timezone.utc) - timedelta(minutes=5)
            save_state(state_path, state)
            loaded = load_state(state_path)
            self.assertEqual(loaded.last_target_protocol, "Drift")
            self.assertAlmostEqual(loaded.total_yield_earned_usdc, 3.5)
            self.assertIsNotNone(loaded.last_rebalance_at)


if __name__ == "__main__":
    unittest.main()

