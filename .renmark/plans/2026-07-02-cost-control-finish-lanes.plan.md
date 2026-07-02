---
artifact_type: plan
schema_version: 1
created_at: 2026-07-02T00:00:00Z
source_sha: 4fb7ae9
related_plan: null
generator: opus
stale_after: 2026-10-02T00:00:00Z
dependency_refs:
  - .renmark/specs/2026-07-02-agency-mode.request.md
completion_state: complete
confidence: high
validation_status: validated
---

# Plan — cost-control-finish-lanes

## Goal
Add cost-control, context-budget, model-routing, and finish-lane infrastructure so
renmark stays cost-aware during long agentic sessions and can later back a future
Agency Mode (queued: `.renmark/specs/2026-07-02-agency-mode.request.md`) — WITHOUT
implementing Agency Mode, weakening verification, removing the renmark self-update
finish workflow, or blocking useful subagents. PRD verdict: **aligned** — this
operationalizes REQ-2 (cost preview + cheapest-capable routing), REQ-5 (context
hygiene), REQ-9 (bounded budgets), REQ-16 (safe pause). No PRD amendment.

## Design (reuse, don't rebuild)

Recon confirmed the load-bearing primitives already exist; this feature adds the
missing declarative/reusable layer around them:

- **Finish lanes** — new `renmark/finish_lanes.py`, mirroring `renmark/sizing.py`
  (deterministic, zero-LLM, never-raises). Four lanes as frozen declarative records
  (`quick | release | self-update | full`), each declaring merges / releases /
  packages / updates_wsl / cleans_worktrees / verification / cost_level / actions.
  `recommend_lane()` picks the cheapest safe lane from lifecycle stage and recommends
  `self-update` when the repo IS renmark itself. `finish/SKILL.md` maps its existing
  PR/Merge/Release/Nothing machinery under these lanes and adds the two missing
  self-update steps (WSL install-update, worktree cleanup) to the self-update/full
  lanes only. The full renmark-on-renmark workflow is preserved, not weakened.
- **Cost preview** — new `renmark/cost.py` extracting the pricing table + formula
  that today live inline in `plan/SKILL.md §6`, exposed as a reusable
  `estimate_cost()` / `cost_band()` plus `requires_escalation()` (is Opus/Fable
  justified?). `plan`'s existing inline math is left untouched (no refactor risk);
  finish + future Agency Mode import the reusable fn.
- **Context thresholds** — extend the existing 60%/80% machinery
  (`state/skills.py` + CLAUDE.md) with the requested absolute tiers via a pure
  `context_budget_hint(tokens)` helper: ~100k → summarize stage, ~120k → `/compact`,
  ~150k → strongly recommend checkpoint. Cross-domain `/clear` detection is unchanged.
- **Model-routing / subagent-budget discipline** — `_shared` fragments +
  CLAUDE.md/AGENTS.md rule blocks (documentation-tier). Haiku/Sonnet/Codex for
  routine work; Opus/Fable escalation-only. Subagents: local grep/read first, one
  scoped Explore before many agents, each carries mission/scope/output/stop/tier/
  verification.
- **Agency Mode reuse** — the queued agency-mode spec is cross-referenced to these
  primitives (finish lanes, cost preview, context thresholds, subagent budget). No
  Agency code in this feature.

## Tasks

