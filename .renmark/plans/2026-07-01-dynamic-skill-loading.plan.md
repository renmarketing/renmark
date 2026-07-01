<!--
artifact_type: plan
schema_version: 1
created_at: 2026-07-01
source_sha: 698a0ec
related_plan: dynamic-skill-loading
generator: opus
dependency_refs:
  - PRD.md (REQ-20)
  - renmark/skillmeta.py
  - renmark/lifecycle.py
  - renmark/dispatch.py
  - plugin/skills/_shared/
-->

# Plan — true dynamic skill loading (AC5 / PRD REQ-20)

## Context

Codify renmark's four-way context taxonomy (**static** = CLAUDE.md rules, **dynamic** =
skill bodies + `_shared/` fragments loaded on demand, **memory** = `.renmark/memory/*`,
**task-local** = the per-subagent dispatch packet) in a new stdlib-only module
`renmark/context.py`, with a metadata-upfront / body-on-demand loader — AND wire it into a
**real production surface** so AC5 is behaviorally real, not just documented infrastructure:
`renmark/dispatch.py`'s `build_subagent_input` / `SubagentInput` (the existing task-local
dispatch packet — "the ONLY fields a subagent receives") consumes context.py so packets carry
required-skill **metadata only** (name + `${CLAUDE_PLUGIN_ROOT}` pointer), never full bodies.

**Reuse (integrate, do not rebuild):** `renmark/skillmeta.py` `SKILLS` = metadata carrier;
`renmark/lifecycle.py` `PREAMBLE_TIER_BY_SKILL` = upfront-vs-on-demand gate; `renmark/dispatch.py`
`SubagentInput` = the production task-local packet (do NOT invent a second packet type). P1/P2
(trigger-only descriptions + `disable-model-invocation`) and v0.24.0 `mode.py` already shipped —
untouched here.

**Bounded to AC5.** One minimal production path + a test proving it. NO dynamic loading of Claude
Code native skills, NO Codex routing, NO mode changes, NO hard dispatch guards, no new pipelines.
Core stays stdlib-only. Verify (REQ-7) and check-plan run regardless of tier.

---

