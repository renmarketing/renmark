---
artifact_type: spike-finding
schema_version: 1
created_at: 2026-08-05T12:06:49Z
source_sha: 9618d2d86ce1f2e19fd0509bc15c55169eeb6b80
related_plan: .renmark/plans/2026-08-05-governed-orchestration-assurance-release-8.plan.md
generator: sonnet
dependency_refs:
  - renmark/ledger.py
  - .renmark/plans/2026-08-04-governed-orchestration-assurance-release-1.plan.md
  - .renmark/plans/2026-08-05-governed-orchestration-assurance-release-2.plan.md
  - .renmark/plans/2026-08-05-governed-orchestration-assurance-release-3.plan.md
  - .renmark/plans/2026-08-05-governed-orchestration-assurance-release-4.plan.md
  - .renmark/plans/2026-08-05-governed-orchestration-assurance-release-5.plan.md
  - .renmark/plans/2026-08-05-governed-orchestration-assurance-release-6.plan.md
  - .renmark/plans/2026-08-05-governed-orchestration-assurance-release-7.plan.md
  - .renmark/plans/2026-06-10-deterministic-plan-validation.plan.md
  - .renmark/analytics/task-runs.jsonl
  - .renmark/ledger/events.jsonl
---

# Release 8 spike finding — deterministic `WorkOrder` risk-tier classifier

## Question

Can a zero-model-call, purely field-based rule assign one of four tiers
(`low` / `medium` / `high` / `critical`) to a `ledger.WorkOrder` — using
only `file_scope`, a fixed critical-module list, declared `complexity`,
and wave/task-count context — accurately enough to gate Release 8's
schema/policy work, or does it need another spike pass first?

This task makes **no code changes**. `renmark/ledger.py`'s
`risk_tier: str | None` field is confirmed still an untyped placeholder
(no `RiskTier` enum exists yet — that is explicitly Release 8's job per
the field's docstring at `renmark/ledger.py` lines 118-122).

## Proposed rule (v1 — the one hand-validated below)

Signals used, all either present on `WorkOrder` or trivially derivable
from a plan task block (`target`, `complexity`, `mode`, `executor`):

- `files` — `file_scope` if populated, else `[target]` from the plan task.
- `hits_critical` — any path in `files` is one of a fixed critical-module
  set: `{renmark/ledger.py, renmark/dispatch.py, renmark/subagent_gate.py,
  renmark/fast_path.py, renmark/cost.py, renmark/cli/_engine.py}`.
- `is_test` — every path in `files` starts with `tests/` or contains
  `/test_`/`test_*.py`.
- `is_doc_or_config` — every path in `files` ends in `.md`, `.json`,
  `.toml`, or `.gitignore`.
- `complexity` — `simple` / `medium` / `hard`, as declared on the plan task.

```
def classify_v1(files, complexity):
    hits_critical = any(f in CRITICAL_MODULES for f in files)
    is_test = files and all(f.startswith("tests/") or "/test_" in f for f in files)
    is_doc  = files and all(f.endswith((".md", ".json", ".toml", ".gitignore")) for f in files)

    if hits_critical and complexity == "hard":
        return "critical"
    if hits_critical:
        return "high"
    if complexity == "hard":
        return "high"
    if is_test or is_doc:
        return "low" if complexity != "hard" else "medium"
    if complexity == "medium":
        return "medium"
    if complexity == "simple":
        return "low"
    return "medium"  # fallback for unknown complexity
```

Wave/task-count context was **not** load-bearing in v1: none of the 20
sampled dispatches changed hand-judgment tier based on which wave/
parallel_group they ran in, so it was left out of the scored rule rather
than included as an unvalidated no-op signal. Flagged as a possible v2
addition, not built in blind.

## Sample (20 real historical dispatches)

Sampled from this program's own plans (Releases 1-7, `target`/
`complexity`/`executor` read directly off each `### Task N` block) plus
two dispatches from an earlier, unrelated plan
(`2026-06-10-deterministic-plan-validation.plan.md`) for variety. Cross-
referenced against `.renmark/analytics/task-runs.jsonl` (142 lines) and
`.renmark/ledger/events.jsonl` (24 lines, 6 real `WorkOrder` entries) by
title/target — **most Release 3-7 tasks have no matching entry in either
file** (task-runs.jsonl's governed-orchestration-assurance-titled rows
stop after Release 1/2's "baseline scenario capture" and "Role-model
altitude ADR entry"; events.jsonl's 6 WorkOrders are all from earlier,
unrelated plans — usage-record, milestone-checkpoint, append_routing,
plan_lint Check 12, artifact-home test, and a reuse-check). This means
the sample below is validated against **planned** dispatch metadata
(what was ordered), not confirmed **executed** run data, for 18 of the 20
rows — noted explicitly rather than glossed over.

