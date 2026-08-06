# Release 1 — Baseline and compatibility coverage (cross-host-native-tool-leverage)

Turns Stage 2's baseline into a real, reusable fast-gate reference so
releases 2-4 have a fast, precise regression check instead of only the
full suite. Test-only — no production code moves.

### Task 1: document the host/dispatch/interaction fast-gate reference

- **mode:** A
- **target:** .renmark/memory/cross-host-fast-gate.md
- **complexity:** simple
- **executor:** haiku
- **role:** docs-editor
- **parallel_group:** 1
- **est_tokens:** 300
- **est_cost_usd:** 0.001
- **verifier:** test -f .renmark/memory/cross-host-fast-gate.md && grep -q "pytest -q -k" .renmark/memory/cross-host-fast-gate.md && echo OK
- **serves:** stage-2 baseline (cross-host-native-tool-leverage program)
- **spec:**
  Create `.renmark/memory/cross-host-fast-gate.md` (a durable reference
  file, NOT auto-regenerated like `.renmark/memory/dev-standards.md` —
  do not touch that file). Content:
  - A one-paragraph purpose statement: this is the fast-gate test target
    for the `cross-host-native-tool-leverage` program (releases 2-4
    should run this before the full suite as a quick regression check).
  - The exact command: `pytest -q -k "host or codex or claude or dispatch or interaction"`
  - Its measured baseline (as of 2026-08-06, source_sha 3142267):
    220 passed, 17 skipped.
  - A second, narrower command for the core cross-host files specifically:
    `pytest -q tests/test_dispatch.py tests/test_hosts.py tests/test_interaction.py tests/test_cross_host_dispatch_e2e.py tests/test_selector_contract.py` — its measured baseline: 70 passed.
  - A note: full-suite baseline for cross-reference: 2101 passed, 32
    skipped (grows as releases 2-4 add their own tests).
  - A note: this file is a static reference, not auto-regenerated —
    update it manually if the baseline numbers are re-measured in a
    future release.

## Compatibility guarantee
`pytest -q` count stays at 2101 passed, 32 skipped (no test changes, this
is a new doc file only).

---
**Total tasks:** 1
**Total tokens:** ~300 + ~10k Agent overhead
**Total cost:** ~$0.001 (haiku)
**Executors:** haiku×1
