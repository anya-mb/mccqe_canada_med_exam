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
| Completed | 3 / 32 (`C`, `ELOM`, `A`) |
| Next chapter | **CP — Clinical Pharmacology** |
| Current chapter (in progress) | none |
| Review-required | none |
| Failed | none |
| Last completed commit | `scope: map A Anesthesia` (see `git log` for hash) |
| Working tree | clean as of this checkpoint |

## Processing order (remaining, one at a time)

1. CP — Clinical Pharmacology *(next)*
2. D — Dermatology
3. ER — Emergency Medicine
4. E — Endocrinology
5. FM — Family Medicine
6. G — Gastroenterology
7. GS — General and Thoracic Surgery
8. GM — Geriatric Medicine
9. GY — Gynecology
10. H — Hematology
11. ID — Infectious Diseases
12. MG — Medical Genetics
13. MI — Medical Imaging
14. NP — Nephrology
15. N — Neurology
16. NS — Neurosurgery
17. OB — Obstetrics
18. OP — Ophthalmology
19. OR — Orthopedic Surgery
20. OT — Otolaryngology
21. P — Pediatrics
22. PM — Palliative Medicine
23. PL — Plastic Surgery
24. PS — Psychiatry
25. PH — Public Health and Preventive Medicine
26. R — Respirology
27. RH — Rheumatology
28. U — Urology
29. VS — Vascular Surgery

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
