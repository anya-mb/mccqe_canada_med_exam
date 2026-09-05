# Clinical contrast relation model V2

Design checkpoint for the layer the option-failure diagnosis named and the
phase-9 vocabulary had no name for: the **contrast-relation model**.

- Status: DESIGN — approved for an isolated V2 pilot path only.
- Supersedes nothing. Replaces no production generator, no safety gate and no
  frozen artifact.
- Starting commit: `3ebdfb3`.
- Preceding decision: `OPTION_REALIZATION_DIAGNOSIS = COMPLETE`,
  `PRIMARY_BOTTLENECK = MULTIPLE_INDEPENDENT_BOTTLENECKS`
  (`reports/qgen_contrast_first_option_failure_diagnosis.json`, diagnosed at
  `889ecb8`).
- Preceding resume pin: `QGEN_NEXT_STEP =
  FIX_CONTRAST_RELATION_MODEL_SILENCE_AS_DEFEAT_FIRST`.

---

## 0. What this design is answering, and what it is not

The contrast-first pilot realized ten items and two were accepted. The
diagnosis assigned one earliest primary cause to each of the eight rejections:
`A_CONTRAST_SET_DEFECT` 3, `C_STEM_BLUEPRINT_DEFECT` 3,
`B_CONTRAST_MATRIX_DEFECT` 1, `H_OPTION_WORDING_REALIZATION_DEFECT` 1. Only the
last is an option-layer cause, and the decisive counterfactual — would every
reject-forcing defect disappear given a perfect option layer — answered **yes
once, no seven times**.

Those seven are not seven unrelated problems. Every one of them is a failure of
the same substrate: the frozen `plausibility_anchor_feature_ids` and
`condition_predicates` over which `build_contrast_matrix`, `solve_stem_blueprint`
and the production anchor floor all reason. That substrate has four measured
defects.

| # | defect | items | mechanism in the current code |
|---|---|---|---|
| 1 | silence scored as defeat | G2-PHELO-01, G2-PSY-03, and every template rationale clause | `_satisfied` counts an *unassigned* feature as unsatisfied, and forbidding a feature PRESENT never assigns it ABSENT, so `no_second_key` passes over competitors the stem never addressed |
| 2 | no competitor-versus-competitor test | G2-MED-03, G2-SURG-01, G2-PED-01 | `validate_contrast_set` evaluates each competitor against the key only; nothing compares a competitor with its peers |
| 3 | anchors are untyped | G2-SURG-01, G2-SURG-02 | `SF-GS76-FEMALE-REPRODUCTIVE-AGE` (a demographic) and `SF-GS76-IMAGING-AVAILABLE-NOW` (a system constraint) satisfy the plausibility floor exactly as an examination finding does |
| 4 | correctness conditions are conjunction-only | G2-PED-02 | `CLM-R2-PED-VIRAL-INDICATION` reads "infection control purposes, **or** high risk patients" and is carried as two predicates that `_satisfied` counts conjunctively |

This design fixes those four and nothing else. It does not touch retrieval,
embeddings, the graph, option realization, the 6,086 allocation, the frozen
pilot artifacts, or the production generator.

**Negative findings this design must not reopen.** `RETRIEVAL_NOT_MAIN_PROBLEM`
(BM25, graph and hybrid arms each reached the same 10/30). Local embedding
trigger not met. Contrast-first already removed stem-anchor failures (9 → 0).
Distractor option realization is already lossless (32/32 verbatim). None of
these is revisited.

---

## 1. Architecture position

```
TORONTO NOTES / MCC SCOPE
  -> CURRENT CONCEPT + EVIDENCE LAYERS          (unchanged)
  -> CLINICAL CONTRAST RELATION MODEL V2        (new, this design)
  -> CONTRAST SET
  -> CONTRAST MATRIX V2
  -> DIFFICULTY-AWARE STEM BLUEPRINT V2
  -> FROZEN STEM
  -> BLIND SOLVER                               (unchanged protocol)
  -> POST-STEM REVALIDATION V2
  -> OPTIONS                                    (unchanged contract)
  -> INDEPENDENT VERIFICATION                   (unchanged protocol)
```

