# Clean Transfer-18 Model Expansion Validation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:test-driven-development while adding any executable validation support. This milestone must run serially because semantic concurrency is capped at one.

**Goal:** Execute the frozen 48-phase clean Transfer-18 protocol against cohort `4227403aae3940b8c78a5ec3aeddaaa1fb5bb34342df5a4bc9a0a9a80eabab7b`, through candidate/evidence reuse, source-first and model expansion, bundle construction, bounded Question Seed generation, independent review, economics, safety, and resume-state reporting.

**Architecture:** Add one append-only, cohort-specific deterministic runner that hash-pins all semantic inputs before unblinding and consumes explicit semantic-review data afterward. Existing V2/V6 architecture and historical artifacts remain immutable. The runner performs only validation, joins, counting, hashing, lifecycle enforcement, and report generation; medical judgments and evidence entailment live in explicit reviewed JSON inputs.

**Tech Stack:** Python 3, pytest, JSON, SQLite structural metadata, SHA-256, canonical repository validators.

**Spec:** `/Users/annabeketova/.codex/attachments/e0f94241-5b6b-4c52-8911-8a7d24c48d36/pasted-text.txt`

## Global Constraints

- Starting HEAD is `01eff40984bee76418c7fab82a1ded9fbfa2d9e5`; preserve the exact current worktree and all user WIP.
- Create no commits; do not reset, clean, stash, checkout, discard, or rewrite historical frozen artifacts.
- Freeze the complete semantic contract and prove cohort cleanliness before inspecting candidate supply or roster clinical content.
- After unblinding, make no semantic architecture changes. Poor yield is an experimental result.
- Toronto Notes is structural/topic-discovery evidence only; use no substantial prose and never treat it as sole current clinical authority.
- Semantic work is serial. Model proposals are concepts only and are never evidence.
- Use the frozen saturation policy and finish every proposed candidate with a terminal Stage-2 verdict before declaring a pass complete.
- Generate at most 18 questions, initially at most one per contrast-ready anchor, with one attempt and no retries.

---

### Task 1: Pre-unblinding contract and cleanliness gate

**Files:**
- Create: `tests/test_clean_transfer_18_model_validation.py`
- Create: `scripts/qbank/clean_transfer_18_model_validation.py`
- Create: `research/qgen/contrast_supply/clean_transfer18_validation_contract_v1.json`
- Create: `reports/qgen_clean_transfer18_cleanliness_proof.json`

**Interfaces:**
- Consumes metadata from `new_clean_transfer_18_selection_v2.json` plus explicit hashes of the V2/V6 schemas, contracts, code, registries, libraries, graphs, bundles, and duplicate classifiers.
- Produces `build_validation_contract(root) -> dict`, `verify_clean_cohort(root, contract) -> dict`, and `verify_frozen_contract(root, contract) -> dict`.

- [ ] Write tests that require the exact cohort hash/balance, `FROZEN_NOT_RUN`, `holdout_consumed=false`, no overlap with every historical cohort/holdout/pilot roster, all semantic paths hash-pinned, and drift rejection.
- [ ] Run the focused test and observe the expected import failure.
- [ ] Implement the minimal metadata-only contract builder and cleanliness validator.
- [ ] Run focused tests green, write the contract/cleanliness artifacts, and rerun them byte-identically.
- [ ] Run the pre-unblinding focused architecture tests and freeze the resulting test count.

### Task 2: Candidate-hidden prerequisite semantics and zero-authoring baseline

**Files:**
- Create: `research/qgen/contrast_supply/clean_transfer18_prerequisite_semantics_v1.json`
- Create: `research/qgen/contrast_supply/clean_transfer18_zero_authoring_reuse_v1.json`
- Modify: `tests/test_clean_transfer_18_model_validation.py`
- Modify: `scripts/qbank/clean_transfer_18_model_validation.py`

**Interfaces:**
- Consumes the frozen 18-row cohort and existing approved V2/V6 libraries.
- Produces candidate-hidden learner-decision/key/signature rows, then an exact reuse-only baseline with per-anchor and aggregate fact/action/edge/bundle counts.

- [ ] Add tests that reject candidate fields in prerequisite rows and prevent replacement or denominator drift.
- [ ] Observe RED; implement validation and deterministic reuse joins; observe GREEN.
- [ ] Freeze all 18 prerequisite rows before candidate retrieval and record the unblinding transition.

### Task 3: Frozen discovery, source-first acquisition, proposals, and two-stage review

