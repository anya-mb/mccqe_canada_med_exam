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
| Completed | 18 / 32 (`C`, `ELOM`, `A`, `CP`, `D`, `ER`, `E`, `FM`, `G`, `GS`, `GM`, `GY`, `H`, `ID`, `MG`, `MI`, `NP`, `N`) |
| Next chapter | **NS — Neurosurgery** |
| Current chapter (in progress) | none |
| Review-required | none |
| Failed | none |
| Last completed commit | `c28896e` — scope: map N Neurology |
| Working tree | clean as of this checkpoint |

## Processing order (remaining, one at a time)

1. NS — Neurosurgery *(next)*
2. OB — Obstetrics
3. OP — Ophthalmology
4. OR — Orthopedic Surgery
5. OT — Otolaryngology
6. P — Pediatrics
7. PM — Palliative Medicine
8. PL — Plastic Surgery
9. PS — Psychiatry
10. PH — Public Health and Preventive Medicine
11. R — Respirology
12. RH — Rheumatology
13. U — Urology
14. VS — Vascular Surgery

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
- **GM (Geriatric Medicine)**: 20 study units from 27 source nodes (1
  chapter root + 3 organizational section headers + 23 leaf/topic
  nodes, all 27 accounted for). Clean chapter: 0 unresolved headings.
  Two OCR-corrupted section titles resolved without inventing content:
  `GM.S01` ("ACFOMYMS") represented under its legible
  `merged_duplicate_headings` alternate "Physiology and Pathology of
  Aging"; `GM.S09` ("RETEFEMCES") corrected to "References" by analogy
  with every other completed chapter's terminal bibliography section.
  `GM.S03` ("Presentations in Older Adults", 11 T-children) kept as 11
  independent study units per the geriatrics scope principle for broad
  syndromes; `GM.S04` (Driving Competency) and `GM.S06` (Geriatric
  Pharmacology) each consolidated their T-children into fewer units
  (2 facets of one fitness-to-drive competency; PK/PD mechanistic
  background vs. applied polypharmacy/prescribing). 3 `CROSS_DISCIPLINE`
  units recorded for the later global overlap audit (`SU-GM-03`
  Constipation vs. completed chapter G's `SU-G-25`, same MCC objective
  16-1; `SU-GM-04` Delirium vs. not-yet-mapped Psychiatry/Neurology;
  `SU-GM-09` Incontinence vs. not-yet-mapped Urology/Gynecology) — none
  finalized. Targeted `search-mcc-objectives` searches confirmed
  presbycusis explicitly named under objective 40's sensorineural
  causal-conditions list (STRONG) and polypharmacy/deprescribing
  explicitly named in objective 125's enabling text (STRONG), while
  immobility, driving-fitness/reporting, hospitalization hazards, and
  PK/PD mechanics have no dedicated MCC objective (classified
  SUPPORTING_KNOWLEDGE or WEAK/flagged rather than fabricated) —
  continuing the same MCC-registry-coverage-gap pattern already
  documented in chapters E, G, and GS. Driving Competency retained as
  jurisdiction-sensitive (`PROVINCIAL_TERRITORIAL`) rather than
  Canada-wide. GM/ELOM final ownership of capacity/consent-adjacent
  content explicitly deferred (no GM source node covers it
  independently). `MAPPING_STRENGTH_COUNTS: STRONG=7 MODERATE=7 WEAK=1`;
  0 `UNCERTAIN` classifications, 0 invalid MCC IDs, 0 hygiene
  violations, validator PASS, 553/553 project tests passing.

