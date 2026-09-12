# QGEN Exposure Registry and Clean Transfer Validation Implementation Plan

> **For agentic workers:** Execute inline in the exact current worktree. Do not commit, reset, clean, stash, check out, or modify frozen historical artifacts.

**Goal:** Build the canonical QGEN Exposure Registry V1, select and independently prove a fresh balanced cohort, freeze Validation Contract V2, and—only after the pre-unblind gates pass—run the frozen clean transfer validation through question admission and reporting.

**Architecture:** A deterministic exposure module converts explicitly classified artifact occurrences into append-only evidence events, aggregates them without losing history, and fails closed on unclassified occurrences. A separate cohort module selects only AVAILABLE eligible rows by discipline and canonical ID, while an independent validator cross-checks selection against the registry and historical artifacts. A clean-validation runner creates append-only child artifacts around the frozen Candidate Role Registry, Catalogue V3, Discovery V6, Concept Feature Library V2, Conditional Next Action V1, Compatibility Graph V2, Bundle V4, and Question Seed V1.

**Tech Stack:** Python 3, JSON canonical hashing, pytest, existing `scripts/qbank` QGEN modules and canonical research artifacts.

**Spec:** `/Users/annabeketova/.codex/attachments/be028f60-1e52-42de-a445-0d3a2c5c9824/pasted-text.txt`

## Global Constraints

- Preserve the blocked `4227403a...` result byte-for-byte.
- Do not alter frozen medical/semantic architecture or historical artifacts.
- Use deterministic processing for parsing, joins, counts, selection, hashing, and validation.
- Fail closed on unknown or ambiguous exposure.
- Do not inspect candidate outcomes before cohort selection, independent cleanliness PASS, contract freeze, focused tests, the full pre-unblind suite, and copyright/integrity preflight.
- Do not create commits.

---

### Task 1: Exposure event and aggregation contracts

**Files:**
- Create: `tests/test_qgen_exposure_registry.py`
- Create: `scripts/qbank/qgen_exposure_registry.py`

**Interfaces:**
- Produces `classify_artifact_event`, `aggregate_registry`, canonical hash helpers, reservation-state validation, and `build_registry(root)`.

- [ ] Write fixture-based tests for Levels 0-8, ambiguous fail-closed behavior, maximum aggregation, non-downgrade, and filename-independence.
- [ ] Run the focused tests and confirm the expected missing-module/symbol failure.
- [ ] Implement the minimal explicit semantic policy and append-only aggregation.
- [ ] Run the focused tests to green and refactor only while green.

### Task 2: Historical inventory and positive controls

**Files:**
- Modify: `tests/test_qgen_exposure_registry.py`
- Modify: `scripts/qbank/qgen_exposure_registry.py`
- Create: `research/qgen/exposure/qgen_exposure_evidence_events_v1.json`
- Create: `research/qgen/exposure/qgen_exposure_registry_v1.json`
- Create: `reports/qgen_exposure_registry_v1_audit.json`

**Interfaces:**
- `build_registry(root)` reads the canonical eligible curriculum inventory and QGEN artifact families, emits events and per-unit rows, and reports the 422740 cohort's exact events.

- [ ] Add integration tests proving known Build, diagnostic Transfer, reference/evidence/model development, and consumed cohorts are exposed while inventory-only controls remain eligible.
- [ ] Run the tests RED against incomplete historical policies.
- [ ] Implement explicit content-semantic policies, defaulting unclassified occurrences to AMBIGUOUS.
- [ ] Generate the three append-only artifacts and validate their canonical hashes and summary counts.

### Task 3: Reservation and deterministic selector V2

**Files:**
- Create: `tests/test_qgen_clean_cohort_v2.py`
- Create: `scripts/qbank/qgen_clean_cohort_v2.py`
- Create: `research/qgen/exposure/qgen_clean_cohort_selection_v2.json`
- Create: `research/qgen/exposure/qgen_exposure_registry_v1_reserved.json`

