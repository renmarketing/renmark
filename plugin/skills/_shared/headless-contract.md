# Headless / Spawned-Session Contract (single source of truth)

**Honored by `/renmark:*` skills via the three centralized menu files —
`_shared/handoff-menu.md`, `_shared/next-steps.md`, `_shared/scope-contract.md`.**
When renmark runs **non-interactively** (a spawned subagent, `-p`/piped/CI, no
human at a TTY), there is no one to answer an `AskUserQuestion` picker. This file
is the one place the headless behavior lives so the skills can't drift: detect
headless, suppress the picker, **auto-pick the recommended option at safe gates**,
**halt at dangerous gates with a human-review record**, and return a structured
machine-readable result plus one classifier-friendly prose line.

Interactive mode is unchanged — when a human is present, the entire contract is
inert and skills render menus exactly as today (see `handoff-menu.md`).

---

## 1. Detection precedence (layered, deterministic)

Resolve in this order; the **first** layer that decides wins:

```
1. RENMARK_HEADLESS=1   -> headless     (forces ON)
2. RENMARK_HEADLESS=0   -> interactive  (forces OFF — explicit OFF wins over config)
3. .renmark/config.json "headless": true|false   -> per-project / per-session config
4. tool-availability fallback adapter:
      AskUserQuestion absent from the tool list -> headless
5. default -> interactive
```

- **Python `config.is_headless(repo)` owns layers 1–3 and 5** — it reads the
  `RENMARK_HEADLESS` env var and `.renmark/config.json`, never raises, and honors
  the precedence above (`=1` → True, `=0` → False even if config says True, config
  flag otherwise, else False). It mirrors the P11 `is_proactive`/`set_proactive`
  pattern exactly (stdlib `json`, read-modify-write).
