# Expanded Candidate Universe and Evidence Economy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and validate the development-only expanded candidate-universe, reusable evidence-card/compatibility-graph, and deterministic question-seed architecture requested in the approved 2026-09-10 milestone brief.

**Architecture:** Add append-only deterministic contracts downstream of the frozen Candidate Feature Evidence and Bundle V2 artifacts. A single reproducible milestone runner will join frozen inputs with separately recorded proposal/review data, fail closed on unsupported candidates, emit hash-bound V1/V3 artifacts, replay the existing ten development items through semantic seed fingerprints, and produce one final accounting report. No clean Transfer cohort, operational holdout, production question generation, frozen-artifact edit, branch operation, or commit is permitted.

**Tech Stack:** Python 3 standard library, JSON/JSON Schema, pytest, existing QGEN deterministic helpers.

**Spec:** `/Users/annabeketova/.codex/attachments/d85b7c54-86b9-4156-a937-4a6c2e52be6b/pasted-text.txt`

## Global Constraints

- Work from exact HEAD `01eff40984bee76418c7fab82a1ded9fbfa2d9e5` and preserve all existing dirty-worktree changes.
- Use the existing 18 consumed development anchors; do not create or run a clean cohort or operational holdout.
- Never admit `REJECTED` or `UNCERTAIN` candidates; model proposals are hypotheses, not evidence.
- Preserve source provenance and fail closed whenever evidence, review, response class, granularity, or pairwise safety is missing.
- Do not modify frozen historical artifacts and do not commit.
- Use TDD for all shared code and run the full suite once after the final shared-code state.

---

### Task 1: Candidate-universe and review contracts

**Files:**
- Create: `scripts/qbank/candidate_universe.py`
- Create: `tests/test_candidate_universe.py`
- Create: `schemas/anchor-candidate-universe-v1.schema.json`

**Interfaces:**
- Consumes: frozen reference set/review, prerequisites, catalogue, candidate-role registry, Bundle V2.
- Produces: `canonical_content_hash`, `normalize_candidate_text`, `validate_candidate`, `build_candidate_universe`, `candidate_density_metrics`.

- [ ] Write failing tests proving duplicate canonical concepts collapse, origin is mandatory, the 24-proposal ceiling is enforced, source-first ordering is recorded, and only Stage-1 `PLAUSIBLE` plus Stage-2 `APPROVED` candidates enter the approved universe.
- [ ] Run `pytest tests/test_candidate_universe.py -q` and confirm the missing module/contracts fail.
- [ ] Implement the minimal deterministic builders and validators.
- [ ] Run `pytest tests/test_candidate_universe.py -q` and confirm all tests pass.

### Task 2: Reusable evidence cards, next-step coverage, and compatibility graph

**Files:**
- Modify: `scripts/qbank/candidate_universe.py`
- Modify: `tests/test_candidate_universe.py`
- Create: `schemas/concept-feature-card-v1.schema.json`
- Create: `schemas/candidate-compatibility-graph-v1.schema.json`

**Interfaces:**
- Consumes: V1 evidence registry, approved V2 profiles/bundles, reference review, applicability scopes.
- Produces: `build_concept_cards`, `build_compatibility_graph`, `derive_pairwise_edge`, `evidence_economy_metrics`.

- [ ] Write failing tests proving only `ENTAILED` facts are reusable, scope is preserved, action-context facts can satisfy `NEXT_ACTION_IF_THIS_CONTEXT_WERE_PRESENT`, diagnosis next steps remain missing without direct evidence, unsafe/nested candidates become exclusion edges, and sparse graphs never invent comparisons.
- [ ] Run the focused tests and confirm expected failures.
- [ ] Implement cards, next-step classification, reusable fact accounting, and evidence-derived graph edges.
- [ ] Run the focused tests and confirm all pass.

### Task 3: Question Seed V1 and semantic duplicate prevention

**Files:**
- Create: `scripts/qbank/question_seed.py`
- Create: `tests/test_question_seed.py`
- Create: `schemas/question-seed-v1.schema.json`

**Interfaces:**
- Consumes: approved universe/bundles, anchor prerequisites, existing development questions.
- Produces: `seed_fingerprint`, `validate_question_seed`, `classify_seed_duplicate`, `item_semantic_fingerprint`, `classify_item_duplicate`, `select_candidate_subset`.

- [ ] Write failing tests for required fields, deterministic fingerprints, reproducible subset selection, response-class/granularity safety, pre-generation duplicate rejection, and post-generation `NEAR_DUPLICATE`/`DUPLICATE` rejection.
- [ ] Run the focused tests and confirm expected failures.
- [ ] Implement the minimal seed and duplicate contracts.
- [ ] Run the focused tests and confirm all pass.

### Task 4: Reproducible milestone runner and append-only artifacts

**Files:**
- Create: `scripts/qbank/run_expanded_candidate_universe_v1.py`
- Create: `tests/test_expanded_candidate_universe_milestone.py`
- Create: `research/qgen/contrast_supply/expanded_candidate_proposals_v1.json`
- Generate append-only artifacts under `research/qgen/contrast_supply/` and reports under `reports/`.

**Interfaces:**
- Consumes: Tasks 1-3 plus frozen canonical inputs.
- Produces: Anchor Candidate Universe V1, Concept Feature Card V1, Compatibility Graph V1, Bundle V3, Question Seed V1, duplicate replay, economics, copyright audit, and milestone report.

- [ ] Write failing integration tests proving exact input hashes, 18-anchor freeze, two bounded zero-yield saturation passes, provenance accounting, fail-closed generated proposals, full-universe preservation, no new production items, immutable historical hashes, and deterministic replay.
- [ ] Run the integration test and confirm expected failures.
- [ ] Author bounded candidate concept proposals only, with separate Stage-1 and Stage-2 records; do not treat proposal prose as evidence.
- [ ] Implement the runner and emit deterministic artifacts.
- [ ] Re-run the integration test and confirm all pass.

### Task 5: Historical safety, copyright, final verification, and resume state

**Files:**
- Modify: `MEMORY.md` only in `QGEN_ARCHITECTURE_RESUME`.
- Modify: final milestone report verification fields.

**Interfaces:**
- Consumes: all milestone outputs and existing historical controls.
- Produces: final verified accounting and exact next step.

- [ ] Run focused candidate-universe, seed, feature-evidence, lifecycle, AOM, and historical exclusion tests.
- [ ] Run copyright/leak audit over every new artifact and require PASS.
- [ ] Run the canonical full pytest suite once at final shared-code state; separate known unrelated coordinator failures if any.
- [ ] Re-run the milestone determinism/integrity test, `git diff --check`, hash checks for frozen inputs, and verify `CLAUDE.md` unchanged.
- [ ] Update only the QGEN resume section in `MEMORY.md`, regenerate the final report verification fields, and repeat final checks because canonical executable state changed.

