---
name: verify
description: Use after `/renmark:orchestrate` completes — runs goal-backward smoke tests derived from the plan's stated feature goal, cross-references open bugs for regressions, reports how many requirements were confirmed, writes a `.verification.md` artifact, and appends a learning entry. Three modes — default shell smoke, `--qa` for one live-browser happy path, `--deep-qa` for 3 live-browser edge cases; browser modes add visual/layout integrity checks and before/after UI-change tracking. Never reads source code into conversation.
---

# verify

## Overview

Three modes, one skill — chosen by flag:

| Mode | Flag | What it does | Where evidence lives |
|---|---|---|---|
| **Smoke** (default) | _none_ | one shell command per stated behavior + open regression | `.verification.md` |
| **QA** | `--qa` | one live-browser happy-path flow via the selected browser channel (Chrome DevTools MCP or native `claude --chrome`) | `.qa.md` + `.renmark/reviews/qa/<feature>/` |
| **Deep QA** | `--deep-qa` | 3 live-browser edge-case flows, risk-ranked from diff + behaviors + bugs.md | `.deep-qa.md` + `.renmark/reviews/qa/<feature>/deep/` |

Smoke is goal-backward shell verification. QA is goal-backward *rendered* verification — proves the user-visible result actually appears in a real browser, not just that curl gets a 200. Deep QA finds where the feature breaks under unusual but valid conditions. All three share: bounded ≤5-line verdict to chat, evidence to disk, `bugs.md` convergence loop, `learnings.md` appending.

**Mode selection.** Parse `$ARGUMENTS` for `--qa` / `--deep-qa`. Default to shell smoke when no flag is given. `--deep-qa` implies and gates on a prior passing `--qa` for the current sha (see Deep QA Gate below).

**Bootstrap modifier.** `--bootstrap` is a **modifier of `--qa`**, not a new flag or command. The only bootstrap invocation is `/renmark:verify --qa --bootstrap`, parsed through the **existing arg parser** (no third browser flag). When both `--qa` and `--bootstrap` are present, run the *Bootstrap path* subsection below instead of the single happy-path flow — it seeds `.renmark/memory/qa-flows.md` (the reusable QA-flow memory) rather than verifying one feature. `--bootstrap` is ignored unless `--qa` is also present.

### When to use which mode

Core principle: **shell/code tests prove a command exits 0, not that the user-visible result is correct.** Browser QA is what tells the whole story — use it whenever there is a real UI surface and the cost is justified. Browser QA is never automatic.

| Mode | Use it when |
|---|---|
| **Default shell smoke** | The standing default after every orchestrate. For non-UI work (CLI, data scripts, libraries, APIs) and as the fast first-pass gate on any feature. Always runs first; browser QA is opt-in on top. |
| **`--qa`** | The feature has a user-visible browser surface and you want to confirm it actually *renders* and the primary flow works live — not just that a shell command exited 0. Opt-in, one happy-path flow. |
| **`--deep-qa`** | Deeper runtime/visual edge-case validation: after `--qa` is green, when the change touches layout/UI, error paths, or risky inputs — to learn where it breaks under unusual-but-valid conditions. Gated on a passing `--qa` for the current sha. |

**Recommendation triggers (advisory — browser QA is recommended, NOT automatic).** Every implementation still gets shell smoke as the default; browser QA is opt-in on top. Surface these as a one-line recommendation; never auto-run a browser.

- **Recommend `--qa`** when the changed files / feature scope touch any user-visible surface: templates / views, frontend JS/CSS, routes or controllers that serve browser pages, forms or buttons, settings screens, preview / render UI, checkout / pricing, or anything else a user can see in a browser.
- **Recommend `--deep-qa`** only for **risky UI/runtime changes**: layout refactors, state persistence, auth / session, render pipelines, multi-step workflows, visual or runtime bug fixes, previously-failed flows, or risky inputs — or after a normal `--qa` passes and the change warrants edge coverage.

State it plainly to the user: browser QA is **recommended, not automatic**; every implementation still gets shell smoke.

## Smoke mode (default)

Reads the plan's intent paragraph via `parser.parse_plan()`, extracts stated user-visible behaviors, cross-references `.renmark/memory/bugs.md` for open regressions whose files overlap with the plan's targets, runs one command per behavior + regression, and reports pass/fail with bounded output (exit code + first 3 lines via `summary.verifier_tail`).

**Compounding verification (G8):** every run — pass or fail — appends to `.renmark/memory/learnings.md`. Failures additionally append a `bugs.md` entry. Verification history accrues as organizational memory.

