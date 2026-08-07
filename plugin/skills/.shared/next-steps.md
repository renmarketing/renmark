# Next-Step Contract — Hand-off Reference (single source of truth)

**Referenced by every `/renmark:*` skill.** This is the one place the
"what should the user do next?" rule lives, so no skill drifts and no renmark
interaction ever dead-ends. Like `_shared/handoff-menu.md` (quality gates) and
`_shared/scope-contract.md` (discovery), this is a **reference file** skills
cite — never paste.

The umbrella rule: **every skill MUST end by recommending a state-derived next
step.** No silent stop, no "you might want to…", no terminal cliff. The
recommendation is either rendered as an explicit, selectable choice, or — per
the auto-proceed rule below — announced in one line and acted on directly.
Either way the user is never left to guess what happens next or which
command to type.

---

## State source — durable, never conversational

The next step is derived from **persisted state, never conversation memory**:

- `.renmark/state/lifecycle.json` — WORKFLOW state (feature, stage, artifacts,
  approval gates). Survives `/clear`. This is the primary driver.
- `.renmark/state/pipeline.json` — RUNTIME state (wave indices, retries). Used
  to tell "mid-orchestrate" from "orchestrate complete."

Because the source is on disk, the recommendation is identical whether the skill
runs fresh, after `/clear`, or in a resumed cold-start session. **Never infer the
next step from "what we just discussed."** If you find yourself reconstructing
state from the transcript, read `lifecycle.json` instead.

---

## The state helper

Skills do not hand-roll stage routing. They call:

```python
renmark.lifecycle.next_steps(repo, skill)
```

`next_steps` returns the structured next-step set for the calling `skill`,
computed from `lifecycle.json` + `pipeline.json` via the existing machinery
(`next_recommended()` → `_resolve_next()` over `NEXT_BY_STAGE`, guarded by
`IMPLEMENTED_SKILLS` so a vibe coder is never sent to an unbuilt skill). The
helper resolves the skill's class (below) and returns the primary recommendation
plus any local/aux actions to surface.

**Render the returned set** by reusing `_shared/handoff-menu.md` **rendering
rules 6–9 verbatim, BY REFERENCE** — do not restate them here:

- **Rule 6** — present survivors through the active host selector (PRIMARY),
  real `options[]` entries, host option cap.
- **Rule 7** — printed numbered fallback when the picker is unavailable/declined.
- **Rule 8** — a choice is always required; never auto-proceed.
- **Rule 9** — visible choices XOR printed fallback, never a bare question; its
  continuation clause re-renders the picker on every open turn (a clarifying
  reply is answered, then the picker is shown again — never prose options).

The primary (state-derived) recommendation is always the top-priority option and
labelled `(Recommended)`.

---

## Auto-proceed vs. explicit choice (interactive sessions)

Rendering the picker (rules 6–9) is the default, but not unconditional. Skip
it — and proceed straight into the recommended next step in the same turn —
when **both** hold:

1. **No Pause-Policy condition fired this run**: unclear intent, a scope/
   direction change, a destructive/irreversible action, a merge/release/
   publish/install action, a missing-information block, or an explicit
   human-review gate. Every skill already tracks when one of these is live
   (that's what its own gate logic exists for) — this reuses that existing
   signal (`requires_decision`); it does not add a new one.
2. **The recommended next command is not itself a dangerous gate** (merge,
   release, publish, install) — those always halt per the dangerous-gate
   rule regardless of `requires_decision`.

When both hold, do not render `AskUserQuestion`. Print one line naming what
happened and what's next (e.g. *"Fixed — resuming `/renmark:plan`."* or
*"Spec approved — moving to `/renmark:plan`."*), then — for **class 1
(pipeline) skills only** — proceed directly into that next command in the
same turn. This is what lets a plain-English ask ("let's add X", "let's
rethink Y") run end-to-end without the user typing any `/renmark:*` command:
brainstorm → PRD → plan → orchestrate → verify → finish auto-chain, stopping
only when `requires_decision` goes true at some stage, the next step is a
dangerous gate, or there is no next step (pipeline complete). Class 2/3
skills auto-proceed the same way but don't chain further themselves — they
hand off to whichever pipeline skill is next.

When either condition fails, render the full picker exactly as before — this
section only narrows *when* the picker fires; it does not change how it
renders or weaken any Pause-Policy gate.

---

## Three skill classes

Each renmark skill belongs to exactly one class. The class decides what
`next_steps` surfaces and which citation block the SKILL.md pastes.

### 1. Pipeline skills — Tier-0 stage routing

`start`, `brainstorm`, `plan`, `check-plan`, `orchestrate`, `finish`,
`feature`, `prd`, `blueprint`, `loop`.

These advance the lifecycle. Their next step is the deterministic stage
transition from `next_recommended()` (which reads `lifecycle.json` and applies
`NEXT_BY_STAGE`). Per the auto-proceed rule above, when `requires_decision` is
false this is not just a picker with the command pre-selected — the skill
chains directly into it. The picker (recommended option + 1–2 sibling steps +
`Nothing`) only renders when `requires_decision` is true.

### 2. Quality gates — defer to the gate sub-menu

`verify` (incl. `--qa` / `--deep-qa`) and `codereview`.

These do not own their hand-off text — they **defer to
`_shared/handoff-menu.md`'s gate sub-menu** (Smoke / QA / Deep QA / Code review
/ Finish / Debug / Nothing, with its own filter rules 1–5). A gate skill MAY
cite EITHER this contract OR `handoff-menu.md` directly; both resolve to the same
rendered menu. Do not duplicate the gate menu text here — it lives in
`handoff-menu.md`.

