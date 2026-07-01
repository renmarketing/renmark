---
artifact_type: plan
schema_version: 1
created_at: 2026-06-29T00:00:00Z
source_sha: b286cc0
related_plan: null
generator: plan
dependency_refs:
  - .renmark/specs/2026-06-29-p7-skill-templates.spec.md
---

# Plan — P7 template-generated SKILL.md (managed-block generator)

Implements the P7 spec (`.renmark/specs/2026-06-29-p7-skill-templates.spec.md`,
ADR-037): a central per-skill registry, a managed-block generator reusing init.py's
marker-merge, a one-time SKILL.md marker migration, and a `--check` lint.

**Do-not-change guards (owner-locked):** the generator MUST NEVER write frontmatter
(v0.20.0 trigger-only descriptions + `disable-model-invocation` are load-bearing —
lint validates only); managed blocks pull canonical text from the `_shared` source;
marker logic is SHARED with init.py, never duplicated.

**Routing note:** test tasks routed to `sonnet`, not codex — this session's learned
routing (`.renmark/memory/routing.md`) shows codex's exec sandbox cannot run pytest
verifiers (exit 127, no writable /tmp). Ledgered, not silent.

### Task 1: skillmeta registry
- **mode:** A
- **target:** renmark/skillmeta.py
- **complexity:** medium
- **executor:** sonnet
- **parallel_group:** 1
- **est_tokens:** 1200
- **est_cost_usd:** 0.04
- **verifier:** `python3 -c "from renmark.skillmeta import SKILLS, SkillMeta; import os,glob; n=len(glob.glob('plugin/skills/*/SKILL.md')); assert len(SKILLS)>=n-1, (len(SKILLS),n); assert all(hasattr(m,'cites') for m in SKILLS.values())"`
- **serves:** P7
- **spec:**
  New module: the single source of truth for per-skill metadata. Define
  `@dataclass(frozen=True) SkillMeta` with: `domain: str`, `next_steps_class: int`
  (1|2|3), `cites: tuple[str,...]` (subset of `"reasoning-contract"`,`"next-steps"`,
  `"handoff-menu"`), `has_handoff: bool`, `disable_model_invocation: bool`. Build
  `SKILLS: dict[str, SkillMeta]` covering every skill in `plugin/skills/*/SKILL.md`.
  To populate accurately, READ each SKILL.md: derive `domain` from the existing
  `lifecycle.DOMAIN_BY_SKILL` (import it as the seed — do NOT contradict it),
  `cites` from which `_shared` files it currently references, `disable_model_invocation`
  from its frontmatter, `next_steps_class` from its next-steps citation (default 1
  for pipeline skills). stdlib-only, never raises on lookup (`.get`). This is the
  table the generator + preamble + next_steps will read.

### Task 2: extract shared marker-merge helper in init.py
- **mode:** B
- **target:** renmark/init.py
- **complexity:** hard
- **executor:** opus
- **parallel_group:** 1
- **est_tokens:** 900
- **est_cost_usd:** 0.16
- **verifier:** `python3 -m pytest -q tests/test_init_pipeline.py >/dev/null 2>&1 && python3 -c "from renmark import init; assert hasattr(init,'merge_marked_block') and hasattr(init,'count_begin_markers')"`
- **serves:** P7
- **spec:**
  init.py already has marker-merge logic (`_count_begin_markers`, `merge_stub_into`,
  the `<!-- BEGIN:<name> -->`/`<!-- END:<name> -->` convention with orphan/duplicate/
  out-of-order detection). Extract a GENERAL, reusable primitive
  `merge_marked_block(text, marker_name, new_body) -> str` (and expose
  `count_begin_markers`) that skillgen can import — same guard semantics (refuse on
  malformed markers, byte-equality skip). Refactor `merge_stub_into` to call the new
  primitive so behavior is unchanged. CORRECTNESS-CRITICAL: existing `tests/test_init.py`
  MUST stay green (init scaffolding is load-bearing). Do not change the public init CLI.

### Task 3: skillgen generator
- **mode:** A
- **target:** renmark/skillgen.py
- **complexity:** hard
- **executor:** opus
- **parallel_group:** 2
- **est_tokens:** 1600
- **est_cost_usd:** 0.17
- **verifier:** `python3 -c "from renmark import skillgen; assert hasattr(skillgen,'render_block') and hasattr(skillgen,'merge_skill') and hasattr(skillgen,'main')"`
- **serves:** P7
- **spec:**
  New module: the generator. Imports `skillmeta.SKILLS` and init's
  `merge_marked_block`/`count_begin_markers` (Task 2). Functions:
  - `render_block(skill, block) -> str` — for a block in {"preamble","reasoning-contract",
    "next-steps","handoff-menu"}, produce the canonical text by reading the relevant
    `_shared` source file (NEVER hardcode the blockquote text — pull it live), parameterized
    by the skill's `SkillMeta` (e.g. class for next-steps). The preamble block renders the
    Step-0 `skill_preamble(repo, '<skill>')` call.
  - `merge_skill(path, meta, *, write) -> tuple[str, bool]` — marker-merge each cited block
    into the SKILL.md between `<!-- BEGIN:gen:<block> -->`/`<!-- END:gen:<block> -->`
    using Task 2's primitive; byte-equality skip; NEVER touch frontmatter or text outside
    the markers. Returns (new_text, changed).
  - `main(argv)` — CLI: `--check` (no writes; exit 1 listing any drifting file or
    frontmatter-discipline violation: description not trigger-only, `disable_model_invocation`
    ≠ registry), `--write` (apply; dry-run summary by default). Frontmatter is READ for
    lint, NEVER written. Never raises uncaught.

