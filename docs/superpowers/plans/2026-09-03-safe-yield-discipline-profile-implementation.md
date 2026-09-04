# Coverage-First Safe-Yield and Discipline-Profile Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the approved `COMMON_CORE_PLUS_DISCIPLINE_PROFILES` architecture with global critical-fact
adjudication, role-blind option-set admissibility, coverage-first safe-yield planning and gap reporting; then run
gate G0 (frozen R4 replay) and, only on a perfect G0, a bounded cross-profile G1 safe-yield micro pilot.

**Architecture:** Deterministic Python modules over externally-authored, frozen JSON vocabularies. Every semantic
judgement is supplied by a party that cannot see the outcome it would certify: option labels are role-blind and
item-blind, the demanded response class is assigned from stem and lead-in only, seed condition predicates are
frozen enrichment of an already-frozen pack, and admissibility is arithmetic over those labels.

**Tech Stack:** Python 3.11, JSON Schema, pytest.

**Spec:** `docs/superpowers/specs/2026-09-03-discipline-profile-qgen-and-fact-safety-design.md` (Parts I and II).

**Starting commit:** `c406053`.

## Global constraints

- `research/scope/question_bank_targets.json` and `research/scope/final_question_allocation.json` stay
  byte-identical. The 6,086 allocation is read as curriculum density, never as a production quota.
- No new artifact may define a minimum-, target-, remaining- or shortfall-shaped field; a validator asserts this.
- Frozen r2/r3/r4 generation artifacts and the r4 seed pack are read at their own schema version and never mutated.
- Profiles are validated data. A profile entry naming a diagnosis, drug, topic or threshold value is a validation
  error.
- No production module may contain an R4 item id or R4 clinical text; a test asserts this.
- An axis that is a response-class axis for an archetype may not also be a nominal parity axis for the same
  archetype, and an axis is declared only where a reviewer-observed defect requires it.
- `NO_SAFE_ITEM` and fail-closed outcomes are first-class successes, never penalties.
- Do not run G1 unless G0 is 8/8 and 7/7. Do not start G2.

## Answers to the spec's open implementation questions

1. **§13.1 — who authorises an option-set archetype exception?** The profile owner, by listing the pair in the
   profile's `permitted_archetype_exceptions` with a justification. The exception is recorded on the item as
   `archetype_exception_id`. No exception is needed for a lead-in that names no narrower purpose: the demanded
   class is then the archetype's declared `generic_token`, which every member of the archetype carries.
2. **§13.2 — which structured references back the anatomy/pharmacology check?** A new
   `research/qgen/reference_constants.json`, schema-validated, each constant carrying an issuing authority, a
   quantity class, a canonical value or proportional definition, and a plausible range. Constants are admitted the
   same way sources are: provenance first, and a constant with no admitted authority cannot adjudicate anything.
3. **§13.3 — does MED need its own pilot?** Yes, but not here. MED is exercised in G1 only to the extent canonical
   evidence exists; its untested status is carried on the profile as `r4_status: UNTESTED_IN_R4`.
4. **§13.4 — merge entailment and ADM-3?** No. Entailment asks whether a claim supports a statement; ADM-3 asks
   whether a competitor's frozen correctness condition survives the realized stem. They share the stem feature map
   and nothing else.
5. **§13.5 — migration of frozen r2-r4 artifacts?** Not migrated. They are read at their own schema version.
6. **§28.6 — who freezes `declared_learner_decisions[]`?** Not the generator. Until an authorised authoring task
   runs, the field is empty and the coverage report must diagnose such an address `DECISIONS_NOT_DECLARED`, never
   `NARROW_TOPIC`. This is the load-bearing guard of §27 item 2 and is enforced by a test.
7. **§28.7 — two state machines?** One. The opportunity lifecycle owns generation state; the manifest's
   `generation_status_values` stay a source-readiness vocabulary and are not duplicated per opportunity.

---

### Task 1: Discipline profiles as validated data

