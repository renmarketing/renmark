# Model Routing Discipline — Reference (single source of truth)

**Shared by `/renmark:orchestrate`, `/renmark:finish`, `/renmark:feature`, and any skill that dispatches subagents.** This is the one place strict model-routing discipline lives: clear rules for when to use Haiku, Sonnet, Opus, and Fable, and explicit gates to prevent escalation creep. Operationalizes cost discipline and REQ-19 (cost control).

---

## The routing matrix

| Task signature | Model | Rationale |
|---|---|---|
| Docs, grep, changelog, small summaries, simple audits | **Haiku** | Pattern-matching, text shuffling, no reasoning or architecture. Haiku is cost-optimal and sufficient. |
| Planning, normal implementation, review summaries, refactor decisions | **Sonnet** | Light reasoning, multi-file scope, moderate context. Sonnet + subagent isolation is the cost/quality sweet spot. |
| Bounded code tasks, single-file fixes, test scaffolding | **Codex** (when `renmark-execute` is available) | Bulk code emit, deterministic, no model fallacy risk. Always prefer Codex for code bulk. If Codex unavailable, route to Sonnet. |
| **Escalation ONLY:** architecture decisions, major design forks, adversarial review, judgment-heavy tradeoffs | **Opus / Fable** | Deep reasoning, cross-domain synthesis. **Reserved.** Do NOT use by default for docs, finish, small verification, or changelog. |

---

## Hard escalation gate

Before dispatching to Opus or Fable, **consult `renmark.cost.requires_escalation(task_spec)` deterministically** — the function returns `True` only when:

- Task involves **major architecture change** (multi-layer refactor, new design pattern, cross-subsystem coordination).
- **Judgment required** that cannot be decomposed to Sonnet-grade planning (trade-off between competing correctness constraints, adversarial review).
- **Prior Sonnet attempt failed** in a way that indicates deeper reasoning is needed (not just missing context, but a conceptual gap).

Escalation is opt-in, not default. A task that "might benefit from Opus" is still a Sonnet task unless it hits one of the three criteria.

---

## Learned routing ledger

Every dispatch logs its decision in `.renmark/memory/routing.md`: task signature, chosen model, justification, outcome (PASS/FAIL), token cost. Over time, this ledger reveals:

- Which task classes consistently fail at Haiku/Sonnet and warrant escalation.
- Which escalations were unnecessary (Sonnet would have passed).
- Cost trends per task type.

Cite the ledger **before choosing non-default escalation** — if an identical prior task succeeded at Sonnet, reuse that tier. If it failed, escalate with evidence. Do not escalate on intuition.

---

## Examples

**Correct:** A changelog entry for a bug fix → Haiku (text assembly, no reasoning).

**Correct:** Planning a new feature refactor → Sonnet (multi-file scope, tradeoff reasoning).

**Incorrect:** Using Opus to write changelog → violates "no escalation for docs."

**Correct escalation:** Designing a new cost-control architecture with cross-layer implications → Opus (major design decision, prior Sonnet planning hit ambiguity on thread-safety semantics).

---

## Why a shared file

Early drafts scattered model-choice rationale across skill prompts. One skill escalated to Fable for a summary; another used Opus for a grep. Centralizing here means:

- One edit point. Model routing discipline is defined once; every skill cites this matrix.
- Deterministic gate. `renmark.cost.requires_escalation` is the programmatic check; this file explains when and why.
- Ledger-driven. The routing.md ledger is the source of truth for learned behavior — don't re-argue old decisions.

When citing this discipline in a SKILL.md or subagent dispatch, write:

> *Honor model routing discipline in `${CLAUDE_PLUGIN_ROOT}/skills/_shared/model-routing.md`: Haiku for docs/grep/summaries/small audits; Sonnet for planning/implementation/reviews; Codex for bounded code tasks; Opus/Fable escalation-only when `renmark.cost.requires_escalation` returns True (architecture/judgment/prior-failure). Consult `.renmark/memory/routing.md` ledger before choosing non-default tier.*

Do not paste the matrix or escalation gate into the calling SKILL.md — cite this file.
