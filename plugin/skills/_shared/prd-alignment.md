# PRD Alignment Subagent — Contract Reference (single source of truth)

**Shared by `/renmark:feature` and any skill that introduces a new feature or
structural change.** This is the one place the PRD-alignment dispatch pattern
lives so skills can't drift. The rule is simple: the orchestrator/router MUST
NOT read the PRD body — it sees ONLY the bounded `verdict` summary returned by
the isolated subagent.

---

## PRD touchpoint policy (read before adding any PRD coupling)

Every renmark skill maps to **exactly one** of three PRD interactions. Before
wiring the PRD into a skill, decide which one — if it isn't WRITE or ALIGN, the
default is NOTHING. This is the guard against PRD duplication and context bloat
(see ADR-005 in `.renmark/memory/decisions.md`).

| Interaction | The only allowed mechanism | Skills |
|---|---|---|
| **WRITE** (create/update) | `/renmark:prd` only — every other skill *routes* (proposes), never writes `PRD.md` | `prd` |
| **ALIGN** (read-only ≤5-line verdict) | this subagent contract only — never inline PRD reading | `feature`, `brainstorm`, `roadmap` |
| **NOTHING** | — | everything else (orchestrate, verify, finish, check-plan, init, debug, codereview, resume, help, doctor) |

- **One writer.** start / brainstorm / feature may *route* to `/renmark:prd`; none
  write `PRD.md` themselves. This is what keeps "multiple entry points, one file"
  safe.
- **`plan` is a deliberate exception, not an ALIGN user:** it does a *light* read
  of `REQ-n` IDs for the optional `serves:` field, not a full alignment check.
  Coverage flows plan → tasks → verify transitively — which is why `verify
  --coverage` is intentionally *not* built.
- **Altitude rule (anti-duplication):** the PRD is product-level (one per
  project); a brainstorm spec is feature-level (many). Product non-goals live in
  the **PRD**; a build's MVP cut lives in the **scope contract**. Cross-reference,
  never copy.

Rejected as bloat (don't re-propose without revisiting ADR-005): brainstorm as a
PRD writer, `verify --coverage`, init/document PRD pointers, orchestrate reading
the PRD. (`roadmap --gaps` uses this ALIGN subagent per ADR-009 — it is in the
ALIGN row, not here.)

---

## Why an isolated subagent

PRD files are large context consumers. Loading one into the orchestrator would
violate the G11 / "orchestrator coordinates, does not accumulate" rule and bloat
the routing context for all subsequent waves. Instead, a single-purpose subagent
is dispatched to absorb the PRD in its own context, reason over it, and return a
compact result.

---

## Hard rule — orchestrator context boundary

> **The router/orchestrator MUST NOT read `PRD.md` or any section of it.**
> It passes only the feature description and file scope to the subagent.
> It receives only the ≤5-line verdict summary. Period.

This is the enforcement point for the G11 contract. Violations — reading PRD
content inline, summarizing PRD sections in orchestrator reasoning, or passing
PRD excerpts as context — are treated as bugs, not optimizations.

---

## What the router dispatches (subagent inputs)

The orchestrator/router invokes an **Agent tool call** (not a Bash subprocess)
and passes ONLY:

| Field | Content |
|---|---|
| `feature_description` | Plain-text description of the feature or change (≤200 words) |
| `file_scope` | List of files or directories the change touches |

The router does **not** pass: the PRD body, any PRD excerpt, prior conversation
context about the PRD, or any artifact whose content is the PRD.

---

## What the subagent does (in its own context)

1. Reads `PRD.md` at the project root.
2. Reads any relevant supporting docs linked from the PRD (in its own context).
3. Checks whether the described feature:
   - Has a clear home in the PRD (aligned scope, existing goal, or natural
     extension of a stated objective).
   - Contradicts a stated non-goal or out-of-scope boundary.
   - Is entirely absent from the PRD (potential drift or new requirement).
4. Returns a **bounded result** (≤5 lines, see format below).

The subagent does NOT modify any file. It does NOT write to the PRD. It reads
and reasons only.

---

## Bounded return format

The subagent returns EXACTLY the following fields — no prose, no reasoning dump:

```
verdict: aligned | drift
reason: <one-line explanation — required only when verdict is drift>
proposed_prd_addition: <small markdown snippet — optional, only when verdict is drift>
```

`verdict` is the required field. `reason` and `proposed_prd_addition` are
included only when `verdict: drift`.

**Line budget.** The **orchestrator-visible** part — `verdict` + `reason` — MUST
NOT exceed 5 lines; that is all the router reads. `proposed_prd_addition`, when
present, is NOT counted against that budget: it is a small snippet (or a pointer
to one) handed straight to `/renmark:prd` update mode for the human, and never
enters the orchestrator/router context. Keep it short — a few lines or an
artifact pointer, not a full draft.

---

## Examples

**Aligned case** (feature maps cleanly to an existing PRD goal):

```
verdict: aligned
```

**Drift case** (feature introduces something outside current PRD scope):

```
verdict: drift
reason: PRD lists "no external API dependencies" as a non-goal; this feature calls a third-party geocoding API.
proposed_prd_addition: |
  ### External Geocoding Integration
  Allow address-to-coordinate resolution via a configurable third-party API.
  Gated by an opt-in env var; no network call is made when unset.
```

---

## What the router does with the verdict

| Verdict | Router action |
|---|---|
| `aligned` | Proceed with the feature plan as normal. |
| `drift` | Route the `proposed_prd_addition` into `/renmark:prd` update mode (human-gated). The feature plan is PAUSED until the human approves or rejects the PRD addition. |

**`drift` never auto-writes the PRD.** `/renmark:prd` update mode is
human-gated — the proposed snippet is surfaced to the user for review, and the
PRD is only updated after explicit approval. AI proposes; the human owns the PRD.

---

## Dispatch reference (for skill authors)

When citing this contract in a SKILL.md, write:

> *Dispatch the PRD alignment subagent from
> `${CLAUDE_PLUGIN_ROOT}/skills/_shared/prd-alignment.md`: Agent tool call,
> passing ONLY `feature_description` + `file_scope`. Receive ONLY the ≤5-line
> verdict summary. Do NOT read PRD.md in the orchestrator context.*

Do not paste the subagent logic or examples into the calling SKILL.md.

---

## Why a shared file

Earlier drafts had `/renmark:feature` inline its own PRD check logic. The text
drifted the moment a second feature-entry skill was added. Centralizing here means:

- One edit point. Any future skill that needs PRD alignment (e.g. `/renmark:change`,
  `/renmark:migrate`) reads the same contract.
- Linter-friendly. `plugin/skills/_shared/` is skipped by `renmark.lint` (it's
  a reference dir, not a skill).
- Symmetric with `_shared/scope-contract.md` and `_shared/handoff-menu.md` —
  same pattern, same precedent.
