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
  - .renmark/reviews/2026-07-29-d3269b6.milestone-signoff.md
completion_state: complete
confidence: high
validation_status: validated
retry_count: 0
parser_success: true
schema_compliance: true
---

# M2 Part 1 — Decision Contract and Two-Mode Runtime

This plan compiles `M2-entry-routing-two-mode` work packages WP-M2-1, WP-M2-3, WP-M2-4, and WP-M2-5 into the current single-target executor format. The goal is one canonical Agency/Orchestrator delivery-mode API and one semantic decision contract whose presentation adapts at render time to Claude, Codex Plan, or Codex Default. Legacy readers remain compatible; selector availability and page position never become canonical state. The task packets constrain outcomes and invariants, while leaving local implementation design to the executor. M2 Part 2 must not run until this plan is committed and green.

**Milestone loop policy:** each failing focused verifier may receive at most two repair iterations. After both M2 parts pass, the milestone requires a fresh full verification, one independent review, at most three fix/re-review cycles, and owner demo/signoff. None of those execution steps is authorized by this planning artifact.

### Task 1: Define the semantic decision interaction contract
- **mode:** A
- **target:** plugin/skills/.shared/interaction-contract.md
- **context_files:** []
- **complexity:** medium
- **executor:** haiku
- **role:** docs-editor
- **parallel_group:** 1
- **est_tokens:** 1000
- **est_cost_usd:** 0.0011
- **verifier:** .venv/bin/python -c "from pathlib import Path; s=Path('plugin/skills/.shared/interaction-contract.md').read_text().lower(); assert all(x in s for x in ('decision','recommended','more','back','cancel','codex plan','codex default'))" > /dev/null
- **verifier_timeout_s:** 60
- **serves:** REQ-23
- **spec:**
  Modify only `/home/renmark/projects/ai-system/plugin/skills/.shared/interaction-contract.md`.
  Create the single host-neutral contract for real decisions and approval gates.
  Require semantic choice IDs/codes, exactly one recommended choice at index 0,
  exact-label/number/code/free-text handling, and an explicit refusal path for
  dangerous decisions. Define render-time capability resolution: Claude native
  choices up to four, Codex Plan native choices only within the active 2–3 cap,
  and Codex Default complete numbered fallback. Specify bounded More/Back/Cancel
  navigation without truncation, one-choice fallback, continuation re-rendering,
  and informational status as prose. Pagination and picker availability are
  ephemeral presentation state and never switch or persist a host collaboration mode.

### Task 2: Add the canonical public delivery-mode resolver
- **mode:** B
- **target:** renmark/mode.py
- **context_files:** []
- **complexity:** hard
- **executor:** codex
- **role:** code-implementer
- **parallel_group:** 2
- **est_tokens:** 2600
- **est_cost_usd:** 0.0780
- **verifier:** .venv/bin/python -m py_compile renmark/mode.py && .venv/bin/ruff check renmark/mode.py
- **verifier_timeout_s:** 90
- **serves:** REQ-22, REQ-23
- **spec:**
  Modify only `/home/renmark/projects/ai-system/renmark/mode.py`.
  Introduce a public delivery-mode resolver using the canonical
  `agency|orchestrator` and `guided|direct|async` vocabularies from M1.
  Accept an explicit owner choice plus a bounded intent/entry classification;
  explicit choice wins, vague new-product work recommends Agency, defined
  feature/fix work recommends Orchestrator, and debug resolves to
  Orchestrator/guided. Persist a new choice through canonical DeliveryState,
  once per run. Preserve legacy `mode.json` path/read/clear compatibility, map
  legacy Conductor to Orchestrator/guided, and prevent new public Conductor writes.
  Keep existing callers functional through compatible wrappers or deprecation paths.

