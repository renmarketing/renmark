---
artifact_type: plan
schema_version: 1
created_at: 2026-08-07T23:20:00Z
source_sha: 8486b22
related_plan: .renmark/rethink/cross-host-native-tool-leverage/roadmap.md
generator: sonnet
---

# Plan — cross-host-native-tool-leverage Release 4

Close REQ-31's Codex gap: a live, interactive Codex session acting as host today has
zero `task_tracking` calls anywhere in its dispatch path (only the headless
`renmark-execute` subprocess path — `renmark/cli/_wave_loop.py` — is wired). This adds
`renmark-execute --task-create`/`--task-in-progress`/`--task-complete` CLI subcommands
wrapping `renmark.task_tracking`'s existing functions, wires an `orchestrate/SKILL.md`
instruction telling a live Codex session to shell out to them, and adds a `source`
field (`"codex-live"` vs `"codex-headless"`) so `.renmark/state/tasks.json` entries are
observable per origin. Per the roadmap's compatibility guarantee, the existing headless
path's behavior is unchanged — only tagged with its own source value.

**Do not change:** `build_host_dispatch_plan`'s "no dispatch, no state/ledger writes"
invariant — these are plain CLI subcommands, never called from `dispatch.py`. No change
to any existing `create_or_reuse_task`/`mark_in_progress`/`complete_task` call signature
beyond one new optional keyword (`source`, default `""`) — fully backward compatible.

### Task 1: add source field to TaskRecord + create_or_reuse_task
- **mode:** B
- **target:** renmark/task_tracking.py
- **complexity:** medium
- **executor:** sonnet
- **role:** code-implementer
- **parallel_group:** 1
- **est_tokens:** 700
- **est_cost_usd:** 0.0291
- **verifier:** python3 -m pytest -q tests/test_task_tracking.py tests/test_task_tracking_contract.py tests/test_task_tracking_engine_wiring.py 2>&1 | tail -3
- **serves:** cross-host-native-tool-leverage Release 4 (REQ-31)
- **spec:**
  In `renmark/task_tracking.py`:
  1. On the `TaskRecord` dataclass (around line 121), add a new field
     `source: str = ""` — place it after `close_reason: str | None = None` and before
     `history: list[str] = field(default_factory=list)` (the mutable-default field must
     stay last since it's the only one using `field(...)`, and dataclass fields without
     defaults can't follow ones with defaults — `source` has a default so this is safe
     anywhere before `history`).
  2. On `create_or_reuse_task` (around line 210), add a new keyword-only parameter
     `source: str = ""` to the signature (after `order_id: str = ""`), and pass it
     through to the `TaskRecord(...)` construction inside the function (after
     `order_id=order_id,`): `source=source,`.
  3. Do not add `source` to any other function's signature (`mark_in_progress`,
     `complete_task`, etc.) — it is set once at creation time only, per the roadmap's
     scope.
  4. Do not change `read_tasks`/`write_tasks` — they already round-trip arbitrary
     dataclass fields via `asdict`/`TaskRecord(**fields)`, so a missing `source` key in
     old persisted JSON degrades safely to the default `""` with zero code change there.
- **Do not change:** every existing caller of `create_or_reuse_task` (in
  `renmark/cli/_wave_loop.py` and any tests) must keep working unchanged since `source`
  defaults to `""` — do not make it positional or required.

