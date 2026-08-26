# MCC Scope Crosswalk Scaling — Progress Ledger

**This file is the canonical resume point.** Conversation history must
never be required to resume this work — read this file plus `git log`,
then continue.

- Schema version: `1.0` (frozen at commit `a8e2ff7`, "feat: freeze MCC
  scope crosswalk schema")
- Total chapters: 32
- Validated pilots (schema-freeze source of truth): Cardiology (`C`),
  ELOM (`ELOM`)

## Status

| | |
|---|---|
| Completed | 10 / 32 (`C`, `ELOM`, `A`, `CP`, `D`, `ER`, `E`, `FM`, `G`, `GS`) |
| Next chapter | **GM — Geriatric Medicine** |
| Current chapter (in progress) | none |
| Review-required | none |
| Failed | none |
| Last completed commit | `64d185c` — scope: map GS General and Thoracic Surgery |
| Working tree | clean as of this checkpoint |

## Processing order (remaining, one at a time)

1. GM — Geriatric Medicine *(next)*
2. GY — Gynecology
3. H — Hematology
4. ID — Infectious Diseases
5. MG — Medical Genetics
6. MI — Medical Imaging
7. NP — Nephrology
8. N — Neurology
9. NS — Neurosurgery
10. OB — Obstetrics
11. OP — Ophthalmology
12. OR — Orthopedic Surgery
13. OT — Otolaryngology
14. P — Pediatrics
15. PM — Palliative Medicine
16. PL — Plastic Surgery
17. PS — Psychiatry
18. PH — Public Health and Preventive Medicine
19. R — Respirology
20. RH — Rheumatology
21. U — Urology
22. VS — Vascular Surgery

## Chapter notes

- **A (Anesthesia)**: 38 study units from 59 TOC nodes. Resolved two
  same-page TOC merges (`A.S01` -> 3 units citing raw OCR pdf page 56;
  `A.S06` -> 2 units citing raw OCR pdf page 74) and one heading dropped
  entirely from `toc_inventory.json` ("Monitoring", previously
  `UNRESOLVED` in `research/tn2025/unresolved_headings.json`), resolved
  via body-heading confirmation against raw OCR pdf page 61 and recorded
  as `SU-A-07` with a synthetic `UNCATALOGUED:` source id (documented in
  full in `study_units.json` and flagged `affects_global_toc: true` in
  `research/scope/chapters/A/review_items.json` for a future TOC-pass).
  0 invalid MCC IDs, 0 unflagged WEAK mappings, 0 hygiene violations, 0
  UNCERTAIN classifications. 2 WEAK mappings flagged for scope review
  (see review queue).
- **CP (Clinical Pharmacology)**: 20 study units from 26 TOC nodes (25
  leaf nodes, all accounted for). Resolved three same-page TOC merges
  (`CP.S01`, `CP.S04`, `CP.S06`) via raw OCR. `CP.S06`'s "References"
  merge was checked against the ELOM `ELOM.S04` misattribution pattern
  and confirmed to be a genuine bibliography (correctly attributed, kept
  as its own zero-question REFERENCE_ONLY unit) rather than a
  misattachment. MCC evidence concentrates on objective 125 "Prescribing
  practices" (15/17 citations) with distinct, substantive per-unit
  rationale for each — verified this reflects a real gap in MCC's
  clinical-presentation-organized taxonomy for general pharmacology
  content, not lazy mapping (cross-checked against
  `research/mcc/objectives_registry.json` for missed better-fit
  objectives; none found). 0 invalid MCC IDs, 0 WEAK mappings, 0 hygiene
  violations, 0 UNCERTAIN classifications.
- **D (Dermatology)**: 48 study units from 42 TOC nodes (largest chapter
  processed so far). Chapter D's TOC page had unusually poor two-column
  OCR: ~20 of 42 nodes carry titles that concatenate two real,
  physically distant headings sharing a TOC line (e.g. `D.S06` merges a
  pdf-196 subsection with a pdf-228 heading 32 pages away), and 7
  headings were dropped entirely (`UNRESOLVED` in
  `research/tn2025/unresolved_headings.json`) plus 2 more silently
  dropped with no registry entry at all. All resolved via body-heading
  confirmation against raw OCR (`derived/toronto-notes-2025/clean-ocr/`,
  pdf 190-246); 9 study units carry synthetic `UNCATALOGUED:` source
  ids. Flagged `affects_global_toc: true` in
  `research/scope/chapters/D/review_items.json` for a future TOC-pass.
  MCC evidence concentrates on objective 38 "Skin and integument
  conditions" (39/41 citations) — the only Medical Expert objective
  covering general dermatology under MCC's presentation-oriented
  framework, per `CLAUDE.md` guidance; most named diagnoses therefore
  map COMPONENT rather than DIRECT, with DIRECT reserved for cases the
  objective names explicitly (e.g. melanoma) or with their own dedicated
  objective (Pruritus=85, Urticaria/angioedema=97-2). 0 invalid MCC IDs,
  0 WEAK mappings, 0 hygiene violations, 0 UNCERTAIN classifications.
- **ER (Emergency Medicine)**: 53 study units. Source-boundary
  page-number lag (`ER.S05`-`ER.S08`) resolved via body-heading
  confirmation; see `research/scope/chapters/ER/review_items.json`.
  Corrected in a follow-up commit (`fix(scope): resolve ER source
  ambiguities`) after initial mapping.
- **E (Endocrinology)**: 60 study units from 81 source nodes (clean
  single-column TOC page — 0 unresolved headings, 0 two-column merges,
  0 `UNCATALOGUED:` synthetic ids, a marked contrast with D). Only two
  structural artifacts: `E.S03.T02`/`E.S03.T03` (a single "Pre-Diabetes"
  heading split by OCR line-wrap, merged into `SU-E-08`) and
  `E.S04.T04`/`E.S04.T05` (TSH/ACTH nodes whose entire body content is a
  one-line cross-reference to the Thyroid/Adrenal Cortex sections,
  folded into `SU-E-17`). The scope packet's bounded candidate MCC set
  (27 entries) was mostly generic cross-discipline Study-Smarter noise
  and lacked objectives for the chapter's core content; targeted
  `search-mcc-objectives` full-registry searches surfaced 12 additional
  relevant objectives (Hyperglycemia=130, Hypoglycemia=129, Stature
  abnormal=101, Hypertension=9-1, Hypokalemia=79-2, Hyponatremia=99-2,
  Fatigue=33, Obesity=118-1, Polyuria=110-2, Amenorrhea=56-1, Breast
  masses/gynecomastia=10-1, Weight loss=118-2) — see
  `research/scope/chapters/E/crosswalk_audit.md` for the full search log,
  including confirmed-absent objectives (no dedicated MCC objective
  exists for thyroid-disease specifics beyond the general neck-mass
  objective, adrenal disorders, pituitary disorders, or osteoporosis).
  18 distinct MCC objective IDs cited (vs. 3 for D), reflecting MCC's
  granular presentation-based framework for this body system. 0 invalid
  MCC IDs, 0 WEAK mappings, 0 hygiene violations, 0 UNCERTAIN
  classifications, 553/553 project tests passing.
- **FM (Family Medicine)**: 57 study units from 63 TOC nodes (63/63
  accounted for: 4 organizational headers, 59 leaf/section nodes). Two
  `UNRESOLVED` headings from `derived/scope_packets/FM.json`
  (`Acronyms`, `Antimicrobial/Antiviral/Antifungal Quick Reference`) and
  one structurally distinct `merged_duplicate_headings` entry
  (`Complementary and Integrative Medicine`, absorbed into `FM.S05`)
  resolved via body-heading confirmation against raw OCR
  (`derived/toronto-notes-2025/clean-ocr/`, pdf 378, 429-431); all three
  represented with synthetic `UNCATALOGUED:` source ids, flagged
  `affects_global_toc: true` in
  `research/scope/chapters/FM/review_items.json`. FM is explicitly
  cross-cutting per task instructions: 33 `DIRECT`, 15 `COMPONENT`, 5
  `SUPPORTING_KNOWLEDGE`, 2 `REFERENCE_ONLY`, 1 `CROSS_DISCIPLINE`
  (`SU-FM-53` Power of Attorney/Advance Directives, deferring to the
  already-completed ELOM chapter), 1 `UNCERTAIN` (`SU-FM-35` Epistaxis —
  no MCC objective found after targeted registry search for
  'epistaxis'/'nose bleed'/'nasal bleeding'/'hemorrhage'; left UNCERTAIN
  rather than forced). 26 of 57 units carry a `cross_discipline_note`
  documenting overlap with an already-completed or not-yet-mapped
  chapter (ER, E, D, ELOM, and 10 not-yet-mapped disciplines) for the
  later global chapter-overlap audit — full list in
  `research/scope/chapters/FM/review_items.json`. Targeted
  `search-mcc-objectives` searches surfaced non-obvious matches for
  several presenting problems with no title-obvious objective (BPH →
  "Lower urinary tract symptoms"=111-1; Depression → "Depressed
  mood"=59-1; Diabetes Mellitus → "Hyperglycemia"=130; Rash → "Skin and
  integument conditions"=38); confirmed-absent objectives include
  osteoarthritis, osteoporosis, sinusitis, asthma/COPD, and a
  comprehensive STI objective (mapped COMPONENT to the closest available
  match with the coverage gap documented in `mapping_rationale`). 0
  invalid MCC IDs, 0 WEAK mappings, 0 hygiene violations, 1 UNCERTAIN
  classification, validator PASS, 553/553 project tests passing.
- **G (Gastroenterology)**: 62 study units from 84 source nodes (75
  leaf/topic nodes + 1 chapter root + 8 organizational section headers,
  all 75 leaf nodes accounted for, 0 missing/0 duplicated — verified
  programmatically). Chapter G is a "clean" chapter per
  `research/tn2025/toc_validation_report.json` (0 unresolved headings,
  `TOC_VALIDATION: PASS`), so no `UNCATALOGUED:` synthetic ids were
  needed. Two structural observations were investigated against
  `toc_inventory.json`'s `raw_ocr_line` (no independent raw-OCR/body-
  heading corpus exists for this project beyond `toc_inventory.json`
  itself) and confirmed as the book's genuine printed structure rather
  than extraction artifacts: (1) `G.S04` ("Small and Large Bowel",
  G14-G41) spans both lower-GI/bowel topics (T01-T21) and hepatobiliary/
  liver topics (T22-T36) under one section heading — no section split
  was invented; study units were built at T-node granularity instead
  (`SU-G-16` through `SU-G-43`); (2) `G.S05` is titled "Liver
  Transplantation" but its three T-children (Portal Hypertension,
  Hepatic Encephalopathy, Ascites) are cirrhosis-complication topics,
  not transplant-procedure content — documented per-unit rather than
  relabeling the canonical heading. 21 of 62 units consolidate 2-5
  T-nodes into one study unit where TN's own subtopics are
  etiology-specific subtypes of one disease sharing one MCC evidence
  citation (e.g. PUD + H. pylori/NSAID/stress-induced ulceration; viral
  hepatitis A/B/C/D; UGIB + Mallory-Weiss; LGIB + diverticular bleeding;
  colorectal carcinoma + polyps) — see
  `research/scope/chapters/G/study_units_audit.md` for the full list.
  The scope packet's bounded candidate MCC set (35 entries) was mostly
  generic cross-discipline Study-Smarter noise (SIDS, personality
  disorders, hypertension, etc. matched only via the broad `Medicine`
  discipline tag) and covered only 11 genuinely GI-relevant objectives;
  targeted `search-mcc-objectives` full-registry searches for
  'gastroesophageal reflux', 'peptic ulcer', 'dyspepsia', 'inflammatory
  bowel disease', 'irritable bowel', 'celiac', 'colorectal cancer',
  'hepatitis', 'cirrhosis', 'pancreatitis', 'gallstones', 'cholecystitis',
  'ascites', and several related terms all returned **zero** direct-
  title matches — a genuine MCC-objectives-registry coverage gap for
  named GI diagnoses, the same pattern chapter E's review flagged and
  asked to be checked in Gastroenterology. Every affected topic was
  still mapped with STRONG or MODERATE evidence by locating its
  explicit appearance inside a nearby presentation-based objective's own
  retrieved `causal_conditions` text (objective 14 "Chest pain" alone
  explicitly names esophagitis, PUD, Mallory-Weiss, and biliary
  disease/pancreatitis as differentials; objective 6-2 "Lower
  gastrointestinal bleeding"'s own key-objective text explicitly covers
  colorectal cancer screening; objective 1 "Abdominal distension"
  explicitly enumerates ascites with the transudative/exudative
  framework) — see `research/scope/chapters/G/crosswalk_audit.md` for
  the full search log. 18 distinct MCC objective IDs cited, 83 total
  evidence citations (58 STRONG, 23 MODERATE, 2 WEAK). Only 2 units
  (Wilson's Disease, Autoimmune Pancreatitis) had no explicit or
  generic-category textual anchor and were left `SPECIALIST_DETAIL`/
  WEAK/`requires_scope_review: true` rather than forced. 0 invalid MCC
  IDs, 0 hygiene violations, 0 UNCERTAIN classifications, validator
  PASS, 553/553 project tests passing.
- **GS (General and Thoracic Surgery)**: 80 study units from 101 source
  nodes (all accounted for and verified programmatically — 0 gaps/
  duplicates, `source_accounting: PASS`). GS is by far the most
  structurally corrupted chapter mapped so far: the deterministic
  `prepare-scope-chapter` tool itself flagged 2 `UNRESOLVED` headings
  ("Abdominal Hernia", "Inflammatory Bowel Disease" — neither has a
  `toc_inventory.json` node, so neither could be represented as a study
  unit; logged as coverage gaps rather than guessed), and 6 additional
  section/topic nodes independently show the same two-column TOC-OCR
  bleed pattern confirmed elsewhere in this project (chapters D and G):
  `GS.S12` ("Anorectum") contains 4 unrelated Liver topics as T08-T11;
  `GS.S16` ("Breast") merges "Short Gut Syndrome" with "Benign Breast
  Lesions" in one T-node; `GS.S17` ("Groin Hernias Surgical
  Endocrinology") merges two section titles, with one T-child
  ("Appendix ... Advent Gland y") corrupted beyond confident resolution
  (left `UNCERTAIN`, `SU-GS-75`) and another ("Appendicitis Pancreas")
  partially recovered (`SU-GS-77`, `Appendicitis`, `UNRESOLVED` page
  precision); `GS.S18`/`GS.S19` each merge a second section title
  ("Pediatric Surgery", "Skin Lesions") with no recoverable independent
  content; `GS.S21` ("Landmark ... Trials", raw_ocr_line HIGH-confidence
  confirmed as the genuine printed title) has T-children that are
  actually Large Bowel Obstruction disease content, not trial names. No
  independent raw-OCR/body-heading corpus beyond `toc_inventory.json`
  exists for this project (same limitation as chapters G and D before
  it), so every case was resolved per `docs/scope-chapter-workflow.md`'s
  resolution order using only canonical TOC data and `raw_ocr_line` —
  either by textually splitting an obvious two-topic merge, retaining a
  legible real-world term found within a corrupted fragment with
  `UNRESOLVED` page precision, or explicit `UNCERTAIN` classification
  where even topic identity could not be confirmed. No Toronto Notes
  heading was invented or silently relabeled. 6 T-node consolidations
  (e.g. Cholelithiasis+Biliary Colic; Acute+Acalculous Cholecystitis;
  Postoperative Dyspnea+Respiratory Complications; Paralytic Ileus
  duplicated across `GS.S04.T08`/`GS.S07.T02` merged into one unit) —
  see `research/scope/chapters/GS/study_units_audit.md`. MCC evidence:
  the packet's bounded candidate set (48 entries) covered most core
  presentations (Acute abdominal pain=3-2, Abdominal distension=1,
  Jaundice=49, GI bleeding=6-1/6-2, Hernia=2-4); targeted
  `search-mcc-objectives` full-registry searches confirmed 0-1 direct
  title matches for 'appendicitis', 'bowel obstruction', 'cholecystitis',
  'pancreatitis', 'colorectal cancer', 'lung cancer', 'pneumothorax',
  'postoperative', and 'preoperative' — the same MCC-registry-coverage-
  gap pattern already flagged in chapters E and G — resolved by locating
  each diagnosis's explicit appearance inside a nearby presentation
  objective's own `causal_conditions` text (e.g. 74-3 "Pre-operative
  medical evaluation" for `GS.S03`; 1 "Abdominal distension" explicitly
  naming volvulus/toxic megacolon/adynamic ileus). 21 distinct MCC
  objective IDs cited. `MAPPING_STRENGTH_COUNTS: STRONG=50 MODERATE=46
  WEAK=10`; 1 `UNCERTAIN` classification (`SU-GS-75`); 2
  `CROSS_DISCIPLINE` units (`SU-GS-22` COPD deferring to not-yet-mapped
  Respirology; `SU-GS-40` Familial Colorectal Cancer Syndromes deferring
  to not-yet-mapped Medical Genetics). 0 invalid MCC IDs, 0 hygiene
  violations, validator PASS, 553/553 project tests passing.

