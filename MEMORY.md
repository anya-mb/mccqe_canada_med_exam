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
- Audited coordinator input commit: `b0cd30f36d307e2881d6b85d189dded8cde11518`.
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
- **G2 completion pass (2026-09-04), resuming from `80ddd5d`.** The G2 wave, its 29 frozen scenarios, the
  targeted seed pack and its independent review, and the four accepted items were already complete at that
  commit and were not redone. One gate was genuinely incomplete and is now closed: **semantic contrast
  admissibility ran outside the production path**. The frozen judgements in
  `g2_profile_pilot.semantic_admissibility.json` (SA-1 decision-granularity match, SA-2 stem anchor, SA-3
  contextual plausibility) were applied by the wave author when picking distractors, so the production wave
  checked only that a realized distractor had been *retrieved*, never that it had survived judgement. A
  retrieved-but-refused competitor could therefore have been realized, and four opportunities reported
  `FAIL_CLOSED_UNINSTANTIABLE_REASONING` - the absence of an authored item - when the real cause was a semantic
  shortfall.
- Production change, under TDD, in `safe_yield_wave` and `question_opportunity`. `run_safe_yield_wave` now takes
  `semantic_admissibility_relative_path` and **refuses to run at all with a contrast library and without it**,
  because retrieval keys on discipline x item archetype x option-set archetype and not on the learner decision.
  The stage requires every retrieved competitor to be judged in rank order, refuses a judgement over a competitor
  retrieval never returned, **recomputes the selection rule** (the first three ranked competitors passing all
  three criteria) rather than trusting the artifact's declared selection, fails closed as
  `FAIL_CLOSED_INSUFFICIENT_SEMANTICALLY_ADMISSIBLE_COMPETITORS` when fewer than three survive, and binds the
  freehand-distractor guard to the *selected* set rather than the retrieved set. One common-core enum extension:
  that reason, reopening on `NEW_SEEDS_OR_A_PROFILE_VOCABULARY_ENTRY`.
- Retrieval provenance is now persisted per opportunity and is sufficient to prove a realized distractor came
  through the path: query dimensions (profile, item archetype, option-set archetype, demanded response class,
  learner decision, ranking preference, stem feature ids), every candidate with its **rank**, source pack and
  `ORIGINAL_CURATED`/`TARGETED_NEW` provenance, each filter verdict (ADM-1, ADM-3, SA-1..SA-3), and the selected
  competitor seed ids. Provenance classes are **declared by the caller**, not inferred from a pack id. The
  execution report's `results` and `retrieval_provenance` block are now the wave's own output and a test
  reproduces them from a fresh run.
- **No terminal state moved.** G2 accounting is unchanged: 30 attempted, **4 ACCEPTED, 13 REJECTED, 12
  NO_SAFE_ITEM, 1 REDUNDANT**; accepted-item invariants all zero; all six profiles `INSUFFICIENT_YIELD`;
  `G2_RESULT = MIXED`. What changed is naming and enforcement: `FAIL_CLOSED_UNINSTANTIABLE_REASONING` 4 -> 0 and
  `FAIL_CLOSED_INSUFFICIENT_SEMANTICALLY_ADMISSIBLE_COMPETITORS` 0 -> 4 (`G2-OBGYN-01`, `G2-OBGYN-04`,
  `G2-PED-04`, `G2-PHELO-04`), and a ninth gate family `SEMANTIC_CONTRAST_ADMISSIBILITY` returns both verdicts.
  The four accepted items are byte-identical, so their fresh independent verification stands and was not rerun.
- Retrieval provenance totals from the production run: 28 retrievals, 126 candidates indexed, 111 ranked after
  admissibility, 25 candidate sets semantically judged, 81 competitors admitted, 3 sets short at retrieval and 4
  short after semantic admissibility. Distinct selected competitor seeds split 42 `ORIGINAL_CURATED` / 16 `TARGETED_NEW`.
  Targeted seeds: 23 authored, **19 approved (16 STRONG, 3 ACCEPTABLE), 4 rejected**; the 4 rejected reach no
  stage of the wave, which is now asserted rather than assumed.
- Tests: 43 focused in `tests/test_profile_retrieval_wave.py` and `tests/test_profile_contrast_retrieval.py`,
  covering all twelve required proofs including the two bypass paths (a freehand distractor and a
  retrieved-but-refused competitor), each run against a **copy of the repository with one artifact mutated**, so
  the guard is proven at the production entry point rather than on a helper. Full canonical suite **993/0** at
  the final production-code state.
- The four repeated realization defects are unchanged and remain the G2 finding. The new stage addresses none of
  them: it fixes where semantic judgement is enforced, not `COMPETITOR_WITHOUT_STEM_ANCHOR`,
  `KEY_DISTRACTOR_REGISTER_ASYMMETRY`, `RATIONALE_CLAIM_OUTSIDE_THE_ITEM_EVIDENCE_SET` or
  `OPTION_NESTING_BETWEEN_KEY_AND_A_RETRIEVED_COMPETITOR`. Note that SA-2 encodes
  `COMPETITOR_WITHOUT_STEM_ANCHOR` as a criterion but the verdicts are authored, so it is enforced consistently
  rather than detected automatically.
- **G2 finalization pass (2026-09-04), verified at `bf3a545`.** Nothing was regenerated: the 29 frozen
  scenarios, the curated 82-seed library, the targeted seed packs, the independent seed review, the 21 authored
  items and the three independent question verifications were all reused as committed. Re-verified fresh at this
  HEAD: focused **43/0** (`tests/test_profile_retrieval_wave.py` 33, `tests/test_profile_contrast_retrieval.py`
  10) and the full canonical suite **993/0**. The curated pack's declared `frozen_sha256` recomputes exactly over
  its `targets`, so the 82-seed library is provably untouched, and every seed pack, scenario, item, semantic-
  admissibility and independent-verification artifact is byte-identical to `80ddd5d`.
- **The report reconciliation is settled; do not "fix" it.** A fresh recomputation of the execution report
  disagrees with the authored per-profile tallies in exactly one metric, and the authored tallies are right.
  Per-profile `candidate_seeds_approved_after_contextual_filter` sums to **83**, while
  `retrieval_provenance.candidates_semantically_admitted` is **81**. The gap is the **2 candidates in the single
  short-at-retrieval set (`QOPP-f475191976ced2f3a0e912d5`, 2 ranked) that were never semantically judged**: the
  per-profile field counts contextual approval across all 28 retrievals, the provenance field counts admissions
  across the 25 sets that reached semantic judgement. Ranked totals agree exactly (111 = 22+17+24+16+21+11, and
  81 ADMITTED + 28 REFUSED + 2 unjudged), as do retrievals (28) and candidates retrieved/indexed (126). Both
  numbers are correct under their own definitions; the provenance block's own note already says its field
  definitions are local to it. Narrowed diff confirmed against `80ddd5d`: 558 added provenance/rank/verdict
  fields, 8 changed values (the 4 fail-closed reason renames and their `reopens_on`) and 1 deleted roll-up key.
  `safe_yield`, `by_profile` counts, `defect_counts_in_accepted`, `coverage_rows`, `terminal_state_by_opportunity`,
  `scope`, `reported` and `admissibility_positive_controls` are unchanged. **No historical metric semantics were
  redefined.**
- Item accounting confirmed from canonical artifacts, not transcript: **21 authored** items in
  `g2_profile_pilot.items.json`, **21** result rows carrying an `admissibility` block, **17** rows carrying a
  realized `item_id` - so 4 failed admissibility after realization. The stale test expectation of 21 realized
  items was corrected to match production rather than production being bent to the test.
- Remaining CORE coverage gaps: 5 CORE MCC objectives with no accepted item (`116`, `27-3`, `3-1`, `59-1`, `74`)
  and 19 uncovered CORE learner decisions. The targeted-enrichment bound is spent: one pass, already used, and no
  further seed round is authorised.
- **G2 safe-yield root-cause diagnosis (2026-09-04), diagnosed at `199696b`.** Diagnosis-only: no production code,
  validator, seed, question, gate or verdict changed. `reports/qgen_g2_safe_yield_root_cause_diagnosis.json`.
  `PRIMARY_BOTTLENECK = STEM_CONTEXT_ALIGNMENT`; the decisive finding is
  `ANCHORING_HAS_A_CEILING_AND_NO_FLOOR` - ADM-3 rejects a competitor whose correctness conditions are *fully*
  satisfied (second-key risk) but nothing requires the stem to give a learner any positive reason to consider the
  competitor at all. Measured: 104 of 111 ranked competitors scored zero on the only machine-readable anchoring
  signal, which was therefore constant in 20 of 26 candidate sets, and `SA_2_STEM_ANCHOR_PRESENT` refused nothing
  in the whole wave because its verdicts are authored rather than computed.
- The diagnosis's control finding, which any fix must respect: the accepted/rejected distinction is **not** seed
  strength, satisfied-condition count or present-to-absent feature ratio, but *how* the stem defeats the
  competitor. Accepted controls: 7 of 12 selected competitors defeated by a positively stated datum requiring an
  inference, only 2 of 12 absent features written as explicit verbal denials. Anchorless rejections: 13 of 18
  defeated by the stem stating the competitor's own precondition absent, 17 of 30 absent features explicit
  denials. `GOOD_DISTRACTOR = LIVE_BUT_INFERIOR`; `BAD_ANCHORLESS_DISTRACTOR = CATEGORICALLY_IMPOSSIBLE`. A
  simplistic "negative finding = bad" rule is therefore wrong and is ruled out.
- Recommended next intervention: `ONE_BOUNDED_STEM_ANCHOR_RETRIEVAL_FIX`. Secondary bottlenecks recorded and
  deliberately not addressed: contrast-library coverage, learner-decision indexing in profile-aware retrieval,
  option realization, evidence-set scoping, and a read-only CORE coverage accounting join defect
  (`build_coverage_row` alarms on two decisions that are already covered).
- **Bounded stem-anchor retrieval fix (2026-09-04), from diagnosis checkpoint `6fe4237`, implemented at
  `9ebee9f`.** Scope held: one bounded fix, no architecture redesign, no new validator family, no new
  contrast seeds, no stem or item rewritten. Every seed pack, enrichment, wave plan, semantic-admissibility
  artifact, item file and the G2 execution report are byte-identical to `199696b`.
- **The invariant, and what it is not.** `STEM_PLAUSIBILITY_ANCHOR_PRESENT`: a retrieved competitor is
  admissible only if at least one of its stem-plausibility anchors is realized PRESENT. Measured first, before
  any code: the floor **cannot** be computed from `condition_predicates`. Every competitor of accepted
  G2-SURG-02, G2-MED-05 and G2-PHELO-01 carries the same correctness signature as every competitor of the
  flagship anchorless rejection G2-MED-01 - zero conditions satisfied, the rest contradicted - so a rule over
  contradiction rejects all four accepted controls. Nor is it the negative-finding rule the diagnosis warned
  against: three of twelve accepted-control competitors are defeated by an explicit verbal denial and stay
  admissible. The missing datum is a second relation - which stem features, PRESENT, give a learner a reason to
  *consider* a competitor, as against the conditions under which it would be *correct*.
- Data layer: `research/qgen/generalization/*.stem_anchors.json`, three additive frozen artifacts over the 81
  already-approved retrievable seeds. Derived by `scripts/qbank/build_stem_anchor_layer.py` under four recorded
  rules - R1 every correctness condition requiring PRESENT is an anchor; R2 a phrase in the seed's own frozen
  prose contributes the vocabulary features it designates; R3 a phrase naming only the option category, the
  decision point or the presenting complaint designates nothing; R4 a seed resting entirely on category
  membership carries an empty anchor set and is admissible against no stem (one seed, `SEED-PED-T03-HYPERTONIC`).
  Every anchor carries its rule and its derivation sentence. Anchors are stem-independent: no opportunity,
  scenario, stem, key, option or G2 verdict is referenced by any derivation.
- Production change, under TDD, in three layers only. `profile_contrast_retrieval` gains `load_seed_stem_anchors`,
  requires the anchor layer to build an index, applies `SAF_1` / `STEM_PLAUSIBILITY_ANCHOR_ABSENT` after ADM-1 and
  ADM-3, adds the `STEM_ANCHOR_STRENGTH` ranking signal and reports the anchor-signal counts. `safe_yield_wave`
  **refuses to run with a contrast library and without the anchor layer**, tolerates a frozen semantic judgement
  over a competitor the floor removed upstream while still refusing one retrieval never returned, and reports a
  declared selection superseded by the floor. `question_opportunity` gains one reason,
  `FAIL_CLOSED_REALIZED_COMPETITOR_LACKS_STEM_ANCHOR`, so an item resting on a floor-refused competitor fails
  closed instead of raising the freehand-distractor construction error. The ADM-3 ceiling is untouched.
- Controls fixture `research/qgen/safe_yield/stem_anchor_invariant_controls.json`, written before the production
  change. Tests: 31 in `tests/test_stem_anchor_floor.py`, 33 in `tests/test_profile_retrieval_wave.py` and 10
  in `tests/test_profile_contrast_retrieval.py`, so **74 focused** across the three modules; full canonical
  suite **1024/0** at the final production-code state. Re-verified at `9ebee9f` with a clean working tree:
  the three focused modules run **74/0**, so no production code changed after the full-suite run and the
  suite was not rerun.
- **Frozen replay:** all four accepted G2 sets keep at least three anchored competitors and all four flagship
  anchorless sets collapse below three. Second-key ceiling preserved exactly:
  `CORRECTNESS_CONDITION_FULLY_SATISFIED` is 8 before and 8 after. Anchor signal, on the same 111-candidate
  population as the baseline: zero **104 -> 64**, positive **7 -> 47**; constant across **20 of 26 sets -> 9 of
  27**. The signal now has real variance and it was not tuned to a target.
- **Controlled G2 retest** (`reports/qgen_g2_stem_anchor_retest_execution.json`), same 30 frozen opportunities,
  same seed library, same semantic judgements, same items: **2 ACCEPTED, 2 REJECTED, 26 NO_SAFE_ITEM, 0
  REDUNDANT**, against a baseline of 4 / 13 / 12 / 1. `COMPETITOR_WITHOUT_STEM_ANCHOR` reaching an authored or
  final item: **6 items and 11 distractors -> 0**; all six named items now end NO_SAFE_ITEM before realization.
  Accepted-item safety unchanged and all zero - factual, numeric, unsupported claims, ambiguous best answers,
  critical-fact safety, material redundancy - reused rather than rerun, because both accepted items are
  byte-identical and no newly realized candidate would become ACCEPTED.
- **Safe yield fell, 4/30 to 2/30, and both losses are analysed rather than explained away.** `G2-SURG-02` is
  *not* a retrieval failure: the corrected path still raises four anchored competitors and selects three, and the
  opportunity fails only because the frozen item was authored on `SEED-SURG-T02-LAPAROSCOPY`, whose own frozen
  rationale says the guideline sends *high*-suspicion patients to laparoscopy while this stem states intermediate
  suspicion. Under the retest rule that no item may be re-authored that is NO_SAFE_ITEM; a fresh authoring pass
  over the same retrieved set would build an item. `G2-MED-05` is a genuine stricter-semantics shortfall: only
  one competitor survives both the floor and SA-1, because discharge home and overnight observation are refused
  against a documented troponin rise and dynamic ST-T changes.
- One control-coverage regression, reported and not worked around: the deliberate redundancy probe `G2-PSY-06`
  was redundant against an item this run no longer accepts, so it is genuinely novel now and fails closed at
  retrieval. `MARGINAL_EDUCATIONAL_VALUE` returns a constant verdict in the retest. The redundancy gate itself is
  unchanged and its G2 result stands.
- **Stated residual risk.** The anchor derivations are authored, by a party that had read the G2 verdicts. Three
  bounds apply and are asserted by tests: every anchor is drawn from the frozen canonical vocabulary of its
  target's anchor study unit, every anchor carries its rule and a derivation sentence quoting the seed's own
  frozen prose, and no anchor row names an opportunity, item, key or option. One independent corroboration
  exists and predates the fix: the G2-MED-04 verifier wrote "Each distractor has a positive stem anchor" and then
  named the PRESENT stem features supplying it, agreeing with the floor on that item.
- `DECISION = STEM_ANCHOR_FIX_VALIDATED_NEXT_CONTRAST_COVERAGE`. The next dominant bottleneck is
  `CONTRAST_LIBRARY_COVERAGE`: 17 of the 19 `FAIL_CLOSED_INSUFFICIENT_ADMISSIBLE_COMPETITORS` are the library
  holding no anchored competitor for the realized stem (2 with no seed indexed at all, 6 with every candidate
  floor-refused, 11 with one or two anchored and short of three). Learner-decision indexing has receded:
  `SA_1_DECISION_GRANULARITY_MATCH` refusals fall from 22 to 5. Option realization, evidence-set scoping and the
  CORE coverage accounting join are unchanged and were deliberately not touched.
- `RECOMMENDED_ARCHITECTURE_ACTION` stays `DO_NOT_SCALE`. No profile validated and safe yield fell.
- **Clinical contrast retrieval milestone (2026-09-04), from design commit `777653a`.** The approved
  design at `docs/superpowers/specs/2026-09-04-mccqe-clinical-contrast-graph-rag-and-difficulty-design.md`
  is implemented as far as its own Phase 3 decision point and stops there, as the design requires.
  Plan: `docs/superpowers/plans/2026-09-04-clinical-contrast-retrieval-implementation.md`. No question
  was generated, no production generation module changed, no frozen artifact moved and
  `LLM_API_CALLS = 0`.
- **Full deterministic Toronto Notes index: IMPLEMENTED.** All 1,595 already-OCR'd pages into
  **14,909 chunks** in 1.8 s, database 36.7 MB, SQLite FTS5 with `porter unicode61 remove_diacritics 2`.
  Structure-aware rather than fixed-token: running header peeled off and its printed page label kept,
  blocks classified HEADING/LIST/PARAGRAPH/NOISE, chunks bounded by page and heading, content-addressed
  chunk ids reproducing exactly on rebuild. Median chunk 212 chars, p95 1,541, max 1,800. The only two
  pages yielding no chunks are exactly the two OCR-quality-flagged cover pages. The database lives under
  gitignored `derived/` and is **never tracked**; `research/tn2025/tn_index_build_manifest.json` carries
  counts, hashes and the tokenizer rationale with no corpus prose.
- **Concept normalization: IMPLEMENTED.** 2,561 concepts / 5,122 aliases / 0 unresolved typings.
  81 curated competitors typed from the closed archetype vocabulary (20 CONDITION, 61 ACTION; all 81
  type cleanly), 102 frozen stem features as FINDING, 2,378 TN discovery topics. Aliases from three
  named rules only. **18 MULTI_MATCH** surface forms remain and all are a curated clinical concept
  colliding with a same-named TN topic; none merges clinically distinct entities.
- **Typed clinical contrast graph: IMPLEMENTED.** 4,275 nodes / 5,916 edges, every one a deterministic
  projection of an already-frozen, already-reviewed artifact — nothing authored here. PLAUSIBILITY_ANCHOR
  153, DEFEATED_BY 100, ANSWERS 81, BELONGS_TO 1,661, CONFUSED_WITH 635, PRESENTS_WITH 3,286.
  All 3,909 Toronto Notes edges are TOPIC_DISCOVERY_SOURCE and none can justify a claim; only the 217
  edges resolving to a dated non-textbook source may. Context fields are NULL throughout because no
  source states them, asserted by test. Answers design open question §15.3: deterministic differential
  parsing yields **623** CONFUSED_WITH edges from only 89 differential-headed chunks, against 628
  clinical-features chunks.
- **`RETRIEVAL_ARCHITECTURE_DECISION = RETRIEVAL_NOT_MAIN_PROBLEM`**, in
  `reports/qgen_clinical_retrieval_benchmark.json` and `.md`. `HYBRID_BENCHMARK_PASS = False`.
  Four arms over the same 30 frozen G2 opportunities, all routed through the *same*
  `retrieve_profile_aware_contrasts`, so the floor and ceiling are one implementation and not four.
  Opportunities reaching three viable competitors: **CURRENT_LIBRARY 10, BM25 0, GRAPH 10, HYBRID 10**.
  Recall 0.4935 / 0.0 / 0.4935 / 0.4935; known-bad returned 0 in every arm; second-key refusals 8 in
  all but BM25; source traceability 1.0. Six of seven pre-committed checks pass; the one that fails is
  the supply criterion the rule was built around.
- **The finding that decides it.** Mean recall of 0.49 is *not* a recall failure. Every frozen reference
  positive missing from arm A was traced to the filter that removed it — **41 SAF_1, 2 ADM_1,
  `NOT_RETRIEVED_AT_ALL = 0`**. Nothing is missed by retrieval in any arm; the gap is the validated
  floor refusing competitors a reviewer had ADMITTED before the floor existed. `BINDING_CONSTRAINT =
  TYPED_ANCHOR_AND_CONDITION_POPULATION`, as the Phase-0 measurement predicted: the 102 stem features
  partition across exactly 6 study units with **zero** cross-unit collisions, so anchor-bearing supply
  is structurally confined to 0.4 % of 1,487 study units, and every typed competitor concept already
  sits in the curated index.
- **The graph is not written off, and its win is named honestly.** Arm C reaches the same 10
  opportunities with **zero** anchor-floor refusals against arm A's 67, because traversal starts at the
  stem's PRESENT anchors and never presents an anchorless candidate to the floor. It also reaches arm
  A's sets by an independent path (inverted PLAUSIBILITY_ANCHOR rather than an archetype lookup), which
  independently corroborates the frozen anchor layer. Both are efficiency/provenance results, not supply.
- `LOCAL_EMBEDDING_TRIGGER_MET = NO`; `LOCAL_EMBEDDINGS = NOT_NEEDED_YET`. The trigger's first limb
  fails outright: nothing is missed, so a denser retriever hands the same competitors to the same floor.
- **Pre-registration is real and committed ahead of results** at `20db2a6`:
  `research/qgen/safe_yield/retrieval_benchmark_reference.json` (83 positives across 29 opportunities,
  67 anchorless + 8 second-key controls) is *derived* from the frozen semantic-admissibility record and
  the retest's own filter verdicts, not authored. A test reproduces it from those inputs, and another
  asserts the pass rule can actually fail.
- **Difficulty infrastructure: IMPLEMENTED**, generation untouched.
  `DIFFICULTY_INTENT_SCHEMA = IMPLEMENTED`, `EMPIRICAL_PSYCHOMETRIC_SCHEMA = IMPLEMENTED`, in
  `scripts/qbank/question_difficulty.py`. Intent and empirical difficulty are separate records that
  cannot carry each other's fields; new items enter BETA with every empirical field null and no minimum
  N is invented. Nine prohibited difficulty sources are refused in a rationale, named or euphemised.
  20/55/25 carries `POLICY_STATUS = INITIAL_LEARNING_DESIGN_POLICY` and
  `DERIVED_FROM_MCC_DISTRIBUTION = False` in the data itself. Validated against the two accepted G2
  items, read not rewritten, with **no difficulty assigned to any item**; that surfaced a real signal —
  G2-PHELO-01's three competitors are all defeated by explicit verbal denials, failing the denial check
  at every level, which shows the checks discriminate.
- **Audits.** `COPYRIGHT_AUDIT = PASS`: all 18 artifacts this milestone created have a longest verbatim
  Toronto Notes run of **0**, and the index database is not tracked.
  `TRACKED_COPYRIGHTED_CORPUS_CONTENT = NO` for this task. Reported and deliberately **not** modified:
  24 pre-existing frozen artifacts carry 22–31 word verbatim runs in free-text rationale fields
  (worst: `research/mcc/objectives_registry.json` 31, `master_scope_crosswalk.json` 25,
  `toc_inventory.json` 22); the frozen-layer rule forbids editing them without authorization, so this is
  raised for a separate decision. Graph quality audit sampled all six discipline profiles: 0 orphan
  edges, 0 missing derivation rules, 0 medically dubious relations to adjudicate because none is
  authored here.
- Performance, all measured on this machine and no dollar figure stated: index build 1.8 s, graph build
  1.2 s, total rebuild 3.0 s, 36.7 MB. Retrieval latency p50/p95 ms — CURRENT_LIBRARY 5.5/9.5,
  BM25 9.9/43.3, GRAPH 5.5/7.2, HYBRID 8.3/12.0. Context packet median 1,770 characters / 102 words for
  GRAPH and HYBRID, 1,737 for the current library. No token count is reported: there is no local
  tokenizer, and characters are not equated with the design's ENGINEERING_ESTIMATE token budget.
- Tests: **113 focused** across the six new modules; full canonical suite **1137/0** at the final
  production state. `qbank build-tn-index`, `qbank build-clinical-graph` and
  `qbank run-retrieval-benchmark` rebuild everything; docs in `docs/clinical-retrieval.md`.
- `PRODUCTION_QUESTION_GENERATOR_CHANGED = NO`. `safe_yield_wave`, `question_opportunity` and
  `profile_contrast_retrieval` are untouched, and `profile_contrast_retrieval` must stay untouched
  because it *is* benchmark arm A. `RECOMMENDED_ARCHITECTURE_ACTION` stays `DO_NOT_SCALE`.
- **Phase-B normalization inventory closed out (2026-09-05).** The milestone's own named deliverable
  `reports/qgen_global_concept_normalization_inventory.json` was missing and is now built by
  `qbank build-normalization-inventory`. It measures the local vocabulary the graph design turns on:
  **183 local source terms** (102 frozen stem features plus 81 curated competitors) across **34** local
  study units, against 2,561 global concepts. `EXACT_LABEL_MATCHES_ACROSS_UNITS = 0`,
  `NORMALIZED_TEXT_MATCHES_ACROSS_UNITS = 0`, `POSSIBLE_ALIAS_MATCHES = 0`,
  `CROSS_UNIT_CANONICAL_CONCEPTS = 0`. The Phase-0 zero-collision finding therefore **widens** rather than
  narrows: it holds over the whole local vocabulary and all 34 units, not just the 102 stem features and
  6 anchor units, which strengthens `BINDING_CONSTRAINT = TYPED_ANCHOR_AND_CONDITION_POPULATION`. The zero
  is measured and a test plants a synthetic duplicate to prove the measurement can report a collision.
- Mapping types over the 183 local terms, one per term: **EXACT 68, NORMALIZED_EXACT 102, ALIAS 0,
  RELATED_BUT_DISTINCT 10, AMBIGUOUS 3, UNRESOLVED 0**. Confidence is 1.0 where a stated rule resolved the
  surface form and 0.0 where the layer fails closed; nothing between the two is invented. The 3 AMBIGUOUS
  are `Pulmonary embolism`, `Acute pericarditis` and `Pelvic inflammatory disease`, each a curated clinical
  concept colliding with a same-named TN discovery topic; all three carry `canonical_concept_id: null`.
- **The refused merges are the report's real content.** Five pairs clear a 0.5 token-Jaccard floor and are
  kept as separate concepts: absolute contraindication to *aspirin* vs to *fibrinolysis* (0.75), depressive
  syndrome due to *hypothyroidism* (SU-E-30) vs due to *anaemia* (SU-H-02) (0.667, the only cross-unit pair
  in the set), *lead-time* vs *length-time* bias (0.5), and two others. The floor is a reporting threshold
  and never a merging rule. This is the Phase-B evidence that string similarity does not prove concept
  identity.
- **Tracked-manifest determinism defect found and fixed.** `tests/test_tn_index.py` wrote the tracked
  `research/tn2025/tn_index_build_manifest.json` from a throwaway tmp index at the *repository* root, so
  every suite run dirtied the working tree and the tracked measured fields described a temporary database.
  Test-side only; no production code changed. Two regression tests added: a manifest write never touches
  the tracked copy, and two independent builds describe themselves identically apart from `build_seconds`
  and `index_bytes`, which are wall clock and file layout by nature.
- The manifest's `index_bytes` 31,932,416 (30.5 MB) and the 36.7 MB figure above are both correct and
  measure different things: the manifest sizes the TN index alone, while `derived/tn_index/tn_index.sqlite3`
  reaches 36.7 MB once the clinical graph is projected into the same database.
- Copyright rescanned 2026-09-05 over 19 artifacts: longest verbatim Toronto Notes run **0** in every one,
  including the new inventory report. `COPYRIGHT_AUDIT = PASS`. The 24 pre-existing frozen artifacts with
  22-31 word runs are unchanged and still raised for a separate decision.
- Tests at this state: focused 24 (`test_clinical_concepts.py`) and 20 (`test_tn_index.py`); full canonical
  suite **1146/0**. `LLM_API_CALLS = 0`, `SEMANTIC_ADJUDICATIONS = 0`: nothing needed adjudication, because
  no cross-unit merge candidate survived the deterministic pass.
- **Continuation 2026-09-05: inventory completeness, reuse and connectivity measured.** The Phase-B
  inventory shipped without the aggregate and provenance blocks its own deliverable spec named, so
  `build_normalization_inventory` now also emits `CONCEPT_TYPES` (ACTION 61, CONDITION 20, FINDING 102),
  `SOURCE_UNIT_COUNTS` (34 units; largest SU-C-21 31, SU-PH-07 28, SU-OB-54 26, SU-P-147 23, SU-GS-76 20,
  SU-PS-12 18), a `global_reuse` block, a `semantic_adjudication` block and a `provenance` block carrying
  the SHA-256 of all **9** vocabulary source artifacts plus an `inventory_content_sha256`. Five new tests,
  RED before GREEN; one plants a shared concept to prove the reuse measurement can report reuse.
