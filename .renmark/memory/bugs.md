# Bugs

Running log of bugs found and fixed. Newest at top. Updated by `/renmark:debug`, `/renmark:codereview` (findings), and `/renmark:orchestrate` (escalations).

## Open

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
