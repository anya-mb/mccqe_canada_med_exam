# MCCQE project

<!-- SOURCE_RESEARCH_RESUME:START -->
## Current phase

- Current phase: scaled current-Canadian source-packet research.
- Source-packet planning is complete and frozen (`SOURCE_PACKET_PLAN = PASS`).
- Total planned source packets: 1,524.
- Source packets READY: 90.
- Source packets PENDING: 1,434.
- Source packets BLOCKED: 0.
- Source packets INCOMPLETE: 0.
- Total research batches: 159.
- Research batches complete: 10.
- Research batches pending: 149.
- Source documents: 75.
- Generation jobs total: 220.
- Generation jobs SOURCE_READY: 11.
- Generation jobs PENDING: 209.
- Generation jobs BLOCKED: 0.
- Generation queue jobs: 11.
- Worker states: `SRB-114` = INTEGRATED; `SRB-117` = INTEGRATED.
- Canonical checkpoint: current Git HEAD.
- Audited coordinator input commit: `ebceb0d435fabc5b2b67c35c8d14452aa1de020a`.
- Current next action: `PLAN_SOURCE_READY_GENERATION`.

## Frozen layers

- Scope, MCC mapping, ownership, competency-component ownership, discipline routing, question planning, and question-bank targets are complete and frozen.
- Do not reopen a frozen layer unless explicitly authorized or a concrete validator/audit failure requires repair.

## Canonical question-bank target

- Final study-bank target: 6,086 questions.
- MED = 1,086.
- PED = 1,000.
- OBGYN = 1,000.
- SURG = 1,000.
- PSY = 1,000.
- PHELO = 1,000.
- MED exactly equals its effective minimum; do not reduce MED minima merely to restore a 1,000-question MED target.
- The separate 230-question MCCQE simulation is not part of the 6,086-question study bank.

## Blocker and next step

- No upstream blocker remains. Continue research one bounded canonical wave at a time.
- NEXT_STEP = `PLAN_SOURCE_READY_GENERATION`
<!-- SOURCE_RESEARCH_RESUME:END -->

<!-- QGEN_ARCHITECTURE_RESUME:START -->
## Question-generation architecture resume state

This section is maintained by hand and sits outside the generated source-research resume block, which
`scripts/qbank/source_research_checkpoint.py` rewrites from canonical artifacts on every suite run.

- Reviewer calibration (`reports/qgen_reviewer_calibration_v2.json`) is still the first thing to read, and its rule
  still holds: **compare defect counts, not pass rates**. Raw pass rates of 9/10 (Cardiology), 7/15 (baseline),
  1/14 (r2), 8/13 (r3) and 7/15 (r4) are not comparable with one another, and r3 and r4 were reviewed by different
  fresh reviewers, so reviewer variance cannot be excluded either.
- `RATIONALE_FATAL_STANDARD_DEFINED = YES`, in `chapter_staged_generation.validate_calibrated_rationale_assessment`.
  Four fatal criteria; register and expansiveness are enhancement classes that never reject an item.
- Second bounded general repair: IMPLEMENTED as staged schema 1.4 (`STAGE_SEQUENCE_V5`), the
  `SEMANTIC_ITEM_ACCEPTANCE_V2` layer, unchanged by this wave and not redesigned.
- Numeric audit of the single r3 numeric defect: `NUMERIC_ERROR_ROOT_CAUSE = BAD_STRUCTURED_INPUT_UNGROUNDED_SCORE_
  COMPONENT`. The gate recomputed a stated Alvarado score from declared components that summed correctly while one
  component contradicted the stem, because nothing checked the components against the stem. The gate should have
  caught it, so one narrow deterministic repair was made: `_validate_scored_component_grounding` requires every
  component of a `SUM_OF_COMPONENTS` formula to cite grounded stem features and to agree with them, a categorical
  criterion matching feature polarity and a measured criterion stating its threshold comparison. Six regression
  tests; focused 121/0, full suite 853/0. Re-running the tightened gate over the frozen r3 artifact rejects
  `QGEN-GEN3-SURG-I02` and nothing else.
- Competitive contrast seed packs: CREATED and FROZEN. Schema `schemas/competitive-contrast-seed-pack.schema.json`,
  data `research/qgen/generalization/competitive_contrast_seed_pack_r4.json`. 82 candidate seeds across the same 15
  targets, drawn from any Toronto Notes chapter. A fresh independent reviewer approved 62 (43 STRONG, 19
  ACCEPTABLE) and rejected 20, overturning the author on eight. Every target cleared three approved competitors, so
  `FAIL_CLOSED_INSUFFICIENT_COMPETITIVE_SEEDS = 0`. Three sources and 47 claims were added to the evidence packet.
