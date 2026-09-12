# Atomic Opportunity Contract V1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Diagnose the V1/V2 recall paradox, define and enforce an atomic opportunity contract, audit benchmark granularity, canonicalize Registry V3, and calibrate Blueprint Mapping V2 without generating questions.

**Architecture:** A new V3 module consumes frozen V1, V2, benchmark, comparison, and blind-audit artifacts. It builds deterministic diagnostics and a lineage-preserving V3 canonicalization; all semantic uncertainty is represented explicitly rather than hidden in counts.

**Tech Stack:** Python 3, pytest, canonical JSON, SHA-256.

**Spec:** `docs/superpowers/specs/2026-09-11-atomic-opportunity-contract-v1-design.md`

## Global Constraints

- Preserve the exact dirty worktree and historical HEAD `01eff40984bee76418c7fab82a1ded9fbfa2d9e5`.
- Create no commit and modify no frozen historical artifact.
- Generate no production question.
- Do not enumerate toward discipline quotas or treat 675 benchmark rows as unquestioned atoms.
- Use deterministic Python for all joins, counts, hashes, partitions, and validation.

---

### Task 1: Matcher regression diagnosis and atomic contract

**Files:**
- Create: `scripts/qbank/curriculum_opportunity_registry_v3.py`
- Create: `tests/test_curriculum_opportunity_registry_v3.py`
- Create: `research/qgen/opportunity_registry_v3/atomic_opportunity_contract_v1.json`
- Create: `research/qgen/opportunity_registry_v3/matcher_regression_diagnosis_v1.json`

- [ ] Write failing tests for the 38 preserved V1 matches, transition accounting, and non-decreasing best-match rank.
- [ ] Run red and record the expected missing-module failure.
- [ ] Implement immutable-lineage diagnostics and matcher relation aggregation.
- [ ] Run focused tests green.

### Task 2: Partial-match forensics and benchmark granularity audit

**Files:**
- Create: `research/qgen/opportunity_registry_v3/partial_match_forensics_v1.json`
- Create: `research/qgen/opportunity_registry_v3/benchmark_granularity_audit_v1.json`
- Modify: `tests/test_curriculum_opportunity_registry_v3.py`

- [ ] Write failing tests for exhaustive 415-row V1 and 386-row V2 partial coverage, controlled forensic classes, benchmark audit conservation, and cluster lineage.
- [ ] Run red, implement deterministic classification and clustering, then rerun green.
- [ ] Report unresolved semantic rows honestly; do not convert heuristic triage into independent validation.

### Task 3: Registry V3 canonicalization

**Files:**
- Create: `schemas/curriculum-question-opportunity-v3.schema.json`
- Create: `research/qgen/opportunity_registry_v3/curriculum_question_opportunity_registry_v3.json`
- Modify: `tests/test_curriculum_opportunity_registry_v3.py`

- [ ] Write failing tests for V2 lineage completeness, signature stability, zero benchmark-ID enumeration, atomicity-status capacity policy, and reproducibility.
- [ ] Run red, implement the minimal V2 canonicalization, and rerun green.

### Task 4: Blueprint Mapping V2

**Files:**
- Create: `research/qgen/opportunity_registry_v3/blueprint_mapping_v2.json`
- Modify: `tests/test_curriculum_opportunity_registry_v3.py`

- [ ] Write failing tests for deterministic calibration/holdout partitioning, rule-ID generality, confusion matrices, confidence, and fail-closed ambiguity.
- [ ] Run red, implement context-aware mapping and evaluation, and rerun green.

### Task 5: Milestone, resume state, and verification

**Files:**
- Create: `reports/atomic_opportunity_contract_v1_registry_v3_milestone.json`
- Modify: `MEMORY.md` only in the changing QGEN resume section.

- [ ] Build every artifact twice and prove byte identity.
- [ ] Run focused V3 and historical V1/V2 tests.
- [ ] Run `git diff --check`, verify frozen hashes and no commits, and run the canonical full suite once at final code state.
- [ ] Keep `READY_FOR_PRODUCTION_BATCH_GENERATION=NO` and report no generated items.
