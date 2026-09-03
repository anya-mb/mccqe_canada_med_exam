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
- Audited coordinator input commit: `6f81c1a5b1240f088f583dff82e381e01d8e1ecb`.
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

- Reviewer calibration (`reports/qgen_reviewer_calibration_v2.json`) is the first thing to read. Eleven previously
  reviewed items were re-presented blind. `RUBRIC_DRIFT_FOUND = YES`, but not where the r2 report said: the standard
  moved on distractor competitiveness and option-set category parity, not on rationale register. Six of eight
  previously accepted controls now fail, including all four Cardiology positive controls, because their stems close
  with a negative checklist mapping onto the distractor list or because the key is the only member of its option
  category. **Raw pass rates of 9/10 (Cardiology), 7/15 (baseline), 1/14 (r2) and 8/13 (r3) are not comparable with
  one another.** Compare defect counts, not pass rates.
- That calibration corrects the recorded r2 diagnosis. `EXCLUSION_BY_EXPLICIT_STEM_NEGATION` and
  `KEY_AS_CATEGORY_ODD_ONE_OUT` predate schema 1.3 and are present in the Cardiology pilot; the verbatim-quote
  requirement amplified the first, it did not create it.
- `RATIONALE_FATAL_STANDARD_DEFINED = YES`, in
  `chapter_staged_generation.validate_calibrated_rationale_assessment`. Four fatal criteria; register and
  expansiveness are enhancement classes that never reject an item. The generator holds the higher bar and refuses to
  emit an imperative key rationale at schema 1.4.
- Second bounded general repair: IMPLEMENTED as staged schema 1.4 (`STAGE_SEQUENCE_V5`), the
  `SEMANTIC_ITEM_ACCEPTANCE_V2` layer. Five fail-closed gates: `CANDIDATE_VISIBLE_STEM_FEATURE_MAP` (semantic
  features, integrated inferences, no verbatim-quote requirement), `NUMERIC_DERIVATION_VALIDATION` (Decimal
  recomputation over a 16-formula registry, independent verification for anything unregistered),
  `EVIDENCE_ENTAILMENT_ADJUDICATION` (entailment status and support scope; a general concept source cannot decide a
  scenario-specific claim), `TERMINAL_EXCLUSION_REVIEW` (negative-checklist and closing-negation detectors),
  `OPTION_SEMANTIC_CATEGORY_PARITY` plus `PRE_ASSEMBLY_SEMANTIC_SET_REVIEW`. Schema 1.0 to 1.3 unchanged. 48 new
  regression tests; focused 115/0, full suite 847/0.
- Controlled retest `cross_discipline_generalization_15_r3`: same 15 targets and anchors, new stems and option sets.
  13 items built and validated; PED-T03 and SURG-T01 recorded `FAIL_CLOSED_NO_VALID_CONTRAST_SET`.
- Fresh independent verification under the calibrated rubric passed 8/13: PED 1/2, OBGYN 3/3, SURG 0/2, PSY 2/3,
  PHELO 2/3. The verifier independently reached the keyed answer on all 13. Defect counts against r2 under the same
  bar: factual 4 to 0, unsupported 6 to 0, ambiguous 1 to 0, weak distractors 14 to 2, option cues 7 to 2, fatal
  rationale defects 14 to 0; one numeric error remains. `RETEST_ASSESSMENT = MIXED` — the defect-rate target was met
  almost everywhere, the yield target of 13/15 was not.
- Four surviving modes, none a shared architectural layer. `LONE_KEY_OPTION_CATEGORY` (PED, PHELO): the detector only
  fires when the distractors share one category, and the exception path was used too readily. `SEVERITY_OR_CATEGORY_
  MISMATCHED_DISTRACTORS` (PSY, PHELO): the fixed contrast inventory holds no competitive same-category alternative.
  `NUMERIC_COMPONENT_NOT_GROUNDED_IN_THE_STEM` (SURG): the gate recomputes the total from declared components but
  never checks the components against the stem, so a declared Alvarado nausea of zero contradicted a stem recording
  mild nausea. `AUTHORED_TERMINAL_CLAUSE_BELOW_THE_DETECTOR` (SURG): a positively worded closing clause carries no
  negation marker yet enumerates a contraindication list.
- `RECOMMENDED_ARCHITECTURE_ACTION = DO_NOT_SCALE`. The stop rule applies and no third universal patch was written.
  The binding constraint has moved off the generator onto contrast-seed and evidence acquisition. Retest items are
  recorded as reviewed, not repaired; do not repair them to raise the score.
- QGEN_NEXT_STEP = `ACQUIRE_COMPETITIVE_CONTRAST_SEEDS`
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
