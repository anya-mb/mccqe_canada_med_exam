# Opportunity Registry V2 and Production Pilot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Independently measure Registry V1 completeness, build a generalizable audited V2 only if justified, and run a 24-item maximum real production pilot only when every production gate passes.

**Architecture:** Preserve V1 as an immutable hash-bound baseline. A new deterministic `curriculum_opportunity_registry_v2` module owns roster selection, comparison arithmetic, V2 construction, allocation, queueing, audits, and report assembly; frozen semantic review artifacts are authored serially and consumed as data. Production-pilot orchestration is isolated in a second module so registry gates can fail closed without generating prose.

**Tech Stack:** Python 3, pytest, canonical JSON/SHA-256, existing QGEN candidate/evidence/Question Seed modules.

**Spec:** User-approved 50-phase `CURRICULUM-OPPORTUNITY-REGISTRY-V2 + INDEPENDENT-COMPLETENESS-BENCHMARK + DEEP-LEARNER-DECISION-ENUMERATION + BLUEPRINT-AND-MCQ-SUITABILITY-AUDIT + PRODUCTION-PILOT-WAVE-1A` contract supplied on 2026-09-10.

## Global Constraints

- Work from HEAD `01eff40984bee76418c7fab82a1ded9fbfa2d9e5` and preserve the exact dirty worktree.
- Create no commits; do not reset, clean, stash, checkout, or discard WIP.
- Preserve every V1 and historical frozen artifact byte-identically.
- Use deterministic Python for selection, joins, counts, hashes, dedupe, allocation, queueing, and validation.
- Keep semantic medical review serial; do not use external LLM APIs.
- Never optimize toward 1,000 questions per discipline and never generate a mass production bank.
- Blind benchmark reviewers cannot see V1 opportunities before the benchmark is frozen.
- Shared-code changes require test-first red-green cycles and one final full-suite run.

---

### Task 1: Safe-resume and immutable V1 comparison contract

**Files:**
- Create: `research/qgen/opportunity_registry_v2/registry_v1_comparison_contract.json`
- Create: `reports/opportunity_registry_v2_safe_resume.json`
- Test: `tests/test_curriculum_opportunity_registry_v2.py`

**Interfaces:**
- Consumes: V1 snapshot, registry, allocation, queue, milestone, master crosswalk, MCC registry, exposure registry, source/readiness assets.
- Produces: `verify_safe_resume(root: Path) -> dict` and `build_v1_comparison_contract(root: Path) -> dict`.

- [x] Write tests asserting the four stated canonical content hashes, HEAD, V1 counts/distributions, and fail-closed behavior on any mismatch.
- [x] Run the focused test and confirm failure because the V2 module does not exist.
- [x] Implement canonical content-hash verification and the comparison contract without touching V1.
- [x] Run the focused test to green and freeze the comparison-contract content hash.

### Task 2: Blind stratified benchmark roster and packets

**Files:**
- Create: `scripts/qbank/curriculum_opportunity_registry_v2.py`
- Create: `research/qgen/opportunity_registry_v2/completeness_benchmark_roster_v1.json`
- Create: `research/qgen/opportunity_registry_v2/blind_benchmark_input_v1.json`
- Modify: `tests/test_curriculum_opportunity_registry_v2.py`

**Interfaces:**
- Produces: `select_benchmark_roster(snapshot, *, per_discipline=12) -> list[dict]` and `build_blind_benchmark_input(...) -> dict`.

- [x] Write tests proving stable approximately 12-per-discipline selection spans priority, chapters, commonness proxy, and V1-density bands without exposing V1 opportunity text or desired yield.
- [x] Run the tests and confirm the expected behavior failures.
- [x] Implement stable stratification and blind-packet projection.
- [x] Run tests to green, generate the roster once, and freeze its hash before semantic enumeration.

### Task 3: Serial independent enumeration and benchmark freeze

**Files:**
- Create: `schemas/independent-opportunity-benchmark-v1.schema.json`
- Create: `research/qgen/opportunity_registry_v2/independent_opportunity_benchmark_v1.json`
- Modify: `tests/test_curriculum_opportunity_registry_v2.py`