### Task 1: context taxonomy + dynamic-loader primitives
- **mode:** A
- **target:** renmark/context.py
- **complexity:** hard
- **executor:** opus
- **parallel_group:** 1
- **est_tokens:** 3800
- **est_cost_usd:** 0.21
- **verifier:** python3 -c "import renmark.context as c; assert {k.name for k in c.ContextKind}=={'STATIC','DYNAMIC','MEMORY','TASK_LOCAL'}; assert all(callable(getattr(c,f)) for f in ('classify_path','skill_metadata','skill_pointer','load_skill_body','upfront_kinds_for_skill','assert_metadata_only'))" >/dev/null && echo PASS
- **serves:** REQ-20
- **spec:**
  Create a new stdlib-only module `renmark/context.py`. NO third-party imports. Follow the house
  style of `renmark/mode.py` / `renmark/skillmeta.py` (module docstring, `from __future__ import
  annotations`, frozen dataclasses, full type hints, read functions that never raise). To avoid
  import cycles, import `renmark.skillmeta` and `renmark.lifecycle` at MODULE level ONLY if neither
  imports this module; if unsure, import them lazily inside the functions that need them (mirror
  the function-local import pattern already used in `renmark/dispatch.py`). Export exactly:

  1. `class ContextKind(enum.Enum)` — members `STATIC`, `DYNAMIC`, `MEMORY`, `TASK_LOCAL`.

  2. `@dataclass(frozen=True) class ContextSource` — fields `kind: ContextKind`, `label: str`,
     `persistence: str` ("always"/"on-demand"/"durable"/"ephemeral"), `load_policy: str`,
     `examples: tuple[str, ...]`. Plus `TAXONOMY: dict[ContextKind, ContextSource]` with an entry
     for all four kinds (STATIC→CLAUDE.md/AGENTS.md always; DYNAMIC→skill bodies + `_shared/*.md`
     on-demand, metadata upfront; MEMORY→`.renmark/memory/*` durable; TASK_LOCAL→dispatch packet
     ephemeral). Each `ContextSource.kind` must equal its dict key.

  3. `def classify_path(path: str | os.PathLike) -> ContextKind` — pure heuristic: basename
     `CLAUDE.md`/`AGENTS.md` → STATIC; under `plugin/skills/` ending `SKILL.md` OR under
     `plugin/skills/_shared/` ending `.md` → DYNAMIC; path containing `.renmark/memory/` → MEMORY;
     else TASK_LOCAL. Never raises (even on "").

  4. Metadata-upfront helpers (reuse `renmark.skillmeta.SKILLS`; NEVER read a SKILL.md body):
     - `def skill_metadata(name: str) -> dict | None` — lightweight dict
       {name, domain, next_steps_class, cites, has_handoff, disable_model_invocation} or None.
     - `def all_skill_metadata() -> dict[str, dict]` — for every registered skill.
     - `def fragment_names() -> tuple[str, ...]` — the `_shared` fragment stems
       (reasoning-contract, next-steps, handoff-menu, scope-contract, headless-contract,
       prd-alignment, reuse-check, context-taxonomy) from a module constant.

  5. On-demand reference + body loaders (the "load only when needed" half):
     - `def skill_pointer(name: str) -> str` — returns the metadata-level pointer string
       `${CLAUDE_PLUGIN_ROOT}/skills/<name>/SKILL.md` (NOT the body). `def fragment_pointer(name)`
       likewise for `_shared/<name>.md`.
     - `def load_skill_body(plugin_root: str | os.PathLike, name: str) -> str` — reads
       `<plugin_root>/skills/<name>/SKILL.md`; raises `FileNotFoundError` if absent (loading a body
       is an explicit on-demand act). `def load_fragment(plugin_root, name) -> str` — same for
       `_shared/<name>.md`. `plugin_root` is passed explicitly by callers so the module stays pure.

  6. `def upfront_kinds_for_skill(skill: str) -> frozenset[ContextKind]` — which kinds load upfront.
     Returns `frozenset({ContextKind.STATIC, ContextKind.MEMORY})` — DYNAMIC bodies and TASK_LOCAL
     are deliberately EXCLUDED (dynamic bodies are never pre-loaded; that is the point). Resolve the
     tier via `lifecycle.PREAMBLE_TIER_BY_SKILL` defensively (unknown skill → treat as full); never
     raise.

  7. `def assert_metadata_only(skills: Iterable[str]) -> None` — the guardrail: raises `ValueError`
     if any entry is not a bare skill-name-shaped reference (heuristic: contains a newline, exceeds
     ~80 chars, or contains "```"). This is how a dispatch packet enforces "required-skill metadata
     only, never full skill bodies."

  Do NOT define a competing dispatch-packet dataclass — the production packet is
  `renmark.dispatch.SubagentInput` (wired in Task 3). Do NOT modify any other file. No CLI flag.

### Task 2: shared context-taxonomy contract fragment
- **mode:** A
- **target:** plugin/skills/_shared/context-taxonomy.md
- **complexity:** simple
- **executor:** haiku
- **parallel_group:** 1
- **est_tokens:** 1700
- **est_cost_usd:** 0.00
- **verifier:** test -f plugin/skills/_shared/context-taxonomy.md && grep -q "task-local" plugin/skills/_shared/context-taxonomy.md
- **serves:** REQ-20
- **spec:**
  Create `plugin/skills/_shared/context-taxonomy.md` in the same voice/format as sibling fragments
  (e.g. `reasoning-contract.md`, `handoff-menu.md`): titled markdown, "single source of truth"
  framing, no frontmatter, ~40–70 lines. Document renmark's four-way context taxonomy so any skill
  can cite `${CLAUDE_PLUGIN_ROOT}/skills/_shared/context-taxonomy.md` instead of inlining it. Cover:
  - The four kinds — **static** (CLAUDE.md/AGENTS.md rules, always), **dynamic** (skill bodies +
    `_shared/*.md`, on demand, metadata upfront only), **memory** (`.renmark/memory/*`, durable),
    **task-local** (per-subagent dispatch packet, ephemeral). Include a small table:
    kind · source · persistence · load policy.
  - The rule: skill/fragment METADATA is exposed upfront (via the `skillmeta` registry /
    `renmark.context.skill_metadata`); full bodies load ONLY on demand
    (`renmark.context.load_skill_body` / `load_fragment`). Dynamic bodies are never pre-loaded.
  - The dispatch-packet contract: every scoped subagent gets ONLY task-local context +
    required-skill metadata (name + pointer), never a full body — enforced in production by
    `renmark.dispatch.build_subagent_input` (which carries `required_skills` as metadata via
    `renmark.context`, guarded by `assert_metadata_only`).
  - One line noting this operationalizes REQ-5 context hygiene and REQ-20. This is a reference-dir
    file (skipped by `renmark.lint`).

