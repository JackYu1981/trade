# Trade

Trade is a research framework for rule-based trading strategy analysis across financial markets.

The project is library-first. It is intended to support historical data preparation, indicator computation, rule evaluation, strategy composition, backtesting, and analysis, with a thin CLI now and room for API integration later.

## Design Goals

- Keep the framework separate from private strategy implementations
- Make rule evaluation inspectable and explainable
- Support incremental research through a small, testable core
- Preserve a clean path to future API or service integration

## Supported Markets

Planned market coverage:

- Forex
- Crypto
- Equities
- Futures
- Other structured financial time-series datasets

Initial research focus:

- market: Forex
- instrument: EUR/USD
- primary timeframe: 1h
- secondary timeframes: 15m and 1d

## Repository Structure

Target high-level layout:

```text
src/
    trade/
        data/
        indicators/
        rules/
        strategy_engine/
        backtest/
        analysis/
        reporting/

tests/
configs/
examples/
```

Private strategy implementations are expected to live outside this public framework or in ignored local directories.

## Project Status

Status: milestone 1 implementation in progress with a runnable minimal vertical slice.

Current vertical slice:

- load normalized OHLCV data from CSV
- compute arithmetic moving averages (`MA`, not `SMA`)
- evaluate reusable rules with structured traces
- compose strategies as pluggable rule collections
- run a single-position backtest
- emit text or JSON reports with review suggestions
- support multi-timeframe MA preparation for `15m`, `1h`, `4h`, and `1d`
- support strategy registration so public example strategies stay separate from framework execution

Current strategy skeleton:

- execution timeframe: `15m`
- higher-timeframe trend filters: `1h`, `4h`, `1d`
- MA stack: `MA20 > MA60 > MA240`
- entry concept: `15m` close crosses above `15m MA20` while higher-timeframe stacks remain bullish
- exit concept: `15m` close falls below `15m MA20` or execution-timeframe MA stack breaks

## Framework Direction

The framework is being shaped around collaborative strategy research rather than a fixed end-user UI.

- framework modules handle data, indicators, rules, backtests, analysis, and reporting
- strategies are expected to be pluggable extensions
- rules are also expected to be reusable building blocks that strategies compose
- rule collections are expected to be organized by lifecycle stage: `trend`, `entry`, `exit`, and `add`
- AI agents and users can iterate on strategy definitions, run tests, inspect blocked reasons, and refine rules together

## Ex-Post Baseline

The framework now includes a first-pass ex-post market-leg baseline for post-trade comparison.

- it does not try to confirm breakouts in real time
- it scans full historical data after the fact
- it can mark candidate legs from swing structure
- it can also mark a simpler "fish" by scanning a fixed `200`-bar window
- it filters those fish legs by timeframe-specific move thresholds

This is intended to support questions such as:

- why did the strategy enter when it should not have entered
- why did the strategy fail to enter when it should have entered
- why did the strategy exit when it should not have exited
- why did the strategy fail to exit when it should have exited

Core objects:

- `SwingPoint`
- `TrendLeg`
- `LegCriteria`
- `FishWindowConfig`

Current implementation lives in [src/trade/analysis/baseline.py](/Users/I064337/ai/codex/trade/src/trade/analysis/baseline.py).

Key design rule:

- move thresholds and duration thresholds are configurable research inputs, not hard-coded truths

Current simplified fish-window defaults:

- `15m`: `200` bars, minimum move `65` points
- `1h`: `200` bars, minimum move `150` points
- `1d`: `200` bars, minimum move `200` points

Primary planning documents:

- `spec.md` for system architecture and responsibilities
- `plans.md` for milestone roadmap

## Current Layout

```text
src/
    trade/
        analysis/
        backtest/
        data/
        indicators/
        reporting/
        rules/
        strategy_engine/

tests/
examples/
```

## Quick Start

The current milestone implementation uses only the Python standard library.

Run the test suite:

```bash
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v
```

Run the demo backtest:

```bash
PYTHONPATH=src .venv/bin/python -m trade.cli examples/eurusd_1h_demo.csv --symbol EUR/USD --timeframe 1h --ma-periods 3 --execution-timeframe 1h --fast-period 3 --mid-period 3 --slow-period 3 --trend-timeframes 4h,1d
```

Run the default multi-timeframe MA skeleton on the long `15m` fixture:

```bash
PYTHONPATH=src .venv/bin/python -m trade.cli examples/eurusd_15m_long_demo.csv --symbol EUR/USD --timeframe 15m
```

Get compact JSON analysis for agent workflows:

```bash
PYTHONPATH=src .venv/bin/python -m trade.cli examples/eurusd_15m_long_demo.csv --symbol EUR/USD --timeframe 15m --format json
```
