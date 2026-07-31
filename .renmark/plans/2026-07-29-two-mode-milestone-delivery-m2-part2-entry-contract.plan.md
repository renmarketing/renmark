---
artifact_type: plan
schema_version: 1
created_at: 2026-07-29T22:12:38-04:00
source_sha: 8d50e08
related_plan: .renmark/plans/2026-07-29-two-mode-milestone-delivery.plan.md
generator: renmark:plan
stale_after: null
dependency_refs:
  - PRD.md
  - .renmark/plans/2026-07-29-two-mode-milestone-delivery-m2-part1-runtime.plan.md
  - .renmark/reviews/2026-07-29-d3269b6.milestone-signoff.md
completion_state: complete
confidence: high
validation_status: validated
retry_count: 0
parser_success: true
schema_compliance: true
---

# M2 Part 2 — Entry Skills and Cross-Host Behavior

This plan compiles WP-M2-2 and WP-M2-6 after M2 Part 1 is green and committed. It removes Conductor from the public entry experience, makes Agency the product-governance path and Orchestrator the defined-execution path, and proves the same decisions remain reachable across Claude and Codex surfaces. REQ-25 managed project-contract propagation is intentionally deferred to M5. The packets stay outcome-oriented even though the current executor still requires one target per task.

**Milestone loop policy:** each failing focused verifier may receive at most two repair iterations. Completion of this plan does not accept M2: fresh milestone verification, independent review, bounded repair/re-review, owner demo, and signoff remain mandatory.

### Task 1: Route new builds through Agency or direct Orchestrator
- **mode:** A
- **target:** plugin/skills/start/SKILL.md
- **context_files:** []
- **complexity:** medium
- **executor:** haiku
- **role:** docs-editor
- **parallel_group:** 1
- **est_tokens:** 900
- **est_cost_usd:** 0.0011
- **verifier:** .venv/bin/python -c "from pathlib import Path; s=Path('plugin/skills/start/SKILL.md').read_text().lower(); assert all(x in s for x in ('delivery_mode','agency','orchestrator','explicit')) and 'conductor vs orchestrator' not in s" > /dev/null
- **verifier_timeout_s:** 60
- **serves:** REQ-22, REQ-23
- **spec:**
  Modify only `/home/renmark/projects/ai-system/plugin/skills/start/SKILL.md`.
  Replace the public Conductor choice and optional Agency overlay with the
  canonical once-per-run delivery decision. Recommend Agency for a vague product
  idea and Orchestrator for a defined build; an explicit owner choice wins and
  an existing canonical choice is reused without another gate. Persist through
  DeliveryState, use the shared interaction contract, keep status as prose, and
  preserve bootstrap, PRD approval, cost, headless, and Codex context safeguards.
  Agency owns discovery/governance and delegates approved execution to Orchestrator.

### Task 2: Make feature work Orchestrator-first
- **mode:** A
- **target:** plugin/skills/feature/SKILL.md
- **context_files:** []
- **complexity:** medium
- **executor:** haiku
- **role:** docs-editor
- **parallel_group:** 1
- **est_tokens:** 900
- **est_cost_usd:** 0.0011
- **verifier:** .venv/bin/python -c "from pathlib import Path; s=Path('plugin/skills/feature/SKILL.md').read_text().lower(); assert all(x in s for x in ('delivery_mode','agency','orchestrator','milestone')) and 'conductor vs orchestrator' not in s" > /dev/null
- **verifier_timeout_s:** 60
- **serves:** REQ-22, REQ-23
- **spec:**
  Modify only `/home/renmark/projects/ai-system/plugin/skills/feature/SKILL.md`.
  Route a directly requested defined feature to Orchestrator without a mode
  question. When the canonical run is Agency, describe feature execution as an
  approved milestone delegated to Orchestrator rather than a third delivery
  modality. Honor explicit choice and persisted run state, remove public
  Conductor language, and preserve the single dispatch gate, PRD drift check,
  isolated branch, cost preview, headless behavior, and existing pause policy.

