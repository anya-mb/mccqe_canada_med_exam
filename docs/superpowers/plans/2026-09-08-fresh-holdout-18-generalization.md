# Fresh Holdout 18 Generalization and Seed Economics Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Freeze and execute a genuinely fresh 18-opportunity, six-discipline QGEN holdout through the repaired centralized lifecycle gate, then report generalization, safety, failure-stage, and seed/review economics without changing the frozen architecture.

**Architecture:** Add a holdout-18 orchestration module that consumes the prepared unselected eligibility inventory, freezes a deterministic roster and architecture hash manifest before clinical work, and validates phase-specific JSON artifacts. Clinical evidence, feature maps, candidate reviews, wave seed packs, stems, and final reviews remain explicit content-addressed artifacts; the runner only admits independently approved upstream objects and calls the existing `generation_lifecycle.execute_generation` boundary immediately before the generator callback.

**Tech Stack:** Python 3, pytest, canonical JSON artifacts, SHA-256 content pinning, existing QGEN Profile V2/retrieval/onboarding/generation modules.

**Spec:** `/Users/annabeketova/.codex/attachments/fea51f91-5d37-422d-b106-16aee8d60ab0/pasted-text.txt`

## Global Constraints

- Work from the exact dirty worktree; do not reset, clean, stash, checkout, discard, or overwrite existing WIP.
- Create no commits.
- The contaminated 24 remains a development regression set and is never selected.
- Freeze 3 opportunities per discipline without inspecting seed or contrast signals; never substitute after freeze.
- Freeze architecture hashes immediately after roster freeze; any later executable architecture change contaminates and stops the run.
- Maximum semantic-review concurrency is one; use a fresh high-reasoning reviewer context for feature, seed/relation/anchor, blind-solve, and final-item review.
- Exactly one bounded seed-acquisition wave and one stem attempt per eligible opportunity; no retries.
- Low yield is not a hard stop. Fail closed on missing evidence, uncertain review, unsafe contrast, or item ambiguity.
- Do not modify `CLAUDE.md`, historical seed packs, historical holdout artifacts, or frozen curriculum/allocation layers.

---

### Task 1: Phase 0 reconciliation and deterministic freeze contract

**Files:**
- Create: `scripts/qbank/fresh_holdout_18.py`
- Create: `tests/test_fresh_holdout_18.py`
- Create: `research/qgen/holdout/fresh_holdout_18_opportunities.json`
- Create: `research/qgen/holdout/fresh_holdout_18_architecture_freeze.json`

**Interfaces:**
- Consumes: `next_fresh_holdout_eligibility_inventory.json`, `historical_exclusion_inventory.json`, canonical allocation/source artifacts, and frozen architecture inputs.
- Produces: `select_fresh_holdout_18(root) -> dict`, `build_architecture_freeze(root, roster) -> dict`, and `verify_freeze_integrity(root, roster, freeze) -> dict`.

- [ ] Write failing tests for exact 3x6 balance, unique study units/addresses/decision signatures/key concepts, zero historical overlap, no selection-time contrast fields, unconsumed inventory, deterministic wave partition, content hashes, and architecture-hash drift detection.
- [ ] Run the focused tests and observe the intended failures.
- [ ] Implement the minimum deterministic selectors and hash manifest, using CORE/IMPORTANT, evidence readiness, MCC relevance, educational distinctness, and canonical order only.
- [ ] Freeze the roster and three six-case waves before any retrieval or candidate inspection.
- [ ] Run the focused tests and verify they pass.

### Task 2: Evidence and early feature-review gates

**Files:**
- Modify: `scripts/qbank/fresh_holdout_18.py`
- Modify: `tests/test_fresh_holdout_18.py`
- Create: `research/qgen/holdout/fresh_holdout_18_decision_evidence.json`
- Create: `research/qgen/holdout/fresh_holdout_18_feature_maps.json`
- Create: `research/qgen/holdout/fresh_holdout_18_feature_independent_review.json`

**Interfaces:**
- Produces one evidence verdict per frozen opportunity and one immutable feature-map review row per evidence-ready opportunity.
- A feature map may proceed only when its review is `APPROVED`, its content hash matches, and the reviewer differs from the author.

- [ ] Add failing tests for exhaustive evidence classification, `UNKNOWN != ABSENT`, exact claim scoping, review-before-retrieval timestamps/stage ordinals, independent identities, and rejected/uncertain fail-closed behavior.
- [ ] Author minimal decision-specific evidence records from existing authoritative source packets; perform narrowly targeted research only when one load-bearing proposition is missing.
- [ ] Author feature maps before reading retrieval results.
- [ ] Run one fresh high-reasoning independent feature review over minimal evidence contexts and serialize per-map/per-feature reasons.
- [ ] Re-run the gate without revising rejected or uncertain maps.

### Task 3: Existing-seed baseline, bounded discovery, and cheap filters

**Files:**
- Modify: `scripts/qbank/fresh_holdout_18.py`
- Modify: `tests/test_fresh_holdout_18.py`
- Create: `research/qgen/holdout/fresh_holdout_18_existing_seed_baseline.json`
- Create: `research/qgen/holdout/fresh_holdout_18_bounded_discovery.json`
- Create: `research/qgen/holdout/fresh_holdout_18_seed_candidates.json`

**Interfaces:**
- Existing baseline uses historical approved packs plus approved development reusable packs only.
- Candidate rows include response class, granularity, positive anchor, inferiority discriminator, safety type, second-key analysis, evidence refs, and exact scope.

