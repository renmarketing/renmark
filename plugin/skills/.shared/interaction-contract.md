# Interaction contract

This is the single host-neutral contract for asking a user to make a real
decision or pass an approval gate. Skill and pipeline authors define semantic
decisions against this contract; host adapters only choose how to render them.

## When to ask

A **decision** exists only when work cannot safely continue without the user
choosing between materially different outcomes. An approval gate is always a
decision and must never be satisfied by silence, timeout, a preselected
recommendation, or a prior approval for a different decision ID.

Progress, observations, next steps, confirmations that need no choice, and
other informational status are prose. They must not be disguised as a picker
or padded with choices merely because a host can display one.

## Semantic decision model

Each decision has:

- a stable, unique `decision_id`;
- one short question with enough context to choose safely;
- an ordered, non-empty list of semantic choices; and
- whether the decision is dangerous, destructive, security-sensitive, or an
  approval gate.

Each semantic choice has a stable `choice_id`, a short stable `code`, an exact
user-facing `label`, and a concise consequence. IDs and codes describe the
meaning, not a host widget, page number, or current collaboration mode.

Exactly one semantic choice is `recommended`, and it is always choice index
`0`. Reordering for display is forbidden. A renderer may decorate that label
with `(Recommended)`, but the decoration is not part of the exact label or
code. A continuation page that does not contain index `0` must not invent a
second recommendation.

Dangerous decisions must include a visible semantic refusal choice, such as
`refuse` or `cancel`, with its consequence stated plainly. The refusal must
remain reachable from every render and must not depend on free text. The
safest viable choice is normally the recommendation; recommending a dangerous
action requires an explicit rationale. No dangerous action proceeds from an
ambiguous answer.

## Resolving an answer

Resolve input only against the current `decision_id` and use this order:

1. A host-native selection resolves to its bound `choice_id`.
2. An exact emitted `code` resolves to that choice.
3. An exact emitted label resolves to that choice.
4. A number resolves to the correspondingly numbered choice in the rendered
   numbered list.
5. Free text is accepted only when the decision explicitly declares a
   free-text response. Otherwise it is not inferred, fuzzily matched, or
   treated as approval; re-render the unresolved decision.

Leading and trailing whitespace may be removed. Labels are otherwise exact;
partial labels and semantic guesses are invalid. Codes are emitted in
lowercase and may be ASCII case-folded before exact comparison. A number is a
presentation alias, never a semantic ID. When an allowed free-text response
could be mistaken for a listed choice, ask for an exact code before acting.

`more`, `back`, and `cancel` are reserved navigation codes and cannot be used
as semantic choice codes, except that a dangerous decision may bind its
explicit refusal choice to `cancel`. Selecting semantic `cancel` resolves the
decision as refused; selecting navigational `cancel` exits without approval.

## Render-time capability resolution

Resolve presentation capability when the question is rendered. The semantic
decision is identical on every host.

- **Claude:** use native choices only when the active render contains no more
  than four selectable entries, including navigation entries.
- **Codex Plan:** use native choices only when the active render fits the
  host's active cap of two or three selectable entries. Never manufacture a
  filler choice to reach the minimum or exceed the currently advertised cap.
- **Codex Default:** render a complete numbered fallback in prose, containing
  every semantic choice, its code, consequence, the recommendation marker,
  and an explicit cancel/refusal instruction. It must accept the exact label,
  displayed number, stable code, or explicitly allowed free text.

If a native render cannot expose all required semantic and navigation entries
within its active cap, use bounded continuation pages or the complete numbered
fallback. Native availability is an optimization, not permission to omit a
choice. If native choices are unavailable, fail closed to the numbered
fallback rather than silently selecting a default.

A decision with only one semantic choice uses the prose/numbered confirmation
fallback with that choice and an explicit Cancel path. Do not create a fake
second substantive choice, and do not present informational prose as a
one-choice decision.

## Bounded continuation

Continuation pages preserve the original `decision_id`, semantic order,
choice IDs, codes, labels, recommendation, and approval status. Only the page
window changes.

- `More` appears only when undisplayed choices remain and advances by one
  bounded page.
- `Back` appears only after the first page and returns by one bounded page.
- `Cancel` remains available on every page, either as a selectable entry or
  as the reserved exact code stated beside the picker.
- Every semantic choice must be reachable; a renderer must never truncate,
  summarize away, or replace remaining choices.
- A page must contain at least one semantic choice. If navigation controls
  would consume the host cap, switch to the complete numbered fallback.
- At either boundary, an invalid `more` or `back` leaves the decision
  unresolved and re-renders the current valid page.

After `more`, `back`, invalid input, or an interrupted native picker, re-render
the same unresolved decision with full local instructions. Do not treat a
continuation as a new approval, duplicate the recommendation, or rely on the
user remembering a hidden page. `Cancel` ends the interaction without passing
the gate; later continuation requires asking the decision again.

Page index, page size, native-picker availability, and the selected renderer
are ephemeral presentation state. They never infer, switch, or persist a host
collaboration mode. Durable state may record the unresolved semantic
`decision_id` and any resolved `choice_id`; after restart, render from the
first page or use the complete numbered fallback.
