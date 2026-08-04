---
artifact_type: rethink-baseline
schema_version: 1
created_at: 2026-08-03T00:00:00Z
source_sha: c6741856f7603aac3e01f324fbaa4b7e6478155e
related_plan: null
generator: renmark:researcher
stale_after: null
dependency_refs: [".renmark/memory/orchestration-baseline.md"]
---

# renmark Behavioral Baseline (Stage 2 of `/renmark:rethink`)

Target: renmark's own Python runtime (`renmark/`) + plugin (`plugin/`). Scope:
document CURRENT observable behavior — not correctness judgment, not the PRD
(a separate stage). Non-goal per dispatch: no change to skill prose, stage
wording, gate wording, or command UX.

## Tooling note — execution limitation for this research pass

This researcher subagent has no Bash tool in its toolset (Read/Grep/Glob/
Write/WebFetch/WebSearch only), so `pytest -q` and `renmark-execute
--behavior` could NOT be executed live in this session. Rather than fabricate
numbers, this baseline reports the most recent **fresh, evidence-backed**
full-suite result recorded in `CHANGELOG.md`, cross-checked against git state:

- Current `HEAD` (`main`): `c6741856f7603aac3e01f324fbaa4b7e6478155e` (`c674185`
  — "release: bump version 0.40.0 -> 0.41.0", a version-only commit).
