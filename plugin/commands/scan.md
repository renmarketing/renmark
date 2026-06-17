---
description: "Use to run a deterministic read-only QA proposer lane — runs audit + verifiers, dedupes findings, proposes backlog items. Writes artifacts only under .renmark/reviews/ and .renmark/state/, never advances lifecycle.json. Scheduling is external."
argument-hint: '[--propose | --emit-cron]'
---

Read `${CLAUDE_PLUGIN_ROOT}/skills/scan/SKILL.md` and follow its instructions exactly. The user provided this input: $ARGUMENTS

If `$ARGUMENTS` is empty, begin the scan skill's flow.
