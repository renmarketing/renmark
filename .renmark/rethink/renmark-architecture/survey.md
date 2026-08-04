---
artifact_type: rethink-survey
schema_version: 1
created_at: 2026-08-03T00:00:00Z
source_sha: c674185
related_plan: null
generator: renmark:researcher
stale_after: null
dependency_refs: [".renmark/memory/project-map.md"]
---

# Internal system survey — renmark (Stage 1 of /renmark:rethink)

Scope note: this survey targets `renmark/` (Python runtime), not `plugin/skills/*/SKILL.md`
prose, per the Owner's transformation intake ("modernize architecture, do not
change pipeline behavior/UX"). No Bash tool was available in this session —
`pytest -q` / `ruff check` / `mypy .` could NOT be executed live; dev-gate
status below is inferred from the most recent CHANGELOG.md entries (which
report fresh full-suite runs from the same commit lineage as HEAD) and is
flagged as such, not fabricated as a live run.

## 1. Architecture and module boundaries

`renmark/` has 73 top-level/sub-package `.py` files. Rough size profile of the
largest modules (line counts, `grep -c ^`):

| Module | Lines | Role |
|---|---|---|
| `renmark/cli/_engine.py` | 1698 | CLI entrypoint + `execute_plan` — the central dispatch loop (wave dispatch, codex/claude routing, pause/resume, ledger emission, task tracking, delivery-state writes) |
| `renmark/lifecycle.py` | 1752 | Lifecycle stage state machine (G12) — largest single module in the repo |
| `renmark/dispatch.py` | 1063 | Wave-based parallel dispatcher, `AgentDispatch`/scope enforcement |
| `renmark/program.py` | 846 | Staged-program data model (rethink/roadmap execution unit) |
| `renmark/schemas.py` | 800 | JSON-shape validators for canonical state files |
| `renmark/delivery_state.py` | 716 | `.renmark/state/delivery.json` aggregate — milestones/work-packages/provenance |
| `renmark/agency.py` | 424 | Agency-mode discovery/handoff |

`renmark/cli/_engine.py` and `renmark/lifecycle.py` are outliers — both
1700+ lines, doing several distinct jobs each (in `_engine.py`: CLI arg
parsing, plan execution, codex/claude dispatch routing, pause/resume,
ledger/task-tracking side-effects, delivery-state bookkeeping). These are the
two clearest "modernize without changing behavior" targets: candidates for
splitting into cohesive submodules the same way `renmark/state/` was already
split (see below) — a precedent already proven in this codebase.

**Layering / dependency observations:**
- `renmark/state/` is a clean example of prior modernization: `state/__init__.py`
  re-exports a full public surface assembled from `_core.py` (paths/time
  helpers), `usage.py`, `pause.py`, `pipeline.py`, `logs.py`, `commits.py`,
  `skills.py` — each single-purpose, no circularity, backward-compatible
  import surface (`from renmark import state; state.X` and
  `from renmark.state import X` both still work). This is the template to
  reuse for `_engine.py`/`lifecycle.py` splits.
- `renmark/schemas.py` (a "shape validator" module, conceptually foundational)
  imports FROM `renmark/delivery_state.py`, `renmark/dispatch.py`, and
  `renmark/lifecycle.py` — i.e. a would-be low-level utility module depends
  upward on higher-level domain modules. Not a hard circular import (verified:
  `delivery_state.py` imports nothing from `renmark.*`; `dispatch.py` imports
  only `fast_path`/`parser`/`providers.claude_agent`), but it inverts the
  expected dependency direction and is worth flagging for the target blueprint.
- `renmark/agency.py` depends on `renmark.delivery_state` only; `renmark.program_driver`
  depends on `renmark.program`, `renmark.recurrence`, `renmark.summary`;
  `renmark.recurrence` depends on `renmark.scan`. No import cycle detected in
  the modules spot-checked (`_engine.py`, `agency.py`, `dispatch.py`,
  `delivery_state.py`, `schemas.py`, `program_driver.py`, `hygiene.py`,
  `plan_lint.py`, `work_packages.py`, `subagent_gate.py`, `usage.py`,
  `summary.py`, `heartbeat_checks.py`, `browser_cli.py`, `fast_path.py`,
  `parser.py`) — this is a spot-check, not an exhaustive import-graph
  traversal (no dependency-graph tool was run; would need `pydeps`/manual AST
  walk for full confidence).
