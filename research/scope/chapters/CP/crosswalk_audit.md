# Clinical Pharmacology (Chapter CP) MCC Crosswalk Audit

**Generated:** 2026-08-25
**Result:** ✅ PASS

## Classification Distribution

| Classification | Count |
|---|---|
| DIRECT | 8 |
| COMPONENT | 7 |
| SUPPORTING_KNOWLEDGE | 2 |
| REFERENCE_ONLY | 3 |

No SPECIALIST_DETAIL, CROSS_DISCIPLINE, or UNCERTAIN units in this chapter — Clinical Pharmacology's content is
generalist-level foundational science and safe-prescribing practice throughout, none of it belonging more
properly to another named MCC discipline's own body-system chapter, and no structural or mapping ambiguity was
left unresolved (see `unresolved_mappings.json`).

## Mapping Strength Distribution

| Strength | Count |
|---|---|
| STRONG | 7 |
| MODERATE | 12 |
| WEAK | 0 |

Evidence type split: 17 OBJECTIVE_REFERENCE, 2 ROLE_LEVEL_REFERENCE (both ROLE_LEVEL_REFERENCE entries use
`mcc_id: null` / `legacy_id: null` as required for the six non-Medical-Expert roles, which MCC publishes no
per-objective ID for: SU-CP-13's Leader/Manager patient-safety-reporting evidence, SU-CP-16's Leader/Manager
narcotic-prescribing-regulation evidence).

## MCC Objectives Represented (3 distinct)

77, 78-12, 125

Overwhelmingly anchored on **125 "Prescribing practices"** (used across 16 of 17 OBJECTIVE_REFERENCE citations,
spanning 13 of the chapter's 20 study units) — the only MCC Medical Expert objective dedicated to the general
practice of safe, evidence-based, individualized prescribing, and thus the closest MCC equivalent to a
dedicated "clinical pharmacology" objective (mirroring how Chapter A concentrated on 74-3 "Pre-operative
medical evaluation" as its closest equivalent to a "perioperative medicine" objective). **77 "Poisoning"** is
used once (SU-CP-09, Therapeutic Index/toxicology framing) and **78-12 "Quality improvement and patient
safety"** is used once (SU-CP-18, medication-error prevention).

## Invalid MCC IDs

**0** — every `mcc_id` cited (125, 77, 78-12) was looked up directly in
`research/mcc/objectives_registry.json` before use; none were mapped from memory. `research/mcc/
study_smarter_discipline_mapping.json` was additionally checked as supporting evidence (125 maps to the
Psychiatry/PHELO disciplines there, 77 to Medicine/Pediatrics/Surgery — consistent with a broadly cross-cutting
prescribing-safety objective rather than a single body-system discipline).

## WEAK Mappings

**None.** Unlike Chapters A and C, chapter CP has zero WEAK-strength `mcc_evidence` citations — see
`crosswalk_audit.json`'s `chapter_notes.no_weak_mappings` for why (objective 125's enabling-objectives text is
unusually broad and explicit, giving most units a direct MODERATE-or-better textual anchor).

## Zero-Question Units (3, all carry `zero_question_reason`)

- **SU-CP-01** (Acronyms (Chapter Glossary)): Pure glossary/reference content, no clinical competency to assess.
- **SU-CP-19** (Landmark Pharmacology Trials): Historical trial citations/results tables, not an independent
  clinical competency.
- **SU-CP-20** (References / Bibliography): Pure bibliography, no independent content — confirmed genuine, not
  a misattribution.

## Coverage Weight Distribution

weight 1: 5 units, weight 2: 2 units, weight 3: 5 units, weight 4: 7 units, weight 5: 1 unit

**Total `minimum_question_coverage` across chapter CP:** 58

## Unresolved / Uncertain Mappings

0 UNCERTAIN classifications; 0 unresolved mappings (see `unresolved_mappings.json`, empty by design).

## Summary

Study units: 20
Classification counts: {'REFERENCE_ONLY': 3, 'SUPPORTING_KNOWLEDGE': 2, 'DIRECT': 8, 'COMPONENT': 7}
Mapping strength counts: {'STRONG': 7, 'MODERATE': 12, 'WEAK': 0}
Distinct MCC objectives used: 3
Invalid MCC IDs: 0
WEAK mappings missing requires_scope_review: 0
UNCERTAIN classifications missing uncertain_reason: 0
Zero-question units missing zero_question_reason: 0

**MCC crosswalk: PASS**
