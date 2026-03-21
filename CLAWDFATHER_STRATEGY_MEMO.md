# ClawdFather Strategy Memo

## Purpose

This memo distills the actual behavior of the legacy `clawdfatherpolybot` so Forge can preserve the real edge (if any) while removing simulator-friendly assumptions that likely broke on live Polymarket.

Repo analyzed:
- `/home/openclawd/.openclaw/workspace/forge/clawdfatherpolybot`

---

## Executive Summary

ClawdFather is a **short-horizon momentum / microstructure bot** trading:
- BTC
- ETH
- SOL
- 5-minute and 15-minute Up-or-Down markets

It uses:
- **Simmer markets API** for market discovery and execution
- **Binance 1-minute candles** for the signal
- small-ticket notional sizing
- spread/edge gating
- risk limits and cooldowns

### Working thesis
The bot likely had a **real signal in Simmer**, but degraded on live Polymarket because:
1. execution remained **Simmer-mediated** rather than Polymarket-native
2. signal timing relied on **coarse 1-minute Binance bars**
3. friction / adverse selection were probably under-modeled
4. cadence override increased participation pressure
5. market universe was broad and likely mixed good/bad sub-regimes

---

## Architecture Overview

### Main loop
File:
- `simmer_bot/simmer_minute_loop.py`

Supporting modules:
- `simmer_bot/core/execution.py`
- `simmer_bot/core/stopping.py`
- `simmer_bot/core/ip_oracle.py`
- `simmer_bot/core/initfw.py`
- `simmer_bot/core/barrier_fw.py`
- `simmer_bot/core/constraints.py`
- `simmer_bot/risk/limits.py`

### Persistent runtime artifacts
The bot writes to:
- `memory/simmer-loop.log`
- `memory/simmer-events.jsonl`
- `memory/simmer-metrics.jsonl`
- `memory/simmer-loop-state.json`

---

## Market Universe and Selection

### Assets
Configured assets:
- BTC / `BTCUSDT`
- ETH / `ETHUSDT`
- SOL / `SOLUSDT`

### Contract family
Targets:
- 5m Up-or-Down
- 15m Up-or-Down

### Selection logic
The loop fetches active markets from Simmer and selects candidates using:
- 5m priority over 15m
- optional least-recently-traded asset diversification
- market cooldown of `125 sec`
- lookahead windows:
  - `LOOKAHEAD_5M_SEC = 480`
  - `LOOKAHEAD_15M_SEC = 1200`

### Operational implication
The bot is intentionally optimized for:
- frequent short-dated contracts
- repeated small entries
- near-expiry opportunities

This profile is highly sensitive to latency and fill quality.

---

## Signal Engine

### Data source
Signal input comes from:
- Binance 1-minute klines
- last 30 bars

### Features
The signal computes:
- `r1` = 1-minute return
- `r3` = 3-minute return
- `r5` = 5-minute return
- rolling short volatility estimate from recent returns

### Score construction
Directional score is built as:
- `r1 > 0` => `+1`
- `r3 > 0` => `+2`
- `r5 > 0` => `+2`
- negatives subtract symmetrically

### Side decision
- `score >= 3` => `yes`
- `score <= -3` => `no`
- otherwise => no side

### Volatility / quality filter
The signal is rejected as `weak_or_choppy` if:
- `vol > 0.18`
- or `abs(r3) + abs(r5) < 0.11`

### Confidence
Confidence is a function of:
- total directional strength
- penalized by volatility

Then an additional proxy gate requires:
- side present
- `confidence >= 0.42`
- price between `0.08` and `0.92`

### Interpretation
This is a fairly clean practical signal:
> trade short-term continuation only when 1m / 3m / 5m momentum align and recent volatility is not too chaotic.

This is likely the true alpha engine.

---

## Projection / Theory Layer

### Modules
- `constraints.py`
- `ip_oracle.py`
- `initfw.py`
- `barrier_fw.py`
- `stopping.py`

### What it does in practice
The bot builds a two-state target probability based on the current market price plus a confidence-linked edge bump, then runs a constrained barrier Frank-Wolfe style optimization to obtain:
- divergence `D`
- gap `g`
- a net guarantee after estimated friction

### Execution gate
A trade is only approved if:
1. alpha extraction condition passes
2. net guarantee exceeds threshold
3. risk is okay

Parameters:
- `ALPHA_STOP = 0.9`
- `NET_THRESHOLD = 0.02`
- `FEE_EST = 0.003`
- `SLIPPAGE_EST = 0.006`
- `RISK_BUFFER_EST = 0.004`

### Interpretation
This layer looks sophisticated, but functionally it acts more like:
- a structured trade filter
- a formalized edge / friction gate

It does **not** appear to be the original economic engine. The practical engine is still momentum + vol + spread gating.

---

## Spread / Edge Gate

### Hard pre-trade filter
Enabled by default:
- `ENABLE_SPREAD_GATE = 1`
- `SPREAD_EPSILON = 0.03`