### Task 4: lifecycle.domain_for_skill reads skillmeta
- **mode:** B
- **target:** renmark/lifecycle.py
- **complexity:** medium
- **executor:** sonnet
- **parallel_group:** 2
- **est_tokens:** 450
- **est_cost_usd:** 0.03
- **verifier:** `python3 -m pytest -q tests/test_lifecycle.py >/dev/null 2>&1 && python3 -c "from renmark import lifecycle; assert lifecycle.domain_for_skill('finish') in {'build','debug','audit','meta'}"`
- **serves:** P7
- **spec:**
  Make `domain_for_skill` (and any `DOMAIN_BY_SKILL` consumer) read from
  `skillmeta.SKILLS[...].domain`, with `DOMAIN_BY_SKILL` kept as a thin
  back-compat alias derived from skillmeta (or re-exported) so existing imports +
  `tests/test_lifecycle.py` stay green and domains are unchanged. Single source of
  truth = skillmeta. Do NOT change the P3 skill_preamble ordering.

### Task 5: marker migration across SKILL.md
- **mode:** B
- **target:** plugin/skills
- **complexity:** medium
- **executor:** sonnet
- **parallel_group:** 3
- **est_tokens:** 1400
- **est_cost_usd:** 0.04
- **verifier:** `python3 -m renmark.skillgen --check >/dev/null 2>&1 && echo OK`
- **serves:** P7
- **spec:**
  One-time migration (bulk, mechanical): for each applicable `plugin/skills/*/SKILL.md`,
  insert `<!-- BEGIN:gen:<block> -->`/`<!-- END:gen:<block> -->` markers around the
  existing Step-0 preamble + cited shared blockquotes, then run `python3 -m renmark.skillgen
  --write` so the marked regions match the generator output. **Do NOT alter frontmatter or
  any prose outside the inserted markers** — diff each file to confirm only the boilerplate
  regions changed. After migration, `python3 -m renmark.skillgen --check` MUST exit 0 and the
  frontmatter of every file MUST be byte-identical to before. Depends on Task 3.

### Task 6: tests for skillmeta
- **mode:** A
- **target:** tests/test_skillmeta.py
- **complexity:** medium
- **executor:** sonnet
- **parallel_group:** 3
- **est_tokens:** 700
- **est_cost_usd:** 0.03
- **verifier:** `python3 -m pytest -q tests/test_skillmeta.py`
- **serves:** P7
- **spec:**
  Tests: every skill under `plugin/skills/*/SKILL.md` has a `SKILLS` entry; each
  `SkillMeta` has valid `next_steps_class` (1-3), `cites` ⊆ the allowed set, `domain`
  in the known domain set; `disable_model_invocation` matches the actual frontmatter of
  each SKILL.md (this is the lint contract); `lifecycle.domain_for_skill` agrees with
  `skillmeta` for a sample. Match existing test style (pathlib, parametrize).

### Task 7: tests for skillgen
- **mode:** A
- **target:** tests/test_skillgen.py
- **complexity:** hard
- **executor:** sonnet
- **parallel_group:** 4
- **est_tokens:** 1000
- **est_cost_usd:** 0.03
- **verifier:** `python3 -m pytest -q tests/test_skillgen.py`
- **serves:** P7
- **spec:**
  Tests: `render_block` pulls text from the `_shared` source (edit a temp copy → output
  changes); `merge_skill` is idempotent (second write is a no-op / byte-equality);
  marker-merge refuses malformed markers; `--check` exits 0 on the migrated tree and
  NON-zero when (a) a `_shared` block is changed without regenerating, (b) a description
  is made non-trigger-only, (c) `disable_model_invocation` drifts from the registry;
  **frontmatter is byte-identical before/after `--write`** (the v0.20.0 guard). Depends on
  Tasks 3 + 5 (run against the migrated tree). Use tmp copies for the mutate-and-detect cases.

---

## Cost preview

| Task | Executor | Tokens (+overhead) | Cost |
|---|---|---|---|
| 1 skillmeta.py | sonnet | 1200 + 10k | $0.034 |
| 2 init.py marker helper | opus | 900 + 10k | $0.164 |
| 3 skillgen.py | opus | 1600 + 10k | $0.174 |
| 4 lifecycle shim | sonnet | 450 + 10k | $0.031 |
| 5 SKILL.md migration | sonnet | 1400 + 10k | $0.034 |
| 6 test_skillmeta.py | sonnet | 700 + 10k | $0.032 |
| 7 test_skillgen.py | sonnet | 1000 + 10k | $0.033 |

**Total: ~$0.50** — 7 tasks, 4 waves (1: T1,T2 · 2: T3,T4 · 3: T5,T6 · 4: T7).
Executors: sonnet×5, opus×2. (Tests on sonnet per learned codex-verifier-env limitation.)
