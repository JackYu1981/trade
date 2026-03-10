# Milestone 1 Architecture Proposal

## Summary

Milestone 1 should establish a library-first research engine with a thin CLI and a future-compatible service layer that can later be reused by FastAPI without moving business logic. The milestone remains a vertical slice, but the architecture must make strategy composition, inspectable rule evaluation, and later contribution analysis first-class from the start.

The core design is:

- `core domain modules` hold data, indicators, rules, strategies, backtest, and analysis logic
- `service layer` orchestrates use cases across those modules
- `interface adapters` such as CLI now and FastAPI later call the same services
- `strategy definitions` use a hybrid model in M1: Python-native objects as the executable source of truth, with config-driven assembly for safe and future API-friendly composition

## Project Directory Tree

```text
trade/
├── spec.md
├── plans.md
├── README.md
├── pyproject.toml
├── .gitignore
├── data/
│   ├── raw/
│   ├── curated/
│   └── reports/
├── configs/
│   ├── data/
│   │   └── default_data.yaml
│   ├── indicators/
│   │   └── default_indicators.yaml
│   ├── strategies/
│   │   └── ma_trend_m1.yaml
│   └── backtests/
│       └── default_backtest.yaml
├── src/
│   ├── forex_research/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── types.py
│   │   ├── constants.py
│   │   ├── exceptions.py
│   │   ├── logging.py
│   │   ├── domain/
│   │   │   ├── market_data.py
│   │   │   ├── indicators.py
│   │   │   ├── rules.py
│   │   │   ├── strategy.py
│   │   │   ├── positions.py
│   │   │   ├── trades.py
│   │   │   ├── backtest.py
│   │   │   └── analysis.py
│   │   ├── data/
│   │   │   ├── providers/
│   │   │   │   ├── base.py
│   │   │   │   └── yfinance.py
│   │   │   ├── normalization.py
│   │   │   ├── storage.py
│   │   │   ├── timeframes.py
│   │   │   └── repository.py
│   │   ├── indicators/
│   │   │   ├── base.py
│   │   │   ├── moving_average.py
│   │   │   ├── rolling_levels.py
│   │   │   └── trend_context.py
│   │   ├── rules/
│   │   │   ├── base.py
│   │   │   ├── trend_filters.py
│   │   │   ├── entries.py
│   │   │   ├── exits.py
│   │   │   └── reason_codes.py
│   │   ├── strategy/
│   │   │   ├── base.py
│   │   │   ├── definitions.py
│   │   │   ├── builder.py
│   │   │   ├── composition.py
│   │   │   └── single_position.py
│   │   ├── backtest/
│   │   │   ├── engine.py
│   │   │   ├── portfolio.py
│   │   │   ├── metrics.py
│   │   │   └── ledger.py
│   │   ├── analysis/
│   │   │   ├── signals.py
│   │   │   ├── performance.py
│   │   │   ├── diagnostics.py
│   │   │   └── contributions.py
│   │   ├── reporting/
│   │   │   ├── models.py
│   │   │   ├── summary.py
│   │   │   ├── exporters.py
│   │   │   └── formatters.py
│   │   └── services/
│   │       ├── data_service.py
│   │       ├── indicator_service.py
│   │       ├── strategy_service.py
│   │       ├── backtest_service.py
│   │       ├── analysis_service.py
│   │       └── reporting_service.py
│   └── forex_research_cli/
│       ├── __init__.py
│       ├── main.py
│       ├── bootstrap.py
│       └── commands/
│           ├── fetch.py
│           ├── analyze.py
│           ├── backtest.py
│           └── report.py
└── tests/
    ├── conftest.py
    ├── fixtures/
    │   ├── market_data/
    │   ├── strategies/
    │   └── reports/
    ├── unit/
    │   ├── data/
    │   ├── indicators/
    │   ├── rules/
    │   ├── strategy/
    │   ├── backtest/
    │   ├── analysis/
    │   └── reporting/
    └── integration/
        ├── test_data_pipeline.py
        ├── test_strategy_pipeline.py
        ├── test_backtest_pipeline.py
        └── test_cli_workflows.py
```

