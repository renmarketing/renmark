---
artifact_type: program
schema_version: 1
created_at: 2026-06-14T16:54:51.490019+00:00
source_sha: bbb8f07
---

# Program — renmark-prd-program

_mode: staged · Stage 1/19 · task 3/3 done · current: Build plain-English guided pipeline entry_

## ● Build plain-English guided pipeline entry — serves REQ-1

- [x] Implement /renmark:start adaptive entry (1 question + max 2 follow-ups)
- [x] Wire start → plan|brainstorm routing
- [x] Hide Loop Mode behind start for vibe coders

## ● Implement multi-LLM cost-aware routing — serves REQ-2

- [x] Route each task to cheapest capable model (Haiku/Codex/Sonnet/Opus/Fable)
- [x] Emit cost preview before spend; reflect Fable $10/$50 pricing
- [x] Add declared-capability top_tier: fable layer with Opus single-retry fallback
- [x] Deterministically forbid Fable on mechanical/bulk work in plan validation

## ● Make multi-step workflows resumable — serves REQ-3

- [x] Persist lifecycle.json + pipeline.json on every stage transition
- [x] Implement /renmark:resume cold-start recovery (zero LLM)

## ● Establish human-owned PRD source of truth — serves REQ-4

- [x] Author /renmark:prd CREATE/UPDATE with human-gated diff approval

## ● Enforce orchestrator context hygiene — serves REQ-5

- [x] Bound orchestrator-visible output to summaries/paths/metadata (≤5 lines)
- [x] Aggregate per-wave summaries; never load code/diffs/bodies

## ● Confine all artifacts inside the project — serves REQ-6

- [x] Write all renmark output under .renmark/; keep global plugin read-only

## ● Validate plans and verify features goal-backward — serves REQ-7

- [x] Implement /renmark:check-plan deterministic validation (PASS/WARN/BLOCK)
- [x] Implement /renmark:verify goal-backward smoke + --qa/--deep-qa modes

## ● Enable non-destructive adoption and diagnosis — serves REQ-8

- [x] Implement /renmark:init front door (scaffold + merge rule blocks)
- [x] Implement /renmark:doctor install-health diagnosis + --fix
- [x] Keep /renmark:setup as thin rule-block-refresh alias

## ● Build bounded, cost-previewed Loop Mode — serves REQ-9

- [x] Implement /renmark:loop bounded by budget AND max-iterations with cost preview

## ● Persist and recover loop state — serves REQ-10

- [x] Persist loop state under .renmark/loops/<id>/; recover via /renmark:resume

## ● Decide loop iterations goal-backward from evidence — serves REQ-11

- [x] Drive each loop iteration from fresh verification evidence only (bounded reads)

## ● Gate destructive loop actions on human approval — serves REQ-12

- [x] Require approval before loop edits PRD/merges/releases/escalates budget

## ● Build backlog intake + approval buffer — serves REQ-13

- [x] Implement /renmark:backlog interactive list + detail view
- [x] Approve-and-build launches bounded Loop (cap 5) on managed branch
- [x] Record one disposition per branch; no orphan branches; persist item state

## ● Reserve scheduled QA read-only proposer lane — serves REQ-14

- [x] Design scheduled read-only proposer lane (propose backlog items, never execute)

## ● Build local-only reporting and analytics — serves REQ-15

- [x] Write task/loop/backlog/feature/release reports under .renmark/reports/
- [x] Aggregate rolling analytics under .renmark/analytics/ (stdlib JSON/JSONL)
- [x] Implement /renmark:usage and /renmark:analytics bounded status views
- [x] Label all account-limit output as observed-local unless provider-sourced

## ● Pause safely on usage/quota limits — serves REQ-16

- [x] Persist pause_reason=usage_limit with reset/fallback; resume later, no polling

## ● Provide read-only self-audit surface — serves REQ-17

- [x] Implement /renmark:audit (lint/modularity/version/registry/parity) advisory-only
- [x] Implement /renmark:inventory alias writing under .renmark/audits/

## ● Centralize approval granting in /renmark:approve — serves REQ-18

- [x] Make /renmark:approve sole setter of human_review_completed; consumers clear gate

## ● Add optional Playwright browser layer — serves REQ-19

- [x] Implement opt-in Playwright layer with persisted storageState in .renmark/
- [x] Fall back to Chrome DevTools MCP channel when Playwright absent
