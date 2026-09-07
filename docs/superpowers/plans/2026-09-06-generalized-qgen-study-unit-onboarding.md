# Generalized QGEN Onboarding Implementation Plan

> **For agentic workers:** Use superpowers:subagent-driven-development for independent review/research and sequential task implementation. Track the steps below.

**Goal:** Make new units eligible through reviewed evidence, compositional profiles and append-only vocabulary, then run the explicitly gated fresh pilot.

**Architecture:** Add independent versioned contracts around the existing registry and contrast gates. Keep historical entry points unchanged. Python validates and builds; separate semantic reviews supply judgments.

**Tech Stack:** Existing Python 3.11+, pytest, JSON, canonical registry utilities.

**Spec:** docs/superpowers/specs/2026-09-06-generalized-qgen-study-unit-onboarding-design.md

## Global Constraints

- No external LLM API or historical artifact mutation.
- No automatic evidence readiness from packet status.
- No ambiguous or unreviewed extension admitted.
- Explicit evidence, feature and profile pins; no implicit latest.
- At least 24 eligible fresh opportunities and all six disciplines before pilot.
- One attempt per frozen opportunity; no difficulty changes.

## Tasks and verification

- [x] 0. Reconcile HEAD, clean tree, current reports and dependency map; write and internally review spec.
- [ ] 1. Add `onboarding_evidence.py` and `tests/test_onboarding_evidence.py`: scoped claim catalog, content-bound independent review, all-address inventory, decision readiness. RED tests for technical READY, wrong address/MCC/claim, partial promotion and stale review; implement and run focused tests.
- [ ] 2. Freeze independent 45-address audit in a new artifact before repairs; build report with exact old/new counts and cause taxonomy. Never rewrite W1.
- [ ] 3. Add `qgen_profiles_v2.py`, versioned profile JSON and tests: closed compositional decision/archetype/response-class pairs, conditional discipline context, explicit pins, canonical scope and approved evidence. Test palliative, gynecology and new PED/SURG/PSY controls plus invalid cross-class/granularity cases.
- [ ] 4. Add `vocabulary_onboarding.py` and tests: typed normalization, evidence-bound feature/anchor manifests, independent approvals, append-only child of V3, duplicate rejection, deterministic hashes, scoped adapters. Historical registry remains unchanged.
- [ ] 5. Revalidate original 26 with individual evidence reviews. Research/review only pilot-relevant new PED/SURG/PSY evidence, declare distinct decisions and vocabulary proposals. Keep author and reviewer artifacts separate.
- [ ] 6. Build approved snapshot, all-address evidence mappings, exact opportunity transitions and fresh gate in `generalized_onboarding.py`; add CLI command and deterministic/adversarial rebuild tests. Gate failures stop generation and are counted as onboarding failures only.
- [ ] 7. If gate passes, commit universe freeze, bounded contrast preflight, independently reviewed extensions and pilot snapshot/profile freeze. Use existing contrast V2 semantics and solver; freeze one-attempt run outputs before independent blind/final review. If gate fails record phases not run and exact reason.
- [ ] 8. Independent code review, focused tests, historical replay equivalence, canonical copyright audit, full suite at final executable state, diff check, verified report and MEMORY update, durable commit.

## Interface preflight review

| Pair / task | Producer → consumer | Consistency check |
| --- | --- | --- |
| 1 → 3,4,6 | decision support + scoped claim catalog | All require same reviewed subject hash; packet READY never substitutes |
| 2 → 1,5 | whole-address audit | Narrow approved decisions may coexist with partial address |
| 3 → 6,7 | explicit compositional profile snapshot | No historical profile loader default changes |
| 4 → 6,7 | V3 child with approved features | Features required at universe gate; contrast acquisition follows freeze |
| 5 → 1,4,6 | new evidence and proposals | Research author cannot independently approve own rows |
| 6 → 7 | eligible universe | Failed gate prevents pilot, not fake NO_SAFE_ITEM rows |
| 7 → 8 | immutable outcomes | No repair after outcomes or inference of psychometric difficulty |
| 0–8 | task text vs requirements | Scoped deliverables match spec; conditional phases remain explicitly not run if gated |

Ruling: work on `codex/generalized-qgen-onboarding` in the supplied clean checkout;
no linked worktree is needed for these additive artifacts. Only the coordinator
changes shared code; research/review agents own disjoint new artifacts. This
preserves access to local canonical source files and runtime.
