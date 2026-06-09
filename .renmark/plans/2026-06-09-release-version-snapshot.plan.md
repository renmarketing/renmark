# Plan: release-version-snapshot

**Feature goal:** Make `.renmark/version/` the canonical local release home (replacing
`.renmark/baks/` for NEW releases; baks stays READABLE for old artifacts). On release,
write BOTH a portable zip (`<basename>-v<VERSION>.zip`) AND an unpacked, browsable
snapshot `v<VERSION>/` containing `manifest.json`, `release.md`, `verification.md`,
`files-changed.txt`. Reuse the existing `build_package` zip + `PACKAGE_EXCLUDES` logic.
The snapshot is the LAST release step — created only after merge approval → merge to
main → final verification passes → version/tag known.

**Reuse, don't duplicate:** `renmark/release.py` already has `build_package(repo, *,
version, dest_dir, archive_stem)`, `package_basename`, `current_version`,
`PACKAGE_EXCLUDES` (already excludes `.git`, `node_modules`, `__pycache__`, `.venv`,
ALL of `.renmark`), and `_is_excluded`. Because `PACKAGE_EXCLUDES` excludes `.renmark`
wholesale, both the zip and the unpacked copy self-exclude `.renmark/version` and
`.renmark/baks` for free (no recursion). The 4 metadata files are GENERATED into the
snapshot dir, not copied from `.renmark`.

**Constraints (every task):** Python ≥3.10 stdlib only (`zipfile`/`shutil`/`json`/
`pathlib`/`subprocess` for git); never-raise where release code is already defensive
(git/verification absence degrades to a fallback, never an exception); REQ-6 (all writes
inside the project's `.renmark/`; `.renmark/version/` self-excludes); keep all existing
tests green. Dev gates: `pytest -q` · `ruff check` · `mypy .`.

> Note: the test task is routed to **sonnet**, not codex — the codex CLI sandbox is
> read-only in this environment (confirmed earlier this session; it exits 0 but cannot
> write the artifact). Routing test scaffolding to a writable Agent avoids a wasted cycle.

---

### Task 1: version-snapshot builder + baks→version default
- **mode:** B
- **target:** renmark/release.py
- **complexity:** hard
- **executor:** opus
- **parallel_group:** 1
- **est_tokens:** 1700
- **est_cost_usd:** 0.18
- **verifier:** python3 -c "from renmark import release; assert release.VERSION_SUBDIR=='.renmark/version'; assert hasattr(release,'build_version_snapshot')"
- **serves:** new
- **spec:**
  Edit `renmark/release.py` (read it first — reuse `build_package`, `package_basename`,
  `current_version`, `PACKAGE_EXCLUDES`, `_is_excluded`; do NOT duplicate the exclude set
  or the zip walk). Changes:

  1. Add `VERSION_SUBDIR = ".renmark/version"` next to the existing `BAKS_SUBDIR`
     constant. KEEP `BAKS_SUBDIR` (legacy, still readable) — do not delete it.
  2. Change `build_package`'s DEFAULT output dir from `repo / BAKS_SUBDIR` to
     `repo / VERSION_SUBDIR` (when `dest_dir is None`). The `--dest` / `dest_dir`
     override is unchanged. Update its docstring (baks → version; note baks is legacy).
  3. Add `build_version_snapshot(repo='.', *, version=None, now=None) -> dict[str, str]`:
     - `ver = version or current_version(repo)`; `base = repo/VERSION_SUBDIR` (mkdir parents).
     - **Zip:** call `build_package(repo, version=ver, dest_dir=base)` → writes
       `base/<package_basename>-v<ver>.zip`. Capture the returned path.
     - **Unpacked copy:** `snap = base / f"v{ver}"`; if it exists, remove it
       (`shutil.rmtree`), then recreate. Walk `repo.rglob('*')`; for each FILE whose
       `rel.parts` is NOT `_is_excluded`, copy it to `snap/rel` (mkdir parents, preserve
       relative layout). This reuses `_is_excluded`, so `.git`, `node_modules`,
       `__pycache__`, `.venv`, and ALL of `.renmark` (incl. `version/` and `baks/`) are
       excluded — no recursion.
     - **Generate 4 metadata files INTO `snap/`:**
       - `manifest.json` — JSON with: `version`, `tag` (`f"v{ver}"`), `source_sha`
         (`git rev-parse HEAD`, or "" on failure), `created_at` (the `now` arg if given,
         else `datetime.now().isoformat()` — accept `now` so tests are deterministic),
         `file_count` (number of copied app files), `basename` (`package_basename`),
         `excludes` (`list(PACKAGE_EXCLUDES)`).
       - `release.md` — the CHANGELOG section for this version: read `CHANGELOG.md`,
         extract the block starting at the heading matching `## v<ver>` (or `## [`…
         containing `v<ver>`) up to the next `## ` heading; fall back to a one-line
         "Release v<ver> — see CHANGELOG.md" if not found.
       - `verification.md` — find the most recent `.renmark/reviews/*.verification.md`
         (sorted by name; newest last) and copy its text; fall back to
         "No verification artifact found for v<ver>." if none.
       - `files-changed.txt` — `git diff --name-only <prev>..HEAD` where `<prev>` is the
         previous version tag if one exists (`git tag --list 'v*' --sort=-v:refname`,
         skip the current `v<ver>`, take the next), else `git ls-files` (all tracked).
         Never raise — git failure → empty file with a "# (git unavailable)" line.
     - Return `{"version": ver, "zip": str(zip_path), "snapshot_dir": str(snap),
       "manifest": str(snap/'manifest.json'), "file_count": str(n)}`.
     - Never raise on git/verification/changelog absence — degrade to fallbacks. Use
       `subprocess.run([...], capture_output=True, text=True)` guarded by try/except.
  4. Add a `snapshot` subcommand to `main()` (mirror the `package` arg-parsing style):
     `python -m renmark.release snapshot [PATH]` runs the drift gate (`drift_report`),
     then `build_version_snapshot(repo)`, and prints `OK  snapshot v<ver> → <snapshot_dir>`
     (+ the zip path). Refuse on drift like `package` does. Update the usage string to
     include `snapshot`.
  Full type hints (mypy clean), ruff clean.