## Service Layer Definition

### Service layer role

The service layer is the application boundary for all non-domain callers. CLI now and FastAPI later should depend on `services/*` only, not on raw rule, indicator, or engine modules. Services orchestrate workflows, validate use-case inputs, and assemble outputs, but they do not own trading logic.

### `data_service.py`

Purpose:
- fetch, normalize, persist, and load market data
- abstract provider and storage details from callers

Owned workflows:
- fetch one symbol and timeframe for a date range
- refresh local dataset
- load a prepared dataset for downstream use

Used by:
- CLI `fetch`
- future API dataset endpoints
- `indicator_service` and `backtest_service`

### `indicator_service.py`

Purpose:
- enrich canonical market data with configured indicator sets
- centralize indicator pipeline execution

Owned workflows:
- apply default indicator pack for M1
- apply strategy-required indicators before rule evaluation
- validate required columns exist before continuing

Used by:
- CLI `analyze`
- `strategy_service`
- future analysis endpoints

### `strategy_service.py`

Purpose:
- explicit strategy orchestration layer
- construct executable strategy objects from definitions/config
- evaluate how a strategy composes rules and emits actions

Owned workflows:
- load strategy definition by name or config
- assemble rule graph or ordered rule set
- expose strategy metadata, required indicators, and composition details
- evaluate strategy decisions over prepared market context

Why this exists separately:
- it becomes the stable API-facing entrypoint for “what strategy is being run”
- it isolates strategy composition from raw backtest execution
- it is the right place to preserve inspectable rule ordering, grouping, and metadata for future contribution analysis

M1 internal responsibilities:
- resolve trend filters, entry rules, and exit rules into one executable strategy
- maintain rule IDs, categories, parameters, and precedence
- return decision traces that show which rules passed, failed, or blocked action

Future API mapping:
- `/strategies`
- `/strategies/{id}`
- `/strategies/validate`
- `/strategies/compose`

### `backtest_service.py`

Purpose:
- run historical simulation using a strategy produced by `strategy_service`
- keep orchestration concerns outside the engine

Owned workflows:
- prepare inputs for backtest execution
- call engine with data, strategy, and backtest settings
- return raw result objects suitable for analysis/reporting

Boundary:
- `backtest/engine.py` remains pure simulation logic
- `backtest_service.py` is the use-case layer that coordinates data, indicators, strategy, and engine

Future API mapping:
- `/backtest/run`
- `/backtest/{id}`

### `analysis_service.py`

Purpose:
- turn raw simulation and decision traces into research outputs
- centralize interpretation logic separate from simulation and presentation

Owned workflows:
- signal analysis
- performance analysis
- diagnostic summaries
- future rule contribution analysis inputs

M1 responsibilities:
- summarize why signals occurred
- summarize which rules blocked or allowed entries
- derive analysis-ready tables from signal logs and trade logs
- expose structured outputs independent of terminal or HTTP formatting

Why this must be explicit now:
- the project is research-oriented, not only execution-oriented
- contribution analysis later should extend this layer rather than be bolted onto backtest code
- CLI and FastAPI can both request the same analysis artifacts

Future API mapping:
- `/analysis/summary`
- `/analysis/signals`
- `/analysis/diagnostics`
- `/analysis/contributions`

### `reporting_service.py`

Purpose:
- generate exportable deliverables from analysis and backtest results
- separate presentation/output formatting from analysis logic

Owned workflows:
- build summary report payloads
- export trade ledger, signal log, metrics, and diagnostics
- format outputs for terminal, JSON, CSV, and later API responses

M1 responsibilities:
- produce terminal-friendly summary
- produce machine-readable report bundle
- write files into `data/reports/` or return in-memory report objects

Why separate from `analysis_service.py`:
- analysis answers “what does the result mean?”
- reporting answers “how do we package and expose it?”

