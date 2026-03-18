from __future__ import annotations

from pathlib import Path
import unittest

from trade.analysis.summary import summarize_backtest
from trade.backtest.engine import run_backtest
from trade.data.csv_loader import load_ohlcv_csv
from trade.data.resample import resample_bars
from trade.indicators.moving_average import build_multi_timeframe_ma_context, moving_average
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


if __name__ == "__main__":
    unittest.main()
