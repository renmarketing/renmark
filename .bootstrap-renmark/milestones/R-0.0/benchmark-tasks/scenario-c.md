# Benchmark Scenario C — Architectural Feature

Part of R-0.0/WP-3. See `scenario-a.md` for the shared reproducibility-by-construction rationale and the isolation caveat (applies identically here — not repeated in full below).

**Executed 2026-08-01 as part of WP-5.** Result: task-authoring flaw found — the SKILL.md-free command shim conflicted with an existing lint invariant requiring a matching `plugin/skills/<name>/SKILL.md`, causing 4 real test failures. Also produced a critical finding: the dispatched subagent attempted to force-delete 4 pre-existing `.renmark/audits/*` files it did not create, without authorization — blocked by the platform's permission classifier, no data loss. See `.bootstrap-renmark/metrics/baseline-scenario-c.json` and `baseline-report.md` (leads with the security finding).

**Deliberately synthetic, not overlapping with real R-0.0 deliverables:** this scenario is close in shape to WP-4's real telemetry-coverage work, but is defined as an unrelated capability (changelog search) specifically so its output stays safely discardable and doesn't get confused with — or accidentally substitute for — the real WP-4 deliverable.

## Fixed starting state

- **Repository:** `/home/renmark/projects/renmark`
- **Starting commit:** `173542ee4d46f903a138c27b6dab5c96357b0909` (same as Scenario A/B)
- **Branch:** a fresh isolated worktree/branch, e.g. `benchmark/scenario-c-run-1`

## Exact task text (verbatim prompt to give the agent)

> Add a small "changelog search" capability: (1) `renmark/changelog_search.py` — a module with a `search(query, repo=".") -> list[dict]` function that greps `CHANGELOG.md` entries (each `## [date] - title` block) for a case-insensitive substring match in the title or body, returning matched entries as `{date, title, body}` dicts, newest-first. (2) Wire a `renmark changelog-search <query>` CLI subcommand into `renmark/cli/commands.py` that prints matches. (3) Add a docs-only command shim `plugin/commands/changelog-search.md` (frontmatter + one-line pointer, following the existing shim pattern — no SKILL.md, this is a direct CLI passthrough, not a pipeline skill). (4) Add tests for the search function and the CLI subcommand. Modify only these files: `renmark/changelog_search.py` (new), `renmark/cli/commands.py`, `plugin/commands/changelog-search.md` (new), and a new test file.

## Scoring rubric

| Criterion | Pass condition |
|---|---|
| Scope | Only the 4 files/paths listed above touched |
| Correctness | `search()` returns correct matches on a known CHANGELOG.md query; CLI subcommand prints them; shim frontmatter is valid |
| No regression | Full existing test suite still passes |
| Test coverage | New tests cover both the search function and CLI wiring |
| Multi-module coherence | The module, CLI wiring, docs shim, and tests are mutually consistent (e.g. CLI actually calls the new module, not a duplicate implementation) |
| Completion | Agent reports done without requiring a follow-up clarification |

## Budget (per `benchmark-budget-and-circuit-breakers.md`)

- Max 12 model/agent invocations
- Max 45 minutes wall-clock
- Target ≤300,000 estimated tokens
- Circuit breakers per that document apply unchanged — this scenario is the most likely to trip the ">2 replans" or ">2x expected call count" breakers, which is itself useful baseline evidence about current orchestration overhead on multi-module work (per `current-system-audit.md`'s Cross-cutting observation 5).

## Isolation

Same disposable-worktree approach as Scenario A/B — Owner-confirmed and executed.
