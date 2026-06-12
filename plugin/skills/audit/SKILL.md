---
name: audit
description: "Use to run a deterministic plugin/registry health audit — composes the lint, modularity, and version-drift checkers and adds registry-sync, shim-thinness, and description-drift passes. Read-only: writes artifacts only under .renmark/audits/, never advances lifecycle.json."
---

# audit

## Overview

`/renmark:audit` is the **deterministic health audit** of the plugin and its
registries. It does not re-implement checks that already ship — it **composes**
them and adds only the passes none cover:

- composed: `lint.lint_all` (frontmatter, shim↔SKILL wiring, next-steps citation,
  template rule-blocks, strict-YAML frontmatter), `modularity.analyze` (5 AST
  code-health metrics, advisory), `release.drift_report` (version-file parity);
- added: **registry-sync** (`lifecycle` dicts vs `plugin/skills/` dirs — ghosts
  + missing both ways), **shim-thinness** (fat or unwired command shims),
  **description-drift** (shim/SKILL descriptions describing different commands).

The deterministic work lives in `renmark/audit.py` (zero LLM). This skill runs
it, relays the bounded result, and adds a thin LLM judgment layer **only when
issues are found**.

## When to Use

- Before a release, to confirm the plugin contract and registries are in sync.
- After landing a new skill, to verify it's wired into every registry.
- Periodically, to catch drift between the lifecycle dicts and the shipped dirs.

## Steps

**Step 0 — Context check.** Call `lifecycle.skill_preamble(repo, 'audit')`. Audit
is `audit` domain; surface the returned hint if non-None (a cross-domain
transition into auditing is worth a `/clear` note).

### 1. Run the engine

```bash
python -m renmark.audit              # full audit (includes modularity)
python -m renmark.audit --quick      # skip modularity (faster)
```

Pass the bounded ≤5-line stdout through to the user **verbatim**. The script
emits per-pass counts, the report + inventory artifact paths, and a
`PASS`/`ISSUES` verdict line. Do not paraphrase or expand — **the format is the
contract** (same discipline as hygiene). Exit 0 = clean, 1 = issues.

### 2. Judgment layer (LLM) — only when issues > 0

If and only if the verdict is `ISSUES`, read the report artifact's `## Summary`
section (via `summary.read_summary_lines`) — **never** the bodies of other
artifacts. Present a prioritized ≤10-line findings digest:

- Lead with registry-sync and version-drift issues (they break routing /
  releases), then lint, then shim/description drift.
- For each, one line: what + where + why it matters.
- End with a single recommendation: **fix now** (small, contained → suggest
  `/renmark:feature`) vs **backlog** (broad → suggest `/renmark:backlog`).

On a `PASS` verdict, skip this step entirely — no digest, no LLM.

### 2b. Adversarial / delta re-runs — route refutation to Fable

When re-running an audit against a prior report's findings (the
"refute each finding" delta-audit pattern, as used for the v0.9.0 delta
audit), refutation subagents SHOULD be dispatched via the Agent tool with
`model: "fable"` — Fable is the designated adversarial-audit tier per REQ-2.
This applies in projects with a declared `top_tier: fable`
(renmark.capabilities); undeclared projects run the same passes on opus.
Each refutation subagent receives one finding plus the relevant file paths,
attempts to refute it against the live tree (read-only), and returns a
bounded confirmed/refuted verdict (≤ 5 lines). This is a routing
recommendation only: the audit remains read-only and artifact-bounded, and
all writes stay inside `.renmark/audits/` — no behavior change beyond where
refutation passes run.

> *Include the reasoning/output-discipline contract from
> `${CLAUDE_PLUGIN_ROOT}/skills/_shared/reasoning-contract.md` in every
> dispatched subagent prompt: multi-perspective decomposition → explicit
> assumptions/edge cases → synthesis; blocking vs deferrable; findings vs
> recommendations; evidence preserved; missing context stated, never guessed.*

### 3. Hand off

audit is an **aux / terminal skill** (class 3 in
`${CLAUDE_PLUGIN_ROOT}/skills/_shared/next-steps.md`). It reports; it never
advances the pipeline.

> *End by calling `renmark.lifecycle.next_steps(repo, "audit")` and render per
> `${CLAUDE_PLUGIN_ROOT}/skills/_shared/next-steps.md` (class 3 — resume-pipeline
> + 1–2 local actions). The in-flight feature's next command is `(Recommended)`;
> add the skill's local follow-ups. Render via `AskUserQuestion`
> (`${CLAUDE_PLUGIN_ROOT}/skills/_shared/handoff-menu.md` rules 6–9); require an
> explicit choice.*

Local follow-ups to offer: `/renmark:inventory` (the inventory-only view), or —
on an `ISSUES` verdict — `/renmark:feature` to fix the top finding. Do not paste
the rendering rules or the gate menu — cite the files.

## Boundaries

- **Read-only.** Never advances `lifecycle.json` stage — audit is diagnostic,
  not a workflow transition.
- **All writes inside `.renmark/audits/`.** The engine writes the report +
  inventory there and nowhere else.
- **Strict-frontmatter pass is ON.** `run_audit` enables
  `include_frontmatter_strict` — the invalid frontmatters were fixed this wave.

## Governance compliance

- **G3 (bounded output)** — Step 1 relays ≤5 lines verbatim; Step 2's digest is
  capped at ≤10 lines and reads only the `## Summary` section, never bodies.
- **G6 (provenance)** — the report + inventory artifacts are written via
  `summary.write_artifact`, so freshness/provenance metadata is automatic.
- audit advances no stage (read-only), so G7/G12 stage rules are N/A.

See `CLAUDE.md` governance rules for definitions.
