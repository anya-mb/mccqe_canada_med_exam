# Anesthesia (Chapter A) Study-Unit Consolidation Audit

**Generated:** 2026-08-25
**Result:** ✅ PASS

## Coverage

- Raw TOC nodes: 59
- Raw leaf nodes: 42
- Derived study units: 38 (37 from catalogued TOC nodes + 1 from an independently-resolved uncatalogued heading, see below)
- Unassigned source nodes: 8
- Organizational header nodes accounted for (not units, not dropped): 8
- **Total accounted:** 59/59 (fully accounted)

## Same-Page TOC Merges Resolved

**A.S01 ("Acromyms", pdf 56-57, TN A2-A3):** Raw OCR of the TOC page (`0055.json`) and body pages
(`0056.json`, `0057.json`, `0058.json`) confirms three genuine printed headings share the TOC's A2
page label: "Acromyms", "Overview of Anesthesia", "Preoperative Assessment". Split into SU-A-01
(Acronyms), SU-A-02 (Overview of Anesthesia), SU-A-03 (Preoperative Assessment + its three topic
children). Body-heading search additionally found that two of A.S01's topic children
("Preoperative Investigations", "American Society of Anesthesiology Classification") are physically
printed on pdf page 58 (TN A4) rather than pdf 56-57 as the TOC node's own A2-A3 range implies - a
genuine page-boundary content overflow. SU-A-03's `pdf_page_range` is tightened to `[56,58]` to
reflect this body-confirmed span, overriding the TOC node's nominal declaration per protocol step 4.

**A.S06 ("Maintenance", pdf 74, TN A20):** Raw OCR of `0074.json` shows the true structure differs
from what the TOC's three-way listing ("Maintenance", "Extubation", "Complications of Extubation")
implies: "Maintenance" and "Complications of Extubation" ARE both genuine, independently-bolded body
headings, but "Extubation" is NOT — its readiness-criteria/procedure content is nested, unlabeled,
inside the "Maintenance" heading's own bullet list. A.S06 has zero topic children in
`toc_inventory.json`, so both resolved study units (SU-A-20, SU-A-21) necessarily cite the same
parent node A.S06 as source (no finer-grained child node exists to redistribute across), matching
the protocol's guidance for a merged node with no children.

## Unresolved Heading Independently Resolved: "Monitoring"

`research/tn2025/unresolved_headings.json` records "Monitoring" (chapter A, source_pdf_page 55) as
UNRESOLVED — the pipeline's search window (pdf 58-66) found no line-level match above its 0.87
similarity threshold. Independent resolution: raw OCR of pdf page 61 (`0061.json`) shows the page
opens with a heading reading "Canadian Guidelines to the Practice of Anesthesia and Patient
Monitoring", followed by "Routine Monitors for All Cases" and "Elements to Monitor", and is in turn
immediately followed on the SAME page by "Airway Management"/"Airway Anatomy" — the confirmed
body-heading match already recorded for node A.S03 (`extraction_method: BODY_HEADING_CONFIRMATION`,
`matched_body_line: "Airway Management"`). This confirms the TOC's single-word abbreviated index
entry "Monitoring...A7" indexes this longer 9-word printed heading, which is why the pipeline's
literal-string search failed. Unlike A.S01/A.S06, this heading has **zero corresponding node**
anywhere in `toc_inventory.json`'s 59 chapter-A nodes — it was dropped entirely rather than merged.
Represented as SU-A-07, sourced from a synthetic id (`UNCATALOGUED:Monitoring@pdf61`) since no real
node exists to cite. This is the one addition to the chapter's study-unit count beyond the 59
catalogued nodes.

## Organizational Header Nodes (Confirmed via Raw OCR, Not Fabricated)

- **A**: Chapter root container - represented by all study units below.
- **A.S03**: 'Airway Management' - confirmed via raw OCR (pdf 61) to be a pure organizational header with zero independent content; heading is immediately followed by its first topic child 'Airway Anatomy'. Its 6 topic children became 5 study units (SU-A-08..SU-A-12; Oxygen Therapy and Ventilation combined into one).
- **A.S04**: 'Intraoperative Management' - confirmed pure organizational header (pdf 66, heading immediately followed by 'Temperature'). Its 6 topic children became 5 study units (SU-A-13..SU-A-17; Fluid Balance and IV Fluids combined into one).
- **A.S05**: 'Induction' - confirmed pure organizational header (pdf 70, heading immediately followed by 'Routine Induction vs. Rapid Sequence Induction'). Its 3 topic children became 2 study units (SU-A-18, SU-A-19; RSI-vs-routine and Induction Agents combined since agent choice is the direct consequence of the technique decision).
- **A.S08**: 'LocalAnesthesia' [sic, OCR-glued] - no independent section-level content was confirmed distinct from its own first child topic; treated as organizational header. Its 4 topic children became 3 study units (SU-A-24..SU-A-26; Local Infiltration and Topical Anesthetics combined).
- **A.S09**: 'Postoperative Care' - no independent content confirmed distinct from its single child topic. Its 1 topic child became SU-A-27.
- **A.S13**: 'Uncommon Complications' - confirmed pure organizational header (pdf 83, heading immediately followed by 'Malignant Hyperthermia'). Its 2 topic children became SU-A-33, SU-A-34.
- **A.S14**: 'Appendices' - confirmed pure organizational header (pdf 84, heading immediately followed by the first flowchart title). Its 3 topic children became 2 study units (SU-A-35, SU-A-36; the two difficult-airway flowcharts combined).

## Double/Triple-Assigned Nodes (All Justified — Same-Page-Merge Splits)

- **A.S01**: cited by ['SU-A-01', 'SU-A-02', 'SU-A-03'] (same-page-merge split; see resolution notes above)
- **A.S06**: cited by ['SU-A-20', 'SU-A-21'] (same-page-merge split; see resolution notes above)

No other node is double-assigned; every one of the 42 topic-level nodes maps to exactly one study
unit.

## Page Traceability

All 38 study units' `pdf_page_range` values fall within the chapter's own OCR-confirmed
bounds (pdf 55-90): ✅ valid. 36 of 38 units carry tight EXACT_SECTION/EXACT_TOPIC precision because chapter A's
derivation read the chapter's raw OCR pages directly rather than relying only on
`toc_inventory.json`'s flat 3-level structure; the remaining 2 (SU-A-17, SU-A-25) use
SECTION_INHERITED/MEDIUM confidence where the exact intra-page heading position was not
independently re-verified.

## Summary

Raw TOC nodes: 59
Raw leaf nodes: 42
Derived study units: 38
Unassigned source nodes: 8
Justified multi-assignments: 2 (A.S01 x3, A.S06 x2 — both same-page-merge splits)

**Study-unit derivation: PASS**