- The immediately preceding commit `fa80a44` merged
  "orchestration-baseline-controls" and its CHANGELOG entry
  (2026-08-02, "usage instrumentation, context checkpoint, routing
  enforcement, artifact lifecycle") states: **"Full suite: 1931 passed, 31
  skipped."** No test-affecting change exists between that commit and current
  HEAD (only a version bump), so this is the last known-good, traceable full
  suite result for the current tree.
- `tests/` contains 106+ test files (`tests/test_*.py`); `tests/test_behavior.py`
  alone defines 15 test functions and is the deterministic scaffolding guard
  for `renmark-execute --behavior` (per CLAUDE.md's "Behavioral test tier /
  P8": asserts `lifecycle.next_steps`, `skill_preamble`, `plan_lint` produce
  contract-required output; no network, no token spend, no model call).
- **Action item for whoever runs the next live stage with Bash access:**
  re-run `pytest -q` and `renmark-execute --behavior` fresh before any
  transformation work starts, and update this artifact's numbers — do not
  treat the 1931/31 figure as current proof, only as the last recorded
  evidence.

## Pipelines with documented observable output

11 of 12 user-facing pipeline/gate skills below have a documented, artifact-
producing contract (init, start, feature, debug, roadmap, finish, rethink,
orchestrate, plan, prd, verify — codereview also qualifies as a 12th gate).
Source: `plugin/commands/*.md` (31 files) + `plugin/skills/*/SKILL.md` (30
skill dirs) + `renmark/lifecycle.py`.

| Pipeline | Observable artifacts / state on success |
|---|---|
| `init` | Bootstraps `.renmark/memory/*` (`INDEX.md`, `project.md`, `routing.md`, `dev-standards.md`, `project-map.md`), `.renmark/config.json`; registers project in `skillmeta`-adjacent memory |
| `brainstorm` | `.renmark/specs/YYYY-MM-DD-<topic>.spec.md`; lifecycle stage → `brainstorm-complete` |
| `plan` / `prd` | `.renmark/plans/YYYY-MM-DD-<topic>.plan.md` (or `PRD.md` update via UPDATE gate); lifecycle stage → `plan-drafted` |
| `check-plan` | Lint verdict only (no new artifact) → lifecycle stage `plan-validated` on PASS |
| `orchestrate` | Executes plan tasks; writes `.renmark/state/pipeline.json` (wave index, retry counts), `.renmark/state/wave-summaries/*`, `.renmark/ledger/events.jsonl` entries (WorkOrder/WorkResult), `.renmark/analytics/task-runs.jsonl`; lifecycle stage → `created` |
| `verify` | `.renmark/reviews/*.qa.md` (generator `verify-qa`, `validation_status`); lifecycle stage → `verified` |
| `codereview` | `.renmark/reviews/*.review.md` (independent-review generator `codereview`); lifecycle stage → `reviewed` |
| `feature` | `begin_feature()` resets lifecycle to `stage="init"` on a new branch, then re-runs the brainstorm→plan→orchestrate→verify chain scoped to the change |
| `debug` | `.renmark/debug/<session-id>/*` isolated artifacts; root-cause-first discipline; feeds back into `verify` |
| `roadmap` | `.renmark/memory/roadmap.md` / `.renmark/roadmap/*` gap analysis (no lifecycle stage change — aux skill) |
| `finish` | Flips lifecycle stage → `ready-to-release`/`released`; `clear_lifecycle()` on merged/released branch; PR/tag per finish-lane (quick/release/self-update/full) |
| `rethink` | `.renmark/rethink/<topic>/*` staged artifacts (survey, baseline — this file, PRD acceptance contract, external discovery, modularity assessment, classification, blueprint, roadmap) culminating in a `renmark.program` handed to Agency/Orchestrator machinery; never touches target code before the Execution Gate |
| `audit` / `inventory` / `scan` | `.renmark/audits/audit-report-*.{md,json}`, `.renmark/audits/inventory-*.{md,json}` |
| `resume` | Zero-LLM: reads `lifecycle.json` (≤1KB), prints `next_recommended`, exits |

All state-bearing pipelines confirm to `CLAUDE.md`'s canonical artifact homes
(`.renmark/specs|plans|reviews|research|state|memory|logs|debug|audits`) —
grep of `plugin/skills/*/SKILL.md` and `renmark/lifecycle.py` found no writer
outside that convention.

## Lifecycle stage contract — confirmed against code

`renmark/lifecycle.py`'s `STAGES` list matches the canonical order in
`CLAUDE.md` exactly:

```
init → brainstorm-complete → plan-drafted → plan-validated → created →
verified → reviewed → documented → ready-to-release → released
```

`NEXT_BY_STAGE` maps each stage to its next command (`/renmark:brainstorm` …
`/renmark:finish`); `documented` is explicitly a **dormant** stage (no writer
today, routes through `finish` if a legacy file carries it). `ready-to-release`
has no dedicated release skill yet — routes to a manual `git tag` + zip hint.
`stages_completed` accumulates prior stages idempotently on transition.
`LIFECYCLE_JSON_BYTE_BUDGET = 1024` bytes is enforced at write time
(`LifecycleBloatError` on overflow) — this is a hard, code-level guard, not
just a CLAUDE.md convention. `write_lifecycle` also runs `schemas.validate_lifecycle`
writer-side before persisting.

## Host-capability contracts (Claude Code vs Codex) — confirmed against code

`renmark/hosts.py` defines `HostCapabilities` per `HostKind` (`CLAUDE_CODE`,
`CODEX`, `UNKNOWN`):

| Capability | Claude Code | Codex | Unknown |
|---|---|---|---|
| `selector_tool` | `AskUserQuestion` | `request_user_input` (marked unavailable) | `None` |
| `selector_available` | `True` | `False` | `False` |
| `supports_clear` | `True` | `False` | `False` |
| `supports_resume` | `True` | `False` | `False` |
| `supports_compact` | `True` | `False` | `False` |

`resolve_host()` precedence: explicit `host` arg → `RENMARK_HOST` env → Codex
process markers (`CODEX_THREAD_ID` / `CODEX_INTERNAL_ORIGINATOR_OVERRIDE`) →
default `CLAUDE_CODE`.

`lifecycle.skill_preamble(repo, skill, host=...)` behavior confirmed in code:
- On `verdict == "clear"` (cross-domain transition detected) AND
  `host_capabilities.supports_clear` is `True` (Claude Code): returns a string
  prefixed `CONTEXT_GATE_CLEAR:` instructing the caller to block on
  `AskUserQuestion` before proceeding, and does NOT record the invocation
  (keeps the gate live on re-entry).
- On the same trigger with `supports_clear` `False` (Codex/unknown): `verdict`
  is downgraded to `None` in code — the transition is recorded and the skill
  continues without presenting an unusable gate; no `CONTEXT_GATE_CLEAR:`
  string is ever returned for Codex.
- Headless mode (`_config.is_headless`) skips the interactive gate
  unconditionally regardless of host, appending a "headless mode: skipping
  interactive gate" note instead.
- `_CONTEXT_BYPASS_SKILLS = {"finish", "approve", "resume"}` never trigger the
  clear gate (advisory-only for these three, matching CLAUDE.md).
- `persist_compact_checkpoint` always writes `.renmark/state/compact_checkpoint.json`
  but sets `resume_cmd: null` when `host_capabilities.supports_resume` is
  `False` (Codex) instead of `/renmark:resume`.

## Measurable performance/cost baseline — `ORCHESTRATION-BASELINE-2026-08`

`.renmark/memory/orchestration-baseline.md` (pinned `v0.39.7`, commit
`d9cccc5`, 2026-08-02) is the canonical REQ-30 reference. Its actual state, as
recorded — **no fabricated numbers found or added here**:

- It documents *structural/qualitative* guarantees only (≤5-line/≤300-token
  orchestrator-visible output cap, deterministic-first gate, one-bounded-
  worker-by-default, cheapest-capable-model routing, fast path for bounded
  fixes, two delivery modes, ≤1KB zero-LLM resume) — all still cited as load-
  bearing in `CLAUDE.md`.
- It explicitly states real token/wall-clock/dispatch-count numbers for the
  four representative scenarios (Start / Feature-Fix / Orchestrate / Rethink)
  are **"not yet measured"** — the file's own open item, not something this
  research pass should invent.
- Its 2026-08-02 audit found per-run token/wall-clock telemetry effectively
  unmeasured in production (`tokens_in`/`tokens_out`/`duration_s` ~0 across
  `.renmark/state/usage.jsonl` and `.renmark/analytics/task-runs.jsonl`), and
  `context_budget_hint` has zero production callers as of that audit.
- Regression rule: any orchestration/routing/context/dispatch/gate-frequency
  change is blocked pre-release if it increases median token use or wall-clock
  by >15%, adds a routine gate, duplicates dispatch, leaks worker context into
  the orchestrator, or weakens verification/recovery — absent an explicit,
  evidence-backed Owner exception with a rollback path.

**Implication for the modernization PRD stage:** there is no numeric
token/latency baseline to hold constant yet — only the structural guarantees
above. Any architecture change must preserve those structural guarantees and,
per REQ-30, should not be the trigger for finally measuring the four
scenarios unless the Owner explicitly asks for it (that measurement itself
spends real tokens and needs its own cost-preview gate).

## Top risks — things easy to accidentally break during modernization

1. **`skill_preamble`'s host-branching logic is dense and order-dependent**
   (record-before-check invariant, headless bypass, bypass-skill set, additive
   `_with_mode_note`/`_with_agency_note`/`_with_headless_note` chaining). A
   refactor that reorders these calls or "simplifies" the tier logic risks
   silently changing when `CONTEXT_GATE_CLEAR:` fires or when Codex gets an
   unsupported gate — this is exactly the kind of UX-stability regression
   REQ-30 exists to block, and it is easy to break without a host-parity test
   catching it immediately.
2. **`LIFECYCLE_JSON_BYTE_BUDGET` (1KB) and the `LifecycleBloatError` guard**
   are a hard invariant, but `write_lifecycle`'s read-modify-write pattern
   (`stages_completed` accumulation, `artifacts` dict growth) means any
   architecture change that adds fields or grows history without matching
   trim logic (cf. the real `delivery_state.py` byte-budget bug fixed
   2026-08-02) can silently reintroduce a crash-on-every-invocation failure
   mode already seen once in this codebase.

## Files referenced

- `/home/renmark/projects/renmark/renmark/lifecycle.py`
- `/home/renmark/projects/renmark/renmark/hosts.py`
- `/home/renmark/projects/renmark/.renmark/memory/orchestration-baseline.md`
- `/home/renmark/projects/renmark/.renmark/audits/orchestration-baseline-audit-2026-08-02.md`
- `/home/renmark/projects/renmark/CHANGELOG.md`
- `/home/renmark/projects/renmark/PRD.md`
- `/home/renmark/projects/renmark/plugin/commands/*.md`
- `/home/renmark/projects/renmark/plugin/skills/*/SKILL.md`
- `/home/renmark/projects/renmark/tests/test_behavior.py`
