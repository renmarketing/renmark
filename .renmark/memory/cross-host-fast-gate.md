# Cross-host fast-gate test reference

Fast-gate test target for the `cross-host-native-tool-leverage` program
(`.renmark/rethink/cross-host-native-tool-leverage/`). Releases 2-4 of this
program should run this before the full suite as a quick, precise regression
check on host-routing behavior specifically, rather than waiting on the full
suite for every iteration.

**Static reference — not auto-regenerated.** Update manually if these
numbers are re-measured in a future release.

## Broad fast-gate (keyword-matched)

```
pytest -q -k "host or codex or claude or dispatch or interaction"
```

Baseline (2026-08-06, source_sha `3142267`): **220 passed, 17 skipped**.

## Narrow fast-gate (core cross-host files)

```
pytest -q tests/test_dispatch.py tests/test_hosts.py tests/test_interaction.py tests/test_cross_host_dispatch_e2e.py tests/test_selector_contract.py
```

Baseline (2026-08-06, source_sha `3142267`): **70 passed**.

## Full-suite cross-reference

Baseline (2026-08-06, source_sha `3142267`): **2101 passed, 32 skipped**.
Expected to grow as releases 2-4 add their own tests — always run the full
suite before committing a release, the fast-gate above is a quick
intermediate check, never a substitute for it.