### Task 3: Prove public mode resolution and legacy compatibility
- **mode:** A
- **target:** tests/test_mode.py
- **context_files:** []
- **complexity:** hard
- **executor:** codex
- **role:** test-writer
- **parallel_group:** 3
- **est_tokens:** 2200
- **est_cost_usd:** 0.0660
- **verifier:** .venv/bin/pytest -q tests/test_mode.py
- **verifier_timeout_s:** 120
- **serves:** REQ-22, REQ-23
- **spec:**
  Modify only `/home/renmark/projects/ai-system/tests/test_mode.py`.
  Replace obsolete public Conductor expectations with a routing matrix covering
  vague start→Agency, defined start/feature/fix→Orchestrator, debug→guided,
  explicit choice precedence, once-per-run persistence, and resume preserving
  the canonical choice. Retain corruption, atomicity, and legacy-read coverage.
  Prove legacy Conductor projects resolve effectively to Orchestrator/guided,
  while new writes use canonical DeliveryState and never create a new public
  Conductor value.

### Task 4: Make host selector capabilities surface-aware
- **mode:** A
- **target:** renmark/hosts.py
- **context_files:** []
- **complexity:** medium
- **executor:** codex
- **role:** code-implementer
- **parallel_group:** 2
- **est_tokens:** 1900
- **est_cost_usd:** 0.0570
- **verifier:** .venv/bin/python -m py_compile renmark/hosts.py && .venv/bin/ruff check renmark/hosts.py
- **verifier_timeout_s:** 90
- **serves:** REQ-23
- **spec:**
  Modify only `/home/renmark/projects/ai-system/renmark/hosts.py`.
  Extend host capabilities with render-time surface and selector availability/
  minimum/maximum capacity without breaking `capabilities_for(host)` callers.
  Model Claude native selection up to four choices, Codex Plan native selection
  only for valid 2–3 choice pages, Codex Default as numbered fallback, and unknown
  hosts conservatively. Allow an explicit runtime capability override so the
  caller, not environment persistence, decides picker availability. Preserve the
  no-clear/no-compact/no-resume Codex contract and never equate selector absence
  with headless mode.

### Task 5: Prove host and surface capability resolution
- **mode:** A
- **target:** tests/test_hosts.py
- **context_files:** []
- **complexity:** medium
- **executor:** codex
- **role:** test-writer
- **parallel_group:** 3
- **est_tokens:** 1500
- **est_cost_usd:** 0.0450
- **verifier:** .venv/bin/pytest -q tests/test_hosts.py
- **verifier_timeout_s:** 120
- **serves:** REQ-23
- **spec:**
  Modify only `/home/renmark/projects/ai-system/tests/test_hosts.py`.
  Add a capability matrix for Claude, Codex Plan, Codex Default, explicit
  availability overrides, and unknown hosts. Assert native minimum/maximum
  capacities, complete fallback availability, and compatibility of the
  host-only call. Preserve assertions that Codex never advertises unsupported
  clear, compact, or resume commands and that selector absence is not headless.

### Task 6: Implement semantic choice sets and bounded continuation
- **mode:** B
- **target:** renmark/interaction.py
- **context_files:** []
- **complexity:** hard
- **executor:** codex
- **role:** code-implementer
- **parallel_group:** 4
- **est_tokens:** 4200
- **est_cost_usd:** 0.1260
- **verifier:** .venv/bin/python -m py_compile renmark/interaction.py && .venv/bin/ruff check renmark/interaction.py
- **verifier_timeout_s:** 90
- **serves:** REQ-23
- **spec:**
  Modify only `/home/renmark/projects/ai-system/renmark/interaction.py`.
  Keep `Choice`, `build_selector`, recommended-first normalization, complete
  numbered fallback, and current reply parsing compatible. Add a semantic
  decision/choice-set representation and an ephemeral continuation result that
  can select, page More, go Back, Cancel/Reject, accept exact label/number/code,
  retain free text, or report invalid input. Render native pages only when the
  supplied host-surface capability supports their size. Overflow must keep the
  recommendation reachable first, expose More instead of truncating, and show
  remaining choices plus Back and a safe refusal action. One semantic choice
  uses fallback, every fallback stays complete, and no page state is persisted.

