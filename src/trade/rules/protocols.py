from __future__ import annotations

from typing import Protocol

from trade.models import RuleResult, StrategyContext


class Rule(Protocol):
    def evaluate(self, context: StrategyContext) -> RuleResult:
        ...
