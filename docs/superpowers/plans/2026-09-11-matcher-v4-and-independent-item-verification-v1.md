# Matcher V4 and Independent Item Verification V1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the failed Matcher V3 generalization baseline with a genuinely independent, representative relation-class calibration and held-out evaluation, while implementing the separate Independent Production Item Verification V1 safety contract without generating production questions.

**Architecture:** Preserve Matcher V3 and every frozen historical artifact byte-for-byte. Add a separate V4 relation-data and evaluation module: deterministic mining and candidate pre-filtering feed blinded external semantic adjudication, while deterministic code validates review independence, freezes calibration/validation/final-heldout partitions before matcher selection, computes classwise metrics, and enforces the one-shot final gate. In parallel, add a standalone item-verification module and schemas that build immutable review packages from existing development/clean-validation items, enforce staged blind-solve then evidence audit, test seeded synthetic mutations, and maintain a content-addressed verification ledger.

**Tech Stack:** Python 3, pytest, jsonschema, canonical JSON/SHA-256 artifacts, isolated Codex semantic-review sessions.

**Spec:** `/Users/annabeketova/.codex/attachments/095fcdb7-ae7a-4240-acb4-445d00b4c455/pasted-text.txt`

## Global Constraints

- Continue from exact HEAD `01eff40984bee76418c7fab82a1ded9fbfa2d9e5`; preserve all pre-existing dirty-worktree changes.
- No commits, reset, clean, stash, destructive checkout, or modification of frozen historical artifacts.
- Do not generate production-bank questions.
- Do not create canonical Registry V3 unless Matcher V4 passes genuinely independent final-heldout validation.
- Preserve failed Matcher V3 implementation, gold review, split, `2/86` result, and confusion matrix as `MATCHER_V3_FAILED_GENERALIZATION_BASELINE`.
- Use deterministic Python for mining, joins, hashing, splitting, reconciliation, metrics, schemas, and gates; reserve semantic labels for isolated blinded reviewers.
- Final relation partitions must be frozen before Matcher V4 development, and final-heldout outcomes must remain unavailable until the selected matcher contract is frozen.
- Fail closed on unresolved relation disagreements, insufficient class support, source conflicts, incomplete staged reviews, changed verified content, or absent provenance.
- Synthetic mutations may test the verifier but must never modify canonical validation items.
- New artifacts must pass the Toronto Notes copyright scan; no substantial source prose may be reproduced.
- Run focused tests throughout and one full canonical suite only after the final executable-code state; report the known unrelated coordinator failure separately.
- Do not modify `CLAUDE.md`.

---

### Task 1: Freeze Baseline and Mine Representative Relation Candidates

**Files:**
- Create: `scripts/qbank/opportunity_relation_v4.py`
- Create: `tests/test_opportunity_relation_v4.py`
- Create: `research/qgen/opportunity_relation_v4/matcher_v3_failed_generalization_baseline.json`
- Create: `research/qgen/opportunity_relation_v4/relation_gold_v2_review_input.json`

**Interfaces:**
- Consumes: Atomic Opportunity Contract V1, normalized benchmark V2, Registry V1/V2, existing independently reviewed relation evidence.
- Produces: `build_failed_v3_baseline(root)`, `mine_relation_review_candidates(root)`, canonical review input with real rows, provenance, curriculum context, and no matcher prediction or desired balance.

- [ ] Write failing tests proving the baseline reproduces hashes, 86/2 metrics, and confusion without modifying V3 artifacts.
- [ ] Run the focused tests and confirm failure because the V4 module is absent.
- [ ] Implement the baseline receipt and deterministic real-pair miner with discipline/family coverage, stable IDs, provenance, and deduplication.
- [ ] Add tests that every pair is drawn from canonical data, all six disciplines are represented, reviewer inputs omit prohibited matcher/version/outcome fields, and rare classes are reported rather than fabricated.
- [ ] Run focused tests and write the two hashed artifacts only after they pass.

### Task 2: Blinded Double Adjudication and Frozen Three-Way Split