**Interfaces:**
- Produces `select_clean_cohort(registry, inventory)`, `reserve_selected_units`, and stable input/cohort hashes.

- [ ] Test 18-row selection, 12-row fallback, insufficient-balanced failure, canonical ordering, prohibited-field independence, and reservation transitions.
- [ ] Run RED, implement minimally, and run GREEN.
- [ ] Select the full cohort from registry-eligible AVAILABLE units and immediately freeze its reservations.

### Task 4: Independent cleanliness proof and Validation Contract V2

**Files:**
- Modify: `tests/test_qgen_clean_cohort_v2.py`
- Create: `scripts/qbank/qgen_cleanliness_validator_v2.py`
- Create: `reports/qgen_clean_cohort_v2_cleanliness_proof.json`
- Create: `research/qgen/exposure/clean_transfer_validation_contract_v2.json`

**Interfaces:**
- Validator consumes selection, reserved registry, and independently classified historical paths; it does not call selector internals.

- [ ] Add a test that a selector false negative is caught by the independent direct-artifact cross-check.
- [ ] Run RED, implement the independent validator, and run GREEN.
- [ ] Require zero overlap and freeze all semantic hashes, rubrics, budgets, and duplicate contracts.

### Task 5: Pre-unblind gates

**Files:**
- Create: `reports/qgen_clean_transfer_v2_preflight.json`

**Interfaces:**
- Recomputes architecture hashes, blocked-artifact hashes, copyright overlap, focused results, and the canonical full suite result.

- [ ] Run focused registry/cohort tests.
- [ ] Run the canonical full suite once at the final shared-code state.
- [ ] Distinguish the documented coordinator failure from new failures.
- [ ] Run the pre-unblind copyright and integrity checks.
- [ ] Stop without unblinding unless every automatic-continuation predicate passes.

### Task 6: Frozen clean validation execution

**Files:**
- Create append-only `research/qgen/exposure/clean_transfer_v2_*.json` artifacts.
- Create: `scripts/qbank/clean_transfer_validation_v2.py`
- Create: `tests/test_clean_transfer_validation_v2.py`

**Interfaces:**
- The runner consumes the frozen cohort and contract, and emits prerequisites, reuse, Discovery V6, source-first, model proposal/reviews, evidence/entailment, universe, graph child, bundles, seeds, items, reviews, duplicate results, economics, and assessments.

- [ ] Author and review prerequisite semantics for the immutable roster without candidate visibility.
- [ ] Measure zero-authoring reuse, then run frozen Discovery V6 and freeze its wave.
- [ ] Run source-first and existing-source discovery before model hypotheses.
- [ ] Apply frozen Stage-1, pre-evidence safety, evidence, entailment, next-action, and Stage-2 gates to every candidate.
- [ ] Preserve all approved candidates and record terminal saturation passes.
- [ ] Build append-only compatibility/bundle children and coverage-driven Question Seeds.
- [ ] Generate at most one no-retry item per ready anchor, then run blind solve, liveness, final medical, and duplicate reviews.
- [ ] Run focused deterministic validation without changing shared semantic code after unblinding.

### Task 7: Final audit and resume state

**Files:**
- Create: `reports/qgen_exposure_registry_and_clean_transfer_validation_v1.json`
- Create: `reports/qgen_exposure_registry_and_clean_transfer_validation_copyright_audit.json`
- Modify only the changing `QGEN_ARCHITECTURE_RESUME` section of `MEMORY.md`.

**Interfaces:**
- Final report contains every field required by the milestone return contract and hash-pins all child artifacts.

- [ ] Recompute all counts and hashes from canonical artifacts.
- [ ] Replay historical safety, AOM, lifecycle, duplicate, and copyright gates.
- [ ] Run focused final validation and `git diff --check`.
- [ ] Confirm frozen historical artifact byte hashes and `CLAUDE.md` are unchanged.
- [ ] Update the QGEN resume section from canonical outputs and return only the prescribed result block.
