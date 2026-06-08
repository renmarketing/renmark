# Plan — next-step-engine (Part 2 of 2): refit completion + lint drift-guard

**Spec:** `.renmark/specs/2026-06-08-next-step-engine.spec.md`
**Branch:** `feature/next-step-engine`
**Depends on:** Part 1 (the `_shared/next-steps.md` contract from Part 1 Task 1 must
exist — refit tasks read their citation snippet from it). Run Part 1 to completion first.

Part 2 refits the remaining 8 skills' hand-offs and adds a lint rule + test that
enforces every skill cites the contract (accepting `next-steps.md` OR `handoff-menu.md`,
so the gate skills verify/codereview/orchestrate pass unchanged). The lint test runs
LAST (parallel_group 3) — it depends on every refit being done.

---

### Task 1: refit blueprint hand-off
- **mode:** B
- **target:** plugin/skills/blueprint/SKILL.md
- **complexity:** simple
- **executor:** haiku
- **parallel_group:** 1
- **est_tokens:** 300
- **est_cost_usd:** 0.00
- **verifier:** grep -q "next-steps.md" plugin/skills/blueprint/SKILL.md
- **spec:**
  blueprint currently has NO next-step hand-off. Add a "What's next" section citing the
  aux/terminal-skill snippet from `plugin/skills/_shared/next-steps.md` (read the contract
  first; copy the exact aux snippet). After refreshing the blueprint, suggest resuming the
  in-flight feature's next stage (or `/renmark:roadmap` gap mode if none). Do not change
  blueprint's artifact-touchpoint behavior.

### Task 2: refit check-plan hand-off
- **mode:** B
- **target:** plugin/skills/check-plan/SKILL.md
- **complexity:** simple
- **executor:** haiku
- **parallel_group:** 1
- **est_tokens:** 300
- **est_cost_usd:** 0.00
- **verifier:** grep -q "next-steps.md" plugin/skills/check-plan/SKILL.md
- **spec:**
  Add the pipeline-skill citation blockquote from `plugin/skills/_shared/next-steps.md`
  (read it first; copy the exact pipeline snippet). After validation, the natural next step
  is `/renmark:orchestrate` (PASS) — let the shared contract drive it. Do not change
  check-plan's PASS/WARN/BLOCK verdict logic.

### Task 3: refit debug hand-off
- **mode:** B
- **target:** plugin/skills/debug/SKILL.md
- **complexity:** simple
- **executor:** haiku
- **parallel_group:** 1
- **est_tokens:** 300
- **est_cost_usd:** 0.00
- **verifier:** grep -q "next-steps.md" plugin/skills/debug/SKILL.md
- **spec:**
  debug currently has NO next-step hand-off. Add a "What's next" section citing the
  aux/terminal-skill snippet from `plugin/skills/_shared/next-steps.md` (read it first).
  After a fix, suggest re-running `/renmark:verify` to confirm, plus resuming the in-flight
  feature's next stage. Do not change debug's Iron-Law / root-cause flow.

### Task 4: refit doctor hand-off
- **mode:** B
- **target:** plugin/skills/doctor/SKILL.md
- **complexity:** simple
- **executor:** haiku
- **parallel_group:** 1
- **est_tokens:** 300
- **est_cost_usd:** 0.00
- **verifier:** grep -q "next-steps.md" plugin/skills/doctor/SKILL.md
- **spec:**
  doctor currently has NO next-step hand-off. Add a "What's next" section citing the
  aux/terminal-skill snippet from `plugin/skills/_shared/next-steps.md` (read it first).
  After diagnosis/fix, suggest re-running the skill that was failing, plus resuming the
  in-flight feature. Do not change doctor's diagnostic checks or --fix logic.

### Task 5: refit hygiene hand-off
- **mode:** B
- **target:** plugin/skills/hygiene/SKILL.md
- **complexity:** simple
- **executor:** haiku
- **parallel_group:** 1
- **est_tokens:** 300
- **est_cost_usd:** 0.00
- **verifier:** grep -q "next-steps.md" plugin/skills/hygiene/SKILL.md
- **spec:**
  hygiene currently has NO next-step hand-off. Add a "What's next" section citing the
  aux/terminal-skill snippet from `plugin/skills/_shared/next-steps.md` (read it first).
  Suggest resuming the in-flight feature's next stage after a hygiene pass. Do not change
  hygiene's existing behavior.

