# MCCQE project

## Current phase

- Current phase: final deterministic question allocation.
- Curriculum scope and MCC crosswalk are complete.
- Total study units: 1,487.
- Do not reopen completed scope, mapping, or ownership work unless a concrete validator/audit failure requires it.

## Scope and source rules

- Never invent Toronto Notes headings or MCC IDs.
- Toronto Notes is used for organization and topic discovery, not as the sole source of current clinical recommendations.
- MCC Objectives and the canonical crosswalk define examination scope.
- Weak or uncertain source/mapping claims must be evidence-grounded.
- Fail closed rather than inventing missing canonical decisions.

## Ownership

- Ownership review is complete: 106/106 ownership candidate groups are effectively resolved.
- Whole-unit ownership remains canonical.
- Competency-component ownership schema v1.1 handles the 13 structural whole-unit exceptions.
- Component layer: 50 components across 30 study units with 43 relationships.
- Final effective ownership audit passed.
- Effective ownership unresolved groups: 0.
- Ownership no longer blocks question allocation.
- Preserve frozen ownership/component artifacts unless a task explicitly requires changing them.

## Question-bank target

- Final study-bank target: 6,086 questions.
- MED = 1,086.
- PED = 1,000.
- OBGYN = 1,000.
- SURG = 1,000.
- PSY = 1,000.
- PHELO = 1,000.
- The MED target was expanded from 1,000 to 1,086 because canonical MED effective minimum_question_coverage totals 1,086.
- Do not reduce MED canonical planning minima merely to restore a 1,000-question MED target.
- The separate 230-question MCCQE simulation is not part of the 6,086-question study bank.

## Current allocation state

- Effective allocation addresses: 1,507.
- Eligible allocation addresses: 1,175.
- Ownership-suppressed addresses: 31.
- Zero-scope addresses: 301.
- There are 18 pre-existing planning conflicts involving zero-scope/context metadata plus positive raw minimum coverage.
- Canonical zero-scope precedence makes those 18 conflicts nonblocking for effective allocation.
- Medical Imaging discipline routing is complete:
  - MED = 18 addresses.
  - SURG = 8 addresses.
  - Deferred = 0.
- No eligible allocation addresses remain unassigned or multiply assigned.

## Effective minimums

- MED = 1,086 / target 1,086.
- PED = 187 / target 1,000.
- OBGYN = 131 / target 1,000.
- SURG = 424 / target 1,000.
- PSY = 106 / target 1,000.
- PHELO = 138 / target 1,000.
- All six discipline targets are feasible.
- MED has no remaining budget above its effective minima.

## QA and implementation rules

- Prefer deterministic Python operations for builders, allocation, and validators.
- Python validators handle structural QA.
- Use LLM reasoning only for bounded semantic residue that deterministic rules cannot resolve.
- Do not silently change frozen canonical inputs to make arithmetic work.
- Preserve scope, MCC mappings, ownership, component ownership, question planning, Medical Imaging routing, and bank targets unless the task explicitly authorizes changing them.
- Run focused tests first; run the full suite when production tooling or canonical executable artifacts change.
- Fail closed on missing policy, missing evidence, or inconsistent canonical inputs.

## Question generation

- Do not generate questions yet.
- First complete final deterministic allocation.
- Then build question-generation manifests.
- Then build current Canadian clinical source packets.
- Only after those steps begin MCQ generation.
- Questions must include correct-answer rationale and distractor rationale and later undergo independent verification.

## Resume

Before continuing, read:

1. `MEMORY.md`
2. `research/scope/question_bank_targets.json`
3. `reports/final_effective_ownership_audit.json`
4. the canonical Medical Imaging allocation-routing artifact
5. the latest final-question-allocation preflight/audit

Current next step:

`BUILD_FINAL_QUESTION_ALLOCATION`

Canonical JSON artifacts and validator output override `MEMORY.md` if they conflict.