- **GY (Gynecology)**: 39 study units from 55 source nodes (1 chapter
  root + 3 organizational section headers + 51 leaf/topic nodes, all 55
  accounted for). 0 `unresolved_headings` per the deterministic tool, but
  three title/merged-heading conflicts more serious than a simple OCR
  garble: (1) `GY.S04` ("Disorders of Menstruation") carries
  `merged_duplicate_headings` 'Endometriosis' and 'Adenomyosis' in
  addition to its three T-children — both clinically distinct diagnoses
  with no dedicated child node, each broken out as its own unit
  (`SU-GY-08`, `SU-GY-09`) cited against the parent section node; (2)
  `GY.S05`'s printed title 'Fibroids' (body-heading-confirmed) conflicts
  with all three of its own T-children (Hormonal Methods, IUD, Emergency
  Postcoital Contraception), which unambiguously match its
  `merged_duplicate_headings` entry 'Contraception' — represented as
  Contraception (`SU-GY-10`); Fibroids/uterine leiomyoma was **not**
  fabricated as a separate unit since no source node carries fibroid
  content, flagged `affects_global_toc: true` for a future raw-source
  check; (3) `GY.S12`'s printed title 'SexualAbuse' with merged heading
  'Sexuality and Sexual Dysfunction' names two clinically distinct topics
  (forensic abuse/assault vs. clinical sexual dysfunction), split into
  `SU-GY-22`/`SU-GY-23`. `GY.S18`'s printed title 'References' is a
  structural mislabel — unlike every other completed chapter's genuine
  terminal bibliography, its four T-children (Menstrual Cycle, Stages of
  Puberty, PMS, PMDD) are real clinical content, represented under
  `SU-GY-02`/`SU-GY-38`/`SU-GY-39`. `GY.S15` ("Gynecological Oncology", 8
  organ-site T-children) kept as 8 independent study units per the
  GM.S03 broad-syndrome-split precedent. Pregnancy-related genuine
  GY-chapter content (Termination of Pregnancy, Early Pregnancy
  Loss/First-Trimester Bleeding, Ectopic Pregnancy) mapped here rather
  than deferred to Obstetrics, per the GY/OB boundary rule; final
  ownership deferred to a future global audit once OB is mapped. Targeted
  `search-mcc-objectives` searches confirmed no dedicated MCC objective
  for endometriosis, adenomyosis, fibroids, PCOS, PID, Bartholin gland
  abscess, or any single gynecologic cancer site — the same
  MCC-registry-coverage-gap pattern flagged in chapters E, G, GS, GM —
  resolved via nearby presentation-based objectives (Pelvic pain=73,
  Abdominal/pelvic masses=2, Vaginal bleeding=112, Vaginal
  discharge/vulvar pruritus=113) except Bartholin Gland Abscess and
  Gynecologic Surgical Site Infections, left `UNCERTAIN` rather than
  forced. 2 `CROSS_DISCIPLINE`-classified units plus 4 more units
  carrying a `cross_discipline_note` under other classifications (PCOS
  vs. completed Endocrinology; STI vs. not-yet-mapped Infectious
  Diseases/Public Health; Surgical Site Infections vs. completed GS;
  Urinary Incontinence vs. not-yet-mapped Urology) recorded for the later
  global overlap audit — none finalized. Termination of Pregnancy and
  Sexual Abuse/Assault both retained as jurisdiction-sensitive
  (`PROVINCIAL_TERRITORIAL`) with `verification_required: true` rather
  than hard-coding a single province's rule; both also touch content
  ELOM (completed) may partly own more generally (consent; abuse
  reporting) — not finalized here. `MAPPING_STRENGTH_COUNTS: STRONG=14
  MODERATE=23 WEAK=4`; 2 `UNCERTAIN` classifications (`SU-GY-18`
  Bartholin Gland Abscess, `SU-GY-21` Gynecologic Surgical Site
  Infections), 0 invalid MCC IDs, 0 hygiene violations, validator PASS,
  553/553 project tests passing.

- **H (Hematology)**: 51 study units from 92 source nodes. Found and
  resolved the most severe page-misattribution defect documented to that
  point: `H.S22`/`H.S23` carried real clinical titles (Sickle Cell
  Disease, Autoimmune Hemolytic Anemia, Microangiopathic Hemolytic
  Anemia, Hereditary Spherocytosis/Elliptocytosis, G6PD Deficiency)
  page-anchored ~40 pages away from their confirmed body content (raw
  OCR, `derived/toronto-notes-2025/clean-ocr/`); the genuine content at
  the toc-recorded location was a Landmark Hematology Trials bibliography
  plus an uncatalogued References section (`SU-H-50`, `SU-H-51`). See
  `research/scope/chapters/H/study_units.json` methodology_note for full
  detail. `MAPPING_STRENGTH_COUNTS` and full audit in
  `research/scope/chapters/H/`.

