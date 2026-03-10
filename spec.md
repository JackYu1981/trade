# Forex Strategy Research System

## 1. Project Overview

This project aims to build a Python-based strategy research and analysis tool for the forex market.

The system will focus on analyzing historical market data, exploring trend-following strategies, performing backtesting, and generating research insights.

The first phase will focus on building a stable research framework, including:

- data ingestion
- local data storage
- multi-timeframe analysis
- strategy research
- backtesting support

This project is research-focused, not a live trading system in the first version.

The system should support iterative development through milestones. Each milestone may focus on a specific part of the system, while the long-term scope includes all core components.

---

## 2. Target Market

### Primary Market

Forex (Foreign Exchange Market)

### Primary Instrument

EUR/USD

Reasons:

- high liquidity
- strong availability of historical data
- suitable for quantitative strategy research
- widely used benchmark pair in forex analysis

### Future Expansion

The system architecture should allow future expansion to additional currency pairs such as:

- GBP/USD
- USD/JPY
- AUD/USD
- USD/CHF

---

## 3. Data Source Strategy

### Primary Data Source

The initial version of the system will use yfinance as the primary market data source.

Primary symbol:

- EURUSD=X

Reasons:

- easy to integrate with Python
- suitable for rapid prototyping
- sufficient for initial strategy research and backtesting
- low setup complexity

### Future Data Source Extension

The system should be designed to support OANDA API in the future.

Reasons:

- more professional forex data access
- better alignment with live trading workflows
- potential support for more advanced market data access

### Data Source Design Requirement

The data layer should be abstracted so that multiple providers can be supported in the future without rewriting the strategy engine.

---

## 4. Data Provider Architecture

The system should abstract the data provider layer.

Suggested flow:

Data Source → Data Provider → Strategy Engine

Possible provider implementations:

- YFinanceProvider
- OandaProvider

This architecture should allow future provider switching with minimal impact on the rest of the system.

---

## 5. Strategy Direction

### Initial Strategy Type

The initial strategy focus will be:

Trend-following strategies

The first version should prioritize simple, explainable, research-friendly trend-following methods rather than overly complex models.

This project is explicitly not intended to be a high-frequency quantitative trading system.

The intended trading philosophy is closer to classical trend-following, where the key difficulty is waiting for high-quality opportunities rather than trading frequently.

### Trading Philosophy

The desired style is to identify and follow the core part of a trend.

A full trend may be loosely viewed as:

- head of the move
- body of the move
- tail of the move

The strategy should aim to:

- avoid unstable and noisy early movement near the "head"
- capture the more stable "body" of the trend
- avoid violent and unstable behavior near the "tail"

The goal is not to catch every market movement, but to participate in the most structured part of the trend.

### Initial Signal Basis

The initial analysis will focus on:

- moving averages
- price action / quote behavior
- trend alignment across multiple timeframes

---

## 6. Timeframe Design

### Primary Timeframe

The primary analysis timeframe will be:

- 1 hour

This timeframe will serve as the main basis for signal generation and trend analysis.

### Secondary Timeframes

The system should also consider:

- 15 minutes
- 1 day

### Multi-timeframe Logic

Multi-timeframe resonance / alignment is an important part of the intended strategy framework.

Examples of intended use:

- daily timeframe for higher-level market bias
- 1-hour timeframe for main trend analysis and signal generation
- 15-minute timeframe for finer-grained confirmation or timing

The exact rules for multi-timeframe resonance will be defined later in more detail.

---

## 7. Functional Scope

The project will eventually include all of the following core capabilities:

### A. Data Fetching and Cleaning

- download historical EUR/USD data
- normalize and clean multi-timeframe data
- handle missing values and timestamp consistency
- provide reusable local datasets

### B. Indicator and Trend Analysis

- calculate moving averages and related indicators
- analyze price structure and trend state
- evaluate multi-timeframe alignment

### C. Strategy Signal Generation

- generate trading signals based on explicit rules
- support long / short / no-trade decisions
- make signal logic explainable and inspectable

### D. Backtesting and Evaluation

- backtest strategy rules on historical data
- evaluate return, drawdown, win rate, and other metrics
- compare different rule combinations

### Milestone Principle

All four areas (A/B/C/D) are within project scope.

However, development should proceed incrementally by milestones. Each milestone may focus on only part of the system, while contributing to the overall framework.

---

## 8. Rule Engine Philosophy

This system is a strategy analysis tool, not an execution-focused live trading tool.

The core idea is to define strategy logic using modular rules.

Each rule should be treated as a reusable building block that can be:

- added
- removed
- combined
- reordered
- tested independently

The first version of the rule system will focus on three major rule categories.

### A. Trend Filter Rules

These rules define the broader market direction and determine whether market conditions are aligned with the intended trend-following logic.

Trend definition should remain flexible and support multiple approaches.

#### A1. Market Structure Based Trend

