---
artifact_type: spec
schema_version: 1
created_at: 2026-06-26T00:00:00Z
source_sha: e06da63
related_plan: null
generator: brainstorm
stale_after: null
dependency_refs:
  - .renmark/research/2026-06-25-external-skills-study.research.md
  - .renmark/research/2026-06-26-p10-headless-detection.research.md
  - .renmark/plans/2026-06-25-external-skills-p4-p12.program.md
---

# P10 — Formal headless / spawned-session contract

## Context

`renmark` is a Claude Code plugin whose skills are markdown that instruct the
model, backed by a small stdlib-only Python runtime (`renmark/`). Renmark is
**already run inside background jobs** and is increasingly driven by an outer
orchestrator rather than a human at a TTY. Today every pipeline skill ends by
rendering an `AskUserQuestion` next-steps/handoff menu and pauses at the
Pause-Policy gates. In a headless run there is no human to answer that picker —
the run stalls on a dead prompt, or (worse) an outer driver guesses.

P10 (from the external-skills study, source: gstack `$OPENCLAW_SESSION`) adds a
**formal headless-session contract**: detect that renmark is running
non-interactively, suppress `AskUserQuestion`, auto-pick the recommended option
at *safe* gates, **halt at dangerous gates with a human-review record**, and
return a structured machine-readable result plus one classifier-friendly prose
line.

This is largely a **formalization of machinery that already exists**:
`config.py` already persists a P11 toggle (`is_proactive`/`set_proactive`);
`handoff-menu.md:154-169` already says the REQ-12 gates (PRD / destructive /
budget / merge-release) **never** default-forward; the menu picker already lists
"headless / `-p` / piped / CI / no TTY" as an unavailability signal
(`handoff-menu.md:113`). P10 turns these scattered hints into one named,
testable contract.

## Goals

1. A single source of truth for "am I headless?" detection with a deterministic
   precedence order, implemented in `renmark/config.py` (mirrors the P11 pattern).
2. A shared doctrine file `_shared/headless-contract.md` that the **three already
   centralized menu files** honor, so all 28 SKILL.md files inherit the behavior
   without being re-touched (protects the v0.20.0 trigger-only +
   disable-model-invocation frontmatter).
3. Safe gates auto-pick the `(Recommended)` option; dangerous gates halt, write a
   decision artifact, set `human_review_required=true`, and return `needs_input`.
4. A structured JSON return schema + one classifier-friendly prose line, emitted
   in place of the interactive menu when headless.
5. Fail safe: when detection is **uncertain**, dangerous gates are treated as
   headless (halt + emit), never auto-picked.

## Non-goals (feature-scoped)

- Inferring headless from `CLAUDE_JOB_DIR`, `CLAUDECODE`, or any ambient signal
  alone — **explicitly rejected** (this session proves the false positive: a
  background job with a live human answering).
- Rewriting all 28 `SKILL.md` files — behavior is inherited via the shared menu
  files, not duplicated per skill.
- A long-running daemon or programmatic HTTP API. The "return" is the skill's
  final message (JSON block + prose), with durable state in `.renmark/state/`.
- Reverse-engineering Claude Code's private `-p`/subagent internals as a *trusted*
  source — tool-availability is a **fallback adapter**, not the contract's truth.
- P7 (template-generated SKILL.md) and P8 (behavioral skill tests) — separate
  proposals in the same program plan.

## The contract (authoritative — owner-specified 2026-06-26)

### 1. Gate policy

| Gate class | Gates | Headless behavior |
|---|---|---|
| **Safe** | routine next-steps menu, quality-gate menu (smoke/QA/review), scope-contract Q&A, unclear-intent that has a clear recommended default | **Auto-pick** the `(Recommended)` option; continue; record the auto-pick in the JSON return (`decision: auto_picked_recommended`). |
| **Dangerous** | `merge`, `release`, destructive ops, **PRD approval**, **cost/token approval above the configured budget** | **Halt.** Write a decision artifact under `.renmark/decisions/`, set `human_review_required=true` in `lifecycle.json`, return `status: needs_input` (NOT `failed`). |

A dangerous gate that cannot be resolved is **`needs_input`, never `failed`** —
`failed` is reserved for a true blocker (missing input with no safe default,
verifier red with no path forward).

