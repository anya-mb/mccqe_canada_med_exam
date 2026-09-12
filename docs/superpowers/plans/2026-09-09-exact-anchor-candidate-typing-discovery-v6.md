# Exact-Anchor Candidate Typing and Discovery V6 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Diagnose the consumed Transfer-18 Discovery-V5 zero-supply result, establish independently reviewed exact-anchor reference candidates, implement a reusable Candidate Role Registry V1 and the smallest justified Discovery V6 repair, and measure diagnostic retrieval and bundle density without consuming another clean cohort.

**Architecture:** Preserve every historical Transfer-18 and V5 artifact byte-for-byte. Add one deterministic V6 module that reconstructs the V5 funnel, normalizes reusable response roles, validates role registry/catalogue inputs, and retrieves from general metadata; keep clinical reference candidates, reviews, feature profiles, and evidence as explicit versioned data. A single runner assembles derived diagnostic artifacts, hashes, benchmark metrics, safety/copyright results, and the final milestone report.

**Tech Stack:** Python 3, pytest, canonical JSON with `canonical_content_sha256`, existing `contrast_supply_v4`/`contrast_supply_v5` primitives, deterministic repository validators.

**Spec:** `/Users/annabeketova/.codex/attachments/4fb158a2-945b-46d2-9825-a1aa4ffd8740/pasted-text.txt`

## Global Constraints

- Starting HEAD is `01eff40984bee76418c7fab82a1ded9fbfa2d9e5`; preserve the exact dirty worktree.
- No commit, reset, clean, stash, destructive checkout, fresh holdout, or new clean Transfer run.
- Historical Transfer-18, Catalogue V2, Signature V2, Discovery V5, and Bundle Cache V1 artifacts are immutable.
- Transfer-18 is consumed development diagnostic data and can never validate V6 as an unseen cohort.
- Use deterministic processing for all joins, counts, gates, rankings, hashes, and validation.
- Semantic review is restricted to reference candidates and genuinely ambiguous role mappings, in batches of at most six and with concurrency one.
- Reference anchor IDs and option mappings must never appear in production retrieval logic.
- Shared-code changes use red-green TDD; run the canonical full suite once at final shared-code state.

---

### Task 1: Freeze status and reconstruct the exact V5 funnel

**Files:**
- Create: `research/qgen/contrast_supply/transfer18_development_status_v1.json`
- Create: `scripts/qbank/contrast_supply_v6.py`
- Create: `tests/test_contrast_supply_v6.py`
- Create: `research/qgen/contrast_supply/transfer18_v5_funnel_accounting_v1.json`
- Create: `research/qgen/contrast_supply/transfer18_response_class_coverage_v1.json`
- Create: `research/qgen/contrast_supply/catalogue_v2_response_role_inventory_v1.json`
- Create: `research/qgen/contrast_supply/response_class_vocabulary_forensics_v1.json`
- Create: `research/qgen/contrast_supply/transfer18_v5_filter_ablation_v1.json`

**Interfaces:**
- Consumes: frozen Catalogue V2, Transfer-18 prerequisites, Signature V2 registry, and Discovery V5 wave.
- Produces: `classify_v5_terminal_outcome(candidate, opportunity, signatures) -> str`, `build_v5_funnel(...) -> dict`, `build_role_inventory(catalogue) -> dict`, and `build_filter_ablation(...) -> dict`.

- [ ] Write failing tests asserting one terminal earliest outcome for each catalogue-row/anchor pair, exact 33,012 reconciliation, the frozen V5 reason totals, stable gate order, per-anchor stage monotonicity, and explicit response-vocabulary mapping.
- [ ] Run `pytest -q tests/test_contrast_supply_v6.py` and confirm the new imports/tests fail.
- [ ] Implement the minimal deterministic classifiers and validators without changing V5.
- [ ] Run `pytest -q tests/test_contrast_supply_v6.py` and confirm Task 1 tests pass.
- [ ] Materialize the five diagnostic artifacts and verify their internal hashes and 1,834-row inventory totals.

