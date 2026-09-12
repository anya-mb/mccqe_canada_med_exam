# Representative Relation Gold V3 and Matcher Validation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a representative, double-blindly adjudicated real relation corpus and use it to calibrate, validate, and once-only heldout-test the opportunity matcher without generating production questions or reopening frozen QGEN layers.

**Architecture:** Extend `scripts/qbank/opportunity_relation_v4.py` with deterministic Gold V3 mining, blindness, assembly, support, partition, metric, and milestone functions while preserving all V2 and Matcher V3/V4 checkpoint artifacts byte-for-byte. Semantic labels are written only by isolated primary/secondary reviewers, a separate disagreement adjudicator, and later matcher-classifier sessions; deterministic Python owns all joins, hashes, gates, partitions, and reports.

**Tech Stack:** Python 3, pytest, canonical JSON/SHA-256, isolated Codex reviewers using GPT-5.6 Sol at high reasoning.

**Spec:** `/Users/annabeketova/.codex/attachments/60331c8d-0d24-4819-9181-10be11234e10/pasted-text.txt`

## Global Constraints

- Continue from exact current worktree and starting HEAD `01eff40984bee76418c7fab82a1ded9fbfa2d9e5`; preserve all pre-existing dirty changes.
- Do not commit, reset, clean, stash, checkout, discard WIP, modify historical frozen artifacts, or modify `CLAUDE.md`.
- Do not generate production questions, modify the validated question-generation pipeline, or redesign Independent Item Verification V1.
- Do not create canonical Registry V3 unless the matcher gate passes and normalized evaluation identifies a real generalizable need.
- Mining strata may propose pairs but may not assign or leak semantic labels, class targets, historical predictions, quotas, or matcher results into reviewer packets.
- Use at most two concurrent semantic agents, exclusively for the intentionally independent primary and secondary reviewers; use a third fresh adjudicator only after both finish.
- Real examples only count toward scientific support. Synthetic examples are permitted only in tests.
- Use TDD for shared code: every new behavior begins with a failing focused test, then minimal implementation, then focused green verification.
- Freeze and hash the blinded packet before review; freeze and hash the entire adjudicated gold corpus and its partitions before matcher tuning.
- Permit at most three mining/adjudication waves; stop fail-closed with exact deficits if real critical-class support remains insufficient.
- Run final heldout exactly once after the selected matcher contract is frozen; no post-heldout tuning.
- Run one canonical full suite at the final shared-code state and separate the known pre-existing source-research-coordinator failure from new failures.

---

### Task 1: Safe Resume and Gold V2 Failure Receipt

**Files:**
- Create: `reports/qgen_relation_gold_v2_failure_analysis.json`
- Test: `tests/test_opportunity_relation_v4.py`

**Interfaces:**
- Consumes: `relation_gold_v2.json`, its frozen review input, existing matcher milestone, current git state, and canonical hashes.
- Produces: `build_gold_v2_failure_analysis(root) -> dict[str, Any]` and a hashed immutable receipt with candidate count, relation counts, uncertain rate, absent classes, discipline/family distributions, and mining strategy.

- [ ] Add a failing test asserting the exact V2 hash, 81 candidates, `35/81` uncertain rate, absent-class list, six-discipline distribution, family distribution, and no mutation of the V2 artifact.
- [ ] Run `./.venv/bin/pytest -q tests/test_opportunity_relation_v4.py -k gold_v2_failure_analysis` and confirm the missing-function failure.
- [ ] Implement `build_gold_v2_failure_analysis` using only canonical V2 artifacts and `with_hash`.
- [ ] Re-run the focused test and write `reports/qgen_relation_gold_v2_failure_analysis.json` via a deterministic writer.

### Task 2: Deterministic Rare-Relation Mining and Blind Packet Freezing

**Files:**
- Modify: `scripts/qbank/opportunity_relation_v4.py`
- Modify: `tests/test_opportunity_relation_v4.py`
- Create: `research/qgen/opportunity_relation_v4/relation_gold_v3_wave_1_candidate_pool.json`
- Create: `research/qgen/opportunity_relation_v4/relation_gold_v3_wave_1_review_input.json`

