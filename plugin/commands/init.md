---
description: "Use when the user wants renmark to onboard or document a project — the non-destructive front door. Scaffolds missing CLAUDE.md/AGENTS.md/CHANGELOG.md/.renmark/, back-fills missing rule blocks, scans the repo for structure/modules/public symbols, writes a stub into CLAUDE.md/AGENTS.md and the full map into .renmark/memory/project-map.md, reports standards health, then hands off to roadmap gap discovery. Renmark's analog to Claude Code's native /init. Idempotent."
---

Read `${CLAUDE_PLUGIN_ROOT}/skills/init/SKILL.md` and follow its instructions exactly. The user provided this input: $ARGUMENTS

If `$ARGUMENTS` is empty, begin the init skill's flow.
