from __future__ import annotations

from dataclasses import asdict

from trade.models import BacktestResult, MarketBar, StrategyContext, Trade
from trade.strategy_engine.protocols import Strategy


def run_backtest(
    bars: list[MarketBar],
    active_ma_values: list[float | None],
    ma_contexts: list[dict[str, dict[int, float | None]]],
    strategy: Strategy,
    initial_cash: float = 10_000.0,
) -> BacktestResult:
    if not bars:
        raise ValueError("bars must not be empty")
    if len(bars) != len(active_ma_values):
        raise ValueError("bars and active_ma_values must have the same length")
    if len(bars) != len(ma_contexts):
        raise ValueError("bars and ma_contexts must have the same length")

    strategy_definition = strategy.definition()
    cash = initial_cash
    open_position: tuple[str, object, float] | None = None
    trades: list[Trade] = []
    decisions: list[dict[str, object]] = []
    equity_curve: list[float] = []

    for index, bar in enumerate(bars):
        context = StrategyContext(
            current_bar=bar,
            previous_bar=bars[index - 1] if index > 0 else None,
            has_position=open_position is not None,
            position_side=open_position[0] if open_position is not None else None,
            features={
                "current_ma": active_ma_values[index],
                "previous_ma": active_ma_values[index - 1] if index > 0 else None,
                "ma_by_timeframe": ma_contexts[index],
            },
        )
        decision = strategy.evaluate(context)
        decision_record = {
            "timestamp": bar.timestamp.isoformat(),
            "action": decision.action,
            "reason": decision.reason,
            "rule_results": [asdict(result) for result in decision.rule_results],
        }

        if decision.action == "BUY" and open_position is None and index < len(bars) - 1:
            open_position = ("LONG", bar.timestamp, bar.close)
        elif decision.action == "SHORT" and open_position is None and index < len(bars) - 1:
            open_position = ("SHORT", bar.timestamp, bar.close)
        elif decision.action in {"SELL", "COVER"} and open_position is not None:
            side, entry_time, entry_price = open_position
            pnl = bar.close - entry_price if side == "LONG" else entry_price - bar.close
            cash += pnl
            trades.append(
                Trade(
                    side=side,
                    entry_time=entry_time,
                    entry_price=entry_price,
                    exit_time=bar.timestamp,
                    exit_price=bar.close,
                    pnl=pnl,
                )
            )
            open_position = None

        marked_equity = cash
        if open_position is not None:
            side, _, entry_price = open_position
            marked_equity += (bar.close - entry_price) if side == "LONG" else (entry_price - bar.close)

        equity_curve.append(marked_equity)
        decisions.append(decision_record)

    if open_position is not None:
        side, entry_time, entry_price = open_position
        final_bar = bars[-1]
        pnl = final_bar.close - entry_price if side == "LONG" else entry_price - final_bar.close
        cash += pnl
        trades.append(
            Trade(
                side=side,
                entry_time=entry_time,
                entry_price=entry_price,
                exit_time=final_bar.timestamp,
                exit_price=final_bar.close,
                pnl=pnl,
            )
        )

    return BacktestResult(
        symbol=bars[0].symbol,
        timeframe=bars[0].timeframe,
        strategy_id=strategy_definition.strategy_id,
        strategy_name=strategy_definition.name,
        strategy_description=strategy_definition.description,
        strategy_parameters=dict(strategy_definition.parameters),
        initial_cash=initial_cash,
        final_cash=cash,
        trades=trades,
        equity_curve=equity_curve,
        decisions=decisions,
    )
