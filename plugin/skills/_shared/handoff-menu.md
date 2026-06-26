# Hand-off Menu — Quality-Gate Reference (single source of truth)

**Shared by `/renmark:verify`, `/renmark:verify --qa`, `/renmark:verify --deep-qa`,
and `/renmark:codereview`.** A feature should be testable from every angle, in
any order, before finishing — not pushed down a one-way line. This file is the
one place the menu text lives so the skills can't drift.

---

## Pause Policy — the only reasons to stop and ask

renmark runs its pipelines automatically. Inside a pipeline it does **not** ask
after every step — it continues on its own and stops for the user at exactly
these seven gates. Nothing else is a reason to halt a running pipeline:

1. **Unclear product intent** — the goal is ambiguous and a wrong guess is expensive.
2. **PRD approval** — creating or changing `PRD.md` (the human owns the product source of truth).
3. **Scope change** — the work drifts past what was agreed / what the PRD covers.
4. **Risky or destructive action** — anything that can lose work or is hard to undo.
5. **Cost / token approval** — a dispatch gate where token spend begins (show the cost preview).
6. **Unresolved blocker** — a verifier fails, a root cause is unconfirmed, or a dependency is missing.
7. **Merge / release approval** — landing to `main`, tagging, or publishing (REQ-12).

Anything not on this list — branch naming, which model ran, intermediate stage
transitions, routine progress — is handled silently: report it in a one-line
status (see `CLAUDE.md` § `response-style-rule`) and keep going.