Trend may be defined using price structure.

Examples:

Uptrend:

- Higher High (HH)
- Higher Low (HL)

Downtrend:

- Lower High (LH)
- Lower Low (LL)

This structure-based approach should be supported for price action style strategies.

#### A2. Moving Average Context

The system will initially support the following moving averages:

- MA20
- MA60
- MA240

These moving averages may be used to evaluate:

- trend direction
- price relative position
- dynamic support/resistance
- multi-timeframe trend alignment

The implementation should allow flexible configuration of moving average periods.

#### A3. Range and Breakout Logic

The system should support custom indicators based on rolling window calculations.

Examples:

- Highest(N)
- Lowest(N)

Example:

- Highest(60)
- Lowest(60)

These indicators may be used to determine:

- consolidation ranges
- breakout conditions
- volatility contraction

Example interpretation:

- if price is between Highest(60) and Lowest(60), market state may be treated as range / consolidation
- if price breaks above Highest(60), it may indicate an upside breakout
- if price breaks below Lowest(60), it may indicate a downside breakout

#### A4. Custom Indicator Support

The system should allow defining custom derived indicators, such as:

- rolling highs/lows
- price relative to indicator
- indicator slope
- indicator distance

Indicators should be easy to define and reusable across different rules.

#### A5. Swing High Definition

The system should support identification of structural swing highs.

A swing high may be defined using a fractal structure.

Example (5-bar fractal):

High[i] > High[i-1]  
High[i] > High[i-2]  
High[i] > High[i+1]  
High[i] > High[i+2]

This indicates a local structural high.

The window size should be configurable to allow different sensitivity levels.

Examples:

- N = 2 → 5-bar fractal
- N = 3 → 7-bar fractal

### B. Entry Rules

These rules determine whether a position can be opened.

Entry rules are comprehensive and may include:

- signal trigger conditions
- confirmation conditions
- multi-timeframe resonance checks
- risk-related admission constraints
- position-related admission constraints

In this design, confirmation logic and position/risk admission logic are considered part of entry qualification rather than independent rule categories.

The system should support pullback-and-validation style entry logic.

#### B1. Core Entry Prototype

One of the core entry prototypes for the first research phase will be based on a pullback validation structure around MA60.

General structure:

1. First close above MA60  
   A candle must close above MA60 for the first time, indicating that price has moved into a potential bullish context.

2. Initial bullish movement above MA60  
   After the breakout, the market may produce one or more bullish candles above MA60.

3. Pullback phase  
   A pullback toward MA60 should occur.

   Pullback requirements:

   - at least one bearish candle with a real body
   - not merely a long lower wick
   - bearish candle close must remain above MA60
   - pullback is allowed to last up to N candles
   - N should remain configurable and be refined through testing

4. Pullback validation  
   The pullback should be treated as a validation of MA60 as support.

5. Temporary high reference  
   The system should support a combined definition of temporary high using both structural and rolling-window logic.

   This may include:

   - recent swing high
   - rolling high such as Highest(20), Highest(60), or another configurable value

6. Continuation trigger  
   Entry occurs when price resumes upward movement and breaks above the temporary high formed before the pullback.

Structure summary:

First close above MA60  
→ bullish movement above MA60  
→ bearish pullback with real body  
→ pullback remains above MA60  
→ breakout of temporary high  
→ entry signal

#### B2. Entry Rule Design Goals

Entry logic should be:

- explainable
- modular
- parameterized
- suitable for comparative testing

The exact numerical values of thresholds and windows should remain configurable and refined through backtesting.

### C. Exit Rules

These rules determine when an open position should be closed.

The first version should support layered research on multiple exit rule types instead of assuming a single universal exit logic.

Possible exit rule categories may include:

- trend-break exits
- moving-average breakdown exits
- structure invalidation exits
- fixed stop-loss exits
- fixed take-profit exits
- trailing exits
- time-based exits
- protective emergency exits

### Exit Rule Philosophy

Capital preservation has the highest priority.

The project should explicitly include several hard protective factors in both entry and exit logic.

These hard protective factors are not the same as normal strategy-layer trend invalidation rules.

Instead, they are intended to be simple, high-priority, non-negotiable constraints that can:

- block a new entry
- force an immediate exit

The first version should focus primarily on single-trade protection rather than account-level protection.

Examples of intended scope include:

- maximum acceptable initial risk per trade
- maximum adverse excursion threshold
- hard stop / emergency exit threshold

The rationale is that if each individual trade is effectively controlled, overall account drawdown will be better contained.

The system should allow future comparison of different exit combinations and protective mechanisms in order to evaluate:

- return impact
- drawdown control
- robustness under different market regimes
- interaction with entry quality
- interaction with trend-following behaviorhard

### Hard Protective Factors

The system should support several simple but strict protective factors.

These protective rules are not part of the strategy logic itself.

Instead, they act as high-priority safety switches designed to prevent extreme risk exposure.

