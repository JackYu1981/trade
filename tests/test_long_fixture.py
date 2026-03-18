from __future__ import annotations

from pathlib import Path
import unittest

from trade.analysis.summary import summarize_backtest
from trade.backtest.engine import run_backtest
from trade.data.csv_loader import load_ohlcv_csv
from trade.data.resample import resample_bars
from trade.indicators.moving_average import build_multi_timeframe_ma_context
from trade.strategy_engine.demo_strategy import MultiTimeframeMaStrategy


class LongFixtureTests(unittest.TestCase):
    def test_long_15m_fixture_supports_default_multi_timeframe_ma_strategy(self) -> None:
        bars = load_ohlcv_csv(
            Path("examples/eurusd_15m_long_demo.csv"),
            symbol="EUR/USD",
            timeframe="15m",
        )
        ma_contexts = build_multi_timeframe_ma_context(
            bars,
            {
                "15m": bars,
                "1h": resample_bars(bars, "1h"),
                "4h": resample_bars(bars, "4h"),
                "1d": resample_bars(bars, "1d"),
            },
            periods=(20, 60, 240),
        )
        active_ma_values = [row["15m"][20] for row in ma_contexts]
        result = run_backtest(
            bars=bars,
            active_ma_values=active_ma_values,
            ma_contexts=ma_contexts,
            strategy=MultiTimeframeMaStrategy(),
            initial_cash=10_000.0,
        )
        summary = summarize_backtest(result)

        self.assertEqual(len(bars), 24_000)
        self.assertEqual(summary["trade_count"], 4)
        self.assertGreater(summary["final_cash"], summary["initial_cash"])


if __name__ == "__main__":
    unittest.main()
