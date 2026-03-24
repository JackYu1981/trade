from __future__ import annotations

import json
from dataclasses import asdict

from trade.analysis.summary import analyze_backtest, curve_series
from trade.models import BacktestAnalysis, BacktestResult, DataQualityReport


def render_text_report(result: BacktestResult, data_quality_report: DataQualityReport | None = None) -> str:
    analysis = analyze_backtest(result)
    summary = analysis.summary
    lines = [
        f"Strategy: {summary['strategy_id']}",
        f"Strategy name: {result.strategy_name}",
        f"Strategy description: {result.strategy_description}",
        f"Symbol: {summary['symbol']}",
        f"Timeframe: {summary['timeframe']}",
        f"Initial cash: {summary['initial_cash']:.5f}",
        f"Final cash: {summary['final_cash']:.5f}",
        f"Net PnL: {summary['net_pnl']:.5f}",
        f"Total return: {summary['total_return_pct']:.2%}",
        f"Annualized return: {summary['annualized_return']:.2%}",
        f"Trades: {summary['trade_count']}",
        f"Win rate: {summary['win_rate']:.2%}",
        f"Profit factor: {_format_ratio(summary['profit_factor'])}",
        f"Expectancy: {summary['expectancy']:.5f}",
        f"Max drawdown: {summary['max_drawdown']:.2%}",
        f"Sharpe: {summary['sharpe']:.2f}",
        f"Avg holding: {summary['avg_holding_minutes']:.1f}m",
        f"Max win streak: {summary['max_win_streak']}",
        f"Max loss streak: {summary['max_loss_streak']}",
        f"Position mode: {result.strategy_parameters.get('position_mode', 'unspecified')}",
        "",
        "Strategy Parameters:",
    ]
    if result.strategy_parameters:
        for key, value in result.strategy_parameters.items():
            lines.append(f"- {key}: {value}")
    else:
        lines.append("- No strategy parameters recorded")

    lines.extend([
        "",
        "Curves:",
        f"- Equity start/end: {analysis.curve_metrics['equity_curve_start']} -> {analysis.curve_metrics['equity_curve_end']}",
        f"- Underwater start/end: {analysis.curve_metrics['underwater_curve_start']} -> {analysis.curve_metrics['underwater_curve_end']}",
        f"- Max drawdown duration bars: {analysis.curve_metrics['max_drawdown_duration_bars']}",
        "",
        "Data Quality:",
    ])
    lines.extend(_render_data_quality_lines(data_quality_report))
    lines.extend([
        "",
        "Review:",
    ])
    lines.extend(_render_review_lines(analysis))
    lines.extend([
        "",
        "Trade Log:",
    ])

    if result.trades:
        for trade in result.trades:
            lines.append(
                (
                    f"- {trade.side} {trade.entry_time.isoformat()} @ {trade.entry_price:.5f} "
                    f"-> {trade.exit_time.isoformat()} @ {trade.exit_price:.5f} | PnL {trade.pnl:.5f}"
                )
            )
    else:
        lines.append("- No completed trades")

    return "\n".join(lines)


def render_json_report(
    result: BacktestResult,
    *,
    data_quality_report: DataQualityReport | None = None,
    include_decisions: bool = False,
    include_equity_curve: bool = False,
) -> str:
    analysis = analyze_backtest(result)
    payload = {
        "analysis": {
            "summary": analysis.summary,
            "curve_metrics": analysis.curve_metrics,
            "blocked_action_counts": analysis.blocked_action_counts,
            "top_blocked_reasons": analysis.top_blocked_reasons,
            "suggestions": analysis.suggestions,
        },
        "strategy": {
            "id": result.strategy_id,
            "name": result.strategy_name,
            "description": result.strategy_description,
            "parameters": result.strategy_parameters,
        },
        "data_quality": _data_quality_payload(data_quality_report),
        "trades": [asdict(trade) for trade in result.trades],
    }
    if include_decisions:
        payload["decisions"] = result.decisions
    if include_equity_curve:
        payload["curves"] = curve_series(result)
    return json.dumps(payload, indent=2, default=str)


def _render_review_lines(analysis: BacktestAnalysis) -> list[str]:
    lines = [f"- Blocked HOLD decisions: {analysis.blocked_action_counts.get('HOLD', 0)}"]
    if analysis.top_blocked_reasons:
        reason_text = ", ".join(f"{reason}={count}" for reason, count in analysis.top_blocked_reasons)
        lines.append(f"- Top blocked reasons: {reason_text}")
    for suggestion in analysis.suggestions:
        lines.append(f"- Suggestion: {suggestion}")
    return lines


def _render_data_quality_lines(report: DataQualityReport | None) -> list[str]:
    if report is None:
        return ["- No data quality report available"]

    lines = [
        f"- Bars: {report.bar_count}",
        f"- Normalized symbol/timeframe: {report.symbol} / {report.timeframe}",
    ]
    if report.issues:
        for issue in report.issues:
            lines.append(f"- {issue.severity.upper()} {issue.code}: {issue.message}")
    else:
        lines.append("- No issues detected")
    return lines


def _data_quality_payload(report: DataQualityReport | None) -> dict[str, object] | None:
    if report is None:
        return None
    return {
        "symbol": report.symbol,
        "timeframe": report.timeframe,
        "bar_count": report.bar_count,
        "issues": [asdict(issue) for issue in report.issues],
    }


def _format_ratio(value: float | int | str) -> str:
    if value == float("inf"):
        return "inf"
    return f"{float(value):.2f}"
