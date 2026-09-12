# Curriculum Question Opportunity Registry V1 Design

## Goal

Build a canonical, deterministic inventory of educationally distinct MCCQE-style question opportunities before any production question authoring. The milestone also freezes dedupe, coverage, capacity, allocation, seed-slot, identity-graph, dry-run, and production-queue artifacts.

## Inputs and invariants

The canonical inputs are `research/scope/master_scope_crosswalk.json`, `research/scope/final_question_allocation.json`, `research/scope/question_bank_targets.json`, `research/mcc/objectives_registry.json`, `research/qgen/source_packet_plan.json`, `research/qgen/generation_source_readiness.json`, and the validated QGEN exposure and Question Seed assets. All are read-only. Eligibility, zero-scope precedence, ownership suppression, discipline routing, MCC mappings, and final allocation remain frozen.

No clinical recommendation is inferred. Each base opportunity comes from one authored `testable_competencies` entry on an eligible study unit. A study unit with no usable competency receives an explicit zero-opportunity reason. The registry stores compact normalized concepts and provenance references, not Toronto Notes prose.

## Architecture

`scripts/qbank/curriculum_opportunity_registry.py` is a deterministic builder and validator. It produces a curriculum snapshot, base registry, coverage matrix, independent-review sample and verdicts, allocation plan, seed population plan, identity graph, production queue, dry-run report, milestone report, and copyright audit. JSON serialization is sorted and stable, with content hashes computed over canonical payloads that exclude their own hash fields.

One base opportunity is created per non-empty competency key/value. Controlled keyword rules map it to an opportunity family, response class, clinical stage, material population/severity context, physician activity, and dimension of care. The original competency text is retained only as a provenance anchor; registry-facing learner decisions and reasoning targets are normalized, compact descriptions derived from the competency label and study-unit title. Unsupported detail remains `NA`.

## Identity and dedupe

The opportunity fingerprint hashes normalized study-unit/topic, learner decision, response class, key concept/action, stage, material population, material severity, reasoning target, and physician activity. It excludes names, incidental demographics, wording, ordering, and surface vignette detail. Exact duplicates collapse while preserving all source study units, source nodes, MCC IDs, and aliases.

Near-duplicate detection is deterministic and conservative: it compares opportunities only inside the same discipline and topic/variant group, requires matching decision/family/response/stage/context, and uses normalized-token similarity. High-confidence equivalents collapse; ambiguous pairs are emitted for review rather than silently merged. Same-topic differences in decision, stage, material population, complication, or response class remain distinct.

## Capacity and allocation

Capacity is not copied from the 6,086 target. Each opportunity begins with capacity one. A second or third slot is allowed only when metadata demonstrates distinct supported pathways through different preferred item forms, materially different context/stage/severity, or multiple MCC activities. Capacity is capped at three. MCQ-weak and unsuitable opportunities receive allocation zero. The proposed discipline total is the smaller of defensible capacity and the frozen discipline target; unmet target is reported, never filled cosmetically.

Slots are assigned coverage-first: CORE before HIGH/IMPORTANT before STANDARD/SUPPORTING, then MCQ strength, source readiness, chapter, study unit, opportunity, and slot. Difficulty slots follow the repository's 20/55/25 planning policy where the opportunity supports the level; no opportunity is forced to carry all three levels. Production waves are WAVE_0 for exact ready assets, WAVE_1 for CORE on-demand work, WAVE_2 for remaining HIGH work, WAVE_3 for STANDARD coverage, and WAVE_4 for explicitly supported extra capacity.

## Readiness and existing assets

Source-packet and generation-job mappings determine evidence readiness. Exact compatible Question Seeds or frozen bundles may produce `READY_EXISTING_BUNDLE` or `READY_EXISTING_CANDIDATES_NEEDS_SEED`; otherwise source-ready opportunities use `READY_ON_DEMAND_EXPANSION`, pending evidence uses `NEEDS_EVIDENCE`, weak contrast supply uses `NEEDS_CANDIDATE_EXPANSION`, and non-MCQ rows use `UNSUITABLE_FOR_MC`. Development and clean-validation items are linked as `VALIDATION_ITEM` only and are not counted as production items.

## Review, quality, and safety

A stable stratified sample covers every discipline and major family. The review sees no desired counts and checks reality of the learner decision, MCCQE level, atomicity, distinctness, MCQ suitability, and capacity. Deterministic defects receive the requested taxonomy; uncertain semantic cases remain visible and cannot silently enter allocation.

The production acceptance contract requires an approved opportunity and seed, approved candidates, evidence-backed load-bearing facts, blind solve, at least three live-but-inferior distractors, final medical review, copyright PASS, and semantic duplicate PASS. Stop rules cover falling acceptance, second-key defects, duplicates, evidence-cost spikes, coverage drift, and repeated family-specific failure.

## Verification

TDD covers snapshot integrity, schema validation, fingerprints, exact and near dedupe, same-topic identity policy, capacity bounds, zero-unit reporting, allocation reconciliation, queue stability, seed uniqueness, dry-run routing, identity graph integrity, copyright scanning, and frozen-input hashes. Focused tests run throughout. Because shared executable code changes, the final canonical suite runs once at final code state. The known unrelated coordinator failure is reported separately; new failures must be zero.

## Worktree policy

No commit, reset, clean, stash, destructive checkout, historical frozen-artifact modification, or `CLAUDE.md` change is permitted.