**Interfaces:**
- Produces: atomic benchmark rows with controlled family, response class, stage/population, MCCQE-level verdict, source anchors, and reviewer rationale.

- [x] Write schema/validation tests for atomicity, generalist scope, controlled families, unique fingerprints, and explicit rejection of compound/specialist/cosmetic opportunities.
- [x] Run the tests red.
- [ ] Enumerate all defensible decisions serially from the blind packets, using no V1 opportunity text or count target.
- [ ] Validate, freeze, hash, and make no semantic edits after unblinding.

### Task 4: V1 matching, recall/precision, taxonomies, and independent audits

**Files:**
- Create: `research/qgen/opportunity_registry_v2/v1_benchmark_comparison.json`
- Create: `research/qgen/opportunity_registry_v2/mcq_suitability_blind_audit_v1.json`
- Create: `research/qgen/opportunity_registry_v2/semantic_duplicate_stress_test_v1.json`
- Create: `research/qgen/opportunity_registry_v2/blueprint_classification_audit_v1.json`
- Create: `reports/opportunity_registry_v1_independent_assessment.json`
- Modify: `scripts/qbank/curriculum_opportunity_registry_v2.py`
- Modify: `tests/test_curriculum_opportunity_registry_v2.py`

**Interfaces:**
- Produces: deterministic stratified sample/pair selectors and metric/confusion-matrix aggregation over frozen semantic verdicts.

- [ ] Write failing tests for exact/semantic/partial/missing/invalid matching; supported/overgenerated/ambiguous V1 rows; recall/precision denominators; taxonomy totals; 120-row MCQ sample; at least 150 likely duplicate pairs; and blueprint confusion matrices.
- [ ] Run red, implement selectors/aggregators, and rerun green.
- [ ] Perform the semantic verdicts serially without exposing prior verdict fields, freeze each audit, then calculate the V1 assessment.
- [ ] Freeze the diagnosis before any V2 rule is written.

### Task 5: Generalizable Enumeration V2 under TDD

**Files:**
- Create: `schemas/curriculum-question-opportunity-v2.schema.json`
- Modify: `scripts/qbank/curriculum_opportunity_registry_v2.py`
- Modify: `tests/test_curriculum_opportunity_registry_v2.py`

**Interfaces:**
- Produces: `enumerate_v2(snapshot_row: dict) -> list[dict]`, `deduplicate_v2(rows)`, and provenance values `V1_PRESERVED`, `V2_NEW_FAMILY`, `V2_STAGE_EXPANSION`, `V2_POPULATION_EXPANSION`, `V2_OTHER`.

- [ ] Add red tests preserving known V1 successes and recovering each diagnosed missed family while excluding compound, cosmetic, specialist, and benchmark-ID-specific behavior.
- [ ] Run red and record the expected failures.
- [ ] Implement the smallest diagnosis-driven general rules, never a study-unit whitelist.
- [ ] Run focused tests green and inspect the source for benchmark identifiers.

### Task 6: Registry V2, dedupe, benchmark replay, capacity, blueprint, readiness

**Files:**
- Create: `research/qgen/opportunity_registry_v2/curriculum_question_opportunity_registry_v2.json`
- Create: `research/qgen/opportunity_registry_v2/semantic_near_duplicate_review_v2.json`
- Create: `research/qgen/opportunity_registry_v2/v2_benchmark_comparison.json`
- Create: `research/qgen/opportunity_registry_v2/curriculum_coverage_matrix_v2.json`
- Create: `reports/opportunity_registry_v2_capacity_and_readiness.json`
- Modify: `scripts/qbank/curriculum_opportunity_registry_v2.py`
- Modify: `tests/test_curriculum_opportunity_registry_v2.py`

**Interfaces:**
- Produces: full-curriculum V2 and independently calculated recall, precision, capacity bands, feasibility classifications, V1/V2 blueprint comparison, and readiness states.