V2 is a **layer, not a replacement**. The concept graph keeps its three jobs —
concept discovery, topic relationships, source provenance — and is not expanded.
Three graphs stay logically distinct and are not collapsed:

1. **Concept graph** — condition / symptom / sign / test / treatment / topic.
2. **Evidence graph** — claim → source → authority → page → currentness.
3. **Contrast graph** — concept A ↔ concept B *in a named learner-decision
   context*, with shared features, discriminators, correctness predicates,
   confusability and difficulty relevance. This is what V2 adds.

---

## 2. Reuse matrix

| existing component | decision | why |
|---|---|---|
| `research/qgen/contrast_first_pilot_opportunities.json` (18 frozen) | **REUSE AS IS** | the same ten opportunities must be replayed or the comparison is not a comparison |
| `research/qgen/contrast_first_pilot_stems.json` (10 frozen stems + feature maps) | **REUSE AS IS** | the counterfactual is defined as V2 evaluated against the *unaltered* V1 stems |
| `research/qgen/safe_yield/g2_stem_feature_vocabulary.json` | **REUSE AS IS** | frozen, and it is the only thing that stops a stem being reverse-engineered around a distractor |
| frozen seed packs + `.enrichment` + `.stem_anchors` | **EXTEND** | the seed's `conditions_under_which_competitor_would_be_correct` prose is re-read into a **predicate tree**; the seed itself is never rewritten |
| `contrast_first_pilot.admit_pre_stem` (P1–P6) | **REUSE AS IS** | key-versus-competitor admission is correct as far as it goes; V2 adds peer comparison beside it, not instead of it |
| `contrast_first_pilot.build_contrast_matrix` / `validate_contrast_matrix` | **DO NOT USE for V2** | its rows are conjunction-only and untyped by construction; a V2 matrix is built alongside and the V1 one is not edited (editing it would move a frozen content hash) |
| `contrast_first_pilot._satisfied` / `_fully_satisfies_any` | **DO NOT USE** | these are defect 1 and defect 4 in code form |
| `contrast_first_pilot.solve_stem_blueprint` | **EXTEND** (new V2 solver) | the floor/ceiling/key-support triple is right; the polarity assignment it produces must become a three-valued feature-state map, and the ceiling must run on Kleene logic |
| `contrast_first_pilot.evaluate_clinical_coherence` (CO-1..CO-6) | **REUSE AS IS** | stem-level coherence is orthogonal to relation semantics and passed on all ten items |
| `profile_contrast_retrieval.retrieve_profile_aware_contrasts` (ADM_1/ADM_3/SAF_1) | **REUSE AS IS** | the production gate. V2 must clear it unchanged, or V2 buys itself an exemption |
| `question_difficulty.evaluate_difficulty_checks` | **EXTEND** | reused unmodified; V2 adds a *structure* vector beside it (§9) rather than editing the frozen checks |
| `contrast_first_pilot.validate_option_realization` | **REUSE AS IS** | 32/32 lossless; the diagnosis refuted the hypothesis that it is the bottleneck |
| `clinical_graph`, `tn_index` (14,909 chunks, FTS5) | **REUSE AS IS**, targeted retrieval only | topic/concept/differential discovery and page context. No whole-book extraction, no embeddings |
| `reports/qgen_contrast_first_*` | **REUSE AS IS**, read-only | the V1 arm is archived, never regenerated after seeing V2 results |

---

## 3. Feature state model

A stem does not assign polarities. It asserts a partial map, and everything it
does not assert is **unknown**, not absent.

```
PRESENT | ABSENT | UNKNOWN | NOT_APPLICABLE
```

- `PRESENT` — the stem states the feature holds.
- `ABSENT` — the stem states the feature does **not** hold. Only an explicit
  statement produces this. Forbidding a feature from a stem never produces it.
- `UNKNOWN` — not stated, not measured, not established, not elicited. The
  **default** for every feature in the study-unit vocabulary that the stem's
  feature map does not name.
