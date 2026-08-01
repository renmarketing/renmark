# Bootstrap Authority Matrix

> **Revision note (2026-07-31, session continuation):** per `governing-methodology-addendum-01.md`, the target *runtime* role set is now 4 roles (General Contractor, Planner, Worker, Inspector) plus deterministic subsystems (Governor, Integrator, Ledger) — Architect and Engineer are now *modes of Planner*, not separate persistent agents. The role table below still lists the original 10-row breakdown from `governing-bootstrap-directive.md` because that document's *authority-order and prohibited-behavior rules* are unchanged by the addendum — only the runtime role *count* is revised. Read "Architect" below as "Planner in Architecture mode" and "Engineer" as "Planner in Milestone mode."

Temporary manual enforcement of the role model defined in `governing-bootstrap-directive.md` §1, until Renmark has native support for it (per governing-architecture-roadmap.md, Milestone 1).

## Roles active during Phase A / Phase B (this pass)

| Role | Who | Active this pass | May modify repository | May change architecture | May dispatch agents |
|---|---|---|---:|---:|---:|
| Owner | Roberto | Directs, will gate | No | Through change request | No |
| General Contractor | Primary Claude Code session (this session) | **Active** | Bootstrap dir only (see below) | No | Yes — read-only audit subagents only, this pass |
| Architect | Not yet invoked | Inactive | No | Yes | No |
| Engineer | Not yet invoked | Inactive | No | No | No |
| Worker | Not yet invoked | Inactive | N/A | No | No |
| Integrator | Not yet invoked | Inactive | N/A | No | No |
| Inspector | Not yet invoked | Inactive | No | No | No |
| Governor | Explicit written limits in this file + M-0 contract budgets | **Active (manual)** | N/A | N/A | N/A |
| Ledger | `ledger/events.jsonl` | **Active** | N/A | N/A | N/A |

## Authority order (governing-bootstrap-directive.md §2)

1. Direct instruction from Roberto.
2. The governing methodology document.
3. The active milestone contract.
4. Approved architectural decisions created during the refactor.
5. Repository tests and externally observable behavior.
6. Existing Renmark documentation.
7. Existing Renmark implementation behavior.
8. Model preferences or inferred best practices.

## This-pass boundaries (General Contractor)

**Permitted this pass:**
- Create `.bootstrap-renmark/` and its contents.
- Dispatch read-only research subagents (Explore-type; no write/edit tools) to inspect specific subsystems of the current Renmark repository, for the purpose of producing `current-system-audit.md`. These are descriptive audit helpers, not Workers under the target role model — they carry no authority to propose or make changes, and their outputs are synthesized by the General Contractor, not treated as approved findings on their own.
- Read `.renmark/` and repository files as passive reference (governing-architecture-roadmap.md §16, "Category A").
- Write only inside `.bootstrap-renmark/`.

**Prohibited this pass (governing-bootstrap-directive.md §3):**
- Modify any production code, `.renmark/` state, or plugin/skill files.
- Dispatch implementation Workers.
- Invoke `/renmark:feature`, `/renmark:orchestrate`, or any other `/renmark:*` pipeline command to govern or execute this refactor.
- Use existing Renmark memory as architectural truth.
- Generate the full Architect blueprint or Engineer milestone plan beyond Milestone 0.
- Continue past the end of this pass without an Owner gate.

## Bootstrap Governor limits applied this pass

Per governing-architecture-roadmap.md §9.2 defaults, scaled down for a read-only audit pass:

```yaml
bootstrap_limits_this_pass:
  active_milestones: 1   # M-0 (proposed only, not yet started)
  architect:
    initial_calls: 0     # not invoked this pass
  engineer:
    calls_per_milestone: 0   # not invoked this pass
  audit_subagents:
    maximum_parallel: 5
    read_only: true
    write_tools_allowed: false
  workers:
    maximum_parallel: 0
    nested_dispatches: 0
  inspectors:
    maximum_parallel: 0
  replanning:
    automatic_replans: 0
  scope:
    unrelated_cleanup: prohibited
    speculative_features: prohibited
    production_code_changes: prohibited
```

Any exception must be recorded in `ledger/events.jsonl` with reason, evidence, authority granting the exception, expected cost, expected outcome (governing-architecture-roadmap.md §9.2 closing rule).
