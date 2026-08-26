# Study Units Audit - GM (Geriatric Medicine)

**Generated:** 2026-08-25  
**Total study units:** 20  
**Total source nodes:** 27

## Source accounting

PASS - every canonical source node is represented in at least one study unit's `source_node_ids` or in `organizational_header_nodes`, verified by `validate-scope-chapter GM` (`source_accounting: PASS`).

## Structural quality summary

Chapter GM is a clean chapter: 0 unresolved headings, all 10 level-2 sections extracted at HIGH confidence, and all 17 level-3 topic nodes extracted at LOW confidence (TOC_OCR_UNANCHORED - per-topic page anchoring not independently confirmed, though topic titles themselves are unmerged and legible). Two sections carry a `merged_duplicate_headings` alternate title alongside their printed title (GM.S01, GM.S05); one section's printed title (GM.S09) is a legible OCR corruption of a recognizable word. No independent raw-OCR/body-heading corpus beyond `toc_inventory.json` exists for this project (same limitation as chapters G and GS), so each case below was resolved using only canonical TOC data, per `docs/scope-chapter-workflow.md`'s resolution order.

## Consolidations (multiple source nodes -> one study unit)

- **SU-GM-14**: GM.S04.T01, GM.S04.T02  
  'Reporting Requirements' and 'Conditions That May Impair Driving' are two facets of one fitness-to-drive competency; consolidated rather than split since MCC has no per-facet objective.

- **SU-GM-16**: GM.S06.T01, GM.S06.T02  
  'Pharmacokinetics' and 'Pharmacodynamics' are consolidated as the shared mechanistic background for the applied polypharmacy/prescribing content, carrying no independent MCC evidence of their own.

- **SU-GM-17**: GM.S06.T03, GM.S06.T04  
  'Polypharmacy' and 'Inappropriate Prescribing in Older Adults' are consolidated as one applied-practice unit sharing the same MCC objective (125, Prescribing practices), whose enabling text names both polypharmacy/deprescribing and age-adjusted prescribing together.

## Title/content notes (documented, not silently corrected)

- **SU-GM-01**: GM.S01's printed TOC title 'ACFOMYMS' is an OCR-corrupted mnemonic acronym with no recoverable literal meaning; `merged_duplicate_headings` records the legible alternate 'Physiology and Pathology of Aging', consistent with the section's actual first-section position. Used as the study-unit title rather than the garbled string or an invented one.

- **SU-GM-15**: GM.S05 carries two plausible titles: printed 'Hazards of Hospitalization' and `merged_duplicate_headings` 'Healthcare Institutions'. Both are compatible (institutional/hospitalization risk) rather than contradictory, so both are retained together in the unit title.

- **SU-GM-20**: GM.S09's printed title 'RETEFEMCES' is an unambiguous OCR corruption of 'REFERENCES', confirmed by its terminal chapter position (last section, bibliographic) matching every other completed chapter's References section. Represented under the corrected reading.

## Broad-syndrome split note

- **GM.S03 ('Presentations in Older Adults')**: 11 T-children (Constipation, Delirium, Elder Abuse, Falls, Frailty, Immobility, Incontinence, Malnutrition, Presbycusis, Presbyopia, Pressure Injuries) are each represented as an independent study unit (SU-GM-03 through SU-GM-13), consistent with the project's geriatrics scope principle that broad syndromes may warrant distinct units where source content and MCC evidence support it - most carry their own dedicated MCC Medical Expert objective.

## Unrecoverable coverage gaps

None. Chapter GM's `derived/scope_packets/GM.json` reports 0 `unresolved_headings` and 0 dropped/merged-away topic content.