## Resume protocol (per Phase 3C instructions)

1. Read `reports/scope_scaling_progress.json`.
2. Verify `git status` is clean and `last_completed_commit` exists in
   `git log`.
3. Spawn exactly **one** fresh subagent for `next_chapter`. Never more
   than one chapter agent concurrently.
4. Wait for it to finish. Independently verify its output (schema
   validation, node accounting, invalid-ID count = 0, WEAK flagging,
   mcc_evidence hygiene, no reintroduced `target_questions`, jurisdiction
   validity, unresolved mappings preserved, no questions generated).
5. Run chapter-specific validation/audit, then the full project test
   suite.
6. If PASS: commit as `scope: map <chapter-code> <chapter-name>`, update
   this ledger (`completed_chapters`, `next_chapter`,
   `last_completed_commit`, `updated_at`), rebuild
   `research/scope/review_queue.json` from all chapter-local
   `review_items.json` files.
7. Only then spawn the next chapter's agent.

## Known incident

An earlier attempt in this project launched 11 chapter-processing
subagents in parallel (in violation of the now-explicit
one-at-a-time rule). All 11 failed identically with a session API
limit error before writing any output; no partial chapter files were
left behind (verified — only `C` and `ELOM` exist under
`research/scope/chapters/`). This ledger and the strict sequential
loop above exist specifically to prevent a repeat.