### Task 2: tests for build_version_snapshot
- **mode:** A
- **target:** tests/test_release_snapshot.py
- **complexity:** hard
- **executor:** sonnet
- **parallel_group:** 2
- **est_tokens:** 1600
- **est_cost_usd:** 0.03
- **verifier:** python3 -m pytest tests/test_release_snapshot.py -q
- **serves:** new
- **spec:**
  pytest tests for `release.build_version_snapshot` (Task 1). Read `renmark/release.py`
  and `tests/test_release_drift.py` for the existing test fixtures/style (how they build
  a tmp repo with VERSION + plugin.json). Build a tmp repo under `tmp_path` with: a
  `VERSION` (e.g. `1.2.3`), a `plugin/.claude-plugin/plugin.json` (name "renmark"), a
  `CHANGELOG.md` containing a `## v1.2.3 — ...` section, a `.renmark/reviews/2026-01-01-x.verification.md`,
  some app files (`renmark/foo.py`, `README.md`), and junk to exclude: `.git/config`,
  `node_modules/x.js`, `__pycache__/y.pyc`, `.renmark/baks/old.zip`. Init a real git repo
  (`git init`, add, commit) so the git calls resolve; if git isn't available, the
  never-raise fallbacks must still produce the files. Pass `now="2026-06-09T00:00:00"`
  for determinism. Assert:
  - `.renmark/version/renmark-v1.2.3.zip` exists.
  - `.renmark/version/v1.2.3/` exists and contains `manifest.json`, `release.md`,
    `verification.md`, `files-changed.txt`.
  - The unpacked copy contains the app files (`renmark/foo.py`) but NOT `.git/`,
    `node_modules/`, `__pycache__/`, and NO nested `.renmark/` (no recursion, no baks).
  - `manifest.json` parses and has `version==1.2.3`, `tag=="v1.2.3"`,
    `created_at=="2026-09..."`-style injected value, a non-negative `file_count`, and a
    non-empty `excludes` list.
  - `release.md` contains the v1.2.3 changelog text; `verification.md` contains the
    seeded verification content (or the documented fallback).
  - Calling `build_version_snapshot` twice for the same version overwrites cleanly (no
    crash, snapshot dir rebuilt).
  Keep ruff clean. Do not modify `renmark/release.py`.

### Task 3: update drift test for version default
- **mode:** B
- **target:** tests/test_release_drift.py
- **complexity:** simple
- **executor:** sonnet
- **parallel_group:** 2
- **est_tokens:** 350
- **est_cost_usd:** 0.03
- **verifier:** python3 -m pytest tests/test_release_drift.py -q
- **serves:** new
- **spec:**
  `build_package`'s default output dir changed from `.renmark/baks/` to
  `.renmark/version/` (Task 1). Update the affected assertion(s) in
  `tests/test_release_drift.py` — notably `test_build_package_writes_versioned_zip_to_baks`
  (~line 189) which asserts `out == repo/".renmark"/"baks"/...`. Change the expected path
  to `.renmark/version/` and rename the test to `..._to_version`. Leave the
  exclusion / inside-project / overwrite tests intact (only their path expectation
  changes if they assert the baks dir). Do NOT touch `renmark/release.py`. All tests in
  this file must pass.

