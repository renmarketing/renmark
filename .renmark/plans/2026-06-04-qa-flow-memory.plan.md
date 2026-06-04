# Plan — QA flow memory + QA bootstrap

**Context.** Add a lightweight, markdown-based QA flow memory layer so
`/renmark:verify --qa` / `--deep-qa` reuse known-good browser flows instead of
inventing tests each run. Centered on a new `.renmark/memory/qa-flows.md`
playbook. Already-scoped project (renmark plugin: Python + Claude Code plugin
markdown) — no scope-contract discovery. The wiring slots into verify's EXISTING
QA sections (applicability gate → flow selection; convergence loop →
promote-on-pass; arg parsing → `--bootstrap`; "When to use which mode" →
recommendation triggers); it does not restructure them.

**Hard constraints (from recent CHANGELOG "Do not change" guards — must hold):**
- **Shell smoke stays the default; browser QA stays opt-in** via `--qa`/`--deep-qa`.
  Browser QA is recommended for UI-facing changes but NEVER automatic.
- **No third browser flag** — bootstrap is `--qa --bootstrap`, reusing the existing
  arg parser. **Preserve the dual browser-channel selection** (Chrome DevTools MCP
  default / native `claude --chrome`) and degrade-to-shell behavior.
- **Context-hygiene (G3/G5) is non-negotiable** — screenshots/DOM/console/network
  stay on disk + artifact body; chat sees only the ≤5-line verdict.
- **Interactive `AskUserQuestion` hand-off menus are PRIMARY** (numbered = fallback);
  never auto-proceed. Don't regress this in any verify edit.
- Markdown-only — NO database, knowledge graph, or Playwright. Do not overwrite
  unrelated memory files. Existing QA must still work when `qa-flows.md` is
  missing/empty.

Tasks 1–4 touch disjoint files (parallel group 1). Task 5 (tests) runs after, in
group 2, so its assertions see the committed content.

---

### Task 1: QA flow memory store
- **mode:** A
- **target:** .renmark/memory/qa-flows.md
- **complexity:** medium
- **executor:** sonnet
- **parallel_group:** 1
- **est_tokens:** 700
- **est_cost_usd:** 0.03
- **verifier:** test -f .renmark/memory/qa-flows.md && grep -q "## Flow:" .renmark/memory/qa-flows.md && grep -qi "Preconditions" .renmark/memory/qa-flows.md && grep -qi "Known risks" .renmark/memory/qa-flows.md && grep -qi "Last passing" .renmark/memory/qa-flows.md
- **spec:**
  Create `.renmark/memory/qa-flows.md` as the canonical, committed QA baseline /
  playbook store for reusable browser QA flows. This is a seeded TEMPLATE, not
  real flows. Structure:
  - A top header explaining the file's purpose (the project's QA playbook;
    `/renmark:verify --qa` / `--deep-qa` read it before choosing a flow and
    update/append/promote flows on pass; newest-first; committed memory).
  - A one-line note: maintained by `/renmark:verify --qa` (and `--qa --bootstrap`).
  - One **commented EXAMPLE flow** demonstrating the field shape (clearly marked
    as an example/template, not a real flow). Use exactly this shape:
    ```
    ## Flow: <name>
    - URL: `/route/pattern`
    - Preconditions:
      - ...
    - Actions:
      1. ...
    - Expected:
      - Preview/page loads
      - No overlapping or clipped controls; nothing off-screen
      - No console errors
      - <feature-specific success state>
    - Key selectors / UI landmarks: (optional)
    - Evidence:
      - Last passing review artifact: `.renmark/reviews/...`
      - Baseline screenshots: `.renmark/reviews/qa/...`
    - Known risks:
      - ...
    - Related bugs / regressions:
      - ...
    ```
  Each flow supports: Flow name, Target URL/route, Preconditions, User actions
  (numbered), Expected behavior (incl. no overlapping/clipped controls + no
  console errors), Key selectors/UI landmarks (optional), Known risks, Last
  passing artifact, Baseline screenshot paths, Related bugs/regressions. Keep it
  lightweight markdown — no schema/DB. Follow the repo memory convention
  (newest-first, committed). The verifier greps for `## Flow:`, `Preconditions`,
  `Known risks`, and `Last passing` — include those literal labels.

