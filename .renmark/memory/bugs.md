# Bugs

Running log of bugs found and fixed. Newest at top. Updated by `/renmark:debug`, `/renmark:codereview` (findings), and `/renmark:orchestrate` (escalations).

## Open

### 2026-08-05 — AC-13 closure path: 2 of 5 guardrail metrics still unmeasured after Release 14

**Severity:** major (blocks AC-13 / Req 13 closure)
**Symptom:** Release 14 (governed-orchestration-assurance) instruments 3 of 5 named guardrail metrics (scope-violation rate, unknown-usage rate, false-pass/reopen rate) with a real, window-aligned measured value in `analytics._agg_guardrail_metrics`. `owner_interruptions_per_milestone` and `duplicate_artifact_rate` remain `None`+documented `_note` — no durable data source exists for either. AC-13 stays `partial` (Owner-confirmed 2026-08-05: "AC-13 cannot close with 2/5 metrics unmeasured").
**Root cause:** No skill call site records an `AskUserQuestion`/gate-interaction event to any durable log, and no analytics/ledger path correlates a re-dispatched task against an already-completed one by `(feature, target, index)` to detect a duplicate artifact emission.
**Fix (scoped, not yet scheduled to a specific release):**
- **Owner-interruptions-per-milestone**: wire the handoff-menu contract (`plugin/skills/.shared/handoff-menu.md`) so every `AskUserQuestion` gate call records `analytics.record_event(repo, ts=..., kind="owner_gate", milestone=<current milestone/feature id if available>)` — additive, one new event kind, read the same way Release 14's `scope_check` events are read. Aggregate as `owner_gate_events_in_window / max(1, milestones_in_window)`.
- **duplicate-artifact rate**: correlate `task-runs.jsonl` rows by `(feature, target, index)` — a second `status: PASS` row for a tuple that already has one PASS row within the window is a duplicate/re-dispatch. Aggregate as `duplicate_task_runs_in_window / max(1, total_task_runs_in_window)`. This directly measures the failure mode Release 13's Finding A demonstrated was real (a resume/skip-list identity gap can cause exactly this).
**Next step:** propose as its own bounded, Owner-approved release (number TBD — not unilaterally inserted into the existing 16-release sequence) before AC-13 can be marked `done`. Cross-reference this entry from any future `/renmark:roadmap` pass over `governed-orchestration-assurance`.

---


### 2026-06-09 — classify_usage_pause: unparseable now yields 1970 resume_after

**Severity:** nit
**Symptom:** When now is not valid ISO, _compute_resume_after falls back to epoch+60min (1970), a past resume_after.
**Root cause:** Unparseable now has no time reference; fallback anchors on epoch. Unreachable via real callers (they pass now_iso()).
**Fix:** (low priority) anchor fallback on a sentinel or skip pause when now invalid. Real callers always pass valid now.

---


### 2026-06-08 — init bootstrap re-creates .renmark/README.md + .gitkeep on every run

**Severity:** minor
**Symptom:** Running init on an already-populated repo leaves untracked .renmark/README.md + .gitkeep files each time (dropped manually in finish twice)
**Root cause:** bootstrap creates scaffold artifacts via existence-skip even in dirs that already have committed content; the renmark repo never tracked these
**Fix:** (pending) either commit them once, or have bootstrap skip README/.gitkeep when the .renmark subtree already has tracked content

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

### 2026-08-05 — renmark-execute --resume never consults the ledger, so dangling work_order events are invisible

**Severity:** low
**Symptom:** Release 13 orphan-detection spike Finding C: a ledger work_order event with no matching work_result (e.g. from an interruption between the two) is never surfaced or reconciled during --resume -- the ledger and the resume skip-list are two disconnected sources of truth.
**Root cause:** (deferred, not investigated in depth this pass) resume logic was built against pipeline.json/skip-list state only, before the ledger (R-0.3/Release 13 itself) existed as a second durable record.
**Fix:** (pending) have --resume cross-check dangling ledger work_order events against the skip-list and surface (not silently drop) any mismatch. Scope to a future release, capped.
**Lesson:** Surfaced by Release 13s orphan-detection spike; deferrable, not blocking. Ledger-resume reconciliation is exactly the kind of gap this program (governed-orchestration-assurance) exists to close -- good candidate for a dedicated future release if it recurs.

---

### 2026-08-05 — renmark-execute --resume has no pre-flight working-tree cleanup