### Task 4: scaffold .renmark/version in init's gitignore set
- **mode:** B
- **target:** renmark/init.py
- **complexity:** simple
- **executor:** sonnet
- **parallel_group:** 1
- **est_tokens:** 350
- **est_cost_usd:** 0.03
- **verifier:** python3 -c "from renmark import init; assert '.renmark/version' in init.EXCLUDE_RENMARK_RUNTIME and '.renmark/baks' in init.EXCLUDE_RENMARK_RUNTIME" && python3 -m pytest tests/ -q -k init
- **serves:** new
- **spec:**
  In `renmark/init.py` (~line 74) add `".renmark/version"` to the
  `EXCLUDE_RENMARK_RUNTIME` set so freshly-scaffolded projects gitignore the new release
  home. KEEP `.renmark/baks` in the set (legacy). Update the nearby comment (~line 70)
  to mention version. If any existing init test asserts the exact contents of that set
  or the generated `.gitignore`, update it to include `.renmark/version` so the suite
  stays green. Touch ONLY `renmark/init.py` (if a test file must change, that is a
  separate concern — but prefer to make the set addition backward-compatible so existing
  tests that check membership still pass).

### Task 5: finish skill — release protocol §4
- **mode:** B
- **target:** plugin/skills/finish/SKILL.md
- **complexity:** medium
- **executor:** sonnet
- **parallel_group:** 1
- **est_tokens:** 900
- **est_cost_usd:** 0.03
- **verifier:** grep -q '.renmark/version' plugin/skills/finish/SKILL.md && grep -q 'snapshot' plugin/skills/finish/SKILL.md
- **serves:** new
- **spec:**
  Rewrite the §4 Release section of `plugin/skills/finish/SKILL.md` to the new protocol
  (read the current §4 first). Key points:
  - The canonical local release home is now `.renmark/version/` (not `.renmark/baks/`).
    `.renmark/baks/` remains readable for old artifacts but new releases write only to
    `.renmark/version/`.
  - The release step runs `python -m renmark.release snapshot` (the new subcommand),
    which writes BOTH `.renmark/version/<basename>-v<VERSION>.zip` AND the unpacked
    `.renmark/version/v<VERSION>/` with `manifest.json` + `release.md` + `verification.md`
    + `files-changed.txt`.
  - **Timing contract (state explicitly):** the snapshot is the LAST release step,
    created ONLY AFTER (1) human merge approval, (2) merge into main, (3) final
    verification on main passes, (4) version/tag metadata is known. Do not snapshot a
    pre-merge or unverified tree.
  - Keep the existing drift gate (`renmark.release check`), the maintainer `--dest`
    override note, the git-tag step, and the "GitHub release only if remote+gh" branch.
    Update the frontmatter `description:` line (baks → version) too.
  - Preserve the human-gate doctrine (merge/release are human-approved). Keep the
    next-steps citation block and the closing "Mirror any rule changes in AGENTS.md" line.

### Task 6: finish command shim description
- **mode:** B
- **target:** plugin/commands/finish.md
- **complexity:** simple
- **executor:** haiku
- **parallel_group:** 1
- **est_tokens:** 150
- **est_cost_usd:** 0.00
- **verifier:** grep -q '.renmark/version' plugin/commands/finish.md && ! grep -q 'baks' plugin/commands/finish.md
- **serves:** new
- **spec:**
  In `plugin/commands/finish.md` frontmatter `description:`, change the phrase
  "distribution zip into .renmark/baks/" to ".renmark/version/ (zip + unpacked snapshot)".
  Change ONLY that reference; leave the rest of the line intact.

### Task 7: gitignore .renmark/version
- **mode:** B
- **target:** .gitignore
- **complexity:** simple
- **executor:** haiku
- **parallel_group:** 1
- **est_tokens:** 100
- **est_cost_usd:** 0.00
- **verifier:** grep -q '.renmark/version/' .gitignore
- **serves:** new
- **spec:**
  In `.gitignore`, in the "renmark runtime (regenerable per project)" block (which
  already lists `.renmark/state/`, `.renmark/debug/`, `.renmark/logs/`, `.renmark/baks/`),
  add a line `.renmark/version/`. Keep `.renmark/baks/` (legacy). Add nothing else.

---

## Cost preview

| # | Task | Executor | Group | est_tokens | est_cost |
|---|---|---|---|---|---|
| 1 | renmark/release.py | opus | 1 | 1700 | $0.18 |
| 2 | tests/test_release_snapshot.py | sonnet | 2 | 1600 | $0.03 |
| 3 | tests/test_release_drift.py | sonnet | 2 | 350 | $0.03 |
| 4 | renmark/init.py | sonnet | 1 | 350 | $0.03 |
| 5 | plugin/skills/finish/SKILL.md | sonnet | 1 | 900 | $0.03 |
| 6 | plugin/commands/finish.md | haiku | 1 | 150 | $0.00 |
| 7 | .gitignore | haiku | 1 | 100 | $0.00 |

**Total (incl. ~10k Agent overhead per haiku/sonnet/opus task): ~$0.33**

Executors: haiku×2, sonnet×4, opus×1. Waves: 2 (group 1 → group 2). Group 1 = release.py
core + the independent doc/config/module edits (disjoint files). Group 2 = the two test
files, which depend on release.py's new behavior.
