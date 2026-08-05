---
artifact_type: audit
schema_version: 1
created_at: 2026-08-05T04:45:23+00:00
source_sha: 91d454ad11ceb265e9790e406666e05612378ecc
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
| analytics | meta | aux | 2 | 75 | Use when the user wants a project build-health summary — typed as /renmark:analy… |
| approve | meta | aux | 2 | 143 | Use to clear a pending human-approval gate — typed as /renmark:approve or \"appr… |
| audit | audit | aux | 2 | 119 | Use to run a deterministic plugin/registry health audit — typed as /renmark:audi… |
| backlog | build | aux | 2 | 231 | Use when the user wants to review or act on tracked work items — typed as `/renm… |
| blueprint | build | pipeline | 2 | 176 | Use when the user wants a visual blueprint of the project — typed as /renmark:bl… |
| brainstorm | build | pipeline | 2 | 211 | Use when the user wants to flesh out a rough idea into a concrete spec — typed a… |
| check-plan | build | pipeline | 2 | 105 | Use before executing a renmark plan to validate it — typed as /renmark:check-pla… |
| codereview | debug | gate | 2 | 380 | Use when the user wants a diff or PR reviewed — typed as /renmark:codereview or … |
| debug | debug | aux | 2 | 161 | Use for the Debug pipeline (/renmark:debug) when something is broken — plain req… |
| doctor | meta | aux | 2 | 181 | Use when /renmark:* commands aren't appearing, the plugin seems broken, or the u… |
| eval | build | aux | 2 | 183 | Use to run the in-session, agent-driven eval path — record golden transcripts or… |
| feature | build | pipeline | 2 | 331 | Use for the Feature pipeline (/renmark:feature) when adding to or changing an ex… |
| finish | build | pipeline | 2 | 528 | Use for the Ship / Readiness pipeline (/renmark:finish) when implementation is d… |
| guide | meta | aux | 2 | 82 | Use when the user types /renmark:guide or says \"I don't know which command to u… |
| heartbeat | meta | aux | 2 | 90 | Use to monitor or schedule recovery when a renmark run is paused by a usage limi… |
| help | meta | aux | 2 | 201 | Use when the user types /renmark:help or asks \"what can renmark do\", \"list re… |
| hygiene | meta | aux | 2 | 76 | Use to garbage-collect stale renmark artifacts and prune append-only memory logs… |
| init | meta | aux | 2 | 251 | Use for the Project Setup pipeline (/renmark:init) to adopt renmark into a repo … |
| inventory | audit | aux | 2 | 68 | Use to harvest a flat inventory of every renmark command and skill — typed as /r… |
| loop | build | pipeline | 2 | 275 | Use when the user wants a bounded agentic loop toward a verifier — typed as /ren… |
| orchestrate | build | pipeline | 2 | 474 | Use to execute a renmark plan — `/renmark:orchestrate` or \"execute the plan\", … |
| plan | build | pipeline | 2 | 291 | Use when the user has a spec and wants it decomposed into an executable task lis… |
| prd | build | pipeline | 2 | 195 | Use when the user wants to author or maintain the project's Product Requirements… |
| resume | meta | aux | 2 | 276 | Use after /clear or /compact, or at the start of a fresh session, to discover wh… |
| rethink | build | pipeline | 2 | 584 | Use for the Brownfield Modernization pipeline (/renmark:rethink) when reassessin… |
| roadmap | meta | aux | 2 | 271 | Use for the Maintenance / Gap pipeline (/renmark:roadmap) to see status and deci… |
| scan | audit | aux | 2 | 168 | Use to run the read-only QA proposer lane — typed as /renmark:scan (--propose to… |
| setup | meta | aux | 2 | 59 | Use /renmark:setup to refresh or back-fill renmark's rule blocks in a project th… |
| start | build | pipeline | 2 | 590 | Use for the New Build pipeline (/renmark:start) when starting something new from… |
| usage | meta | aux | 2 | 86 | Use when the user wants observed local usage status — typed as /renmark:usage or… |
| verify | build | gate | 6 | 592 | Use after a build or `/renmark:orchestrate` to confirm it works — the post-build… |

## Summary

- 31 commands harvested from plugin/commands/*.md
- 31 have a backing SKILL.md, 0 missing
- domains: audit=3, build=14, debug=2, meta=12
- classes: aux=18, gate=2, pipeline=11
