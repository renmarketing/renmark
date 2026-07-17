# Cost Preview — Reference (single source of truth)

**Shared by `/renmark:brainstorm`, `/renmark:plan`, `/renmark:orchestrate`, and `/renmark:finish`.** This is the one place cost-preview discipline lives: what to show before expensive work, when to escalate to Opus/Fable, and how to present cheaper alternatives. Operationalizes cost control (REQ-19) and cost transparency. The deterministic source of truth is `renmark/cost.py` (estimate_cost, requires_escalation).

---

## When to show a cost preview

Show a cost preview BEFORE executing expensive work if:

- The plan or task will dispatch **3+ subagents**, OR
- The task **routes to Opus/Fable**, OR
- The estimated **token cost exceeds low threshold** (~10k tokens, plan-dependent), OR
- The estimated **cost band is medium or high** (see table below).

Quick scripts, single-file fixes, and verification runs are usually "low cost" — show preview only if the plan itself is expensive.

---

## What a cost preview MUST show

| Field | Content |
|---|---|
| **Estimated model tier** | Which model(s) will run: Haiku, Sonnet, Codex, Opus, Fable, or a mix. |
| **Token/cost band** | Low (≤$0.01), Medium ($0.01–$0.10), High (≥$0.10), or a range. |
| **Subagent count** | How many subagents will be spawned (if >0). |
| **Escalation justification** | If routing to Opus/Fable, why: architecture, judgment, prior-failure (cite `renmark.cost.requires_escalation`). |
| **Cheaper alternative** | If a cheaper approach exists, show it (e.g., "Use Sonnet for planning instead of Opus if estimates are uncertain"). |

**Format:** Plain prose, ≤10 lines. Embed in the skill response before asking for approval.

---

## Estimating cost

Use `renmark.cost.estimate_cost(task_spec, subagent_count, model_tiers)` to compute:

- `estimated_tokens` (input + output, averaged by model)
- `estimated_cost` (USD, using current Claude API pricing)
- `cost_band` (`low` / `medium` / `high`)

For a plan with multiple phases, sum across all tasks:

```python
total_cost = sum(
    estimate_cost(task) for task in plan.tasks
)
```

---

## Escalation discipline

Before routing to Opus or Fable, **show the cost preview and justify it**:

| Scenario | Cost band | Show preview? | Justification |
|---|---|---|---|
| Feature planning with moderate complexity | Low–Medium | Yes (if Medium) | Show to set expectations. |
| Architecture review / design fork | Medium–High | **Yes** | Cite `requires_escalation` — is this really necessary, or can Sonnet plan it? |
| Adversarial review before release | Medium–High | **Yes** | Cite the high-risk factor justifying Opus/Fable. |
| Sonnet attempt failed; escalate to Opus | Medium–High | **Yes** | Cite the failure reason. Show why Sonnet won't suffice. |

**Bias:** default to Sonnet. Escalate only when justified. Show cost BEFORE asking approval so the user can decline or suggest a cheaper path.

---

## Complement to finish lanes and planning

**Plan costs (§6):** The `/renmark:plan` skill pre-computes task costs and shows a cost band upfront. A plan with "High" cost band may warrant lane adjustment (quick vs. release vs. self-update).

**Finish lane costs:** Each finish lane has an estimated cost (low/medium/high). The `/renmark:finish` skill shows lane costs BEFORE asking which lane to use.

**This file:** Emphasizes transparency — show estimates before work starts, offer cheaper alternatives, and escalate only when justified by the hard gates in `_shared/model-routing.md`.

---

## Examples

**Example 1: Feature plan with high subagent count.**
```
Cost Preview
—
Estimated model tiers: Sonnet (planning), Haiku (reads)
Subagents: 6 (one per task, model: sonnet)
Estimated tokens: ~45k
Estimated cost: $0.07 (Medium band)

Consideration: 6 subagents is reasonable for parallel work. If cost is a concern,
we could reduce to 3 agents (sequential, ~$0.04). Would you prefer sequential?
```

**Example 2: Escalation to Opus (justified).**
```
Cost Preview
—
This task (architecture redesign for thread-safety) requires Opus reasoning.
Estimated tokens: ~35k
Estimated cost: $0.15 (High band)

Justification: Prior Sonnet planning hit ambiguity on acquire/release ordering
that Opus-grade judgment can resolve. No cheaper alternative; this is a required
architecture decision.

Proceed? [yes/no]
```

**Example 3: Cheaper alternative available.**
```
Cost Preview
—
Current plan routes to Opus for finish verification: ~$0.14 (High)

Alternative: Use Sonnet for finish verification (test re-run only): ~$0.06 (Medium)

Which would you prefer?
```

---

## Why a shared file

Cost transparency was scattered across skills. One skill silently escalated to Fable for a summary; another showed a $20 estimate mid-execution. Users had no way to set cost budgets or compare alternatives. Centralizing here means:

- One standard. Every skill that does expensive work shows the same preview format.
- Deterministic source. `renmark.cost.estimate_cost` and `requires_escalation` are the programmatic gates.
- Transparency by default. Escalations and multi-agent dispatches MUST be justified and visible before execution.

When citing in a SKILL.md, write:

> *Show a cost preview before expensive work via `renmark/cost.py::estimate_cost`. Format per `${CLAUDE_PLUGIN_ROOT}/skills/.shared/cost-preview.md`: model tiers, token/cost band, subagent count, escalation justification (cite `requires_escalation`), and cheaper alternatives. Do not route to Opus/Fable without justifying and surfacing the cost.*

Do not paste the matrix or examples into the calling SKILL.md — cite this file.

## Subagent-gate line (required)

Every pre-dispatch cost preview MUST include the subagent-gate verdict from
`renmark.subagent_gate` — call `challenge_plan(tasks)` then `preview_line(...)`
and show the line (e.g. `⚠ CHALLENGE: 3 of 5 subagent(s) unjustified; 2
deterministic-eligible; 1 general-purpose`). When the verdict is challenged,
the dispatch gate requires explicit acknowledgment before proceeding — a
subagent-heavy or deterministic-eligible plan is never auto-dispatched silently.