- Controlled retest `cross_discipline_generalization_15_r4`: all 15 targets built, all 15 valid under the production
  gates, including the two targets that recorded `FAIL_CLOSED_NO_VALID_CONTRAST_SET` in r2 and r3. Fresh independent
  verification under the calibrated rubric passed 7/15: PED 3/3, OBGYN 0/3, SURG 1/3, PSY 1/3, PHELO 2/3. The
  verifier reached the keyed answer on all 15.
- `SEED_HYPOTHESIS = PARTIALLY_SUPPORTED`. Supply was the constraint it was claimed to be, and lifting it removed
  every fail-closed outcome and cleared one whole discipline. It did not raise the score, because the binding
  constraint moved rather than lifted. Defects against r3: terminal exclusions 1 to 0, rationale fatal 0 to 0, but
  weak distractors 2 to 5, option cues 2 to 4, factual 0 to 1 and unsupported 0 to 1.
- Four surviving modes, all at selection and realization time rather than acquisition time.
  `LONE_KEY_OPTION_CATEGORY` recurred in SURG, PSY and PHELO even though every seed passed a seed-stage
  semantic-category review, because that review judges one competitor against the target's abstract lead-in
  dimension before the other two options and the stem exist. `SEVERITY_OR_CATEGORY_MISMATCHED_DISTRACTOR` survived
  once per failing item in OBGYN, SURG and PSY. **Corrected 2026-09-03 against
  `research/qgen/generalization/competitive_contrast_seed_pack_r4.json`:** these were *not* in each case seeds
  approved as ACCEPTABLE rather than STRONG. Of the six defective distractors, five were independently reviewed
  STRONG (`SEED-OB-T02-MILK-CULTURE`, `SEED-SURG-T03-NONOP`, `SEED-PSY-T02-RISK-SCALE`, `SEED-PSY-T02-START-MED`,
  `SEED-PHELO-T02-AUTHORITY`); only `SEED-OB-T01-GALACTOCELE` was ACCEPTABLE. Seed strength does not predict
  realized failure, and restricting retrieval to STRONG seeds would have prevented one of eight failures. The
  defect is created at assembly against a realized stem, where no seed reviewer can see it.
  `STEM_ENACTED_DISTRACTORS` (OBGYN-I03): every wrong practice was named in the stem as something the patient is
  already doing, leaving the key as the only option not pre-enacted. `PROPAGATED_SOURCE_ERROR` (SURG-I01 **and PSY-I03**):
  McBurney's point was written as 1.5 to 2 cm, faithfully quoting a unit error in the Canadian source, where the
  accepted figure is 1.5 to 2 inches. Faithful citation is not factual correctness, and no gate checks a quoted
  figure against the anatomy or units it describes. **Corrected 2026-09-03 against
  `research/qgen/generalization/cross_discipline_generalization_15_r4.evidence.json`:** PSY-I03's
  `UNSUPPORTED_CLAIM` did not originate in rationale writing. The disputed severity band originates in the
  evidence-packet claim `CLM-R4-PSY-EXERCISE`, whose statement reads "a first-line monotherapy for mild depression
  and a second-line adjunctive treatment for moderate severity illness"; the rebuttal quoted the packet
  accurately. Like `CLM-R4-SURG-PRESENTATION`, that claim carries `verification_status: VERIFIED_COMPLETE`. Both
  defects share the same factual/evidence-source failure class: `VERIFIED_COMPLETE` asserts fidelity of
  transcription and is being read as truth.
- `RECOMMENDED_ARCHITECTURE_ACTION = DO_NOT_SCALE`. A factual error reached a candidate-facing stem, an unsupported
  discriminator narrowed a guideline severity band and evidence entailment failed, against success criteria that
  required zero of each. No scaling is warranted while the factual-safety invariant is broken. The secondary
  finding, that the failure locus has moved to option-set selection and realization and clusters by discipline,
  makes discipline-specific generation profiles the next candidate to test, but it was not implemented here and no
  third universal distractor patch was written. Retest items are recorded as reviewed, not repaired; do not repair
  them to raise the score.
