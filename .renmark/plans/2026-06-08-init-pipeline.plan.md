# Plan — init-pipeline (init as the front-door adoption pipeline)

**Spec:** `.renmark/specs/2026-06-08-init-pipeline.spec.md`
**Branch:** `feature/init-pipeline`

Folds `/renmark:setup`'s bootstrap into `/renmark:init` so init never dead-ends when
CLAUDE.md is absent. Reuses `renmark/bootstrap.py` + lint's BEGIN/END marker logic;
adds a deterministic `merge_rule_blocks()` (Option A — context-hygiene + accuracy).
`init.py` stays zero-LLM; the roadmap `--gaps` hand-off is inherited (ADR-009).
Task 1 (the init.py core) is correctness-critical and gates the tests (Task 4).
The two SKILL.md docs are disjoint files and run in parallel with Task 1.

---

### Task 1: init.py — scaffold phase + deterministic rule-block back-fill
- **mode:** B
- **target:** renmark/init.py
- **complexity:** hard
- **executor:** opus
- **parallel_group:** 1
- **est_tokens:** 2500
- **est_cost_usd:** 0.19
- **verifier:** python3 -c "from renmark import init; assert hasattr(init,'merge_rule_blocks'); print('ok')" && ruff check renmark/init.py && mypy renmark/init.py
- **serves:** REQ-8
- **spec:**
  Make `python -m renmark.init` self-bootstrap deterministically (zero-LLM). Read the
  WHOLE current renmark/init.py first; do NOT remove/alter existing functions
  (scan_repo, merge_stub_into, write_full_map, write_standards_md, run/main). Also read
  renmark/bootstrap.py (the existing `bootstrap(repo, *, init_git=...)` scaffold) and
  renmark/lint.py (`_BEGIN_RE`/`_END_RE` + `lint_template_rule_blocks` marker logic) and
  renmark/memory.py (`template_dir`). Changes:
  1. **Scaffold phase at the TOP of `run()`**, BEFORE the current CLAUDE.md-missing
     hard-error (~line 1295): call `bootstrap(repo, init_git=False)` (creates
     CLAUDE.md/AGENTS.md/.gitignore/.renmark/ from templates, existence-skip) and create
     `CHANGELOG.md` from template if absent (bootstrap omits it today). After scaffolding,
     CLAUDE.md exists — convert the old exit-1 into a should-never-happen guard (only fires
     if scaffolding genuinely failed, with a clear message), NOT a "run setup first" bail.
  2. **NEW `merge_rule_blocks(repo, *, template_dir=...)`** — deterministic back-fill of
     missing canonical `BEGIN:<name>`…`END:<name>` rule blocks into an existing
     CLAUDE.md/AGENTS.md. REUSE lint's marker regexes (import them or a shared helper — do
     NOT duplicate/redefine the patterns; keep one source of truth). Rules: insert ONLY
     blocks that are ABSENT (idempotent); insert the template block BYTE-VERBATIM at the
     correct marker position; NEVER edit or reorder an existing block (non-destructive);
     keep CLAUDE.md and AGENTS.md in sync; on a malformed/unbalanced existing block, SKIP
     it and report rather than corrupt. Return a small result (e.g. count of blocks added
     per file).
  3. **Wire `merge_rule_blocks` into `run()`** after scaffold, before the scan. Extend the
     bounded `OK …` stdout line with a `blocks=<n added|unchanged>` field. Keep byte-skip
     idempotency and the zero-LLM guarantee. No new third-party deps (stdlib + existing
     renmark modules only). Match existing style + type hints.

### Task 2: init/SKILL.md — redefine as the 6-step front-door pipeline
- **mode:** B
- **target:** plugin/skills/init/SKILL.md
- **complexity:** medium
- **executor:** sonnet
- **parallel_group:** 1
- **est_tokens:** 1600
- **est_cost_usd:** 0.03
- **verifier:** grep -qi "scaffold" plugin/skills/init/SKILL.md && grep -qi "roadmap" plugin/skills/init/SKILL.md && grep -q "next-steps.md" plugin/skills/init/SKILL.md
- **serves:** REQ-8
- **spec:**
  Read the current plugin/skills/init/SKILL.md + the spec
  (.renmark/specs/2026-06-08-init-pipeline.spec.md) first. Rewrite init's SKILL.md to
  document the 6-step front-door pipeline: (1) detect project state, (2) scaffold-if-missing
  (now done by `python -m renmark.init` via bootstrap + CHANGELOG create — non-destructive),
  (3) deterministic rule-block back-fill (`merge_rule_blocks`, zero-LLM, byte-verbatim — the
  agent does NOT read/merge blocks itself; init.py does it), (4) scan & map, (5) standards +
  health gaps, (6) roadmap `--gaps` hand-off at the end (nudge /renmark:prd if no PRD —
  KEEP the existing ADR-009 wiring) → hand off. Update the old "CLAUDE.md missing → run
  setup first" guidance (exit-1 contract) since init now scaffolds. Keep boundaries:
  init.py is zero-LLM; the roadmap hand-off + the aux-class `next-steps.md` citation stay.
  Note `/renmark:setup` is now a thin alias of init's rule-block refresh. Mirror any
  rule-affecting change note for AGENTS.md/CLAUDE.md sync if that convention is in the file.