`verify` belongs to class 2 only — it is NOT a pipeline skill.

### 3. Aux / terminal skills — resume-pipeline + local actions

`debug`, `doctor`, `hygiene`, `roadmap`, `init`, `setup`, `help`, `resume`,
`backlog`, `usage`, `analytics`, `approve`, `audit`, `inventory`.

Unlisted skills default to class 3 (aux) via `lifecycle.skill_class`.

These sit off the main line. Their recommended next step is **resume-pipeline**:
the in-flight feature's `next_recommended()` (from `lifecycle.json`), so the user
is returned to the pipeline rather than stranded. Alongside it, offer **1–2
domain-appropriate local actions** — e.g. `doctor` → re-run `--fix`; `roadmap` →
open the top-ranked item; `setup`/`init` → `/renmark:start`; `debug` → re-run the
failing verifier. If no feature is in flight, the resume option becomes
`/renmark:start`.

---

## Tiered cost gating for gap discovery

Skills that look for *missing* work (`roadmap`, `finish`, `init`) escalate cost
deliberately. Never jump to an expensive tier silently.

- **T0 — deterministic next (free, always).** The stage-derived
  `next_recommended()`. Always computed; costs nothing; the floor every skill
  returns.
- **T1 — local LLM gap analysis (default).** Compare `PRD.md` against
  `CHANGELOG.md` + `.renmark/memory/features.md` to surface drift / unbuilt
  promises. Local reasoning only — no network.
- **T2 — live web research (OPT-IN, default OFF).** Web search for
  prior-art / competitive gaps. Runs **only** on explicit user opt-in, **or** when
  T1 raises its unknown-domain flag. Never the default; never silent.

`next_steps` returns T0 unconditionally; callers request T1/T2 explicitly.

---

## When citing this contract in a SKILL.md, write:

**Pipeline skill** (class 1):

> *End by calling `renmark.lifecycle.next_steps(repo, "<skill>")`. If
> `requires_decision` is false, announce the recommendation in one line and
> chain directly into it — do not render a picker. Otherwise present via
> `AskUserQuestion` (handoff-menu.md rules 6–9), state-derived next command as
> `(Recommended)`, explicit choice required. See
> `${CLAUDE_PLUGIN_ROOT}/skills/.shared/next-steps.md` (class 1 — Tier-0 stage
> routing + auto-proceed rule).*

**Quality gate** (class 2):

> *End by rendering the gate hand-off menu from
> `${CLAUDE_PLUGIN_ROOT}/skills/.shared/handoff-menu.md` (the next-step contract's
> class 2 defers to it). Filter (rules 1–5). If `requires_decision` is false,
> announce the recommendation in one line and hand off directly; otherwise
> present via `AskUserQuestion` (rules 6–9), explicit choice required.*

**Aux / terminal skill** (class 3):

> *End by calling `renmark.lifecycle.next_steps(repo, "<skill>")`. If
> `requires_decision` is false, announce the resume-pipeline recommendation in
> one line and hand off directly (no local-action picker); otherwise render
> per `${CLAUDE_PLUGIN_ROOT}/skills/.shared/next-steps.md` (class 3 —
> resume-pipeline + 1–2 local actions) via `AskUserQuestion` (handoff-menu.md
> rules 6–9), explicit choice required.*

Do not paste the rendering rules or the gate menu into the calling SKILL.md —
cite the file.

---

## Headless mode

When the run is headless (per `skills/.shared/headless-contract.md` in the active plugin root
detection), the state-derived next-step set computed above is **not** presented
via a host selector. Instead the `(Recommended)` next command — always a safe,
state-derived route — is auto-selected and the skill emits the contract's
JSON + prose return rather than rendering rules 6–9. The one exception: if the
recommended next step is itself a **dangerous** action (e.g. a `merge` / `release`
gate), it is not auto-run — it defers to the dangerous-gate halt rule
(write `.renmark/decisions/<gate>-approval.json`, set `human_review_required=true`,
return `needs_input`). This contract's class-1/2/3 routing is unchanged; headless
only swaps how the resolved recommendation is surfaced.

---

## Why a shared file

One edit point: change the next-step policy here and every skill picks it up next
run, instead of restating it in 20+ SKILL.md files that drift within a release
(the same failure that motivated `handoff-menu.md`). `plugin/skills/.shared/` is
skipped by `renmark.lint` (it's a reference dir, not a skill), so this file never
trips the "missing command pair" check. Symmetric with
`_shared/handoff-menu.md` and `_shared/scope-contract.md` — same pattern, same
precedent.
