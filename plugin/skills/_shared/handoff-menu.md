# Hand-off Menu — Quality-Gate Reference (single source of truth)

**Shared by `/renmark:verify`, `/renmark:verify --qa`, `/renmark:verify --deep-qa`,
and `/renmark:codereview`.** A feature should be testable from every angle, in
any order, before finishing — not pushed down a one-way line. This file is the
one place the menu text lives so the skills can't drift.

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
**not** shown verbatim — the calling skill filters it (rules 1–5) and then
numbers the survivors (rule 6) before rendering.

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

6. **Number the surviving options.** After applying filters 1–5, render the
   options that remain as a numbered list — `1.`, `2.`, `3.`, … in display
   order — keeping the `[x]` bracket code on each line. The number is the
   primary selector; the letter still works. Example after filtering out the
   just-run gate and an all-clean (no Debug) run:

   ```
   1. [qa] QA          — run one happy-path flow live in the browser via /renmark:verify --qa
   2. [c]  Code review — run an adversarial Codex pass over the diff via /renmark:codereview
   3. [f]  Finish      — close the branch (PR or merge) via /renmark:finish
   4. [n]  Nothing     — stop here; work stays committed
   ```

7. **A choice is required to continue.** End on `What's next?` and wait. Never
   auto-proceed, assume a default, or act on an empty answer — every hand-off
   is an explicit decision the user must make. Accept either the number or the
   bracket code; if the answer matches neither, re-show the menu and ask again.

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
> applying the rendering rules (omit the gate just run; show `[dq]` only after
> `--qa` passes; show `[d]` only on failure; number the survivors; require an
> explicit choice).*

Do not paste the menu text into the calling SKILL.md.