### Task 6: refit help hand-off
- **mode:** B
- **target:** plugin/skills/help/SKILL.md
- **complexity:** simple
- **executor:** haiku
- **parallel_group:** 1
- **est_tokens:** 300
- **est_cost_usd:** 0.00
- **verifier:** grep -q "next-steps.md" plugin/skills/help/SKILL.md
- **spec:**
  Add a brief "What's next" pointer to help's SKILL.md citing the aux-skill snippet from
  `plugin/skills/_shared/next-steps.md` (read it first). help is zero-cost/no-LLM — keep it
  that way; the citation is a static pointer (e.g. suggest `/renmark:start` or resuming the
  in-flight feature). Do not add LLM calls.

### Task 7: refit resume hand-off
- **mode:** B
- **target:** plugin/skills/resume/SKILL.md
- **complexity:** simple
- **executor:** haiku
- **parallel_group:** 1
- **est_tokens:** 300
- **est_cost_usd:** 0.00
- **verifier:** grep -q "next-steps.md" plugin/skills/resume/SKILL.md
- **spec:**
  resume already prints the recommended next command from lifecycle.json. Add a citation to
  `plugin/skills/_shared/next-steps.md` (aux-skill snippet — read the contract first) so its
  output format is the shared one. resume MUST stay zero-LLM / pure file IO — the citation is
  a static reference, not a new code path. Do not change its cold-start recovery logic.

### Task 8: refit setup hand-off
- **mode:** B
- **target:** plugin/skills/setup/SKILL.md
- **complexity:** simple
- **executor:** haiku
- **parallel_group:** 1
- **est_tokens:** 300
- **est_cost_usd:** 0.00
- **verifier:** grep -q "next-steps.md" plugin/skills/setup/SKILL.md
- **spec:**
  Add a "What's next" section to setup's SKILL.md citing the aux-skill snippet from
  `plugin/skills/_shared/next-steps.md` (read it first). After adding renmark to a project,
  suggest `/renmark:prd` (pin product direction) then `/renmark:start` / `/renmark:roadmap`.
  Do not change setup's non-destructive merge behavior.

### Task 9: lint next-steps citation rule
- **mode:** B
- **target:** renmark/lint.py
- **complexity:** medium
- **executor:** sonnet
- **parallel_group:** 2
- **est_tokens:** 1000
- **est_cost_usd:** 0.03
- **verifier:** python3 -c "from renmark.lint import lint_next_steps_citation; print('ok')" && ruff check renmark/lint.py && mypy renmark/lint.py
- **spec:**
  Add `lint_next_steps_citation(plugin_dir)` to `renmark/lint.py`, modeled on the existing
  `lint_skill_files` / `lint_command_shims` (read them first; reuse the same skip set for
  `_shared` and any non-skill dirs). For every `skills/<name>/SKILL.md`, it is an issue if the
  file cites NEITHER `next-steps.md` NOR `handoff-menu.md` (gate skills satisfy via
  handoff-menu.md). Return a `list[str]` of issues in the same format as the sibling linters.
  Wire it into whatever aggregator runs all lint checks (e.g. a top-level `lint_plugin` /
  `run`/`main`) so it's part of the normal lint run. Keep style/imports consistent; stdlib only.

### Task 10: lint citation test
- **mode:** A
- **target:** tests/test_lint_next_steps.py
- **complexity:** medium
- **executor:** sonnet
- **parallel_group:** 3
- **est_tokens:** 1200
- **est_cost_usd:** 0.03
- **verifier:** python3 -m pytest tests/test_lint_next_steps.py -q
- **spec:**
  Write pytest tests for `lint_next_steps_citation` (sonnet per ADR-007 — new test file).
  Two kinds of test:
  1. **Synthetic fixture** (tmp_path plugin dir): a skill SKILL.md citing next-steps.md →
     no issue; one citing handoff-menu.md only → no issue; one citing neither → exactly one
     issue naming that skill. Follow tmp-dir patterns in existing `tests/`.
  2. **Live guard:** run `lint_next_steps_citation` against the REAL `plugin/` dir and assert
     it returns ZERO issues — this proves every shipped skill (after Part 1 + Part 2 refits)
     cites the contract. This test is why Task 10 is parallel_group 3 (runs after all refits).

---

## Cost preview (Part 2)

| Task | Executor | Total tokens (incl. ~10k overhead) | Cost |
|---|---|---|---|
| 1–8 refit (haiku ×8) | haiku | 10,300 ea | $0.0082 |
| 9 lint rule | sonnet | 11,000 | $0.0330 |
| 10 lint test | sonnet | 11,200 | $0.0336 |

**Tasks: 10 (3 parallel groups). Executors: haiku×8, sonnet×2.**
**Total tokens: ~104k. Total cost: ~$0.075**

---

## Combined (Part 1 + Part 2)

**21 tasks total · ~$0.29 · executors: haiku×13, sonnet×8.** All 19 skills end up citing
the contract (gate skills verify/codereview/orchestrate via the pre-existing handoff-menu.md
citation, accepted by the lint).
