# Generalized Pre-Holdout Readiness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and independently review a broad decision-evidence-ready and feature-expressible development pool, then create an append-only V6 feature snapshot and an untouched future-holdout eligibility inventory without selecting a holdout or running any downstream question-generation stage.

**Architecture:** A deterministic Python module owns reconciliation, historical exclusions, balanced curriculum selection, artifact validation, V6 snapshot assembly, regression checks, metrics, and future eligibility bookkeeping. Clinical decision/evidence and feature judgments live in bounded, hash-pinned JSON artifacts and are admitted only through explicit independent-review records. The existing V5 snapshot and all historical holdout/development artifacts remain immutable.

**Tech Stack:** Python 3 via `.venv/bin/python`, pytest, canonical JSON artifacts, SHA-256 content/file hashing.

**Spec:** `/Users/annabeketova/.codex/attachments/d295120a-b2d5-45aa-96ac-9c28d214614a/pasted-text.txt`

## Global Constraints

- Work from HEAD `01eff40984bee76418c7fab82a1ded9fbfa2d9e5` on the current dirty worktree.
- Do not reset, clean, stash, checkout, discard WIP, or commit.
- Preserve V5 and every historical/frozen artifact byte-identically.
- Exclude every materially used architecture-development opportunity and all 18 diagnostic units.
- Select 15 units per discipline where available, using only curriculum priority, MCC relevance, diversity, source availability, and canonical identifiers.
- Never use seed, contrast, retrieval-yield, distractor, or generation outcomes in selection or readiness decisions.
- Treat packet readiness and decision-evidence readiness as separate states; partial, missing, uncertain, misaligned, and out-of-scope evidence fail closed.
- Only independently approved, hash-matched evidence and feature rows can enter the ready pool or V6.
- V6 is an append-only child of V5 and contains no distractor anchors.
- Do not run seed discovery, contrast retrieval, blueprinting, stem generation, blind solve, or final question review.
- Do not modify `CLAUDE.md`.

---

### Task 1: Deterministic readiness contracts and exclusion/selection layer

**Files:**
- Create: `scripts/qbank/pre_holdout_readiness.py`
- Create: `tests/test_pre_holdout_readiness.py`
- Create: `research/qgen/readiness/development_exclusion_inventory.json`
- Create: `research/qgen/readiness/development_90_selection.json`

**Interfaces:**
- Consumes: `eligible_fresh_study_units.json`, `next_fresh_holdout_eligibility_inventory.json`, historical exclusion artifacts, diagnostic-18 roster, master scope crosswalk, final allocation, and source-packet plan/populations.
- Produces: `build_development_exclusions(root) -> dict`, `select_development_units(root, exclusions) -> dict`, `validate_development_selection(root, artifact) -> dict`.

- [ ] Write tests proving exclusions cover historical sets and diagnostic-18 while selection produces 15 distinct units per discipline without forbidden outcome fields.
- [ ] Run focused tests and confirm RED because the module does not exist.
- [ ] Implement deterministic exclusion joins, taxonomy-aware diversity ordering, and exact content hashes.
- [ ] Run focused tests and confirm GREEN.

### Task 2: Decision evidence audit and independent-review gate

**Files:**
- Modify: `scripts/qbank/pre_holdout_readiness.py`
- Modify: `tests/test_pre_holdout_readiness.py`
- Create: `research/qgen/readiness/development_decision_evidence_audit.json`
- Create: `research/qgen/readiness/development_targeted_evidence.json`
- Create: `research/qgen/readiness/development_evidence_independent_review.json`

**Interfaces:**
- Consumes: selected units, canonical competencies, verified packet claims, foundational claims, source refs, and targeted evidence rows.
- Produces: `validate_decision_audit(selection, audit)`, `validate_evidence_reviews(audit, reviews, catalog)`, and exact evidence-economics counts.

- [ ] Write tests proving exhaustive audit coverage, load-bearing claim requirements, packet-ready false positives, independent author/reviewer identities, and stale-review rejection.
- [ ] Run focused tests and confirm RED for missing behavior.
- [ ] Implement the minimal deterministic validation and rollup logic.
- [ ] Build bounded decision rows from canonical competencies and exact existing claims; add only genuinely necessary targeted evidence with authoritative citations.
- [ ] Perform a separate-context clinical entailment review of changed/new decision-support rows and serialize hash-pinned verdicts.
- [ ] Run focused tests and confirm GREEN; require at least eight approved decisions per discipline or stop with the true shortage.

