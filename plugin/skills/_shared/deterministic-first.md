# Deterministic-First Execution — Reference (single source of truth)

**Shared by `/renmark:orchestrate`, `/renmark:finish`, `/renmark:feature`, `/renmark:debug`, and any skill that dispatches tasks or verifies state.** This is the one place the rules for preferring deterministic checks before AI/model calls live: a 4-question gate, a routing matrix, and a catalog of deterministic task types. Operationalizes cost discipline (REQ-19) and deterministic-first principle (REQ-21).

---

## The deterministic-first principle

Before dispatching a task to any model (Haiku, Sonnet, Opus, Fable) or a subagent, **check whether a deterministic tool, script, or file check can answer the question first**. Deterministic means: no model call, no ambiguity, repeatable, fast, and cheap. This rule is not "never use AI" — it's "exhaust the cheap, sure path before the expensive, probabilistic one."

Examples of deterministic checks:
- **Git / worktree state:** branch name, merge status, stale detection, diff size, clean-tree validation, merged-to-main check, cleanup readiness.
- **Artifact existence & integrity:** PRD frontmatter validation, plan lint, spec schema compliance, artifact metadata presence.
- **Package / release checks:** version reads, zip/archive creation, install verification, changelog structure, tag existence.
- **File sync checks:** mirror validation (CLAUDE.md ≡ AGENTS.md byte-to-byte), skill registry sync, test command consistency.
- **Execution baseline:** test/lint/typecheck runs, exit code validation, test count comparisons (regression guards).

**Do NOT use AI for these tasks.** Use `renmark/worktree.py`, direct git commands, file parsing, `ast` module, regex, checksum comparisons, or simple shell scripts.

---

## The 4-question gate (in order)

Before dispatching ANY task — deterministic verification, interpretation, or ambiguity-resolution — ask these four questions:

1. **Can existing state, files, git, grep, or a parser answer this?**  
   Examples: Is the tree clean? (`git status`), Does the file exist? (`os.path.exists`), What version is declared? (read + regex), Do these files match byte-for-byte? (`diff`, `hashlib`). → **Use deterministic checks immediately.**

2. **Can a deterministic script/check do it reliably?**  
   Examples: Validate schema, count tests before/after, check git merge status, compute token estimate, verify artifact metadata, lint a plan. → **Write a deterministic validator; no model call.**

3. **Is this repeated enough to deserve a reusable check?**  
   If the same validation appears in 2+ skills or tasks, extract it to a shared module (`renmark/worktree.py`, `renmark/lint.py`, `renmark/plan_lint.py`). → **Invest in reusable infrastructure.**

4. **Is AI actually needed for judgment, synthesis, or ambiguous reasoning?**  
   Only if questions 1-3 cannot close the task: the task requires judgment (which branch strategy is safer?), synthesis (is this design coherent across files?), or resolving ambiguity (did the user intend X or Y?). → **Route to model only here.**

---

## Deterministic routing matrix (task type → tool/method)

| Task | Deterministic check | When to stop | When to escalate to AI |
|---|---|---|---|
| Git/worktree lifecycle | `renmark/worktree.py` checks + git commands | State is readable (branch, merge, stale, clean-tree) | Ambiguous merge conflict history / release-readiness judgment |
| Artifact existence & metadata | Direct file read + schema validator | Frontmatter present, all required fields present | Validity judgment (is the content sound?) |
| Version / release readiness | Read version file + semantic-version parser | Version matches tag / changelog / code | Judgment: safe to release given context? |
| Plan/spec lint | Schema validator + cross-reference checker | Plan structure is valid, task indices consistent, no duplicates | Judgment: is the plan sound strategically? |
| Mirror validation (CLAUDE.md ↔ AGENTS.md) | Byte-for-byte diff (or hash comparison) | Blocks are identical | Never — diff is proof. If not identical, halt. |
| Skill registry sync | Parse plugin/ metadata, compare against registry | All declared skills present and registered | Never — regex/parse is sufficient. |
| Test/lint/typecheck baseline | Run verifier command, count results | Exit codes + test counts (before/after) | Judgment: does regression warrant a rerun or revert? |
| Package / zip creation | File listing, byte count, archive integrity checks | File present, size sane, unpacks correctly | Never for creation. For safety (should we ship?) → AI. |

---

## Worktree deterministic checks

