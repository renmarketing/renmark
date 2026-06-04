# Plan — verify browser QA refinement (`--qa` / `--deep-qa`)

**Context.** Audit finding: `/renmark:verify --qa` and `--deep-qa` already perform
real browser validation via the Chrome DevTools MCP (navigate, click/fill,
`wait_for`, screenshots, console + network checks, hard/soft pass criteria),
already keep browser QA **opt-in** (default is shell smoke), and already degrade
to shell smoke when the browser MCP is unreachable. So this is NOT a "make QA use
a browser" build — it is the **smallest scoped refinement** that closes four real
gaps against the request, all inside the single file `plugin/skills/verify/SKILL.md`:

1. **When-to-use decision guide** — crisp "default smoke vs `--qa` vs `--deep-qa`"
   so browser QA is reached for at the right moment and stays opt-in / contextual.
2. **Visual/layout integrity** — add overlapping / clipped / broken-layout
   detection as an explicit QA + Deep QA criterion (the user's "interface
   overlaps" ask). Functional-only criteria don't tell the whole story.
3. **UI-change tracking** — before/after screenshot capture + agent-observed
   visual diff stored in the evidence dir, so UI changes/regressions are tracked.
4. **Stop/flag-on-break** — make "can't finish / hangs / layout broken → STOP and
   report" explicit and consistent, and ensure visual bugs are logged to `bugs.md`.

**Hard constraints (do not violate):**
- **Preserve existing non-browser QA behavior** — shell smoke (default mode) is
  untouched; the applicability gate (web project? browser MCP available?) and the
  degrade-to-shell fallback stay exactly as-is. Browser QA must NOT become the
  default for every run.
- **Context-hygiene contract is non-negotiable (G3/G5)** — screenshots, DOM trees,
  console/network dumps, and visual-diff data go to disk only; chat sees only the
  bounded ≤5-line verdict. New visual/diff evidence follows the same rule.
- **Keep frontmatter intact** — `name: verify` must still match the directory and
  `description:` must stay present and non-empty (enforced by `renmark.lint`).
- **No new mode/flag** — refine the existing `--qa` and `--deep-qa`; do not add a
  third browser flag. Smallest scoped change.

---

### Task 1: verify skill — browser QA refinement
- **mode:** B
- **target:** plugin/skills/verify/SKILL.md
- **complexity:** hard
- **executor:** opus
- **parallel_group:** 1
- **est_tokens:** 2500
- **est_cost_usd:** 0.19
- **verifier:** python -m renmark.lint && grep -q "When to use which mode" plugin/skills/verify/SKILL.md && grep -qi "overlapping interactive elements" plugin/skills/verify/SKILL.md && grep -qi "before/after" plugin/skills/verify/SKILL.md
- **spec:**
  Refine `plugin/skills/verify/SKILL.md` IN PLACE to close the four gaps below.
  This is a prompt/instruction (markdown) change to a Claude Code plugin skill —
  there is no runtime app to run. Make surgical insertions; preserve the file's
  existing structure, section order, headings, code blocks, and the three-mode
  model (Smoke default / `--qa` / `--deep-qa`). Do NOT rewrite sections wholesale.
  Keep the YAML frontmatter (`name: verify`, a non-empty `description:`) intact —
  you MAY lightly extend the description to mention visual/layout checks, but it
  must remain one line and non-empty.

  **(1) When-to-use decision guide.** Add a short new subsection titled exactly
  `### When to use which mode` (place it near the top — just after the Overview
  table or the "Mode selection" paragraph, whichever reads cleaner). Give a crisp,
  scannable guide for choosing among the three modes, e.g.:
    - **Default shell smoke** — the standing default after every orchestrate; use
      for non-UI work (CLI, data scripts, libraries, APIs) and as the fast
      first-pass gate. Browser QA is never automatic.
    - **`--qa`** — reach for it when the feature has a user-visible browser surface
      and you want to confirm it actually renders and the primary flow works live
      (not just that a shell command exits 0). Opt-in, one happy-path flow.
    - **`--deep-qa`** — prefer this for deeper runtime/visual edge-case validation:
      after `--qa` is green, when the change touches layout/UI, error paths, or
      risky inputs, and you want to know where it breaks under unusual-but-valid
      conditions. Gated on a passing `--qa` for the current sha.
    State the core principle plainly: code/shell tests prove a command exits 0, not
    that the user-visible result is correct — browser QA is what tells the whole
    story, so use it whenever there is a real UI surface and the cost is justified.
    Keep this section tight (a small table or a few bullets); do not bloat the file.

  **(2) Visual/layout integrity criterion.** In the `--qa` "Happy-path pass
  criteria" list, ADD a new HARD criterion for visual/layout integrity: the
  rendered UI must have no broken layout — specifically no overlapping interactive
  elements, no content clipped/cut off or pushed off-screen, no controls rendered
  on top of each other or outside their container, and no critical element hidden
  behind another. Describe how to detect it with the MCP tools already in use
  (`take_snapshot` for the accessibility tree + bounding boxes, `take_screenshot`
  for visual confirmation, optionally `evaluate_script` to read element rects /
  `getBoundingClientRect` to detect overlap or off-viewport positions). Make the
  verdict line able to name this criterion when it fails (e.g. "criterion: submit
  button overlaps the input — layout broken at <viewport>"). In Deep QA, strengthen
  the existing "no corrupt state / broken layout" hard criterion to call out
  overlapping/clipped interface elements explicitly with the same detection method.

  **(3) UI-change tracking (before/after visual diff).** Add instructions so QA
  captures a `before/after` screenshot pair around the main action (and Deep QA per
  edge case) and the agent compares them to surface visible UI changes/regressions.
  Use the literal phrase `before/after` so it's greppable. Store both images plus a
  short text note of observed differences in the existing evidence dir
  (`.renmark/reviews/qa/<feature>/` for QA; `.../deep/case-N/` for Deep QA) — e.g.
  `before.png` / `after.png` + a one-line diff note in the artifact body. This is
  agent-observed visual comparison (look at the two shots), NOT a new pixel-diff
  dependency. Reinforce the hygiene rule: the images and diff notes live on disk and
  in the artifact body only — NEVER inline a screenshot or paste raw diff data into
  chat; the verdict stays ≤5 lines.

  **(4) Stop/flag-on-break semantics.** Make the "stop and report" behavior
  explicit and consistent across `--qa` and `--deep-qa`: if the flow cannot finish —
  page fails to load, an action hangs (infinite spinner / never reaches the
  expected state within the bounded wait), the browser becomes unresponsive, an
  uncaught exception fires, or the layout is visibly broken (overlap/clipping) — the
  run STOPS at that step, marks the flow FAILED, names the failing step + criterion
  in the verdict, and does NOT silently continue or report success. Ensure such
  visual/layout and "could-not-finish" failures are logged to `bugs.md` via the
  existing `memory.log_bug` convergence loop with a reproducible finding (symptom +
  the offending criterion + screenshot path + repro steps), exactly like functional
  failures already are. Tie any early-exit into the existing bounded-verdict +
  artifact + learnings flow — do not invent a parallel reporting path.

  GUARD (from a CHANGELOG "Do not change" entry on this same file): the hand-off
  menu lines in this file use the numbered `N. [x] Label` format and reference
  bracket codes. Preserve BOTH the number AND the `[x]` bracket code on every menu
  line; do not alter the hand-off menu rendering or the dispatch-on-number-or-letter
  wording. Your edits target the QA criteria / evidence / when-to-use / stop-on-break
  content, NOT the menu blocks.

  After editing, the file must still pass `python -m renmark.lint` (frontmatter and
  command/skill pairing intact) and contain the EXACT anchor strings the verifier
  greps for (include them verbatim): the literal heading `When to use which mode`,
  the phrase `overlapping interactive elements` (in the visual/layout criterion),
  and the phrase `before/after` (in the UI-change-tracking instructions).

---

## Cost preview

| Task | Executor | Output + overhead | $/kT | Cost |
|---|---|---|---|---|
| 1. verify skill — browser QA refinement | opus | 2500 + 10000 = 12500 | $0.015 | $0.19 |

**Total: ~$0.19** (1 task, 1 parallel group, opus×1)
