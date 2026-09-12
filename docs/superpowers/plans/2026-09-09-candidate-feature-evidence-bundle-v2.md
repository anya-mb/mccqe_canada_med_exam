# Candidate Feature Evidence and Bundle V2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert the 60 independently approved Transfer-18 development candidates into source-traced feature profiles and evidence-backed contrast bundles, then conditionally validate a bounded set of development questions.

**Architecture:** Add an append-only evidence layer downstream of frozen Discovery V6. A deterministic Python module owns cohort binding, registry validation, evidence reuse classification, profile and bundle admission, tracing, metrics, and hashes; reviewed JSON inputs own clinical propositions and independent decisions. A single runner materializes reproducible milestone artifacts without altering frozen V6 inputs.

**Tech Stack:** Python 3 standard library, JSON Schema artifacts, pytest/unittest repository suite, canonical JSON, repository copyright validator.

**Spec:** `/Users/annabeketova/.codex/attachments/93cd2d1c-8447-4856-8628-39ba4dee8dc3/pasted-text.txt`

## Global Constraints

- Work from the exact dirty worktree at `01eff40984bee76418c7fab82a1ded9fbfa2d9e5`; do not reset, clean, stash, checkout, discard WIP, or commit.
- Preserve all frozen historical artifacts byte-identical; Discovery V6 may receive only a nonsemantic adapter if proven necessary.
- Freeze exactly 60 `APPROVED_REFERENCE` candidates; exclude 10 rejected and 2 uncertain candidates.
- Existing repository evidence is searched before new evidence; topical similarity is not entailment.
- Only independently `ENTAILED` propositions may carry load-bearing admission roles.
- `UNKNOWN` is not `ABSENT`; silence is not negative evidence.
- Semantic medical adjudication is serial; no external LLM APIs.
- Generate at most 12 development questions only if at least six anchors have three evidence-backed approved alternatives; no retries and no fresh clean cohort.
- Run focused validation throughout and one canonical full suite at final shared-code state; separate the known unrelated source-research coordinator failure.
- Copyright audit must pass with normalized propositions and references only.

---

### Task 1: Freeze and validate the evidence cohort

**Files:**
- Create: `scripts/qbank/feature_evidence.py`
- Create: `tests/test_feature_evidence.py`
- Create: `research/qgen/contrast_supply/feature_evidence_cohort_v1.json`

**Interfaces:**
- Consumes: reference candidate set, independent review, Candidate Role Registry V1, Catalogue V3, Discovery V6 hashes.
- Produces: `build_evidence_cohort(reference_set, review) -> dict`, `validate_evidence_cohort(cohort) -> list[str]`, and a 60-row hash-bound cohort.

- [ ] Write tests proving exact 60-member admission, rejected/uncertain exclusion, required decision metadata, duplicate rejection, and hash stability.
- [ ] Run the focused tests and confirm they fail because the new module is absent.
- [ ] Implement the smallest cohort builder and validator that passes.
- [ ] Run the focused tests and preserve the generated cohort only after validation.

### Task 2: Add Feature Evidence Registry V1 contracts and reuse lookup

**Files:**
- Create: `schemas/feature-evidence-registry-v1.schema.json`
- Modify: `scripts/qbank/feature_evidence.py`
- Modify: `tests/test_feature_evidence.py`
- Create: `research/qgen/contrast_supply/anchor_reference_provisional_feature_audit_v1.json`
- Create: `research/qgen/contrast_supply/feature_evidence_reuse_baseline_v1.json`

**Interfaces:**
- Produces: `validate_evidence_fact`, `canonical_fact_hash`, `classify_evidence_reuse`, and feature-role compatibility enforcement.

- [ ] Write failing tests for required registry fields, closed feature roles, response-class relevance, source refs, content hashes, duplicate proposition handling, and all seven reuse classifications.
- [ ] Implement minimal registry/reuse validation and rerun focused tests.
- [ ] Deterministically classify all 180 provisional feature rows and inventory all existing verified repository evidence before any new source acquisition.
- [ ] Persist the audit and baseline with reproducible counts and input hashes.

### Task 3: Acquire, normalize, and independently review load-bearing evidence

**Files:**
- Create: `research/qgen/contrast_supply/feature_evidence_registry_v1.json`
- Create: `research/qgen/contrast_supply/feature_evidence_entailment_review_v1.json`
- Create: `research/qgen/contrast_supply/evidence_backed_candidate_feature_profiles_v1.json`
- Create: `research/qgen/contrast_supply/evidence_backed_key_feature_profiles_v1.json`

**Interfaces:**
- Registry facts are concept-scoped and reusable; profiles reference fact IDs rather than duplicate proposition prose.

