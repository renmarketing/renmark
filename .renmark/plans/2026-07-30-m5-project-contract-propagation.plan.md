---
artifact_type: plan
schema_version: 1
created_at: 2026-07-30T22:30:00-04:00
source_sha: ce3a47d
related_plan: .renmark/plans/2026-07-29-two-mode-milestone-delivery.plan.md
generator: renmark:plan
completion_state: complete
confidence: high
validation_status: pending
retry_count: 0
parser_success: pending
schema_compliance: pending
dependency_refs:
  - PRD.md#REQ-25
  - .renmark/plans/2026-07-29-two-mode-milestone-delivery.plan.md#milestone-m5
---

# M5 — Project Contract Propagation

M5 implements REQ-25 through a single concise canonical managed contract and
the existing non-destructive init merge path. Start and Feature only detect
freshness and invoke that primitive; they never become independent writers.
Every package runs implementation plus its direct tests, then a bounded build
→ verify → review → scoped-fix loop (two repairs per package, three review
cycles per milestone). Any unmarked-content overwrite, malformed-marker write,
semantic parity drift, or budget expansion stops the milestone.

## Acceptance evidence

- New/existing `init`, stale `start`, and stale `feature` converge on one
  current two-mode selector-capable managed contract.
- A second refresh produces no diff; prose outside managed markers is
  byte-preserved; malformed marker targets are left untouched.
- Root guidance, templates, and host variants pass deterministic semantic
  parity checks without duplicating full skill bodies.

## WP M5-1 — Canonical contract source

### Task 1: Add concise canonical managed delivery contract
- **mode:** A
- **target:** plugin/skills/.shared/project-delivery-contract.md
- **complexity:** medium
- **executor:** haiku
- **role:** docs-editor
- **parallel_group:** 1
- **est_tokens:** 1200
- **est_cost_usd:** 0.0012
- **verifier:** rg -q 'Agency.*Orchestrator' plugin/skills/.shared/project-delivery-contract.md && rg -q 'numbered fallback' plugin/skills/.shared/project-delivery-contract.md
- **serves:** REQ-25
- **spec:** Create the one concise source fragment for the managed delivery contract. Cover two owner paths, milestone outcomes, bounded work packages, planner/executor/reviewer separation, deterministic verification, local loops, independent review/repair, canonical state, stop/human gates, and selector-capable native-picker/numbered-fallback behavior. Cite shared contracts by pointer; never inline skill bodies.

### Task 2: Add canonical contract validation fixtures
- **mode:** A
- **target:** tests/test_project_delivery_contract.py
- **complexity:** medium
- **executor:** codex
- **role:** test-writer
- **parallel_group:** 2
- **est_tokens:** 1800
- **est_cost_usd:** 0.0540
- **verifier:** .venv/bin/pytest -q tests/test_project_delivery_contract.py
- **serves:** REQ-25
- **spec:** Test required concise clauses, pointer-only references, and forbidden full-skill/transcript content. Keep assertions semantic rather than byte-copying host-specific wording.

## WP M5-2 — One refresh primitive and freshness routing

### Task 3: Make init merge the sole canonical contract writer
- **mode:** B
- **target:** renmark/init.py
- **complexity:** hard
- **executor:** sonnet
- **role:** code-implementer
- **parallel_group:** 3
- **est_tokens:** 3200
- **est_cost_usd:** 0.0396
- **verifier:** .venv/bin/pytest -q tests/test_init_pipeline.py
- **serves:** REQ-25
- **spec:** Extend the existing safe marker merge to render the canonical fragment into semantically mirrored managed blocks for CLAUDE.md and AGENTS.md. Preserve all outside content byte-for-byte; malformed markers must remain untouched; make repeat runs no-op and expose deterministic freshness/parity helpers. Do not create a second writer or write PRD.

