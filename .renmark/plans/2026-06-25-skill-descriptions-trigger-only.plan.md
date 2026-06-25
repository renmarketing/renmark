---
artifact_type: plan
schema_version: 1
created_at: 2026-06-25T00:00:00Z
source_sha: 184a75499dec4a0e981736fec1f1acaa188dbcbb
related_plan: null
generator: opus
stale_after: 2026-09-25T00:00:00Z
dependency_refs:
  - .renmark/research/2026-06-25-external-skills-study.research.md
completion_state: complete
confidence: high
validation_status: validated
---

# Plan — trigger-only skill descriptions + disable-model-invocation (P1+P2)

## Goal
Cut steady-state per-turn context/token load and sharpen plain-word auto-routing by
(A) rewriting every skill `description` to TRIGGER-ONLY (WHEN + plain-word triggers; workflow
recap moves to the body; collapse synonym lists) and (B) adding `disable-model-invocation: true`
to the 11 zero-LLM / meta / human-driven skills so their descriptions leave the model's context
while their slash commands keep working.

## Hard constraints (from coupling investigation; baseline = 62 tests green)
1. Each description lives in **2 files** — `plugin/skills/<n>/SKILL.md` + `plugin/commands/<n>.md`.
   Both must be rewritten to the **same** text per skill (≥25% token overlap or `description_drift`
   audit BLOCKS, asserted by `test_audit.py::test_run_audit_real_repo`). Easiest: write once, paste both.
2. **Quote** any description containing `: ` (colon-space) or inner quotes, else strict-YAML
   (`lint_frontmatter_values`) fails. Repo is currently 0 frontmatter issues — don't introduce the first.
3. `disable-model-invocation: true` on **SKILL.md only**, exact hyphenated spelling (a typo silently no-ops).
4. Keep all 27 skills (inventory count assertion `>= 23`). No test asserts trigger phrasing — safe to reword.

## Classification
Tier: **standard** (frontmatter-only, no logic, strong deterministic verifier, but ~54 files / 27 skills).
Lane: full (already on `feature/skill-descriptions-trigger-only`). Review: codereview → finish.

## Tasks
- **T1** (parallel) — 11 meta skills: rewrite descriptions to trigger-only **and** add
  `disable-model-invocation: true` to each SKILL.md. Skills: analytics, usage, inventory, help,
  approve, resume, doctor, hygiene, audit, scan, check-plan. (22 description edits + 11 flag adds.)
- **T2** (parallel) — pipeline group A descriptions → trigger-only: start, feature, debug, roadmap,
  finish, init, setup. (14 files.)
- **T3** (parallel) — pipeline group B descriptions → trigger-only: brainstorm, plan, orchestrate,
  verify, codereview, prd, backlog, blueprint, loop. (18 files.)
- **T4** (sequential, after T1–T3) — verifier sweep + fix any strict-YAML/drift residue.

T1/T2/T3 edit disjoint file sets → safe in parallel, no shared file.

## Verifier (exact, from repo root)
```
python3 -m pytest tests/test_audit.py tests/test_lint.py -q   # decisive gate
python3 -m pytest -q
ruff check .
mypy .
```

## Rewrite style contract (applies to every description)
- Lead with WHEN + a few distinct plain-word triggers; remove "Runs A → B → C …" and "Routes … to …".
- Collapse synonym trigger lists to a few branches (don't list 6 near-synonyms).
- Preserve the `/renmark:<name>` typed-trigger mention and genuinely distinct trigger phrases that
  drive auto-routing (e.g. debug's "why is X failing", feature's "add X").
- Workflow detail that's being cut must already exist (or be added) in the SKILL.md body.
