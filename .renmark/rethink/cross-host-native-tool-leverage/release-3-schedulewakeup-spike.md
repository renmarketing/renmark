---
artifact_type: rethink-spike-evidence
schema_version: 1
created_at: 2026-08-07T23:10:00Z
source_sha: 9b81f04
related_plan: .renmark/rethink/cross-host-native-tool-leverage/roadmap.md
generator: sonnet
---

# Spike evidence — ScheduleWakeup live-invokability

**Question (from roadmap.md Release 3):** is `ScheduleWakeup` (or an
equivalent scheduled-resume primitive) actually callable by a live Claude
Code session executing a renmark skill today?

## Result: CONFIRMED AVAILABLE

Evidence is a real, unstaged call made during this same session while
waiting on a background `pytest -q` run (task id `bfe1a7dd0`) for Release
3's own verification:

1. `ScheduleWakeup({delaySeconds: 60, reason: "Waiting on background
   full-suite pytest run to finish before committing the hosts.py
   capability field change.", prompt: "<continuation instructions>"})`
   returned: `"Next wakeup scheduled for 23:09:00 (in 107s). Nothing more
   to do this turn — the harness re-invokes you when the wakeup fires or a
   task-notification arrives."` — a successful live invocation, not an
   error or "tool does not exist" response.
2. The background task's own completion notification arrived first
   (harness-tracked work auto-notifies). `ScheduleWakeup({stop: true})`
   was then called to cancel the pending wakeup and returned: `"Loop
   stopped — cancelled 1 pending wakeup(s); no further dynamic-loop
   wakeups scheduled."` — cancellation also works.

Both the schedule and the cancel paths are confirmed live-invokable in a
plain orchestrate-style session, not just inside an explicit `/loop`
invocation.

## Self-correction — this was NOT actually the recommended use pattern

`ScheduleWakeup`'s own tool guidance is explicit: *"Do NOT schedule a
short-interval wakeup to poll for background work you started — when
harness-tracked work finishes, you are re-invoked automatically, so
polling is wasted."* The background pytest run I was waiting on **was**
harness-tracked and did deliver its own automatic completion
notification — the scheduled wakeup was redundant and correctly
cancelled before firing. This is honestly recorded here because it is
part of the evidence: the tool is callable outside a formal `/loop`
context, but this specific call was an example of the anti-pattern its
own docs warn against, not a model usage.

## Stop condition per roadmap.md

Confirmed available → per the roadmap's stated stop condition, a
**follow-up release (not this one)** may add a `supports_schedule_wakeup`
capability field and skill-prose wiring mirroring `ExitWorktree`'s
pattern — scoped separately, with real design for *when* a renmark skill
should use it (e.g. Tier-2 usage-limit pause resumption in `orchestrate`,
where no other harness-tracked notification would fire). This spike does
not itself add any capability field or wiring — no production code
changed beyond this evidence file, per the roadmap's stated budget.
