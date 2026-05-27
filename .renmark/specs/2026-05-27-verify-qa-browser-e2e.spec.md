---
artifact_type: spec
schema_version: 1
created_at: 2026-05-27
generator: brainstorm
related_plan: null
status: draft
---

# Spec — `verify --qa` / `--deep-qa`: opt-in live browser E2E in the verification stage

## Context

`/renmark:orchestrate` already auto-runs `/renmark:verify` after a clean build
(v0.3.3). Today verify is a **shell smoke test**: it derives the spec's
user-visible behaviors and runs one terminal command per behavior. That proves
the happy path *responds*, but for web/UI projects it can't prove the feature
actually *works in a browser* — you can still ship something that 200s on curl
but renders blank or throws in the console.

This spec adds an **opt-in, single-flow, live-browser end-to-end check** as one
more option on verify's end-of-run menu. It is the minimalist first step of a
QA capability; a future deep/multi-journey mode is explicitly out of scope here.

**Driving goal (user's words):** stop the loop of "ask to fix → find it's still
broken → surgically fix what QA should have caught." A live E2E pass that runs
automatically-on-request and produces *specific, reproducible* findings makes
the fix loop converge.

## Goals

1. Add `[qa] Verify --qa` to verify's hand-off menu (both the auto-run-from-orchestrate
   path and the standalone `/renmark:verify` path).
2. When chosen, run **one** happy-path user journey live in the browser via the
   Chrome DevTools MCP tools, asserting rendered/visible result — not terminal exit codes.
2b. Make the three quality gates (smoke / QA / code review) **mutually reachable**:
   each gate's hand-off menu offers the other two, via a single shared menu
   (`_shared/handoff-menu.md`) reused by verify and codereview. A feature can be
   tested from every angle in any order before finishing.
2c. Add `verify --deep-qa`: a **risk-based planning pass** picks the 3 edge cases
   *most likely to break* (from the diff, behaviors, and bugs.md history), then
   runs them one at a time the same live-browser way as `--qa`. **Gated behind a
   passing `--qa`** (edge cases are pointless until the happy path works). Same
   disk-dump + bounded-verdict + bugs.md convergence contract.
3. Preserve context-window hygiene absolutely: all heavy evidence (screenshots,
   console logs, network, DOM snapshots) is written to disk under
   `.renmark/reviews/qa/`; the conversation sees only a bounded verdict (≤5 lines).
4. Increase verification certainty: a QA failure logs to `bugs.md` with a
   reproducible finding (what failed + console/error + repro steps), so a later
   re-run re-checks that exact flow and confirms convergence.
5. Degrade gracefully: web project + browser connected → run E2E; otherwise
   fall back to shell smoke with a one-line note. Never block or crash.

## Non-goals

- **Unbounded journeys / subagent fan-out.** `--qa` runs exactly 1 happy-path
  flow; `--deep-qa` runs exactly 3 edge-case flows. We do NOT support an
  arbitrary N, and we do NOT fan out to analysis subagents — at 1+3 serial
  flows that dump evidence to disk and return only verdict lines, the context
  stays clean without subagents. (Revisit only if flow count ever grows large.)
- **Subagents driving browsers.** The browser MCP session is a singleton owned
  by the main agent; no parallel browser dispatch. Both `--qa` and `--deep-qa`
  run flows **one at a time** in the main agent. (See Architecture.)
- **A new `/renmark:qa` command.** This is a flag/option on verify — no new
  command, no new lifecycle stage.
- **Fixing failures.** QA reports; fixes route to `/renmark:debug` as today.
- **Replacing a real test suite.** This is feature-level E2E smoke, not unit coverage.

## Design

### The three quality gates are mutually reachable

A feature should be testable from every angle, in any order, until the user is
satisfied — not pushed down a one-way line. There are three independent quality
lenses, plus the terminal actions:

| Gate | What it checks | Command |
|---|---|---|
| **Smoke** | happy path responds (shell, terminal) | `/renmark:verify` (light) |
| **QA** | feature works live in a browser (rendered E2E) | `/renmark:verify --qa` |
| **Code review** | the code itself is sound (adversarial, static) | `/renmark:codereview` |

**Each gate's hand-off menu offers the other two**, so you can chain
smoke → QA → review → QA-again in whatever order the feature needs before
finishing. This is a shared menu, defined once and reused by all three skills:

```
[s]  Smoke test  — re-run the goal-backward shell smoke test via /renmark:verify
[qa] QA          — run one happy-path flow live in the browser via /renmark:verify --qa
[dq] Deep QA     — run 3 edge-case flows live in the browser via /renmark:verify --deep-qa  (only after QA passes)
[c]  Code review — run an adversarial Codex pass over the diff via /renmark:codereview
[f]  Finish      — close the branch (PR or merge) via /renmark:finish
[d]  Debug       — investigate a failure via /renmark:debug
[n]  Nothing     — stop here; work stays committed
```

Rules for rendering the menu:
- **Omit the gate you just ran** (don't offer "Smoke" right after smoke) — but
  list the other gates, so re-testing a different way is one keystroke.
- **`[dq] Deep QA` is shown ONLY after `--qa` has passed for the current feature**
  (a `.qa.md` artifact exists for the current sha). Edge cases are pointless
  until the happy path works — gating deep QA behind QA enforces that order.
- **`[d] Debug` appears whenever the just-run gate found a failure**; on an
  all-clean run it may be omitted.
- Single source of truth: the menu text lives in
  `${CLAUDE_PLUGIN_ROOT}/skills/_shared/handoff-menu.md` (new shared file,
  same pattern as `_shared/scope-contract.md`) so verify, codereview, and any
  future gate cite it instead of each restating the options — keeps them from
  drifting and keeps each SKILL.md small.

This means the menu changes touch **three** skills, not one:
- `verify` (light/smoke branch) → offer QA + Code review (+ Debug on fail).
- `verify --qa` branch → offer Smoke + Code review (+ Debug on fail).
- `codereview` → offer Smoke + QA (+ Debug on fail) in addition to its existing
  Open/Fix options.

### Entry point

`[qa]` re-invokes verify in `--qa` mode against the same plan/feature. It is
purely additive — light shell verify has already run and passed at this point.
The orchestrate auto-run still triggers light smoke first; QA and code review
are always reached by choosing them from the shared menu (opt-in, never auto).

### Applicability gate (before doing anything)

1. **Web project?** Read `.renmark/memory/stack.md` / `package.json`. If there's
   no frontend/server (CLI tool, data script), `--qa` is N/A → tell the user
   "no browser surface to test" and stop. Don't open a page that doesn't exist.
2. **Browser connected?** Check the Chrome DevTools MCP is available
   (`list_pages` succeeds). If not → fall back to shell smoke, print:
   *"browser not connected — ran shell smoke only; connect the extension for live E2E."*

### Server lifecycle

E2E needs the app running. verify --qa:

1. Reads the run command from `CLAUDE.md § Testing` (or `stack.md`).
2. Detects if the dev server is already up (probe the health URL). If not,
   boots it in the background (`Bash run_in_background`) and waits for the
   health endpoint to respond (bounded retry, e.g. 30s).
3. Records whether *it* started the server (so it tears down only what it booted).
4. On completion (pass or fail), tears down any server it started.

### The single E2E flow

Derive the **one** highest-value happy-path journey from the spec's stated
user-visible behaviors (goal-backward, same engine as light verify — just the
#1 flow). Drive it with the Chrome DevTools MCP tools:

- `navigate_page` to the app URL
- `take_snapshot` to locate elements (accessibility tree, not raw DOM)
- `click` / `fill` / `fill_form` to perform the main action
- `wait_for` the expected result text/element
- evaluate the pass criteria below

### Happy-path pass criteria (what `--qa` actually checks)

A happy-path flow PASSES only if **all hard criteria** hold. Soft criteria are
recorded as warnings in the artifact but don't fail the run. These same criteria
are reused by edge cases — only criterion #4 inverts (an edge case expects a
*handled failure*, not a success).

**Hard (any one failing = FAIL):**

1. **Page loads.** `navigate_page` resolves; the document reaches a ready state;
   the expected root content/element is present (not a blank page, not the
   framework's error/500 page).
2. **No uncaught console errors** during the flow — `list_console_messages`
   shows no `error`-level entries or uncaught exceptions. (Warnings are soft.)
3. **No failed network requests on the path** — `list_network_requests` shows
   no 4xx/5xx for calls the flow triggers. The happy path must not hit an error
   response.
4. **The action completes and the expected result is visible.** After the main
   action, the UI reaches the success state the spec promised — the expected
   text/element renders (asserted via `wait_for` / snapshot). No infinite
   spinner, no hang, no silent no-op. *This is the goal-backward assertion: the
   user-visible behavior the spec described actually happened, observed live.*
5. **No error UI.** No error toast/banner, no stack-trace page, no empty state
   where content was expected.

**Soft (recorded, don't fail):**

6. **Persistence** — if the action creates/saves something, an optional
   follow-up check (reload or list view) confirms it stuck. Flagged as a warning
   if it can't be confirmed, since some flows can't be re-observed cheaply.
7. **Latency sanity** — the action resolved within a generous bound (e.g. the
   `wait_for` didn't need its full timeout). A slow-but-correct result warns,
   doesn't fail.

Each criterion maps to a specific signal so the verdict line can name *which*
one failed (e.g. "❌ checkout — criterion 4: success text never rendered;
spinner still visible after 10s"). Evidence (screenshot at the failure point +
the console/network slice) goes to the artifact, not chat.

### Context-hygiene contract (non-negotiable)

This is the make-or-break rule. The MCP tools return large payloads (DOM trees,
console dumps, screenshots). **None of that enters the conversation.** Per step:

- Screenshots (`take_screenshot`) → `.renmark/reviews/qa/<feature>/step-N.png`
- Console + network dumps → captured into the verification artifact body, not chat
- The accessibility snapshot is used transiently to find selectors, then discarded

The orchestrator/chat sees only the bounded verdict, e.g.:

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
`artifact_type: qa`, body = full step log + console + network + screenshot paths,
`summary_lines` = the ≤5-line verdict above, `completion_state` =
complete/partial, `confidence`, `validation_status`.

### Convergence loop (the certainty mechanism)

- On **fail**, log to `bugs.md` via `memory.log_bug` with a **reproducible**
  finding: symptom + console/error + file:line if discoverable + repro steps.
  This is what makes a later fix surgical instead of guesswork.
- On **every** run, append to `learnings.md` (G8 compounding).
- A subsequent `verify --qa` re-runs this flow AND the `bugs.md` regression set,
  so after a fix it confirms the exact flow now passes and nothing regressed.
  The loop converges; no "still broken" surprises downstream.

### Lifecycle

`--qa` does not add a stage. It runs at stage `verified` (or re-runs there).
A passing/failing QA updates the verification artifact pointer but leaves the
stage at `verified` — codereview/finish remain the next steps.

## Architecture notes / constraints

- **Browser MCP is the main agent's, singleton.** verify --qa runs in the main
  Claude Code skill context (which has the MCP tools), not in a codex subprocess
  or Agent subagent. One flow = one session = no concurrency. This is why deep
  multi-journey is deferred — it needs the subagent-analysis pattern in Appendix A.
- **renmark-execute (Python) is not involved.** This is a Claude-driven skill
  step, like verify's existing shell smoke tests. No changes to `renmark/` Python
  modules are strictly required, though `summary.write_artifact` gains an
  `artifact_type: qa` usage and `memory.log_bug` is reused as-is.

## Open questions

1. **Flow selection when the spec lists several behaviors equally.** Heuristic:
   pick the one the spec's goal paragraph names first / the primary user action.
   Confirm with the user in one line before driving? (Leaning: auto-pick, state
   which flow it chose, let them redirect.)
2. **Auth'd pages.** If the happy path needs login, does verify --qa use the
   gstack `setup-browser-cookies` import, or a test account from `.env`? (Likely
   out of scope for v1 — note it as a limitation, support unauth flows first.)
3. **Health-probe URL discovery** when not in CLAUDE.md — infer from stack
   (localhost:3000 / :5173 / :8000) or ask once and record in `stack.md`.

## Success criteria

- For a web project with the browser connected, choosing `[qa]` runs one live
  browser flow and reports pass/fail from **rendered** state, not exit codes.
- The conversation never receives a DOM dump, full console log, or screenshot
  binary — only the ≤5-line verdict + artifact pointer.
- From any quality gate (smoke / QA / code review) the user can reach the other
  two in one keystroke; the menu omits the just-run gate and lists the rest.
  All three skills render the same shared menu text (no drift).
- `[dq] Deep QA` is offered **only** after `--qa` passes for the current sha;
  invoking `--deep-qa` without a prior passing `--qa` refuses with a clear note.
- `--deep-qa` first runs a risk-ranking plan pass (diff + behaviors + bugs.md →
  failure modes ordered by likelihood) and presents the chosen 3 with one-line
  rationale for approval BEFORE opening the browser.
- `--deep-qa` then runs exactly 3 edge-case flows one at a time in risk order,
  each judged on *graceful handling* (clear error / no crash / no uncaught
  console error), dumps evidence to `.renmark/reviews/qa/<feature>/deep/`,
  surfaces only 3 verdict lines + a pointer, and logs reproducible `bugs.md`
  entries on failure.
- A failure produces a `bugs.md` entry specific enough to fix surgically, and a
  re-run confirms the fix.
- For a non-web project or a disconnected browser, verify --qa degrades to shell
  smoke with a clear one-line note — never errors out.

## Deep QA (`verify --deep-qa`)

### Use case vs edge case (definition, for precision)

- A **use case / happy path** is the feature used the normal way, with the
  inputs a user is expected to give. `--qa` tests exactly one of these.
- An **edge case** is a *valid but unusual* condition at the boundary of the
  input space — where bugs hide. Same feature, hostile-ish conditions.

Common edge-case categories `--deep-qa` draws from (it picks the 3 highest-value
for the feature):

| Category | Example for a "create journal entry" feature |
|---|---|
| Empty / missing input | submit with the title field blank |
| Boundary / extreme size | a 10,000-char title; zero existing entries; the 1000th entry |
| Malformed / hostile input | title = `<script>alert(1)</script>` or `'; DROP TABLE` |
| Error path / failure | submit while the backend/DB is unreachable |
| State / sequence | double-click submit; navigate back mid-action; refresh mid-form |
| Authz | act as an unauthorized / logged-out user (if applicable) |

For each, the **pass condition is graceful handling**: a clear error message,
no crash, no uncaught console exception, no corrupt state — NOT necessarily
"the action succeeds." An edge case passes when the app fails *safely*.

### How it runs

`--deep-qa` is the natural extension of `--qa`: same live-browser mechanism,
same context-hygiene contract, just **3 edge-case flows run one at a time**
instead of one happy-path flow.

1. **Gate.** Refuse unless `--qa` has passed for the current feature/sha (a
   `.qa.md` artifact exists). If not: *"Run /renmark:verify --qa first — deep QA
   tests the edges of a flow that's already confirmed to work."* Edge cases on a
   broken happy path are noise.
2. **Reuse the server + browser setup** from `--qa` (boot/health-check if not
   already running; the app is typically still up from the `--qa` run).
3. **Plan phase — risk-rank, then pick 3 (no browser yet).** Before launching
   anything, `--deep-qa` spends a distinct planning pass deciding *what is most
   likely to break*, so the 3 cases are the highest-risk ones — not a generic
   sample of the taxonomy. Inputs to the risk analysis:
   - the feature's behaviors (from the spec / plan goal),
   - the **diff** for this feature (which inputs, branches, and error paths the
     code actually added — read via `git`, bounded, not pasted into chat),
   - open `bugs.md` entries whose files overlap (history of where it broke before),
   - the edge-case categories table above as a checklist of failure *modes*.

   Produce a short ranked list of candidate failure modes ("most likely to
   break" first), each tagged with the category it stresses and *why* it's
   risky (e.g. "title field has no maxlength → 10k-char input likely overflows
   the layout or the DB column"). Take the **top 3** distinct cases. Write the
   full ranked candidate list to the artifact; surface only the chosen 3 + a
   one-line rationale each, and let the user redirect before any browser action:

   > *"Deep QA plan — 3 highest-risk edges for `<feature>`:*
   > *  1. empty title — no client validation seen in diff*
   > *  2. backend-down submit — new fetch has no catch/timeout*
   > *  3. 10k-char title — column + layout untested at size*
   > *Run these one at a time? [y/edit/n]"*
4. **Run them serially** (one at a time — singleton browser), in risk order
   (most-likely-to-break first, so a fail surfaces fast). Each flow is the same
   shape as the `--qa` happy-path flow: navigate → perform the edge action →
   assert graceful handling → screenshot + console/network to disk → emit one
   bounded verdict line. Announce each case as it launches ("running 1/3: empty
   title…") so progress is visible without dumping detail.
5. **Report** 3 verdict lines + evidence pointer; on any fail, log a reproducible
   `bugs.md` entry (same convergence loop as `--qa`).

Bounded output example:

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

### Why serial-in-main, not subagents

At 1 (`--qa`) + 3 (`--deep-qa`) flows that each dump evidence to disk and return
only a verdict line, the main context never holds heavy payloads — so the
subagent fan-out considered earlier buys nothing and adds coordination cost
against a singleton browser. Keep it serial. Only revisit subagent analysis if
a future version needs *many* journeys where even verdict lines + orchestration
overhead pressure the window.

### Out of scope for this version

- A configurable number of edge cases (fixed at 3).
- Auto-generating edge cases beyond the categories above (e.g. fuzzing).
- Edge cases requiring auth setup, if the auth open question (below) lands as a
  v1 limitation.
