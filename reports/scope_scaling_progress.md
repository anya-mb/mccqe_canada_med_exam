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
| Completed | 7 / 32 (`C`, `ELOM`, `A`, `CP`, `D`, `ER`, `E`) |
| Next chapter | **FM — Family Medicine** |
| Current chapter (in progress) | none |
| Review-required | none |
| Failed | none |
| Last completed commit | `539da16` — scope: map E Endocrinology |
| Working tree | clean as of this checkpoint |

## Processing order (remaining, one at a time)

1. FM — Family Medicine *(next)*
2. G — Gastroenterology
3. GS — General and Thoracic Surgery
4. GM — Geriatric Medicine
5. GY — Gynecology
6. H — Hematology
7. ID — Infectious Diseases
8. MG — Medical Genetics
9. MI — Medical Imaging
10. NP — Nephrology
11. N — Neurology
12. NS — Neurosurgery
13. OB — Obstetrics
14. OP — Ophthalmology
15. OR — Orthopedic Surgery
16. OT — Otolaryngology
17. P — Pediatrics
18. PM — Palliative Medicine
19. PL — Plastic Surgery
20. PS — Psychiatry
21. PH — Public Health and Preventive Medicine
22. R — Respirology
23. RH — Rheumatology
24. U — Urology
25. VS — Vascular Surgery

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