**Files:** create `schemas/discipline-profile.schema.json`, `scripts/qbank/qgen_profiles.py`,
`research/qgen/profiles/{MEDICINE,PEDIATRICS,OBGYN,SURGERY,PSYCHIATRY,PHELO}.profile.json`,
`tests/test_qgen_profiles.py`.

- [ ] Step 1: Failing tests — profile naming a clinical entity rejected; unknown archetype rejected; an axis
      declared both response-class and nominal for one archetype rejected; all six profiles load and validate.
- [ ] Step 2: Implement `load_discipline_profile`, `validate_discipline_profile`, `resolve_option_set_contract`.
- [ ] Step 3: Author the six profiles at discipline x item-archetype level, every axis traced to a spec §5 line.

### Task 2: Option-set archetypes and independent admissibility

**Files:** create `scripts/qbank/option_set_admissibility.py`,
`schemas/role-blind-option-labels.schema.json`, `tests/test_option_set_admissibility.py`.

- [ ] Step 1: Failing tests — identical generator labels on semantically mismatched options are rejected;
      valid same-archetype options accepted; lone-key response class rejected; severity/category mismatch
      rejected; label file containing a role or item id rejected; ADM-3/4/5 fire on synthetic inputs.
- [ ] Step 2: Implement ADM-1 membership, ADM-2 (existing parity logic on declared nominal axes only), ADM-3
      condition-predicate join, ADM-4 action-signature intersection, ADM-5 deterministic realization parity.
- [ ] Step 3: Implement `adjudicate_option_set_admissibility` returning per-rule verdicts and an arithmetic
      overall verdict, plus `FAIL_CLOSED_INSUFFICIENT_ADMISSIBLE_COMPETITORS` when fewer than three survive.

### Task 3: Global critical-fact adjudication

**Files:** create `scripts/qbank/critical_fact_adjudication.py`,
`schemas/critical-fact-adjudication.schema.json`, `schemas/reference-constants.schema.json`,
`research/qgen/reference_constants.json`, `research/qgen/source_authority_registry.json`,
`tests/test_critical_fact_adjudication.py`.

- [ ] Step 1: Failing tests — numeric/unit conflict adjudicates or fails closed; safe derivation accepted;
      unit-transposition suspicion fires; structured-reference contradiction fires; a mandatory-corroboration
      class with one source fails closed; an ordinary qualitative claim stays Level 0.
- [ ] Step 2: Implement deterministic fact-class detection over the fourteen classes, Levels 0-3, the seven §4.3
      sanity checks, and the `SOURCE_CLAIM / CONFLICTING_EVIDENCE / ADJUDICATED_VALUE / ADJUDICATION_BASIS` record.
- [ ] Step 3: Implement the `transcription_status` / `fact_status` split and numeric *assertion* enumeration.

### Task 4: Coverage priority from the frozen allocation

**Files:** create `scripts/qbank/coverage_priority.py`, `tests/test_coverage_priority.py`.

- [ ] Step 1: Failing tests — depth-derived classes reproduce 488/424/263/332; reachability promotion promotes
      15 addresses and leaves every mapped objective with a CORE address; non-ELIGIBLE addresses get a zero
      opportunity budget; no minimum-shaped field is emitted.
- [ ] Step 2: Implement derivation, promotion, and `priority_class_basis`.

### Task 5: Question-opportunity model and safe-yield lifecycle

**Files:** create `scripts/qbank/question_opportunity.py`,
`schemas/curriculum-opportunity-plan.schema.json`, `tests/test_question_opportunity.py`.

- [ ] Step 1: Failing tests — deterministic id; existence rule refuses a decision outside the frozen declared
      list; budget is an upper bound with no deficit anywhere; unused slot is valid; illegal lifecycle transition
      rejected; `NO_SAFE_ITEM` reopens only on a new input; one realization-level retry only.
- [ ] Step 2: Implement identity, lifecycle, budget, fail-closed reasons and the anti-thrash rule.

### Task 6: Marginal educational value

**Files:** create `scripts/qbank/marginal_educational_value.py`, `tests/test_marginal_educational_value.py`.

