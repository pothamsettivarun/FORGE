# Forge Spec

## Purpose

Forge is a new project to re-engineer the legacy ClawdFather / Simmer strategy for **real Polymarket survivability**.

The goal is **not** to port old code blindly.
The goal is to:
1. preserve any real predictive edge,
2. remove simulator-friendly assumptions,
3. rebuild execution and risk around live-market reality.

---

## Problem Statement

The legacy bot was strongly profitable in Simmer / `$SIM`, but degraded materially when pointed at real Polymarket exposure.

Working diagnosis:
- the old bot likely had some real signal,
- but execution assumptions, timing assumptions, and venue abstraction were too soft for live conditions.

Forge exists to answer one question:

> Can the old signal family be made profitable on real Polymarket when rebuilt with live-native execution assumptions?

---

## Primary Objective

Build a Polymarket-native short-horizon trading system that captures only the part of the old edge that survives:
- real fills,
- real latency,
- real spread,
- real adverse selection,
- real friction.

---

## Non-Goals

Forge v1 is **not** trying to:
- trade every asset and every horizon at once
- maximize trade count
- recreate the entire old architecture/module-for-module
- preserve academic/theoretical wrappers unless they prove incremental value
- optimize for simulator PnL

---

## Core Design Principles

1. **Reality first**
   - any edge must survive live execution assumptions

2. **Narrow scope first**
   - start with a single asset and single horizon if possible

3. **Simple beats decorative**
   - explicit signal logic, explicit friction model, explicit execution logic

4. **Instrumentation from day one**
   - every trade, skip, fill, and failure should be inspectable

5. **Small size until proven**
   - no scaling before clean evidence

---

## What Forge Keeps from ClawdFather

### Signal family
Keep the broad signal concept:
- short-horizon momentum continuation
- multi-window directional agreement
- volatility / chop filter
- hard edge threshold

### Safety and discipline
Keep:
- small-ticket sizing
- hard per-trade limits
- daily kill switch
- exposure caps
- cooldown logic where appropriate

### Logging discipline
Keep structured persistence:
- logs
- trade ledgers
- summaries
- state
- diagnostics

---

## What Forge Deletes or Replaces

### Delete
- Simmer-mediated live execution assumptions
- cadence override / forced participation behavior
- broad multi-asset initial scope
- broad multi-horizon initial scope
- complexity that does not materially improve decision quality

### Replace
- 1-minute-candle-only dependence with better real-time timing alignment
- soft friction assumptions with more realistic ones
- abstract execution with explicitly Polymarket-aware execution logic

---

## Forge v1 Scope

### Asset universe
Start with:
- **BTC only**

### Horizon
Start with:
- one horizon only
- likely the shortest horizon that has acceptable liquidity and signal persistence

### Trade style
- small fixed notional
- one position per market initially
- highly selective
- no cadence pressure

---

## Signal Layer (v1)

### Goal
Replicate the spirit of ClawdFather’s edge without carrying over its execution fragility.

### Inputs
- BTC spot feed
- Polymarket market state / orderbook / price state

### Candidate features
- very short-term return windows
- directional alignment across short windows
- volatility / chop filter
- optional market microstructure sanity checks

### Requirements
- side must be explicit
- confidence must be explicit
- edge must be explicit
- no hidden magic

---

## Fair Value / Edge Layer

Forge must distinguish between:
- **predicted direction**, and
- **tradeable value**.

A trade should only be allowed when:
- signal says direction is favorable
- real executable price is below fair value by enough margin
- margin survives estimated fees + slippage + adverse selection buffer

---

## Execution Layer (v1)

### Requirement
Forge must be designed around **real Polymarket conditions**, not simulator comfort.

### Needed properties
- orderbook-aware entry logic
- explicit maker vs taker choice
- price cap / slippage cap
- stale order cancellation rules
- partial fill handling
- no fake fill assumptions
- accurate post-trade state reconciliation

### Principle
If execution quality is uncertain, Forge should prefer **not trading** over optimistic assumptions.

---

## Risk Layer (v1)

### Required controls
- fixed tiny notional per trade
- max one position per market initially
- max gross exposure
- max daily drawdown
- optional per-market cooldown
- kill switch

### Principle
Risk model should be simple, explicit, and hard to reason about incorrectly.

---

## Telemetry and Persistence

Forge should include from day one:
- `logs/` per-session runtime logs
- `trades/` JSONL trade ledgers
- `summary/` session summaries
- `state/` persistent state if needed
- explicit skip reasons
- explicit execution outcomes

### Summary requirements
A run summary should expose:
- markets seen
- trades entered
- trades skipped
- reasons for skips
- fills / partial fills / rejects
- realized PnL
- win/loss counts
- expected-vs-realized edge where possible

---

## Validation Plan

### Phase 1 — signal validation
Validate whether the narrowed signal still produces promising opportunities.

### Phase 2 — execution realism
Measure how much edge survives after realistic fill / slippage assumptions.

### Phase 3 — small live exposure
Trade only at tiny size until:
- fills are understood
- realized behavior matches modeled expectations closely enough

### Phase 4 — iterate
Adjust only after sufficient sample, not from emotional variance.

---

## Success Criteria

Forge v1 is successful if it demonstrates:
1. disciplined selectivity,
2. stable logging and observability,
3. realistic execution accounting,
4. positive expectancy after friction on a meaningful sample.

Not simulator PnL.
Not narrative comfort.
Real post-friction expectancy.

---

## Failure Criteria

Forge v1 is considered failed or requires major redesign if:
- trade edge disappears after realistic execution assumptions,
- latency / spread destroy expectancy,
- signal only works in sandbox-like environments,
- strategy requires forced participation to look profitable,
- profitability depends on assumptions not available in real Polymarket conditions.

---

## Initial Build Order

1. **ClawdFather extraction memo** ✅
2. **Forge spec** ✅
3. **Forge scaffold**
4. **Narrow-scope signal implementation**
5. **Execution + logging layer**
6. **Paper / replay validation**
7. **Tiny live testing**

---

## Forge Working Hypothesis

> The old bot’s core signal may have been real, but it was trapped inside a Simmer-native execution habitat.

Forge is the attempt to free the signal from that habitat and see whether it survives in the real market.