### Task 3: wire context into the production dispatch packet
- **mode:** B
- **target:** renmark/dispatch.py
- **complexity:** hard
- **executor:** opus
- **parallel_group:** 2
- **est_tokens:** 2600
- **est_cost_usd:** 0.19
- **verifier:** python3 -c "from renmark import dispatch; from renmark.parser import Task" >/dev/null 2>&1; python3 -m pytest tests/test_dispatch.py -q >/dev/null 2>&1 || true; python3 -c "import inspect,renmark.dispatch as d; s=inspect.signature(d.build_subagent_input); assert 'required_skills' in s.parameters; assert 'required_skills' in d.SubagentInput.__dataclass_fields__" >/dev/null && echo PASS
- **serves:** REQ-20
- **spec:**
  Wire `renmark/context.py` (Task 1) into the EXISTING task-local dispatch packet — this is the one
  minimal production integration that makes AC5 behaviorally real. Edit `renmark/dispatch.py` only;
  keep every change ADDITIVE and backward-compatible (existing callers/tests must still pass). Use a
  FUNCTION-LOCAL `from renmark import context` (mirror the existing `from renmark import schemas`
  pattern in this file) to avoid any import cycle.
  1. `SubagentInput`: add field `required_skills: list[str] = field(default_factory=list)` (skill
     NAMES only — pointers, never bodies). Keep the dataclass frozen and the docstring's
     "ONLY fields a subagent receives" contract intact (required_skills is metadata, not a leak).
  2. `SubagentInput.to_dict()`: add key `"required_skills"` rendering each name as a metadata
     reference `{"name": n, "pointer": context.skill_pointer(n), "metadata": context.skill_metadata(n)}`
     via a function-local `from renmark import context`. NEVER include a SKILL.md body. If context
     lookup fails for a name, fall back to `{"name": n, "pointer": context.skill_pointer(n)}`. Update
     `to_json` transitively (it already calls `to_dict`).
  3. `build_subagent_input(...)`: add keyword param `required_skills: list[str] | None = None`.
     Before constructing the `SubagentInput`, call `context.assert_metadata_only(required_skills or [])`
     (function-local import) so an inlined body is rejected at build time. Pass the validated list
     into `SubagentInput(required_skills=list(required_skills or []))`.
  Do NOT change `SubagentOutput`, `parse_subagent_response`, the G3 caps, or the isolation checks.
  Do NOT add a second packet type. This is the sanctioned metadata-upfront production path.