The bot computes:
- `mu_yes` from the projection layer
- compares it against current market price
- requires `abs(mu_yes - market_price) >= epsilon`

### Adaptive epsilon
Adaptive mode is enabled:
- min `0.02`
- max `0.06`
- step up `0.005`
- step down `0.002`
- recalc every `600 sec`

Adaptation uses:
- order reject rate
n- partial fill rate

### Interpretation
This is one of the smartest practical parts of the bot.
It prevents many tiny or noisy edges from being traded.

---

## Sizing Logic

### Formula
`size_order()` does roughly:
- base amount = `40 + 80 * confidence`
- if `secs_left <= 30`, multiply by `1.2`
- cap by affordability
- cap by `MAX_TRADE`
- finally cap by `SAFE_MAX_ORDER_NOTIONAL`

### Key active caps
- `MAX_TRADE = 100`
- `SAFE_MAX_ORDER_NOTIONAL = 20`

### Effective result
Despite larger internal sizing math, actual orders are mostly clipped to:
- **$20 max notional requested**

### Interpretation
The bot is effectively a:
> small-ticket, high-frequency edge harvester

This style is much easier to make look smooth in a soft simulator than in a competitive live venue.

---

## Cadence Override

### Behavior
If no successful trade has happened for about 60 seconds, the bot may override normal selectivity and force a conservative trade attempt if conditions are “good enough.”

### Conditions for cadence override
The projection layer can be bypassed if:
- cadence is due
- spread is acceptable
- confidence is acceptable
- volatility is acceptable

Then size may be clipped to as low as `$10`.

### Interpretation
This is a major live-risk feature.
In a simulator it may improve opportunity capture.
In a live venue it likely increases participation in marginal trades.

This is a strong candidate for deletion in Forge.

---

## Execution Layer

### Implementation
File:
- `core/execution.py`

Strengths:
- idempotent submit
- explicit handling of submitted / partial / filled / rejected / timeout / error
- no fake fill assumption if provider omits explicit fill
- conservative inventory reconciliation

### Key issue
Even in “live” mode, the bot submits via:
- `POST https://api.simmer.markets/api/sdk/trade`
- with `venue = "polymarket"`

So the strategy is still **Simmer-mediated**, not direct Polymarket-native execution.

### Interpretation
This is likely the biggest portability problem.
For short-horizon momentum on near-expiry markets, routing / abstraction latency is extremely costly.

---

## Risk Layer

### Config
- max position per market: `400`
- max gross exposure: `1500`
- max daily drawdown: `-500`
- max trades per day: `1000`

### Additional guards
- low-tail hard block at `price <= 0.08`
- high-tail hard block at `price >= 0.98`
- per-market cooldown

### Interpretation
The risk framework is basic but real. It likely helped contain blowups, but it does not solve execution quality problems.

---

## Why Simmer Performance Could Have Looked Excellent

Most likely reasons:
1. short-horizon momentum continuation existed in the Simmer environment
2. market repricing may have been slower / softer
3. fills may have been friendlier
4. small-ticket strategy compounded smoothly
5. spread gate filtered out much of the noise

This is consistent with:
- high trade count
- smooth, linear PnL curves
- repeated small profits

---

## Why Live Polymarket Performance Likely Broke

### 1. Mediated execution latency
The bot was still trading through Simmer routing while trying to capture short-lived edges.

### 2. Coarse signal timing
Using 1-minute Binance candles is likely too slow / coarse for live microstructure competition.

### 3. Under-modeled friction
Configured fee/slippage assumptions were likely too optimistic for real market conditions.

### 4. Cadence override
This likely forced marginal trades in a venue where selectivity mattered more.

### 5. Broad market universe
BTC/ETH/SOL across 5m/15m probably mixed very different liquidity and efficiency regimes.

---

## Keep / Delete Recommendations for Forge

### Keep
- momentum family (`r1/r3/r5` idea or equivalent short-horizon continuation logic)
- volatility / chop filter
- hard spread / edge threshold
- small-ticket discipline
- logging and statefulness
- risk caps

### Delete or radically change
- Simmer-mediated live execution assumption
- cadence override
- broad multi-asset / multi-horizon launch scope
- dependence on coarse 1-minute-only timing for live execution
- over-reliance on academic wrapper modules as if they are the alpha source

---

## Forge Working Hypothesis

> ClawdFather probably contained a real signal, but it was built for a softer execution habitat than real Polymarket.

Therefore Forge should aim to:
1. preserve the real signal components
2. eliminate simulator-comfort assumptions
3. rebuild the strategy around direct real-market constraints

---

## Recommended Forge v1 Scope

- BTC only
- one horizon first
- direct Polymarket-aware execution model
- explicit real friction handling
- no cadence override
- small fixed notional
- strong logging and post-trade diagnostics

---

## Conclusion

ClawdFather should not be dismissed as a fluke bot.
It is better understood as:
- a real short-horizon momentum strategy
- wrapped in a Simmer-native operational model
- that likely lost its edge once exposed to real Polymarket execution conditions

That makes it a good candidate for re-engineering, not blind porting.