**Interfaces:**
- Consumes: Registry V1/V2, normalized benchmark V2, preserved V1 lineage, duplicate stress inputs, source paths, variant groups, aliases, and existing real relation inputs.
- Produces: `mine_relation_gold_v3_candidates(root, wave, prior_pair_ids=())`, `build_relation_gold_v3_review_packet(pool)`, stable unordered semantic-pair signatures, structural strata metadata in the private pool, and a label-free public reviewer packet.

- [ ] Add failing tests for a 240–360-pair Wave 1 pool, all six disciplines, broad family coverage, stable IDs, real canonical endpoints, unordered-pair deduplication, and explicit private structural features.
- [ ] Add failing blindness tests proving the review packet omits `mining_stratum`, structural scores, desired labels, support targets, historical labels, matcher outputs, source-version labels, and quotas while retaining the Atomic Opportunity Contract plus minimal context.
- [ ] Add failing tests that hard-unrelated candidates remain within discipline and preferably family/topic neighborhood, and that duplicate/near-duplicate candidates originate from real aliases, source paths, lineage, or variant groups.
- [ ] Run the focused tests and confirm expected failures.
- [ ] Implement deterministic mining strata for possible equivalence, containment, variants, related-distinct, near-duplicate/duplicate, and hard-unrelated candidates without assigning semantic labels.
- [ ] Implement stable selection balancing discipline/family/stratum opportunity without quota-label leakage; cap Wave 1 at 300 pairs unless fewer genuine unique candidates exist.
- [ ] Re-run focused tests and freeze/hash the private Wave 1 pool and public Wave 1 reviewer packet.

### Task 3: Double-Blind Review, Disagreement Adjudication, and Gold Assembly

**Files:**
- Create per wave: `research/qgen/opportunity_relation_v4/relation_gold_v3_wave_<n>_primary_review.json`
- Create per wave: `research/qgen/opportunity_relation_v4/relation_gold_v3_wave_<n>_secondary_review.json`
- Create per wave: `research/qgen/opportunity_relation_v4/relation_gold_v3_wave_<n>_disagreement_input.json`
- Create per wave: `research/qgen/opportunity_relation_v4/relation_gold_v3_wave_<n>_adjudication.json`
- Modify: `scripts/qbank/opportunity_relation_v4.py`
- Modify: `tests/test_opportunity_relation_v4.py`

**Interfaces:**
- Consumes: each frozen public packet and isolated review files containing exactly one allowed relation plus concise justification per pair.
- Produces: `validate_relation_review`, `build_relation_disagreement_packet_v3`, `assemble_relation_gold_v3_waves`, reviewer agreement/confusion/per-class agreement/uncertain metrics, and only terminal agreed or adjudicated labels.

- [ ] Add failing validator tests for exact one-time coverage, packet-hash binding, independent reviewer IDs, allowed labels, non-empty concise reasons, and adjudication containing exactly every disagreement and no agreement.
- [ ] Add failing tests for reviewer-reviewer confusion, per-class agreement, uncertain rate, and fail-closed missing adjudication.
- [ ] Run focused tests and confirm expected failures.
- [ ] Implement the V3 validators, disagreement packet including both reviewer verdicts/reasons but no matcher prediction, and multi-wave gold assembly with duplicate-pair rejection.
- [ ] Dispatch exactly two fresh isolated GPT-5.6 Sol/high reviewers concurrently against the same packet, with each prohibited from reading peer outputs or any prior gold/matcher artifact.
- [ ] After both finish, deterministically build the disagreement packet and dispatch one fresh GPT-5.6 Sol/high adjudicator for only those pairs.
- [ ] Assemble Wave 1, compute support deficits, and repeat bounded Waves 2–3 only when required by the support gate; do not reveal deficit labels to semantic reviewers.

### Task 4: Gold V3 Support Gate and Leakage-Safe Partitions

