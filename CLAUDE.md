# CLAUDE.md — Trade Framework

## Project Overview

Library-first Python research framework for rule-based trading strategy analysis.
Data → Indicators → Rules → Strategy → Backtest → Report.

## Quick Reference

```bash
# Run tests
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v

# Run default strategy (single_position_ma_trend) on 15m data
PYTHONPATH=src .venv/bin/python -m trade.cli examples/eurusd_15m_long_demo.csv --symbol EUR/USD --timeframe 15m

# Run on 1h demo data
PYTHONPATH=src .venv/bin/python -m trade.cli examples/eurusd_1h_demo.csv --symbol EUR/USD --timeframe 1h --ma-periods 3 --execution-timeframe 1h --fast-period 3 --mid-period 3 --slow-period 3 --trend-timeframes 4h,1d

# JSON output for agent workflows
PYTHONPATH=src .venv/bin/python -m trade.cli examples/eurusd_15m_long_demo.csv --symbol EUR/USD --timeframe 15m --format json

# HTML report
PYTHONPATH=src .venv/bin/python -m trade.cli examples/eurusd_1h_demo.csv --symbol EURUSD=X --timeframe 60min --format html

# Download data via yfinance
PYTHONPATH=src .venv/bin/python -m trade.data.download_cli EURUSD=X examples/eurusd_15m_yf.csv --interval 15m --period 60d
```

## Architecture

```
src/trade/
  models.py          — All frozen dataclasses (MarketBar, RuleResult, StrategyDecision, Trade, BacktestResult, etc.)
  cli.py             — Main backtest CLI entrypoint
  data/              — CSV loader, yfinance provider, download CLI, quality checks, resampling, standards
  indicators/        — MA computation and multi-timeframe alignment
  rules/             — Rule protocol, primitives, MA rule classes, RuleSet/StagedRuleSets composition
  strategy_engine/   — Strategy protocol, registry, demo strategies (multi_timeframe_ma, single_position_ma_trend)
  backtest/          — Single-position backtest engine (long + short)
  analysis/          — KPI summary, curve analysis, ex-post baseline (swing/fish)
  reporting/         — Text, JSON, and HTML report renderers
```

## Key Conventions

- **MA not SMA**: Always use "MA" (arithmetic moving average), never "SMA"
- **Frozen dataclasses**: All model objects are immutable
- **Protocol-based**: Rules, Strategies, Providers use `typing.Protocol`
- **Registry pattern**: Strategies and data providers auto-register at import
- **Four rule stages**: `trend`, `entry`, `exit`, `add` — rules declare their phase
- **Framework vs strategy boundary**: Generic code in `src/trade/`, demo strategies are plugins in `strategy_engine/demo_strategy.py`, private strategies go to `strategies_private/` (gitignored)
- **Strategy metadata flows through pipeline**: StrategyDefinition → BacktestResult → Reports (no strategy-specific coupling in reporting)

## Dependencies

- Python 3.14.3 (local `.venv`)
- `yfinance>=0.2.65` — historical data download
- `plotly>=6.0.0` — HTML report charts
- No other external dependencies; keep it minimal

## File Roles

| File | Purpose |
|---|---|
| `AGENTS.md` | Codex (OpenAI) agent instructions — framework boundary, architecture, workflow |
| `spec.md` | System architecture specification with module responsibilities |
| `plans.md` | Milestone roadmap and implementation order |
| `task_plan.md` | Phase-level task tracking |
| `findings.md` | Design decisions and verification results |
| `progress.md` | Chronological development log — update when making significant changes |
| `README.md` | User-facing documentation |

## Development Rules

1. **Always run tests** after code changes: `PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v`
2. **Keep commits focused** — don't mix docs-only with feature work
3. **Don't commit datasets**, cached data, logs, or experiment outputs (see `.gitignore`)
4. **Update progress.md** with date-stamped entries for significant changes
5. **Preserve inspectable traces** — rule evaluation must produce structured RuleResult with IDs and reason codes
6. **No market-specific assumptions** in generic framework code
7. **Strategies are plugins** — registered via `strategy_registry.register()`, never hardcoded into the engine