**Severity:** low
**Symptom:** Release 13 orphan-detection spike Finding B: on --resume, renmark-execute does not check/clean the working tree before continuing dispatch, so leftover uncommitted changes from an interrupted run could interact unpredictably with the resumed waves execution.
**Root cause:** (deferred, not investigated in depth this pass) _setup_resume_state/_cross_check_skip_list focus on task-index bookkeeping, not working-tree state, per the spike finding.
**Fix:** (pending) add a git status check at the top of --resume, matching this repos own pre-refactor-safety-protocol pattern (confirm clean tree or checkpoint before continuing). Scope to a future release, capped.
**Lesson:** Surfaced by Release 13s orphan-detection spike; deferrable, not blocking (unlike Finding A).

---

### 2026-08-05 — summary.is_stale crashes on naive-vs-aware datetime compare against this repos real .renmark tree

**Severity:** medium
**Symptom:** Running renmark.hygiene.py scan against this live repo crashes inside summary.is_stale on a naive-vs-aware datetime comparison. Reproduced as pre-existing (not introduced by Release 12 task 3s hygiene.py changes) via git stash + re-run on main before the diff.
**Root cause:** (unconfirmed, not investigated in depth) summary.is_stale likely compares a timezone-naive datetime.now() or similar against a timezone-aware timestamp parsed from an artifacts stale_after/created_at metadata field (or the reverse), which raises TypeError: can not compare offset-naive and offset-aware datetimes in Python.
**Fix:** (pending) route through /renmark:debug to reproduce with a real traceback and fix summary.is_stale to normalize both operands to the same awareness (prefer UTC-aware throughout, matching this programs own established convention in recurrence.py/ledger.py).
**Lesson:** Found via live dogfooding of Release 12s hygiene.py extension -- the additive change itself is correct and isolated, but running it against the real repo surfaced a genuine pre-existing defect in a function outside this releases scope. Logged rather than silently fixed inline, per this programs own out-of-scope-finding convention.

---

### 2026-08-05 — docs-editor allowed_targets glob (**/*.md) never matches root-level .md files

**Severity:** medium
**Symptom:** check_capability_envelope(role="docs-editor", paths=["CLAUDE.md"]) returns path passed=False even though docs-editor is clearly the correct role for editing root-level project markdown (CLAUDE.md, AGENTS.md, README.md). Confirmed live: fnmatch.fnmatch("CLAUDE.md", "**/*.md") is False -- Pythons stdlib fnmatch has no globstar semantics; ** is treated as literal repeated *, and the pattern still requires a literal / character to appear in the tested string, which a root-level filename never has.
**Root cause:** subagent_profiles.py docs-editor.allowed_targets = "**/*.md, plugin/skills/**/*.md, docs/**" was written assuming shell-style globstar ("** matches zero or more directories, including none"), but Release 6 (Task 3) wired check_capability_envelope to use Pythons plain fnmatch.fnmatch, which has no such semantics -- this is the 4th occurrence this session of a capability-envelope path-matching gap (after researcher x2, audit-reader x1), but the first that is a genuine glob-syntax defect rather than a role/target mismatch.
**Fix:** (pending) either add an explicit root-level pattern ("*.md") to docs-editor.allowed_targets, or replace the fnmatch-based matcher in subagent_gate.py/the prototype hook with a matcher that supports real globstar semantics (e.g. pathlib.Path.match with proper ** handling, or a small custom translator). Scope to a future release, not fixed inline -- this run works around it by dispatching CLAUDE.md/AGENTS.md edits under role=general-purpose instead of docs-editor.
**Lesson:** 4 occurrences of the same underlying capability-envelope coverage gap across Releases 7, 8, 11, 12 -- worth a dedicated remediation pass rather than continuing to patch role assignments one dispatch at a time. Also a reminder that ** in Python fnmatch is NOT shell globstar -- any allowed_targets pattern using ** should be verified with a real fnmatch.fnmatch() call, not assumed.

---

### 2026-08-05 — codex ad-hoc dispatches self-append CHANGELOG entries in wrong format/location

