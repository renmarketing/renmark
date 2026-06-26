---
artifact_type: plan
schema_version: 1
created_at: 2026-06-26T00:00:00Z
source_sha: 5d227fb
related_plan: .renmark/plans/2026-06-26-p10-headless-fixes.plan.md
generator: plan
dependency_refs:
  - plugin/skills/_shared/headless-contract.md
---

# Plan — P10 wire resolve_gate into the dangerous-gate skills

Scopes the "under-built" follow-up to its real surface (per gate-point audit):
the 5 dangerous-gate callsites in 4 skills. Safe gates (22 skills) already inherit
headless behavior via the shared menu files — no per-skill change. Each task adds a
"Headless gate" instruction block (in the SKILL.md body, NOT frontmatter — must not
regress v0.20.0 trigger-only descriptions) telling the skill: at this gate, consult
`renmark.headless.resolve_gate(repo, "<gate>", kind="dangerous", originating_skill="<skill>", what="<one line>")`; if it returns a `needs_input` envelope (headless), emit that JSON + `render_return(envelope)` prose and STOP — do NOT render the picker; otherwise render the interactive menu exactly as today. Pattern reference: `headless-contract.md §Runtime helper`.

**Do not change:** SKILL.md frontmatter (descriptions stay trigger-only); the
interactive (human-present) path is unchanged — wiring only adds the headless branch.
Per ADR-035, resolve_gate returns interactive when a human may be present.

### Task 1: wire finish merge/release gate
- **mode:** B
- **target:** plugin/skills/finish/SKILL.md
- **complexity:** medium
- **executor:** sonnet
- **parallel_group:** 1
- **est_tokens:** 450
- **est_cost_usd:** 0.03
- **verifier:** `grep -q "resolve_gate" plugin/skills/finish/SKILL.md`
- **serves:** under-built-followup
- **spec:**
  At the merge/release hand-off (~line 193, the `[m] Merge [r] Release` menu), add a
  "Headless gate" instruction: before rendering the picker, call
  `resolve_gate(repo, "merge"|"release", kind="dangerous", originating_skill="finish", what=<what is being merged/released>)`. If headless → emit the `needs_input`
  envelope + `render_return` prose and STOP (the contract: headless can never approve
  merge/release). If interactive → render the existing menu unchanged. Do not alter
  the human-gated REQ-12 wording; add the headless branch alongside it.

### Task 2: wire plan dispatch gate
- **mode:** B
- **target:** plugin/skills/plan/SKILL.md
- **complexity:** medium
- **executor:** sonnet
- **parallel_group:** 1
- **est_tokens:** 400
- **est_cost_usd:** 0.03
- **verifier:** `grep -q "resolve_gate" plugin/skills/plan/SKILL.md`
- **serves:** under-built-followup
- **spec:**
  At the Step 8b dispatch gate (~line 191), add the "Headless gate" branch:
  `resolve_gate(repo, "dispatch", kind="dangerous", originating_skill="plan", what="dispatch N tasks ~$X")`. Headless → emit needs_input + prose, STOP (cost/dispatch
  approval needs a human). Interactive → existing dispatch menu unchanged. Respect the
  single-dispatch-gate ownership rule (only the standalone-plan path owns this gate;
  the embedded-in-feature path still suppresses it — the headless branch lives in the
  same standalone-only block).

### Task 3: wire orchestrate cost gate
- **mode:** B
- **target:** plugin/skills/orchestrate/SKILL.md
- **complexity:** medium
- **executor:** sonnet
- **parallel_group:** 1
- **est_tokens:** 400
- **est_cost_usd:** 0.03
- **verifier:** `grep -q "resolve_gate" plugin/skills/orchestrate/SKILL.md`
- **serves:** under-built-followup
- **spec:**
  At the pre-flight cost gate (~line 77, the `"Proceed? [y/N]"` after
  `renmark-execute --dry-run`), add the "Headless gate" branch:
  `resolve_gate(repo, "cost", kind="dangerous", originating_skill="orchestrate", what="~$X across N tasks")`. Headless → emit needs_input + prose, STOP. Interactive →
  existing `[y/N]` prompt unchanged. (This is distinct from the Tier-1 usage-limit
  pause already in the skill — leave that intact.)

### Task 4: wire prd create + update gates
- **mode:** B
- **target:** plugin/skills/prd/SKILL.md
- **complexity:** medium
- **executor:** sonnet
- **parallel_group:** 1
- **est_tokens:** 450
- **est_cost_usd:** 0.03
- **verifier:** `grep -c "resolve_gate" plugin/skills/prd/SKILL.md | grep -qv '^0$'`
- **serves:** under-built-followup
- **spec:**
  At BOTH PRD approval gates (~line 72 create, ~line 95 update), add the "Headless
  gate" branch: `resolve_gate(repo, "prd-create"|"prd-update", kind="dangerous", originating_skill="prd", what=<one-line of the PRD change>)`. Headless → emit
  needs_input + prose, STOP (human owns the product source of truth). Interactive →
  existing approval picker unchanged.

### Task 5: guard test — dangerous-gate skills reference resolve_gate
- **mode:** A
- **target:** tests/test_dangerous_gate_wiring.py
- **complexity:** simple
- **executor:** sonnet
- **parallel_group:** 2
- **est_tokens:** 350
- **est_cost_usd:** 0.03
- **verifier:** `python3 -m pytest -q tests/test_dangerous_gate_wiring.py`
- **serves:** under-built-followup
- **spec:**
  New test that reads each of plugin/skills/{finish,plan,orchestrate,prd}/SKILL.md and
  asserts each contains `resolve_gate` (and `kind="dangerous"`), so a future edit that
  drops the headless wiring fails CI. Keep it a simple file-content assertion (no
  imports of the skills); match the repo's plugin-lint/test style. Parametrize over the
  4 skill paths.

---

## Cost preview

| Task | Executor | Tokens (+overhead) | Cost |
|---|---|---|---|
| 1 finish | sonnet | 450 + 10k | $0.031 |
| 2 plan | sonnet | 400 + 10k | $0.031 |
| 3 orchestrate | sonnet | 400 + 10k | $0.031 |
| 4 prd | sonnet | 450 + 10k | $0.031 |
| 5 guard test | sonnet | 350 + 10k | $0.031 |

**Total: ~$0.16** — 5 tasks, 2 waves (1: tasks 1-4 parallel, disjoint files · 2: task 5). Executors: sonnet×5.
