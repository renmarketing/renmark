---
description: "Use when the user wants a visual blueprint of the project — typed as /renmark:blueprint or phrases like \"diagram this architecture\", \"draw the system\", \"show me a schematic\", \"mock up the UI\". Synthesizes a Container-granularity Mermaid architecture diagram (SCHEMATIC.md) and, when the build has a UI, a self-contained HTML/CSS mockup (PROTOTYPE.html). Reads architecture only from .renmark/memory/project-map.md; halts to /renmark:init when the map is missing or stale."
argument-hint: '[create | update | change description]'
---

Read `${CLAUDE_PLUGIN_ROOT}/skills/blueprint/SKILL.md` and follow its instructions exactly. The user provided this input: $ARGUMENTS

If `$ARGUMENTS` is empty, begin the blueprint skill's flow.