### Task 2: tag existing headless call sites with source="codex-headless"
- **mode:** B
- **target:** renmark/cli/_wave_loop.py
- **complexity:** simple
- **executor:** sonnet
- **role:** code-implementer
- **parallel_group:** 2
- **est_tokens:** 350
- **est_cost_usd:** 0.0271
- **verifier:** python3 -m pytest -q tests/test_task_tracking_engine_wiring.py 2>&1 | tail -3
- **serves:** cross-host-native-tool-leverage Release 4 (observability hook)
- **spec:**
  In `renmark/cli/_wave_loop.py`, add `source="codex-headless",` as a new keyword
  argument to all THREE existing `_task_tracking.create_or_reuse_task(...)` calls (do
  not touch `mark_in_progress`/`complete_task`/`complete_worker_task`/`record_failure`/
  `record_blocker` calls — `source` is create-only):
  1. In `_create_parent_task` (around line 107): the call creating `parent_task_id`
     (`title=f"Execute plan {plan_path}", role="orchestrator", scope=plan_path,
     verification_expectation="every dispatched task independently verified"`).
  2. In `_track_worker_dispatch` (around line 161): the call creating `worker_task_id`
     (`title=task.title or task.spec or f"task {task.index}", role=task.role or
     task.executor or "unknown", scope=task.target, verification_expectation=
     task.verifier, parent_id=parent_task_id, dispatch_identity=dispatch_identity,
     order_id=order_id`).
  3. In `_inspect_and_track` (around line 285): the call creating `verify_task_id`
     (`title=f"Verify task {task.index}", role="inspector", scope=task.target,
     verification_expectation=task.verifier, parent_id=parent_task_id,
     depends_on=(worker_task_id,), dispatch_identity=_INSPECTOR_DISPATCH_IDENTITY`).
  This task depends on Task 1 landing first (the `source` keyword must exist on
  `create_or_reuse_task` before these calls can pass it).

### Task 3: add task-tracking CLI subcommand handler
- **mode:** B
- **target:** renmark/cli/_dispatch_flags.py
- **complexity:** medium
- **executor:** sonnet
- **role:** code-implementer
- **parallel_group:** 2
- **est_tokens:** 900
- **est_cost_usd:** 0.0327
- **verifier:** python3 -m pytest -q tests/test_cli_task_mode.py 2>&1 | tail -3
- **serves:** cross-host-native-tool-leverage Release 4 (REQ-31)
- **spec:**
  In `renmark/cli/_dispatch_flags.py`:
  1. Add `from renmark import task_tracking as _task_tracking` near the existing
     `from renmark import hygiene` / `from renmark import lifecycle as _lifecycle`
     imports at the top of the file.
  2. Add a new function `_dispatch_task_tracking_flags(args: argparse.Namespace, repo:
     Path) -> int | None`, following the exact style of `_dispatch_compact_flags` in
     this same file (a one-line docstring, `if args.<flag>: ... return 0/2`, falling
     through to `return None` if none of the flags are set):
     ```python
     def _dispatch_task_tracking_flags(args: argparse.Namespace, repo: Path) -> int | None:
         """Handle --task-create/--task-in-progress/--task-complete (REQ-31 Codex
         live-session task tracking; cross-host-native-tool-leverage Release 4).

         Wraps renmark.task_tracking for a live, interactive Codex session, which has
         no native TaskCreate/TaskUpdate tool of its own. Tags every task it creates
         with source="codex-live" to distinguish from the pre-existing headless
         renmark-execute subprocess path (source="codex-headless").
         """
         if args.task_create:
             rec = _task_tracking.create_or_reuse_task(
                 repo,
                 args.task_create,
                 title=args.title or "",
                 role=args.role or "",
                 scope=args.scope or "",
                 verification_expectation=args.verification_expectation or "",
                 parent_id=args.parent_id,
                 source="codex-live",
             )
             print(f"task {rec.task_id} tracked (status={rec.status})")
             return 0
         if args.task_in_progress:
             try:
                 rec = _task_tracking.mark_in_progress(repo, args.task_in_progress)
             except _task_tracking.UnknownTaskError as e:
                 print(f"ERROR: {e}", file=sys.stderr)
                 return 2
             print(f"task {rec.task_id} in_progress")
             return 0
         if args.task_complete:
             try:
                 rec = _task_tracking.complete_task(
                     repo,
                     args.task_complete,
                     artifact_path=args.artifact_path or "",
                     result_summary=args.result_summary or "",
                 )
             except (_task_tracking.UnknownTaskError, _task_tracking.MissingEvidenceError) as e:
                 print(f"ERROR: {e}", file=sys.stderr)
                 return 2
             print(f"task {rec.task_id} completed (artifact={rec.artifact_path})")
             return 0
         return None
     ```
  3. `sys` is already imported in this file (used by other dispatch functions) — do not
     re-import it.
  4. This task depends on Task 1 landing first (`source=` keyword must exist on
     `create_or_reuse_task`).

