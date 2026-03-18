from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class MarketBar:
    timestamp: datetime
    symbol: str
    timeframe: str
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0


@dataclass(frozen=True)
class RuleResult:
    rule_id: str
    passed: bool
    reason_code: str
    message: str
    phase: str = "unspecified"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class StrategyDecision:
    action: str
    reason: str
    rule_results: list[RuleResult]
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class StrategyContext:
    current_bar: MarketBar
    previous_bar: MarketBar | None
    has_position: bool
    features: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class StrategyDefinition:
    strategy_id: str
    name: str
    description: str
    parameters: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class LegCriteria:
    swing_window: int
    min_move_points: float
    min_duration_bars: int
    max_duration_bars: int | None = None
    point_size: float = 0.0001


@dataclass(frozen=True)
class SwingPoint:
    bar_index: int
    timestamp: datetime
    price: float
    kind: str


@dataclass(frozen=True)
class TrendLeg:
    direction: str
    start_index: int
    start_time: datetime
    start_price: float
    end_index: int
    end_time: datetime
    end_price: float
    extreme_index: int
    extreme_time: datetime
    extreme_price: float
    duration_bars: int
    move_points: float
    is_tradeable: bool


@dataclass(frozen=True)
class Trade:
    side: str
    entry_time: datetime
    entry_price: float
    exit_time: datetime
    exit_price: float
    pnl: float


@dataclass(frozen=True)
class BacktestResult:
    symbol: str
    timeframe: str
    strategy_id: str
    initial_cash: float
    final_cash: float
    trades: list[Trade]
    equity_curve: list[float]
    decisions: list[dict[str, Any]]


@dataclass(frozen=True)
class BacktestAnalysis:
    summary: dict[str, float | int | str]
    curve_metrics: dict[str, Any]
    blocked_action_counts: dict[str, int]
    top_blocked_reasons: list[tuple[str, int]]
    suggestions: list[str]
