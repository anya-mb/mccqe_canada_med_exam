# NS Low-Effort Semantic Audit (Sonnet 5, MEDIUM effort)

Targeted audit of the 26-unit NS risk set (SPECIALIST_DETAIL, WEAK-evidence,
CROSS_DISCIPLINE, requires_scope_review). Full per-unit table:
`low_effort_semantic_audit.json`. Not a full remap.

## Changes applied

| study_unit_id | change |
|---|---|
| SU-NS-06 (IIH) | SPECIALIST_DETAIL → COMPONENT — same evidentiary pattern (obj 39 Headache, WEAK, RECOGNIZE depth) as SU-NS-07 Hydrocephalus / SU-NS-13 Meningioma, both already COMPONENT |
| SU-NS-22 (AVM/cavernoma/dural AVF) | evidence WEAK → MODERATE against obj 41 (stroke) — its causal_conditions text explicitly names "Hemorrhage - Intracerebral and cerebellar - Subarachnoid" |

## Result

- 16 SPECIALIST_DETAIL units reviewed: 15 KEEP_SPECIALIST, 1 upgraded
- 15 WEAK-evidence units reviewed: 14 KEEP_WEAK, 1 remapped to MODERATE
- 3 CROSS_DISCIPLINE units reviewed: all defensible at chapter level, unchanged
- 2 canonical crosswalk.json entries changed

**LOW_EFFORT_NS_QUALITY = CAUTION** — two internally-inconsistent
classifications found and corrected; no systematic under/over-classification
pattern across the rest of the risk set.
