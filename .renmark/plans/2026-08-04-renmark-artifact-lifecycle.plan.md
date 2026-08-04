# Plan: `.renmark/` artifact-lifecycle hygiene

Implements `.renmark/rethink/artifact-lifecycle/implementation-proposal.md`
(Phase 3 of the scoped rethink run on Renmark's own `.renmark/` subsystem —
see `survey.md` and `lifecycle-contract.md` in the same directory for full
rationale). Extends existing machinery only — `renmark/hygiene.py` (registry +
`budget`/`validate` subcommands), `renmark/cli/_dispatch_flags.py` +
`renmark/cli/_engine.py` (`--artifact-hygiene` flag, mirroring the existing
`--compact-checkpoint` pattern at `_dispatch_flags.py:384`), one gate function
in `renmark/finish_lanes.py::release_readiness`, and a Hermes startup
allowlist in `renmark/lifecycle/preamble.py`. No parallel module, no new
Owner gate (REQ-30/REQ-31 compliant). First release action: delete the
byte-duplicate unpacked `.renmark/version/v0.39.7/` and `v0.40.0/` trees.

**Planning correction (found during grounding, not in the proposal):**
`renmark/lifecycle/preamble.py::skill_preamble` does not read the files the
proposal's allowlist listed (`lifecycle.json`, `program.json`, `tasks.json`,
`memory/INDEX.md` are read by *other* Step-0 calls skills make themselves,
outside `skill_preamble`). Its actual call graph (traced through
`renmark/state/skills.py`, `renmark/mode.py`, `renmark/agency.py`,
`renmark/config.py`, `renmark/capabilities.py`) touches: `.renmark/state/
last-skill.json`, `.renmark/state/delivery.json`, `.renmark/state/mode.json`,
`.renmark/state/agency.json`, `.renmark/config.json`,
`.renmark/state/compact_checkpoint.json` (write-only), and — **missing from
the proposal entirely** — `.renmark/memory/routing.md` (read by
`capabilities.top_tier()` when `tier == "full"` and the skill is a synthesis
skill). Task 6 below uses this corrected, code-verified list. Task 7's test
is designed as **runtime instrumentation** (patch `Path.read_text`/`open`/
`rglob`/`glob`/`iterdir` and call `skill_preamble` across a skill/tier/state
matrix) rather than the proposal's static grep, because a static grep of
`preamble.py` alone cannot see reads performed inside the five helper modules
above.

**`_resolve_release_link` correction:** `renmark/reports.py:90` only
auto-picks a version dir when exactly one exists under `.renmark/version/`;
today there are three (v0.39.7/v0.40.0/v0.41.0) so it already returns `""`
unless `version_path` is passed explicitly (which `plugin/skills/finish/
SKILL.md:244` always does). No source change is needed here — Task 1 only
needs a regression test proving the single-remaining-dir case still resolves
correctly, not a "redirect" as the proposal assumed.

### Task 1: retire duplicate unpacked version trees
- **mode:** B
- **target:** .renmark/version/
- **complexity:** medium
- **executor:** sonnet
- **role:** release-manager
- **parallel_group:** 1
- **est_tokens:** 800
- **est_cost_usd:** 0.0324
- **verifier:** bash -c 'test ! -d .renmark/version/v0.39.7 && test ! -d .renmark/version/v0.40.0 && test -d .renmark/version/v0.41.0 && test -f .renmark/version/renmark-v0.39.7.zip && test -f .renmark/version/renmark-v0.40.0.zip && test -f .renmark/version/renmark-v0.41.0.zip && python3 -m pytest -q tests/test_reports_analytics.py 2>&1 | tail -n 5'
- **serves:** REQ-6, REQ-28
- **spec:**
  Before deleting anything: (1) for each of `v0.39.7` and `v0.40.0`, extract
  the sibling zip (`renmark-v0.39.7.zip`, `renmark-v0.40.0.zip`) to a scratch
  dir and `diff -rq` it against the corresponding unpacked tree — abort this
  task and report if any diff is found (do not delete on a diff). (2) `grep
  -rn "version/v0\.39\.7\|version/v0\.40\.0"` across the repo (excluding
  `.renmark/version/` itself and `.renmark/rethink/artifact-lifecycle/*`,
  which reference the trees historically as inventory findings) — confirm no
  production code hardcodes either path. Only then delete
  `.renmark/version/v0.39.7/` and `.renmark/version/v0.40.0/` (`rm -rf`,
  git-tracked so reversible via `git checkout` pre-commit or `unzip
  .renmark/version/renmark-v0.39.7.zip -d .renmark/version/v0.39.7/` post-commit
  — record the rollback command in your task summary). Keep
  `.renmark/version/v0.41.0/` and all three `.zip` files untouched. Do NOT
  modify `renmark/reports.py` — `_resolve_release_link` (line 90) already
  auto-picks the sole remaining version dir correctly once only `v0.41.0/`
  is left; no redirect code is needed (see the plan-level correction note
  above). Run `pytest -q tests/test_reports_analytics.py` yourself before
  finishing to confirm nothing regressed.

