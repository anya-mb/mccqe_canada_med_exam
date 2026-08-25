# MCCQE QBank Project

## Current phase

We are building the Toronto Notes 2025 → MCC scope crosswalk.

Do NOT generate practice questions yet.

Canonical resume state:
`reports/scope_scaling_progress.json`

Always read that file first.

## Source authority

Toronto Notes structure:
`research/tn2025/toc_inventory.json`

MCC objective authority:
`research/mcc/objectives_registry.json`

Study Smarter:
`research/mcc/study_smarter_discipline_mapping.json`

Frozen scope schema:
<actual schema path>

## Accuracy rules

- Never invent Toronto Notes headings.
- Never invent MCC IDs.
- DIRECT/COMPONENT requires actual MCC evidence.
- If evidence is insufficient, use WEAK/UNCERTAIN.
- Do not use model memory as evidence.
- Do not encode changing treatment recommendations at scope stage.
- Keep all source-node traceability.
- One chapter at a time.
- Run deterministic validation before committing.
- Commit every completed chapter.
- Stop after one chapter unless explicitly told otherwise.

## Chapter lifecycle

1. Read progress ledger.
2. Process `next_chapter` only.
3. Build study units.
4. Map to MCC.
5. Run chapter validator.
6. Run tests.
7. Update review queue + progress ledger.
8. Commit.
9. Report checkpoint.
10. STOP.

## Important

Do not re-read historical reports unless needed to resolve a specific problem.

Use Cardiology and ELOM only as examples when the frozen schema/methodology
does not make a rule clear.