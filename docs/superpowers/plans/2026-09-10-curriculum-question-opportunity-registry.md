# Curriculum Question Opportunity Registry V1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce and freeze the complete curriculum opportunity registry, dedupe/allocation/seed plan, identity graph, production queue, dry run, audits, and resume state without generating production MCQs.

**Architecture:** One deterministic Python module reads frozen canonical inputs and emits stable validated artifacts. A dedicated test module drives each behavior through red-green cycles, while semantic classification remains conservative and serial.

**Tech Stack:** Python 3, pytest, JSON Schema-compatible validation, canonical JSON/SHA256.

**Spec:** `docs/superpowers/specs/2026-09-10-curriculum-question-opportunity-registry-design.md`

## Global Constraints

- Exact current worktree; no commits, reset, clean, stash, or checkout.
- Historical frozen artifacts modified = 0; `CLAUDE.md` unchanged.
- No production MCQ generation and no invented clinical facts or MCC IDs.
- Deterministic-first; semantic concurrency = 1.
- Canonical allocation targets remain MED 1,086 and 1,000 for each other discipline, total 6,086, but are not forced.

---

### Task 1: Canonical snapshot and schema

**Files:** Create `schemas/curriculum-question-opportunity-v1.schema.json`, `scripts/qbank/curriculum_opportunity_registry.py`, `tests/test_curriculum_opportunity_registry.py`.

- [ ] Write failing tests proving eligible study units are snapshotted exactly once, zero-scope rows remain excluded, source readiness is joined deterministically, required schema fields are enforced, and self-hashes reproduce.
- [ ] Run the focused tests and confirm the expected missing-module/schema failures.
- [ ] Implement canonical loaders, stable serialization, hashing, snapshot construction, and record validation.
- [ ] Run focused tests to green.

### Task 2: Enumeration, fingerprints, and dedupe

**Files:** Modify the Task 1 module and tests.

- [ ] Write failing tests for competency-derived atomic opportunities, controlled family/response/stage mappings, cosmetic-detail-insensitive fingerprints, exact provenance-preserving collapse, conservative near-duplicate review, variant groups, and same-topic distinctness rules.
- [ ] Run the focused tests and confirm behavior failures.
- [ ] Implement enumeration, normalization, fingerprinting, exact collapse, semantic-pair review, and variant grouping.
- [ ] Run focused tests to green.

### Task 3: Suitability, capacity, coverage, and blueprint reports

**Files:** Modify the module/tests; generate `research/qgen/opportunity_registry/*.json` only after tests pass.

- [ ] Write failing tests for MCC-level scope, MCQ suitability, controlled priority, capacity bounded to 0-3, explicit zero-unit reasons, discipline/family/response/MCC rollups, and feasibility arithmetic independent of target forcing.
- [ ] Run red tests, implement the minimal deterministic rules, and rerun to green.

### Task 4: Review and existing-asset reconciliation

**Files:** Modify module/tests.

- [ ] Write failing tests for a count-blind deterministic stratified sample spanning six disciplines and major families, allowed review/error verdicts, validation-item-only reconciliation, and exact-scope readiness mapping.
- [ ] Run red tests, implement review/reconciliation, and rerun to green.

### Task 5: Allocation, seed plan, graph, queue, and dry run

**Files:** Modify module/tests.

- [ ] Write failing tests for allocation reconciliation, stable coverage-first ordering, unique seed slots and fingerprints, the 20/55/25 planning mix, five production waves, graph referential integrity, queue dependency routing, and a maximum-30-entry cross-discipline dry run with zero duplicates.
- [ ] Run red tests, implement planners, and rerun to green.

### Task 6: Milestone generation and audits

**Files:** Generate canonical registry artifacts and `reports/curriculum_question_opportunity_registry_v1_milestone.json`; modify `MEMORY.md` changing resume-state section only.

- [ ] Write failing integration tests for deterministic regeneration, frozen-input hashes, copyright scan, acceptance contract, stop rules, and final readiness gate.
- [ ] Run red tests, implement artifact writer/CLI, generate once, and rerun focused tests.
- [ ] Inspect every produced count/hash and update `MEMORY.md` from the canonical report.

### Task 7: Final verification

**Files:** All milestone changes.

- [ ] Run the focused registry tests and historical safety/AOM/lifecycle controls.
- [ ] Run `git diff --check` and verify frozen input hashes and `CLAUDE.md` status.
- [ ] Run the full canonical suite once at final shared-code state.
- [ ] Classify the known coordinator failure separately and require zero new failures.
- [ ] Re-run the canonical builder and prove byte-identical outputs.