- **Cross-unit reuse, measured at three layers — the zero is layer-specific and must not be generalized.**
  Local-term layer: `GLOBAL_CONCEPTS_USED_IN_1_UNIT = 180`, `_2_OR_MORE = 0`, `_3_OR_MORE = 0`,
  `MAX_SOURCE_UNITS_PER_GLOBAL_CONCEPT = 1`, `CROSS_UNIT_CANONICAL_MAPPINGS = 0`. Graph layer: of 196
  typed clinical concept nodes, 183 reach a study unit, **72 reach 2 or more, 10 reach 3 or more, max 6**.
  TN mention layer: 460 concepts are mentioned, **428 in 2 or more study units, max 304**.
  `DIAGNOSED_CAUSE_OF_LOCAL_LAYER_ZERO = PROPOSITIONAL_VOCABULARY_GRANULARITY`, not a normalization
  failure: 137 of the 183 local labels are full clinical propositions of 6+ tokens ("an absolute
  contraindication to aspirin is present"), all 183 normalized labels are distinct, and
  `canonical_concept_id == local_feature_id` for all 180 resolved terms. Two units cannot collide on a
  proposition authored inside one of them. The three terms that *are* reusable entity names — pulmonary
  embolism, acute pericarditis, PID — are exactly the three that fail closed as AMBIGUOUS. **Cross-unit
  reach is supplied by graph edges and TN mentions, never by label identity**, which is why the zero does
  not contradict the graph result.
- **`NORMALIZATION_AUDIT = PASS`.** Over-merging is structurally impossible at this layer: 0 canonical
  concepts are claimed by more than one local term and `POSSIBLE_ALIAS_MATCHES = 0`. Thirteen dangerous
  pairs probed live against the alias index all stay distinct or unresolved: syncope/presyncope,
  dizziness/vertigo, depressed mood/major depressive disorder, chest pain/ACS, troponin/elevated troponin,
  hyper-/hypokalemia, hyper-/hypotonic saline, pre-eclampsia/eclampsia, lead-/length-time bias,
  sepsis/septic shock, asthma/status asthmaticus, screening/diagnosis, anaemia/anemia. All six discipline
  profiles sampled per mapping category. One typing quirk noted, not a defect: `Lead-time bias` types as
  ACTION because the closed archetype rule assigns everything outside DIAGNOSIS_SET to the action family.
- **Graph connectivity measured (not previously recorded).** `GRAPH_NODES = 4,275`, `GRAPH_EDGES = 5,916`,
  `CROSS_UNIT_GRAPH_EDGES = 59` of 185 edges carrying a study unit at both ends, `GRAPH_COMPONENT_COUNT =
  2,265`, `LARGEST_COMPONENT_SIZE = 1,878`, `ISOLATED_NODE_COUNT = 2,223` (1,962 TN topics never mentioned,
  247 study units, 13 findings, 1 learner decision — registered discovery vocabulary spanning the whole
  textbook while the frozen anchor layer covers 6 units). Provenance: **5,916/5,916** edges carry a
  derivation rule, content hash and derivation source; **265/265** claim-eligible edges carry source-claim
  provenance. Every edge without a source claim carries `TOPIC_DISCOVERY_SOURCE`, and all 3,909
  `TORONTO_NOTES` edges are discovery-only — **Toronto Notes is never current clinical authority**, as
  required. 0 edges reference a node absent from `nodes`.
- Nothing about the benchmark was rerun: `reports/qgen_clinical_retrieval_benchmark.json` was already
  complete over all four arms on the frozen 30-opportunity G2 set, and its verdict stands —
  `RETRIEVAL_ARCHITECTURE_DECISION = RETRIEVAL_NOT_MAIN_PROBLEM`, `HYBRID_BENCHMARK_PASS = false` on the
  one pre-committed limb that matters (`raises_opportunities_with_three_viable`), A/C/D all at 10 of 30
  and B at 0, `LOCAL_EMBEDDING_TRIGGER_MET = false` because no reference positive is ever *missed* — every
  one is retrieved and then refused by the anchor floor. Graph's real result is efficiency and provenance:
  0 anchor-floor refusals against arm A's 67, at equal recall and precision.
- Copyright rescanned again after the inventory regeneration: longest verbatim run **0** in the report and
  in both changed source files. `COPYRIGHT_AUDIT = PASS`. Index database still untracked.
- **Why the other 20 of 30 opportunities still fail, classified (2026-09-05).** Every one fails closed as
  `FAIL_CLOSED_INSUFFICIENT_ADMISSIBLE_COMPETITORS`, and the primary cause was read per opportunity off the
  frozen arm-A funnel (`candidates_entering_the_index` -> `indexed_count` -> ADM_1/ADM_3/SAF_1 ->
  `ranked_count`): **`STEM_ANCHOR_FLOOR` 15, `ARCHETYPE_FILTER` 3, `LEARNER_DECISION_FILTER` 2**. The
  causes that would have indicted retrieval are all **zero**: `NO_RELEVANT_SOURCE_CONCEPT` 0,
  `NORMALIZATION_MISS` 0, `BM25_RECALL_MISS` 0, `GRAPH_CONNECTIVITY_MISS` 0, `EVIDENCE_LIMITATION` 0.
  The three `ARCHETYPE_FILTER` cases (G2-MED-02, G2-OBGYN-05, G2-SURG-04) reach `indexed_count = 0`: no
  seed in the library carries the opportunity's discipline profile *and* item archetype *and* option-set
  archetype, so they are a seed-coverage gap, not a retrieval gap. This is the evidence for
  `RETRIEVAL_NOT_MAIN_PROBLEM`: the yield of 10/30 is low because 17 of the 20 shortfalls are a safety or
  admissibility refusal working as designed, and no better retriever can undo a refusal.
- The 72 cross-unit figure is reproducible and its method is now pinned, because it is definition-sensitive:
  seed **all 196** typed clinical concept nodes, traverse `graph_neighbourhood` at **`max_depth=1`**, and
  count distinct `nodes.study_unit_id` among the neighbours. That gives 183 reaching >=1 unit, **72 >=2, 10
  >=3, max 6**. Seeding only the 183 inventory ids gives 60/9/max 3, and depth 2 gives 121/71/max 29;
  neither is the recorded number. Quote the depth and the seed set whenever this figure is repeated.
- **Contrast-first pilot (2026-09-05), design commit `f594838`, spec at
  `docs/superpowers/specs/2026-09-05-contrast-first-difficulty-aware-item-construction-design.md`.**
  The retrieval benchmark's decision stands and was not rerun. Because 15 of the 20 residual failures
  were the anchor floor refusing a competitor an already-frozen stem gave no reason to consider, this
  wave changed **generation order**, not any gate. Five things move upstream -- contrast discovery, the
  stem-independent admission predicate P1-P6, the contrast matrix, and a stem blueprint solved as a
  feature-set constraint problem over the frozen 102-feature study-unit vocabulary. `SAF_1` and `ADM_3`
  cannot exist before a stem and were **not** moved; they run afterwards through
  `retrieve_profile_aware_contrasts`, unchanged, which is also benchmark arm A.
  `PRODUCTION_QUESTION_GENERATOR_CHANGED = NO`, `LLM_API_CALLS = 0`, no frozen artifact moved.
- **Sample frozen before generation** at `f0556d0`: 18 opportunities, selection rule S1 stated before the
  draw (per discipline one from each of the DIAGNOSTIC / INVESTIGATIVE / THERAPEUTIC_OR_DISPOSITION
  families, CORE first, then unused learner decision, then lowest wave label), 16 of 18 CORE, difficulty
  6/6/6 assigned from the nature of each decision and not from what the library supports. The rule
  excludes `G2-MED-04`, one of only two archived stem-first accepts, so the comparison is reported against
  both the 18-subset and the full frozen 30. Metrics were frozen in the same artifact.
- **Funnel: 18 attempted -> 12 valid pre-stem contrast sets -> 10 blueprints -> 10 stems -> 10 post-stem
  3-viable -> 2 ACCEPTED, 8 REJECTED, 8 NO_SAFE_ITEM.** Against the archived stem-first arm on the same 18:
  post-stem 3-viable **7 -> 10** (+3, +42.9 %), anchor-floor failures **9 -> 0** with refusals **34 -> 0**,
  second-key refusals **3 -> 0**, items realized **3 -> 10**, ACCEPTED **1 -> 2**, NO_SAFE_ITEM **15 -> 8**,
  REJECTED **2 -> 8**. `G2-PHELO-03` is a CORE decision the archived arm could not make safe and this one did.
- **`CONTRAST_FIRST_ASSESSMENT = PROMISING_NEEDS_LARGER_PILOT`.** All three limbs of the pre-registered rule
  hold: accepted-item safety perfect (both accepted items score 0 on all nine dimensions), post-stem survival
  materially improved, safe yield improved and a previously impossible CORE decision became safe. It is not
  VALIDATED, and the counter-evidence is recorded rather than explained away: **8 of 10 realized items were
  rejected** and the three independent reviewers recorded **45 defects** across the ten --
  UNSUPPORTED_CLAIMS 12, UNNATURAL_STEM_ENGINEERING 7, SECOND_KEY_RISK 6, FACTUAL_ERRORS 6, AMBIGUOUS 5,
  CRITICAL_FACT_SAFETY 4, REDUNDANCY 2, COMPETITOR_WITHOUT_STEM_ANCHOR 2, NUMERIC 1. Two accepted items
  cannot separate an architecture that works from one that happened to work twice.
- **The finding that matters most.** `COMPETITOR_WITHOUT_STEM_ANCHOR` was **0 by the production gate and 2 by
  an independent reviewer on the same item** (`G2-SURG-02`). The frozen anchor layer counts a generic scenario
  fact -- imaging is available, suspicion is intermediate -- as a plausibility anchor. Stem-first rarely
  exposed this because such anchors were rarely present by chance; contrast-first states them deliberately, so
  a weak anchor becomes visible stem furniture. The architecture did not create the defect, it made **anchor
  quality** the binding constraint. `G2-SURG-02` also scored UNNATURAL_STEM_ENGINEERING 4 and is the
  assembled-checklist failure the design's own section 16 predicted.
- **One real defect found by running the stage, not by reading it.** CO-3 refused four opportunities for
  "defeating a competitor only by explicit verbal denial" when the stem defeated it with a *positive* finding.
  An explicit denial is now only a PRESENT-required condition the blueprint assigns ABSENT; two regression
  tests pin both directions. A second fix threads the profile's declared `token_implications` through P2, as
  production ADM_1 does.
- `NEXT_DOMINANT_BOTTLENECK = OPTION_REALIZATION`, meaning the option-and-rationale layer. All three reviewers
  independently identified one template clause: every competitor rationale ends "That condition is not met
  here", which is false whenever the stem is merely *silent* about the condition. It accounts for almost all
  of UNSUPPORTED_CLAIMS 12 and touches 7 of the 10 realized items. Runner-up is anchor quality, above. Neither
  is fixed here.
- **Recurring structural property of the frozen library, worth knowing before the next wave:** several curated
  competitors carry a single plausibility anchor that is also their single correctness condition, so they can
  be live only by being a second key and are unusable in any contrast set. This is the most common reason a
  contrast set fell below three (`G2-OBGYN-02`, `G2-OBGYN-03`, `G2-SURG-03`, `G2-PSY-01`).
- Difficulty: attempted 6/6/6, accepted EASY 0, MEDIUM 1, HARD 1. Intent match EASY 0/0, MEDIUM 1/1, HARD 0/1
  -- the accepted HARD item was judged EASY by both the deterministic checks and the reviewer, because its
  capacity shortfall was stated so completely that little inference was left. `question_difficulty.py` was
  reused unmodified.
- Graph: `GRAPH_USED_UPSTREAM = YES`, seeded at the target node the key answers over inverted `ANSWERS` then
  `CONFUSED_WITH`, because arm C's stem-seeded traversal is unusable when there is no stem.
  `GRAPH_UNIQUE_USEFUL_CONTRIBUTIONS = 0`: it reached 5 typed concepts beyond the admissible pool and all five
  were already curated seeds refused by P2, plus 6 Toronto Notes topic nodes that may never justify a claim.
  Consistent with the benchmark; recorded rather than engineered away.
- Context, characters only because no local tokenizer is installed: total per opportunity median 14,895 / p95
  17,157. The stem author's own context is median **510** / p95 707, because it carries feature ids, their
  frozen normalized text and the prohibitions, and no option string.
- `COPYRIGHT_AUDIT = PASS`, longest verbatim Toronto Notes run **0** across all 10 tracked pilot artifacts.
  Focused tests **72**; full canonical suite **1224/0** at the final code state. Reports rebuild with
  `qbank run-contrast-first-pilot` and a test asserts they regenerate byte-identically from committed
  artifacts. Docs at `docs/contrast-first-generation.md`.
- **Contrast-first option-failure diagnosis (2026-09-05), diagnosed at `889ecb8`.** Diagnosis-only:
  `PRODUCTION_CODE_CHANGED = NO`, no opportunity, contrast set, matrix, stem, item, seed, gate or verdict
  moved, `FROZEN_QGEN_ARTIFACTS_CHANGED = 0`, `LLM_API_CALLS = 0`, no larger pilot, no new retrieval, no
  embeddings, graph untouched. `reports/qgen_contrast_first_option_failure_diagnosis.json`. Stages were
  recomputed from the frozen artifacts through `build_pilot_contrast_sets` and
  `run_post_stem_revalidation` rather than read from the pilot narrative.
- **`NEXT_DOMINANT_BOTTLENECK = OPTION_REALIZATION` is refuted by its own artifacts, and the refutation is
  the headline.** Distractor realization is *already* lossless: **32 of 32** realized distractor option
  texts are the frozen curated `competitor_concept` string verbatim, **32 of 32** "Live:" clauses are the
  seed's frozen `why_a_partially_knowledgeable_candidate_might_choose_it` verbatim, and **32 of 32**
  "Inferior: Correct where..." clauses are the seed's frozen
  `conditions_under_which_competitor_would_be_correct` verbatim. The only clinical claim the option layer
  authors for a distractor is the appended sentence "That condition is not met here." (32 of 32).
  `PROVENANCE_LOCKED_OPTION_REALIZATION` would lock what is already locked, so it was **not implemented**.
- `PRIMARY_FAILURE_COUNTS` over the eight rejected items, one earliest cause each, each resting on a quoted
  reviewer sentence: **`A_CONTRAST_SET_DEFECT` 3** (G2-MED-03, G2-SURG-01, G2-SURG-02),
  **`C_STEM_BLUEPRINT_DEFECT` 3** (G2-PED-01, G2-PSY-03, G2-PHELO-01),
  **`B_CONTRAST_MATRIX_DEFECT` 1** (G2-PED-02), **`H_OPTION_WORDING_REALIZATION_DEFECT` 1** (G2-OBGYN-01).
  Option-layer causes G-L total **1 of 8**. `GOOD_CONCEPT_BAD_RENDERING` 1,
  `BAD_CONCEPT_BEFORE_RENDERING` 4, `OTHER_FAILURE` 3. As primaries,
  `KEY_DISTRACTOR_SCOPE_ASYMMETRY`, `OPTION_CATEGORY_MISMATCH`, `DECISION_GRANULARITY_MISMATCH`,
  `CUEING_OR_TESTWISENESS` and `UNSUPPORTED_QUALIFIER_IN_RENDERED_OPTION_TEXT` are all **0**.
- **The decisive counterfactual, not the defect tally.** Asked per item whether every reject-forcing defect
  would disappear given an option layer that never asserted an unstated condition false and never mutated a
  cited claim: **1 yes (G2-OBGYN-01), 7 no**. Rewording the template clause would lower `UNSUPPORTED_CLAIMS`
  from 12 but change **no** verdict except that one, because in the other seven the competitor is genuinely
  live (second key), the pair is redundant, or the key itself is wrong. R1 said of G2-PED-02 in terms:
  not repairable by editing rationales.
- `PRIMARY_BOTTLENECK = MULTIPLE_INDEPENDENT_BOTTLENECKS` under the task's own rule (no option-layer cause
  reaches a plurality), so `BOUNDED_FIX_IMPLEMENTED = NO`, `FIX = NONE`, `FROZEN_REPLAY_RUN = NO`. But the
  seven non-option primaries are **not seven unrelated problems**: all seven are failure modes of one layer
  the phase-9 vocabulary has no name for, the **contrast-relation model** -- the frozen
  `plausibility_anchor_feature_ids` and `condition_predicates` over which the matrix, the blueprint solver
  and the anchor floor all reason. Four measured defects, in order of cost:
  (1) **silence is scored as defeat** -- `_satisfied` counts an unassigned feature as unsatisfied, and
  forbidding a feature PRESENT never assigns it ABSENT, so `no_second_key` passes over competitors the stem
  never addressed (G2-PHELO-01, G2-PSY-03, and every template clause);
  (2) **no competitor-versus-competitor test** -- redundant, nested or anchor-equals-condition competitors
  are admissible (G2-MED-03 one preload proposition defeats two options, G2-SURG-01 tubo-ovarian abscess
  nests in PID, G2-PED-01 `SF-P147-FOCAL-ASYMMETRIC-FINDINGS` is simultaneously the only available anchor
  and a correctness condition of two competitors);
  (3) **anchors are untyped** -- `SF-GS76-FEMALE-REPRODUCTIVE-AGE` and `SF-GS76-IMAGING-AVAILABLE-NOW`
  count as plausibility anchors and no reviewer accepts them (G2-SURG-01, G2-SURG-02); this is the pilot's
  already-recorded anchor-quality finding, now attributed;
  (4) **correctness conditions are conjunction-only** -- `CLM-R2-PED-VIRAL-INDICATION` reads "infection
  control purposes, **or** high risk patients" and `CLM-R2-PED-CXR-INDICATION` reads "unclear, ... not as
  expected **or** severity"; both are carried as conjunctions, so G2-PED-02 scored two genuinely correct
  competitors as defeated and keyed an answer its own `CLM-R4-PED-CONTINUOUS` contradicts.
- **The smallest property separating the two accepted controls from the eight rejections, measured.** Not
  seed strength, anchor count, response-class parity, decision-granularity parity, option wording or
  cueing -- every one of those is uniform across both groups or present in both (a mild lone-category cue
  appears in both accepted items). It is whether the stem's description is **closed over the domain of each
  competitor's unmet condition**. Every unsatisfied condition was classified against a stated rule:
  accepted **CLOSED 3 / OPEN 1 / STATED_CONTRARY 2** over 6 competitors; rejected **CLOSED 15 / OPEN 15 /
  STATED_CONTRARY 4** over 26. Competitors defeated *only* by open silence: accepted 1 of 6, rejected 9 of
  26. Both accepted items sit at the cohort minimum of **0.67** silent conditions per competitor; every
  rejected item is at 0.75 or above. In the accepted items the silences fall in domains the stem enumerates
  -- the contents of a letter, the region's staffing -- so silence is a real negation; in the rejected ones
  they fall on a pelvic examination never performed, a treatment preference never elicited, a case mix
  never reported, a body habitus never given. **Stated limit: two controls cannot prove a property, and
  G2-PHELO-03 was accepted while carrying one open-silence competitor.** This is the strongest measured
  association, not a validated rule.
- Option-realization contract audit: `validate_option_realization` receives only the matrix's `seed_id`
  set. It validates **no rationale text at all**, so realization may freely change severity, timing,
  management stage, certainty, diagnostic specificity, scope, population, route, modality or granularity in
  a rationale. Measured exercise of that freedom is near zero for distractors and confined to the
  free-authored **key** rationale, which is where G2-OBGYN-01's two unsupported claims live: `CLM-R2-OB-ABSCESS`
  says an abscess "often" has a palpable collection and the key rationale renders the categorical inverse
  (POLARIZED); `CLM-R2-OB-MASTITIS-ANCHOR` attaches the presentation to *inflammatory* mastitis and the key
  rationale renders it as defining both (BROADENED). The contract fired on 2 of 10 items
  (`OPTION_SPECIFICITY_MISMATCH` on G2-PHELO-01 and G2-SURG-02); both were rejected, so precision 2/2,
  recall 2/8.
- `DIFFICULTY_STATUS = NOT_VALIDATED`, and difficulty shares the root rather than being separate.
  `EASY_FAILURE_ROOT = EASY_FEATURE_BUDGET_MAXIMISES_OPEN_SILENCE`: all five realized EASY items were
  rejected, their causes spread exactly like the cohort, but `REQUIRED_FEATURE_CAP` gives EASY the smallest
  stem-feature budget and EASY stems carry the most unaddressed competitor conditions -- **1.20** silent
  conditions per competitor against 1.06 at MEDIUM and 0.71 at HARD. Closing a competitor's condition costs
  stem material, so the ladder's budget runs opposite to what safe discrimination needs.
  `HARD_DIFFICULTY_MISMATCH_ROOT = SAFETY_AND_DIFFICULTY_ARE_IN_DIRECT_TENSION_UNDER_THE_CURRENT_MODEL`:
  G2-PHELO-03 was declared HARD and judged EASY because its shortfall is "closed off so completely that
  little inference is left" -- the very property that made it safe -- while
  `MAXIMUM_ABSENT_REQUIRED_FEATURES` is 0 at HARD, forbidding the explicit denials that close a domain and
  pushing HARD items toward the open silence that produced the second keys.
- Context cost, characters only: median 14,895 / p95 17,157 per opportunity, unchanged. Components as a
  share of the median total: **contrast matrix 38.3 %**, verification context 24.3 %, stem blueprint 17.4 %,
  retrieved evidence 9.2 %, opportunity metadata 6.6 %, stem-author generation context 3.4 %.
  `NEXT_TOKEN_OPTIMIZATION_TARGET = CONTRAST_MATRIX_ROW_PAYLOAD`: in **39 of 39** rows `SUPPORTING_FEATURES`
  is an exact duplicate of `SHARED_PLAUSIBILITY_FEATURES.stem_feature_ids` and
  `DEFEATING_DISCRIMINATORS.unsatisfiable_conditions` an exact duplicate of the ids already in
  `CORRECTNESS_CONDITIONS` -- 424 characters at the median, 7.2 % of the matrix, 2.8 % of the total.
  **Identified only and deliberately not removed**, because deleting them edits the frozen matrix schema and
  moves its content hash.
- `COPYRIGHT_AUDIT = PASS`, longest verbatim Toronto Notes run **0** in the new report. Focused tests
  `tests/test_contrast_first_pilot.py` **72/0**; full canonical suite `NOT_REQUIRED` and not run, because no
  production code, validator or executable canonical artifact changed. `RECOMMENDED_ARCHITECTURE_ACTION`
  stays `DO_NOT_SCALE`.
- **Clinical contrast relation model V2 (2026-09-05), from `3ebdfb3`.** Design `58066e9`
  (`docs/superpowers/specs/2026-09-05-clinical-contrast-relation-model-v2-design.md`),
  engine `55d1749`, relations and counterfactual `c6eeebe`, solver `810e721`, replay `f8bd916`.
  `V2_ASSESSMENT = CLINICAL_CONTRAST_MODEL_V2_PROMISING`. No production generator replaced, no
  broad bank generated, `FROZEN_QGEN_ARTIFACTS_CHANGED = 0`, `LLM_API_CALLS = 0`, no embeddings,
  no full-book Toronto Notes extraction, graph untouched, `CLAUDE.md` unchanged.
- The four diagnosed defects are fixed and nothing else is. A feature the state map does not
  name resolves `UNKNOWN`, predicates evaluate under Kleene three-valued logic, correctness is a
  nested Boolean tree, features carry a semantic contrast role whose class depends on the
  decision domain, and every option set is evaluated over all pairs by `CS2-1..CS2-9`.
  Derived absences survive where the frozen contradiction pairs entail them, so "the letter
  states the relative benefit only" still says the denominator is missing.
- **Counterfactual against the unaltered V1 stems: `COUNTERFACTUAL_GATE = PASS` on all six
  precommitted limbs.** `NON_OPTION_REJECTIONS_INTERCEPTED_PRE_FINAL_REVIEW = 7/7`,
  `ACCEPTED_V1_CONTROLS_PRESERVED = 2/2`, silence-as-absence defects **15 -> 0**. G2-OBGYN-01 is
  deliberately not intercepted: its cause was `H_OPTION_WORDING_REALIZATION_DEFECT`, and a
  contrast-relation model has nothing to say about a rationale that polarizes its own claim.
- **V2 replay over the same ten opportunities: `V2_ACCEPTED = 4/10`, `V2_REJECTED = 1/10`,
  `V2_NO_SAFE_ITEM = 5/10`, against V1's 2 / 8 / 0.** Reviewer defect total over all realized
  items **45 -> 1**. `ACCEPTED_ITEM_SAFETY = PASS`, zero on all eleven dimensions. Every realized
  item clears `retrieve_profile_aware_contrasts` unchanged with no ADM_1, ADM_3 or SAF_1
  exclusion. Difficulty intent match EASY 1/1, MEDIUM 1/1, HARD 1/2; G2-PHELO-03 is declared
  HARD and reads EASY for the same reason it did in V1, its shortfall being stated completely.
- **Failure moved upstream rather than yield moving up.** V1 realized ten items and eight were
  rejected after a reviewer read them; V2 realizes five and refuses five before a stem exists,
  each by the defect the diagnosis named. V2 converts unsafe items into no items.
- **The one rejection is the most informative result.** G2-OBGYN-01 fails because
  `CLM-R2-OB-MASTITIS-ANCHOR` describes inflammatory mastitis in the stem's own words and
  separates bacterial mastitis from it only by whether antibiotics are needed to resolve it,
  which nothing at presentation settles. The key concept is one level finer than any frozen
  vocabulary feature can resolve. **V2 has no gate for an out-of-set concept that shares every
  discriminator with the key**; a human reading caught it and no rule did.
- Two mechanisms were added during authoring and both are load-bearing:
  `forbidden_present_features`, which refuses a feature a cited claim makes the signature of a
  concept the option set cannot contain, and discriminator scoping, because a feature two
  concepts share cannot decide between them however well cited it is.
- **The specified medium-36 pilot was not run and cannot be built.**
  `MEDIUM_36_PILOT_TRIGGERED = NO`. The frozen opportunity universe is **30**; only **18** carry
  an authored option-set contract; **16** of those reach three admissible curated candidates;
  **10** are consumed by this replay, leaving **6**. Building 36 needs new opportunities, seed
  packs with independent seed review and current-source evidence packets, which is source-packet
  research rather than an architecture pilot.
- `WHOLE_BOOK_CONTRAST_SCALING_DECISION = SCALE_CONTRAST_RELATIONS_ON_DEMAND`. Sixty-eight
  relations settled ten opportunities; all-pairs precomputation over 1,595 pages is the
  combinatorial explosion the design refuses. Keep the concept, evidence and contrast graphs
  logically distinct.
- Context cost, characters only: median **8,481** / p95 **9,123** per opportunity against V1's
  14,895 / 17,157. The V1 optimization target `CONTRAST_MATRIX_ROW_PAYLOAD` does not arise: the
  V2 path has no contrast matrix. `COPYRIGHT_AUDIT = PASS`, longest verbatim Toronto Notes run
  **0**. Focused tests **88/0**; full canonical suite **1312/0** at the final code state.
- `NEXT_DOMINANT_BOTTLENECK = CONTRAST_SUPPLY`. Not retrieval, settled by the four-arm
  benchmark, and no longer the relation model. The curated library carries three usable
  competitors for too few opportunities once V2 removes the nested, redundant and
  anchor-equals-condition members, and 12 of 30 opportunities have no option-set contract at all.
  Runner-up: the missing out-of-set second-key gate above.
- **On-demand clinical contrast supply (2026-09-05), from `b591226`.** Diagnosis `02cfa58`, design
  `42cdca3` (`docs/superpowers/specs/2026-09-05-on-demand-clinical-contrast-supply-design.md`),
  infrastructure `ad1c820`, wave `1a132aa`. `SUPPLY_ASSESSMENT = ON_DEMAND_CONTRAST_SUPPLY_PROMISING`.
  V2 was not redesigned, the production generator was not replaced, no broad bank was generated,
  no embeddings, no whole-book extraction, `LLM_API_CALLS = 0`, `FROZEN_QGEN_ARTIFACTS_CHANGED = 0`,
  `CLAUDE.md` unchanged.
- **The diagnosis is the part worth remembering.** Six competitor drops across the five frozen
  NO_SAFE_ITEM opportunities: four `CS2-6` ANCHOR_EQUALS_CONDITION, one `CS2-7` NO_USABLE_ANCHOR,
  one `CS2-1` nesting. Five of the six are properties of the **frozen stem-anchor layer** rather
  than of the clinical concept, so the missing supply was anchor supply, not concept supply.
  `FROZEN5_PRIMARY_SUPPLY_CAUSES` = `H_CURRENT_CONTRAST_LIBRARY_COVERAGE_GAP` (G2-PED-01,
  G2-PED-02), `L_OTHER_DIFFICULTY_SETTLEMENT_BUDGET` (G2-PSY-03),
  `L_OTHER_FROZEN_STEM_FEATURE_VOCABULARY_CEILING` (G2-SURG-01),
  `L_OTHER_KEY_CONDITION_NOT_OBSERVABLE` (G2-SURG-02).
- **One bounded wave each: 15 candidates discovered, 15 reviewed, 4 approved, 11 refused, 0
  uncertain.** Opportunities holding three admissible V2 competitors went **1/5 -> 3/5**. All four
  approved relations came from sources already in the repository -- 2 `APPROVED_V2_RELATION`, 2
  `CURATED_LIBRARY` -- and all four rest on rule S-4, an evidence-cited plausibility anchor added to
  a candidate whose frozen anchor row equalled its own correctness conditions. New-supply safety is
  zero on all eight dimensions.
- **The finding that matters most: an anchor the supply layer adds is invisible to the production
  gate.** G2-PED-01 reached a stem, realized its blueprint exactly, stayed post-stem coherent and
  was accepted by an independent review scoring zero on all eleven dimensions -- and
  `retrieve_profile_aware_contrasts` then refused two of its three competitors under **`SAF_1`
  STEM_PLAUSIBILITY_ANCHOR_ABSENT**, because that rule reads the frozen stem-anchor pack that design
  rule S-2 forbids supply to edit. `FROZEN5_RECOVERED_ACCEPTED = 0`. Supply can move a competitor in
  V2's semantics and cannot move it in production's.
- **Rule S-6 was added mid-wave, before any stem was written, and it changed an outcome.** The
  solver's first admissible blueprint for G2-PSY-03 dropped digital CBT from the option set and then
  asserted the inaccessibility of in-person delivery, a required-PRESENT leaf of that same dropped
  candidate. Supply may not remove an option and then spend its own condition to defeat its
  neighbour; G2-PSY-03 fails closed again as `FAIL_CLOSED_DROPPED_CANDIDATE_SIGNATURE_SPENT`.
- The two surgical opportunities stayed refused for the reasons the diagnosis predicted and neither
  is a retrieval failure. Toronto Notes FTS returned exactly the non-gynaecologic right-lower-quadrant
  differential G2-SURG-01 needs -- Crohn disease, mesenteric lymphadenitis, caecal diverticulitis,
  genitourinary and cardiopulmonary causes -- and every one was refused because SU-GS-76 carries no
  feature in which it could state a correctness condition. G2-SURG-02 fails `CS2-9` on its own frozen
  key and no competitor supply reaches that.
- The reviewer also refused, in terms, to relabel ectopic pregnancy into a separate concept category
  to clear `CS2-5`: the cue that rule exists to catch is that appendicitis is the only
  non-gynaecologic option on the page, and a relabelling would hide the cue from the rule while
  leaving it in front of the candidate.
- `GRAPH_UNIQUE_APPROVED_CONTRIBUTIONS = 0`, measured: `graph_neighbourhood` at `max_depth=1` from
  each study unit and its Toronto Notes topic node reaches 6 and 3 CONCEPT nodes, and all 9 are
  already curated seeds. `TN_FTS_UNIQUE_APPROVED_CONTRIBUTIONS = 0`.
  `LOCAL_EMBEDDING_TRIGGER_MET = NO`: the missing competitors were all found and then refused as
  inexpressible, so a better retriever returns the same list.
- Cache economics: `TOTAL_RELATION_REQUESTS 42`, `CONTRAST_CACHE_HITS 29`, `NEW_RELATIONS_CREATED 13`,
  reuse across opportunities and disciplines 0. Adding an anchor changes a relation's payload and so
  its content hash, which is why the two opportunities that received anchors show few hits.
- Context, characters, measured the same way `measure_v2_context` measures it so the comparison is
  like for like: median **9,422** / p95 9,422 over the one realized item against V2's 8,481 / 9,123.
  The supply layer adds a further median **35,824** / p95 42,860 per opportunity, **96 % of it the
  serialized pairwise relation payload**, which is the next token-cost target if this scales.
- `MEDIUM_36_PILOT_TRIGGERED = NO`, for two independent and sufficient reasons: the Phase 21 trigger
  is not met with zero accepted items, and the pilot still cannot be built. Re-measured unchanged --
  frozen opportunity universe 30, 18 with an authored option-set contract, 16 reaching three
  admissible candidates, 10 consumed by the V2 replay, **6 remaining**.
- `WHOLE_BOOK_CONTRAST_SCALING_DECISION = SCALE_CONTRAST_RELATIONS_ON_DEMAND` stands, now on measured
  evidence against the alternative rather than on principle: broad prepopulation would have
  contributed 0 novel concepts and 0 approved relations here, because the constraint is
  expressibility rather than recall. One stated precondition: until the plausibility-anchor layer is
  extendable and shared with the production gate, scaling on-demand supply scales V2-admissible sets
  that production refuses.
- `COPYRIGHT_AUDIT = PASS`, longest verbatim Toronto Notes run **0** over 8 tracked artifacts. Focused
  tests `tests/test_contrast_supply.py` **30/0**; full canonical suite **1342/0** at the final code
  state. Reports rebuild with `qbank run-contrast-supply-diagnosis` and `qbank
  run-contrast-supply-wave`, and a test asserts each regenerates byte-identically.
- `NEXT_DOMINANT_BOTTLENECK = OTHER_FROZEN_STEM_FEATURE_AND_ANCHOR_LAYER`. Four of the five refusals
  are that layer directly or the difficulty settlement budget colliding with what it cannot state;
  only G2-SURG-02 is something else. Runner-up stays `DIFFICULTY_CALIBRATION`, on no stronger
  evidence than before: the single realized item was declared MEDIUM and read EASY, for the same
  reason G2-PHELO-03 did.
- QGEN_NEXT_STEP = `USER_REVIEW_SUPPLY_MILESTONE`. The change this points at -- making the
  plausibility-anchor layer an extendable, independently reviewed artifact that both V2 and
  `retrieve_profile_aware_contrasts` read, and deciding whether the frozen stem-feature vocabulary
  may grow -- reopens a frozen layer, which AGENTS.md requires explicit authorization for and this
  task did not carry.
- **Versioned clinical feature/anchor registry (2026-09-06), from `14f4508`.** Diagnosis `317f965`, design
  `7a9d828` (`docs/superpowers/specs/2026-09-06-versioned-clinical-feature-anchor-registry-design.md`),
  registry and snapshots `0f2bea1`, adapters and gate replay `798cac0`, frozen-five replay and milestone
  `49f153c`, docs `cc0e358`. `FEATURE_ANCHOR_REGISTRY_MILESTONE = COMPLETE`,
  `CONTRACT_RECONCILIATION = PASS` on all six precommitted limbs.
  `HISTORICAL_FROZEN_ARTIFACTS_MODIFIED = 0`, `LLM_API_CALLS = 0`, no embeddings, no graph or TN FTS
  expansion, no broad bank, production generator not replaced, `CLAUDE.md` unchanged.
- **This is the change the supply milestone's `USER_REVIEW_SUPPLY_MILESTONE` pointed at, and this task
  carried the authorization the previous one did not.** The frozen 102-feature stem-feature vocabulary was
  **not** grown; only the plausibility-anchor layer became extendable and shared.
- Phase 0 (`reports/qgen_feature_anchor_contract_reconciliation.json`) measured the defect rather than
  restating it: **4 approved anchor additions, 0 visible to `SAF_1`**. It also counted a second mismatch
  nobody had: of the **87** features the frozen packs already use as anchors, **14 are `CLINICAL_JUDGEMENT`,
  7 `SYSTEM_CONSTRAINT`, 2 `PROGRAMME_CAPACITY`** -- roles typing outside `ANCHOR_CLASSES` in
  `PATIENT_CLINICAL`. That is the pilot's anchor-quality finding with a number on it. The registry
  **reports** it and deliberately does not enforce it, because enforcing it would move historical verdicts.
- **Two tables, not one, and that is the whole design.** A feature is something the vocabulary can say; an
  anchor relation is a claim that this feature PRESENT, for this learner decision, gives a candidate a reason
  to consider that competitor. `FEATURE_REGISTRY_IMPLEMENTED = YES`,
  `ANCHOR_RELATION_REGISTRY_IMPLEMENTED = YES`, `VERSIONED_SNAPSHOTS_IMPLEMENTED = YES`.
  `BASELINE_SNAPSHOT_ID = FEATURE_ANCHOR_SNAPSHOT_V1`, **102 features / 153 anchor relations**, hash
  `e8fa80dcc2d594ad9b7848d4172f154af94bb80fc5d73fb749ee7ecb4e115d5b`.
  `NEW_SNAPSHOT_ID = FEATURE_ANCHOR_SNAPSHOT_V2`, **102 / 157**, hash
  `863aee59b5017253614e1d2a24eb6aa93001f29f7481c1cbebf374083cc11a89`. Anchor relation ids are content
  addressed over the identity tuple alone, so restating evidence does not move an id.
- Baseline import fidelity is asserted by **set equality per seed on all 81 retrievable seeds**, not by
  equal counts, including the one deliberately anchorless seed `SEED-PED-T03-HYPERTONIC`.
- **Frozen-five extension set** (`research/qgen/feature_anchor_extensions.json`), derived from the already-run
  wave with no new discovery: 15 proposed. `FROZEN5_PROPOSED_NEW_FEATURES = 5`,
  `FROZEN5_PROPOSED_ANCHOR_RELATIONS = 7`, `INVALID_EXTENSION = 3`.
  `FROZEN5_APPROVED_NEW_FEATURES = 0`, `FROZEN5_APPROVED_ANCHOR_RELATIONS = 4`,
  `FROZEN5_REJECTED_EXTENSIONS = 11`, `FROZEN5_UNCERTAIN_EXTENSIONS = 0`. All four approved extensions need
  **zero** new features: `SF-P147-MODERATE-SEVERE-DISTRESS` and `SF-PS12-MODERATE-SEVERITY` already exist.
- The registry-level review found a **third identity mismatch nobody had counted**: three of the four approved
  candidates carry a supply-minted `concept_id` that differs from the curated pack's
  (`CONCEPT-R2-SU-P-147-FOREIGN-BODY` against `CONCEPT-R4-SU-OT-56-FOREIGN-BODY`, and two more). The registry
  binds to the registered id and records the alias.
- **The precommitted historical regression failed on its first run, and it was right to.** Under the
  extended snapshot `SEED-PSY-T03-COMBINED` became admissible in **`G2-PSY-04`**, a different learner
  decision (`LD-PS12-05` rather than `LD-PS12-03`) whose stem also states moderate severity and which no
  reviewer had considered. Retrieval keys on discipline x item archetype x option-set archetype and not on
  the decision, so an unscoped approved anchor becomes a universal one -- the exact failure the two-table
  design exists to prevent, arriving from the retrieval side. **Fix:** an approved anchor relation names the
  decision contexts its review considered in `scope_opportunity_labels` and applies nowhere else; with no
  scope it applies nowhere at all. `G2-PSY-04`'s verdict is restored and only `G2-PSY-03` moves.
- **Migration seams: three index builders, not `SAF_1`.** `build_retrieval_index`,
  `load_curated_candidates` and `build_current_library_index` each take an optional
  `feature_anchor_snapshot` plus `feature_anchor_scope`. **Unpinned they add no field at all** and read the
  frozen packs, which is why every frozen report still regenerates byte-identically and retrieval benchmark
  arm A is unmoved. `SAF_1`'s rule is untouched; only where its anchors come from changed.
- **Visibility reconciles exactly.** `APPROVED_EXTENSIONS_VISIBLE_TO_V2 = 4/4`, `..._TO_SAF1 = 4/4`,
  `..._TO_PROFILE_RETRIEVAL = 4/4`, and the three sets are the *same* set. `SAF_1` visibility is measured
  from the gate's own verdicts, not from an index field.
- Historical regression over the 30 frozen G2 opportunities through arm A:
  `BASELINE_REPRODUCES_LEGACY_EXACTLY = True`. Known-anchorless controls 67, returned 0 legacy and **0
  without an approved extension** under V2; second-key controls 8, returned 0 in both, with `ADM_3` refusals
  constant at 8; accepted controls preserved 40 -> 41. The `KNOWN_ANCHORLESS` list is derived from the old
  floor's own verdicts and is therefore circular for exactly the seeds an extension names, so the strict
  count (1) and the non-circular count (0) are both reported rather than one replacing the other.
- **`G2_PED_01_LEGACY_SAF1 = FAIL`, `G2_PED_01_NEW_SAF1 = PASS`**, with the stem, options, key, evidence and
  rationales untouched. Legacy `SAF_1` refused `SEED-PED-T01-FOREIGN-BODY` and `SEED-PED-T01-PNEUMONIA`; the
  new contract refuses nothing and ranks all three.
- **Frozen-five replay, one variable.** `FROZEN5_WITH_3_VALID_AFTER_SUPPLY = 3/5` unchanged.
  `FROZEN5_VISIBLE_TO_LEGACY_SAF1 = 0/5` -> `FROZEN5_VISIBLE_TO_NEW_SAF1 = 1/5`.
  `GENERATED_BEFORE = 1`, `GENERATED_AFTER = 1`, `ACCEPTED_BEFORE = 0`, **`ACCEPTED_AFTER = 1`**.
  `ACCEPTED_ITEM_SAFETY = PASS`, zero on all eleven dimensions on a fresh review that reread the cited claims
  verbatim before consulting the earlier verdict. Two dimensions are argued rather than asserted and both
  reservations are recorded: escalating work of breathing is a general trigger to widen the differential
  rather than a pointer specific to aspiration or pneumonia, and the pneumonia second-key objection turns on
  the frozen vocabulary separating an observation of respiratory effort from a raised bacterial concern.
- **`NEW_GENERATION_ATTEMPTS_RUN = 0`, and that is the honest number.** No opportunity newly reached a stem:
  `G2-PED-02` and `G2-PSY-03` still fail closed inside the blueprint solver on settleability and on supply
  rule S-6, and `G2-SURG-01`/`G2-SURG-02` are unchanged. An anchor snapshot touches none of those. All four
  non-control opportunities are byte-identical between the legacy and new replays.
- **`MEDIUM36_TRIGGERED = NO`, and for the first time the reason is only feasibility.** All three Phase 26
  trigger limbs are now met. `MEDIUM36_OPPORTUNITIES = 0`. The pilot cannot be built: frozen universe 30, 18
  with an authored option-set contract, 16 reaching three admissible candidates, 10 consumed by the V2
  replay, **6 remaining**. Reaching 36 is source-packet research, not an architecture pilot.
- Production lifecycle documented in `reports/qgen_feature_anchor_registry_milestone.json` and
  `docs/feature-anchor-registry.md`: run N pins `SNAPSHOT_N`, collects proposed extensions without applying
  any, reviews them independently with `UNCERTAIN` failing closed, builds `SNAPSHOT_N+1`, and runs the next
  batch. An extension proposed during a batch is invisible to every later question in that batch.
- Token cost, characters, re-measured and **unmoved**: supply layer median **35,824** / p95 **42,860** per
  opportunity, V2-comparable median 9,422. The registry added no serialization.
  `NEXT_TOKEN_OPTIMIZATION_TARGET = SERIALIZED_PAIRWISE_RELATION_PAYLOAD`: stable `anchor_relation_id`s are
  now the precondition for sending references instead of re-serializing a competitor's full anchor and
  condition payload on every pairwise relation. Deliberately not done here, per Phase 29's own rule, and no
  evidence a semantic reviewer needs was removed.
- `COPYRIGHT_AUDIT = PASS`, longest verbatim Toronto Notes run **0** across all 10 tracked artifacts.
  Focused tests **55/0** (`tests/test_feature_anchor_registry.py` 31, `tests/test_feature_anchor_adapters.py`
  24); full canonical suite **1397/0** at the final shared-code state.
- **Stated limits.** `R-REGISTRY-1` and `R-REGISTRY-REVIEW-1` are separate reasoning passes by the same model
  instance rather than separate agents, which is weaker than the contrast-first pilot's three fresh
  reviewers, and the item review is not blind. Every load-bearing claim was rechecked against the frozen
  artifact rather than the supply layer's summary: correctness trees from the enrichments, the
  `SF-PS12-MODERATE-SEVERITY` role override from the frozen V2 readings (where it already existed, cited, and
  predates the supply wave), and all six cited claims from the R2 and R4 evidence packets.
- `NEXT_DOMINANT_BOTTLENECK = EVIDENCE_SCOPING`. The anchor layer is no longer it. Of the four frozen-five
  opportunities still refused, two fail inside the blueprint solver and two because `SU-GS-76` carries no
  feature in which a non-gynaecologic differential could state a correctness condition. All five
  `NEW_FEATURE_REQUIRED` proposals are the same shape -- a clinically legitimate competitor the vocabulary
  cannot express -- and the vocabulary cannot grow without an evidence packet for the features it would need.
  Runner-up stays `DIFFICULTY_CALIBRATION`, on no stronger evidence than before.
- QGEN_NEXT_STEP = `USER_REVIEW_FEATURE_ANCHOR_REGISTRY`. The change this points at -- authorising an
  evidence-backed extension of the frozen 102-feature stem-feature vocabulary, which is what
  `G2-SURG-01` and the five refused proposals need -- reopens a frozen layer that this task's own
  authorization explicitly did not cover.
- **Cross-discipline medium pilot on one pinned snapshot (2026-09-06), from `c640ede`.** Code and tests
  `c516d60`, pilot artifacts and reports `86445f5`, `e682bc6` and `c47a216`. `MEDIUM_PILOT_TRIGGERED = YES`,
  `MEDIUM_PILOT_N = 6`. `HISTORICAL_FROZEN_ARTIFACTS_MODIFIED = 0`, `LLM_API_CALLS = 0`,
  `SNAPSHOT_MUTATED_DURING_PILOT = NO`, no embeddings, no graph or TN FTS expansion, no broad bank,
  production generator not replaced, `CLAUDE.md` unchanged.
