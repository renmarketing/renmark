---
artifact_type: spec
schema_version: 1
created_at: 2026-06-29T00:00:00Z
source_sha: b286cc0
related_plan: null
generator: brainstorm
stale_after: null
dependency_refs:
  - .renmark/research/2026-06-25-external-skills-study.research.md
  - .renmark/plans/2026-06-25-external-skills-p4-p12.program.md
---

# P7 — Template-generated SKILL.md (managed-block generator)

## Context

renmark has 28 plugin SKILL.md files. Each has a unique prose body but shares
cross-cutting boilerplate: the Step-0 `skill_preamble` call, and the
reasoning-contract / next-steps / handoff-menu citation blockquotes. Today a
doctrine change (e.g. editing the canonical reasoning instruction, or the
next-steps rendering rules) means hand-editing up to 26 files — error-prone and
exactly how the v0.20.0 trigger-only / `disable-model-invocation` discipline can
silently drift.

P7 (external-skills study) adds a **managed-block generator**: marker-delimited
regions inside each hand-authored SKILL.md that a generator owns and regenerates
from the `_shared` source of truth, driven by a central per-skill registry. It
reuses renmark's existing marker-merge machinery (`init.py`) and per-skill
metadata (`lifecycle.DOMAIN_BY_SKILL`) rather than inventing new infrastructure.

This is **internal maintainability tooling**, orthogonal to the product PRD
(PRD-alignment verdict: drift-but-benign — the PRD covers user-facing behavior,
not maintainer scaffolding). It is deliberate engineering, not a product change;
no PRD update is required.

## Goals

1. A central per-skill registry (`renmark/skillmeta.py`) — one source of truth
   for each skill's domain, next-steps class, which shared contracts it cites,
   whether it has a hand-off, and `disable_model_invocation`. Absorbs/extends
   `lifecycle.DOMAIN_BY_SKILL` so the preamble, `next_steps`, and the generator
   all read ONE table.
2. A generator (`renmark/skillgen.py`) that renders the managed blocks (Step-0
   preamble call + the cited shared blockquotes, pulled live from the `_shared`
   files) and merges them into each SKILL.md between markers — reusing init.py's
   marker-merge (byte-equality skip, orphan/duplicate/out-of-order guard).
3. A one-time marker migration: wrap the existing boilerplate in each applicable
   SKILL.md with `<!-- BEGIN:gen:<block> -->` / `<!-- END:gen:<block> -->`.
4. A `--check` lint mode (CI) that fails on drift: (a) any managed block differs
   from what the generator would emit, (b) frontmatter discipline broken
   (description not trigger-only, `disable_model_invocation` mismatch vs registry).
5. **Hard guard:** never regress v0.20.0 — the generator NEVER writes frontmatter
   (descriptions/`disable-model-invocation` stay hand-authored); the lint only
   *validates* frontmatter. Generation is confined to the marked body regions.

## Non-goals (feature-scoped)

- **Full-file generation** — bodies stay hand-authored; the generator never emits
  a whole SKILL.md or encodes the 28 unique prose bodies as data.
- **Generating frontmatter** — descriptions and `disable-model-invocation` are
  hand-authored; the registry's `disable_model_invocation` flag is used for
  *lint validation only*, not injection (rejected the broader scope to protect
  the sensitive v0.20.0 frontmatter).
- **A product-PRD change** — internal tooling; tracked as engineering, not product.
- **P8** (behavioral skill testing + LLM-judge eval) — separate proposal.

## The decisions (owner-confirmed, brainstorm 2026-06-29)

1. **Generation model: managed blocks.** Marker-delimited regions the generator
   owns inside hand-authored files; reuse init.py's marker-merge. (Rejected:
   full-file generation — too large a migration, high regression risk on rich
   bodies; lint-only — no auto-propagation of doctrine changes.)
2. **Block scope: Step-0 preamble + the 3 shared citations** (reasoning-contract,
   next-steps, handoff-menu), pulled from the `_shared` source. Frontmatter stays
   hand-authored, enforced by lint. (Rejected: also generating frontmatter — touches
   v0.20.0 directly; verbatim-only — too little payoff.)
3. **Per-skill data: central registry**, extending `lifecycle.DOMAIN_BY_SKILL`
   into a fuller table read by generator + preamble + `next_steps`. (Rejected:
   28 per-skill manifest files — second source vs the existing map; inference from
   existing SKILL.md — fragile, no declarative source of truth.)

## Architecture