### Task 4: wire task-tracking CLI flags into argparse + main()
- **mode:** B
- **target:** renmark/cli/_engine.py
- **complexity:** medium
- **executor:** sonnet
- **role:** code-implementer
- **parallel_group:** 3
- **est_tokens:** 600
- **est_cost_usd:** 0.0318
- **verifier:** python3 -m pytest -q tests/test_cli_task_mode.py tests/test_engine_resume_crosscheck.py 2>&1 | tail -3
- **serves:** cross-host-native-tool-leverage Release 4 (REQ-31)
- **spec:**
  In `renmark/cli/_engine.py`:
  1. Add `_dispatch_task_tracking_flags` to the existing multi-line
     `from ._dispatch_flags import (...)` block that already imports
     `_dispatch_agency_flags, _dispatch_artifact_hygiene_flags, _dispatch_compact_flags,
     _dispatch_handoff_flags, _dispatch_mode_read_flags, _dispatch_proactive_mode_flags,
     _dispatch_query_flags` (around line 100-108) — add it alphabetically to that same
     import group, do not create a new import statement.
  2. In `main()`'s argparse setup (after the existing `--review-package` argument,
     before `args = ap.parse_args(argv)` around line 784), add six new arguments:
     ```python
     ap.add_argument(
         "--task-create",
         metavar="TASK_ID",
         help="(REQ-31) create/reuse a tracked task for a live Codex session; requires --title, --role, --scope, --verification-expectation",
     )
     ap.add_argument("--title", metavar="TITLE", help="(with --task-create) task title")
     ap.add_argument("--role", metavar="ROLE", help="(with --task-create) task role")
     ap.add_argument("--scope", metavar="SCOPE", help="(with --task-create) task scope, e.g. target file")
     ap.add_argument(
         "--verification-expectation",
         metavar="TEXT",
         help="(with --task-create) what verification must exist before completion",
     )
     ap.add_argument("--parent-id", metavar="TASK_ID", help="(with --task-create) optional parent milestone task id")
     ap.add_argument(
         "--task-in-progress",
         metavar="TASK_ID",
         help="(REQ-31) mark an existing tracked task in_progress",
     )
     ap.add_argument(
         "--task-complete",
         metavar="TASK_ID",
         help="(REQ-31) mark an existing tracked task completed; requires --artifact-path and --result-summary",
     )
     ap.add_argument("--artifact-path", metavar="PATH", help="(with --task-complete) artifact path evidencing completion")
     ap.add_argument("--result-summary", metavar="TEXT", help="(with --task-complete) one-line result summary")
     ```
  3. After `args = ap.parse_args(argv)` (around line 785), add validation alongside the
     existing `if (args.propose or args.emit_cron) and not args.scan:` style checks:
     ```python
     if args.task_create and not (args.title and args.role and args.scope and args.verification_expectation):
         print("--task-create requires --title, --role, --scope, and --verification-expectation", file=sys.stderr)
         return 2
     if args.task_complete and not (args.artifact_path and args.result_summary):
         print("--task-complete requires --artifact-path and --result-summary", file=sys.stderr)
         return 2
     ```
  4. Add `lambda: _dispatch_task_tracking_flags(args, repo),` to the existing
     `for _handler in (...)` tuple (around line 802-810) — add it as a new line in that
     tuple, anywhere among the existing entries.
  5. Update the `ap.error(...)` message (around line 816-820) that lists flags valid
     without a plan path — append `/ --task-create / --task-in-progress /
     --task-complete` to the existing list text.
  6. Do not change any existing argparse argument, validation check, or handler already
     in this file — purely additive.
- **Do not change:** the existing `--task`/`--output` ad-hoc Codex dispatch flags (a
  different, pre-existing mechanism) — do not conflate or merge them with the new
  `--task-create`/`--task-in-progress`/`--task-complete` flags.

