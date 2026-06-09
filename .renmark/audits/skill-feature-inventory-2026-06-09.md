---
artifact_type: audit
schema_version: 1
created_at: 2026-06-09T17:17:52-04:00
source_sha: 9a050a8
related_plan: .renmark/audits/skill-feature-inventory-spec.md
generator: claude-fable-5 (orchestrator + 8 parallel read-only subagents)
dependency_refs:
  - .renmark/audits/skill-feature-inventory-spec.md
completion_state: complete
confidence: high
validation_status: unvalidated
---

# Skill-feature inventory — 23 commands · 2026-06-09

READ-ONLY audit at `9a050a8` (plugin version **0.7.8** — all 7 version locations agree).
Ground truth: `plugin/commands/*.md` ↔ `plugin/skills/*/SKILL.md` are in **perfect 1:1
parity (23/23)** — the only fully-correct registration surface in the repo.
Machine-readable mirror: `skill-feature-inventory-2026-06-09.json`.

**Category counts:** build 8 · governance 3 · reporting 3 · meta 4 · recovery 2 · aux 2 · terminal 1.

## Capability matrix

| command | cat | code | commit | merge | release | del-branch | agents | codex | human gate | stages advanced |
|---|---|---|---|---|---|---|---|---|---|---|
| start | build | – | – | – | – | – | – | – | yes (confirm) | none (reads) |
| brainstorm | build | scaffold | scaffold | – | – | – | yes | – | yes | brainstorm-complete |
| prd | governance | – | – | – | – | – | – | – | yes (load-bearing) | none (gate fields) |
| blueprint | aux | – | – | – | – | – | – | – | partial | none (artifact ptr) |
| plan | build | – | – | – | – | – | – | – | yes (dispatch gate) | plan-drafted, plan-validated |
| check-plan | build | – | – | – | – | – | – | – | partial | plan-validated |
| orchestrate | build | via agents | per task | – | – | – | yes | yes | yes (cost gate) | created |
| verify | build | – | – | – | – | – | – | – | partial | verified |
| feature | build | – | – | – | – | – | yes | indirect | yes (single gate) | init (reset) |
| finish | terminal | – | doc-map | **yes** [m] | **yes** [r] | **yes** -d | – | – | yes | ready-to-release |
| resume | recovery | – | – | – | – | – | – | – | no (read-only) | none |
| loop | build | indirect | per iter | – (REQ-12) | – | – | yes | indirect | yes (one upfront) | none (loop.json) |
| backlog | governance | indirect | indirect | **yes** §3b | – | **yes** -d/-D | yes | indirect | yes (+ approve) | none |
| debug | aux | fix step | – | – | – | – | yes | yes | partial | none |
| codereview | governance | – | – | – | – | – | – | yes | yes | none |
| doctor | recovery | – | – | – | – | – | – | – | yes (--fix) | none |
| hygiene | meta | – | – | – | – | – | – | – | yes (--apply) | none |
| init | meta | docs | – | – | – | – | – | – | partial | none |
| setup | meta | docs | – | – | – | – | – | – | no | none |
| help | meta | – | – | – | – | – | – | – | no | none |
| roadmap | reporting | – | – | – | – | – | --gaps only | – | partial | none |
| usage | reporting | – | – | – | – | – | – | – | no | none |
| analytics | reporting | – | – | – | – | – | – | – | no | none |

## Registration / docs-sync status per skill