- Discipline-profile and fact-safety design: AUTHORED, design-only, in
  `docs/superpowers/specs/2026-09-03-discipline-profile-qgen-and-fact-safety-design.md`. Recommended architecture
  `COMMON_CORE_PLUS_DISCIPLINE_PROFILES`, with global critical-fact adjudication, risk-based fact escalation,
  required option-set archetypes and profile-aware contrast retrieval. No production code was written and no
  questions were generated.
- Part II of that spec (coverage-first safe-yield amendment, 2026-09-03) retires the fixed 6,086-question output
  as a mandatory production goal and restates scale gates G1-G4 on quality, safety, coverage, yield and
  redundancy; G0 is unchanged and remains the falsification test. **User-approved 2026-09-03 at commit
  `c406053`.** The 6,086 allocation artifacts (`research/scope/question_bank_targets.json`,
  `research/scope/final_question_allocation.json`) are preserved byte-identical and reread as a curriculum-density
  plan. `AGENTS.md` still states 6,086 as a production commitment and has not been amended, so the repository
  holds two readings of that number; amending it is a separate authorisation (spec §28 item 8).
- Safe-yield implementation: COMPLETE, at commit `2475b1125649b75340f8b788174d48b67ec9348d`. Eleven modules and data layers:
  `option_set_admissibility` (eight archetypes, closed response-class and nominal-parity vocabularies, role-blind
  labels, ADM-1..ADM-5 as arithmetic), `qgen_profiles` (six validated profiles as data, anti-hard-coding invariant
  checked against the canonical study-unit titles, quota-shaped-field validator), `critical_fact_adjudication`
  (fourteen fact classes, Levels 0-3, the §4.3 sanity checks, transcription/fact status split, numeric assertion
  enumeration), `coverage_priority`, `question_opportunity`, `marginal_educational_value`,
  `profile_contrast_retrieval`, `coverage_gap_report`, `safe_yield_gates`, `safe_yield_wave`, `g0_replay`. One
  common-core enum extension only: four PHELO values added to `DECISION_GRANULARITIES`, forced by two observed
  `OTHER`s. Focused 107/0; full suite 954/0. Re-verified at that commit with a clean working tree on 2026-09-04:
  the six safe-yield test modules, including `tests/test_profile_contrast_retrieval.py`, run 104/0, so no production
  code changed after the full-suite run and the suite was not rerun.
- Priority model reproduces the spec's arithmetic exactly from the frozen allocation: CORE 488, IMPORTANT 424,
  SUPPORTING 263, NOT_IN_SCOPE 332; 16 MCC objectives have no CORE address and 3 are reachable only through
  SUPPORTING; the reachability promotion promotes 15 addresses and raises CORE to 503, after which every mapped
  objective is reachable from CORE.
- `G0_RESULT = PASS`, in `reports/qgen_g0_r4_admissibility_replay.json`. Replaying critical-fact adjudication plus
  ADM-1..ADM-5 over the frozen R4 cohort rejects **8 of 8** independently failed items and accepts **7 of 7**
  independently passed items, with zero false acceptances and zero false rejections. Attribution matches the
  design's own predictions per item: OBGYN-I01 and I02 and SURG-I03 on ADM-1, OBGYN-I03 on ADM-4, SURG-I01 on
  ADM-2 plus the fact layer, PSY-I02 on ADM-1 and ADM-2, PSY-I03 on the fact layer, PHELO-I02 on ADM-1 and ADM-5.
  ADM-3 is constant PASS across the cohort, which is expected: no R4 failure is attributed to explicit stem
  negation as its earliest layer. **Stated residual risk:** the role-blind labels and demanded response classes
  were authored in the same session that ran the replay, by a party that had read the R4 verdicts. Three
  structural bounds apply and are asserted by tests - labels are choices among closed enumerations, no artifact
  can express a role, a key or an item identity, and no production module contains an R4 item id or any replayed
  option text.
- `G1_RESULT = PASS`, in `reports/qgen_g1_safe_yield_micro_pilot_execution.json`. Eleven opportunities across six
  profiles: **5 ACCEPTED, 3 NO_SAFE_ITEM, 2 REJECTED, 1 REDUNDANT**. The three fail-closed outcomes carry three
  different reasons (erroneous source fact, unresolved critical fact, incoherent option-set archetype), so no
  reason class exceeds 60%. The deliberate redundancy probe was rejected pre-generation. All five ADM positive
  controls fired, so no gate family returned a constant verdict. Fresh independent verification in an isolated
  context reached the keyed answer on 7 of 7 and passed 5: `FACTUAL_ERRORS`, `NUMERIC_ERRORS`,
  `UNSUPPORTED_CLAIMS`, `AMBIGUOUS_BEST_ANSWERS` all 0 in accepted items, `EVIDENCE_ENTAILMENT` PASS,
  `LONE_KEY_OPTION_CATEGORY` 0.