**Files:**
- Create: `research/qgen/contrast_supply/clean_transfer18_candidate_review_inputs_v1.json`
- Create: `research/qgen/contrast_supply/clean_transfer18_discovery_v6_v1.json`
- Create: `research/qgen/contrast_supply/clean_transfer18_source_first_v1.json`
- Create: `research/qgen/contrast_supply/clean_transfer18_model_proposals_v1.json`
- Create: `research/qgen/contrast_supply/clean_transfer18_candidate_reviews_v1.json`
- Modify: `tests/test_clean_transfer_18_model_validation.py`
- Modify: `scripts/qbank/clean_transfer_18_model_validation.py`

**Interfaces:**
- Consumes frozen V6/Catalogue/Role Registry, Toronto Notes structural metadata, existing source/evidence identities, and explicit serial semantic reviews.
- Produces provenance-preserving source/model pools, deterministic pre-evidence rejects, entailed evidence packets, conditional next actions, terminal Stage-2 verdicts, and saturation-pass accounting.

- [ ] Test exact provenance, source-before-model ordering, blinded Stage-1 review vocabulary, deterministic reject-before-research, ENTAILED-only approval, stronger model evidence, terminal reviews, and saturation reconciliation.
- [ ] Observe RED; implement only deterministic validators/builders; observe GREEN.
- [ ] Run serial candidate proposal, evidence acquisition, entailment, and Stage-2 review to completion for every backlog row.

### Task 4: Transfer universe, compatibility graph, and expanded bundles

**Files:**
- Create: `research/qgen/contrast_supply/clean_transfer18_candidate_universe_v1.json`
- Create: `research/qgen/contrast_supply/candidate_compatibility_graph_v3_transfer.json`
- Create: `research/qgen/contrast_supply/clean_transfer18_contrast_bundles_v1.json`
- Modify: `tests/test_clean_transfer_18_model_validation.py`
- Modify: `scripts/qbank/clean_transfer_18_model_validation.py`

**Interfaces:**
- Consumes only terminal Stage-2-approved Transfer candidates plus safely reusable V2 concept/action/edge evidence.
- Produces untruncated per-anchor universes, additive reviewed graph edges, A/B/C candidate tiers, bundle density, feature coverage, and reuse/economic metrics.

- [ ] Test approved-only admission, reserve preservation, no arbitrary maximum, next-action gap reporting, edge provenance, and exact density thresholds through 20.
- [ ] Observe RED; implement deterministic builders; observe GREEN.

### Task 5: Question Seed lifecycle and duplicate prevention

**Files:**
- Create: `research/qgen/contrast_supply/clean_transfer18_question_seeds_v1.json`
- Create: `research/qgen/contrast_supply/clean_transfer18_questions_v1.json`
- Create: `research/qgen/contrast_supply/clean_transfer18_blind_solve_v1.json`
- Create: `research/qgen/contrast_supply/clean_transfer18_liveness_v1.json`
- Create: `research/qgen/contrast_supply/clean_transfer18_final_medical_review_v1.json`
- Create: `research/qgen/contrast_supply/clean_transfer18_duplicate_review_v1.json`
- Modify: `tests/test_clean_transfer_18_model_validation.py`
- Modify: `scripts/qbank/clean_transfer_18_model_validation.py`

**Interfaces:**
- Consumes frozen Transfer bundles, Question Seed V1 schema/fingerprint, deterministic subset selection, and frozen evidence.
- Produces coverage-driven seeds, pre-generation duplicate verdicts, no-retry generated items, blind solves, distractor liveness, rationales, final reviews, and post-generation semantic duplicate verdicts.

- [ ] Test pre-generation rejection before callbacks, one question per ready anchor, maximum 18, no retry/swap/research, three live distractors, evidence-bounded rationales, final-review admission, and duplicate fail-closed behavior.
- [ ] Observe RED; implement deterministic lifecycle joins; observe GREEN.
- [ ] Execute serial independent blind-solve and final-review passes.

### Task 6: Canonical assessment, safety, copyright, and resume state

**Files:**
- Create: `reports/qgen_clean_transfer18_model_expansion_validation.json`
- Create: `reports/qgen_clean_transfer18_model_expansion_copyright_audit.json`
- Modify: `MEMORY.md`

**Interfaces:**
- Consumes all frozen phase outputs and fresh validator/test results.
- Produces every exact final-return metric, separate architecture assessments, the production decision gate, one dominant bottleneck if not ready, and the next step.

- [ ] Rebuild every generated artifact twice and verify identical canonical hashes.
- [ ] Verify architecture hashes and all historical safety/AOM/lifecycle controls.
- [ ] Run focused tests, then the full suite only if shared executable code changed before unblinding.
- [ ] Run the canonical copyright/leak audit over every new artifact.
- [ ] Update only the changing QGEN resume section in `MEMORY.md` from canonical metrics.
- [ ] Run `git diff --check`, verify `CLAUDE.md` unchanged, confirm zero commits and zero historical frozen-artifact modifications, and render the exact required final return.
