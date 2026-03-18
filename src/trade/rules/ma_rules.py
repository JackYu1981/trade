from __future__ import annotations

from dataclasses import dataclass
from dataclasses import replace

from trade.models import MarketBar, RuleResult, StrategyContext
from trade.rules.primitives import bullish_ma_stack, entry_cross_above_ma, exit_close_below_ma, trend_above_ma


def _ma_values(context: StrategyContext, timeframe: str) -> dict[int, float | None]:
    ma_by_timeframe = context.features.get("ma_by_timeframe")
    if not isinstance(ma_by_timeframe, dict):
        raise ValueError("StrategyContext is missing 'ma_by_timeframe'")
    values = ma_by_timeframe.get(timeframe, {})
    if not isinstance(values, dict):
        raise ValueError(f"MA values for timeframe {timeframe} must be a dict")
    return values


@dataclass(frozen=True)
class BullishMaStackRule:
    timeframe: str
    fast_period: int
    mid_period: int
    slow_period: int
    phase: str = "trend"

    def evaluate(self, context: StrategyContext) -> RuleResult:
        return replace(
            bullish_ma_stack(
                _ma_values(context, self.timeframe),
                timeframe=self.timeframe,
                fast_period=self.fast_period,
                mid_period=self.mid_period,
                slow_period=self.slow_period,
            ),
            phase=self.phase,
        )


@dataclass(frozen=True)
class PriceAboveMaRule:
    timeframe: str
    period: int
    phase: str = "trend"

    def evaluate(self, context: StrategyContext) -> RuleResult:
        ma_value = _ma_values(context, self.timeframe).get(self.period)
        return replace(
            trend_above_ma(
                context.current_bar,
                ma_value,
                timeframe=self.timeframe,
                period=self.period,
            ),
            phase=self.phase,
        )


@dataclass(frozen=True)
class EntryCrossAboveMaRule:
    timeframe: str
    period: int
    phase: str = "entry"

    def evaluate(self, context: StrategyContext) -> RuleResult:
        previous_ma = context.features.get("previous_ma")
        normalized_previous_ma = float(previous_ma) if isinstance(previous_ma, (int, float)) else None
        current_ma = _ma_values(context, self.timeframe).get(self.period)
        return replace(
            entry_cross_above_ma(
                previous_bar=context.previous_bar,
                previous_ma=normalized_previous_ma,
                current_bar=context.current_bar,
                current_ma=current_ma,
                timeframe=self.timeframe,
                period=self.period,
            ),
            phase=self.phase,
        )


@dataclass(frozen=True)
class ExitCloseBelowMaRule:
    timeframe: str
    period: int
    phase: str = "exit"

    def evaluate(self, context: StrategyContext) -> RuleResult:
        ma_value = _ma_values(context, self.timeframe).get(self.period)
        return replace(
            exit_close_below_ma(
                context.current_bar,
                ma_value,
                timeframe=self.timeframe,
                period=self.period,
            ),
            phase=self.phase,
        )
