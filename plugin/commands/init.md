---
description: Use when the user wants renmark to document the project itself — scans the repo for file structure, modules, and public functions/exports, then merges a managed project map block into CLAUDE.md and AGENTS.md. Renmark's analog to Claude Code's native /init. Idempotent — re-run anytime to refresh the map without touching hand-written content.
---

Read `${CLAUDE_PLUGIN_ROOT}/skills/init/SKILL.md` and follow its instructions exactly. The user provided this input: $ARGUMENTS

If `$ARGUMENTS` is empty, begin the init skill's flow.