- [ ] Step 1: Failing tests — demographic-only change is `REDUNDANT`; a context change that alters the answer is
      novel; a synonym competitor swap is not `NOVEL_CONTRAST`; the adjudicator input carries no candidate marker.
- [ ] Step 2: Implement the five verdicts over structured tuples, pre- and post-generation.

### Task 7: Profile-aware contrast retrieval

**Files:** create `scripts/qbank/profile_contrast_retrieval.py`,
`research/qgen/generalization/competitive_contrast_seed_enrichment_r4.json`,
`tests/test_profile_contrast_retrieval.py`.

- [ ] Step 1: Failing tests — retrieval is a deterministic index lookup; generic medical similarity alone does not
      qualify; seed strength is a tie-break not a gate; fewer than three survivors fails closed.
- [ ] Step 2: Implement the index, the ADM-1/ADM-3 filter and near-miss ranking. Enrichment is additive and frozen;
      the curated pack is not rebuilt.

### Task 8: Coverage and gap reporting

**Files:** create `scripts/qbank/coverage_gap_report.py`,
`schemas/coverage-and-yield-report.schema.json`, `tests/test_coverage_gap_report.py`.

- [ ] Step 1: Failing tests — `NARROW_TOPIC` vs `PIPELINE_GAP` separation; an address with no declared decisions
      reads `DECISIONS_NOT_DECLARED`; the report carries no target column; the five standing alarms fire.
- [ ] Step 2: Implement rows, rollups, diagnosis and alarms.

### Task 9: Safe-yield accounting and the restated gates

**Files:** create `scripts/qbank/safe_yield_gates.py`, `tests/test_safe_yield_gates.py`.

- [ ] Step 1: Failing tests — SAFE_YIELD excludes repaired, redundant and uninformative-gate acceptances; a
      constant gate family is `GATE_UNINFORMATIVE`; `SAFE_YIELD = 0` fails a gate; fail-closed concentration
      above 60% alarms; the six stop rules.
- [ ] Step 2: Implement accounting, verdict-variance monitoring, stop rules and gate evaluation for G0-G4.

### Task 10: G0 frozen R4 replay

**Files:** create `research/qgen/g0/r4_role_blind_labels.json`,
`research/qgen/g0/r4_demanded_response_classes.json`, `research/qgen/g0/r4_stem_action_signatures.json`,
`scripts/qbank/g0_replay.py`, `reports/qgen_g0_r4_admissibility_replay.json`.

- [ ] Step 1: Author the role-blind label pool keyed by normalised option-text hash, carrying no role, no key
      marker and no item id, in a single flat pool.
- [ ] Step 2: Author demanded response classes keyed by hash of lead-in plus stem, carrying no option text.
- [ ] Step 3: Run the replay. Require `FAILED_R4_REJECTED = 8/8` and `PASSED_R4_ACCEPTED = 7/7`.
- [ ] Step 4: Prove generality — assert no item id or R4 clinical string appears in any production module, assert
      identical option texts carry identical labels, and record which rule fired for each rejection.

### Task 11: G1 cross-profile safe-yield micro pilot (conditional on a perfect G0)

**Files:** create `research/qgen/safe_yield/g1_micro_pilot.opportunities.json`, the wave artifacts, and
`reports/qgen_g1_safe_yield_micro_pilot.json`.

- [ ] Step 1: Open a bounded pool of opportunities across the six profiles where canonical scope and evidence
      exist. No target count.
- [ ] Step 2: Drive every opportunity to a terminal state. One retry only, realization-level only.
- [ ] Step 3: Fresh independent verification of every ACCEPTED item, no access to the construction record.
- [ ] Step 4: Report attempted / accepted / no-safe-item / rejected / redundant with coverage by discipline,
      priority, learner decision and item archetype.

### Task 12: Full suite and checkpoint

- [ ] Step 1: Run the full canonical suite once after the final production-code state; require 0 failures.
- [ ] Step 2: Reconcile the generated source-research checkpoint side effect per `AGENTS.md`.
- [ ] Step 3: Update `QGEN_ARCHITECTURE_RESUME` in `MEMORY.md` and commit.
