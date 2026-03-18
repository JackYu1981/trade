from __future__ import annotations

from datetime import datetime, timedelta
import unittest

from trade.analysis.baseline import (
    build_trend_legs,
    build_window_legs,
    default_fish_window_config,
    find_swing_points,
    tradeable_legs,
)
from trade.models import FishWindowConfig, LegCriteria, MarketBar


def make_wave_bars() -> list[MarketBar]:
    closes = [1.1000, 1.0990, 1.1010, 1.1000, 1.1035, 1.1025, 1.1055, 1.1040, 1.1020]
    start = datetime(2026, 1, 1, 0, 0)
    bars: list[MarketBar] = []
    previous_close = closes[0]
    for index, close in enumerate(closes):
        open_ = previous_close
        bars.append(
            MarketBar(
                timestamp=start + timedelta(minutes=15 * index),
                symbol="EUR/USD",
                timeframe="15m",
                open=open_,
                high=max(open_, close) + 0.0003,
                low=min(open_, close) - 0.0003,
                close=close,
                volume=1000 + index,
            )
        )
        previous_close = close
    return bars


class BaselineTests(unittest.TestCase):
    def test_find_swing_points_marks_local_highs_and_lows(self) -> None:
        swings = find_swing_points(make_wave_bars(), window=1)

        self.assertGreaterEqual(len(swings), 4)
        self.assertEqual(swings[0].kind, "low")
        self.assertEqual(swings[1].kind, "high")

    def test_build_trend_legs_creates_tradeable_leg_from_history(self) -> None:
        criteria = LegCriteria(
            swing_window=1,
            min_move_points=15,
            min_duration_bars=1,
            point_size=0.0001,
        )

        legs = build_trend_legs(make_wave_bars(), criteria)
        valid = tradeable_legs(make_wave_bars(), criteria)

        self.assertTrue(legs)
        self.assertTrue(any(leg.direction == "up" for leg in legs))
        self.assertTrue(any(leg.is_tradeable for leg in valid))

    def test_window_legs_mark_tradeable_fish_on_15m_data(self) -> None:
        start = datetime(2026, 1, 1, 0, 0)
        bars: list[MarketBar] = []
        for index in range(220):
            close = 1.1000 + (0.00004 * index)
            bars.append(
                MarketBar(
                    timestamp=start + timedelta(minutes=15 * index),
                    symbol="EUR/USD",
                    timeframe="15m",
                    open=close - 0.0001,
                    high=close + 0.0003,
                    low=close - 0.0003,
                    close=close,
                    volume=1000 + index,
                )
            )

        legs = build_window_legs(
            bars,
            FishWindowConfig(
                window_bars=200,
                min_move_points_by_timeframe={"15m": 65.0},
                point_size=0.0001,
            ),
        )

        self.assertTrue(legs)
        self.assertTrue(all(leg.direction == "up" for leg in legs))
        self.assertTrue(all(leg.move_points >= 65.0 for leg in legs))

    def test_default_fish_window_config_contains_requested_thresholds(self) -> None:
        config = default_fish_window_config()

        self.assertEqual(config.window_bars, 200)
        self.assertEqual(config.min_move_points_by_timeframe["15m"], 65.0)
        self.assertEqual(config.min_move_points_by_timeframe["1h"], 150.0)
        self.assertEqual(config.min_move_points_by_timeframe["1d"], 200.0)


if __name__ == "__main__":
    unittest.main()
