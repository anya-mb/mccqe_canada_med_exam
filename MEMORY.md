# MCCQE project

## Current phase

- Current phase: scaled current-Canadian source-packet research.
- Source-packet plan: PASS.
- Total planned source packets: 1,524.
- Research batches: 159.
- Pilot batch `SRB-089`: PASS.
- Pilot packets ready: 10/10.
- Pilot source-packet validator: PASS.
- Pilot commit: `f5ae57b`.
- Full test baseline: 644 passed / 0 failed.
- Approximately 1,514 source packets remain to research.
- Current next step: `SCALE_SOURCE_PACKET_RESEARCH`.

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

- No upstream blocker remains. Populate the planned current Canadian source packets.
- NEXT_STEP = `POPULATE_CURRENT_CANADIAN_SOURCE_PACKETS`

## Resume artifacts

Before continuing, read:

1. `MEMORY.md`
2. `research/scope/question_bank_targets.json`
3. `reports/final_effective_ownership_audit.json`
4. the canonical Medical Imaging allocation-routing artifact
5. the latest final-question-allocation preflight/audit

Canonical JSON artifacts and validator output override `MEMORY.md` if they conflict.