Future API mapping:
- `/results/{id}`
- `/reports/{id}`
- `/exports/{id}`

## Strategy Evaluation Boundary

### Design goal

`Strategy.evaluate()` must sit at a stable domain boundary:

- rich enough for multi-timeframe research and inspectable traces
- narrow enough to avoid leaking CLI, API, or backtest-engine orchestration into strategy logic
- structured enough to support later FastAPI serialization through service-layer DTO mapping

The recommended milestone-1 contract is:

- input: `EvaluationContext`
- output: `Decision`

### Input options compared

#### Option A: raw pandas row or dataframe slice

Advantages:
- fast to start
- minimal wrapper types
- convenient for indicator prototyping

Disadvantages:
- leaks storage shape into strategy logic
- weak semantics for multi-timeframe access
- difficult to evolve without touching every rule
- poor fit for explicit trace metadata and later API schemas
- encourages rules to reach into arbitrary columns rather than depend on a clear contract

Recommendation:
- reject for `Strategy.evaluate()`
- acceptable only at the data/indicator preparation boundary before domain objects are assembled

#### Option B: domain-level `MarketState`

Advantages:
- much cleaner than raw pandas
- keeps strategy logic on domain concepts
- easier to test than dataframe slices

Disadvantages:
- too narrow for milestone-1 needs if it only models current market/bar state
- does not naturally hold indicator values, timeframe views, trace metadata, or execution-relevant context
- tends to grow into an ad hoc catch-all if stretched to cover all evaluation needs

Recommendation:
- useful as a nested domain object inside the evaluation input
- not sufficient as the full `Strategy.evaluate()` input on its own

#### Option C: richer `EvaluationContext`

Advantages:
- explicit contract for multi-timeframe strategy evaluation
- keeps strategy independent from pandas and engine internals
- gives rules stable access to current bar, timeframe views, and precomputed indicators
- can carry trace IDs and evaluation metadata without coupling to transport layers
- maps cleanly to future API DTOs through the service layer

Disadvantages:
- more upfront modeling work
- risks becoming bloated if execution concerns are not kept disciplined

Recommendation:
- use this for milestone 1
- keep it intentionally narrow and strategy-facing rather than making it a generic container

### Recommended input model: `EvaluationContext`

`EvaluationContext` should contain only strategy-facing facts for one evaluation step.

Required milestone-1 fields:
- `strategy_id`
- `symbol`
- `primary_timeframe`
- `timestamp`
- `bar_index`
- `market`: current-bar market snapshot for the primary timeframe
- `views`: read-only timeframe views keyed by timeframe such as `1h`, `15m`, `1d`
- `features`: precomputed indicator and derived feature values keyed by stable feature IDs
- `position`: current position snapshot needed by exit logic
- `trace`: lightweight evaluation metadata such as evaluation ID and parent run ID

Important exclusions:
- no CLI or API request details
- no portfolio accounting internals beyond current position snapshot
- no order execution model details
- no reporting-format concerns

Design note:
- active protective constraints should not be embedded in `EvaluationContext` as strategy-owned logic inputs
- if the orchestrator needs them during the same step, they should live in a sibling execution-policy object outside the strategy boundary

### Output options compared

#### Option A: enum-like action only

Examples:
- `ENTER_LONG`
- `EXIT_LONG`
- `HOLD`

Advantages:
- simple
- easy to wire into a backtest engine

Disadvantages:
- throws away the main research value of the system
- cannot preserve triggered vs blocked rules
- forces later diagnostics to reconstruct reasoning from logs or side channels

Recommendation:
- reject for milestone 1

#### Option B: `Action` object with metadata

Advantages:
- better than a bare enum
- leaves room for some annotations

Disadvantages:
- still under-specified unless it grows into a richer decision envelope
- usually collapses strategy reasoning and execution intent into one vague object

Recommendation:
- viable only if expanded into the `Decision` shape below

#### Option C: richer `Decision`