**Context hygiene (G3, G5):** the orchestrator NEVER reads source files. Only command output, bounded at 3 lines per command. The full verification artifact lives at `.renmark/reviews/YYYY-MM-DD-<sha>.verification.md`; the orchestrator emits only the pointer summary.

## When to Use

- **Automatically by `/renmark:orchestrate`** after a fully clean run (v0.3.3+) — orchestrate clears pipeline state, sets stage `created`, then invokes this. You rarely run it by hand.
- Manually to re-verify an already-built feature (stage `created` or later).
- Before `/renmark:finish`.

**Do NOT use:**
- As a substitute for a test suite — this is feature-level smoke testing, not unit coverage
- To fix failures — route those to `/renmark:debug`
- When the orchestrate pipeline is still in flight — refuse if `pipeline_is_resumable(repo)` is True (this is also why orchestrate only auto-verifies on a fully clean run)

## Steps

**Step 0 — Context check + pipeline gate.** Call `lifecycle.skill_preamble(repo, 'verify')`. If it returns a non-None hint, surface as a one-line note. Also check `state.read_pipeline_state(repo)` — if a prior orchestrate run is paused or in flight (`pipeline_is_resumable(repo)` is True), refuse:

> *"Orchestrate did not finish cleanly. Run `/renmark:debug` first or re-run `/renmark:orchestrate --resume`."*

Verify the lifecycle stage is `created` or later. If `stage == "init"` or `"plan-validated"`, refuse — there's nothing to verify yet.

### 1. Read the plan goal + cross-reference open bugs

```python
from renmark import parser, lifecycle
from pathlib import Path
plan_path = lifecycle.read_lifecycle(repo).artifacts.get("plan")
tasks = parser.parse_plan(Path(plan_path))  # plain list[Task] — there is no Plan object
target_files = {t.target for t in tasks}
# The intent block is the prose ABOVE the first task header; parse_plan drops it,
# so read it from the plan file directly:
goal_paragraph = Path(plan_path).read_text(encoding="utf-8").split("### Task", 1)[0].strip()
```

Extract N user-visible behaviors from `goal_paragraph` — what the feature is supposed to do, not how it was decomposed.

**Regression cross-reference (G8 compounding):** read `.renmark/memory/bugs.md`. For each open bug, check if its declared `files:` overlap with `target_files`. Add each overlapping bug as an additional smoke test — *"the fix for bug #N still holds: <bug.symptom>"*. This is how prior failures expand future regression coverage.

### 2. Build smoke tests

For each behavior + regression, write one shell command a user would actually run. Not internal module checks — observable output.

| Behavior | Example smoke test |
|---|---|
| "create entries with frontmatter" | `node src/journal.js new "Test" --tags "x" && echo OK` |
| "list past entries" | `node src/journal.js list \| grep "Test"` |
| "search by keyword" | `node src/journal.js search "Test" \| grep "Test"` |
| "store in SQLite" | `test -f ~/md-journal/journal.db && echo OK` |
| (regression) "bug #42 — empty input no longer crashes" | `echo "" \| node src/journal.js new && echo OK` |

### 3. Run and report

For each smoke test, call `summary.verifier_tail(cmd, cwd=repo, tail_lines=3)`. Orchestrator-visible output per test is bounded at 1 line: `exit <code> | <first 3 lines collapsed>`. Do NOT read source files.

Sample output:

```
verify: <feature-name>

✅ create entry — exit 0 | OK
✅ list entries — exit 0 | Test
❌ search entries — exit 1 | Error: no such table: entries
✅ bug #42 regression — exit 0 | OK

Result: 3/4 requirements verified.
Failed: search entries — run /renmark:debug with symptom: "search exits 1: no such table: entries"
```

### 4. Emit verification artifact (G6)

Write `.renmark/reviews/YYYY-MM-DD-<sha>.verification.md` via `summary.write_artifact`:

```python
from renmark import summary
summary.write_artifact(
    artifact_path,
    artifact_type="verification",
    body=full_test_log,  # all commands + bounded outputs
    summary_lines=[
        f"{passed}/{total} behaviors verified",
        f"feature: {feature_name}",
        f"failed: {', '.join(failed_names) or 'none'}",
        f"regressions checked: {n_regressions}",
        f"next: {recommended_next_command}",
    ],
    related_plan=plan_path,
    source_sha=summary.git_head_sha(repo),
    generator="verify",
    completion_state="complete" if passed == total else "partial",
    confidence="high" if passed == total else "medium",
    validation_status="validated",
)
```

Emit only the pointer to the orchestrator's conversation via `summary.emit_pointer(artifact_path, "verify")`.

