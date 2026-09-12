# Curriculum Opportunity Enumeration V2 Design

## Frozen diagnosis

Registry V1 is precise but not complete. On the frozen 72-unit benchmark it has strict recall 0.056296 and precision 1.0: 38 semantic matches, 415 partial matches, 222 missing, and no invalid benchmark decisions. Its one-row-per-competency strategy retains the broad competency but does not decompose the distinct decisions inside it. The independent audits also show suitability overclaim (15/120 weak or unsuitable), nine near-duplicate pairs, Dimension of Care accuracy 0.666667, Physician Activity accuracy 0.6, and family accuracy 0.266667. The frozen assessment is `MULTIPLE_ISSUES`.

## Goal and non-goals

V2 will preserve every independently supported V1 decision while adding only decisions explicitly grounded in canonical competency text. It will improve atomicity, family/blueprint classification, MCQ suitability, and semantic dedupe without using benchmark study-unit IDs or targeting a bank size.

V2 will not infer clinical recommendations, expand a unit merely because a family is absent, copy MCC objective boilerplate into a topic where it may not apply, or create population/stage variants that are not named by the competency. MCC objectives remain provenance and scope checks, not an automatic opportunity generator.

## Generalizable enumeration rules

1. Preserve each V1 row as a V2 candidate with `provenance_type = V1_PRESERVED`.
2. Parse each canonical `testable_competencies` value into top-level sentence and semicolon clauses.
3. Split a conjunction only when the right side begins with an independent decision verb such as diagnose, recognize, differentiate, select, interpret, initiate, treat, manage, monitor, screen, counsel, communicate, determine, arrange, refer, assess, calculate, or apply. This prevents noun-list splitting from manufacturing decisions.
4. Expand a parenthetical list only when an explicit governing decision verb applies to two through six short parallel clinical objects. Each child inherits the governing verb and remains traceable to the exact competency. Illustrative lists introduced by `e.g.`, `such as`, or `including` are retained as one decision unless the competency explicitly requires selection or interpretation among the members.
5. When one clause contains two different response-class verbs, create one decision per response class. Diagnosis, investigation, interpretation, stabilization, management, prevention, communication, and ethical/legal action are never combined into one opportunity.
6. Assign family and response class from the atomic clause using explicit semantic precedence: ethical/legal and communication; emergency/red flag; screening/prevention/follow-up/monitoring; investigation/interpretation; differential/diagnosis; management. `INITIAL_MANAGEMENT` requires initial/first-line/immediate initiation language; subsequent, referral, escalation, complication treatment, or abnormal-result action is `NEXT_MANAGEMENT_STEP`.
7. Add a V2 candidate only when its action and clinical object are both non-empty and occur in the canonical competency. The generated learner-decision wording may normalize grammar but may not add a drug, test, threshold, population, or recommendation.
8. Population and stage context are material only when explicit in the competency or inherited from the V1 unit context. Cosmetic demographics are ignored.

## Identity, dedupe, and provenance

V2 identity uses study unit, normalized response class, family, action, clinical object, stage, and material population. Generic synonyms are normalized only within the same response class: recognize/identify/diagnose, assess/evaluate, and manage/treat. Broad V1 rows may collapse into a more specific atomic child only when both share the same source competency and response class; all aliases and V1 IDs remain in provenance.

The nine V1 near-duplicate patterns motivate general rules, not pair IDs. Generic `Apply <label> reasoning for <unit>` rows with the same unit, response class, and stage collapse when their labels are synonym-only. Emergency recognition and emergency action remain distinct unless both rows express the same response class and no distinct action/object.

Every row records `provenance_type`, `source_competency_key`, `source_competency_text`, `source_v1_opportunity_ids`, and `enumeration_rule_ids`. Permitted provenance types are `V1_PRESERVED`, `V2_NEW_FAMILY`, `V2_STAGE_EXPANSION`, `V2_POPULATION_EXPANSION`, and `V2_OTHER`.

## Classification and suitability

Family drives the default MCC blueprint mapping, then explicit stage and psychosocial/preventive terms refine Dimension of Care. The mapping is data-driven and tested against the independent audit confusion classes.

MCQ suitability is no longer universally strong. A concrete, single action/object with a discriminable response is `MCQ_STRONG`. A valid but context-dependent communication, counselling, systems, or broad management decision is `MCQ_ACCEPTABLE`. Vague awareness, overview, principles, anatomy-only, terminology-only, or non-decision content is `MCQ_WEAK` or `NOT_SUITABLE_FOR_MC`. Weak and unsuitable rows remain visible with zero allocatable capacity.

## Evaluation gates

The full V2 registry is generated once, exact and semantic dedupe run, and the frozen benchmark is replayed without per-row tuning. At most one further revision may change a general rule. V2 may supersede V1 only if precision remains at least 1.0 on the benchmark and recall materially improves. A fresh blind audit must show trustworthy suitability, family, and blueprint labels, and the duplicate stress test must pass after collapses. If any production gate remains false, Queue V2 may be built but the real production pilot must not run.

## Testing

Red tests cover preserved V1 decisions; decomposition into diagnosis, investigation, initial management, follow-up, complication, communication/legal, and other explicit response classes; compound splitting; illustrative-list restraint; cosmetic collapse; specialist/vague exclusion; corrected suitability/blueprint mappings; and absence of benchmark-ID whitelists. Whole-registry tests cover stable hashes, provenance, dedupe accounting, capacity bounds, allocation conservation, coverage-first queueing, and fail-closed pilot gating.