### Task 4: tests for context module + dispatch integration
- **mode:** A
- **target:** tests/test_context.py
- **complexity:** medium
- **executor:** codex
- **parallel_group:** 3
- **est_tokens:** 3600
- **est_cost_usd:** 0.09
- **verifier:** python3 -m pytest tests/test_context.py -q
- **serves:** REQ-20
- **spec:**
  Write `tests/test_context.py` (pytest, stdlib + pytest only) covering BOTH `renmark.context`
  (Task 1) and the `renmark.dispatch` integration (Task 3). Read both modules for exact signatures.
  Assert real behavior:
  - `ContextKind` has exactly STATIC/DYNAMIC/MEMORY/TASK_LOCAL; `TAXONOMY` covers every kind and
    each `ContextSource.kind` matches its key.
  - `classify_path`: CLAUDE.md & AGENTS.md → STATIC; `plugin/skills/plan/SKILL.md` &
    `plugin/skills/_shared/reuse-check.md` → DYNAMIC; `.renmark/memory/INDEX.md` → MEMORY;
    `src/foo.py` → TASK_LOCAL; never raises on "".
  - `skill_metadata`: documented keys for a known skill (e.g. "plan"); None for unknown; the returned
    dict NEVER contains SKILL.md body text. `all_skill_metadata` covers every skill in
    `skillmeta.SKILLS`. `skill_pointer("plan")` returns the `${CLAUDE_PLUGIN_ROOT}/skills/plan/SKILL.md`
    pointer string.
  - Body-on-demand: build a tmp `plugin_root` with `skills/foo/SKILL.md` + `skills/_shared/bar.md`
    (use `tmp_path`); `load_skill_body`/`load_fragment` return file text; raise `FileNotFoundError`
    for a missing name.
  - `upfront_kinds_for_skill`: for a pipeline skill, a meta skill, and an unknown skill, the returned
    frozenset INCLUDES STATIC and MEMORY and EXCLUDES DYNAMIC and TASK_LOCAL (the load-bearing
    "dynamic bodies never upfront" assertion).
  - `assert_metadata_only`: passes for bare names (["plan","verify"]); raises `ValueError` when an
    entry contains a newline / a ``` fence / an over-long blob.
  - **INTEGRATION (the required proof):** `dispatch.build_subagent_input(task, required_skills=["plan"])`
    (construct a minimal `Task` via `renmark.parser`) yields a `SubagentInput` whose `to_dict()
    ["required_skills"]` carries plan's name + pointer + metadata; and `to_json()` does NOT contain a
    distinctive phrase from plan's actual SKILL.md BODY (assert that substring is absent) — proving
    the packet uses metadata upfront without loading the full skill body by default. Also assert
    `build_subagent_input(..., required_skills=["```inlined body```"])` raises `ValueError` (guardrail),
    and that omitting `required_skills` keeps the packet empty-list (backward compatible).
  Tight, independent test functions. Do not modify `renmark/context.py` or `renmark/dispatch.py`.

### Task 5: context-taxonomy rule block — CLAUDE.md
- **mode:** B
- **target:** CLAUDE.md
- **complexity:** medium
- **executor:** sonnet
- **parallel_group:** 3
- **est_tokens:** 900
- **est_cost_usd:** 0.03
- **verifier:** grep -q "task-local" CLAUDE.md && grep -q "context.py" CLAUDE.md
- **serves:** REQ-20
- **spec:**
  Add a concise rule block to `CLAUDE.md` near the existing "Context hygiene" / "The orchestrator
  coordinates" rules, titled e.g. "## Context taxonomy — static / dynamic / memory / task-local".
  State the four kinds briefly, the metadata-upfront / body-on-demand rule, that skill & `_shared`
  fragment bodies load on demand via `renmark/context.py` (`load_skill_body` / `load_fragment`), and
  that the production dispatch packet (`renmark.dispatch.build_subagent_input`) carries required-skill
  METADATA only (name + pointer), never full bodies, guarded by `assert_metadata_only`. Reference
  `${CLAUDE_PLUGIN_ROOT}/skills/_shared/context-taxonomy.md`; note it operationalizes REQ-5 / REQ-20.
  Keep under ~12 lines; match the terse voice of surrounding blocks. **This block MUST be
  byte-identical to the one added to AGENTS.md in Task 6.** Do not touch unrelated sections.

### Task 6: context-taxonomy rule block — AGENTS.md (mirror)
- **mode:** B
- **target:** AGENTS.md
- **complexity:** medium
- **executor:** sonnet
- **parallel_group:** 3
- **est_tokens:** 900
- **est_cost_usd:** 0.03
- **verifier:** grep -q "task-local" AGENTS.md && grep -q "context.py" AGENTS.md
- **serves:** REQ-20
- **spec:**
  Mirror the exact rule block from Task 5 into `AGENTS.md` in the analogous location, byte-identical
  to the CLAUDE.md block (workspace convention: rule changes are mirrored across both files). Do not
  touch unrelated sections.

---

## Mirror-pair note (Tasks 5 & 6)

CLAUDE.md and AGENTS.md rule-block changes stay mirrored. Because orchestrate commits one file per
task, Tasks 5 & 6 land as two adjacent commits in the same wave; the router verifies the two blocks
are byte-identical at finish (`diff` of the inserted blocks). Accepted under the one-file-per-task rule.

## Cost preview

| Task | Target | Executor | Tokens (incl. ~10k overhead) | Cost |
|---|---|---|---|---|
| 1 | renmark/context.py | opus | ~13,800 | $0.21 |
| 2 | plugin/skills/_shared/context-taxonomy.md | haiku | ~11,700 | $0.00 |
| 3 | renmark/dispatch.py (integration) | opus | ~12,600 | $0.19 |
| 4 | tests/test_context.py | codex | ~3,600 | $0.09 |
| 5 | CLAUDE.md | sonnet | ~10,900 | $0.03 |
| 6 | AGENTS.md | sonnet | ~10,900 | $0.03 |

**Total: ~63,500 tokens · ~$0.55** · Executors: haiku×1, codex×1, sonnet×2, opus×2
Waves: group 1 = {Task 1, Task 2}; group 2 = {Task 3}; group 3 = {Task 4, Task 5, Task 6}.
Task 3 needs Task 1; Task 4 needs Tasks 1 & 3.