Advantages:
- preserves intent, reasoning, and diagnostics together
- makes trace capture a first-class output instead of an afterthought
- supports later contribution analysis and API exposure without redesign
- keeps the backtest engine focused on applying a decision, not deriving one

Disadvantages:
- slightly heavier than the minimum needed for execution

Recommendation:
- use this for milestone 1

### Recommended output model: `Decision`

`Decision` should represent the strategy result for a single evaluation step.

Required milestone-1 fields:
- `strategy_id`
- `timestamp`
- `action`
- `direction`
- `trace_summary`
- `triggered_rule_ids`
- `blocked_rule_ids`
- `reason_codes`
- `diagnostics`

Optional milestone-1 fields:
- `proposed_stop`
- `risk_notes`
- `candidate_entry_tags`

Action semantics for M1:
- `ENTER_LONG`
- `EXIT_LONG`
- `HOLD`

Notes:
- the action remains intentionally simple because the backtest engine owns position transitions
- the surrounding decision object carries the research metadata the platform needs
- short-side expansion later can extend the action enum without changing the boundary shape

### Rule trace representation for milestone 1

Milestone 1 should store structured trace objects, not free-form strings.

Recommended shape:

1. `RuleTrace`
- `rule_id`
- `rule_name`
- `stage` such as `trend_filter`, `entry`, or `exit`
- `outcome` such as `passed`, `failed`, `blocked`, or `not_evaluated`
- `reason_codes`
- `observed_values`
- `thresholds`
- `message`

2. `DecisionTrace`
- `evaluation_id`
- `strategy_id`
- `timestamp`
- ordered list of `RuleTrace`
- final decision action
- aggregate triggered, failed, and blocked rule IDs

Milestone-1 trace design rules:
- preserve stable IDs rather than only labels
- keep observed values machine-readable
- preserve evaluation order
- distinguish `failed` from `blocked`
- allow `not_evaluated` when short-circuiting occurs

Why this is the right M1 representation:
- contribution analysis can aggregate rule outcomes directly
- diagnostics can explain both accepted and rejected entries
- blocked-entry analysis can isolate which rule or protective factor stopped a trade
- FastAPI later can expose the same shape through response models with minimal translation

### Protective-factor ownership

Protective factors should not live inside `Strategy.evaluate()`.

Reasoning:
- the spec defines them as high-priority safety switches, not strategy logic
- embedding them inside strategy composition would blur research signals with hard execution constraints
- keeping them outside the strategy preserves cleaner comparison of strategy quality vs protection policy

Recommended placement for milestone 1:
- a separate pre-check/post-check layer in backtest orchestration

Operational flow:
1. run protective pre-checks before strategy entry evaluation to determine whether entry is allowed
2. run `Strategy.evaluate(context)` for strategy intent
3. run protective post-checks against open-position state to determine whether an immediate forced exit overrides strategy hold/exit intent
4. pass the final executable action into the backtest engine state transition step

Boundary split:
- strategy decides what it wants to do
- protective policy decides what is permitted or mandatory
- backtest engine applies the final action to portfolio state

Milestone-1 representation:
- protective checks should emit trace records parallel to rule traces, but marked with a separate source/category such as `protective`
- final decision logs should record whether an action was strategy-triggered, protection-blocked, or protection-forced

## Strategy Definition Model

### Recommended approach: hybrid

Milestone 1 should use a hybrid approach.

Executable source of truth:
- pure Python strategy, rule, and condition objects inside the core engine

External assembly and selection:
- configuration-driven definitions that describe which strategy to build, which rules to include, and what parameters to supply

This is the right tradeoff for M1 because it keeps execution safe and deterministic while preparing for future CLI and API usage.

### Why not pure Python only

Pure Python objects alone are good for internal development, but they are weak for the future platform goals:

- hard to expose safely through API or web workflows
- difficult to validate externally
- poor fit for strategy sharing and cataloging
- harder to compare strategy definitions structurally

Pure Python only would make M1 fast to build but would create avoidable migration work in stage 2 and stage 3.

### Why not fully configuration-driven only