### Task 1: finish_lanes.py — declarative finish lanes
- **mode:** B
- **target:** renmark/finish_lanes.py
- **complexity:** medium
- **executor:** sonnet
- **parallel_group:** 1
- **est_tokens:** 2600
- **est_cost_usd:** 0.08
- **verifier:** python3 -m pytest tests/test_finish_lanes.py -q && python3 -m py_compile renmark/finish_lanes.py
- **serves:** REQ-2
- **spec:**
  Create `renmark/finish_lanes.py`, mirroring the style of `renmark/sizing.py`
  (module constants, `Literal` type alias, pure functions, **never raises** — degrade
  to the safe default on any uncertainty). Define:
  - `Lane = Literal["quick", "release", "self-update", "full"]` and
    `LANE_QUICK/RELEASE/SELF_UPDATE/FULL` string constants.
  - A frozen `@dataclass(frozen=True) class LaneSpec` with fields:
    `name: str`, `merges: bool`, `releases: bool`, `packages: bool`,
    `updates_wsl: bool`, `cleans_worktrees: bool`, `verification: str`
    (`"artifact-confirm" | "re-verify" | "re-verify+release-qa" | "deepest"`),
    `cost_level: str` (`"low" | "medium" | "high"`), `actions: tuple[str, ...]`.
  - `LANES: dict[Lane, LaneSpec]` with these exact declarations:
    - `quick`: merges=F, releases=F, packages=F, updates_wsl=F, cleans_worktrees=F,
      verification="artifact-confirm", cost_level="low",
      actions=(summarize state, confirm verify/review artifacts exist).
    - `release`: merges=T, releases=T, packages=F, updates_wsl=F, cleans_worktrees=F,
      verification="re-verify", cost_level="medium",
      actions=(verify release readiness, merge when approved, version/changelog/release when relevant).
    - `self-update`: merges=T, releases=T, packages=T, updates_wsl=T,
      cleans_worktrees=T, verification="re-verify+release-qa", cost_level="high",
      actions=(merge branches/worktrees, release/version bump, package/zip renmark,
      update/install renmark on WSL, verify installed CLI/plugin, clean worktrees, document release).
    - `full`: all bool True, verification="deepest", cost_level="high",
      actions=(all finish behaviours; deepest verification; release + package + install + cleanup where applicable).
  - `def recommend_lane(repo, *, is_self=None, lifecycle_stage=None) -> Lane:`
    Cheapest safe default keyed off lifecycle stage — if the stage indicates work is
    not release-ready (e.g. not yet `reviewed`/`ready-to-release`) default `quick`;
    once `reviewed`/`ready-to-release`, default `release`. **If the repo IS renmark
    itself, recommend `self-update` instead of a cheap lane.** Detect self via
    `is_self` when passed, else `is_renmark_repo(repo)` below. Never `full` by default
    (`full` is explicit-only). Never raises → fall back to `quick`.
  - `def is_renmark_repo(repo) -> bool:` True when the repo root contains BOTH a
    `renmark/` package dir and a `plugin/skills/finish/SKILL.md` (the renmark plugin
    signature). Pure, never raises (missing paths → False).
  - `def resolve_lane(recommended: Lane, override: str | None) -> Lane:` explicit
    selection wins; unknown override → return `recommended` (never raise). `full`
    always honored when requested.
  - `def lane_table() -> str:` compact markdown table with one row per lane and
    columns: Lane | Merges | Releases | Packages | WSL | Verification | Cost — for the
    finish preview. `def describe_lane(name) -> str:` one-line summary of a lane's
    actions. Both pure/never-raise.
  Add a module docstring stating the deterministic/never-raise contract and that this
  is reused by `finish/SKILL.md` today and by a future Agency Mode.

### Task 2: cost.py — reusable cost preview + escalation helper
- **mode:** B
- **target:** renmark/cost.py
- **complexity:** medium
- **executor:** sonnet
- **parallel_group:** 1
- **est_tokens:** 2200
- **est_cost_usd:** 0.07
- **verifier:** python3 -m pytest tests/test_cost.py -q && python3 -m py_compile renmark/cost.py
- **serves:** REQ-2
- **spec:**
  Create `renmark/cost.py` (deterministic, never-raises). Extract the pricing/formula
  that currently live inline in `plan/SKILL.md §6` into reusable code — do NOT modify
  `plan/SKILL.md` (leave its inline math; this module is additive):
  - `PRICE_PER_KTOK: dict[str, float]` = {haiku: 0.0001, codex: 0.03 (midpoint of
    0.01–0.05), sonnet: 0.003, opus: 0.015, fable: 0.030}. `AGENT_OVERHEAD_TOKENS =
    10_000` (per non-codex agent task, matching plan §6).
  - `@dataclass(frozen=True) class CostPreview` with: `est_tokens: int`,
    `est_cost_usd: float`, `cost_band: str` (low/medium/high), `uses_subagents: bool`,
    `requires_expensive_model: bool`, `cheaper_alternative: str | None`.
  - `def estimate_cost(items) -> CostPreview:` accept a list of dicts/objects each with
    `executor` and optional `est_tokens`; sum tokens (+overhead for agent executors),
    price per tier, set `requires_expensive_model` when any item routes opus/fable,
    set `uses_subagents` when any item is an agent executor, and set
    `cheaper_alternative` to a one-line note when an expensive tier is used for work
    that looks routine (heuristic: opus/fable on a task whose complexity is not
    "hard"). Never raises → unknown executor priced at sonnet, missing tokens → 0.
  - `def cost_band(usd: float) -> str:` low < $0.10, medium < $1.00, else high.
    (Thresholds as module constants.)
  - `def requires_escalation(*, complexity=None, kind=None) -> bool:` True only for
    high-risk architecture, major design forks, adversarial review, or judgment-heavy
    work (`complexity == "hard"` OR `kind in {"architecture","adversarial-review",
    "design-fork"}`); else False. This is the "Opus/Fable only when justified" gate.
  Module docstring: reusable by finish lane previews and a future Agency Mode; states
  the "escalate only when justified" contract.

