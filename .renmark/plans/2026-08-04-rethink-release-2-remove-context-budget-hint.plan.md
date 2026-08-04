# Release 2: Remove context_budget_hint dead code

Source: `.renmark/rethink/renmark-architecture/roadmap.md` Release 2 (serves
REQ-5), Program `.renmark/state/program.json` stage
`release-2-remove-context-budget-hint`, task `r2-remove-dead-code`.
`renmark.state.skills.context_budget_hint` has zero production callers
(confirmed by repo-wide grep, matching classification.md item 7's
"dead scaffolding masquerading as enforcement" finding, re-verified
2026-08-03/04). The 100k/120k/150k tiers it encodes are already enforced as
prose-only rules in `CLAUDE.md`/`AGENTS.md` (the orchestrator self-monitors
them) — removing the unused function does not remove the behavior, only the
unreferenced code duplicating it. `record_skill_invocation` and
`context_budget_check` in the same module stay untouched — they ARE called
(G4 cross-domain hint) and are out of scope.

**Owner-mandated protections (do not touch, do not weaken, do not rename):**
- `renmark/agency.py` role/milestone machinery and ADR-001's
  Owner/General-Contractor/Architect/Worker/Inspector role model.
- `plugin/skills/.shared/interaction-contract.md` / `build_selector`
  (`AskUserQuestion`, 1–4 options, recommended option first).
- `plugin/skills/.shared/task-tracking.md` / `renmark/task_tracking.py`.

If any task below would need to touch one of those three, it must NOT be
executed — stop and report back to the Owner instead.

### Task 1: remove context_budget_hint from renmark/state/skills.py
- **mode:** B
- **target:** renmark/state/skills.py
- **complexity:** simple
- **executor:** haiku
- **role:** code-implementer
- **parallel_group:** 1
- **est_tokens:** 300
- **est_cost_usd:** 0.00
- **verifier:** python3 -m py_compile renmark/state/skills.py && ! grep -q "def context_budget_hint" renmark/state/skills.py
- **serves:** REQ-5
- **spec:**
  Delete the `context_budget_hint` function (lines ~23-49) and its three
  module-level constants `CTX_SUMMARIZE`, `CTX_COMPACT`, `CTX_CHECKPOINT`
  (lines ~14-20, including the comment above them) from
  `renmark/state/skills.py`. Do NOT touch `_last_skill_path`,
  `record_skill_invocation`, `last_skill_invocation`, or
  `context_budget_check` — those are used elsewhere and stay exactly as-is.
  Keep the module docstring and imports unchanged unless an import becomes
  unused after the deletion (check before removing any import).

### Task 2: remove the associated test
- **mode:** B
- **target:** tests/test_state_skills.py
- **complexity:** simple
- **executor:** haiku
- **role:** test-writer
- **parallel_group:** 1
- **est_tokens:** 200
- **est_cost_usd:** 0.00
- **verifier:** python3 -m py_compile tests/test_state_skills.py
- **serves:** REQ-5
- **spec:**
  Remove `test_context_budget_hint_tiers_and_invalid_inputs` (the test
  covering the now-deleted `context_budget_hint`) and its now-unused
  `from renmark.state.skills import context_budget_hint` import from
  `tests/test_state_skills.py`. Leave every other test in the file
  untouched. If the import line also imports other still-used names,
  keep those and only drop `context_budget_hint` from the import list.

### Task 3: update CLAUDE.md's context-thresholds-rule block
- **mode:** B
- **target:** CLAUDE.md
- **complexity:** simple
- **executor:** haiku
- **role:** docs-editor
- **parallel_group:** 1
- **est_tokens:** 250
- **est_cost_usd:** 0.00
- **verifier:** ! grep -q "context_budget_hint" CLAUDE.md
- **serves:** REQ-5
- **spec:**
  In the `<!-- BEGIN:context-thresholds-rule -->` ... `<!-- END -->` block,
  change the line `Complement the %-based budget above with absolute hard
  stops (see `renmark.state.skills.context_budget_hint`):` to describe these
  as self-monitored prose thresholds instead of pointing at the now-deleted
  function, e.g. `Complement the %-based budget above with absolute hard
  stops (self-monitored — no dedicated helper function; the orchestrator
  tracks its own token count):`. Do not change the three threshold bullets
  (100k/120k/150k) or any other content in the block. Do not touch any other
  rule block in the file.

### Task 4: update AGENTS.md's mirrored paragraph
- **mode:** B
- **target:** AGENTS.md
- **complexity:** simple
- **executor:** haiku
- **role:** docs-editor
- **parallel_group:** 1
- **est_tokens:** 250
- **est_cost_usd:** 0.00
- **verifier:** ! grep -q "context_budget_hint" AGENTS.md
- **serves:** REQ-5
- **spec:**
  Mirror Task 3's change in AGENTS.md's "Context thresholds (absolute token
  counts)" paragraph: replace the `(`renmark.state.skills.context_budget_hint`)`
  parenthetical with the same "self-monitored — no dedicated helper function"
  phrasing used in CLAUDE.md's updated block, keeping the rest of the
  paragraph (100k/120k/150k behavior, Codex handling, the `CLAUDE.md` §
  pointer) unchanged. Per this project's "mirror all rule changes in
  AGENTS.md in the same commit" convention.

### Task 5: update the agency-delivery.md fragment
- **mode:** B
- **target:** plugin/skills/.shared/agency-delivery.md
- **complexity:** simple
- **executor:** haiku
- **role:** docs-editor
- **parallel_group:** 1
- **est_tokens:** 250
- **est_cost_usd:** 0.00
- **verifier:** ! grep -q "context_budget_hint" plugin/skills/.shared/agency-delivery.md
- **serves:** REQ-5
- **spec:**
  Two edits in `plugin/skills/.shared/agency-delivery.md`:
  1. The bullet `**Context budget:** `renmark.state.skills.context_budget_hint`
     (100k summarize / 120k compact / 150k checkpoint).` — reword to
     `**Context budget:** self-monitored absolute thresholds, 100k summarize /
     120k compact / 150k checkpoint (see `CLAUDE.md` § `context-thresholds-rule`).`
  2. The closing blockquote's `Delegate cost infra to finish_lanes / cost.py /
     context_budget_hint / subagent-profiles — do not inline those rules.`
     — drop `context_budget_hint` from that list (it's no longer a delegable
     helper), leaving `finish_lanes / cost.py / subagent-profiles`.
  Do not change anything else in the file.

---

## Cost preview

| Task | Executor | Est. tokens (incl. overhead) | Est. cost |
|---|---|---|---|
| 1. renmark/state/skills.py | haiku | ~10,300 | ~$0.001 |
| 2. tests/test_state_skills.py | haiku | ~10,200 | ~$0.001 |
| 3. CLAUDE.md | haiku | ~10,250 | ~$0.001 |
| 4. AGENTS.md | haiku | ~10,250 | ~$0.001 |
| 5. agency-delivery.md | haiku | ~10,250 | ~$0.001 |

**Total: ~$0.005, 5 tasks, 1 parallel group (disjoint files, no dependency
between them), no Opus/Fable escalation.**

Subagent gate: five well-scoped haiku mechanical-deletion tasks with defined
grep/compile verifiers — deterministic-eligible-and-simple, cheapest tier per
`plugin/skills/.shared/model-routing.md`.