**Files:**
- Create: `research/qgen/opportunity_relation_v4/relation_gold_v3.json`
- Create: `research/qgen/opportunity_relation_v4/relation_gold_v3_uncertain.json`
- Create: `research/qgen/opportunity_relation_v4/relation_gold_v3_frozen_partitions.json`
- Modify: `scripts/qbank/opportunity_relation_v4.py`
- Modify: `tests/test_opportunity_relation_v4.py`

**Interfaces:**
- Consumes: terminal multi-wave adjudications.
- Produces: `evaluate_relation_class_support`, `freeze_relation_gold_v3_partitions`, class floors `{EQUIVALENT:12, BROADER:12, NARROWER:8, VARIANT:12, RELATED:20, UNRELATED:12}`, and heldout floors `{4,4,3,4,6,4}` for those classes.

- [ ] Add failing tests for exact class floors, separate UNCERTAIN preservation, no pair overlap, no study-unit/near-equivalent sibling leakage where avoidable, and required heldout variant support.
- [ ] Run focused tests and confirm expected failures.
- [ ] Implement support assessment and deterministic group-stratified CALIBRATION/VALIDATION/FINAL_HELDOUT assignment.
- [ ] If support fails after Wave 3, write the corpus, exact deficit report, and fail-closed status, then skip matcher execution.
- [ ] If support passes, freeze/hash the terminal gold corpus, uncertain corpus, and partitions before any matcher prediction work.

### Task 5: Matcher Calibration, Validation, and Once-Only Heldout

**Files:**
- Preserve: `research/qgen/opportunity_relation_v4/matcher_v4_contract.json`
- Create: `research/qgen/opportunity_relation_v4/matcher_v4_calibration_predictions.json`
- Create: `research/qgen/opportunity_relation_v4/matcher_v4_approach_comparison.json`
- Create: `research/qgen/opportunity_relation_v4/matcher_v4_validation_predictions.json`
- Create conditionally: `research/qgen/opportunity_relation_v4/matcher_v4_calibrated_contract.json` or Matcher V5 contract/artifacts if architecture changes materially
- Create: `research/qgen/opportunity_relation_v4/matcher_selected_frozen_contract.json`
- Create: `research/qgen/opportunity_relation_v4/matcher_final_heldout_predictions.json`
- Create: `reports/qgen_relation_matcher_validation.json`
- Modify: `scripts/qbank/opportunity_relation_v4.py`
- Modify: `tests/test_opportunity_relation_v4.py`

**Interfaces:**
- Consumes: frozen Gold V3 partitions; calibration labels first, validation labels second, heldout labels only after frozen predictions.
- Produces: deterministic, semantic, and hybrid calibration metrics; selected contract; validation and heldout macro/per-class precision/recall/F1 and confusion; `evaluate_matcher_gate`; append-only monotonicity evidence.

- [ ] Add failing tests that prediction packets contain endpoint content but no gold label, heldout labels are not read before prediction freeze, all partition predictions cover exactly once, and architecture selection contains no ID-specific rule.
- [ ] Add failing gate tests including `UNRELATED` as a critical class, supported-class F1 floor `0.70`, macro-F1 floor `0.80`, and explicit `INSUFFICIENT_CLASS_SUPPORT`.
- [ ] Run focused tests and confirm expected failures.
- [ ] Implement deterministic structural baseline features/classifier and prediction-packet builders; use isolated semantic classification for the semantic and hybrid approaches.
- [ ] Evaluate all three architectures on CALIBRATION only, then validate the selected architecture and make only pre-heldout architecture-level corrections.
- [ ] Freeze the selected matcher version/hash and prediction contract before dispatching the FINAL_HELDOUT classifier exactly once.
- [ ] Score heldout deterministically, run monotonicity tests, and classify `MATCHER_VALIDATED`, `MATCHER_PROMISING`, `MATCHER_FAILED`, or `INSUFFICIENT_GOLD_SUPPORT`.

### Task 6: Conditional Normalized Evaluation and Registry Decision

