# Endocrinology (Chapter E) MCC Crosswalk Audit

**Generated:** 2026-08-25
**Result:** ✅ PASS (`python -m scripts.qbank validate-scope-chapter E`)

## Classification distribution (60 study units)

| Classification | Count |
|---|---|
| DIRECT | 28 |
| COMPONENT | 19 |
| SUPPORTING_KNOWLEDGE | 7 |
| REFERENCE_ONLY | 4 |
| CROSS_DISCIPLINE | 2 |
| SPECIALIST_DETAIL | 0 |
| UNCERTAIN | 0 |

## Mapping-strength quality

- 0 WEAK `mapping_strength` citations — every `mcc_evidence` entry achieved at least MODERATE strength, so no
  unit required `requires_scope_review` flagging on mapping-quality grounds.
- 0 UNCERTAIN classifications.
- 18 distinct MCC objective IDs cited (vs. 3 in Dermatology — see "Objective distribution" below): 130
  (Hyperglycemia), 129 (Hypoglycemia), 12-2 (Calcium disorders), 63 (Neck masses and thyroid disease), 9-1
  (Hypertension), 101 (Stature abnormal), 74 (Periodic health encounter), 46 (Infertility), 94 (Sexual
  dysfunctions and disorders), 36 (Genetic concerns), 56-1 (Amenorrhea, oligomenorrhea), 10-1 (Breast masses and
  enlargement), 79-2 (Hypokalemia), 99-2 (Hyponatremia), 33 (Fatigue), 118-1 (Obesity), 110-2 (Polyuria), 89-2
  (Chronic kidney disease).

## Objective distribution (expected, not an error)

