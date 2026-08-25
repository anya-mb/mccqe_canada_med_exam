# ER (Emergency Medicine) — Study Unit Audit

Generated 2026-08-25.

- 60 raw `toc_inventory.json` nodes (1 chapter root, 14 sections, 45 topics) → 52 study units.
- Full source-node coverage: all 60 nodes accounted for (1 organizational header, 1 excluded artifact,
  58 cited by ≥1 study unit; 19 nodes cited by 2+ units).

## Why so many nodes are cited by more than one unit

Chapter ER's TOC page (pdf 247) is a badly OCR'd two-column layout: adjacent-column TOC lines were
interleaved onto single lines, so most level-3 "topic" node titles concatenate two real, unrelated
headings (e.g. `ER.S03.T04` = "Chest Pain Common Infections", merging the real Chest Pain entry with a
distant pediatric-infections entry). Each such node is cited from both of the study units representing
its two real fragments — see `study_units.json`'s `same_page_merge_resolutions` for the full per-node
breakdown.

A second, independent defect was found for nodes `ER.S05`–`ER.S08`: their recorded `start_pdf_page` /
`end_pdf_page` values are each one page earlier than where their titled content actually begins in body
OCR. Titles remain the correct structural match; study units in this range record the true confirmed
`pdf_page_range` and flag `page_mapping_precision: SECTION_INHERITED`. See `study_units.json`'s
`section_boundary_lag` field.

Three TOC fragments (`ER.S11`'s "opine ... Spinal Cord Trauma", `ER.S13`'s "Joint Pain", `ER.S14`'s
"Shortness of Breath") could not be matched to any real content in this chapter's pdf 247-308 range and
are not assigned to any study unit — flagged for coordinator review in `review_items.json`.

## Coverage check

See `study_units_audit.json` → `coverage_check` for the machine-readable accounting.
