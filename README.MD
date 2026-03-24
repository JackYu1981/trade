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
- download real historical data through pluggable providers
- normalize symbol and timeframe inputs before research execution
- inspect imported bars for data-quality issues before backtests
- compute arithmetic moving averages (`MA`, not `SMA`)
- evaluate reusable rules with structured traces
- compose strategies as pluggable rule collections
- run a single-position backtest
- emit text or JSON reports with review suggestions
- support multi-timeframe MA preparation for `15m`, `1h`, `4h`, and `1d`
- support strategy registration so public example strategies stay separate from framework execution
- carry strategy metadata through the backtest result so reports can render plugin-defined rules without coupling to specific strategies
- carry explicit position side through strategy context so long/short logic stays outside the engine

Current strategy skeleton:

- execution timeframe: `15m`
- higher-timeframe trend filters: `1h`, `4h`, `1d`
- MA stack: `MA20 > MA60 > MA240`
- entry concept: `15m` close crosses above `15m MA20` while higher-timeframe stacks remain bullish
- exit concept: `15m` close falls below `15m MA20` or execution-timeframe MA stack breaks

Current default execution strategy:

- single-position
- bidirectional
- long entry: `MA20 > MA60` and `close > MA20`
- long exit: `close < MA20`
- short entry: `MA20 < MA60` and `close < MA20`
- short exit: `close > MA20`
- no pyramiding, no simultaneous long/short exposure

## Framework Direction

The framework is being shaped around collaborative strategy research rather than a fixed end-user UI.

- framework modules handle data, indicators, rules, backtests, analysis, and reporting
- market-data providers are expected to be pluggable so public adapters can grow without changing core consumers
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

The current milestone implementation keeps the core backtest slice lightweight, with `yfinance` added for real historical data ingestion.

Note:

- real-data download now uses `yfinance`, so `requirements.txt` is no longer standard-library-only
- the download entrypoint is provider-driven and keeps canonical CSV output stable across providers

Current download architecture:

- `DownloadRequest` defines provider, symbol, timeframe, and time scope
- `LiveDataRequest` and `MarketSnapshot` define the separate realtime contract
- `CachePolicy` controls local cache directory and refresh behavior
- `ProviderSettings` carries symbol mapping, interval mapping, credentials, and provider-specific extra parameters
- `download_market_data(...)` orchestrates provider execution and canonical CSV output
- provider metadata is carried by `ProviderSpec` and `ProviderCapabilities`
- `yfinance` is the first historical provider; future providers such as `tushare`, `akshare`, or broker streams can plug into the same interface
- historical download and realtime quote access are intentionally separated so future signal generation does not distort the backtest ingestion path
- imported bars are normalized through shared symbol/timeframe standards and can be checked with the data-quality inspector
- CLI and JSON reports include data-quality context so import problems are visible before strategy conclusions are trusted
- static HTML reporting is available for readable backtest review, including candlestick charts, trade markers, KPI cards, equity curves, and strategy parameter contracts

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

Run the multi-timeframe MA skeleton explicitly:

```bash
PYTHONPATH=src .venv/bin/python -m trade.cli examples/eurusd_15m_long_demo.csv --symbol EUR/USD --timeframe 15m --strategy-id demo.multi_timeframe_ma
```

Get compact JSON analysis for agent workflows:

```bash
PYTHONPATH=src .venv/bin/python -m trade.cli examples/eurusd_15m_long_demo.csv --symbol EUR/USD --timeframe 15m --format json
```

Generate a static HTML report:

```bash
PYTHONPATH=src .venv/bin/python -m trade.cli examples/eurusd_1h_demo.csv --symbol EURUSD=X --timeframe 60min --format html
```

Download real Yahoo Finance history to normalized CSV:

```bash
PYTHONPATH=src .venv/bin/python -m trade.data.download_cli EURUSD=X examples/eurusd_15m_yf.csv --interval 15m --period 60d
```

Download a fixed historical range and reuse local cache on later runs:

```bash
PYTHONPATH=src .venv/bin/python -m trade.data.download_cli EURUSD=X examples/eurusd_1h_2025.csv --interval 1h --start 2025-01-01 --end 2025-03-31
```

Refresh cache explicitly:

```bash
PYTHONPATH=src .venv/bin/python -m trade.data.download_cli EURUSD=X --interval 15m --period 60d --refresh-cache
```

Apply provider-side symbol or interval mapping from the CLI:

```bash
PYTHONPATH=src .venv/bin/python -m trade.data.download_cli EURUSD --provider akshare --interval 1h --start 2025-01-01 --end 2025-03-31 --symbol-map EURUSD=FX_EURUSD --interval-map 1h=60m --provider-option market=forex
```

List currently registered download providers:

```bash
PYTHONPATH=src .venv/bin/python -m trade.data.download_cli --list-providers
```

List providers with capability details:

```bash
PYTHONPATH=src .venv/bin/python -m trade.data.download_cli --list-providers --verbose-providers
```

The downloaded CSV uses the same canonical columns as local demo data:

```text
timestamp,open,high,low,close,volume
```

Planned provider evolution:

- `yfinance`: public historical adapter for development and smoke validation
- `tushare`: credential-backed historical provider with provider-specific symbol and frequency mapping
- `akshare`: free/public China-market oriented provider with mapping and normalization hooks
- broker or market-data stream providers: separate realtime implementations that return `MarketSnapshot`