- **Six, not thirty-six, and the shortfall is the universe rather than the rule.** Frozen universe 30,
  18 with an authored option-set contract, 16 reaching three admissible curated candidates, 10
  consumed by the V2 frozen-ten replay, **6 remaining** -- MED 1, PED 1, OBGYN 2, SURG 1, PSY 1,
  **PHELO 0**. Below the stated floor of 24, reported rather than closed; no criterion was weakened
  and no opportunity invented. Difficulty mix MEDIUM 3 / HARD 3, no EASY.
- **The pilot's whole result is one number: `MEDIUM_GENERATED = 0`.** Pre-supply contrast-ready 1/6,
  post-supply **1/6**, generated 0, accepted 0, `NO_SAFE_ITEM` 6.
  `MEDIUM_ACCEPTED_ITEM_SAFETY = NO_ACCEPTED_ITEMS`, which is not `PASS` over an empty set and is not
  a regression either; the two statements are different and both are recorded.
- **What blocked it is the pinned-snapshot rule doing exactly its job.** The one bounded supply wave
  approved 8 anchor additions and 3 new members, and **none of the 8 anchor relations is asserted by
  `FEATURE_ANCHOR_SNAPSHOT_V2`**. Phase 19 withholds them from every item in the batch, so 4 of the 6
  fail with `NEW_EXTENSION_NOT_IN_PINNED_SNAPSHOT` -- the largest failure category at **66.7%**. This
  is the invariant, not a defect: the production gate independently refused the same three competitors
  under `SAF_1` for the same reason, which is the V2-versus-`SAF_1` divergence the registry closed,
  arriving this time from the supply side and being caught.
- **Counterfactual, reported and not counted:** had those relations been in the pinned snapshot,
  contrast-ready would be 3/6 and generated 1 (`G2-SURG-03`). That item was **rejected** on
  `UNSUPPORTED_CLAIMS = 1`.
- **`SNAPSHOT_V3` as reviewed unblocks nothing, and that is the most important measurement here.**
  Extension yield 10 proposals (8 anchor relations, 2 features), independently reviewed:
  **5 APPROVED, 0 REJECTED, 5 UNCERTAIN**, none activated. Applying only the 5 approved relations
  takes contrast-ready from 1 to **2** and items reaching a stem to **0**. One turn of the snapshot
  cycle does not close the batch that fed it.
- **The extension review overturned three of the wave's own approvals, on downstream evidence.** The
  wave admitted `SF-GS76-MIGRATORY-RLQ-PAIN` as a shared anchor for all three surgical competitors by
  substituting the vocabulary's statement of appendicitis for what the claims actually name, which is
  the disease. The post-stem gate then fired **CS2-7 `SET_LIVES_ON_ONE_FEATURE`** on the counterfactual
  item -- the set living on one feature is precisely that anchoring's signature. UNCERTAIN fails closed.
- **Five named architectural defects, one at or above the Phase 25 threshold.**
  `SYSTEMATIC_DEFECT_GE_20_PERCENT = YES`, `SYSTEMATIC_DEFECT = V2_CANNOT_CARRY_A_NEVER_CORRECT_DISTRACTOR`
  at **33.3%**: V2 requires every competitor to carry a condition under which it would be right, an
  empty tree fails validation, and eight frozen seeds across three opportunities are options their own
  reviewed prose records as never correct. The other four, one opportunity each:
  `MISSING_VOCABULARY_FEATURE_FOR_A_SHARED_PRESENTATION` (`G2-MED-01`),
  `ONE_MEMBERS_CORRECTNESS_CONDITION_IS_ANOTHERS_SOLE_ANCHOR` (`G2-PED-03`),
  `DENIAL_BUDGET_AGAINST_DENIAL_ONLY_COMPETITORS` (`G2-PSY-01`), and
  `KEY_EVIDENCE_SCOPE_NOT_CHECKED_AGAINST_THE_SETTLEMENT_DEVICE` (`G2-SURG-03`). None repaired here,
  per Phase 25's own rule.
- **The last of those is new and has no gate.** At HARD the solver may spend no explicit denial, so it
  settled three competitors with one stated positive contrary, perforation with generalised peritonitis.
  Nothing asks whether that contrary carries the patient outside the evidence scope of the **key's own**
  correctness conditions -- and here it did: the key's tree was read from `CLM-R2-SURG-STANDARD`, whose
  words are "adult NON-COMPLICATED appendicitis". The rationale could only stand by eliding that
  qualifier. It is the mirror image of the silence-as-absence defect V2 was built to close.
- Difficulty: the one realized item was declared **HARD** and read **EASY** on the blind solve, for a
  structural reason rather than a stylistic one -- a finding strong enough to settle three competitors
  at once is strong enough to give the answer away. One observation is not a rate; `DIFFICULTY_INTENT`
  stays authored and separate from a future `EMPIRICAL_DIFFICULTY`, and the six reserved learner-data
  fields stay unpopulated.
- `GRAPH_UNIQUE_APPROVED_CONTRIBUTIONS = 0`, `TN_FTS_UNIQUE_APPROVED_CONTRIBUTIONS = 0` over five
  bounded full-text queries -- the second consecutive wave in which both contributed nothing.
  `WHOLE_BOOK_TN_DECISION = ON_DEMAND_TN_CONTRAST_SCALING` stands: none of the six failures is a recall
  problem. `LOCAL_EMBEDDING_TRIGGER_MET = NO`, `EMBEDDINGS_ADDED = NO`.
- Supply cost, characters, per opportunity: median **25,753** / p95 **38,181**, again almost entirely
  the serialized pairwise relation payload. `NEXT_TOKEN_OPTIMIZATION_TARGET` unchanged at
  `SERIALIZED_PAIRWISE_RELATION_PAYLOAD`; measured, deliberately not optimized.
- **`SNAPSHOT_LIFECYCLE_STATUS = PROMISING`, and `PRODUCTION_SCALEOUT_SPEC_WRITTEN = NO`.** Every
  mechanical limb of the lifecycle ran and held -- the snapshot did not move, extensions were collected
  and none applied, an extension proposed mid-batch was invisible to every later item. What it has not
  shown is a batch that yields an accepted item, which is Phase 30's own precondition for the scale-out
  design, so no spec was written and no production batch size is recommended: a batch size derived from
  an acceptance rate of 0/6 would be invented. The measurable quantity the pilot does support is the
  extension yield, **1.67 proposals per opportunity, 8 of 10 anchor relations rather than features**.
- `COPYRIGHT_AUDIT = PASS`, longest verbatim Toronto Notes run **0** across 10 tracked artifacts.
  Focused tests `tests/test_medium_pilot.py` **20/0**; full canonical suite **1417/0** at the final
  shared-code state. Everything rebuilds with `qbank run-medium-pilot`, and a test asserts all four
  reports regenerate byte-identically.
- **Shared-code change, and its blast radius.** `build_v2_contrast_sets`, `run_v2_replay`,
  `run_acquisition_wave` and `run_frozen5_replay` take optional artifact paths defaulting to the frozen
  files, and an under-size contrast set is now **reported** rather than raised. Nothing is admitted that
  was refused before -- the refusal is the same, the reason is now measurable -- and the frozen-ten
  replay, the frozen-five recovery report and the registry gate replay all still regenerate
  byte-identically, each asserted by its own test.
- **Stated limits.** The wave reviewer, the item reviewer and the extension reviewer are separate
  reasoning passes by the same model instance rather than separate agents, and the item review is not
  blind. `PHELO` contributes nothing to this pilot because all three of its eligible opportunities were
  consumed by the frozen-ten replay, so "cross-discipline" here means five disciplines, not six.
- `NEXT_DOMINANT_BOTTLENECK = SNAPSHOT_EXTENSION_RATE`. Four of six failed on anchor-relation coverage
  in the pinned snapshot, and the wave could cite every one of those relations from frozen evidence in a
  single bounded pass: the constraint is the rate at which reviewed relations enter a snapshot, not the
  rate at which they can be found. Runner-up stays `EVIDENCE_SCOPING`.
- QGEN_NEXT_STEP = `DIAGNOSE_MEDIUM_PILOT_FAILURE`. The two changes it points at are the systematic
  defect -- whether a competitor that is never correct can be carried at all, which needs a model
  decision rather than a snapshot -- and a gate for the key's own evidence scope against the settlement
  device. Neither was repaired here, per Phase 25.
- **Snapshot bootstrap and distractor semantics (2026-09-06), from `2e90375`.** `SNAPSHOT_BOOTSTRAP_AND_DISTRACTOR_MILESTONE = COMPLETE`. Design
  `docs/superpowers/specs/2026-09-06-distractor-semantics-and-snapshot-bootstrap-design.md`.
  `HISTORICAL_FROZEN_ARTIFACTS_MODIFIED = 0`, `LLM_API_CALLS = 0`, no embeddings, no graph or TN FTS
  expansion, no broad bank, production generator not replaced, `CLAUDE.md` unchanged. Everything rebuilds
  with `qbank run-snapshot-bootstrap`, and a test asserts all seven artifacts regenerate byte-identically.
- **`FEATURE_ANCHOR_SNAPSHOT_V3`, parent V2, 102 features / 162 anchor relations**, hash
  `93870b56369816533dd234a2af34f6f99a50dc77fd91ed259d0a2cee810e9c70`. It carries the **5** anchor relations
  the medium pilot's extension review independently approved and **0** of the 5 it left UNCERTAIN.
  `V3_VISIBILITY_REPLAY = PASS`: 5/5 visible to the snapshot, to the seed-anchor adapter and to profile
  retrieval, and the three sets are the *same* set; 0/5 uncertain rows visible to any snapshot. The store is
  **append-only** -- V1 and V2 regenerate byte-identically and their hashes are unmoved.
- The five UNCERTAIN rows stay excluded, re-read rather than re-reviewed for yield. Three are the surgical
  `SF-GS76-MIGRATORY-RLQ-PAIN` anchors, which fail S-4 limb B on the strict reading (the claims name
  appendicitis, the disease, not the migratory pain, the feature) and whose downstream signature is CS2-7
  `SET_LIVES_ON_ONE_FEATURE`; two would grow the frozen 102-feature vocabulary, which `validate_extension`
  refuses on its own account. **`REVIEWER_INCONSISTENCY_OR_EVIDENCE_BUG = NONE` on all five.**
- **Three arms over the same six frozen opportunities, one variable each.** Contrast-ready
  **1/6 -> 2/6 -> 3/6**; `GENERATED = 0`, `ACCEPTED = 0`, `REJECTED = 0`, `NO_SAFE_ITEM = 6` in every arm.
  `ALL_ACCEPTED_ITEM_SAFETY = NO_ACCEPTED_ITEMS`, and Part G's independent review ran **zero** times because
  there was nothing to review; neither is stated as a PASS.
- **`SNAPSHOT_BOOTSTRAP_ASSESSMENT = VALIDATED`**, on all four precommitted limbs: `G2-PSY-01` converts from
  a 1-competitor under-size set to a coherent 4-competitor set reaching the blueprint, historical controls are
  unchanged, no uncertain extension is visible, no gate is weakened. The mechanism is validated and the batch
  is **not** rescued by it -- one turn of the cycle still does not close the batch that fed it.
- **`V2_CANNOT_CARRY_A_NEVER_CORRECT_DISTRACTOR` is a real defect, and it is repaired.**
  `CURRENT_V2_REQUIRES_COUNTERFACTUAL_CORRECTNESS = YES`, structurally rather than by policy:
  `validate_predicate` refuses an empty branch, so "no state makes this correct" was unrepresentable.
  It is **not necessary for one-best-answer safety** -- a competitor with no state in which it is right is the
  safest possible option against a second key -- and the frozen record already held the counterexample:
  **`G2-MED-04` is an accepted item, zero defects on all eleven dimensions, two of whose three competitors
  carry zero condition predicates** -- accepted under the G2 safe-yield contract, before V2 existed, so it is a
  counterexample to a universal claim and not a rate. The G2 root-cause diagnosis drew the never-*optimal* against
  never-*appropriate* distinction, said the library does not distinguish them, and deliberately proposed no
  rule. This is that rule, and the disagreement it owns is that the earlier reviewer put G2-OBGYN-03's deep
  massage and nipple shield on the never-appropriate side.
- `NEVER_CORRECT_DISTRACTOR_CASES = 9` (7 from the pilot, 2 prior frozen accepted-control examples):
  `PLAUSIBLE_BUT_NEVER_BEST` 8, `WRONG_DECISION_CLASS` 1 (`SEED-OB-T02-CRP`), and zero each
  `COUNTERFACTUAL_CORRECT`, `DEAD_DISTRACTOR`, `UNSAFE_OR_AMBIGUOUS`. `SEED-OB-T02-MILK-CULTURE` is carried as
  a negative control so the case file cannot be read as sweeping every refused option into one class.
- **OPTION 2 implemented, OPTION 3 refused as unnecessary.** `PLAUSIBLE_BUT_NEVER_BEST` is declared per member;
  absence means the old class, and a default competitor's verdict serializes **no new key at all**, which is why
  every frozen replay is still byte-identical. A never-best member carries no correctness tree, so correctness is
  `NOT_SATISFIED` under every stem, `second_key_risk` is zero by construction, and `_settlement_route` returns
  `NEVER_BEST_BY_EVIDENCE` costing **no denial budget**. Seven limbs, each a positive cited statement; four
  inferiority bases, and deliberately **none meaning "the stem does not say so"**, so silence cannot supply
  inferiority because the shape cannot be encoded.
- **The contract has teeth, and the gates did the refusing.** `SEED-PED-T03-HYPERTONIC` fails
  `POSITIVE_PLAUSIBILITY_SUPPORT` -- genuinely plausible in prose, anchorless in the frozen vocabulary -- and
  the unmodified CS2-3 threw out `SEED-OB-T02-CRP` and `SEED-PED-T03-SALBUTAMOL` on response class. The
  salbutamol refusal is a frozen response-class-token gap rather than a semantic mismatch (the nebulized
  epinephrine seed beside it carries both tokens) and is reported rather than repaired: editing a frozen seed
  row to admit a candidate is the move this architecture refuses.
- **The bottleneck moved because the previous one was fixed.** Both opportunities the repairs carried
  downstream stop at `FAIL_CLOSED_COMPETITOR_CANNOT_BE_SETTLED` with the denial budget spent:
  `MAXIMUM_ABSENT_REQUIRED_FEATURES` is 1 at MEDIUM and **0** at HARD. `G2-OBGYN-03` (HARD) has none to spend;
  `G2-PSY-01` (MEDIUM) already spent its one denying a past hypomanic period. `SYSTEMATIC_ARCHITECTURE_DEFECT_
  GE_20_PERCENT = YES` at **33.3%**, defect `DIFFICULTY_DENIAL_BUDGET_AGAINST_DENIAL_ONLY_COMPETITORS`.
  Measured and left alone, per Phase 25's own rule. No item was realized in any arm, so there is no blind solve
  and no structural difficulty read; `DIFFICULTY_INTENT` stays authored and `EMPIRICAL_DIFFICULTY` stays absent.
- **`FRESH_PILOT_TRIGGERED = NO`, and the diagnosis is the opportunity-construction layer's bound rather than
  its quality.** The canonical universe declares **32** learner decisions across exactly **six** study units --
  one per discipline, the only six with a frozen stem-feature vocabulary and a curated seed pack -- and **29**
  are already opportunities. **3** remain, all inside study units Part U's own rule excludes, against a floor of
  24. `BINDING_LAYER = SOURCE_PACKET_RESEARCH`: a study unit becomes usable to qgen only after its packets are
  researched and a vocabulary, a seed pack and claim cards are built from them, and that has happened for 6 of
  1,175 planned allocation addresses. Nothing was invented to reach a number.
- `TWO_STAGE_SNAPSHOT_LIFECYCLE = PROMISING`. Preflight's load-bearing mechanism is now demonstrated rather than
  argued, and the no-leakage argument is explicit: preflight conditions on the decision the item is about, never
  on an outcome, because no item exists yet. **Arm B is deliberately not an instance of that lifecycle** -- its
  extensions were proposed inside a batch and reviewed with downstream evidence available, which is how three of
  the wave's approvals were overturned -- so the verdict is not VALIDATED.
- `SNAPSHOT_EXTENSION_RATE = INSUFFICIENT_DATA`. Proposed 1.67 and approved 0.83 per opportunity, 83.3% of
  opportunities requiring an extension, **0** reused across opportunities and 0 across disciplines. Two cycles
  is not a trend, both drew from the same six study units, and reuse across opportunities is structurally 0
  because the scope rule binds a relation to the decisions its review named.
- Context unchanged and deliberately not optimized: median **25,753** / p95 **38,181** characters,
  `NEXT_TOKEN_OPTIMIZATION_TARGET = SERIALIZED_PAIRWISE_RELATION_PAYLOAD`. `GRAPH_UNIQUE_APPROVED_CONTRIBUTIONS`
  and `TN_FTS_UNIQUE_APPROVED_CONTRIBUTIONS` were not re-measured because no query was run: nothing here is a
  retrieval problem, since every candidate arm C admitted was already a frozen curated seed.
- `COPYRIGHT_AUDIT = PASS`, longest verbatim Toronto Notes run **0** across all 12 tracked artifacts.
  Focused tests `tests/test_distractor_semantics.py` **22/0** and `tests/test_snapshot_bootstrap.py` **28/0**;
  full canonical suite at the final shared-code state.
- **Shared-code change and its blast radius.** `load_extensions` and `build_snapshot_store` take a second
  extension document; `run_pilot` takes a snapshot id and an acquisition path, both defaulting to what the
  medium pilot used; `enforce_pinned_snapshot` now resolves seed anchors *scoped* to the opportunity, which
  changes nothing for V2's four extensions because none is scoped to any of the six. In V2 the never-best class
  is inert unless declared. Every committed medium-pilot, frozen-ten, frozen-five and registry report
  regenerates byte-identically, each asserted by its own existing test.
- **Stated limits.** The extension re-review, the classification and the inferiority bases are separate
  reasoning passes by the same model instance rather than separate agents, and the re-review had this
  experiment's downstream evidence available to it. Six opportunities is not a sample: the 33.3% difficulty
  finding rests on two of them and cannot be confirmed or refuted at this size.
- `PRODUCTION_READINESS = BLOCKED_BY_OPPORTUNITY_CONSTRUCTION`, with `BLOCKED_BY_DIFFICULTY` the runner-up.
  Two blockers stand and they have different roles: opportunity construction bounds what can be *measured*,
  difficulty bounds what can be *generated*, and until the first moves no further architecture finding can be
  measured at a size that would justify acting on it. `PRODUCTION_SCALEOUT_SPEC_WRITTEN = NO`: three of Part
  AH's four preconditions fail.
- `NEXT_DOMINANT_BOTTLENECK = DIFFICULTY_CALIBRATION`, runner-up `OPPORTUNITY_CONSTRUCTION`.
- QGEN_NEXT_STEP = `USER_REVIEW_SNAPSHOT_BOOTSTRAP_AND_DISTRACTOR_SEMANTICS`. The two changes it points at are
  onboarding further study units to the question-generation layer, which is source-packet research and not an
  architecture change, and revisiting the difficulty contract's denial budget, which Part Q deliberately
  withheld authorization for.
- **Fresh-universe onboarding wave W1 (2026-09-06), from `0c8c82e`.** `FRESH_QGEN_UNIVERSE_MILESTONE = PARTIAL`.
  Code, tests and artifacts at `6327efe` (inventory) and the wave commit that follows it. No item was generated,
  no snapshot was built or mutated, no profile or frozen artifact was edited, no research was redone.
  `HISTORICAL_FROZEN_ARTIFACTS_MODIFIED = 0`, `LLM_API_CALLS = 0`, no embeddings, no graph or TN FTS expansion,
  no broad bank, production generator not replaced, `CLAUDE.md` unchanged. Everything rebuilds with
  `qbank build-fresh-universe-inventory` and `qbank run-fresh-universe-onboarding`, and tests assert all four
  artifacts regenerate byte-identically.
- **`STUDY_UNITS_INVENTORIED = 1507`, classified by the *earliest* qgen layer each one fails**, so the classes
  partition the address set: `OUT_OF_SCOPE` 332, `SOURCE_PACKET_INCOMPLETE` 1088, `SOURCE_READY_BUT_NOT_
  OPPORTUNITY_READY` **45** (MED 17, OBGYN 4, PHELO 24), `MCC_SCOPE_INCOMPLETE` 41,
  `ALREADY_CONSUMED_BY_PRIOR_PILOT` 1, `GENERATION_READY` **0**. PED, SURG and PSY hold no source-ready address
  outside their single existing anchor, so the onboarding pool is three disciplines, not six.
- **`UNCONSUMED_LEARNER_DECISIONS` is empty, not 3.** `LD-C21-03`, `LD-OB54-04` and `LD-PS12-04` were each
  already an opportunity in the G1 micro pilot; the earlier feasibility report compared against the G2 universe
  alone. Both counts are correct under their own rule and `PRIOR_FEASIBILITY_RECONCILIATION` records the
  difference rather than overwriting it. The stricter rule is the one a fresh pilot needs, so the pre-wave fresh
  ceiling was **0**.
- **`ONBOARDED_UNIT_SOURCE_PACKET_STATE` puts the two evidence routes side by side.** Five of the six onboarded
  units are `SOURCE_PACKET_INCOMPLETE` under the canonical plan, because their qgen evidence came from targeted
  pilot research rather than from completing their planned packets. Only `SU-PH-07` arrived by both routes.
- **First new blocker: `SOURCE_PACKET_READY` does not mean the evidence is about the address.** An independent
  alignment review of all 45 source-ready addresses returned **ALIGNED 22, PARTIALLY_ALIGNED 4, MISALIGNED 19**
  -- 42.2% of the queue. Two shapes. A packet populated with a different topic entirely: `SRC-PHELO-006` is
  planned for PH.S01.T01, the structure of Canadian public health, and holds incidence against prevalence;
  `SRC-MED-032` is planned for CP.S05, drug-suffix recognition, and holds atopic dermatitis. And a packet reused
  across addresses on `EXACT_CANONICAL_SOURCE_NODES_AND_MCC_OBJECTIVES`: `SRC-MED-035` covers `SU-D-28` through
  `SU-D-33` with one dermatophyte recommendation, which supports neither the scabies address nor the molluscum
  address nor the yeast address. Sharing a Toronto Notes node and an MCC objective is not sharing a clinical
  content, and nothing in the reuse basis checks that. **Reported, not repaired**: repairing it is source-packet
  research, and 19 packets are `PREVIOUS_READY` and immutable without a validated defect record.
- **Second new blocker: the frozen discipline profiles cannot express the decisions the richest new evidence
  supports.** Six ALIGNED addresses yield nothing, and `permitted_archetype_exceptions` is empty in all six
  profiles. `MEDICINE` admits DIAGNOSIS, INVESTIGATION_SELECTION, PHARMACOTHERAPY, RISK_STRATIFICATION and
  INTERPRETATION only, so **`SU-PM-06` (end-of-life decision making) and `SU-PM-10` (MAID)** -- both CORE, both
  carrying the richest packets in the whole source-ready set, CMPA, CPSO, Health Canada and CAMAP with three
  exceptions apiece -- have no archetype to sit in. Every `OBGYN` archetype requires
  `GESTATIONAL_AGE_OR_POSTPARTUM_DAY`, so **no gynaecologic address can be expressed at all**, including CORE
  contraception (`SU-GY-10`), gynaecologic imaging (`SU-GY-03`) and hysterectomy (`SU-GY-04`). `PHELO` has no
  single-clinical-next-action granularity, which costs `SU-PH-35`. The profiles were derived from what six anchor
  units needed and do not generalise. **No profile was edited and no decision was restated into a permitted
  archetype**, because restating a legal duty as a diagnosis is how an unsafe item gets built.
- **`FRESH_OPPORTUNITIES_CREATED = 26` across 16 new study units, MED 17 / OBGYN 3 / PHELO 6, all FRESH.**
  Each is checked in code against its own frozen discipline profile -- archetype, granularity and option-set
  archetype -- and against a recommendation or exception that actually exists in a researched packet for its own
  address; a fabricated reference and an empty reference list are both refused by test. Difficulty intents
  MEDIUM 16, EASY 6, HARD 4. Nothing was invented to reach a number and no criterion was weakened.
- **`FRESH_UNIVERSE_READY = NO` even though 26 clears the floor of 24, and the reason is a measurement.**
  `PREFLIGHT_CONTRAST_READY = 0/26` across 16 study units with **zero** features in the frozen vocabulary:
  contrast retrieval joins on the 102-feature vocabulary and the curated seed pool and on nothing else, and both
  cover the six anchor units only. The extension that would move it was **probed rather than quoted** --
  `validate_extension` refuses a `NEW_FEATURE_REQUIRED` proposal on its own account, saying a new feature reopens
  the frozen vocabulary and needs its own authorization. `SYSTEMATIC_DEFECT_GE_20_PERCENT = YES` at **100%**,
  defect `FROZEN_VOCABULARY_REFUSES_A_NEW_STUDY_UNIT`. Freezing a 26-opportunity pilot here would spend the whole
  batch, under the no-replacement rule, rediscovering a refusal visible before it started.
- **`BINDING_LAYER` is no longer `SOURCE_PACKET_RESEARCH` alone.** The wave shows three layers between a
  researched packet and a fresh opportunity, and research moves only the first: evidence-decision alignment
  (42.2% of the queue), profile expressibility (13.3%, including three CORE addresses), and the vocabulary
  refusal (100% of what survives). The last is a code-level refusal, so no amount of research moves it.
- `ACCEPTED_ITEM_SAFETY = NO_ACCEPTED_ITEMS`, which is not a PASS over an empty set. `GENERATED`, `ACCEPTED`,
  `REJECTED` and `NO_SAFE_ITEM` are all 0 because no pilot was frozen; `SAFE_YIELD` and `GENERATION_ACCEPTANCE`
  are undefined rather than zero. Context cost, snapshot extension rate, contrast cache economics and
  graph/FTS contributions were **not re-measured**: no wave ran, so the medium-pilot figures stand unchanged.
- `COPYRIGHT_AUDIT = PASS`, longest verbatim Toronto Notes run **0** across all 5 tracked artifacts. Focused
  tests `tests/test_fresh_universe_inventory.py` **23/0** and `tests/test_fresh_universe_onboarding.py` **24/0**;
  full canonical suite **1514/0** at the final shared-code state.
- **Shared-code change and its blast radius.** Two new modules and one new CLI command each; `cli.py` gains two
  handlers and two table rows. Nothing existing was edited, no frozen artifact was touched, and the full suite
  is unchanged apart from the 47 new tests.
- **Stated limits.** The alignment review, the decision authoring and the profile-refusal reasoning are separate
  reasoning passes by the same model instance rather than separate agents. The 26 decisions are authored, not
  independently re-derived, and their difficulty intents are declarations. The alignment verdicts are semantic
  judgements about 45 addresses and the four PARTIALLY_ALIGNED calls are the ones most open to disagreement;
  they were excluded from the wave rather than argued either way.
- `PRODUCTION_READINESS = BLOCKED_BY_OPPORTUNITY_CONSTRUCTION`, unchanged, but the diagnosis under it has moved
  from "research more packets" to three named layers, two of which are architecture rather than research.
  `PRODUCTION_SCALEOUT_SPEC_WRITTEN = NO`.
- `NEXT_DOMINANT_BOTTLENECK = FROZEN_VOCABULARY_REFUSES_A_NEW_STUDY_UNIT`, runner-up
  `EVIDENCE_DECISION_MISALIGNMENT`. `DIFFICULTY_CALIBRATION` drops to third: it bounds what can be generated
  inside six study units, and nothing can leave those six until the vocabulary refusal is authorised either way.
- QGEN_NEXT_STEP = `USER_REVIEW_FRESH_UNIVERSE_ONBOARDING_BLOCKERS`. The three decisions it points at are
  authorising an append-only stem-feature vocabulary for a new study unit (which `validate_extension` refuses
  under the current authorization and which no other work can proceed without), authorising discipline-profile
  archetype extensions for legal, ethical and gynaecologic decisions, and opening a defect record against the
  19 misaligned READY packets so source-packet research can repair them. None was done here.
- **Generalized QGEN onboarding, session of 2026-09-07, from `60046f9`/`01eff40` (design commit unchanged).** All
  three named blockers above are now addressed by committed, tested code: `scripts/qbank/onboarding_evidence.py`
  (address/decision-scoped evidence states), `scripts/qbank/qgen_profiles_v2.py` (compositional Profile V2,
  `QGEN_PROFILE_SNAPSHOT_V2`) and `scripts/qbank/vocabulary_onboarding.py` (append-only
  `FEATURE_ANCHOR_SNAPSHOT_V4`, parent V3). `GENERALIZED_QGEN_ONBOARDING_MILESTONE = PARTIAL`, not complete --
  see the exact stopping point below.
- **The frozen 45-address re-audit is unchanged and confirmed**: `research/qgen/onboarding/v2_evidence_audit_review.json`,
  `ALIGNED_COMPLETE=2 / ALIGNED_PARTIAL=23 / MISALIGNED=20`, `audit_status=FROZEN_REVIEW_BEFORE_REPAIR`, 20/0 tests.
- **Independent review of the pending V2 onboarding proposals is done, by a fresh Sonnet 5 subagent with no
  authorship stake** (`reviewer_execution_id = sonnet5-independent-review-2026-09-07`,
  `research/qgen/onboarding/v2_independent_review_raw.json`). Of 45 feature proposals across three files: 42
  `APPROVED`, 2 `REJECTED`, 1 `UNCERTAIN`. The two rejections and one uncertainty are real catches, not
  rubber-stamping: `FP-ONB2-P146-PERSISTENT-ASYMMETRY` conflates a brand-new proposal with the existing
  FROZEN_CANONICAL feature `SF-P147-FOCAL-ASYMMETRIC-FINDINGS` and should be split rather than approved as
  submitted; `FP-ONB2-P146-REDUCED-AIR-ENTRY` has no load-bearing decision citing it; `FP-ONB2-P146-INCOMPLETE-RESPONSE`
  needs an operational definition the source claim does not clearly give. Of the 26+6 decision-support review
  rows, 2 came back `UNCERTAIN` (`LD-D23-01`, `LD-PH11-02`): each decision statement asserts a specific clinical
  fact -- same-site fixed-drug-eruption recurrence, and "a larger sample cannot fix an unrepresentative frame"
  -- that is not textually present in its cited source claim, only a plausible domain inference from it.
- **`FEATURE_ANCHOR_SNAPSHOT_V4` is built, verified and reproducible from code**
  (`scripts/qbank/onboarding_v2_build.py`, `tests/test_onboarding_v2_build.py`, 4/0). Parent V3 (102 features,
  162 anchor relations) is untouched; V4 adds the 42 `APPROVED` rows only, giving **144 features / 162 anchor
  relations** (0 anchor proposals were pending). `research/qgen/onboarding/feature_anchor_snapshot_v4.json`
  passes `vocabulary_onboarding.verify_snapshot`.
- **Phase 7 revalidation of the original 26 fresh opportunities, under decision-scoped evidence + the V4
  vocabulary**: `research/qgen/onboarding/v2_phase7_phase8_revalidation.json`. **24/26 VALID**, 2 `EVIDENCE_BLOCKED`
  (`LD-D23-01`, `LD-PH11-02`, both because their independent review was `UNCERTAIN` rather than `APPROVED` --
  see above). No opportunity was kept "because the old module already called it validated"; each was re-run
  through `onboarding_evidence.validate_decision_support` against the canonical `final_question_allocation.json`
  addresses.
- **The two Profile V2 blockers from the prior wave are confirmed fixed, not just unit-tested.** The six
  previously `PROFILE_BLOCKED` decisions in `research/qgen/onboarding/v2_profile_blocked_decision_proposals.json`
  (gynecologic imaging `LD-ONB2-GY-IMAGING`, hysterectomy `LD-ONB2-GY-HYSTERECTOMY`, emergency contraception
  `LD-ONB2-GY-EC`, advance-care-planning consent `LD-ONB2-PM-CONSENT`, MAID substitute-decision-maker consent
  `LD-ONB2-PM-MAID-CONSENT`, occupational work history `LD-ONB2-PH-WORK-HISTORY`) are now **6/6 EVIDENCE_READY**
  under Profile V2 plus independent review -- run through the identical `validate_decision_support` path as the
  original 26, not asserted.
- **New PED/PSY/SURG discipline research (`research/qgen/onboarding/v2_new_discipline_evidence.json`, real CPS/
  CUA/BCCSU sources) supplies 12 candidate fresh decisions (PED 4, PSY 4, SURG 4) plus one SURG/pediatric
  croup unit (`SU-OT-52`, canonically routed SURG, population pediatric -- disclosed, not hidden). Their 14
  features were independently reviewed (11 approved, 2 rejected, 1 uncertain, folded into V4 above). Renal-stone
  recurrence prevention (`SU-U-09`) was excluded by the original author's own scope review before independent
  review even started, because its canonical MCC mapping is weak and narrow -- do not promote it; this matches
  the prior session's standing "do not promote" note for that exact unit.**
- **Not yet done, and this is the actual stopping point.** The 12 new PED/PSY/SURG decisions above have not been
  wrapped into `validate_decision_support`-shaped support objects (they currently use the simpler
  `proposed_decisions` schema, which lacks `clinical_target`/`population`/`limitations`/`mapping_provenance`) and
  so have not been run through the Phase 7-style decision-level evidence gate the 26+6 got -- only their
  *features* were independently reviewed. Contrast-supply/preflight readiness (Phase 13's
  `PREFLIGHT_CONTRAST_READY`) was not measured for any of the 12, or for the 6 unblocked ones, because that
  requires exercising `contrast_supply.py`/`profile_contrast_retrieval.py`, which this session did not touch.
  No item was generated; Phases 14-20 (freeze pilot, preflight, generation, final review, difficulty/cost
  metrics) were not attempted. `QGEN_NEXT_STEP = BUILD_DECISION_SUPPORT_OBJECTS_FOR_THE_12_NEW_DECISIONS_THEN_
  RUN_CONTRAST_PREFLIGHT`.
- **Continuation session, 2026-09-07, from the same `60046f9`/`01eff40` design/audit commits (no rewrite).**
  Picked up exactly the prior stopping point. `scripts/qbank/onboarding_v2_build.py` already provided
  `build_onb2_claim_catalog` for exactly this purpose, so no new library code was needed -- only new research
  artifacts. **The 12 PED/PSY/SURG decisions were wrapped into full `validate_decision_support`-shaped objects**
  (`research/qgen/onboarding/v2_new_discipline_decision_supports.json`) and checked structurally against
  `qgen_profiles_v2.resolve_profile` before any review spend: two real fixes were required and applied --
  PEDIATRICS' `always_required: ['age']` needed an explicit `age` context field (missed in the first draft), and
  two decisions (`LD-ONB2-PSY-AUD-WITHDRAWAL`, `LD-ONB2-SURG-CROUP-DISCHARGE`) were authored with a
  `DISPOSITION_ACTION` response class that does not exist in Profile V2's `DISPOSITION_SET` vocabulary and were
  relabelled to `SECURES_IMMEDIATE_SAFETY` / `NONE` respectively, the closest correct canonical tokens. All 12
  are `PROFILE_EXPRESSIBLE` with **zero new `study_unit_specific_exceptions`** -- Profile V2 still generalizes,
  not overfit.
- **One fresh independent-review subagent pass (`sonnet5-independent-review-2026-09-07-onb2-decisions`), seeing
  only each decision statement + its cited claim text + population/MCC scope -- never generation targets or
  discipline balance -- returned 8 `APPROVED` / 4 `UNCERTAIN` / 0 `REJECTED`** across the 12
  (`research/qgen/onboarding/v2_new_discipline_decision_validation.json`). Fail-closed per the anti-hallucination
  contract: `UNCERTAIN` did not proceed. Real catches, not rubber-stamping: `LD-ONB2-PED-ASTHMA-IMAGE` and
  `LD-ONB2-PED-ASTHMA-MAG` turned a source claim's permissive "can investigate" / "consider" into an imperative
  decision statement; `LD-ONB2-PSY-AUD-WITHDRAWAL`'s claim never actually states a care-setting recommendation
  (also flagged as textually truncated); `LD-ONB2-SURG-CROUP-EPINEPHRINE` borrowed a "moderate croup" severity
  definition to characterize the broader "moderate/severe" category the claim never itself defines. Run through
  the real `onboarding_evidence.validate_decision_support` gate (not asserted): **8/12 `EVIDENCE_READY`, 4/12
  blocked** -- PED 2/4, PSY 3/4, SURG 3/4.
- **`TOTAL_FRESH_VALID_OPPORTUNITIES = 38`** = the 24 still-valid original + 6 profile-unblocked (MED 18 / OBGYN 6
  / PHELO 6, confirmed by re-deriving disciplines from `final_question_allocation.json`, not assumed) + the 8
  newly valid (PED 2, PSY 3, SURG 3). **All six disciplines are represented for the first time this milestone.**
  A grep-level freshness check against the study units of the four generation batches that actually produced
  items (G1 micro pilot, G2 targeted seed, medium pilot, frozen-5 replay) found zero overlap with the four new
  study units (`SU-P-099`, `SU-P-146`, `SU-PS-29`, `SU-OT-52`) -- consistent with the research file's own "no
  prior target" disclosures.
- **Per Phase 6's own rule, 38 > 36 so a balanced 36 was frozen before any contrast signal was visible**, not
  after: 2 MED opportunities were dropped by a pre-registered deterministic rule (the sibling decision of the two
  highest-numbered multi-decision MED addresses, `SU-C-35` and `SU-D-26`, so each address keeps one decision) --
  never chosen by outcome. **`FROZEN_PILOT_N = 36`**, `FROZEN_BY_DISCIPLINE = {MED 16, OBGYN 6, PHELO 6, PED 2,
  PSY 3, SURG 3}` (`research/qgen/onboarding/v2_frozen_pilot_opportunities.json`). PED/PSY/SURG sit below the
  preferred 4-6 floor because only 8 of the 12 candidate decisions cleared independent review -- reported as a
  real limit, not patched by inventing more candidates or forcing an `UNCERTAIN` to `VALID`.