### Task 2: Establish and independently review exact-anchor reference candidates

**Files:**
- Create: `research/qgen/contrast_supply/anchor_reference_candidate_set_v1.json`
- Create: `research/qgen/contrast_supply/anchor_reference_candidate_review_v1.json`
- Create: `research/qgen/contrast_supply/anchor_reference_feature_profiles_v1.json`
- Create: `research/qgen/contrast_supply/anchor_reference_pairwise_review_v1.json`
- Create: `research/qgen/contrast_supply/anchor_reference_catalogue_coverage_v1.json`
- Create: `research/qgen/contrast_supply/anchor_reference_v5_failure_attribution_v1.json`

**Interfaces:**
- Consumes: 18 prerequisite rows and existing evidence packets/approved relations only; V5 rankings stay hidden during candidate proposal.
- Produces: 3-8 clinically justified same-response-class options when safe, review verdicts (`APPROVED_REFERENCE`, `REJECTED`, `UNCERTAIN`), evidence-linked feature profiles, pairwise admission, catalogue coverage, and earliest V5 loss.

- [ ] Author candidate proposals serially in batches no larger than six, keeping disease differentials separate from option candidates for non-diagnosis decisions.
- [ ] Perform a separate independent clinical verification pass over every proposal and fail closed on `UNCERTAIN`.
- [ ] Record 3-8 supported features, correctness context, preferred context, next step, second-key risk, and population limits for every approved candidate where clinically meaningful.
- [ ] Reject aliases, near-synonyms, nested/co-key alternatives, and duplicate actions in pairwise review.
- [ ] Deterministically join approved candidates to Catalogue V2 by canonical identity/alias and attribute every approved candidate to exactly one V5 loss state.
- [ ] Validate proposal/review/count reconciliation and calculate the reference-set content hash.

### Task 3: Build and approve Candidate Role Registry V1

**Files:**
- Create: `research/qgen/contrast_supply/candidate_role_registry_v1.json`
- Create: `research/qgen/contrast_supply/candidate_role_registry_v1_review.json`
- Modify: `scripts/qbank/contrast_supply_v6.py`
- Modify: `tests/test_contrast_supply_v6.py`
- Conditionally create: `research/qgen/contrast_supply/global_candidate_concept_catalogue_v3.json`

**Interfaces:**
- Consumes: measured role inventory, vocabulary forensics, approved references, structural metadata, and reviewed provenance.
- Produces: `normalize_response_role(value) -> str`, `validate_candidate_role_registry(registry) -> dict`, `candidate_roles(candidate_id, registry) -> frozenset[str]`, and optional immutable-child Catalogue V3.

- [ ] Add RED tests for diagnosis, investigation, management, ethical/legal, historical controls, wrong-role rejection, explicit multi-role behavior, untyped fail-closed behavior, alias normalization, and absence of opportunity-specific whitelists.
- [ ] Run the focused test file and verify RED failures.
- [ ] Implement the smallest controlled role vocabulary and provenance-bearing registry justified by Task 2 metrics.
- [ ] Review the controlled vocabulary, derivation rules, representative positives, and negatives independently; require `APPROVED` before V6 work.
- [ ] If material approved-reference absence is proven, create Catalogue V3 as an immutable child with canonical identity, source provenance, safe label, and role metadata; otherwise record that V3 was not created.
- [ ] Run focused tests and the canonical copyright audit over the role and optional catalogue artifacts.

### Task 4: Implement Discovery V6 and benchmark reference retrieval