### 5. Compounding learnings + bug logging (G8)

On EVERY run (pass or fail):

```python
from renmark.memory import append_learning
append_learning(
    repo,
    signal=f"verify-{feature_name}",
    observation=(
        f"{passed}/{total} behaviors verified; "
        f"failed: {','.join(failed_names) or 'none'}; "
        f"regressions: {n_regressions}"
    ),
    source=str(artifact_path),
    model="verify",
)
```

On any FAIL:

```python
from renmark.memory import log_bug
for failed in failed_tests:
    log_bug(
        repo,
        title=f"verify failure: {failed.name}",
        severity="medium",  # promote to high if it's a regression of a closed bug
        symptom=failed.bounded_output,
        root_cause="(unknown — route to /renmark:debug)",
        fix="(pending)",
        lesson=f"smoke test '{failed.name}' failed during verify of {feature_name}",
    )
```

This is what makes verification compound. Every failed verify expands the next verify's regression set; every passed verify accrues confidence in the routing memory.

### 6. Lifecycle update

```python
from renmark import lifecycle
lifecycle.write_lifecycle(repo, stage="verified",
                          artifact_update=("verification", str(artifact_path)))
```

Sets the stage to `verified` so `/renmark:resume` knows the next step is `/renmark:codereview` (or `/renmark:finish` if review was already done in a prior pass).

### 7. Hand off (wizard step)

Render the hand-off menu from `${CLAUDE_PLUGIN_ROOT}/skills/_shared/handoff-menu.md`, applying the rendering rules:

- **Omit `[s] Smoke test`** — we just ran smoke.
- **Show `[qa] QA`** unconditionally (always reachable as a different lens).
- **Show `[dq] Deep QA`** only if a passing `.qa.md` exists for the current sha.
- **Show `[c] Code review`** unconditionally.
- **Show `[d] Debug`** only if any smoke test failed.
- **Show `[f] Finish`** and `[n] Nothing` unconditionally.

Prefix the menu with `N/M requirements verified. Artifact: PATH.` and end with `What's next?`.

Dispatch on the chosen option (arrow-selected via `AskUserQuestion`, or a typed number/bracket letter in the text fallback): invoke the matching `/renmark:` skill (passing the failed-symptom into `/renmark:debug` if `[d]`), or stop on `[n]`. Require an explicit choice — don't proceed without one.

---

## QA mode (`verify --qa`)

Opt-in live-browser end-to-end check. Proves the feature works from rendered state, not exit codes. renmark can drive the browser through **either of two channels** — the Chrome DevTools MCP or the native Claude-in-Chrome extension — chosen by environment (see *Browser channel selection* below). Runs **exactly one** happy-path flow, one at a time in the main agent (the browser session is a singleton — no subagent fan-out, no parallel pages). All heavy evidence goes to disk; chat sees only the ≤5-line verdict.

### Applicability gate (before opening a browser)

1. **Web project?** Read `.renmark/memory/stack.md` and/or `package.json`. If there's no frontend or web server (CLI tool, pure data script, ML notebook), QA is N/A — print *"no browser surface to test — verify --qa is N/A for this project"* and stop. Do not open a page that doesn't exist.