**Files:**
- Create: `research/qgen/opportunity_relation_v4/relation_gold_v2_primary_review.json`
- Create: `research/qgen/opportunity_relation_v4/relation_gold_v2_secondary_review.json`
- Create: `research/qgen/opportunity_relation_v4/relation_gold_v2_disagreement_adjudication.json`
- Create: `research/qgen/opportunity_relation_v4/relation_gold_v2.json`
- Modify: `scripts/qbank/opportunity_relation_v4.py`
- Modify: `tests/test_opportunity_relation_v4.py`

**Interfaces:**
- Consumes: blinded review input from Task 1 and isolated reviewer outputs containing exactly one allowed label plus concise justification.
- Produces: `assemble_relation_gold_v2(...)` and `freeze_relation_partitions(...)`, including agreement, disagreement/adjudication counts, UNCERTAIN failures, relation/discipline/family coverage, and immutable calibration/validation/final-heldout membership.

- [ ] Dispatch a fresh isolated primary reviewer that sees only the contract, pair endpoints, and curriculum context.
- [ ] Dispatch a different isolated reviewer for EQUIVALENT, BROADER, NARROWER, VARIANT, and NEAR_DUPLICATE candidates without revealing primary labels.
- [ ] Send only genuine disagreements to a third fresh adjudication pass; unresolved cases become `UNCERTAIN`.
- [ ] Write failing validator tests for reviewer independence, exact input coverage, controlled labels, disagreement routing, and partition leakage.
- [ ] Implement deterministic assembly and a seeded stable stratifier by relation, discipline, and family where possible.
- [ ] Freeze and hash all three partitions before any matcher development; verify variant support independently in the final-heldout set or report insufficient support.

### Task 3: Compare Three Approaches and Freeze Matcher V4

**Files:**
- Create: `docs/qgen/OPPORTUNITY_RELATION_CLASSIFIER_V4_PROMPT.md`
- Create: `research/qgen/opportunity_relation_v4/matcher_v4_approach_comparison.json`
- Create: `research/qgen/opportunity_relation_v4/matcher_v4_contract.json`
- Create: `research/qgen/opportunity_relation_v4/matcher_v4_validation_predictions.json`
- Create: `research/qgen/opportunity_relation_v4/matcher_v4_final_heldout_predictions.json`
- Create: `reports/qgen_matcher_v4_relation_validation.json`
- Modify: `scripts/qbank/opportunity_relation_v4.py`
- Modify: `tests/test_opportunity_relation_v4.py`

**Interfaces:**
- Consumes: frozen partitions; only calibration labels during approach comparison, then validation labels for selection, never final-heldout labels before contract freeze.
- Produces: deterministic/lexical baseline, constrained-semantic prompt contract, recommended hybrid prefilter-plus-semantic architecture, `compute_multiclass_metrics`, monotonic many-to-many graph validation, and one-shot gate report.

- [ ] Write failing tests for macro/per-class precision/recall/F1, zero-division/insufficient-support handling, confusion matrices, many-to-many edges, and append-only monotonicity.
- [ ] Implement deterministic metrics and structural/lexical baseline evaluation on calibration only.
- [ ] Run a blinded semantic calibration classification and record it separately from gold labels.
- [ ] Evaluate deterministic, semantic, and hybrid approaches on calibration; select and freeze the simplest supported contract without ID-specific rules.
- [ ] Run the frozen contract on validation, make any permitted architecture-level correction using calibration/validation only, then freeze the final Matcher V4 hash.
- [ ] Dispatch final-heldout classification once to a fresh isolated session and only then unblind deterministic scoring.
- [ ] Gate on macro-F1 and critical-class F1 where support is sufficient; otherwise report `INSUFFICIENT_CLASS_SUPPORT` and keep production closed.
- [ ] If the gate passes, compute normalized Registry V1/V2 metrics with the exact frozen matcher; otherwise leave them `NOT_AUTHORIZED` and do not create Registry V3.

### Task 4: Production Item Verification Package and Two-Stage Contract

**Files:**
- Create: `schemas/production-item-verification-package-v1.schema.json`
- Create: `schemas/production-item-blind-solve-v1.schema.json`
- Create: `schemas/production-item-evidence-audit-v1.schema.json`
- Create: `scripts/qbank/independent_item_verification.py`
- Create: `tests/test_independent_item_verification.py`
- Create: `research/qgen/independent_verification_v1/validation_item_packages.json`

