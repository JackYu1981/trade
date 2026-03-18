from __future__ import annotations

from datetime import datetime
import unittest

from trade.models import MarketBar, StrategyContext
from trade.rules import RuleSet, StagedRuleSets
from trade.rules.ma_rules import BullishMaStackRule, EntryCrossAboveMaRule, ExitCloseBelowMaRule, PriceAboveMaRule


class StagedRuleSetTests(unittest.TestCase):
    def test_staged_rule_sets_keep_phase_boundaries(self) -> None:
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
                    "1h": {20: 1.1000, 60: 1.0990, 240: 1.0980},
                },
            },
        )
        staged = StagedRuleSets(
            trend=RuleSet(rules=(BullishMaStackRule("1h", 20, 60, 240),)),
            entry=RuleSet(rules=(PriceAboveMaRule("15m", 20, phase="entry"), EntryCrossAboveMaRule("15m", 20, phase="entry"))),
            exit=RuleSet(rules=(ExitCloseBelowMaRule("15m", 20, phase="exit"),)),
            add=RuleSet(rules=()),
        )

        evaluation = staged.evaluate(context)

        self.assertEqual(len(evaluation.trend.results), 1)
        self.assertEqual(len(evaluation.entry.results), 2)
        self.assertEqual(len(evaluation.exit.results), 1)
        self.assertEqual(evaluation.trend.results[0].phase, "trend")
        self.assertTrue(all(result.phase == "entry" for result in evaluation.entry.results))
        self.assertEqual(evaluation.exit.results[0].phase, "exit")
        self.assertEqual(len(evaluation.combined_results("trend", "entry")), 3)


if __name__ == "__main__":
    unittest.main()
