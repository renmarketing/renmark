# Shadow baseline changes

## 2026-06-10 00:56:22 UTC — dispatch

SUBAGENT_OUTPUT_FIELDS gained G9 triplet validation_status/parser_success/schema_compliance (v0.9.0 codereview fix)

## 2026-05-26 17:13:08 UTC — lifecycle

fix: dead-pointer lifecycle stages route to manual hint until /renmark:release ships

## 2026-05-21 — initial baselines

Initial baselines recorded for dispatch, lifecycle, and summary subsystems
as part of v0.3.1 shadow framework introduction. These freeze the
known-good output shape for each subsystem so future code changes that
alter behavior must be explicitly accepted.

Subsystems baselined:
- dispatch (4 cases): pass-clean, fail-with-retry, transcript-leak, oversize-summary
- lifecycle (3 cases): fresh-feature, full-walk, approval-gate
- summary (2 cases): verification-artifact, failed-artifact
