# Progress

## 2026-03-18

- Initialized planning files for implementation phase
- Confirmed repository starts as docs-only
- Confirmed existing virtual environment is Python 3.14.3 with no project dependencies installed
- Read `spec.md` and `plans.md` to lock Milestone 1 boundaries
- Decided to implement the first vertical slice with standard library only
- Implemented package skeleton, demo strategy pipeline, sample dataset, and initial tests
- Fixed a backtest edge case where the engine created a same-bar final trade
- Updated README to reflect the implemented runnable slice and current commands
- Verified dependency install step, tests, and demo CLI execution
- Replaced public `SMA` naming with `MA`
- Added `15m -> 1h/4h/1d` resampling and multi-timeframe MA alignment utilities
- Added multi-timeframe MA tests and revalidated the CLI path
- Replaced the old single-MA demo strategy with a multi-timeframe MA strategy skeleton
- Generated a long synthetic `15m` fixture for `1d MA240` coverage
- Added an automated long-fixture test for the default multi-timeframe MA skeleton
- Verified the long-fixture CLI output: 4 trades and small positive PnL
- Introduced generic strategy contracts and a registry-driven plugin path
- Refactored the backtest engine to depend on strategy interfaces instead of the demo strategy class
- Added analysis-first reporting with review suggestions for agent collaboration
- Added rule protocols, MA rule objects, and rule-set composition
- Refactored the demo strategy to build decisions from reusable rule collections
- Added staged rule-set support for `trend`, `entry`, `exit`, and `add`
- Added tests to verify phase boundaries and staged rule aggregation
- Expanded the first analysis template with traditional trading KPIs and curve metrics
- Cleaned floating-point noise from underwater-curve output for more readable reports
- Added ex-post baseline objects and a swing/leg marker for post-trade comparison
- Documented the baseline as a historical benchmark, not a realtime entry model

## 2026-03-24

- Added explicit `position_side` to `StrategyContext` so strategies can implement long/short logic without coupling to the backtest engine
- Extended `BacktestResult` with strategy name, description, and parameters so reports can render plugin-defined strategy contracts generically
- Added reusable MA pair-order rules for `fast > mid` and `fast < mid` conditions
- Added `demo.single_position_ma_trend`, a bidirectional single-position MA strategy plugin using `MA20/MA60` trend gating and `MA20` exits
- Extended the backtest engine to support `LONG` and `SHORT` positions in the same single-position framework
- Updated text, JSON, and HTML reports to show strategy metadata and execution rules
- Switched the CLI default strategy to `demo.single_position_ma_trend`
- Verified strategy, pipeline, and reporting tests all pass after the framework changes

## 2026-04-01

- Added fish body (鱼身) identification within existing fish/trend legs
- Extended `TrendLeg` with 7 optional `body_*` fields for body start/end/move
- Implemented `identify_fish_body()` in `baseline.py` using swing-point analysis within each fish
- When swing points are insufficient (monotonic fish), body defaults to the whole fish
- Integrated body detection into `build_window_legs()` via optional `body_swing_window` parameter
- Added `DEFAULT_BODY_SWING_WINDOW = 5` based on empirical testing across 1h (730d) and 15m (60d) EUR/USD data
- Updated HTML report to render fish body as darker vrect overlay on existing fish background
- Added 5 new tests for fish body: monotonic up, internal wave, insufficient swings, down fish, and None passthrough
- All 44 tests pass (39 existing + 5 new)
