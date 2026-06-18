---
description: "Use for the Project Setup pipeline — adopting renmark into any repo (new, in-progress, or production). The non-destructive front door. Scaffolds missing CLAUDE.md/AGENTS.md/CHANGELOG.md/.renmark/, back-fills missing rule blocks, scans the repo for structure/modules/public symbols, writes a stub into CLAUDE.md/AGENTS.md and the full map into .renmark/memory/project-map.md, reports standards health, then hands off to roadmap gap discovery. Renmark's analog to Claude Code's native /init. Idempotent."
---

Read `${CLAUDE_PLUGIN_ROOT}/skills/init/SKILL.md` and follow its instructions exactly. The user provided this input: $ARGUMENTS

If `$ARGUMENTS` is empty, begin the init skill's flow.
