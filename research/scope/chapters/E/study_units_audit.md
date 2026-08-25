# Endocrinology (Chapter E) Study-Unit Consolidation Audit

**Generated:** 2026-08-25
**Result:** ✅ PASS (fully accounted, 0 unassigned source nodes)

## Coverage

- Raw source nodes (`derived/scope_packets/E.json`): 81 (1 chapter root, 16 level-2 section nodes, 64 level-3
  topic nodes)
- Derived study units: 60
- Unassigned source nodes: 0
- Organizational header nodes accounted for (not units, not dropped): 12 — `E` (chapter root, represented
  narratively by all study units below, per the C/ELOM/A/CP/D convention), plus 11 section-level umbrella
  headings with no independent content beyond their T-children: `E.S02` (Dyslipidemias), `E.S03` (Disorders of
  Glucose Metabolism), `E.S04` (Pituitary Gland), `E.S05` (Thyroid), `E.S06` (Adrenal Cortex), `E.S07` (Adrenal
  Medulla), `E.S08` (Disorders of Multiple Endocrine Glands), `E.S09` (Calcium Homeostasis), `E.S10` (Metabolic
  Bone Disease), `E.S11` (Male Reproductive Endocrinology), `E.S14` (Common Medications).
- **Total accounted:** 81/81 (fully accounted)

## Source-quality context

Chapter E's TOC page (pdf 309) is a single-column layout and produced **no** two-column-merge garbling, unlike
Dermatology's badly-OCR'd two-column TOC page. `research/tn2025/unresolved_headings.json` records **zero**
entries for chapter E, and the scope packet reports `unresolved_headings: []` and `candidate_set_truncated:
false`.

The only genuine structural artifact found:

- **E.S03.T02 / E.S03.T03 line-wrap split.** A single TOC heading, "Pre-Diabetes (Impaired Glucose
  Tolerance/Impaired Fasting Glucose)", wrapped across two lines during OCR and was parsed into two separate
  topic nodes (`E.S03.T02` title truncates mid-phrase at "...Impaired Fasting", `E.S03.T03` title is the
  orphaned closing fragment "Glucose)"). Body confirmation (`clean-ocr/0315.txt`, pdf 315) shows this is one
  continuous heading/subsection, not two distinct topics or a two-column merge. Merged into a single study unit
  (SU-E-08).
- **E.S04.T04 / E.S04.T05 pure cross-reference stubs.** "Thyroid Stimulating Hormone" and "Adrenocorticotropic
  Hormone" are real, unmerged TOC nodes whose entire body content is a one-line cross-reference ("see Thyroid,
  E24" / "see Adrenal Cortex, E33", `clean-ocr/0329.txt`, pdf 329) with no independent material. Rather than
  create two content-free study units, they are folded into the pituitary-hormone-physiology unit (SU-E-17);
  their substantive disease content is fully represented under the Thyroid (SU-E-23 onward) and Adrenal Cortex
  (SU-E-36 onward) units.
- **E.S12 pure cross-reference section.** "Female Reproductive Endocrinology" is a real, unmerged section node
  whose entire body content is a single line ("see Gynecology, GY23", `clean-ocr/0363.txt`, pdf 363). Represented
  as its own CROSS_DISCIPLINE unit (SU-E-56) rather than folded elsewhere, since it is a section-level node with
  no sibling T-children to fold into.

No node in this chapter required an `UNCATALOGUED:` synthetic id (0, vs. 9 in Dermatology) and no source node is
cited by more than one study unit (0 `double_assigned_source_nodes`, vs. 17 in Dermatology) — a direct
consequence of chapter E's clean single-column TOC source.

## Consolidation approach

Per the frozen methodology (a TOC node is not automatically a study unit; generic umbrella/organizational
headings with no independent content beyond their children are documented as `organizational_header_nodes`
rather than split out):

- Each named diagnosis/presentation with its own dedicated Toronto Notes subsection became its own study unit
  (e.g. Graves' Disease, Cushing's Syndrome, Pheochromocytoma/Paraganglioma, Hypercalcemia, Osteoporosis) — the
  chapter's DIRECT/CORE_ACTION content, and the large majority of the 13 clean 1:1 Thyroid T-nodes and 7 clean
  1:1 Adrenal Cortex T-nodes.
- The one line-wrap-split heading (Pre-Diabetes) was reunited into a single unit (SU-E-08).
- Two pure cross-reference stubs sharing a parent section (TSH, ACTH) were folded into that section's physiology
  overview unit (SU-E-17) rather than given independent content-free units.
- Physiology/background subheadings (Lipid Transport, Glucose Regulation, Pituitary Hormones, Thyroid Hormones,
  Adrenocortical Hormones, Catecholamine Metabolism, Androgen Regulation/Testicular Function Tests) are their
  own SUPPORTING_KNOWLEDGE units, retained for scope completeness with `minimum_question_coverage: 0` since they
  frame rather than constitute an independently testable clinical presentation.
- Pure reference/bibliographic content (Acronyms, Common Medications drug-summary tables, Landmark Trials,
  References) is REFERENCE_ONLY with `minimum_question_coverage: 0`, each with a documented
  `zero_question_reason`, since their testable content is already captured within each diagnosis's own
  management competencies.
- The two pure "see [other chapter]" cross-references (Female Reproductive Endocrinology → Gynecology; Renal
  Osteodystrophy's underlying CKD staging/management → Nephrology) are CROSS_DISCIPLINE units scoped to only the
  endocrinology-relevant slice of content, per the same convention used for Dermatology's SU-D-15 (Psoriatic
  Arthritis → Rheumatology).

## Multi-node study units

Only 2 of 60 study units combine more than one source node (both intentional, documented merges — not OCR
artifacts):

| Unit | Source nodes | Reason |
|---|---|---|
| SU-E-01 Acronyms and Basic Anatomy Review | E.S01, E.S01.T01 | Contiguous glossary + endocrine-organ-overview figure on the same page |
| SU-E-08 Pre-Diabetes | E.S03.T02, E.S03.T03 | Single heading split by OCR line-wrap (see above) |
| SU-E-17 Hypothalamic-Pituitary Axis Physiology | E.S04.T01, E.S04.T04, E.S04.T05 | TSH/ACTH cross-reference stubs folded into physiology overview |
| SU-E-52 Androgen Regulation and Tests of Testicular Function | E.S11.T01, E.S11.T02 | Contiguous shared physiology/investigation background |
| SU-E-58 Common Endocrine Medications Reference | E.S14.T01–T05 | Five discipline-specific medication tables combined into one reference unit |

(SU-E-01, SU-E-17, SU-E-52, and SU-E-58 combine 2+ nodes by design per the methodology's "combine short/related
subheadings rather than fragment them" rule, not because of source ambiguity.)