Protective factors must remain:

- simple
- deterministic
- independent from complex strategy logic
- high priority in execution

They should be able to perform only two actions:

- block a new position from being opened
- force an existing position to be closed

These rules should avoid complex structural interpretation and should behave as hard constraints.

---

### Maximum Loss Per Trade

The system should support a simple hard limit on the maximum allowed loss for a single trade.

Example concept:

If the unrealized loss of a position exceeds a predefined threshold:


### Rule System Design Goals

The rule system should be:

- modular
- explainable
- extensible
- easy to test
- easy to compare across combinations

The exact internal structure of A/B/C rules will be refined later.

---

### News Event Protection

The system should support time-based protection around important macroeconomic events.

During certain predefined time windows, opening new positions should be disabled.

Example:

- US Non-Farm Payroll (NFP)

Example protection window:

- NFP release time 15 minutes


## 9. System Architecture Principle

The project will adopt the following layered architecture:

Indicator Layer  
↓  
Rule Layer  
↓  
Strategy Layer  
↓  
Backtest Engine

### Indicator Layer

Responsible for calculating reusable indicators, such as:

- moving averages
- rolling highs / lows
- price-relative metrics
- slope and distance metrics
- future custom indicators

### Rule Layer

Responsible for evaluating reusable rules, such as:

- trend filter rules
- entry qualification rules
- exit rules

### Strategy Layer

Responsible for combining multiple rules into complete strategy configurations.

Strategies should support flexible rule composition and comparison.

### Backtest Engine

Responsible for executing historical backtests and evaluating strategy behavior.

---

## 10. Research and Analysis Goals

The project should provide strong research and analysis capabilities.

The system is not only for generating signals, but also for helping the user understand:

- why a signal appeared
- what market regime the system detected
- which rules contributed to a decision
- how different rule combinations behave across time

The system should support deep analysis of strategy behavior across different market conditions.

---

## 11. Self-Learning / Adaptive Capability

The system should be designed with future support for self-learning or adaptive analysis features.

This does not necessarily mean full machine learning in the first version.

Possible future directions include:

- parameter sensitivity analysis
- rule performance comparison
- adaptive threshold tuning
- market regime classification
- strategy scoring and rule ranking

The architecture should leave room for such features in later milestones.

---

## 12. Logging and Backtest Statistics

The system should provide scientific and detailed logging.

### Logging Goals

Logs should help explain:

- data loading and preprocessing steps
- indicator calculation steps
- rule evaluation results
- entry / exit decision reasons
- backtest execution flow
- errors and edge cases

### Backtest Statistics Goals

The backtest subsystem should produce detailed statistics, including but not limited to:

- total return
- win rate
- profit factor
- maximum drawdown
- average gain / loss
- trade count
- long / short distribution
- holding time statistics
- rule-level contribution analysis
- period-by-period performance analysis

The reporting system should be designed for both summary and drill-down analysis.

### Rule Contribution Analysis

A core objective of the system is to evaluate the contribution of each rule based on backtest results.

The system should support analysis of:

- positive contribution of a rule
- negative contribution of a rule
- whether a rule improves or weakens overall strategy performance
- how a rule behaves under different market regimes
- whether two or more rules reinforce or conflict with each other

This rule contribution analysis should help iterative strategy refinement.

The long-term goal is to improve strategy quality through repeated cycles of:

1. define rules
2. combine rules into strategies
3. backtest
4. evaluate rule contribution
5. keep, adjust, or remove rules
6. re-test

---

## 13. Output Requirements

The first version should support structured research outputs, including:

- indicator tables
- rule evaluation tables
- trade records
- backtest summary reports
- detailed logs

Preferred output formats may include:

- pandas DataFrame
- CSV
- Parquet
- JSON
- terminal summary reports

A graphical interface is not required in the initial version.

---

## 14. Position Model for Initial Version

The first version will use a single-position model.

Constraints:

- at most one open position at any time
- no pyramiding in the first version
- no hedging
- a new trade can only be opened after the prior trade is closed

This simplification is intended to support clearer rule evaluation, cleaner backtest interpretation, and easier contribution analysis.

### Future Extension

Pyramiding / add-on entries may become important in future versions, especially for trend-following strategies.

This is considered an important future direction, but is outside the scope of the first version.

---

## 15. Initial System Goals

The initial version of the system should support:

- historical data download
- local data storage
- multi-timeframe market analysis
- trend-following strategy experimentation
- modular rule definition
- basic backtesting capability
- research-oriented iteration of strategy rules
- detailed logging and statistics outputs
- rule contribution evaluation

---

## 16. Scope Boundaries for Current Phase

The current phase is focused on:

- defining the research framework
- selecting data sources
- specifying strategy analysis requirements
- defining system architecture principles
- gradually refining the project specification

Detailed trading rules, feature definitions, and exact signal logic will be added step by step in later discussions.