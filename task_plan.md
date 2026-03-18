# Task Plan

## Goal

Implement Milestone 1 as a runnable minimal vertical slice for the public trading framework:
data -> indicators -> rules -> strategy -> backtest -> report.

## Constraints

- Keep framework code separate from private strategy logic
- Prefer working implementations over empty abstractions
- Preserve a runnable vertical slice
- Keep the design library-first with a thin CLI
- Avoid overengineering and market-specific lock-in beyond the demo slice

## Phases

| Phase | Status | Notes |
|---|---|---|
| Create planning files and capture repo state | complete | Repository is docs-only; local worktree already has unrelated user edits |
| Read implementation constraints from spec and plans | complete | Milestone 1 confirmed as minimal vertical slice with inspectable traces |
| Scaffold Python package and minimal CLI | complete | Added `src/trade`, `pyproject.toml`, sample data, and runnable `python -m trade.cli` entrypoint |
| Implement milestone-1 vertical slice modules | complete | Implemented CSV loader, MA indicator path, inspectable rules, demo strategy, single-position backtest, analysis, and reporting |
| Extend framework for multi-timeframe MA support | complete | Added `15m -> 1h/4h/1d` resample/alignment support and a multi-timeframe MA strategy skeleton |
| Add tests and run minimal verification | complete | Expanded tests for multi-timeframe alignment and strategy decisions; validation passes |
| Refactor toward framework-first strategy plugins and agent-oriented reporting | complete | Added generic strategy contracts, registry-driven strategy creation, analysis review output, and kept demo strategy as a plugin |
| Extract rule objects and rule composition as reusable framework primitives | complete | Added rule protocols, rule sets, MA rule objects, and updated the demo strategy to compose rules rather than hard-code them inline |
| Add four-stage rule collection framework (`trend`, `entry`, `exit`, `add`) | complete | Added staged rule sets/evaluations so future strategies can organize logic by lifecycle phase |
| Expand traditional KPI and curve analysis template | complete | Added return, drawdown, profit factor, expectancy, sharpe, holding stats, streaks, and curve snapshots |
| Add ex-post market-leg baseline objects for post-trade comparison | in_progress | Implement swing points, trend legs, configurable move/time criteria, and documentation for fish-body benchmark analysis |

## Errors Encountered

| Error | Attempt | Resolution |
|---|---|---|
| `setuptools` and `wheel` absent from `.venv` | 1 | Avoid dependency on editable-install workflow; keep runtime and tests runnable directly from source |
| Backtest opened a new position on the final bar and force-closed it immediately | 1 | Disallow new entries on the last evaluation bar to avoid zero-holding-period trades |