### Task 3: Express debugging as guided Orchestrator execution
- **mode:** A
- **target:** plugin/skills/debug/SKILL.md
- **context_files:** []
- **complexity:** medium
- **executor:** haiku
- **role:** docs-editor
- **parallel_group:** 2
- **est_tokens:** 700
- **est_cost_usd:** 0.0011
- **verifier:** .venv/bin/python -c "from pathlib import Path; s=Path('plugin/skills/debug/SKILL.md').read_text().lower(); assert all(x in s for x in ('delivery_mode','orchestrator','execution_policy','guided')) and 'conductor mode' not in s" > /dev/null
- **verifier_timeout_s:** 60
- **serves:** REQ-22
- **spec:**
  Modify only `/home/renmark/projects/ai-system/plugin/skills/debug/SKILL.md`.
  Replace public/default Conductor language with
  `delivery_mode=orchestrator` and `execution_policy=guided`. Do not add a mode
  question for a defined failure. Preserve root-cause-first investigation,
  reproduction, bounded retries/recurrence handling, scope control, verification,
  pause policy, and host-aware context behavior. Conductor may appear only as a
  legacy value mapped internally to this guided policy.

### Task 4: Resume from canonical delivery state without re-asking
- **mode:** A
- **target:** plugin/skills/resume/SKILL.md
- **context_files:** []
- **complexity:** medium
- **executor:** haiku
- **role:** docs-editor
- **parallel_group:** 2
- **est_tokens:** 900
- **est_cost_usd:** 0.0011
- **verifier:** .venv/bin/python -c "from pathlib import Path; s=Path('plugin/skills/resume/SKILL.md').read_text().lower(); assert all(x in s for x in ('delivery state','orchestrator','guided','never re-ask'))" > /dev/null
- **verifier_timeout_s:** 60
- **serves:** REQ-22, REQ-23
- **spec:**
  Modify only `/home/renmark/projects/ai-system/plugin/skills/resume/SKILL.md`.
  Make canonical DeliveryState the first workflow source, retain ledger/git
  cross-checks, and never re-ask a resolved delivery mode. Map legacy Conductor
  to Orchestrator/guided and stop reading legacy Agency state as an independent
  public mode source. Re-resolve only the presentation of a genuinely pending
  decision using current host-surface capability; never persist selector/page
  state. Preserve Codex's no-clear/compact/manual-resume behavior and all
  anti-redispatch, orphan detection, approval, and bounded-summary rules.

### Task 5: Expand natural-language entry routing coverage
- **mode:** A
- **target:** tests/test_skill_trigger_phrases.py
- **context_files:** []
- **complexity:** medium
- **executor:** codex
- **role:** test-writer
- **parallel_group:** 3
- **est_tokens:** 2400
- **est_cost_usd:** 0.0720
- **verifier:** .venv/bin/pytest -q tests/test_skill_trigger_phrases.py
- **verifier_timeout_s:** 120
- **serves:** REQ-22, REQ-23
- **spec:**
  Modify only `/home/renmark/projects/ai-system/tests/test_skill_trigger_phrases.py`.
  Expand the exact-trigger matrix beyond plan/dispatch/loop to cover new build,
  defined feature/change, broken/fix/debug, adopt/init, resume, explicit Agency,
  and explicit Orchestrator language on both plugin surfaces. Assert each phrase
  resolves to the intended entry skill without exposing Conductor as a public
  choice or confusing informational status with a decision gate. Preserve every
  existing exact phrase.

