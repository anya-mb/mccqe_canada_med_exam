# MCCQE QBank Repository Instructions

## Start here

Before doing MCCQE pipeline work:

1. Read `MEMORY.md` for the current project phase, active blocker, frozen layers, and next step.
2. Read the canonical artifacts relevant to the requested task.
3. Treat canonical JSON artifacts and deterministic validator output as authoritative if they conflict with `MEMORY.md`.

Do not resume work from an old phase merely because older reports remain in the repository.

## Current architecture

The pipeline is staged:

scope
→ MCC mapping
→ ownership
→ competency-component ownership
→ discipline routing
→ question-bank targets
→ final allocation
→ generation manifests
→ current Canadian source packets
→ MCQ generation
→ independent verification

Do not skip prerequisite stages.

## Canonical-data rules

- Never invent Toronto Notes headings.
- Never invent MCC IDs.
- Do not reconstruct missing source evidence from medical knowledge.
- Toronto Notes is for organization/topic discovery; it is not the sole authority for current clinical recommendations.
- Preserve provenance.
- Fail closed when canonical evidence or policy is missing.
- Model agreement is not evidence.

## Frozen-layer rule

Completed canonical layers must remain unchanged unless the current task explicitly authorizes modifying them or a concrete validator/audit failure proves repair is necessary.

In particular, do not casually reopen:

- study-unit scope;
- MCC mappings;
- ownership decisions;
- competency-component ownership;
- Medical Imaging allocation routing;
- question-bank targets.

## Deterministic-first rule

Use deterministic Python for:

- parsing;
- joins;
- reconciliation;
- counting;
- allocation arithmetic;
- sorting;
- graph validation;
- schema validation;
- reproducibility checks.

Use an LLM only for bounded semantic decisions that deterministic evidence cannot resolve.

Do not use an LLM for bulk deterministic transformations.

## Allocation rules

The canonical final study-bank target is defined by:

`research/scope/question_bank_targets.json`

Current target:

- MED: 1,086
- PED: 1,000
- OBGYN: 1,000
- SURG: 1,000
- PSY: 1,000
- PHELO: 1,000
- Total: 6,086

The separate 230-question MCCQE simulation is not part of this bank.

Do not reduce MED planning minima simply to force MED back to 1,000.

Use canonical allocation discipline routing, including committed Medical Imaging routing.

Zero-scope precedence must be preserved.

Ownership-suppressed content must not receive independent question allocation.

Component-mode parents must not be double-allocated at whole-unit level.

## Testing and validation

Prefer:

1. focused deterministic validation;
2. focused tests;
3. one full test-suite run after final production/canonical changes.

If code or canonical executable artifacts change after the full-suite run, rerun it.

Never claim PASS without fresh verification.

Keep the working tree clean between canonical stages where practical.

## Question generation

Do not generate MCQs until:

- final question allocation passes;
- generation manifests exist;
- appropriate current Canadian source packets are available.

Question generation must use small, evidence-grounded batches rather than sending the entire curriculum to an LLM.

Clinical recommendations should be refreshed from current authoritative Canadian sources where available.

Questions must remain original and must not reproduce Toronto Notes, actual/recalled MCC questions, or commercial QBank questions.

## Current resume point

Read `MEMORY.md`.

Current expected next stage:

`BUILD_FINAL_QUESTION_ALLOCATION`