```
renmark/skillmeta.py            # NEW — central per-skill registry (source of truth)
  @dataclass SkillMeta: domain, next_steps_class (1|2|3),
       cites: list[str] (subset of {"reasoning-contract","next-steps","handoff-menu"}),
       has_handoff: bool, disable_model_invocation: bool
  SKILLS: dict[str, SkillMeta]  # all 28 skills
  # lifecycle.DOMAIN_BY_SKILL absorbed: lifecycle.domain_for_skill() now reads
  # skillmeta (re-export / thin shim for back-compat; existing tests stay green).

renmark/skillgen.py             # NEW — the generator
  BEGIN/END marker convention reused from init.py: "<!-- BEGIN:gen:<block> -->"
  render_block(skill, block)    # pulls canonical text from the _shared file for
                                #   that block, parameterized by SkillMeta
  merge_skill(path, meta)       # marker-merge the rendered blocks into one SKILL.md
                                #   (byte-equality skip; orphan/dup/out-of-order guard
                                #    via the shared marker helpers)
  main(argv)                    # CLI: --check (lint, zero writes, exit 1 on drift)
                                #      --write (regenerate; default dry-run summary)

renmark/init.py                 # reuse: factor the marker-merge primitive
  (_count_begin_markers / merge_stub_into) into a shared helper skillgen imports —
  do NOT duplicate marker logic.

plugin/skills/*/SKILL.md        # one-time migration: wrap existing boilerplate in
  <!-- BEGIN:gen:preamble -->…<!-- END:gen:preamble --> and one region per cited
  block. Bodies + frontmatter untouched.

tests/test_skillgen.py          # generator + marker-merge + --check drift
tests/test_skillmeta.py         # registry completeness (all 28 present) + back-compat
```

## Data flow

1. `skillgen --check` (CI / pre-commit): for each skill in `SKILLS`, render the
   managed blocks from the `_shared` source + SkillMeta, compare byte-for-byte to
   the marked regions in the file; also validate frontmatter (trigger-only
   description, `disable_model_invocation` matches registry). Any mismatch →
   list the drifting files, exit 1. Zero writes.
2. `skillgen --write`: same render, but marker-merge the regions in place
   (byte-equality skip — unchanged files not rewritten, mirroring init.py).
3. A doctrine change (edit a `_shared` blockquote) → run `skillgen --write` →
   every citing skill's marked region refreshes from the one source.
4. The preamble and `next_steps` read `skillmeta.SKILLS` for domain/class instead
   of the old `DOMAIN_BY_SKILL` literal (single source).

## Error handling / edge cases

- **Malformed markers** (orphan/duplicate/out-of-order BEGIN/END) → refuse to
  write that file, report it, exit non-zero — reuse init.py's existing guard.
- **Skill missing from registry** → `--check` fails (registry must be complete);
  generator skips unknown files rather than guessing.
- **A skill that cites nothing / has no hand-off** (e.g. zero-LLM `help`) → its
  SkillMeta has `cites=[]`, `has_handoff=False`; generator emits only what applies
  (likely just nothing or a minimal preamble) — never forces a block on.
- **Frontmatter never written** by the generator; if lint finds a frontmatter
  violation it reports but does not auto-fix (hand-authored discipline).
- **Byte-equality skip** keeps a no-op `--write` from churning 28 files.

## Success criteria

1. `renmark/skillmeta.py` exists with a complete `SKILLS` table (all 28); the
   preamble + `next_steps` read it; `lifecycle.domain_for_skill` still returns the
   same domains (back-compat test green).
2. `renmark/skillgen.py` renders the 4 block types from the `_shared` source and
   marker-merges them; marker logic is shared with init.py (not duplicated).
3. All applicable SKILL.md files carry the `<!-- BEGIN:gen:* -->` markers and a
   fresh `--write` is a no-op (byte-equality) immediately after migration.
4. `skillgen --check` passes on the migrated tree, and FAILS when a `_shared`
   blockquote is edited without regenerating, OR when a description is made
   non-trigger-only, OR when `disable_model_invocation` drifts from the registry.
5. **No v0.20.0 regression:** descriptions stay trigger-only and
   `disable-model-invocation` frontmatter is unchanged after a full regenerate
   (a test asserts frontmatter byte-identical across `--write`).
6. `pytest -q`, `ruff check`, `mypy .` green; `renmark:audit` still PASS.

## Prior art & references

- External-skills study: `.renmark/research/2026-06-25-external-skills-study.research.md` (P7 entry).
- Internal reuse (extend, don't rebuild): `renmark/init.py` marker-merge
  (`merge_stub_into`, `_count_begin_markers`, `<!-- BEGIN:<name> -->` convention);
  `renmark/lifecycle.py` `DOMAIN_BY_SKILL` (:108) + `domain_for_skill` (:599);
  the `_shared` source files (`reasoning-contract.md`, `next-steps.md`,
  `handoff-menu.md`) as the canonical blockquote text.
- v0.20.0 trigger-only + `disable-model-invocation` discipline is the load-bearing
  invariant this generator must preserve (lint enforces).
- Program plan: `.renmark/plans/2026-06-25-external-skills-p4-p12.program.md`.
