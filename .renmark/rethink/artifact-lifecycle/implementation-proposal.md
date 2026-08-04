---
artifact_type: rethink-implementation-proposal
schema_version: 1
created_at: 2026-08-04T00:00:00Z
source_sha: 9bd233548a7f7b34695124596c3faa6398ec044b
related_plan: null
generator: sonnet
stale_after: null
dependency_refs:
  - .renmark/rethink/artifact-lifecycle/survey.md
  - .renmark/rethink/artifact-lifecycle/lifecycle-contract.md
---

# Stage 3 Implementation Proposal — `.renmark/` artifact lifecycle

PROPOSAL ONLY. No source file, migration, deletion, or rotation is executed
by this document. Every item below states which existing module/CLI surface
it extends and why the extension can't be folded into that surface's current
shape.

## Grounding — what already exists (do not duplicate)

- `renmark/hygiene.py` (`python -m renmark.hygiene {scan,prune,all}`) already
  walks `specs/plans/reviews/research/state/wave-summaries`, archives
  stale-and-unreferenced files to `.renmark/archive/YYYY-MM/<original-path>`,
  dry-run by default (`--apply` to write), never touches
  `lifecycle.json`-referenced paths, and already calls
  `lifecycle.skill_preamble`. This is the canonical hygiene engine — Phase 3
  extends it, it does not get a sibling.
- `renmark/schemas.py::validate_artifact_metadata` already validates the
  per-file provenance block (`artifact_type`, `schema_version`, `created_at`,
  ..., `dependency_refs`) plus the size-budget pattern used for
  `lifecycle.json` (1024-byte cap, `validate_lifecycle`). This is the
  per-file frontmatter validator — Phase 3 reuses it as-is (unchanged) and
  adds a repo-level walk on top, which is a different concern (one file vs.
  the whole tree) so it cannot live inside `schemas.py`'s single-document
  functions without breaking their "validate one parsed dict" contract.
- `plugin/skills/.shared/artifact-lifecycle.md` already defines the
  three-step retirement policy (stop generation → leave existing → redirect
  readers) and the additive lifecycle fields (`owner`, `status`,
  `dependencies`, `invalidated_by`, `replacement`, `retention`). Phase 3
  reuses this policy verbatim for every retirement below; no new policy text
  is introduced.
- `renmark/finish_lanes.py::release_readiness` already runs a deterministic,
  no-LLM gate list before release/package/install actions and returns a
  `ReadinessReport` of `GateResult`s. Phase 3 adds one more `GateResult`
  producer to that same list — it does not create a second gate mechanism.
- No `renmark/audit.py` artifact-type registry, no `renmark/lint.py` artifact
  walk, and no `renmark/rethink.py` exist (rethink is skill-orchestrated).
  `renmark/audit.py` writes dated audit/inventory reports but has no
  budget/placement notion — out of scope to extend for this purpose since it
  is a *report generator*, not the *sweeper*; hygiene.py is the sweeper.

---

## 1. Artifact-type registry

**New, but the smallest possible new surface: a module-level dataclass list
appended to `renmark/hygiene.py`, not a new file.** hygiene.py already owns
`_ARTIFACT_SUBDIRS`/`_ARTIFACT_SUFFIXES`/`_MEMORY_LOGS` — the exact same
"which paths does hygiene care about, and how" concern the registry answers,
just generalized from 5 flat subdirs + 3 memory files to all 13 types with
per-type class/budget/owner/regenerable metadata. A brand-new module would
duplicate hygiene.py's existing path-walk/archive-move machinery; extending
the constants block in place lets `scan_artifacts`/`prune_memory` (and the
two new functions in §2/§3) consume one source of truth.

