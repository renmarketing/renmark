---
name: approve
description: "Use to clear a pending human-approval gate — typed as /renmark:approve or \"approve the release\", \"what's pending approval\", \"approve this\"."
disable-model-invocation: false
---

# approve

## Overview

`/renmark:approve` is the **human-approval surface** (G7 / principle #7: AI may
generate code; the human owns merges and releases). It is the **only** sanctioned
way to flip `human_review_completed` to `true` in `.renmark/state/lifecycle.json`.
Skills that perform a destructive or irreversible step — release, restore, merge,
a security override, a PRD scope change — set `human_review_required` and stop;
they re-enter only after this skill records the human's explicit decision.

Cost: **near-zero LLM** — one file read, the human's yes/no, one file write. No
judgment, no analysis. The human decides; this skill records.

## When to Use

- A previous skill set an approval gate and told you the next step is
  `/renmark:approve` (e.g. resume surfaced "⚠ Approval pending: …").
- You want to check whether anything is awaiting your approval.

**Do NOT use:**
- To make a workflow decision — approve only records a yes/no the human already
  made.
- To advance a lifecycle stage — approve never changes `stage`; it only flips the
  approval bit.

## Steps

### 0. Context check

Call `lifecycle.skill_preamble(repo, 'approve')`. Approve is a `meta` domain skill.
If it returns a non-None hint, surface it as a one-line note.

### 1. Read the gate

```bash
python3 -c "
from pathlib import Path
from renmark import lifecycle
state = lifecycle.read_lifecycle(Path('.'))
if state is None:
    print('NO-GATE: no lifecycle in this project.')
elif not state.human_review_required:
    print('NO-GATE: no approval pending.')
elif state.human_review_completed:
    print(f'ALREADY-APPROVED: gate for {state.human_review_for!r} was already cleared.')
else:
    print(f'PENDING: {state.human_review_for}')
"
```

- `NO-GATE` / `ALREADY-APPROVED` → print the line, skip to **Step 4** (hand-off).
  There is nothing to approve.
- `PENDING: <what>` → continue to Step 2.

### 2. Confirm with the human

Display `human_review_for` verbatim (what is being approved). Ask for an
**explicit** decision via `renmark.interaction.build_selector` (two options:
`Reject (Recommended)` first, then `Approve`). A recommendation is not approval;
only the user's explicit `Approve` selection grants the gate.
Never assume a default — this is the one gate the human must own. If
`$ARGUMENTS` already carries `approve` or `reject`, treat that as the answer but
still echo what is being approved before acting.

### 3. Record the decision

- **Approve** → flip the bit, but **never clear the gate itself**:

  ```bash
  python3 -c "
  from pathlib import Path
  from renmark import lifecycle
  lifecycle.write_lifecycle(Path('.'), human_review_completed=True)
  print('APPROVED: human_review_completed=True recorded.')
  "
  ```

  Leave `human_review_required` / `human_review_for` untouched. The **consuming**
  skill clears the gate after it acts on the approval (`prd` self-clears its own
  gate; `backlog` / `finish` check `human_review_completed == True` then proceed).
  Approve's job is to record consent, not to consume it.

- **Reject** → leave lifecycle state **untouched** (write nothing). Recommend the
  consuming skill so the human can revise rather than approve.

### 3.5 Surface any loop awaiting approval

A bounded `/renmark:loop` run that hit a REQ-12 gate persists
`status: awaiting-approval` in `.renmark/loops/<id>/loop.json`. If one exists,
surface the resume hint so the loop is re-enterable after this approval. Pure
file IO, zero LLM:

```bash
python3 -c "
from pathlib import Path
from renmark.loop import read_loop, LOOPS_SUBDIR
from renmark.state import RENMARK_DIR_NAME
root = Path('.') / RENMARK_DIR_NAME / LOOPS_SUBDIR
for d in (sorted(root.glob('loop-*')) if root.is_dir() else []):
    st = read_loop('.', d.name)
    if st is not None and st.status == 'awaiting-approval':
        print(f'⟳  Loop awaiting approval: {d.name} — resume with /renmark:loop --resume {d.name}')
"
```

### 4. Hand off

approve is an **aux / terminal skill** (class 3 in
`${CLAUDE_PLUGIN_ROOT}/skills/.shared/next-steps.md`). It records a decision and
returns the human to the in-flight feature.

> *End by calling `renmark.lifecycle.next_steps(repo, "approve")` and render per
> `${CLAUDE_PLUGIN_ROOT}/skills/.shared/next-steps.md` (class 3 — resume-pipeline
> + 1–2 local actions). The in-flight feature's next command is `(Recommended)`;
> add the skill's local follow-ups. Render via `AskUserQuestion`
> (`${CLAUDE_PLUGIN_ROOT}/skills/.shared/handoff-menu.md` rules 6–9); require an
> explicit choice.*

After an **approve**, the recommended local follow-up is the consuming skill
(the one that set the gate — `human_review_for` names it), so the human resumes
exactly where the gate paused. After a **reject**, recommend that same skill so
the human can revise. Do not paste the rendering rules or the gate menu — cite
the files.

## Governance compliance

- **G7 (human approval gate)** — approve is THE surface that records human
  consent. It flips `human_review_completed` only on explicit confirmation and
  never auto-proceeds (Step 2 requires a selection).
- **G2 / G12 (canonical state outside the conversation)** — the decision is
  persisted via `write_lifecycle` to `lifecycle.json`, not held in chat. A
  `/clear` after approval is recoverable: the bit is on disk.
- **G3 (bounded output)** — each step prints ≤5 lines; no artifact body is read.
- approve dispatches nothing and emits no artifact, so G6/G9/G11 are N/A.

See `CLAUDE.md` governance rules for definitions.