| command | shim thin? | preamble | docs sync | tests |
|---|---|---|---|---|
| start | yes | pointer | OK | none specific |
| brainstorm | yes | pointer | minor: hardcoded `~/.claude/plugins/renmark/templates/` (should be `${CLAUDE_PLUGIN_ROOT}`) | indirect |
| prd | yes | pointer | OK | partial (gate fields) |
| blueprint | yes | pointer | **shim description stale** (PRD-flavored, predates schematic design) | test_blueprint.py ✓ |
| plan | yes | pointer | table omits absorbed check-plan | test_parser, test_sizing |
| check-plan | yes | pointer | OK | **none for the 8 checks** (no Python backing) |
| orchestrate | yes | pointer | OK (exact) | best-covered skill (8 files) |
| verify | mostly (mode-parse in shim) | pointer | CLAUDE.md understates QA modes | test_qa_flows, test_verifier |
| feature | yes | pointer | **missing from root tooling table** | test_sizing, test_lifecycle |
| finish | yes | pointer | table understates release/analytics ownership | release/reports tests ✓ |
| resume | yes | pointer | absent from tooling table | cold-start integration ✓ |
| loop | yes — **`--verifier` vs `--verify` flag drift** | pointer | **absent from ALL root doc tables** | test_loop.py (472 lines) ✓ |
| backlog | yes | pointer | OK | test_backlog.py ✓ |
| debug | yes | pointer | OK | test_debug.py ✓ |
| codereview | yes | pointer | **stale ×2**: shim + CLAUDE.md still say "multi-pass"; SKILL removed it | sizing/gate only — review flow untested |
| doctor | yes | **none** (undocumented; defensible) | not in tooling table; **missing from DOMAIN_BY_SKILL** | **ZERO tests** |
| hygiene | yes | pointer | not in tooling table; `AUX_LOCAL_ACTIONS` offers `--fix` but real flag is `--apply` | test_hygiene.py ✓ |
| init | yes | pointer | **shim stale** (pre-front-door); not in tooling table; missing from DOMAIN_BY_SKILL | test_init_pipeline.py ✓ |
| setup | yes | pointer | **shim stale** (advertises old full-scaffold) | indirect via init |
| help | yes | none (by design) | **worst drift: lists 10/23 commands, "v0.0.x", shim says "all six"** | lint only |
| roadmap | yes | **MISSING Step 0** (only registered skill that skips it) | absent from tooling table; "Zero LLM calls" false for --gaps | test_roadmap.py ✓ |
| usage | yes | pointer | **unregistered everywhere** (CLAUDE.md, DOMAIN_BY_SKILL, IMPLEMENTED_SKILLS) | test_usage.py — only skill with disclaimer + no-raw enforced |
| analytics | yes | pointer | **unregistered everywhere**; SKILL claims sources Python doesn't read; omits its own summary.json write | test_reports_analytics.py ✓ |

## One-sentence-purpose test (skills needing an "and")

- **verify** — 3 modes is one job, but `--bootstrap` (seeds qa-flows.md, verifies nothing) is a second job riding a flag.
- **finish** — close branch AND own release packaging AND record reports+analytics; most overloaded skill (309 lines). `NEXT_BY_STAGE_PLANNED` already reserves `/renmark:release`.
- **roadmap** — status table AND `--gaps` discovery are two modes.
- **init** — scaffold AND back-fill AND map AND standards-health; acceptable because one deterministic Python command serves all.
- **start** — interview AND route; acceptable for a funnel entry.
- **hygiene / brainstorm / plan / backlog / doctor** — mild "and"s, each defensible.
- Clean single-purpose: prd, blueprint, check-plan, orchestrate, feature, resume, loop, debug, codereview, setup, help, usage, analytics.

## UX verdicts (dimension 12)

| verdict | skills |
|---|---|
| keep-separate | start, brainstorm, prd, plan, orchestrate, verify, feature, finish, resume, backlog, debug, doctor, hygiene, roadmap, usage, analytics |
| document-better | blueprint, codereview, init, setup, help, loop (all = stale shim/table/help text, not structural problems) |
| make-internal | check-plan (auto-run by both callers; keep manual path, demote from user-facing table) |
| split-candidate (later) | finish→release sub-flow; verify→`--bootstrap` |
| fold/rename/deprecate | none warranted |

## Pre-finding confirmations

1. **CONFIRMED:** `/renmark:hygiene` is a stale-artifact GC + memory-log pruner (scans only
   `.renmark/{specs,plans,reviews,research,state/wave-summaries}` per `_ARTIFACT_SUBDIRS`,
   prunes `learnings/bugs/features.md` per `_MEMORY_LOGS`). A skill-feature inventory did
   not exist before this audit.
2. **CONFIRMED + EXPANDED:** docs→code ghost drift is far wider than secure/document/map/research —
   see `modularity-scorecard-2026-06-09.md` §registry-drift and `recommended-cleanup-backlog-2026-06-09.md`.