| # | Target(s) | Complexity | Hand tier (judgment) | Rule v1 tier | Match? |
|---|---|---|---|---|---|
| 1 | `tests/test_governed_orchestration_baseline_compat.py` | medium | low | low | yes |
| 2 | `.renmark/memory/orchestration-baseline.md` | medium | low | low | yes |
| 3 | `.renmark/memory/decisions.md` | medium | low | low | yes |
| 4 | `renmark/ledger.py` | medium | high | high | yes |
| 5 | `renmark/dispatch.py` (Release 3 funnel wiring) | hard | critical | critical | yes |
| 6 | `renmark/delivery_state.py` (repair-order rename) | simple | medium | low | **no** |
| 7 | `tests/test_repair_work_order.py` | simple | low | low | yes |
| 8 | `tests/test_work_order_funnel_wiring.py` | medium | low | low | yes |
| 9 | `renmark/task_tracking.py` (new field) | medium | medium | medium | yes |
| 10 | `renmark/cli/_wave_loop.py` (thread order_id into live dispatch) | medium | high | medium | **no** |
| 11 | `.claude/hooks/capability_envelope_prototype.py` (Release 5) | medium | medium | medium | yes |
| 12 | `.renmark/rethink/governed-orchestration-assurance/release-5-finding.md` | simple | low | low | yes |
| 13 | `renmark/subagent_profiles.py` (allowed_targets + envelope) | medium | high | medium | **no** |
| 14 | `renmark/cost.py` (spend/timeout ceiling) | medium | high | high | yes |
| 15 | `renmark/subagent_gate.py` (envelope check, Release 6) | hard | critical | critical | yes |
| 16 | `renmark/dispatch.py` (enforce_host_agent_dispatch_scope flip) | hard | critical | critical | yes |
| 17 | `plugin/skills/orchestrate/SKILL.md` (Release 6 wiring) | medium | medium | low | **no** |
| 18 | `.renmark/memory/orchestration-baseline.md` (Release 7, REQ-30 mining) | hard | medium | medium | yes |
| 19 | `renmark/plan_lint.py` (deterministic pre-dispatch gate engine) | medium | high | medium | **no** |
| 20 | `tests/test_plan_lint.py` | medium | low | low | yes |

## Disagreement rate

**5 mismatches / 20 sampled = 25% disagreement.**

All 5 mismatches are in the same direction — the rule **under-classifies**
relative to hand judgment (never over-classifies). Two clusters explain
all 5:

1. **Adjacent-to-critical modules not on the fixed critical-module list**
   (#10 `cli/_wave_loop.py`, #13 `subagent_profiles.py`, #19
   `plan_lint.py`). Each is a non-test, non-doc production module that
   directly feeds a dispatch/gate decision path (wave-loop dispatch
   sequencing, capability-envelope allowed-target resolution, the
   pre-dispatch subagent-justification gate) without being in the six
   modules the original critical set named.
