from __future__ import annotations

from datetime import datetime, timedelta
import unittest

from trade.data.resample import resample_bars
from trade.indicators.moving_average import build_multi_timeframe_ma_context, moving_average
from trade.models import MarketBar


def make_15m_bars(count: int) -> list[MarketBar]:
    start = datetime(2026, 1, 1, 0, 0, 0)
    bars: list[MarketBar] = []
    for index in range(count):
        close = 100.0 + index
        bars.append(
            MarketBar(
                timestamp=start + timedelta(minutes=15 * index),
                symbol="EUR/USD",
                timeframe="15m",
                open=close - 0.2,
                high=close + 0.3,
                low=close - 0.4,
                close=close,
                volume=1000.0 + index,
            )
        )
    return bars


class MultiTimeframeMaTests(unittest.TestCase):
    def test_resample_15m_to_1h_builds_expected_bar_count(self) -> None:
        bars = make_15m_bars(16)
        hourly = resample_bars(bars, "1h")

        self.assertEqual(len(hourly), 4)
        self.assertEqual(hourly[0].open, bars[0].open)
        self.assertEqual(hourly[0].close, bars[3].close)
        self.assertEqual(hourly[-1].close, bars[-1].close)

    def test_multi_timeframe_ma_context_aligns_latest_completed_values(self) -> None:
        base_bars = make_15m_bars(16)
        hourly_bars = resample_bars(base_bars, "1h")
        context = build_multi_timeframe_ma_context(
            base_bars,
            {"15m": base_bars, "1h": hourly_bars},
            periods=(2,),
        )

        ma_15m = moving_average(base_bars, 2)
        ma_1h = moving_average(hourly_bars, 2)

        self.assertEqual(context[-1]["15m"][2], ma_15m[-1])
        self.assertEqual(context[-1]["1h"][2], ma_1h[-1])
        self.assertIsNone(context[0]["15m"][2])
        self.assertIsNone(context[0]["1h"][2])


if __name__ == "__main__":
    unittest.main()