### Task 2: artifact-type registry + budget/validate subcommands
- **mode:** B
- **target:** renmark/hygiene.py
- **complexity:** hard
- **executor:** sonnet
- **role:** code-implementer
- **parallel_group:** 1
- **est_tokens:** 3000
- **est_cost_usd:** 0.039
- **verifier:** python3 -m py_compile renmark/hygiene.py && python3 -c "from renmark.hygiene import ARTIFACT_REGISTRY; assert len(ARTIFACT_REGISTRY) == 14" && python3 -m renmark.hygiene budget --repo . 2>&1 | tail -n 5 && python3 -m renmark.hygiene validate --repo . 2>&1 | tail -n 5
- **serves:** REQ-6, REQ-28, REQ-30
- **spec:**
  Extend `renmark/hygiene.py` (do not create a new module — this file already
  owns `_ARTIFACT_SUBDIRS`/`_ARTIFACT_SUFFIXES`/`_MEMORY_LOGS`, the same
  "which .renmark paths, and how" concern). Add, verbatim in spirit from
  `.renmark/rethink/artifact-lifecycle/implementation-proposal.md` §1 (read
  it for the exact 13-entry table — path_glob, art_class, owner, regenerable,
  budget_count, budget_bytes, budget_age_days):

  1. `@dataclass(frozen=True) class ArtifactTypeSpec` with fields `name: str`,
     `path_glob: str` (relative to `.renmark/`), `art_class: str`
     (`active-context|canonical-evidence|archived-history|ephemeral`),
     `owner: str`, `regenerable: bool`, `budget_count: int | None`,
     `budget_bytes: int | None`, `budget_age_days: int | None`,
     `warn_pct: float = 0.8`.
  2. `ARTIFACT_REGISTRY: tuple[ArtifactTypeSpec, ...]` with exactly the 13
     entries from the proposal (audits, plans, reviews, state-live,
     state-scratch, memory, ledger, reports, rethink, roadmap, specs, debug,
     version-unpacked, version-zip — note that's 14 names in the proposal's
     list; treat `version-unpacked`/`version-zip` as the two halves of the
     `version/` "mixed" type from `lifecycle-contract.md`, giving 14 total
     registry rows even though the contract counted them as "13 types" —
     resolve the off-by-one by keeping both rows since they have genuinely
     different budgets/classes, and note the corrected count as 14 in your
     task summary).
  3. New CLI subcommand `budget` (alongside `scan`/`prune`/`all` in
     `_build_parser()`): `python -m renmark.hygiene budget [--repo PATH]` —
     read-only, walks `ARTIFACT_REGISTRY`, computes live count/bytes/oldest-age
     per type under `repo/.renmark/<path_glob>`, prints one line per type:
     `BUDGET  <name>  count=N/cap  bytes=N/cap  status=ok|warn|block` (cap
     printed as `-` when the budget field is `None`; status `warn` at
     `>= warn_pct` of any bounded dimension, `block` at `>= 100%`, else `ok`).
  4. New function `validate_registry_compliance(repo: Path) -> list[str]` —
     NOT an extension of `schemas.validate_artifact_metadata` (different
     contract: one file vs. whole tree). Walks `.renmark/` and produces issue
     strings for: (a) placement — any file matching zero `ARTIFACT_REGISTRY`
     globs → `"no registry entry: <relpath>"`; (b) metadata — for every
     `.md`/`.json` file with YAML/JSON frontmatter, call
     `schemas.validate_artifact_metadata` on the parsed dict, reused
     unchanged; (c) budget — same warn/block logic as `budget` subcommand,
     emitted as `"WARN <name>: ..."` / `"BLOCK <name>: ..."` strings; (d)
     canonical ownership — assert `.renmark/memory/project-map.md` exists and
     that every `.renmark/audits/inventory-*.md` and every
     `.renmark/rethink/*/survey.md` file's frontmatter `dependency_refs`
     contains a path ending in `memory/project-map.md` (a simple substring
     membership check on the parsed list, no LLM) — missing citation →
     `"no project-map.md pointer: <relpath>"`.
  5. New CLI subcommand `validate`: `python -m renmark.hygiene validate
     [--repo PATH]` — calls `validate_registry_compliance`, prints
     `VALIDATE  issues=N` then each issue on its own line, exit code 0
     always (report-only; nothing in this task blocks a CLI exit).
  6. `scan`/`all` gain type-aware behavior: for `art_class == "ephemeral" and
     spec.regenerable` entries, additionally apply this safe-deletion
     predicate on `--apply` runs: (i) file is under a `budget_age_days`-aged
     entry AND older than that age, (ii) file has zero inbound
     `dependency_refs` from any other artifact (best-effort — reuse
     `_referenced_paths`/an equivalent walk you add), (iii) it is not the
     single most-recent file of its type. All four conditions must hold
     before `--apply` deletes (not archives) — anything not meeting all four
     keeps today's archive-only behavior. `canonical-evidence`/
     `active-context` types are never touched by this predicate.

  Keep `scan_artifacts`/`prune_memory`'s existing signatures and dry-run
  default unchanged — this is additive. Run `mypy renmark/hygiene.py` before
  finishing (repo is "Mypy-strict clean" per the file's own docstring).

### Task 3: `--artifact-hygiene` CLI dispatch handler
- **mode:** B
- **target:** renmark/cli/_dispatch_flags.py
- **complexity:** simple
- **executor:** codex
- **role:** code-implementer
- **parallel_group:** 2
- **est_tokens:** 500
- **est_cost_usd:** 0.02
- **verifier:** python3 -m py_compile renmark/cli/_dispatch_flags.py 2>&1 | tail -n 5 && python3 -c "from renmark.cli._dispatch_flags import _dispatch_artifact_hygiene_flags" 2>&1 | tail -n 5
- **serves:** REQ-6, REQ-28
- **spec:**
  Add `_dispatch_artifact_hygiene_flags(args: argparse.Namespace, repo: Path)
  -> int | None`, mirroring `_dispatch_compact_flags` (line 384 of this file)
  exactly in shape: checks `if args.artifact_hygiene:` (the flag Task 4 will
  add to `_engine.py`'s parser), then calls
  `hygiene.main(["all", "--repo", str(repo)] + (["--apply"] if
  args.artifact_hygiene_apply else []))`, then additionally calls
  `hygiene.main(["budget", "--repo", str(repo)])` and `hygiene.main(["validate",
  "--repo", str(repo)])`, then returns `0`. Returns `None` when
  `args.artifact_hygiene` is falsy (so the handler chain in `_engine.py` falls
  through, matching every other `_dispatch_*_flags` function's contract).
  Import `hygiene` from `renmark` at the top of the file alongside the
  existing `_lifecycle` import. Depends on Task 2's `hygiene.py` additions
  being present (the `budget`/`validate` subcommands).

### Task 4: wire `--artifact-hygiene` flag into the CLI parser
- **mode:** B
- **target:** renmark/cli/_engine.py
- **complexity:** simple
- **executor:** codex
- **role:** code-implementer
- **parallel_group:** 3
- **est_tokens:** 400
- **est_cost_usd:** 0.015
- **verifier:** python3 -m py_compile renmark/cli/_engine.py && renmark-execute --artifact-hygiene --repo . | grep -q "BUDGET\|HYGIENE"
- **serves:** REQ-6, REQ-28
- **spec:**
  In `renmark/cli/_engine.py`: (1) import `_dispatch_artifact_hygiene_flags`
  alongside the existing `_dispatch_compact_flags` import (line 96 area); (2)
  add two `ap.add_argument` calls mirroring the `--compact-checkpoint` block
  at line ~691: `--artifact-hygiene` (`action="store_true"`, help text
  "run the .renmark/ artifact-lifecycle hygiene report (dry-run by
  default)") and `--artifact-hygiene-apply` (`action="store_true"`, help
  "with --artifact-hygiene: apply safe ephemeral-artifact cleanup instead of
  dry-run"); (3) add a validation check next to the existing
  `--accept/--judge require --behavior` check (line ~757):
  `--artifact-hygiene-apply` requires `--artifact-hygiene` (print to stderr,
  `return 2`, same pattern); (4) add `lambda:
  _dispatch_artifact_hygiene_flags(args, repo)` to the handler tuple at line
  763, in the same position as `_dispatch_compact_flags` (right after it).
  Depends on Task 3.

### Task 5: finish-time artifact-budget gate
- **mode:** B
- **target:** renmark/finish_lanes.py
- **complexity:** medium
- **executor:** sonnet
- **role:** code-implementer
- **parallel_group:** 2
- **est_tokens:** 1200
- **est_cost_usd:** 0.0336
- **verifier:** python3 -m py_compile renmark/finish_lanes.py 2>&1 | tail -n 5 && python3 -c "from renmark.finish_lanes import release_readiness; r = release_readiness('.'); assert any(g.name == 'artifact_budget' for g in r.gates)" 2>&1 | tail -n 5
- **serves:** REQ-6, REQ-28, REQ-30, REQ-31
- **spec:**
  Add `_gate_artifact_budget(repo: Path) -> GateResult` to
  `renmark/finish_lanes.py`, following the exact shape of the existing
  `_gate_tests_present` (line 390) and `_gate_version_consistent` (line 317)
  functions: import `hygiene` lazily inside the function (matching this
  file's existing lazy-import pattern for `renmark.release`/`renmark.worktree`),
  call `hygiene.validate_registry_compliance(repo)`, and reduce the returned
  issue-string list to a `GateResult("artifact_budget", passed, detail)`
  where `passed = not any(issue.startswith("BLOCK") for issue in issues)` and
  `detail` summarizes counts, e.g. `"3 WARN, 0 BLOCK"` or `"ok — 0 issues"`.
  Never raise (wrap in try/except like the other gates, returning
  `GateResult("artifact_budget", False, f"check error: {exc}")` on failure).
  Add `"artifact_budget"` to the `_INFORMATIONAL_GATES` frozenset (line 314)
  — this must be reported but must NOT block `release_readiness().ready`,
  matching `tests_present`'s precedent and the proposal's "adds zero new
  Owner questions" requirement (REQ-30). Add `_gate_artifact_budget(root)` to
  the `gates` list inside `release_readiness()` (line ~431), after
  `_gate_tests_present(root)`. Depends on Task 2's `validate_registry_compliance`.

### Task 6: Hermes startup allowlist
- **mode:** B
- **target:** renmark/lifecycle/preamble.py
- **complexity:** simple
- **executor:** sonnet
- **role:** code-implementer
- **parallel_group:** 1
- **est_tokens:** 400
- **est_cost_usd:** 0.0312
- **verifier:** python3 -m py_compile renmark/lifecycle/preamble.py 2>&1 | tail -n 5 && python3 -c "from renmark.lifecycle.preamble import HERMES_STARTUP_ALLOWLIST; assert '.renmark/memory/routing.md' in HERMES_STARTUP_ALLOWLIST and '.renmark/state/last-skill.json' in HERMES_STARTUP_ALLOWLIST" 2>&1 | tail -n 5
- **serves:** REQ-5, REQ-28
- **spec:**
  Add a module-level constant to `renmark/lifecycle/preamble.py` (do not
  touch any function body — this is documentation-as-code for what
  `skill_preamble()` already does):

  ```python
  HERMES_STARTUP_ALLOWLIST: frozenset[str] = frozenset({
      ".renmark/state/last-skill.json",
      ".renmark/state/delivery.json",
      ".renmark/state/mode.json",
      ".renmark/state/agency.json",
      ".renmark/config.json",
      ".renmark/state/compact_checkpoint.json",
      ".renmark/memory/routing.md",
  })
  ```

  **Use this exact list — do NOT copy the list from
  `implementation-proposal.md` §6.** That proposal's list (which included
  `lifecycle.json`, `program.json`, `tasks.json`, `memory/INDEX.md`) was
  written before this plan traced `skill_preamble`'s actual call graph; those
  four files are read by other Step-0 calls individual skills make
  themselves, not by `skill_preamble` itself, and the proposal's list
  entirely missed `.renmark/memory/routing.md` (read by
  `capabilities.top_tier()`, called from inside `skill_preamble` at line 224
  when `tier == "full" and skill in SYNTHESIS_SKILLS`). This corrected list
  is grounded directly in `renmark/state/skills.py` (`last-skill.json`),
  `renmark/mode.py` (`delivery.json`, `mode.json`), `renmark/agency.py`
  (`agency.json`), `renmark/config.py` (`config.json`), and
  `renmark/capabilities.py` (`routing.md`). Place the constant near the top
  of the file, after the imports, before `preamble_tier()`.

### Task 7: Hermes allowlist enforcement test (runtime instrumentation)
- **mode:** A
- **target:** tests/test_preamble_allowlist.py
- **complexity:** hard
- **executor:** sonnet
- **role:** test-writer
- **parallel_group:** 2
- **est_tokens:** 2500
- **est_cost_usd:** 0.0375
- **verifier:** python3 -m pytest -q tests/test_preamble_allowlist.py 2>&1 | tail -n 10
- **serves:** REQ-5, REQ-28
- **spec:**
  New test file. **Do not write a static grep-based test** — a text search of
  `preamble.py` alone cannot see file reads performed inside
  `renmark/state/skills.py`, `renmark/mode.py`, `renmark/agency.py`,
  `renmark/config.py`, or `renmark/capabilities.py`, all of which
  `skill_preamble()` calls into. Instead, write a **runtime instrumentation**
  test:

  1. A pytest fixture that monkeypatches `pathlib.Path.open`,
     `pathlib.Path.read_text`, and `pathlib.Path.write_text` to record every
     resolved path passed through them (relative to a temp repo root) into a
     list, while still delegating to the real implementation (don't break
     I/O — just observe it).
  2. Also monkeypatch `pathlib.Path.rglob`, `pathlib.Path.glob`, and
     `pathlib.Path.iterdir` to raise `AssertionError` if called at all during
     the instrumented window — `skill_preamble`'s whole invariant is that it
     never recurses/lists a directory; catching a future `rglob` addition is
     the point of this test, not just cataloguing files.
  3. In a `tmp_path`-based fake repo (create `.renmark/state/`,
     `.renmark/memory/`, write minimal valid `mode.json`/`agency.json`/
     `delivery.json`/`config.json`/`routing.md` fixtures — reuse
     `tests/test_hygiene.py`'s `_write_artifact`-style helper pattern for
     frontmatter if needed), call `renmark.lifecycle.skill_preamble(repo,
     skill)` for at least: `"debug"` (minimal tier), `"feature"` (agency-aware,
     standard/full tier), and `"start"` (a `SYNTHESIS_SKILLS` member, to
     exercise the `routing.md` read path — set `top_tier: fable` in
     `routing.md`'s frontmatter first so that branch actually executes).
  4. After each call, assert every recorded path (relative to repo root) is a
     member of `renmark.lifecycle.preamble.HERMES_STARTUP_ALLOWLIST` (from
     Task 6) — a path outside the allowlist fails the test with the offending
     path in the message.
  5. Assert the `rglob`/`glob`/`iterdir` instrumentation recorded zero calls
     across all three invocations.

  Depends on Task 6.

### Task 8: registry + validator tests
- **mode:** B
- **target:** tests/test_hygiene.py
- **complexity:** medium
- **executor:** codex
- **role:** test-writer
- **parallel_group:** 2
- **est_tokens:** 1500
- **est_cost_usd:** 0.03
- **verifier:** python3 -m pytest -q tests/test_hygiene.py 2>&1 | tail -n 10
- **serves:** REQ-6, REQ-28
- **spec:**
  Add tests to the existing `tests/test_hygiene.py` (reuse its
  `_write_artifact` helper — see the file's existing pattern) covering Task
  2's additions: (1) `ARTIFACT_REGISTRY` has exactly 14 entries (per Task 2's
  corrected count) and every `path_glob` is a non-empty string; (2) `budget`
  CLI subcommand on an empty `.renmark/` tree reports `status=ok` for every
  type with a defined budget; (3) budget crossing `warn_pct` reports
  `status=warn` (write N+1 files where cap is N*warn_pct, e.g. for a type
  with `budget_count=10, warn_pct=0.8`, write 9 files); (4) budget at/over
  100% reports `status=block`; (5) `validate_registry_compliance` flags a
  file written outside any registered glob as `"no registry entry: ..."`;
  (6) `validate_registry_compliance` flags an `audits/inventory-*.md` file
  whose `dependency_refs` frontmatter list omits a `memory/project-map.md`
  pointer, and does NOT flag one that includes it; (7) the safe-deletion
  predicate: an ephemeral+regenerable file past its `budget_age_days`, with
  no inbound `dependency_refs`, and not the newest of its type, IS deleted
  (not archived) on `--apply`; a file failing any one of those three
  conditions is left untouched by the predicate (existing archive-only
  behavior may still apply to it via `scan_artifacts`, that's fine — this
  test only checks the *delete* path is properly gated). Depends on Task 2.

### Task 9: CLI dispatch flag tests
- **mode:** A
- **target:** tests/test_cli_artifact_hygiene.py
- **complexity:** medium
- **executor:** codex
- **role:** test-writer
- **parallel_group:** 4
- **est_tokens:** 800
- **est_cost_usd:** 0.02
- **verifier:** python3 -m pytest -q tests/test_cli_artifact_hygiene.py 2>&1 | tail -n 10
- **serves:** REQ-6, REQ-28
- **spec:**
  New test file, following `tests/test_mode_cli.py`'s pattern for testing a
  `renmark-execute`-style flag (invoke `renmark.cli._engine.main` or the
  equivalent entry point directly with an argv list, in a `tmp_path` fake
  repo, capturing stdout). Cover: (1) `--artifact-hygiene` alone runs in
  dry-run and prints `HYGIENE`/`BUDGET`/`VALIDATE` report lines, makes no
  filesystem changes; (2) `--artifact-hygiene --artifact-hygiene-apply`
  requires `--artifact-hygiene` — passing `--artifact-hygiene-apply` alone
  exits 2 with a stderr message (mirroring the existing `--accept` requires
  `--behavior` test, if one exists — check `tests/` for that pattern first
  and match its structure); (3) `--artifact-hygiene --artifact-hygiene-apply`
  actually applies (use a fixture ephemeral file that Task 8 already proves
  is delete-eligible, confirm it's gone after the CLI call, not just after a
  direct `hygiene.main()` call). Depends on Task 4.

### Task 10: finish-lane gate test
- **mode:** B
- **target:** tests/test_finish_lanes.py
- **complexity:** medium
- **executor:** codex
- **role:** test-writer
- **parallel_group:** 3
- **est_tokens:** 900
- **est_cost_usd:** 0.025
- **verifier:** python3 -m pytest -q tests/test_finish_lanes.py 2>&1 | tail -n 10
- **serves:** REQ-6, REQ-28, REQ-30, REQ-31
- **spec:**
  Add tests to `tests/test_finish_lanes.py` covering Task 5's
  `_gate_artifact_budget`/`release_readiness` wiring: (1) a clean `.renmark/`
  tree (or one with only WARN-level issues) yields a `GateResult` named
  `"artifact_budget"` with `passed=True`; (2) `release_readiness(repo).ready`
  stays `True` even when `artifact_budget`'s `passed` is `False` (confirms
  it's correctly in `_INFORMATIONAL_GATES` and never blocks release — this is
  the REQ-30 "no new Owner gate" assertion, make it explicit in the test
  name/docstring); (3) a fixture repo with a file matching zero
  `ARTIFACT_REGISTRY` globs produces a non-empty detail string mentioning the
  issue count. Depends on Task 5.

---

## Cost preview

| Task | Executor | Complexity | Est. tokens | Est. cost |
|---|---|---|---|---|
| 1. version-tree retirement | sonnet | medium | 800 | $0.0324 |
| 2. registry + budget/validate | sonnet | hard | 3000 | $0.0390 |
| 3. dispatch handler | codex | simple | 500 | $0.0200 |
| 4. CLI wiring | codex | simple | 400 | $0.0150 |
| 5. finish-lane gate | sonnet | medium | 1200 | $0.0336 |
| 6. Hermes allowlist | sonnet | simple | 400 | $0.0312 |
| 7. allowlist enforcement test | sonnet | hard | 2500 | $0.0375 |
| 8. registry/validator tests | codex | medium | 1500 | $0.0300 |
| 9. CLI flag tests | codex | medium | 800 | $0.0200 |
| 10. finish-lane gate test | codex | medium | 900 | $0.0250 |

**Total estimated cost: ~$0.284** (5× sonnet incl. ~10k Agent overhead/task,
5× codex subprocess). Executors: sonnet×5, codex×5. 4 parallel groups
(1 → 2 → 3 → 4), 10 tasks total.