### Task 3: context_budget_hint — absolute context thresholds
- **mode:** B
- **target:** renmark/state/skills.py
- **complexity:** medium
- **executor:** sonnet
- **parallel_group:** 1
- **est_tokens:** 1400
- **est_cost_usd:** 0.05
- **verifier:** python3 -m pytest tests/test_state_skills.py -q && python3 -m py_compile renmark/state/skills.py
- **serves:** REQ-5
- **spec:**
  In `renmark/state/skills.py`, ADD a pure, never-raises helper (do NOT change the
  existing `context_budget_check` cross-domain logic — this is additive):
  `def context_budget_hint(tokens: int) -> str | None:` returning the tiered absolute
  guidance — thresholds as module constants
  (`CTX_SUMMARIZE = 100_000`, `CTX_COMPACT = 120_000`, `CTX_CHECKPOINT = 150_000`):
  - `< 100k` → `None`
  - `>= 100k and < 120k` → "≈100k context — summarize the current stage before continuing."
  - `>= 120k and < 150k` → "≈120k context — recommend `/compact` before the next skill."
  - `>= 150k` → "≈150k context — strongly recommend `/compact` or a checkpoint before continuing."
  Non-int / negative input → `None` (never raise). Add a short docstring noting these
  absolute tiers complement the existing 60%/80% self-monitored budget and the
  cross-domain `/clear` hint (unchanged). If `tests/test_state_skills.py` does not
  exist, the test task (Task 4) creates it; keep the verifier as written.

### Task 4: tests for finish_lanes + cost + context hint
- **mode:** B
- **target:** tests/test_finish_lanes.py, tests/test_cost.py, tests/test_state_skills.py
- **complexity:** medium
- **executor:** codex
- **parallel_group:** 2
- **est_tokens:** 3000
- **est_cost_usd:** 0.10
- **verifier:** python3 -m pytest tests/test_finish_lanes.py tests/test_cost.py tests/test_state_skills.py -q 2>&1 | tail -n 3
- **serves:** REQ-2
- **spec:**
  Add focused, deterministic tests (tmp_path where a repo is needed; no network; no
  model calls). Cover:
  - **finish_lanes:** every lane in `LANES` has all declared boolean/verification/
    cost fields; `quick` merges/releases/packages/updates_wsl all False;
    `self-update` all the self-update flags True; `full` all True.
    `recommend_lane` returns `quick` for an early lifecycle stage, `release` for a
    `ready-to-release`/`reviewed` stage on a NON-renmark repo, and **`self-update`
    when `is_self=True`** (and when pointed at a repo whose root has both `renmark/`
    and `plugin/skills/finish/SKILL.md`). `recommend_lane` never returns `full`.
    `is_renmark_repo` True for a fixture repo with both markers, False for an empty
    tmp dir. `resolve_lane` honors an explicit `full`, and returns the recommended
    lane for an unknown override. `lane_table()`/`describe_lane()` return non-empty
    strings and never raise.
  - **cost:** `estimate_cost` sums tokens+overhead and prices per tier; a plan using
    only haiku is `low` band; a plan with an opus task sets
    `requires_expensive_model=True`; opus on a non-hard task yields a non-None
    `cheaper_alternative`; unknown executor and missing tokens do not raise.
    `cost_band` boundaries ($0.10, $1.00). `requires_escalation` True for
    `complexity="hard"` and for `kind="adversarial-review"`, False for a routine doc
    task.
  - **context hint:** `context_budget_hint` returns None below 100k, the summarize
    string in [100k,120k), the compact string in [120k,150k), the checkpoint string
    at/above 150k, and None for negative/non-int input.
  Follow existing test style in `tests/`. Do not modify tests unrelated to these
  modules. Keep everything green.

