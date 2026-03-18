# Findings

## Repository State

- Current repository contains planning/docs only
- No dependency manifest existed at start of implementation
- Existing `.venv` uses Python 3.14.3
- Worktree is not clean before implementation; existing user changes are present in documentation files

## Working Assumptions

- Python is the intended implementation language based on existing `.venv`
- Milestone 1 should favor a simple CSV-driven demo over generalized ingestion
- A thin CLI is acceptable as long as core modules remain library-first

## Design Decisions

- Implement Milestone 1 using only the Python standard library
- Use a simple canonical bar model and CSV loader for the initial data path
- Keep rule evaluation traceable through structured result objects with IDs and reason codes
- Provide a thin `python -m trade.cli` entrypoint instead of a heavier packaging setup
- Treat `MA` as arithmetic moving average and avoid `SMA` naming/semantics in the public interface
- Add multi-timeframe MA preparation so `15m` source bars can align `1h`, `4h`, and `1d` MA values onto the base evaluation timeline
- Default strategy skeleton now targets `15m` execution with `1h/4h/1d` bullish MA-stack filters and `MA20/60/240`
- The framework now has a generic `StrategyContext` / `StrategyDefinition` contract plus a `StrategyRegistry`
- The demo MA strategy is now an example plugin rather than a hard-coded engine dependency
- Rules now also have a framework layer: rule protocols, reusable MA rule objects, and `RuleSet` composition
- The framework now supports four explicit rule stages: `trend`, `entry`, `exit`, and `add`
- Traditional KPI reporting now includes returns, drawdown, profit factor, expectancy, holding-duration stats, streaks, and sharpe
- Curve analysis now exposes equity snapshots, peak-equity snapshots, underwater snapshots, and drawdown duration
- Ex-post baseline analysis now has first-pass objects for `SwingPoint`, `TrendLeg`, and `LegCriteria`

## Verification Results

- `./.venv/bin/python -m pip install -r requirements.txt` completed successfully; the file is intentionally empty for this milestone
- `PYTHONPATH=src ./.venv/bin/python -m unittest discover -s tests -v` passed
- `PYTHONPATH=src ./.venv/bin/python -m trade.cli examples/eurusd_1h_demo.csv --symbol EUR/USD --timeframe 1h --ma-periods 3 --trend-timeframe 1h --trend-period 3 --entry-timeframe 1h --entry-period 3 --exit-timeframe 1h --exit-period 3` produced a successful text report with one completed trade
- Updated MA smoke command also passed with `--ma-periods 3 --trend-timeframe 1h --entry-timeframe 1h --exit-timeframe 1h`
- Added `examples/eurusd_15m_long_demo.csv`, a 24,000-row synthetic `15m` fixture spanning 250 days so `1d MA240` is available
- `PYTHONPATH=src ./.venv/bin/python -m trade.cli examples/eurusd_15m_long_demo.csv --symbol EUR/USD --timeframe 15m` produced 4 completed trades with net PnL `0.00029`
- `PYTHONPATH=src ./.venv/bin/python -m trade.cli examples/eurusd_15m_long_demo.csv --symbol EUR/USD --timeframe 15m --format json` now returns a compact analysis-first payload suitable for agent workflows

## Output Observations

- The current multi-timeframe MA skeleton now runs end-to-end on full `15m/1h/4h/1d` MA20/60/240 data
- The resulting trades are short-lived and low-PnL, which is useful as a baseline but too sensitive for realistic research use
- The current reporting shape is now better aligned to human + agent collaboration: summary, blocked reasons, and suggestions come first; large raw traces are optional
- The demo strategy is now closer to the target architecture because it assembles reusable rule objects instead of embedding all rule flow inline
- Stage ownership now lives at the rule-object layer, so the same rule primitive can be reused in different phases with different semantics
- Traditional KPI values are now available in both text and JSON reports, which makes the framework usable for standard trading-performance review before deeper strategy diagnostics
- The first-pass fish-body marker is intentionally parameterized by move size and duration so research can tune experience-based thresholds instead of hard-coding them
