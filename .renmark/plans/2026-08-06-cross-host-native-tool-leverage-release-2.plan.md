---
artifact_type: plan
schema_version: 1
created_at: 2026-08-06T23:00:00Z
source_sha: 03ed0a6
related_plan: .renmark/rethink/cross-host-native-tool-leverage/roadmap.md
generator: sonnet
---

# Plan — cross-host-native-tool-leverage Release 2

Consolidate `renmark/dispatch.py`'s standalone `HostName = Literal["claude", "codex"]`
onto `renmark/hosts.py`'s canonical `HostKind` enum. `HostKind` is a `(str, Enum)`
whose members (`CLAUDE_CODE = "claude"`, `CODEX = "codex"`, `UNKNOWN = "unknown"`)
already carry the exact string values `dispatch.py` relies on, so every existing
`host_name == "claude"` / `host_name == "codex"` comparison, dict key, and dataclass
field keeps working unchanged — only the type/validation definition moves. This
closes the duplication flagged by the rethink's modularity assessment
(`.renmark/rethink/cross-host-native-tool-leverage/modularity-assessment.md`) without
changing any host-branch decision (per the Owner-approved roadmap's `AC` for this
release).

**Do not change:** no host-branch DECISION logic in `dispatch.py` (which host gets
which transport) — only where the host-type is defined and validated. `HostKind.UNKNOWN`
must continue to be rejected by `build_host_dispatch_plan`/`build_host_dispatch_plan_with_scope`
exactly as `"unknown"` was rejected before (still raises `ValueError`).

### Task 1: consolidate dispatch.py's HostName onto hosts.py's HostKind
- **mode:** B
- **target:** renmark/dispatch.py
- **complexity:** medium
- **executor:** sonnet
- **role:** code-implementer
- **parallel_group:** 1
- **est_tokens:** 900
- **est_cost_usd:** 0.0327
- **verifier:** python3 -m pytest -q -k "host or codex or claude or dispatch or interaction" 2>&1 | tail -3
- **serves:** cross-host-native-tool-leverage Release 2 (modularity finding)
- **spec:**
  In `renmark/dispatch.py`:
  1. Remove the standalone line `HostName = Literal["claude", "codex"]` (currently
     around line 976).
  2. Add `from renmark.hosts import HostKind` near the existing imports (check for an
     existing `from renmark import hosts` / `from renmark.hosts import ...` import
     first and extend it rather than duplicating).
  3. Add `HostName = HostKind` as a type alias in the same place the old Literal was,
     so every existing annotation site (`host: HostName`, `HostDispatchPlan.host: HostName`,
     `host: HostName | str` parameters) keeps compiling unchanged — do not touch those
     call sites.
  4. In `build_host_dispatch_plan` (and `build_host_dispatch_plan_with_scope` if it
     duplicates the same validation rather than delegating), replace the manual
     `normalized not in {"claude", "codex"}` check + `cast(HostName, normalized)` with:
     resolve via `hosts.resolve_host(host)` (or equivalent using `HostKind` directly),
     and raise the same `ValueError(f"unsupported host {host!r}; expected 'claude' or
     'codex'")` message when the resolved kind is `HostKind.UNKNOWN`. Preserve the
     existing error message text exactly (tests may assert on it) — only change how
     the valid/invalid decision is computed.
  5. Do not change `_build_claude_host_calls`, `_build_codex_host_calls`, or any other
     function's branching logic — they keep comparing against the same string values,
     which remain valid since `HostKind` is a `str` subclass.
  6. Run `grep -n "Literal\[.claude.,\s*.codex.\]" renmark/dispatch.py` after editing to
     confirm no independent host-type Literal remains in this file.

### Task 2: add grep-based regression guard against re-duplication
- **mode:** A
- **target:** tests/test_dispatch_hostname_consolidation.py
- **complexity:** simple
- **executor:** codex
- **role:** test-writer
- **parallel_group:** 2
- **est_tokens:** 400
- **est_cost_usd:** 0.02
- **verifier:** python3 -m pytest -q tests/test_dispatch_hostname_consolidation.py 2>&1 | tail -3
- **serves:** cross-host-native-tool-leverage Release 2 (modularity finding)
- **spec:**
  Create `tests/test_dispatch_hostname_consolidation.py`, following the pure
  file-content-check style of `tests/test_dangerous_gate_wiring.py` (read that file
  first for the pattern — no imports of `renmark.dispatch` needed, just source text
  assertions so the guard can't be defeated by renaming the symbol at runtime):

  1. Read `renmark/dispatch.py`'s source text.
  2. Assert it does NOT contain a standalone `Literal["claude", "codex"]` definition
     for `HostName` (i.e. assert the pattern `HostName = Literal[` is absent from the
     file text).
  3. Assert it DOES import `HostKind` from `renmark.hosts` (e.g. assert
     `"HostKind" in text` and `"hosts" in text` in a way that confirms the import,
     such as checking for `"from renmark.hosts import"` or `"from renmark import hosts"`
     followed by a `HostKind` reference).
  4. Also assert `renmark/dispatch.py` still exposes a `HostName` name at all (e.g.
     `"HostName" in text`) so downstream type annotations aren't silently broken.

  Keep the test file under ~40 lines, mirroring the header docstring style of
  `tests/test_dangerous_gate_wiring.py` ("Pure file-content checks... We do NOT
  import or run the skills/module.").

---

**Cost preview**

| task | executor | est. tokens (incl. overhead) | est. cost |
|---|---|---:|---:|
| Task 1 | sonnet | 900 + 10,000 = 10,900 | $0.0327 |
| Task 2 | codex | 400 | $0.02 |

**Total: ~11,300 tokens · ~$0.05**

Executors: sonnet×1, codex×1. No opus/fable. Subagent roles: code-implementer, test-writer — both narrow-scope, no `general-purpose` fallback needed.
