---
artifact_type: spec
schema_version: 1
created_at: 2026-06-12T17:00:00+00:00
source_sha: HEAD
generator: brainstorm
related_prd: PRD.md#REQ-5
---

# Spec: CLAUDE/AGENTS doc slimming — terse-rewrite in place

## Context

`plugin/templates/CLAUDE.md.template` is **426 lines** — 328 of them in 23
`BEGIN:/END:` governance rule blocks, the rest (~100) in non-block sections
(Tooling table, File conventions, Executor preferences, project-at-a-glance,
Code conventions, Testing). The template's own line-3 note says "keep under 200
lines," which it now violates 2×. This repo's own `CLAUDE.md` (450 lines) and
`AGENTS.md` (133) carry the same content and load into every session
(~7.2k tokens each turn), so slimming serves REQ-5 (smaller always-loaded docs).

**Approach chosen by the owner:** terse-rewrite in place (not the two-tier
governance-doc split, not block consolidation) — lowest risk, preserves the
merge/registry/audit machinery. **Target: hard ≤200 lines** for each file,
achieved by compressing BOTH the 23 rule blocks AND the non-block sections.

## Goals

- `plugin/templates/CLAUDE.md.template` ≤ 200 lines.
- This repo's `CLAUDE.md` ≤ 200 lines (kept in sync — `merge_rule_blocks` only
  back-fills *missing* blocks, never updates existing ones, so the template and
  the live file would silently diverge if only one is tersed).
- `AGENTS.md.template` (113) and `AGENTS.md` (133): mirror the same terse rule
  prose; already under 200 but must stay consistent with CLAUDE per the
  sync-note discipline (AGENTS has **no** `BEGIN:` markers — plain prose mirror).
- Every governance rule block keeps its **name + `BEGIN:/END:` markers** and its
  **load-bearing clause**; this is a documentation-density change, not a
  rule-semantics change.

## Non-goals (feature-scoped)

- NOT the two-tier stub+governance-doc architecture (deferred; revisit if
  trimming is needed again — see the prior analysis).
- NOT consolidating/renaming/removing any block (that breaks the registry +
  merge + audit + test pins).
- NOT changing any rule's *meaning* or removing any enforcement clause.
- NOT touching the global plugin install or any project but this one.

## Load-bearing clauses that MUST survive the compression (verbatim intent)

- `executor-dispatch-rule`: codex RED-FLAG (never Agent-dispatch codex); fable =
  Agent call w/ `model: "fable"` override, escalation-only; the 2026-06-11
  usage-limit codex→sonnet reroute exception.
- `summary-boundary-rule` / `context-budget-rule`: the ≤5-line / ≤300-token caps
  and the 60%/80% utilization thresholds.
- `task-isolation-rule`: the "receives ONLY / writes ONLY / aggregates ONLY"
  G11 contract (compress prose, keep the three lists).
- `lifecycle-rule`: the canonical stage order + lifecycle.json-vs-pipeline.json
  separation + human-approval-gate fields.
- `artifact-governance-rule`: the provenance metadata field list.
- `project-write-boundary-rule`: never-write-outside-project + the canonical
  artifact-home list (can become a compact list).
- Executor-preferences fable + reasoning-contract + reuse-check pointer lines
  (added this session) — keep the pointers, drop the prose.

## Design

**Rule blocks (23):** each compressed to a 1-3 line directive — keep the
`## Heading`, the `BEGIN:/END:` markers, and the imperative core; cut examples,
rationale paragraphs, and restated context. Target ~6 lines/block incl. markers
+ heading ≈ ~140 lines for all 23.

**Non-block sections → memory pointers** (the detail already lives in memory):
- *Tooling — renmark workflow* table → one line + `see /renmark:help`.
- *Executor preferences* defaults → one line + `see .renmark/memory/routing.md`.
- *Project at a glance* / module tree → keep stack one-liner + `see
  .renmark/memory/project-map.md` (already the pattern).
- *File conventions* → compress to the path list only.
- *Code conventions* / *Testing* → keep the dev-gate one-liner + `see
  .renmark/memory/dev-standards.md`.

**Sync:** CLAUDE.md ↔ AGENTS.md mirror pair (same terse prose where shared);
CLAUDE template ↔ project CLAUDE.md kept identical block content so a future
`merge_rule_blocks` back-fill (missing-only) never reintroduces a verbose block.

## Verification (goal-backward)

- `wc -l` on all four files ≤ 200.
- `python -m renmark.lint` marker validation passes (all 23 blocks well-formed).
- `pytest tests/test_init_pipeline.py tests/test_lint.py` green — the verbatim
  back-fill test reads the template dynamically, so it self-adjusts; confirm.
- `python -m renmark.audit --quick` PASS (template rule-block integrity).
- Full `pytest -q` green; every load-bearing clause above still grep-findable.
- Spot-check: a fresh `merge_rule_blocks` into a stripped CLAUDE.md back-fills
  the terse blocks (not the old verbose ones).

## Prior art & references

Internal: the prior-turn analysis (per-block sizes, the three approaches and
their blast radius). No external research needed — this is a self-contained
documentation refactor of renmark's own governance scaffolding.
