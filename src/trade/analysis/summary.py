from __future__ import annotations

from collections import Counter
from datetime import datetime
from math import sqrt

from trade.models import BacktestAnalysis, BacktestResult


def summarize_backtest(result: BacktestResult) -> dict[str, float | int | str]:
    wins = sum(1 for trade in result.trades if trade.pnl > 0)
    losses = sum(1 for trade in result.trades if trade.pnl < 0)
    total_return = result.final_cash - result.initial_cash
    total_return_pct = (result.final_cash / result.initial_cash - 1.0) if result.initial_cash else 0.0
    gross_profit = sum(trade.pnl for trade in result.trades if trade.pnl > 0)
    gross_loss = abs(sum(trade.pnl for trade in result.trades if trade.pnl < 0))
    avg_trade_pnl = total_return / len(result.trades) if result.trades else 0.0
    avg_win = gross_profit / wins if wins else 0.0
    avg_loss = gross_loss / losses if losses else 0.0
    profit_factor = gross_profit / gross_loss if gross_loss else (float("inf") if gross_profit > 0 else 0.0)
    expectancy = (
        (wins / len(result.trades)) * avg_win - (losses / len(result.trades)) * avg_loss
        if result.trades
        else 0.0
    )
    holding_minutes = [
        (trade.exit_time - trade.entry_time).total_seconds() / 60.0
        for trade in result.trades
    ]
    max_win_streak, max_loss_streak = _compute_streaks(result)
    bar_returns = _bar_returns(result.equity_curve)
    sharpe = _sharpe_ratio(bar_returns, result.timeframe)
    annualized_return = _annualized_return(result)
    max_drawdown, _, underwater_curve, peak_curve = _drawdown_stats(result.equity_curve)

    return {
        "symbol": result.symbol,
        "timeframe": result.timeframe,
        "strategy_id": result.strategy_id,
        "initial_cash": result.initial_cash,
        "final_cash": result.final_cash,
        "net_pnl": total_return,
        "total_return_pct": total_return_pct,
        "annualized_return": annualized_return,
        "trade_count": len(result.trades),
        "wins": wins,
        "losses": losses,
        "win_rate": wins / len(result.trades) if result.trades else 0.0,
        "gross_profit": gross_profit,
        "gross_loss": gross_loss,
        "profit_factor": profit_factor,
        "avg_trade_pnl": avg_trade_pnl,
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "expectancy": expectancy,
        "max_drawdown": max_drawdown,
        "sharpe": sharpe,
        "avg_holding_minutes": (sum(holding_minutes) / len(holding_minutes)) if holding_minutes else 0.0,
        "max_holding_minutes": max(holding_minutes) if holding_minutes else 0.0,
        "min_holding_minutes": min(holding_minutes) if holding_minutes else 0.0,
        "max_win_streak": max_win_streak,
        "max_loss_streak": max_loss_streak,
    }


def analyze_backtest(result: BacktestResult) -> BacktestAnalysis:
    summary = summarize_backtest(result)
    max_drawdown, max_drawdown_duration, underwater_curve, peak_curve = _drawdown_stats(result.equity_curve)
    blocked_reasons: Counter[str] = Counter()
    blocked_actions: Counter[str] = Counter()

    for decision in result.decisions:
        if decision["action"] == "HOLD":
            blocked_actions["HOLD"] += 1
        for rule_result in decision["rule_results"]:
            if not rule_result["passed"]:
                blocked_reasons[rule_result["reason_code"]] += 1

    suggestions: list[str] = []
    if summary["trade_count"] == 0:
        suggestions.append("No trades were executed. Relax entry filters or validate whether the market regime is too restrictive.")
    if blocked_reasons.get("indicator_unavailable", 0) > 0:
        suggestions.append("Some signals were blocked by unavailable indicators. Check dataset length against the selected lookbacks.")
    if float(summary["max_drawdown"]) > 0.05:
        suggestions.append("Maximum drawdown is elevated. Review exits, regime filters, and position sizing before increasing complexity.")
    if summary["trade_count"] and float(summary["net_pnl"]) <= 0.001:
        suggestions.append("Signal path is active but edge is weak. Review exit conditions, costs, and confirmation rules.")
    if not suggestions:
        suggestions.append("Use blocked reasons and trade distribution to decide the next strategy iteration.")

    return BacktestAnalysis(
        summary=summary,
        curve_metrics={
            "equity_curve_start": result.equity_curve[:5],
            "equity_curve_end": result.equity_curve[-5:],
            "peak_equity_curve_start": peak_curve[:5],
            "peak_equity_curve_end": peak_curve[-5:],
            "underwater_curve_start": underwater_curve[:5],
            "underwater_curve_end": underwater_curve[-5:],
            "max_drawdown_duration_bars": max_drawdown_duration,
        },
        blocked_action_counts=dict(blocked_actions),
        top_blocked_reasons=blocked_reasons.most_common(5),
        suggestions=suggestions,
    )