- `renmark/cli/_engine.py` imports across nearly every domain module
  (`ledger`, `task_tracking`, `parser`, `providers.codex`, `state`, `verifier`,
  `_codex_runner`, `commands`) — it is the de facto integration root, which is
  expected for a CLI entrypoint but reinforces why it has grown to 1698 lines.

## 2. Data flows and stores

`.renmark/state/` (runtime, gitignored) currently holds: `program.json`,
`mode.json`, `agency.json`, `delivery.json`, `delivery-archive.json`,
`recurrences.json` + `.lock`, `usage.jsonl`, `tasks.json`,
`compact_checkpoint.json`, `last-skill.json`, plus several stray `.md` spec
files (`blueprint-t6-codex-spec.md`, `task2-spec.md`, `req14-*-task.md`,
`task2-codex-spec.md`) that look like leftover per-task dispatch scratch
artifacts rather than canonical state — worth a cleanup pass in the target
architecture (they are gitignored so not a source-control issue, only a
disk-hygiene one).

`lifecycle.json` is NOT listed under the sampled `.renmark/state/` glob
output (likely absent in this repo's current state — no in-flight feature —
but its path is `_lifecycle_path()` → `.renmark/state/lifecycle.json`,
confirmed in `renmark/lifecycle.py:310-311`).

