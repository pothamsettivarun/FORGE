# clawdfather-native port notes

## Goal
Run the original ClawdFather strategy with minimal strategy drift while replacing Simmer-specific discovery/pricing with native Polymarket-compatible adapters.

## Current status
Implemented so far:
- native compatibility scaffold
- slug-first market discovery for BTC/ETH/SOL 5m + 15m updown markets
- CLOB midpoint probability inference
- normalized market objects
- minimal context shim
- minimal paper snapshot shim
- `run_native_port.py` smoke-test entrypoint

## Next implementation target
Wire the original ClawdFather loop to use the native adapter functions instead of Simmer `/markets`, `/context`, and snapshot calls.
