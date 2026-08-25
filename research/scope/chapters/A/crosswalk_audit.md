# Anesthesia (Chapter A) MCC Crosswalk Audit

**Generated:** 2026-08-25
**Result:** ✅ PASS

## Classification Distribution

| Classification | Count |
|---|---|
| COMPONENT | 16 |
| CROSS_DISCIPLINE | 2 |
| DIRECT | 10 |
| REFERENCE_ONLY | 4 |
| SPECIALIST_DETAIL | 2 |
| SUPPORTING_KNOWLEDGE | 4 |

## Mapping Strength Distribution

| Strength | Count |
|---|---|
| MODERATE | 26 |
| STRONG | 9 |
| WEAK | 5 |

Evidence type split: 38 OBJECTIVE_REFERENCE, 2 ROLE_LEVEL_REFERENCE
(both ROLE_LEVEL_REFERENCE entries use `mcc_id: null` / `legacy_id: null` as required for the six
non-Medical-Expert roles, which MCC publishes no per-objective ID for: SU-A-03's Communicator
consent evidence, SU-A-07's Leader/Manager patient-safety evidence).

## MCC Objectives Represented (17 distinct)

13, 19, 27, 92, 116, 9-1, 9-2, 15-1, 42-1, 74-3, 79-1, 80-2, 107-1, 107-5, 78-12, 67-2-2, 67-1-2-1

Notably anchored on **74-3 "Pre-operative medical evaluation"** (used across 7 units — the closest
MCC has to a dedicated "perioperative medicine" objective, whose own causal_conditions explicitly
name malignant hyperthermia, sleep apnea, and intubation/airway as anaesthesic risk domains) and
**13 "Cardiac arrest"** (used across 5 units — anchoring the Heart Rate, Difficult Airway, LAST, and
both Appendices/ACLS units).

## Invalid MCC IDs

**0** — every `mcc_id` cited was looked up directly in
`research/mcc/objectives_registry.json` before use; none were mapped from memory.

## WEAK Mappings (all carry `requires_scope_review: true`)

- SU-A-06: mcc_id 42-1
- SU-A-09: mcc_id 13
- SU-A-12: mcc_id 27
- SU-A-17: mcc_id 9-2
- SU-A-18: mcc_id 9-2

## Zero-Question Units (6, all carry `zero_question_reason`)

- **SU-A-01** (Acronyms (Chapter Glossary)): Pure glossary/reference content, no clinical competency to assess.
- **SU-A-23** (Peripheral Nerve Blocks): Regional anesthesia technique selection is already tested at the appropriate generalist depth in SU-A-22; individual peripheral nerve block techniques are procedural specialist skill beyond expected graduating-MD depth.
- **SU-A-29** (Neuropathic Pain (Cross-Reference to Neurology)): Chapter A's own text is a cross-reference only ('see Neurology, N43') with no independent content; testable neuropathic-pain competency belongs to the Neurology chapter's own crosswalk, out of scope for chapter A.
- **SU-A-35** (Appendices: Difficult Tracheal Intubation Algorithms): Detailed published algorithm flowcharts beyond expected graduating-MD depth; the core testable decision points (call for help, escalate to LMA, surgical airway if can't-intubate-can't-ventilate) are already captured in SU-A-11.
- **SU-A-37** (Landmark Anesthesiology Trials): Historical trial citations/results tables, not an independent clinical competency - matches the explicit task guidance that trial trivia is do-not-test content.
- **SU-A-38** (References): Pure bibliography, no independent content.

## Coverage Weight Distribution

weight 1: 10 units, weight 2: 6 units, weight 3: 12 units, weight 4: 6 units, weight 5: 4 units

**Total `minimum_question_coverage` across chapter A:** 105

## Unresolved / Uncertain Mappings

0 UNCERTAIN classifications; 0 unresolved mappings (see `unresolved_mappings.json`, empty by design
— the "Monitoring" structural ambiguity is a study-unit-derivation matter, independently RESOLVED
per `study_units_audit.md`, not an MCC-mapping ambiguity, so it does not appear here).

## Summary

Study units: 38
Classification counts: {'REFERENCE_ONLY': 4, 'SUPPORTING_KNOWLEDGE': 4, 'DIRECT': 10, 'COMPONENT': 16, 'SPECIALIST_DETAIL': 2, 'CROSS_DISCIPLINE': 2}
Mapping strength counts: {'STRONG': 9, 'MODERATE': 26, 'WEAK': 5}
Distinct MCC objectives used: 17
Invalid MCC IDs: 0
WEAK mappings missing requires_scope_review: 0
UNCERTAIN classifications missing uncertain_reason: 0
Zero-question units missing zero_question_reason: 0

**MCC crosswalk: PASS**
