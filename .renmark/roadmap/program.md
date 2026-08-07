---
artifact_type: program
schema_version: 1
created_at: 2026-08-06T22:33:31+00:00
source_sha: 3142267
---

# Program — cross-host-native-tool-leverage

_mode: staged · Stage 4/4 · task 0/2 done · current: Release 4: REQ-31 Codex task-tracking CLI wrapper + skill wiring_

## ● Release 1: Baseline and compatibility coverage — serves stage-2 baseline

- [ ] Document host/dispatch/interaction fast-gate test target

## ● Release 2: Consolidate dispatch.py HostName onto hosts.py HostKind — serves Modularity finding (duplication fix)

- [x] Replace dispatch.py HostName Literal with hosts.py HostKind imports
- [x] Add grep-based regression test guarding against re-duplication

## ● Release 3: ExitWorktree adoption + bounded ScheduleWakeup spike — serves guardrail: REQ-30 budget; Direction Gate scope items 2-3 (ExitWorktree committed, ScheduleWakeup spiked)

- [x] Add supports_exit_worktree to HostCapabilities
- [x] Wire ExitWorktree instruction into finish/SKILL.md worktree cleanup
- [x] Bounded spike: confirm ScheduleWakeup live-invokability (no committed code)

## ○ Release 4: REQ-31 Codex task-tracking CLI wrapper + skill wiring — serves REQ-31 **(current)**

- [ ] Add renmark-execute --task-create/--task-in-progress/--task-complete subcommands
- [ ] Wire live-Codex task-tracking instruction into orchestrate/SKILL.md