def curve_series(result: BacktestResult) -> dict[str, list[float]]:
    _, _, underwater_curve, peak_curve = _drawdown_stats(result.equity_curve)
    return {
        "equity_curve": result.equity_curve,
        "peak_equity_curve": peak_curve,
        "underwater_curve": underwater_curve,
    }


def _compute_streaks(result: BacktestResult) -> tuple[int, int]:
    max_win_streak = 0
    max_loss_streak = 0
    current_win_streak = 0
    current_loss_streak = 0
    for trade in result.trades:
        if trade.pnl > 0:
            current_win_streak += 1
            current_loss_streak = 0
        elif trade.pnl < 0:
            current_loss_streak += 1
            current_win_streak = 0
        else:
            current_win_streak = 0
            current_loss_streak = 0
        max_win_streak = max(max_win_streak, current_win_streak)
        max_loss_streak = max(max_loss_streak, current_loss_streak)
    return max_win_streak, max_loss_streak


def _bar_returns(equity_curve: list[float]) -> list[float]:
    if len(equity_curve) < 2:
        return []
    returns: list[float] = []
    for previous, current in zip(equity_curve, equity_curve[1:]):
        if previous == 0:
            returns.append(0.0)
        else:
            returns.append(current / previous - 1.0)
    return returns


def _sharpe_ratio(bar_returns: list[float], timeframe: str) -> float:
    if len(bar_returns) < 2:
        return 0.0
    mean_return = sum(bar_returns) / len(bar_returns)
    variance = sum((value - mean_return) ** 2 for value in bar_returns) / (len(bar_returns) - 1)
    if variance <= 0:
        return 0.0
    annualization = {
        "15m": sqrt(365 * 24 * 4),
        "1h": sqrt(365 * 24),
        "4h": sqrt(365 * 6),
        "1d": sqrt(365),
    }.get(timeframe, 1.0)
    return (mean_return / sqrt(variance)) * annualization


def _annualized_return(result: BacktestResult) -> float:
    if len(result.decisions) < 2 or result.initial_cash == 0:
        return 0.0
    start = datetime.fromisoformat(result.decisions[0]["timestamp"])
    end = datetime.fromisoformat(result.decisions[-1]["timestamp"])
    days = max((end - start).total_seconds() / 86400.0, 1 / 365)
    total_return = result.final_cash / result.initial_cash
    if total_return <= 0:
        return -1.0
    return total_return ** (365.0 / days) - 1.0


def _drawdown_stats(equity_curve: list[float]) -> tuple[float, int, list[float], list[float]]:
    if not equity_curve:
        return 0.0, 0, [], []
    peak_curve: list[float] = []
    underwater_curve: list[float] = []
    peak = equity_curve[0]
    max_drawdown = 0.0
    current_duration = 0
    max_duration = 0
    for value in equity_curve:
        peak = max(peak, value)
        peak_curve.append(peak)
        drawdown = (value / peak - 1.0) if peak else 0.0
        if abs(drawdown) < 1e-12:
            drawdown = 0.0
        underwater_curve.append(drawdown)
        if drawdown < 0:
            current_duration += 1
        else:
            current_duration = 0
        max_duration = max(max_duration, current_duration)
        max_drawdown = min(max_drawdown, drawdown)
    return abs(max_drawdown), max_duration, underwater_curve, peak_curve
