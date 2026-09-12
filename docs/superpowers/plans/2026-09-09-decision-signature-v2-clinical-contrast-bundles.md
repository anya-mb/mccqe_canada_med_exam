# Decision Signature V2, Discovery V5, and Clinical Contrast Bundles Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:test-driven-development to implement this plan task-by-task and superpowers:verification-before-completion before completion claims. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and validate Decision Signature V2, global Discovery V5, and a reusable evidence-backed Clinical Contrast Bundle V1 cache on development data without consuming a clean cohort.

**Architecture:** Add a V5 module and deterministic runner beside the frozen V4 code. Freeze semantic inputs before replay, keep authored clinical judgements in explicit hash-bound artifacts, and compute all schemas, gates, counts, hashes, density, economics, and readiness deterministically.

**Tech Stack:** Python 3.13, JSON Schema, pytest, existing canonical SHA256/copyright/generation-lifecycle utilities.

**Spec:** `docs/superpowers/specs/2026-09-09-decision-signature-v2-clinical-contrast-bundles-design.md`

## Global Constraints

- Preserve every V1/V3/V4/cache/Transfer historical artifact byte-identically.
- Use Catalogue V2 canonical identities; do not generate candidate names or use embeddings.
- Use one bounded retrieval wave of at most eight candidates per anchor and at most 24 anchors.
- Run semantic review sequentially and store evidence as normalized propositions plus references.
- Do not run a clean transfer cohort or operational holdout.
- Create no commit and do not modify `CLAUDE.md`.

---

### Task 1: Freeze benchmark and V2 forensic evidence

**Files:**
- Create: `research/qgen/contrast_supply/decision_signature_v2_compatibility_benchmark.json`
- Create: `reports/qgen_decision_signature_v2_forensics.json`
- Create: `reports/qgen_decision_signature_v2_economy.json`
- Create: `reports/qgen_decision_signature_v2_independent_review.json`

**Interfaces:**
- Produces hash-bound positive and hard-negative pairs plus a reviewed V2 controlled vocabulary.

- [ ] Reconstruct approved positives and the six frozen V4 residual failures from canonical artifacts.
- [ ] Classify the earliest reusable mismatch for all six cases and reject disease/opportunity-specific values.
- [ ] Compute value counts, single-use values, cross-unit/cross-discipline reuse, and authored/derived fractions.
- [ ] Record a separate review verdict; stop before implementation unless it is `APPROVED`.

### Task 2: Implement Signature V2 and Discovery V5 with TDD

**Files:**
- Create: `scripts/qbank/contrast_supply_v5.py`
- Create: `tests/test_contrast_supply_v5.py`
- Create: `research/qgen/contrast_supply/decision_signature_v2.json`
- Create: `research/qgen/contrast_supply/build_12_discovery_v5.json`
- Create: `research/qgen/contrast_supply/diagnostic_transfer_12_discovery_v5.json`

**Interfaces:**
- Produces `validate_decision_signature_v2(signature, vocabularies)`, `signatures_v2_compatible(opportunity, candidate)`, and `discover_global_candidates_v5(catalogue, opportunity, signatures, budget=8)`.

- [ ] Write failing positive-recall and hard-negative signature tests, including cross-chapter controls.
- [ ] Run the tests and confirm RED failures are caused by missing V2 behavior.
- [ ] Implement the minimal V2 validator/compatibility function and run GREEN.
- [ ] Write failing V5 tests for global retrieval, exclusions, generic concepts, and four-candidate supply.
- [ ] Run RED, implement V5 filtering/ranking/provenance, and run GREEN.
- [ ] Freeze implementation and artifact content hashes before clinical review.

### Task 3: Define and validate Clinical Contrast Bundle V1

**Files:**
- Create: `schemas/clinical-contrast-bundle-v1.schema.json`
- Modify: `scripts/qbank/contrast_supply_v5.py`
- Modify: `tests/test_contrast_supply_v5.py`