- `NOT_APPLICABLE` — the question does not arise for this patient or context.
  Must be asserted explicitly with evidence; never inferred.

A feature assertion carries:

```json
{
  "feature_id": "SF-PS12-PATIENT-PREFERS-PSYCHOTHERAPY",
  "state": "UNKNOWN",
  "explicitness": "NOT_STATED",
  "value": null, "units": null,
  "temporal_context": null, "severity_context": null,
  "evidence_refs": [], "source_span": null
}
```

`explicitness` ∈ `EXPLICIT | IMPLIED | NOT_STATED`. `IMPLIED` requires a stated
`source_span` and is treated as `EXPLICIT` by the logic; it exists so a reviewer
can see which negations the stem actually says out loud.

**The load-bearing rule.** `UNKNOWN` is never coerced to `ABSENT`, in any
direction, at any layer, including rationale text. `{"fever": "ABSENT",
"explicitness": "EXPLICIT"}` and `{"fever": "UNKNOWN"}` are different objects and
must produce different verdicts.

---

## 4. Feature role model

Roles are semantic, not numeric. No invented weights.

| contrast role | discriminative class |
|---|---|
| `BACKGROUND_CONTEXT` | `NON_DISCRIMINATING` |
| `RESOURCE_AVAILABILITY` | `NON_DISCRIMINATING` |
| `PRIOR_PROBABILITY_FEATURE` | `PRIOR_ONLY` |
| `SHARED_PRESENTATION_FEATURE` | `PRESENTATION` |
| `POSITIVE_SUPPORT` | `PRESENTATION` |
| `TIMING_FEATURE` | `PRESENTATION` |
| `SEVERITY_FEATURE` | `PRESENTATION` |
| `INVESTIGATION_FINDING` | `PRESENTATION` |
| `MANAGEMENT_ELIGIBILITY` | `PRESENTATION` |
| `NEGATIVE_SUPPORT` | `DISCRIMINATING` |
| `KEY_DISCRIMINATOR` | `DISCRIMINATING` |
| `EXCLUSIONARY_FEATURE` | `DISCRIMINATING` |
| `CONTRAINDICATION` | `DISCRIMINATING` |

**`ANCHOR_ROLE_FLOOR`.** A competitor is plausible only if at least one of its
supporting features is `PRESENT` **and** of class `PRESENTATION`. A background
fact, a resource-availability clause or a prior-probability feature is recorded
and may add plausibility, but **cannot be a competitor's sole anchor**. This is
defect 3 stated as a rule: "a woman of reproductive age" and "imaging is
available now" stop being anchors.

Default map from the frozen vocabulary's `clinical_role` to a V2 contrast role,
overridable per relation only with a cited claim:

| frozen `clinical_role` | default contrast role |
|---|---|
| `AGE`, `DEMOGRAPHIC` | `PRIOR_PROBABILITY_FEATURE` |
| `SYSTEM_CONSTRAINT`, `PROGRAMME_CAPACITY` | `RESOURCE_AVAILABILITY` |
| `CLINICAL_JUDGEMENT`, `PROGRAMME_DOCUMENT`, `PROGRAMME_OBJECTIVE` | `BACKGROUND_CONTEXT` |
| `SYMPTOM` | `SHARED_PRESENTATION_FEATURE` |
| `EXAMINATION_FINDING`, `HISTORY`, `COLLATERAL_SOURCE`, `EXPLICIT_RISK_INVENTORY` | `POSITIVE_SUPPORT` |
| `VITAL_SIGN` | `SEVERITY_FEATURE` |
| `INVESTIGATION_RESULT`, `STUDY_DESIGN`, `STUDY_RESULT` | `INVESTIGATION_FINDING` |
| `TIME_COURSE`, `LONGITUDINAL_COURSE` | `TIMING_FEATURE` |
| `PATIENT_PREFERENCE` | `MANAGEMENT_ELIGIBILITY` |

`CLINICAL_JUDGEMENT` defaults to `BACKGROUND_CONTEXT` deliberately: the
diagnosis found that `SF-GS76-INTERMEDIATE-CLINICAL-SUSPICION` is a
meta-assertion about the clinician's state rather than an observable finding,
and the reviewer refused it. A relation may override it to
`SEVERITY_FEATURE` where a cited claim makes the judgement the operative
clinical criterion.