- **Layer 4 (tool-availability) is skill-side** — the Python runtime cannot see
  the model's tool list, so the *skill* observes its own available tools (or runs
  a `ToolSearch("select:AskUserQuestion")` probe). `AskUserQuestion` is
  intentionally **absent from spawned subagents** and this is a reliable headless
  signal (Claude Code issue #34592, closed "not planned"). The skill combines the
  Python verdict (layers 1–3,5) with this layer-4 adapter to reach the final mode.
- **NEVER infer headless from `CLAUDE_JOB_DIR` or `CLAUDECODE`.** Claude Code sets
  `CLAUDECODE=1` in *every* subprocess (including `renmark-execute` with a live
  human answering), so it is useless as a signal. A background job is not the same
  as a headless session.

**Uncertainty rule (fail safe):** if the layers above cannot decide (config
absent and tool-availability indeterminate), treat **DANGEROUS gates as
headless** — halt and emit the decision artifact rather than rendering a picker
that may never be answered. Never auto-approve a merge/release because detection
was unsure. Safe gates in the uncertain case may still render the interactive
menu (if a human is present they answer; if absent, the run is only stalled on a
recoverable safe gate).

> **`=0` caveat:** `RENMARK_HEADLESS=0` suppresses auto-pick; it does **not**
> conjure a missing tool. If a forced-interactive run is actually in a subagent
> where `AskUserQuestion` is absent, the skill must degrade to the prose+JSON
> return rather than stalling on a picker it cannot render.

---

## 2. Safe vs dangerous gates

| Gate class | Gates | Headless behavior |
|---|---|---|
| **Safe** | routine next-steps menu · quality-gate menu (smoke / QA / review) · scope-contract Q&A · unclear-intent **that has a clear recommended default** | **Auto-pick** the `(Recommended)` option (the same one `next_steps()` computes); continue; record `decision: auto_picked_recommended` in the JSON return. |
| **Dangerous** | `merge` · `release` · destructive ops · **PRD approval** · **cost/token approval above the configured budget** | **Halt.** Write a decision artifact under `.renmark/decisions/`, set `human_review_required=true` in `lifecycle.json`, return `status: needs_input`. **Never `failed`.** |

**`needs_input` ≠ `failed`.** A dangerous gate that cannot be resolved headless is
`needs_input` — the run is healthy, it just awaits a human grant. `failed` is
reserved for a **true blocker**: a missing input with no safe default, or a
verifier red with no path forward. Returning `failed` for a merge gate is a bug.

---

## 3. Return schema + prose line

When headless, a skill ends with a fenced JSON block **plus** one
classifier-friendly prose line, instead of an `AskUserQuestion` menu.

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

**Prose-line vocabulary** — exactly one line, using this repo's background-job
classifier words so the job-list state extractor catches the outcome:

- `result:` — on `status: success`
- `needs input:` — on `status: needs_input` (**note the SPACE** — the prose form
  carries a space to match the classifier; the JSON enum stays snake_case
  `needs_input`)
- `failed:` — on `status: failed`

### Worked examples

**Success** (safe gate auto-picked):
```json
{"status":"success","mode":"headless","gate":null,"decision":"auto_picked_recommended","human_review_required":false,"artifacts":[".renmark/plans/example.plan.md"]}
```
`result: planned feature and wrote .renmark/plans/example.plan.md`

**Dangerous gate** (merge — halted for human review):
```json
{"status":"needs_input","mode":"headless","gate":"merge","decision":"halted_for_human_review","human_review_required":true,"artifacts":[".renmark/decisions/merge-approval.json"]}
```
`needs input: merge approval required; headless mode cannot approve merge/release gates`

**Blocker** (true `failed`):
```json
{"status":"failed","mode":"headless","gate":null,"decision":"blocked","human_review_required":false,"artifacts":[],"reason":"missing PRD path and no safe default could be inferred"}
```
`failed: missing PRD path and no safe default could be inferred`

---

## Runtime helper (how skills call this)

The detection precedence, gate classification, return schema, and decision-artifact
format above are all implemented once in `renmark/headless.py`. A skill does not
reimplement them — at any gate it calls:

```python
from renmark import headless

result = headless.resolve_gate(
    repo,
    gate,                       # e.g. "merge", "next-steps", "prd"
    kind="safe",                # "safe" | "dangerous"
    recommended=<the (Recommended) option>,
    tool_available=<is AskUserQuestion available?>,   # Layer-4 signal
    originating_skill=<skill>,  # e.g. "finish"
    what=<one-line description of what the gate decides>,
)
```

- `resolve_gate(...)` returns `{"mode": "interactive"}` when the run is **not**
  headless → render the normal `AskUserQuestion` menu **exactly as today** (the
  contract is inert; see `handoff-menu.md`).
- On a headless **safe** gate it returns the success / `auto_picked_recommended`
  envelope; on a headless **dangerous** gate (or any unknown/uncertain gate, per
  the fail-safe uncertainty rule) it returns the `halt_for_human_review`
  `needs_input` envelope and writes the decision artifact.
- **Layer-4:** pass `tool_available=False` when `AskUserQuestion` is absent from
  the tool list to force headless — the Python runtime can't see the model's tool
  list, so the skill supplies this signal (see §1, layer 4).

When `resolve_gate(...)` returns anything other than `{"mode": "interactive"}`,
the skill emits the **returned envelope** as the fenced JSON block **and**
`headless.render_return(envelope)` as the single classifier-friendly prose line
(`result:` / `needs input:` / `failed:`; `render_return` returns `""` for the
interactive case) — **instead of** an `AskUserQuestion` menu.

> **Adoption status (tracked follow-up):** the three shared menu files already
> reference this contract, but threading the `resolve_gate(...)` call into each of
> the **28 individual SKILL.md gate points is a tracked follow-up — not yet wired
> per-skill.** Headless enforcement is therefore currently **helper-available**
> (the runtime exists and is correct) but **not yet called from every skill**.

---

## 4. Decision-artifact format

A dangerous-gate halt writes one JSON file at
`.renmark/decisions/<gate>-approval.json` (e.g. `merge-approval.json`,
`release-approval.json`, `prd-approval.json`):

```json
{
  "gate": "merge",
  "timestamp": "2026-06-26T00:00:00Z",
  "what": "land feature/x to main",
  "originating_skill": "finish",
  "stage": "ready-to-release",
  "human_review_required": true
}
```

| Field | Meaning |
|---|---|
| `gate` | the dangerous gate name (`merge` · `release` · `prd` · `destructive` · `budget`) |
| `timestamp` | ISO8601 of the halt |
| `what` | one line describing what needs approval |
| `originating_skill` | the skill that hit the gate (`finish`, `prd`, …) |
| `stage` | the lifecycle stage at halt |
| `human_review_required` | always `true` for a halt record |

The halt also sets `human_review_required=true` (and `human_review_for=<gate>`) in
`lifecycle.json`. **`/renmark:approve` is the sole surface that clears the gate** —
it consumes the decision artifact, clears `human_review_required`, and lets a
later (interactive or explicitly-authorized) run proceed past the dangerous gate.

---

## Why a shared file

Same precedent as `_shared/handoff-menu.md` and `_shared/scope-contract.md`: one
edit point, and the behavior is **inherited** by all SKILL.md files through the
three menu files rather than duplicated per skill — protecting the v0.20.0
trigger-only / disable-model-invocation frontmatter from any description bloat.

When citing this contract in a menu file, write:

> *If headless (per `${CLAUDE_PLUGIN_ROOT}/skills/_shared/headless-contract.md`
> detection), do not render `AskUserQuestion`: auto-pick the `(Recommended)`
> option at safe gates and continue; at dangerous gates halt, write
> `.renmark/decisions/<gate>-approval.json`, set `human_review_required=true`, and
> return the `needs_input` JSON + `needs input:` prose line.*

Do not paste this contract into the calling SKILL.md.