### Task 7: Test selector compatibility and continuation behavior
- **mode:** A
- **target:** tests/test_interaction.py
- **context_files:** []
- **complexity:** hard
- **executor:** codex
- **role:** test-writer
- **parallel_group:** 5
- **est_tokens:** 3400
- **est_cost_usd:** 0.1020
- **verifier:** .venv/bin/pytest -q tests/test_interaction.py
- **verifier_timeout_s:** 120
- **serves:** REQ-23
- **spec:**
  Modify only `/home/renmark/projects/ai-system/tests/test_interaction.py`.
  Preserve existing Choice caller coverage, then add one-choice fallback,
  exact-label and free-text replies, invalid continuation, More/Back/Cancel
  traversal, dangerous-decision refusal reachability, and complete numbered
  fallback assertions. Cover Claude native, Codex Plan native within capacity,
  Codex Default fallback, unavailable-selector fallback, and ensure no case
  marks selector absence as headless or persists page state.

### Task 8: Add cross-surface semantic parity fixtures
- **mode:** A
- **target:** tests/test_selector_contract.py
- **context_files:** []
- **complexity:** hard
- **executor:** codex
- **role:** test-writer
- **parallel_group:** 5
- **est_tokens:** 2800
- **est_cost_usd:** 0.0840
- **verifier:** .venv/bin/pytest -q tests/test_selector_contract.py
- **verifier_timeout_s:** 120
- **serves:** REQ-23
- **spec:**
  Modify only `/home/renmark/projects/ai-system/tests/test_selector_contract.py`.
  Create table-driven golden fixtures that render the same semantic decisions
  through Claude native, Codex Plan native, and Codex Default fallback paths.
  Assert identical reachable semantic choices, one recommendation first,
  complete overflow across More/Back/Cancel pages, one-choice fallback,
  invalid/free-text continuation, and an explicit refusal path for dangerous
  gates. Prove render-time presentation fields never enter DeliveryState and
  no helper attempts to switch Codex collaboration mode.

### Task 9: Route lifecycle preambles through canonical delivery state
- **mode:** B
- **target:** renmark/lifecycle.py
- **context_files:** []
- **complexity:** hard
- **executor:** codex
- **role:** code-implementer
- **parallel_group:** 6
- **est_tokens:** 3000
- **est_cost_usd:** 0.0900
- **verifier:** .venv/bin/python -m py_compile renmark/lifecycle.py && .venv/bin/ruff check renmark/lifecycle.py
- **verifier_timeout_s:** 90
- **serves:** REQ-22, REQ-23
- **spec:**
  Modify only `/home/renmark/projects/ai-system/renmark/lifecycle.py`.
  Replace the public Conductor/Agency-overlay preamble decision with canonical
  DeliveryState routing. `init` and `start` may surface the once-per-run choice
  only when product intent remains unresolved; defined `feature` and `debug`
  route directly to Orchestrator, with debug guided. Existing canonical choice
  always wins and resume never asks again. Preserve M1 legacy projection,
  approval, context-budget, headless, Codex no-clear/compact/resume, byte-budget,
  and invocation-recording behavior. Do not persist selector capability or page state.

### Task 10: Prove lifecycle entry routing and resume stability
- **mode:** A
- **target:** tests/test_lifecycle.py
- **context_files:** []
- **complexity:** hard
- **executor:** codex
- **role:** test-writer
- **parallel_group:** 7
- **est_tokens:** 2400
- **est_cost_usd:** 0.0720
- **verifier:** .venv/bin/pytest -q tests/test_lifecycle.py
- **verifier_timeout_s:** 150
- **serves:** REQ-22, REQ-23
- **spec:**
  Modify only `/home/renmark/projects/ai-system/tests/test_lifecycle.py`.
  Replace obsolete Conductor-versus-Orchestrator prompt tests with canonical
  Agency/Orchestrator routing cases for unresolved start/init, defined feature,
  debug guided, explicit persisted choice, legacy Conductor mapping, and resume
  without a second question. Preserve all approval, stage, artifact, byte-budget,
  headless, context-domain, and Codex unsupported-command regressions.