### Task 4: Prove init preservation, idempotency, and corruption handling
- **mode:** B
- **target:** tests/test_init.py
- **complexity:** hard
- **executor:** codex
- **role:** test-writer
- **parallel_group:** 4
- **est_tokens:** 2600
- **est_cost_usd:** 0.0780
- **verifier:** .venv/bin/pytest -q tests/test_init_pipeline.py
- **serves:** REQ-25
- **spec:** Cover new/existing repo convergence, second-run no diff, byte-preserved unmarked prose, stable freshness markers even with unchanged body, malformed-marker no-write, and semantic mirror parity.

### Task 5: Route Start through deterministic contract freshness
- **mode:** B
- **target:** plugin/skills/start/SKILL.md
- **complexity:** medium
- **executor:** haiku
- **role:** docs-editor
- **parallel_group:** 5
- **est_tokens:** 900
- **est_cost_usd:** 0.0011
- **verifier:** rg -q 'freshness\|refresh' plugin/skills/start/SKILL.md && rg -q 'init' plugin/skills/start/SKILL.md
- **serves:** REQ-25
- **spec:** Add the deterministic pre-planning freshness check and route stale/missing contracts to init's sole merge primitive. Do not copy contract text, write files directly, or add a new user gate.

### Task 6: Route Feature through deterministic contract freshness
- **mode:** B
- **target:** plugin/skills/feature/SKILL.md
- **complexity:** medium
- **executor:** haiku
- **role:** docs-editor
- **parallel_group:** 6
- **est_tokens:** 900
- **est_cost_usd:** 0.0011
- **verifier:** rg -q 'freshness\|refresh' plugin/skills/feature/SKILL.md && rg -q 'init' plugin/skills/feature/SKILL.md
- **serves:** REQ-25
- **spec:** Mirror Start's freshness-routing rule with Feature-specific entry wording. It must invoke the same init primitive, not create a writer or duplicate the contract.

## WP M5-3 — Installed/root parity and entry-proof

### Task 7: Update root guidance and both templates from the canonical contract
- **mode:** B
- **target:** CLAUDE.md
- **complexity:** hard
- **executor:** sonnet
- **role:** docs-editor
- **parallel_group:** 7
- **est_tokens:** 2600
- **est_cost_usd:** 0.0378
- **verifier:** bash -o pipefail -c '.venv/bin/pytest -q tests/test_project_delivery_contract.py tests/test_init_pipeline.py | tail -3'
- **serves:** REQ-22, REQ-25
- **spec:** Replace legacy public Conductor/third-modality guidance with the canonical two-mode managed contract in root guidance, and update AGENTS/template mirrors through the established canonical rendering path in the same package. Preserve all unrelated rules and project-specific text; do not hand-maintain divergent copies.

### Task 8: Prove init/start/feature convergence and installed parity
- **mode:** A
- **target:** tests/test_contract_propagation.py
- **complexity:** hard
- **executor:** codex
- **role:** test-writer
- **parallel_group:** 8
- **est_tokens:** 2800
- **est_cost_usd:** 0.0840
- **verifier:** .venv/bin/pytest -q tests/test_contract_propagation.py
- **serves:** REQ-25
- **spec:** Build isolated fixtures proving init on new/existing projects plus start/feature stale paths install the same contract without overwriting custom instructions. Verify second-run no diff, root/template/installed semantic parity, native-picker wording versus guaranteed fallback, and malformed-marker fail-safe behavior.

## Deterministic gates

- `python -m renmark.plan_lint <plan>` and `python -m renmark.subagent_gate <plan>` before dispatch.
- Per package: focused pytest, Ruff, and mypy; fresh independent review with any preservation/parity finding blocking progression.
- Final M5 gate: full suite, Ruff, mypy, contract-propagation fixture, and before/after demo of custom project instructions surviving refresh.

## Cost preview

| Lane | Tasks | Estimated tokens | Estimated cost |
|---|---:|---:|---:|
| Contract/rendering and tests | 4 | 18,800 | $0.25 |
| Init/freshness/docs routing | 4 | 27,200 | $0.20 |
| Independent review and bounded repairs reserve | — | 17,000 | $0.25 |
| **M5 approved cap** | **8** | **63,000** | **$0.70** |

No frontier model is planned. Deferring parity/preservation proof is cheaper,
but would fail REQ-25 and is not recommended.