### 2. Detection (layered, deterministic precedence)

```
1. RENMARK_HEADLESS=1   -> headless  (forces on)
2. RENMARK_HEADLESS=0   -> interactive (forces off)   [explicit OFF wins over config]
3. project/session config: .renmark/config.json "headless": true|false
4. tool-availability fallback adapter:
      AskUserQuestion absent from the tool list (confirmed reliable for
      spawned subagents — intentionally absent, Claude Code issue #34592
      closed "not planned") -> headless
5. default -> interactive
```

- **Never** infer headless from `CLAUDE_JOB_DIR` (or `CLAUDECODE`, which Claude
  Code sets in *every* subprocess and is therefore useless as a signal).
- **Uncertainty rule:** if the layers above cannot decide (e.g. config absent and
  tool-availability indeterminate), treat **dangerous gates as headless-safe** —
  halt and emit the decision rather than rendering a picker that may never be
  answered. Safe gates in the uncertain case may still render the interactive
  menu (the human, if present, answers; if absent, the run is already stalled
  only on a safe gate, which is recoverable).

`config.py` owns layers 1–3 and 5 (it can read env + `.renmark/config.json`).
Layer 4 (tool-availability) is **skill-side** — the model observes its own tool
list / a `ToolSearch("select:AskUserQuestion")` probe — because the Python
runtime cannot see the model's available tools. The shared contract file tells
the skill how to combine the Python verdict with the tool-availability adapter.

### 3. Return form

When headless, a skill ends with a fenced JSON block **plus** one
classifier-friendly prose line, instead of an `AskUserQuestion` menu.

Schema:

```json
{
  "status": "success | needs_input | failed",
  "mode": "headless | interactive",
  "gate": "<gate name | null>",
  "decision": "auto_picked_recommended | halted_for_human_review | blocked",
  "human_review_required": true,
  "artifacts": [".renmark/..."],
  "reason": "<only present when status == failed>"
}
```

Success:
```json
{"status":"success","mode":"headless","gate":null,"decision":"auto_picked_recommended","human_review_required":false,"artifacts":[".renmark/plans/example.plan.md"]}
```
`result: planned feature and wrote .renmark/plans/example.plan.md`

Dangerous gate:
```json
{"status":"needs_input","mode":"headless","gate":"merge","decision":"halted_for_human_review","human_review_required":true,"artifacts":[".renmark/decisions/merge-approval.json"]}
```
`needs input: merge approval required; headless mode cannot approve merge/release gates`

Blocker:
```json
{"status":"failed","mode":"headless","gate":null,"decision":"blocked","human_review_required":false,"artifacts":[],"reason":"missing PRD path and no safe default could be inferred"}
```
`failed: missing PRD path and no safe default could be inferred`

