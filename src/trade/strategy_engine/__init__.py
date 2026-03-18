"""Strategy composition and decision interfaces."""

from trade.strategy_engine.protocols import Strategy
from trade.strategy_engine.registry import strategy_registry

__all__ = ["Strategy", "strategy_registry"]
