# R-0.1 / WP-1 — Small-Task Classification and Routing Design

**Status:** design deliverable, not implementation. No `renmark/**` file is
touched by this document. Produces the classification threshold and routing
rule that WP-4 (implementation) will encode; WP-2 (Worker scope enforcement)
and WP-3 (UX regression suite) build on the same classification.

## 1. Problem this solves

Per `governing-methodology-addendum-01.md`'s routing model, three paths exist
in principle — small task / normal feature / architectural feature — but
today General Contractor has no deterministic rule for choosing between them.
Every request currently goes through the same flow regardless of size. The
only classification signal that exists anywhere in the codebase today is
`Task.complexity` (`renmark/parser.py:43`, `"simple" | "medium" | "hard"`) —
and that's assigned *after* a plan already exists, per-task, not as a
front-door routing decision for the whole request. There is also an informal,
human-only heuristic already in `CLAUDE.md` ("Stay on main for small
changes... single-file changes land directly on main") — this design makes
that heuristic explicit, mechanical, and reusable by General Contractor
itself, not just by a human deciding where to commit.

## 2. Classification signals (deterministic, no model call to classify)

A request is a **candidate for the fast path** only if ALL of the following
hold. Any one failing routes it to Normal Feature (or Architectural Feature,
per the existing distinguishing criteria in `governing-architecture-
roadmap.md`). This mirrors the deterministic-first gate's pattern
(`plugin/skills/.shared/deterministic-first.md`) — a fast, cheap, mechanical
check runs before any model judgment is invoked, and answers "no" cheaply
when the request obviously doesn't qualify.

| Signal | Threshold | Rationale |
|---|---|---|
| **Declared file scope size** | ≤ 2 files, named explicitly (not a glob/directory) | Mirrors `CLAUDE.md`'s existing "single-file changes" heuristic and R-0.0 Scenario A's own definition (1 file) |
| **Action type** | add/modify only — no delete, no rename, no file-permission change | The exact action class involved in R-0.0's Scenario C finding; excluding it from the fast path by definition removes the highest-risk action from the lowest-ceremony path, independent of WP-2's enforcement work |
| **No `renmark/**`/`plugin/**` target** | target path is outside both | Production/orchestration code changes are inherently higher-blast-radius; they route to Normal Feature (existing `/renmark:feature` pipeline) regardless of line count |
| **No cross-file dependency** | the task's `context_files` (if any) must not overlap the target set (existing invariant, `dispatch.validate_wave`'s "context_files" check reused, not reinvented) | A change that requires reading another file to write this one is a signal of real coupling, not a truly isolated small task |
| **Verifier is a single deterministic command** | e.g. `pytest tests/test_x.py::test_y`, not a multi-stage verification chain | Consistent with "deterministic tests only" in the routing model's small-task path — no Inspector needed to interpret ambiguous verifier output |

These five signals are answerable from the request text and target-file
metadata alone — no LLM call needed to classify (Q1/Q2 of the deterministic-
first gate). A request failing classification is not blocked; it simply
routes to the existing Normal Feature flow unchanged (this design adds a
fast path, it does not remove or gate the current default).

## 3. Explicit non-signals (deliberately NOT part of classification)

- **Line count of the diff** — deferred; a 1-line change to a 500-line file
  and a 40-line addition to a 10-line file are both plausibly "small," and
  diff size isn't knowable before the Worker runs. Using post-hoc diff size
  as a *scope-violation* signal is WP-2's job (enforcement), not WP-1's
  (pre-dispatch classification).
- **Estimated token cost** — `renmark.cost.is_deterministic_item` and
  `subagent_gate._DIRECT_TOKEN_CEILING` already answer a related but
  different question ("should the orchestrator do this without ANY
  subagent"). This design's fast path still dispatches exactly one Worker —
  it does not attempt to answer "can the orchestrator skip dispatch
  entirely," which stays subagent_gate's job. The two gates compose:
  subagent_gate can still short-circuit to zero-dispatch for a fast-path
  task that's small enough, same as it would for any other task.
- **Task.complexity ("simple"/"medium"/"hard")** — reused as an *input*
  signal where already assigned in an existing plan (a "simple" task is
  necessarily fast-path-eligible if it also passes the 5 signals above), but
  not treated as sufficient on its own — a "simple" task that deletes a file
  or touches `renmark/**` still fails classification per signal 2/3 above.

## 4. Routing rule (General Contractor decision point)

```text
Incoming request
  → run the 5-signal check above (pure function, no model call)
  → ALL PASS?
      yes → FAST PATH
              General Contractor → single Worker (declared scope = the
              named file(s), add/modify only) → deterministic verifier
              → Inspector ONLY IF a WP-2 scope-violation trigger fires
                (see classification-design.md §5) → done
      no  → EXISTING FLOW, unchanged
              (Normal Feature: /renmark:feature's current PRD → plan →
              build → verify → QA → review → ship pipeline; Architectural
              Feature: same pipeline plus the Architecture-mode planning
              gate — this design does not change either path)
```

The routing decision itself is a pure function of the 5 signals — it is not
delegated to a model, is not itself a subagent dispatch, and produces a
one-line justification (which signal(s), if any, failed) for the ledger.
This keeps the "why was this task routed here" question auditable the same
way `subagent_gate.SubagentVerdict.reason` already is.

## 5. Interface with WP-2 (Worker scope enforcement) and WP-3 (UX regression)

- WP-2 owns what happens *during* Worker execution on the fast path: the
  declared scope this design produces (the named file(s), add/modify only)
  becomes WP-2's enforcement input — WP-2 is responsible for making a
  scope-exceeding action (e.g. an attempted delete of an undeclared file,
  the exact shape of R-0.0's Scenario C finding) blocked or escalated, not
  merely logged. WP-1 stops at "here is the declared scope"; WP-2 starts at
  "here is how that scope is enforced."
- WP-3's regression suite must assert that a request failing ANY of the 5
  signals in §2 is routed identically to how it is routed today (unchanged
  behavior for non-fast-path requests) — this is the guarantee that keeps
  the existing single-command UX invariant intact per Phase 1's scope.

## 6. Reused vs. new

**Reused, not reimplemented:**
- `dispatch.validate_wave`'s context-files-into-target check (signal 4)
- The existing `Task.complexity` field as an optional accelerant, not the
  sole signal (§3)
- The deterministic-first gate's shape (cheap mechanical check before any
  model judgment) — this design is that same pattern applied one layer
  earlier, at request-routing time rather than dispatch-justification time

**New for R-0.1 (WP-4's implementation scope, not built yet):**
- The 5-signal classifier function itself (pure, no I/O beyond reading the
  request's declared target paths)
- The routing decision point in General Contractor's flow
- The ledger entry format for a routing decision (signal-by-signal PASS/FAIL)

## 7. Open question for WP-2/WP-4 (flagged, not resolved here)

Signal 3 excludes any `renmark/**`/`plugin/**` target from the fast path
entirely — meaning Renmark's own future small self-changes (a one-line fix
to a skill doc, for instance) will NOT use the fast path even though they
plausibly could. This is a deliberate, conservative default for R-0.1's
first cut (lower risk while WP-2's enforcement is new and unproven) — not a
permanent architectural position. Revisiting it is explicitly out of scope
for R-0.1 and would need its own follow-up item, the same way R-0.0 left
F1/F2 rather than silently resolving them.