- **The G1 finding that matters more than the yield:** both rejections are the same mode, and it is one no rule in
  the approved design covers - an option carrying no positive anchor in the stem. A biomarker wait against a
  diagnostic ST-elevation tracing, and a restart of oxygen against a child who has held room-air saturations for a
  day, both belong to the demanded response class, are not lone categories, are not defeated by a planted
  negation, do not restate an enacted practice, and do not break format parity. Call it
  `COMPETITOR_WITHOUT_STEM_ANCHOR`. It is the surviving `WEAK_DISTRACTOR` mode and it is the first thing a G2
  design should address. Both items are recorded as reviewed, not repaired: a weak distractor is an option-set
  selection failure, so the one-retry rule refused a retry.
- Two G1 coverage alarms fired correctly and are open: MCC objective `27-3` has no accepted item, and CORE
  learner decisions `LD-C21-02` and `LD-P147-04` were attempted and remain uncovered. `reports/qbank_coverage_and_yield.json`
  diagnoses SU-OB-54 and SU-PH-07 `NARROW_TOPIC` and the other four `PIPELINE_GAP`, on the decisions the wave
  attempted rather than on counts.
- Not done, and not claimed: the one-time enrichment pass over the 82-seed curated contrast pack was **not**
  performed. `profile_contrast_retrieval` is implemented and unit-tested against synthetic inputs, but it has not
  been run over the curated library, and the G1 wave used directly authored option sets plus the frozen
  `defeating_stem_feature_ids` field rather than parsed `condition_predicates`. The 21-stage
  `STAGE_SEQUENCE_V5` successor is not implemented as a staged-item validator; `chapter_staged_generation` is
  unchanged apart from the granularity enum.
- `RECOMMENDED_ARCHITECTURE_ACTION` is upgraded from `DO_NOT_SCALE` to `DO_NOT_SCALE_PENDING_USER_REVIEW_OF_G1`.
  G1 passed and the factual-safety invariant held in accepted items, but G2 has not run and the design has one
  known uncovered failure mode. Do not start 10-item pilots or production waves without explicit authorisation.
- G1 final safe-yield accounting, one terminal state per opportunity, from
  `reports/qgen_g1_safe_yield_micro_pilot_execution.json`: 11 attempted, 7 generated and independently reviewed,
  **5 ACCEPTED, 2 REJECTED, 3 NO_SAFE_ITEM, 1 REDUNDANT**. Both rejections carry the single reason
  `WEAK_DISTRACTOR` (`COMPETITOR_WITHOUT_STEM_ANCHOR`) and neither is retryable, because an option-set selection
  failure is out of scope for the one-retry rule; they stay REJECTED and are not regenerated. Rejected-item
  defects are not aggregated into the accepted-item safety counters, which are all zero: factual 0, numeric 0,
  unsupported claims 0, ambiguous best answers 0, material redundancy 0, with `EVIDENCE_ENTAILMENT` PASS and
  `independent_context` PASS. Low accepted yield is a safe-yield outcome, not a coverage failure: the three
  NO_SAFE_ITEM decisions are recorded as legitimately fail-closed rather than uncovered, so the genuinely
  uncovered CORE population is 2 learner decisions (`LD-C21-02`, `LD-P147-04`) plus MCC objective `27-3`.
- G1 is superseded as the resume point by G2 below; the G1 accounting above stands unchanged.
- **G2 profile-aware retrieval pilot: `G2_RESULT = MIXED`**, in `reports/qgen_g2_profile_aware_retrieval_execution.json`.
  `PROFILE_AWARE_CONTRAST_RETRIEVAL_EXERCISED_END_TO_END = YES`: the component G1 left untested now runs
  inside the wave, against the curated library, for every opportunity. The missing one-time enrichment over the
  82-seed pack was performed (`competitive_contrast_seed_pack_r4.enrichment.json`, 62 approved seeds tagged; the
  20 the R4 reviewer rejected are deliberately left unenriched and so unreachable), joined to a frozen canonical
  stem-feature vocabulary (`g2_stem_feature_vocabulary.json`, 102 features) in which a seed states the conditions
  under which it would be correct and a realized stem states which of them hold.