**How a pause resolves** follows the default-forward classification in rule 8
below: reversible hand-offs may default-forward to the `(Recommended)` option
after one restatement; **dispatch gates** (#5) default-forward only with a
validated plan AND a shown cost preview; **REQ-12 gates** (#2 PRD writes, #4
destructive ops, #5 budget escalation, #7 merge/release) **never default —
silence is a no**, and `/renmark:approve` is the only grant surface.

### Headless mode

When renmark runs non-interactively (spawned subagent, `-p`/piped/CI, no TTY) the
`AskUserQuestion` picker has no one to answer it. The headless behavior lives in
one place so the skills can't drift:

> *If headless (per `${CLAUDE_PLUGIN_ROOT}/skills/_shared/headless-contract.md`
> detection), do not render `AskUserQuestion`: auto-pick the `(Recommended)`
> option at safe gates and continue; at dangerous gates halt, write
> `.renmark/decisions/<gate>-approval.json`, set `human_review_required=true`, and
> return the `needs_input` JSON + `needs input:` prose line.*

A **dangerous gate** is exactly a REQ-12 gate — merge/release (#7), destructive
ops (#4), PRD approval (#2), cost/budget escalation (#5). This does **not** relax
the never-default-forward rule above: REQ-12 gates still never auto-proceed, and
auto-picking the `(Recommended)` option applies only to the safe reversible gates.
Headless halt + decision artifact is the machine-readable form of "silence is a
no"; `/renmark:approve` remains the only grant surface.

---

## The three quality gates

| Gate            | What it checks                                  | Command                         |
|-----------------|-------------------------------------------------|---------------------------------|
| **Smoke**       | happy path responds (shell, terminal)           | `/renmark:verify`               |
| **QA**          | feature works live in a browser (rendered E2E)  | `/renmark:verify --qa`          |
| **Deep QA**     | 3 highest-risk edge cases handled gracefully    | `/renmark:verify --deep-qa`     |
| **Code review** | the code itself is sound (adversarial, static)  | `/renmark:codereview`           |

Plus the terminal actions `Finish`, `Debug`, and `Nothing`.

---

## Canonical menu text

This is the master list of every gate, keyed by its `[x]` bracket code. It is
**not** shown verbatim — the calling skill filters it (rules 1–5), then presents
the survivors as an interactive `AskUserQuestion` choice when available (rule 6),
falling back to a printed numbered list (rule 7).

```
[s]  Smoke test  — re-run the goal-backward shell smoke via /renmark:verify
[qa] QA          — run one happy-path flow live in the browser via /renmark:verify --qa
[dq] Deep QA     — run 3 edge-case flows live in the browser via /renmark:verify --deep-qa  (only after QA passes)
[c]  Code review — run an adversarial Codex pass over the diff via /renmark:codereview
[f]  Finish      — close the branch (PR or merge) via /renmark:finish
[d]  Debug       — investigate a failure via /renmark:debug
[n]  Nothing     — stop here; work stays committed
```

---

## Rendering rules

Each calling skill applies these filters before showing the menu — every gate
should be reachable from every other gate, but the menu must stay short and
contextual:

1. **Omit the gate that was just run.** Don't offer "Smoke" right after smoke,
   "QA" right after `--qa`, "Code review" right after codereview. List the
   other two so re-testing a different way is one keystroke.

2. **`[dq] Deep QA` shows ONLY when a `.qa.md` artifact exists for the current
   sha.** Edge cases are pointless on a happy path that hasn't been confirmed
   to work — gating Deep QA behind a passing QA enforces that order. Detect
   via `summary.read_metadata` over `.renmark/reviews/*.qa.md` filtered by
   `source_sha == git_head_sha(repo)` and `completion_state == "complete"`.

3. **`[d] Debug` shows whenever the just-run gate found a failure.** On an
   all-clean run, omit it (the user shouldn't be prompted to debug nothing).

4. **`[f] Finish` is always offered** on a passing gate (the work is shippable
   from any green light); omit on a failing gate (debug first).

5. **`[n] Nothing` is always offered** — the user can stop at any gate. Work
   stays committed; the artifact stays on disk.

6. **Present the survivors as an interactive choice (PRIMARY path).** After
   applying filters 1–5, render the menu by **calling the `AskUserQuestion`
   tool** — an arrow-key-selectable picker — not by printing markdown. This is
   the default behavior; the printed list (rule 7) is only a fallback.
   - One question. The `question` field holds ONLY the prompt (`What's next?`)
     — a short interrogative sentence. `multiSelect: false`.
   - **Every option MUST be a real entry in the `options` array — never list the
     choices inside the `question` text.** Each surviving option is its own
     `options[]` entry: `label` = the action name with its code (e.g.
     `Code review [c]`), `description` = the one-line gloss from the canonical
     list. A call whose `question` embeds the option list (and whose `options`
     array is empty/degenerate) renders as a header with no selectable choices —
     that is the failure this rule forbids. If you cannot populate a real
     `options` array (≥2 entries), do NOT call the tool — print the rule 7
     fallback instead.
   - `AskUserQuestion` is blocking and offers no default — that is what enforces
     rule 8 (no auto-proceed).
   - **Fall back to rule 7 the moment the picker does not present visible,
     selectable choices — for ANY reason.** Concretely, immediately print the
     numbered list (rule 7) if the call: is unavailable (subagents, headless /
     `-p` / piped / CI, no TTY); errors or throws; is declined / rejected /
     interrupted by the user; returns no selection or no valid option; or would
     render only the question header with no visible options. Never block on,
     retry indefinitely, or wait after a picker that showed nothing. **A
     declined or empty picker is a signal to print the fallback, not to stop.**
   - **4-option cap.** `AskUserQuestion` allows **at most 4 options** per
     question. If **≤4 options survive, every one is a selectable choice.** If
     **>4 survive, surface the 4 highest-priority as choices AND also print the
     full numbered fallback list (rule 7)** beneath, so the overflow options stay
     reachable by typing their number or bracket code (free-text is always
     accepted). Priority for which 4 to surface (highest first): failure actions
     (`[d]`, or `[fix]` on critical findings) → `[c]` → `[qa]` → `[f]` → `[dq]`
     → `[o]` → `[s]`, and ALWAYS keep `[n] Nothing` as one of the four so "stop"
     is one selection away.
   - On return, dispatch by the chosen option (map the selected label back to its
     `[x]` action); a free-text reply is matched to a number or bracket code.
     **A free-text reply that maps to NO option — a clarifying question, a
     follow-up, a request for more detail — is NOT a selection: answer it, then
     **re-render this picker in the same turn** (rule 9 continuation clause). The
     hand-off stays open until an actual action is chosen — never reply to a
     non-selection with a prose / inline list of the options.**

7. **Fallback — printed numbered list.** Used when `AskUserQuestion` is
   unavailable/non-interactive or errors, AND printed as the reference list
   beneath an overflow (>4) picker. Render the survivors as a numbered markdown
   list — `1.`, `2.`, `3.`, … in priority order — keeping the `[x]` bracket code
   on each line, and accept either the number or the bracket code:

   ```
   1. [qa] QA          — run one happy-path flow live in the browser via /renmark:verify --qa
   2. [c]  Code review — run an adversarial Codex pass over the diff via /renmark:codereview
   3. [f]  Finish      — close the branch (PR or merge) via /renmark:finish
   4. [n]  Nothing     — stop here; work stays committed
   ```

   Prefer the interactive picker (rule 6) whenever `AskUserQuestion` is available
   — this printed list is the fallback, not the primary presentation.

8. **A choice is required — with a bounded default-forward (owner rule,
   2026-06-11).** End on the question and wait for a selection — but renmark
   favors pipeline momentum over gate ceremony, so silence is handled by
   decision class:
   - **Reversible hand-offs** (quality-gate menus, what's-next pickers, resume
     hints): if the picker is declined/aborted **without an alternative
     instruction** (accidental declines happen — e.g. exiting dictation mode),
     or the text fallback sits unanswered, restate the question once; if still
     unanswered, **proceed with the option labeled `(Recommended)`**, stating
     plainly: *"no answer — proceeding with <option> (default-forward rule)."*
     A decline that comes WITH instructions is an answer — follow the
     instructions instead.
   - **Dispatch gates** (token spend begins): default-forward is allowed ONLY
     when the plan is validated AND the cost preview was displayed in the same
     hand-off; otherwise keep waiting.
   - **REQ-12 gates NEVER default:** merge, release, `PRD.md` writes, budget
     escalation, and branch-destructive operations always require an explicit
     yes — silence is a no. (`/renmark:approve` remains the only grant surface.)

   > **Note on `[o]` and `[fix]` codes:** `[o] Open` (open the review file) and
   > `[fix] Fix` (kick off a plan from the findings) are codereview-lite-lane
   > extension codes defined in `codereview/SKILL.md`. They are NOT in the
   > canonical master list above — they appear only in the combined menu that
   > codereview builds for its own hand-off. Priority for the 4-option cap
   > (above) already accounts for them when they are present.

9. **Hard guarantee — visible choices XOR printed fallback, never neither.**
   Every hand-off MUST end in one of exactly two visible states: (a) an
   `AskUserQuestion` picker showing the selectable choices, OR (b) the printed
   numbered list (rule 7). It must **never** end on the bare question
   (`What's next?`) with no visible options. If the picker did not render visible
   choices — declined, errored, header-only, or no valid selection — print the
   numbered list in the **same turn** before yielding. When in doubt, print the
   fallback: a redundant numbered list is harmless; a choiceless prompt is a bug.

   **Continuation clause (owner rule, 2026-06-14) — the guarantee applies to
   EVERY turn the hand-off is open, not just the first.** A hand-off is not
   "done" when `AskUserQuestion` returns — it is done only when the user *selects
   an action* (or a rule-8 default-forward / REQ-12 resolution fires). When the
   user instead replies with a clarifying question, a follow-up, or any free text
   that maps to no surviving option, the hand-off is **still open**: answer them,
   then in the **same turn re-render the picker** (rule 6) — or the printed
   fallback (rule 7) if the picker is unavailable. **Never let a continuation turn
   end in prose options or an inline list** — a `1. … 2. …` written in the reply
   body is NOT a rule-7 fallback and does not satisfy this guarantee. Re-render
   the real picker on every open turn until an action is chosen.

---

## Why a shared file

Earlier drafts had each skill restate the menu in its own SKILL.md. The text
drifted within two releases (different verbs, different bracket letters, one
skill forgot to list Debug). Centralizing here means:

- One edit point. Add a future gate (e.g. perf, security) and every skill picks
  it up next run.
- Linter-friendly. `plugin/skills/_shared/` is skipped by `renmark.lint` (it's
  a reference dir, not a skill), so this file never trips the "missing command
  pair" check.
- Symmetric with `_shared/scope-contract.md` — same pattern, same precedent.

When citing this menu in a SKILL.md, write:

> *Render the hand-off menu from `${CLAUDE_PLUGIN_ROOT}/skills/_shared/handoff-menu.md`,
> applying the rendering rules: filter (omit the gate just run; `[dq]` only after
> `--qa` passes; `[d]` only on failure), then present the survivors as an
> interactive `AskUserQuestion` choice when available — printed numbered list only
> as fallback (or beneath a >4-option picker) — and require an explicit choice.*

Do not paste the menu text into the calling SKILL.md.
