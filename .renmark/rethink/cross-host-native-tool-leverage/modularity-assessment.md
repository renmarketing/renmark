---
artifact_type: rethink-modularity-assessment
schema_version: 1
created_at: 2026-08-06T00:00:00Z
source_sha: 3142267324409b8a981a7a35faf642ff63135940
related_plan: null
generator: sonnet
transformation_topic: cross-host-native-tool-leverage
stage: 5
dependency_refs: []
---

# Modularity / Scalability / Maintainability — Host-Routing Layer

## 1. `renmark/hosts.py` — decoupling and third-host cost

`hosts.py` cleanly separates two concerns: `resolve_host()` (identity — env var,
explicit arg, Codex process-marker sniffing) and `capabilities_for()` (a frozen
`HostCapabilities` dataclass keyed by `HostKind`). Adding `HostKind.THIRD_HOST`
is a small, bounded, single-file change: one new enum member, one new
`_CAPABILITIES` entry, one or more `_HOST_ALIASES` strings. No branching logic
elsewhere needs new host-specific `if` arms *if* callers only read capability
fields (they do — see §2).

Imports of `renmark.hosts` / `capabilities_for` (grep, deduped, non-test):
`renmark/global_routing.py`, `renmark/interaction.py`, `renmark/lifecycle/preamble.py`,
`renmark/lifecycle/stage.py` (imports `HostKind` only, for a local
`_lifecycle_host` resolution helper) — **4 non-test call sites**, plus
`renmark/hosts.py` itself. Test files importing it: `test_hosts.py`,
`test_interaction.py`, `test_selector_contract.py`,
`test_artifact_home_and_baseline_compat.py` — 4 files. This is a small,
countable fan-out; a third host does not ripple beyond `hosts.py` for any of
these 4 call sites, since they all consume `capabilities_for(...)` output
rather than re-encoding per-host facts.

## 2. Are the 5 decision points one coherent layer or independent drift risks?

Checked concretely:
- `global_routing.py` — imports `HostKind, resolve_host` from `hosts.py`, uses
  them only to pick a global instruction-file path (`~/.claude/CLAUDE.md` vs
  `~/.codex/AGENTS.md`). Delegates identity fully to `hosts.py`; adds no
  independent host fact.
- `interaction.py` — imports `HostKind, capabilities_for, resolve_host`,
  builds selectors from the returned `HostCapabilities`. Delegates fully.
- `lifecycle/preamble.py` — imports `HostKind, capabilities_for` from
  `..hosts`, reads `supports_resume` / `supports_clear` / `supports_compact`
  off the returned capabilities. Delegates fully.
- `lifecycle/stage.py` — imports only `HostKind` (not `capabilities_for`) and
  defines a local `_lifecycle_host(host)` **resolution** helper (explicit →
  `RENMARK_HOST` → Codex-runner marker) that mirrors, but does not call,
  `hosts.resolve_host`'s precedence contract. This is delegated identity
  *policy* re-implemented in a second place — a real but narrow duplication:
  if `resolve_host`'s precedence order ever changes, `_lifecycle_host` must be
  updated in lockstep or the two diverge silently. It does not duplicate the
  *capability table* (that still comes from `capabilities_for`), only the
  precedence order for resolving identity in one lifecycle-specific context
  (a Codex-hosted test runner nuance documented in its docstring).
