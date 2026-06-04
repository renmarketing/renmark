# Bugs

Running log of bugs found and fixed. Newest at top. Updated by `/renmark:debug`, `/renmark:codereview` (findings), and `/renmark:orchestrate` (escalations).

## Open


### 2026-06-04 — /renmark:feature does not write feature identity to lifecycle.json

**Severity:** major
**Symptom:** After a full feature pipeline (feature->plan->orchestrate->verify->finish), lifecycle.json still showed the PRIOR feature's identity (feature=codereview-focus, branch=main) while actually on branch feature/verify-browser-qa. finish's decision-log ADR captured the wrong feature name and branch.
**Root cause:** The feature router (plugin/skills/feature/SKILL.md) creates the git branch in Step 1 but never calls lifecycle.write_lifecycle(feature=<slug>, branch=<branch>). plan/orchestrate/verify/finish each write only `stage` (+ artifacts), so feature/branch fields retain whatever the previous feature left.
**Fix:** (pending) Have /renmark:feature Step 1 write_lifecycle(feature=<slug>, branch=feature/<slug>) immediately after creating the branch; optionally have plan assert identity matches the current branch. Worked around manually for verify-browser-qa this run.
**Lesson:** Any pipeline-entry skill that establishes a new work unit must persist that unit's IDENTITY (not just its stage) to canonical state at entry, or downstream stage writes silently inherit stale identity.

---

(Unresolved bugs. Move to `Fixed` once a commit lands.)

(Empty.)

---

## Fixed

(Each entry: symptom, root cause, fix, lesson. The lesson goes to `learnings.md` too for cross-project carry-over.)

### YYYY-MM-DD — (example) /metrics returns 500 under load

**Severity:** major
**Symptom:** Intermittent 500s on `/metrics` when QPS > 200.
**Root cause:** `MetricsCollector.flush()` shared a non-thread-safe buffer; concurrent requests corrupted it.
**Fix:** wrap buffer access in `threading.Lock()`. Commit `<sha>`. Files: `src/metrics.py`.
**Lesson:** Anything mutated by a request handler in a multi-threaded server must be either thread-local or lock-guarded. Added to `learnings.md` as a general pattern.