### Task 11: Unify mode CLI commands on canonical delivery state
- **mode:** B
- **target:** renmark/cli/_engine.py
- **context_files:** []
- **complexity:** hard
- **executor:** codex
- **role:** code-implementer
- **parallel_group:** 8
- **est_tokens:** 2600
- **est_cost_usd:** 0.0780
- **verifier:** .venv/bin/python -m py_compile renmark/cli/_engine.py && .venv/bin/ruff check renmark/cli/_engine.py
- **verifier_timeout_s:** 90
- **serves:** REQ-22
- **spec:**
  Modify only `/home/renmark/projects/ai-system/renmark/cli/_engine.py`.
  Make `--set-mode agency|orchestrator` write the canonical delivery run,
  make `--get-mode` read canonical state first and legacy state only as fallback,
  and render effective execution policy. A legacy Conductor value remains
  readable but reports deprecation and effective Orchestrator/guided behavior;
  new Conductor selection is rejected. Reconcile existing Agency activate/
  deactivate and clear aliases so they cannot contradict canonical state while
  preserving their compatibility surface. Keep output bounded, deterministic,
  and non-mutating for get/status paths.

### Task 12: Test canonical mode CLI and deprecation behavior
- **mode:** A
- **target:** tests/test_mode_cli.py
- **context_files:** []
- **complexity:** hard
- **executor:** codex
- **role:** test-writer
- **parallel_group:** 9
- **est_tokens:** 2200
- **est_cost_usd:** 0.0660
- **verifier:** .venv/bin/pytest -q tests/test_mode_cli.py
- **verifier_timeout_s:** 120
- **serves:** REQ-22
- **spec:**
  Modify only `/home/renmark/projects/ai-system/tests/test_mode_cli.py`.
  Cover canonical Agency and Orchestrator set/get round trips, execution-policy
  output, canonical-first precedence, legacy Conductor read with deprecation
  guidance and guided mapping, rejection of new Conductor writes, alias
  convergence, clear idempotency, corruption, atomic failures, and no false
  success output. Keep existing command entry and exit-code contracts.

### Task 13: Point handoff menus at the canonical interaction contract
- **mode:** A
- **target:** plugin/skills/.shared/handoff-menu.md
- **context_files:** []
- **complexity:** medium
- **executor:** haiku
- **role:** docs-editor
- **parallel_group:** 10
- **est_tokens:** 1000
- **est_cost_usd:** 0.0011
- **verifier:** .venv/bin/python -c "from pathlib import Path; s=Path('plugin/skills/.shared/handoff-menu.md').read_text().lower(); assert all(x in s for x in ('interaction-contract.md','more','back','exact label','informational status'))" > /dev/null
- **verifier_timeout_s:** 60
- **serves:** REQ-23
- **spec:**
  Modify only `/home/renmark/projects/ai-system/plugin/skills/.shared/handoff-menu.md`.
  Replace duplicated/fixed selector rules with a pointer to the new interaction
  contract while preserving Pause Policy and dangerous-gate semantics. Require
  render-time host-surface capability, one-choice fallback, number/code/exact
  label/free-text handling, bounded More/Back/Cancel-or-Reject navigation, and
  re-rendering after continuation. Preserve recommended-first order, complete
  fallback, selector-absence-is-not-headless, and informational status as prose.

## Cost Preview

- Tasks: 13 across 10 ordered parallel groups
- Base task-output estimate: 30,800 tokens
- Agent overhead: 20,000 tokens (two Haiku docs-editor packets)
- Total estimated tokens: 50,800
- Total estimated cost: USD 0.8662
- Executors: Codex ×11, Haiku ×2
- Roles: code-implementer ×5, test-writer ×6, docs-editor ×2
- Expensive models: none; no Opus or Fable
- Cheaper alternative: none that preserves the current one-target executor and contract quality; M3 replaces this temporary granularity backend