### Task 5: _shared discipline fragments
- **mode:** B
- **target:** plugin/skills/_shared/model-routing.md, plugin/skills/_shared/subagent-budget.md, plugin/skills/_shared/finish-lanes.md, plugin/skills/_shared/cost-preview.md
- **complexity:** simple
- **executor:** haiku
- **parallel_group:** 1
- **est_tokens:** 2000
- **est_cost_usd:** 0.001
- **verifier:** test -s plugin/skills/_shared/model-routing.md && test -s plugin/skills/_shared/subagent-budget.md && test -s plugin/skills/_shared/finish-lanes.md && test -s plugin/skills/_shared/cost-preview.md
- **serves:** REQ-2
- **spec:**
  Create four `_shared` reference fragments (documentation only; match the existing
  `_shared/*.md` house style — a "single source of truth" header, concise tables, no
  duplicated skill logic). These are loaded on demand, never pre-loaded.
  - **model-routing.md** — stricter routing discipline: Haiku for docs/grep/summaries/
    changelog/small audits; Sonnet for normal planning/implementation/review
    summaries; Codex for bounded code/test tasks; Opus/Fable escalation-only
    (high-risk architecture, major design forks, adversarial review, judgment-heavy).
    Explicit: do NOT use Opus/Fable by default for simple finish/docs/grep/changelog/
    small verification. Point to `renmark/cost.py::requires_escalation` as the gate and
    to `.renmark/memory/routing.md` for the ledger.
  - **subagent-budget.md** — before spawning subagents: prefer local grep/read first;
    one scoped Explore pass before many agents; cheaper models for read-only tasks; no
    general-purpose subagents unless necessary. Every subagent packet MUST carry:
    mission, files/search targets, output format, stop condition, model tier,
    verification expectation. Warn/route carefully when a workflow becomes
    subagent-heavy. Cross-reference `_shared/reuse-check.md` and `context-taxonomy.md`.
  - **finish-lanes.md** — the finish-lane contract: the four lanes and the per-lane
    matrix (merges / releases / packages / updates WSL / verification / cost), the
    cheapest-safe-default rule, and the "recommend self-update when the project is
    renmark itself" rule. State that `renmark/finish_lanes.py` is the deterministic
    source of truth (`LANES`, `recommend_lane`, `lane_table`). Note the self-update
    lane preserves the full renmark-on-renmark workflow (merge → release → zip →
    WSL install → verify installed CLI/plugin → clean worktrees → document).
  - **cost-preview.md** — before expensive work, show: estimated model tier, est
    token/cost band, whether subagents will be used, whether expensive models are
    required, and a cheaper alternative when reasonable; escalate to Opus/Fable only
    when justified. State `renmark/cost.py::estimate_cost` is the reusable source and
    that this complements plan §6 and the orchestrate pre-flight cost preview.

### Task 6: wire finish/SKILL.md to lanes + cost preview
- **mode:** B
- **target:** plugin/skills/finish/SKILL.md
- **complexity:** hard
- **executor:** sonnet
- **parallel_group:** 2
- **est_tokens:** 2800
- **est_cost_usd:** 0.09
- **verifier:** python3 -m pytest tests/ -q -k "finish or lint" 2>&1 | tail -n 3 && python3 -m renmark.lint 2>&1 | tail -n 3
- **serves:** REQ-2
- **spec:**
  Edit `plugin/skills/finish/SKILL.md` to organize its close-out around the four
  finish lanes WITHOUT removing or weakening any existing capability (merge, release,
  version bump, zip/package, tag, gh release, map refresh, feature report, release QA
  all stay). Changes:
  - Add a "Finish lanes" section near the top that renders the lane matrix (point to
    `renmark/finish_lanes.py::lane_table` / `_shared/finish-lanes.md` — do not hardcode
    a divergent copy of the table logic). Explain each lane's actions/merge/release/
    package/WSL/verification/cost.
  - Add a lane-selection step BEFORE the destructive close-out: compute the
    recommended lane via `recommend_lane` (cheapest safe by lifecycle stage;
    **self-update when `is_renmark_repo`**), show a cost preview for that lane via
    `renmark/cost.py`, and require an explicit choice (this is the existing
    merge/release human gate — keep it gated per handoff-menu.md; do not add a second
    gate). `full` is explicit-only.
  - Map the EXISTING PR/Merge/Release/Nothing machinery under the lanes: quick =
    summarize + confirm artifacts (no merge/release/zip/WSL); release = verify + merge
    + version/changelog/release; self-update = release PLUS package/zip + WSL
    install-update + verify installed CLI/plugin + clean worktrees + document release;
    full = deepest verify + everything.
  - ADD the two currently-missing self-update steps (self-update and full lanes only):
    (a) update/install renmark on WSL and verify the installed CLI/plugin, referencing
    the manual installer (`install.sh`) and the WSL/Windows note — keep it a gated,
    optional step, never automatic; (b) clean worktrees after merge. Cite the memory
    note about the separate Windows clone if relevant.
  - Verify still runs on the appropriate lanes (REQ-7 not weakened): quick confirms
    existing artifacts; release/self-update/full re-verify.
  - Keep the next-steps hand-off contract intact.
  Keep the edit surgical; do not rewrite unrelated sections. `renmark.lint` must pass.

