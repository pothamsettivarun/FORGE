# Forge

Forge is a Polymarket-native rebuild of the legacy ClawdFather strategy.

## Current status
Paper-validation scaffold stage.

## Included docs
- `CLAWDFATHER_STRATEGY_MEMO.md`
- `FORGE_SPEC.md`

## Scaffold goals
- narrow initial scope to BTC-only
- separate signal, execution, risk, and runtime concerns
- keep observability first-class from day one

## Planned structure
- `forge_bot/data/` market and spot feeds
- `forge_bot/signal/` momentum and edge logic
- `forge_bot/execution/` execution abstractions
- `forge_bot/risk/` risk gates
- `forge_bot/runtime/` logging, state, summaries

## Run
```bash
cd /home/openclawd/.openclaw/workspace/forge
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 main.py --config config.example.yaml
```

## Runtime artifacts
- `logs/` — per-session runtime logs
- `trades/` — per-session JSONL trade ledger
- `summary/` — per-session summaries
- `summary/latest-summary.json` — easiest file to inspect mid-run