Unlike Dermatology, where one broad objective (38) anchors nearly every unit, Endocrinology's MCC evidence is
spread across 18 distinct presentation/sign-based objectives because MCC's Medical Expert framework covers this
domain with granular symptom objectives (Hyperglycemia, Hypoglycemia, Calcium disorders, Hypertension, etc.)
rather than one umbrella "endocrine conditions" objective — no such umbrella objective exists in the registry.
Most named Toronto Notes diagnoses still map as **COMPONENT** of the nearest broader presentation objective
(e.g. individual thyrotoxicosis etiologies — Graves' aside — as COMPONENT of objective 63) rather than each
independently DIRECT, per `CLAUDE.md`'s guidance against forcing DIRECT status merely because a diagnosis is
named. A unit earned **DIRECT** chiefly where the objective's own `causal_conditions`/`key_objectives` text
names the exact presentation, mechanism, or diagnosis: e.g. objective 110-2's `causal_conditions` explicitly
list `"diabetes insipidus: central versus nephrogenic"` (SU-E-21); objective 10-1's `key_objectives` names `"a
breast mass or gynecomastia"` verbatim (SU-E-55); objective 130's `causal_conditions` explicitly list `"Diabetes
mellitus (type 1, type 2, gestational)"` (SU-E-09, SU-E-10, SU-E-11).

## MCC registry search note

The scope packet's bounded `candidate_mcc_objectives` set (27 entries) was largely generic Study-Smarter
cross-discipline noise (substance use disorders, SIDS, OCD, personality disorders — rows tagged Psychiatry/
Pediatrics/Surgery in `study_smarter.explicit_discipline_rows` rather than Endocrinology-relevant) and did
**not** contain dedicated objectives for the chapter's highest-yield content: diabetes, thyroid-disease
specifics, pituitary, adrenal, or osteoporosis. Per `docs/scope-chapter-workflow.md`'s instruction to use
`search-mcc-objectives` when the candidate set is insufficient, targeted full-registry searches were run for:
diabetes, thyroid, hyperthyroidism, hypothyroidism, osteoporosis, adrenal, Cushing, pituitary, hypogonadism,
gynecomastia, hirsutism, amenorrhea, diabetic ketoacidosis, hyperosmolar, obesity, polyuria, polydipsia, adrenal
insufficiency, hyperglycemia, weight gain, weight loss, goiter/goitre, growth, short stature, puberty,
menstrual, erectile, bone, electrolyte, endocrine, metabolic syndrome, lipid, cholesterol, dyslipidemia,
menopause, breast mass, virilization, precocious, hormone, fatigue, malaise, hypertension, hypokalemia,
hyponatremia, and periodic health.

This surfaced 12 additional relevant objectives not present in the bounded candidate set: **130** (Hyperglycemia),
**101** (Stature abnormal), **57** (Menopause), **10-1** (Breast masses and enlargement), **79-2** (Hypokalemia),
**99-2** (Hyponatremia), **9-1** (Hypertension), **33** (Fatigue), **118-1** (Obesity), **110-2** (Polyuria),
**56-1** (Amenorrhea, oligomenorrhea), **118-2** (Weight loss/eating disorders/anorexia).

Several searched terms returned **zero matches** — confirming MCC genuinely has no dedicated named objective for
these (not a search-tooling gap): thyroid hyper-/hypothyroidism specifically, adrenal, Cushing, pituitary,
hypogonadism, gynecomastia, hirsutism, osteoporosis, goiter/goitre, puberty, menstrual, erectile, electrolyte,
endocrine, lipid/cholesterol/dyslipidemia, virilization, hormone, malaise. Units in these areas were mapped as
COMPONENT/MODERATE evidence under the nearest presentation-based objective (e.g. objective 63 "Neck masses and
thyroid disease" for the thyroid-specific units; objective 33 "Fatigue" for adrenal insufficiency; objective 9-1
"Hypertension" for Cushing's/pheochromocytoma/primary aldosteronism) rather than left unmapped or forced onto a
non-existent DIRECT id. Objective 57 (Menopause) was found but ultimately not cited, since chapter E's Female
Reproductive Endocrinology content is itself only a cross-reference stub (SU-E-56) with no independent
menopause-specific body content to map.

## Zero-question (non-testable) units — all documented

12 units carry `minimum_question_coverage: 0`, each with a `zero_question_reason`:

| Unit | Reason |
|---|---|
| SU-E-01 Acronyms and Basic Anatomy Review | Pure glossary/reference content |
| SU-E-02 Overview of Lipid Transport | Normal physiology background, not independently testable |
| SU-E-07 Overview of Glucose Regulation | Normal physiology background, not independently testable |
| SU-E-17 Hypothalamic-Pituitary Axis Physiology | Normal physiology background; TSH/ACTH stubs' real content lives under Thyroid/Adrenal Cortex |
| SU-E-23 Thyroid Hormone Physiology | Normal physiology background, not independently testable |
| SU-E-36 Adrenocortical Hormone Physiology | Normal physiology background, not independently testable |
| SU-E-43 Catecholamine Metabolism | Normal physiology background, not independently testable |
| SU-E-52 Androgen Regulation and Tests of Testicular Function | Normal physiology/investigation background |
| SU-E-56 Female Reproductive Endocrinology | Pure "see Gynecology, GY23" cross-reference, no independent E-chapter content |
| SU-E-58 Common Endocrine Medications Reference | Drug-summary tables duplicating each disease unit's own management competencies |
| SU-E-59 Landmark Endocrinology Trials | Bibliographic/trial-summary reference material |
| SU-E-60 References | Pure bibliography |

## Cross-discipline units

- **SU-E-50 Renal Osteodystrophy** — bone-mineral-disease complication of CKD; primary CKD diagnosis, staging,
  and management belong to the Nephrology chapter (Objective 89-2), matching the SU-D-15-style convention of
  scoping the unit to only the endocrinology-relevant slice.
- **SU-E-56 Female Reproductive Endocrinology** — Toronto Notes itself defers entirely to "see Gynecology,
  GY23"; no independent Endocrinology-chapter content exists to map.

## Freshness flags

15 units are flagged `verification_required: true` (all MEDICATION) where Toronto Notes cites specific drug
regimens subject to change: Dyslipidemia Treatment, Pre-Diabetes, Diabetes Mellitus Diagnosis, Treatment of
Diabetes, Acute Diabetes Complications, Diabetic Microvascular Complications, Prolactin Disorders, Graves'
Disease, Thyroid Storm, Hypothyroidism, Myxedema Coma, Adrenocortical Insufficiency, Osteoporosis, Male
Hypogonadism/Infertility, Erectile Dysfunction, and the Common Endocrine Medications reference unit. Per
chapter-scope-stage rules, no specific dosing/regimen was itself encoded as a scope decision — freshness
verification is deferred to the question-generation stage.

## Source-quality note

See `study_units_audit.md` for chapter E's clean single-column TOC source (no two-column merges, 0 unresolved
headings, 0 UNCATALOGUED synthetic ids) — a markedly better source-structural starting point than Dermatology.
Every resulting study unit was mapped independently and none required WEAK evidence.
