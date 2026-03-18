from __future__ import annotations

from dataclasses import dataclass

from trade.models import RuleResult, StrategyContext
from trade.rules.protocols import Rule


@dataclass(frozen=True)
class RuleSetEvaluation:
    results: list[RuleResult]

    def all_passed(self) -> bool:
        return all(result.passed for result in self.results)

    def any_passed(self) -> bool:
        return any(result.passed for result in self.results)


@dataclass(frozen=True)
class RuleSet:
    rules: tuple[Rule, ...]

    def evaluate(self, context: StrategyContext) -> RuleSetEvaluation:
        return RuleSetEvaluation(results=[rule.evaluate(context) for rule in self.rules])


@dataclass(frozen=True)
class StagedRuleSets:
    trend: RuleSet = RuleSet(rules=())
    entry: RuleSet = RuleSet(rules=())
    exit: RuleSet = RuleSet(rules=())
    add: RuleSet = RuleSet(rules=())

    def evaluate(self, context: StrategyContext) -> "StagedRuleEvaluations":
        return StagedRuleEvaluations(
            trend=self.trend.evaluate(context),
            entry=self.entry.evaluate(context),
            exit=self.exit.evaluate(context),
            add=self.add.evaluate(context),
        )


@dataclass(frozen=True)
class StagedRuleEvaluations:
    trend: RuleSetEvaluation
    entry: RuleSetEvaluation
    exit: RuleSetEvaluation
    add: RuleSetEvaluation

    def phase_results(self, phase: str) -> RuleSetEvaluation:
        return getattr(self, phase)

    def combined_results(self, *phases: str) -> list[RuleResult]:
        results: list[RuleResult] = []
        for phase in phases:
            results.extend(self.phase_results(phase).results)
        return results