### Task 7: rule blocks + help + routing + agency cross-ref
- **mode:** B
- **target:** CLAUDE.md, AGENTS.md, plugin/skills/help/SKILL.md, .renmark/memory/routing.md, .renmark/specs/2026-07-02-agency-mode.request.md
- **complexity:** medium
- **executor:** sonnet
- **parallel_group:** 2
- **est_tokens:** 2400
- **est_cost_usd:** 0.08
- **verifier:** python3 -m renmark.lint 2>&1 | tail -n 3 && python3 -m pytest tests/ -q -k "lint or claudemd or agents or help" 2>&1 | tail -n 3
- **serves:** REQ-2
- **spec:**
  Documentation wiring (keep each block concise; CLAUDE.md/AGENTS.md are mirrored —
  edit BOTH identically in the same task):
  - Add/extend rule blocks in CLAUDE.md AND AGENTS.md:
    (a) **Model-routing discipline** — Haiku/Sonnet/Codex for routine; Opus/Fable
    escalation-only; do not default to expensive models for simple finish/docs/grep/
    changelog/small verification. Point to `_shared/model-routing.md`.
    (b) **Context thresholds** — the 100k-summarize / 120k-compact / 150k-checkpoint
    tiers (complementing the existing 60%/80% block, not replacing it); cross-domain →
    `/clear`. Point to `context_budget_hint`.
    (c) **Cost preview before expensive work** — show tier/band/subagents/expensive-
    model/cheaper-alternative first. Point to `_shared/cost-preview.md` +
    `renmark/cost.py`.
    (d) **Finish lanes** — one-line pointer to `_shared/finish-lanes.md` and the
    default-cheapest-safe / self-update-for-renmark rule.
    (e) **Subagent budget** — one-line pointer to `_shared/subagent-budget.md`.
  - `plugin/skills/help/SKILL.md`: mention that `/renmark:finish` supports lanes
    (quick / release / self-update / full) in the finish line.
  - `.renmark/memory/routing.md`: append a short guidance note reinforcing the
    escalation-only rule for opus/fable and pointing at `_shared/model-routing.md`.
  - `.renmark/specs/2026-07-02-agency-mode.request.md`: add a short "Reuses these
    primitives" note listing `renmark/finish_lanes.py`, `renmark/cost.py`,
    `context_budget_hint`, and the four `_shared` discipline fragments — so Agency
    Mode is wired to reuse this infrastructure (AC8), no Agency code added.
  Do not touch behavior code. `renmark.lint` must pass.

## Verifier (whole-plan)
`python3 -m pytest -q && python3 -m renmark.lint`
(existing suite stays green — AC9 — plus the three new test files.)

## Acceptance-criteria mapping
- AC1 documented cost-control + model-routing rules → Task 5, Task 7.
- AC2 finish supports/defines lanes → Task 1, Task 6.
- AC3 renmark self-update finish preserved → Task 6 (additive; nothing removed).
- AC4 expensive finish only when the lane requires it → Task 1 (cost_level) + Task 6.
- AC5 subagent-heavy workflows get budget discipline → Task 5 (subagent-budget) + Task 7.
- AC6 context-size hygiene enforced/guided → Task 3, Task 7(b).
- AC7 cost previews before expensive work → Task 2, Task 5 (cost-preview), Task 6, Task 7(c).
- AC8 Agency Mode can reuse infra → Task 7 (agency spec cross-ref) + reusable modules.
- AC9 existing workflows still pass tests → whole-plan verifier + Task 4.

---

## Addendum (2026-07-02) — specialized subagent profiles

Owner-directed extension of the subagent-budget discipline (aligned, no PRD drift):
reduce generic `general-purpose` subagents; prefer specialized role profiles;
dispatch packets carry `role`/`profile`; cost/routing summaries report the role;
general-purpose is fallback-only; specialized agents get narrower context.

Roles: docs-editor, code-implementer, test-writer, reviewer, release-manager,
researcher, audit-reader, finish-lane-specialist (+ `general-purpose` fallback).

