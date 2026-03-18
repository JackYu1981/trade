from __future__ import annotations

import argparse

from trade.backtest.engine import run_backtest
from trade.data.csv_loader import load_ohlcv_csv
from trade.data.resample import TIMEFRAME_TO_MINUTES, resample_bars
from trade.indicators.moving_average import (
    DEFAULT_MA_PERIODS,
    DEFAULT_MA_TIMEFRAMES,
    build_multi_timeframe_ma_context,
)
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
    parser.add_argument("--execution-timeframe", default="15m")
    parser.add_argument("--fast-period", type=int, default=20)
    parser.add_argument("--mid-period", type=int, default=60)
    parser.add_argument("--slow-period", type=int, default=240)
    parser.add_argument("--trend-timeframes", default="1h,4h,1d")
    parser.add_argument("--initial-cash", type=float, default=10_000.0)
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument("--include-decisions", action="store_true")
    parser.add_argument("--include-equity-curve", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.timeframe not in TIMEFRAME_TO_MINUTES:
        raise ValueError(f"Unsupported timeframe: {args.timeframe}")

    bars = load_ohlcv_csv(args.csv_path, symbol=args.symbol, timeframe=args.timeframe)
    ma_periods = tuple(sorted({int(value) for value in args.ma_periods.split(",") if value}))
    requested_timeframes = tuple(value.strip() for value in args.ma_timeframes.split(",") if value.strip())
    unsupported_timeframes = [timeframe for timeframe in requested_timeframes if timeframe not in TIMEFRAME_TO_MINUTES]
    if unsupported_timeframes:
        raise ValueError(f"Unsupported MA timeframes: {', '.join(unsupported_timeframes)}")
    if args.execution_timeframe not in TIMEFRAME_TO_MINUTES:
        raise ValueError(f"Unsupported execution timeframe: {args.execution_timeframe}")

    source_minutes = TIMEFRAME_TO_MINUTES[args.timeframe]
    ma_timeframes = tuple(
        timeframe
        for timeframe in requested_timeframes
        if TIMEFRAME_TO_MINUTES[timeframe] >= source_minutes
    )
    if args.timeframe not in ma_timeframes:
        ma_timeframes = (args.timeframe, *ma_timeframes)
    if args.execution_timeframe not in ma_timeframes:
        raise ValueError(
            "execution timeframe must be present in the MA timeframe set after source-timeframe filtering"
        )

    bars_by_timeframe = {}
    for timeframe in ma_timeframes:
        bars_by_timeframe[timeframe] = bars if timeframe == args.timeframe else resample_bars(bars, timeframe)

    ma_contexts = build_multi_timeframe_ma_context(bars, bars_by_timeframe, ma_periods)
    active_ma_values = [row.get(args.execution_timeframe, {}).get(args.fast_period) for row in ma_contexts]
    strategy = strategy_registry.create(
        args.strategy_id,
        execution_timeframe=args.execution_timeframe,
        execution_fast_period=args.fast_period,
        execution_mid_period=args.mid_period,
        execution_slow_period=args.slow_period,
        trend_timeframes=tuple(
            value.strip()
            for value in args.trend_timeframes.split(",")
            if value.strip()
        ),
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
                include_decisions=args.include_decisions,
                include_equity_curve=args.include_equity_curve,
            )
        )
    else:
        print(render_text_report(result))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
