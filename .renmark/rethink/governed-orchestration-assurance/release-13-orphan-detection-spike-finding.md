---
artifact_type: spike-finding
schema_version: 1
created_at: 2026-08-05T00:00:00Z
source_sha: bb0c05111a5c65a1dd96993ecf38a9cb7c544c79
related_plan: .renmark/plans/2026-08-05-governed-orchestration-assurance-release-13.plan.md
generator: sonnet
---

# Release 13 — Orphan-Detection Spike Finding

Bounded, one-session spike. No production code was changed by this task
(verified: `git status --porcelain -- '*.py'` returns empty before and after).
All scenario evidence below comes from either (a) direct calls into the real,
unmodified `renmark` functions against a disposable scratch git repo at
`/tmp/claude-1000/.../scratchpad/orphan-spike/repo` (never this project's real
`.renmark/state/`), or (b) read-only inspection of this repo's actual `git
log`, `.renmark/ledger/events.jsonl`, and `.renmark/state/PAUSED`. Simulation
was used throughout in preference to killing a live `renmark-execute`
process — the on-disk state a real interruption leaves (partial git log,
dangling ledger `work_order`, dirty working tree, stale `PAUSED` file) is
fully reproducible by direct construction, and doing so is safer and more
reproducible than a real kill against this session's own in-flight state.

**Scope caveat:** the functions probed (`completed_task_indices`,
`_cross_check_skip_list`, `_setup_resume_state`) are specifically
`renmark-execute <plan> --resume`'s CLI-level resume path, which the code
handles only for `codex`-executed tasks (`_execute_task` → `_execute_task_codex`
unconditionally — the "nim executor removed" comment at `renmark/cli/_engine.py:547`
confirms only codex reaches this function). Tasks with `executor: sonnet/opus/haiku`
pause with `reason: needs_agent` and are dispatched/committed by the
`/renmark:orchestrate` *skill* layer, which this spike did not have time to
trace for a second, independent resume/skip-list implementation. If that skill
layer has its own git-log-based skip-list, findings 1 and 2 below likely apply
there too (same regex, same `_cross_check_skip_list` shape it can import
from `_engine.py`); if it uses `pipeline.json`/wave-summaries as its primary
skip source, it was not verified in this spike. **Deferred, not assumed
safe.**

## Scenario table

| # | Scenario | Interruption point | State constructed/simulated | Expected resume behavior | Observed resume behavior | Pass/Fail (no duplicate, no orphan) |
|---|---|---|---|---|---|---|
| 1 | Kill mid-wave | After task 1 of a 3-task wave commits (`[renmark] task 1: ...`), before tasks 2–3 dispatch | Scratch repo, 1 real commit matching the resume regex, 2 tasks never touched | Task 1 skipped; tasks 2–3 re-run | `completed_task_indices` → `{1}`; `_cross_check_skip_list({1}, tasks)` → `safe_to_skip={1}, ambiguous={}` | **PASS** |
| 2 | Kill mid-commit | Codex/agent writes `t2.txt` to the working tree; process dies before `git commit` (and before verifier/rollback ever runs) | Scratch repo: task 1 committed, `t2.txt` left as an **untracked, uncommitted** file (`git status --porcelain` → `?? t2.txt`) | Task 2 not skipped (correct); *and* the dirty leftover is cleaned before the fresh attempt | `completed_task_indices` → `{1}` (task 2 correctly excluded, so **no duplicate commit** and **no orphan** in the skip-list sense) — but grep of `renmark/cli/*.py` for `git status`/`git clean`/`git stash` returns **zero matches**, and `_classify_and_rollback` (the only cleanup path, `renmark/cli/_codex_runner.py:137`) is called only inside the *same* in-memory retry loop (`retries_left`), never at `--resume` process startup. The stale `t2.txt` is never proactively cleared before the re-dispatch. | **PASS on skip-list correctness; GAP on pre-flight hygiene** (see Finding B) |
| 3 | Kill after `work_order`, before matching `work_result` | Ledger event ordering per `renmark/cli/_wave_loop.py:368-395`: `_emit_work_order` → `_execute_task` (commits inside here) → `_emit_work_result`. Killed in the gap. | Inspected real `.renmark/ledger/events.jsonl` (24 lines) with a paired-event scan: `work_order` count = 7, `work_result` count = 7, **0 orphans** in the current live ledger. Reasoned through both sub-cases: (3a) commit landed before the kill → git log has the commit, ledger has a dangling `work_order` — resume-safe but audit-trail-broken; (3b) commit never landed → git log has nothing, ledger has a dangling `work_order` — resume re-runs, correct. | Ledger dangling entries should either not affect resume, or should be surfaced somewhere | Grep of `renmark/cli/_run_lifecycle.py` (`_setup_resume_state`) and `renmark/state/commits.py` confirms **the ledger is never read during resume** — `check_dispatch_independence`'s only caller is `_wave_loop.py:240` inside `_inspect_and_track` (an inspection-time check), not the resume path. Resume is git-log-only. So a dangling `work_order` cannot cause a duplicate dispatch or a dropped task — but it **is** a silent audit-trail gap: nothing ever flags "this work_order has no matching work_result," so a partial/interrupted dispatch is invisible to any ledger-based reporting (`--analytics`, `--roadmap`, inspection verdicts) even though `check_dispatch_independence` exists and could, in principle, be run at startup to surface exactly this. | **PASS on duplicate/orphan-dispatch; GAP on observability** (see Finding C) |
| 4 | Kill during `_cross_check_skip_list` re-entering a live run (reused task index across two different plans) | The function itself is pure/synchronous (no I/O, one `for` loop over an already-loaded `done` set) — it cannot itself be "killed mid-execution" in a way that leaves partial state. The realistic manifestation is the docstring's own stated concern: **a git-log commit from Plan A's task N gets misread as Plan B's task N being done**, because renmark task indices are always 1..N sequential and routinely collide across plans. | Scratch repo: committed `[renmark] task 3: add auth module (plan A)`. Constructed **Plan B** — an unrelated 3-task plan whose own task 3 is `refactor db connection pool` targeting `db/pool.py`. Called the real `completed_task_indices` + `_cross_check_skip_list` against Plan B's task list. | `_cross_check_skip_list`'s own docstring says exactly this case ("reused task numbers... a task that was never run in THIS plan can be silently marked done — the single most expensive observed failure mode") should land the index in `ambiguous`, not `safe_to_skip` | `safe_to_skip = {3}`, `ambiguous = {}`. **Plan B's task 3 (`db/pool.py`) is silently marked done and would be skipped — it is never touched, no warning is printed.** The function only checks `idx in plan_indices` (index membership), never title/target identity, so any index collision across plans passes the check. Confirmed this is not a contrived edge case: `git log --pretty=%s --all` in **this real repo** shows 29 commits matching the resume regex across its full history, and index `1` alone appears in **12 different plans' commits** — the collision precondition is the common case here, not the exception. | **FAIL — orphan produced** (Finding A, the headline gap) |
| 5 | (optional) Kill during a `PAUSED` usage-limit window, resume via `heartbeat.auto_resume` | Read `renmark/heartbeat.py` in full: `auto_resume()` is a pure subprocess wrapper — `subprocess.run(["renmark-execute", "--resume"], ...)`, zero LLM calls, zero additional state logic of its own | Inspected the real, currently-live `.renmark/state/PAUSED` (`reason: needs_agent`, `run_id: 20260805-034003-9c81`, plan `release-3`) rather than fabricating one — this repo has a genuine in-flight pause right now, left untouched | `auto_resume` should not introduce any *new* resume-correctness behavior beyond what `--resume` already does | Confirmed by code reading only (no execution against the live PAUSED state, to avoid disturbing this session's own in-flight run): `auto_resume` adds nothing of its own — it is a thin, correct delegation. It therefore **inherits Findings A and B verbatim**, and inherits them into an **unattended cron context** where the printed `ambiguous`-set warning (the one safety net Finding A's collision case would have produced, had the check worked) would go to a log nobody is watching in real time. | **PASS on `heartbeat.py` itself; inherits upstream gaps A/B with reduced visibility in unattended mode** |

## Findings (evidence-backed, separated from recommendations)

- **Finding A (blocking).** `_cross_check_skip_list` (`renmark/cli/_engine.py:274-312`) validates a resume skip-list candidate by **index membership in the current plan only**. It does not compare title, target, or any other task-identity field. Because renmark task indices restart at 1 for every plan and this repo's real history already has 29 matching commits with heavy index reuse (index `1` × 12, `6` × 4, `5` × 4, `8` × 3, `4` × 3, `14` × 3, ...), a resumed run whose plan happens to reuse an index that some *unrelated* prior plan also used and committed will silently treat that unrelated commit as proof the current task is done — skipping real work with **no warning printed**, because the check that exists to catch exactly this (its own docstring names this the "single most expensive observed failure mode") does not check the one thing that would catch it.
- **Finding B (deferrable, but real).** No code path in `renmark/cli/*.py` inspects or cleans working-tree state at `--resume` startup (`grep` for `git status`/`git clean`/`git stash` across `renmark/cli/*.py` returns zero hits). `_classify_and_rollback` — the only rollback/cleanup mechanism — fires solely inside the in-memory verifier-retry loop of the *same* process invocation, never on a fresh `--resume`. A process killed after a codex/agent wrote files to `task.target` but before `git commit` leaves that dirty state in the tree indefinitely; the next `--resume` dispatches straight into it without cleanup.
- **Finding C (deferrable, observability-only).** The ledger (`WorkOrder`/`WorkResult` pairs) is never consulted by the resume path — confirmed no caller of `read_ledger_events`/`check_dispatch_independence` exists in `_run_lifecycle.py` or `commits.py`; the only caller of `check_dispatch_independence` is the inspection path in `_wave_loop.py:240`. This means dangling `work_order` events (dispatch started, no matching result — e.g. from an interruption) never surface as a signal anywhere, even though the primitive to detect them (`check_dispatch_independence`) already exists and is already wired for a *different* purpose. Does not cause duplicate dispatch or dropped tasks (git log remains authoritative), but it is a real audit-trail/observability gap.
- **No gap found** in Scenarios 1 and 3's core resume-correctness question (no duplicate dispatch, no task silently dropped when the plan/git-log correlation is unambiguous), and none in `heartbeat.py` itself (Scenario 5) — it is a correct, inert delegation that inherits, rather than introduces, risk.

## Recommendation

**Gaps found — Finding A (blocking, headline) and Findings B/C (deferrable) —
recommend a follow-up plan capped at ~2 sessions per the roadmap.**

Rationale for the 2-session cap: Finding A's fix is scoped and mechanical —
`_cross_check_skip_list` needs a task-identity check beyond index membership
(e.g. compare `title`/`target`, or better, stop relying on commit-message
index parsing entirely and instead have `renmark-execute` stamp a
plan-content-hash or `plan_path` into the commit trailer so
`completed_task_indices` can positively bind a commit to *this* plan, not
just *some* plan with a matching index). Finding B's fix is a single
pre-flight `git status --porcelain -- <targets>` + `_classify_and_rollback`
call added at the top of `_setup_resume_state` (the mechanism to do the
cleanup, `_classify_and_rollback`, already exists — it's just never invoked
at the right time). Finding C's fix, if pursued, is a bounded read-only
report (an "unresolved work_order" warning line printed alongside the
existing `ambiguous`-index warning) using the already-wired
`check_dispatch_independence`/`read_ledger_events` primitives. None of the
three requires new state, a new file format, or an architecture change —
all are localized to functions already read in this spike
(`renmark/cli/_engine.py`, `renmark/cli/_run_lifecycle.py`,
`renmark/state/commits.py`).

Finding A should be treated as the priority item in that follow-up: it is
the one scenario where this spike observed an actual silent-orphan result
(a real task silently marked done and skipped, zero warning), matching
exactly the failure mode this program's own documentation names as the
single most expensive one observed to date — and the evidence shows the
existing guard against it does not, in fact, guard against it.

## Evidence appendix

**Scratch repo location (disposable, not part of this repo):**
`/tmp/claude-1000/-home-renmark-projects-renmark/720b837f-49d3-4987-98ce-823bf23ed41c/scratchpad/orphan-spike/repo`
— branches `scenario1`, `scenario2` (built from `scenario1`), `scenario4`
(built from `init`). This project's real `.renmark/state/` and `.renmark/ledger/`
were only ever *read*, never written, during this spike.

**Scenario 1/2 git log (scratch repo):**
```
e5c6c6b [renmark] task 1: build the widget
fc0e1e9 init
```
Scenario 2 adds an untracked `t2.txt` on top (`git status --porcelain` →
`?? t2.txt`), no new commit.

**Scenario 4 git log (scratch repo):**
```
d342f74 [renmark] task 3: add auth module (plan A)
fc0e1e9 init
```
Python evidence (verbatim run output):
```
SCENARIO 4: raw_done= {3}
plan_b task 3 title: refactor db connection pool  target: db/pool.py
safe_to_skip= {3}  ambiguous= set()
!!! GAP CONFIRMED: plan B's task 3 (db/pool.py refactor) is treated
    as already-done and SKIPPED, because plan A's UNRELATED task 3
    ('add auth module') happened to share the same index and matched
    the commit-message regex. db/pool.py is never touched.
```

**Real-repo index-collision census** (`git log --pretty=%s --all | grep -oiE
"^\[?(renmark|codex|nim|manual)\]?\s+task\s+[0-9]+" | grep -oE "[0-9]+" | sort
-n | uniq -c | sort -rn`, top entries):
```
12 1
 4 6
 4 5
 3 8
 3 4
 3 14
 2 7
 2 3
 2 2
 2 11
```
(29 total matching commits out of 1106 in `git log --oneline | wc -l`, i.e.
most real commits in this repo use the project's own `type(scope): summary`
convention rather than the `[renmark] task N:` format — see Scope caveat
above.)

**Live ledger pairing check** (`.renmark/ledger/events.jsonl`, 24 lines,
read-only): `work_order` count = 7, `work_result` count = 7, orphan
`work_order`s = `{}` (none) at the time of this spike.

**Live PAUSED file** (`.renmark/state/PAUSED`, read-only, untouched):
```json
{
  "run_id": "20260805-034003-9c81",
  "plan_path": ".renmark/plans/2026-08-05-governed-orchestration-assurance-release-3.plan.md",
  "last_task_index": 1,
  "reason": "needs_agent",
  ...
}
```
This is a genuine, currently-live `needs_agent` pause (not a crash) —
useful confirmation that `PAUSED` files are in active real-world use in
this repo, but not itself a crash scenario; left untouched per the task's
explicit instruction not to risk corrupting an in-flight run.

**Key line references:**
- `renmark/cli/_engine.py:274-312` — `_cross_check_skip_list` (Finding A)
- `renmark/cli/_engine.py:547-550` — `_execute_task` unconditionally routes to codex (Scope caveat)
- `renmark/cli/_run_lifecycle.py:42-71` — `_setup_resume_state`
- `renmark/state/commits.py:13-37` — `completed_task_indices` + `_COMMIT_TASK_RE`
- `renmark/cli/_wave_loop.py:368-395` — `_emit_work_order` → `_execute_task` (commit) → `_emit_work_result` ordering (Scenario 3)
- `renmark/cli/_wave_loop.py:240` — sole caller of `check_dispatch_independence` (Finding C)
- `renmark/cli/_codex_runner.py:137-167` — `_classify_and_rollback` (Finding B), only called from the in-memory retry loop
- `renmark/heartbeat.py:78-105` — `auto_resume`, a pure `renmark-execute --resume` subprocess delegation (Scenario 5)
