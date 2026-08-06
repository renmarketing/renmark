---
artifact_type: program
schema_version: 1
created_at: 2026-08-06T22:33:31+00:00
source_sha: 3142267
---

# Program — cross-host-native-tool-leverage

_mode: staged · Stage 1/4 · task 0/1 done · current: Release 1: Baseline and compatibility coverage_

## ○ Release 1: Baseline and compatibility coverage — serves stage-2 baseline **(current)**

- [ ] Document host/dispatch/interaction fast-gate test target

## ○ Release 2: Consolidate dispatch.py HostName onto hosts.py HostKind — serves Modularity finding (duplication fix)

- [ ] Replace dispatch.py HostName Literal with hosts.py HostKind imports
- [ ] Add grep-based regression test guarding against re-duplication

## ○ Release 3: ExitWorktree adoption + bounded ScheduleWakeup spike — serves guardrail: REQ-30 budget; Direction Gate scope items 2-3 (ExitWorktree committed, ScheduleWakeup spiked)

- [ ] Add supports_exit_worktree to HostCapabilities
- [ ] Wire ExitWorktree instruction into finish/SKILL.md worktree cleanup
- [ ] Bounded spike: confirm ScheduleWakeup live-invokability (no committed code)

## ○ Release 4: REQ-31 Codex task-tracking CLI wrapper + skill wiring — serves REQ-31

- [ ] Add renmark-execute --task-create/--task-in-progress/--task-complete subcommands
- [ ] Wire live-Codex task-tracking instruction into orchestrate/SKILL.md