```python
# renmark/hygiene.py — new, replaces/extends _ARTIFACT_SUBDIRS

@dataclass(frozen=True)
class ArtifactTypeSpec:
    name: str                     # e.g. "audits", "version-unpacked"
    path_glob: str                # relative to repo/.renmark, e.g. "audits/**"
    art_class: str                # active-context | canonical-evidence | archived-history | ephemeral
    owner: str                    # skill/module name, per artifact-lifecycle.md's `owner` field
    regenerable: bool
    budget_count: int | None      # None = unbounded
    budget_bytes: int | None
    budget_age_days: int | None
    warn_pct: float = 0.8

ARTIFACT_REGISTRY: tuple[ArtifactTypeSpec, ...] = (
    ArtifactTypeSpec("audits", "audits/**", "ephemeral", "audit", True, 60, 1_500_000, 60),
    ArtifactTypeSpec("plans", "plans/**", "canonical-evidence", "plan", False, 150, 3_000_000, None),
    ArtifactTypeSpec("reviews", "reviews/**", "canonical-evidence", "review", False, 250, 1_500_000, None),
    ArtifactTypeSpec("state-live", "state/{lifecycle,program,delivery,mode,agency,tasks,compact_checkpoint,last-skill}.json", "active-context", "lifecycle", False, None, 51_200, None),
    ArtifactTypeSpec("state-scratch", "state/{escalations,_wave-prompts,handoffs,adhoc-specs}/**", "ephemeral", "dispatch", True, 200, 1_000_000, 14),
    ArtifactTypeSpec("memory", "memory/*.md", "active-context", "memory", False, 16, None, None),
    ArtifactTypeSpec("ledger", "ledger/events.jsonl", "canonical-evidence", "ledger", False, None, 25_000_000, None),
    ArtifactTypeSpec("reports", "reports/features/*/*", "archived-history", "reports", True, 100, 500_000, None),
    ArtifactTypeSpec("rethink", "rethink/*/*.md", "canonical-evidence", "rethink", False, None, 500_000, None),
    ArtifactTypeSpec("roadmap", "roadmap/*.md", "active-context", "roadmap", False, 2, 307_200, None),
    ArtifactTypeSpec("specs", "specs/*.md", "canonical-evidence", "brainstorm", False, 100, 500_000, None),
    ArtifactTypeSpec("debug", "debug/*/*", "ephemeral", "debug", True, 40, 1_000_000, 90),
    ArtifactTypeSpec("version-unpacked", "version/v*/**", "ephemeral", "release", True, 1, None, None),
    ArtifactTypeSpec("version-zip", "version/*.zip", "canonical-evidence", "release", False, None, None, None),
)
```

Path/class/budget numbers are copied verbatim from `lifecycle-contract.md`
§1–§13; `path_glob` is new (the contract described paths in prose — this is
the first place they become one machine-checkable string per type).
`art_class` values map 1:1 onto this task's four requested classes:
`active-context`/`canonical-evidence`/`archived-history`/`ephemeral`
(`lifecycle-contract.md`'s "canonical"/"canonical (acceptance evidence)"/
"canonical (release history)" all collapse to `canonical-evidence`;
"derived/terminal" → `archived-history`; "ephemeral/generated" → `ephemeral`).

## 2. Deterministic inventory/hygiene command, dry-run default

**Extend `renmark/hygiene.py`'s existing CLI, not a parallel command.**
Two changes, both additive to the existing `argparse` parser in
`_build_parser()`:

1. New subcommand `budget` alongside the existing `scan`/`prune`/`all`:
   `python -m renmark.hygiene budget [--repo PATH]` — walks
   `ARTIFACT_REGISTRY`, computes count/bytes/oldest-age per type, prints one
   bounded line per type (`BUDGET  <name>  count=N/cap  bytes=N/cap
   status=ok|warn|block`), always read-only (no `--apply` for `budget` — it
   is report-only by construction, matching this task's "dry-run: report
   only" requirement without needing a flag).
2. `scan`/`all` gain type-aware behavior: instead of the current flat
   `_ARTIFACT_SUBDIRS` tuple, they iterate `ARTIFACT_REGISTRY` entries whose
   `art_class == "ephemeral"` for TTL-archival (existing behavior, now
   type-driven) and additionally apply the safe-deletion predicate from
   `lifecycle-contract.md`'s Global Rules (regenerable + zero inbound
   `dependency_refs` + past age + not sole-most-recent) for `--apply` runs —
   this is new logic inside `scan_artifacts`, gated behind
   `art_class == "ephemeral" and spec.regenerable`, never touching
   `canonical-evidence`/`active-context` types (those keep today's
   archive-only behavior).

