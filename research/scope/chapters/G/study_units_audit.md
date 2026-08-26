# Gastroenterology (Chapter G) Study-Unit Consolidation Audit

**Generated:** 2026-08-25
**Result:** ✅ PASS (fully accounted, 0 unassigned source nodes)

## Coverage

- Raw source nodes (`derived/scope_packets/G.json`): 84 (1 chapter root, 11 level-2 section nodes, 72 level-3
  topic nodes)
- Derived study units: 62
- Unassigned source nodes: 0
- Organizational header nodes accounted for (not units, not dropped): 9 — `G` (chapter root, represented
  narratively by all study units below, per the C/ELOM/A/CP/D/E/FM convention), plus 8 section-level umbrella
  headings with no independent content beyond their T-children: `G.S01` (Acronyms), `G.S02` (Esophagus),
  `G.S03` (Stomach and Duodenum), `G.S04` (Small and Large Bowel), `G.S05` (Liver Transplantation — see title
  mismatch below), `G.S06` (Biliary Tract), `G.S07` (Pancreas), `G.S08` (Clinical Nutrition).
- Three sections have no T-children and are themselves leaf content nodes, each given its own study unit:
  `G.S09` (Common Medications → SU-G-60), `G.S10` (Landmark Gastroenterology Trials → SU-G-61), `G.S11`
  (References → SU-G-62).
- **Total accounted:** 84/84 (fully accounted; verified programmatically — every one of the 72 topic nodes plus
  the 3 leaf sections appears in exactly one study unit's `source_node_ids`, with no duplicates and no
  omissions).

## Source-quality context

Chapter G is a **clean** chapter per `research/tn2025/toc_validation_report.json`: 0 unresolved headings for
chapter G, `TOC_VALIDATION: PASS`, all 11 section nodes extracted at HIGH confidence via `TOC_OCR`, and all 72
topic nodes extracted via `TOC_OCR_UNANCHORED` (confidence LOW — meaning per-topic page anchoring within the
section's page range was not independently confirmed, though the topic titles themselves are unmerged,
unambiguous, and directly readable from the TOC). No independent raw-OCR or body-heading-confirmation corpus
exists for this project beyond `toc_inventory.json` itself, so canonical-TOC `raw_ocr_line` fields (which record
the literal OCR'd TOC text before any structural parsing) were used as the next-best evidence per the resolution
order in `docs/scope-chapter-workflow.md` (canonical TOC → raw/normalized OCR → body-heading confirmation →
nearby pages → unresolved).

Two genuine structural points were investigated and resolved against the canonical TOC's `raw_ocr_line`:

- **G.S04 spans two organ systems under one heading.** `G.S04` ("Small and Large Bowel", G14–G41, 28 pages)
  contains 36 T-children split between lower-GI/bowel disease (T01–T21: diarrhea, IBD, IBS, GI bleeding,
  colorectal neoplasia, anorectal disease) and hepatobiliary/liver disease (T22–T36: LFT interpretation, viral
  hepatitis, autoimmune/drug-induced/genetic liver disease, cirrhosis, HCC). `raw_ocr_line` confirms
  `"Small and Large Bowel... G14"` is the book's actual printed TOC entry (HIGH confidence, not an OCR-merge
  artifact affecting reading order — chapter G has 0 unresolved headings). No section-node split was invented;
  study units were instead built at T-node granularity (SU-G-16 through SU-G-43), so bowel and liver content
  remain fully separated topic-by-topic in the crosswalk despite sharing one parent TOC section.
- **G.S05 is titled "Liver Transplantation" but its content is cirrhosis complications.** `raw_ocr_line`
  confirms `"Liver Transplantation... G42"` is the exact printed heading (HIGH confidence), yet its three
  T-children are Portal Hypertension, Hepatic Encephalopathy, and Ascites — cirrhosis-complication topics
  relevant to transplant-*listing* criteria, not transplant surgical/procedural content. This mismatch is
  documented per-unit (SU-G-44 through SU-G-46) rather than silently relabeling the canonical heading, per the
  accuracy rule against inventing/altering Toronto Notes headings.

No node in this chapter required an `UNCATALOGUED:` synthetic id and no source node is cited by more than one
study unit — chapter G's TOC page produced a clean single-pass extraction with only the two title/scope
observations above (neither is an extraction defect).

## Consolidation approach

Per the frozen methodology (a TOC node is not automatically a study unit; generic umbrella/organizational
headings with no independent content beyond their children are documented as `organizational_header_nodes`
rather than split out), the large majority of G's 72 topic nodes became 1:1 study units (each a distinct named
diagnosis with its own dedicated Toronto Notes subsection, e.g. Celiac Disease, Crohn's Disease, Cirrhosis,
Ascending Cholangitis, Acute Pancreatitis). Consolidation into a single study unit across multiple T-nodes was
applied only where TN's own T-children are etiology-specific subtypes of one disease entity sharing one MCC
evidence citation, not merged on clinical-similarity judgment alone:

- **SU-G-08** (3 nodes): Esophageal diverticula, peptic stricture, and webs/rings — all intrinsic
  mechanical/structural causes of esophageal dysphagia, named together in MCC objective 26's own
  causal-conditions text.
- **SU-G-14** (4 nodes): Peptic ulcer disease, H. pylori-induced, NSAID-induced, and stress-induced
  ulceration — etiology subtypes of one disease sharing objectives 6-1/3-2/14's evidence.
- **SU-G-17** (2 nodes): Acute diarrhea + traveller's diarrhea (an infectious subtype of the same objective,
  22-1).
- **SU-G-26** (2 nodes): Upper GI bleeding + Mallory-Weiss tear (explicitly named as a traumatic cause within
  objective 6-1's own causal-conditions list).
- **SU-G-28** (2 nodes): Lower GI bleeding + diverticular bleeding (explicitly named within objective 6-2's own
  causal-conditions list).
- **SU-G-30** (2 nodes): Colorectal carcinoma + polyps (one neoplasia continuum sharing objectives 6-2/74's
  screening-based evidence).
- **SU-G-34** (5 nodes): Acute viral hepatitis (general) + hepatitis A/B/C/D — TN presents a general overview
  followed by four virus-specific subsections; MCC has no per-virus objective, only a general "infection"
  etiology category under objectives 49/52/3-2.

No generic subheadings (Epidemiology/Pathophysiology/Investigations/Management as separate TOC nodes) were
encountered in this chapter's TOC — all 72 topic nodes are named diagnoses/topics, not disease-internal
subsections, so the CLAUDE.md guidance on consolidating generic subheadings within one disease did not apply
as a distinct consolidation category here (it is implicitly satisfied since each named-disease study unit's
`testable_competencies` already spans that disease's epidemiology/clinical features/investigations/management
as one unit, consistent with how TN itself presents each topic).

Three background/overview topics (SU-G-01, SU-G-02, SU-G-11) and one lab-interpretation topic (SU-G-53) were
kept as their own zero-question SUPPORTING_KNOWLEDGE units (anatomy/physiology/imaging-modality overview and
enzyme-interpretation background) rather than folded into a neighboring disease unit, since each spans multiple
downstream disease units rather than belonging to one.