**Files:**
- Modify: `scripts/qbank/contrast_supply_v6.py`
- Modify: `tests/test_contrast_supply_v6.py`
- Create: `scripts/qbank/run_contrast_supply_v6.py`
- Create: `research/qgen/contrast_supply/transfer18_reference_retrieval_benchmark_v1.json`
- Create: `research/qgen/contrast_supply/transfer18_discovery_v6_wave_v1.json`
- Create: `research/qgen/contrast_supply/transfer18_discovery_v6_clinical_review_v1.json`

**Interfaces:**
- Consumes: general catalogue identity, Candidate Role Registry V1, Signature V2, granularity, subdomain, applicability, and containment metadata.
- Produces: `discover_global_candidates_v6(...) -> dict`, V5/V6 reference recall and precision, one frozen diagnostic V6 wave, and clinical review of only new survivors.

- [ ] Add RED tests for AOM/HbA1c/TTE/chest-radiography controls, representative diagnosis/investigation/management/ethical references, wrong-role/signature/containment negatives, cross-chapter compatibility, stable budget, and no anchor whitelist.
- [ ] Run focused tests and verify RED failures.
- [ ] Implement the minimal root-cause-specific V6 change, retaining all non-implicated V5 safety gates and deterministic ranking.
- [ ] Run focused tests and verify GREEN.
- [ ] Benchmark V5 and V6 on approved references, then freeze exactly one Transfer-18 development wave with no top-up.
- [ ] Reuse exact context-hash verdicts where valid and clinically review only genuinely new survivors.

### Task 5: Build diagnostic bundles and conditionally test questions

**Files:**
- Create: `research/qgen/contrast_supply/transfer18_v6_contrast_bundles_v1.json`
- Create: `research/qgen/contrast_supply/transfer18_v6_bundle_density_v1.json`
- Create: `research/qgen/contrast_supply/transfer18_v6_educational_feature_audit_v1.json`
- Conditionally create: `research/qgen/contrast_supply/transfer18_v6_development_questions_v1.json`
- Conditionally create: `research/qgen/contrast_supply/transfer18_v6_development_question_reviews_v1.json`

**Interfaces:**
- Consumes: approved references, feature profiles, evidence, pairwise review, and V6 survivors.
- Produces: Contrast Bundle V1-compatible diagnostic bundles, density metrics, bounded educational audit, and at most six no-retry development questions only when at least three anchors are contrast-ready.

- [ ] Construct or reuse bundles only for anchors with at least three safe alternatives and never re-author identical evidence.
- [ ] Validate bundle compatibility, second-key exclusions, evidence references, feature matrices, and density thresholds.
- [ ] Audit a bounded sample as `STRONG`, `ADEQUATE`, `WEAK`, or `UNSAFE`.
- [ ] If the generation gate is met, generate at most six development items, blind solve them, run post-stem liveness and final medical review, and record no retries; otherwise record zero generation.

### Task 6: Final verification, economics, report, and resume state

**Files:**
- Create: `reports/qgen_exact_anchor_candidate_typing_discovery_v6_milestone.json`
- Create: `reports/qgen_exact_anchor_candidate_typing_discovery_v6_copyright_audit.json`
- Modify: `MEMORY.md`

**Interfaces:**
- Consumes: all Task 1-5 artifacts and test outputs.
- Produces: final assessment/economics/readiness fields, immutable hash inventory, canonical audit, and exact resume point.

- [ ] Run focused deterministic validators and all QGEN safety/control/lifecycle tests; require zero new failures.
- [ ] Run the canonical copyright/leak audit over every new artifact; require PASS.
- [ ] Run the full canonical suite once after the final shared-code change and separate the known coordinator failure from new failures.
- [ ] Re-hash every historical frozen artifact and require exact preservation.
- [ ] Compute role-registry, Discovery V6, reference-supply, economics, and next-clean-cohort classifications without gaming suggested thresholds.
- [ ] Write the canonical milestone report with all requested final-return fields.
- [ ] Update only the changing QGEN resume section in `MEMORY.md`, run `git diff --check`, and verify `CLAUDE.md` plus all historical frozen artifacts are unchanged.
