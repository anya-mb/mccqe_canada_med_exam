# MCCQE project

- Current phase: final question allocation.
- Curriculum scope and MCC crosswalk are complete.
- Total study units: 1,487.
- Never invent Toronto Notes headings or MCC IDs.

## Ownership

- Ownership review is complete: 106/106 candidate groups are effectively resolved.
- Whole-unit ownership remains canonical.
- Competency-component ownership schema v1.1 handles the 13 structural whole-unit exceptions.
- Component layer: 50 components across 30 study units, with 43 relationships.
- Final effective ownership audit passed.
- Ownership no longer blocks question allocation.
- Preserve frozen ownership artifacts unless a task explicitly requires changing them.

## Question-bank targets

- Final study-bank target is 6,086 questions.
- MED = 1,086.
- PED = 1,000.
- OBGYN = 1,000.
- SURG = 1,000.
- PSY = 1,000.
- PHELO = 1,000.
- The MED target was increased from 1,000 to 1,086 because the current canonical MED effective minimum_question_coverage totals 1,086.
- Do not reduce MED planning minima merely to restore a 1,000-question MED target.
- The separate 230-question MCCQE simulation is not part of the 6,086-question study bank.

## Allocation state

- Effective allocation address count: 1,507.
- Eligible allocation addresses: 1,175.
- Ownership-suppressed addresses: 31.
- Zero-scope addresses: 301.
- There are 18 pre-existing planning conflicts involving zero-scope/context metadata and positive raw minimum coverage; canonical zero-scope precedence makes these nonblocking for effective allocation.
- Medical Imaging discipline routing is complete: 18 eligible addresses route to MED and 8 to SURG.
- No eligible allocation address remains unassigned or multiply assigned.
- Current next step: update the canonical question-bank target config to 6,086 / MED 1,086, then build final question allocation.

## Source and QA rules

- Toronto Notes is used for organization and topic discovery, not as the sole source of current clinical recommendations.
- MCC Objectives and the canonical crosswalk define examination scope.
- Weak or uncertain source/mapping claims must be evidence-grounded; fail closed rather than inventing canonical decisions.
- Python validators handle structural QA.
- Preserve frozen scope, MCC mappings, ownership, component ownership, Medical Imaging routing, and planning metadata unless a task explicitly requires changing them.
- Prefer deterministic Python operations for allocation and validation.
- Do not generate questions yet.
- After final allocation, build question-generation manifests and current Canadian clinical source packets before MCQ generation.

## Resume

Before continuing allocation work, read the current canonical artifacts, especially:

- `research/scope/question_bank_targets.json`
- `reports/final_effective_ownership_audit.json`
- the canonical Medical Imaging allocation-routing artifact
- the latest final-question-allocation preflight/audit

Canonical JSON and validator output override this file if they conflict.