- Focused tests unchanged and re-run clean: `tests/test_onboarding_v2_build.py` +
  `tests/test_qgen_profiles_v2.py` + `tests/test_vocabulary_onboarding.py` + `tests/test_onboarding_evidence.py`
  **77/0** (no library code was modified, only new research JSON artifacts and one reused build-module function).
- **Not yet done, and this is the actual new stopping point.** Phases 9-33 were not attempted: contrast-supply
  baseline measurement (Phase 11) was scoped but not executed -- a real check found the curated seed pool
  (`research/qgen/generalization/competitive_contrast_seed_pack_r4.enrichment.json`) already tags PEDIATRICS,
  PSYCHIATRY and SURGERY seeds (62 rows), so `PREFLIGHT_CONTRAST_READY` for the new-discipline opportunities is
  a genuinely open question rather than an assumed zero -- but answering it correctly requires
  `build_retrieval_index` + `retrieve_profile_aware_contrasts` with a realized stem-feature map, which does not
  exist until a stem is drafted, i.e. it is Phase-12/17 work, not a preflight-only check. No pilot feature
  snapshot V5 was built, no contrast sets were frozen, no items were generated, and no final independent medical
  review of generated items happened. `QGEN_NEXT_STEP = RUN_BOUNDED_CONTRAST_PREFLIGHT_ON_THE_36_FROZEN_
  OPPORTUNITIES_AGAINST_THE_EXISTING_CURATED_SEED_POOL_THEN_PROCEED_TO_GENERATION`.
- **Continuation session, 2026-09-07 (fresh-36 validation attempt, PARTIAL).** Verified Phase 0 (safe resume) and
  Phase 1-2 (interface reconnaissance + 3-opportunity integration probe) for real, from the same `60046f9`/
  `01eff40` design/audit commits; no rewrite, nothing discarded, nothing committed. `FROZEN_36_SHA256 =
  14c8491f3fb66c7e78c0f78f4692debb558229c36296f12ff09e5c200daa27fe`; structurally valid (36 rows, exact
  discipline distribution `{MED 16, OBGYN 6, PHELO 6, PED 2, PSY 3, SURG 3}`, 36 unique
  `learner_decision_id`s).
- **3-opportunity probe (`LD-C35-01`/MED, `LD-ONB2-PED-AOM-DX`/PED, `LD-OB53-01`/OBGYN) ran the REAL functions,
  not simulated ones: `onboarding_evidence.validate_decision_support` -> `EVIDENCE_READY` for all three (PED one
  freshly executed against its real review/catalog objects; MED/OBGYN confirmed already `EVIDENCE_READY`/`VALID`
  in the existing `v2_phase7_phase8_revalidation.json`), then `qgen_profiles_v2.resolve_profile` -> resolved
  cleanly for all three against `profile_snapshot_v2.json` (MEDICINE/PEDIATRICS/OBGYN, correct
  `option_set_archetype`/`demanded_response_class`). `INTERFACE_PROBE = PASS` for the decision-support ->
  Profile V2 leg.**
- **Real architectural finding, not a bug: the curated contrast-seed pools are anchored per specific pre-existing
  case, not a generic per-discipline library.** `build_retrieval_index`/`retrieve_profile_aware_contrasts`
  (`scripts/qbank/profile_contrast_retrieval.py`) work correctly when fed through the real
  `load_seed_enrichment`/`load_seed_stem_anchors` loaders (an initial probe that fed raw JSON `seeds` lists
  directly into `build_retrieval_index` failed with `AttributeError` -- that was a probe-script error, not a
  library defect; using the loaders resolved it). Measured directly: the three existing curated packs together
  hold 81 candidate rows -- `competitive_contrast_seed_pack_r4` (62 rows: OBGYN/PEDIATRICS/PHELO/PSYCHIATRY/
  SURGERY, zero MEDICINE), `..._g2_extensions` (5 rows: PHELO/PSYCHIATRY), `..._g2_targeted` (14 rows:
  MEDICINE only). Their combined `anchor_study_unit_id`s (`SU-C-21, SU-GS-76, SU-OB-54, SU-P-147, SU-PH-07,
  SU-PS-12`) have **zero overlap** with any of the 36 frozen addresses. Row filtering in
  `retrieve_profile_aware_contrasts` is by discipline/item_archetype/option_set_archetype/response-class token,
  not by anchor unit, so cross-case candidate discovery is structurally possible -- but the anchor-floor gate
  (`SAF_1`) then requires the new stem's own feature map to mark a competitor's specific anchor feature IDs
  `PRESENT`, and those IDs were authored for the *other* case (e.g. bronchiolitis `SU-P-147` features), making
  a real anchor match for an unrelated frozen-36 stem (e.g. AOM `SU-P-099`) unlikely by construction rather than
  by defect.
- **Phases 4-45 were not attempted this session and their numbers are NOT filled in below -- filling them in
  without doing the real per-opportunity clinical work (36 stem-feature maps, real retrieval runs, clinical
  contrast adjudication, stem authoring, blind solve, independent review) would be exactly the "invent clinical
  support to improve pilot yield" failure mode the milestone's own anti-hallucination contract prohibits.**
  Building 36 real stem-feature maps (Phase 4) requires genuine clinical-case authoring per opportunity, which
  is a substantially larger unit of work than interface reconnaissance and was not done. `PREFLIGHT_FEATURE_
  EXTENSION_REQUIRED` was not evaluated for any opportunity beyond the 3 probed.
  `QGEN_NEXT_STEP = BUILD_REAL_STEM_FEATURE_MAPS_FOR_ALL_36_FROZEN_OPPORTUNITIES_PHASE_4_THEN_RUN_BASELINE_
  RETRIEVAL_PHASE_5_MEASURING_ACTUAL_CANDIDATES_RETRIEVED_PER_OPPORTUNITY_AGAINST_THE_81_EXISTING_CURATED_ROWS
  _BEFORE_ANY_SUPPLY_WAVE`.
- **Fresh-36 feature-map + baseline-retrieval milestone (2026-09-07), from unchanged `60046f9`/`01eff40`.**
  `FROZEN36_FEATURE_BASELINE_MILESTONE = COMPLETE` for feature-map authoring + baseline measurement only; no
  generation was attempted (out of scope by the milestone's own instruction). Frozen-36 artifact re-verified
  byte-identical (`14c8491f...9daa27fe`, 36 rows, exact discipline distribution) and untouched.
- **36 stem-feature maps authored, BEFORE any retrieval was run**, in
  `research/qgen/onboarding/v2_frozen_pilot_stem_feature_maps.json`, reusing only existing `FEATURE_ANCHOR_
  SNAPSHOT_V4` feature IDs bound to each opportunity's own study unit, grounded strictly in that opportunity's own
  cited `claim_ids` (not the union of claims for the whole study unit). A fresh independent-review subagent with no
  authorship stake (`sonnet5-independent-review-2026-09-07-fresh36-feature-maps`) returned **26 APPROVED / 9
  REVISE / 1 UNCERTAIN** of 36 -- real catches, the dominant pattern being a citation-scope violation: a feature
  grounded in a claim cited by a *sibling* decision on the same study unit (e.g. the paired diagnosis/management
  decision) but not in *this* decision's own `claim_ids`. All 9 REVISE and the 1 UNCERTAIN were fixed by one bounded,
  bounded-to-the-reviewer's-exact-finding revision each (drop the out-of-scope feature, or downgrade an overclaiming
  role) -- no new claim was invented to rescue a map. Final: **36/36 approved**, 0 UNSAFE. Two opportunities
  (`LD-D12-02`, `LD-ONB2-PSY-AUD-INTERVIEW`) have **zero** grounded feature within their own citation scope after
  revision -- an honest `VOCABULARY_EXTENSION_REQUIRED` finding, not patched. 19 extension needs recorded across 17
  opportunities (13 `NEW_FEATURE`, 3 `NORMALIZATION_MISS`, 2 `AMBIGUOUS_FEATURE`, 1
  `EXISTING_FEATURE_NOT_BOUND_TO_UNIT`); zero were added to V4 this session. No `FEATURE_ROLE_SCHEMA_GAP`: every
  role used is already a V4 `supported_roles` token or its documented milestone-vocabulary equivalent
  (`SHARED_PRESENTATION_FEATURE` == `SHARED_PLAUSIBILITY_FEATURE`).
- **Baseline retrieval ran for real, for all 36**, via the actual `build_retrieval_index` /
  `retrieve_profile_aware_contrasts` (unpinned path, matching the prior session's probe) over the unmodified 81-row
  curated library (r4 62 + g2_extensions 5 + g2_targeted 14). `reports/qgen_fresh36_baseline_retrieval.json`.
  **`BASELINE_CONTRAST_READY = 0/36`.** 95 candidate encounters were indexed across the 36 opportunities; 83 reached
  the anchor gate and **all 83 were rejected `FEATURE_BOUND_TO_DIFFERENT_STUDY_UNIT`** -- no historical anchor
  relation exists for any of the 25 new study units, confirming the prior session's structural prediction with a
  real number rather than an assumption. The other 12 died at `ADM_1` (response-class mismatch) before reaching the
  anchor gate at all, for the 3 opportunities whose response class has no matching-tagged candidate in the library.
- **The measured finding that matters most: historical-seed transferability was checked directly, not assumed zero
  from ID non-overlap** (per the milestone's own instruction). Of 95 encounters across 40 distinct seeds (of 81 in
  the library), only **15 (16%) were clinically plausible competitors** for their new opportunity despite the
  missing anchor -- concentrated in three topic-adjacent pairs: constrictive pericarditis's real differential
  (acute pericarditis, PE) surviving from the old STEMI seed pack for exactly one opportunity (`LD-C35-01`);
  epidemiologic bias concepts (lead-time, length-time, healthy-screenee, overdiagnosis) genuinely on-topic for the
  two statistical-interpretation opportunities (`LD-PH11-01`, `LD-PH12-01`) but not the hazard-classification one
  (`LD-PH36-01`); and the old mastitis self-care pack for the postpartum-fever management opportunity
  (`LD-OB53-02`). The remaining 80/95 encounters (84%) were genuinely off-topic (ACS/chest-pain management
  competitors offered to skin-lesion decisions; screening-programme competitors offered to a pandemic-response
  decision; mastitis-workup competitors offered to a fibroid-imaging decision) -- retrieved only because they
  share a discipline/archetype/response-class token, not because they are clinically relevant.
- **Failure taxonomy, one primary cause per opportunity**: `ANCHOR_FLOOR` 20 (of which only 4 carry a clinically
  relevant blocked candidate; 16 were blocked by candidates that are also clinically irrelevant), `NO_CANDIDATE_
  DISCOVERY` 11 (the opportunity's own discipline/archetype/option-set-archetype combination has zero populated
  rows in the library at all), `RESPONSE_CLASS_FILTER` 3, `VOCABULARY_EXTENSION_REQUIRED` 2. Future-supply need:
  `NEW_CONTRAST_CANDIDATE_NEEDED` 30, `EXISTING_CANDIDATE_NEEDS_NEW_ANCHOR_RELATION` 4, `NEW_FEATURE_NEEDED` 2.
  Graph/FTS were not invoked (out of scope this milestone; only the curated seed-pool path was exercised).
- **`BASELINE_ASSESSMENT = EXISTING_LIBRARY_POORLY_TRANSFERS_NEEDS_ON_DEMAND_CONTRAST_SUPPLY`.** 30/36 opportunities
  need a genuinely new contrast candidate authored (not just a new anchor relation on an existing one); the
  81-seed library was authored entirely around the 6 old study units and does not clinically cover the 25 new
  ones. This is a stronger and more specific conclusion than the prior session's structural prediction, now
  measured rather than inferred.
- No shared production code changed (`git diff --stat -- scripts/ tests/` empty); only new research JSON artifacts
  (`v2_frozen_pilot_stem_feature_maps.json`, `qgen_fresh36_baseline_retrieval.json`) were added. Per policy, the
  full suite was not rerun (`FULL_SUITE = NOT_REQUIRED`). `COMMITS_CREATED = 0`; nothing was reset, cleaned, or
  overwritten; the frozen-36 roster is unchanged.
  `QGEN_NEXT_STEP = RUN_BOUNDED_SUPPLY_WAVE_TARGETING_THE_30_OPPORTUNITIES_THAT_NEED_A_NEW_CONTRAST_CANDIDATE
  _FIRST_THEN_THE_4_THAT_ONLY_NEED_A_NEW_ANCHOR_RELATION_THEN_THE_2_VOCABULARY_EXTENSIONS`.
- **Route-A supply wave attempted (2026-09-07), PARTIAL, from unchanged `60046f9`/`01eff40`.** Ran the deterministic
  Phase 0-2 steps for real: re-verified `FROZEN_36_SHA256` and the stem-feature-map SHA256 byte-identical to their
  declared values, then built `research/qgen/onboarding/v3_fresh36_supply_input_manifest.json` (joins the frozen
  feature maps with the baseline retrieval report per opportunity) and split the 36 into the measured
  `ROUTE_A=4 / ROUTE_B=30 / ROUTE_C=2` used by the prior session's own taxonomy (Route A = the 4 named opportunities
  whose baseline-blocked candidate was independently confirmed clinically relevant: `LD-C35-01`, `LD-PH11-01`,
  `LD-PH12-01`, `LD-OB53-02`; Route C = the 2 `feature_maps_with_zero_grounded_features` opportunities `LD-D12-02`,
  `LD-ONB2-PSY-AUD-INTERVIEW`; Route B = the remaining 30).
- **Only Route A (4 opportunities) was attempted this session; Route B (30) and Route C (2) were NOT attempted --
  each requires the same per-opportunity clinical-authoring depth that took a full session for smaller slices of
  this milestone historically, and there was not budget to do it without shortcutting the evidence-grounding
  requirement.** For Route A: one discovery+adjudication subagent identified historical candidates in the curated
  library and drafted 2 candidate anchor relations (`research/qgen/onboarding/v3_route_a_raw_supply.json`, hashed
  before review) -- `LD-C35-01` "Acute pericarditis" vs. key "Constrictive pericarditis", and `LD-PH12-01` "Healthy
  screenee (selection) bias" vs. key "Confounding" -- plus 2 REJECT verdicts on other historical candidates (PE for
  `LD-C35-01`; length-time bias and overdiagnosis for `LD-PH12-01`) and 2 outright `NO_SAFE_ITEM` opportunities
  (`LD-PH11-01`: best candidate collides with the likely key itself; `LD-OB53-02`: response-class/category mismatch,
  breast-care technique instructions vs. an infection-management next action).
- **A second, independent review subagent (no authorship stake, blind to desired yield) REJECTED both of the 2
  drafted relations** (`research/qgen/onboarding/v3_route_a_independent_review.json`), for concrete, verifiable
  reasons, not vibes: the `LD-C35-01` relation reused two `FROZEN_CANONICAL` V4 features hard-scoped to a different
  learner decision/study unit/response class (`QGEN-G2-MED-T01`/`SU-C-21`/`LOCALIZED_INFLAMMATION`, not
  `LD-C35-01`/`SU-C-35`/`PLAUSIBLE_DIAGNOSTIC_ENTITY`) with no repository authorization to repurpose them and a
  flipped required state, its cited claim's own `exact_reason` scopes it to an acute-pericarditis-vs-ACS contrast
  (not constrictive pericarditis), and the study unit's own evidence audit names restrictive cardiomyopathy, not
  acute pericarditis, as the canonical near-miss -- i.e. this is exactly the `FEATURE_BOUND_TO_DIFFERENT_STUDY_UNIT`
  failure mode the milestone exists to repair, still unresolved. The `LD-PH12-01` relation's cited source claim
  explicitly disclaims covering selection-bias subtypes, and the claimed corroborating library tag
  (`CONCEPT-R4-SU-PH-12-HEALTHY-SCREENEE`) is actually scoped to a *different* learner decision (lead-time bias /
  `SU-PH-07`) with a different, allocation-based discriminator -- it contradicts rather than corroborates the
  proposal, and unresolved second-key risk remains (healthy-screenee bias is itself commonly explained via a
  third variable, so "third variable present" does not cleanly rule it out).
- **`ROUTE_A_READY = 0/4`. All 4 Route-A opportunities remain `NO_SAFE_ITEM`.** No new feature or anchor relation
  was approved this session; **no `FEATURE_ANCHOR_SNAPSHOT_V5` was built** (there is nothing approved yet to append,
  and building an empty child snapshot would not be a real deliverable). `POST_PREFLIGHT_CONTRAST_READY` is
  unchanged from baseline at `0/36` because Route B (the 30 opportunities carrying the actual majority of future
  supply need) and Route C were not attempted. `SUPPLY_ASSESSMENT` for this session's own attempted scope =
  `NO_BETTER` (Route A specifically); the milestone as a whole remains `INSUFFICIENT_DATA` pending Route B/C.
  Per Phase 34, since zero opportunities are contrast-ready, the conditional generation gate was correctly NOT
  triggered -- no stems, blind solves, or final reviews were attempted, and none should be fabricated.
- Frozen-36 and stem-feature-map SHA256 re-verified byte-identical after this session; `feature_anchor_snapshot_v4.json`
  was only read, never written. Focused tests re-run clean (`128 passed` across the onboarding/qgen_profiles/
  vocabulary suites). No shared production code changed. `COMMITS_CREATED = 0`; nothing reset, cleaned, or
  discarded.
  `QGEN_NEXT_STEP = RUN_THE_SAME_BOUNDED_SUPPLY_WAVE_ON_ROUTE_B_30_OPPORTUNITIES_ONE_OR_A_FEW_AT_A_TIME_WITH_
  DISCOVERY_PLUS_INDEPENDENT_REVIEW_EACH_TIME_THEN_ROUTE_C_2_THEN_BUILD_V5_ONLY_FROM_WHATEVER_SURVIVES_REVIEW`.
- **Route-B/C supply wave attempted (2026-09-07), PARTIAL, first bounded slice, from unchanged `60046f9`/`01eff40`.**
  Re-verified both frozen SHA256 values byte-identical before starting. Attempted 8 of the 32 remaining Route-B/C
  opportunities (`LD-D04-01`, `LD-D05-01`, `LD-D05-02`, `LD-D07-01`, `LD-D07-02`, `LD-D08-01`, `LD-D12-01` [ROUTE_B],
  `LD-D12-02` [ROUTE_C]) -- the dermatology cluster on SU-D-04/05/07/08/12, chosen because their own cited evidence
  claims explicitly name the candidate differential concepts. The other 22 ROUTE_B and 1 ROUTE_C opportunity were
  NOT attempted this session. Raw supply drafted and hashed before review
  (`research/qgen/onboarding/v4_route_bc_raw_supply.json`): 10 candidates drafted, 6 with a proposed relation, 4
  self-rejected `NO_SAFE_ITEM`.
- **A fresh independent-review subagent with no authorship stake** reviewed the 6 proposed relations
  (`research/qgen/onboarding/v4_route_bc_independent_review.json`): **5 APPROVED, 1 REJECTED**. The rejection
  (`LD-D05-02`) was a genuine citation-scope error -- the candidate cited `SRC-MED-045-EX-01` for an operative
  quote that actually lives in `SRC-MED-045-REC-01` -- the same failure mode Route A's independent review caught.
  This is the first session in this milestone's history where independent review approved any new Route-B/C
  candidate. A separate corroboration error was also caught (the raw-supply file mislabels
  `SRC-MED-048/045/051/049` as living in `source_packet_population_srb_006.json`; they actually live in
  `source_packet_population_srb_007.json`) -- recorded here rather than editing the frozen-post-review raw file.
- **`FEATURE_ANCHOR_SNAPSHOT_V5` was built for real**, via the actual, deterministic
  `scripts/qbank/vocabulary_onboarding.build_extended_snapshot` (no hand-authored rows), parented on V4:
  `research/qgen/onboarding/feature_anchor_snapshot_v5.json`, content SHA256
  `7d0952df5554634f5dacb6a928258a4593c4a817ee897e888d68b6bacaffe273`, 145 features (+1 new), 164 anchor relations
  (+2 new). Only 2 of the 5 approved relations were promoted: for `LD-D07-01`, `LD-D07-02`, and `LD-D08-01`, the
  reviewer approved the underlying clinical/citation soundness, but the only available reused V4 feature in each
  case is diagnostic **of the key**, not of the candidate -- registering it at `required_state=PRESENT` on the
  candidate would assert a medically backwards claim, so those 3 were correctly held back as a self-caught
  modeling error rather than promoted (see `research/qgen/onboarding/v5_route_bc_snapshot_build_inputs.json`).
