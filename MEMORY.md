# MCCQE project

## Current state

- Current phase: FINAL QUESTION ALLOCATION.
- Total study units: 1,487.
- Ownership candidates effectively resolved: 106 / 106.
- Component schema: 1.1; 50 component records across 30 study units.
- Final effective ownership audit: PASS.
- Allocation addresses: 1,507 (eligible 1,175; ownership-suppressed 31; zero-scope 301).
- Medical Imaging routing: MED 18 / SURG 8 / deferred 0.

## Frozen layers

- Scope, MCC mapping, ownership, competency-component ownership, discipline routing, question planning, and question-bank targets are complete and frozen.
- Do not reopen a frozen layer unless explicitly authorized or a concrete validator/audit failure requires repair.

## Canonical question-bank target

- Final study-bank target: 6,086 questions.
- MED = 1,086.
- PED = 1,000.
- OBGYN = 1,000.
- SURG = 1,000.
- PSY = 1,000.
- PHELO = 1,000.
- MED exactly equals its effective minimum; do not reduce MED minima merely to restore a 1,000-question MED target.
- The separate 230-question MCCQE simulation is not part of the 6,086-question study bank.

## Effective minimums

- MED = 1,086 / target 1,086.
- PED = 187 / target 1,000.
- OBGYN = 131 / target 1,000.
- SURG = 424 / target 1,000.
- PSY = 106 / target 1,000.
- PHELO = 138 / target 1,000.
- All six discipline targets are feasible.

## Blocker and next step

- No upstream blocker remains. Build and validate the final question allocation.
- NEXT_STEP = `BUILD_FINAL_QUESTION_ALLOCATION`

## Resume artifacts

Before continuing, read:

1. `MEMORY.md`
2. `research/scope/question_bank_targets.json`
3. `reports/final_effective_ownership_audit.json`
4. the canonical Medical Imaging allocation-routing artifact
5. the latest final-question-allocation preflight/audit

Canonical JSON artifacts and validator output override `MEMORY.md` if they conflict.