**Files:**
- Create conditionally: `reports/qgen_v1_v2_normalized_matcher_evaluation.json`
- Do not modify frozen Registry V1/V2; do not create Registry V3 unless both gates authorize it.

**Interfaces:**
- Consumes: the exact validated frozen matcher, normalized benchmark V2, Registry V1, and Registry V2.
- Produces conditionally: atomic-equivalent precision/recall, decision coverage, atomization deficit, variant capture, over-split rate, duplicate rate, and V2 monotonicity relative to preserved V1 relations.

- [ ] Add failing authorization tests proving normalized evaluation and Registry V3 construction cannot run unless `MATCHER_ASSESSMENT == MATCHER_VALIDATED`.
- [ ] If unauthorized, emit `V1_NORMALIZED_METRICS=NOT_AUTHORIZED`, `V2_NORMALIZED_METRICS=NOT_AUTHORIZED`, and the correct no-Registry status.
- [ ] If authorized, evaluate V1 and V2 with the same matcher/benchmark/contract and create Registry V3 only when a generalizable enumeration gap is proven without ID whitelists or count targeting.

### Task 7: Independent Verifier Integrity and External Dry-Run Manifest

**Files:**
- Create: `research/qgen/independent_verification_v1/external_verifier_dry_run_manifest_v1.json`
- Modify only for proven nonsemantic defect: `scripts/qbank/independent_item_verification.py`, `tests/test_independent_item_verification.py`

**Interfaces:**
- Consumes: six existing non-production validation packages, frozen external prompt, schemas, ledger, and seven mutation results.
- Produces: a hashed manifest listing six package IDs/hashes and separate-session launch instructions without self-verifying any item.

- [ ] Add a failing manifest test asserting exactly six unique non-production packages, stable package hashes, stable prompt/schema/ledger hashes, append-only/hash-valid ledger, and all seven mutation detections true.
- [ ] Run the focused test and confirm the manifest builder is absent.
- [ ] Implement the deterministic manifest builder without changing verifier semantics or emitting `VERIFIED_ACCEPT`.
- [ ] Re-run verifier focused tests and freeze/hash the manifest.

### Task 8: Milestone, Historical Safety, Copyright, Full Verification, and Resume State

**Files:**
- Create: `reports/qgen_representative_relation_gold_v3_matcher_validation_milestone.json`
- Create: `reports/qgen_representative_relation_gold_v3_matcher_validation_copyright_audit.json`
- Modify: `MEMORY.md` only within `QGEN_ARCHITECTURE_RESUME`
- Test: `tests/test_opportunity_relation_v4.py`, `tests/test_independent_item_verification.py`, existing historical-safety suites

**Interfaces:**
- Consumes: every new hash, gate, metric, verifier receipt, historical-frozen hash receipt, git state, and copyright scan.
- Produces: every exact final-return field from the supplied spec, canonical milestone status, next bottleneck, and next step.

- [ ] Add failing milestone tests for all required return fields, zero production questions, zero commits, zero historical modifications, preserved hashes, and hard-stop status mapping.
- [ ] Implement deterministic milestone assembly and copyright input inventory.
- [ ] Run focused relation/verifier/historical AOM/lifecycle/exposure/candidate/evidence tests and record exact pass/fail counts.
- [ ] Run the Toronto Notes overlap/copyright audit over mining, review, gold, matcher, and manifest artifacts; manually classify any machine hit before recording PASS.
- [ ] Run `git diff --check`, frozen-artifact hash comparison, and verify `CLAUDE.md` unchanged.
- [ ] Run one canonical full suite at the final shared-code state and classify the known source-research-coordinator failure separately; require `NEW_TEST_FAILURES=0`.
- [ ] Update only the changing `QGEN_ARCHITECTURE_RESUME` block in `MEMORY.md` from canonical outputs, then rerun `git diff --check` and focused resume checks.
- [ ] Reconcile the supplied final-return template line by line and report only that template, with no completion claim unsupported by fresh command output.
