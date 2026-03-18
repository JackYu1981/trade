from __future__ import annotations

from collections.abc import Callable

from trade.strategy_engine.protocols import Strategy


StrategyFactory = Callable[..., Strategy]


class StrategyRegistry:
    def __init__(self) -> None:
        self._factories: dict[str, StrategyFactory] = {}

    def register(self, strategy_id: str, factory: StrategyFactory) -> None:
        if strategy_id in self._factories:
            raise ValueError(f"Strategy already registered: {strategy_id}")
        self._factories[strategy_id] = factory

    def create(self, strategy_id: str, **kwargs: object) -> Strategy:
        if strategy_id not in self._factories:
            raise KeyError(f"Unknown strategy: {strategy_id}")
        return self._factories[strategy_id](**kwargs)

    def list_strategies(self) -> list[str]:
        return sorted(self._factories)


strategy_registry = StrategyRegistry()