- **Replay (Phase 19) was done by code-path verification of `build_retrieval_index` /
  `feature_anchor_registry.snapshot_anchor_index`/`resolve_seed_anchors`, not literal re-execution, and found a
  real architectural blocker**: `build_retrieval_index` (`scripts/qbank/profile_contrast_retrieval.py:140-141`)
  only iterates `seed_id` rows already present in the 3 frozen curated seed packs (81 rows total). Both new V5
  anchor relations use brand-new seed IDs that are not rows in any curated pack, so pinning V5 cannot change their
  retrieval outcome at all -- **`POST_PREFLIGHT_CONTRAST_READY` stays `0/36`, unchanged from baseline**, and this is
  provable from the code rather than assumed. Introducing a genuinely new competitor requires authoring a new
  curated-seed-pack-shaped file (targets/seeds + `.enrichment.json` + `.stem_anchors.json`, independently reviewed
  and hash-frozen, matching `competitive_contrast_seed_pack_g2_targeted.json`'s schema) -- a V4/V5 registry
  extension alone is necessary but not sufficient.
- **`SUPPLY_ASSESSMENT = PROMISING_BUT_STRUCTURALLY_BLOCKED`** for this session's attempted scope: the first real
  clinical-review approval progress in the milestone's history, but zero movement on contrast-readiness because of
  the seed-pack architecture gap above, not because the clinical candidates were unsound.
  `PRODUCTION_READINESS = NOT_READY_FOR_SCALEOUT`. Generation (Phase 23+) was correctly not attempted
  (gate not met). Focused tests re-run clean (98 passed, 0 failed;
  `test_onboarding_v2_build.py`/`test_qgen_profiles_v2.py`/`test_vocabulary_onboarding.py`/
  `test_profile_contrast_retrieval.py`/`test_stem_anchor_floor.py`); no shared code changed, so the full suite was
  not rerun per policy. `COMMITS_CREATED = 0`; nothing reset, cleaned, or discarded; frozen-36 and stem-feature-map
  files re-verified byte-identical and untouched. Full detail in
  `reports/qgen_route_bc_preflight_wave_report.json`.
  `QGEN_NEXT_STEP = EITHER_(A)_AUTHOR_A_NEW_CURATED_SEED_PACK_FILE_TARGETS_SEEDS_PLUS_ENRICHMENT_PLUS_STEM_ANCHORS_
  FOR_THE_2_PROMOTED_V5_CANDIDATES_THEN_THE_REMAINING_24_UNATTEMPTED_ROUTE_B_C_OPPORTUNITIES_THE_ONLY_WAY_TO_
  INTRODUCE_A_GENUINELY_NEW_RETRIEVABLE_COMPETITOR_OR_(B)_FOR_A_GIVEN_OPPORTUNITY_FIND_A_REAL_EVIDENCE_GROUNDED_
  SHARED_PLAUSIBILITY_FEATURE_WITHIN_ITS_OWN_CITATION_SCOPE_AND_PROPOSE_IT_AS_AN_INDEPENDENTLY_REVIEWED_EXTENSION_
  TO_THAT_OPPORTUNITYS_FROZEN_STEM_FEATURE_MAP_THEN_RETEST_THE_ANCHOR_GATE`.
- **Route-B/C supply wave, second bounded slice (2026-09-07), from unchanged `01eff40`.** Re-verified both frozen
  SHA256 values byte-identical before starting (`FROZEN_36_SHA256 = 14c8491f...`, stem-feature-map
  `dcf569fe...`) -- no mismatch. Recomputed the remaining Route-B/C set directly from
  `research/qgen/onboarding/v3_fresh36_supply_input_manifest.json` rather than trusting the prior entry's "22
  ROUTE_B + 1 ROUTE_C" arithmetic: the actual remaining set is **24** (23 ROUTE_B + 1 ROUTE_C), listed in
  `research/qgen/onboarding/v4_route_bc_wave2_raw_supply.json#remaining_opportunity_ids`. Attempted all 24.
- **Cheap filter before any clinical adjudication**: called the real
  `scripts/qbank/profile_contrast_retrieval.build_retrieval_index` over all 3 frozen curated seed packs (r4,
  g2_extensions, g2_targeted; 81 rows total) and enumerated every distinct `anchor_study_unit_id`/`anchor_topic`
  pair the curated library actually contains. Finding: only 6 topics exist in the entire library -- SU-C-21 (ACS),
  SU-GS-76 (appendicitis), SU-OB-54 (mastitis), SU-P-147 (bronchiolitis), SU-PH-07 (screening bias), SU-PS-12
  (depression) -- and **none** overlap with, or are clinically related to, any of the 24 remaining opportunities'
  own study units (the D-cluster dermatology, consent/MAID law, OBGYN contraception/hysterectomy/imaging, AOM,
  PHELO programme/hazard, alcohol-use-disorder pharmacology, croup). The `baseline_indexed_count>0` rows the
  manifest shows for several of these (e.g. `LD-D21-01` at 3, `LD-PH34-01` at 4) are matches on
  discipline/item-archetype/option-set-archetype tags only, not on any real clinical relationship -- exactly why
  `build_retrieval_index`'s `SAF_1` rule correctly refuses them all.
- **Zero candidates were proposed this wave** (`research/qgen/onboarding/v4_route_bc_wave2_raw_supply.json`,
  frozen `raw_supply_sha256_before_review = 0da536d141b84db46d66ff2fb599cc1fecbfc80dd66d7630399d7ce3cfe2a626`,
  self-verified against its own content). **Option (b)** (an evidence-grounded `SHARED_PLAUSIBILITY_FEATURE`
  extension to a frozen stem-feature-map, to make an existing curated seed's anchor gate fire) is
  `VOCABULARY_EXTENSION_BLOCKED` for all 24: it requires an existing curated seed that is genuinely plausible as a
  competitor, and per the cheap filter above none exists -- forcing one would fabricate a clinical relationship,
  which the anti-hallucination contract forbids. **Option (a)** (author a whole new curated-seed-pack-shaped file)
  was judged `NOT_TRACTABLE_WITHIN_THIS_BOUNDED_WAVE` for the same reason the prior session gave for the
  dermatology cluster -- a materially larger unit of work than a bounded discovery-plus-review pass -- and was not
  attempted. No independent-review subagent was spawned (nothing to adjudicate).
- **No V5/V6 registry change**: `feature_anchor_snapshot_v5.json` is untouched; nothing was approved to promote.
  **`POST_PREFLIGHT_CONTRAST_READY` stays `0/36`, unchanged** -- `NOT_REACHED`. Phase 23+ generation was correctly
  not attempted; no stems, blind solves, or final reviews were fabricated. Frozen-36, stem-feature-map, and
  `feature_anchor_snapshot_v4.json` re-verified byte-identical/untouched. Focused tests re-run clean (`98 passed`,
  same five suites as the prior wave); no shared code changed, so the full suite was not rerun. `COMMITS_CREATED =
  0`; nothing reset, cleaned, stashed, or pushed. Full detail in
  `reports/qgen_route_bc_preflight_wave2_report.json`.
  `QGEN_NEXT_STEP = AUTHOR_ONE_NEW_CURATED_SEED_PACK_SHAPED_FILE_TARGETS_SEEDS_PLUS_ENRICHMENT_PLUS_STEM_ANCHORS_
  FOR_ONE_STUDY_UNIT_FROM_THE_REMAINING_24_AS_ITS_OWN_BOUNDED_TASK_INDEPENDENTLY_REVIEWED_AND_HASH_FROZEN_BEFORE_
  ANY_FURTHER_DISCOVERY_WAVE_SINCE_OPTION_B_IS_NOW_SHOWN_EXHAUSTED_FOR_ALL_32_ROUTE_BC_OPPORTUNITIES_ACROSS_BOTH_
  SESSIONS`.
- **Generalized seed-pack onboarding milestone completed (2026-09-07), from starting HEAD `01eff40984bee76418c7fab82a1ded9fbfa2d9e5`.** The root-cause regression reproduced that a reviewed relation and positive anchor are unreachable when the candidate has no row in one of the three historical packs. `build_retrieval_index` now accepts only explicitly supplied, schema-validated, independently approved additional packs; no directory scanning or implicit latest-pack behavior was added. Historical-only replay remains identical at 81 rows, rejected and uncertain proposals remain unavailable, exact learner-decision plus study-unit scope prevents leakage, and the existing anchor floor and second-key ceiling still pass their regression coverage. The historical packs, frozen 36 (`14c849...`), frozen maps (`dcf569...`), and V5 snapshot (`7d0952...`; 145 features/164 anchors) remain unchanged.
- The deterministic development-12 selection is frozen at two opportunities per discipline after excluding Route A. Discovery produced 31 raw candidates and six seed proposals; independent clinical review approved four AOM seeds, rejected one backwards-anchor dermatology seed, and marked one AUD seed uncertain. The explicit versioned development pack contains only the four approved rows. Replay improved development-12 from `0/12` to `1/12`, and full development-36 replay reached `1/36` with zero scope leakage (`PED 1/2`; all other disciplines zero). One three-competitor contrast set was frozen and one original item was generated without retry. Blind solve selected acute otitis media with high confidence and no ambiguity; post-stem validation retained three `LIVE_BUT_INFERIOR` competitors; deterministic option/rationale gates passed; independent final medical review accepted the item with all ten required defect checks passing.
- Current classification is **`DEVELOPMENT_REGRESSION_SET`**, not a pristine holdout, and production readiness is **`NOT_ASSESSED_ON_CURRENT_36`**. The architecture decision is **`SEED_PACK_ONBOARDING_VALIDATED`**, while supply economics remain **`INSUFFICIENT_DATA`** because cross-unit reuse has not been observed. Canonical outputs are `research/qgen/onboarding/v6_development_seed_registry.json` and `reports/qgen_seed_pack_onboarding_milestone.json`. `QGEN_NEXT_STEP = BUILD_NEW_FRESH_HOLDOUT_PILOT`. No commits were created and `CLAUDE.md` was not changed.
- Final verification: focused onboarding/retrieval coverage passed `105/105`. The single canonical full-suite run finished `1605 passed, 1 failed`; the sole failure was the known unrelated source-research coordinator classification test (`test_discovery_classifies_dirty_worktree_retry_and_committed_branch_awaiting_integration`), with zero new failures. The deterministic copyright audit found zero 12-word-or-longer Toronto Notes overlap across all six authored evidence/item artifacts.
- **Fresh holdout-24 milestone attempted and closed fail-closed (2026-09-07), from unchanged starting HEAD `01eff40984bee76418c7fab82a1ded9fbfa2d9e5`.** A deterministic historical exclusion contains 68 decision entries across 31 study units; 895 fresh CORE/IMPORTANT candidates remained. The roster was frozen before seed inspection at 24 distinct new study units, exactly 4 each MED/PED/OBGYN/SURG/PSY/PHELO (`fresh_holdout_24_opportunities.json`, content SHA256 `6b352c3d377e272fc2c5def60fbf659bc6e6bc01ace0dbb64882e00c2daff805`). The profile, feature/anchor, development seed registry, Clinical Contrast V2, retrieval, and generator inputs were explicitly hash-pinned. Existing approved historical plus development seeds produced `0/24` contrast-ready opportunities and zero reusable candidates.
- Two predetermined 12-opportunity waves were executed without opportunity substitution or generation retry. Bounded discovery measured 144 raw candidates and 48 proposals. A provisional, non-independent pass incorrectly admitted 36 candidates and produced 12 apparent contrast-ready cases (Wave 1: 7; Wave 2: 5), leading to 12 one-attempt stems. A genuinely independent high-reasoning review then found that the purported pre-retrieval feature/seed review was not independent: 33/36 packed seeds were REJECTED and 3/36 UNCERTAIN, with zero approved. Dominant concrete defects were wrong response-capability tags, backwards or absent positive candidate anchors, second-key risk, silence-as-absence, and conditional rules presented as live patient-specific competitors. Ten feature maps have concrete safety defects and the remaining 14 could not be independently certified from the minimal supplied evidence context. Because that review occurred after provisional retrieval, `HOLDOUT_CONTAMINATED = YES`; no repair, retry, opportunity replacement, or architecture change was made.
- Valid final state: existing-seed-ready `0/24`; post-new-seed-ready `0/24`; generated 12; independently final-reviewed 12; accepted 0; rejected 12; no-safe 12; safe yield, generation acceptance, and final-review acceptance all 0. Primary earliest-cause taxonomy sums to 24: `FEATURE_MAP_UNSAFE=10`, `SEED_REVIEW_REJECTED=4`, `NO_SEED_CANDIDATE=10`. `SYSTEMATIC_DEFECT_GE_20_PERCENT=YES`. Seed economics: 0 approved, 45 rejected (including the 12 pre-pack rejections), 3 uncertain, 2.0 proposals/opportunity, 0 approved/opportunity, 24/24 requiring new seeds, no seed/relation/anchor/cross-discipline reuse, 18 targeted external research requests, zero graph-unique or TN-FTS-unique approvals; classification `INSUFFICIENT_DATA`. Serialized semantic context measured median 1,935 chars and p95 3,496 chars; no token or dollar figure was fabricated. Assessment: `HOLDOUT_CONTAMINATED`; dominant bottleneck: late independent review plus unsafe feature/anchor authoring; `QGEN_NEXT_STEP = DIAGNOSE_HOLDOUT_FAILURE`.
- Canonical holdout report: `research/qgen/holdout/fresh_holdout_24_milestone.json`, content SHA256 `fd2ba91eaefd627b1db4790e3a2bfbfa4f323996f24cab528492e1586a501b07`. Copyright audit PASS after canonical scan returned REVIEW solely for a 12-token Canada.ca URL path match; manual inspection confirmed no Toronto Notes prose and all generated items are original. Final focused coverage passed `123/123`. The single final full-suite run finished `1615 passed, 1 failed`; the sole failure is the same known unrelated source-research coordinator classification test. No historical frozen artifact or `CLAUDE.md` was modified, no commit was created, and the current WIP was preserved.
- **Fresh Holdout 24 contamination diagnosis and lifecycle repair completed (2026-09-08), from unchanged starting HEAD `01eff40984bee76418c7fab82a1ded9fbfa2d9e5`.** The run is permanently classified `CONTAMINATED_DEVELOPMENT_REGRESSION_SET`; its original roster, feature maps, 12 item drafts, and milestone remain byte-identical. Root cause is `GATE_EXECUTED_TOO_LATE`: `fresh_holdout_24._seed_pack` minted author-embedded `APPROVED` review objects and frozen packs, `compose_execution_artifacts` consumed them for retrieval and item construction, and `_apply_independent_holdout_audit` invalidated them only afterward. Secondary causes are `PROVISIONAL_OBJECT_ADMITTED`, `REPORTING_STATE_MISMATCH`, `REVIEW_CONTRACT_MISMATCH`, and `AUTHORING_CONTRACT_MISMATCH`.
- Canonical reconciliation counts only final independent approvals, frozen coherent contrast sets, and generator callbacks executed after a passed central precondition. Recomputed H24 metrics are feature-ready `0/24`, seed-ready `0/24`, contrast-ready `0/24`, stems generated `0`; all 12 physical drafts are `PREMATURE_GENERATION` / `INVALID_PIPELINE_OUTPUT`, so valid generated and accepted denominators are both zero and the contaminated run cannot estimate safe yield. The 48-proposal taxonomy is deliberately provenance-conservative: 12 explicit `DUPLICATE_OR_ALIAS`, 36 `INSUFFICIENT_INFORMATION` because the late audit serialized verdict IDs but no per-seed reasons. Those 12 structural rejects are catchable before review, an estimated `26.7%` reduction against 45 rejections; 36 genuine semantic judgements remain.
- `scripts/qbank/generation_lifecycle.py` now owns the explicit lifecycle states and central `assert_generation_ready` boundary. The real H24 composition path refuses missing lifecycle contexts before item construction; the gate requires approved and pinned decision evidence and feature maps, a pinned profile, one frozen key, at least three independently approved/pinned viable seeds with approved relations and positive non-backwards anchors, a frozen coherent no-second-key contrast set, and a pinned ready blueprint. `seed_proposal_contract.py` rejects only deterministic structural defects and requires the author fields the reviewer consumes. The preserved AOM development control passes the same central gate without medical re-authoring.
- Regression-24 replay is lifecycle-consistent: `0 <= 0 <= 0`, zero generator callbacks, and 24 `NO_SAFE_ITEM` terminal states. Focused safety coverage is `190 passed / 0 failed`; the final full suite is `1646 passed / 1 failed`, with the sole failure the known unrelated source-research coordinator `AWAITING_INTEGRATION` versus `INTEGRATED` classification test, so `NEW_TEST_FAILURES=0`. Canonical copyright scan of five new artifacts is PASS with zero Toronto Notes token overlap. The next selection inventory is prepared but unselected/unconsumed, with 871 eligible rows after excluding the contaminated roster. `READY_TO_FREEZE_NEW_HOLDOUT=YES`; recommend `FRESH_HOLDOUT_18` because the prior run required 24 feature reviews plus 48 seed proposals and serialized context median/p95 was 1,935/3,496 characters. `QGEN_NEXT_STEP = FREEZE_AND_RUN_NEW_FRESH_HOLDOUT`.
- **Fresh Holdout 18 generalization and seed-economics milestone completed fail-closed (2026-09-08), from unchanged starting HEAD `01eff40984bee76418c7fab82a1ded9fbfa2d9e5`.** The deterministic roster was frozen before contrast inspection at exactly 3 each MED/PED/OBGYN/SURG/PSY/PHELO (`fresh_holdout_18_opportunities.json`, content SHA256 `e819f3f2eca6aae8057e1f578652c244af80c39377dfab4eef58854afb1a84dd`), with three fixed six-case waves. The architecture freeze SHA256 is `57e5dac9fba86a920cc7591e06f840d7899d82c5d82bb229c2ca2290ce575999`; it remained unchanged, every preserved H24 artifact recomputed byte-identically, and `HOLDOUT_CONTAMINATED=NO`.
- Decision-specific evidence was `3/18 EVIDENCE_READY`, `2 ALIGNED_PARTIAL`, `11 EVIDENCE_MISSING`, and `2 OUT_OF_SCOPE`. The three evidence-ready cases (MED chest-pain differential, OBGYN amenorrhea, PHELO culturally safe care) were feature-authored before retrieval and reviewed in one fresh independent Sol-high context. All three were `REJECTED`: none of the 871 eligible fresh units has a unit/decision binding in frozen Feature/Anchor Snapshot V5, so the evidence-entailing load-bearing propositions cannot be expressed without changing the frozen architecture; the reviewer also identified missing broader discriminators. The early gate therefore held: `FEATURE_READY=0/18`, existing-seed baseline eligible cases `0`, new seed discovery/review `0`, contrast-ready `0`, blueprints `0`, generator callbacks/stems/final reviews/accepted items `0`, and all 18 terminate `NO_SAFE_ITEM` without retry.
- Earliest failure taxonomy is exhaustive: `EVIDENCE_NOT_READY=15`, `FEATURE_MAP_REJECTED=3`. Wave evidence-ready counts were 2/6, 0/6, and 1/6; every discipline ended 0 accepted. Seed/relation/anchor reuse and new external research requests were all zero because the seed stage was correctly not reached; contrast-supply economics are `INSUFFICIENT_DATA`. Review economics: 3 feature-review rows, 0 seed rows, 0 final-item rows, serialized context median/p95 1,594/1,694 characters. `SAFE_YIELD=0/18`; generation/final-review acceptance are not applicable because both denominators are zero; accepted-item safety is `NO_ACCEPTED_ITEMS`.
- Assessment: `BLOCKED_BY_EVIDENCE`; `NEXT_DOMINANT_BOTTLENECK=DECISION_EVIDENCE_READINESS`. The subordinate architecture-generalization finding is `FROZEN_FEATURE_SNAPSHOT_HAS_NO_BINDINGS_FOR_FRESH_UNITS` (3/3 evidence-ready cases), recorded without modifying the architecture. `QGEN_NEXT_STEP = RESOLVE_BLOCKER`: prepare independently reviewed decision evidence and a pre-holdout feature-vocabulary onboarding snapshot for genuinely fresh units before attempting another holdout; do not reinterpret this cohort as a seed-economics estimate. Canonical report: `reports/qgen_fresh_holdout_18_generalization.json`, content SHA256 `39a0c9b7378a742740090e2361ed72ecb31dfdd70e8466f4aad84f65d93bf764`. Copyright audit PASS with zero Toronto Notes overlap. Focused tests `200/0`; full suite `1656/1`, solely the same known unrelated source-research coordinator classification failure (`NEW_TEST_FAILURES=0`). No commit was created and `CLAUDE.md` was unchanged.
- **Generalized pre-holdout decision-evidence and feature-readiness milestone completed (2026-09-08), from unchanged starting HEAD 01eff40984bee76418c7fab82a1ded9fbfa2d9e5.** The prior fresh 18 is now classified as FRESH_PREREQUISITE_DIAGNOSTIC_18 without changing any of its artifacts. An explicit 73-unit historical-development exclusion union was applied to the existing fresh inventory, then 90 development units were selected outcome-blind at exactly 15 per discipline with canonical taxonomy diversity. Exactly one legitimate MCCQE-level learner decision was audited per unit. Twenty selected units had a repository packet, but only eight decisions were independently evidence-ready before new research; 11 packet-ready units remained decision-not-ready after the wave, a 0.55 packet false-positive rate.
- Forty bounded, decision-only Canadian evidence requests produced 40 additional independently approved decisions. Final decision readiness is exactly 8 each MED/PED/OBGYN/SURG/PSY/PHELO (48 total); other candidates fail closed as EVIDENCE_MISSING. Append-only FEATURE_ANCHOR_SNAPSHOT_V6 has content SHA256 25ddd3acc23fbd8f0e46119954c2b024d60e888362f263ebad22cd29f7122482, parent V5 unchanged. It adds 48 approved minimal trigger features and 57 approved unit/decision bindings, with 2 features reused across at least two units, 0 across multiple disciplines, 1.0 new feature per ready unit, and 1.1875 bindings per ready unit. All 48 approved decisions revalidate FEATURE_READY; vocabulary growth is MANAGEABLE.
- Historical anchorless and second-key controls remain rejected, the AOM development control still passes the centralized generation precondition, and the lifecycle invariant remains PASS. Copyright is PASS: the canonical scanner's only overlap was bibliographic source-title/URL metadata in the claim catalog, while normalized claim statements had zero 12-word Toronto Notes matches. Focused verification passed 97/97; the final full suite passed 1667 with the sole known unrelated source-research coordinator classification failure (NEW_TEST_FAILURES=0). The future eligibility inventory contains 753 untouched units (MED 376, PED 87, OBGYN 42, SURG 220, PSY 11, PHELO 17) and selects none. READY_FOR_NEW_HOLDOUT=YES; recommend 18 because 40/48 ready decisions still required research. NEXT_DOMINANT_BOTTLENECK=NEW_FRESH_HOLDOUT_EXECUTION; QGEN_NEXT_STEP = FREEZE_AND_RUN_NEW_FRESH_HOLDOUT. No commit was created and CLAUDE.md was unchanged.
- **Fresh Operational Holdout 18 completed fail-closed (2026-09-08), from unchanged starting HEAD `01eff40984bee76418c7fab82a1ded9fbfa2d9e5`.** The outcome-blind roster is frozen at exactly three untouched study units per discipline and three fixed waves (`fresh_operational_holdout_18_opportunities.json`, content SHA256 `d299edadf948d3f97d7263c9f9faf7538eb5a9f61e1aa264e19ab5a8367364f5`). The architecture freeze SHA256 is `bc91bf53af78737c7fd67f58724078fccf12b36099ecc6cfa121d827c2d73df5`; all 120 architecture pins and 47 historical-artifact pins remain byte-identical. `HOLDOUT_CONTAMINATED=NO`, with no substitution, retry, provisional admission, shared contract change, or historical-artifact edit.
- Zero-shot independently validated evidence readiness was `0/18`. Four selected units were packet-ready, but all four were decision-not-ready after independent validation (packet false-positive rate 1.0); the pre-review baseline had tentatively classified three as ready and one as packet-ready but decision-not-ready. One bounded pass made 15 load-bearing research requests and independently approved 12 decisions (`12/18` after research); 5 were rejected and 1 uncertain. V6 represented none of those 12 (`0/18`). Twelve minimal one-feature additions were proposed; independent review approved 10 and marked 2 uncertain. Append-only `FEATURE_ANCHOR_SNAPSHOT_V7`, parent V6 unchanged, has content SHA256 `0840ce0b99940172dd560fdcbec8be1e7fc1f493f6afdb4521b0726dc63632cc`, adding 10 features and 10 unit/decision bindings. All 10 final maps passed a separate early independent review. Feature readiness is `10/18`; V6 reuse is zero and feature economics are `MANAGEABLE_ON_DEMAND` because the bounded cost stayed at one proposal per evidence-ready opportunity with fail-closed uncertainty.
- Existing-seed reuse was measured only after map review. Across 109 eligible pre-holdout historical/development seed rows, exact scope and positive-anchor joins produced zero survivors and `0/18` existing-seed-ready. The single bounded structural discovery pass over the 10 feature-ready cases found 50 raw topic-family candidates. Cheap response-class and evidence-binding filters rejected all 50 before semantic review, so zero seed proposals, approvals, relations, anchors, or holdout seed packs were admitted and final contrast readiness remained `0/18`. No blueprint became ready; the central generation precondition therefore had zero callbacks and no stems, options, blind solves, or final item reviews were fabricated.
- All 18 opportunities have exactly one earliest terminal failure: `EVIDENCE_NOT_READY=6`, `FEATURE_MAP_UNCERTAIN=2`, `NO_SEED_CANDIDATE=10`. Accepted `0`, rejected final items `0`, `NO_SAFE_ITEM=18`, safe yield `0/18`; generation and final-review acceptance are not applicable at zero denominators, and accepted-item safety is `NO_ACCEPTED_ITEMS`. Copyright scan passed with zero 12-word Toronto Notes overlap. Focused architecture/lifecycle coverage passed `127/127`; deterministic validation passed 27 artifact hashes, V7 reproducibility/append-only preservation, lifecycle arithmetic, failure-taxonomy reconciliation, roster/architecture/historical integrity, and `git diff --check`. No shared executable code changed after freeze, so the full suite is `NOT_REQUIRED`; `NEW_TEST_FAILURES=0`. Canonical report: `reports/qgen_fresh_operational_holdout_18_generalization.json`, content SHA256 `8d52e8c0b9cb1cb45223377d612fcaea0ee9988b7834393af1fb8d112332c2c0`.
- `GENERALIZATION_ASSESSMENT=BLOCKED_BY_CONTRAST_SUPPLY`; the systematic finding is `NO_REUSABLE_OR_EVIDENCE_BOUND_SEED_SUPPLY_FOR_ANY_OF_10_FEATURE_READY_OPPORTUNITIES`. `CONTRAST_SUPPLY_MODEL=EXCESSIVE_PER_OPPORTUNITY_AUTHORING`; `NEXT_DOMINANT_BOTTLENECK=SAFE_CONTRAST_SEED_SUPPLY_AND_CANDIDATE_RELATION_EVIDENCE`; `QGEN_NEXT_STEP = IMPROVE_CONTRAST_SUPPLY_ECONOMICS`. Do not implement that next milestone as part of this holdout. No commit was created and `CLAUDE.md` was unchanged.
- **Contrast-supply root-cause diagnosis completed (2026-09-08), PARTIAL, from unchanged starting HEAD `01eff40984bee76418c7fab82a1ded9fbfa2d9e5`.** H18's own `EXCESSIVE_PER_OPPORTUNITY_AUTHORING` hypothesis is **refuted**. All 50 raw H18 candidates came from exactly one discovery source (`CANONICAL_TN_STRUCTURAL_SIBLING`, blanket TN chapter-adjacency enumeration); the four decision-aware sources ahead of it in `discovery_order` all returned zero. Mechanical reconstruction (`reports/qgen_contrast_supply_diagnosis_and_repair.json`) found exactly two rejection reasons across the 50: `WRONG_RESPONSE_CLASS` 42 and `MISSING_EVIDENCE_BINDING` 8 (13 other taxonomy categories are zero).
- Tracing the real, committed cheap filter (`scripts/qbank/contrast_supply.filter_candidates`) proved it only ever emits `RESPONSE_CLASS_MISMATCH`/`GRANULARITY_MISMATCH` and has no evidence/anchor requirement; that requirement is correctly enforced much later, only in `admit_relation`/`_enforce_anchor_sufficiency`, post-authoring and post-independent-review. No committed script produces the H18 bounded-discovery artifact -- it is hand-authored, and its `MISSING_EVIDENCE_BINDING` label is a rejection reason the real contract never authorizes at the cheap-filter stage.
- A known-good counterfactual (the AOM development control, `SEED-V6-AOM-OME`) run through the real unmodified `filter_candidates` in its pre-authoring shape was `KEPT` (PASS); the same control would have been wrongly killed by H18's ad hoc `MISSING_EVIDENCE_BINDING` gate. A bounded semantic spot audit of 12 of the 50 candidates (careful clinical reasoning, one at a time, no external API) found 6 `CLINICALLY_PLAUSIBLE_FOR_SEMANTIC_AUTHORING` (5 of 6 sampled from the `MISSING_EVIDENCE_BINDING` bucket), 3 `CLEARLY_DEAD`, 1 `POTENTIAL_SECOND_KEY`, 1 `WRONG_DECISION`, 1 `UNCERTAIN` -- confirming most `WRONG_RESPONSE_CLASS` rejections were correct (genuinely off-topic chapter siblings) while most `MISSING_EVIDENCE_BINDING` rejections were premature.
- **`DOMINANT_ROOT_CAUSE = DISCOVERY_PRECISION_TOO_LOW`** (84% of rejections, 8/10 opportunities with candidates got 100% response-class-mismatch because discovery never targeted the key decision's own response class), with a confirmed secondary **`EVIDENCE_BINDING_TOO_EARLY`** pipeline-ordering defect (16% of rejections, 2/10 opportunities: PSY-01, PHELO-03). TDD repair in `scripts/qbank/contrast_supply.py`: added `AUTHORIZED_PRE_SEMANTIC_REJECTION_REASONS`, `PREMATURE_AUTHORING_REJECTION_REASONS`, and `reclassify_premature_authoring_rejections()` (4 RED tests added to `tests/test_contrast_supply.py`, confirmed failing via `ImportError` before the fix, all green after). `filter_candidates` itself is unmodified; `admit_relation`/`_enforce_anchor_sufficiency` are unmodified and still gate APPROVED SEEDS on independent review plus `EVIDENCE_VERIFIED`.
- Replaying the repaired contract over the 50 H18 candidates (funnel-only, explicitly **not** a new holdout acceptance rate) gives `H18_RAW_CANDIDATES_NOW_REACHING_SEMANTIC_STAGE = 8` across `FOH18-PSY-01` (5) and `FOH18-PHELO-03` (3); the other 42 remain correctly rejected. A development-12 roster was frozen (2 per discipline, deterministic `development_id`-sort rule) from the 48-row `DECISION_EVIDENCE_READY`+`FEATURE_READY` pool in `research/qgen/readiness/development_feature_maps_v6.json`, disjoint from H18, the AOM control, and historical pilots (`development_12_ids_sha256 = a20732467b62428dd2388f9bb21820c8ee501e9b3457dbcb0a8d28f6931a6509`). Existing-seed baseline via deterministic study-unit-scope membership across all 4 existing curated/development packs is `DEVELOPMENT_EXISTING_SEED_READY = 0/12` (no existing pack scopes any of the 12 units).
- **Phases 14-24 (bounded discovery, relation authoring, independent seed review, development seed pack, retrieval replay, conditional item generation/blind-solve/final-review for the development-12) were explicitly NOT attempted this session** -- each requires the same per-opportunity clinical-authoring depth that took full prior sessions for comparable or smaller slices; compressing it here would mean less scrutiny than the anti-hallucination contract requires. Reported `PARTIAL` rather than fabricated. `SHARED_CODE_CHANGED=YES`; full suite `1676` run: `1675 passed, 1 failed` (the same known unrelated `test_discovery_classifies_dirty_worktree_retry_and_committed_branch_awaiting_integration` source-research-coordinator failure), `NEW_TEST_FAILURES=0`. Focused `tests/test_contrast_supply.py` plus adjacent retrieval/lifecycle suites: `203 passed`. No historical/frozen artifact was modified (H18's own report/roster/architecture-freeze/V7 hashes all reverified byte-identical), no commit was created, `CLAUDE.md` was unchanged. Canonical report: `reports/qgen_contrast_supply_diagnosis_and_repair.json`.
- `READY_FOR_NEW_OPERATIONAL_HOLDOUT = NO` (development contrast-readiness has not yet been demonstrated for any opportunity -- Phases 14-24 remain to run). `QGEN_NEXT_STEP = RUN_BOUNDED_DISCOVERY_PLUS_SEMANTIC_AUTHORING_ON_THE_FROZEN_DEVELOPMENT_12_USING_THE_REPAIRED_CHEAP_FILTER_CONTRACT_THEN_INDEPENDENT_SEED_REVIEW_THEN_RETRIEVAL_REPLAY_BEFORE_ANY_NEW_HOLDOUT`.
- **Development-12 Phase-1 prerequisite re-verification (2026-09-08), from unchanged starting HEAD `01eff40984bee76418c7fab82a1ded9fbfa2d9e5`.** Re-ran `tests/test_contrast_supply.py` (34/0) and `tests/test_generation_lifecycle.py` (31/0) fresh; both PASS, confirming the repair and lifecycle invariant are still intact. Reused the existing frozen development-12 roster (`development_12_ids_sha256 = a20732467b62428dd2388f9bb21820c8ee501e9b3457dbcb0a8d28f6931a6509`) and its decision-evidence/feature-map state without redoing that research: all 12 RDY-* rows are `audit_verdict=ALIGNED_COMPLETE` (`research/qgen/readiness/development_decision_evidence_audit.json`) and `verdict=APPROVED` on independent feature-map review (`research/qgen/readiness/development_feature_map_independent_review.json`), each pinned to `FEATURE_ANCHOR_SNAPSHOT_V6`.
- **New concrete finding: `demanded_response_class`/`decision_granularity` opportunity objects do not exist for any of the 12 RDY-* rows.** `scripts/qbank/contrast_supply.filter_candidates`/`supply_context` require these two fields on an authored "opportunity" record (the vocabulary is decision-specific and hand-authored, e.g. `research/qgen/contrast_first_pilot_opportunities.json` uses values like `ACUTE_RESPIRATORY_DISTRESS`/`SINGLE_NEXT_ACTION`, not a small fixed enum). A repo-wide search (`grep -rl "LD-RDY-MED-01"`) across every readiness/onboarding/snapshot artifact confirms only `decision_type` (e.g. `EMERGENCY_STABILIZATION`, `DIAGNOSIS`) and the learner-decision sentence exist for the RDY-* roster; the finer response-class/granularity layer that Phase 1 of the milestone brief calls "response class frozen" / "granularity frozen" has never been authored for this specific roster. A real bounded TN-FTS discovery pass was run for all 12 (`retrieve_tn_chunks`, 5 chunks each, subheading-level only, no chapter text loaded) confirming the discovery mechanism works and reproduces the same chapter-sibling noise pattern documented for H18.
- This is treated as a genuine Phase-1 fail-closed blocker, not a per-opportunity idiosyncrasy: inventing `demanded_response_class`/`decision_granularity` values on the fly (rather than authoring and independently reviewing them the way every other decision-evidence/feature-map layer in this roster was authored and reviewed) would be exactly the un-reviewed, un-evidenced authoring step the anti-hallucination contract and the H18 root-cause finding (`WRONG_RESPONSE_CLASS`-dominated failures from ungated candidate/response-class matching) both exist to prevent. Phases 2-34 (existing-seed baseline replay through final medical review) were therefore not attempted against the real pipeline this session; running them without this object would either raise `ContrastSupplyError` (context fails closed on missing fields) or require fabricating the missing field, so stopping here was preferred over producing funnel numbers, seed approvals, or generated items grounded in an unauthored response-class assignment. No historical/frozen artifact was modified, no commit was created, `CLAUDE.md` was unchanged.
- `QGEN_NEXT_STEP = AUTHOR_AND_INDEPENDENTLY_REVIEW_DEMANDED_RESPONSE_CLASS_AND_DECISION_GRANULARITY_FOR_THE_FROZEN_DEVELOPMENT_12_THEN_RETRY_PHASE_1`. `READY_FOR_NEW_OPERATIONAL_HOLDOUT = NO` (unchanged).
- **Opportunity-semantics completion (2026-09-08), from unchanged HEAD `01eff40`.** `SEMANTICS_ROOT_CAUSE = SEMANTICS_EXIST_BUT_NOT_ON_OPPORTUNITY_LAYER`, confirmed from code rather than assumed: `demanded_response_class` is a closed, code-enforced vocabulary
  (`scripts/qbank/option_set_admissibility.RESPONSE_CLASS_AXES`, 8 archetypes/axes, already wired into
  `contrast_supply.library_eligible_candidates`/`filter_candidates`), and `decision_granularity` is a separate
  pre-existing closed enum (`scripts/qbank/chapter_staged_generation.DECISION_GRANULARITIES`, 11 values) that had
  simply never been bridged to the Development-12 opportunity layer or checked against a controlled vocabulary at
  the contrast-supply layer at all (there it was previously just free-string equality). Both vocabularies were
  reused directly -- no new token was invented for any of the 12.
- Authored (from `learner_decision` text only, in `research/qgen/readiness/development_decision_evidence_audit.json`,
  with **no visibility into candidate discovery**) and then independently reviewed (single fresh reviewer,
  `sonnet5-independent-review-2026-09-08-opportunity-semantics-dev12`, seeing only development_id + learner_decision +
  proposed archetype/response_class/granularity) for all 12 RDY-* rows. The review was a real catch, not a rubber
  stamp: **9/12 response_class APPROVED, 11/12 decision_granularity APPROVED, 8/12 approved on both axes.**
  Rejected/uncertain: `RDY-PED-01` response_class REJECTED (`MINIMAL_SUPPORT` overloads a respiratory-support-ladder
  token for oral-vs-IV rehydration route selection -- a genuine vocabulary gap, no existing token covers fluid-route
  choice); `RDY-PSY-01` and `RDY-MED-02` response_class UNCERTAIN (`ESCALATION_TO_CRITICAL_CARE` literally denotes a
  critical-care-unit escalation, which urgent psychiatric assessment is not; `MONITORING` vs `FUNCTIONAL` is genuinely
  ambiguous for ECG-or-symptom-rhythm-correlation); `RDY-OBGYN-02` decision_granularity UNCERTAIN (the decision names
  two investigations plus open-ended follow-up, not one discrete test, and `DECISION_GRANULARITIES` has no
  multi-step-pathway token). `RDY-PSY-03` (no cardinal-syndrome token exists for primary psychotic disorders) and
  `RDY-PHELO-02` (no archetype covers taxonomic classification of prevention levels) both correctly fell back to
  their axis's own generic token rather than inventing a one-off label, and both were independently APPROVED.
- Frozen: `research/qgen/contrast_supply/development_12_opportunity_semantics_v1.json`
  (`OPPORTUNITY_SEMANTICS_V1`, pinned to `development_12_ids_sha256 = a20732467b62428dd2388f9bb21820c8ee501e9b3457dbcb0a8d28f6931a6509`,
  own `content_sha256 = 05d5f345246c80f8e4e1edb85f77af203e8db3376342872801c265db6684dbe8`). Not modified after review.
- Validator added under TDD in `scripts/qbank/contrast_supply.load_opportunity_semantics`: fails closed on a missing
  field, an unknown response-class or granularity token, a tampered learner-decision hash, a duplicate row, or a
  missing Development-12 row; silently excludes (does not raise on) an UNCERTAIN/REJECTED row, matching how a
  fail-closed `NO_SAFE_ITEM` opportunity is excluded rather than raised elsewhere in this pipeline. 9 new RED-then-GREEN
  tests in `tests/test_contrast_supply.py` (`test_missing_response_class_fails_closed`,
  `test_missing_granularity_fails_closed`, `test_unreviewed_response_class_is_excluded_not_raised`,
  `test_unknown_response_class_fails_closed`, `test_unknown_granularity_fails_closed`,
  `test_tampered_learner_decision_hash_fails_closed`, `test_duplicate_development_id_fails_closed`,
  `test_missing_development_12_row_fails_closed`, `test_valid_semantics_allow_candidate_filtering_to_continue`,
  `test_wrong_response_class_candidate_rejected`, `test_wrong_granularity_candidate_rejected`); confirmed failing
  (`ImportError`) before the implementation, all green after. Focused `tests/test_contrast_supply.py`: **46/0**. Full canonical suite run once after all shared-code changes:
  **1687 passed, 1 failed** (the same pre-existing, unrelated `test_discovery_classifies_dirty_worktree_retry_and_committed_branch_awaiting_integration`
  source-research-coordinator classification failure seen in every prior QGEN session this file records);
  `NEW_TEST_FAILURES = 0`.
- **`DEVELOPMENT12_PREREQUISITE_READY = 8/12`** (`RDY-MED-01`, `RDY-PED-04`, `RDY-OBGYN-01`, `RDY-SURG-03`,
  `RDY-SURG-05`, `RDY-PSY-03`, `RDY-PHELO-02`, `RDY-PHELO-08`), reusing the already-established 12/12 decision-evidence,
  feature-map and snapshot-pinning state without redoing that research; the new opportunity-semantics gate is the
  only reason the count is 8 rather than 12, and no substitution was made for the 4 that failed it.
- **Phases 13-35 (existing-seed baseline, official candidate-discovery wave, cheap filters, semantic candidate screen,
  relation/anchor authoring, independent seed review, development seed pack, retrieval replay, conditional
  generation, blind solve, final medical review) were explicitly NOT attempted this session.** Each of the 8 ready
  opportunities still needs a full concept-graph-linked opportunity object (candidate discovery inputs beyond
  response_class/granularity) that this session did not build, and compressing per-opportunity relation authoring,
  independent review and item generation into the same pass as semantics authoring would mean materially less
  scrutiny than every comparable prior session in this file gave a smaller slice of the same work. Reported
  `PARTIAL`, not fabricated. No historical/frozen artifact was modified, no commit was created, `CLAUDE.md` was
  unchanged. `READY_FOR_NEW_OPERATIONAL_HOLDOUT = NO` (unchanged).
- `QGEN_NEXT_STEP = BUILD_CONCEPT_GRAPH_LINKED_OPPORTUNITY_OBJECTS_FOR_THE_8_PREREQUISITE_READY_DEVELOPMENT_12_ROWS_THEN_RUN_EXISTING_SEED_BASELINE_THEN_ONE_OFFICIAL_CANDIDATE_DISCOVERY_WAVE_PER_PHASES_13_16`.
- **Development-12 official discovery and cheap filtering (2026-09-08), from unchanged starting HEAD `01eff40984bee76418c7fab82a1ded9fbfa2d9e5`.** Re-verified the opportunity-semantics integration is still GREEN before touching anything: `tests/test_contrast_supply.py` 46/0, plus `test_generation_lifecycle.py`/`test_clinical_retrieval.py`/`test_profile_contrast_retrieval.py`/`test_safe_yield_wave.py` 123/0 combined. No shared code changed this session, so the full suite was not rerun (last recorded full run: 1687 passed/1 failed, the known unrelated source-research coordinator classification failure, `NEW_TEST_FAILURES=0`).
- Confirmed `DEVELOPMENT12_PREREQUISITE_READY = 8/12` and `EXISTING_SEED_READY = 0/12` (via the already-frozen `reports/qgen_contrast_supply_diagnosis_and_repair.json#phase13_existing_seed_baseline`; not recomputed, since study-unit-scope membership across the 4 existing packs is unchanged). Ran one fresh, genuinely official bounded TN-FTS discovery pass (`retrieve_tn_chunks`, 5 chunks/opportunity, subheading/node metadata only, no chapter prose loaded) for all 8 prerequisite-ready opportunities -- explicitly not a reuse of the earlier diagnostic-only probe that only confirmed the discovery mechanism works.
- Applied real bounded clinical judgment to each of the 40 discovered chunks from metadata alone (per this project's copyright policy), assigning exactly one earliest cheap-filter outcome per Phase-11's enumeration: `OFFICIAL_RAW_CANDIDATES=40`, `OFFICIAL_CHEAP_REJECTIONS=36`, `OFFICIAL_SEMANTIC_STAGE_ENTRIES=4`, `SEMANTIC_STAGE_ENTRY_RATE=10%`. Breakdown: `WRONG_RESPONSE_CLASS=4`, `DUPLICATE_ALIAS=3`, `OTHER_CHEAP_REJECTION=29` (chapter-sibling noise/generic headings/pagination artifacts/content that is source material for the key itself), `WRONG_GRANULARITY=0`, `KEY_DUPLICATE=0`, `WRONG_STAGE=0`, `KNOWN_SECOND_KEY=0`, `SCOPE_CONTRADICTION=0`. The 4 semantic-stage survivors: `RDY-PED-04` (formal DM diagnostic-criteria workup vs urgent glucose/ketone check), `RDY-SURG-03` (transthoracic echo vs thoracic POCUS for pneumothorax), `RDY-PSY-03` x2 (a shorter-course primary psychotic disorder from the DDx-for-psychosis table; organic/seizure-related psychosis). Zero survivors for `RDY-MED-01`, `RDY-OBGYN-01`, `RDY-SURG-05`, `RDY-PHELO-02`, `RDY-PHELO-08` -- the latter two are exactly the opportunities whose response-class axis was already flagged in the semantics review as a forced generic-token fallback with no dedicated archetype.
- **`DISCOVERY_PRECISION_FINDING`**: consistent with, not a new instance contradicting, the H18/H24 root cause -- 72.5% of raw chunks were off-topic or non-actionable chapter-sibling noise. Frozen artifact: `research/qgen/contrast_supply/development_12_official_discovery_v1.json`, `content_sha256 = 1d17394dead1f3323ae3e9c507eac9ef86114a9f9d7fc5aa550868513f072f77`.
- **Phases 13-34 (clinical plausibility screen, relation authoring, targeted evidence, independent seed/relation/anchor review, development seed pack, retrieval replay, conditional generation, blind solve, final medical review) were explicitly NOT attempted this session.** Each of the 4 semantic-stage survivors still needs the same per-candidate depth every comparable prior session in this file gave a smaller slice of the same work; compressing it into this pass would mean materially less scrutiny of safety-critical medical content than this project's own established practice requires (the exact compression this project already had to diagnose and repair once, for Fresh-Holdout-24). Reported `PARTIAL_QUOTA_INTERRUPTION`, not fabricated. No historical/frozen artifact was modified, no commit was created, `CLAUDE.md` was unchanged. `READY_FOR_NEW_OPERATIONAL_HOLDOUT = NO` (unchanged).
- `QGEN_NEXT_STEP = RUN_BOUNDED_CLINICAL_PLAUSIBILITY_SCREEN_PHASE_13_ON_THE_4_SEMANTIC_STAGE_SURVIVORS_IN_research_qgen_contrast_supply_development_12_official_discovery_v1_json_THEN_RELATION_AUTHORING_AND_INDEPENDENT_REVIEW_PHASES_14_16_ONE_OPPORTUNITY_AT_A_TIME`.
- **Development-12 survivor adjudication (2026-09-08), continuation from unchanged starting HEAD `01eff40984bee76418c7fab82a1ded9fbfa2d9e5`, no code changed this session.** Reconciled all 29 `OTHER_CHEAP_REJECTION` chunks into an expanded taxonomy against the frozen `development_12_official_discovery_v1.json` (content_sha256 unchanged, `1d17394dead1f3323ae3e9c507eac9ef86114a9f9d7fc5aa550868513f072f77`): `GENERIC_OR_NON_OPTION_CONCEPT=13`, `OFF_TOPIC_CHAPTER_SIBLING=8`, `KEY_DUPLICATE=4`, `PARENT_SUBTYPE_COLLISION=1`, `DUPLICATE_OR_ALIAS=1`, `CANONICALIZATION_FAILURE=1` (the "Toronto Notes 2025" pagination-artifact chunk), `TRULY_UNRESOLVED=1` (the generic "Consent and Capacity" `RDY-PHELO-08` heading -- genuinely too generic to name a competitor from metadata alone, recorded honestly rather than guessed); sums to 29. `CORRECT_CHEAP_REJECTIONS=35`, `TRULY_UNRESOLVED_REJECTIONS=1`, `POSSIBLY_INCORRECT_CHEAP_REJECTIONS=0`, `NEW_FILTER_DEFECT_DISCOVERED=NO`.
- **Existing-viable-competitor counts (Phase 3-4)**: `EXISTING_SEED_READY=0/12` is unchanged (no existing pack scopes any of the 12 units), so every one of the 8 prerequisite-ready opportunities starts at 0 existing competitors. `THEORETICAL_MAX_COMPETITORS` (existing + semantic survivors) per opportunity: `RDY-MED-01=0`, `RDY-PED-04=1`, `RDY-OBGYN-01=0`, `RDY-SURG-03=1`, `RDY-SURG-05=0`, `RDY-PSY-03=2`, `RDY-PHELO-02=0`, `RDY-PHELO-08=0`. **`OPPORTUNITIES_THEORETICALLY_CAPABLE_OF_3 = 0/8`** -- this single frozen discovery wave cannot reach the >=3-competitor contrast floor for *any* opportunity even in the best case, a deterministic ceiling independent of clinical-review quality.
- **Clinical plausibility review (Phase 5) of the 4 semantic-stage survivors**: `RDY-PED-04` (formal HbA1c/DM diagnostic criteria vs urgent glucose/ketone check) = `CLINICALLY_PLAUSIBLE`; `RDY-SURG-03` (transthoracic echo vs thoracic POCUS for pneumothorax) = `CLINICALLY_PLAUSIBLE`; `RDY-PSY-03` shorter-course psychotic disorder (brief/schizophreniform vs schizophrenia by DSM-5 duration) = `CLINICALLY_PLAUSIBLE`; `RDY-PSY-03` organic/seizure-related psychosis (complex partial status epilepticus) = `POTENTIAL_SECOND_KEY` (standard-of-care requires ruling out organic causes before a primary-psychosis diagnosis; without stem evidence excluding it, it risks being an equally-defensible answer rather than a clean distractor) -- excluded before relation authoring, fails closed. `CLINICALLY_PLAUSIBLE=3/4`, `RAW_TO_CLINICALLY_PLAUSIBLE_RATE=3/40=0.075`, `SEMANTIC_TO_CLINICALLY_PLAUSIBLE_RATE=3/4=0.75`. `DISCOVERY_PRECISION=POOR`: cheap-filter precision and semantic-stage judgment quality are both good (72.5% correct chapter-sibling-noise rejection, 75% semantic-survivor plausibility hit rate), but volume/density is structurally inadequate -- discovery never surfaces enough real candidates per opportunity to reach the project's own 3-competitor minimum.
- **Relations authored (Phase 7) for all 3 `CLINICALLY_PLAUSIBLE` candidates** (Clinical Contrast Relation V2: positive anchor + why-it-supports, inferiority discriminator + why-key-superior, `PLAUSIBLE_BUT_NEVER_BEST`/`COUNTERFACTUAL_CORRECT` classification, second-key analysis, required evidence propositions), using only already-frozen TN structural metadata already present in the discovery artifact -- `TARGETED_RELATION_RESEARCH_REQUESTS=0` (no new discovery/retrieval performed; both required-evidence propositions per relation are high-confidence standard medical knowledge, not provenance-dependent claims needing verification). One fresh independent, blinded reviewer (given only opportunity/decision/key/candidate/response-class/granularity/relation/anchor/evidence, not contrast-count or yield targets) returned: `RDY-PED-04` HbA1c = `APPROVED`; `RDY-SURG-03` TTE = `APPROVED` (with a disclosed scope-dependent caveat: only stays a clean distractor if the eventual stem never introduces cardiac tamponade as a competing differential); `RDY-PSY-03` brief/schizophreniform = `UNCERTAIN` (schizophreniform disorder shares identical criteria with schizophrenia except the <6-month cutoff; reviewer could not confirm an undrafted stem would state duration unambiguously enough to foreclose it) -- fails closed. `RELATIONS_AUTHORED=3`, `SEEDS_PROPOSED=3`, `SEEDS_APPROVED=2`, `SEEDS_REJECTED=0`, `SEEDS_UNCERTAIN=1`.
- **Development-12 seed pack (Phase 11) persisted**: `research/qgen/contrast_supply/development_12_seed_pack_v1.json`, `content_sha256=a4b4fc760e8c3da78d29ac7b4b98eb44a292082311b3fe9cf09fecd4a9c07be5`, containing only the 2 independently-approved seeds (`SEED-DEV12-PED04-HBA1C`, `SEED-DEV12-SURG03-TTE`); the uncertain and second-key-excluded candidates are recorded but not persisted as seeds.
- **Final contrast replay (Phase 12-14)**: with the 2 new approved seeds added to 0 existing competitors, `RDY-PED-04` and `RDY-SURG-03` each reach 1 total competitor; every other ready opportunity stays at 0. **`CONTRAST_READY=0/12`** (confirms the Phase 4 ceiling; no top-up performed per Phase 13). **`CONTRAST_SUPPLY_ASSESSMENT=PROMISING`** (plausible/approved candidates exist -- 2 approved seeds -- but no opportunity reaches 3 competitors under this single frozen wave; distinct from `NO_BETTER`). Generation (Phases 16-20) correctly skipped: `BLUEPRINT_READY=0`, `STEMS_GENERATED=0`, `ACCEPTED=0`, `NO_SAFE_ITEM=8` (all 8 ready opportunities). Historical safety re-verified without any code change: `tests/test_contrast_supply.py` 46/0, plus `test_generation_lifecycle.py`/`test_clinical_contrast_v2.py`/`test_seed_pack_onboarding.py`/`test_seed_pack_onboarding_milestone.py` 99/0 combined (145/0 focused total); full suite not rerun (no shared code changed). `HISTORICAL_SAFETY_REGRESSION=PASS`, `LIFECYCLE_INVARIANT=PASS`. `READY_FOR_NEW_OPERATIONAL_HOLDOUT=NO` (unchanged -- no safe contrast set exists). `NEXT_DOMINANT_BOTTLENECK=CONTRAST_COVERAGE_DENSITY` (approved seeds exist but the single-wave discovery mechanism structurally cannot supply enough of them per opportunity, not a relation/evidence/anchor quality problem).
- `QGEN_NEXT_STEP = THIS_FROZEN_DISCOVERY_WAVE_IS_EXHAUSTED_FOR_ALL_8_READY_OPPORTUNITIES_AT_CONTRAST_READY_0_OF_12 -- BUILD_A_REUSABLE_MULTI_WAVE_CONTRAST_CACHE_OR_RUN_A_NEW_BOUNDED_DISCOVERY_WAVE_WITH_A_HIGHER_CHUNK_FLOOR_BEFORE_ATTEMPTING_GENERATION_AGAIN; do not top up this specific frozen wave`.
- **Targeted Discovery V2 designed, implemented and replayed (2026-09-08), PARTIAL_QUOTA_INTERRUPTION, from unchanged starting HEAD `01eff40984bee76418c7fab82a1ded9fbfa2d9e5`.** Root cause re-confirmed at the code level, not merely re-asserted: `retrieve_tn_chunks`'s query is an unbounded whole-corpus `OR` of every word in the raw `learner_decision` sentence, with no study-unit or response-class restriction at all -- `test_targeted_discovery_narrower_than_whole_corpus_baseline` reproduces a real off-study-unit hit in the V1 baseline for the same COPD query. Traced the deterministic `chunk_study_units` crosswalk (72,669 rows, 1,486 study units, already populated in `derived/tn_index/tn_index.sqlite3`) and the existing `clinical_graph._project_toronto_notes_discovery` heading-family convention (`DIFFERENTIAL_HEADINGS`/`PRESENTATION_HEADINGS`) as the two existing, generalizable, non-disease-specific signals V1 never used.
- New `scripts/qbank/contrast_supply.retrieve_targeted_tn_chunks` (plus `RESPONSE_CLASS_HEADING_FAMILIES`, one generic TN section-heading family per `RESPONSE_CLASS_AXES` key, reusing the same heading-family convention already trusted by the committed graph builder): restricts every candidate chunk to the opportunity's own `study_unit_id` and, where the axis has one, to a response-class-shaped heading family; falls back to study-unit-scope-only (never whole-corpus) when an axis has no family or a unit measurably has zero chunks in it (proven necessary for `RDY-PSY-03`/`RDY-PHELO-02`, both genuinely zero on their differential/etiology/pathophysiology family). No embeddings, no new architecture, no per-disease term invented. 7 new RED-then-GREEN tests in `tests/test_contrast_supply.py`; focused module `53/0` (was 46/0); combined focused (`test_contrast_supply`/`test_generation_lifecycle`/`test_clinical_retrieval`/`test_profile_contrast_retrieval`/`test_safe_yield_wave`/`test_clinical_contrast_v2`/`test_seed_pack_onboarding`/`test_seed_pack_onboarding_milestone`) `198/0`.
- Replayed over the same 8 prerequisite-ready opportunities with a fixed per-opportunity candidate budget of 8: `DISCOVERY_V2_RAW_CANDIDATES = 57` (uncapped 63) vs `DISCOVERY_V1_RAW_CANDIDATES = 40`; every opportunity now clears a nonzero raw-candidate floor (V1 left `RDY-MED-01`/`RDY-OBGYN-01`/`RDY-SURG-05`/`RDY-PHELO-02`/`RDY-PHELO-08` at zero). **Finding is explicitly `MIXED`, not `V2 is better`**: V2's scope restriction is a measured precision gain (every candidate provably same-study-unit), but for `RDY-PED-04`, `RDY-OBGYN-01`, `RDY-SURG-03` and `RDY-SURG-05` the top bm25-ranked chunks under a generic heading family (`Treatment`/`Management`/`Investigations`) carry no distinguishing metadata beyond that repeated generic label, so no specific candidate can be named without reading chunk prose or inventing one from general medical knowledge -- both forbidden by this project's canonical-data rules. This is a genuinely new limitation V1 did not have (V1 occasionally benefited from Toronto Notes' `subheading` field capturing a body-text fragment rather than a clean section title).
- Clinical plausibility screen (Phase 8) was therefore only safely attemptable for 2 of 8: `RDY-PSY-03`'s V2 candidates (`DDx for Psychosis`, `Schizophrenia Criterion 4 >6mo`, `DSM-5 DIAGNOSTIC CRITERIA FOR SCHIZOPHRENIA`) are `RE-DISCOVERY_OF_ALREADY_ADJUDICATED_CANDIDATE` -- the identical shorter-course-psychotic-disorder relation already independently reviewed `UNCERTAIN` in `development_12_seed_pack_v1.json`'s excluded relation, unchanged by rediscovery via a different retrieval path, not promoted. `RDY-PHELO-08` surfaced two genuinely new, specific, nameable concepts distinct from the capacity-assessment key itself -- `Four Basic Requirements of Valid Consent` and `Bill C-14 Criteria for MAID` -- both `PROPOSED`, **not** `APPROVED`: no genuinely independent (separately blinded) reviewer pass was run this session, and an author-minted approval is invalid per this project's own established practice. `SEEDS_PROPOSED_THIS_WAVE = 0` (still), `SEEDS_APPROVED_THIS_WAVE = 0`. `CONTRAST_READY` is unchanged at `0/12`.
- Frozen artifact: `research/qgen/contrast_supply/development_12_targeted_discovery_v2.json`, `content_sha256 = 1c1d726e4633347b9a830c043e40b66416fd4c539d47d3972ea1b5896bb59515`, referencing `development_12_official_discovery_v1.json` byte-identically (untouched).
- **Phases 9-24 (relation authoring, targeted evidence, independent seed/relation review, reusable-cache V1 construction, Build-12-with-cache replay, Transfer-12 selection and everything downstream, conditional generation) were explicitly NOT attempted this session.** They require either newly identifiable candidates this session's discovery could not safely name from metadata (6 of 8 opportunities) or the same full-session, one-candidate-at-a-time clinical/legal authoring depth already established for every comparable prior slice of this pipeline; compressing them here would be materially less scrutiny of safety-critical content than this project's own established practice requires (the exact compression already diagnosed and repaired once, Fresh-Holdout-24). Reported `PARTIAL_QUOTA_INTERRUPTION`, not fabricated. No historical/frozen artifact was modified, no commit was created, `CLAUDE.md` was unchanged. `READY_FOR_NEW_OPERATIONAL_HOLDOUT = NO` (unchanged). One canonical full-suite run at this final production-code state: **1694 passed, 1 failed** -- the same known unrelated `test_discovery_classifies_dirty_worktree_retry_and_committed_branch_awaiting_integration` source-research-coordinator classification failure seen throughout this file; `NEW_TEST_FAILURES = 0`.
- `QGEN_NEXT_STEP = RUN_A_GENUINELY_INDEPENDENT_BLINDED_REVIEW_OF_THE_2_RDY-PHELO-08_PROPOSALS_(VALID-CONSENT-REQUIREMENTS,_MAID-CRITERIA); SEPARATELY, DECIDE_WHETHER_TO_EXTEND_RESPONSE_CLASS_HEADING_FAMILIES_WITH_A_SUBHEADING-SPECIFICITY_FILTER_(REJECT_A_CHUNK_WHOSE_SUBHEADING_EQUALS_THE_GENERIC_HEADING_TOKEN_WITH_NOTHING_ELSE)_BEFORE_TRUSTING_V2_RAW_COUNTS_FOR_THE_OTHER_6_READY_OPPORTUNITIES; do not build the reusable cache or select Transfer-12 before this`.
- **Candidate-identifiability audit + independent PHELO-08 review (2026-09-08), continuation from unchanged starting HEAD `01eff40984bee76418c7fab82a1ded9fbfa2d9e5`, no shared/production code changed this session.** Ran the requested genuinely independent blinded review of the 2 `RDY-PHELO-08` proposals from `development_12_targeted_discovery_v2.json` (seen only: learner decision, demanded response class `AUTONOMY`, granularity `ETHICAL_ACTION`, candidate label, chunk metadata -- not this milestone's desired cache yield): `Bill C-14 Criteria for MAID` -> `APPROVED` (a specific, legally distinct ethical action, same response-class/granularity lane as the key, low collision risk -- candidate identity/plausibility only, relation still needs authoring); `Four Basic Requirements of Valid Consent` -> `UNCERTAIN` (decision-specific capacity, the key, is itself one of the four requirements, so this candidate risks being the key's own parent/superset rather than an independently competing option; fails closed, not promoted). `PHELO08_APPROVED=1, PHELO08_UNCERTAIN=1, PHELO08_REJECTED=0`.
- Built a deterministic (subheading-string-only, no prose) identity classifier over all 57 Discovery-V2 retrieval hits across the 8 prerequisite-ready opportunities: `SPECIFIC_HEADING_IDENTITY=16`, `GENERIC_HEADING_ONLY=29`, `OTHER=12` (captions/body-text fragments, e.g. `Figure 10. Guidelines for COPD management`, `Outcome: Treatment failure...`) -- `IDENTITY_RESOLVABLE_HITS=16/57` under subheading-only rules, explicitly reported as an upper bound, not a final production count. Artifact: `reports/qgen_candidate_identifiability_audit.json`.
- **Root-cause finding, proven at the database level (not re-asserted): `chunks.section_path` in `derived/tn_index/tn_index.sqlite3` (a TOC breadcrumb, e.g. `Gynecology > Gynecological Infections > Physiologic Discharge`) is populated for 57/57 (100%) of the Discovery-V2 chunk_ids, but `development_12_targeted_discovery_v2.json`'s chunk records never capture it -- only subheading/tn_node_id/page are exposed.** This is `STRUCTURAL_PATH_NOT_USED`, the single most actionable identifiability gap, alongside `GENERIC_HEADINGS_DOMINATE` (29/57) and a partial `CANONICAL_CONCEPT_JOIN_MISSING` (the `concepts`/`concept_mentions` tables exist and are populated elsewhere in the corpus -- 2,907 rows -- but return 0/57 for this specific chunk set). Root cause classified `MULTIPLE_COMPARABLE_CAUSES`.
- Confirmed `ALLOWED_IDENTITY_SIGNALS` (subheading, tn_node_id, `section_path` TOC breadcrumb, `concept_mentions`/`concepts` canonical join where populated, existing reviewed relation/seed) vs `DISALLOWED_IDENTITY_SIGNALS` (chunk body prose, medical-knowledge inference over an unresolved generic heading, embeddings/generative renaming) against `AGENTS.md`'s canonical-data rules; consistent with, not a loosening of, existing copyright policy. Spot-checked the AOM control (`research/qgen/onboarding/v6_development_seed_pack.json`, target `LD-ONB2-PED-AOM-DX`, seed `SEED-V6-AOM-OME`) as an existing frozen reference point; confirmed HbA1c/TTE are Development-12 semantic-stage survivors, not approved seeds, so they are not a seed-pack regression control.
- Designed (specification only) a minimal `resolve_candidate_identity` priority order (existing reviewed identity -> canonical concept join -> specific non-generic non-fragment subheading -> `section_path` TOC fallback -> `CANDIDATE_IDENTITY_NOT_RESOLVABLE`), but **did not implement it** -- no code was changed in `scripts/qbank/contrast_supply.py` or elsewhere, no TDD tests were added, Discovery V2 was not rerun, and Phases 9-24 (relation authoring, independent relation review, Reusable Contrast Cache V1 construction, Build-12 cache replay, historical safety re-verification, Transfer-12 selection) were **not attempted this session** -- same rationale as the prior session: implementing and safety-verifying a shared-code identity resolver plus a full downstream cache build/replay is multi-hour, TDD-and-full-suite-gated work, and compressing it here would repeat the exact scrutiny failure this project already diagnosed and repaired once (Fresh-Holdout-24). Reported `PARTIAL_QUOTA_INTERRUPTION`, not fabricated. No shared code changed, so no full-suite rerun was performed this session (consistent with the project's test policy that a full run is required only after shared/production code changes); the last known full-suite state remains **1694 passed, 1 failed** (same known unrelated coordinator classification failure). No historical/frozen artifact was modified, no commit was created, `CLAUDE.md` was unchanged. `CONTRAST_READY` unchanged at `0/12`. `REUSABLE_CONTRAST_CACHE_V1` not built (0 approved cache entries; the 1 APPROVED PHELO-08 candidate this session has no authored relation/evidence yet, so it is not cache-admissible).
- `QGEN_NEXT_STEP = IMPLEMENT_THE_DESIGNED_STRUCTURAL-PATH_IDENTITY_RESOLVER_IN_CONTRAST_SUPPLY.PY_WITH_TDD_(RED_TESTS_FIRST:_GENERIC_HEADING_DOES_NOT_RESOLVE,_SPECIFIC_HEADING_RESOLVES,_SECTION_PATH_FALLBACK_RESOLVES,_AMBIGUOUS_FAILS_CLOSED); THEN_RERUN_BUILD-12_DISCOVERY_V2_WITH_IDENTITY_CLASSIFICATION_ATTACHED; THEN_AUTHOR_THE_ONE_APPROVED_BILL-C-14-MAID_RELATION_(POSITIVE_ANCHOR,_INFERIORITY_DISCRIMINATOR,_EVIDENCE)_BEFORE_ANY_CACHE_CONSTRUCTION; do not build the reusable cache or select Transfer-12 before this`.
- **`resolve_candidate_identity` implemented with TDD and Build-12 Discovery-V2 rerun with identity classification (2026-09-08), continuation from unchanged starting HEAD `01eff40984bee76418c7fab82a1ded9fbfa2d9e5`.** `retrieve_targeted_tn_chunks` (`scripts/qbank/contrast_supply.py`) now also selects and carries `chunks.section_path` (a TN table-of-contents breadcrumb) on every hit; no ranking-semantics change. Added `resolve_candidate_identity(hit, *, existing_reviewed_identities=None)`, a deterministic (no chunk-prose reading, no medical-knowledge inference) priority resolver: existing reviewed identity by chunk_id -> trusted canonical concept label -> specific non-generic non-ambiguous `subheading` -> specific non-generic non-ambiguous terminal `section_path` component -> fail closed. `GENERIC_STRUCTURAL_TOKENS` is a small closed set (`treatment`/`management`/`investigations`/`diagnosis`/`differential diagnosis`/`complications`/`overview`/`approach`/`principles`); ambiguity detection rejects labels naming more than one concept (` vs `/` and `/` or `/`/`); a real defect found only by actually replaying the real 57 hits -- `_is_extraction_artifact` -- separately fails closed on figure/table captions, colon-prefixed label:continuation fragments (`Outcome:`, `Conclusion:`), sentence-opening fragments (`This is a...`), and truncated trailing-stopword/possessive endings, all pure typographic/structural signals, not content reading. 22 TDD tests added (all 12 phase-2-required cases plus 6 artifact-detection cases discovered from the real replay), all initially RED against a stub, all GREEN after implementation. Focused: `tests/test_contrast_supply.py` `72 passed`; combined with `test_clinical_retrieval.py`/`test_generation_lifecycle.py`/`test_profile_contrast_retrieval.py`/`test_safe_yield_wave.py`, `143 passed / 0 failed`.
- Reran Discovery V2 over the same 8 prerequisite-ready Build-12 opportunities, same budget=8, same queries/study-units/axes as `development_12_targeted_discovery_v2.json`, now with `section_path` attached and every hit resolved. `DISCOVERY_V2_RETRIEVAL_HITS=57` (unchanged from the frozen artifact). `IDENTITY_CLASSIFICATION = {EXPLICIT_CANONICAL_IDENTITY: 0, SPECIFIC_HEADING_IDENTITY: 17, SECTION_PATH_IDENTITY: 25, EXISTING_REVIEWED_IDENTITY: 0, GENERIC_HEADING_ONLY: 0, AMBIGUOUS_STRUCTURAL_IDENTITY: 4, NO_IDENTITY_METADATA: 0, OTHER: 11}` (counts sum to 57). `IDENTITY_RESOLVABLE_HITS=42/57`, `IDENTITY_UNRESOLVABLE_HITS=15/57` -- a large, measured improvement over the pre-resolver upper-bound classification (`SPECIFIC_HEADING_IDENTITY=16, GENERIC_HEADING_ONLY=29, OTHER=12` from the earlier subheading-only pass), because `section_path` recovers many hits whose `subheading` alone was generic (`Treatment`/`Investigations`/etc.) but whose breadcrumb names a specific terminal concept (e.g. `Antidiuretic Hormone`, `Physiologic Discharge`, `Cholelithiasis`). Canonical-string-deduplicated: `UNIQUE_RESOLVED_CANDIDATES=22` across the 8 opportunities (per-opportunity raw/method breakdown and every hit's resolution provenance in the artifact). No `EXISTING_REVIEWED_IDENTITY` or `EXPLICIT_CANONICAL_IDENTITY` hits fired because no chunk_id->identity mapping or trusted `concept_mentions` join exists for this specific 57-hit set (confirmed absent in the prior session's audit); this is an honest absence, not a resolver defect -- both paths are exercised and pass in the unit tests (cases 9-12). Artifact: `reports/qgen_candidate_identity_resolution_build12.json`, `content_sha256=c01230d54646adaf603bb033ef2c2a51d3b86c8c002b97b71132739a524e9e00`.
- **Phases 8's canonical-string dedup is done (22 unique); Phases 9-24 (cheap-filter application against full candidate/context objects, clinical plausibility review of the 22 newly-nameable candidates, relation authoring, targeted evidence, independent relation/anchor review, Reusable Contrast Cache V1 construction, Build-12-with-cache replay, historical safety re-verification, Transfer-12 selection, and everything downstream) were explicitly NOT attempted this session.** Rationale unchanged from the prior two sessions at this same milestone boundary: this project's own history (Fresh-Holdout-24) already diagnosed and repaired the exact failure mode of compressing one-candidate-at-a-time clinical/legal authoring plus independent review into a single pass; 22 freshly-nameable candidates at that same required depth is a multi-hour, TDD-and-full-suite-gated undertaking each subsequent session has correctly declined to compress. Reported `PARTIAL_QUOTA_INTERRUPTION`, not fabricated. No historical/frozen artifact was modified, no commit was created, `CLAUDE.md` was unchanged, nothing was reset/cleaned/stashed. One canonical full-suite run at this final production-code state (required because shared/production code changed this session): **1713 passed, 1 failed** -- the same known unrelated `test_discovery_classifies_dirty_worktree_retry_and_committed_branch_awaiting_integration` source-research-coordinator classification failure seen throughout this file (count differs from the prior session's `1694` only because more tests were added across sessions since, not because any previously-passing test changed status); `NEW_TEST_FAILURES=0`. `CONTRAST_READY` unchanged at `0/12`. `REUSABLE_CONTRAST_CACHE_V1` still not built (0 approved cache-admissible entries; the 1 APPROVED PHELO-08 candidate still has no authored relation/evidence).
- `QGEN_NEXT_STEP = CLINICALLY_REVIEW_THE_22_NEWLY-IDENTITY-RESOLVED_BUILD-12_CANDIDATES_ONE_AT_A_TIME_(CLASSIFY_CLINICALLY_PLAUSIBLE/CLEARLY_DEAD/WRONG_DECISION/POTENTIAL_SECOND_KEY/UNCERTAIN_PER_PHASE_11,_NOTING_SEVERAL_ARE_LIKELY_KEY-DUPLICATES_E.G._RDY-PHELO-08'S_"OVERVIEW_OF_CAPACITY"/"ASSESSMENT_OF_CAPACITY"_RESTATING_THE_KEY_ITSELF_RATHER_THAN_A_COMPETITOR,_TO_BE_CAUGHT_BY_PHASE_9_CHEAP_FILTERS_ONCE_MAPPED_TO_CANDIDATE_OBJECTS); THEN_AUTHOR_THE_ONE_APPROVED_BILL-C-14-MAID_RELATION_(POSITIVE_ANCHOR,_INFERIORITY_DISCRIMINATOR,_EVIDENCE)_BEFORE_ANY_CACHE_CONSTRUCTION; do not build the reusable cache or select Transfer-12 before this`.
- **Build-12 candidate adjudication, relation review and Reusable Contrast Cache V1 completion (2026-09-08), from unchanged starting HEAD `01eff40984bee76418c7fab82a1ded9fbfa2d9e5`.** Applied deterministic cheap filtering (Phase 2-4) to all 22 unique identity-resolved Build-12 candidates before any clinical review: **19 rejected** (`WRONG_RESPONSE_CLASS=6` all `RDY-PHELO-02` -- its `explained_phenomenon_class` axis's tokens are statistical-artefact concepts [confounding/bias/chance/etc.], and none of its 6 candidates name one; `KEY_DUPLICATE=4` -- `RDY-PSY-03` schizophrenia's own DSM-5 criterion x2, `RDY-PHELO-08`'s "Overview of Capacity"/"Assessment of Capacity" restating the key itself, confirming the risk flagged in the prior session's `QGEN_NEXT_STEP`; `PARENT_SUBTYPE_COLLISION=2` -- `RDY-SURG-05` "Cholelithiasis" [the parent diagnosis of the key's own biliary-colic scenario] and `RDY-PHELO-08` "Four Basic Requirements of Valid Consent" [capacity, the key, is one of the four -- consistent with and reproducing the prior session's independent UNCERTAIN verdict, kept unavailable per this milestone's own instruction]; `CANONICALIZATION_FAILURE=4`, `WRONG_STAGE=1`, `DUPLICATE_OR_ALIAS=1`, `OTHER=1` [re-discovery of the standing-UNCERTAIN `RDY-PSY-03` shorter-course-psychotic-disorder candidate, kept unavailable]), **3 `SURVIVES_TO_SEMANTIC`**: `RDY-PED-04` "Antidiuretic Hormone" (maps to `next_action_class`'s `DIAGNOSTIC_ORDER` token, on-axis, distinct from the glucose/ketone key), `RDY-OBGYN-01` "Physiologic Discharge" (maps to `management_capability`'s `NO_ACTIVE_TREATMENT` token, on-axis, distinct from the key's `PHARMACOLOGIC_TREATMENT`), `RDY-PHELO-08` "Bill C-14 Criteria for MAID" (same `value_served` `AUTONOMY` token as the key, previously independently APPROVED for candidate identity/plausibility). `CHEAP_FILTER_SURVIVORS=3/22`. Theoretical density ceiling unchanged: `OPPORTUNITIES_CAPABLE_OF_REACHING_3_PRE_REVIEW=0/8` even counting the 2 pre-existing approved seeds (`RDY-PED-04` and `RDY-SURG-03` each cap at 2). Artifact: `reports/qgen_build12_candidate_cheap_filter.json`, `content_sha256=2a0174717557586736aa9519c79c4c1d58b8d37d52a17751667ece76d6133de6`.
- **Clinical plausibility review (Phase 6)**: all 3 semantic survivors `CLINICALLY_PLAUSIBLE` (0 `CLEARLY_DEAD`/`WRONG_DECISION`/`POTENTIAL_SECOND_KEY`/`UNCERTAIN`). `RESOLVED_TO_SEMANTIC_RATE=3/22=0.136`, `SEMANTIC_TO_PLAUSIBLE_RATE=1.0`, `RESOLVED_TO_PLAUSIBLE_RATE=0.136`, `DISCOVERY_PRECISION=NOISY_BUT_USABLE` (cheap filter and clinical judgment both did real, correct work -- 19/22 rejections were substantively justified and all 3 survivors held up -- but discovery volume remains structurally inadequate to reach the 3-competitor floor).
- **Relation authoring and independent review (Phase 8-12)**: authored 3 Clinical Contrast Relation V2 entries (same prose schema as `development_12_seed_pack_v1.json`'s `relations_authored`: positive anchor, why-anchor-supports-candidate, inferiority discriminator, why-key-superior, `COUNTERFACTUAL_CORRECT`/`PLAUSIBLE_BUT_NEVER_BEST` classification, second-key analysis, required evidence propositions). `TARGETED_RELATION_RESEARCH_REQUESTS=0` (both evidence propositions per relation are standard, non-provenance-dependent medical/legal knowledge, matching this project's established practice for this schema). One fresh independent review pass (blinded to yield/discipline targets) returned **`RELATIONS_APPROVED=3/3`, 0 REJECTED, 0 UNCERTAIN**: `CCR2-DEV12-PED04-ADH` (ADH/DI workup fails the urgency requirement even where DI is differential-relevant); `CCR2-DEV12-OBGYN01-PHYSIOLOGIC-DISCHARGE` (approved without a residual-risk caveat, unlike the prior session's TTE precedent -- the discriminator's supporting features are the opportunity's own defining precondition, not an unguaranteed future stem feature); `CCR2-DEV12-PHELO08-BILLC14-MAID` (approved with a **mandatory** population/context restriction: not usable when the stem's proposed decision is itself a MAID request, since MAID eligibility does require capacity and the candidate would become a live co-key in that scope). Artifact: `reports/qgen_build12_relation_authoring_and_review.json`, `content_sha256=6e299d646b10a0417f1fa9d38e19adae2812c758a2a1cfc0e3af96f2f142de4d`.
- **Seed pack V2 (Phase 13)**: `research/qgen/contrast_supply/development_12_seed_pack_v2.json`, additive over `development_12_seed_pack_v1.json` (its 3 relations/2 approved seeds reproduced byte-identically, parent hash pinned). Adds the 3 newly APPROVED relations and seeds. **`seeds_approved=5`** total (2 historical + 3 new), `seeds_uncertain=1` (unchanged, `CCR2-DEV12-PSY03-BRIEF-SCHIZOPHRENIFORM`), `seeds_rejected=0`. `content_sha256=afdf226266fdd17da614e7d471c807e2beeac3b79327f56bab0a2d86a2a84c90`.
- **Reusable Contrast Cache V1 (Phase 14-15)**: implemented under TDD in `scripts/qbank/contrast_supply.py` -- `build_reusable_contrast_cache_v1(seed_pack)` (admits only `review_status == "APPROVED"` seeds carrying a non-empty `anchor_id`, raising `ContrastSupplyError` otherwise) and `lookup_reusable_cache_entry(cache, *, opportunity_id, candidate_id_, response_class, decision_granularity, stem_context=None)` (exact 4-field scope match, no near-miss/fallback; a seed's `population_context_restriction_rule.forbidden_if_context` mapping requires an explicit `stem_context` and returns `None` on a match, rather than silently ignoring the restriction). 10 new RED-then-GREEN tests in `tests/test_contrast_supply.py` (admits-only-approved, refuses-missing-anchor, exact-scope hit, wrong-opportunity/response-class/granularity misses, restriction-requires-context, restriction-rejects/allows-matching-context, no-implicit-latest-cache). Built the real cache from `development_12_seed_pack_v2.json`: **`CACHE_V1_APPROVED_ENTRIES=5`**. All Phase-15 safety checks run live against the built cache (not asserted only in prose): exact-scope-allowed, wrong-decision/response-class/granularity-rejected, MAID population-mismatch-rejected-where-material, rejected/UNCERTAIN/second-key-risk relations structurally unavailable (never entered `seeds`), no-implicit-latest-lookup (explicit `cache` argument required), scope-narrowing preserved -- **all PASS**. Artifact: `research/qgen/contrast_supply/reusable_contrast_cache_v1.json`, `content_sha256=f848045e18123da6128ebf05e085f572d74f25cb055a75d0c47ab2b73cc6e780`.
- **Build-12 cache replay (Phase 16-19)**: same 8 prerequisite-ready opportunities, no new discovery wave -- reuses the 2 pre-existing approved seeds (now reachable through the cache lookup path) plus the 3 newly approved. `BUILD12_WITH_1_PLUS_COMPETITOR=4/8`, `BUILD12_WITH_2_PLUS_COMPETITORS=1/8` (`RDY-PED-04` only, at 2: HbA1c + ADH), `BUILD12_WITH_3_PLUS_COMPETITORS=0/8`, `BUILD12_CACHE_CONTRAST_READY=0/12`. `CACHE_REUSE_COUNT=RELATION_REUSE_COUNT=ANCHOR_REUSE_COUNT=2` (the 2 historical seeds). Not topped up, per this milestone's explicit instruction. Artifact: `reports/qgen_build12_cache_v1_replay.json`, `content_sha256=78c3585f7f71ef7245cfde388da45ec9b9f067eb5fe1f420fa4528e8674d16b9`.
- **`CACHE_V1_ASSESSMENT=CACHE_V1_PROMISING`**: approved cache entries exist (5, up from 0), safe scope/restriction behavior is proven live, and density measurably improved (`RDY-PED-04` 1->2 competitors; two more opportunities gained their first competitor) -- but no opportunity reaches the 3-competitor `CONTRAST_READY` floor yet, so `VALIDATED` is not claimed. Not `INSUFFICIENT_DENSITY` (density did improve) or `UNSAFE` (all controls pass).
- **Historical safety**: `HISTORICAL_SAFETY_REGRESSION=PASS`, `LIFECYCLE_INVARIANT=PASS`, `AOM_DEVELOPMENT_CONTROL=PASS` (unchanged; no historical/frozen artifact touched -- `development_12_seed_pack_v1.json`, `development_12_official_discovery_v1.json`, `development_12_targeted_discovery_v2.json` and `qgen_candidate_identity_resolution_build12.json` all reverified byte-identical by hash). Focused `tests/test_contrast_supply.py`: **82 passed**; combined focused (+`test_generation_lifecycle.py`/`test_clinical_retrieval.py`/`test_profile_contrast_retrieval.py`/`test_safe_yield_wave.py`/`test_clinical_contrast_v2.py`/`test_seed_pack_onboarding.py`/`test_seed_pack_onboarding_milestone.py`): **227 passed**. Full canonical suite run once (shared/production code changed): **1723 passed, 1 failed** -- the same known unrelated `test_discovery_classifies_dirty_worktree_retry_and_committed_branch_awaiting_integration` source-research-coordinator classification failure seen throughout this file; `NEW_TEST_FAILURES=0`. Copyright audit PASS: every new artifact carries only self-authored prose and already-frozen structural metadata (subheading/tn_node_id/pdf_page/section_path); no chapter body prose was read or reproduced this session.
- `READY_FOR_TRANSFER_TEST=YES` (Cache V1 exists with 5 approved entries > 0, safety tests PASS, historical safety PASS, lifecycle PASS, `NEW_TEST_FAILURES=0`, `CACHE_V1_PROMISING`). `TRANSFER12_SELECTED=NO` -- not selected this session, per this milestone's explicit instruction. No commit was created, `CLAUDE.md` was unchanged, nothing was reset/cleaned/stashed, no historical/frozen artifact was modified.
- `NEXT_DOMINANT_BOTTLENECK=CACHE_DENSITY` (approved seeds accumulate across waves -- 2 to 5 -- and density measurably improves, but the single-wave-per-opportunity discovery mechanism still cannot supply enough candidates per opportunity to clear 3; this is not a relation/evidence/anchor quality problem, both this and the prior wave's relations were approved on quality). `QGEN_NEXT_STEP = EXPAND_CACHE_DENSITY_VIA_EITHER_(A)_A_NEW_BOUNDED_DISCOVERY_WAVE_PER_OPPORTUNITY_WITH_A_HIGHER_CHUNK_FLOOR/DIFFERENT_HEADING_FAMILY_TO_SURFACE_CANDIDATES_BEYOND_THIS_SESSION'S_57_HITS,_OR_(B)_USER_AUTHORIZATION_TO_RUN_TRANSFER-12_NOW_GIVEN_READY_FOR_TRANSFER_TEST=YES; do not select Transfer-12 without that authorization`.
- **Global typed Discovery V3 + Cache V2 + Transfer-12 milestone (2026-09-08): BLOCKED at the final copyright gate.** Starting HEAD remains `01eff40984bee76418c7fab82a1ded9fbfa2d9e5`; no commit, reset, clean, stash, or historical-artifact modification occurred. Transfer-12 was selected outcome-blind before V3 (`transfer12_sha256=9c738a1500da7b57d0a209ffc6937411f94208628fac75e3ba3cc75108ca2ee7`, two per discipline) and remained candidate-embargoed through opportunity-only semantic review; 10/12 semantics were approved and two compound decisions failed closed without substitution. Build-12 root cause is `F_MULTIPLE_COMPARABLE_CAUSES`; the V2 hard study-unit boundary is proven to be a locality ceiling. The structural/canonical catalogue contains 1,919 concepts (90 deterministically typed), hash `f6dff256cdd68aa65400feb72f6959a9946263b0453bfac6132bbaf0e98909ad`; Discovery V3 implementation file hash `59a1bbfe60498f3e599b659e34ba402e05b3ae2d622c62df7623bf38fffdeabb`.
- Build-12 V3 froze 24 candidates: cheap rejection 0, semantic survivors 24, clinically plausible 5, wrong decision 19, other semantic outcomes 0. One new chest-radiography-versus-thoracic-POCUS relation was independently approved after one narrow Canadian evidence request. Cache V2 is append-only over Cache V1, hash `5ab890e15a6d3b57420fc4439242b88ea7baca5a9c0e9766cd0fd1985f115d9b`, 1 new / 6 total entries. Build-12 density became 4/8 with >=1, 2/8 with >=2, 0/8 with >=3, 0 contrast-ready; Discovery V3 and density are `PROMISING`, not validated.
- After the architecture freeze (`9522d67d0671778cafa370ab5ab76b22707e62880370bfb332b79eefcf617f67`), Transfer was unblinded. Cache V1 and Cache V2 zero-top-up reuse were both 0 at every density threshold because their safety contract is exact-opportunity scoped. The one permitted V3 top-up froze 54 candidates over the 10 semantics-approved opportunities: cheap rejection 0, semantic survivors 54, clinically plausible 0, wrong decision 52, potential second key 2 (both OCD psychotherapy labels), no new relations/evidence requests/seeds. Cache V3 is a zero-addition append-only child, hash `cc11c1aa8eee28909563c5ed5db57322284f72bfe884ec7fb1007c5dab3b7f18`; final Transfer density is 0/12 at all thresholds, so the development-smoke gate did not trigger. Supply economics classify `GLOBAL_TYPED_DISCOVERY_DOMINATES_COST`.
- Final focused tests: 238/0. Canonical full suite: 1,734 passed / 1 failed, solely the known unrelated source-research coordinator classification failure; new failures 0. Historical safety, AOM development control, lifecycle invariant, and architecture-freeze file hashes pass. The canonical copyright scan found one 12-word TN overlap in catalogue row `TOPIC-cbf55dc6ec094ff4`, whose preferred label is extraction garbage (`I Primary Suro agement ... of Toxicology`). This violates the catalogue requirement that extraction fragments be excluded. Because repairing catalogue construction would change frozen Discovery V3 after Transfer unblinding, `TRANSFER_CONTAMINATED=YES`, `COPYRIGHT_AUDIT=FAIL`, and the hard-stop contract requires a blocked checkpoint rather than an in-place repair. Canonical report: `reports/qgen_global_typed_discovery_v3_cache_transfer12_milestone.json`. `READY_FOR_NEW_OPERATIONAL_HOLDOUT=NO`; `NEXT_DOMINANT_BOTTLENECK=CATALOGUE_EXTRACTION_ARTIFACT_FILTER_AND_TRANSFER_REFREEZE`; `QGEN_NEXT_STEP=RESOLVE_BLOCKER_BY_ADDING_A_RED_EXTRACTION_GARBAGE_REGRESSION_TEST_FIXING_THE_CATALOGUE_FILTER_THEN_REFREEZING_AND_RERUNNING_TRANSFER_12_FROM_THE_ZERO_TOPUP_BASELINE`.
- **Catalogue-integrity repair + Discovery-V3 diagnosis + Decision-Compatible Discovery V4 milestone (2026-09-09): COMPLETE, but not ready for a new transfer cohort.** The old Transfer-12 is permanently reclassified as `DISCOVERY_V3_DIAGNOSTIC_TRANSFER_12`; its roster hash remains `9c738a1500da7b57d0a209ffc6937411f94208628fac75e3ba3cc75108ca2ee7`, its original V3 results remain immutable, and it is prohibited from future fresh-transfer, operational-holdout, or unseen-generalization claims. The frozen V1/V3/cache/Transfer files reverified byte-identically; no commit, reset, clean, stash, or frozen-artifact modification occurred.
- The full 1,919-row catalogue audit classified `VALID_CONCEPT=1834`, `OCR_GARBLED_LABEL=13`, `STRUCTURAL_FURNITURE=10`, `OTHER_INVALID=61` (59 canonical stem-feature statements plus two unbalanced labels), `UNCERTAIN=1`, and zero in the remaining required categories. The known copyright-failing row is caught by a general repeated-extraction-filler rule rather than an ID/string ban. Clean Catalogue V2 is a fresh canonical-source rebuild child of V1, contains 1,834 concepts, removes/fails closed on 85 rows, and has `content_sha256=ab2ff3ab8a9732f3b11edaaba5adbff00f0258902539a066bc36cd74d4b35ea2`. Copyright scan over all 13 new tracked artifacts is PASS with zero 12-word Toronto Notes overlap.
- The 52 frozen Transfer `WRONG_DECISION` rows were reconstructed with learner decision, key-as-canonical-decision statement, candidate identity/type/granularity/source metadata, V3 ranking signals, and prior verdict/reason. Eight serial representative group reviews (under the limit of 12) produced: `WRONG_DECISION_INTENT=20`, `WRONG_TARGET_CONDITION=21`, `WRONG_ETHICAL_LEGAL_ACTION=11`, all other taxonomy values 0. `DOMINANT_V3_SEMANTIC_GAP=MULTIPLE_COMPARABLE_CAUSES`: V3 lacks both the act being decided and the target decision domain.
- Candidate Decision Signature V1 is approved and implemented with three exact-match dimensions: `decision_intent`, `target_domain`, and `clinical_stage`; value counts are 11/11/7. It maps all 90 typed Catalogue-V2 candidates and 19 development/control opportunities, carries zero disease-specific exception rules, and passed its economy and separate pre-replay review. Signature hash: `9264ec971023ff79b33140e8d550cb71e9ede6860a2ca7a0ff82368d8cd3354a`.
- Discovery V4 implementation hash is `00d79f38f8de5efd22416cbb3057a8cd1f76835415be48d3e31347b2b1394ca4`. It preserves V3 global canonical search, response-class/granularity gates, deterministic ranking/provenance and ten-candidate budget, but applies signature compatibility before ranking. Build-12 replay: 9 candidates/semantic survivors, 5 clinically plausible, 4 wrong decision, 0 second-key/uncertain; all five V3 plausible candidates remain and the AOM/HbA1c/TTE/chest-radiography controls pass. Two below-V3-budget mood-diagnosis survivors received the only new V4 reviews and were both `WRONG_DECISION`; the algorithm was not changed in response.
- Diagnostic Transfer-12 V4 replay (development evidence, not validation): 2 candidates/semantic survivors, 0 clinically plausible, 0 wrong decision, 2 potential second keys, 0 uncertain. Wrong-decision rate fell from `52/54` to `0/2`, and V4 avoided 67 semantic reviews across the two replays, but candidate volume fell from 24 to 9 on Build-12 and 54 to 2 on diagnostic Transfer; Transfer produced no plausible candidates and the surviving set is entirely second-key risk. `DISCOVERY_V4_ASSESSMENT=PROMISING`, architectural consequence `V4_SUPPLY_TOO_SPARSE`, not validated.
- Final verification: focused **277 passed / 0 failed**. The one canonical full-suite run at final shared-code state finished **1,773 passed / 1 failed**, solely the known unrelated source-research coordinator `AWAITING_INTEGRATION` versus `INTEGRATED` classification test; `NEW_TEST_FAILURES=0`. Historical safety, AOM development control, lifecycle invariant, frozen hashes, and copyright pass. `READY_FOR_NEW_TRANSFER_COHORT=NO`; no new cohort was selected or consumed. `NEXT_DOMINANT_BOTTLENECK=TARGET_ENTITY_SUBDOMAIN_AND_SAFE_COMPETITOR_SUPPLY`; `QGEN_NEXT_STEP=IMPROVE_DECISION_SIGNATURE` without consuming a clean cohort.
- **Decision Signature V2 + Discovery V5 + Clinical Contrast Bundle V1 development milestone (2026-09-09): COMPLETE.** Starting HEAD remains `01eff40984bee76418c7fab82a1ded9fbfa2d9e5`; no commit, reset, clean, stash, or frozen-artifact modification occurred. Signature V2 preserves the three canonical V1 dimensions and adds only `target_subdomain` plus `semantic_containment_role`; its 27 registered development/control opportunities use a reusable 12-value subdomain vocabulary rather than one value per opportunity. Signature hash `fed7c5289d576c6ff91e979c7b584d010cd708c01b17cc5017839c3f995d17c0`; frozen compatibility benchmark 85/85 positives retained and 6/6 hard negatives rejected. Discovery V5 implementation hash `1d09592dd12242370f3de5186e5d491e11d1f141e41ae2dd41cfda206f2ca222`; it retains global Catalogue-V2 search and deterministically gates response class, granularity, V2 signature, subdomain, applicability, aliases/generic concepts, and containment before ranking.
- The frozen development roster contains 24 anchors. One bounded pool wave retrieved 113 canonical candidates; 113 survived cheap gates, 88 were clinically plausible, and all 88 received three-feature evidence-backed profiles (264 profile features). Independent bundle review admitted 80 alternatives and rejected 30, with 3 uncertain; options with no context in which they could become correct and options beyond the six-option cap remain excluded. The 24 matrices contain 240 candidate-linked feature rows. Admission: 11 `STRONG_BUNDLE`, 10 `MINIMUM_GENERATABLE_BUNDLE`, 2 `PARTIAL_BUNDLE`, 1 `NO_SAFE_BUNDLE`; cache hash `c7eea4d559302f9fcf88a0423c2ecaddf369982fb50a9c74851b9544a59d5c5f`. Build-12 exact-anchor density is >=1 `4/8`, >=2 `1/8`, >=3 `0/8`, >=4 `0/8`; contaminated diagnostic Transfer-12 development replay is >=1 `2/12`, >=2 `2/12`, >=3 `2/12`, >=4 `0/12`. This supports `CONTRAST_BUNDLE_V1=PROMISING`, not validated; economics are `BUNDLES_PROMISING_BUT_AUTHORING_HEAVY` because reuse across multiple opportunities remains zero and exact Build-12 three-option density remains zero.
- Educational review sampled 6 generatable bundles: 6 strong, 0 adequate/weak/unsafe. The no-retry development smoke generated and final-reviewed 5 cross-discipline items; all 5 were accepted with zero recorded safety defects. Historical safety, AOM control, lifecycle invariant, frozen hashes, and the zero-overlap Toronto Notes copyright audit all PASS. Focused verification: **235 passed / 0 failed**. The canonical full suite at final shared-code state: **1,796 passed / 1 failed**, solely the same known source-research coordinator `AWAITING_INTEGRATION` versus `INTEGRATED` expectation; `NEW_TEST_FAILURES=0`.
- `READY_FOR_NEW_CLEAN_TRANSFER=YES`. A new outcome-blind Transfer-18 has been frozen but not run: 3 per discipline, cohort hash `dae0e32368878130efaf20e38fa41c576e0c4194d8d6687a169e558e2b459a49`. Selection deterministically excludes 157 study units found across every prior pilot/development/transfer/holdout selection artifact plus the current bundle roster; candidate retrieval and generation remain unrun. `NEXT_DOMINANT_BOTTLENECK=BUILD12_EXACT_ANCHOR_BUNDLE_DENSITY`; `QGEN_NEXT_STEP=RUN_NEW_CLEAN_TRANSFER_VALIDATION`.
- **Clean Transfer-18 bundle validation (2026-09-09): COMPLETE, uncontaminated negative result.** Starting HEAD remains `01eff40984bee76418c7fab82a1ded9fbfa2d9e5`; the frozen cohort hash is `dae0e32368878130efaf20e38fa41c576e0c4194d8d6687a169e558e2b459a49`, and its false run/retrieval flags, 3x6 distribution, 157-unit exclusion inventory, and no-outcome selection contract were verified before unblinding. Validation contract hash: `24ebf8b12fd5b35a58358b679ca5b955136d62420000983e2110e8dfdd2baf40`. All 18 learner-decision/key/signature prerequisites were authored and reviewed without candidate visibility, so `TRANSFER_PREREQUISITE_READY=18/18`.
- Zero-top-up replay against immutable Bundle Cache V1 produced zero alternatives for all 18 anchors: every one-through-five threshold is `0/18`, contrast-ready `0/18`, and seed/relation/anchor/feature/bundle/cross-unit/cross-discipline reuse are all zero (`ZERO_REUSE`). The single frozen Discovery-V5 wave then scanned 1,834 Catalogue-V2 rows for each anchor (33,012 deterministic row decisions), with budget 8 and no repeat search, but returned **0 canonical candidates and 0 semantic survivors**. Rejections were `WRONG_RESPONSE_CLASS=32,941`, `GENERIC_CONCEPT=54`, `MISSING_CANDIDATE_SIGNATURE=8`, `WRONG_GRANULARITY=5`, and `KEY_ALIAS=4`. With no survivor, no clinical review, feature profile, evidence request, matrix, pairwise review, or alternative authoring was permitted.
- Final density is `NO_SAFE_BUNDLE=18/18`, with all >=1 through >=5 thresholds `0/18`. Append-only Cache V2 references the immutable V1 parent and adds zero bundles/alternatives; hash `57e80b8cb965d17c37520ab2066b9a6913fc700eddd47145718f9dec7030382d`. The conditional generation gate was not met: 0 stems, blind solves, liveness passes, final reviews, acceptances, rejections, or retries; `ACCEPTED_ITEM_SAFETY=NO_ACCEPTED_ITEMS`. Assessment: `LOW_TRANSFER`; economics: `DISCOVERY_STILL_DOMINATES_COST` because the frozen catalogue/typing layer supplied no response-class-compatible, V2-signed concepts for any untouched anchor. This is low yield, not evidence of unsafe accepted output, and no architecture rule was changed after unblinding; `TRANSFER18_CONTAMINATED=NO`.
- Final integrity: architecture freeze PASS; historical safety, AOM development control, lifecycle invariant, and copyright audit PASS (zero Toronto Notes overlap across seven new data artifacts). Focused validation: **240 passed / 0 failed**. The one pre-unblinding canonical full-suite run at final shared-code state: **1,803 passed / 1 failed**, solely the known unrelated source-research coordinator `AWAITING_INTEGRATION` versus `INTEGRATED` expectation; `NEW_TEST_FAILURES=0`. No commit, reset, clean, stash, checkout, or historical frozen-artifact modification occurred; `CLAUDE.md` is unchanged. Canonical report: `reports/qgen_clean_transfer18_bundle_validation.json`. `NEXT_DOMINANT_BOTTLENECK=EXACT_ANCHOR_CANONICAL_CANDIDATE_TYPING_AND_RESPONSE_CLASS_COVERAGE`; `QGEN_NEXT_STEP=IMPROVE_EXACT_ANCHOR_BUNDLE_DENSITY`.
- **Exact-anchor reference candidates + Candidate Role Registry V1 + Discovery V6 development milestone (2026-09-09): COMPLETE.** The clean Transfer-18 result is now consumed and permanently reclassified `EX_CLEAN_TRANSFER_NOW_DEVELOPMENT_DIAGNOSTIC`; it may be used for development diagnosis but never again for fresh/unseen V6-or-later validation. Starting HEAD remains `01eff40984bee76418c7fab82a1ded9fbfa2d9e5`; the original Transfer-18 cohort, validation contract, Signature V2, Discovery V5 implementation, and Bundle Cache V1 hashes remain exactly `dae0e32368878130efaf20e38fa41c576e0c4194d8d6687a169e558e2b459a49`, `24ebf8b12fd5b35a58358b679ca5b955136d62420000983e2110e8dfdd2baf40`, `fed7c5289d576c6ff91e979c7b584d010cd708c01b17cc5017839c3f995d17c0`, `1d09592dd12242370f3de5186e5d491e11d1f141e41ae2dd41cfda206f2ca222`, and `c7eea4d559302f9fcf88a0423c2ecaddf369982fb50a9c74851b9544a59d5c5f`.
- The canonical frozen V5 funnel reconciles all **33,012** candidate-anchor evaluations: `CATALOGUE_IDENTITY=54`, `RESPONSE_CLASS=32,941`, `DECISION_GRANULARITY=5`, `SIGNATURE_V2=8`, `KEY_OR_ALIAS=4`, and every later/other/accepted bucket `0`. A new reproducibility diagnostic records that the current helper replays `RESPONSE_CLASS=32,606`, `DECISION_GRANULARITY=25`, and `SIGNATURE_V2=323`; the frozen wave persisted per-anchor aggregate reason counts but not candidate-level decisions, so the canonical observed counts remain authoritative and the mismatch is not rewritten. Catalogue V2 role inventory is 1,834 total: 90 single-role, 0 multi-role, 1,744 untyped, 0 ambiguous. Declared `RESPONSE_CLASS_AXES` correctly normalize the demanded generic tokens; no semantic-equivalent string mismatch was found.
- Anchor Reference Candidate Set V1 (`content_sha256=fc0ad21c2d4929b147f888b114ed3171f7795a14cf7961fcfc297ee6e193ff47`) proposed 72 same-response-class alternatives. A fresh independent GPT-5.6 Sol HIGH review, serial in 18 batches of four and blinded to V5 rankings, returned **60 APPROVED_REFERENCE, 10 REJECTED, 2 UNCERTAIN**; uncertainty fails closed. Admission is 10/18 `REFERENCE_STRONG`, 5/18 `REFERENCE_MINIMUM`, 3/18 `REFERENCE_PARTIAL`, 0/18 `REFERENCE_NONE`. Sixty approved candidate profiles contain 180 clinical-review feature rows, but **0 are candidate-specific evidence-backed**; they remain teaching hypotheses requiring targeted canonical evidence.
- Approved-reference Catalogue-V2 coverage is `EXACT_PRESENT=11`, `ALIAS_PRESENT=0`, `RELATED_CONCEPT_ONLY=36`, `ABSENT_FROM_CATALOGUE=13`, all parent/child/ambiguous buckets 0. Of the 11 exact-present candidates, response-role coverage is 1 correct and 10 untyped. Earliest V5 loss across all 60 approved references is `ABSENT_FROM_CATALOGUE=49`, `RESPONSE_CLASS=10`, `SIGNATURE=1`, all other buckets 0. `ROOT_CAUSE=MULTIPLE_COMPARABLE_CAUSES`, with exact candidate catalogue coverage dominant and response-role coverage material.
- Candidate Role Registry V1 is independently contract-approved and `PROMISING`, hash `bfdf744fa25dab55d4e8f297dc5995b1c540ceb62bd824d72f6b5866e1fd3d81`: 148 typed/single-role candidates, 0 multi-role, 1,734 Catalogue-V3 concepts left untyped/fail-closed, 58 manually reviewed unique reference identities, and 90 deterministically derived historical entries. Immutable-child Candidate Catalogue V3 adds 48 reviewed identities (49 approved absent/related occurrences with one reused identity), total 1,882, hash `f9e4f6d299b9c789df53cc8c338f9d2319de4792880d6d33289038b633a3b5df`.
- Discovery V6 is implemented as the minimal role-registry repair while retaining granularity, Signature V2, subdomain, applicability, containment, key/alias, and eight-candidate-budget gates; implementation hash `20ba89b4d5dfc5c58e8f2af431138d2ca7fee6d17fe0d3cd8cdf2f73e97257df`. On the development reference benchmark, V5 recall is 0/60 and V6 recall is 60/60 with precision 60/60; anchors with >=1/2/3/4 references retrieved are 18/18, 17/18, 15/18, and 10/18. This benchmark is reference-informed and therefore supports `DISCOVERY_V6=PROMISING`, not validation.
- No Contrast Bundle V1 artifact was admitted: model review is not evidence, all 18 anchors remain `NO_SAFE_BUNDLE_NEEDS_CANDIDATE_SPECIFIC_EVIDENCE`, the educational audit and conditional question generation did not run, and 0 development questions were generated. Thus diagnostic bundle density did not improve from V5 zero, `READY_FOR_NEW_CLEAN_TRANSFER=NO`, and no new cohort was selected or run. Economics classify `CATALOGUE_COVERAGE_DOMINATES_COST`, followed by candidate-specific feature evidence. Focused tests: **277 passed / 0 failed**. Canonical full suite: **1,825 passed / 1 failed**, solely the known unrelated source-research coordinator expectation; `NEW_TEST_FAILURES=0`. Copyright scan: PASS across 16 artifacts with zero 12-word Toronto Notes overlap. Historical safety, AOM control, and lifecycle: PASS. No commit, reset, clean, stash, checkout, or frozen historical-artifact modification occurred; `CLAUDE.md` is unchanged. Canonical report: `reports/qgen_exact_anchor_candidate_typing_discovery_v6_milestone.json`. `NEXT_DOMINANT_BOTTLENECK=CANDIDATE_SPECIFIC_FEATURE_EVIDENCE`; `QGEN_NEXT_STEP=IMPROVE_FEATURE_EVIDENCE_PIPELINE`.
- **Candidate-specific feature evidence + evidence-backed Bundle V2 development milestone (2026-09-09): COMPLETE.** Starting HEAD remains `01eff40984bee76418c7fab82a1ded9fbfa2d9e5`; the fixed 60-candidate cohort is hash-bound at `bf86e7d68f54e3afb995cb0dd5026524d80c2d5c06c8b1bc7d6e1e8e7b717ca0` to Reference Set `fc0ad21c2d4929b147f888b114ed3171f7795a14cf7961fcfc297ee6e193ff47`, and excludes all 10 rejected and 2 uncertain references. All 180 provisional rows were audited `LOAD_BEARING`. Baseline repository coverage was 0 exact, 0 semantic, 33 partial and 147 absent; a TDD regression now prevents the milestone's own generated outputs from contaminating that baseline on replay.
- Feature Evidence Registry V1 contains 180 normalized, source-traced propositions from 26 authoritative source records, all serially reviewed `ENTAILED`; registry hash `a297ed7f79613ee6b326dc0e91ae78834a6872f1d9ca99d03b27b932f5e7d660`. All 60 candidates have three verified facts, positive plausibility, a pairwise discriminator and a what-makes-correct proposition; none has independently grounded next-step evidence. The evidence-backed bundle cache hash is `c8e9aa10353d650679f7f55d3e59cdb924f33c1ff176bd72481f5d0602c9a26d`, with 10/18 STRONG (>=4), 5/18 MINIMUM (3), 3/18 PARTIAL (1-2), 0 NO_SAFE; thresholds are >=1 18/18, >=2 17/18, >=3 15/18, >=4 10/18. The deterministic educational sample was 4 STRONG and 4 ADEQUATE.
- The conditional development gate fired. Ten no-retry evidence-traced questions were generated across MED/PED/OBGYN/SURG/PSY (two per discipline); PHELO was omitted because its actions were sequential or consent-contingent and carried avoidable second-key risk. Separate serial blind-solve, post-stem-liveness and final medical review artifacts passed 10/10; accepted-item safety is PASS with zero recorded factual, unsupported, certainty, second-key, absence-inference, response-class, granularity, overstatement, next-step, rationale or cueing defects.
- The scientific result is `FEATURE_EVIDENCE_PIPELINE_ASSESSMENT=AUTHORING_HEAVY`, not validated: 180 propositions required new research, zero proposition safely reused across anchors or candidate contexts, and next-step coverage is 0/60. `PRODUCTION_ECONOMIC_MODEL=PAIRWISE_CONTRAST_EVIDENCE_DOMINATES_COST`. Accordingly `READY_FOR_NEW_CLEAN_TRANSFER=NO`; no clean cohort was frozen or run. Historical safety, AOM control, lifecycle, and copyright are PASS; the copyright scan covered 18 content artifacts with zero 12-word Toronto Notes overlap. Final focused tests **158/0**; canonical-equivalent full suite **1848/1**, solely the known unrelated source-research coordinator `AWAITING_INTEGRATION` versus `INTEGRATED` test, so `NEW_TEST_FAILURES=0`. No commit or frozen historical-artifact modification occurred; `CLAUDE.md` is unchanged. Canonical report hash `b83a8d3fdf111f390a1f321ed4ab19dc571811d2a09da496bf0db629e9fc164b`. `NEXT_DOMINANT_BOTTLENECK=EVIDENCE_REUSE_AND_NEXT_STEP_COVERAGE`; `QGEN_NEXT_STEP=REDESIGN_EVIDENCE_AUTHORING_ECONOMICS`.
- **Expanded Candidate Universe V1 + Evidence Economy V2 + Question Seed V1 development milestone (2026-09-10): COMPLETE.** Starting HEAD remains `01eff40984bee76418c7fab82a1ded9fbfa2d9e5`; all historical inputs are hash-bound and unchanged. `ANCHOR_CANDIDATE_UNIVERSE_V1` hash `effd06d5f7439657ab06eb550a76ceed4722fc3cea1923e17951a16df2e2ffa1` contains 108 distinct proposals across the same 18 consumed development anchors: 60 existing-bundle-derived, 12 canonical-catalogue-derived, and 36 model-proposed. Stage 1 recorded 87 plausible, 15 rejected, and 6 uncertain. Stage 2 admits exactly the prior 60 evidence-backed candidates; all 27 Stage-1-plausible model proposals remain `UNCERTAIN` for insufficient independent evidence, and none enters a bundle. Approved density remains min 1 / median 4 / mean 3.33 / max 4, with >=3 15/18, >=4 10/18, and >=5 0/18. Six bounded passes end with two consecutive zero-yield saturation checks; marginal approvals per pass are `[60,0,0,0,0,0]`. Generated-candidate strategy is `LOW_VALUE` at the current evidence cost, not unsafe.
- `CONCEPT_FEATURE_CARD_V1` hash `1a0af52239340ed62a2298a71ed7ee172890ec3804421765a7c6f238114b5cb7` contains 59 canonical concept cards backed by all 180 entailed V1 facts; one concept is shared by two anchors. Fact applicability was not widened: cross-anchor and cross-candidate fact reuse both remain zero. Evidence grouping nevertheless reuses 25 authoritative source families across candidate concepts and 3 across anchors. Multi-source status is 27 concordant cards and 32 single-authoritative-source cards, with 0 conflicting or insufficient among admitted concepts. No new evidence request was issued: model proposals fail closed before expensive research.
- Next-step coverage improves from 0/60 to **26/60** without inventing new clinical facts: the 14 management, 9 ethical/legal, and 3 investigation candidates reuse their already-entailed `WHAT_MAKES_CANDIDATE_CORRECT` context as `NEXT_ACTION_IF_THIS_CONTEXT_WERE_PRESENT`. The 34 diagnosis candidates remain explicitly `MISSING` direct next-step evidence; none is relabelled by inference. `CANDIDATE_COMPATIBILITY_GRAPH_V1` hash `ea8c1dc044f854e204da88e20fd45f234b7938ca67c2f6ae1b1d17c1991d533b` has 67 reviewed sparse edges, of which 30 are reused across preferred three- and four-distractor subset plans. `CLINICAL_CONTRAST_BUNDLES_V3_EXPANDED` hash `92d53f63912a64d9f21e198fb54190e50f11531f91457167030aa741d6c4d299` preserves the full approved universe and reserves.
- `QUESTION_SEED_V1` is implemented at hash `fe994fbe67dd5c6e25818887aee15b783417f518685e4e1f60b2c938e8add7e6`: 18 deterministic seeds bind curriculum context, learner decision, key, clinical stage/population, discriminator, candidate universe, subset strategy, family, and semantic fingerprint. A deliberate duplicate control is rejected pre-generation; replaying semantic item fingerprints over the existing 10 accepted development items yields 0 near-duplicates and 0 duplicates. No new questions were generated, no clean Transfer cohort was frozen, and no operational holdout ran.
- Historical safety, AOM control, lifecycle, and copyright PASS; the copyright audit covered 12 new content artifacts with zero Toronto Notes overlap. Focused verification is **172/0**. Canonical full suite at final shared-code state is **1,877/1**, solely the known unrelated source-research coordinator expectation; `NEW_TEST_FAILURES=0`. No commit, reset, clean, stash, checkout, or frozen historical-artifact modification occurred; `CLAUDE.md` is unchanged. Milestone report hash `316f05386a6a23b8ce2dd8461f37631677396938a43e7376c97a05bc84768aa7`. `READY_FOR_NEW_CLEAN_TRANSFER=NO`; `NEXT_DOMINANT_BOTTLENECK=MODEL_PROPOSAL_EVIDENCE_ACQUISITION_AND_DIRECT_DIAGNOSIS_NEXT_STEP_EVIDENCE`; `QGEN_NEXT_STEP=EXPAND_CONCEPT_FEATURE_LIBRARY`.
- **Model-proposal evidence validation + Concept Feature Library V2 + Question Seed end-to-end development milestone (2026-09-10): COMPLETE.** The frozen 27-row model cohort is `864135621929be054b64e46124c7d705e07001efbfe119fe47402c9ebdd261b0`: 21 were evidence-researched and 6 deterministically rejected; final Stage 2 is 19 approved, 8 rejected, 0 uncertain (evidence-validated approval rate 0.7037, `GENERATED_CANDIDATE_STRATEGY=VALUABLE`). Source status across all 27 is 15 multi-source concordant, 6 single-authoritative-source, 0 conflicting, and 6 insufficient. TN source-first replay found four structural identities, all already known, supporting `MULTIPLE_CAUSES` (no genuinely new TN candidates plus historical provenance collapse). Multi-origin provenance is preserved in Candidate Provenance V2 hash `500c260703196e2dd8017faa903789d70a78fcbba51a25861bbfbec89680616d`.
- Existing fact-scope review classifies the 180 entailed facts as 60 concept-intrinsic, 60 context-dependent, and 60 pairwise-only; all other/uncertain scope buckets are zero. Concept Feature Library V2 hash `fe76778300159bf03efd02f89875e510da24f3f0896964c0c3218823f16e748a` safely reuses 8 facts across anchors and 8 across candidate occurrences. Conditional Next Action V1 hash `7d13f1af8fdc6c3a0f84556522ad968a96e35017bee05c40a59d2f929188b3ab` covers all 79 approved candidate occurrences, with 79 having at least one verified branch and 14 having at least two; missing/not-applicable are zero. Evidence economics classify `MODEL_EXPANSION_PLUS_CONCEPT_EVIDENCE_SCALES`: 15 source retrieval groups reused and 19 pairwise requests avoided.
- Additive Candidate Universe V2 hash `1aa3ca135c3b22696ab0c94dbcd122fba08d48a122dbdd2973fdef74b25f8114` admits 79 candidates, density min 1 / median 4.5 / mean 4.39 / max 6; >=3 is 15/18, >=5 is 9/18, and >=8 through >=20 are 0/18. Three fully adjudicated saturation passes yielded `[19,0,0]`. New quality tiers are 14 A, 4 B, and 1 C. Compatibility Graph V2 hash `a4ecd869eeddaf730950d4a2ada50f7c4af58ba1a1fcbb9ecd9e659fc00d5c66` contains 86 relations, including 19 derived without new pairwise research; expanded Bundle V4 hash is `d28d13de3f644f95406b97abef38ac2d4669c6e0a9c6a0dbd66d3c4c89c24d0f` and preserves all reserves.
- Question Seed V1's prior zero-item result is diagnosed as `MISSING_RUNNER_AND_VOLUNTARY_SKIP`. The new deterministic no-retry lifecycle proposed 7 seeds, rejected 1 near-duplicate before generation, generated and accepted 6 evidence-traced development items, and passed 6/6 blind solves, 6/6 post-stem liveness reviews, and 6/6 final medical reviews. Post-generation review found 0 near-duplicates and 0 duplicates plus 1 same-topic substantively distinct pair. Shared duplicate classification now rejects superficial same-objective rewrites while allowing a materially different clinical stage.
- Final integrity: 22 artifacts reproduce byte-for-byte; historical frozen hashes, AOM control, lifecycle, and copyright PASS. Focused verification is **244/0**. The canonical full suite at final shared-code state is **1,888/1**, solely the known unrelated source-research coordinator `AWAITING_INTEGRATION` versus `INTEGRATED` expectation; `NEW_TEST_FAILURES=0`. No clean cohort was run and no operational holdout or mass generation occurred. A balanced 18-row Transfer cohort was frozen but unrun at hash `4227403aae3940b8c78a5ec3aeddaaa1fb5bb34342df5a4bc9a0a9a80eabab7b`. No commit or frozen historical-artifact modification occurred; `CLAUDE.md` is unchanged.
- **Clean Transfer-18 model-expansion validation preflight blocked on cohort contamination (2026-09-10).** Before any candidate-supply or clinical roster-content inspection, append-only instrumentation froze 20 semantic inputs in `CLEAN_TRANSFER18_VALIDATION_CONTRACT_V1`, hash `a2f6be5f59e06bc46a27ce97ce712b04dea10abbfbc2f46342851ecf4d7ec761`. The exact expected cohort hash and 3-per-discipline balance both verify, but the deterministic historical-roster audit proves all **18/18 study units overlap prior QGEN cohorts**: 6 occur in `new_clean_transfer_18_selection_v1.json` and 12 occur in the completed `fresh_operational_holdout_18_opportunities.json`. The two overlap sets are disjoint. Cleanliness proof hash `eeebb29a1d612f7b6dc3fa896c345facd0dbb7ef304acf72f05bf93f9048607d`; blocked milestone report hash `2fefdfeb359ac6e0291e3b03933284d4e1098654b224080e7098ff8a62e30f48`.
- Protocol hard-stop A therefore fires: `TRANSFER18_UNTOUCHED_VERIFIED=NO`, `TRANSFER18_CONTAMINATED=YES`, and the milestone is `BLOCKED` at Phase 1. Phases 3-45 and the clinical-content portion of Phase 46-48 were not run; no candidate retrieval, model proposal, clinical candidate review, candidate-specific research, question generation, or historical safety replay was performed. The five new preflight tests pass, architecture freeze integrity passes, and a canonical 12-word Toronto Notes overlap scan of the three preflight artifacts passes with longest run 0. No commit was created, and no historical frozen artifact or `CLAUDE.md` was changed. `READY_FOR_PRODUCTION_SCALE_UP=NO`; `NEXT_DOMINANT_BOTTLENECK=TRANSFER18_COHORT_CONTAMINATION`; `QGEN_NEXT_STEP=RESOLVE_BLOCKER` by freezing a genuinely untouched balanced cohort before any clean-transfer claim.
- **Canonical QGEN Exposure Registry V1 + clean Transfer V2 validation milestone (2026-09-10): COMPLETE.** Starting HEAD remains `01eff40984bee76418c7fab82a1ded9fbfa2d9e5`. The historical blocked cohort `4227403aae3940b8c78a5ec3aeddaaa1fb5bb34342df5a4bc9a0a9a80eabab7b` and its contract/proof/report remain byte-for-byte preserved; the semantic registry confirms every row is Level 8. `QGEN_EXPOSURE_REGISTRY_V1` hash `12cf1a79917b3795d79a1a94574ad910bbc0865d71e3cb1d07bb9305543b8e67` covers 885 units: inventory-only 0, metadata-only 699, reserved-not-inspected 0, prerequisite-reviewed 0, candidate-supply-inspected 0, clinical-candidate-reviewed 0, evidence-authored/reviewed 2, question-generated/reviewed 4, architecture-outcome-used 179, ambiguous 1. Before reservation, clean-eligible counts were MED 359, PED 78, OBGYN 36, SURG 210, PSY 5, PHELO 11; remaining AVAILABLE counts after reserving the new cohort are MED 356, PED 75, OBGYN 33, SURG 207, PSY 2, PHELO 8.
- Cohort Selector V2 implementation hash is `60e7e5e7b63272ce3b12f8da00921cf936264d8d2a74a14b463798e8c6c1f024`. It selected a stable-order, outcome-blind, balanced 18-row cohort (three per discipline), hash `58d6b9b9779aac2fae51854d3c71d46b1b3047bef13939b44f2ba5747320754f`. The independent cleanliness proof passes with 0 overlaps, hash `b30496b9333cd9a443d0e48aa06bddc15c969f7a6974dbe6f1e8a90590cd5fb1`. Validation Contract V2 was frozen before candidate-supply unblinding at hash `cb26990650fcb4fdfb65168fd6a23c85bb8855d39b210ad7ad7f942854d9b397`. Pre-unblind focused tests passed 118/118; the canonical full suite passed 1,921 with the sole known unrelated source-research-coordinator failure (`NEW_TEST_FAILURES=0`). No shared semantic code changed after unblinding.
- Clean transfer results: zero-authoring reuse and frozen Discovery V6 both supplied 0 candidates. The Toronto Notes structural pass found six identities (five already known, one genuinely new). Source-first supply proposed and approved 6/6. The model proposed 36 candidates: 18 Stage-1 plausible and evidence-researched with multi-source concordance, all 18 Stage-2 approved; 18 were deterministically rejected before evidence and terminally Stage-2 rejected; 0 uncertain and 0 second-key risk. Clean model approval is 18/36 = 50%, descriptively below development 19/27 and classified `PROMISING`. Full approved-universe density is min 0 / median 0 / mean 1.33 / max 4, with six anchors >=3 and none >=5. Three fully adjudicated passes yielded `[18,0,0]` and satisfy the frozen saturation rule.
- Clean evidence economics: 0 concept facts reused, 24 new; 36 source bindings reused after 12 grouped new retrievals; 42 pairwise research requests avoided. Conditional next actions have 24 new verified branches, 24/24 approved candidates covered, 0 missing. The append-only compatibility child has 36 new evidence-derived edges, 0 reused, and 0 pairwise research requests. Six bundles are contrast-ready and none is strong-choice-ready. Six distinct Question Seeds produced six no-retry original items, with 6/6 blind-solve, liveness, final-medical-review, and admission passes; pregeneration duplicates, postgeneration near-duplicates, duplicates, and rejections are all zero.
- Generalization assessments: Discovery V6 `LOW_TRANSFER`; model expansion `PROMISING`; Concept Feature reuse `LOW_REUSE`; Conditional Next Action `PROMISING`; expanded bundles `PROMISING`; Question Seed pipeline `VALIDATED`. `PRODUCTION_ECONOMIC_MODEL=SOURCE_PLUS_MODEL_ON_DEMAND_SCALES`: pre-existing reuse contributed no supply, while grouped authoritative evidence plus bounded model hypotheses produced one accepted clean item per discipline. Historical safety, AOM control, lifecycle, architecture freeze, and copyright all pass; the copyright scanner's only 12-word-plus overlap is a 15-token Canada.ca URL already present in Toronto Notes bibliographic metadata, with zero semantic-prose overlap. Milestone hash `e1734d84156e33594fa52873911244650bbd1201444734c6fc198ad7924bf6b3`. `READY_FOR_PRODUCTION_SCALE_UP=YES`; `NEXT_DOMINANT_BOTTLENECK=CURRICULUM_QUESTION_OPPORTUNITY_ENUMERATION`; `QGEN_NEXT_STEP=BUILD_CURRICULUM_QUESTION_OPPORTUNITY_REGISTRY`. No commit or frozen historical-artifact modification occurred; `CLAUDE.md` remains unchanged.
- **Curriculum Question Opportunity Registry V1 + opportunity dedupe + blueprint allocation + Question Seed population plan + Production Queue V1 milestone (2026-09-10): COMPLETE.** Starting HEAD remains `01eff40984bee76418c7fab82a1ded9fbfa2d9e5`. The canonical curriculum snapshot contains 1,165 unique in-scope study units from 1,175 eligible allocation addresses; ten extra eligible component-mode addresses are aggregated without reviving suppressed parents or double-allocating whole units. Snapshot hash `70c0875060e8aa5ae8563b70074fa365941b2eb7d4a2a32a2a6ed0fe776817a9`. One eligible unit (`SU-ER-34`) has no authored testable competency and remains explicitly zero with `INSUFFICIENT_DISTINCT_DECISION`.
- The registry contains **1,541 base opportunities** in 1,164 variant groups and **926** evidence-supported extra-item pathways, for a conservative defensible capacity of **2,467**. Registry hash `aa465f77c65ba21955e01c3ddf0f32de18022d6a76583bf1ed1da34e62a5e11e`. Discipline capacity is MED 1,360 (791 base + 569 variants), PED 312 (156 + 156), OBGYN 152 (100 + 52), SURG 393 (304 + 89), PSY 127 (89 + 38), and PHELO 123 (101 + 22). Medicine reaches its 1,086 frozen target comfortably; each other discipline is `NO_WITHOUT_DUPLICATION` for 1,000. The recommended initial bank target is therefore **2,193**, not 6,086: MED 1,086, PED 312, OBGYN 152, SURG 393, PSY 127, PHELO 123.
- Count-blind stratified opportunity review covered all six disciplines and all 20 observed opportunity families: 36 approved, 0 revise, 0 reject, 0 uncertain. Exact duplicate collapses 0; semantic near-duplicate collapses 0; 461 within-topic pairs are recorded as `RELATED_BUT_DISTINCT`. All 1,541 rows are `MCQ_STRONG` under the frozen preferred-item-form metadata. Readiness is 6 `READY_EXISTING_BUNDLE`, 1 `READY_EXISTING_CANDIDATES_NEEDS_SEED`, 30 `READY_ON_DEMAND_EXPANSION`, and 1,504 `NEEDS_EVIDENCE`; all other readiness buckets are zero. Existing development/clean-validation items are linked only as validation assets and are not counted as production-bank items.
- Allocation Plan V1 hash `73fbf8675c9221d98c5fe18edbce4edf7d45b5f451d61a6aeb6a511cd117c50b`; Production Queue V1 hash `7d88f03a109e68a82864f591369081b3098671633dfeadf134c5f1221fca58f3`, with 2,193 unique seed slots. Waves: WAVE_0 7, WAVE_1 735, WAVE_2 516, WAVE_3 283, WAVE_4 652. The deterministic 30-entry dry run spans all disciplines with 0 opportunity/seed duplicates and 0 dependency-routing errors. Recommended batch sizes are 40 for ready-existing assets and 20 for on-demand expansion. The production acceptance contract and stop rules are frozen; `READY_TO_GENERATE_PRODUCTION_WAVE_1=YES` because WAVE_1 contains 24 source-ready on-demand slots, enough for the recommended first 20-item bounded batch.
- A deterministic exposure-registry integration defect was repaired under TDD: curriculum planning artifacts now classify as QGEN exposure levels 0-1, while unit-specific count-blind opportunity reviews classify at level 3. This prevents metadata-only registry references from becoming ambiguous level 99 without hiding actual semantic review exposure. Historical safety, AOM control, lifecycle, and copyright PASS; copyright is zero 12-word Toronto Notes overlap across ten new content artifacts. Focused controls pass **88/88**. The final full suite is **1,936 passed / 1 failed**, solely the known unrelated source-research coordinator `AWAITING_INTEGRATION` versus `INTEGRATED` expectation; `NEW_TEST_FAILURES=0`. No commit or frozen historical-artifact modification occurred; `CLAUDE.md` is unchanged. `NEXT_DOMINANT_BOTTLENECK=SOURCE_AND_CANDIDATE_READINESS`; `QGEN_NEXT_STEP=GENERATE_PRODUCTION_WAVE_1` as a bounded 20-item on-demand batch, not mass generation.
- **Curriculum Opportunity Registry V2 completeness benchmark and production-pilot gate (2026-09-11): COMPLETE, PILOT NOT TRIGGERED.** A frozen 72-unit (12/discipline) development benchmark contains 675 independently enumerated atomic learner decisions, hash `4d6da8293535244d76361e034dd9b0ad4265c681c960b1e0d3dd281385d2c6e2`. V1 matched 38/675 strictly (recall 0.056296) while all 114 V1 benchmark-unit rows were supported (precision 1.0). Misses were dominated by `MISSING_DISCRIMINATOR_VARIANT=415`, with management 56, investigation 43, emergency 22, prevention 20, follow-up 19, counselling 17, communication 10, ethical/legal 9, diagnosis 6, complication 5, differential 4, and other 11. The frozen assessment is `MULTIPLE_ISSUES`: major underenumeration, classification bias, suitability overclaim, and a semantic-deduplication gap; not overgeneration.
- Blind V1 quality audits found suitability 51 STRONG / 54 ACCEPTABLE / 14 WEAK / 1 NOT_SUITABLE across 120 rows; blueprint accuracy was 0.666667 for Dimension of Care and 0.6 for Physician Activity, confirming major heuristic bias. The 150-pair duplicate stress test found 62 distinct, 79 related-but-distinct, 9 near-duplicates, and 0 duplicates. Enumeration V2 was implemented under TDD and applied curriculum-wide. The permitted single general revision added a blind, candidate-ID-agnostic semantic gate over 3,770 decisions: 1,539 V1 preserved, 2 deferred, 460 expansions approved, and 1,769 expansions rejected. Final Registry V2 has 2,001 opportunities (1,541 preserved + 460 new), hash `d1625711d9efd7db50a47ab54dd90a83de56302108775ecbac31f38afcd309c8`; exact and semantic collapse counts remain zero.
- Final independent evaluation did **not** validate V2: 18 semantic matches, 386 partial, 271 missing, 0 exact/invalid; strict recall 0.026667 and precision 0.127660 (18 supported / 122 ambiguous / 1 overgenerated among 141 benchmark-unit rows). Both metrics are below V1, and the nine unresolved near-duplicate pairs plus blueprint/suitability audit defects remain open. The production-pilot gate therefore failed and the required fail-closed policy generated **0 production items**. Allocation V2 (`6c9781c805267277318540f42556d4f968df8c81c8f515e58b4e1ecb2c23f950`) and Queue V2 (`ab1b462b7421ab5cf7948299e4ba97421b456722aaeca2024fba3433dcd3aa9b`, 2,002 slots) are diagnostic planning artifacts only and are not production authorization. V2 analytic capacity is conservative floor 1,119, recommended target 2,002, upper defensible 2,291; MED capacity 1,283, PED 293, OBGYN 110, SURG 392, PSY 112, PHELO 101. Only MED reaches 1,000 without duplication.
- The V2 semantic review is now explicitly represented at QGEN exposure level 3 for all 1,164 reviewed units, avoiding ambiguous level 99 while truthfully consuming metadata-only controls. Copyright PASS after review of one isolated 13-word anatomy fact inherited through canonical competency provenance; no substantial Toronto Notes prose was found. Focused historical controls pass **183/183**. The canonical `.venv` full suite is **1,967 passed / 1 failed**, solely the same known unrelated source-research coordinator `AWAITING_INTEGRATION` versus `INTEGRATED` expectation; `NEW_TEST_FAILURES=0`. No commit or frozen historical artifact was modified; `CLAUDE.md` is unchanged. `READY_FOR_PRODUCTION_BATCH_GENERATION=NO`; `NEXT_DOMINANT_BOTTLENECK=ATOMIC_ENUMERATION_AND_BENCHMARK_ALIGNMENT`; `QGEN_NEXT_STEP=REFINE_ENUMERATION_V2` in a future milestone, with no further tuning permitted in this completed evaluation cycle.
- **Atomic Opportunity Contract V1 + benchmark normalization + Matcher V3 calibration milestone (2026-09-11): BLOCKED AT THE REQUIRED MATCHER VALIDATION GATE.** The frozen contract hash is `c250e20c3da4e109c06c856c573e0e0006ab959ffd26faeccd2c55ebf3237e9a`. One opportunity is one clinically material state requiring one coherent, independently scoreable learner response. Cosmetic presentation, alternate evidence paths, item form, difficulty, distractors, and non-decision-changing demographics remain variants or Question Seed attributes. Response-class changes, independently scoreable decisions, material context changes, and distinct sequential outcomes require separate atoms.
- The V2 recall paradox is `ADJUDICATION_CONTRACT_DRIFT_AND_LINKAGE_FAILURE`, not content loss: all 38 V1 full matches have text-identical V2 descendants, but the unversioned V2 semantic pass downgraded 31 to partial and 2 to missing. The 675-row transition matrix reconciles, V1/V2 comparison inputs and outputs are frozen, and the preservation audit covers all 1,541 V1 rows. The provisional lineage-aware graph restores monotonicity but is not accepted as Matcher V3.
- A fresh blinded review classified 120 stratified V1 partials as 8 equivalent, 64 registry-broader, 1 registry-narrower, 3 same-decision variants, 43 related-distinct, and 1 uncertain; discriminator classes are 108 distinct-reasoning opportunities, 11 legitimate item variants, and 1 uncertain. No validated rule safely generalized beyond the sample, so the other 295 of 415 partials fail closed to uncertain rather than becoming enumeration additions.
- A separate benchmark-only reviewer audited 120 rows with sibling context: 95 atomic-distinct, 2 merge-with-sibling, 2 item-variant-not-opportunity, 16 compound-needs-split, 5 not-MC-suitable, and 0 specialist/uncertain. The immutable 675-row benchmark remains hash `4d6da8293535244d76361e034dd9b0ad4265c681c960b1e0d3dd281385d2c6e2`. Reviewed transformations only produce `NORMALIZED_ATOMIC_OPPORTUNITY_BENCHMARK_V2`, 145 atoms, hash `dba01681d56e3321256379eaf802cdd6a101cb4188f11ecbf86cb4d007229487`: 105 kept/merge targets, 4 source variant rows merged, 16 compound sources split into 40 atoms, 5 excluded as not MC-suitable, and 545 untouched rows deferred.
- The independent 24-study-unit gold set (4/discipline; 171 complete within-unit pairs) is hash `9004a3524debe6fc9025fe1ab1ae30f4c8d9ab4583b5d0811d916cae08a2893c`: 6 equivalent, 37 registry-broader, 118 related-distinct, and 10 unrelated. Matcher V3's held-out accuracy is only `0.023256` (2/86), and the holdout contains no independently labeled same-decision variant. It therefore cannot reliably distinguish the required equivalent/broader/variant/distinct classes. Phase 19 requires a hard stop: V1/V2 normalized metrics, gap taxonomy, Enumeration V3, canonical Registry V3, MCQ Suitability V2, final Blueprint Mapping V2, capacity, allocation, and queue were not authorized. The 2,001-row V3-shaped artifact is explicitly a noncanonical zero-capacity scaffold blocked by the matcher gate, not Registry V3.
- Semantic review exposure is explicitly linked at level 3; normalized/matcher outcomes are architecture-level; the rebuilt QGEN Exposure Registry has zero ambiguous units. Copyright PASS covers the contract, concise reviewed split labels, normalized benchmark, gold/matcher artifacts, provisional scaffold, blueprint scaffold, and confirms no substantial source-prose passage. Focused historical controls pass **260/260**. The final `.venv` full suite is **2,011 passed / 1 failed**, solely the known unrelated source-research coordinator `AWAITING_INTEGRATION` versus `INTEGRATED` expectation; `NEW_TEST_FAILURES=0`. V1 (`aa465f77c65ba21955e01c3ddf0f32de18022d6a76583bf1ed1da34e62a5e11e`), V2 (`d1625711d9efd7db50a47ab54dd90a83de56302108775ecbac31f38afcd309c8`), and benchmark hashes remain unchanged. No commit, reset, clean, stash, checkout, production question, or historical frozen-artifact modification occurred; `CLAUDE.md` is unchanged. `PRODUCTION_PILOT_GATE=FAIL`; `READY_FOR_PRODUCTION_PILOT=NO`; `NEXT_DOMINANT_BOTTLENECK=MATCHER_V3_RELATION_DISCRIMINATION_AND_VARIANT_HOLDOUT_COVERAGE`; `QGEN_NEXT_STEP=REFINE_MATCHER_V3` with a fresh relation-balanced held-out set before any registry redesign.
- **Relation Gold V2 + Matcher V4 architecture + Independent Item Verification V1 milestone (2026-09-11): BLOCKED at representative relation-class support; verifier infrastructure complete.** Matcher V3 remains frozen as the failed 2/86 opportunity-relation baseline. Two isolated reviewers independently labeled all 81 real mined pairs and a third fresh reviewer adjudicated all 8 disagreements; Gold V2 hash `7bff03312c9023244054f8760d75f1e706c0d13526cd2a9f3e600d4ce4b49cc3`, agreement 73/81 (`0.901235`), counts 4 equivalent, 42 related-distinct, 35 uncertain, and zero broader, narrower, variant, near-duplicate, duplicate, or unrelated. The pre-development split is frozen at `94f6ca616eda062d5256816f09f9577c45034c9839d89472d26286c512849a35`, but calibration, validation, and final held-out execution fail closed because critical classes lack support; variant held-out support is 0. Hybrid Matcher V4 contract hash `41f48e744e51e910f621c448a33cc8d2666ac6b0e9810b18accd70bceec24335` selects a deterministic recall prefilter plus constrained semantic classifier; no Registry V3 or normalized V1/V2 evaluation is authorized.
- Independent Item Verification V1 is implemented with strict production-package, blind-solve, evidence-audit, adjudication, and append-only hash-ledger schemas. Six historical development/clean-validation items (one per discipline) remain nonproduction validation fixtures. All seven seeded defects are detected: wrong key, second key, unsupported claim, false citation, outdated guidance, Toronto Notes conflict, and Canadian-guideline conflict. The external verifier prompt is `docs/qgen/INDEPENDENT_PRODUCTION_ITEM_VERIFIER_PROMPT.md` (file hash `d08b68006221dbb2a205b4ffe05aca00a843517fc3d2a1152764be2f351770f6`); package-schema file hash `a6d222bde3224983ef219d4e753f79a37e1ff521dd6d6ed64c4ff11825497e86`; empty-until-real-production verification-ledger content hash `5647678da319d896afe03e2291f361b3a6e00d85e67b8663975c4818d0e5a40b`. Copyright PASS after manual review of the machine scan's sole 15-token overlap: two Canada.ca URLs in source provenance and zero semantic prose. Focused verification is **137/0**. The final `.venv` suite is **2,057 passed / 1 failed**, solely the known unrelated source-research coordinator expectation; `NEW_TEST_FAILURES=0`. Historical safety, AOM control, and lifecycle pass. No production question, Registry V3, commit, or historical frozen-artifact change occurred; `CLAUDE.md` is unchanged. `READY_FOR_INDEPENDENTLY_VERIFIED_PRODUCTION_PILOT=NO`; `NEXT_DOMINANT_BOTTLENECK=REPRESENTATIVE_RARE_RELATION_CLASS_GOLD_AND_VARIANT_HOLDOUT_SUPPORT`; `QGEN_NEXT_STEP=EXPAND_RELATION_GOLD`.
- **Representative Relation Gold V3 + Matcher V4.1 calibration milestone (2026-09-12): PARTIAL_QUOTA_INTERRUPTION, MATCHER NOT SELECTED.** One deterministic mining wave produced 300 real pairs spanning all six disciplines. Two isolated reviewers agreed on 241/300 (`0.803333`); a fresh adjudicator resolved all 59 disagreements, leaving one fail-closed `UNCERTAIN`. Terminal Gold V3 hash `8ff4a8150f3213591dbbf0c8cc6fe55e79414cb914a7fbed9fe450bf61762c4a` contains 299 pairs: 12 equivalent, 37 registry-broader, 36 registry-narrower, 15 same-decision variants, 137 related-distinct, 10 near-duplicates, 23 duplicates, and 29 unrelated. Real-class support passes.
- Independent audit proved the first partition leaked shared study units and exact endpoint projections across splits. The TDD repair now partitions connected leakage components, excludes prior semantic signatures across later mining waves, and quarantines all 150 previously calibration-exposed pairs plus their connected components. Corrected frozen partition hash `83fd2a6b18329f2d4a87976288d03e5db83f919055af93737769aacf155e88dc` contains 167 calibration, 65 validation, and 67 final-heldout rows, with zero cross-partition study-unit or endpoint overlap, all six disciplines in every partition, and heldout support floors passing; final-heldout variant support is 4. The prior 150-pair V4.1 calibration result (accuracy `0.886667`, macro F1 `0.777316`) is retained only as invalidated exploratory evidence. Seventeen corrected-calibration pairs lack blinded semantic predictions, so no matcher is selected and validation, final heldout, normalized V1/V2 metrics, and Registry V3 remain not authorized.
- Independent Verifier integrity and all seven mutations remain PASS; top-level ledger/mutation hashes, exact mutation-key coverage, and all-seven-true status now fail closed. The six-package separate-session dry-run manifest hash remains `2e110dcba82182f872b53fa1b774650b737f938571fdcf01cd02ba72ac580740`, and this authoring session did not self-verify items. Focused historical controls pass **252/252**. The final canonical suite is **2,058 passed / 3 failed**: the one known coordinator-state failure plus two new frozen-starting-HEAD assertion failures caused by an external concurrent branch advance from required start `01eff40984bee76418c7fab82a1ded9fbfa2d9e5` to `b0cd30f36d307e2881d6b85d189dded8cde11518`; the guard was not weakened. AOM and lifecycle controls pass, but aggregate historical safety is FAIL because `NEW_TEST_FAILURES=2`. This session created no commit and changed no historical frozen artifact or `CLAUDE.md`. Canonical report hash `272af9a12bdbcdfcd1c92a9c1b5a4c60fbe400ddfe32f83ab1a3c813641d74ae`. Copyright PASS; `READY_FOR_NEXT_REGISTRY_STAGE=NO`; `NEXT_DOMINANT_BOTTLENECK=17_MISSING_BLINDED_CALIBRATION_PREDICTIONS_AND_EXTERNAL_HEAD_DRIFT`; `QGEN_NEXT_STEP=RESOLVE_BLOCKER` by classifying only those 17 missing calibration pairs after semantic-model quota returns, then scoring all 167 before any validation-label exposure.
- **Corrected Matcher V4.1/V4.2 calibration and validation milestone (2026-09-12): BLOCKED at the immutable validation gate.** Current HEAD `b0cd30f36d307e2881d6b85d189dded8cde11518` is the sole direct descendant commit of historical QGEN baseline `01eff40984bee76418c7fab82a1ded9fbfa2d9e5`. Content inspection classifies that misleadingly titled `Added ui` commit as 426 QGEN semantic artifacts, 64 QGEN deterministic-infrastructure files, 28 documentation files, 30 test files, one other source-research report, and zero UI-only files. All frozen hashes reproduce, including AOM `c250e20c3da4e109c06c856c573e0e0006ab959ffd26faeccd2c55ebf3237e9a`, Gold V2 `7bff03312c9023244054f8760d75f1e706c0d13526cd2a9f3e600d4ce4b49cc3`, Gold V3 `8ff4a8150f3213591dbbf0c8cc6fe55e79414cb914a7fbed9fe450bf61762c4a`, corrected partition `83fd2a6b18329f2d4a87976288d03e5db83f919055af93737769aacf155e88dc`, and Independent Verifier manifest `2e110dcba82182f872b53fa1b774650b737f938571fdcf01cd02ba72ac580740`. The narrow lineage repair preserves the historical starting-head field, records current HEAD separately, and requires explicit descendant ancestry; the two false head-pin failures are resolved without weakening artifact checks. Historical safety therefore returns PASS.
- The 17 missing corrected-calibration predictions were completed once under frozen V4.1, producing full 167/167 coverage. Corrected V4.1 semantic/hybrid accuracy is `0.898204`, macro F1 `0.782279`, with EQUIVALENT F1 `0.571429`, so it failed. The single permitted calibration-only refinement produced frozen Matcher V4.2, hybrid contract hash `5ddd6cad599d7716d06a91920de6b009fe005ea83b79b31263a8fbe561649942`. V4.2 calibration passed: accuracy `0.916168`, macro precision `0.883077`, macro recall `0.906044`, macro F1 `0.889833`; EQUIVALENT F1 `0.727273` and all supported critical classes cleared `0.70`. The selected hybrid matcher then ran once on all 65 blinded validation rows and failed: accuracy `0.907692`, macro precision `0.776563`, macro recall `0.789931`, macro F1 `0.761146`; EQUIVALENT F1 `0.571429` and VARIANT F1 `0.0` on support 2. Final heldout remained sealed and unrun; normalized V1/V2 evaluation and Registry V3 remain unauthorized. Monotonicity, AOM, lifecycle, Independent Verifier integrity/all seven mutations, and copyright pass (zero Toronto Notes overlap); focused controls pass **431/431** and the canonical suite is **2,061 passed / 1 failed**, solely the known source-research coordinator expectation, with zero external-lineage failures and zero actual new regressions. `MATCHER_ASSESSMENT=MATCHER_FAILED_VALIDATION`; `NEXT_DOMINANT_BOTTLENECK=EQUIVALENT_VS_VARIANT_VALIDATION_GENERALIZATION`; `QGEN_NEXT_STEP=REFINE_MATCHER` in a future independently frozen cycle without opening the 67-row final heldout.
- **Selective Matcher V5 fresh-validation failure + matcher-line closeout (2026-09-13): COMPLETE, ARCHITECTURE DECISION FROZEN.** Continuing unchanged HEAD `b0cd30f36d307e2881d6b85d189dded8cde11518`; no commit, reset, clean, stash, checkout, or historical frozen-artifact modification occurred this session, and this closeout ran no semantic subagents and generated no new relation labels. Matcher V5 is selective (`AUTO_ACCEPT` or `NEEDS_SEMANTIC_ADJUDICATION`), frozen contract `content_sha256=d32e983fbad4273a1f463529abf6559568a0d00f1b7d8a4602cace6fe91a7045` (`research/qgen/opportunity_relation_v5/matcher_v5_contract.json`), parented on frozen V4.2. Development evidence (232 pairs, `matcher_v5_development_cross_validation.json`, aggregate hash `0923a960c7d5a9d414074d9bae07be58ec18a42317881949d32d5a60b15409bc`): auto-resolved 108/232, coverage `0.465517`, auto-accuracy `0.981481`, auto-critical precision `1.0`, 0 catastrophic errors — development-only, not validation.
- A genuinely fresh, previously unseen 185-pair validation corpus was built and frozen **before** any V5 inference ran: Wave 1 (162 pairs, two blinded reviewers agreeing 128/162 ≈ 0.79, third reviewer adjudicating all 34 disagreements) plus Supplement 1 (8 pairs, 0 new EQUIVALENT) plus Supplement 2 (15 pairs, 1 new EQUIVALENT), reconciled in `fresh_v5_validation_gold.json`, `content_sha256=41d392b480749b622b9c0f6c7e1127d1f9f8e1516dd2d79936771d5a100342dc`, `frozen_before_matcher_v5_run=true`. Terminal relation counts (185 total): EQUIVALENT 8, REGISTRY_BROADER_CONTAINS_BENCHMARK 20, REGISTRY_NARROWER_THAN_BENCHMARK 11, VARIANT_OF_SAME_DECISION 11, RELATED_BUT_DISTINCT 70, NEAR_DUPLICATE 44, DUPLICATE 10, UNRELATED 11, UNCERTAIN 0. Two blinded inference streams (frozen V4.2 corroborator, structured V5 semantic classifier) ran once each on all 185 pairs, were merged, and the frozen selective policy was applied before fresh gold was ever opened; frozen selective predictions `content_sha256=902fe9d8613f26af676eb4a657a7a3973898679247deae2b7c57e8a775369152`.
- Reproduced `fresh_v5_validation_auto_metrics.json` (`source_gold_sha256` and `source_prediction_sha256` both verified against the frozen gold and frozen predictions above) exactly: pairs 185, auto_resolved 64, abstained 121, auto_coverage `0.345946`, auto_accuracy `0.890625`, auto_macro_f1 `0.592674`, auto_critical_precision `0.5`, catastrophic_errors 0. The predeclared fresh-validation safety floors (auto-critical precision ≥0.95, auto-resolved accuracy ≥0.95) were violated; development metrics did not generalize. `V5_AUTO_GATE=FAIL`; `FRESH_VALIDATION_GATE=FAIL`; `SELECTIVE_SYSTEM_ASSESSMENT=SELECTIVE_MATCHER_FAILED`.
- Adjudicating the 121 V5-abstained pairs was deliberately, intentionally not completed: those pairs are outside the already-computed and immutable AUTO metrics, so no adjudication result could repair the already-failed AUTO gate. `ABSTENTION_ADJUDICATION_COMPLETED=NO_INTENTIONALLY_STOPPED_AFTER_IRREVERSIBLE_AUTO_GATE_FAILURE`. Two partial abstention-adjudication batches exist on disk (`fresh_v5_validation_abstention_adjudication_batch_1_predictions.json`, `..._batch_2_predictions.json`; 40 labeled pairs each, same `adjudicator_id=FRESH_V5_ABSTENTION_ADJUDICATOR`, no on-disk marker distinguishing a disqualified/truncated spawn from its replacement); batches 3 and 4 (40 and 1 pairs) have inputs but no predictions. Neither batch's labels are consumed by any frozen artifact — `fresh_v5_validation_auto_metrics.json`'s prediction hash traces only to the pre-adjudication selective-predictions file. `DISQUALIFIED_ADJUDICATOR_OUTPUT_USED=NO`; both existing batches are marked `PARTIAL_NOT_USED` in `docs/qgen/RELATION_MATCHER_EXPERIMENT_CLOSEOUT.md`; no new adjudication label was generated this session.
- The 67-row `FINAL_HELDOUT` partition of corrected Gold V3 (`relation_gold_v3_frozen_partitions.json`, partition_counts `{CALIBRATION: 167, VALIDATION: 65, FINAL_HELDOUT: 67}`) remains unopened for V5: no V5 script, test, or artifact references it. `FINAL_HELDOUT_OPENED=NO`; `FINAL_HELDOUT_PRESERVED=YES`.
- Architecture decision frozen in `docs/qgen/RELATION_MATCHER_EXPERIMENT_CLOSEOUT.md`: do not build Matcher V6; the automatic-relation-matcher research line is closed after three generations (V3, V4-family, V5) each failing fresh/held-out validation. `FURTHER_MATCHER_R_AND_D_RECOMMENDED=NO`. Replacement production relation strategy: `DETERMINISTIC_CANDIDATE_PROPOSAL_PLUS_SEMANTIC_ADJUDICATION` — deterministic mining proposes candidates, exact-invariant duplicates resolve deterministically, all other relations affecting registry atomicity/dedup/coverage (at minimum EQUIVALENT, VARIANT_OF_SAME_DECISION, NEAR_DUPLICATE, REGISTRY_BROADER_CONTAINS_BENCHMARK, REGISTRY_NARROWER_THAN_BENCHMARK) are adjudicated semantically offline in bounded batches, UNCERTAIN fails closed. `BENCHMARK_ATOMICITY_STATUS=SUFFICIENT` (Atomic Opportunity Contract V1 and Registry V1/V2 enumeration remain frozen and unaffected by this closeout); `REGISTRY_V3_READY_TO_BUILD=YES` using this strategy; `MORE_MATCHER_RESEARCH_REQUIRED_BEFORE_QUESTIONS=NO`.
- Independent Item Verification V1 regression re-run clean (package schema, ledger integrity, all seven mutation detections, external verifier manifest): PASS. Focused tests this session: `test_opportunity_relation_v5.py` 9/9, `test_opportunity_relation_v4.py` 28/28, `test_independent_item_verification.py` 21/21, `test_curriculum_opportunity_registry_v2.py` 29/29 — **87 passed / 0 failed**. No executable production code was changed by this closeout (only this doc and this `MEMORY.md` section were written), so the canonical full suite was not rerun (`FULL_SUITE=NOT_RERUN_NO_EXECUTABLE_CHANGE`); the most recent valid canonical full-suite result remains **2,061 passed / 1 failed** (the known unrelated source-research coordinator expectation) from the prior V4.2 milestone. Copyright audit of the new closeout doc and the pre-existing new V4.2/V5 prompt docs: PASS, original methodology prose only, zero verbatim Toronto Notes overlap. No commit was created; `CLAUDE.md` is unchanged.
- Two major milestones remain before a first independently verified production-question pilot: (1) build Registry V3 with deterministic-proposal-plus-semantic-adjudication relation resolution, then (2) run a first independently verified production-question pilot (target ~20-50 questions from frozen Registry V3 opportunities, author session strictly separate from an independent verification session, Stage 1 blind solve frozen before Stage 2 claim/rationale/source/TN/current-Canadian-guidance audit). `NEXT_DOMINANT_BOTTLENECK=REGISTRY_V3_CONSTRUCTION_WITH_SEMANTIC_ADJUDICATION`; `QGEN_NEXT_STEP=BUILD_REGISTRY_V3_WITH_SEMANTIC_ADJUDICATION`.
- **Registry V3 is built and frozen for production use** (`docs/qgen/REGISTRY_V3_CANONICALIZATION.md`, code `scripts/qbank/registry_v3_canonicalization.py`, tests `tests/test_registry_v3_canonicalization.py`, artifacts `research/qgen/opportunity_registry_v3_canonical/`). It is the first registry built under the closeout architecture `DETERMINISTIC_CANDIDATE_PROPOSAL_PLUS_SEMANTIC_ADJUDICATION`; no automatic matcher has authority anywhere in it. Frozen input: Registry V2, file sha256 `64f2b854b680c7bdb2bb21306728076a8e814816d97d23eb6e43c1648547ed92`, content sha256 `d1625711d9efd7db50a47ab54dd90a83de56302108775ecbac31f38afcd309c8`, 2,001 rows, treated as immutable; V3 lives in a new directory and rewrites nothing. `REGISTRY_V3_SHA256=57a12e09be8322939814e1a1c41850cba7cb937e2868c827472ecd3407d54e38`, 1,964 canonical rows, `ACCEPTANCE_GATE=PASS` on all twelve checks, `DETERMINISTIC_REBUILD=PASS` (26/26 artifacts reproduce their content hash from frozen inputs plus frozen adjudication files; semantic reviews are frozen inputs and are never rerun).
- **Cost discipline held**: no all-pairs semantic comparison. Deterministic blocking proposed **21,770** candidate pairs of 2,001,000 possible (~1%), tiering routed only **427** to review, **99** were already answered by the frozen double-reviewed relation gold, and **328** primary adjudications were performed. Candidate-retrieval recall audit against the 167 frozen Registry-V2-to-V2 gold pairs (diagnostic only, no label tuning): every collapsing relation retrieved *and queued* 14/14, containment 15/15, known-UNRELATED correctly excluded 40/40, one non-destructive RELATED_BUT_DISTINCT miss. Exact-duplicate fast path found **0** pairs — Registry V2 is already exactly deduplicated on fingerprint, atomic signature and projected-record hash, so every collapse in V3 came from semantic adjudication, never fuzzy similarity.
- **Destructive-decision safety**: 52 destructive proposals went to a second independent HIGH reviewer; agreement was **28/52 (0.538)**; the 24 disagreements went to a third fresh adjudicator, which returned 8 BROADER, 7 NARROWER, 5 VARIANT, 2 RELATED_BUT_DISTINCT, 1 EQUIVALENT, 1 NEAR_DUPLICATE. `resolve_registry_relations` raises if any destructive relation ever binds on a single review. Bound registry relations: EQUIVALENT 29, VARIANT_OF_SAME_DECISION 5, NEAR_DUPLICATE 7, BROADER 62, NARROWER 68, RELATED_BUT_DISTINCT 157, UNCERTAIN 0. The append-only relation graph over V2 source ids holds 454 edges; monotonicity invariant PASS. Canonicalization: 2,001 V2 rows -> **1,964** canonical rows (33 collapsed by adjudicated equivalence, 4 demoted to variant descriptors); every V2 row traces to exactly one canonical row; canonical ids are `QOP-V3C-<sha256(sorted source ids)[:12]>`, content-derived and order-independent. Variants (4) are held in `registry_v3_variants.json` and count **zero** toward curriculum coverage.
- **The dominant structural finding, and the reason production eligibility is narrow**: Registry V2 inherited all 1,541 V1 rows in the generated wrapper form `Apply <phrase> reasoning for <study unit>.` A frozen deterministic atomicity screen splits the 2,001 rows into `CONCRETE_DECISION_STATEMENT` **458**, `NAMED_PHRASE_WRAPPER` **685**, and `GENERIC_CATEGORY_WRAPPER` **821** (phrase built entirely from curriculum-category vocabulary, so it names a heading and can never be a canonical decision). Lifecycle: `PRODUCTION_ELIGIBLE` **445**, `NEEDS_SEMANTIC_REVIEW` 1,510, `REFERENCE_ONLY` 9. Production-eligible rows span all six disciplines (MED 248, SURG 108, OBGYN 36, PED 29, PSY 14, PHELO 10).
- **Coverage, reported separately and never collapsed into one recall number** (`registry_v3_coverage_report.json`, sha256 `50d67cff45dfa6016fdf657eafa7989e412428b91aae87fe742ffa86e62480ca`): atomic-equivalent benchmark recall **0.0207**, atomic-equivalent precision 0.0256, curriculum-decision coverage (any granularity) **0.5586**, missing benchmark decisions **64**, registry-only decisions 1,847, atomization deficit **77**, variant capture 3, duplicate rate 0.0165, over-split rate 0.0, uncertain rate 0.0. Read this honestly: of 145 benchmark decisions, 81 are represented somewhere but only **3** at the same granularity, and **77** exist solely inside a broader registry heading. The registry's deficiency is not scope but granularity — the same fact the atomicity screen measures independently. Benchmark mapping is many-to-many by construction (95 benchmark rows match >1 registry row; 69 registry rows match >1 benchmark row), adjudicated over 264 fresh pairs plus 37 reused frozen judgments.
- **Missing-benchmark investigation**: all 64 unmapped benchmark decisions sit in study units the registry already contains, so none is a scope gap. Dispositions: candidate-retrieval miss 16, out-of-scope detail 15, granularity mismatch 14, true omission 12, cross-discipline mapping 5, benchmark artifact 2, uncertain 0. Of the 12 true omissions, **10** also satisfy the atomic contract and were admitted as `QOP-V3G-*` rows in `NEEDS_SOURCE_RESEARCH` (benchmark provenance, no Canadian source packet of their own yet). The 16 retrieval misses are a genuine limitation of study-unit-scoped blocking and are recorded, not hidden. Review queue: **1,583** rows (1,490 ambiguous atomicity, 64 unresolved benchmark gaps, 29 unresolved relations); a non-empty fail-closed queue does not fail the acceptance gate.
- **No fake capacity**: no questions-per-opportunity ratio is asserted anywhere. Curriculum decision count (1,964), variant count (4) and production-eligible count (445) are reported separately, and the historical 6,086 / 1,000-per-discipline allocation targets are not treated as a registry truth.
- **Production pilot manifest** (`registry_v3_pilot_manifest.json`, sha256 `5a20b814f636a7af8c33cf92980e1cf695975b0d8449808753f4f8626e187dc8`): **36** production-eligible opportunities chosen by deterministic stratified round-robin over (discipline, family), covering all 6 disciplines, 18 opportunity families, 10 response classes, 4 dimensions of care and 4 physician activities; ids and structural metadata only. **Zero questions were generated in this milestone.** Independent Verification V1 is unchanged and its regression is clean; every pilot item must flow author session -> frozen item package -> separate verification session -> Stage 1 blind solve -> freeze verdict -> Stage 2 rationale/claim/source/TN/current-Canadian-guidance audit -> VERIFIED_ACCEPT or REJECT.
- Focused tests this session: `test_registry_v3_canonicalization.py` 57/57, plus `test_independent_item_verification.py`, `test_curriculum_opportunity_registry_v2.py`, `test_curriculum_opportunity_registry_v3.py`, `test_opportunity_relation_v4.py`, `test_opportunity_relation_v5.py` 120/120 — **177 passed / 0 failed**. Canonical full suite rerun at final executable-code state: **2,127 passed / 1 failed**; the one failure is the known pre-existing `test_source_research_coordinator.py::test_discovery_classifies_dirty_worktree_retry_and_committed_branch_awaiting_integration`, which builds its own isolated `tmp_path` repository and is untouched by this milestone. `ACTUAL_NEW_REGRESSIONS=0`. Copyright audit PASS (original adjudicator prose only, Toronto Notes source-prose fields dropped from every V3 row, no substantial reproduction). `HISTORICAL_FROZEN_ARTIFACTS_MODIFIED=0`; no commit was created; `CLAUDE.md` unchanged.
- `NEXT_DOMINANT_BOTTLENECK=REGISTRY_GRANULARITY_MOST_ROWS_ARE_HEADINGS_NOT_DECISIONS` — 1,490 canonical rows remain category or named-phrase wrappers whose atomicity is unproven, and 77 benchmark decisions are covered only by a broader heading; decomposing those is what would raise atomic-equivalent recall above 0.02. That work is **not** a prerequisite for the pilot, which draws on the 445 already-atomic production-eligible rows. `QGEN_NEXT_STEP=FIRST_INDEPENDENTLY_VERIFIED_PRODUCTION_QUESTION_PILOT` from the frozen 36-opportunity manifest.
- **First production authoring pilot: AUTHORING HALF COMPLETE, `PILOT_AUTHORING_GATE=FAIL` (2026-09-13)**, from unchanged starting HEAD `b0cd30f`. Code `scripts/qbank/production_pilot_authoring.py`, tests `tests/test_production_pilot_authoring.py`, artifacts `research/qgen/production_pilot_v1/`, milestone `reports/qgen_first_production_authoring_pilot_milestone.json` (content sha256 `33ac0055637ab8c4d9b26e5274b35b4bb1ed6076b06dd636dc04336900ddf384`). Both frozen inputs reproduce their declared content hashes (`REGISTRY_V3_SHA256=57a12e09…`, `PILOT_MANIFEST_SHA256=5a20b814…`), all 36 manifest rows are still `PRODUCTION_ELIGIBLE` and `CONCRETE_DECISION_STATEMENT`, and the Independent Verification V1 regression is clean (6 non-production packages, empty ledger chain, 7/7 mutation detections). Independent Verification V1 was **not** redesigned: packages are built through its own `canonical_hash`, `VERIFIED_CONTENT_FIELDS` and `blind_projection`, and validate against the unchanged `schemas/production-item-verification-package-v1.schema.json`.
- **The gate failed on evidence supply, not on authoring capacity, and this is the finding that matters.** A frozen evidence index over five repository layers (READY source packets and their exceptions, readiness targeted-evidence claims, fresh-operational-holdout-18 decision evidence, cross-discipline and chapter evidence packets) resolves **373** clinical facts, yet only **12 of 36** manifest opportunities have evidence that entails their *specific atomic decision*. `research/qgen/production_pilot_v1/pilot_evidence_coverage_diagnostic.json` (sha256 `bcf88f8398b85384afd74e50096109553939e467c5e5066618fae28fcb924ff7`) records the per-opportunity verdict. The cause is structural: the pilot manifest was selected by stratified round-robin over discipline and family with **no evidence-coverage criterion**, against a corpus where only **90 of 1,524** source packets are READY. Unauthored by discipline: MED 11, SURG 6, PED 3, PHELO 2, OBGYN 1, PSY 1.
- **12 items authored, every one at `AUTHOR_COMPLETE_PENDING_INDEPENDENT_VERIFICATION`; 24 fail closed** (22 `NEEDS_SOURCE_RESEARCH`, 2 `INSUFFICIENT_EVIDENCE`), each with a named reason, one disposition per manifest opportunity and no opportunity left undisposed. Discipline counts MED 2, OBGYN 3, PED 2, PSY 3, SURG 1, PHELO 1; author-target difficulty EASY 4, MEDIUM 8, **HARD 0**, reported rather than quota-filled. Two fail-closed decisions are judgment calls a later wave may revisit: `QOP-V3C-7576CFC1A160` (ASA classification) was rejected because drafted option sets could not be separated from a defensible second key on the available evidence, and `QOP-V3C-3BAD5C5A9792` (SU-PH-10) accepts the repository's own prior independent audit of `ALIGNED_PARTIAL` / `PREREQUISITE_ONLY` rather than overriding it.
- **Two reused author-quality controls found real defects on their first run over authored content, and the items were repaired rather than the controls waived.** ADM-5 `find_realization_parity_defects`, imported unchanged from `option_set_admissibility`, flagged `SOLE_NUMERAL_BEARING_OPTION` in two OBGYN items; a new key/distractor length-asymmetry check (key longer than twice the longest distractor) flagged four items, which is the `KEY_DISTRACTOR_REGISTER_ASYMMETRY` mode that recurred throughout G2; and the copyright audit caught two 12-word verbatim runs against repository *claim* statements. All eight were repaired before freeze. The deterministic near-duplicate shingle screen flagged **0** item pairs.
- **Copyright PASS with a working detector.** Longest Toronto Notes word overlap over all 236 authored text segments is **0**, longest source-claim overlap **0**, and a positive control asserts the same detector returns **107** on real Toronto Notes prose, so the zero is a measurement rather than a silent failure.
- **Trust boundary held.** `ANY_ITEM_MARKED_VERIFIED_ACCEPT=NO`; no Stage-1 blind solve or Stage-2 audit was performed here; the validator rejects any authored row that sets `VERIFIED_ACCEPT`, and a test asserts `open_evidence_audit` raises `NONINDEPENDENT_VERIFIER_SESSION` when the author session id is offered as verifier. `WEB_EXPORT_AUTHORIZED=NO`. Handoff for the next session is `research/qgen/production_pilot_v1/pilot_independent_verification_handoff.json`, `VERIFICATION_MANIFEST_SHA256=91050b09177dda3b672379e45aac2c6824a29116443b51f6977dc0106d3cab9f`, 12 packages, with Stage-1 blind packets frozen separately in `pilot_stage_1_blind_packets.json` (`b8294e942ee18ea6a29409f4fc5f0d6c3dc1d449d684f2423757fcf7a1690096`) carrying stem, lead-in and options only.
- Registry V3 was sufficient *for this pilot* because the selected manifest rows are already-atomic production-eligible decisions; it remains **not** evidence of full-bank curriculum coverage (`REGISTRY_GRANULARITY_FULL_BANK_READY=NO`), and atomic-equivalent benchmark recall stays 0.0207. Registry granularity was deliberately not touched.
- Focused tests this session **202 passed / 0 failed** across seven modules (25 of them new in `test_production_pilot_authoring.py`, alongside the independent-verification, registry V2/V3 and relation V4/V5 modules). Canonical full suite at final executable-code state: **2,152 passed / 1 failed**, the one failure being the known unrelated `test_source_research_coordinator.py::test_discovery_classifies_dirty_worktree_retry_and_committed_branch_awaiting_integration`; `ACTUAL_NEW_REGRESSIONS=0`. No commit was created, no reset/clean/stash occurred, `HISTORICAL_FROZEN_ARTIFACTS_MODIFIED=0`, and `CLAUDE.md` is unchanged.
- `NEXT_DOMINANT_BOTTLENECK=INDEPENDENT_MEDICAL_VERIFICATION_OF_PILOT_ITEMS` for the 12 frozen packages, with `SOURCE_EVIDENCE_COVERAGE_OF_PRODUCTION_ELIGIBLE_OPPORTUNITIES` immediately behind it: passing a 20-item authoring gate needs a source-research wave targeted at production-eligible manifest rows, or a manifest reselected with an evidence-coverage criterion, not more authoring effort. `QGEN_NEXT_STEP=RUN_THE_12_FROZEN_PACKAGES_IN_A_DIFFERENT_FRESH_VERIFICATION_SESSION`.
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
