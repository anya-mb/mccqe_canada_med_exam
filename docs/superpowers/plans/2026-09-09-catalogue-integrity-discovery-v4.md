# Catalogue Integrity and Discovery V4 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:test-driven-development to implement this plan task-by-task and superpowers:verification-before-completion before every completion claim. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Repair the candidate catalogue as a new immutable child, diagnose the frozen V3 Transfer failures, implement reviewed decision-signature filtering, replay Build-12 and diagnostic Transfer-12, and decide whether a new cohort may be frozen.

**Architecture:** Preserve V3 byte-identically and implement catalogue audit, signature validation, V4 discovery, replay, and reporting in new modules. Canonical JSON artifacts bind every input by content hash and distinguish authored semantic evidence from deterministic calculations.

**Tech Stack:** Python 3.13, SQLite, JSON, pytest, existing QGEN canonical hash and copyright utilities.

**Spec:** `docs/superpowers/specs/2026-09-09-catalogue-integrity-discovery-v4-design.md`

## Global Constraints

- Do not modify any frozen V1/V3/cache/Transfer artifact or the V3 implementation.
- Do not select or run a new transfer cohort before the readiness gate.
- Use no external LLM API, embeddings, chapter prose, or generated candidate identity.
- Maximum new pre-design semantic reviews is 12; semantic work is serial.
- Run the full canonical suite once at final shared-code state.
- Create no commits and do not change `CLAUDE.md`.

---

### Task 1: Freeze diagnostic status and audit the catalogue

**Files:**
- Create: `scripts/qbank/contrast_supply_v4.py`
- Test: `tests/test_contrast_supply_v4.py`
- Create: `research/qgen/contrast_supply/transfer_12_diagnostic_classification_v1.json`
- Create: `reports/qgen_candidate_catalogue_integrity_audit_v1.json`

**Interfaces:**
- Produces: `classify_catalogue_label(row) -> CatalogueAuditResult` and `audit_catalogue(rows) -> dict`.

- [ ] Write literal failing tests for the known corrupt row, representative OCR/furniture/sentence fragments, and valid long medical and reviewed action labels.
- [ ] Run the focused tests and verify the expected RED failures.
- [ ] Implement ordered taxonomy classification with explicit reason codes.
- [ ] Run the focused tests and verify GREEN.
- [ ] Generate the diagnostic-status and all-1,919-row audit artifacts with frozen hashes.

### Task 2: Build clean Catalogue V2

**Files:**
- Modify: `scripts/qbank/contrast_supply_v4.py`
- Modify: `tests/test_contrast_supply_v4.py`
- Create: `scripts/qbank/run_contrast_supply_v4.py`
- Create: `research/qgen/contrast_supply/global_candidate_concept_catalogue_v2.json`

**Interfaces:**
- Produces: `build_global_candidate_catalogue_v2(connection, reviewed_identities, parent_rows) -> dict`.

- [ ] Write failing rebuild tests proving invalid and uncertain rows are absent, provenance is preserved, and valid complex controls survive.
- [ ] Run RED, implement the minimal V2 rebuild, and run GREEN.
- [ ] Generate V2, verify parent hash/count arithmetic, and run the canonical copyright scanner before proceeding.

### Task 3: Reconstruct and classify the 52 failures

**Files:**
- Modify: `scripts/qbank/run_contrast_supply_v4.py`
- Modify: `tests/test_contrast_supply_v4.py`
- Create: `reports/qgen_discovery_v3_wrong_decision_diagnosis_v1.json`

**Interfaces:**
- Produces: `reconstruct_v3_wrong_decisions(...) -> list[dict]` and a count reconciliation requiring exactly 52 rows.

- [ ] Write failing join/count tests that reject missing, duplicate, or non-WRONG_DECISION rows.
- [ ] Run RED, implement the deterministic reconstruction, and run GREEN.
- [ ] Apply one earliest semantic-mismatch classification to every row, reconcile counts to 52, and determine the dominant V3 gap quantitatively.

### Task 4: Define and independently review Decision Signature V1

**Files:**
- Create: `research/qgen/contrast_supply/decision_signature_v1.json`
- Create: `reports/qgen_decision_signature_v1_independent_review.json`
- Create: `reports/qgen_decision_signature_v1_economy.json`

**Interfaces:**
- Provides controlled values for `decision_intent`, `target_domain`, `clinical_stage`, and reviewed stage adjacency.

- [ ] Map known-good AOM, HbA1c, TTE, chest-radiography, Build-12, and diagnostic Transfer examples.
- [ ] Measure dimension/value counts, single-use values, and cross-unit/cross-discipline reuse.
- [ ] Perform a separate blinded contract review for meaning, nonredundancy, safety, future-distractor independence, and disease independence.
- [ ] Revise until the review verdict is `APPROVED`, or stop if the contract is unsafe.

### Task 5: Implement signature validation and Discovery V4

**Files:**
- Modify: `scripts/qbank/contrast_supply_v4.py`
- Modify: `tests/test_contrast_supply_v4.py`

**Interfaces:**
- Produces: `validate_decision_signature`, `signatures_compatible`, and `discover_global_typed_candidates_v4`.

- [ ] Write failing behavior tests for every required preservation and rejection control.
- [ ] Run RED and confirm each test fails for the missing signature gate.
- [ ] Implement schema validation, compatibility, deterministic rejection provenance, and V4 ranking with a ten-candidate budget.
- [ ] Run focused GREEN tests and historical-safety controls.

### Task 6: Replay Build-12 and diagnostic Transfer-12

**Files:**
- Modify: `scripts/qbank/run_contrast_supply_v4.py`
- Create: `research/qgen/contrast_supply/build_12_discovery_v4.json`
- Create: `research/qgen/contrast_supply/diagnostic_transfer_12_discovery_v4.json`
- Create: `reports/qgen_discovery_v4_precision_and_readiness.json`

**Interfaces:**
- Consumes the frozen V3 waves/reviews, Catalogue V2, and signature registry.
- Produces hash-bound replay funnels, exact-hash verdict reuse, precision, economics, safety, and readiness.

- [ ] Freeze the V4 implementation hash before replay.
- [ ] Run one Build-12 replay, reuse exact frozen verdicts, and review only genuinely new survivors.
- [ ] Run one diagnostic Transfer replay without adapting V4 to individual outcomes.
- [ ] Compute wrong-decision rate, diversity/yield, reviews avoided, and all readiness criteria.
- [ ] Freeze a new outcome-blind cohort only if readiness is `YES`; never run it in this milestone.

### Task 7: Final verification and resume state

**Files:**
- Modify: `MEMORY.md`
- Create: `reports/qgen_catalogue_repair_and_discovery_v4_milestone.json`

- [ ] Run focused tests, historical frozen-hash checks, lifecycle/AOM controls, and copyright scans.
- [ ] Run the full canonical suite once at final shared-code state and separate the known unrelated failure.
- [ ] Run `git diff --check`, prove frozen artifacts unchanged and `CLAUDE.md` unchanged, then update only the QGEN resume block.
- [ ] Re-run report validation after the MEMORY update and return the exact requested final template.