### Task 5: wire live-Codex task-tracking instruction into orchestrate/SKILL.md
- **mode:** B
- **target:** plugin/skills/orchestrate/SKILL.md
- **complexity:** simple
- **executor:** sonnet
- **role:** docs-editor
- **parallel_group:** 1
- **est_tokens:** 400
- **est_cost_usd:** 0.0312
- **verifier:** grep -q "task-create" plugin/skills/orchestrate/SKILL.md && echo OK
- **serves:** cross-host-native-tool-leverage Release 4 (REQ-31)
- **spec:**
  In `plugin/skills/orchestrate/SKILL.md`'s Overview section, the existing paragraph
  (starting "Dispatches plan tasks in waves...") ends with a sentence that says:
  "`renmark.task_tracking`'s Python-side mirror is wired specifically into the
  `codex`/subprocess executor path in `renmark/cli/_engine.py`, where no live session
  exists to call native tools."

  Add ONE new sentence immediately after that one, in the same paragraph, saying
  (adapt wording to fit the surrounding prose naturally, but preserve this meaning
  exactly): "**When this skill is run by a live, interactive Codex session**
  (host-native `spawn_agent`/`wait_agent` dispatch, not the headless `renmark-execute`
  subprocess path), the executing agent shells out to `renmark-execute --task-create`
  (with `--title`/`--role`/`--scope`/`--verification-expectation`) before each
  dispatch, `renmark-execute --task-in-progress <id>` immediately before the real
  dispatch call, and `renmark-execute --task-complete <id> --artifact-path <path>
  --result-summary <text>` only once verification evidence exists — mirroring the
  Claude Code `TaskCreate`/`TaskUpdate` pattern above, since Codex has no native
  task-tracking tool of its own. These CLI calls tag `source: "codex-live"` in
  `.renmark/state/tasks.json`, distinct from the headless subprocess path's
  `source: "codex-headless"`."

  Do not restate the full `.shared/task-tracking.md` contract here — this is a
  one-paragraph addition to the existing Overview section, not a new section. Do not
  change anything else in this file.

### Task 6: add CLI test coverage for the new task-tracking subcommands
- **mode:** A
- **target:** tests/test_cli_task_tracking_flags.py
- **complexity:** medium
- **executor:** codex
- **role:** test-writer
- **parallel_group:** 4
- **est_tokens:** 700
- **est_cost_usd:** 0.03
- **verifier:** python3 -m pytest -q tests/test_cli_task_tracking_flags.py 2>&1 | tail -3
- **serves:** cross-host-native-tool-leverage Release 4 (REQ-31)
- **spec:**
  Create `tests/test_cli_task_tracking_flags.py` testing the new
  `--task-create`/`--task-in-progress`/`--task-complete` subcommands end-to-end
  through `renmark.cli._engine.main(argv)` (see `tests/test_cli_task_mode.py` for the
  established pattern of invoking `main()` with an argv list against a `tmp_path` repo
  fixture — read that file first to match its style, including how it initializes a
  minimal git repo / `.renmark/` dir if needed). Use `tmp_path` (pytest fixture) as the
  repo, not the real repo. Cover:

  1. `--task-create <id> --title T --role R --scope S --verification-expectation V`
     returns exit code 0 and prints a line containing the task id; then read back
     `.renmark/state/tasks.json` (via `renmark.task_tracking.read_tasks`) and assert
     the created record has `source == "codex-live"` and `status == "pending"`.
  2. `--task-create` without `--title` (or missing any of the four required flags)
     returns exit code 2 and prints an error mentioning the missing requirement to
     stderr (use `capsys`).
  3. `--task-in-progress <id>` on a task created in step 1 returns exit code 0 and the
     record's status becomes `"in_progress"`.
  4. `--task-in-progress <id>` on an UNKNOWN task id returns exit code 2 (maps to
     `UnknownTaskError`).
  5. `--task-complete <id> --artifact-path P --result-summary R` on the task from step
     3 returns exit code 0 and the record's status becomes `"completed"` with
     `artifact_path == P`.
  6. `--task-complete <id>` WITHOUT `--artifact-path`/`--result-summary` returns exit
     code 2 (the CLI-level required-flags check, not `MissingEvidenceError` — that
     check happens before task_tracking is even called).

  Keep assertions on exit codes and `task_tracking` state — do not assert on exact
  stdout wording beyond "contains the task id" (avoid brittle string-matching).
