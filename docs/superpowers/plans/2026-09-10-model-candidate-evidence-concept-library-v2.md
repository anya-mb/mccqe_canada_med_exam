# Model Candidate Evidence and Concept Library V2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fairly adjudicate the frozen 27-candidate model backlog, preserve multi-origin provenance, normalize reusable concept and conditional-action evidence, build V2 candidate/graph/bundle artifacts, and exercise Question Seed V1 end to end with a bounded nonduplicate development set.

**Architecture:** Historical V1 artifacts remain immutable inputs. A new append-only milestone runner reads hash-bound V1 inputs plus explicit reviewed evidence data, applies deterministic validation and joins, and emits independently hashed V2 artifacts and one canonical report. Shared Question Seed logic receives one narrow, test-first correction for clinically distinct stages.

**Tech Stack:** Python 3, pytest, JSON, SQLite FTS metadata, SHA-256.

**Spec:** `/Users/annabeketova/.codex/attachments/fe032aa7-54c0-46e5-9fe7-707b762475e4/pasted-text.txt`

## Global Constraints

- Preserve historical HEAD `01eff40984bee76418c7fab82a1ded9fbfa2d9e5` and all frozen historical artifacts.
- Create no commits; do not reset, clean, stash, checkout, or discard existing worktree changes.
- Use Toronto Notes only for structural identity/provenance; store no substantial Toronto Notes prose.
- Keep the 27-member backlog frozen after evidence acquisition starts.
- Use deterministic code for joins, validation, counting, sorting, allocation, deduplication, and hashes.
- No clean Transfer cohort, fresh operational holdout, mass generation, retries, or more than 12 development questions.

---

### Task 1: Question Seed stage-aware duplicate contract

**Files:**
- Modify: `scripts/qbank/question_seed.py`
- Test: `tests/test_question_seed.py`

**Interfaces:**
- Consumes: two valid `QUESTION_SEED_V1` mappings.
- Produces: `classify_seed_duplicate(left, right) -> str`, returning `RELATED_BUT_DISTINCT` when the same illness/key is tested at a substantively different clinical stage.

- [ ] Add a failing test asserting same illness + same key + different clinical stage is allowed as `RELATED_BUT_DISTINCT`.
- [ ] Run `python3 -m pytest tests/test_question_seed.py -q` and confirm the new test fails as `NEAR_DUPLICATE`.
- [ ] Add the minimal clinical-stage comparison before the near-duplicate return.
- [ ] Rerun the focused test and confirm PASS.

### Task 2: Frozen cohort, pre-evidence screen, and provenance V2

**Files:**
- Create: `scripts/qbank/candidate_evidence_v2.py`
- Create: `tests/test_candidate_evidence_v2.py`
- Create: `research/qgen/contrast_supply/model_candidate_review_inputs_v1.json`

**Interfaces:**
- Consumes: `anchor_candidate_universe_v1.json`, Stage-1/Stage-2 V1 reviews, Catalogue V3, TN SQLite structural metadata.
- Produces: exact 27-row cohort, deterministic pre-evidence screen, TN replay, and additive candidate provenance.

- [ ] Write failing tests for exact cohort membership/hash stability, zero duplicate candidate rows, multi-origin retention, and fail-closed invalid review inputs.
- [ ] Run the new test module and confirm RED due to the absent runner.
- [ ] Implement frozen-input validation, canonical hashes, TN structural replay, and provenance joins.
- [ ] Run the focused tests and confirm GREEN.

### Task 3: Evidence packets, entailment, Stage-2 review, and concept library

**Files:**
- Modify: `scripts/qbank/candidate_evidence_v2.py`
- Modify: `tests/test_candidate_evidence_v2.py`
- Create: `research/qgen/contrast_supply/model_candidate_review_inputs_v1.json`

**Interfaces:**
- Consumes: source records, normalized propositions, independent entailment verdicts, independent candidate verdicts.
- Produces: evidence packets, terminal Stage-2 verdicts, concept-fact scope review, `CONCEPT_FEATURE_LIBRARY_V2`, and `CONDITIONAL_NEXT_ACTION_V1`.

- [ ] Write failing tests for terminal verdicts, load-bearing ENTAILED-only facts, two-source/exception status, compatibility fail-closed behavior, and nonzero safe reuse.
- [ ] Confirm RED.
- [ ] Implement evidence validation, scope classification, concept-level deduplication/reference links, and conditional action branches.
- [ ] Confirm GREEN.

### Task 4: Candidate Universe V2, graph V2, bundles V4, and saturation

**Files:**
- Modify: `scripts/qbank/candidate_evidence_v2.py`
- Modify: `tests/test_candidate_evidence_v2.py`

**Interfaces:**
- Consumes: terminal candidate reviews and V2 concept/action evidence.
- Produces: immutable-child `ANCHOR_CANDIDATE_UNIVERSE_V2`, compatibility graph, expanded bundles, density/quality tiers, pairwise economics, and fully adjudicated saturation metrics.

- [ ] Write failing tests asserting V1 is unchanged, approved V2 membership is additive, reserves are untruncated, all new approvals are tiered, and saturation has no unreviewed backlog.
- [ ] Confirm RED.
- [ ] Implement deterministic universe, graph, bundle, tier, density, and saturation builders.
- [ ] Confirm GREEN.

### Task 5: Question Seed end-to-end development exercise

**Files:**
- Modify: `scripts/qbank/candidate_evidence_v2.py`
- Modify: `tests/test_candidate_evidence_v2.py`

**Interfaces:**
- Consumes: V2 bundles, concept facts, action branches, existing Question Seed fingerprints.
- Produces: bounded seed population, pre-generation duplicate review, deterministic subsets, at most 12 no-retry items, blind solve, liveness, final medical review, and semantic duplicate review.

- [ ] Write failing tests for unique-seed generator reachability, pre-generation duplicate refusal, deterministic RNG/subset selection, at least two same-topic/different-decision pairs, and admission only after all reviews pass.
- [ ] Confirm RED.
- [ ] Implement the bounded data-driven lifecycle and artifacts.
- [ ] Confirm GREEN.

### Task 6: Canonical outputs, safety, copyright, and resume state

**Files:**
- Modify: `scripts/qbank/candidate_evidence_v2.py`
- Modify: `MEMORY.md`
- Create: V2 research/report JSON artifacts declared by the runner.

**Interfaces:**
- Consumes: all prior task outputs and verification counts.
- Produces: final milestone report, copyright audit, and updated QGEN resume state.

- [ ] Run the milestone writer twice and verify identical content hashes.
- [ ] Run focused QGEN tests and historical safety controls.
- [ ] Run the canonical full suite once at the final shared-code state and classify only the known coordinator failure as pre-existing.
- [ ] Run `git diff --check`, verify `CLAUDE.md` unchanged, inspect frozen-artifact hashes, and run the copyright audit.
- [ ] Update only the changing QGEN resume section in `MEMORY.md`, then re-run final checks that include it.