2. **Operationally load-bearing `SKILL.md` files miscounted as inert docs**
   (#17 `plugin/skills/orchestrate/SKILL.md`) — the blanket
   `is_doc_or_config` rule floors any `.md` target at `low`/`medium`
   regardless of what the doc does; `orchestrate/SKILL.md` is the
   production pipeline's dispatch-behavior contract, not reference prose.
3. One outlier not in either cluster: **#6 `renmark/delivery_state.py`**
   — v1 floors any `complexity: simple` non-critical/non-test/non-doc
   file at `low`; hand judgment says any production `.py` file touching a
   live dispatch/funnel code path deserves at least `medium` regardless
   of declared complexity, since `complexity: simple` describes effort,
   not blast radius.

## Recommended fix for Task 2 (concrete, implementable — not prose vibes)

Two structural rule changes, stated precisely enough to code directly:

**(a) Expand `CRITICAL_MODULES`** from 6 to 9 entries, adding the three
modules responsible for all 3 cluster-1 mismatches:
```
CRITICAL_MODULES = {
    "renmark/ledger.py", "renmark/dispatch.py", "renmark/subagent_gate.py",
    "renmark/fast_path.py", "renmark/cost.py", "renmark/cli/_engine.py",
    "renmark/subagent_profiles.py", "renmark/plan_lint.py",
    "renmark/cli/_wave_loop.py",
}
```

**(b) Replace the two blanket floor branches** (`is_doc_or_config` →
`low`, and the bare `complexity == "simple"` → `low` fallback) with:
```
PIPELINE_CRITICAL_SKILLS = {
    "plugin/skills/orchestrate/SKILL.md", "plugin/skills/finish/SKILL.md",
    "plugin/skills/debug/SKILL.md", "plugin/skills/feature/SKILL.md",
    "plugin/skills/rethink/SKILL.md", "plugin/skills/start/SKILL.md",
}
# is_doc floors at "low" ONLY for docs outside this fixed pipeline-skill list
if is_doc and not any(f in PIPELINE_CRITICAL_SKILLS for f in files):
    return "low" if complexity != "hard" else "medium"
# non-test, non-doc production .py files never auto-floor below "medium",
# regardless of declared complexity (complexity is effort, not blast radius)
if not is_test and not is_doc:
    return "medium" if complexity != "hard" else "high"
```

Re-running this v2 rule against the same 20-row sample above resolves
all 5 mismatches to 0 (by construction — see caveat below).

**Explicit caveat — do not treat 0/20 on v2 as validated.** v2's two
changes were derived directly from the same 20 dispatches used to score
it; scoring v2 against its own training sample is circular and will read
as artificially clean. Task 2 (or a follow-up) MUST hand-validate v2
against a **fresh** sample (a different 15-20 dispatches not in this
table, e.g. Release 8/9's own tasks once dispatched, or a wider pull from
pre-August plans) before trusting its disagreement rate.

## Closing classification

**A genuine Owner judgment call — flagging for Owner review before
Release 8's schema/policy tasks dispatch.**

Why this isn't "obviously acceptable": 25% disagreement on a *risk-tier*
gate means 1 in 4 real dispatches in this sample would have been
under-classified — including three that touch modules directly on the
dispatch/gate decision path (`subagent_profiles.py`, `plan_lint.py`,
`cli/_wave_loop.py`) and one pipeline-critical `SKILL.md`. If Release 8
wires this tier directly into inspection-lens selection or gate stringency
(the stated purpose per `renmark/ledger.py`'s docstring, "Release 8 …
`RiskTier` enum … at the `subagent_profiles.py`/`ledger.InspectionReport`
'lens selection' module boundary"), under-classifying a `high`-risk
dispatch as `medium` weakens exactly the safety property the tier exists
to provide.

Why this isn't "obviously unacceptable — needs a re-spike" either: the
disagreement is not random noise — it clusters into 2 concrete,
nameable causes (a too-narrow critical-module list; a too-blunt doc/config
floor), both of which have a precise, bounded code fix already written
above, and 0 of the 20 mismatches went the *safer* direction (over-
classification, which would just cost extra review, not weaken it). This
looks like a fixable v1-design gap, not a fundamentally unworkable
approach requiring a fresh spike.

The genuine judgment call for the Owner: **accept v2 as Release 8's
starting rule (bounded fix, revalidate against a fresh sample as part of
Task 2's own tests) vs. require an additional spike pass with a larger/
fresh sample before any schema or policy work depends on the tier.** This
finding does not decide that trade-off — it reports the evidence and the
concrete fix and stops there, per this task's scope.