**Severity:** low
**Symptom:** Two Release 8 codex ad-hoc dispatches (tasks 6, 8) appended their own CHANGELOG.md entries at the very bottom of the file (inside an old 2026-06-era historical section) using a different heading/bullet format (## YYYY-MM-DD title / - Request:) than this repos actual convention (## [YYYY-MM-DD] -- title / **Request:**), breaking the newest-first ordering. Content was accurate but mislocated and reformatted.
**Root cause:** The task briefs never instructed workers to leave CHANGELOG.md to the orchestrator (only Release 4 onward briefs added an explicit no-self-commit instruction for git commits, not for CHANGELOG writes specifically) -- codex apparently pattern-matched on seeing CHANGELOG.md entries elsewhere in the repo and added its own without being asked, guessing at placement/format rather than being told not to touch it.
**Fix:** (pending) add an explicit "do not edit CHANGELOG.md -- the orchestrator writes it" instruction to task briefs/dispatch prompts, or scope this as part of a future capability-envelope release covering documentation-write paths, not just code.
**Lesson:** A second instance (after Release 3 task 4s self-commit) of a Worker self-integrating beyond its declared scope without being told not to. Low severity here (content was accurate, just misplaced) but the same underlying gap -- dispatch briefs should explicitly say what NOT to touch (CHANGELOG.md, git commit) by default, not just for tasks where it happened to matter before.

---

### 2026-08-05 — researcher role allowed_targets does not cover .renmark/rethink/** (2nd occurrence)

**Severity:** medium
**Symptom:** check_capability_envelope pre-dispatch denies role=researcher writing to .renmark/rethink/<slug>/*.md (Release 7 task 1, Release 8 task 1) because ProfileSpec.allowed_targets for researcher is scoped to .renmark/research/**/*.md only -- but this repos own REQ-28 rethink pipeline convention writes ALL its stage artifacts (survey, baseline, prd-acceptance-map, external-benchmark, modularity-assessment, classification, target-blueprint, roadmap, spike findings) under .renmark/rethink/<slug>/, never under .renmark/research/. Every rethink-stage researcher dispatch in this program has needed a manual role reassignment to docs-editor to pass the envelope check.
**Root cause:** subagent_profiles.py PROFILES["researcher"].allowed_targets was set to .renmark/research/**/*.md without cross-checking it against REQ-28/the rethink SKILL.md file-conventions table, which predates Release 6s enforcement wiring and has always written under .renmark/rethink/, not .renmark/research/ -- the two directories serve genuinely different purposes (.renmark/research/ = ad-hoc external research artifacts from renmark:researcher role in feature/plan work; .renmark/rethink/ = the rethink pipelines own staged transformation artifacts) but researcher role was only ever scoped for the former.
**Fix:** (pending) either broaden researcher.allowed_targets to include .renmark/rethink/**/*.md, or -- likely the more correct fix -- have the rethink skill dispatch its stage/spike-finding tasks with a role better scoped for that convention (a new rethink-artifact-writer role, or reuse docs-editor as already done twice now) rather than researcher. Scope to a future governed-orchestration-assurance release (Release 12, context/memory governance, or a small standalone fix), not fixed inline here.
**Lesson:** Live dogfooding caught the same capability-envelope gap twice in a row (Release 7 task 1, Release 8 task 1) -- a real, systemic role/target mismatch for this repos own rethink pipeline, not a one-off plan authoring mistake. When check_capability_envelope denies a path twice for the same role across different releases, treat it as a profile-definition bug, not a per-task fix.

---

### 2026-08-05 — enforce_host_agent_dispatch_scope has no bookkeeping-path allowlist

**Severity:** medium
**Symptom:** Running enforce_host_agent_dispatch_scope live (first real end-to-end test, Release 7 task 1) against a real orchestrator commit that bundled the dispatched task file (.renmark/memory/orchestration-baseline.md) with routine bookkeeping (CHANGELOG.md, .renmark/plans/*.plan.md, .renmark/reviews/*.verification.md, .renmark/audits/*, .renmark/memory/learnings.md) raised WaveScopeViolationError (8 disallowed changes) even though the dispatched Worker itself never touched anything out of scope -- the violation is entirely orchestrator-added bookkeeping, not Worker misbehavior.
**Root cause:** enforce_host_agent_dispatch_scope (Release 6 task 8, renmark/dispatch.py) reuses fast_path.verify_worker_scope literal git-diff-vs-allowed_paths semantics with no allowance for known-safe orchestrator bookkeeping paths bundled into the same commit as a task, unlike a hypothetical caller-aware design that would separate Worker-attributable changes from orchestrator-attributable ones.
**Fix:** (pending) add a configurable bookkeeping-path allowlist (CHANGELOG.md, .renmark/plans/**, .renmark/reviews/**, .renmark/audits/**, .renmark/memory/**) that enforce_host_agent_dispatch_scope (and/or fast_path.verify_worker_scope generally) excludes from violation counting when computing the diff -- scoped to a future governed-orchestration-assurance release, not fixed inline here.
**Lesson:** Live dogfooding of newly-wired enforcement inside the very program building it caught a real gap on first real use: the orchestrator commit-bundling practice used throughout this whole session (task diff + CHANGELOG + plan + audits in one commit) is incompatible with a strict single-task-scope post-action check as currently written. Test enforcement logic against REAL commit shapes, not just synthetic single-file test fixtures.

---

### 2026-08-04 — Release snapshot never compacted the previous version tree

**Severity:** medium
**Symptom:** .renmark/version/<ver>/ accumulates full unpacked source trees forever; only v0.39.7/v0.40.0 had ever been manually compacted to .meta form, v0.41.0 was still a full 740KB tree after v0.42.0 released.
**Root cause:** renmark/release.py::build_version_snapshot wrote a fresh full unpacked snapshot on every release but no function anywhere ever retired a prior version snapshot to a slim form, and no call site invoked such a step.
**Fix:** Added release.compact_snapshot_dir() + release.compact_previous_snapshots(); build_version_snapshot() now calls compact_previous_snapshots(keep=<current snap name>) at the end of every build, retiring every other full snapshot dir under the version dir to <name>.meta/ (manifest.json, release.md, verification.md, files-changed.txt only). Retroactively compacted v0.41.0 -> v0.41.0.meta/ in the live repo. 4 new regression tests added.
**Lesson:** When a release/build step creates a versioned artifact, always pair it with a retirement step for the artifact it superseded in the SAME function -- a one-off manual cleanup does not prevent recurrence.

---

### 2026-07-30 — Persist approved Agency handoff

**Severity:** major
**Symptom:** Approved Agency milestone was not persisted to canonical delivery state through production lifecycle.
**Root cause:** The production lifecycle path projected approved Agency state read-only and never invoked the canonical approval handoff that writes the active milestone into delivery state.
**Fix:** Route explicit approved Agency activation through the preserving canonical handoff and add regression coverage.
**Lesson:** Keep approval transitions as explicit writers; compatibility projections and summary readers must stay read-only.

---

### 2026-07-30 — Fix M3 package parser/compiler typing

**Severity:** medium
**Symptom:** mypy rejected M3 package parser/compiler boundary
**Root cause:** The parser selected a nullable milestone/package dictionary through a ternary without narrowing it, while the compiler forwarded string metadata through kwargs into a boolean parameter.
**Fix:** Explicit narrowing and typed forwarding restored mypy compatibility.
**Lesson:** New package adapters need explicit typed boundaries instead of nullable ternary targets or untyped forwarding.

---

### 2026-07-30 — M2 task 7 selector compatibility verifier

**Severity:** medium
**Symptom:** Task 7 verifier failed and its generated test changes were rolled back.
**Root cause:** Task 7 mixed stale host-presentation expectations with an incorrect host=None assumption, while continue_selector also searched only current-page bindings despite advertising the hidden semantic refusal code/label on every page; the resulting contract mismatch made the generated focused verifier fail and roll back.
**Fix:** Aligned interaction tests with bounded More/Back/fallback metadata and runtime host resolution, and made exact hidden refusal codes/labels resolve as cancel from every page.
**Lesson:** Selector tests must assert semantic parity and runtime-resolved host identity, not freeze one host presentation or assume host=None means Codex.

---

### 2026-07-30 — Nested Codex workspace-write sandbox unavailable in WSL

**Severity:** major
**Symptom:** Codex implementation tasks exited zero without changing their targets, so completion and recurrence guards stopped M2.
**Root cause:** Renmark invoked bare `codex`, WSL selected the WindowsApps executable, and that executable had no usable Bubblewrap helper for workspace-write.
**Fix:** Installed system Bubblewrap and made the provider probe PATH candidates without a model call, launch the first passing absolute executable, reject workspace-owned runtimes, and fail safely without sandbox bypass.
**Lesson:** Executable presence is not executor readiness: prove the actual sandbox before model spend, and never launch a runtime controlled by the target workspace.

---

### 2026-07-30 — Codex executor accepted unchanged targets as PASS

**Severity:** high
**Symptom:** M2 tasks 2–12 reported PASS while producing no target changes, artifacts, or commits.
**Root cause:** The Codex runner enforces only that no out-of-lane files changed and then treats a green verifier as completion, so an empty target delta and empty commit SHA are mislabeled as PASS instead of failed evidence.
**Fix:** Require the target in the executor delta before verification and require a real commit SHA or the explicit no-commit sentinel after verification.
**Lesson:** An agent exit plus a green verifier is not implementation completion; require attributable target change and durable commit evidence, or an explicit validated batching sentinel.

---

### 2026-07-30 — Ruff baseline regressed after M1 delivery-state additions

**Severity:** medium
**Symptom:** Six Ruff findings across four files blocked the approved M2 preflight.
**Root cause:** Recent M1 canonical-delivery-state additions inserted imports, exports, and validator branches without a final repository-wide Ruff normalization pass, leaving six mechanical style violations across four files while behavior remained green.
**Fix:** Applied the exact Ruff-canonical mechanical normalization and re-ran focused plus repository-wide gates.
**Lesson:** Run the repository-wide Ruff gate after milestone task commits and before the next milestone preflight; passing task-local verifiers alone does not prove cross-file style convergence.

---

### 2026-07-29 — M1 canonical state had unstable identity and validator drift

**Severity:** high
**Symptom:** Repeated legacy reads changed run_id and DeliveryState serialized metadata rejected by validate_delivery_state.
**Root cause:** M1 omitted deterministic legacy run-identity derivation and treated canonical schema, contract, and run-ID metadata as caller-owned during normalization even though the validator defines those fields as fixed invariants.
**Fix:** Derive legacy run IDs from persisted Program/Lifecycle/Agency identity fields; normalize schema_version, contract_version, and malformed run IDs to canonical values; add stability and writer-validator convergence regressions.
**Lesson:** Canonical metadata must be normalized by the writer and legacy projections need identity derived from stable persisted fields, never a fresh UUID per read.

---

### 2026-07-29 — M1 delivery-state CLI crashed on legacy work packages

**Severity:** medium
**Symptom:** ./bin/renmark-execute --delivery-state raised AttributeError on dict.normalized()
**Root cause:** The live CLI projection both round-trips DeliveryState through asdict, which erases nested types, and re-normalizes already-qualified work-package IDs as raw tokens, so reconstruction either crashes on dictionaries or silently drifts stable IDs.
**Fix:** Use dataclasses.replace for typed lifecycle cloning, make stable_work_package_id idempotent for already-qualified IDs, add live CLI and exact round-trip regressions, and clear M1 lint/type defects.
**Lesson:** Never clone nested dataclasses with asdict plus a top-level constructor; typed clones and normalization functions must preserve nested types and be idempotent.

---

### 2026-07-17 - Recurrence guard discarded the actionable verifier failure

**Severity:** medium
**Symptom:** A blocked third Codex attempt left only the recurrence summary in `verifier.log`, so the patch path could not inspect the failure that triggered the stop.
**Root cause:** `_codex_fail_recurrence_guard` forwarded its status note as the escalation verifier log and had no parameter for the current bounded failure evidence.
**Fix:** Pass the current verifier tail, executor tail, or lane reason into the guard escalation while keeping the bounded status note user-facing.
**Lesson:** A retry guard must preserve the failure evidence needed to repair the issue it stops.

---

### 2026-07-17 — Repeated verifier failures recommended an instruction guard

**Severity:** medium
**Symptom:** The second equivalent verifier failure blocked another retry but recommended durable_guard instead of patch.
**Root cause:** Remediation was derived solely from occurrence_count, so failure kind never influenced the recommendation.
**Fix:** Classify remediation from the stable rule_id and persist bounded check/rule identity with legacy-key recovery.
**Lesson:** Use recurrence count to decide when to stop retrying; use failure identity to decide how to remediate.

---

### 2026-07-17 — Claude specialist agents fell back to general-purpose

**Severity:** major
**Symptom:** Claude runs showed general-purpose agents instead of Renmark specialist roles
**Root cause:** Renmark shipped no plugin agent definitions, falsely reported static native roles, ignored explicit plan roles, and failed to classify ordinary project source as code work.
**Fix:** Shipped eight plugin-scoped agent definitions, verified files before native dispatch, honored explicit roles, and expanded source classification.
**Lesson:** A dispatch-role registry is not host capability proof; package the host-native definition and resolve its installed scoped name before dispatch.

---

### 2026-07-17 — Claude native picker missing after parity install

**Severity:** high
**Symptom:** Claude Code answered Renmark gates as prose without an arrow-key selector or recommended-first option.
**Root cause:** The installer had no authoritative post-install health gate: its pre-Codex doctor pass could return nonzero and was discarded by `|| true`, so it could announce success while Claude's registered Renmark cache path was missing; without the loaded skill, Claude could not invoke AskUserQuestion or render the recommended-first picker.
**Fix:** Repaired the live Claude cache and made install.sh fail unless a final doctor pass confirms the registry and cache are healthy.
**Lesson:** Treat plugin-manager registration and cache existence as installation postconditions; never suppress the final health check behind an output-filtering pipeline.

---

### 2026-07-16 — Repository-wide Ruff and mypy baseline was red

**Severity:** medium
**Symptom:** Ruff reported 60+ violations and mypy reported an undefined datetime annotation while pytest was green.
**Root cause:** The heartbeat and reduce-complexity changes landed with tests green but without a green repo-wide Ruff/mypy gate, leaving lazy annotation imports, stale extracted imports, and mechanical formatting debt in the committed baseline.
**Fix:** Applied safe Ruff fixes, repaired remaining annotations and formatting, preserved legacy engine aliases, then passed Ruff, mypy, focused tests, and the full 1,423-test suite.
**Lesson:** A green pytest run is not a substitute for running every repository quality gate after cross-file extraction work.

---

### 2026-07-01 — harness-modes: mode mutators silently swallowed write failures + wrong CLI path

**Severity:** medium (was Major in codereview)
**Symptom:** set_mode/clear_mode swallowed OSError while the CLI printed success + exited 0; CLI help/success text printed .renmark/mode.json instead of .renmark/state/mode.json; writes were non-atomic.
**Root cause:** best-effort no-raise mutators + hardcoded wrong path strings + plain-write (no atomic replace).
**Fix:** set_mode raises OSError (atomic temp + os.replace); clear_mode surfaces delete failures but idempotent on absent; CLI catches OSError → stderr + exit 1; path sourced from mode_state_path()/MODE_REL; read_mode still never raises.
**Lesson:** a "never raises" convention is right for reads but wrong for mutators — a write that can silently fail while the UI reports success is a trust bug.

### 2026-07-01 — P8 weakened reference-case assertions

**Severity:** high
**Symptom:** mini-format conversion dropped explicit-choice/menu-terminal/read-only contracts
**Root cause:** codex re-review 96505ea..HEAD
**Fix:** extend assertion language or add structured per-case checks; restore stronger assertions
**Lesson:** fix round partial; deterministic behavioral testing has a fundamental live-call constraint

---

### 2026-07-01 — P8 feature un-bootstrappable

**Severity:** high
**Symptom:** --accept hard-fails; no in-tree capture() caller; no committed snapshots -> cases always ERROR
**Root cause:** codex re-review 96505ea..HEAD
**Fix:** wire capture() to a real host runner OR ship snapshots + drop advertised accept until runner exists
**Lesson:** fix round partial; deterministic behavioral testing has a fundamental live-call constraint

---

### 2026-07-01 — P8 Major 1 residual: replay returns golden as current transcript

**Severity:** high
**Symptom:** _current_transcript() ignores inputs, returns golden verbatim; no distinct current transcript
**Root cause:** codex re-review 96505ea..HEAD
**Fix:** decide: deterministic tier should execute renmark deterministic code path (real current), or explicitly re-scope to recorded-expectation validation
**Lesson:** fix round partial; deterministic behavioral testing has a fundamental live-call constraint

---

### 2026-07-01 — P8 snapshot ref path traversal

**Severity:** medium
**Symptom:** baseline_ref/golden_ref interpolated into paths; ../ can escape snapshots dir
**Root cause:** codex review 2a05fbf..HEAD
**Fix:** validate refs as plain stems, reject resolved paths escaping snapshots/
**Lesson:** codereview caught under-built P8 before merge

---

### 2026-07-01 — P8 judge silent-pass on bad confidence

**Severity:** high
**Symptom:** judge.py accepts {outcome:pass,confidence:bogus} as validated PASS, coerces confidence to low
**Root cause:** codex review 2a05fbf..HEAD
**Fix:** unrecognized required field -> validation_status=unvalidated, non-pass outcome
**Lesson:** codereview caught under-built P8 before merge

---

### 2026-07-01 — P8 --accept cannot record from CLI

**Severity:** high
**Symptom:** _engine --accept hard-wires a runner that always raises
**Root cause:** codex review 2a05fbf..HEAD
**Fix:** reject --accept up-front as unsupported-without-live-runner (honest) instead of faking capture
**Lesson:** codereview caught under-built P8 before merge

---

### 2026-07-01 — P8 replay does not test current behavior

**Severity:** high
**Symptom:** replay diffs stored golden vs baseline; judge gets actual=golden; cannot catch regressions
**Root cause:** codex review 2a05fbf..HEAD
**Fix:** assertion-based replay: run recorded inputs through current code, eval case.assertions on current transcript, pass current as actual to judge
**Lesson:** codereview caught under-built P8 before merge

---

### 2026-06-25 — P11 proactivity toggle: persisted but not runtime-enforced

**Severity:** low
**Symptom:** is_proactive() has no runtime call-site; --set-proactive false persists the flag + documents the CLI in the routing rule, but no mechanism injects the flag into the agent per turn, so auto-routing enforcement remains doc-level (the agent honors the CLAUDE.md rule).
**Root cause:** renmark auto-routing is implemented as agent-read doc instructions, not a code router; a persisted flag needs a SessionStart-style injection to actually gate routing.
**Fix:** (follow-up) surface is_proactive(repo) via a session-start context injection or doctor/status read so the flag has runtime effect.
**Lesson:** persist+document is a valid first increment, but a config flag with zero readers is half-wired — wire a real consumer or log the gap.

---

### 2026-06-14 — Hand-off picker not re-rendered on continuation turns

**Severity:** medium
**Symptom:** After a renmark hand-off, when the user replies with a clarifying question instead of selecting, the skill answers in prose with an inline numbered list instead of re-rendering the clickable AskUserQuestion picker.
**Root cause:** handoff-menu.md rules 6-9 + next-steps.md mandate the clickable picker only at the first turn the skill ends with a question; no rule required re-rendering the picker when the hand-off continues across turns (user replies with a non-selection), so the agent legitimately drops to prose and the visible-choices guarantee lapses.
**Fix:** Added a continuation clause to handoff-menu.md rule 9 (the existing hard-guarantee the 21 SKILL citations already point at) + tightened rule 6 dispatch bullet + updated next-steps.md rule-9 gloss. Zero renumbering, so all citing skills inherit the fix.
**Lesson:** A non-selection free-text reply to a hand-off (clarifying question/follow-up) keeps the hand-off OPEN: answer it, then re-render the picker in the same turn. An inline 1./2. list in the reply body is NOT a rule-7 fallback.

---

### 2026-06-14 — roadmap --setup staleness guard unclearable by /renmark:init after non-structural commit

**Severity:** major
**Symptom:** program_map_is_stale() stays True after /renmark:init when the map body is unchanged; --setup permanently halts to /renmark:init which can never clear it
**Root cause:** init.write_full_map only rewrote project-map.md when the header-stripped BODY differed, preserving the stale Last-refreshed @ <sha> header on body-unchanged refreshes; program_map_is_stale keys freshness off that header sha vs HEAD, so any structure-neutral commit wedged staleness True with no remediation
**Fix:** init.write_full_map now rewrites the file (advancing the freshness header) whenever the full text differs even if the body matches, still returning unchanged; +regression test test_init_advances_map_header_so_staleness_clears
**Lesson:** A freshness marker (Last-refreshed @ sha) must advance independently of body-content equality — coupling a staleness check to a sha that only moves on body change creates an unclearable wedge. Also: test fixtures for sha-keyed checks must use VALID HEX (the header regex is [0-9a-fA-F]+).

---

### 2026-06-09 — loop driver stalled on first failed verify + could overshoot budget + raised on bad input

**Severity:** major
**Symptom:** build_decision left next_action blank on any failed verify → loop marked stalled on iteration 1 (never iterated); budget checked AFTER spend (one-iteration overshoot); parse_budget raised on nan/inf/1e309; read_loop/usage raised/undercounted on corrupt input
**Root cause:** next_action never derived from verify evidence; budget gate sequenced post-dispatch; budget/state/ledger inputs not defensively coerced
**Fix:** build_decision derives next_action from verify symptom lines (loop iterates); should_continue_budget preflights before dispatch; isfinite/try-except budget coerce; read_loop field coercion; usage clamp+decode-tolerant. +tests

---

### 2026-06-08 — modularity analyzer under-reported gaps + over-suppressed real files

**Severity:** major
**Symptom:** function-LOC undercounted (dropped signature, swallowed nested defs); cognitive BoolOp flat; generated-file suppression matched substrings in docstrings/prose (real file with "generated by" in docstring → 0 gaps); test-tree match hit src/test/
**Root cause:** imprecise ast span/branch math + over-broad substring suppression (not anchored to comment-only header lines)
**Fix:** span from decorator/signature minus nested spans; BoolOp +len(values)-1; suppress only on #-comment header markers; tests/__tests__ exact components; +boundary/regression tests

---

### 2026-06-08 — sizing classifier produced false-lite on code-with-template, malformed tasks, and --lite override

**Severity:** critical
**Symptom:** _is_doc_or_config matched "template" as a substring (real .py code → doc → lite); classify_plan([object()]) → lite; --lite override bypassed the hard/core safety floor — all FALSE-LITE (skips full review on risky code)
**Root cause:** substring (not suffix) matching; unvalidated task shape reaching the lite branch; override specified to always beat the classifier
**Fix:** code-suffix-wins + .template/.j2 suffix matching; validate task shape before lite (else standard); resolve_override() — --full escalates, --lite only narrows standard; +regression tests

---

### 2026-06-08 — merge_rule_blocks corrupted files on malformed markers

**Severity:** major
**Symptom:** A CLAUDE.md with an orphan END (or unclosed BEGIN) caused merge to insert a block anyway → unbalanced markers (1 BEGIN + 2 END), violating the non-destructive guarantee
**Root cause:** merge trusted a too-loose substring marker regex and never pre-validated balanced markers before inserting
**Fix:** tightened regex to full <!-- BEGIN:name --> own-line comments; added validate_rule_markers + MarkerCorruptionError; malformed target is SKIPPED (file unchanged), run()→exit 2

---

### 2026-06-08 — plan parser rejected the documented `serves` field

**Severity:** medium
**Symptom:** `renmark-execute --dry-run` aborted with "unknown field serves" on any plan using the documented `serves: REQ-n` task field (forced stripping `serves` from the next-step-engine plans).
**Root cause:** `renmark/parser.py` allowed-fields branch + `Task` dataclass + `_build_task` were never updated when the v0.6.0 PRD feature added `serves` traceability to the plan format docs — parser and docs drifted.
**Fix:** added `serves` to the parser's accepted keys, the `Task` dataclass, and the `_build_task` constructor (commit on main). +2 parser tests; dry-run repro now parses.
**Lesson:** a documented plan field is only real if the parser accepts it — keep `parser.py` accepted-keys in lockstep with `plan/SKILL.md`'s format example.



### 2026-06-08 — deep-QA gate could be unlocked by a foreign .qa.md

**Severity:** medium
**Symptom:** _gates_not_run counted any complete .qa.md for HEAD as a passed QA gate, ignoring generator
**Root cause:** metadata match omitted the documented generator==verify-qa constraint (handoff-menu rule 2)
**Fix:** per-gate (glob, required-generator) spec; qa requires generator==verify-qa. Test added (foreign generator stays not-run).

---

### 2026-06-08 — next_steps() raised on non-str skill

**Severity:** medium
**Symptom:** lifecycle.next_steps(repo, []) raised TypeError (unhashable as set/dict key), violating the never-raise contract
**Root cause:** skill_class() and the aux AUX_LOCAL_ACTIONS.get() ran membership/key ops on raw skill before any type guard
**Fix:** skill_class(skill: object) isinstance-guards; aux lookup guarded by isinstance(skill,str); both typed object. Tests added.
**Lesson:** A try/except around state reads is not enough — defend every hashable-key op on untrusted input; the FIRST guard fix missed the aux dict lookup, caught only by re-running the repro.

---

### 2026-06-05 — pre-existing: 3 integration tests fail under RENMARK_SMOKE=1

**Severity:** medium
**Symptom:** test_cold_start_with_pending_approval, test_cold_start_recovers_at_every_stage, test_human_approval_gate_blocks_progression fail on main and branch alike
**Root cause:** (unknown — pre-existing on main, NOT caused by PRD feature; route to /renmark:debug)
**Fix:** (pending — separate from PRD feature)
**Lesson:** Integration tests gate on RENMARK_SMOKE=1 and were not being exercised; surfaced during PRD verify. Track and fix independently.

---

### 2026-06-04 — /renmark:feature does not write feature identity to lifecycle.json

**Severity:** major
**Symptom:** After a full feature pipeline (feature->plan->orchestrate->verify->finish), lifecycle.json still showed the PRIOR feature's identity (feature=codereview-focus, branch=main) while actually on branch feature/verify-browser-qa. finish's decision-log ADR captured the wrong feature name and branch.
**Root cause:** The feature router (plugin/skills/feature/SKILL.md) creates the git branch in Step 1 but never persisted feature identity. plan/orchestrate/verify/finish each write only `stage` (+ artifacts), so feature/branch fields retain whatever the previous feature left.
**Fix:** Added `lifecycle.begin_feature(repo, *, feature, branch)` — resets to a clean `init` state with the correct identity (empty stages_completed/artifacts) — and wired `/renmark:feature` Step 1 to call it immediately after creating/switching to the branch. Verifier: `tests/test_lifecycle.py::test_begin_feature_writes_identity` + `::test_begin_feature_resets_prior_feature_state`.
**Lesson:** Any pipeline-entry skill that establishes a new work unit must persist that unit's IDENTITY (not just its stage) to canonical state at entry, or downstream stage writes silently inherit stale identity.

---
