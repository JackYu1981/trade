from __future__ import annotations

from datetime import datetime, timedelta
import unittest

from trade.analysis.baseline import (
    build_trend_legs,
    build_window_legs,
    default_fish_window_config,
    find_swing_points,
    identify_fish_body,
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

    def test_window_legs_do_not_overlap_after_first_tradeable_fish(self) -> None:
        start = datetime(2026, 1, 1, 0, 0)
        bars: list[MarketBar] = []
        for index in range(420):
            close = 1.1000 + (0.00005 * index)
            bars.append(
                MarketBar(
                    timestamp=start + timedelta(minutes=15 * index),
                    symbol="EUR/USD",
                    timeframe="15m",
                    open=close - 0.0001,
                    high=close + 0.0002,
                    low=close - 0.0002,
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

        self.assertGreaterEqual(len(legs), 2)
        for left, right in zip(legs, legs[1:]):
            self.assertLess(left.end_index, right.start_index)


class FishBodyTests(unittest.TestCase):
    def test_monotonic_up_fish_body_spans_largest_swing_pair(self) -> None:
        """All bars ascending — body should be the largest low→high swing pair."""
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
            body_swing_window=3,
        )

        self.assertTrue(legs)
        for leg in legs:
            self.assertIsNotNone(leg.body_start_index)
            self.assertIsNotNone(leg.body_move_points)
            self.assertGreater(leg.body_move_points, 0)
            self.assertGreaterEqual(leg.body_start_index, leg.start_index)
            self.assertLessEqual(leg.body_end_index, leg.end_index)

    def test_internal_wave_fish_body_is_max_same_direction_move(self) -> None:
        """Fish with internal oscillation — body is the segment with max move."""
        start = datetime(2026, 1, 1, 0, 0)
        # Build an up-trending sequence with a clear larger swing in the middle
        # Segment 1: slow rise (+200 pts over 30 bars)
        # Segment 2: dip (-100 pts over 10 bars)
        # Segment 3: strong rise (+500 pts over 40 bars)  <-- should be body
        # Segment 4: dip (-80 pts over 10 bars)
        # Segment 5: mild rise (+150 pts over 30 bars)
        closes: list[float] = []
        base = 1.1000
        for i in range(30):
            closes.append(base + 0.0200 * (i / 29.0))  # +200 pts
        base = closes[-1]
        for i in range(10):
            closes.append(base - 0.0100 * (i / 9.0))  # -100 pts
        base = closes[-1]
        for i in range(40):
            closes.append(base + 0.0500 * (i / 39.0))  # +500 pts
        base = closes[-1]
        for i in range(10):
            closes.append(base - 0.0080 * (i / 9.0))  # -80 pts
        base = closes[-1]
        for i in range(30):
            closes.append(base + 0.0150 * (i / 29.0))  # +150 pts

        bars: list[MarketBar] = []
        prev_close = closes[0]
        for index, close in enumerate(closes):
            bars.append(
                MarketBar(
                    timestamp=start + timedelta(minutes=15 * index),
                    symbol="EUR/USD",
                    timeframe="15m",
                    open=prev_close,
                    high=max(prev_close, close) + 0.0005,
                    low=min(prev_close, close) - 0.0005,
                    close=close,
                    volume=1000 + index,
                )
            )
            prev_close = close

        legs = build_window_legs(
            bars,
            FishWindowConfig(
                window_bars=len(bars),
                min_move_points_by_timeframe={"15m": 300.0},
                point_size=0.0001,
            ),
            body_swing_window=3,
        )

        self.assertTrue(legs)
        leg = legs[0]
        self.assertIsNotNone(leg.body_start_index)
        # Body should be in the middle segment (roughly bars 30-80)
        self.assertGreater(leg.body_start_index, 20)
        self.assertLess(leg.body_end_index, 90)
        # Body move should be the largest — close to 500 pts
        self.assertGreater(leg.body_move_points, 300)

    def test_insufficient_swings_body_equals_whole_fish(self) -> None:
        """Fish too short for swing detection — body should equal the whole fish."""
        start = datetime(2026, 1, 1, 0, 0)
        # Only 5 bars — too few for swing_window=3 (needs 2*3+1=7)
        bars: list[MarketBar] = []
        for index in range(5):
            close = 1.1000 + 0.0001 * index
            bars.append(
                MarketBar(
                    timestamp=start + timedelta(minutes=15 * index),
                    symbol="EUR/USD",
                    timeframe="15m",
                    open=close - 0.0001,
                    high=close + 0.0002,
                    low=close - 0.0002,
                    close=close,
                    volume=1000,
                )
            )

        from trade.models import TrendLeg

        leg = TrendLeg(
            direction="up",
            start_index=0,
            start_time=bars[0].timestamp,
            start_price=bars[0].low,
            end_index=4,
            end_time=bars[4].timestamp,
            end_price=bars[4].high,
            extreme_index=4,
            extreme_time=bars[4].timestamp,
            extreme_price=bars[4].high,
            duration_bars=4,
            move_points=40.0,
            is_tradeable=True,
        )

        result = identify_fish_body(bars, leg, swing_window=3, point_size=0.0001)
        self.assertEqual(result.body_start_index, leg.start_index)
        self.assertEqual(result.body_end_index, leg.end_index)
        self.assertEqual(result.body_move_points, leg.move_points)

    def test_down_fish_body_identified_correctly(self) -> None:
        """Down fish — body should be the largest high→low swing pair."""
        start = datetime(2026, 1, 1, 0, 0)
        bars: list[MarketBar] = []
        for index in range(220):
            close = 1.1200 - (0.00004 * index)
            bars.append(
                MarketBar(
                    timestamp=start + timedelta(minutes=15 * index),
                    symbol="EUR/USD",
                    timeframe="15m",
                    open=close + 0.0001,
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
            body_swing_window=3,
        )

        self.assertTrue(legs)
        for leg in legs:
            self.assertEqual(leg.direction, "down")
            self.assertIsNotNone(leg.body_start_index)
            self.assertIsNotNone(leg.body_move_points)
            self.assertGreater(leg.body_move_points, 0)

    def test_body_swing_window_none_leaves_body_fields_none(self) -> None:
        """Omitting body_swing_window should leave body fields as None."""
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
        for leg in legs:
            self.assertIsNone(leg.body_start_index)
            self.assertIsNone(leg.body_move_points)


if __name__ == "__main__":
    unittest.main()