**Interfaces:**
- Consumes: a bounded sample of existing accepted development/clean-validation items, Question Seeds, evidence registries, Toronto Notes refs, and Canadian source refs.
- Produces: `build_verification_package`, `blind_projection`, `validate_blind_solve`, `validate_evidence_audit`, content hashes, and a package sample explicitly marked non-production.

- [ ] Write schema and behavior tests first for all required package fields, no private reasoning, per-distractor rationale, conditional next action, source versions/dates, and hashes.
- [ ] Verify tests fail before implementation.
- [ ] Implement canonical package construction and strict blind projection that hides key, rationale, evidence, and author confidence.
- [ ] Implement stage ordering so Stage 2 cannot validate without a frozen Stage-1 verdict hash.
- [ ] Implement claim-by-claim statuses, Toronto Notes statuses, Canadian-guidance/conflict statuses, hallucination checklist, answer-validity rules, distractor rules, rationale-quality rules, and controlled final verdicts.
- [ ] Build packages from a discipline-spanning bounded sample without promoting any item to production.

### Task 5: Mutation Detection, Disagreement, Ledger, and Immutability

**Files:**
- Create: `schemas/production-item-verification-ledger-v1.schema.json`
- Create: `research/qgen/independent_verification_v1/synthetic_mutation_cases.json`
- Create: `research/qgen/independent_verification_v1/verification_mutation_results.json`
- Create: `research/qgen/independent_verification_v1/production_item_verification_ledger_v1.json`
- Create: `docs/qgen/INDEPENDENT_PRODUCTION_ITEM_VERIFIER_PROMPT.md`
- Modify: `scripts/qbank/independent_item_verification.py`
- Modify: `tests/test_independent_item_verification.py`

**Interfaces:**
- Consumes: Task 4 packages and immutable synthetic copies.
- Produces: deterministic mutation detector coverage, disagreement packet/adjudication contract, ledger validator, and `requires_reverification(previous_hash, current_package)`.

- [ ] Write failing tests for wrong key, second key, unsupported claim, false citation, outdated guidance, Toronto Notes contradiction, and Canadian-guideline contradiction.
- [ ] Implement only the validation needed to detect each seeded mutation and prove the canonical source item remains unchanged.
- [ ] Add tests and implementation for compact disagreement packets and controlled third-session outcomes.
- [ ] Add ledger tests for package/session/stage/adjudication hashes, source versions, permitted final states, and immutable verified hashes.
- [ ] Write the reusable external-session prompt with strict stage separation and actual-source-inspection requirements.
- [ ] Run focused tests and generate hashed mutation, prompt, and ledger artifacts.

### Task 6: Milestone Gate, Safety Regressions, Copyright, and Resume State

**Files:**
- Create: `reports/qgen_matcher_v4_and_independent_item_verification_v1.json`
- Create: `reports/qgen_matcher_v4_and_independent_item_verification_v1_copyright_audit.json`
- Modify: `scripts/qbank/opportunity_relation_v4.py`
- Modify: `scripts/qbank/independent_item_verification.py`
- Modify: `tests/test_opportunity_relation_v4.py`
- Modify: `tests/test_independent_item_verification.py`
- Modify: `MEMORY.md`

**Interfaces:**
- Consumes: all prior task artifacts and existing historical safety/AOM/lifecycle validators.
- Produces: exact final-return fields, frozen-artifact integrity receipt, readiness decision, dominant bottleneck, and next step.

- [ ] Write failing milestone tests for every required final field, hard-stop behavior, zero production items, zero commits, and zero historical frozen-artifact modifications.
- [ ] Implement deterministic milestone assembly and provenance/hash reconciliation.
- [ ] Run historical safety regression, AOM development control, lifecycle invariant, and focused V4/verifier tests.
- [ ] Run the canonical Toronto Notes overlap audit over every new content artifact and prompt.
- [ ] Run `git diff --check`; compare all frozen-file hashes with the baseline receipt; verify `CLAUDE.md` unchanged.
- [ ] Run one full canonical suite at the final executable-code state and classify the known coordinator failure separately from new failures.
- [ ] Update only the changing QGEN resume section in `MEMORY.md` from canonical artifacts and rerun `git diff --check` plus focused resume validation.
- [ ] Re-read the supplied milestone line by line and reconcile every required return field before reporting completion or a fail-closed blocker.
