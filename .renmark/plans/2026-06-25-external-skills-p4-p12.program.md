---
artifact_type: program
schema_version: 1
created_at: 2026-06-25T00:00:00Z
source_sha: 9737336
related_plan: null
generator: opus
dependency_refs:
  - .renmark/research/2026-06-25-external-skills-study.research.md
completion_state: complete
confidence: medium
validation_status: validated
---

# Program — external-skills-study P4–P12 (the remaining 9)

Drive the 9 unshipped proposals from the external-skills study as a sequenced program.
Each stage = one `/renmark:feature`-equivalent (plan → orchestrate → verify → codereview),
advancing on success. Sequenced low-risk/high-value first; P7/P8/P10 are large and flagged.

**Autonomy legend:** 🟢 autonomous-ready (well-specced, mechanical/doc) · 🟡 needs a design
call I'll make + flag · 🔴 design-heavy, an autonomous one-shot is risky — recommend its own
brainstorm pass.

| # | Stage | Scope / files | Tier | Auto | Est tokens | Est $ |
|---|---|---|---|---|---|---|
| 1 | **P5** anti-re-dispatch ledger doctrine | `CLAUDE.md`/`AGENTS.md` rule-block + a resume/roadmap skip-list cross-check (ties to a known bug) | lite | 🟢 | ~15k | ~$0.10 |
| 2 | **P4** file-handoff helper scripts | new `bin/` or `renmark-execute` helpers (`task-brief PLAN N`, `review-package BASE HEAD` → write uniquely-named file, print path) + tests | standard | 🟢 | ~40k | ~$0.35 |
| 3 | **P12** feedback-loop-first debug gate | `debug` SKILL.md: add "reproduce with a real red command first" precondition to the Iron Law | lite | 🟢 | ~12k | ~$0.08 |
| 4 | **P11** persisted proactivity toggle | `.renmark/` config flag + read it in routing-preference; `setup`/`doctor` surface | standard | 🟡 | ~30k | ~$0.30 |
| 5 | **P6** two-verdict task review | `codereview` (+ maybe `verify`): score spec-compliance AND code-quality separately | standard | 🟡 | ~45k | ~$0.45 |
| 6 | **P9** router / decision-tree skill | new skill (or `help` enhancement): "idea → ship? on-ramp? standalone?" decision tree | standard | 🟡 | ~50k | ~$0.50 |
| 7 | **P10** headless-session contract | cross-cutting: detect headless/spawned, suppress `AskUserQuestion`, auto-pick recommended, prose-only return | full | 🔴 | ~80k | ~$0.90 |
| 8 | **P7** template-generated SKILL.md | build-time `.tmpl` + generator + regenerate all 27 SKILL.md/shims; drift-proofs P1/P2 | full | 🔴 | ~120k | ~$1.80 |
| 9 | **P8** behavioral skill testing + LLM-judge eval | new test harness: baseline-fail → skill → pass, under subagent pressure; cheap LLM-judge tier | full | 🔴 | ~120k | ~$1.80 |

**Totals (rough, incl. ~10k/agent overhead + per-stage verify+codereview):**
~510k tokens · **~$6–9** build spend (Claude/codex), wider if codex stays limited and bulk
emission reroutes to sonnet. Multi-hour autonomous run. Each stage commits on its own branch
and merges to main on clean verify+review.

**Sequencing rationale:** stages 1–3 are the study's recommended hygiene-hardening pass + a
cheap debug-gate win (fast, low-risk, build momentum). Stages 4–6 are moderate Tier-2/3 with
contained design calls. Stages 7–9 (🔴) are large: P10 changes pipeline behavior cross-cutting;
P7 restructures how all 27 SKILL.md are maintained (and must not regress the v0.20.0 trigger-only
+ disable-model-invocation frontmatter); P8 is a net-new harness. An autonomous one-shot on these
three risks mediocre output — **recommend running 7–9 as their own brainstorm-first features.**

**Gates preserved even in autonomous mode:** plan-validate + goal-backward verify run every
stage; merge/release stay human-gated (REQ-12); a HARD_STOP (verify fail, plan block, critical
review) pauses the program for a human/re-plan. codex usage-limit → reroute-to-sonnet (ledgered).
