---
artifact_type: external-benchmark
schema_version: 1
created_at: 2026-08-04T00:00:00Z
source_sha: e6898917ddf3a30505bb01b1b0569c28a187d792
related_plan: governed-orchestration-assurance
generator: sonnet
stale_after: 2026-11-04T00:00:00Z
dependency_refs: []
---

# External Discovery & Benchmarking — governed-orchestration-assurance

Stage 4 of `/renmark:rethink`. External research only (WebSearch), conducted
2026-08-04. Scope: the 7 topics in the Owner's proposed "software-engineering
control plane" evolution of renmark. All findings below come from live web
search on 2026-08-04; no claim here is drawn from model memory alone.

Access date for all sources: **2026-08-04** (via WebSearch tool).

---

## Tier 1 — Verified external facts (sourced, checkable)

### 1. Structured work-order / task-contract schemas
- **F1.1** Production multi-agent systems in 2026 converge on a "deterministic
  backbone that orchestrates the flow, with LLM intelligence deployed only at
  specific steps" — Anthropic engineering guidance, per aggregation in
  [LLM Orchestration in 2026: Top 22 frameworks](https://aimultiple.com/llm-orchestration)
  and [Multi-Agent Orchestration Patterns for Production](https://beam.ai/agentic-insights/multi-agent-orchestration-patterns-production).
  Evidence strength: **medium** (secondary aggregation of vendor guidance, not
  a primary spec). Applicability: **high** — this is exactly renmark's existing
  shape (deterministic dispatch/verify loop + bounded LLM calls); it validates
  the current architecture rather than demanding a new one.
- **F1.2** Explicit **stage-boundary validation gates** that check LLM output
  schema/contents before forwarding to the next pipeline stage are called out
  as the differentiator between systems that fail from "undefined multi-agent
  contracts" and ones that don't (same source set). Evidence strength:
  medium. Applicability: high — directly supports the proposed
  DispatchReceipt/InspectionReceipt/ReleaseReceipt chain; each receipt is a
  gate-boundary validation artifact.
- **Limitation**: no primary named open standard (no "typed task contract"
  RFC/schema equivalent to, say, OpenAPI) was found for LLM agent dispatch.
  The field describes the *pattern* qualitatively, not a canonical schema
  renmark could adopt wholesale.

### 2. Capability-scoped / sandboxed execution — pre- vs post-action
- **F2.1** Claude Code's own security model is **pre-action enforcement via
  blocking hooks** (`PreToolUse` fires and is awaited before a tool executes;
  the policy decision gates the call) **plus OS-level sandboxing** as a second,
  independent layer — "permissions stop Claude from trying something, and
  sandboxing stops the attempt from succeeding if [it] tries anyway." Source:
  [Claude Code Hooks Complete Guide](https://hidekazu-konishi.com/entry/claude_code_hooks_complete_guide.html),
  [Claude Code Security Guide (DataCamp)](https://www.datacamp.com/tutorial/claude-code-security),
  [Claude Code Permissions Explained](https://www.datastudios.org/post/claude-code-permissions-explained-safe-command-execution-project-controls-sandboxing-hooks-and).
  Evidence strength: **high** (converges across 3 independent write-ups
  describing the same shipped, documented behavior of the tool renmark itself
  runs on). Applicability: **very high** — renmark is a Claude Code plugin;
  this is the enforcement substrate already available to it, not a future
  bet.
- **F2.2** A named 2026 primary-source paper, [Before the Tool Call:
  Deterministic Pre-Action Authorization for Autonomous AI Agents](https://arxiv.org/pdf/2603.20953),
  argues explicitly for deterministic pre-action authorization over
  prompt-only or post-hoc guardrails. Evidence strength: medium (single
  arXiv paper, not yet independently replicated per this search).
  Applicability: high — directly underwrites the Owner's proposed
  "pre-action + post-action enforcement" pairing; the paper's framing
  suggests pre-action is the load-bearing layer and post-action is a
  secondary catch, which should shape where renmark invests engineering
  effort first.
- **F2.3** A second 2026 paper, [Don't Let AI Agents YOLO Your Files](https://arxiv.org/pdf/2604.13536),
  argues for pushing authority checks to the filesystem/OS layer rather than
  trusting the agent's own self-restraint — reinforces defense-in-depth over
  single-layer trust. Evidence strength: medium. Applicability: high for the
  "role capability envelope" proposal — argues envelopes should be enforced
  at the tool/OS boundary (matching Claude Code's actual permission system),
  not merely encoded as instructions in a dispatch packet.
- **Limitation**: Codex sandboxing specifics were not directly retrieved in
  this pass (search focused on Claude Code); renmark already runs both hosts,
  so Codex's actual enforcement mechanism (prompt-only vs. OS-level) is an
  **open unknown** (see Unknowns).

### 3. LLM-as-judge calibration
- **F3.1** Position bias is empirically real and NOT fixed by prompting:
  "instructing judges to avoid position bias through rubric lines has
  roughly zero measured effect, as the bias is in the autoregressive decode,
  not the prompt." Mitigation requires structural randomization — run every
  pairwise comparison in both orderings and treat order-flip verdicts as
  ties/uncertain. Source: [Judging the Judges: Systematic Evaluation of Bias
  Mitigation Strategies in LLM-as-Judge Pipelines](https://arxiv.org/pdf/2604.23178),
  aggregated via [LLM-Judge Bias Mitigation 2026](https://futureagi.com/blog/evaluating-llm-judge-bias-mitigation-2026/).
  Evidence strength: **high** (primary arXiv empirical study + independent
  practitioner aggregation agree). Applicability: **very high** — directly
  actionable for renmark's proposed "three-state verdict (pass/fail/
  uncertain)" judge: order-flip-driven disagreement should route to
  `uncertain`, not be silently resolved.
- **F3.2** Three properties define a production-ready judge: **reproducibility**
  (same input → same score within tolerance), **calibration** (correlates
  with a human-labeled gold set), and **bias control** (position, verbosity,
  self-preference/family bias measured and mitigated). Recommended gold set
  size: 100-300 cases for bias calibration, 200 hand-labeled traces for
  general calibration, tracked via Cohen's kappa, re-checked periodically.
  Source: [LLM-as-Judge Best Practices in 2026](https://futureagi.com/blog/llm-as-judge-best-practices-2026),
  [futureagi.com LLM-as-a-Judge 2026](https://futureagi.com/blog/llm-as-a-judge/).
  Evidence strength: medium-high (consistent practitioner consensus, not a
  single controlled trial). Applicability: high, with a caveat — a
  100-300-case gold set is a meaningfully large one-time investment for a
  single-Owner CLI tool; renmark's "calibrated blind judge" should size the
  gold set to its actual dispatch volume, not import the SaaS-scale number
  uncritically (see Recommendations).
- **F3.3** Verbosity bias (longer answers preferred independent of quality)
  and self-preference bias (a model favors outputs resembling its own style)
  are named as the other two dominant, well-replicated bias types, mitigated
  respectively by length-normalization and cross-family judging. Source:
  same as F3.1/F3.2. Evidence strength: high. Applicability: high — supports
  the Owner's "input isolation" and "bias controls" requirements concretely:
  isolate/redact length signals and prefer a judge model from a different
  family than the worker that produced the artifact, where feasible.
- **Limitation**: all sources found are 2026 blog/aggregator secondary
  sources plus arXiv preprints — none is a peer-reviewed, widely-cited
  landmark paper; treat magnitude claims (e.g., "5% flip rate threshold") as
  indicative, not calibrated truth, until renmark runs its own flip-rate
  measurement.

### 4. Falsification-lens vs. indiscriminate persona debate
- **F4.1** A named methodology, **"Refute-or-Promote"**, uses a critic with
  an explicit **kill mandate** (empowered to reject, not just critique) rather
  than an "improve/evaluate" mandate, and pairs it with **cross-family
  reviewers** specifically to catch shared-prior blind spots (i.e., same-
  family reviewers share the same blind spots as the author). Source:
  [Refute-or-Promote: An Adversarial Stage-Gated Multi-Agent Review
  Methodology for High-Precision LLM-Assisted Defect Discovery](https://arxiv.org/pdf/2604.19049).
  Evidence strength: medium (single arXiv paper with reported benchmark
  results, not independently replicated). Applicability: **high** — this is
  close to a direct precedent for "selected falsification lenses (not
  indiscriminate multi-persona debate)": the paper's core claim is that a
  narrow, empowered critic beats a broad debate panel.
- **F4.2** A second methodology, **"Adversarial Review"** (structured
  disagreement between two models), reportedly "achieves the highest pass
  rate among tested methods on LiveCodeBench, outperforming a six-agent
  baseline" — i.e., a smaller structured-disagreement setup beat a larger
  unstructured multi-agent panel on a concrete benchmark. Source:
  [OpenReview: Adversarial Review — Cooperative Code Review through
  Structured Disagreement](https://openreview.net/forum?id=fOHvpLs6zp).
  Evidence strength: medium (peer-reviewed venue submission, but a single
  benchmark). Applicability: high — direct evidence FOR the Owner's stated
  preference (selected lenses over indiscriminate debate) and against
  scaling review by adding more personas.
- **F4.3** Countervailing finding: naive (unstructured) multi-agent debate
  can *diminish* accuracy rather than improve it — the effect is
  structure-dependent, not agent-count-dependent. Source:
  [Can LLM Agents Really Debate? A Controlled Study of Multi-Agent Debate in
  Logical Reasoning](https://arxiv.org/pdf/2511.07784). Evidence strength:
  medium-high (controlled study). Applicability: high — reinforces that
  renmark should NOT read "more inspection lenses = more safety" as true by
  default; lens *selection logic* (risk-tiered, task-scoped) is the
  load-bearing design choice, matching the Owner's stated intent.
- **F4.4** "Council mode spawns disposable lenses — not permanent personas,
  but task-scoped perspectives selected based on what could break" is
  described as an emerging pattern name for exactly the risk-tiered,
  non-fixed-roster selection renmark is proposing. Source:
  [Cross-Model Adversarial Review blog](https://codex.danielvaughan.com/2026/03/28/cross-model-adversarial-review/).
  Evidence strength: low-medium (single blog, not an academic source).
  Applicability: medium — useful vocabulary/precedent, not strong proof.

### 5. Failure-derived constraint registries
- **F5.1** A named anti-pattern: constraints "folded into reward functions
  as large negative shaping terms" — i.e., constraint accumulation without
  bound is called out explicitly as a governance failure mode in the SARC
  framework. Source: [SARC: A Governance-by-Architecture Framework for
  Agentic AI Systems](https://arxiv.org/pdf/2605.07728). Evidence strength:
  medium (single framework paper). Applicability: high — directly validates
  the Owner's stated worry ("not a growing global prohibition list").
- **F5.2** "Deterministic Constraint Systems" pattern: scope restriction
  enforced **in code** (a tool registry), not in the system prompt — "the
  registry enforcing scope is a hard constraint that cannot be overridden by
  the model's reasoning." Source: [Deterministic Constraint Systems: Building
  Tool Registries That Keep Agents in Scope](https://ranjankumar.in/harness-engineering-deterministic-constraint-systems-tool-registry-agents).
  Evidence strength: low-medium (practitioner blog, not peer-reviewed).
  Applicability: high — this matches renmark's existing
  `deterministic-first.md` philosophy; reinforces putting constraint
  enforcement in `renmark/*.py` gates rather than in prose rules appended to
  CLAUDE.md/AGENTS.md indefinitely.
- **F5.3** "Multi-Agent Constitution Learning" (MAC) proposes a **Creator
  agent** whose specific job is to propose new constitutional rules "grounded
  in observed failure patterns," i.e., a designed mechanism for rules to
  originate FROM failures rather than from anticipatory brainstorming.
  Source: [MAC: Multi-Agent Constitution Learning](https://arxiv.org/pdf/2603.15968).
  Evidence strength: medium (single arXiv paper). Applicability: high —
  close structural precedent for the proposed "failure-derived constraint
  registry": a rule proposal step gated on a real observed failure, distinct
  from a free-form "add another CLAUDE.md line" habit.
- **F5.4** Named failure mode: "constraint drift" — safety-critical
  conditions "stop functioning as operative constraints" as agents
  coordinate/delegate/optimize over time, i.e., constraints decay in
  practice even when nominally still present. Source: [Safe Multi-Agent
  Behavior Must Be Maintained, Not Merely Asserted: Constraint Drift in
  LLM-Based Multi-Agent Systems](https://arxiv.org/pdf/2605.10481). Evidence
  strength: medium. Applicability: medium-high — argues a constraint
  registry needs periodic re-verification (not just creation), which is not
  currently an explicit stage in the Owner's proposal as summarized.

### 6. Durable event-sourcing / append-only ledgers without heavyweight infra
- **F6.1** General event-sourcing principle confirmed across multiple
  sources: "data stored as a sequence of immutable events in an append-only
  log," with **git itself cited as a real-world example of an event-sourced
  system** (commits = sequential immutable events). Source: aggregation
  incl. [Event Sourcing Pattern — Microsoft Learn](https://learn.microsoft.com/en-us/azure/architecture/patterns/event-sourcing),
  general search results. Evidence strength: high for the general pattern
  (canonical, well-established architecture pattern with decades of
  precedent), but **no source found describing a lightweight, database-free,
  single-user CLI implementation matching renmark's actual constraints** —
  virtually all retrieved material assumes a service/microservice context
  with a message broker or event store.
- **Limitation (important)**: this sub-topic returned the **weakest**
  evidence of the seven. No primary source was found benchmarking or
  describing a JSONL-file-backed, single-process, single-user append-only
  ledger pattern equivalent to what renmark already does
  (`.renmark/state/lifecycle.json` + wave-summaries). The git-as-event-log
  analogy is real but generic. Treat renmark's existing approach as
  reasonable-by-precedent (git itself does this) rather than as validated
  against a named comparable tool.

### 7. Known failure modes in comparable AI-SDLC/agent-governance rollouts
- **F7.1** "43% of AI-suggested code changes still require manual debugging
  in production even after passing QA and staging" — cited from the
  "Lightrun State of AI-Powered Engineering 2026" report. Source:
  [Lightrun: SDLC Phases and the Reliability Gap AI Can't Close](https://lightrun.com/blog/sdlc-phases/).
  Evidence strength: medium (single vendor-report statistic, not
  independently replicated in this pass — vendor reports have a
  self-interest bias toward alarming numbers that justify their product).
  Applicability: medium — supports investing in verification, but the
  number itself should not be treated as calibrated for renmark's context
  (bounded coding tasks with inspection receipts, not unconstrained
  generation).
- **F7.2** Named governance principle: **"designed autonomy"** — automate
  what's repeatable, govern what's risky, preserve human judgment where
  accountability matters; explicitly NOT "full autonomy everywhere." Source:
  [Augment Code: AI SDLC Maturity Model](https://www.augmentcode.com/guides/ai-sdlc-maturity-model),
  [Lightrun](https://lightrun.com/blog/sdlc-phases/). Evidence strength:
  medium (consistent theme across vendor content, not academically
  measured). Applicability: high — validates renmark's existing
  Pause-Policy/gate design philosophy in principle, but doesn't specify
  *where* the risk/repeatable line falls — that's a judgment call renmark
  already makes via its gate list, not something external research resolves.
- **Limitation**: no source in this search pass specifically documented a
  **failed or rolled-back** agent-governance deployment with concrete
  post-mortem detail (the "migration lessons" the Owner asked about). All
  retrieved material is prescriptive/forward-looking ("do this to avoid
  failure") rather than a retrospective on an actual governance rollout that
  went wrong. This is a genuine gap — flagged in Unknowns.

---

## Tier 2 — Inferences (reasoned, not directly sourced)

- **I1.** Because Claude Code's own hook system is already pre-action/
  blocking (F2.1) and renmark runs as a Claude Code plugin, the "role
  capability envelope pre-action enforcement" the Owner wants is likely
  achievable largely by **wiring renmark's role model into existing
  `PreToolUse` hooks and permission settings**, rather than building a novel
  enforcement layer from scratch. This is an inference, not confirmed by any
  source describing renmark specifically.
- **I2.** The consistent cross-topic theme — deterministic backbone (F1.1),
  deterministic tool registries (F5.2), pre-action enforcement (F2.1-F2.3),
  structural (not prompted) bias mitigation (F3.1) — suggests the field's
  2025-2026 consensus is "push governance into code/architecture, not
  prose/instructions." This directly matches renmark's own stated
  `deterministic-first.md` philosophy already in CLAUDE.md; the external
  research is confirmatory of the existing direction rather than
  contradictory.
- **I3.** No source distinguishes CLI/single-user tools from multi-tenant
  SaaS in any of the 7 topics — nearly all retrieved material implicitly
  assumes a service context (API-served agents, enterprise fleets). This
  means renmark cannot safely import numeric thresholds (gold-set sizes,
  bias flip-rate cutoffs, kappa targets) without rescaling them down for a
  single-Owner, low-volume dispatch context — importing SaaS-scale
  calibration overhead (e.g., a 200-case hand-labeled gold set) could itself
  become the "over-engineering" failure mode the research warns about (F7.2).
- **I4.** The Refute-or-Promote/Adversarial Review results (F4.1, F4.2)
  outperforming larger panels is evidence *for* the Owner's instinct
  (selected lenses over indiscriminate debate), but both are benchmarked on
  code-defect-finding tasks, not architecture/release-readiness review —
  applicability to renmark's non-code review surfaces (e.g., release
  readiness, plan review) is inferred by analogy, not directly evidenced.

---

## Tier 3 — Recommendations

1. **Treat pre-action enforcement as primarily a wiring problem, not a build
   problem.** Map the proposed role capability envelopes onto Claude Code's
   existing `PreToolUse` hook + permissions + sandboxing stack (F2.1) before
   designing new enforcement machinery. Spike: can a role's envelope be
   expressed as a hook-time allow/deny check against dispatch-packet
   metadata already carried per `context-taxonomy.md`?
2. **Size the judge calibration gold-set to renmark's real dispatch volume**,
   not the SaaS-scale numbers in F3.2 (100-300 / 200 cases). Start with the
   smallest set that gives a stable Cohen's kappa reading (likely 20-40
   renmark-specific cases given its actual task volume), and treat 100-300
   as an upper bound only if judge disagreement rate justifies it. Re-run
   F7.2's "designed autonomy" filter on this decision explicitly.
3. **Implement position-bias mitigation structurally, not via prompt
   instructions** (F3.1 — prompting has ~zero measured effect). If judge
   pairwise comparisons are ever used, run both orderings and route
   order-flips to the `uncertain` verdict state already planned.
4. **Adopt a kill-mandate critic + cross-family check as the falsification
   lens template**, rather than a fixed roster of personas (F4.1, F4.3,
   F4.4) — this is close to Owner's stated intent already; the research
   gives concrete structural language ("kill mandate," "disposable
   task-scoped lens") to formalize the risk-tiered selection logic.
5. **Gate every new constraint-registry entry on a cited real failure**
   (F5.3's Creator-agent pattern) and add a periodic re-verification pass
   for existing constraints (F5.4's "constraint drift") — the current
   proposal as summarized has creation but not decay-checking; add a
   lightweight "does this constraint still fire / is it still true" sweep
   to `/renmark:hygiene` or an audit stage.
6. **Do not treat the append-only ledger design as needing external
   validation** — F6.1 shows the pattern is sound in principle (git itself
   is proof) but no comparable lightweight implementation was found to
   benchmark against; renmark's existing `.renmark/state/lifecycle.json` +
   wave-summaries approach should be evaluated on its own merits (size caps,
   G12 stage order, recovery correctness) rather than against an
   external example that doesn't exist in the literature searched.
7. **Do not import F7.1's "43%" figure as a target/baseline** — it's a
   single vendor statistic in an unconstrained-generation context, not
   validated for bounded, receipt-gated dispatch. If an outcome-guardrail
   metric is needed here, define and measure renmark's own baseline instead.

---

## Unknowns (each needs a bounded spike, not open-ended research)

- **U1.** Codex's actual sandboxing/enforcement mechanism (prompt-only vs.
  OS-level pre-action) was not retrieved in this pass — needed because
  renmark dispatches to Codex via `renmark-execute` and the proposed
  pre-action envelope must work identically on both hosts. *Spike*: read
  Codex CLI's own sandboxing docs directly (not web search) and compare to
  Claude Code's `PreToolUse` model.
- **U2.** No retrospective/post-mortem of a failed agent-governance rollout
  was found (Topic 7's core ask). *Spike*: bounded search specifically for
  named case studies ("we removed our multi-agent review gate because...")
  rather than general "AI SDLC 2026" material, or accept this as
  genuinely under-documented in public literature as of 2026-08 and rely on
  renmark's own `ORCHESTRATION-BASELINE-2026-08` empirical baseline instead.
- **U3.** No file-backed, database-free, single-user event-sourcing
  reference implementation was found to benchmark renmark's
  `.renmark/state/` design against. *Spike*: this may simply not exist in
  public literature at renmark's scale — recommend treating this as
  self-benchmarked (measure renmark's own resume/recovery correctness)
  rather than continuing external search.
- **U4.** Real-world flip-rate / disagreement-rate numbers for a *small*
  (renmark-scale) blind judge deployment are unknown — the 5% flip-rate
  threshold in F3.1 is drawn from larger calibration sets. *Spike*: run
  renmark's own judge on ~20-30 real past dispatch outcomes once the
  blind-judge feature exists, and set thresholds from that data rather than
  the literature's number.
- **U5.** Whether Refute-or-Promote / Adversarial Review's benchmark gains
  (F4.1, F4.2) generalize beyond code-defect review to renmark's
  architecture/release-readiness review surfaces is unverified. *Spike*:
  small internal A/B on renmark's own `/renmark:codereview` outputs, kill-
  mandate critic vs. current approach, on a handful of real past PRs.

---

## Sources (all accessed 2026-08-04)

- [6 Multi-Agent Orchestration Patterns for Production (2026)](https://beam.ai/agentic-insights/multi-agent-orchestration-patterns-production)
- [LLM Orchestration in 2026: Top 22 frameworks and gateways](https://aimultiple.com/llm-orchestration)
- [Claude Code Hooks Complete Guide](https://hidekazu-konishi.com/entry/claude_code_hooks_complete_guide.html)
- [Claude Code Security Guide (DataCamp)](https://www.datacamp.com/tutorial/claude-code-security)
- [Claude Code Permissions Explained (DataStudios)](https://www.datastudios.org/post/claude-code-permissions-explained-safe-command-execution-project-controls-sandboxing-hooks-and)
- [Before the Tool Call: Deterministic Pre-Action Authorization for Autonomous AI Agents](https://arxiv.org/pdf/2603.20953)
- [Don't Let AI Agents YOLO Your Files](https://arxiv.org/pdf/2604.13536)
- [LLM-Judge Bias Mitigation (2026)](https://futureagi.com/blog/evaluating-llm-judge-bias-mitigation-2026/)
- [LLM-as-Judge Best Practices in 2026](https://futureagi.com/blog/llm-as-judge-best-practices-2026)
- [LLM-as-a-Judge in 2026: How It Works, When It Fails](https://futureagi.com/blog/llm-as-a-judge/)
- [Judging the Judges: Systematic Evaluation of Bias Mitigation Strategies](https://arxiv.org/pdf/2604.23178)
- [Fairness or Fluency? Language Bias of Pairwise LLM-as-a-Judge](https://arxiv.org/pdf/2601.13649)
- [Refute-or-Promote: Adversarial Stage-Gated Multi-Agent Review](https://arxiv.org/pdf/2604.19049)
- [Adversarial Review: Cooperative Code Review through Structured Disagreement (OpenReview)](https://openreview.net/forum?id=fOHvpLs6zp)
- [Cross-Model Adversarial Review blog](https://codex.danielvaughan.com/2026/03/28/cross-model-adversarial-review/)
- [Can LLM Agents Really Debate? Controlled Study of Multi-Agent Debate](https://arxiv.org/pdf/2511.07784)
- [SARC: A Governance-by-Architecture Framework for Agentic AI Systems](https://arxiv.org/pdf/2605.07728)
- [Deterministic Constraint Systems: Tool Registries That Keep Agents in Scope](https://ranjankumar.in/harness-engineering-deterministic-constraint-systems-tool-registry-agents)
- [MAC: Multi-Agent Constitution Learning](https://arxiv.org/pdf/2603.15968)
- [Safe Multi-Agent Behavior Must Be Maintained: Constraint Drift](https://arxiv.org/pdf/2605.10481)
- [Event Sourcing Pattern — Microsoft Learn](https://learn.microsoft.com/en-us/azure/architecture/patterns/event-sourcing)
- [Lightrun: SDLC Phases and the Reliability Gap AI Can't Close](https://lightrun.com/blog/sdlc-phases/)
- [Augment Code: AI SDLC Maturity Model](https://www.augmentcode.com/guides/ai-sdlc-maturity-model)
- [Dynamic Capability Scoping for Enterprise AI Agents](https://arxiv.org/html/2607.22445v1)
- [Why AI Agents Need Their Own Permission Model (Auth0)](https://auth0.com/blog/why-ai-agents-need-their-own-permission-model/)