**Prose-line vocabulary:** the prose line uses this repo's existing background-job
classifier words — `result:` / `needs input:` / `failed:` — so the job-list state
extractor catches the outcome. (JSON `status` keeps the snake_case enum
`success|needs_input|failed`; the prose `needs input:` carries a space to match
the classifier. This is the one reconciliation between the owner's JSON example
and the repo's existing classifier convention — flagged here for plan/review.)

## Architecture

```
renmark/config.py
  is_headless(repo) -> bool            # layers 1-3,5 (env + .renmark/config.json)
  set_headless(repo, value) -> None    # persist .renmark/config.json "headless"
  headless_source(repo) -> str         # "env" | "config" | "default" (for the note)
        (mirrors is_proactive/set_proactive exactly: stdlib json, never raises,
         read-modify-write; RENMARK_HEADLESS=0 forces False even if config True)

plugin/skills/_shared/headless-contract.md   # NEW doctrine, single source of truth
  - detection precedence (incl. layer-4 tool-availability adapter + uncertainty rule)
  - safe vs dangerous gate table (gates enumerated)
  - JSON return schema + 3 worked examples + prose-line vocabulary
  - the decision-artifact format (.renmark/decisions/<gate>-approval.json)

plugin/skills/_shared/handoff-menu.md         # honor contract: if headless,
  next-steps.md                                #   don't render AskUserQuestion;
  scope-contract.md                            #   auto-pick recommended (safe) /
                                               #   halt+emit (dangerous)

renmark/lifecycle.py
  - on dangerous-gate halt: set human_review_required=true (existing gate fields)
  - skill_preamble(): surface one-line "headless mode active (source: env|config)"
    note when is_headless() is true

.renmark/decisions/<gate>-approval.json        # NEW decision-artifact home
  (gitignore policy: committed? -> decisions are durable human-gate records;
   default committed unless plan says otherwise)
```

## Data flow

1. Skill starts → `skill_preamble` calls `config.is_headless(repo)`; if true,
   surfaces the one-line headless note and sets the skill into headless mode.
2. Skill reaches a gate. It classifies the gate (safe vs dangerous) per the
   shared table.
3. **Safe** → instead of `AskUserQuestion`, the skill picks the `(Recommended)`
   option (the same one `next_steps()` already computes), continues, and records
   `decision: auto_picked_recommended` for the final JSON.
4. **Dangerous** → write `.renmark/decisions/<gate>-approval.json`, call
   `lifecycle.write_lifecycle(..., human_review_required=True, human_review_for=<gate>)`,
   stop, emit `status: needs_input` JSON + `needs input:` prose line.
5. On normal completion → emit `status: success` JSON + `result:` prose line.
6. On blocker → emit `status: failed` JSON + `failed:` prose line with `reason`.
7. `/renmark:approve` remains the sole surface that clears `human_review_required`
   and lets a later (interactive or explicitly-authorized) run proceed past the
   dangerous gate.

## Error handling / edge cases

- **Detection uncertain** → dangerous gates halt + emit (fail safe); never
  auto-approve a merge/release because we weren't sure.
- **RENMARK_HEADLESS=0 in a real subagent** (where AskUserQuestion is absent):
  explicit OFF wins, but if the skill then *tries* to render a picker it can't,
  it must degrade to the prose+JSON return rather than stalling — `=0` suppresses
  auto-pick, it does not conjure a missing tool. (Documented caveat in the
  contract file.)
- **Interactive mode** → entire contract is inert; skills render menus exactly as
  today. No behavior change for the human-at-TTY path.
- **renmark-execute subprocesses** always carry `CLAUDECODE=1`; this is *not* a
  headless signal and must be ignored by detection.

## Success criteria

1. `config.is_headless` / `set_headless` / `headless_source` exist, are
   stdlib-only, never raise, and honor precedence: `RENMARK_HEADLESS=1` → True,
   `=0` → False (overriding config), config flag otherwise, default False.
2. Unit tests pin both env directions, the config flag, and the `=0`-overrides-
   config case (mirrors the existing fable/env precedence tests).
3. `_shared/headless-contract.md` exists and is referenced by `handoff-menu.md`,
   `next-steps.md`, and `scope-contract.md`.
4. A dangerous-gate halt writes `.renmark/decisions/<gate>-approval.json`, sets
   `human_review_required=true` in `lifecycle.json`, and the skill returns
   `needs_input` (verified via a scripted headless run of `finish` at the merge
   gate).
5. A safe gate in headless mode auto-picks the recommended option and returns
   `success` without rendering `AskUserQuestion`.
6. No regression to the v0.20.0 trigger-only / disable-model-invocation SKILL.md
   frontmatter (no SKILL.md description bloat from this change).
7. `pytest -q`, `ruff check`, `mypy .` all green.

## Prior art & references

- External-skills study: `.renmark/research/2026-06-25-external-skills-study.research.md`
  (P10 entry, lines 121-125) — source: gstack `$OPENCLAW_SESSION`.
- Headless-detection research: `.renmark/research/2026-06-26-p10-headless-detection.research.md`
  — `CLAUDECODE=1` set in all subprocesses (useless as signal); AskUserQuestion
  intentionally absent in subagents (reliable fallback); no documented `-p` env
  var (explicit flag required for `-p` main-session).
- Internal reuse (extend, don't rebuild): `renmark/config.py` P11 toggle pattern;
  `handoff-menu.md:113,154-169` (headless hint + REQ-12 never-default-forward);
  `lifecycle.py` human-review gate fields; `/renmark:approve` as the clear surface.
- Program plan: `.renmark/plans/2026-06-25-external-skills-p4-p12.program.md`.
