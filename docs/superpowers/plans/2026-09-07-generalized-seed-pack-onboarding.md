# Generalized Seed-Pack Onboarding Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make independently reviewed seed packs for new study units explicit, versioned, scoped retrieval inputs and validate the architecture on the frozen development 12 before conditionally expanding to 36.

**Architecture:** Preserve the historical single-pack adapter and add a validated explicit multi-pack layer for onboarding packs. Only approved, correctly scoped rows enter the existing retrieval gates; all clinical artifacts remain evidence-grounded, independently reviewed, and content-addressed.

**Tech Stack:** Python 3, JSON Schema, pytest, canonical JSON/SHA-256 helpers, existing QGEN retrieval and feature-anchor modules.

**Spec:** `docs/superpowers/specs/2026-09-07-generalized-seed-pack-onboarding-design.md`

## Global Constraints

- Preserve both frozen development-input SHA-256 values byte-identically.
- Preserve all historical seed packs byte-identically.
- Use explicit pinned pack inputs only; never scan directories or select an implicit latest version.
- Admit only independently reviewed `APPROVED` seed rows.
- Do not relax the anchor floor, second-key ceiling, response-class gates, or feature maps.
- Treat the frozen 36 as a development regression set, not a pristine holdout.
- Create no commits because this request does not explicitly authorize them.

---

### Task 1: Reproduce and repair the retrieval integration gap

**Files:**
- Create: `tests/test_seed_pack_onboarding.py`
- Create: `scripts/qbank/seed_pack_onboarding.py`
- Modify: `scripts/qbank/profile_contrast_retrieval.py`

**Interfaces:**
- Consumes: existing seed-pack, enrichment, anchor, V5 snapshot, and profile documents.
- Produces: `validate_onboarding_pack`, `build_explicit_retrieval_index`, and optional scope filtering in `retrieve_profile_aware_contrasts`.

- [ ] Write a test passing an approved new pack to the desired explicit adapter and verify it fails because the current adapter cannot enumerate the new seed.
- [ ] Run the focused test and confirm the failure is the missing additional-pack contract.
- [ ] Implement strict pack validation, approved-row adaptation, explicit bundle ingestion, duplicate rejection, and scope metadata.
- [ ] Add tests for rejected/uncertain exclusion, omitted-pack invisibility, scope mismatch, historical exact replay, anchor floor, and second-key ceiling.
- [ ] Run the focused retrieval/onboarding suites.

### Task 2: Freeze and validate development-12 inputs

**Files:**
- Create: `scripts/qbank/seed_pack_onboarding_milestone.py`
- Create: `research/qgen/onboarding/v6_development_12_selection.json`
- Test: `tests/test_seed_pack_onboarding_milestone.py`

**Interfaces:**
- Consumes: frozen-36 roster, Route-A report, feature maps, V5, and Profile V2.
- Produces: deterministic 12-row roster and hash manifest.

- [ ] Write selection tests for two rows per discipline, canonical ID order, and Route-A exclusion.
- [ ] Verify RED, implement the deterministic selector, and verify GREEN.
- [ ] Build the roster and validate frozen hashes and discipline counts.

### Task 3: Discover, review, and package bounded clinical seeds

**Files:**
- Create: `research/qgen/onboarding/v6_development_seed_candidates.json`
- Create: `research/qgen/onboarding/v6_development_seed_independent_review.json`
- Create: `research/qgen/onboarding/v6_development_seed_pack.json`
- Create: `research/qgen/onboarding/v6_development_seed_pack.enrichment.json`
- Create: `research/qgen/onboarding/v6_development_seed_pack.stem_anchors.json`
- Create: `schemas/generalized-competitive-contrast-seed-pack.schema.json`

**Interfaces:**
- Consumes: development-12, canonical relations/anchors/evidence, graph, and TN FTS discovery results.
- Produces: reviewed seed rows and explicit retrieval bundle with content/review hashes.

- [ ] Discover up to five candidates per opportunity and apply deterministic cheap filters.
- [ ] Author relation/anchor/scope proposals only where evidence supports both plausibility and inferiority.
- [ ] Run one independent high-reasoning semantic review, blind to yield.
- [ ] Materialize only approved rows into the retrievable companion layers while retaining all review outcomes in the registry.
- [ ] Validate schema, hashes, provenance, duplicate identities, and backwards-anchor guard.

### Task 4: Replay development gates and conditionally generate

**Files:**
- Create: `reports/qgen_seed_pack_onboarding_milestone.json`
- Create when gated: development-36 registry/replay, frozen contrast-set, generated-item, blind-solve, and independent-review artifacts.
- Modify: `MEMORY.md`

**Interfaces:**
- Consumes: historical bundles, approved new bundle, frozen 36/maps, V5, and Profile V2.
- Produces: development-12 and conditional development-36 readiness, economics, failure taxonomy, and final decision.

- [ ] Replay historical-only and prove exact identity.
- [ ] Replay development-12 with explicit new packs and evaluate the five architecture gates.
- [ ] If validated, expand bounded onboarding to the remaining 24 and replay all 36.
- [ ] If any row is contrast-ready, freeze exactly one three-competitor set, run one generation attempt, blind solve, post-stem validation, and final medical review.
- [ ] Calculate failure counts, reuse/economics, graph/FTS contribution, and context percentiles deterministically.
- [ ] Update only the changing QGEN resume section in `MEMORY.md`.
- [ ] Run focused tests, `git diff --check`, frozen-hash checks, and one full canonical suite.
