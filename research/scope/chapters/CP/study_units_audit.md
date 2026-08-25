# Clinical Pharmacology (Chapter CP) Study-Unit Consolidation Audit

**Generated:** 2026-08-25
**Result:** ✅ PASS

## Coverage

- Raw TOC nodes: 26 (1 chapter node, 6 level-2 section nodes, 19 level-3 topic nodes)
- Raw leaf nodes: 19
- Derived study units: 20
- Unassigned source nodes: 0
- Organizational header nodes accounted for (not units, not dropped): 1 (the chapter root, `CP` — see note below)
- **Total accounted:** 26/26 (fully accounted)

Note on the chapter root: `CP` is never cited as a `source_node_id` of any study unit — consistent with
Chapters A and C's own convention that the chapter root is represented narratively ("represented by all
study units below") rather than literally cited. All 25 remaining nodes are cited by at least one unit.

## Same-Page TOC Merges Resolved

**CP.S01 ("ACFOMYMS", pdf 176, TN CP2):** Raw OCR of the TOC page (`0175.json`) confirms two genuine printed
headings share the TOC's CP2 page label: "ACFOMYMS" and "General Principles" (the latter itself printing three
further unindented sub-entries: Drug Nomenclature, Phases of Clinical Drug Testing, Drug Administration). Raw
OCR of the body page (`0176.json`) confirms the acronym table is immediately followed by a distinct bold
"General Principles" heading. Split into SU-CP-01 (Acronyms) and SU-CP-02 (General Principles: Drug
Nomenclature + Phases of Clinical Drug Testing, combined as thin orientation-level content) / SU-CP-03 (Drug
Administration, kept separate given its substantially deeper Table-1-based route-selection content).

**CP.S04 ("Adverse Drug Reactions", pdf 185-186, TN CP11-CP12):** Raw OCR of the TOC page (`0175.json`)
confirms two genuine printed headings share the TOC's CP11 page label: "Adverse Drug Reactions" (with sub-
entries Approach to Suspected ADRs, Drug Interactions) and "Autonomic Physiology & Pharmacology" (with sub-
entries Parasympathetic NS, Sympathetic NS, Opioid Therapy and Chronic Non-Cancer Pain). Raw OCR of body pages
`0185.json`/`0186.json` confirms both headings are genuine, independently-bolded body headings. Split into
SU-CP-13 (Adverse Drug Reactions + Approach to Suspected ADRs), SU-CP-14 (Drug Interactions, kept separate
given its extensive named-interaction sidebar), SU-CP-15 (Autonomic Physiology & Pharmacology: Parasympathetic
+ Sympathetic NS), and SU-CP-16 (Opioid Therapy and Chronic Non-Cancer Pain — thematically unrelated to
autonomic physiology despite its TOC nesting under that heading, so kept as its own unit rather than folded in).

**CP.S06 ("Landmark Pharmacology Trials", pdf 188, TN CP14):** Raw OCR of the TOC page (`0175.json`) confirms
two genuine printed headings share the TOC's CP14 page label: "Landmark Pharmacology Trials" and "References".
Raw OCR of the body page (`0188.json`) confirms both are genuine, independently-bolded body headings. **This is
structurally similar to the ELOM `ELOM.S04` case but resolves differently**: where ELOM's "References" nodes
turned out to be a misattributed disclaimer paragraph (not a genuine bibliography), CP.S06's "References"
heading here IS confirmed — by direct reading of the body text — to be a genuine, correctly-attributed,
>30-entry chapter bibliography (author/journal/year citations throughout, e.g., Boyer's "The serotonin
syndrome" NEJM 2005, Busse et al.'s opioid-guideline CMAJ 2017), with no clinical/testable prose mixed in. No
content required reattachment. Split into SU-CP-19 (Landmark Pharmacology Trials, REFERENCE_ONLY) and SU-CP-20
(References/Bibliography, REFERENCE_ONLY) — both zero-question, matching the treatment given to the equivalent
genuine References/Landmark-Trials sections in Chapters A and C.

## Unresolved Headings

`research/tn2025/unresolved_headings.json` records 0 entries with `chapter_code == "CP"` (independently
verified by filtering all 27 total entries in that file — none belong to chapter CP). A sanity pass over all of
CP's body pages (176–188, `derived/toronto-notes-2025/ocr/pages/0176.json` through `0188.json`) found no further
structurally-off content beyond the three same-page merges documented above — no headings were dropped, and no
topic child's content was thematically inconsistent with its declared section beyond the merge cases already
resolved.

## Organizational Header Nodes (Confirmed via Raw OCR, Not Fabricated)

- **CP**: Chapter root container - represented by all study units below.
- **CP.S02**: "Pharmacokinetics" - confirmed via raw OCR (pdf 177) to carry only two brief definitional bullets
  ("what the body does to the drug"; the ADME process list) before its first child topic "Absorption" begins
  with no other intervening content. Its two bullets are folded into SU-CP-04's framing. Its 10 topic children
  became 7 study units (SU-CP-04..SU-CP-11; Pharmacodynamics + Effectiveness and Safety + Therapeutic Indices
  combined into SU-CP-09).

## Double-Assigned Nodes (All Justified — Same-Page-Merge Splits)

- **CP.S01**: cited by [`SU-CP-01`, `SU-CP-02`] (same-page-merge split; see resolution notes above)
- **CP.S04**: cited by [`SU-CP-13`, `SU-CP-15`] (same-page-merge split; see resolution notes above)
- **CP.S06**: cited by [`SU-CP-19`, `SU-CP-20`] (same-page-merge split; see resolution notes above)

No other node is double-assigned; every other topic-level node maps to exactly one study unit.

## Page Traceability

All 20 study units' `pdf_page_range` values fall within the chapter's own OCR-confirmed bounds (pdf 175–188):
✅ valid. 19 of 20 units carry EXACT_SECTION precision because chapter CP's derivation read every one of the
chapter's raw OCR body pages (176–188) directly rather than relying only on `toc_inventory.json`'s flat 3-level
structure; SU-CP-11 (Variability in Drug Response) uses EXACT_TOPIC precision reflecting a body-confirmed
single-page tightening of the TOC node's own section-wide declared range (see study_units.json).

## Summary

Raw TOC nodes: 26
Raw leaf nodes: 19
Derived study units: 20
Unassigned source nodes: 0
Justified multi-assignments: 3 (CP.S01 x2, CP.S04 x2, CP.S06 x2 — all same-page-merge splits)

**Study-unit derivation: PASS**