Worktree lifecycle (branch, stale detection, divergence, diff size, clean tree, merged-check, cleanup) are **deterministic via git** — see `renmark/worktree.py` for the shared module. AI is invoked **only for**:
- Ambiguous merge-conflict judgment (which resolution is semantically safer?).
- Complex branch history reasoning (should we rebase or merge?).
- Risk/release-readiness framing (explain why this branch is risky/ready).

All other worktree checks: deterministic git. Cross-ref `renmark/finish_lanes.py` (which calls `renmark/worktree.py` before gating finish lanes).

---

## Cost preview labeling

In `renmark/cost.py`, the `estimate_cost` function labels each task as **deterministic** or **model-driven**:
- **Deterministic:** Haiku call → $0 marginal (no new model cost); Codex subprocess → charged per task.
- **Model-driven:** Sonnet/Opus/Fable Agent calls → charged per model and token count.

Cost preview MUST expose this labeling so users see which tasks are cheap (deterministic checks) vs. expensive (model-heavy).

---

## Examples of deterministic-first in action

**Example 1: Verify merge readiness (finish lane)**  
Q1: Can git tell us the state? → Yes, `git merge-base --is-ancestor main HEAD`.  
Q2: Can a script validate the diff size? → Yes, `git diff main --stat | wc -l`.  
Q3: Reusable? → Yes, in `renmark/worktree.py::merged_to_main()`.  
→ **Stop. No AI needed.** Only escalate to Sonnet/Fable if the user asks "is this safe to release?" — that's judgment.

**Example 2: Validate plan structure**  
Q1: Can a parser check task indices? → Yes, regex + unique-set validation.  
Q2: Can a linter validate schema? → Yes, `renmark/lint.py`.  
Q3: Reusable? → Yes, in `plugin/skills/orchestrate.py::lint_plan()`.  
→ **Stop. No AI needed.** Only escalate if user asks "is this plan strategically sound?" — that's judgment.

**Example 3: Release-readiness checklist**  
Q1: Can we check changelog, version tag, test count, artifact existence? → Yes, all deterministic.  
Q2: Can a script compose a checklist? → Yes, `renmark/state.py::release_readiness_items()`.  
Q3: Reusable? → Yes, across finish lanes.  
→ **Stop. No AI needed.** Fable only if user asks "should we release given all this context?" — judgment + synthesis.

---

## Why a shared file

Early drafts of renmark routed many cheap, deterministic tasks to models: "is the tree clean?" → Haiku; "does the file exist?" → Sonnet. Each skill made its own judgment about what warranted a model call. Centralizing here means:

- One decision framework. The 4-question gate is defined once; every skill uses the same rubric.
- Fast escalation path. When model-based reasoning is needed, every skill knows the routable task types.
- Cost transparency. Users see which tasks are deterministic (free or cheap) vs. model-heavy (expensive).
- Infrastructure investment. Repeated deterministic checks are extracted to `renmark/worktree.py`, `renmark/lint.py`, `renmark/plan_lint.py` — shared, maintainable, auditable.

When citing this discipline in a SKILL.md or subagent dispatch, write:

> *Honor deterministic-first discipline in `${CLAUDE_PLUGIN_ROOT}/skills/_shared/deterministic-first.md`: before any task dispatch or model call, answer the 4-question gate (existing state? script? reusable? AI-needed?). Deterministic checks: git/worktree state, artifact existence/metadata, version/release readiness, plan lint, mirror validation, test baseline. Route judgment-heavy tasks (merge risk, release-readiness reasoning, branch strategy) only to model-based agents. See `renmark/worktree.py` for shared checks.*

Do not paste the gate or matrix into the calling SKILL.md — cite this file.

## Enforcement (not just advice)

The subagent side of this gate is now **enforced deterministically** by
`renmark/subagent_gate.py` (zero-LLM). Before dispatching a plan, run it like
`plan_lint`:

```bash
python -m renmark.subagent_gate <plan.md>   # exit 0 = clean, 1 = challenged, 2 = usage
```

It answers the 4 questions mechanically per task (`justify_task`) and rolls the
plan up (`challenge_plan`): deterministic-eligible tasks, inline-able simple
tasks, and unexplained `general-purpose` spawns are flagged BEFORE tokens flow.
The cost preview surfaces `subagent_gate.preview_line(...)`. This turns REQ-21's
"prefer deterministic / challenge subagents" from a rule the orchestrator is
asked to follow into a check it must run.
