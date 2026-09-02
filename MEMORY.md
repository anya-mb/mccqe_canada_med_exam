# MCCQE project

<!-- SOURCE_RESEARCH_RESUME:START -->
## Current phase

- Current phase: scaled current-Canadian source-packet research.
- Source-packet planning is complete and frozen (`SOURCE_PACKET_PLAN = PASS`).
- Total planned source packets: 1,524.
- Source packets READY: 90.
- Source packets PENDING: 1,434.
- Source packets BLOCKED: 0.
- Source packets INCOMPLETE: 0.
- Total research batches: 159.
- Research batches complete: 10.
- Research batches pending: 149.
- Source documents: 75.
- Generation jobs total: 220.
- Generation jobs SOURCE_READY: 11.
- Generation jobs PENDING: 209.
- Generation jobs BLOCKED: 0.
- Generation queue jobs: 11.
- Worker states: `SRB-114` = INTEGRATED; `SRB-117` = INTEGRATED.
- Canonical checkpoint: current Git HEAD.
- Audited coordinator input commit: `457e17f0daef6fd16b45afbc91e9525a4b609767`.
- Current next action: `PLAN_SOURCE_READY_GENERATION`.

## Frozen layers

- Scope, MCC mapping, ownership, competency-component ownership, discipline routing, question planning, and question-bank targets are complete and frozen.
- Do not reopen a frozen layer unless explicitly authorized or a concrete validator/audit failure requires repair.

## Canonical question-bank target

- Final study-bank target: 6,086 questions.
- MED = 1,086.
- PED = 1,000.
- OBGYN = 1,000.
- SURG = 1,000.
- PSY = 1,000.
- PHELO = 1,000.
- MED exactly equals its effective minimum; do not reduce MED minima merely to restore a 1,000-question MED target.
- The separate 230-question MCCQE simulation is not part of the 6,086-question study bank.

## Blocker and next step

- No upstream blocker remains. Continue research one bounded canonical wave at a time.
- NEXT_STEP = `PLAN_SOURCE_READY_GENERATION`
<!-- SOURCE_RESEARCH_RESUME:END -->

<!-- QGEN_ARCHITECTURE_RESUME:START -->
## Question-generation architecture resume state

This section is maintained by hand and sits outside the generated source-research resume block, which
`scripts/qbank/source_research_checkpoint.py` rewrites from canonical artifacts on every suite run.

- Cardiology ACS 10-item chapter-review pilot: SUCCESS (9/10). Positive control for the staged architecture.
- Frozen-architecture cross-discipline generalization experiment (`c69fbae7`): 7/15 PASS. PED 2/3, OBGYN 1/3,
  SURG 1/3, PSY 2/3, PHELO 1/3. `GENERALIZATION_ASSESSMENT = FAILED_GENERALIZATION`.
- Diagnosis: COMPLETE. `PRIMARY_ROOT_CAUSE` = the contrast layer enforced only referential consistency between an
  item competitor and its library edge. It required the competitor's evidence set to equal the edge's set, never
  that the competitor's plausibility and disqualification be traceable to competitor-specific evidence, and never
  that either be grounded in the stem the candidate reads. All 45 baseline competitors cited exactly one claim
  each, always that item's anchor key claim; the successful Cardiology pilot by contrast carried competitor-specific
  claims. Secondary causes: the distractor adversarial review was a boolean checkbox map with no required grounding,
  and polarity/completeness were assessed only after surface realization by heuristics blind to option-set
  architecture. `COMMON_LAYER_FAILURE_CONFIRMED = YES`.
- Bounded general fix: IMPLEMENTED in `scripts/qbank/chapter_staged_generation.py` as staged schema 1.3
  (`STAGE_SEQUENCE_V4`) adding two fail-closed gates, `CONTEXTUAL_COMPETITOR_PROOF` and
  `SEMANTIC_POLARITY_COMPLETENESS_PREFLIGHT`. Schema 1.0 to 1.2 behaviour is unchanged. 22 new regression tests.
- Controlled derivative retest (`cross_discipline_generalization_15_r2`): same 15 educational targets, anchors and
  learner decisions reused, new evidence lineage. 14 items built and validated by the production validator;
  `QGEN-GEN-SURG-T01` recorded `FAIL_CLOSED_NO_VALID_CONTRAST_SET` after two candidate contrast sets.
- Fresh independent verification passed 1/14: PED 0/3, OBGYN 0/3, SURG 0/2, PSY 0/3, PHELO 1/3.
  `EVIDENCE_TRACEABILITY` moved FAIL to PASS and the original unsupported-competitor-evidence mode did not recur.
  The reviewer nonetheless found 4 factual errors, 14 weak distractors and 7 option-cue failures, and applied a
  stricter bar than the baseline review, so 1/14 is not directly comparable with 7/15. `RETEST_ASSESSMENT = FAILURE`.
- Two new general failure modes were identified. `EXCLUSION_BY_EXPLICIT_STEM_NEGATION` is induced by the new gate's
  requirement that every defeating stem feature be a verbatim stem quote, which pushes stems into terminal clauses
  that negate each competitor. `KEY_AS_CATEGORY_ODD_ONE_OUT` is not covered by the preflight's polarity,
  completeness and scope dimensions. Both are general rather than discipline-specific.
- `RECOMMENDED_ARCHITECTURE_ACTION = ONE_MORE_BOUNDED_GENERAL_FIX`. Discipline-specific generators remain
  unjustified. Do not scale question generation, and do not repair the retest items to raise the score.
- QGEN_NEXT_STEP = `IMPLEMENT_SECOND_BOUNDED_GENERAL_FIX`
<!-- QGEN_ARCHITECTURE_RESUME:END -->

## Research-level policy

- MEDIUM is the default for LOW/MODERATE-freshness, diagnosis/recognition, non-jurisdiction-sensitive packets with straightforward Canadian guidance.
- HIGH is used for HIGH-freshness, medications/treatment, screening, immunization, pregnancy, emergency care, legal/jurisdiction-sensitive material, conflicting guidance, uncertain Canadian applicability, or international-fallback adjudication.

## Source-research protection rules

- Previously READY packets are immutable unless a concrete validated defect is found.
- Frozen upstream curriculum, allocation, manifests, and source-plan layers must not change during source research.
- Research one bounded canonical wave at a time.
- Do not generate MCQs until required source packets are READY.

## Resume artifacts

Before continuing, read:

1. `MEMORY.md`
2. `research/scope/question_bank_targets.json`
3. `reports/final_effective_ownership_audit.json`
4. the canonical Medical Imaging allocation-routing artifact
5. the latest final-question-allocation preflight/audit
6. `reports/source_packet_research_progress.json`

Canonical JSON artifacts and validator output override `MEMORY.md` if they conflict.