### Task 3: setup/SKILL.md — thin alias of init's rule-block refresh
- **mode:** B
- **target:** plugin/skills/setup/SKILL.md
- **complexity:** simple
- **executor:** haiku
- **parallel_group:** 1
- **est_tokens:** 500
- **est_cost_usd:** 0.00
- **verifier:** grep -qi "alias" plugin/skills/setup/SKILL.md && grep -qi "init" plugin/skills/setup/SKILL.md && grep -q "next-steps.md" plugin/skills/setup/SKILL.md
- **serves:** REQ-8
- **spec:**
  Read the current plugin/skills/setup/SKILL.md first. Rewrite it as a THIN ALIAS: keep the
  frontmatter `name: setup` and a real body (so lint's command↔skill pairing + frontmatter
  checks stay green), but have it delegate to `/renmark:init`'s rule-block refresh rather
  than duplicating scaffold logic. State plainly that `/renmark:init` is now the front-door
  adoption pipeline and `setup` exists as a thin rule-block-refresh alias (per PRD REQ-8).
  Keep/ensure the aux-class `next-steps.md` citation (required by lint_next_steps_citation).
  Do NOT delete commands/setup.md or skills/setup/. Keep it short.

### Task 4: tests for scaffold + merge_rule_blocks
- **mode:** A
- **target:** tests/test_init_pipeline.py
- **complexity:** medium
- **executor:** sonnet
- **parallel_group:** 2
- **est_tokens:** 1800
- **est_cost_usd:** 0.04
- **verifier:** python3 -m pytest tests/test_init_pipeline.py -q
- **serves:** REQ-8
- **spec:**
  Write hermetic pytest tests (sonnet per ADR-007 — new test file; codex's read-only
  sandbox can't write it). Depends on Task 1 (renmark/init.py: scaffold phase +
  `merge_rule_blocks`). Read renmark/init.py (post-Task-1), renmark/bootstrap.py, and an
  existing test that builds a tmp repo for fixture style. Cover:
  - **No more exit 1:** run init's `run()` (or `python -m renmark.init` via subprocess) in a
    tmp repo with NO CLAUDE.md → it scaffolds CLAUDE.md/AGENTS.md/CHANGELOG.md/.renmark/ and
    returns success (exit 0), NOT the old exit-1 "run setup first".
  - **Non-destructive:** re-run on a repo that already has CLAUDE.md → existing content is
    untouched (existence-skip / byte-skip); idempotent.
  - **merge_rule_blocks:** an existing CLAUDE.md missing some canonical BEGIN/END rule
    blocks → only the missing blocks are inserted, BYTE-VERBATIM from the template; blocks
    already present (including a hand-modified one) are NOT edited or reordered;
    CLAUDE.md↔AGENTS.md stay in sync; idempotent on re-run.
  - **Malformed markers:** an unbalanced BEGIN/END block is skipped/reported, never
    corrupted.
  Keep tests hermetic (tmp_path; no network; no mutation outside tmp). Use the real
  template_dir via memory.template_dir().

---

## Cost preview

| Task | Executor | Total tokens (incl. ~10k overhead) | Cost |
|---|---|---|---|
| 1 init.py core (scaffold + merge_rule_blocks) | opus | 12,500 | $0.1875 |
| 2 init/SKILL.md pipeline | sonnet | 11,600 | $0.0348 |
| 3 setup/SKILL.md alias | haiku | 10,500 | $0.0011 |
| 4 tests | sonnet | 11,800 | $0.0354 |

**Tasks: 4 (2 parallel groups). Executors: opus×1, sonnet×2, haiku×1.**
**Total tokens: ~46k. Total cost: ~$0.26**
