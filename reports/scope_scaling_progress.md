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
| Completed | 2 / 32 (`C`, `ELOM`) |
| Next chapter | **A — Anesthesia** |
| Current chapter (in progress) | none |
| Review-required | none |
| Failed | none |
| Last completed commit | `a8e2ff7` — feat: freeze MCC scope crosswalk schema |
| Working tree | clean as of this checkpoint |

## Processing order (remaining, one at a time)

1. A — Anesthesia *(next)*
2. CP — Clinical Pharmacology
3. D — Dermatology
4. ER — Emergency Medicine
5. E — Endocrinology
6. FM — Family Medicine
7. G — Gastroenterology
8. GS — General and Thoracic Surgery
9. GM — Geriatric Medicine
10. GY — Gynecology
11. H — Hematology
12. ID — Infectious Diseases
13. MG — Medical Genetics
14. MI — Medical Imaging
15. NP — Nephrology
16. N — Neurology
17. NS — Neurosurgery
18. OB — Obstetrics
19. OP — Ophthalmology
20. OR — Orthopedic Surgery
21. OT — Otolaryngology
22. P — Pediatrics
23. PM — Palliative Medicine
24. PL — Plastic Surgery
25. PS — Psychiatry
26. PH — Public Health and Preventive Medicine
27. R — Respirology
28. RH — Rheumatology
29. U — Urology
30. VS — Vascular Surgery

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
