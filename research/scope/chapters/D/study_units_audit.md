# Dermatology (Chapter D) Study-Unit Consolidation Audit

**Generated:** 2026-08-25
**Result:** ✅ PASS (fully accounted, 0 unassigned source nodes)

## Coverage

- Raw TOC nodes: 42 (1 chapter root, 15 level-2 section nodes, 26 level-3 topic nodes)
- Derived study units: 48
- Unassigned source nodes: 0
- Organizational header nodes accounted for (not units, not dropped): 3 — `D` (chapter root, represented
  narratively by all study units below, per the A/C/CP convention), `D.S04` ("Drug Eruptions" umbrella,
  content fully covered by its 5 T-children), `D.S05` ("Heritable Disorders" umbrella, content fully covered
  by its 5 T-children).
- **Total accounted:** 42/42 (fully accounted)

## Source-quality context

Chapter D's TOC page (pdf 189) is printed in two columns; OCR interleaved the two columns' text onto shared
lines. This produced two distinct classes of structural damage, both resolved via body-heading confirmation
(raw OCR + `derived/toronto-notes-2025/clean-ocr/` normalized text) rather than left unresolved:

1. **Two-column node-title merges (~20 of 42 nodes).** A node's `title` in `toc_inventory.json` concatenates
   two real, physically distant headings that happened to share a TOC line (e.g. `D.S06`: "Cysts" [Common Skin
   Lesions, pdf 196] + "Malignant Skin Tumours" [pdf 228]). Each such node is split into 2+ study units, one
   per real fragment — see `same_page_merge_resolutions` in `study_units.json` for the full per-node ledger.
   14 node_ids are consequently cited by 2 or more study units (`double_assigned_source_nodes` in
   `study_units_audit.json`) — this is the *expected, correct* signature of a resolved merge, not a
   duplication error.
2. **Headings dropped entirely (9 headings, no node at all).** 7 are recorded UNRESOLVED in
   `research/tn2025/unresolved_headings.json` (Introduction to Skin, Morphology, Patterns and Distribution,
   Differential Diagnoses for Common Presentations, Common Skin Lesions, Acneiform Eruptions, Papulosquamous
   Diseases); 2 further headings with real body content were found via full manual reading of pdf 189-246 but
   have no `unresolved_headings.json` entry either (Pre-Malignant Skin Conditions, Dermatologic Therapies) —
   plus Sunscreens/Preventative Therapy and Landmark Dermatology Trials, which do appear as the "other half" of
   two of the 7 documented UNRESOLVED raw OCR lines. Of these 9, 2 (Common Skin Lesions, Acneiform Eruptions)
   needed no standalone unit because all of their child subsections are already independently accounted for
   via existing (merged) nodes. The remaining 7 were each assigned a synthetic `UNCATALOGUED:D-*` id per the
   documented convention and represented as their own study unit(s) — 9 study units in total carry an
   `UNCATALOGUED:` id (`uncatalogued_synthetic_id_units` in `study_units_audit.json`).

This is a substantially higher merge/drop rate than chapters A or CP, reflecting genuinely worse source OCR
for this specific TOC page rather than any change in methodology; see `crosswalk_audit.json`'s
`chapter_notes.toc_structural_quality` and `research/scope/chapters/D/review_items.json` for the corresponding
informational review-queue entries.

## Consolidation approach

Per the frozen methodology (a TOC node is not automatically a study unit; generic child headings — Epidemiology,
Etiology, Investigations, Management, etc. — are folded into their parent diagnosis rather than split out):

- Each named diagnosis/presentation with its own dedicated Toronto Notes subsection became its own study unit
  (e.g. Acne Vulgaris, Psoriasis, SJS/TEN, Malignant Melanoma, Scabies) — these are the chapter's DIRECT/CORE
  content.
- Short, thematically-related, lower-yield subheadings were combined into a single unit (e.g. "Other
  Eczematous Dermatoses" combines 7 short dermatitis subtypes; "Heritable Genodermatoses" combines 3 rare
  single-gene disorders).
- Pure cross-references to other chapters ("see Plastic Surgery, PL8"; "see Pediatrics, P62") were combined
  into one CROSS_DISCIPLINE unit (SU-D-44) rather than given independent dermatology-chapter coverage.
- Pure reference/bibliographic content (Acronyms, Landmark Trials, References) is REFERENCE_ONLY with
  `minimum_question_coverage: 0` and a documented `zero_question_reason`.

See `study_units.json`'s `methodology_note`, `same_page_merge_resolutions`, and `unresolved_heading_resolution`
fields for the complete per-node resolution ledger, and `study_units_audit.json` for the machine-checkable
coverage accounting.