- [ ] Group evidence gaps by canonical concept and reuse exact/semantic repository evidence where it entails the requested proposition.
- [ ] Acquire only missing load-bearing propositions from current authoritative sources, recording source authority/date/scope and normalized propositions.
- [ ] Independently review every load-bearing proposition serially; narrow and rereview partial statements, and fail closed on rejected/uncertain evidence.
- [ ] Build 60 candidate profiles and 18 scoped key profiles, marking FULL/PARTIAL/UNSUPPORTED from admitted fact roles.
- [ ] Validate hashes, source references, and profile admission rules with focused tests.

### Task 4: Build contrast matrices and evidence-backed Bundle Cache V2

**Files:**
- Modify: `scripts/qbank/feature_evidence.py`
- Modify: `tests/test_feature_evidence.py`
- Create: `research/qgen/contrast_supply/evidence_backed_contrast_matrices_v2.json`
- Create: `research/qgen/contrast_supply/clinical_contrast_bundles_v2_evidence_backed.json`
- Create: `research/qgen/contrast_supply/clinical_contrast_bundles_v2_independent_review.json`

**Interfaces:**
- Produces: `admit_candidate_to_bundle(profile, registry)`, `build_contrast_matrix`, and `classify_bundle_density`.

- [ ] Write failing tests proving non-UNKNOWN cells require entailed evidence, absent cannot be inferred from silence, and bundle candidates require both positive plausibility and a meaningful discriminator.
- [ ] Implement minimal admission and matrix logic; rerun focused tests.
- [ ] Materialize all 18 matrices and candidate sets using evidence-ready profiles only.
- [ ] Perform serial independent candidate/bundle review for educational coherence, containment, and second-key risk; exclude rejected/uncertain rows.
- [ ] Recompute density and evidence-pipeline loss against the frozen reference supply.

### Task 5: Measure reuse, Build-12 transfer, and educational quality

**Files:**
- Create: `research/qgen/contrast_supply/feature_evidence_build12_reuse_replay_v1.json`
- Create: `research/qgen/contrast_supply/evidence_backed_bundle_educational_review_v1.json`
- Create: `reports/qgen_candidate_feature_evidence_economics_v1.json`

**Interfaces:**
- Produces deterministic reuse metrics over fact-to-anchor and fact-to-candidate-context references.

- [ ] Write failing tests for unique-fact counting, cross-anchor/cross-candidate reuse, key-profile reuse, and pairwise evidence accounting.
- [ ] Implement metrics and run the focused tests.
- [ ] Replay exact-scope reuse against Build-12 without authoring extra Build-12 evidence.
- [ ] Select at most eight bundles deterministically across disciplines and independently grade their educational utility.

### Task 6: Conditionally generate and validate development questions

**Files:**
- Create if gated: `research/qgen/contrast_supply/evidence_backed_development_questions_v1.json`
- Create if gated: `research/qgen/contrast_supply/evidence_backed_development_blind_solve_v1.json`
- Create if gated: `research/qgen/contrast_supply/evidence_backed_development_post_stem_liveness_v1.json`
- Create if gated: `research/qgen/contrast_supply/evidence_backed_development_final_medical_review_v1.json`
- Modify: `scripts/qbank/feature_evidence.py`
- Modify: `tests/test_feature_evidence.py`

**Interfaces:**
- Every stem and rationale claim carries registry fact IDs; generation is disabled unless six anchors have at least three independently approved evidence-backed alternatives.

- [ ] Write failing tests for the generation threshold, 12-item/2-per-discipline bounds, selected-candidate provenance, stem/rationale tracing, and no-retry policy.
- [ ] Implement the deterministic gate and trace validator; rerun focused tests.
- [ ] If gated, author at most 12 evidence-derived development items, run blind solve, require three live-but-inferior distractors, and perform final medical review with no retries.
- [ ] If not gated, emit a deterministic zero-item gate result and no fabricated question artifacts.

### Task 7: Historical safety, copyright, final report, and resume state

**Files:**
- Create: `scripts/qbank/run_candidate_feature_evidence_v1.py`
- Create: `reports/qgen_candidate_feature_evidence_bundle_v2_milestone.json`
- Create: `reports/qgen_candidate_feature_evidence_bundle_v2_copyright_audit.json`
- Modify: `MEMORY.md`

**Interfaces:**
- Runner rebuilds all deterministic outputs from frozen/reviewed inputs and emits the exact final contract fields.

- [ ] Write failing end-to-end tests for historical safety controls, exclusions, lifecycle invariants, reproducible hashes, and report reconciliation.
- [ ] Implement the runner and rerun all focused tests.
- [ ] Run the canonical copyright/leak audit over every new registry/profile/matrix/bundle/question/rationale/report artifact.
- [ ] Run `git diff --check`, the focused suite, and exactly one canonical full suite at final shared-code state; classify pre-existing versus new failures.
- [ ] Verify frozen artifact hashes and that no commit was created, update only the changing QGEN resume section in `MEMORY.md`, then rerun `git diff --check` and the focused resume/report checks.

