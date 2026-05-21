# Shadow baseline changes

## 2026-05-21 — initial baselines

Initial baselines recorded for dispatch, lifecycle, and summary subsystems
as part of v0.3.1 shadow framework introduction. These freeze the
known-good output shape for each subsystem so future code changes that
alter behavior must be explicitly accepted.

Subsystems baselined:
- dispatch (4 cases): pass-clean, fail-with-retry, transcript-leak, oversize-summary
- lifecycle (3 cases): fresh-feature, full-walk, approval-gate
- summary (2 cases): verification-artifact, failed-artifact