**Interfaces:**
- Produces `validate_contrast_bundle_v1(bundle)`, `classify_bundle_admission(bundle)`, and `build_contrast_bundle_cache_v1(bundles)`.

- [ ] Write failing schema/semantic tests for response-class consistency, matrix states, UNKNOWN-vs-ABSENT, positive anchors, inferiority discriminators, evidence refs, visibility, pairwise containment, and admission arithmetic.
- [ ] Run RED, implement minimal validators/cache scoping, and run GREEN.
- [ ] Validate the JSON Schema against representative valid and invalid bundles.

### Task 4: Freeze roster, pools, clinical reviews, and evidence-backed bundles

**Files:**
- Create: `research/qgen/contrast_supply/development_bundle_roster_v1.json`
- Create: `research/qgen/contrast_supply/development_candidate_pools_v5.json`
- Create: `research/qgen/contrast_supply/development_candidate_cheap_filter_v5.json`
- Create: `research/qgen/contrast_supply/development_candidate_clinical_review_v1.json`
- Create: `research/qgen/contrast_supply/clinical_contrast_bundles_v1.json`
- Create: `research/qgen/contrast_supply/clinical_contrast_bundle_independent_review_v1.json`
- Create: `research/qgen/contrast_supply/clinical_contrast_bundle_cache_v1.json`

**Interfaces:**
- Consumes only canonical candidate identities and frozen evidence.
- Produces a one-wave pool and one serial independent verdict per candidate/bundle.

- [ ] Select and hash at most 24 evidence-rich anchors across development cohorts and controls.
- [ ] Retrieve at most eight canonical candidates per anchor once, then apply deterministic gates.
- [ ] Review every survivor as plausible/dead/wrong/second-key/uncertain.
- [ ] Reuse verified evidence, perform only necessary narrow authoritative research, and normalize propositions.
- [ ] Author 3–8 useful features per plausible candidate where evidence permits.
- [ ] Build matrices with pairwise and next-step metadata, classify visibility, and independently review serially.
- [ ] Admit/cache only approved alternatives and compute bundle categories.

### Task 5: Replay density and assess educational quality

**Files:**
- Create: `reports/qgen_build12_contrast_bundle_density_v1.json`
- Create: `reports/qgen_diagnostic_transfer_contrast_bundle_density_v1.json`
- Create: `reports/qgen_contrast_bundle_supply_assessment_v1.json`
- Create: `reports/qgen_contrast_bundle_educational_review_v1.json`

**Interfaces:**
- Produces threshold counts, review economics, and at most six deterministic educational-review rows.

- [ ] Replay Build-12 and diagnostic Transfer-12 strictly against the frozen cache.
- [ ] Compute one-through-five alternative density and semantic-review economics.
- [ ] Select at most six generatable bundles deterministically and record independent education verdicts.

### Task 6: Conditional smoke test and final milestone report

**Files:**
- Create conditionally: `research/qgen/contrast_supply/development_bundle_smoke_questions_v1.json`
- Create conditionally: `reports/qgen_contrast_bundle_smoke_review_v1.json`
- Create: `reports/qgen_signature_v2_discovery_v5_contrast_bundles_milestone.json`
- Modify: `MEMORY.md`

**Interfaces:**
- Consumes frozen approved bundles through the existing lifecycle.
- Produces final safety, assessment, copyright, economics, and readiness fields.

- [ ] If at least three bundles are generatable, create at most six one-attempt items from STEM_ELIGIBLE features and approved options only.
- [ ] Run blind solve, post-stem liveness, rationale-from-matrix validation, and final medical review with no retries.
- [ ] Run focused tests and historical/AOM/lifecycle controls.
- [ ] Run the canonical full suite once at final shared-code state and reconcile the known coordinator failure separately.
- [ ] Run copyright/leak audit, frozen-file verification, `git diff --check`, and prove `CLAUDE.md` unchanged.
- [ ] Update only the QGEN architecture resume block in `MEMORY.md` and emit the requested final template.
