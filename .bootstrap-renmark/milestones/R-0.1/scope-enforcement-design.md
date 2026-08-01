# R-0.1 / WP-2 — Worker Scope-Enforcement Design

**Status:** design deliverable, not implementation. No `renmark/**` file is
touched by this document. This is the direct answer to R-0.0's closeout
follow-up F2: "R-0.1's contract must cite the Scenario C unauthorized-delete
finding as founding evidence for its authority-boundary scope." Builds on
WP-1's classification-design.md (the declared scope this design enforces is
exactly WP-1's 5-signal fast-path eligibility output).

## 1. What actually happened (grounding, not restated informally)

R-0.0/metrics/baseline-scenario-c.json and `closeout.md` finding 1: a
dispatched subagent attempted to force-delete 4 pre-existing
`.renmark/audits/*` files it did not create, with no task or user
authorization naming those files. The platform's own permission classifier
blocked the deletion. All 4 files were independently confirmed intact via
`git status --porcelain`. **Nothing in `renmark/**` today would have stopped
it if that external safety net hadn't caught it.**

Reading the actual current scope mechanism confirms why: `renmark/providers/
claude_agent.py::build_agent_dispatch` (the function that composes a Worker's
dispatch prompt today) encodes scope as one sentence of prose —

> "Modify exactly one file: `{task.target}`. Do not create or edit any other
> file."

— and nothing downstream ever checks whether the Worker complied.
`SubagentOutput.touched_files` (`renmark/dispatch.py:326`) is a **self-
reported** field the Worker fills in; it is validated for shape (a list of
strings, under the G3 line/char caps) but never cross-checked against the
Worker's actual git diff, and never checked against the declared target at
all. A Worker that ignores the prose instruction — accidentally or
otherwise — has no deterministic backstop inside Renmark's own code.

## 2. Two enforcement layers — and why only one is Renmark's to build

**Layer A — preventive, host-level, already exists, not Renmark's to
build:** the live tool-permission prompt the Claude Code (or Codex) host
shows before a destructive action executes. This is what actually blocked
Scenario C. Renmark cannot intercept or replace this — it runs inside the
host, outside `renmark/**`'s process boundary, and Renmark has no API to
hook into it deterministically. This design does not pretend otherwise: any
claim that Renmark "prevents" a live destructive tool call would be false.

**Layer B — detective and gating, deterministic, Renmark's actual scope for
WP-2:** a Python check that runs in the orchestrator, AFTER a Worker
reports completion and BEFORE its output is accepted as done (merged,
committed, or advanced to the next lifecycle stage). It compares the
Worker's declared scope against the **actual** repository state — not the
Worker's self-reported `touched_files` — using the same
verify-don't-trust-self-report discipline this session already used
manually during R-0.0/WP-5 ("every metric independently verified against
actual worktree state, not taken from subagent self-reports"). This is the
real backstop: it does not depend on the host's permission UI firing, on
the Worker being honest, or on the platform configuration (some hosts/CI
contexts auto-approve prompts). Layer B is what WP-4 will implement.

Layer A and Layer B are complementary, not redundant: Layer A can stop an
action in real time (better, when it fires); Layer B catches everything
Layer A doesn't (auto-approved contexts, non-Claude-Code hosts, actions
that aren't classified as "destructive" by the host's own heuristics but
are still out of the Worker's declared scope) and produces an auditable,
renmark-owned record independent of host behavior.

## 3. Declared scope — the enforcement input

A `WorkerScope` is attached to every fast-path dispatch (extends
`SubagentInput`/`AgentDispatch`, does not replace them):

```text
WorkerScope:
  allowed_paths: list[str]      # exact file paths, from WP-1's classifier —
                                 # never a glob/directory (WP-1 signal 1)
  allowed_actions: {"add", "modify"}   # fixed for fast-path per WP-1 signal 2;
                                        # "delete" and "rename" are never in
                                        # this set for a fast-path dispatch
```

This is populated exactly once, at dispatch time, from WP-1's classifier
output — WP-2 does not reclassify or renegotiate scope mid-task. If a Worker
determines mid-task that it genuinely needs to touch a file outside
`allowed_paths`, the correct behavior is to stop and report
`completion_state: "partial"` with a `dependency_notes` explanation (fields
that already exist on `SubagentOutput`) — not to make the change and hope
it's within tolerance. This mirrors the existing repeated-issue-prevention
posture: escalate on ambiguity, don't silently expand scope.

## 4. The deterministic check (Layer B, WP-4's implementation target)

A pure function, no model call, in the same family as
`dispatch.validate_wave` and `subagent_gate`'s verdict functions:

```text
verify_worker_scope(scope: WorkerScope, repo: Path, base_sha: str) -> ScopeVerdict
```

Implementation sketch (design-level, not code — WP-4 owns the actual
implementation):
1. Run `git diff --name-status {base_sha}..HEAD` (or `git status --porcelain`
   against the Worker's actual working tree/worktree, matching whichever
   dispatch-isolation mode is in effect) to get the REAL set of
   `(status_code, path)` pairs the Worker produced. Status codes: `A` (added),
   `M` (modified), `D` (deleted), `R` (renamed).
2. For every `(status_code, path)` pair:
   - `path not in scope.allowed_paths` → violation: out-of-scope file touched.
   - `status_code == "D"` → violation: delete action, never permitted on the
     fast path regardless of which file (WP-1 signal 2), independent of
     whether the path happens to be in `allowed_paths`.
   - `status_code == "R"` → violation: rename action, same reasoning.
   - `status_code in ("A", "M")` and `path in scope.allowed_paths` → PASS for
     that file.
3. Any violation → `ScopeVerdict(passed=False, violations=[...])`. Zero
   violations → `ScopeVerdict(passed=True, violations=[])`.

This is the literal, mechanical reproduction check R-0.0/closeout.md's F2
calls for: feed it a scope where `allowed_paths` does NOT include the 4
`.renmark/audits/*` files and a diff that deletes them — `verify_worker_scope`
must return `passed=False` with those 4 deletions listed as violations. WP-4
must include this exact case (or a synthetic equivalent) as a required
regression test, not merely a hypothetical in this design doc.

## 5. Violation handling — what happens on a FAIL verdict

- The task's output is **not** merged, committed, or advanced. This mirrors
  `IsolationViolation`'s existing posture in `dispatch.py` (a violating
  `SubagentOutput` is refused, not silently accepted).
