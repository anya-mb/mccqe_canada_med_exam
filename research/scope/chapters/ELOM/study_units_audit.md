# ELOM Study-Unit Consolidation Audit

**Generated:** 2026-08-24
**Result:** ✅ PASS

## Coverage

- Raw TOC nodes: 45
- Raw leaf nodes: 40
- Derived study units: 25
- Unassigned source nodes: 0
- Double-assigned source nodes: 0
- Organizational header nodes (not units, not dropped): 2
- Excluded OCR-artifact nodes (not units, not dropped, explicitly documented): 1
- **Total accounted:** 45 / 45 (fully accounted)

## Source Ambiguities Found and Resolved

Unlike Cardiology (one same-page merge), ELOM's TOC page contains THREE separate same-page-merge/misattribution artifacts, each resolved by directly reading the raw OCR source rather than guessed:

- ELOM.S01 merge (Acronyms + Ethical Issues in Health Care + Canadian Healthcare System, all sharing page ELOM2) - resolved by direct inspection of raw OCR page 21, split into SU-ELOM-01 through SU-ELOM-06.
- ELOM.S03 merge (Clinical Informatics and Ethical Considerations + Indigenous Health, both sharing page ELOM25) - resolved by direct inspection of raw OCR page 21, split into SU-ELOM-19 through SU-ELOM-23.
- ELOM.S04 'References' topic-children misattribution (12 genuine content nodes about the Canadian legal framework, actually printed on the chapter's TOC page 21, not the bibliography pages 52-54, misattributed as bibliography sub-topics by the TOC parser) - resolved by direct text search confirming this content's true source location, reattributed to SU-ELOM-25. One further node (T13) confirmed as a genuine OCR artifact and explicitly excluded.

## Excluded Artifact Nodes

**ELOM.S04.T13:** Raw OCR text: 'ELOMI1 Ethical, Legal, and Organizational Medicine Toronto Notes 2025'. Verified against the source: this is a corrupted copy of the chapter's own running footer from page 21 itself ('ELOM1 Ethical, Legal, and Organizational Medicine Toronto Notes 2025', with '1' misread as 'I1'), not a genuine content line. Explicitly excluded as a parsing artifact, not silently dropped - tracked here with its full raw text so the exclusion is auditable.

## Page Traceability

All 25 study units' pdf_page_range falls within the chapter's own bounds (21-54): ✅ valid

## Summary

Raw TOC nodes: 45
Raw leaf nodes: 40
Derived study units: 25
Unassigned source nodes: 0

**Study-unit derivation: PASS**

