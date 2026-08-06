---
artifact_type: rethink-prd-acceptance-map
schema_version: 1
created_at: 2026-08-06
source_sha: da16469
related_plan: cross-host-native-tool-leverage
generator: sonnet
dependency_refs:
  - PRD.md
  - renmark/task_tracking.py
  - renmark/context.py
  - renmark/cost.py
  - renmark/dispatch.py
  - plugin/skills/.shared/task-tracking.md
completion_state: complete
confidence: medium
validation_status: validated
retry_count: 0
parser_success: true
schema_compliance: true
---

# PRD Acceptance Map — cross-host native-tool leverage

Stage 3 (PRD acceptance contract) for `/renmark:rethink` topic
"cross-host native-tool leverage."

## Requirement map

| Requirement | Current implementation | Evidence | Compliance | Native-tool-leverage impact |
|---|---|---|---|---|
| REQ-2 (cost-appropriate routing, Haiku/Codex/Sonnet/Opus/Fable) | `renmark/cost.py` — `_AGENT_EXECUTORS`, `_EXPENSIVE_EXECUTORS`, `_DETERMINISTIC_EXECUTORS`, `requires_escalation()` | `cost.py:97-107,399` define the routed executor set and escalation gate | met | Neutral-to-advance: leaning on host-native tools (e.g. Claude's own Task tools) doesn't change model routing, but any new host-native capability must still route through the same executor set, not bypass it |
| REQ-5 (context hygiene / metadata-only dispatch) | `renmark/context.py::assert_metadata_only`, `renmark/dispatch.py::build_subagent_input` | `context.py:333-345` rejects non-bare skill refs; `dispatch.py:885` builds packets | met | Advances if done right: native task tools (TaskCreate/TaskUpdate) carry only bounded title/status fields by design, which is naturally REQ-5-shaped; risk is scope creep if someone starts mirroring transcript content into task bodies |
| REQ-20 (context taxonomy: static/dynamic/memory/task-local) | `renmark/context.py` (`ContextKind`, `load_skill_body`, `load_fragment`) | `context.py:325-330` | met | Neutral — native-tool leverage doesn't add a new context kind, just a new task-local artifact (the native task record) |
| REQ-23 (Claude Code / Codex host parity) | `plugin/skills/.shared/` selector contracts; no single Python file — host parity is a skill-instruction + fixture contract | PRD.md:268-300 (selector-capable contract, Plan-mode vs Default-mode); no equivalent code module found for task-tool parity specifically | partial | Directly threatened: REQ-23 requires host adapters that "translate interaction... without forking lifecycle... semantics," but REQ-31 already documents (see below) that Claude and Codex do NOT have equivalent native task-tracking surfaces — deeper native-tool leverage on Claude Code risks widening, not narrowing, that gap unless deliberately designed for parity or explicitly scoped as a Claude-only enhancement |
| REQ-30 (orchestration efficiency is a protected capability) | `.renmark/memory/orchestration-baseline.md`; regression-protection clause in PRD.md:634-650 | Baseline `ORCHESTRATION-BASELINE-2026-08` (v0.39.7, commit d9cccc5) | met (baseline recorded) | Directly governs this topic: REQ-30(i) requires an explicit PRD change + Owner approval before altering dispatch policy, Owner-gate frequency, or orchestration routing — any expansion of native-tool leverage (e.g. new host tool calls per dispatch, new gate types) is itself a REQ-30-regulated change, not a free-standing feature |
| REQ-31 (native task tracking, two non-substitutable mechanisms) | `renmark/task_tracking.py` (mechanism ii, headless-only); `plugin/skills/.shared/task-tracking.md` (mechanism i, skill-instruction only, no Python) | `task_tracking.py:98-138` (Status enum, `complete_worker_task` self-approval guard); `task-tracking.md:17-38` (mechanism split) | partial | This IS the topic's core object: REQ-31 mechanism (i) is written as "the live host's own native Task tools (Claude Code's TaskCreate/TaskUpdate/TaskList/TaskGet)" with "(or equivalent host)" language for Codex, but no Codex-native equivalent is named, implemented, or evidenced anywhere in the repo (see Flagged issues) |

## Flagged issues

1. **REQ-31 mechanism (i) has no confirmed Codex equivalent — directly material to this topic.**
   `plugin/skills/.shared/task-tracking.md` (lines 17-30) and PRD.md:689-703 both hedge with
   "Claude Code (or equivalent host)" but never name what Codex's task-tool equivalent actually
   is. A repo-wide grep for Codex-side task/plan-tracking primitives
   (`update_plan`, Codex-native TaskCreate, etc.) found nothing — `renmark/codex_routing.py`
   only resolves model/effort settings, not task-tool routing. PRD.md:727-730 is explicit that
   "graceful degradation... never [applies] to an interactive session where the native tools are
   simply present in the tool palette" — but for an interactive Codex session, it is unclear
   whether native task tools are ever present in the palette at all, as opposed to genuinely
   absent. As written, REQ-31 mechanism (i) is **untestable for interactive Codex** — there's no
   stated fixture or acceptance evidence (the REQ-31 acceptance block, PRD.md:736-762, cites only
   Claude Code TaskCreate/TaskUpdate transcripts and the one Python-mirrored headless path).
   This is precisely the ambiguity this transformation topic (cross-host native-tool leverage)
   would either have to resolve or explicitly scope around.

2. **REQ-23 host-parity contract does not yet enumerate task-tracking as a parity dimension.**
   REQ-23's acceptance criteria (PRD.md:299-308) list selector/menu parity fixtures but never
   mention task-tool parity. REQ-31 was added later (2026-08-02, per revision notes at
   PRD.md:1148 and 1193) without an amendment to REQ-23's own scope list. This is a
   spec-consistency gap, not a contradiction — REQ-31 already carves out the Codex headless
   path explicitly — but the interactive-Codex case sits in neither requirement's stated
   acceptance criteria.

3. **Non-goals check.** The "No third-party runtime dependencies in the core" non-goal
   (PRD.md:88-91) constrains the *core Python runtime* only; it explicitly allows opt-in
   capability layers (Codex CLI, Playwright). Leaning harder on host-native tools (Claude's
   Task tools, Codex's own tool surface) does not conflict with this non-goal, since those are
   host-provided interaction surfaces, not third-party runtime dependencies bundled into
   renmark's own package — consistent with the Vision's "Claude Code and Codex are first-class
   hosts... not separate product forks" framing and the "Not a standalone app" non-goal
   (PRD.md:81-83), which explicitly endorses using host-provided interaction surfaces.

## Blocking vs deferrable

- **Blocking:** none found. No requirement outright forbids increasing native-tool leverage;
  REQ-30 and REQ-5 constrain *how* (bounded, no new Owner gates, no context bloat), and REQ-31
  already anticipates and scopes the Codex gap rather than silently assuming parity.
- **Deferrable (worth recording, not gating):**
  - REQ-31's Codex-equivalent for mechanism (i) is unresolved (issue 1) — the transformation
    topic should decide, and record as a PRD amendment if the decision changes REQ-31's scope,
    whether interactive Codex sessions (a) get a real equivalent mechanism, (b) are formally
    exempted with a stated reason, or (c) fall back to mechanism (ii)'s pattern even though
    REQ-31 currently reserves (ii) for the headless path only.
  - REQ-23's acceptance criteria should eventually enumerate task-tracking parity explicitly
    (issue 2) — cosmetic/spec-hygiene, not a blocker.

**FLAGGED FOR EXCEPTION CHECK-IN:** issue 1 (REQ-31 mechanism (i) has no confirmed Codex
equivalent) is a real ambiguity in Owner intent, not something this research pass should resolve
silently — if the transformation topic's design would extend, redefine, or bypass REQ-31's
two-mechanism split for Codex, that is a scope/intent question for the Owner, not an
implementation detail.

---

## Exception check-in — decision (2026-08-06)

**Finding:** REQ-31 ("every dispatched unit of work is visible as a native
host task with an honest lifecycle") has no confirmed Codex-native
equivalent to Claude Code's TaskCreate/TaskUpdate. `renmark/task_tracking.py`
exists specifically as the Codex/subprocess-path substitute, not a mirror of
something native that already exists there. Stage 4's external research
(2026-08-06 access date) confirms Codex's plugin API shows no equivalent
task-visibility primitive as of its research date.

**Owner decision:** REQ-31 means "visible via whatever mechanism fits the
host" — Claude gets native Task-tool visibility, Codex gets renmark's own
`task_tracking.py` bookkeeping (evidence requirements, self-approval guard,
honest lifecycle). Both are honest, both are visible to someone (the user via
Claude's UI, the operator via renmark's own state files on Codex). REQ-31 is
**already met** under this reading. PRD.md's REQ-31 wording will be amended
to state this explicitly (routed to `/renmark:prd`'s UPDATE gate) so this
ambiguity does not recur in a future rethink pass.

Compliance status for REQ-31 updates from `partial` to `met` under this
Owner-confirmed reading.
