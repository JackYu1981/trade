from __future__ import annotations

from dataclasses import dataclass

from trade.models import StrategyContext, StrategyDecision, StrategyDefinition
from trade.rules.composites import RuleSet, StagedRuleSets
from trade.rules.ma_rules import BullishMaStackRule, EntryCrossAboveMaRule, ExitCloseBelowMaRule, PriceAboveMaRule
from trade.strategy_engine.registry import strategy_registry


@dataclass(frozen=True)
class MaStackConfig:
    timeframe: str
    fast_period: int
    mid_period: int
    slow_period: int


class MultiTimeframeMaStrategy:
    """Long-only multi-timeframe MA strategy skeleton exposed as a plugin example."""

    def __init__(
        self,
        *,
        execution_timeframe: str = "15m",
        execution_fast_period: int = 20,
        execution_mid_period: int = 60,
        execution_slow_period: int = 240,
        trend_timeframes: tuple[str, ...] = ("1h", "4h", "1d"),
    ) -> None:
        self.execution = MaStackConfig(
            timeframe=execution_timeframe,
            fast_period=execution_fast_period,
            mid_period=execution_mid_period,
            slow_period=execution_slow_period,
        )
        self.trend_filters = tuple(
            MaStackConfig(
                timeframe=timeframe,
                fast_period=execution_fast_period,
                mid_period=execution_mid_period,
                slow_period=execution_slow_period,
            )
            for timeframe in trend_timeframes
        )
        self.rule_sets = StagedRuleSets(
            trend=RuleSet(
                rules=tuple(
                    BullishMaStackRule(cfg.timeframe, cfg.fast_period, cfg.mid_period, cfg.slow_period, phase="trend")
                    for cfg in self.trend_filters
                )
            ),
            entry=RuleSet(
                rules=(
                    BullishMaStackRule(
                        self.execution.timeframe,
                        self.execution.fast_period,
                        self.execution.mid_period,
                        self.execution.slow_period,
                        phase="entry",
                    ),
                    PriceAboveMaRule(self.execution.timeframe, self.execution.fast_period, phase="entry"),
                    EntryCrossAboveMaRule(self.execution.timeframe, self.execution.fast_period, phase="entry"),
                )
            ),
            exit=RuleSet(
                rules=(
                    BullishMaStackRule(
                        self.execution.timeframe,
                        self.execution.fast_period,
                        self.execution.mid_period,
                        self.execution.slow_period,
                        phase="exit",
                    ),
                    PriceAboveMaRule(self.execution.timeframe, self.execution.fast_period, phase="exit"),
                    ExitCloseBelowMaRule(self.execution.timeframe, self.execution.fast_period, phase="exit"),
                )
            ),
            add=RuleSet(rules=()),
        )

    def definition(self) -> StrategyDefinition:
        return StrategyDefinition(
            strategy_id="demo.multi_timeframe_ma",
            name="Demo Multi-Timeframe MA",
            description="Example long-only strategy plugin built from composable MA rules.",
            parameters={
                "execution_timeframe": self.execution.timeframe,
                "fast_period": self.execution.fast_period,
                "mid_period": self.execution.mid_period,
                "slow_period": self.execution.slow_period,
                "trend_timeframes": [config.timeframe for config in self.trend_filters],
            },
        )

    def evaluate(self, context: StrategyContext) -> StrategyDecision:
        staged = self.rule_sets.evaluate(context)
        if context.has_position:
            exit_evaluation = staged.exit
            price_exit = exit_evaluation.results[-1]
            execution_stack = exit_evaluation.results[0]
            if not price_exit.passed and not execution_stack.passed:
                return StrategyDecision(
                    action="SELL",
                    reason="Execution MA stack broke down.",
                    rule_results=staged.combined_results("trend", "exit"),
                    metadata={"strategy_id": self.definition().strategy_id},
                )
            return StrategyDecision(
                action="SELL" if price_exit.passed else "HOLD",
                reason="Exit rule fired." if price_exit.passed else "Position remains open.",
                rule_results=staged.combined_results("trend", "exit"),
                metadata={"strategy_id": self.definition().strategy_id, "active_phase": "exit"},
            )

        trend_ok = staged.trend.all_passed()
        entry_ok = staged.entry.all_passed()
        should_buy = trend_ok and entry_ok
        return StrategyDecision(
            action="BUY" if should_buy else "HOLD",
            reason="Multi-timeframe MA conditions passed." if should_buy else "Entry conditions not satisfied.",
            rule_results=staged.combined_results("trend", "entry"),
            metadata={
                "strategy_id": self.definition().strategy_id,
                "active_phase": "entry",
                "add_rules_defined": bool(self.rule_sets.add.rules),
            },
        )


class DemoMaCrossStrategy(MultiTimeframeMaStrategy):
    """Backward-compatible name while the demo strategy evolves."""


strategy_registry.register("demo.multi_timeframe_ma", MultiTimeframeMaStrategy)
