# Plan — modularity-health-lens (advisory ast code-health gaps)

**Spec:** `.renmark/specs/2026-06-08-modularity-health-lens.spec.md`
**Branch:** `feature/modularity-health-lens`

New `renmark/modularity.py` ast analyzer (the core) → wired into `init`'s existing
standards-health pipeline + tests + a one-line SKILL note. Advisory, never blocking,
zero-LLM, no new deps. Task 1 is correctness-critical (ast + cognitive complexity) →
opus; the dependents → sonnet/haiku.

---

### Task 1: modularity ast analyzer (5 metrics)
- **mode:** A
- **target:** renmark/modularity.py
- **complexity:** hard
- **executor:** opus
- **parallel_group:** 1
- **est_tokens:** 2600
- **est_cost_usd:** 0.19
- **verifier:** python3 -c "from renmark.modularity import analyze; print('ok')" && ruff check renmark/modularity.py && mypy renmark/modularity.py
- **serves:** REQ-7
- **spec:**
  Create `renmark/modularity.py` — PURE, stdlib-`ast`-only, zero-dep, never-raise
  analyzer. READ FIRST: renmark/init.py (the `Gap` dataclass — REUSE it; the
  source-file walker / exclusion set; `evaluate_health` / `write_standards_md` /
  `HEALTH:` line so output matches) and renmark/sizing.py (mirror its tunable-
  constants + never-raise style). Compute the 5 metrics, each with two bands
  (warn/major) as tunable module constants (defaults from the research artifact):
  - module LOC (code lines, exclude blanks/comments/docstrings): 500 / 1000
  - function/method length (LOC): 50 / 100
  - cyclomatic branch count per function (count if/for/while/and/or/except/case/
    comprehension-if ast nodes): 10 / 20
  - import fan-out per module (count import statements): 15 / 25
  - cognitive complexity per function (nesting-WEIGHTED: +1 per branch, +nesting
    level for nested branches): 15 / 30
  FALSE-POSITIVE SUPPRESSION (mandatory): skip files under `tests/`, generated
  markers, and `__init__.py` for the fan-out metric; don't count dataclass/Enum
  field assignments as complexity; count code lines not raw. Public API:
  `analyze(repo: Path|str) -> list[Gap]` (Gap imported/reused from init) — NEVER
  raises; on a per-file SyntaxError/parse failure, SKIP that file and continue.
  Walk only Python source. Module docstring explains the metrics + that findings
  feed init's standards-health (advisory). Full type hints; no third-party import.

### Task 2: wire modularity gaps into init standards-health
- **mode:** B
- **target:** renmark/init.py
- **complexity:** medium
- **executor:** sonnet
- **parallel_group:** 2
- **est_tokens:** 1300
- **est_cost_usd:** 0.03
- **verifier:** python3 -c "import renmark.init" && ruff check renmark/init.py && mypy renmark/init.py && python3 -m pytest tests/test_init_pipeline.py -q
- **serves:** REQ-7
- **spec:**
  Read renmark/init.py (the `evaluate_health` flow + how standards-health `Gap`s
  are collected/rendered/counted) and renmark/modularity.py (Task 1 — `analyze(repo)
  -> list[Gap]`). Wire it in: inside the existing health evaluation, call
  `modularity.analyze(repo)` and MERGE its `Gap`s into the standards-health gap list
  so they render in `dev-standards.md` and count toward the `HEALTH:` stdout line.
  ADDITIVE ONLY — do not change/remove existing standards-health detectors; init
  must still exit 0 (advisory). If existing init tests assert exact gap counts/output,
  update them minimally to account for modularity gaps WITHOUT weakening them
  (or make modularity gaps a clearly-labeled subsection). Keep init zero-LLM.
  Confirm the FULL existing init test suite still passes (verifier runs it).

### Task 3: modularity unit tests
- **mode:** A
- **target:** tests/test_modularity.py
- **complexity:** medium
- **executor:** sonnet
- **parallel_group:** 2
- **est_tokens:** 1700
- **est_cost_usd:** 0.04
- **verifier:** python3 -m pytest tests/test_modularity.py -q
- **serves:** REQ-7
- **spec:**
  Hermetic pytest for `renmark.modularity.analyze` (sonnet per ADR-007 — new test
  file; depends on Task 1). Read renmark/modularity.py + an existing test for fixture
  style; write tiny synthetic .py files into tmp_path. Cover EACH metric at its
  warn/major boundary (a file just over module-LOC; a function just over length; a
  function with > branch-count branches; a module with > fan-out imports; a deeply-
  nested function over cognitive threshold) → a Gap is reported with the right
  severity; and JUST UNDER each threshold → NO gap. FP suppression: a big file under
  `tests/` and an `__init__.py` with many imports → NOT flagged. never-raise: a file
  with a SyntaxError is skipped (no raise) and other files still analyzed. Reference
  the module's threshold CONSTANTS, don't hardcode magic numbers. Do NOT weaken to
  force green — if a metric misbehaves, return FAIL with the reason.

### Task 4: init SKILL note
- **mode:** B
- **target:** plugin/skills/init/SKILL.md
- **complexity:** simple
- **executor:** haiku
- **parallel_group:** 2
- **est_tokens:** 300
- **est_cost_usd:** 0.00
- **verifier:** grep -qi "modularity" plugin/skills/init/SKILL.md
- **serves:** REQ-7
- **spec:**
  Read plugin/skills/init/SKILL.md. Add ONE line to its standards-health / output
  description noting init's health report now also includes ADVISORY
  modularity/scalability gaps (oversized files, long/complex functions, high import
  coupling) — never blocking. Use the literal word "modularity". Do not change other
  behavior; keep it brief.

---

## Cost preview

| Task | Executor | Total tokens (incl. ~10k overhead) | Cost |
|---|---|---|---|
| 1 modularity.py analyzer | opus | 12,600 | $0.189 |
| 2 init wiring | sonnet | 11,300 | $0.0339 |
| 3 modularity tests | sonnet | 11,700 | $0.0351 |
| 4 init SKILL note | haiku | 10,300 | $0.0010 |

**Tasks: 4 (2 parallel groups). Executors: opus×1, sonnet×2, haiku×1.**
**Total tokens: ~46k. Total cost: ~$0.26**