- [ ] Write red tests for whole-snapshot coverage, provenance, exact/semantic dedupe accounting, no tuning during benchmark replay, capacity bounds, readiness conservation, and non-quota feasibility.
- [ ] Run red, implement deterministic builders, and rerun green.
- [ ] Build V2 once; allow at most one generalizable rule revision if the frozen benchmark demonstrates a rule-level failure.

### Task 7: Allocation Plan V2, Production Queue V2, and pilot gate

**Files:**
- Create: `research/qgen/opportunity_registry_v2/question_bank_allocation_plan_v2.json`
- Create: `research/qgen/opportunity_registry_v2/production_queue_v2.json`
- Create: `reports/opportunity_registry_v2_production_gate.json`
- Modify: `scripts/qbank/curriculum_opportunity_registry_v2.py`
- Modify: `tests/test_curriculum_opportunity_registry_v2.py`

**Interfaces:**
- Produces coverage-first slot allocation and deterministic queue rows preserving opportunity, seed slot, readiness, priority, wave, and dependencies.

- [ ] Write red tests for coverage-before-variants, priority/blueprint/distinctness/difficulty ordering, slot uniqueness, five waves, dependency validity, and every Phase-30 gate.
- [ ] Run red, implement allocation/queue/gate, and rerun green.
- [ ] Stop all production-item work if the gate fails.

### Task 8: Gated no-retry real production pilot

**Files:**
- Create: `scripts/qbank/production_pilot_wave_1a.py`
- Create: `research/qgen/production_pilot_wave_1a/*.json`
- Create: `reports/production_pilot_wave_1a_milestone.json`
- Test: `tests/test_production_pilot_wave_1a.py`

**Interfaces:**
- Consumes: passing production gate, Queue V2, validated candidate/evidence/Question Seed architecture.
- Produces: at most 24 `PRODUCTION_ITEM` records and separate blind-solve, liveness, final-review, duplicate, quality, and economics artifacts.

- [ ] Write red lifecycle tests for roster balance without weak substitution, seed-before-item, one attempt only, no post-generation discovery, blind-solve isolation, three live distractors, evidence-bounded rationales, duplicate rejection, and production-only status.
- [ ] Run red, implement the deterministic orchestrator, and rerun green.
- [ ] Select the roster; perform source/candidate/evidence work serially; create one seed and one item attempt per selected opportunity.
- [ ] Perform blind solve, liveness, final medical, duplicate, and fresh quality reviews serially; weak/unsafe items remain rejected.
- [ ] Calculate production economics and scale-batch recommendation from actual pilot outcomes.

### Task 9: Safety, copyright, milestone report, and resume state

**Files:**
- Create: `reports/opportunity_registry_v2_and_production_pilot_milestone.json`
- Create: `reports/opportunity_registry_v2_and_production_pilot_copyright_audit.json`
- Modify: `MEMORY.md` changing only `QGEN_ARCHITECTURE_RESUME` current/resume-state content.
- Modify: focused tests only if a reproducible defect is discovered.

**Interfaces:**
- Produces the exact final-return fields requested by the milestone contract.

- [ ] Replay AOM, anchorless/second-key, response-class, granularity, admission, evidence, next-action, bundle, seed-lifecycle, duplicate, exposure, and historical-hash controls.
- [ ] Audit every new prose-bearing artifact for substantial Toronto Notes overlap.
- [ ] Assemble the milestone solely from canonical artifacts and update the resume state from that report.

### Task 10: Final verification

**Files:** All milestone outputs.

- [ ] Run all focused V2/pilot tests plus historical safety controls.
- [ ] Run `git diff --check`, verify `CLAUDE.md` unchanged, compare the pre/post frozen-artifact hash manifest, and confirm `COMMITS_CREATED=0`.
- [ ] Run the canonical full suite exactly once at final shared-code state and classify only the known coordinator failure as pre-existing.
- [ ] Regenerate deterministic outputs and prove byte identity.
- [ ] Reconcile every requested final-return field against the canonical milestone report before responding.