- G2 accounting, one terminal state per opportunity, 30 attempted across six profiles: **4 ACCEPTED, 13 REJECTED,
  12 NO_SAFE_ITEM, 1 REDUNDANT**. Accepted: `G2-MED-04`, `G2-MED-05`, `G2-SURG-02`, `G2-PHELO-01`. Accepted-item
  invariants are all zero - factual 0, numeric 0, unsupported claims 0, ambiguous best answers 0, critical-fact
  safety 0, material redundancy 0 - with `EVIDENCE_ENTAILMENT` PASS over accepted items and verdict variance PASS.
  Twelve fail-closed outcomes carry four different reasons, none above 33%, and all five admissibility positive
  controls fired. The deliberate redundancy control `G2-PSY-06` was refused before generation.
- **`PROFILES_VALIDATED = 0/6`; all six are `INSUFFICIENT_YIELD`.** MEDICINE 5 attempted / 2 accepted, PEDIATRICS
  5/0, OBGYN 5/0, SURGERY 4/1, PSYCHIATRY 6/0, PHELO 5/1. SURGERY carries four rather than five opportunities
  because SU-GS-76's frozen curriculum density is five and one is already occupied by an accepted G1 item; that
  bound is reported rather than worked around. The encoded `evaluate_gate("G2")` returns FAIL on
  `CORE_DECISION_NEITHER_ACCEPTED_NOR_FAIL_CLOSED`, which is the coverage criterion and not a safety one.
- Three verifiers, working blind before seeing any key, reached the keyed answer on every item they judged in the
  MEDICINE and PEDIATRICS group (7 of 7), so no rejection in this wave is a keying error. Rejections are
  realization defects, and they cluster.
- **The four repeated realization defects are the G2 result that matters**, and none is a retrieval-supply problem:
  - `COMPETITOR_WITHOUT_STEM_ANCHOR` (MED-01, PED-01, PED-02, PSY-01; three profiles). This is G1's surviving mode
    and G2 supplies its cause. A seed's frozen correctness condition names the stem feature under which it would
    be right, so the natural way to keep the key unique is to report that feature *absent* - which removes the
    positive pull the competitor needed. ADM-3 cannot see it: it catches only a negation defeating exactly one
    competitor while grounding nothing in the key, so a stem that negates *every* competitor passes ADM-3 and
    still yields an anchorless set.
  - `KEY_DISTRACTOR_REGISTER_ASYMMETRY` (MED-01, MED-03, PED-01, PED-02, PED-03). Created by the provenance rule
    itself: distractor text is locked to the curated concept string so it cannot be authored freehand, while the
    key is written fresh, so the key differs in grammatical form, hedging and length from every distractor. ADM-5
    measures numerals and paired quantities only and does not see it.
  - `RATIONALE_CLAIM_OUTSIDE_THE_ITEM_EVIDENCE_SET` (PED-02, PSY-01, PSY-03, PSY-04, OBGYN-02). A rationale
    asserts something present in the packet but outside the claim set the item declared. The critical-fact layer
    adjudicates declared claims; nothing checks that a rationale stays inside them.
  - `OPTION_NESTING_BETWEEN_KEY_AND_A_RETRIEVED_COMPETITOR` (PSY-04). Retrieval returned a competitor that
    properly contains the key. It excludes a competitor whose conditions are fully satisfied, which catches a
    second key, and has no test for a competitor that subsumes the key.
- One further defect reached a rejected item and was caught only by independent verification: `G2-SURG-03`
  inverted a source figure, writing "53 per cent of patients avoided appendectomy" where `CLM-R2-SURG-NONOP`
  says 53% *crossed over to surgery*. Numeric assertions are enumerated but nothing checks a quoted figure's
  direction against the claim's meaning. Same family as R4's McBurney unit error.
- Retrieval itself worked and its limits are now measured. The index keys on discipline x item archetype x
  option-set archetype and **not on the learner decision**, so seeds curated for one decision are retrieved for
  any other sharing that triple; 22 of 28 semantic-admissibility refusals are that one cause
  (`SA_1_DECISION_GRANULARITY_MATCH`), in PED-04, OBGYN-04, PHELO-04, MED-03 and MED-05. Retrieval-failure
  classification over the twelve fail-closed opportunities: `NO_RELEVANT_SEED` 4, `WRONG_DECISION_GRANULARITY` 3,
  `OTHER` 3 (two nominal-parity, one realization-parity), `CONTEXTUALLY_IMPLAUSIBLE` 1, `INSUFFICIENT_EVIDENCE` 1.
  `WRONG_OPTION_ARCHETYPE` never fired, which is expected: the index filters on it.
