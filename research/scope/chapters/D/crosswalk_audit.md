# Dermatology (Chapter D) MCC Crosswalk Audit

**Generated:** 2026-08-25
**Result:** ✅ PASS (`python -m scripts.qbank validate-scope-chapter D`)

## Classification distribution (48 study units)

| Classification | Count |
|---|---|
| DIRECT | 24 |
| COMPONENT | 17 |
| CROSS_DISCIPLINE | 2 |
| SPECIALIST_DETAIL | 2 |
| REFERENCE_ONLY | 2 |
| SUPPORTING_KNOWLEDGE | 1 |
| UNCERTAIN | 0 |

## Mapping-strength quality

- 0 WEAK `mapping_strength` citations — every `mcc_evidence` entry achieved at least MODERATE strength, so no
  unit required `requires_scope_review` flagging on mapping-quality grounds.
- 0 UNCERTAIN classifications.
- 3 distinct MCC objective IDs cited: **38** (Skin and integument conditions, 39 of 41 citations), **85**
  (Pruritus, 1 citation), **97-2** (Urticaria, angioedema, 1 citation).

## Single-objective concentration (expected, not an error)

MCC's Medical Expert framework has exactly one broad, presentation-oriented objective covering the full
breadth of dermatologic diagnoses (objective 38). Per `CLAUDE.md`'s explicit guidance that "the current MCC
Medical Expert framework is presentation-oriented, so many diagnoses may legitimately map as COMPONENTS of
broader presentation objectives," most named Toronto Notes diagnoses in this chapter map as **COMPONENT** of
objective 38 rather than DIRECT. A unit only earned **DIRECT** when either (a) objective 38's own
`causal_conditions`/`rationale` text names the diagnosis or category explicitly and unambiguously — e.g.
`"Malignant (e.g., melanoma)"` for SU-D-36 (Malignant Melanoma), or the verbatim list
`"Hair presentations - Alopecia - Scarring - Non-scarring - Hirsutism - Hypertrichosis"` informed SU-D-38 — or
(b) a dedicated MCC objective exists for the exact presentation: Pruritus (85) for SU-D-43, Urticaria/angioedema
(97-2) for SU-D-42. No Dermatology-diagnosis DIRECT mapping was made merely because it is a recognized disease
name, per the explicit instruction against that shortcut.

## Zero-question (non-testable) units — all documented

6 units carry `minimum_question_coverage: 0`, each with a `zero_question_reason`:

| Unit | Reason |
|---|---|
| SU-D-01 Acronyms | Pure glossary/reference content |
| SU-D-02 Skin Anatomy/Function/Aging | Normal anatomy background, not independently testable |
| SU-D-37 Other Cutaneous Cancers (Kaposi Sarcoma) | Rare, HIV/immunosuppression-associated malignancy; specialist-level detail |
| SU-D-44 Wounds/Ulcers, Pediatric Exanthems | Pure "see [other chapter]" cross-references, no independent D-chapter content |
| SU-D-46 Dermatologic Therapies | Pharmacy-reference-table detail (steroid potency rankings, product names); drug specifics already captured per-diagnosis elsewhere |
| SU-D-48 Landmark Trials + References | Bibliographic/trial-summary material |

## Cross-discipline units

- **SU-D-15 Psoriatic Arthritis** — Toronto Notes itself defers to "see Rheumatology, RH25"; this unit covers
  only the dermatology-side risk-marker recognition task (nail/scalp psoriasis as a PsA risk marker).
- **SU-D-44 Wounds and Ulcers / Pediatric Exanthems** — pure cross-references, see above.

## Freshness flags

7 units are flagged `verification_required: true` (MEDICATION and/or IMMUNIZATION) where Toronto Notes cites
specific drug regimens or vaccine recommendations that are subject to change: Acne Vulgaris, Atopic Dermatitis,
Psoriasis, Drug Eruptions (Exanthematous/DRESS), SJS/TEN, Bacterial SSTI, HSV/HZV (incl. zoster vaccine).
Per chapter-scope-stage rules, no specific dosing/regimen was itself encoded as a scope decision — freshness
verification is deferred to the question-generation stage.

## Source-quality note

See `study_units_audit.md` for the chapter's unusually high two-column-TOC-OCR merge/drop rate (worse than
pilot/A/CP chapters) and its resolution via body-heading confirmation. This is a structural/source-derivation
finding, not an MCC-mapping-quality finding — every resulting study unit was mapped independently and none
required WEAK evidence as a result.
