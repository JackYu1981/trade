# AGENTS.md

## Project Context

This repository contains the **Trade research framework**, a modular platform for developing, testing, and analyzing rule-based trading strategies across financial markets.

The long-term vision of this project is to provide an **open research framework for systematic trading**, while allowing proprietary strategies and alpha logic to remain private.

This document defines architectural and development constraints for AI agents (including Codex) working inside this repository.

---

# Core Principle

This repository is intended to contain an **open-source trading research framework**, not proprietary trading strategies.

The framework should enable strategy research, but **must not expose private alpha logic or production trading strategies**.

---

# What Should Be Open Source

The public repository should include the framework infrastructure required to support strategy research:

- data ingestion and normalization framework
- market data abstractions
- indicator computation framework
- reusable rule interfaces and generic rule primitives
- strategy composition engine
- backtest engine
- portfolio / execution simulation
- research analysis tools
- reporting utilities
- service layer orchestration
- CLI interface
- architecture that can support future API or web services

These components form the **core research framework**.

---

# What Must NOT Be Included in the Public Repository

The following must remain outside the open-source framework:

- proprietary trading strategies
- alpha-generating rule combinations
- production parameter sets
- market-specific trading edge logic
- private datasets
- experiment outputs
- research logs
- production trading infrastructure

The public repository should never reveal a complete production trading system.

---

# Framework vs Strategy Boundary

The framework must be designed so that **strategies can live outside the repository**.

Architecture must support:

- private strategy modules
- plugin-style strategy loading
- configuration-driven strategy definitions
- strategy packages outside the public repo
- framework-first design independent of specific strategies

The framework provides **interfaces and primitives**, not final trading strategies.

---

# Strategy Examples

Example strategies may exist in the repository for demonstration purposes.

These strategies must be:

- simple
- educational
- non-proprietary
- not representative of real alpha logic

Example strategies exist only to demonstrate how the framework works.

---

# Repository Design Expectations

The repository should remain **library-first**.

Expected high-level structure:
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

Private strategy implementations may exist outside the repository or in ignored directories.

---

# Git and Data Constraints

The repository must not track:

- datasets
- experiment results
- backtest outputs
- cached market data
- proprietary strategy modules

These should remain local or be ignored via `.gitignore`.

---

# Planning and Implementation Guidance

When designing new features:

- maintain a clear separation between framework and strategy logic
- avoid embedding strategy assumptions in the core framework
- prefer configuration-driven architecture
- keep services reusable and market-agnostic
- ensure future compatibility with API and web services

---

# Milestone 1 Constraint

Milestone 1 should still implement a **complete vertical slice**, including:

- data ingestion
- indicators
- rule evaluation
- strategy interface
- backtest engine
- reporting pipeline

However:

The strategy used in Milestone 1 must be a **minimal demonstration strategy**, not a real trading system.

---

# Long-Term Vision

The goal of this project is to evolve into an **open research platform for systematic trading**, where:

- the framework is open source
- strategy research remains flexible
- proprietary alpha can remain private
- future community contributions are possible

This repository should prioritize **clean architecture, extensibility, and research transparency**.
