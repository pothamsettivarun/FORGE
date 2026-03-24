# Native Port Notes

## Phase A+B status

Implemented:
- `native/core/polymarket_adapter.py`
- slug-first market fetch from Gamma for BTC/ETH/SOL 5m/15m updown contracts
- midpoint-based current probability inference from CLOB
- normalization into a Simmer-like market shape with:
  - `id`
  - `slug`
  - `question`
  - `current_probability`
  - `resolves_at`
- minimal context shim
- minimal paper snapshot shim

## Intended next step
Wire these adapters into a native entrypoint / compatibility loop so ClawdFather can run on native Polymarket discovery and pricing with minimal strategy drift.
