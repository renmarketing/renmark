# Bugs

Running log of bugs found and fixed. Newest at top. Updated by `/renmark:debug`, `/renmark:codereview` (findings), and `/renmark:orchestrate` (escalations).

## Open

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