- **`renmark/dispatch.py` does NOT import `renmark.hosts` at all.** It defines
  its own `HostName = Literal["claude", "codex"]` and its own validation
  (`normalized not in ("claude", "codex")` → `ValueError`). This is a genuine
  second, independent encoding of "what hosts exist" that does not go through
  `HostKind`/`_HOST_ALIASES` — it silently omits the aliases `hosts.py`
  accepts (`"claude-code"`, `"claude_code"`, `"openai-codex"`) and has no path
  to `HostKind.UNKNOWN`'s conservative fallback. Today this is harmless
  because `dispatch.py`'s `HostName` is a pure transport-plan tag, not a
  capability lookup — but it is the one place a third host addition requires
  a second file edit (`dispatch.py`'s `Literal` and validation check),
  contradicting the "single bounded change" story from §1 for this one path.

Net: 4 of 5 decision points form one coherent layer (delegate to `hosts.py`
cleanly); `lifecycle/stage.py` has a narrow precedence-order duplication;
`dispatch.py` is the one outlier with a fully independent host-identity
encoding.

`subagent_gate.py` also carries a per-control × per-host
`ENVELOPE_CONTROL_STATUS` table (`control_status(control, host)`), but this is
a different concern (capability *enforcement* status per control) than
`hosts.py`'s render/selector capabilities — not the same fact duplicated, so
not counted as drift risk here.

## 3. Extension points for `ScheduleWakeup` / `ExitWorktree`

- **`ScheduleWakeup` (usage-pause path):** `heartbeat.py` currently hand-rolls
  cron emission with no native scheduling call. Adoption's smallest blast
  radius is `renmark/heartbeat.py` alone — add a `HostCapabilities`-gated
  branch (new field, e.g. `supports_schedule_wakeup: bool`, added to
  `hosts.py`'s dataclass + both `_CAPABILITIES` entries) that heartbeat.py
  reads to decide cron-file emission vs. native scheduling. This does **not**
  need to touch `renmark/state/pause.py` or `renmark/cli/` — heartbeat.py
  already owns the read/decide/emit sequence for the pause path.
- **`ExitWorktree` (worktree cleanup):** the mutating `git worktree remove`
  shell-out lives in `finish/SKILL.md` §3.6 (skill-level, not
  `renmark/worktree.py`'s Python — confirm the actual removal call site before
  editing; `worktree.py` itself is deterministic-check-only per the
  deterministic-first contract). Adoption's smallest blast radius is that one
  skill body plus, if a host-capability gate is wanted, one new
  `HostCapabilities` field consumed only where the skill (or a thin
  `renmark/worktree.py` wrapper it calls) currently branches on host. No
  ripple into `state.py` or `cli/` is required for either adoption — both are
  leaf consumers of `hosts.py`'s capability table by construction.

## 4. Testability of the 5 decision points

Spot-checked `tests/test_hosts.py` (178 lines) and `tests/test_interaction.py`
(170 lines): both mock host purely via `monkeypatch.setenv("RENMARK_HOST", ...)`
or an explicit `host=HostKind.X` / string kwarg — no live tool call, no
subprocess, no network. `test_selector_contract.py` (253 lines) does the same
for the selector-building branch. All three are pure unit tests with
parametrized fixtures. `lifecycle/preamble.py`'s branches are exercised the
same way (host passed as plain string/`HostKind`). `dispatch.py`'s
`HostName`-based validation is likewise trivially unit-testable (pure string
literal check) — testability is not the gap; encoding duplication is.

## 5. State-file ownership

- `pipeline.json` + wave-summaries: sole writer `renmark/state/pipeline.py`
  (`write_pipeline_state`, `write_wave_summary`). `agency.py` and `loop.py`
  reference it only in comments/docstrings steering cruft *away* from
  themselves and *into* pipeline.py — confirms single-writer intent, not a
  second writer.
- `tasks.json`: sole writer `renmark/task_tracking.py::write_tasks`, using an
  atomic tmp-file + rename pattern.
- Pause state: sole writer `renmark/state/pause.py::write_pause`.

No file found with two independent write paths. Ownership is clean —
no race/drift risk identified in the state layer.

## Target-state recommendation

**No architecture change.** The host-routing layer's current shape (one
capability table in `hosts.py`, ~4 clean delegating consumers) is already
reasonably good; a hypothetical third host is a small, bounded addition for
3 of the 4 in-layer consumers. Recommend two narrow, concrete fixes instead
of restructuring:

1. **Fix `dispatch.py`'s independent `HostName` encoding.** Replace the local
   `Literal["claude", "codex"]` + hand-rolled validation with
   `renmark.hosts.HostKind` (or a thin re-export), so host identity has
   exactly one encoding project-wide. This is the one genuine duplication
   found — not a design flaw needing a new abstraction, just an unwired
   import.
2. **Adopt `ScheduleWakeup` and `ExitWorktree` as scoped, additive changes**
   inside `heartbeat.py` and the finish-skill worktree-cleanup call site
   respectively, gated by new optional fields on the existing
   `HostCapabilities` dataclass (not a new adapter layer). Both are leaf
   consumers already; no change to `state.py` or `cli/` is required.

Explicitly rejected: a generic "host adapter" abstraction, a plugin registry
for host tools, or splitting `hosts.py` into per-host modules — none of these
are justified by the current fan-out (5 decision points, 1 real duplication,
otherwise clean).

## Migration seams (if `ScheduleWakeup`/`ExitWorktree` adoption is approved)

- `renmark/hosts.py`: add `supports_schedule_wakeup: bool` and/or
  `supports_exit_worktree: bool` fields to `HostCapabilities` + both
  `_CAPABILITIES` entries (default `False` for `UNKNOWN`).
- `renmark/heartbeat.py`: the cron-emission function(s) gain a
  `capabilities_for(host)` read and a native-vs-cron branch.
- Finish-skill worktree-cleanup call site (`finish/SKILL.md` §3.6, and/or a
  thin wrapper added to `renmark/worktree.py` if the removal call is moved
  into Python): gains the equivalent host-capability-gated branch.
- `renmark/dispatch.py`: separately, replace local `HostName` literal with
  `renmark.hosts.HostKind` to close the duplication found in §2 (independent
  of the ScheduleWakeup/ExitWorktree work, but same file family).

---

## Discovery Direction Gate — decision (2026-08-06)

**Direction approved:** Targeted native-tool adoption within the existing
architecture. No new abstraction layer.

**Scope for stages 6-8:**
1. Fix `dispatch.py`'s independent `HostName` encoding — consolidate onto
   `hosts.py`'s `HostKind`/`capabilities_for`, eliminating the duplication
   stage 5 found.
2. Adopt `ScheduleWakeup` as an additive resume-nudge for the usage-pause
   path (`renmark/usage.py`) — complementing, never replacing, the existing
   `PauseState`/`pipeline.json` persistence (ScheduleWakeup is
   session-scoped only, does not survive `/clear`).
3. Adopt `ExitWorktree` for the one mutating `git worktree remove` shell-out
   in `finish/SKILL.md` §3.6.
4. Wire `renmark.task_tracking` into the live-Codex dispatch path, closing
   REQ-31's Codex gap for real (the PRD text was already amended this same
   session; this closes the code side).
5. Explicitly KEEP unchanged: `WorkOrder`/capability-envelope/G11 isolation,
   the already-adopted Workflow-fanout decision, `renmark.task_tracking`'s
   domain logic (evidence requirements, self-approval guard) — confirmed by
   stage 4's external research as genuine value neither host provides
   natively.

**Rejected alternatives:** a formal host-adapter abstraction layer (stage
5's own modularity finding says the current shape is already clean enough
to add a hypothetical 3rd host without restructuring); deferring everything
except the dispatch.py fix (Owner chose the fuller scope).
