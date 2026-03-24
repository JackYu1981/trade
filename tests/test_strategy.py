from __future__ import annotations

from datetime import datetime
import unittest

from trade.models import MarketBar, StrategyContext
from trade.strategy_engine import strategy_registry
from trade.strategy_engine.demo_strategy import MultiTimeframeMaStrategy, SinglePositionMaTrendStrategy


class MultiTimeframeMaStrategyTests(unittest.TestCase):
    def test_strategy_buys_when_all_trend_filters_and_execution_rules_pass(self) -> None:
        strategy = MultiTimeframeMaStrategy(
            execution_timeframe="15m",
            execution_fast_period=20,
            execution_mid_period=60,
            execution_slow_period=240,
            trend_timeframes=("1h", "4h", "1d"),
        )
        decision = strategy.evaluate(
            StrategyContext(
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
                    "current_ma": 1.1002,
                    "previous_ma": 1.1002,
                    "ma_by_timeframe": {
                        "15m": {20: 1.1002, 60: 1.0998, 240: 1.0990},
                        "1h": {20: 1.1000, 60: 1.0990, 240: 1.0980},
                        "4h": {20: 1.1010, 60: 1.1000, 240: 1.0990},
                        "1d": {20: 1.1020, 60: 1.1010, 240: 1.1000},
                    },
                },
            )
        )

        self.assertEqual(decision.action, "BUY")

    def test_strategy_holds_when_higher_timeframe_stack_fails(self) -> None:
        strategy = MultiTimeframeMaStrategy(
            execution_timeframe="15m",
            execution_fast_period=20,
            execution_mid_period=60,
            execution_slow_period=240,
            trend_timeframes=("1h", "4h", "1d"),
        )
        decision = strategy.evaluate(
            StrategyContext(
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
                    "current_ma": 1.1002,
                    "previous_ma": 1.1002,
                    "ma_by_timeframe": {
                        "15m": {20: 1.1002, 60: 1.0998, 240: 1.0990},
                        "1h": {20: 1.0990, 60: 1.1000, 240: 1.0980},
                        "4h": {20: 1.1010, 60: 1.1000, 240: 1.0990},
                        "1d": {20: 1.1020, 60: 1.1010, 240: 1.1000},
                    },
                },
            )
        )

        self.assertEqual(decision.action, "HOLD")

    def test_strategy_registry_creates_registered_plugin(self) -> None:
        strategy = strategy_registry.create("demo.multi_timeframe_ma")
        self.assertEqual(strategy.definition().strategy_id, "demo.multi_timeframe_ma")


class SinglePositionMaTrendStrategyTests(unittest.TestCase):
    def test_strategy_buys_when_fast_ma_is_above_mid_and_price_is_above_fast_ma(self) -> None:
        strategy = SinglePositionMaTrendStrategy(execution_timeframe="15m", execution_fast_period=20, execution_mid_period=60)
        decision = strategy.evaluate(
            StrategyContext(
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
                previous_bar=None,
                has_position=False,
                position_side=None,
                features={"ma_by_timeframe": {"15m": {20: 1.1002, 60: 1.0998}}},
            )
        )

        self.assertEqual(decision.action, "BUY")

    def test_strategy_shorts_when_fast_ma_is_below_mid_and_price_is_below_fast_ma(self) -> None:
        strategy = SinglePositionMaTrendStrategy(execution_timeframe="15m", execution_fast_period=20, execution_mid_period=60)
        decision = strategy.evaluate(
            StrategyContext(
                current_bar=MarketBar(
                    timestamp=datetime(2026, 1, 1, 10, 15),
                    symbol="EUR/USD",
                    timeframe="15m",
                    open=1.1000,
                    high=1.1002,
                    low=1.0988,
                    close=1.0990,
                    volume=1000.0,
                ),
                previous_bar=None,
                has_position=False,
                position_side=None,
                features={"ma_by_timeframe": {"15m": {20: 1.0995, 60: 1.1001}}},
            )
        )

        self.assertEqual(decision.action, "SHORT")

    def test_strategy_exits_long_when_price_falls_below_fast_ma(self) -> None:
        strategy = SinglePositionMaTrendStrategy(execution_timeframe="15m", execution_fast_period=20, execution_mid_period=60)
        decision = strategy.evaluate(
            StrategyContext(
                current_bar=MarketBar(
                    timestamp=datetime(2026, 1, 1, 10, 30),
                    symbol="EUR/USD",
                    timeframe="15m",
                    open=1.1005,
                    high=1.1008,
                    low=1.0990,
                    close=1.0994,
                    volume=1000.0,
                ),
                previous_bar=None,
                has_position=True,
                position_side="LONG",
                features={"ma_by_timeframe": {"15m": {20: 1.0998, 60: 1.0992}}},
            )
        )

        self.assertEqual(decision.action, "SELL")

    def test_strategy_registry_creates_new_single_position_plugin(self) -> None:
        strategy = strategy_registry.create("demo.single_position_ma_trend")
        self.assertEqual(strategy.definition().strategy_id, "demo.single_position_ma_trend")


if __name__ == "__main__":
    unittest.main()