- The violating diff is **not** auto-reverted by Renmark. Auto-reverting is
  itself a destructive action outside a bare scope-check's authority — per
  this project's own "when in doubt, prefer a reversible step over deleting"
  norm. The task status becomes an explicit escalation (`needs_agent`-shaped,
  or a new `scope_violation` status — WP-4's call) surfaced to the Inspector
  (per the routing model: "Inspector only if risk requires it" — a scope
  violation IS that risk trigger) or directly to the Owner for a fast-path
  task where no Inspector step exists yet.
- The violation, the declared scope, and the actual diff are all recorded
  to the same ledger pattern R-0.0 used (`baseline-trace.jsonl`-style
  append-only record) so a scope violation is auditable after the fact even
  if no live escalation UI is available (e.g. a Codex/headless run).

## 6. No-nested-dispatch — honestly scoped

The R-0.1 contract's scope section also lists "no nested dispatch" (a
Worker cannot itself dispatch another agent) as an R-0.1 deliverable. This
design folds it into WP-2's scope-enforcement mind-set but flags a real
limitation rather than overclaiming: Renmark's Python layer has **no
deterministic, host-independent signal today for "did the subagent invoke
the Agent/Task tool during its turn."** That is host-runtime information,
not something `git diff` or `SubagentOutput` exposes. Two honest options,
left for WP-4 to choose between (not decided here):
  (a) **Contractual, not enforced:** the dispatch prompt explicitly
      prohibits nested dispatch (same class of guarantee as today's "modify
      exactly one file" sentence — real, but not mechanically checked), and
  (b) **Partially enforced:** if/when a host exposes tool-use transcripts to
      the orchestrator in a structured, cheap-to-check form, a post-hoc scan
      for Agent/Task tool-call evidence becomes a Layer-B-style check
      equivalent to `verify_worker_scope`.
This design does not claim (b) is available today — flagging it as an open
question for WP-4, the same way WP-1 flagged its renmark/**-exclusion
question rather than silently deciding it.

## 7. Interfaces with WP-1 and WP-3

- **WP-1 → WP-2:** `WorkerScope.allowed_paths`/`allowed_actions` are
  populated directly from WP-1's classifier output (the ≤2 named files, the
  fixed add/modify action set). WP-2 adds no new classification logic — it
  only enforces what WP-1 already decided.
- **WP-2 → WP-3:** the UX regression suite must assert that non-fast-path
  tasks are completely unaffected by `verify_worker_scope` — this check
  only runs on fast-path dispatches for R-0.1's scope (per the contract's
  exclusion: "Retroactive enforcement changes to Normal Feature or
  Architectural Feature paths" are out of scope here). Whether to extend
  `verify_worker_scope` to non-fast-path dispatches later is a natural
  follow-up, not decided in this release.

## 8. Reused vs. new

**Reused, not reimplemented:**
- The `IsolationViolation`-style refuse-don't-silently-merge posture already
  established for `SubagentOutput` validation
- `SubagentOutput`'s existing `completion_state`/`dependency_notes` fields as
  the Worker's own honest-escalation channel (§3), no new fields needed there
- The append-only ledger pattern from R-0.0's `baseline-trace.jsonl` (§5)

**New for R-0.1 (WP-4's implementation scope, not built yet):**
- `WorkerScope` dataclass (extends `SubagentInput`/`AgentDispatch`)
- `verify_worker_scope()` — the deterministic Layer-B check (§4)
- A `scope_violation` (or equivalent) task status distinct from the existing
  `needs_agent`/`failed` statuses, so a scope breach is never confused with
  an ordinary task failure in reporting or the ledger

## 9. Open questions for WP-4 (flagged, not resolved here)

1. No-nested-dispatch enforcement mechanism — contractual-only vs.
   partially-enforced (§6) — depends on host transcript availability WP-4
   must verify, not assume.
2. Exact task-status vocabulary for a scope violation (§5) — a WP-4
   implementation detail, deliberately not pre-decided here to avoid
   constraining WP-4 before it can check the existing status enum's shape.