---

## 5. Predicate logic

Correctness is a **condition tree**, never a flat list.

Operators: `ALL_OF`, `ANY_OF`, `NOT`, `AT_LEAST_N` (with `n`), `COMPARISON`,
`THRESHOLD`. Leaves resolve to typed feature-state assertions.

```json
{"operator": "ANY_OF", "conditions": [
  {"feature_id": "SF-P147-INFECTION-CONTROL-NEED", "required_state": "PRESENT"},
  {"feature_id": "SF-P147-HIGH-RISK-EARLY-COURSE", "required_state": "PRESENT"}
]}
```

must behave as logical OR. Nesting is supported: `A AND (B OR C)`, `NOT D`,
`AT_LEAST_N 2 of [A,B,C]`, `value >= threshold`. An empty `conditions` list
fails closed rather than defaulting to true or false.

`COMPARISON` / `THRESHOLD` leaves carry `comparison` (`lt|lte|gt|gte|eq|ne`),
`value` and optional `units`; they are used only where a clinical statement is
genuinely numeric.

---

## 6. Three-valued evaluation

Results are `SATISFIED | NOT_SATISFIED | INDETERMINATE`. Python truthiness is
not used anywhere in the evaluator.

Leaf resolution:

| asserted state | required `PRESENT` | required `ABSENT` |
|---|---|---|
| `PRESENT` | SATISFIED | NOT_SATISFIED |
| `ABSENT` | NOT_SATISFIED | SATISFIED |
| `UNKNOWN` | **INDETERMINATE** | **INDETERMINATE** |
| `NOT_APPLICABLE` | NOT_SATISFIED | SATISFIED |

Composition is Kleene:

- `ALL_OF` — any NOT_SATISFIED → NOT_SATISFIED; else any INDETERMINATE →
  INDETERMINATE; else SATISFIED.
- `ANY_OF` — any SATISFIED → SATISFIED; else any INDETERMINATE →
  INDETERMINATE; else NOT_SATISFIED.
- `NOT` — SATISFIED ↔ NOT_SATISFIED, INDETERMINATE unchanged.
- `AT_LEAST_N` — satisfied ≥ n → SATISFIED; satisfied + indeterminate < n →
  NOT_SATISFIED; otherwise INDETERMINATE.
- `COMPARISON` / `THRESHOLD` — INDETERMINATE unless a numeric value is asserted.

**A competitor whose correctness depends on `UNKNOWN` information is not
defeated.** That single sentence is the fix for defect 1 and for the
"That condition is not met here" rationale clause the reviewers found seven
times.

---

## 7. Clinical contrast relation object

One evidence-backed relation between two candidate concepts *in a named learner
decision*. Field names follow repository convention (snake_case, `*_id`,
`evidence_refs`), and the object is content-addressed like every other
contrast-first artifact.

```json
{
  "contrast_relation_id": "CCR2-<sha256[:24]>",
  "learner_decision_id": "LD-PS12-01",
  "response_class": "PLAUSIBLE_TREATMENT_OPTION",
  "decision_granularity": "SINGLE_TREATMENT",
  "concept_a": {"concept_id": "...", "concept": "...", "role_in_set": "KEY"},
  "concept_b": {"concept_id": "...", "concept": "...", "role_in_set": "COMPETITOR",
                "seed_id": "SEED-..."},
  "shared_features": [{"feature_id": "...", "contrast_role": "SHARED_PRESENTATION_FEATURE"}],
  "a_supporting_features": [...],
  "b_supporting_features": [...],
  "discriminators": [{"feature_id": "...", "favours": "A", "contrast_role": "KEY_DISCRIMINATOR",
                      "salience": "SALIENT|MODERATE|SUBTLE", "evidence_refs": ["CLM-..."]}],
  "correctness_conditions_a": {"operator": "ALL_OF", "conditions": [...]},
  "correctness_conditions_b": {"operator": "ANY_OF", "conditions": [...]},
  "second_key_conditions": [{"feature_id": "...", "required_state": "PRESENT"}],
  "categorical_exclusion_conditions": [{"operator": "...", "conditions": [...],
                                        "basis": "EXPLICIT_CONTRAINDICATION",
                                        "evidence_refs": ["CLM-..."]}],
  "nesting_relation": "NONE|B_NESTS_IN_A|A_NESTS_IN_B|SAME_CONCEPT|COMPLICATION_OF",
  "confusability": "HIGH|MODERATE|LOW",
  "mcc_relevance": "...",
  "evidence_refs": ["CLM-..."],
  "verification_status": "EVIDENCE_VERIFIED|EVIDENCE_PENDING|UNVERIFIED"
}
```