- [ ] Add failing tests proving baseline execution precedes new-seed authoring and rejected/uncertain/provisional rows cannot enter retrieval.
- [ ] Run actual existing-seed retrieval for approved feature maps and record retrieved, surviving, and contrast-ready counts.
- [ ] Run exactly one bounded discovery pass in the specified cache/pack/graph/TN/evidence/research order.
- [ ] Apply deterministic duplicate, response-class, granularity, stage, evidence-binding, obvious co-key, and backwards-anchor filters before semantic review.
- [ ] Serialize only complete candidate proposals and compute cheap-filter savings from raw counts.

### Task 4: Independent seed review and versioned wave packs

**Files:**
- Modify: `scripts/qbank/fresh_holdout_18.py`
- Modify: `tests/test_fresh_holdout_18.py`
- Create: `research/qgen/holdout/fresh_holdout_18_seed_independent_review.json`
- Create per completed wave: `research/qgen/holdout/fresh_holdout_18_wave_N_seed_pack.json`
- Create per completed wave: `research/qgen/holdout/fresh_holdout_18_wave_N_seed_pack.enrichment.json`
- Create per completed wave: `research/qgen/holdout/fresh_holdout_18_wave_N_seed_pack.stem_anchors.json`
- Create: `research/qgen/holdout/fresh_holdout_18_clinical_contrast_relations_v2.json`

**Interfaces:**
- Only review rows with verdict `APPROVED`, matching proposal hash/evidence hash, independent identities, approved relation, and positive non-backwards anchor are packable.

- [ ] Add failing tests for explicit verdict/reason completeness, hash freshness, reviewer independence, and non-approved retrieval impossibility.
- [ ] Run one fresh high-reasoning semantic review context over minimal per-candidate evidence.
- [ ] Build content-addressed wave packs containing approved rows only; preserve scope, review, evidence, relation, and anchor provenance.
- [ ] Replay retrieval with historical plus currently available approved holdout packs, require three safe competitors, run anchor/second-key/coherence checks, and freeze exactly one contrast set or fail closed.

### Task 5: Blueprint, centralized generation, and post-stem gates

**Files:**
- Modify: `scripts/qbank/fresh_holdout_18.py`
- Modify: `tests/test_fresh_holdout_18.py`
- Create: `research/qgen/holdout/fresh_holdout_18_contrast_sets.json`
- Create: `research/qgen/holdout/fresh_holdout_18_blueprints.json`
- Create: `research/qgen/holdout/fresh_holdout_18_lifecycle_trace.json`
- Create: `research/qgen/holdout/fresh_holdout_18_stems.json`
- Create: `research/qgen/holdout/fresh_holdout_18_blind_solve.json`
- Create: `research/qgen/holdout/fresh_holdout_18_post_stem_validation.json`
- Create: `research/qgen/holdout/fresh_holdout_18_items.json`

**Interfaces:**
- `execute_ready_opportunity(context, generator) -> dict` must delegate to existing `generation_lifecycle.execute_generation` immediately before the sole callback.
- Generator callback count is zero for every failed precondition and at most one otherwise.

- [ ] Add failing tests for lifecycle monotonicity, callback gating, no retries, immutable roster/feature maps/contrast sets, and wave hard stops.
- [ ] Build blueprints with existing frozen logic only.
- [ ] Execute one stem callback per passed central precondition and freeze its result.
- [ ] Run fresh blind solves using only stem and lead-in; fail closed on disagreement or material ambiguity.
- [ ] Require three `LIVE_BUT_INFERIOR` competitors against the frozen stem.
- [ ] Realize options/rationales with the existing implementation and no unsupported teaching additions.

### Task 6: Final independent medical review and wave accounting

**Files:**
- Modify: `scripts/qbank/fresh_holdout_18.py`
- Modify: `tests/test_fresh_holdout_18.py`
- Create: `research/qgen/holdout/fresh_holdout_18_final_medical_review.json`
- Create: `research/qgen/holdout/fresh_holdout_18_milestone.json`

**Interfaces:**
- Produces one terminal state and exactly one earliest failure cause for every frozen opportunity.
- Accepted items require zero defects across every safety dimension in the milestone contract.

- [ ] Add failing tests for mutually exclusive/exhaustive terminal states, failure-taxonomy sum, lifecycle inequalities, per-wave/per-discipline/per-difficulty sums, and accepted-item safety.
- [ ] Run one fresh high-reasoning final medical review context per completed wave, blind to yield and desired verdict.
- [ ] Compute wave metrics after each six-case wave and enforce only the declared hard-stop list.
- [ ] Complete all three waves unless a hard stop fires.

### Task 7: Economics, integrity, copyright, and resume state

**Files:**
- Modify: `scripts/qbank/fresh_holdout_18.py`
- Modify: `tests/test_fresh_holdout_18.py`
- Create: `reports/qgen_fresh_holdout_18_generalization.json`
- Create: `reports/qgen_fresh_holdout_18_test_results.json`
- Modify: `MEMORY.md`

**Interfaces:**
- Produces exact safe-yield, discipline, difficulty, seed-economics, review-cost, context-size, failure, systematic-defect, contrast-supply, integrity, and next-step fields required by the milestone contract.

- [ ] Recompute every metric from canonical artifacts; do not hand-copy counts.
- [ ] Verify roster and architecture hashes, stage ordering, no substitutions/retries/provisional admissions, and zero historical frozen-artifact changes.
- [ ] Run focused holdout/lifecycle/retrieval tests and the canonical copyright/leak audit.
- [ ] Run the full suite only if shared executable code changed, recording the known source-research failure separately from new failures.
- [ ] Run `git diff --check`, update only the QGEN resume block in `MEMORY.md` after verified completion, and verify `CLAUDE.md` unchanged and commits created equals zero.