- **ID (Infectious Diseases)**: 32 study units from 75 source nodes (all
  accounted for, `source_accounting: PASS`). Surpassed H as the most
  structurally corrupted chapter mapped to date, resolved via the
  canonical raw-OCR corpus (`derived/toronto-notes-2025/clean-ocr/`, pdf
  719-778) rather than raw `pdftotext` of the source PDF (found
  significantly noisier for this densely two-column-formatted chapter).
  Six defects found: (1) `ID.S04`'s printed title 'Gastrointestinal
  Infections' is a pure cross-reference-only entry (see Gastroenterology
  G13/G18/G19/G31, Pediatrics P44) merged with a genuine 'Bone and Joint
  Infections' section (Septic Arthritis, Diabetic Foot Infections,
  Osteomyelitis) — split into `SU-ID-06` (REFERENCE_ONLY) and `SU-ID-07`
  (DIRECT); (2) `ID.S07` ('Systemic Infections') was missing a genuine
  T-child, 'Cat Scratch Disease' (confirmed pdf 741-742/ID23-24 within
  the section's own range; its title had instead been concatenated onto
  unrelated node `ID.S17`) — `SU-ID-16`; (3) a substantial Syphilis
  section (pdf 742-743/ID24-25) has **no** `toc_inventory.json` node at
  all anywhere in the chapter's 75 nodes — represented as
  `UNCATALOGUED:ID.SYPHILIS` (`SU-ID-17`), a more severe gap than any
  prior mislabeled-node case since even a wrong page range does not
  exist for it; (4) `ID.S08` 'Tuberculosis' was recorded spanning a
  7-page range (pdf 743-749) that actually contains two chapter topics —
  TB itself occupies only pdf 743-744/ID25-26 (`SU-ID-18`), and the
  remaining pdf 745-749/ID27-31 is a substantial, genuine HIV/AIDS
  section with no node of its own at its true location; (5) the largest
  single defect: nodes `ID.S17`-`ID.S23` (toc-recorded pdf 764-778/
  ID46-60, HIGH-confidence titles) are a two-column TOC merge spanning
  ~26 pages, concatenating genuine HIV disease-topic subheadings
  (Epidemiology, Modes of Transmission, Natural History, Prevention,
  Types of Testing, HIV Pre-/Post-Test Counselling — confirmed at their
  true pdf 745-750/ID27-32 location, `SU-ID-19`/`SU-ID-20`) with an
  unrelated antimicrobial-reference-appendix column (Antibiotics/
  Antifungals/Antiparasitics tables, Landmark ID Trials, chapter
  References — confirmed at the nodes' own toc-recorded pdf 764-778
  location, `SU-ID-32`, REFERENCE_ONLY); Rocky Mountain Spotted Fever/
  West Nile Virus (part of `ID.S18`'s title) were searched for as
  standalone body headings across the full chapter and not found (only
  table-row mentions in a travel-exposure table), so no separate unit
  was fabricated for them; (6) `ID.S09`/`ID.S14` each repeat the
  cross-reference-only pattern of finding (1) (Superficial Fungal
  Infections/Dermatophytes → Dermatology; Ectoparasites → Dermatology
  D33), and `ID.S10`'s printed title 'Endemic Mycoses' is merged with
  its real `merged_duplicate_headings` entry 'Opportunistic Fungi' — two
  genuine adjacent sections sharing one node, split into `SU-ID-21`/
  `SU-ID-22` per the GY-Fibroids/H-Sickle-Cell dual-unit precedent. No
  heading was invented; all findings documented in
  `research/scope/chapters/ID/study_units.json` methodology_note and
  flagged `affects_global_toc: true` in
  `research/scope/chapters/ID/review_items.json`. MCC's presentation-
  based framework has no dedicated objective for HIV, TB, syphilis,
  sepsis, meningitis, or several other named ID topics — resolved via
  explicit causal_conditions/enabling_objectives text where possible
  (e.g. 'Sepsis' named under objective 9-2; 'meningitis, encephalitis'
  named under objective 58-1; 'Plasmodium' named under objective 107-1;
  'immunocompromised state due to HIV' named in objective 107-1's
  enabling objectives; objective 107-4 is a near-exact match for
  HIV/opportunistic-infection content) — continuing the same
  MCC-registry-coverage-gap pattern documented in chapters E, G, GS, GM,
  GY, H. `MAPPING_STRENGTH_COUNTS: STRONG=13 MODERATE=21 WEAK=5`; 2
  `UNCERTAIN` classifications (`SU-ID-10` Generalized Tetanus, `SU-ID-11`
  Rabies), 0 invalid MCC IDs, 0 hygiene violations, validator PASS,
  553/553 project tests passing.

- **NP (Nephrology)**: 22 study units derived from all 44 canonical
  `toc_inventory.json` source nodes, plus 4 additional core-content topics
  (Acute Kidney Injury, Glomerular/Tubulointerstitial/Vascular/Analgesic
  renal disease, Hypertension, Renal Transplantation) confirmed via
  raw-OCR body-heading verification against pages the deterministic
  packet flagged as unresolved TOC anchors, represented via the
  `UNCATALOGUED:` synthetic source-node-id convention rather than
  dropped. 29 MCC evidence references (14 STRONG, 14 MODERATE, 1 WEAK)
  across 9 objectives, 5 of which (89-1 AKI, 8 Hematuria, 84 Proteinuria,
  9-1 Hypertension, 29-1 Generalized edema) were located via targeted
  `search-mcc-objectives` calls after the packet's candidate set did not
  surface them — continuing the same MCC-registry-coverage-gap pattern
  documented in earlier chapters. Primary classification breakdown:
  DIRECT=9, COMPONENT=7, SUPPORTING_KNOWLEDGE=3, REFERENCE_ONLY=2,
  CROSS_DISCIPLINE=1, SPECIALIST_DETAIL=0, UNCERTAIN=0. Processed in an
  isolated worktree (`scope/NP-nephrology`, commit `7de9470`) and
  integrated into `main` via fast-forward merge (no divergence). 0
  invalid MCC IDs, 0 hygiene violations, validator PASS, 553/553 project
  tests passing.

- **N (Neurology)**: 49 study units from 28 canonical section-level TOC
  nodes (107 total nodes including T-level children, all accounted for).
  Most severely two-column-TOC-OCR-corrupted chapter mapped to date by
  node-confidence count (79/107 nodes LOW packet-extraction confidence,
  vs. GS's previous high of ~8/101). Unlike prior chapters' corruption
  patterns (headings entirely missing, or two headings merged into one
  title), N's defect is systematically mis-parented children: a node's
  own title is correct but its T-level children actually belong to a
  same-page `merged_duplicate_headings` entry instead (`N.S17` 'Vertigo'
  with child 'Amyotrophic Lateral Sclerosis' belongs to merged 'Motor
  Neuron Disease'; `N.S18` 'Other Motor NeuronDiseases' with children
  'Classification'/'Guillain-Barré Syndrome' belongs to merged
  'PeripheralNeuropathies'; `N.S24` 'Central Nervous System Infections'
  with 7 children belongs to merged 'Stroke'), plus two nodes
  concatenating two unrelated genuine headings with **no**
  `merged_duplicate_headings` flag at all (`N.S24.T06` 'Aphasia
  Intracranial Hemorrhage' = real Aphasia [Behavioural Neurology] + real
  Intracranial Hemorrhage [Stroke]; `N.S25` 'Agnosia Neurocutaneous
  Syndromes' = real Agnosia [Behavioural Neurology] + real Neurocutaneous
  Syndromes [cross-reference-only, see Pediatrics P89]), and one node
  (`N.S27`) titled entirely from OCR noise unrelated to its actual body
  content (real content = 'Landmark Neurology Trials' at N59; its
  title-text 'Paraneoplastic Syndromes'/'Tumours of the Nervous System'
  are themselves genuine headings already correctly located elsewhere, at
  N30 under Neuro-Oncology/`N.S13`). No independent raw-OCR text corpus
  resolved this reliably (the source PDF's own embedded text layer
  preserves the same two-column line-order corruption under
  `pdftotext -layout`); resolved instead via direct visual review of the
  chapter's real TOC page and 11 body pages rendered to PNG via
  `pdftoppm` from `Toronto Notes 2025.pdf` (pdf 871, 900, 905, 907-909,
  912, 921-926, 929-930). Every real heading traces to an existing
  `toc_inventory.json` node_id (reused directly, not synthetic
  `UNCATALOGUED:`, since the node objects genuinely exist, just mistitled
  or misparented) with the correction documented in full in each affected
  study unit's `structural_rationale`, plus a chapter-wide summary in
  `study_units.json`'s `methodology_note`. Six cross-reference-only
  entries identified and represented as thin `CROSS_DISCIPLINE` study
  units for source-node traceability rather than duplicated content: CNS
  Infections -> Infectious Diseases (ID17); Spinal Cord Syndromes ->
  Neurosurgery (NS34); Vertigo -> Otolaryngology (OT12); Neurocutaneous
  Syndromes -> Pediatrics (P89); Tumours of the Nervous System ->
  Neurosurgery (NS12); Paraneoplastic Syndromes -> Endocrinology (E56).
  Coma (`N.S23.T02`) is split out from its TN parent 'Sleep Disorders'
  into its own study unit despite genuinely being a TN sub-heading there
  (confirmed, not a corruption artifact), given its status as an
  independently-named MCC objective (58-1) and distinct emergency
  competency. 49 MCC evidence citations (27 STRONG, 22 MODERATE, 5 WEAK)
  across 26 objectives; targeted `search-mcc-objectives` searches
  confirmed MCC has no dedicated objective for multiple sclerosis,
  Parkinson disease (as a title), myasthenia gravis, Guillain-Barré
  syndrome, or meningitis/encephalitis — each instead mapped via its
  governing presentation-based objective (e.g. MS via numbness=66 +
  acute visual disturbance=115-1 + ataxia=35; Parkinson's disease via
  movement disorders=61, which explicitly names it in the enabling
  objectives) — continuing the same MCC-registry-coverage-gap pattern
  documented in chapters E, G, GS, GM, GY, H, ID, NP. 0 invalid MCC IDs,
  0 hygiene violations, 0 `UNCERTAIN` classifications, validator PASS,
  553/553 project tests passing. Worked in the canonical `main` checkout
  per explicit instruction for this chapter (no isolated worktree/branch).

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