`shared_features` make **both** concepts plausible. `discriminators` change the
**preference** between them. The model may not treat every present feature as
discriminative: a feature appearing in `shared_features` may not also appear in
`discriminators` for the same relation, and a discriminator needs an
`evidence_refs` entry or the relation fails closed.

---

## 8. Contrast-set coherence

Every planned option set is evaluated over **all** pairs, key↔competitor *and*
competitor↔competitor. `CONTRAST_SET_COHERENCE_GATE` rules:

| rule | refuses |
|---|---|
| `CS2-1 NESTED_OR_DUPLICATE_CONCEPT` | any pair with `nesting_relation != NONE` — a complication of another option, a subtype of another option, the same concept rephrased (G2-SURG-01 PID/TOA) |
| `CS2-2 MUTUAL_REDUNDANCY` | two competitors whose defeating-discriminator sets are identical, so one option slot does no independent work (G2-MED-03 furosemide/nitroglycerin) |
| `CS2-3 RESPONSE_CLASS_MISMATCH` | a competitor outside the demanded response class |
| `CS2-4 GRANULARITY_MISMATCH` | a competitor at a different decision granularity or a different stage of management |
| `CS2-5 CATEGORY_IMBALANCE` | one broad category beside three narrow subtypes, or a key alone in its category |
| `CS2-6 ANCHOR_EQUALS_CONDITION` | a competitor whose only `PRESENTATION`-class anchor is also a leaf of its own correctness condition — it can be live only by being a second key (G2-PED-01; the frozen library's `SEED-PED-T02-CBC`, `G2-OBGYN-02`, `G2-OBGYN-03`, `G2-SURG-03`, `G2-PSY-01`) |
| `CS2-7 SET_ANCHOR_DEGENERACY` | every competitor anchored on the same single feature, or no competitor clearing `ANCHOR_ROLE_FLOOR` (G2-SURG-01, G2-SURG-02) |
| `CS2-8 SHARED_SOLE_CORRECTNESS_CONDITION` | two competitors whose correctness predicates reduce to the same leaf set — not independently discriminable |

A set that violates any rule fails closed. It is not repaired by adding a stem
finding.

---

## 9. Difficulty

Difficulty is **not** "number of absent features", and it is not bought with
open silence. `REQUIRED_FEATURE_CAP` and `MAXIMUM_ABSENT_REQUIRED_FEATURES` are
reused unchanged; V2 adds a structure vector measured off the relation set:

`DISCRIMINATOR_SALIENCE`, `FEATURE_INTEGRATION_COUNT`, `COMPETITOR_SIMILARITY`,
`TEMPORAL_REASONING`, `SEVERITY_REASONING`, `SEQUENCING_REASONING`,
`DATA_INTERPRETATION`, `CONTEXTUAL_COMPLEXITY`.

- **EASY** — a real MCC decision, live distractors, one relatively `SALIENT`
  discriminator, low integration burden. Never made easy by silence, absurd
  distractors, category mismatch or definitional recall.
- **MEDIUM** — several live alternatives, multiple meaningful findings,
  moderate discrimination burden.
- **HARD** — strongly plausible alternatives, `MODERATE`/`SUBTLE` but legitimate
  discriminators, multi-feature integration. Never made hard by ambiguity,
  obscure trivia, missing information or specialist detail.

The diagnosis found `EASY_FEATURE_BUDGET_MAXIMISES_OPEN_SILENCE`: the tightest
feature cap left the most competitor conditions unaddressed. Under V2 that
tension is *visible* rather than silent — an unaddressed condition now produces
`AMBIGUOUS` instead of a passed ceiling — so an EASY item that cannot close its
competitors' domains fails closed rather than shipping.

---

## 10. Competitor states after a stem

`classify_competitor` returns exactly one of:

| state | condition | may be an option? |
|---|---|---|
| `SECOND_KEY` | correctness `SATISFIED` under the frozen stem | no — reject |
| `CATEGORICALLY_EXCLUDED` | an exclusion predicate `SATISFIED` on explicit evidence | no |
| `INSUFFICIENT_SUPPORT` | no `PRESENT` anchor of class `PRESENTATION` | no |
| `AMBIGUOUS` | correctness `INDETERMINATE` and no `SATISFIED` evidence-backed discriminator favours the key | no — **fail closed** |
| `LIVE_BUT_INFERIOR` | plausible, not excluded, and either correctness `NOT_SATISFIED` or `INDETERMINATE` **with** a satisfied evidence-backed discriminator favouring the key | yes |

**`LIVE_BUT_INFERIOR` may never be reached by silence alone.** If the only thing
standing between a competitor and the key is a feature the stem never mentions,
the state is `AMBIGUOUS`.

**Second-key ceiling.** `SATISFIED` rejects the competitor, as today.
`INDETERMINATE` neither accepts nor rejects automatically: the missing
information is examined, and if the ambiguity cannot be resolved without
altering the frozen stem the item fails closed.

**Categorical exclusion** requires explicit evidence — a stated
contraindication, a mutually exclusive clinical state, an explicitly `ABSENT`
mandatory feature, incompatible timing, an objective test result, or the wrong
stage of management. It is **never** inferred from silence.

---

## 11. Evidence

Every load-bearing relation is grounded in `FOUNDATIONAL_EVIDENCE`, a current
guidance packet, a validated graph/source relationship, or targeted authoritative
research. Toronto Notes supports topic organization, differential discovery and
stable foundational relationships; current recommendations still come from
current authoritative sources. Model memory is never the only evidence, and
model agreement is not evidence.

Toronto Notes usage is **targeted chunk retrieval against the existing 14,909-chunk
FTS5 index only**. No full-book LLM extraction. No embeddings. No broad
population of the contrast graph: the initial scope is the ten frozen
final-review opportunities and exactly the candidate concepts their planned sets
need.

---

## 12. Fail-closed rules

1. An empty predicate `conditions` list.
2. A discriminator without `evidence_refs`.
3. A feature id outside the frozen study-unit vocabulary.
4. A competitor classifying `AMBIGUOUS`.
5. A contrast set violating any `CS2-*` rule.
6. A relation whose `verification_status` is not `EVIDENCE_VERIFIED` used as
   load-bearing.
7. Unresolved single-best-answer ambiguity after post-stem revalidation.
8. Any attempt to coerce `UNKNOWN` to `ABSENT`.

---

## 13. Integration with the existing pipeline

V2 objects are **derivative and additive**. V1 artifacts are read and never
written. The V2 path writes only new files (§15). The production gate
`retrieve_profile_aware_contrasts` is still run, unchanged, on the V2 stems: V2
must clear the same bar, and its own classification is applied *in addition*,
never instead.

---

## 14. Precommitted gates

Frozen here, before any V2 result is computed. Not to be weakened afterwards.

### 14.1 `COUNTERFACTUAL_GATE` (phase 21)

V2 is mechanically promising only if **all** hold:

1. every known OR/AND logic defect is corrected (`G2-PED-02`'s disjunctive
   indications evaluate as disjunctions);
2. silence-as-absence defects are eliminated — no competitor is scored defeated
   by a feature the frozen stem leaves `UNKNOWN`;
3. no accepted V1 control (`G2-PHELO-02`, `G2-PHELO-03`) becomes unsafe under
   V2;
4. the second-key ceiling remains effective — a competitor whose correctness is
   `SATISFIED` under the frozen stem is still rejected;
5. competitor-set coherence identifies the previously diagnosed set defects
   (`G2-MED-03`, `G2-SURG-01`, `G2-PED-01`);
6. **at least 5 of the 7** non-option-layer rejected items are intercepted
   before final review or correctly reclassified.

### 14.2 Accepted-item safety (phase 29)

Every V2 item that is ACCEPTED must score **0** on all of:
`FACTUAL_ERRORS`, `NUMERIC_ERRORS`, `UNSUPPORTED_CLAIMS`,
`AMBIGUOUS_BEST_ANSWERS`, `CRITICAL_FACT_SAFETY_FAILURES`,
`MATERIAL_REDUNDANCY`, `COMPETITOR_WITHOUT_STEM_ANCHOR`, `SECOND_KEY_RISK`,
`UNNATURAL_STEM_ENGINEERING`, `BOOLEAN_LOGIC_DEFECT`,
`SILENCE_AS_ABSENCE_DEFECT`.

### 14.3 Medium-36 trigger (phase 33)

The medium pilot runs only if the counterfactual gate passes **and** the frozen-10
V2 replay shows accepted-item safety perfect **and** material improvement over
V1's 2/10.

### 14.4 Medium-36 success (phase 38)

No question quota. Ready for scalable population only if: accepted-item safety
stays perfect; at least two disciplines produce safe items at each feasible
difficulty level; no systematic silence/Boolean/feature-role defect reappears;
no single architecture defect explains ≥20% of attempted opportunities;
independent acceptance materially exceeds 2/10; and fail-closed remains common
where evidence or contrast support is insufficient.

---

## 15. Artifacts

| path | content |
|---|---|
| `schemas/clinical-contrast-relation-v2.schema.json` | the relation schema |
| `scripts/qbank/clinical_contrast_v2.py` | feature states, predicate engine, roles, relations, coherence gate, classifier |
| `scripts/qbank/contrast_first_v2_pilot.py` | frozen-10 population, counterfactual replay, V2 replay, reports |
| `tests/test_clinical_contrast_v2.py` | the TDD suite of §16 |
| `research/qgen/clinical_contrast_relations_v2.json` | the populated relation cache |
| `research/qgen/pilot/contrast-first-v2-frozen-10-relations.json` | per-opportunity V2 sets |
| `research/qgen/pilot/contrast-first-v2-frozen-10-blueprints.json` | V2 blueprints |
| `research/qgen/pilot/contrast-first-v2-frozen-10-generated.json` | V2 stems, options, rationales |
| `reports/qgen_clinical_contrast_v2_counterfactual.json` | phase 20/21 |
| `reports/qgen_clinical_contrast_v2_pilot_verification.json` | phase 28/29 |
| `reports/qgen_clinical_contrast_v1_vs_v2.json` | phase 30/31 |

Frozen V1 artifacts are never overwritten. `FROZEN_QGEN_ARTIFACTS_CHANGED` must
stay 0.

---

## 16. Required tests

`UNKNOWN != ABSENT`; explicit `ABSENT`; explicit `PRESENT`; `ANY_OF` is OR;
`ALL_OF` is AND; nested predicates; `NOT`; threshold comparison; `AT_LEAST_N`;
`UNKNOWN` propagates to `INDETERMINATE`; background context does not act as a
key discriminator; strong discriminator typing preserved; pairwise competitor
coherence; nested-diagnosis detection; response-class mismatch; granularity
mismatch; second-key ceiling; ambiguity fails closed; the two accepted V1
controls are preserved; each of the four diagnosed failure patterns is caught as
a regression fixture.

---

## 17. Boundaries

- No production generator replacement. No broad bank generation.
- No embeddings. No full-book Toronto Notes extraction. No graph expansion.
- `LLM_API_CALLS = 0`.
- No substantial Toronto Notes text in tracked artifacts: normalized
  propositions, minimal feature statements, page/chunk references and claim ids
  only.
- Token-cost optimization (`CONTRAST_MATRIX_ROW_PAYLOAD`) is measured after
  semantic correctness, never before.
