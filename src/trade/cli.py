from __future__ import annotations

import argparse
from pathlib import Path

from trade.backtest.engine import run_backtest
from trade.data.csv_loader import load_ohlcv_csv
from trade.data.quality import inspect_bars
from trade.data.resample import TIMEFRAME_TO_MINUTES, resample_bars
from trade.data.standards import normalize_symbol, normalize_timeframe
from trade.indicators.moving_average import (
    DEFAULT_MA_PERIODS,
    DEFAULT_MA_TIMEFRAMES,
    build_multi_timeframe_ma_context,
)
from trade.reporting.html_report import render_html_report
from trade.reporting.text_report import render_json_report, render_text_report
from trade.strategy_engine import strategy_registry
from trade.strategy_engine import demo_strategy as _demo_strategy  # noqa: F401


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run a strategy backtest within the research framework.")
    parser.add_argument("csv_path", help="Path to the OHLCV CSV file")
    parser.add_argument("--strategy-id", default="demo.multi_timeframe_ma")
    parser.add_argument("--symbol", default="EUR/USD")
    parser.add_argument("--timeframe", default="15m")
    parser.add_argument("--ma-periods", default=",".join(str(period) for period in DEFAULT_MA_PERIODS))
    parser.add_argument("--ma-timeframes", default=",".join(DEFAULT_MA_TIMEFRAMES))
    parser.add_argument("--execution-timeframe")
    parser.add_argument("--fast-period", type=int, default=20)
    parser.add_argument("--mid-period", type=int, default=60)
    parser.add_argument("--slow-period", type=int, default=240)
    parser.add_argument("--trend-timeframes", default="1h,4h,1d")
    parser.add_argument("--initial-cash", type=float, default=10_000.0)
    parser.add_argument("--format", choices=("text", "json", "html"), default="text")
    parser.add_argument("--output-path")
    parser.add_argument("--include-decisions", action="store_true")
    parser.add_argument("--include-equity-curve", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    normalized_symbol = normalize_symbol(args.symbol)
    source_timeframe = normalize_timeframe(args.timeframe)
    execution_timeframe = normalize_timeframe(args.execution_timeframe) if args.execution_timeframe else source_timeframe
    trend_timeframes = tuple(
        normalize_timeframe(value.strip())
        for value in args.trend_timeframes.split(",")
        if value.strip()
    )
    requested_timeframes = tuple(
        normalize_timeframe(value.strip())
        for value in args.ma_timeframes.split(",")
        if value.strip()
    )
    if source_timeframe not in TIMEFRAME_TO_MINUTES:
        raise ValueError(f"Unsupported timeframe: {source_timeframe}")

    bars = load_ohlcv_csv(args.csv_path, symbol=normalized_symbol, timeframe=source_timeframe)
    data_quality_report = inspect_bars(bars)
    ma_periods = tuple(sorted({int(value) for value in args.ma_periods.split(",") if value}))
    unsupported_timeframes = [timeframe for timeframe in requested_timeframes if timeframe not in TIMEFRAME_TO_MINUTES]
    if unsupported_timeframes:
        raise ValueError(f"Unsupported MA timeframes: {', '.join(unsupported_timeframes)}")
    if execution_timeframe not in TIMEFRAME_TO_MINUTES:
        raise ValueError(f"Unsupported execution timeframe: {execution_timeframe}")

    source_minutes = TIMEFRAME_TO_MINUTES[source_timeframe]
    ma_timeframes = tuple(
        timeframe
        for timeframe in requested_timeframes
        if TIMEFRAME_TO_MINUTES[timeframe] >= source_minutes
    )
    if source_timeframe not in ma_timeframes:
        ma_timeframes = (source_timeframe, *ma_timeframes)
    if execution_timeframe not in ma_timeframes:
        raise ValueError(
            "execution timeframe must be present in the MA timeframe set after source-timeframe filtering"
        )

    bars_by_timeframe = {}
    for timeframe in ma_timeframes:
        bars_by_timeframe[timeframe] = bars if timeframe == source_timeframe else resample_bars(bars, timeframe)

    ma_contexts = build_multi_timeframe_ma_context(bars, bars_by_timeframe, ma_periods)
    active_ma_values = [row.get(execution_timeframe, {}).get(args.fast_period) for row in ma_contexts]
    strategy = strategy_registry.create(
        args.strategy_id,
        execution_timeframe=execution_timeframe,
        execution_fast_period=args.fast_period,
        execution_mid_period=args.mid_period,
        execution_slow_period=args.slow_period,
        trend_timeframes=trend_timeframes,
    )
    result = run_backtest(
        bars=bars,
        active_ma_values=active_ma_values,
        ma_contexts=ma_contexts,
        strategy=strategy,
        initial_cash=args.initial_cash,
    )

    if args.format == "json":
        print(
            render_json_report(
                result,
                data_quality_report=data_quality_report,
                include_decisions=args.include_decisions,
                include_equity_curve=args.include_equity_curve,
            )
        )
    elif args.format == "html":
        html = render_html_report(result, bars=bars, data_quality_report=data_quality_report)
        destination = Path(args.output_path) if args.output_path else _default_html_output_path(result)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(html, encoding="utf-8")
        print(destination)
    else:
        print(render_text_report(result, data_quality_report=data_quality_report))

    return 0

def _default_html_output_path(result: object) -> Path:
    if not hasattr(result, "strategy_id") or not hasattr(result, "symbol") or not hasattr(result, "timeframe"):
        return Path("reports") / "backtest-report.html"
    strategy_id = str(getattr(result, "strategy_id")).replace(".", "-")
    symbol = str(getattr(result, "symbol")).replace("/", "-")
    timeframe = str(getattr(result, "timeframe"))
    return Path("reports") / f"{strategy_id}-{symbol}-{timeframe}.html"


if __name__ == "__main__":
    raise SystemExit(main())
