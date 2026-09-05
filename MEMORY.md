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
- Audited coordinator input commit: `1f9ef4633009595ba6b04bf303d7ddf5b3fb6c43`.
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
- QGEN_NEXT_STEP = `USER_REVIEW_RETRIEVAL_BENCHMARK`
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
