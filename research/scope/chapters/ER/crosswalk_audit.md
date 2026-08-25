# ER (Emergency Medicine) — Crosswalk Audit

Generated 2026-08-25.

## Classification counts (52 units)

| Classification | Count |
|---|---|
| DIRECT | 28 |
| COMPONENT | 18 |
| UNCERTAIN | 2 |
| SPECIALIST_DETAIL | 2 |
| REFERENCE_ONLY | 2 |

## Source-quality confidence counts

| Confidence | Count |
|---|---|
| HIGH | 17 |
| MEDIUM | 10 |
| LOW | 25 |

The high LOW-confidence count reflects that most study units cite at least one `TOC_OCR_UNANCHORED`
topic node alongside their `BODY_HEADING_CONFIRMATION`/`TOC_OCR` section node (see
`study_units_audit.md`); every unit's actual content and page range was independently confirmed against
body OCR regardless of the underlying node's own extraction confidence.

## Zero-question units (4)

Acronyms (SU-ER-01), Antidotes/Warfarin table (SU-ER-42), Medications table (SU-ER-51), References
(SU-ER-52) — all reference/table material with `zero_question_reason` set; no missing reasons.

## WEAK / UNCERTAIN / CROSS_DISCIPLINE units requiring scope review (7)

SU-ER-19 (Cardiac Dysrhythmias), SU-ER-22 (VTE), SU-ER-27 (Sepsis), SU-ER-29 (Epistaxis — UNCERTAIN),
SU-ER-34 (Heat-Related Illness — UNCERTAIN), SU-ER-37 (Bites), SU-ER-44 (Approach to Psychiatric
Presentations). Each was checked against the full MCC objectives registry via `search-mcc-objectives`
before being left WEAK/UNCERTAIN rather than forced to a fabricated STRONG match. Electrolyte
Disturbances (SU-ER-24) was initially WEAK/CROSS_DISCIPLINE but was upgraded to MODERATE/COMPONENT after
a targeted search found dedicated Hyperkalemia (79-1) and Hyponatremia (99-2) objectives. Full detail in
`crosswalk_audit.json` and `review_items.json`.