A fully config-driven rule system is too ambitious for M1 because:

- the rule language would become its own design problem
- validation, composition semantics, and error handling would expand significantly
- it risks forcing premature abstraction before the initial vertical slice is proven

That would slow milestone 1 and push effort away from proving the research engine.

### Hybrid model details

In M1, a strategy definition should have two layers:

1. Definition layer
- declarative metadata
- strategy ID and name
- enabled rule list
- rule ordering or grouping
- parameter values
- timeframe bindings
- output/reporting preferences if needed

2. Executable layer
- Python classes or dataclass-like objects implementing rules and strategy composition
- built from the definition layer by `strategy/builder.py` and orchestrated by `strategy_service.py`

Concrete M1 flow:

- config file names a strategy and its rule parameters
- `strategy_service.py` loads the config
- `strategy/builder.py` maps config entries to known Python rule classes
- the result is an executable strategy object used by backtest and analysis services

### First-class composition requirements

To support strategy/rule composition as a first-class concern, M1 strategy definitions must include:

- stable strategy ID
- stable rule IDs
- rule category: trend filter, entry, exit
- ordered composition or explicit evaluation stage
- parameter payload per rule
- enabled/disabled state
- human-readable description fields

Protective factors should be configured alongside the strategy run, but represented as a separate execution policy rather than as strategy-owned rules.

This metadata is necessary for later rule contribution analysis, even if M1 only logs it and does not yet compute advanced attribution.

### Rule contribution support in M1

M1 should not implement full contribution attribution, but its representations must preserve the raw ingredients:

- each decision record includes strategy ID and rule IDs
- each rule evaluation stores pass/fail/block outcome
- each protective evaluation stores block/force-exit outcome separately from strategy rules
- each signal/trade stores the set of rule reasons that led to it
- analysis modules can later aggregate these traces into contribution metrics

That means contribution support is primarily a representation and logging requirement in milestone 1, not a modeling requirement deferred to later.

## Validation Criteria

The architecture proposal is correct only if all of the following remain true:

- core engine modules under `src/forex_research/` contain no CLI, FastAPI, or notebook dependencies
- CLI commands call service modules rather than domain/backtest internals directly
- a future FastAPI layer could call the same service modules without refactoring domain code
- strategy definitions can be selected and built without arbitrary code execution from user input
- `Strategy.evaluate()` accepts a domain `EvaluationContext`, not raw pandas objects
- `Strategy.evaluate()` returns a structured `Decision`, not only an action enum
- rule and strategy metadata are preserved in a structured form suitable for later contribution analysis
- protective factors remain outside strategy composition and are enforced by orchestration policy
- analysis and reporting are separate concerns with separate service boundaries
- backtest engine remains reusable as a pure programmatic component

## Implementation Order

1. Establish repo scaffolding, package boundaries, and `src/` layout.
2. Define domain models and canonical data contracts, including `EvaluationContext`, `Decision`, `RuleTrace`, and protective-policy trace records.
3. Implement data layer and `data_service.py`.
4. Implement indicator layer and `indicator_service.py`.
5. Define rule interfaces, strategy definition schema, and strategy builder around the `EvaluationContext -> Decision` boundary.
6. Implement `strategy_service.py` as the composition boundary for strategy-owned rules and decision traces.
7. Implement single-position backtest orchestration with a separate protective pre-check/post-check layer plus `backtest_service.py`.
8. Add `analysis_service.py` for signal, diagnostic, and performance outputs.
9. Add `reporting_service.py` for terminal and file/report packaging.
10. Add thin CLI commands that call only service-layer workflows.
11. Add tests proving the same strategy flow works through service calls and CLI.

## Assumptions and defaults

- Milestone 1 remains a vertical slice, not a generic plugin marketplace.
- Config-driven strategy assembly is limited to known, trusted Python rule classes registered in the core engine.
- FastAPI is a future interface layer and is not implemented in M1.
- `plans.md` is the milestone 1 planning document for the repository.
