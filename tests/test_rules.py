from __future__ import annotations

from datetime import datetime
import unittest

from trade.models import MarketBar, StrategyContext
from trade.rules.composites import RuleSet
from trade.rules.ma_rules import BullishMaStackRule, EntryCrossAboveMaRule, PriceAboveMaRule


class RuleTests(unittest.TestCase):
    def test_ruleset_evaluates_all_rules(self) -> None:
        context = StrategyContext(
            current_bar=MarketBar(
                timestamp=datetime(2026, 1, 1, 10, 15),
                symbol="EUR/USD",
                timeframe="15m",
                open=1.1000,
                high=1.1015,
                low=1.0998,
                close=1.1010,
                volume=1000.0,
            ),
            previous_bar=MarketBar(
                timestamp=datetime(2026, 1, 1, 10, 0),
                symbol="EUR/USD",
                timeframe="15m",
                open=1.0990,
                high=1.1001,
                low=1.0988,
                close=1.1000,
                volume=900.0,
            ),
            has_position=False,
            features={
                "previous_ma": 1.1002,
                "ma_by_timeframe": {
                    "15m": {20: 1.1002, 60: 1.0998, 240: 1.0990},
                },
            },
        )
        ruleset = RuleSet(
            rules=(
                BullishMaStackRule("15m", 20, 60, 240),
                PriceAboveMaRule("15m", 20),
                EntryCrossAboveMaRule("15m", 20),
            )
        )

        evaluation = ruleset.evaluate(context)

        self.assertEqual(len(evaluation.results), 3)
        self.assertTrue(evaluation.all_passed())


if __name__ == "__main__":
    unittest.main()
