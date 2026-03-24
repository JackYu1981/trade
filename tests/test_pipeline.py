from __future__ import annotations

from datetime import datetime
from pathlib import Path
import unittest

from trade.analysis.summary import summarize_backtest
from trade.backtest.engine import run_backtest
from trade.data.csv_loader import load_ohlcv_csv
from trade.data.resample import resample_bars
from trade.indicators.moving_average import build_multi_timeframe_ma_context, moving_average
from trade.models import MarketBar, StrategyContext, StrategyDecision, StrategyDefinition
from trade.strategy_engine.demo_strategy import MultiTimeframeMaStrategy


class PipelineTests(unittest.TestCase):
    def test_demo_pipeline_produces_completed_trade_and_summary(self) -> None:
        bars = load_ohlcv_csv(Path("examples/eurusd_1h_demo.csv"), symbol="EUR/USD", timeframe="1h")
        ma_values = moving_average(bars, period=3)
        ma_contexts = build_multi_timeframe_ma_context(
            bars,
            {"1h": bars, "4h": resample_bars(bars, "4h"), "1d": resample_bars(bars, "1d")},
            periods=(3,),
        )
        result = run_backtest(
            bars,
            ma_values,
            ma_contexts,
            MultiTimeframeMaStrategy(
                execution_timeframe="1h",
                execution_fast_period=3,
                execution_mid_period=3,
                execution_slow_period=3,
                trend_timeframes=("4h", "1d"),
            ),
            initial_cash=10_000.0,
        )
        summary = summarize_backtest(result)

        self.assertEqual(summary["trade_count"], 0)
        self.assertAlmostEqual(summary["final_cash"], 10_000.0)
        self.assertAlmostEqual(summary["net_pnl"], 0.0)

    def test_backtest_supports_short_entry_and_cover_in_single_position_mode(self) -> None:
        class ShortThenCoverStrategy:
            def definition(self) -> StrategyDefinition:
                return StrategyDefinition(
                    strategy_id="test.short_then_cover",
                    name="Short Then Cover",
                    description="Minimal test strategy for short execution support.",
                    parameters={"position_mode": "single_position"},
                )

            def evaluate(self, context: StrategyContext) -> StrategyDecision:
                if context.current_bar.timestamp.hour == 0 and context.position_side is None:
                    return StrategyDecision(action="SHORT", reason="Open short", rule_results=[])
                if context.current_bar.timestamp.hour == 1 and context.position_side == "SHORT":
                    return StrategyDecision(action="COVER", reason="Close short", rule_results=[])
                return StrategyDecision(action="HOLD", reason="No action", rule_results=[])

        bars = [
            MarketBar(datetime(2026, 1, 1, 0, 0), "EUR/USD", "1h", 1.1000, 1.1002, 1.0998, 1.1000, 1000.0),
            MarketBar(datetime(2026, 1, 1, 1, 0), "EUR/USD", "1h", 1.0995, 1.0996, 1.0988, 1.0990, 1000.0),
            MarketBar(datetime(2026, 1, 1, 2, 0), "EUR/USD", "1h", 1.0991, 1.0993, 1.0989, 1.0992, 1000.0),
        ]
        result = run_backtest(
            bars,
            active_ma_values=[None, None, None],
            ma_contexts=[{}, {}, {}],
            strategy=ShortThenCoverStrategy(),
            initial_cash=10_000.0,
        )

        self.assertEqual(len(result.trades), 1)
        self.assertEqual(result.trades[0].side, "SHORT")
        self.assertAlmostEqual(result.trades[0].pnl, 0.0010)
        self.assertAlmostEqual(result.final_cash, 10_000.0010)


if __name__ == "__main__":
    unittest.main()