- A separate, concrete consequence of provenance locking: `G2-PED-05` failed ADM-5 as
  `SOLE_NUMERAL_BEARING_OPTION` because the curated concept string is "Nebulized 3% hypertonic saline" and the
  provenance rule forbids rewording it at realization. Curated concept strings are not realization-parity safe.
- Targeted enrichment was bounded and independently reviewed, and the reviewer pushed back. Twenty-three seeds
  were authored only where retrieval actually returned fewer than three;
  `reports/qgen_g2_targeted_seed_independent_review.json` records **19 approved, 4 rejected**, including one
  where the author mis-cited `CLM-ACS-REPERFUSION-NO-DELAY-01` and one whose load-bearing discriminator appeared
  in neither cited claim. Those rejections stand and cost items: `G2-SURG-01` and `G2-PSY-02` fail closed as a
  direct result. Seeds live in `competitive_contrast_seed_pack_g2_targeted.json` (four MEDICINE targets, schema
  valid) and `competitive_contrast_seed_pack_g2_extensions.json` (five one- or two-seed top-ups, deliberately not
  forced into the pack schema, whose four-candidate minimum is real acquisition discipline and was not weakened).
  The curated 82-seed pack is byte-identical.
- Production code changed, under TDD, for two genuine defects and one integration. `safe_yield_wave` now takes an
  optional `contrast_library`, builds one index across several packs, runs profile-aware retrieval **before**
  realization, refuses an opportunity that cannot raise three admissible competitors, feeds retrieved
  correctness predicates into ADM-3 so it can fire on a real item for the first time, and raises rather than
  fails closed when an item carries a distractor retrieval never produced. The stem feature map moved to the
  wave plan, because retrieval and adjudication must run against the same stem. Six new tests in
  `tests/test_profile_retrieval_wave.py`; the G1 wave is unchanged and its recorded outcome still holds.
- Coverage: `reports/qgen_g2_coverage_and_yield.json`. **`LD-C21-02` is now covered** - the CORE decision G1
  rejected was accepted here as `G2-MED-04`. `LD-P147-04` was attempted again and is recorded as legitimately
  fail-closed rather than uncovered. **MCC objective `27-3` still has no accepted item**, and the standing alarm
  now names five CORE objectives with none: `116`, `27-3`, `3-1`, `59-1`, `74`.
- `RECOMMENDED_ARCHITECTURE_ACTION` stays `DO_NOT_SCALE`. Accepted items are safe and retrieval demonstrably
  works end to end, but no profile validated and four realization defects recur across profiles, three of them
  invisible to every automated gate. **The MIXED/FAIL boundary is a user judgement**: G2_MIXED is met as written
  (accepted questions safe; multiple profiles with insufficient yield), and the second G2_FAIL limb - "one
  repeated architecture-wide retrieval/realization defect remains" - is arguably met by
  `COMPETITOR_WITHOUT_STEM_ANCHOR`, which G1 flagged, which G2 reproduced in three profiles, and which no gate
  covers. Do not start G3, cross-profile scale waves or bank production.
- QGEN_NEXT_STEP = `USER_REVIEW_G2_PROFILE_AWARE_RETRIEVAL`
<!-- QGEN_ARCHITECTURE_RESUME:END -->

## Research-level policy

- MEDIUM is the default for LOW/MODERATE-freshness, diagnosis/recognition, non-jurisdiction-sensitive packets with straightforward Canadian guidance.
- HIGH is used for HIGH-freshness, medications/treatment, screening, immunization, pregnancy, emergency care, legal/jurisdiction-sensitive material, conflicting guidance, uncertain Canadian applicability, or international-fallback adjudication.

## Source-research protection rules

- Previously READY packets are immutable unless a concrete validated defect is found.
- Frozen upstream curriculum, allocation, manifests, and source-plan layers must not change during source research.
- Research one bounded canonical wave at a time.
- Do not generate MCQs until required source packets are READY.

## Resume artifacts

Before continuing, read:

1. `MEMORY.md`
2. `research/scope/question_bank_targets.json`
3. `reports/final_effective_ownership_audit.json`
4. the canonical Medical Imaging allocation-routing artifact
5. the latest final-question-allocation preflight/audit
6. `reports/source_packet_research_progress.json`

Canonical JSON artifacts and validator output override `MEMORY.md` if they conflict.
