# Retry V2 Quality Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement and execute the ten-item `STRUCTURED_ITEM_SPEC_V2` pilot for `QGEN-PHELO-011` without changing V1 or frozen evidence/allocation artifacts.

**Architecture:** Extend the existing source-ready pilot module with a separate V2 lineage, deterministic schema/fingerprint/signature gates, and explicit independent preflight and verification contracts. Semantic judgments remain in fresh review artifacts; Python validates only mechanically provable structure, allocation, evidence closure, identity, and independence.

**Tech Stack:** Python 3, pytest, canonical JSON artifacts, SHA-256 fingerprints, Git.

**Spec:** `docs/superpowers/specs/2026-08-31-retry-v2-quality-design.md`

## Global Constraints

- Preserve V1 behavior and keep every V1/frozen artifact byte-unchanged.
- Preserve exact V2 allocation `SU-PH-01=5`, `SU-PH-02=3`, `SU-PH-03=2`.
- Use only existing authorized foundational claims and READY recommendations; no web or new evidence research.
- Fail closed at each phase and do not weaken semantic or deterministic gates.
- Generate exactly ten V2 questions and do not scale beyond this pilot.
- Apply the user-authorized pilot acceptance threshold of at least `9/10` PASS with zero factual errors and zero unsupported claims; this supersedes the design document's earlier `7/10` threshold.

---

### Task 1: V2 item-spec and semantic-preflight contracts

**Files:**
- Modify: `scripts/qbank/source_ready_generation_pilot.py`
- Modify: `tests/test_source_ready_generation_pilot.py`
- Create later at the data gate: `research/qgen/pilot/QGEN-PHELO-011.retry-v2-10.item-spec.json`
- Create later at the semantic gate: `reports/qgen_phelo_011_retry_v2_semantic_preflight.json`

**Interfaces:**
- Produces `build_retry_v2_preflight_input`, `validate_retry_v2_item_specs`, and `validate_retry_v2_semantic_preflight`.
- The item-spec validator enforces schema `STRUCTURED_ITEM_SPEC_V2`, exact slots/allocation, evidence identifiers, deterministic semantic signatures, V1/evidence fingerprints, and unique lineage.
- The preflight validator binds a non-author reviewer and ten explicit `APPROVED_FOR_GENERATION` or `REJECTED_FOR_SPEC_REVISION` verdicts to the exact item-spec fingerprint.

- [ ] Add focused tests first for a valid ten-card fixture and failures caused by a missing V2 field, `5/3/2` drift, forged semantic signature, invalid/cross-slot evidence, mismatched V1 fingerprint, duplicate deterministic signature, missing verdict, fingerprint mismatch, self-review, and any rejected card.
- [ ] Run the focused tests and confirm they fail because the V2 interfaces do not yet exist.
- [ ] Implement the minimum separate V2 constants, canonical hashing/normalization, item-spec/evidence/lineage checks, preflight-input builder, and preflight-verdict validator needed to pass.
- [ ] Run the focused test file and preserve all V1 tests.

### Task 2: Retry generator V2 quality and verification contracts

**Files:**
- Modify: `scripts/qbank/source_ready_generation_pilot.py`
- Modify: `tests/test_source_ready_generation_pilot.py`
- Create later at the generation gate: `research/qgen/pilot/QGEN-PHELO-011.retry-v2-10.generated.json`
- Create later at the final gate: `research/qgen/pilot/QGEN-PHELO-011.retry-v2-10.verification.json`

**Interfaces:**
- Produces `build_retry_v2_generator_input`, `validate_retry_v2_generated_artifact`, `build_retry_v2_verifier_input`, and `validate_retry_v2_verification`.
- Generator input is available only after an all-approved preflight and exposes slot-scoped evidence.
- Generated validation mechanically enforces ten exact items, item-spec fingerprints/fields, approved distractor-blueprint identifiers, required-vignette realization markers, assertion-level evidence closure, semantic-signature lineage, and no duplicate candidate signature.
- Verification validation binds a fresh verifier to exact generated/item-spec/preflight bytes and computes the user-approved `9/10` pilot gate without treating deterministic checks as semantic approval.

- [ ] Add focused tests first for blocked generation before approval, V2/V1 path separation, plan-fingerprint mismatch, unapproved distractor mapping, missing vignette realization, unsupported closure, verifier self-approval/context overlap, incomplete verdicts, acceptance-count/category failures, and one local-revision lineage.
- [ ] Run the focused tests and confirm the expected RED failures.
- [ ] Implement the minimum V2 generator/output/verifier contracts and deterministic acceptance summary.
- [ ] Run focused tests, then run the full repository pytest suite once because production Python changed; run `git diff --check` and commit infrastructure only if both gates pass.

### Task 3: Ten-card pilot execution and integration verification

**Files:**
- Create: `research/qgen/pilot/QGEN-PHELO-011.retry-v2-10.item-spec.json`
- Create: `reports/qgen_phelo_011_retry_v2_semantic_preflight.json`
- Create: `research/qgen/pilot/QGEN-PHELO-011.retry-v2-10.generated.json`
- Create: `research/qgen/pilot/QGEN-PHELO-011.retry-v2-10.verification.json`
- Modify only if the canonical resume point materially changes: `MEMORY.md`

**Interfaces:**
- Consumes the V2 contracts from Tasks 1-2 plus immutable V1/evidence artifacts.
- Produces the complete approved item-spec, independent preflight, generated set, independent verification, and final pilot assessment.

- [ ] Construct all ten evidence-supported item specs in exact `5/3/2` allocation, calculate deterministic signatures/fingerprints, and validate them without modifying evidence or V1.
- [ ] Give a fresh non-author reviewer only the V2 specs, authorized evidence, and canonical level context; write and validate its ten-card preflight, revising only rejected specs for at most two bounded passes.
- [ ] Generate exactly ten original questions from the approved specs, including blueprint-matched distractors, material vignette facts, complete rationales, and assertion-level slot-scoped evidence; run structural/evidence validation and commit the validated artifact.
- [ ] Give a fresh non-generator verifier only the approved specs/evidence/generated questions/scope; write and validate all ten verdicts, using at most one bounded local item-revision cycle if exactly one or two local defects are identified.
- [ ] Run final deterministic validators, focused tests, protected-artifact fingerprint comparison, `git diff --check`, and `git status --short`; update `MEMORY.md` only if required by canonical state, then commit the final V2 assessment artifacts.
