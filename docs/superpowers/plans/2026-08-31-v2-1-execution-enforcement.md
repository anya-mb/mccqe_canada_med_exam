# V2.1 Execution Enforcement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fail closed unless a V2 generated item semantically instantiates its approved item spec before final verification.

**Architecture:** Keep approved V2 specs immutable. Add a V2.1 generated-artifact contract requiring an explicit instantiation map and a separate fresh semantic generated-item review; deterministic validation binds their lineage and rejects any non-accepted candidate. V1 and V2 contracts remain untouched.

**Tech Stack:** Python, JSON artifacts, pytest.

**Spec:** User-authorized V2.1 retry request, 2026-08-31.

## Global Constraints

- No web or new evidence research.
- Preserve V1, V2, foundational evidence, READY packets, allocation, mappings, manifests, and audits byte-for-byte.
- Use existing approved V2 item specs and slot-scoped evidence only.
- Generate a three-item V2.1 micro-pilot before any full retry.

---

### Task 1: V2.1 execution and semantic-gate contracts

**Files:**
- Modify: `scripts/qbank/source_ready_generation_pilot.py`
- Test: `tests/test_source_ready_generation_pilot.py`

**Interfaces:**
- Produces `build_retry_v2_1_generator_input`, `validate_retry_v2_1_generated_artifact`, and `validate_retry_v2_1_semantic_generation_review`.
- Consumes immutable V2 specs and preflight artifacts.

- [ ] **Step 1: Write failing contract tests**

```python
with pytest.raises(SourceReadyGenerationPilotError, match="instantiation map"):
    validate_retry_v2_1_generated_artifact(REPO, JOB_ID, specs, preflight, generated)
```

Cover flattened definition recognition, unnecessary vignette, missing reasoning step, an unplanned distractor, and keyword-recognition shortcuts; include a complete PASS-like fixture and a V1 regression assertion.

- [ ] **Step 2: Run the focused tests to verify RED**

Run: `.venv/bin/pytest -q tests/test_source_ready_generation_pilot.py -k v2_1`

Expected: failure because V2.1 contract functions are absent.

- [ ] **Step 3: Add the minimum V2.1-only implementation**

Require per-item reasoning-step scenario mappings, a decisive discriminant location, complete distractor instantiations, prohibited-shortcut declarations, and detailed rationales. Bind a fresh semantic reviewer artifact with `ACCEPT_GENERATED_ITEM` verdicts before accepting a V2.1 generated artifact.

- [ ] **Step 4: Run focused tests to verify GREEN**

Run: `.venv/bin/pytest -q tests/test_source_ready_generation_pilot.py -k v2_1`

Expected: PASS.

### Task 2: V2.1 micro-pilot and independent verification

**Files:**
- Create: `research/qgen/pilot/QGEN-PHELO-011.retry-v2-1-micro-3.generated.json`
- Create: `reports/qgen_phelo_011_retry_v2_1_micro_semantic_generation_review.json`
- Create: `research/qgen/pilot/QGEN-PHELO-011.retry-v2-1-micro-3.verification.json`

**Interfaces:**
- Consumes Task 1 V2.1 contracts and immutable V2 specs/preflight.
- Produces a three-item accepted candidate set for a fresh final verifier.

- [ ] **Step 1: Build exactly three candidates from one V2 PASS, one plan-mismatch failure, and one weak-distractor failure**

Use V2 cards 05, 03, and 07 unless the semantic gate identifies a supported reason to substitute.

- [ ] **Step 2: Run a fresh generated-item semantic review**

Every candidate must receive `ACCEPT_GENERATED_ITEM`; otherwise stop with the review artifact.

- [ ] **Step 3: Run a distinct fresh independent verification**

Require all three items to pass factual correctness, evidence support, plan fidelity, applied reasoning, vignette necessity, distractors, rationales, and writing quality.

### Task 3: Full V2.1 retry only after micro-pilot acceptance

**Files:**
- Create: `research/qgen/pilot/QGEN-PHELO-011.retry-v2-1-10.generated.json`
- Create: `reports/qgen_phelo_011_retry_v2_1_semantic_generation_review.json`
- Create: `research/qgen/pilot/QGEN-PHELO-011.retry-v2-1-10.verification.json`

**Interfaces:**
- Consumes Task 1 contracts and the micro-pilot gate.
- Produces the final V2.1 acceptance result.

- [ ] **Step 1: Generate each full-set candidate with at most two attempts**

Keep only semantic-gate accepted candidates; stop if a card cannot satisfy the immutable spec twice.

- [ ] **Step 2: Run a fresh independent final verification and deterministic acceptance validation**

Require at least 9/10 with zero factual or unsupported claims, no systemic plan/difficulty/distractor failure, and NONE/LOW duplication.

- [ ] **Step 3: Run full regression once and commit green work**

Run: `.venv/bin/pytest -q`

Expected: PASS; restore only confirmed test side effects before committing.