### Task 6: Replace the obsolete public-mode behavior fixture
- **mode:** A
- **target:** tests/behavioral/mode.behavior.json
- **context_files:** []
- **complexity:** medium
- **executor:** codex
- **role:** test-writer
- **parallel_group:** 4
- **est_tokens:** 800
- **est_cost_usd:** 0.0240
- **verifier:** .venv/bin/python -c "import json; json.load(open('tests/behavioral/mode.behavior.json', encoding='utf-8'))" > /dev/null
- **verifier_timeout_s:** 60
- **serves:** REQ-22
- **spec:**
  Modify only `/home/renmark/projects/ai-system/tests/behavioral/mode.behavior.json`.
  Replace the Conductor-versus-Orchestrator golden contract with deterministic
  cases for unresolved vague start recommending Agency, defined feature/debug
  resolving to Orchestrator, guided debug policy, explicit choice precedence,
  legacy Conductor mapping, and a persisted choice that resume does not ask again.
  Keep the fixture schema valid and assertions grounded in live behavior adapters.

### Task 7: Refresh the Claude native-selector behavior fixture
- **mode:** A
- **target:** tests/behavioral/selector_claude.behavior.json
- **context_files:** []
- **complexity:** medium
- **executor:** codex
- **role:** test-writer
- **parallel_group:** 4
- **est_tokens:** 700
- **est_cost_usd:** 0.0210
- **verifier:** .venv/bin/python -c "import json; json.load(open('tests/behavioral/selector_claude.behavior.json', encoding='utf-8'))" > /dev/null
- **verifier_timeout_s:** 60
- **serves:** REQ-23
- **spec:**
  Modify only `/home/renmark/projects/ai-system/tests/behavioral/selector_claude.behavior.json`.
  Update the deterministic golden assertions for the semantic decision contract:
  native selection within Claude capacity, one recommendation first, complete
  fallback retained, overflow navigation reachable, and informational status
  excluded from decision gating. Keep current fixture schema and golden reference.

### Task 8: Refresh Codex Plan and Default selector behavior
- **mode:** A
- **target:** tests/behavioral/selector_codex.behavior.json
- **context_files:** []
- **complexity:** medium
- **executor:** codex
- **role:** test-writer
- **parallel_group:** 4
- **est_tokens:** 1200
- **est_cost_usd:** 0.0360
- **verifier:** .venv/bin/python -c "import json; json.load(open('tests/behavioral/selector_codex.behavior.json', encoding='utf-8'))" > /dev/null
- **verifier_timeout_s:** 60
- **serves:** REQ-23
- **spec:**
  Modify only `/home/renmark/projects/ai-system/tests/behavioral/selector_codex.behavior.json`.
  Replace fixed truncation expectations with surface-aware assertions: Codex
  Plan uses native 2–3 choice pages when available, Codex Default prints the
  complete numbered fallback, overflow uses More/Back/Cancel, one choice falls
  back, invalid/free text continues, and selector absence never means headless.
  Preserve one recommendation first and the existing fixture/golden schema.

### Task 9: Lock the updated routing and selector behavior suite
- **mode:** A
- **target:** tests/test_behavior.py
- **context_files:** []
- **complexity:** hard
- **executor:** codex
- **role:** test-writer
- **parallel_group:** 5
- **est_tokens:** 2400
- **est_cost_usd:** 0.0720
- **verifier:** .venv/bin/pytest -q tests/test_behavior.py && ./bin/renmark-execute --behavior
- **verifier_timeout_s:** 180
- **serves:** REQ-22, REQ-23
- **spec:**
  Modify only `/home/renmark/projects/ai-system/tests/test_behavior.py`.
  Add regression coverage that the updated mode, Claude selector, and Codex
  selector fixtures load and execute against current deterministic adapters,
  reject stale Conductor-public assertions, and preserve the two-tier behavior
  harness contract. The test must prove deterministic behavior execution makes
  no model call and that live-eval spend remains opt-in.

## Cost Preview

- Tasks: 9 across 5 ordered parallel groups
- Base task-output estimate: 10,900 tokens
- Agent overhead: 40,000 tokens (four Haiku docs-editor packets)
- Total estimated tokens: 50,900
- Total estimated cost: USD 0.2293
- Executors: Codex ×5, Haiku ×4
- Roles: test-writer ×5, docs-editor ×4
- Expensive models: none; no Opus or Fable
- Dependency: M2 Part 1 must be green and committed before this plan is dispatched