### Task 8: subagent_profiles.py + dispatch role wiring
- **mode:** B
- **target:** renmark/subagent_profiles.py
- **complexity:** medium
- **executor:** sonnet
- **parallel_group:** 3
- **est_tokens:** 2600
- **est_cost_usd:** 0.08
- **verifier:** python3 -m pytest tests/test_subagent_profiles.py tests/test_dispatch.py -q 2>&1 | tail -n 3 && python3 -m py_compile renmark/subagent_profiles.py renmark/dispatch.py
- **serves:** REQ-5
- **spec:** New `renmark/subagent_profiles.py` (deterministic, never-raises, sizing.py
  style) with a frozen `ProfileSpec` (role, model_tier, allowed_targets, output_format,
  stop_condition, verification, context_scope) and `PROFILES` for the 8 roles +
  `general-purpose`. `resolve_profile(task)->role` heuristic (test targets→test-writer,
  docs/md→docs-editor, core code→code-implementer, review kind→reviewer, etc.), falling
  back to `general-purpose` ONLY when nothing fits. `profile_tier(role)`. Wire
  `SubagentInput.role: str = "general-purpose"` and `build_subagent_input(..., role=None)`
  resolving via `resolve_profile(task)` when None. Keep packet metadata-only.

### Task 9: role reporting in ledger + cost summary
- **mode:** B
- **target:** renmark/memory.py
- **complexity:** medium
- **executor:** sonnet
- **parallel_group:** 3
- **est_tokens:** 1800
- **est_cost_usd:** 0.06
- **verifier:** python3 -m pytest tests/test_memory.py tests/test_cost.py -q 2>&1 | tail -n 3 && python3 -m py_compile renmark/memory.py renmark/cost.py
- **serves:** REQ-2
- **spec:** Add optional `role: str | None = None` to `memory.append_routing` and record
  it in the ledger line (backward-compatible; omitted → today's format). Add role
  awareness to `renmark/cost.py::estimate_cost`: items may carry `role`; expose
  `CostPreview.roles: tuple[str, ...]` (distinct roles seen, sorted) so cost summaries
  report role/profile not just generic agent usage. Never raises; existing calls unchanged.

### Task 10: profiles tests
- **mode:** B
- **target:** tests/test_subagent_profiles.py
- **complexity:** medium
- **executor:** codex
- **parallel_group:** 4
- **est_tokens:** 2200
- **est_cost_usd:** 0.07
- **verifier:** python3 -m pytest tests/test_subagent_profiles.py -q 2>&1 | tail -n 3
- **serves:** REQ-5
- **spec:** Cover: every role in PROFILES has all fields + a non-general model_tier where
  appropriate; `resolve_profile` maps a test-target task→test-writer, a .md-target→
  docs-editor, a core-code task→code-implementer, and an unmatched task→general-purpose
  (fallback only); `build_subagent_input` populates `role`; `append_routing(role=...)`
  writes the role; `estimate_cost` exposes `roles`. Deterministic, tmp_path.

### Task 11: profiles docs + rule + agency note
- **mode:** B
- **target:** plugin/skills/_shared/subagent-profiles.md
- **complexity:** simple
- **executor:** haiku
- **parallel_group:** 3
- **est_tokens:** 1500
- **est_cost_usd:** 0.001
- **verifier:** test -s plugin/skills/_shared/subagent-profiles.md && python3 -m renmark.lint 2>&1 | tail -n 3
- **serves:** REQ-5
- **spec:** New `_shared/subagent-profiles.md` describing the 8 roles + fallback, each
  with mission/context/targets/output/stop/tier/verification, and the "prefer
  specialized, general-purpose is fallback, UI may still show general-purpose but
  renmark logs the intended role" rule. Add a one-line pointer + role list to
  `_shared/subagent-budget.md`, a mirrored one-line rule to CLAUDE.md AND AGENTS.md
  (subagent-profiles), and a one-line note to the agency-mode spec that Agency agents
  reuse these profiles. `renmark/subagent_profiles.py` is the source of truth.

### Addendum acceptance mapping
- AC1 avoid generic when a role fits → Task 8 (resolve_profile fallback-only).
- AC2 packets include role/profile → Task 8 (SubagentInput.role).
- AC3 profiles map to cheaper/default tiers → Task 8 (ProfileSpec.model_tier).
- AC4 general-purpose only fallback → Task 8 (resolve_profile).
- AC5 cost summaries report role → Task 9 (ledger role + CostPreview.roles).
- AC6 specialized get less context → Task 8 (ProfileSpec.context_scope; packet stays bounded).
