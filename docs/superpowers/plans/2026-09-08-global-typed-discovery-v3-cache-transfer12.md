# Global Typed Discovery V3, Cache V2, and Transfer-12 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:test-driven-development and superpowers:verification-before-completion. Execute inline in the exact current worktree; do not commit.

**Goal:** Freeze an outcome-blind Transfer-12 cohort, build and validate global typed Discovery V3 and append-only Cache V2 on Build-12 only, then unblind Transfer-12 for zero-top-up and one-top-up evaluation and, when safe, a bounded development question smoke test.

**Architecture:** Add deterministic catalogue, discovery, cache-versioning, and experiment-orchestration functions alongside the existing contrast-supply module. Canonical JSON artifacts carry hashes, stage inputs, review decisions, metrics, and embargo state. Shared algorithms freeze before Transfer unblinding; Transfer may add reviewed data to Cache V3 but may not change shared semantics.

**Tech Stack:** Python 3, SQLite/FTS structural metadata, JSON, pytest, existing QGEN validators.

**Spec:** `/Users/annabeketova/.codex/attachments/c424ad73-87f5-4d3b-b7e1-d76a61af216e/pasted-text.txt`

## Global Constraints

- Preserve all historical and frozen artifacts byte-identically.
- Build and evaluate Discovery V3 on Build-12 before inspecting Transfer candidate outcomes.
- Use structural/canonical metadata only for candidate identity; never infer identities from medical knowledge or paragraph prose.
- Candidate budget is at most 10 unique canonical concepts per opportunity and one wave only.
- Deterministic filters precede sequential semantic review; uncertain decisions fail closed.
- Cache V2 and V3 are append-only and require explicit version selection.
- Require three pairwise-coherent, anchored, non-second-key competitors for contrast readiness.
- Run one final canonical suite after the last shared-code change; report the known unrelated coordinator failure separately.
- Create no commits and do not change `CLAUDE.md`.

---

### Task 1: Reconcile and freeze Transfer-12

**Files:**
- Create: `research/qgen/contrast_supply/transfer_12_selection_v1.json`
- Create: `research/qgen/contrast_supply/transfer_12_opportunity_semantics_v1.json`
- Test: `tests/test_contrast_supply_v3.py`

- [ ] Write selection tests for exact 2-per-discipline balance, exclusions, determinism, and candidate-outcome blindness.
- [ ] Run the focused test and verify RED.
- [ ] Implement deterministic selection and hash helpers.
- [ ] Run the focused test and verify GREEN.
- [ ] Freeze the roster before any V3 catalogue/discovery query and prepare independently reviewed opportunity semantics without candidate inspection.

### Task 2: Build the global candidate concept catalogue

**Files:**
- Create: `scripts/qbank/contrast_supply_v3.py`
- Create: `research/qgen/contrast_supply/global_candidate_concept_catalogue_v1.json`
- Test: `tests/test_contrast_supply_v3.py`

- [ ] Write tests for generic/fragment exclusion, alias merging, parent/subtype preservation, provenance, known AOM/HbA1c/TTE identities, and absence of paragraph prose.
- [ ] Run tests and verify RED.
- [ ] Implement deterministic catalogue construction from structural/canonical sources.
- [ ] Run tests and verify GREEN, then build and hash the canonical catalogue.

### Task 3: Implement and freeze Discovery V3

**Files:**
- Modify: `scripts/qbank/contrast_supply_v3.py`
- Create: `research/qgen/contrast_supply/build_12_discovery_v3.json`
- Test: `tests/test_contrast_supply_v3.py`

- [ ] Write tests for same-unit, cross-unit, cross-chapter discovery; response-class, key-alias, and generic exclusion; preservation of AOM/HbA1c/TTE; and non-equivalence to V1/V2 locality.
- [ ] Run tests and verify RED.
- [ ] Implement typed deterministic filtering/ranking and a strict ten-candidate budget.
- [ ] Run tests and verify GREEN.
- [ ] Run exactly one Build-12 V3 wave and freeze its output before semantic review.

### Task 4: Review Build-12 V3 and build Cache V2

**Files:**
- Create: `research/qgen/contrast_supply/build_12_v3_semantic_review.json`
- Create: `research/qgen/contrast_supply/build_12_v3_relations_v2.json`
- Create: `research/qgen/contrast_supply/reusable_contrast_cache_v2.json`
- Create: `reports/qgen_build12_v3_cache_v2_validation.json`

- [ ] Apply unchanged cheap filters and record candidate-level rejection taxonomy.
- [ ] Review survivors sequentially in canonical batches of at most six and persist every batch.
- [ ] Author/reuse evidence-grounded relations and perform a separate independent review pass.
- [ ] Build Cache V2 append-only from Cache V1 plus approved entries and verify all scope/safety controls.
- [ ] Replay the same eight prerequisite-ready Build-12 opportunities with no additional discovery and classify density.

### Task 5: Freeze architecture and evaluate Transfer-12

**Files:**
- Create: `research/qgen/contrast_supply/discovery_v3_cache_v2_freeze.json`
- Create: `research/qgen/contrast_supply/transfer_12_discovery_v3.json`
- Create: `research/qgen/contrast_supply/transfer_12_semantic_review.json`
- Create: `research/qgen/contrast_supply/transfer_12_relations_v2.json`
- Create: `research/qgen/contrast_supply/reusable_contrast_cache_v3.json`
- Create: `reports/qgen_transfer12_v3_cache_validation.json`

- [ ] Hash and freeze catalogue, algorithm/version, tests, budget, ranking contract, Cache V2, and Build-12 result.
- [ ] Unblind the fixed roster and measure Cache V1 then Cache V2 zero-top-up baselines.
- [ ] Run exactly one unchanged V3 top-up on non-ready opportunities and freeze candidates before review.
- [ ] Apply unchanged cheap/semantic/relation review gates, then build append-only Cache V3.
- [ ] Replay final Transfer density and compute zero-top-up versus one-top-up economics.

### Task 6: Conditional development smoke and final verification

**Files:**
- Create when triggered: `research/qgen/contrast_supply/transfer_12_development_smoke.json`
- Create: `reports/qgen_global_typed_discovery_v3_cache_transfer12_milestone.json`
- Modify: `MEMORY.md`

- [ ] If at least one Transfer opportunity is contrast-ready, run at most six canonical opportunities through one stem attempt, blind solve, post-stem liveness, realization, rationales, and independent final review with no retry.
- [ ] Run historical safety, lifecycle, AOM, cache-version, and copyright checks.
- [ ] Run focused tests, `git diff --check`, and the canonical full suite once after the final shared-code state.
- [ ] Reconcile `MEMORY.md` from canonical artifacts and verify hashes/status against the final report.

