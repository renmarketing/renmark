# Bugs

Running log of bugs found and fixed. Newest at top. Updated by `/renmark:debug`, `/renmark:codereview` (findings), and `/renmark:orchestrate` (escalations).

## Open



### 2026-06-05 — plan parser rejects documented serves field

**Severity:** medium
**Symptom:** renmark-execute --dry-run aborts: "unknown field serves" on any plan written to the documented format (plan SKILL.md lists serves: REQ-n / new as a task field).
**Root cause:** renmark/parser.py allowed-fields branch (~line 149) was never updated when the v0.6.0 PRD feature added serves traceability to the plan skill + format example. Parser and plan-format docs drifted.

---

(Unresolved bugs. Move to `Fixed` once a commit lands.)

### 2026-06-05 — install.ps1 fails to parse under Windows PowerShell 5.1 (encoding)

**Severity:** major (Windows install path is broken)
**Symptom:** `powershell.exe -File install.ps1 -NoCodex` aborts with a cascade of
spurious "Missing closing '}'" ParserErrors; line 200's em-dash renders as `�?"`.
**Root cause:** `install.ps1` contains non-ASCII characters (em-dashes `—`,
ellipses `…`, curly quotes) and is saved as UTF-8 **without a BOM**; Windows
PowerShell 5.1 decodes BOM-less `.ps1` files as the system ANSI codepage, turning
those bytes into mojibake that corrupts tokens and breaks brace matching.
**Fix:** (pending) save `install.ps1` as UTF-8-with-BOM, OR replace all non-ASCII
chars with ASCII equivalents (`—`→`-`, `…`→`...`, smart quotes→straight). The
ASCII-only route is the most robust (codepage/BOM-independent). PowerShell 7
(`pwsh`) is unaffected but is not installed on this Windows host.
**Workaround used 2026-06-05:** Windows plugin updated WITHOUT the installer —
git fast-forwarded the Windows repo copy (`C:\Users\roberto.renteria\ai-system`,
whose `origin` is the WSL repo) to v0.6.0, then patched the recorded version in
`%USERPROFILE%\.claude\plugins\installed_plugins.json` (settings.json registration
entries already present). Directory-marketplace install means content was already live.
**Lesson:** Cross-platform shell scripts must be ASCII-only or BOM-tagged — a
WSL-authored UTF-8 script silently breaks on the default Windows interpreter.

---

## Fixed


### 2026-06-05 — pre-existing: 3 integration tests fail under RENMARK_SMOKE=1

**Severity:** medium
**Symptom:** test_cold_start_with_pending_approval, test_cold_start_recovers_at_every_stage, test_human_approval_gate_blocks_progression fail on main and branch alike
**Root cause:** (unknown — pre-existing on main, NOT caused by PRD feature; route to /renmark:debug)
**Fix:** (pending — separate from PRD feature)
**Lesson:** Integration tests gate on RENMARK_SMOKE=1 and were not being exercised; surfaced during PRD verify. Track and fix independently.

---

(Each entry: symptom, root cause, fix, lesson. The lesson goes to `learnings.md` too for cross-project carry-over.)

### 2026-06-04 — /renmark:feature does not write feature identity to lifecycle.json

**Severity:** major
**Symptom:** After a full feature pipeline (feature->plan->orchestrate->verify->finish), lifecycle.json still showed the PRIOR feature's identity (feature=codereview-focus, branch=main) while actually on branch feature/verify-browser-qa. finish's decision-log ADR captured the wrong feature name and branch.
**Root cause:** The feature router (plugin/skills/feature/SKILL.md) creates the git branch in Step 1 but never persisted feature identity. plan/orchestrate/verify/finish each write only `stage` (+ artifacts), so feature/branch fields retain whatever the previous feature left.
**Fix:** Added `lifecycle.begin_feature(repo, *, feature, branch)` — resets to a clean `init` state with the correct identity (empty stages_completed/artifacts) — and wired `/renmark:feature` Step 1 to call it immediately after creating/switching to the branch. Verifier: `tests/test_lifecycle.py::test_begin_feature_writes_identity` + `::test_begin_feature_resets_prior_feature_state`.
**Lesson:** Any pipeline-entry skill that establishes a new work unit must persist that unit's IDENTITY (not just its stage) to canonical state at entry, or downstream stage writes silently inherit stale identity.

### YYYY-MM-DD — (example) /metrics returns 500 under load

**Severity:** major
**Symptom:** Intermittent 500s on `/metrics` when QPS > 200.
**Root cause:** `MetricsCollector.flush()` shared a non-thread-safe buffer; concurrent requests corrupted it.
**Fix:** wrap buffer access in `threading.Lock()`. Commit `<sha>`. Files: `src/metrics.py`.
**Lesson:** Anything mutated by a request handler in a multi-threaded server must be either thread-local or lock-guarded. Added to `learnings.md` as a general pattern.
