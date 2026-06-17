---
artifact_type: audit
schema_version: 1
created_at: 2026-06-14T02:36:18+00:00
source_sha: dc0ae63ba38318e3ff08a7c6cb3c29c1845f4a05
related_plan: null
generator: renmark-audit
stale_after: null
dependency_refs: []
completion_state: complete
confidence: high
validation_status: validated
retry_count: 0
parser_success: true
schema_compliance: true
---

# renmark command inventory

| command | domain | class | shim lines | skill lines | description |
|---|---|---|---|---|---|
| analytics | meta | aux | 2 | 74 | Use when you need a bounded project build-health summary — typed as /renmark:ana… |
| approve | meta | aux | 2 | 140 | Use to clear a pending human-approval gate — `/renmark:approve` is the ONLY surf… |
| audit | audit | aux | 2 | 118 | Use to run a deterministic plugin/registry health audit — composes the lint, mod… |
| backlog | build | aux | 2 | 227 | Use to triage and approve backlog items — `/renmark:backlog` opens an interactiv… |
| blueprint | build | pipeline | 2 | 176 | Use when the user wants a visual blueprint of the project — typed as /renmark:bl… |
| brainstorm | build | pipeline | 2 | 211 | Use when the user wants to flesh out an idea into a concrete spec — typed as /re… |
| check-plan | build | pipeline | 2 | 102 | Use before executing a renmark plan — deterministic validation via renmark.plan_… |
| codereview | debug | gate | 2 | 329 | Use when the user wants a diff or PR reviewed — typed as /renmark:codereview or … |
| debug | debug | aux | 2 | 123 | Use when the user reports a bug or unexpected behavior — typed as /renmark:debug… |
| doctor | meta | aux | 2 | 125 | Use when `/renmark:*` commands aren't appearing, the plugin seems broken, or the… |
| feature | build | pipeline | 2 | 253 | Use to start a new feature or significant change with branch isolation — typed a… |
| finish | build | pipeline | 2 | 355 | Use when implementation is complete — re-runs verifiers, shows commit summary, t… |
| help | meta | aux | 2 | 183 | Use when the user types /renmark:help or asks \"what can renmark do\", \"list re… |
| hygiene | meta | aux | 2 | 75 | Use to garbage-collect stale renmark artifacts and prune append-only memory logs… |
| init | meta | aux | 2 | 184 | Use when the user wants renmark to onboard or document a project — the non-destr… |
| inventory | audit | aux | 2 | 67 | Use to harvest a flat inventory of every renmark command and skill — name, domai… |
| loop | build | pipeline | 2 | 275 | Use to run a bounded agentic loop — `/renmark:loop` or "loop on this until it pa… |
| orchestrate | build | pipeline | 2 | 323 | Use to execute a renmark plan — `/renmark:orchestrate` or "execute the plan", "b… |
| plan | build | pipeline | 2 | 244 | Use when the user has a spec and wants it decomposed into an executable task lis… |
| prd | build | pipeline | 2 | 182 | Use to create or update the project's PRD (Product Requirements Document) — the … |
| resume | meta | aux | 2 | 216 | Use after `/clear` or `/compact`, or at the start of a fresh session, to discove… |
| roadmap | meta | aux | 2 | 170 | Use when the user wants a status report on what renmark has built in this projec… |
| setup | meta | aux | 2 | 59 | Thin alias — /renmark:setup refreshes/back-fills renmark rule blocks in an exist… |
| start | build | pipeline | 2 | 220 | Use when a vibe coder wants to build something and doesn't know where to begin —… |
| usage | meta | aux | 2 | 85 | Use when the user wants observed local usage status — typed as /renmark:usage, "… |
| verify | build | gate | 6 | 583 | Use after `/renmark:orchestrate` completes — three modes selected by flag. Defau… |

## Summary

- 26 commands harvested from plugin/commands/*.md
- 26 have a backing SKILL.md, 0 missing
- domains: audit=2, build=12, debug=2, meta=10
- classes: aux=14, gate=2, pipeline=10
