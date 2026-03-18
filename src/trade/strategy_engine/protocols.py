from __future__ import annotations

from typing import Protocol

from trade.models import StrategyContext, StrategyDecision, StrategyDefinition


class Strategy(Protocol):
    def definition(self) -> StrategyDefinition:
        ...

    def evaluate(self, context: StrategyContext) -> StrategyDecision:
        ...
