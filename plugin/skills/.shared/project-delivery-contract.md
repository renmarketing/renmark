# Managed Project Delivery Contract

This concise fragment is the canonical source for managed `CLAUDE.md` and
`AGENTS.md` blocks.  It defines two owner paths: **Agency** governs an
owner-facing project engagement (discovery, agreement, milestones, signoff),
while **Orchestrator** executes a defined, approved milestone through scoped
work.  Neither path replaces the other; Agency drives Orchestrator when build
work is ready.

## Milestone delivery

- Express each milestone as a demonstrable owner outcome with acceptance
  criteria, not a list of activities.  Plan only bounded work packages needed
  for that outcome; preserve the approved scope and surface drift as a human
  decision.
- Separate roles: the planner defines packages and evidence, executors make
  scoped changes, and an independent reviewer assesses the result.  The
  coordinator consumes bounded package summaries and pointers, never full
  skill bodies, transcripts, or accumulated implementation context.
- Verify with deterministic, fresh evidence first.  Each package has a focused
  verifier; the milestone also requires its stated acceptance evidence.  See
  `deterministic-first.md`, `workflow-fanout.md`, and `subagent-profiles.md`.
- Keep build, review, and repair loops milestone-local.  A failed verifier or
  review may receive only bounded, scoped repair attempts, followed by
  re-verification and independent re-review.  Stop rather than expand scope,
  repeat an equivalent failure, or treat status prose as proof.

## State and human decisions

Canonical progress, package status, evidence pointers, and gates live in
`.renmark/state/` and the relevant plan/review artifacts, not conversation
history.  Stop for unclear intent, scope or risk changes, failed bounded
repair, required owner demo, approval/signoff, merge, release, or another
human-review gate.  Passing tests alone never clear an owner gate.  See
`handoff-menu.md`, `context-taxonomy.md`, and `agency-delivery.md`.

## Decision presentation

When the active host supports a native picker, present selector-capable
decisions with that picker.  In an interactive Claude Code main session,
invoke `AskUserQuestion` with a real `options` array; never replace a decision
with ordinary prose or a typed-only list.  Otherwise present the same choices
as a numbered fallback, with the recommended safe option first; do not make
the fallback a different decision or an automatic approval.  See
`interaction-contract.md`.