2. **Browser channel selection (renmark supports two).** renmark runs on both WSL and the native Windows/desktop app, so QA can drive a browser through either of two channels. **Plain CLI sessions — including Windows PowerShell/cmd — default to Chrome DevTools MCP unless `claude --chrome` is explicitly connected.** Pick by environment, with the CLI / MCP path as the default:

   | Channel | How it connects | When renmark uses it |
   |---|---|---|
   | **Chrome DevTools MCP** (default) | MCP server (`chrome-devtools`) over the Chrome DevTools Protocol | **The universal default for every CLI session** — Windows PowerShell, cmd, macOS/Linux terminals — and the **only** option under WSL, where it can target Chrome running on the Windows host. |
   | **Native Claude-in-Chrome** (`claude --chrome`) | Native messaging to the "Claude in Chrome" extension (no MCP) | Used **only when the native channel is actually connected** — typically the Windows / desktop app (or any session that explicitly ran `claude --chrome`). Native messaging does **not** cross the WSL boundary. |

   **Detection + precedence (first match wins):**
   1. **WSL?** — `grep -qi microsoft /proc/version`, or `$WSL_DISTRO_NAME` / `$WSL_INTEROP` is set → use **Chrome DevTools MCP** (probe `list_pages`). The native extension is unsupported on WSL; do not attempt it.
   2. **Native channel connected?** — concretely: this Claude Code session was launched with `claude --chrome` (or reconnected via the `/chrome` built-in) AND that integration reports the extension connected. There is no shell probe for this — it is a session capability the agent can observe directly, unlike MCP's `list_pages`. If the session was not started with `--chrome`, treat native as NOT connected and fall through to rule 3. When it IS connected → use the **native Claude-in-Chrome** channel.
   3. **Otherwise (default — any CLI: PowerShell, cmd, terminal)** → use **Chrome DevTools MCP** (probe `list_pages`). MCP is the default everywhere; the native channel is never assumed, only used when explicitly connected.

   **If the selected channel isn't available, guide then degrade — never block.** Branch the install hint on the **channel that was selected** (not on the OS bucket), then fall back to shell smoke and run the Smoke-mode steps above:
   - **Selected channel = Chrome DevTools MCP** (the default, and all WSL/CLI sessions) → *"browser not connected — ran shell smoke only. For live E2E, add the Chrome DevTools MCP: `claude mcp add chrome-devtools --scope user -- npx chrome-devtools-mcp@latest`"* (the `--` separates claude's flags from the stdio launch command — omitting it misparses the `npx` args).
   - **Selected channel = native Claude-in-Chrome** → *"native browser channel not connected — ran shell smoke only. For live E2E, install the 'Claude in Chrome' extension, then relaunch with `claude --chrome` (or run the Claude Code built-in `/chrome` to reconnect — it is a core command, not a renmark one)."*

   Record the chosen channel in local state and name it once in the verdict header (e.g. `verify --qa: <feature> (1 E2E flow, live browser — Chrome DevTools MCP)`). Everything below — flow derivation, pass criteria, evidence handling, and the context-hygiene contract — is **identical regardless of channel**; only the connection differs.

### Server lifecycle

E2E needs the app running:

1. Read the run command from `CLAUDE.md § Testing` or `.renmark/memory/stack.md`.
2. Detect if the dev server is already up — probe the health URL (from `stack.md`, or infer `localhost:3000` / `:5173` / `:8000` from the stack). If `curl -sf <health-url>` returns 0, reuse the running server.
3. If not running, boot it via `Bash` with `run_in_background=True` and wait for the health endpoint (bounded retry, ~30s; abort with a clean error if it never comes up).
4. Record `qa_started_server: bool` in local state — we tear down only what we booted, never a server the user is using.
5. On completion (pass or fail), if `qa_started_server` is True, kill the background shell.

### BEFORE QA — flow selection from memory

Before deriving the happy-path flow, consult the QA-flow memory to reuse a known-good journey when one exists:

1. Read `.renmark/memory/stack.md`, `.renmark/memory/project-map.md`, `.renmark/memory/qa-flows.md` **if it exists**, and `.renmark/memory/bugs.md`.
2. **Pick the best matching known flow** for the current feature — match on the changed files / routes / surfaces against the flows recorded in `qa-flows.md`.
3. **If no known flow matches**, synthesize a one-off flow from the plan / spec goal (same goal-backward derivation as "The single happy-path flow" below).
4. **If `qa-flows.md` is missing or empty, behave exactly as today** — synthesize the flow from the plan goal. Existing QA must not break in the absence of QA-flow memory; the file is a reuse cache, never a hard dependency.

The selected flow (matched or synthesized) is what the next subsection drives. Carry whether it was *matched* or *synthesized-one-off* into the AFTER-QA convergence step (a synthesized one-off that passes is a promotion candidate).

### The single happy-path flow

Derive **one** highest-value journey from the spec's stated user-visible behaviors — same goal-backward engine as smoke, just the #1 flow (the action named first in the goal paragraph, or the primary user action). State which flow you chose in one line before driving: *"QA flow: <chosen> — redirect with [edit] before I open the browser? [y/edit]"* (default to running if no response).

Drive it with the selected channel's tools (the tool names below are the Chrome DevTools MCP set; the native Claude-in-Chrome channel exposes equivalent navigate / snapshot / click / fill / wait / screenshot / console / network actions — use whichever the active channel provides):

- `navigate_page` to the app URL
- `take_snapshot` (accessibility tree) to locate elements — transient, not pasted into chat
- `click` / `fill` / `fill_form` to perform the main action
- `wait_for` the expected result text/element
- `take_screenshot` at each step → `.renmark/reviews/qa/<feature>/step-N.png` (NEVER inline the image)
- **`before/after` visual capture around the main action** — `take_screenshot` immediately *before* the main action → `.renmark/reviews/qa/<feature>/before.png`, and immediately *after* → `.../after.png`. Then compare the two shots yourself (agent-observed visual comparison — look at both images; this is NOT a new pixel-diff dependency) to surface any visible UI change or regression, and write a one-line diff note of observed differences into the artifact body. NEVER inline a screenshot or paste raw diff data into chat — images and the diff note live on disk and in the artifact body only.
- `list_console_messages`, `list_network_requests` for failure-mode signals — captured to artifact body, not chat

### Happy-path pass criteria

The flow PASSES only if **all hard criteria** hold. Soft criteria are recorded as warnings but don't fail.

**Hard (any one failing = FAIL):**

1. **Page loads.** `navigate_page` resolves; document reaches a ready state; the expected root content/element is present (not a blank page, not the framework's error/500 page).
2. **No uncaught console errors** during the flow — `list_console_messages` shows no `error`-level entries or uncaught exceptions. Warnings are soft.
3. **No failed network requests on the path** — `list_network_requests` shows no 4xx/5xx for calls the flow triggers. The happy path must not hit an error response.
4. **The action completes and the expected result is visible.** After the main action, the UI reaches the success state the spec promised — the expected text/element renders (asserted via `wait_for` / snapshot). No infinite spinner, no hang, no silent no-op. *This is the goal-backward assertion: the user-visible behavior the spec described actually happened, observed live.*
5. **No error UI.** No error toast/banner, no stack-trace page, no empty state where content was expected.
6. **Visual/layout integrity.** The rendered UI has no broken layout: no **overlapping interactive elements**, no content clipped/cut off or pushed off-screen, no controls rendered on top of each other or outside their container, no critical element hidden behind another. Detect with tools already in use — `take_snapshot` (accessibility tree + roles to confirm expected controls are reachable), `take_screenshot` (visual confirmation), and optionally `evaluate_script` reading `getBoundingClientRect` on key controls to flag overlapping bounding boxes or off-viewport positions. The verdict line names this criterion on failure (e.g. *"criterion 6: submit button overlaps the input — layout broken at <viewport>"*).

**Soft (recorded, don't fail):**

7. **Persistence** — if the action creates/saves something, an optional follow-up check (reload or list view) confirms it stuck. Flagged as a warning if it can't be confirmed.
8. **Latency sanity** — the action resolved within a generous bound. A slow-but-correct result warns, doesn't fail.

Each criterion maps to a specific signal so the verdict line can name *which* one failed (e.g. *"❌ checkout — criterion 4: success text never rendered; spinner still visible after 10s"*).

### Bootstrap path (`verify --qa --bootstrap`)

When `--bootstrap` modifies `--qa`, the goal is **not** to verify one feature — it is to seed `.renmark/memory/qa-flows.md` with the project's critical user flows so later `--qa` / `--deep-qa` runs can reuse them. Run this instead of *The single happy-path flow* (the applicability gate, browser-channel selection, and server lifecycle above still apply):

1. **Read project memory + history:** `.renmark/memory/stack.md`, `.renmark/memory/project-map.md`, the plans under `.renmark/plans/`, `.renmark/memory/bugs.md`, and `CHANGELOG.md`.
2. **Detect the main browser surfaces/routes** — the entry routes, primary pages, forms, and controllers serving browser pages — from stack/project-map + the running app.
3. **Ask or infer the top 3–5 critical user flows.** Prefer the interactive `AskUserQuestion` hand-off to confirm the candidate flows; infer from the surfaces above if the user defers.
4. **Create `.renmark/memory/qa-flows.md`** (the QA-flow memory file) seeded with those flows.
5. **When browser QA actually runs**, drive each candidate flow with the active channel (same steps/criteria as a normal `--qa` flow) and save **baseline notes + screenshot/artifact paths** into each flow entry (paths only — evidence stays on disk).
6. **If browser QA cannot run** (no channel connected / degrade-to-shell), still create the documented candidate flows in `qa-flows.md`, each marked **UNVERIFIED** (no baseline screenshots yet) so a later `--qa` can verify and upgrade them.

Bootstrap honors the same context-hygiene contract: chat sees only a bounded summary (flows created + verified/UNVERIFIED counts + the `qa-flows.md` path); screenshots and dumps stay on disk.

### Context-hygiene contract (non-negotiable)

The MCP tools return large payloads (DOM trees, console dumps, screenshot bytes). **None of that enters the conversation.** Per step:

- Screenshots → `.renmark/reviews/qa/<feature>/step-N.png`
- Console + network dumps → captured into the artifact body, not chat
- Accessibility snapshots are used transiently to find selectors, then discarded

Bounded verdict format (this is what chat sees, nothing more):

```
verify --qa: <feature>  (1 E2E flow, live browser)

✅ load app — rendered, no console errors
✅ <main action> — result visible: "<expected>"
❌ <assertion> — expected "Order placed", got blank; console: TypeError cart undefined @ cart.js:42

Result: E2E flow FAILED at step 3.
Evidence: .renmark/reviews/qa/<feature>/  (screenshots + console log)
Failed: run /renmark:debug — "checkout: cart undefined at cart.js:42; repro: add item → checkout → blank"
```

### Artifact (G6)

Write `.renmark/reviews/YYYY-MM-DD-<sha>.qa.md` via `summary.write_artifact`:

```python
summary.write_artifact(
    qa_artifact_path,
    artifact_type="qa",
    body=full_step_log,  # screenshot paths + console slice + network slice + step-by-step
    summary_lines=verdict_lines,  # the ≤5-line block above
    related_plan=plan_path,
    source_sha=summary.git_head_sha(repo),
    generator="verify-qa",
    completion_state="complete" if all_hard_pass else "partial",
    confidence="high" if all_hard_pass else "medium",
    validation_status="validated",
)
summary.emit_pointer(qa_artifact_path, "verify --qa")
```

### Stop and report on break (could-not-finish)

If the flow cannot finish, the run **STOPS at that step**, marks the flow FAILED, names the failing step + criterion in the verdict, and does **NOT** silently continue or report success. Trigger conditions:

- the page fails to load,
- an action hangs (infinite spinner / never reaches the expected state within the bounded `wait_for`),
- the browser becomes unresponsive,
- an uncaught exception fires,
- the layout is visibly broken (overlap / clipping — criterion 6).

Such visual/layout and "could-not-finish" failures are logged to `bugs.md` via the existing `memory.log_bug` convergence loop below, exactly like functional failures — a reproducible finding (symptom + offending criterion + screenshot path + repro steps). The early exit ties into the same bounded-verdict + artifact + learnings flow; do not invent a parallel reporting path.

### DURING QA — run the selected flow

Run the **selected flow** (from *BEFORE QA — flow selection from memory*) using the existing browser-channel behavior already documented above — do not duplicate or weaken those steps:

- Drive it through the active channel's tools per *The single happy-path flow* (navigate / snapshot / click / fill / wait / screenshot / console / network).
- Capture the **before/after screenshots** around the main action and the agent-observed visual comparison exactly as documented there.
- Capture `list_console_messages` / `list_network_requests` to the artifact body.
- Enforce the **visual/layout integrity** check (criterion 6 — overlapping / clipped controls, off-viewport elements) per *Happy-path pass criteria*.
- Honor **Stop and report on break**: STOP + FAIL on hang / crash / broken layout; do not silently continue.

### QA convergence loop

- On **fail** (including a stop-on-break early exit): `memory.log_bug` to `.renmark/memory/bugs.md` with a **reproducible** finding — symptom + offending criterion + console/error + file:line if discoverable + screenshot path + repro steps, **linking the review artifact** (the `.qa.md` path). Severity `medium` (or promote to `high` if it's a regression of a closed bug). *(Unchanged.)*
- On **pass**: update the QA-flow memory at `.renmark/memory/qa-flows.md`:
  - If the flow was **matched** from `qa-flows.md`, update its entry (refresh the linked passing review artifact path + baseline screenshot paths).
  - If the flow has no entry yet, **append** it.
  - If the flow was a **synthesized one-off** that just passed, **promote** it into `qa-flows.md` as a reusable flow — link it to the passing review artifact (`.qa.md`) and the baseline screenshot paths (`before.png` / `after.png` / `step-N.png`).
  - Keep all heavy evidence on disk + artifact body; chat stays a bounded verdict. The flow entry stores **paths**, not embedded screenshots or dumps.
- On **every** run: `memory.append_learning(signal="verify-qa-<feature>", observation=...)`.
- A later `verify --qa` re-runs this flow AND the bugs.md regression set; after a fix the exact flow confirms green.

### Lifecycle

`--qa` does NOT add a new stage. It runs at stage `verified` (or re-runs there). A passing/failing QA updates the verification artifact pointer via `lifecycle.write_lifecycle(repo, artifact_update=("qa", str(qa_artifact_path)))` but leaves `stage="verified"` — codereview / finish remain the next steps.

### QA hand-off

Render the menu from `${CLAUDE_PLUGIN_ROOT}/skills/_shared/handoff-menu.md`:

- **Omit `[qa] QA`** — we just ran QA.
- **Show `[s] Smoke`** (re-test from the other lens).
- **Show `[dq] Deep QA`** only if QA passed (a complete `.qa.md` for the current sha now exists).
- **Show `[c] Code review`** unconditionally.
- **Show `[d] Debug`** only if QA failed; pass the failed-step symptom and the artifact pointer to debug.
- **Show `[f] Finish`** and `[n] Nothing` unconditionally.

---

## Deep QA mode (`verify --deep-qa`)

Three live-browser edge-case flows, **risk-ranked** from diff + behaviors + bugs.md. Same singleton-browser, same context-hygiene contract as `--qa`. The pass condition flips: an edge case passes when the app fails *gracefully* (clear error / no crash / no uncaught exception) — NOT necessarily when the action succeeds.

### Deep QA gate (refuse-on-empty-QA)

Before doing anything, scan `.renmark/reviews/*.qa.md` via `summary.read_metadata`:

```python
from renmark import summary
head = summary.git_head_sha(repo)
qa_passed = any(
    md.get("source_sha") == head
    and md.get("completion_state") == "complete"
    and md.get("generator") == "verify-qa"
    for md in (summary.read_metadata(p) for p in qa_review_paths)
)
```

If `qa_passed` is False, refuse with:

> *"Run `/renmark:verify --qa` first — deep QA tests the edges of a flow that's already confirmed to work. Edge cases on a broken happy path are noise."*

Do not open a browser. Stop.

### Reuse the QA setup

The app is typically still running from the prior `--qa`. Same applicability gate (web project + browser channel selection — Chrome DevTools MCP or native Claude-in-Chrome, picked by environment). Same server lifecycle: detect-or-boot, record-what-we-booted, tear-down-only-our-own-on-exit.

Deep QA also reuses the **QA-flow memory**: select the base flow via *BEFORE QA — flow selection from memory* (read `qa-flows.md` if it exists; behave as today when it is missing or empty), and on a passing run **promote** any synthesized one-off into `qa-flows.md` exactly as the QA convergence loop does.

### Plan phase — risk-rank, then pick 3 (no browser yet)

Before launching anything, spend a distinct planning pass deciding *what is most likely to break*. Inputs:

- the feature's behaviors (spec / plan goal)
- the **diff** for this feature (`git diff <range> --stat` and bounded per-file diffs — read which inputs, branches, and error paths the code added; never paste the diff into chat)
- open `bugs.md` entries whose declared `files:` overlap the diff (history of where it broke before)
- the edge-case categories table below as a checklist of failure *modes*

**Edge-case categories (the failure-mode checklist):**

| Category | Example for a "create journal entry" feature |
|---|---|
| Empty / missing input | submit with the title field blank |
| Boundary / extreme size | a 10,000-char title; zero existing entries; the 1000th entry |
| Malformed / hostile input | title = `<script>alert(1)</script>` or `'; DROP TABLE` |
| Error path / failure | submit while the backend/DB is unreachable |
| State / sequence | double-click submit; navigate back mid-action; refresh mid-form |
| Authz | act as an unauthorized / logged-out user (if applicable) |

Produce a ranked list of candidate failure modes (most-likely-to-break first), each tagged with the category it stresses and *why* it's risky (e.g. *"title field has no maxlength in the diff → 10k-char input likely overflows layout or DB column"*). Take the **top 3 distinct cases**, preferring cases that stress *different* categories so the 3 aren't redundant.

Write the full ranked list to the artifact body. Surface only the chosen 3 + one-line rationale each, and let the user redirect before any browser action:

> *"Deep QA plan — 3 highest-risk edges for `<feature>`:*
> *  1. empty title — no client validation seen in diff*
> *  2. backend-down submit — new fetch has no catch/timeout*
> *  3. 10k-char title — column + layout untested at size*
> *Run these one at a time in risk order? [y/edit/n]"*

On `edit`, accept replacements (also from the ranked list, or freeform). On `n`, stop. Default to `y` if no response.

### Run them serially

One at a time (singleton browser), in risk order — most-likely-to-break first, so any fail surfaces fast. Each edge case follows the same shape as the `--qa` happy-path flow:

1. Announce: *"running 1/3: empty title…"* (progress visible without dumping detail)
2. Navigate → take a `before/after` pair around the edge action: `take_screenshot` immediately *before* → `.renmark/reviews/qa/<feature>/deep/case-N/before.png`, perform the edge action, then `take_screenshot` immediately *after* → `.../after.png`. Compare the two shots yourself (agent-observed visual comparison — look at both images, NOT a pixel-diff dependency) and write a one-line diff note of observed differences into the artifact body.
3. Assert **graceful handling**, not success:
   - **Hard criteria for edge cases (any fail = FAIL):**
     - No uncaught console exception
     - No browser crash / page unresponsive
     - No corrupt state or broken layout visible after the action (e.g. half-saved record; **overlapping interactive elements**, content clipped/cut off or pushed off-screen, controls rendered on top of each other or outside their container, a critical element hidden behind another — detect via `take_snapshot` + `take_screenshot`, optionally `evaluate_script` reading `getBoundingClientRect` to flag overlap or off-viewport positions)
     - Either the action completed safely (the app tolerated the edge) OR the app rejected it with a clear, visible error message — *not* a silent no-op, *not* an infinite spinner
4. Screenshot + console/network slice → `.renmark/reviews/qa/<feature>/deep/case-N/`
5. Emit one verdict line

**Stop and report on break:** if a case cannot finish — the page fails to load, the action hangs (infinite spinner / never reaches expected state within the bounded `wait_for`), the browser becomes unresponsive, an uncaught exception fires, or the layout is visibly broken (overlap/clipping) — STOP at that step, mark the case FAILED, name the failing step + criterion in the verdict, and do NOT silently continue or report success. Log it to `bugs.md` via the `memory.log_bug` convergence loop below (symptom + offending criterion + screenshot path + repro steps), exactly like functional failures, and tie the early exit into the same bounded-verdict + artifact + learnings flow.

After all 3 (or after an early-exit on hard crash), assemble the bounded report.

### Bounded Deep QA verdict

```
verify --deep-qa: <feature>  (3 edge cases, live browser)

✅ empty title       — rejected with inline error, no crash
✅ 10k-char title    — truncated, saved, no console error
❌ backend down      — spinner hangs forever; expected a timeout/error toast
                       console: net::ERR_CONNECTION_REFUSED (uncaught)

Result: 2/3 edge cases handled gracefully.
Evidence: .renmark/reviews/qa/<feature>/deep/
Failed: run /renmark:debug — "no timeout handling when backend unreachable; repro: stop server → submit → spinner never resolves"
```

### Deep QA artifact

Write `.renmark/reviews/YYYY-MM-DD-<sha>.deep-qa.md` via `summary.write_artifact`:

```python
summary.write_artifact(
    deep_artifact_path,
    artifact_type="deep-qa",
    body=full_run_log,  # the full ranked candidate list + per-case screenshots + console/network slices
    summary_lines=verdict_lines,  # the ≤5 lines above
    related_plan=plan_path,
    source_sha=summary.git_head_sha(repo),
    generator="verify-deep-qa",
    completion_state="complete" if all_pass else "partial",
    confidence="medium",  # edge cases are inherently lower-confidence than the happy path
    validation_status="validated",
)
```

### Deep QA convergence

Same as `--qa`: every fail (including a stop-on-break early exit) logs a reproducible `bugs.md` entry via `memory.log_bug` (symptom + offending criterion + screenshot path + repro steps); every run appends a learning. The next `verify --qa` picks up the new bug entry in its regression set, so a Deep QA finding becomes a recurring smoke check too.

### Why serial-in-main, not subagents

At 1 (`--qa`) + 3 (`--deep-qa`) flows that each dump evidence to disk and return only verdict lines, the main context never holds heavy payloads. Subagent fan-out buys nothing here and adds coordination cost against a singleton browser. Revisit only if a future version needs *many* journeys where verdict-line + orchestration overhead pressure the window.

### Deep QA hand-off

Render the menu from `${CLAUDE_PLUGIN_ROOT}/skills/_shared/handoff-menu.md`:

- **Omit `[dq] Deep QA`** — we just ran it.
- **Show `[s] Smoke`** and `[qa] QA` (re-test from other lenses if a fix lands).
- **Show `[c] Code review`** unconditionally.
- **Show `[d] Debug`** only if any edge case failed; pass the failed-case symptom to debug.
- **Show `[f] Finish`** and `[n] Nothing` unconditionally.

---

## Governance compliance

Upholds G2/G3/G6/G7/G8/G9/G10/G12 — see `CLAUDE.md` governance rules for definitions. Skill-specific load-bearing behavior: G8 compounding is the differentiator — every run (any mode) appends to `learnings.md`, every fail to `bugs.md`, and the next verify reads `bugs.md` to expand its regression set. Output is bounded via `summary.verifier_tail(tail_lines=3)` for smoke, and a strict ≤5-line verdict block for `--qa` / `--deep-qa` (G3); all artifacts carry full metadata (G6). G5 holds for all modes — source files are never read into chat. G11 is N/A for smoke (local shell), and held by construction for `--qa` / `--deep-qa` (the browser MCP session lives in the main agent; no subagent dispatch).