**Lifecycle vs runtime separation — verified as honored in code:**
`renmark/lifecycle.py`'s module docstring explicitly states the contract
("lifecycle.json carries WORKFLOW state... runtime state lives in
pipeline.json") and the code matches: `lifecycle.py` only ever reads/writes
`_lifecycle_path()` (`.renmark/state/lifecycle.json`) and enforces a byte
budget (`LifecycleBloatError` at ~1KB, confirmed in code, not just docs).
`pipeline.json` lives entirely inside `renmark/state/pipeline.py`
(`PipelineState`, `write_pipeline_state`/`read_pipeline_state`), a separate
module with no import from `lifecycle.py`. The two state files are written
from different call sites and validated by different schemas
(`schemas.validate_lifecycle` vs pipeline's own shape). This separation is
real, not aspirational.

`.renmark/memory/` (committed) holds the durable project memory:
`project.md`, `architecture.md`, `stack.md`, `conventions.md`, `dev-standards.md`,
`routing.md`, `decisions.md`, `learnings.md`, `features.md`, `bugs.md`,
`roadmap.md`, `analytics.md`, `qa-flows.md`, `project-map.md`,
`orchestration-baseline.md`, `INDEX.md` — written by `renmark/memory.py`
(`log_feature`, `log_bug`, `log_decision`, etc.) and `renmark/init.py`
(project-map generation).

## 3. Features declared vs. actually live

- **`renmark/shadow.py`** (record-and-replay regression harness for
  dispatch/lifecycle/summary subsystems) — only referenced by its own test
  files (`tests/test_shadow.py`, `tests/test_shadow_live.py`) and its own
  design plan doc. No `renmark/cli/*` call site invokes it; it is a standalone
  `python -m renmark.shadow` CLI tool by design (per its docstring), not
  wired into any pipeline dispatch path. Live as a manual dev tool, not as
  part of the runtime pipeline.
- **`renmark/skillgen.py`** (SKILL.md doc-slimming lint) — same pattern:
  standalone `python -m renmark.skillgen` CLI, referenced only by its own test
  and a 2026-06-29 plan doc, no pipeline-runtime caller.
- **`context_budget_hint`** (`renmark/state/skills.py`) — CHANGELOG's own
  2026-08-02 entry ("orchestration baseline controls") explicitly names this
  as a previously "dead code, zero production callers" finding. A repo-wide
  grep after that fix still shows the function defined in `state/skills.py`
  with no call site elsewhere in `renmark/` — i.e. the audited fix wired
  *usage instrumentation* and *routing enforcement* but `context_budget_hint`
  itself may still be uncalled from production code; this needs a fresh
  eyes-on check by whoever executes the modernization plan, not asserted
  fixed here.
- Both `shadow.py` and `skillgen.py` are legitimate, tested, single-purpose
  dev-tool modules — not "vestigial" in the sense of rotting code, but they
  are NOT part of any `/renmark:*` pipeline's live execution path. A
  modernization pass should classify them explicitly (Keep-as-dev-tool vs.
  Remove) rather than silently carry them forward as if pipeline-critical.

## 4. Tests

113 test files under `tests/` (plus `tests/integration/`), covering nearly
every `renmark/*.py` module 1:1 (`test_lifecycle.py`, `test_dispatch.py`,
`test_program.py`, `test_program_driver.py`, `test_ledger.py`,
`test_agency_behavior.py`, `test_delivery_state.py`, `test_delivery_state_integration.py`,
`test_engine_resume_crosscheck.py`, `test_engine_budget_and_rollback.py`, etc.),
plus several milestone-specific regression suites named after release codes
(`test_wp8_scope_wiring.py`, `test_wp9_scope_enforcement_wiring.py`,
`test_r0_1_ux_regression_baseline.py`, `test_r0_2_dispatch_regression_baseline.py`)
— these are historical regression pins from the R-0.x ledger/inspector
milestones, still present and (per CHANGELOG) still passing, but their names
no longer map to a current architecture concept — a "what does this actually
guard" audit would help before any restructuring touches their subjects.

**Dev gates — could NOT be executed live in this session (no Bash tool
available).** Inferred status from CHANGELOG.md's most recent entries on the
same commit lineage as HEAD (`c674185`):
- 2026-08-02 "orchestration baseline controls" entry: "Full suite: 1931
  passed, 31 skipped."
- 2026-08-02 "add /renmark:rethink pipeline" entry: "Full suite: 1782 passed,
  31 skipped, 0 failed."
- An older 2026-08-01 R-0.2 entry explicitly flags: **"`ruff`/`mypy` remain
  unavailable in this environment (F7) — `pytest` was the only dev gate
  actually exercised."** This is a real, repo-acknowledged gap: `ruff check`
  and `mypy .` are declared as dev gates in `CLAUDE.md`/`pyproject.toml`
  (`mypy` configured `strict = true`) but there is direct evidence they have
  NOT reliably run in this environment historically. A modernization plan
  should not assume mypy-strict is currently green — it should treat "does
  mypy actually pass in strict mode" as an open question to verify fresh,
  not inherited truth.
- 31 skipped tests recur across multiple CHANGELOG entries without an
  explanation of why — worth a quick audit (likely environment-gated,
  e.g. `browser`/playwright-dependent tests) before restructuring near those
  areas.

## 5. Integrations / deployment / ops dependencies

Shells out via `subprocess.run` to:
- `git` — by far the most common (`init.py`, `fast_path.py`, `worktree.py`,
  `bootstrap.py`, `finish_lanes.py`, `summary.py`, `roadmap.py`, `sizing.py`,
  `health.py`, `release.py`) — rev-parse, diff, log, status, config, commit,
  init. Heavy, pervasive dependency on `git` being on PATH and the target repo
  being a git repo.
- `bash -c <command>` — `verifier.py` (runs the project's verifier command
  string) — hard Unix-shell assumption (bash specifically, not sh).
- `renmark-execute --resume` — `heartbeat.py` (self-recursive CLI invocation
  for scheduled recovery)
- `crontab -l` — `heartbeat.py` (Unix-only cron integration for
  `--emit-cron`)
- Claude Code CLI (`doctor.py`: `[cli, "plugin", "list", "--json"]`) and Codex
  CLI (`renmark/providers/codex.py`, not read in depth this pass) — both
  external CLIs assumed present for their respective dispatch paths.
- `renmark/browser.py` / `bin/renmark-browser` — Playwright, an optional dep
  group (`[project.optional-dependencies] browser`), not installed by
  default.

Hard filesystem assumptions: all state paths are relative to a discovered
repo root (`.renmark/...`); `verifier.py`'s `bash -c` assumes a POSIX shell
even though `pyproject.toml` targets py3.10+ cross-platform; `install.sh`
comment in `pyproject.toml` notes Windows/WSL gets a separate wrapper path
("install.sh still symlinks the canonical repo-aware Bash wrapper on Unix...
gives Windows/Codex a native executable") — i.e. there are already two
divergent code paths for Unix vs Windows entrypoints, a latent
cross-platform seam to be aware of during restructuring.

## 6. Pain and cost signals

- **TODO/FIXME/HACK density:** essentially zero. `renmark/` (73 files): 1
  occurrence (`renmark/cli/_engine.py`). `plugin/` (skills/commands/agents):
  1 occurrence (`plugin/skills/rethink/SKILL.md`). This is a very low-debt-marker
  codebase by that signal — but see below, the debt shows up as documented
  "known limitation" prose in CHANGELOG.md instead of inline TODOs (a
  deliberate convention per this repo's own rules: CHANGELOG "Do not change"
  blocks function as an external debt ledger).
- **Duplicated logic:** not deeply verified this pass (would need an
  AST-level similarity scan), but structurally: `_engine.py` (1698 lines)
  concentrates dispatch/pause/resume/ledger/task-tracking logic that overlaps
  conceptually with `dispatch.py` (wave scheduling) and `program_driver.py`
  (stage sequencing) — three modules each with their own notion of "what
  happens next," which is a plausible location for logic duplication or drift
  worth checking directly during the modularity assessment stage, not
  confirmed as duplicated here.
- **Stale/unmaintained deps:** `pyproject.toml` has a minimal, modern
  dependency surface — only `python-dotenv>=1.0.0` as a hard runtime dep;
  dev deps `pytest>=8.0.0`, `ruff>=0.6.0`, `mypy>=1.11`; optional
  `playwright>=1.40.0`. No stale/abandoned packages detected — this is not a
  dependency-debt codebase.
- **Known failure hotspots (from CHANGELOG.md, repeated same-area fixes):**
  1. **Delivery-state provenance byte budget** — fixed twice in close
     succession within the same 2026-08-02 entry: `append_provenance_event`'s
     count-based cap (24 events) didn't prevent `delivery.json` exceeding its
     4096-byte budget from long `detail` strings; a live crash was found and
     fixed with byte-aware trimming *in the same session* the audit was being
     done. This module (`renmark/delivery_state.py`) is a recurring
     size/budget-fragility hotspot.
  2. **`work_packages` archival step skipped** — a second, related regression
     class in the same file/session: `cli/_engine.py`'s `_complete_clean_run`
     wrote `work_packages` directly instead of calling the existing
     `archive_completed_work_packages`, "the same bug class surfaced a second
     time live during this session's own dispatches." Two same-shape bugs in
     one file in one session is a concrete hotspot signal for
     `delivery_state.py` + its `_engine.py` call sites specifically.
  3. **Lifecycle/delivery staleness on resume** — recurs across at least
     three separate CHANGELOG entries (R-0.1, R-0.2, R-0.3 release notes all
     mention `/renmark:resume` finding `delivery.json`/`lifecycle.json` stale
     relative to the actually-released milestone, corrected as "bookkeeping,
     not a blocker" each time) — a soft but repeated signal that the
     resume/reconciliation path between `lifecycle.py`, `delivery_state.py`,
     and `program.py` is where staleness bugs keep resurfacing.
  4. **R-0.2's "mechanism built but zero production callers" pattern**
     recurs structurally: R-0.2's own closeout notes 5 of 8 acceptance
     criteria were "correct-and-tested but with zero production callers,"
     required a follow-up wiring pass (WP-8/WP-9) to close, and even after
     that pass the closeout says the gap was "narrowed but not closed." This
     is the same shape as the `context_budget_hint`/`shadow.py`/`skillgen.py`
     findings above — a repo-level pattern (not a bug, an explicit and
     acknowledged tendency) of building schema/logic ahead of wiring it to a
     real call site. Worth naming explicitly as an architectural convention
     to either keep (deliberate staged rollout) or tighten (require a real
     caller before merge) in the target blueprint.