### Task 3: Feature normalization, proposal review, and V6 snapshot

**Files:**
- Modify: `scripts/qbank/pre_holdout_readiness.py`
- Modify: `tests/test_pre_holdout_readiness.py`
- Create: `research/qgen/readiness/development_feature_audit.json`
- Create: `research/qgen/readiness/development_feature_proposals.json`
- Create: `research/qgen/readiness/development_feature_independent_review.json`
- Create: `research/qgen/readiness/development_feature_maps_v6.json`
- Create: `research/qgen/onboarding/feature_anchor_snapshot_v6.json`

**Interfaces:**
- Consumes: independently approved decision evidence and immutable `FEATURE_ANCHOR_SNAPSHOT_V5`.
- Produces: normalization classifications, approved feature/unit-binding rows, `build_snapshot_v6(...) -> dict`, and `validate_feature_maps(...) -> dict`.

- [ ] Write tests proving V5 immutability, exact/normalized reuse, distinct-concept preservation, fail-closed ambiguous/unsupported rows, append-only V6 construction, and absence of new anchors.
- [ ] Run focused tests and confirm RED for missing behavior.
- [ ] Implement the minimal normalization/proposal/map validation and V6 build orchestration by reusing `vocabulary_onboarding`.
- [ ] Author minimal decision-only feature proposals and bindings with evidence refs.
- [ ] Perform a separate-context clinical feature identity/state/role review and serialize hash-pinned verdicts.
- [ ] Build V6 from approved additions only, validate every approved decision map, and run focused tests to GREEN.

### Task 4: Regression, economics, future eligibility, and milestone report

**Files:**
- Modify: `scripts/qbank/pre_holdout_readiness.py`
- Modify: `tests/test_pre_holdout_readiness.py`
- Create: `research/qgen/readiness/future_holdout_eligibility_inventory.json`
- Create: `research/qgen/readiness/pre_holdout_readiness_milestone.json`
- Create: `reports/qgen_pre_holdout_readiness_milestone.json`
- Create: `reports/qgen_pre_holdout_readiness_test_results.json`

**Interfaces:**
- Consumes: all readiness artifacts, V5/V6, frozen historical pins, lifecycle regressions, and the full fresh inventory.
- Produces: `build_future_eligibility_inventory(...)`, `build_milestone_report(...)`, readiness gate, feature reuse/growth classification, evidence economics, and exact final counts.

- [ ] Write tests proving diagnostic-18 remains frozen/reclassified but unreplayed, future inventory excludes development units, no next holdout is selected, downstream counts remain zero, and readiness gates fail closed.
- [ ] Run focused tests and confirm RED for missing behavior.
- [ ] Implement deterministic regression, economics, eligibility, and reporting logic.
- [ ] Generate the canonical milestone and mirrored report; verify internal hashes and arithmetic.
- [ ] Run focused tests to GREEN.

### Task 5: Final verification and resume-state update

**Files:**
- Modify: `MEMORY.md` only if verified canonical state materially changes.

**Interfaces:**
- Consumes: final canonical artifacts and validator/test output.
- Produces: reconciled QGEN architecture resume state and final milestone return values.

- [ ] Verify all historical file hashes against recorded pins and confirm zero frozen-artifact modifications.
- [ ] Run the focused readiness/lifecycle/vocabulary tests and record exact pass/fail counts.
- [ ] Run the canonical copyright/leak audit over new artifacts.
- [ ] If shared executable code changed, run the full canonical suite once at final code state and separate the known pre-existing source-research coordinator failure.
- [ ] Update only the changing `QGEN_ARCHITECTURE_RESUME` section of `MEMORY.md` from verified canonical results.
- [ ] Run `git diff --check`, re-run any validator affected by the memory edit, and confirm `CLAUDE.md` is unchanged.
- [ ] Return only the user-specified milestone template and create no commit.