### Task 2: wire QA memory + bootstrap + triggers into verify
- **mode:** B
- **target:** plugin/skills/verify/SKILL.md
- **complexity:** hard
- **executor:** opus
- **parallel_group:** 1
- **est_tokens:** 2800
- **est_cost_usd:** 0.19
- **verifier:** python -m renmark.lint && grep -q "qa-flows.md" plugin/skills/verify/SKILL.md && grep -q -- "--qa --bootstrap" plugin/skills/verify/SKILL.md && grep -qi "promote" plugin/skills/verify/SKILL.md && grep -qi "missing or empty" plugin/skills/verify/SKILL.md
- **spec:**
  Edit `plugin/skills/verify/SKILL.md` IN PLACE — surgical insertions into the
  EXISTING QA / Deep QA sections; preserve the three-mode model, the dual
  browser-channel selection, the context-hygiene contract, the interactive
  hand-off rules, and the frontmatter (`name: verify`, non-empty `description:`).
  Do NOT make browser QA automatic. Add:
  1. **Mode/arg parsing:** recognize `--bootstrap` as a modifier of `--qa`
     (`/renmark:verify --qa --bootstrap`). No new flag/command beyond this.
  2. **BEFORE QA — flow selection from memory** (new subsection in QA mode, after
     the applicability gate / server lifecycle, before "The single happy-path
     flow"): read `.renmark/memory/stack.md`, `project-map.md`, `qa-flows.md`
     **if it exists**, and `bugs.md`; pick the best matching known flow for the
     current feature; if none matches, synthesize a one-off flow from the
     plan/spec. **If `qa-flows.md` is missing or empty, behave exactly as today**
     (synthesize from the plan goal) — existing QA must not break. Use the
     literal phrase "missing or empty".
  3. **DURING QA:** run the SELECTED flow via the existing browser-channel
     behavior already documented (before/after screenshots, console/network,
     visual/layout integrity incl. overlapping/clipped controls, stop+fail on
     hang/crash/broken layout). Reference the existing steps; do not duplicate or
     weaken them.
  4. **AFTER QA** (extend the existing QA convergence loop): on FAIL still
     `log_bug` to `bugs.md` linking the review artifact (unchanged). On PASS,
     update or append the matching flow in `qa-flows.md`, and **promote** a
     reusable one-off flow into `qa-flows.md`, linking it to the passing review
     artifact + baseline screenshot paths. Use the literal word "promote". Keep
     evidence on disk; chat stays a bounded verdict.
  5. **Bootstrap path** (`--qa --bootstrap`, new subsection): read `stack.md`,
     `project-map.md`, plans, `bugs.md`, `CHANGELOG.md`; detect main browser
     surfaces/routes; ask or infer the top 3–5 critical user flows; create
     `.renmark/memory/qa-flows.md`; save baseline notes + screenshot/artifact
     paths when browser QA actually runs; if browser QA cannot run, still create
     documented candidate flows marked **UNVERIFIED**.
  6. **Recommendation triggers** (in the existing "When to use which mode"
     section): recommend `--qa` when changed files / feature scope touch
     templates, frontend JS/CSS, routes/controllers serving browser pages,
     forms/buttons, settings screens, preview/render UI, checkout/pricing, or
     anything user-visible; recommend `--deep-qa` only for risky UI/runtime
     changes (layout refactors, state persistence, auth/session, render
     pipelines, multi-step workflows, visual/runtime bug fixes, previously-failed
     flows, risky inputs) or after a normal `--qa` passes. State plainly: browser
     QA is recommended, NOT automatic; every implementation still gets shell smoke.
  7. **Deep QA** reuses the same QA memory (flow selection + promote-on-pass) —
     add a one-line pointer in the Deep QA section's "Reuse the QA setup".
  Verifier greps for: `qa-flows.md`, `--qa --bootstrap`, `promote`, `missing or empty`.

### Task 3: register qa-flows.md in the memory index
- **mode:** B
- **target:** .renmark/memory/INDEX.md
- **complexity:** simple
- **executor:** haiku
- **parallel_group:** 1
- **est_tokens:** 120
- **est_cost_usd:** 0.00
- **verifier:** grep -q "qa-flows.md" .renmark/memory/INDEX.md
- **spec:**
  Add ONE row to the existing memory file table in `.renmark/memory/INDEX.md`
  (the `| File | What it documents | Auto-updated by |` table), without altering
  any other row or section. New row:
  `| \`qa-flows.md\` | Reusable browser QA flows / baselines (the QA playbook) | \`/renmark:verify --qa\`, \`/renmark:verify --qa --bootstrap\` |`
  Place it logically near `bugs.md` / `learnings.md`. Do not touch the Counts or
  Conventions sections except, optionally, a one-line mention if a count list
  enumerates files. Keep it minimal.

### Task 4: orchestrate post-run QA recommendation (not automatic)
- **mode:** B
- **target:** plugin/skills/orchestrate/SKILL.md
- **complexity:** medium
- **executor:** sonnet
- **parallel_group:** 1
- **est_tokens:** 400
- **est_cost_usd:** 0.03
- **verifier:** python -m renmark.lint && grep -q "Recommend \`/renmark:verify --qa\`" plugin/skills/orchestrate/SKILL.md && grep -qi "not automatic" plugin/skills/orchestrate/SKILL.md
- **spec:**
  Edit `plugin/skills/orchestrate/SKILL.md` IN PLACE — in the auto-verify / post-run
  hand-off area (Step 8, where the next steps are surfaced), add a SHORT
  recommendation note (2–4 lines): after a clean run whose changed files / feature
  scope touch user-visible/browser surfaces (templates, frontend JS/CSS,
  routes/controllers serving pages, forms/buttons, settings, preview/render UI,
  checkout/pricing, browser-facing pages), **recommend** the user run
  `/renmark:verify --qa` (and `--deep-qa` for risky UI/runtime changes or after a
  normal `--qa` passes). State explicitly that this is a recommendation and browser
  QA is **not automatic** — the default auto-verify remains shell smoke. Do not
  change the auto-verify-on-clean-run logic or make browser QA run automatically.
  Preserve the existing interactive hand-off menu behavior. Verifier greps for the
  literal `Recommend \`/renmark:verify --qa\`` and `not automatic`.

### Task 5: tests for QA flow memory
- **mode:** A
- **target:** tests/test_qa_flows.py
- **complexity:** medium
- **executor:** codex
- **parallel_group:** 2
- **est_tokens:** 700
- **est_cost_usd:** 0.02
- **verifier:** python -m pytest tests/test_qa_flows.py -q
- **spec:**
  Create `tests/test_qa_flows.py` with focused, fast content-presence tests
  (pure stdlib + pathlib, no new deps; match the style of existing tests in
  `tests/`). Assert against the repo's real files (resolve repo root from the test
  file location). Tests:
  1. `test_qa_flows_store_exists_and_has_template` — `.renmark/memory/qa-flows.md`
     exists and contains `## Flow:` plus the field labels `Preconditions`,
     `Actions`, `Expected`, `Known risks`, `Last passing`.
  2. `test_verify_reads_qa_flows_before_choosing` — `plugin/skills/verify/SKILL.md`
     references `qa-flows.md` and instructs reading it before choosing a flow
     (assert `qa-flows.md` appears and a "before" / flow-selection anchor exists).
  3. `test_verify_handles_missing_qa_flows` — verify SKILL.md contains the
     "missing or empty" guarantee (existing QA still works without the file).
  4. `test_verify_bootstrap_flag_documented` — verify SKILL.md documents
     `--qa --bootstrap`.
  5. `test_verify_promotes_passing_flow` — verify SKILL.md contains the `promote`
     (on-pass) instruction.
  6. `test_index_registers_qa_flows` — `.renmark/memory/INDEX.md` lists
     `qa-flows.md`.
  Keep each test small and deterministic (string/anchor assertions over file
  contents). No browser, no network. The verifier runs `pytest tests/test_qa_flows.py -q`.

---

## Cost preview

| Task | Executor | Output + overhead | Cost |
|---|---|---|---|
| 1. qa-flows.md store | sonnet | 700 + 10000 | $0.03 |
| 2. verify wiring + bootstrap + triggers | opus | 2800 + 10000 | $0.19 |
| 3. INDEX.md row | haiku | 120 + 10000 | $0.00 |
| 4. orchestrate recommendation | sonnet | 400 + 10000 | $0.03 |
| 5. tests | codex | 700 (no overhead) | $0.02 |

**Total: ~$0.27** (5 tasks · 2 waves · group 1 = T1–T4 parallel, group 2 = T5)
