# QA Flows

This is the project's QA playbook — the canonical, committed store of reusable
browser QA flows. `/renmark:verify --qa` and `--deep-qa` read this file before
choosing a flow to run, and update / append / promote a flow back here when it
passes. Newest flow at top. Committed memory — it survives `/clear` and carries
across sessions.

Maintained by `/renmark:verify --qa` (and `--qa --bootstrap`).

## Format

Each flow records: flow name, target URL/route, preconditions, numbered user
actions, expected behavior (including no overlapping/clipped controls and no
console errors), optional key selectors / UI landmarks, known risks, last
passing review artifact, baseline screenshot paths, and any related
bugs/regressions. Keep it lightweight markdown — no schema, no database. Promote
a flow to the top of the list each time it passes so the freshest flows are
found first.

## Flows

<!--
EXAMPLE / TEMPLATE FLOW — this is not a real flow. It exists only to show the
field shape. Copy it, fill it in, and remove the comment markers when you add a
real flow. `/renmark:verify --qa --bootstrap` seeds real flows from the live app.

## Flow: <name>
- URL: `/route/pattern`
- Preconditions:
  - ...
- Actions:
  1. ...
- Expected:
  - Preview/page loads
  - No overlapping or clipped controls; nothing off-screen
  - No console errors
  - <feature-specific success state>
- Key selectors / UI landmarks: (optional)
- Evidence:
  - Last passing review artifact: `.renmark/reviews/...`
  - Baseline screenshots: `.renmark/reviews/qa/...`
- Known risks:
  - ...
- Related bugs / regressions:
  - ...
-->

(No real flows yet — run `/renmark:verify --qa --bootstrap` to seed the first one.)
