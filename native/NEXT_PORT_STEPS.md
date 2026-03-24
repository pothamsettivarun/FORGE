# Native Port Next Steps

## Current stage
- Native market discovery works via slug-first Gamma/CLOB adapter.
- A minimal compatibility shim exists for snapshot / markets / context.
- Original loop has been copied to `native/clawdfather_native_loop.py` for venue-layer substitution work.

## Immediate next engineering step
Patch `clawdfather_native_loop.py` to:
1. import native compat shim
2. replace Simmer snapshot reads with `compat.get_snapshot()`
3. replace Simmer market fetch with `compat.fetch_markets()`
4. replace Simmer context fetch with `compat.fetch_context(market_id)`
5. leave signal / theory / sizing / risk logic untouched as much as possible

## After that
- wire a native paper execution shim preserving the ExecutionAdapter interface
- then run the first native-paper ClawdFather loop