`renmark-execute --artifact-hygiene` / `--artifact-hygiene --apply`
(`renmark/cli/_engine.py`): a **thin dispatch flag**, not new logic — mirrors
the existing `--compact-checkpoint`/`--behavior` pattern of one
`ap.add_argument` plus one `_dispatch_*` handler function
(`_dispatch_artifact_hygiene_flags`, added next to
`_dispatch_compact_flags` in the same `for _handler in (...)` chain at
`_engine.py:763`). The handler calls `hygiene.main(["all", "--repo", str(repo)]
+ (["--apply"] if args.artifact_hygiene_apply else []))` and additionally
prints the `budget` subcommand's report — i.e. `renmark-execute
--artifact-hygiene` = `python -m renmark.hygiene all` (dry-run) +
`python -m renmark.hygiene budget`, `--apply` forwards `--apply`. This gives
users the CLAUDE.md-familiar `renmark-execute --flag` surface the task asked
for while keeping `renmark.hygiene` the single implementation.

## 3. Validator

**One new function in `renmark/hygiene.py`: `validate_registry_compliance(repo) -> list[str]`.**
Not an extension of `schemas.py::validate_artifact_metadata` (that function's
contract is "validate one parsed JSON/frontmatter dict" — repo-wide
placement/budget/ownership checks operate on the whole tree, a different
input shape that would break that function's single-document signature).
Instead this new function *composes* the existing per-file validator with a
tree walk hygiene.py already knows how to do:

- **Placement:** for every file under `.renmark/`, resolve which
  `ARTIFACT_REGISTRY` `path_glob` it matches (if any); a file matching zero
  globs is flagged `"no registry entry: <path>"` (catches drift like a plan
  written outside `plans/`).
- **Metadata:** for every `.md`/`.json` file with YAML/JSON frontmatter,
  call `schemas.validate_artifact_metadata` on the parsed frontmatter dict —
  reused unchanged, not reimplemented.
- **Budget compliance:** per registry entry, compare live count/bytes/age
  against `budget_count`/`budget_bytes`/`budget_age_days`; `>= warn_pct`
  → `"WARN"` issue string, `>= 100%` → `"BLOCK"` issue string (block is
  informational at this layer — see §4 for how `finish` turns a BLOCK into a
  visible flag, never a silent skip).
- **Canonical ownership (three-way-overlap resolution):** a small fixed
  check list encoding `lifecycle-contract.md`'s Closing §A/§C resolution —
  e.g. assert `.renmark/memory/project-map.md` exists and is the only file
  among `{project-map.md, audits/inventory-*.md structural bodies,
  rethink/*/survey.md}` NOT carrying a `dependency_refs` pointer back to
  `project-map.md`; every `inventory-*.md`/`survey.md` must cite it. This is
  a grep-checkable string-membership test, no LLM.

Wired into `python -m renmark.hygiene validate [--repo PATH]` (third CLI
subcommand alongside `budget`), and into `renmark-execute
--artifact-hygiene` output as a fourth report section (`VALIDATE  issues=N`).

## 4. Finish-time rotation/retirement checks

**Extend `renmark/finish_lanes.py::release_readiness`'s existing gate list,
not a new Owner gate.** `release_readiness` already aggregates a list of
`GateResult` objects the `release`/`full` lanes consult before
release/package actions (`_engine.py:401` area, `renmark/finish_lanes.py`).
Add one more gate function, `_gate_artifact_budget(repo) -> GateResult`,
that calls `hygiene.validate_registry_compliance(repo)` and reduces it to
PASS (no BLOCK issues) / WARN (WARN issues only, non-fatal) / FAIL (any
BLOCK issue) — same three-state shape every other gate in that file already
returns. This is read-only reporting, consistent with REQ-30/REQ-31: it adds
zero new Owner questions (a WARN/FAIL surfaces in the existing finish-lane
report line, the same place a failing test-gate result already surfaces),
and rotation itself (moving `escalations/`/`_wave-prompts/`/`handoffs/*.raw.md`
scratch for the now-`released` feature) is triggered by calling
`hygiene.scan_artifacts(repo, dry_run=not apply)` from inside the existing
`quick`/`release` lane bodies at the point they already flip
`lifecycle.json` to `released` — one extra function call in an existing
lane function, not a new lane, new gate class, or new pause point.

## 5. Migration plan for existing `.renmark/` artifacts

Phased, reversible, smallest-blast-radius-first. No step in this list is
executed by this proposal.

**Step 1 — RETIRE-UNPACKED-VERSION-TREES (lowest risk, highest payoff, do
first).**
- What moves/deletes: delete `.renmark/version/v0.39.7/` and
  `.renmark/version/v0.40.0/` (the two non-current unpacked trees); keep
  `.renmark/version/v0.41.0/` (current) and all three `.zip` files
  untouched.
- Why safe: each deleted tree is a byte-for-byte duplicate of its sibling
  zip (survey.md §12 item 10 — "the clearest, most unambiguous overlap
  found in this entire survey"); the sole production reader
  (`renmark/reports.py::_resolve_release_link`) reads the *directory name*
  only, never file bodies, and gets redirected to resolve from the zip
  filename first (code change, done as part of this step, not a later
  step — the retirement policy requires "redirect readers" before or with
  the delete, never after).
- Rollback: `unzip .renmark/version/renmark-v<ver>.zip -d
  .renmark/version/v<ver>/` — the zip is authoritative and untouched, so
  this is a lossless, single-command restore.
- Risk: **low.** ~1,730 of ~2,168 files removed, zero canonical content
  lost, one code-path redirect to verify (`pytest -q -k release_link` or
  equivalent).

**Step 2 — audits/ rotation.** Move dated `audit-report-*`/`inventory-*`
pairs older than the 15 most-recent per family under `.renmark/audits/archive/`
(mkdir + `git mv`, or the widened `hygiene.py scan` once §2 ships). Safe:
fully regenerable, pointer-only reads (survey.md §1 item 4). Rollback:
`git mv` back (git-tracked) or re-run `/renmark:audit` for a fresh
equivalent.

**Step 3 — audits/inventory-*.md retirement (three-step policy).** (1) stop
generating full structural bodies in `renmark/audit.py`'s inventory writer,
emit only a delta-vs-`project-map.md` pointer going forward; (2) leave
existing inventory files where step 2 archived them; (3) any reader
currently treating an inventory file as source-of-truth redirects to
`project-map.md`. Safe: `lifecycle-contract.md` Closing §A already resolved
`project-map.md` as sole canonical home. Rollback: revert the
`renmark/audit.py` diff — no data was deleted, only future-generation
behavior changed.

**Step 4 — state/ scratch GC.** For every feature/plan already at
`released` in git-log-visible `lifecycle.json` history, delete
`escalations/task-N/*`, `_wave-prompts/task-N.json`, `handoffs/*.raw.md`
older than 14 days. Safe: regenerable by re-dispatch, task-scoped, the
global safe-deletion predicate's 5 conditions all hold once a feature is
released. Rollback: none needed at file level (nothing downstream reads
these once released); if wrongly deleted before release, re-run the
specific wave/dispatch to regenerate.

**Step 5 — debug/ repro-repo cleanup.** For the one session with a nested
`repro-repo/.git` tree (`20260730-130449-c190`), confirm its fix commit is
reachable from `main` (`git merge-base --is-ancestor <sha> main`), then
delete `repro-repo/`, keep `session.md`. Rollback: re-run the session's
repro steps from `session.md`'s recorded reproduction commands (the
narrative documents how to regenerate it).

**Step 6 — README.md refresh.** Update `.renmark/README.md`'s committed/
gitignored directory list to match reality (`roadmap/`, `reports/`,
`rethink/`, `ledger/` are currently undocumented per survey.md §13). Pure
docs edit, trivially revertible via git.

Each step is independently revertible via git (git-tracked artifacts) or
via the stated regeneration command (gitignored/derived artifacts) — no step
depends on a later step succeeding first.

## 6. Hermes startup allowlist

Codify the *already-narrow* behavior `preamble.py` exhibits today (survey.md
§4 item 5, verified directly from source) as an explicit, enforced
constant — smallest extension: add one frozenset to
`renmark/lifecycle/preamble.py` (the module that already performs these
reads) rather than a new module:

```python
# renmark/lifecycle/preamble.py
HERMES_STARTUP_ALLOWLIST: frozenset[str] = frozenset({
    ".renmark/state/lifecycle.json",
    ".renmark/state/program.json",
    ".renmark/state/delivery.json",
    ".renmark/state/mode.json",
    ".renmark/state/agency.json",
    ".renmark/state/tasks.json",
    ".renmark/state/compact_checkpoint.json",
    ".renmark/state/last-skill.json",
    ".renmark/memory/INDEX.md",
    ".renmark/config.json",
})
```

Enforcement: a new deterministic test (`tests/test_preamble_allowlist.py` —
new test file, not new production code) that greps `skill_preamble`'s call
graph in `preamble.py` for any `open`/`Path(...).read_text`/`read_json`-style
call and asserts every literal path argument is a member of
`HERMES_STARTUP_ALLOWLIST` (or is dynamically built strictly from one of
those literals, e.g. joining `repo` + an allowlisted relative path — no
`rglob`/`glob`/`iterdir` calls permitted inside `skill_preamble`'s call
chain at all, which is the actual invariant being protected: never recurse).
This turns "we verified it's narrow today" into "CI fails if it ever grows"
without touching `preamble.py`'s runtime behavior — the allowlist constant is
new, but it is documentation-as-code for exactly what that module already
does, per this task's framing.

## 7. Before/after metrics

Using survey.md's actual counts (all figures approximate/flagged per
survey.md's own caveats — no `du`/`find -printf` in that session):

| | Before (today) | After Step 1 only | After full migration (Steps 1–6) |
|---|---|---|---|
| File count | ~2,168 | ~438 (−1,730 unpacked-version files) | ~410–420 (−~20 more from audits/state/debug rotation moves, which relocate not delete, plus a handful of true deletes in state-scratch/debug) |
| Bytes | ~10–22 MB | ~0.3–2 MB (version/ zips only, tens KB–low-MB each vs. 10–20+ MB unpacked) | ~1–3 MB live tree + archived/moved content preserved under `archive/` subfolders (not deleted, so total repo bytes on disk barely changes past Step 1 — only *live/discoverable* bytes shrink) |
| Injected-context chars/tokens | Unchanged by this migration — Phase 1 already found `skill_preamble()` never recurses into audits/reviews/rethink/reports/debug/version (survey.md closing summary); those families were never startup-injected to begin with | Unchanged | Unchanged at startup; §6's allowlist makes "unchanged" an enforced invariant rather than an observation. The only context-injecting families per survey.md's table (`plans` active-only, `reviews` bounded status field, `state` narrow subset, `memory` bounded on-demand, `ledger` bounded lookup, `roadmap`, `config.json`) are untouched by this migration — none of them are deleted or resized by Steps 1–6 |

Step 1 alone removes ~80% of all `.renmark/` files and the overwhelming
majority of bytes, at the lowest risk of any step — confirms
`lifecycle-contract.md`'s framing of it as the single highest-leverage
action.

## 8. Rollback and compatibility tests

- **`pytest -q`** — full existing suite must stay green before and after
  each migration step (baseline-then-compare per CLAUDE.md's pre-refactor
  protocol); specifically exercises `renmark/reports.py`'s release-link
  resolution once Step 1's redirect lands.
- **Resume-from-lifecycle.json smoke test** (existing pattern, no new
  infra): pick one in-flight feature's `lifecycle.json`, run
  `renmark-execute --get-mode` / the skill's resume path, confirm it reads
  the same live pointer files listed in §6's allowlist and resolves to the
  same `next_recommended` before/after Steps 1–6 (none of those files move).
- **Artifact-path compat check** (new, small, deterministic — belongs next
  to `validate_registry_compliance` in `renmark/hygiene.py` as
  `check_documented_paths_resolve(repo)`): for a fixed sample list (one
  path per artifact type, e.g. the newest `plans/*.plan.md`, the newest
  `reviews/*.review.md`, `rethink/renmark-architecture/target-blueprint.md`,
  `roadmap/program.md`), assert the path still exists at its documented
  location after migration — catches an accidental move/rename of a
  canonical-evidence file, which Steps 1–6 must never do (they only touch
  `ephemeral`-classified paths).
- **`python -m renmark.schemas artifact <path>`** re-run against a sample
  of surviving frontmatter-carrying files — confirms migration didn't
  corrupt any provenance block in a file that was moved (archive-tier moves
  in Steps 2/3 must preserve file bytes exactly; `git mv`/`shutil.move`
  already guarantee this, this test just proves it post-hoc).
- **Rollback drill for Step 1 specifically:** `unzip
  .renmark/version/renmark-v0.39.7.zip -d .renmark/version/v0.39.7/` then
  diff against a pre-deletion `git stash`/tar snapshot taken before Step 1
  runs — proves the stated rollback command is not just plausible but
  produces a byte-identical tree.
