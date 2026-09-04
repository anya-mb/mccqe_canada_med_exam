# Discipline-profile question generation and global critical-fact safety — design

- Status: DESIGN ONLY. No production code, no question generation, no change to the frozen R4 experiment.
- Amended 2026-09-03 by **Part II — coverage-first safe-yield amendment** (§§14-28). Part II retires the
  fixed 6,086-question production target, preserves the 6,086 allocation as a historical curriculum-density
  plan, and restates the scale gates on quality, safety, coverage, yield and redundancy rather than on
  quota fill. Part II **supersedes §9**. Parts I and II are otherwise cumulative: every conclusion in
  §§0-13 stands unless Part II says otherwise, and Part II found no contradiction with any of them.
- Starting commit: `4a0117e` (audited R4 implementation checkpoint `9d6bb57`).
- Evidence base: `reports/qgen_cross_discipline_generalization_15_r4_independent_verification.json`,
  `reports/qgen_cross_discipline_generalization_15_r4_execution.json`,
  `reports/qgen_reviewer_calibration_v2.json`,
  `research/qgen/generalization/cross_discipline_generalization_15_r4.{staged,contrasts,evidence}.json`,
  `research/qgen/generalization/competitive_contrast_seed_pack_r4.json`,
  `scripts/qbank/chapter_staged_generation.py` (schema 1.4, `STAGE_SEQUENCE_V5`).
- Supersedes nothing. Extends `2026-08-31-chapter-anchored-global-contrast-qbank-design.md`.

---

## 0. Executive finding

The R4 retest is usually summarised as "curated contrast seeds did not generalise". Re-reading the
frozen artifacts gives a sharper and less comfortable result.

**Finding 1 — the semantic acceptance layer emitted no information in R4.** Across 15 items, 45
competitors and 8 gate families, every semantic verdict in the staged artifact is `PASS`:

| Gate | Verdicts recorded | Distinct values |
| --- | --- | --- |
| `CONTEXTUAL_COMPETITOR_PROOF` `post_stem_status` | 45 | 1 (`STRONG_COMPETITOR`) |
| `CONTEXTUAL_COMPETITOR_PROOF` hidden-key adversary | 45 | 1 (`PASS`) |
| `TERMINAL_EXCLUSION_REVIEW` | 15 | 1 (`PASS`) |
| `SEMANTIC_POLARITY_COMPLETENESS_PREFLIGHT` | 15 | 1 (`PASS`) |
| `OPTION_SEMANTIC_CATEGORY_PARITY` | 15 | 1 (`PASS`), 0 parity exceptions |
| `PRE_ASSEMBLY_SEMANTIC_SET_REVIEW` (8 checks) | 120 | 1 (`PASS`) |
| `PARALLEL_OPTION_SET_REVIEW` | 15 | 1 (`PASS`) |
| `DECISION_GRANULARITY_PARITY` | 15 | 1 (`PASS`) |

An independent reviewer then failed 8 of the same 15 items, 8 of them on option-set construction.
A gate whose output is constant across the outcome it is meant to predict has zero discriminating
power. Seven of the twenty-five stages in `STAGE_SEQUENCE_V5` did no work.

**Finding 2 — the cause is self-certification over generator-authored free text, not a missing rule.**
`find_option_category_parity_defects` is a value-equality test over five fields the generator
writes itself. Four are closed enums that are too coarse to express the axes on which R4 failed;
the fifth, `option_scope`, is validated only as a non-empty string. In all 15 items the generator
wrote one identical `option_scope` for all four options, so parity passed vacuously. `QGEN-GEN4-PSY-I02`
is the clean example: three community actions and one inpatient admission were each labelled
`option_semantic_type: DISPOSITION`, `option_scope: DISPOSITION_OF_AN_ACUTELY_SUICIDAL_PATIENT`.
The gate compared the labels, not the options.

This is the same defect the r3 numeric audit already named once — *"recomputation is vacuous when
the components themselves are ungrounded"*. It has now recurred in a second gate family. It is a
class of defect, not an incident.

**Finding 3 — the datum that would have rejected the failures was already in a frozen artifact and
was never joined.** Every seed in `competitive_contrast_seed_pack_r4.json` carries
`conditions_under_which_competitor_would_be_correct`. Every defective distractor's condition is
contradicted by the realized stem:

| Item | Competitor | Frozen correctness condition | Realized stem |
| --- | --- | --- | --- |
| OBGYN-I01 | Galactocele | "without erythema or systemic symptoms" | 38.4 °C, tachycardia, spreading erythema |
| OBGYN-I02 | Milk culture | "no symptomatic improvement after 48 hours" | systemic symptoms improved |
| SURG-I03 | Antibiotics alone | "selected adults with *uncomplicated* appendicitis" | free perforation, generalised peritonitis |
| PSY-I02 | Risk rating scale | "never as the determinant of disposition" | option text: "…*to set the disposition*" |
| PSY-I02 | Antidepressant + 48 h | "once safety is secured" | safety not secured |
| PHELO-I02 | Officer-of-health endorsement | "where *uptake, not autonomy*, is the objective" | lead-in asks about autonomy |

The pipeline held the refutation and asked a model to write prose arguing the opposite. It wrote 45
such arguments.

**Finding 4 — seed strength does not predict realized failure.** `MEMORY.md` records that the
surviving severity-mismatched distractors were "in each case a seed the reviewer had approved as
ACCEPTABLE rather than STRONG". The artifact does not support this. Of the six defective
distractors, five were independently reviewed `STRONG`; only `SEED-OB-T01-GALACTOCELE` was
`ACCEPTABLE`. **Correction to `MEMORY.md`.** Restricting future retrieval to STRONG seeds would
have prevented one of eight failures. The defect is created at assembly against a realized stem,
which is exactly where no seed reviewer can see it.

**Finding 5 — discipline clustering in R4 is not statistically supported.** Conditioning on 7
passes among 15 items in 5 disciplines of 3, an exact permutation test gives **p = 0.31** for a
spread at least as extreme as the observed 3/3 … 0/3. Separately,
`qgen_reviewer_calibration_v2.json` records that `KEY_AS_CATEGORY_ODD_ONE_OUT` and
`EXCLUSION_BY_EXPLICIT_STEM_NEGATION` "predate schema 1.3 [and] are present in the Cardiology pilot
and in the accepted baseline items", where the previously accepted Cardiology cohort scored 0/4
under the calibrated rubric. **The two dominant R4 failure modes are universal and long-standing,
not discipline-specific.** Any recommendation that rests on discipline clustering rests on nothing.

**Finding 6 — but two failures are irreducibly source-level, and both were transcribed faithfully.**
`CLM-R4-SURG-PRESENTATION` states McBurney's point at "1.5 to 2 cm from the anterior superior iliac
spine"; the accepted figure is 1.5 to 2 inches. `CLM-R4-PSY-EXERCISE` states exercise as first-line
monotherapy "for mild depression and a second-line adjunctive treatment for moderate severity
illness", a band the independent reviewer holds to be mild-to-moderate and moderate-to-severe. Both
claims carry `verification_status: VERIFIED_COMPLETE`. **Correction to `MEMORY.md`:** the PSY-I03
`UNSUPPORTED_CLAIM` is not a rationale-writing defect. The rebuttal quoted the packet accurately;
the packet claim is the disputed statement. Both defects are therefore the same root cause.
`VERIFIED_COMPLETE` today asserts fidelity of transcription and is being read as truth.

**Finding 7 — the numeric gate never saw the number.** `QGEN-GEN4-SURG-I01`'s
`numeric_derivation_validation` records `no_derived_values_present: true`, `derivations: []`,
verdict `PASS`, while the stem asserts "2 cm from the right anterior superior iliac spine". The gate
covers *derived* values only. `NUMERIC_ASSERTION_SITES` exists in the vocabulary but is only
populated for derivations. **An asserted or quoted numeric fact currently carries no obligation of
any kind.**

### What this means for the requested architecture

The hypothesis put to this design was that discipline-specific generation profiles are the next
thing to test. The evidence supports that conclusion but **not for the reason offered**. Profiles
are not justified by disciplines failing at different rates — they do not, at this n. They are
justified because the axis on which an option set must be comparable is **archetype- and
discipline-shaped**, is not expressible in the current universal vocabulary, and must be supplied
from outside the generator so that the comparison stops being self-certifying. Two of fifteen R4
items (`PHELO-I01`, `PHELO-I02`) already fall out of the universal vocabulary entirely, carrying
`decision_granularity: OTHER`.

Recommended architecture is therefore **COMMON_CORE_PLUS_DISCIPLINE_PROFILES**, with the profile's
job narrowly defined as *supplying closed, externally-authored comparison vocabularies and evidence
escalation policy* — never as separate generation logic. The primary repair is common-core and is
about **independence and falsifiability**, not about adding gates. The proposal **deletes seven
stages and adds three**, for a net stage count of 21 against the current 25.

---

## 1. Phase 1 — R4 failure matrix

Each failure is assigned to its earliest causal layer. Downstream symptoms are recorded but not
counted. Two items carry two independent causal chains and are listed twice with that stated.

| # | Item | Reviewer defects | Earliest causal layer | Downstream symptoms (not counted) |
| --- | --- | --- | --- | --- |
| 1 | OBGYN-I01 | WEAK_DISTRACTOR | `OPTION_SET_ARCHETYPE` — galactocele cannot produce the stem's cardinal systemic inflammatory syndrome; its own frozen condition says so | severity-tier appearance |
| 2 | OBGYN-I02 | WEAK_DISTRACTOR | `OPTION_SET_ARCHETYPE` — a microbiological test offered where the lead-in demands structural characterisation | "discardable from the lead-in alone" |
| 3 | OBGYN-I03 | OPTION_CUE_FAILURE | `STEM_CONSTRUCTION` — all three wrong practices named in the stem as things the patient already does | lone-key-by-exclusion cue |
| 4 | SURG-I01 (a) | NUMERIC_ERROR, FACTUAL_ERROR | `SOURCE_UNIT_ERROR` — `CLM-R4-SURG-PRESENTATION` states cm for inches, transcribed faithfully, never re-derived | evidence_support FAIL |
| 5 | SURG-I01 (b) | OPTION_CUE_FAILURE | `WRONG_OPTION_CATEGORY` — key is the sole non-gynecologic diagnosis; no axis in the vocabulary expresses organ system | option_category_parity FAIL |
| 6 | SURG-I03 | WEAK_DISTRACTOR | `OPTION_SET_ARCHETYPE` — antibiotics alone provides no source control, the action class the scenario demands | "two severity tiers below" |
| 7 | PSY-I02 (a) | WEAK_DISTRACTOR ×2, OPTION_CUE_FAILURE | `OPTION_SET_ARCHETYPE` — risk scale and 48-hour antidepressant review do not secure immediate safety | lone-key inpatient category |
| 8 | PSY-I02 (b) | DECISION_GRANULARITY_FAILURE | `WRONG_SEVERITY_LEVEL` (scenario) — stem pitched beyond the discrimination band; every feature points one way | reasoning_demand FAIL |
| 9 | PSY-I03 | UNSUPPORTED_CLAIM | `SOURCE_FACT_ERROR` — `CLM-R4-PSY-EXERCISE` states a severity band the reviewer holds to be wrong; rebuttal quoted it faithfully | evidence_support FAIL |
| 10 | PHELO-I02 | OPTION_CUE_FAILURE, WEAK_DISTRACTOR | `OPTION_SET_ARCHETYPE` — three uptake levers against one autonomy-protecting revision; lead-in names autonomy | lone-key category, key-only two-figure format |

Controls examined and passing: PED-I01/I02/I03 (3/3), SURG-I02, PSY-I01, PHELO-I01, PHELO-I03.
Historical control: Cardiology `QGEN-MED-007-ACS-CR10-*`, 0/4 under the calibrated rubric, carrying
the same two modes.

### Root-cause tally (earliest layer only)

| Class | Count | Items |
| --- | --- | --- |
| `OPTION_SET_ARCHETYPE` | 5 | OBGYN-I01, OBGYN-I02, SURG-I03, PSY-I02(a), PHELO-I02 |
| `SOURCE_FACT_ERROR` / `SOURCE_UNIT_ERROR` | 2 | SURG-I01(a), PSY-I03 |
| `WRONG_OPTION_CATEGORY` | 1 | SURG-I01(b) |
| `STEM_CONSTRUCTION` | 1 | OBGYN-I03 |
| `WRONG_SEVERITY_LEVEL` (scenario) | 1 | PSY-I02(b) |

Classes that R4 evidence does **not** support: `CONTRAST_SEED_BAD` (0 — five of six defective
distractors were independently reviewed STRONG), `UNSUPPORTED_SCENARIO_INFERENCE` (0 — the one
candidate resolves to a source defect), `POLARITY_MISMATCH` (0),
`DISCIPLINE_SPECIFIC_REASONING_PATTERN` (0 as an *earliest* layer; it appears only as the reason the
missing axes differ).

### The rule the data actually forces

One rule accounts for all five `OPTION_SET_ARCHETYPE` failures **and correctly acquits every
competitor the independent reviewer accepted** — 45 competitors, zero false positives:

> **Every option must belong to the response class the realized stem and lead-in demand.**

| Item | Demanded response class | Accepted options | Rejected option |
| --- | --- | --- | --- |
| OBGYN-I01 | entity capable of the stem's systemic inflammatory syndrome | ductal narrowing, abscess | galactocele (non-inflammatory) |
| OBGYN-I02 | structural characterisation of a mass | mammography, aspiration | milk culture (microbiologic) |
| SURG-I03 | provides source control | drainage, interval appendectomy | antibiotics alone (none) |
| PSY-I02 | secures immediate safety | safety plan + means removal | risk scale, antidepressant |
| PHELO-I02 | supplies decision-relevant information | detection count | endorsement, reminder |

Note the discriminations this rule gets *right* that a naive severity-distance rule gets wrong:
percutaneous drainage sits two rungs from urgent appendectomy but was accepted, and a safety plan
sits well below admission but was accepted, because both deliver the demanded class. Distance on an
ordinal ladder is the wrong primitive; **membership of the demanded response class is the right
one.**

---

## 2. Phase 2 — testing the discipline-profile hypothesis

Candidate explanations for the cross-discipline failures:

| Explanation | Verdict | Evidence |
| --- | --- | --- |
| **A.** another missing universal rule | **Partly true — 2 of 10 chains.** OBGYN-I03 stem-enactment and the source-sanity checks are genuinely universal | reviewer failure mode 4; findings 6–7 |
| **B.** different natural question structures between disciplines | **True as a vocabulary claim, false as a rate claim.** PHELO twice falls to `decision_granularity: OTHER`; PSY and PHELO have no ordinal intensity axis in the universal enum. But pass-rate clustering is p = 0.31 and the same modes appear in MED/Cardiology | Finding 5; `OPTION_SEMANTIC_TYPES` coarseness |
| **C.** evidence acquisition differences | **True and material.** PED passed 3/3 on a source rich in explicit conditionals whose competitor conditions the stem does *not* negate; the two source-level defects are a surgical anatomical figure and a psychiatric guideline severity band | execution report `what_the_seeds_changed`; findings 6–7 |
| **D.** a mixture | **Accepted, with the decomposition above** | — |

**Answer: D, decomposed as 5 × option-set architecture (universal mechanism, discipline-shaped
vocabulary), 2 × source fact safety (universal), 2 × universal item-writing rules, 1 × scenario
calibration (discipline-shaped).**

The decisive negative result is that **no failure is explained by a discipline needing different
generation logic.** Every failure is explained by a comparison the generator could not make because
the vocabulary lacked the axis, or by a fact nobody checked. That bounds what a profile may contain.

### Per-discipline structural comparison

`MED` was **not exercised in R4**; its row is derived from the Cardiology pilot and the calibration
cohort and is explicitly marked untested at this checkpoint.

| | MEDICINE | PEDIATRICS | OBGYN | SURGERY | PSYCHIATRY | PHELO |
| --- | --- | --- | --- | --- | --- | --- |
| Most natural learner decisions | diagnosis, investigation selection, drug/dose choice, risk stratification | age-banded diagnosis, red-flag recognition, supportive-care ceiling, dosing by weight | pregnancy-dated diagnosis, maternal-vs-fetal action, screening/timing | recognition, stabilisation, imaging selection, operative-vs-nonoperative, disposition | diagnosis, safety assessment, longitudinal differential, pharmacotherapy, communication/capacity | epidemiologic interpretation, ethical action, legal duty, screening decision, population intervention |
| Vignette/context structure | single encounter + labs | age + weight + growth/immunisation + caregiver | gestational age + parity + fetal status | time-course + vitals + imaging + physiologic stability | longitudinal course + collateral history + risk inventory | study design or programme description, often no patient |
| Typical option dimensions | diagnosis, test, drug | diagnosis, supportive-care intensity, disposition | diagnosis, timing, route/mode of delivery | intervention intensity, imaging modality, disposition | care intensity, treatment modality, communication act | bias class, ethical value served, legal duty, programme action |
| Typical contrast types | same-syndrome mimics; same-class drugs | age-adjacent diagnoses; over-treatment | non-pregnant mimic; wrong-trimester action | wrong intensity; wrong modality; premature/delayed operation | wrong care intensity; over/under-pathologising; treating before securing safety | wrong bias; uptake-vs-autonomy confusion; wrong duty holder |
| Common item-writing failure modes | key-only qualifier; lone-key drug class | option set drifts to adult thresholds | severity-tier mismatch (R4 ×1); enacted-practice cue (R4 ×1) | lone-key organ system (R4 ×1); intensity mismatch (R4 ×1) | lone-key care setting (R4 ×1); scenario beyond discrimination band (R4 ×1) | lone-key intent (R4 ×1); statistical option not parallel |
| Evidence currentness sensitivity | HIGH (drug/threshold churn) | MODERATE–HIGH | HIGH (screening intervals, gestational thresholds) | MODERATE (anatomical constants — but see finding 6) | HIGH (guideline severity bands — see finding 6) | HIGH (jurisdiction, statute, programme policy) |
| Differential diagnosis central? | central | central | central | secondary to intensity/disposition | central *and* longitudinal | not applicable |
| Strategy- vs action-level options | both | mostly action | both | **strategy-level required** for definitive care | **strategy-level required** for treatment plans | strategy-level |
| Longitudinal reasoning required? | sometimes | growth/development | pregnancy timeline | peri-operative course | **yes, definitional** (PSY-I01 turned on 15 years of collateral) | programme timeline |
| Quantitative interpretation common? | yes (scores, labs) | yes (weight-based dosing, centiles) | yes (dating, screening intervals) | yes (scores, measurements — the R4 unit defect) | scale scores, but scales must not determine disposition | **yes, definitional** |
| Legal/jurisdictional reasoning? | capacity, consent | consent, child protection | consent, confidentiality | consent, trauma reporting | **yes — involuntary admission, capacity** | **yes — statutes, mandatory reporting** |

The three cells that carry real architectural weight are the **option dimension** row (five failures),
the **evidence currentness** row (two failures), and the **strategy-vs-action** row (the PSY-I02
granularity defect). Everything else is context that the common core already handles.

---

## 3. Phase 3 — common core versus profile

### Common core (never profile-controlled)

Ownership of these stays with `chapter_staged_generation`. A profile may not weaken any of them.

1. Toronto Notes anchor lineage and `ANCHOR_FIDELITY`.
2. MCC objective and physician-activity mapping; the four `PHYSICIAN_ACTIVITIES`.
3. `PRIMARY_LEARNER_DECISION` declaration.
4. Evidence provenance: source registry, claim ids, sha256 binding.
5. `EVIDENCE_ENTAILMENT_ADJUDICATION`, including the refusal of `GENERAL_CONCEPT_CLAIM` scope for
   scenario-specific claim types.
6. `CRITICAL_FACT_ADJUDICATION` (new, §4) — global, discipline-independent.
7. `BLIND_COVER_OPTIONS_SOLVER`.
8. Single-best-answer requirement.
9. The calibrated rationale contract (`RATIONALE_FATAL_CRITERIA`, enhancement classes never reject).
10. `FRESH_INDEPENDENT_VERIFICATION` under `qgen_reviewer_calibration_v2`.
11. Deterministic duplicate detection (`semantic_fingerprint`) and option-position cue detection.
12. **The admissibility *mechanism*** — the rules in §6 are universal; only their vocabularies are
    profile-supplied.
13. The two universal item-writing rules R4 forces: stem-enactment prohibition and the
    negation-mode test (§6, ADM-3/ADM-4).

### Profile-controlled

A profile is **data**, not code: a validated JSON document per discipline. It may declare only:

1. Permitted `ITEM_ARCHETYPE`s and their weights.
2. Permitted `OPTION_SET_ARCHETYPE`s per item archetype.
3. **Closed response-class vocabularies** per option-set archetype (the missing axes).
4. **Nominal parity axes** and their closed value sets (organ system, investigation purpose,
   communicative intent, care setting).
5. Scenario requirements (which context fields a stem of this archetype must carry).
6. Decision-granularity patterns permitted per archetype.
7. Competitor-ranking preference order among admissible competitors.
8. Evidence-source preference order and currentness escalation triggers.
9. Numeric-risk classes that escalate to Level 2 for this discipline.
10. Named prohibited shortcuts (traps) for profile-specific preflight.

A profile may **not** declare: a diagnosis, a drug, a topic, a threshold value, a stem template, an
option string, or any relaxation of a common-core gate. Any profile entry naming a specific clinical
entity is a validation error. This is the anti-hard-coding invariant, and it is machine-checkable
against the study-unit and concept registries.

---

## 4. Phase 4 — global critical-fact adjudication

Scope: **claim admission into an evidence packet**, not per-question. 106 claims served 15 items in
R4; escalating at claim level amortises the cost roughly 7:1 and rises far more slowly than the
question count. A question inherits its claims' adjudication status; it does not re-adjudicate.

### 4.1 Claims requiring enhanced validation

A claim is `CRITICAL` if its statement contains any of:

`NUMERIC_VALUE`, `UNIT`, `MEDICATION_DOSE`, `CLINICAL_SCORE_COMPONENT`,
`CLINICAL_SCORE_THRESHOLD`, `SCREENING_INTERVAL`, `TREATMENT_THRESHOLD`,
`GUIDELINE_SEVERITY_BAND`, `GESTATIONAL_AGE_THRESHOLD`, `ANATOMICAL_MEASUREMENT`,
`EPIDEMIOLOGIC_VALUE`, `FORMULA_DERIVED_VALUE`, `TIME_WINDOW`, `LEGAL_JURISDICTIONAL_REQUIREMENT`.

`GUIDELINE_SEVERITY_BAND` is added on the strength of finding 6 — the PSY-I03 defect is a band, not
a number, and would escape a purely numeric trigger.

Detection is deterministic: regex over numerals and units, plus a closed lexicon of band/threshold/
interval/duty phrases. No model call. Ordinary qualitative claims — the large majority — stay at
Level 0 and cost nothing extra.

### 4.2 Validation levels

| Level | Applies to | Action | Cost |
| --- | --- | --- | --- |
| **0** | ordinary supported qualitative claim | existing evidence entailment only | none |
| **1** | deterministically derivable claim (arithmetic, unit conversion, formula in `NUMERIC_FORMULA_IDS`) | recompute locally; mismatch → Level 3 | deterministic |
| **2** | `CRITICAL` claim passing the sanity checks in §4.3 | require a second independent corroborating source, **or** an authoritative primary reference cited directly for that value | one bounded retrieval per *claim*, amortised across items |
| **3** | sources conflict, sanity check trips, or magnitude implausible | **fail closed**; record adjudication; exclude the fact from generation | one high-reasoning adjudication, rare |

Level 2 is **not** "two sources for every question". It is "a second source for a claim that states
a number, a unit, a band, a threshold, an interval or a legal duty". In the R4 packet that is a
minority of 106 claims, and each such claim is reused across items.

### 4.3 Source sanity checks (deterministic, run before Level 2)

1. **Unit incompatibility** — the unit is not of the dimension the quantity requires (a length given
   in mg).
2. **Unit-transposition suspicion** — the numeral matches a canonical value under a customary unit
   swap (inch↔cm, lb↔kg, mg↔g, mmol/L↔mg/dL, °F↔°C). *This check alone catches the R4 McBurney
   defect: "1.5 to 2 cm" is the canonical "1.5 to 2 inches" numeral under an inch→cm transposition.*
3. **Dimensional inconsistency** — a derived quantity whose units do not reduce correctly.
4. **Internal arithmetic inconsistency** — stated components do not produce the stated total; already
   implemented for `SUM_OF_COMPONENTS`, generalised to all `NUMERIC_FORMULA_IDS`.
5. **Implausible magnitude** — outside a stored plausible range for the quantity class.
6. **Contradiction with a structured reference** — anatomy, pharmacology, or physiology constants
   held as data. *McBurney's point is one third of the ASIS-to-umbilicus line; 2 cm is roughly one
   tenth. This check catches it a second, independent way.*
7. **High-authority disagreement** — two admitted sources state incompatible values for the same
   quantity. *This is the PSY-I03 detector.*

### 4.4 When an authoritative source appears wrong

The generator **never silently corrects a source.** On a Level 3 outcome it writes a
`critical_fact_adjudication` record:

```
{ claim_id, fact_class, SOURCE_CLAIM, CONFLICTING_EVIDENCE[],
  ADJUDICATED_VALUE | null, ADJUDICATION_BASIS, status }
```

`status` ∈ `{ADJUDICATED_SOURCE_CORRECT, ADJUDICATED_SOURCE_ERRONEOUS, UNRESOLVED}`. Until status is
not `UNRESOLVED`, the disputed fact is **excluded from generation** and any item depending on it
fails closed. An `ADJUDICATED_SOURCE_ERRONEOUS` claim may be cited for context but its disputed
value may never reach a stem, option or rationale.

### 4.5 Two schema corrections this forces

- **`verification_status` is split.** `VERIFIED_COMPLETE` today means *faithfully transcribed* and is
  being read as *true*. It becomes `transcription_status` (fidelity to the source) plus
  `fact_status` (outcome of adjudication). The invariants `AUTHORITATIVE_SOURCE ≠ GUARANTEED_FACTUAL_
  CORRECTNESS`, `TRACEABILITY ≠ FACTUAL_VALIDATION` and `ENTAILMENT ≠ TRUTH_VALIDATION` are made
  structural rather than advisory.
- **`NUMERIC_DERIVATION_VALIDATION` becomes `NUMERIC_ASSERTION_AND_DERIVATION_VALIDATION`.** Finding 7:
  every numeral in a candidate-facing stem, option or rationale must be enumerated as an assertion
  and bound to a claim, whether or not it was derived. `no_derived_values_present: true` may no
  longer coexist with a numeral in the stem.

---

## 5. Phase 5 — discipline profiles

Each profile is expressed at discipline × item-archetype level. **No profile names a diagnosis, a
drug or a topic.** Only the fields that carry architectural weight are given here; the full field
list is §3.

Shared archetype-independent fields for all six: preferred physician activities drawn from
`PHYSICIAN_ACTIVITIES`; scenario requirements; competitor-ranking rule
(*prefer the admissible competitor whose frozen correctness condition is nearest to being satisfied
by this stem* — the near-miss preference, which is the ranking signal R4 lacked).

### MEDICINE — `UNTESTED_IN_R4`
- Item archetypes: `DIAGNOSIS`, `INVESTIGATION_SELECTION`, `PHARMACOTHERAPY`, `RISK_STRATIFICATION`, `INTERPRETATION`.
- Option-set archetypes: `DIAGNOSIS_SET`, `INVESTIGATION_SET`, `NEXT_ACTION_SET`, `MANAGEMENT_STRATEGY_SET`.
- Response classes — `DIAGNOSIS_SET`: entity capable of the stem's cardinal syndrome.
  `INVESTIGATION_SET`: purpose ∈ {`STRUCTURAL`, `FUNCTIONAL`, `MICROBIOLOGIC`, `BIOCHEMICAL`, `MONITORING`, `STAGING`}.
  Nominal parity axes: `organ_system`, `drug_class`, `investigation_purpose`.
- Numeric-risk: drug doses, score thresholds, laboratory cut-offs → Level 2.
- Currentness: HIGH for therapy and thresholds.
- Traps: key-only qualifier; lone-key drug class; option set mixing diagnosis with test.

### PEDIATRICS — R4 control, 3/3
- Item archetypes: `AGE_BANDED_DIAGNOSIS`, `RED_FLAG_RECOGNITION`, `SUPPORTIVE_CARE_CEILING`, `INVESTIGATION_SELECTION`, `WEIGHT_BASED_THERAPY`.
- Response classes — `NEXT_ACTION_SET`: `supportive_care_intensity` ∈ {`OBSERVATION`, `MINIMAL_SUPPORT`, `LOW_FLOW_SUPPORT`, `HIGH_FLOW_SUPPORT`, `ESCALATION_TO_CRITICAL_CARE`}.
  Nominal parity axes: `age_appropriateness`, `investigation_purpose`.
- Scenario requirements: age **and** weight where dosing is at issue; immunisation status where infection is at issue.
- Numeric-risk: weight-based doses, centiles, age thresholds → Level 2.
- Traps: adult thresholds imported; over-investigation distractors that are simply wrong rather than tempting.
- *Why it passed:* the source states explicit conditions ("recommended where required for infection
  control"), and the stem satisfies rather than negates those conditions. The profile encodes that
  preference — prefer sources that state conditions of applicability.

### OBGYN — R4 0/3
- Item archetypes: `PREGNANCY_DATED_DIAGNOSIS`, `MATERNAL_FETAL_ACTION`, `SCREENING_TIMING`, `POSTPARTUM_LACTATION_MANAGEMENT`, `INVESTIGATION_SELECTION`.
- Response classes — `DIAGNOSIS_SET`: entity capable of the stem's cardinal syndrome, with
  `inflammatory_state` ∈ {`NON_INFLAMMATORY`, `LOCALIZED_INFLAMMATORY`, `SYSTEMIC_INFLAMMATORY`} as a
  parity axis (**directly catches OBGYN-I01**).
  `INVESTIGATION_SET`: `investigation_purpose` bound to the lead-in (**directly catches OBGYN-I02**).
- Nominal parity axes: `inflammatory_state`, `investigation_purpose`, `gestational_applicability`.
- Scenario requirements: gestational age or postpartum day; parity; fetal status where relevant.
- Numeric-risk: gestational-age thresholds, screening intervals → Level 2.
- Traps: **stem-enactment** (the OBGYN-I03 mode) is listed as a profile trap *and* enforced
  universally by ADM-4; non-inflammatory entity offered against a febrile presentation.

### SURGERY — R4 1/3
- Item archetypes: `RECOGNITION`, `STABILIZATION`, `IMAGING_SELECTION`, `OPERATIVE_VS_NONOPERATIVE`, `DISPOSITION`. (No appendicitis anywhere in the profile.)
- Response classes — `MANAGEMENT_STRATEGY_SET`: `source_control_class` ∈ {`NONE`, `PHARMACOLOGIC_ONLY`, `PERCUTANEOUS`, `DELAYED_OPERATIVE`, `IMMEDIATE_OPERATIVE`}; where the stem establishes a source-control-demanding physiology, options with `NONE`/`PHARMACOLOGIC_ONLY` are inadmissible (**catches SURG-I03 while correctly admitting drainage and interval operation**).
  `INVESTIGATION_SET`: `invasiveness_tier` and `investigation_purpose`.
- Nominal parity axes: `organ_system` (**catches SURG-I01(b)**), `source_control_class`, `investigation_purpose`.
- Numeric-risk: **anatomical measurements → Level 2 with mandatory unit-transposition and structured-anatomy checks** (finding 6). Scores → Level 1 then Level 2.
- Traps: lone non-gynecologic key in a female abdominal-pain set; operative option offered where the stem gives no physiologic instability.

### PSYCHIATRY — R4 1/3
- Item archetypes: `DIAGNOSIS`, `SAFETY_ASSESSMENT`, `LONGITUDINAL_DIFFERENTIAL`, `PHARMACOTHERAPY`, `COMMUNICATION_AND_CAPACITY`. (No depression anywhere in the profile.)
- Response classes — `DISPOSITION_SET` under `SAFETY_ASSESSMENT`: `safety_securing_class` ∈ {`NONE`, `ASSESSMENT_ONLY`, `COMMUNITY_SAFETY_MEASURE`, `INTENSIVE_COMMUNITY`, `INVOLUNTARY_OR_INPATIENT`}; options with `NONE`/`ASSESSMENT_ONLY` are inadmissible where the stem establishes imminent risk (**catches PSY-I02's risk scale and antidepressant, correctly admits the safety plan**).
  `care_setting` ∈ {`COMMUNITY`, `INTENSIVE_OUTPATIENT`, `INPATIENT`} as a nominal parity axis (**catches the lone-key setting cue**).
- Scenario requirements: longitudinal course; collateral source; explicit risk inventory.
- **Decision-granularity rule:** `SAFETY_ASSESSMENT` items must be pitched *at* the discrimination
  band. A scenario in which every risk feature points one way is rejected before wording (**catches
  PSY-I02(b)**). This is the one place a profile constrains the *scenario*, and it is justified by a
  reviewer defect, not by taste.
- Numeric-risk: **`GUIDELINE_SEVERITY_BAND` → Level 2 mandatory** (finding 6, PSY-I03).
- Traps: a rating scale offered as a determinant of disposition; treatment offered before safety.

### PHELO — R4 2/3
- Item archetypes: `EPIDEMIOLOGY_INTERPRETATION`, `ETHICAL_ACTION`, `LEGAL_DUTY`, `SCREENING_DECISION`, `PUBLIC_HEALTH_INTERVENTION`.
- Option-set archetypes: `STATISTICAL_INTERPRETATION_SET`, `ETHICAL_ACTION_SET`, `LEGAL_ACTION_SET`, `MANAGEMENT_STRATEGY_SET`.
- Response classes — `ETHICAL_ACTION_SET`: `value_served` ∈ {`AUTONOMY`, `BENEFICENCE`, `NON_MALEFICENCE`, `JUSTICE`, `PROGRAMME_UPTAKE`, `CONFIDENTIALITY`}; every option must serve the value the lead-in names (**catches PHELO-I02**).
  `STATISTICAL_INTERPRETATION_SET`: every option must be an explanation of the same observed phenomenon class.
  `LEGAL_ACTION_SET`: every option available to the same duty holder in the same jurisdiction.
- **Granularity fix:** PHELO items twice fell to `decision_granularity: OTHER`. The profile adds
  `EPIDEMIOLOGIC_EXPLANATION`, `ETHICAL_ACTION`, `LEGAL_DUTY`, `PROGRAMME_ACTION` to
  `DECISION_GRANULARITIES` — the only extension to a common-core enum this design proposes, and it
  is forced by two observed `OTHER`s.
- Numeric-risk: epidemiologic values, formula-derived values, screening intervals → Level 2;
  legal/jurisdictional requirements → Level 2 with a Canadian-jurisdiction source required.
- Traps: an uptake lever offered against an autonomy lead-in; key distinguished by carrying two
  figures when the distractors carry one (a realization-level format cue — ADM-5).

---

## 6. Phase 6 — option-set architecture

Every item declares an `OPTION_SET_ARCHETYPE` **before any wording exists**, drawn from a closed
common-core set:

`DIAGNOSIS_SET`, `INVESTIGATION_SET`, `NEXT_ACTION_SET`, `MANAGEMENT_STRATEGY_SET`,
`DISPOSITION_SET`, `STATISTICAL_INTERPRETATION_SET`, `ETHICAL_ACTION_SET`, `LEGAL_ACTION_SET`.

The archetype selects, from the bound profile, one `RESPONSE_CLASS_AXIS` and a list of
`NOMINAL_PARITY_AXES` — all closed enumerations authored in the profile, not by the generator.

### The falsifiability repair

This is the part that makes the design different from adding a gate.

1. The realized stem and lead-in determine a single `DEMANDED_RESPONSE_CLASS`, assigned by a bounded
   call that sees the stem, the lead-in and the axis definition — **and not the options.**
2. Each option is assigned its `RESPONSE_CLASS` and its value on each nominal axis by a bounded
   classifier that sees **one option text and the axis definition only** — not the item, not the
   stem, not the key, not the roles, not the other options.
3. Admissibility is then **arithmetic over those labels**, with no further model judgement.

Because the classifier cannot know which option is the key, it cannot label to make the set pass.
That property, not the rule content, is what R4 lacked: in R4 the same agent that built the set also
declared its labels and its verdict, and it declared `PASS` 250 times out of 250.

### Admissibility rules

- **ADM-1 (response class).** Every option's `RESPONSE_CLASS` must equal `DEMANDED_RESPONSE_CLASS`.
  *Accounts for 5 of 10 R4 causal chains; zero false positives against the 45 R4 competitors.*
- **ADM-2 (nominal parity).** On each nominal axis, the key may not be the sole holder of its value
  while all distractors share one value; and no distractor may be a sole outlier. This is the
  existing `find_option_category_parity_defects` logic, unchanged, finally run on non-degenerate
  inputs. *Accounts for SURG-I01(b).*
- **ADM-3 (negation mode).** For each competitor, join its frozen
  `conditions_under_which_competitor_would_be_correct` against the `stem_feature_map`. If the only
  defeating feature is a stem clause with no other clinical function, the competitor is inadmissible
  — this is `EXCLUSION_BY_EXPLICIT_STEM_NEGATION`, which the calibration report shows predates
  schema 1.3 and survives in the Cardiology pilot. Replaces `TERMINAL_EXCLUSION_REVIEW` with a
  version that has an input it cannot fabricate.
- **ADM-4 (stem enactment).** No option may restate an action the `stem_feature_map` records the
  patient as already performing (`TREATMENT_RESPONSE` / `EXPLICIT_FINDING` features naming a
  patient-performed action). Deterministic set intersection. *Accounts for OBGYN-I03.*
- **ADM-5 (realization parity).** After wording, no option may be the sole member carrying a
  structural format the others lack (two figures against one, a paired clause against three single
  clauses). Deterministic. *Accounts for the PHELO-I02 format cue.*

### Does this add another generic post-hoc validator?

No, on four grounds, each checkable:

1. It runs **before wording**, at set selection, not post hoc. ADM-5 is the single post-wording rule
   and is purely deterministic.
2. It **replaces seven stages** (`CONTEXTUAL_COMPETITOR_PROOF`, `TERMINAL_EXCLUSION_REVIEW`,
   `SEMANTIC_POLARITY_COMPLETENESS_PREFLIGHT`, `OPTION_SEMANTIC_CATEGORY_PARITY`,
   `PRE_ASSEMBLY_SEMANTIC_SET_REVIEW`, `PARALLEL_OPTION_SET_REVIEW`, `DECISION_GRANULARITY_PARITY`)
   with one. Net stages fall from 25 to 21.
3. Its inputs are **externally authored** — profile enumerations and a frozen seed field — so it is
   falsifiable in a way none of the seven were.
4. Its rules were **derived from and validated against** the R4 outcome data, including the negative
   cases. A rule that could not have separated the 7 passes from the 8 failures is not in the list.

---

## 7. Phase 7 — the contrast library under profiles

The curated library is **reused as it stands**. No rebuild. R4's central positive result is that
supply is solved: 15/15 targets cleared three approved competitors and
`FAIL_CLOSED_INSUFFICIENT_COMPETITIVE_SEEDS = 0`.

### Incremental enrichment (additive tags only)

Existing seed fields are unchanged and remain authoritative. Added per seed:

| New tag | Source | Cost |
| --- | --- | --- |
| `applicable_disciplines[]` | from the target's existing `discipline` | deterministic |
| `applicable_item_archetypes[]` | from the target's existing `learner_decision_type` | deterministic, one-time mapping table |
| `option_set_archetypes[]` | from `decision_granularity` + `option_semantic_category` | deterministic |
| `response_class` | role-blind classifier over `competitor_concept` and the profile axis | one small call per seed, one time |
| `nominal_axis_values{}` | same classifier | same call |
| `condition_predicates[]` | structured parse of the existing `conditions_under_which_competitor_would_be_correct` prose into `{feature, polarity, comparator}` triples | one small call per seed, one time |

`condition_predicates` is the highest-value addition: it converts the field that already refutes six
of the R4 defective distractors from prose into something ADM-3 can join deterministically against
the `stem_feature_map`. 82 seeds × two small calls is a one-time cost, and the tags are then frozen
alongside the pack.

### Retrieval filter

Retrieval is a deterministic index lookup on `(discipline, item_archetype, learner_decision,
option_set_archetype, decision_granularity)`, followed by ADM-1/ADM-3 against the realized scenario,
followed by ranking. Only the ranking step is a model call, and it ranks an already-admissible set.

**Seed strength is demoted as a retrieval filter.** Finding 4 shows `reviewed_strength` did not
predict realized failure (5 of 6 defective distractors were `STRONG`). It is retained as a
tie-breaker in ranking, not as a gate.

---

## 8. Phase 8 — quality-control architecture

```
CURRICULUM TARGET
  -> DISCIPLINE PROFILE BINDING            (deterministic lookup on the manifest's discipline)
  -> ITEM ARCHETYPE                        (profile-constrained choice)
  -> LEARNER DECISION
  -> OPTION_SET_ARCHETYPE + AXES           (deterministic from archetype x profile)
  -> CRITICAL FACT CHECK                   (claim-level, amortised; §4)
  -> STEM + KEY
  -> STEM FEATURE MAP + NUMERIC ASSERTIONS
  -> BLIND SOLVER
  -> PROFILE-AWARE CONTRAST RETRIEVAL      (deterministic index + ADM-1/ADM-3 filter)
  -> CONTRASTIVE EVIDENCE + ENTAILMENT
  -> OPTION-SET ADMISSIBILITY ADJUDICATION (role-blind labels, arithmetic verdict; ADM-1..4)
  -> ITEM REALIZATION
  -> SEMANTIC ACCEPTANCE                   (ADM-5 + cue checks)
  -> RATIONALE
  -> INDEPENDENT VERIFICATION
```

Proposed stage sequence (21 stages against `STAGE_SEQUENCE_V5`'s 25):

1 `CURRICULUM_TARGET_AND_PROFILE_BINDING` · 2 `TORONTO_NOTES_ANCHOR` ·
3 `MCC_OBJECTIVE_PHYSICIAN_ACTIVITY` · 4 `ITEM_AND_OPTION_SET_ARCHETYPE_DECLARATION` ·
5 `PRIMARY_LEARNER_DECISION` · 6 `ANCHOR_FIDELITY` · 7 `CRITICAL_FACT_ADJUDICATION` ·
8 `OPEN_ENDED_STEM_KEY` · 9 `CANDIDATE_VISIBLE_STEM_FEATURE_MAP` ·
10 `NUMERIC_ASSERTION_AND_DERIVATION_VALIDATION` · 11 `BLIND_COVER_OPTIONS_SOLVER` ·
12 `PROFILE_AWARE_CONTRAST_RETRIEVAL` · 13 `CONTRASTIVE_EVIDENCE_MATRIX` ·
14 `EVIDENCE_ENTAILMENT_ADJUDICATION` · 15 `OPTION_SET_ADMISSIBILITY_ADJUDICATION` ·
16 `SEPARATE_DISTRACTOR_CONSTRUCTION` · 17 `OPTION_REALIZATION` · 18 `MCQ_ASSEMBLY` ·
19 `PLAN_FIDELITY_SHORTCUT_CUE_CHECK` · 20 `RATIONALES` · 21 `FRESH_INDEPENDENT_VERIFICATION`.

Removed: the seven constant-`PASS` stages (§0 finding 1) and `DISTRACTOR_ADVERSARIAL_RANKING`,
folded into stage 15 as its one bounded ranking call.
Added: stages 1, 4 (both deterministic, zero model cost) and 7.

**Is this simpler and safer than the current sequence?** Simpler: four fewer stages, and the seven
that carried no information are gone. Safer: every retained semantic judgement now has at least one
input the judging party did not author, and every deterministic gate now runs on a closed vocabulary
rather than on free text.

---

## 9. Phase 9 — scale-readiness gates

> **Superseded by §24.** The invariants below and gate G0 are carried forward unchanged. G1-G4 are
> restated in §24 on quality, safety, coverage, yield and redundancy, because Part II removes the
> quota this section's pass-rate ratios were denominated against.

Scaling to 6,086 is **not** recommended and no gate in this section authorises it. The invariants
below must hold at every gate; a single breach stops the wave.

```
FACTUAL_ERRORS        = 0
NUMERIC_ERRORS        = 0
UNSUPPORTED_CLAIMS    = 0
AMBIGUOUS_BEST_ANSWERS= 0
EVIDENCE_ENTAILMENT   = PASS
```

| Gate | Scope | Additional criteria |
| --- | --- | --- |
| **G0 — Retrospective replay** | Re-run stage 15 over the frozen R4 artifact | Must reject ≥ 7 of the 8 failed items **and** accept ≥ 6 of the 7 passed items. Any rejection of a passing item must be individually justified. *This is the falsification test: a design that cannot separate the R4 outcomes does not proceed.* |
| **G1 — Profile micro pilot** | 3 items in one discipline | Invariants hold; 3/3 independent verification; `LONE_KEY_OPTION_CATEGORY` = 0; no gate family may return a constant verdict across the pilot |
| **G2 — Profile 10-item pilot** | 10 items, same discipline, ≥ 3 archetypes | Invariants hold; ≥ 8/10; `WEAK_DISTRACTOR` ≤ 1; `OPTION_CUE_FAILURE` ≤ 1; fail-closed rate ≤ 20 % |
| **G3 — Cross-profile generalization** | 18 items, 6 disciplines × 3, **MED included** | Invariants hold; ≥ 15/18; no single discipline below 2/3; `LONE_KEY_OPTION_CATEGORY` = 0 across all disciplines; `SEVERITY_OR_CATEGORY_MISMATCH` = 0 across all disciplines; fresh reviewer, no access to the construction record |
| **G4 — Production wave** | first 100 items | Invariants hold on a 20-item audited sample; defect rates within G3 bounds; explicit user authorization |

Two standing requirements:

- **Verdict-variance monitoring.** Any gate family returning a single distinct verdict across a
  whole pilot is reported as `GATE_UNINFORMATIVE` and blocks the gate, regardless of pass rate. This
  is the direct institutional lesson of finding 1.
- **Reviewer variance.** G1–G3 use fresh reviewers under `qgen_reviewer_calibration_v2`. Defect
  counts, not pass rates, are the comparable quantity across waves.

---

## 10. Phase 10 — cost and token design

### Deterministic (zero model cost)

Profile binding; archetype and axis selection; seed index retrieval; `CRITICAL` fact-class detection;
unit, dimension, transposition and magnitude checks; formula recomputation; evidence joins;
provenance and sha256 binding; ADM-2, ADM-4, ADM-5; duplicate and position-cue detection; the
admissibility arithmetic itself.

### Bounded small calls

Role-blind option classification (4 per item, cacheable — options recur across items);
`DEMANDED_RESPONSE_CLASS` (1 per item); seed enrichment (one-time per seed, not per question).

### High-reasoning calls, reserved

Stem and key generation; blind solver; competitor ranking among admissible candidates; Level 3 fact
adjudication (rare, claim-level); independent verification.

### Estimated per-item budget

| | Current (schema 1.4) | Proposed |
| --- | --- | --- |
| Semantic gate calls | ~7 (all constant-`PASS`) | 0 |
| Adversarial/ranking calls | 2 | 1 |
| Option/response classification | 0 | 5 small |
| Critical-fact calls | 0 | ~0.15 amortised (claim-level, 106 claims / 15 items in R4, minority `CRITICAL`) |
| Core generation + verification | ~6 | ~6 |
| **Approximate total** | **~15 calls, 7 uninformative** | **~7 large + 5 small** |

Cost direction is **LOWER**, and the reduction comes from deleting calls that produced no
information rather than from weakening any check. Broad web research per question is not introduced:
Level 2 retrieval is per *claim*, one time, and its results are frozen into the evidence packet.

---

## 11. Option comparison

| | **A. Universal generator + more gates** | **B. Common core + discipline profiles + global fact safety** | **C. Fully separate generator per discipline** |
| --- | --- | --- | --- |
| Quality | Low. Three universal patches have been tried; R4's seven newest gates returned 250/250 `PASS`. Adding an eighth over the same free-text inputs is the defect, repeated | High, *conditional on the falsifiability repair*. Without role-blind labelling, B degrades into A with more vocabulary | Possibly high per discipline; no shared learning; a defect found in one is fixed six times |
| Maintainability | Degrading — 25 stages, seven inert | Good — 21 stages; profiles are validated data, not code | Poor — six divergent codebases against a 6,086-item bank |
| Medical accuracy | Unchanged. Neither R4 source defect is an option-set problem and no universal gate addresses them | Improved — §4 is common-core and addresses both directly | Improved only if §4 is duplicated six times |
| MCCQE realism | Poor — PHELO already falls out of the universal granularity vocabulary twice in 15 items | Good — archetypes match how each discipline's decisions are actually posed | Good, at high cost |
| Scaling cost | Rising with each gate | Lower than current (§10) | Highest |
| Evidence requirements | Unchanged, and the R4 defects show that is insufficient | Risk-escalated, claim-level, amortised | Same as B, six times over |
| Overfitting risk | High — each patch is fitted to the last wave's defects | **Moderate, and the real risk of this proposal.** Mitigated by the anti-hard-coding invariant (§3), by profiles carrying no clinical entities, and by gate G0 requiring the design to accept R4's passes as well as reject its failures | Severe — a per-discipline generator is a per-discipline overfit by construction |
| Contrast library reuse | Full | Full, plus additive tags | Fragmented |

**Recommendation: B**, adopted on the structural grounds in §2 rather than on discipline clustering,
which finding 5 does not support. The strongest argument against B is that a profile is another place
to hide an overfit; §3's invariant and gate G0 exist specifically to make that failure visible.

---

## 12. Self-review

- **Universal-patch creep.** Checked. The design removes seven stages and adds three, two of which
  are deterministic. It extends exactly one common-core enum (`DECISION_GRANULARITIES`, forced by two
  observed `OTHER` values). Every new rule ADM-1…ADM-5 is traced to a specific reviewer defect *and*
  tested against the competitors the reviewer accepted. **Residual risk:** ADM-3 and ADM-5 are close
  in spirit to gates that already failed; their difference is that their inputs are externally
  authored. If implementation lets the generator author `condition_predicates` for the seed it is
  about to use, this collapses back into A. Enrichment must be a separate, frozen, one-time pass.
- **Excessive discipline hard-coding.** Checked. No profile names a diagnosis, drug, topic or
  threshold; §5 deliberately notes the absence of appendicitis from SURGERY and depression from
  PSYCHIATRY. **Residual risk:** response-class vocabularies such as `source_control_class` are one
  abstraction step from their motivating cases. They must be reviewed against study units outside
  the R4 targets before implementation.
- **Factual-safety loopholes.** Two closed explicitly: `verification_status` split into transcription
  and fact status (§4.5), and numeric *assertions* brought under obligation alongside derivations
  (finding 7). **Residual loophole:** a qualitative claim that is simply wrong and carries no numeral,
  band or duty stays at Level 0 and is caught only by independent verification. This is accepted; the
  alternative is redundant research on every claim, which §10 rules out. It is stated here rather than
  hidden.
- **Source-trust assumptions.** The three invariants are made structural, not advisory. Level 3
  records rather than corrects, and excludes the disputed fact. **Residual risk:** two sources may
  agree and both be wrong; no architecture in this class detects that.
- **Option-archetype ambiguity.** Eight archetypes with a single declared `RESPONSE_CLASS_AXIS` each,
  declared before wording, with closed profile vocabularies. **Residual risk:** an item that
  legitimately mixes archetypes (a set combining a test and an observation, as in PED-I02) needs a
  validated exception path; the design permits one but does not yet specify who authorises it. This is
  an open question for the implementation plan.
- **Token-cost scaling.** Per-item calls fall from ~15 to ~7 large + 5 small; the fact layer is
  claim-level and amortises 7:1 at R4 density and better at scale. **Residual risk:** the role-blind
  classifier adds four calls per item; if option-text caching is not implemented, that erodes part of
  the saving.
- **Statistical honesty.** The discipline-clustering claim that motivated this task is not supported
  (p = 0.31), and two `MEMORY.md` statements are corrected here (findings 4 and 6). The recommendation
  survives without them, on structural grounds; this is stated rather than smoothed over.
- **What would falsify this design.** Gate G0. If stage 15, replayed over the frozen R4 artifact,
  cannot reject the 8 failed items while accepting the 7 passed ones, the design is wrong and should
  not be implemented.

---

## 13. Open questions for the implementation plan

1. Who authorises an `OPTION_SET_ARCHETYPE` exception, and what record does it leave?
2. Which structured references back the anatomy/pharmacology sanity check, and how are they admitted?
3. Does the MED profile need its own pilot before G3, given it was untested in R4 and its historical
   cohort scored 0/4 under the calibrated rubric?
4. Should `EVIDENCE_ENTAILMENT_ADJUDICATION` and ADM-3 merge, since both join claims to the stem
   feature map?
5. What is the migration path for the frozen r2–r4 artifacts under a schema 1.5 that adds
   `fact_status`? (Default assumption: frozen artifacts are not migrated; they are read at their own
   schema version.)

---
---

# Part II — coverage-first safe-yield amendment

## 14. Amendment scope

A product decision taken after Part I was written removes question count as an optimisation target.
The project no longer optimises for approximately 1,000 questions per discipline, and no longer
optimises for exactly 6,086 final questions.

**New production objective:**

> **Maximise safe, high-quality, educationally distinct MCCQE-style questions subject to adequate
> curriculum coverage.**

Explicitly not the objective: maximise raw question count; fill every allocated slot; reach 6,086 at
any quality cost.

### Does this contradict Part I?

No. Every Part I conclusion is re-examined against the new objective and survives:

| Part I conclusion | Status under Part II |
| --- | --- |
| `RECOMMENDED_ARCHITECTURE = COMMON_CORE_PLUS_DISCIPLINE_PROFILES` | **Retained.** Its justification (§2) was structural — the comparison axis is archetype- and discipline-shaped and must come from outside the generator — and never rested on volume |
| `GLOBAL_CRITICAL_FACT_ADJUDICATION = YES` | **Retained and strengthened.** §4 amortises at claim level, which improves as the item count falls only if claim reuse holds; §25 revisits the arithmetic |
| `RISK_BASED_FACT_ESCALATION = YES` | **Retained.** Risk is a property of the claim, not of how many questions are wanted |
| `OPTION_SET_ARCHETYPE_REQUIRED = YES` | **Retained.** It becomes *more* load-bearing: `FAIL_CLOSED_INCOHERENT_OPTION_SET_ARCHETYPE` is now an acceptable terminal outcome rather than a blocker to be worked around |
| `PROFILE_AWARE_CONTRAST_RETRIEVAL = YES` | **Retained.** Retrieval that returns fewer than three admissible competitors now legitimately ends the opportunity instead of forcing a weaker set |
| `RECOMMENDED_ARCHITECTURE_ACTION = DO_NOT_SCALE` (`MEMORY.md`) | **Retained.** Part II changes what a wave is measured on; it does not authorise a wave. Gate G0 is still the falsification test |

The one place Part I is genuinely in tension with the new objective is §9, whose G1-G4 criteria are
pass-rate ratios over a fixed attempted count. Those ratios presuppose that every attempt should
produce an item. §24 restates them. Nothing else in Part I changes.

---

## 15. Phase 1 — reinterpreting the 6,086 allocation

### The allocation is preserved, not deleted

`research/scope/question_bank_targets.json` and `research/scope/final_question_allocation.json`
remain **frozen and byte-identical**. They are not mutated by this design task and must not be
mutated by the implementation that follows it. They are reclassified, not rewritten.

New classification: the 6,086 allocation is a **historical curriculum-planning artifact** recording
**potential question opportunities / curriculum density**, not mandatory final output.

What the artifact actually contains, and what each field now means:

| Field | Quota reading (retired) | Density reading (adopted) |
| --- | --- | --- |
| `total_target_questions: 6086` | questions to produce | total question *opportunities* the curriculum could support at planning time |
| `final_question_count` (per address, 0-30, sum 6,086 over 1,507 addresses) | questions to produce here | `opportunity_budget` — the **maximum** number of distinct opportunities that may be opened against this address. An upper bound. Never a floor |
| `effective_minimum` (1 on 576 addresses, 2 on 394, up to 8) | a floor to satisfy — 1,364 mandatory questions on the 1-and-2 addresses alone | `curriculum_attention_signal` — evidence that the planning layer judged this address to need coverage. It ceases to be an enforcement threshold and becomes an input to priority ordering only |
| `coverage_weight` (1-5) | tie-break for slot distribution | unchanged meaning; used for within-class ordering and for reachability promotion (§16) |
| `depth` (`CORE_ACTION`, `RECOGNIZE_AND_ACT`, `RECOGNIZE`, `CONTEXT_ONLY`, `OUT_OF_SCOPE_DETAIL`) | input to slot arithmetic | **primary basis of the priority class** (§16) |
| `allocation_status` | eligibility for slots | unchanged and still binding. `ZERO_BY_SCOPE_METADATA` (301 addresses) and `SUPPRESSED_BY_OWNERSHIP` (31) remain hard zeros |

Two AGENTS.md invariants survive this reinterpretation intact and are restated because they are the
ones an opportunity model could accidentally break: **zero-scope precedence must be preserved**, and
**ownership-suppressed content must not receive independent question allocation**. Under Part II
these become: a non-`ELIGIBLE` address has an `opportunity_budget` of zero and may never open an
opportunity. Component-mode parents likewise remain non-double-allocated, since opportunities are
opened against allocation addresses, which already encode that decision.

### A slot may remain permanently unpopulated

This is now a supported, expected, non-defect outcome. Of the 1,507 addresses, 332 already carry
zero; the amendment simply removes the assumption that the other 1,175 must all be filled. An
address with an `opportunity_budget` of 30 and one accepted item is not behind — it is a topic that
safely supported one item.

### The derivative planning artifact that replaces quota enforcement

To be created by a **later, separately authorised** task. Not created here.

`research/qgen/curriculum_opportunity_plan.json`, schema
`schemas/curriculum-opportunity-plan.schema.json`. Derived **deterministically** from the frozen
allocation plus `research/qgen/question_generation_manifest.json`; regenerable; never hand-edited.
One record per allocation address:

```
{ allocation_address_id, study_unit_id, discipline, chapter,
  mcc_objective_ids[], priority_class, priority_class_basis,
  opportunity_budget,               // == final_question_count, upper bound only
  declared_learner_decisions[],     // authored and frozen BEFORE generation (§27 item 2)
  opportunities[] }                 // §18
```

Two schema-level prohibitions, machine-checkable, that exist to stop the quota returning through the
back door:

1. The schema **must not define any minimum-, target-, remaining- or shortfall-shaped field.** A
   validator asserting the absence of such a field is cheap and should exist from day one.
2. `opportunity_budget` is `maximum_opportunities` semantically and should be named that way in the
   schema. Nothing in the pipeline may compare an accepted count against it and emit a deficit.

### Follow-up flagged, not performed

`AGENTS.md` § *Allocation rules* currently states the 6,086 total as a production commitment
("Current target: MED 1,086 … Total: 6,086"). Amending it is outside this task's authorisation.
Until it is amended the repository holds two readings of the same number. This is recorded as an
open question (§28) rather than resolved silently.

---

## 16. Phase 2 — coverage-first priority model

Coverage is designed **independently of question volume**. A topic is covered when its important
learner decisions are covered, not when a number of items exists.

### Deriving the priority class

The class is derived deterministically from fields the frozen allocation already carries. Nothing is
estimated, and **no exam-frequency figure is fabricated** — MCC exam frequency is not published at
the granularity this would need, so it is simply not an input. The MCC-objective link, the
competency depth, and the Toronto Notes chapter organisation are all already present, and they are
sufficient.

| Class | Rule | Addresses | Allocated slots (density) | Distinct MCC objectives |
| --- | --- | --- | --- | --- |
| `CORE` | `allocation_status = ELIGIBLE` ∧ `depth = CORE_ACTION` | 488 | 3,339 | 174 |
| `IMPORTANT` | `ELIGIBLE` ∧ `depth = RECOGNIZE_AND_ACT` | 424 | 1,643 | 147 |
| `SUPPORTING` | `ELIGIBLE` ∧ `depth = RECOGNIZE` | 263 | 1,104 | 102 |
| `NOT_IN_SCOPE` | any non-`ELIGIBLE` status | 332 | 0 | — |

Read as meaning, not as arithmetic: `CORE_ACTION` is the depth at which the curriculum says the
learner must **act**, `RECOGNIZE_AND_ACT` that they must recognise and then act, `RECOGNIZE` that
recognition suffices. That is exactly the ordering a question bank should prioritise, and it is
already adjudicated and frozen, so the priority model adds no new judgement.

### The reachability promotion — the coverage hole this model would otherwise create

Applying the table above naively hides objectives. Computed against the frozen allocation:

- **16 mapped MCC objectives have no `CORE` address at all.** They are reachable only through
  `IMPORTANT` or `SUPPORTING` addresses.
- **3 of those are reachable only through `SUPPORTING`.**

Under a policy where `SUPPORTING` generation is optional, those 3 objectives could receive zero
questions and the bank would look healthy. That is precisely the failure Part II exists to prevent.

**`OBJECTIVE_REACHABILITY_PROMOTION` (mandatory).** For every mapped MCC objective with no `CORE`
address, promote to `CORE` the single highest-`coverage_weight` address that carries it (ties broken
by `final_question_count`, then by `allocation_address_id` for determinism). Against the frozen
allocation this promotes **15 addresses** (one covers two orphan objectives) and raises `CORE` to
**503 addresses**. After promotion, **every mapped MCC objective has at least one `CORE` address**,
which is the invariant the coverage report (§22) is entitled to assume.

`priority_class_basis` records `DEPTH_DERIVED` or `OBJECTIVE_REACHABILITY_PROMOTION` so the
promotion is visible rather than folded in.

### Generation policy per class

| Class | Policy |
| --- | --- |
| `CORE` | Make a **serious attempt** to produce at least one accepted item covering each **important learner decision** at the address — not one item per address, and not one item per slot |
| `IMPORTANT` | Generate when a strong, non-redundant item exists |
| `SUPPORTING` | Optional. Generate only when it is cheap and non-redundant; STOP-4 (§23) explicitly withdraws new evidence research from this class |

**`NO_SAFE_ITEM_YET` applies at every class, `CORE` included.** If a safe high-quality item cannot be
produced for a CORE learner decision, the pipeline records `NO_SAFE_ITEM_YET` with a reason from the
§21 taxonomy. It never lowers a standard to satisfy a class policy. `CORE` raises **effort and
ordering priority**; it never relaxes an invariant, and no gate in §24 penalises a `NO_SAFE_ITEM_YET`
outcome. It is a research signal, not a generation failure.

---

## 17. Phase 3 — SAFE_YIELD

`SAFE_YIELD(scope)` is the count of **independently accepted** questions in that scope. An item
counts toward `SAFE_YIELD` only if all of the following hold:

1. Every common-core gate (§3) returns `PASS`.
2. Every claim the item cites has `CRITICAL_FACT_ADJUDICATION` status other than `UNRESOLVED`, and no
   `ADJUDICATED_SOURCE_ERRONEOUS` value reaches its stem, options or rationale (§4.4).
3. Option-set admissibility ADM-1…ADM-5 passes on **role-blind** labels (§6).
4. `FRESH_INDEPENDENT_VERIFICATION` returns `PASS` under `qgen_reviewer_calibration_v2`, with the
   five invariants at zero: `FACTUAL_ERRORS`, `NUMERIC_ERRORS`, `UNSUPPORTED_CLAIMS`,
   `AMBIGUOUS_BEST_ANSWERS` = 0 and `EVIDENCE_ENTAILMENT` = `PASS`.
5. The item is not `REDUNDANT` under §19.

**Does not count toward `SAFE_YIELD`:** anything fail-closed; anything rejected; anything repaired
after independent review in order to raise a score — the R4 precedent stands, items are recorded as
reviewed, not repaired; and anything accepted solely by a gate family that returned a constant
verdict across the wave (`GATE_UNINFORMATIVE`, §24), which is Finding 1 made into an accounting rule.

`SAFE_YIELD` is defined and reported at five scopes: **study unit, topic, chapter, discipline, whole
bank.** No scope carries a required total. The report states the actual number.

### Yield is never reported alone

Every `SAFE_YIELD` figure is published with its companions, so a reader cannot mistake a count for a
verdict:

```
attempted_opportunities, accepted (= SAFE_YIELD), fail_closed, rejected,
redundant, no_safe_item, coverage_achieved, remaining_high_priority_gaps
```

`SAFE_YIELD_RATE = accepted / attempted` is a **diagnostic, never an objective.** It must not be
optimised, because the cheapest way to raise it is to attempt only easy opportunities. Two guards:
it is reported per priority class rather than in aggregate, and a **rising rate alongside rising
uncovered CORE decisions is a defined alarm** (§22).

---

## 18. Phase 4 — the question-opportunity model

Fixed question slots are replaced by opportunities. An opportunity is a *meaningful educational
decision*, and it exists because a physician makes that decision — never because a budget has room.

### Identity

```
OPPORTUNITY_ID = deterministic_hash(
    anchor_study_unit_id,       // frozen allocation address
    learner_decision_id,        // from the address's frozen declared_learner_decisions[]
    physician_activity,         // one of the four PHYSICIAN_ACTIVITIES (common core, §3.2)
    item_archetype,             // profile-permitted (§5)
    option_set_archetype,       // profile-permitted (§6)
    discipline_profile_id )
```

Carried alongside, not in the identity: `educational_purpose` (what the candidate can do afterwards
that they could not before), `priority_class` inherited from the address, and — populated at
`EVIDENCE_READY` — `decisive_discriminator`, which §19 compares against.

### Existence rule

An opportunity may be opened **iff** both hold:

1. It names a learner decision drawn from the address's frozen `declared_learner_decisions[]` — a
   decision a physician actually makes at this study unit, enumerated **before** generation.
2. That decision is not already covered by an `ACCEPTED` item, or, if it is, the new candidate is
   `NOVEL` on some §19 axis.

A single study unit legitimately exposes several opportunities: diagnosis and initial investigation
and disposition are three different decisions, not three phrasings of one. What it may not expose is
a second opportunity whose only distinguishing feature is that the budget has room.

**Budget:** opportunities opened against an address may not exceed its `opportunity_budget`.
**Falling short of the budget is not a defect, is never reported as one, and no report displays the
difference.**

### Lifecycle

| State | Entered when | Exits to |
| --- | --- | --- |
| `CANDIDATE` | opportunity opened; passes the existence rule and the pre-generation §19 screen | `EVIDENCE_READY`, `REDUNDANT`, `NO_SAFE_ITEM` |
| `EVIDENCE_READY` | required source packets READY; every cited claim adjudicated (§4); `decisive_discriminator` declared and evidence-grounded | `CONTRAST_READY`, `NO_SAFE_ITEM` |
| `CONTRAST_READY` | ≥ 3 competitors survive profile-aware retrieval and ADM-1/ADM-3 against the realised scenario (§7) | `GENERATABLE`, `NO_SAFE_ITEM` |
| `GENERATABLE` | option-set archetype coherent; axes bound; all pre-wording gates pass | `ACCEPTED`, `REJECTED`, `NO_SAFE_ITEM` |
| `ACCEPTED` | all five §17 conditions hold | terminal |
| `REJECTED` | independent verification fails, or a post-wording gate fails | terminal for this wave |
| `NO_SAFE_ITEM` | fail-closed at any stage, with a §21 reason | terminal for this wave; reopenable only on new input |
| `REDUNDANT` | §19 finds no materially new educational value | terminal |

### Anti-thrash rule

`NO_SAFE_ITEM` is reopenable **only on a new input** — a new source packet, a resolved Level 3
adjudication, a new profile vocabulary entry, or new admissible seeds. It is **never** reopenable by
re-running the same inputs.

Regeneration budget: **at most one** retry per opportunity, and only when the recorded failure is
**realisation-level** (ADM-5 format parity, or wording that a deterministic check rejected).
Evidence-level, fact-level, admissibility-level and ambiguity-level failures fail closed on first
occurrence with no retry. Under quota semantics the incentive ran the other way, and repeated
regeneration to fill a slot is exactly the behaviour this rule removes.

---

## 19. Phase 5 — marginal educational value

Additional questions on a topic require **materially new educational value**. The gate runs twice:
once before generation, against the opportunity tuple (so a redundant candidate costs nothing), and
once after, against the realised item.

A candidate is admitted only if it is novel on at least one axis **against every `ACCEPTED` item in
the same topic**:

| Verdict | Definition |
| --- | --- |
| `NOVEL_DECISION` | A different `PRIMARY_LEARNER_DECISION` — a different action, at a different point in care |
| `NOVEL_REASONING` | Same decision, materially different reasoning chain: a **different `decisive_discriminator`** reached by a different evidence path. A different route to the same discriminator is not novel |
| `NOVEL_CONTRAST` | The admissible competitor set differs by ≥ 2 of 3 competitors **by concept id**, *and* the newly introduced competitors change which discrimination the item tests. Swapping one competitor for a synonym of it is not novel |
| `NOVEL_CONTEXT_WITH_REAL_PEDAGOGIC_VALUE` | The strictest axis, and the one that must be defended explicitly: **the context change alters the correct answer or the reasoning required.** Qualifying: pregnancy changing the admissible agent; an age band changing the differential or the dosing rule; renal impairment changing the drug; a jurisdiction changing the legal duty. **Not qualifying:** name, sex where sex is not decision-relevant, an age inside the same band, city, occupation where not decision-relevant, presenting-complaint wording, reordered vitals |
| `REDUNDANT` | None of the above |

**A demographic change is not educational novelty.** This is stated as a checkable rule with the
qualifying and non-qualifying lists above, rather than as an aspiration, because it is the single
easiest way to manufacture apparent coverage.

### Where the comparison is made — and where it is not

Pre-generation: over `(learner_decision_id, physician_activity, decisive_discriminator,
option_set_archetype, competitor_concept_ids)`. Deterministic on four of five fields.

Post-generation: the existing common-core `semantic_fingerprint` (§3 item 11) plus a **role-blind**
novelty adjudication over `(learner_decision, decisive_discriminator, competitor_concept_ids,
management_rule)`.

The comparison is deliberately **not** made over vignette prose. Prose similarity is exactly the
signal that demographic rewording defeats, and a generator asked to judge its own item's novelty
over its own prose is Finding 2 repeating in a third gate family. The adjudicator sees the structured
tuple and the tuples of the accepted items, and does not see which one it is being asked to admit.

Stopping follows from this: once new candidates on a topic repeat the same learner decision, the
same decisive discriminator, the same reasoning chain, the same contrast set, the same management
rule, or differ only cosmetically in the vignette, they are `REDUNDANT` and the topic stops (§23).

---

## 20. Phase 6 — flexible volume

The assumption that each major discipline requires approximately 1,000 questions is **removed**. It
was an allocation-arithmetic consequence, never a curricular finding.

Per-discipline totals become **natural variable yield with no floor**. The frozen density plan shows
how uneven the underlying material already is: MED holds 515 non-zero addresses against PHELO's 64,
while both were allocated 1,000-1,086 slots. The slots were levelled; the material is not.

Illustrative shapes a chapter or topic group may legitimately produce:

- a few questions;
- 10-20 questions;
- 20-30 questions;
- up to approximately 50 where genuinely justified.

**These are illustrations of observed shape. They are not quotas, not tiers, and not thresholds. 50
is not a new minimum and not a target.** Any implementation that stores these numbers as
configuration values violates this amendment. The correct number for any unit is:

> **the number of distinct high-quality questions the material safely supports.**

Structural guard: the coverage report (§22) has **no target column, no percent-of-target, and no
under-target flag**. There is nothing in the reporting surface to fill.

---

## 21. Phase 7 — fail-closed generation as a product principle

> **NO QUESTION IS BETTER THAN A WEAK QUESTION.**

This is promoted from an engineering behaviour to a stated product principle. Generation fails closed
whenever any of the following holds, and each maps to an existing gate rather than a new one:

| Reason | Gate that raises it | Reopenable on |
| --- | --- | --- |
| `FAIL_CLOSED_INSUFFICIENT_EVIDENCE` | evidence packet holds no claim for the decisive discriminator | a new source packet |
| `FAIL_CLOSED_UNRESOLVED_CRITICAL_FACT` | §4.4 status `UNRESOLVED` | a completed Level 3 adjudication |
| `FAIL_CLOSED_ERRONEOUS_SOURCE_FACT` | §4.4 `ADJUDICATED_SOURCE_ERRONEOUS` on a load-bearing value | a corrected or superseding source |
| `FAIL_CLOSED_INSUFFICIENT_ADMISSIBLE_COMPETITORS` | fewer than three competitors survive ADM-1/ADM-3 | new seeds, or a profile vocabulary entry |
| `FAIL_CLOSED_INCOHERENT_OPTION_SET_ARCHETYPE` | no archetype expresses the demanded response class | an authorised profile extension |
| `FAIL_CLOSED_ANSWER_AMBIGUITY` | single-best-answer or blind-solver failure | **never by retry** |
| `FAIL_CLOSED_REDUNDANT` | §19 | a different opportunity |
| `FAIL_CLOSED_UNINSTANTIABLE_REASONING` | the intended reasoning cannot be posed naturally — the PSY-I02(b) mode, where every stem feature points one way and the item degenerates to recognition | a rescoped opportunity |

Every fail-closed writes a record carrying the reason, the opportunity id, the stage, and the input
that would reopen it. **The fail-closed count is a first-class reported quantity and never a penalty
on the wave.**

The accounting consequence, stated plainly because it inverts the previous incentive:

> A wave with a high fail-closed count and complete CORE decision coverage is a **success**.
> A wave with a low fail-closed count and uncovered CORE decisions is **not**.

Counterweight, so that failing everything closed cannot pass a gate trivially: `SAFE_YIELD = 0` at
any gate in §24 is a failure regardless of how well-reasoned the fail-closed records are, and
`FAIL_CLOSED_CONCENTRATION` — more than 60 % of a wave's fail-closed outcomes in one reason class —
is an alarm requiring the responsible gate to be examined before the wave proceeds. A gate that
rejects everything is as uninformative as one that accepts everything; that is Finding 1 read in the
other direction.

---

## 22. Phase 8 — coverage and gap reporting

A smaller bank still needs defensible scope. Proposed artifact:
`reports/qbank_coverage_and_yield.json` (created by a later authorised task, not here).

One row per `(mcc_objective_id × allocation_address_id)`:

```
{ mcc_objective_id, allocation_address_id, study_unit_id, discipline, chapter,
  priority_class, priority_class_basis,
  opportunities_opened, opportunity_state_counts{},
  accepted_count,                       // SAFE_YIELD at this address
  covered_learner_decisions[],
  uncovered_learner_decisions[],
  no_safe_item_gaps[],                  // { learner_decision_id, reason, reopens_on }
  evidence_gaps[],                      // { decision, missing_claim_class, packet_id }
  contrast_gaps[],                      // { decision, admissible_competitors_found }
  diagnosis, wave_id }
```

Rollups at topic, chapter, discipline and bank level carry the §17 companion set.

### The diagnosis, and why it does not read the count

The report's purpose is to separate two situations that look identical if you only look at a number:

| Diagnosis | Condition |
| --- | --- |
| `NARROW_TOPIC` | Every declared learner decision is in `covered_learner_decisions`; `no_safe_item_gaps`, `evidence_gaps` and `contrast_gaps` are all empty. **The low count is correct** |
| `PIPELINE_GAP` | Any of: a CORE objective with `accepted_count` 0; a non-empty `uncovered_learner_decisions` at CORE; any outstanding `no_safe_item_gaps`, `evidence_gaps` or `contrast_gaps` |

`accepted_count` is **not an input to the diagnosis** except in the single CORE-zero case, where it
is used as a presence test rather than as a magnitude. Two units with one accepted item each receive
different diagnoses if one has covered its only decision and the other has three uncovered ones.
That separation is the whole point of the report, and it is why §16's frozen
`declared_learner_decisions[]` must be authored before generation: if the decision list were derived
from what was generated, `uncovered_learner_decisions` would be empty by construction and every unit
would read `NARROW_TOPIC`.

### Standing alarms

- A CORE MCC objective with zero accepted items across the whole bank.
- An uncovered high-priority learner decision at a CORE address.
- A `NO_SAFE_ITEM` outstanding across more than one wave without its reopening input being pursued.
- `SAFE_YIELD_RATE` rising while uncovered CORE decisions rise — the easy-questions-only signature.
- `FAIL_CLOSED_CONCENTRATION` above 60 % in one reason class.

---

## 23. Phase 9 — production stop rules

Generation on a topic stops when **any** of these fires. Each is checkable, and none refers to a
count target.

| Rule | Condition |
| --- | --- |
| **STOP-1** decision coverage | Every high-priority learner decision at the unit is `ACCEPTED` or carries a `NO_SAFE_ITEM` with a reason |
| **STOP-2** redundancy | The next *k* consecutive candidates score `REDUNDANT` at the pre-generation screen. Default *k* = 2, revisited after G2 |
| **STOP-3** competitor exhaustion | Fewer than three competitors survive ADM-1/ADM-3 for the remaining opportunities — the declining-competitor-quality signal |
| **STOP-4** evidence cost | A remaining opportunity would require a new source packet or a fresh Level 2/3 adjudication whose only consumer is a `SUPPORTING` item |
| **STOP-5** marginal value | Remaining candidates are novel only on `NOVEL_CONTEXT` and the context change does not alter the answer or the reasoning |
| **STOP-6** budget | Opportunities opened equals `opportunity_budget` |

**Anti-rule, stated because it is the specific behaviour being retired:** unused allocation slots are
**not** a reason to continue. STOP-1 satisfied together with STOP-2 or STOP-5 is a complete and
successful stop even at one accepted item against a budget of thirty.

---

## 24. Phase 10 — safe scale gates, restated

Supersedes §9's G1-G4. The five invariants are carried forward **unchanged and unconditional**, and
apply at every priority class:

```
FACTUAL_ERRORS         = 0
NUMERIC_ERRORS         = 0
UNSUPPORTED_CLAIMS     = 0
AMBIGUOUS_BEST_ANSWERS = 0
EVIDENCE_ENTAILMENT    = PASS
```

Gates now evaluate **quality, safety, coverage, yield and redundancy**. A production wave does
**not** succeed by generating every planned opportunity, and does not fail by failing many closed.

| Gate | Scope | Criteria |
| --- | --- | --- |
| **G0 — retrospective replay** | Stage 15 replayed over the frozen R4 artifact | **Unchanged from §9.** Must reject ≥ 7 of the 8 failed items and accept ≥ 6 of the 7 passed items; any rejection of a passing item individually justified. It is a separation test over a fixed frozen cohort and never involved a count target, so Part II leaves it alone. It remains the falsification test |
| **G1 — profile micro pilot** | 3 CORE opportunities, one discipline | Invariants hold on accepted items; `SAFE_YIELD ≥ 1`; every non-accepted opportunity carries a valid §21 reason confirmed by a reviewer; every accepted item covers its declared learner decision; `LONE_KEY_OPTION_CATEGORY` = 0; **no gate family returns a constant verdict** |
| **G2 — profile pilot** | 10 CORE/IMPORTANT opportunities, one discipline, ≥ 3 archetypes | Invariants hold; among **accepted** items `WEAK_DISTRACTOR` ≤ 1 and `OPTION_CUE_FAILURE` ≤ 1; every CORE decision attempted is covered or carries `NO_SAFE_ITEM` with a reason; `FAIL_CLOSED_CONCENTRATION` below 60 %; **redundancy positive control**: a deliberately redundant probe candidate is injected and §19 must reject it |
| **G3 — cross-profile generalisation** | 6 disciplines × 3 CORE opportunities, **MED included** | Invariants hold; accepted-item defect rates within G2 bounds; `LONE_KEY_OPTION_CATEGORY` = 0 and `SEVERITY_OR_CATEGORY_MISMATCH` = 0 across accepted items; **no discipline with zero accepted items**; fresh reviewer with no access to the construction record; verdict-variance monitoring; redundancy positive control fires |
| **G4 — first production wave** | The first **chapter-scoped** wave: every CORE opportunity in one chapter driven to a terminal state | Invariants hold on an audited sample of 20 accepted items, or on all accepted items if fewer than 20; defect rates within G3 bounds; the coverage report shows every CORE learner decision either `ACCEPTED` or `NO_SAFE_ITEM`-with-reason; **no slot-fill requirement**; explicit user authorisation |

### What changed, and in which direction

The §9 ratios (`≥ 8/10`, `≥ 15/18`, `no discipline below 2/3`, `fail-closed ≤ 20 %`) are removed.
They are not loosened into weaker ratios; they are replaced, for two reasons. First, their
denominator is now legitimately variable, because a correct fail-closed is a success and a quota no
longer guarantees the attempt count. Second,
`reports/qgen_reviewer_calibration_v2.json` already establishes that raw pass rates across waves are
not comparable and that **defect counts, not pass rates, are the comparable quantity** — the §9
ratios were in tension with the project's own calibration rule before this amendment.

What replaces them is stricter on the axis that matters: the two dominant R4 failure modes must be at
**zero** across accepted items at G3, not merely below a rate; every non-accepted opportunity must
carry a defensible reason, so a wave cannot pass by quietly abandoning hard items; and the
redundancy detector must be shown to fire against a positive control, so §19 cannot become the next
constant-`PASS` gate.

### Reported per wave

```
attempted_opportunities   accepted (SAFE_YIELD)      fail_closed_count by reason
rejected_count            redundant_count            coverage_achieved
remaining_high_priority_gaps
```

Two standing requirements from §9 carry forward: **verdict-variance monitoring** (any gate family
returning a single distinct verdict across a whole pilot is reported `GATE_UNINFORMATIVE` and blocks
the gate regardless of pass rate) and **fresh reviewers** at G1-G3 under
`qgen_reviewer_calibration_v2`.

---

## 25. Phase 11 — token and cost consequences

Directional analysis only. No multiplier is claimed: the accepted-per-attempted rate under the
proposed pipeline is unmeasured, and R4's 7/15 fresh-verification pass came from a pipeline with no
pre-generation screens at all, so it is not the same quantity.

### Downward pressure

- **Source-packet research is the dominant cost centre and benefits most.** 1,434 of 1,524 planned
  packets are still `PENDING`. Under quota semantics that queue must be worked to completion because
  every allocated slot eventually needs its packet. Under coverage-first priority the queue is
  worked CORE-first, and STOP-4 withdraws new packet research from `SUPPORTING` addresses entirely.
  This is very likely the **largest single cost effect of the amendment**, and it is larger than
  anything at the per-item level.
- **Pre-generation screening kills candidates before any large call.** The §19 novelty screen and the
  archetype/admissibility screens run on structured tuples. Under quota semantics the same candidate
  was generated, verified, rejected, and often regenerated.
- **The one-retry rule replaces open-ended regeneration.** Repeated regeneration existed to fill a
  slot; there is no slot to fill.
- **Fewer competitor searches and fewer contrastive-evidence builds**, because retrieval runs only
  for opportunities that already passed the novelty and archetype screens.
- **Fail-closed avoids the whole downstream chain** — realisation, rationale, and independent
  verification — for items that would have been rejected anyway. Independent verification is a
  high-reasoning call and the most expensive per-item stage, so failures moved earlier are the ones
  that save the most.
- **Fewer Level 2 retrievals**, since claims are escalated only for opportunities that reach
  `EVIDENCE_READY`.

### Upward or neutral pressure

- The §19 novelty adjudication adds one small role-blind call per candidate. Bounded by
  `opportunity_budget` above and by STOP-2 firing after two consecutive redundant candidates.
- Coverage and gap reporting is deterministic and negligible.
- A fail-closed item still costs everything spent up to its failure point. A failure at independent
  verification saves nothing — which is the argument for the pre-generation screens carrying the
  weight, and against adding more post-hoc gates.
- **Claim-level amortisation weakens slightly as the bank shrinks.** §4 amortised critical-fact
  adjudication roughly 7:1 at R4 density (106 claims serving 15 items). Fewer items per claim means
  less amortisation per item. The effect is second-order — the number of `CRITICAL` claims falls
  alongside the number of items, since unattempted opportunities pull no claims — but it is the one
  place the amendment pushes cost the wrong way, and it is recorded rather than omitted.

### Net

Total cost **LOWER**, and cost **per accepted item** materially lower, on top of the §10 per-item
reduction (~15 calls to ~7 large + 5 small). The bank is smaller and its average quality is higher.
The saving comes from attempting fewer items and from failing earlier, not from checking less.

---

## 26. Phase 12 — the consolidated architecture

The final architecture is:

```
COMMON CORE
  + DISCIPLINE PROFILES
  + OPTION SET ARCHETYPES
  + GLOBAL CRITICAL FACT ADJUDICATION
  + PROFILE-AWARE CONTRAST RETRIEVAL
  + COVERAGE-FIRST SAFE-YIELD GENERATION
```

**A fixed output of 6,086 questions is retired as a mandatory production goal.** The 6,086 allocation
is preserved unchanged as a historical curriculum-density plan (§15).

The per-item pipeline of §8 is **unchanged at 21 stages**. Part II adds no per-item stage. What it
adds is a planning front end and a reporting back end around that pipeline:

```
FROZEN ALLOCATION                       (historical density plan, immutable)
  -> PRIORITY CLASS DERIVATION          (deterministic; + reachability promotion, §16)
  -> QUESTION OPPORTUNITY ENUMERATION   (bounded above by opportunity_budget, §18)
  -> MARGINAL EDUCATIONAL VALUE SCREEN  (pre-generation, §19)
  -> [ §8 per-item pipeline, stages 1..21, unchanged ]
  -> OPPORTUNITY STATE WRITE-BACK       (§18 lifecycle)
  -> COVERAGE AND YIELD REPORT          (§22)
  -> STOP RULE EVALUATION               (§23)
```

Everything the frozen allocation, the ownership decisions, the discipline routing and the
question-bank targets already decided is read, never rewritten.

---

## 27. Phase 14 — amendment self-review

1. **Has 6,086 been replaced by another quota?** No target replaces it. `opportunity_budget` is
   upper-bound-only; the schema forbids minimum-, target- and shortfall-shaped fields; the coverage
   report has no target column and no percent-of-target; §20's illustrative ranges are explicitly
   barred from becoming configuration values. **Residual risk:** `opportunity_budget` is derived from
   `final_question_count`, so the retired quota is one careless rename away from returning as a
   floor — hence the field should be named `maximum_opportunities` and a validator should assert the
   absence of any minimum-shaped field. A second, non-technical residual risk: a reviewer who sees
   3,339 CORE slots against 200 accepted items may re-impose the quota socially even though no
   artifact does.
2. **Can coverage holes hide behind low counts?** Addressed by §22's count-independent diagnosis and
   by §16's reachability promotion, which closed a real hole — 16 MCC objectives had no CORE address
   and 3 were reachable only through `SUPPORTING`. **Residual risk, and the most load-bearing one in
   this amendment:** the diagnosis depends on `uncovered_learner_decisions` being enumerated
   honestly. If the enumerator lists only decisions it already generated for, the list is empty by
   construction and every unit reads `NARROW_TOPIC`. `declared_learner_decisions[]` must therefore be
   authored from the study unit and its MCC objectives **before** generation and frozen — the same
   independence lesson as Findings 1 and 2, applied to the coverage layer. Who authors it and when is
   an open question (§28).
3. **Does this incentivise generating only easy questions?** It is a real risk: `SAFE_YIELD` rewards
   accepted items, and easy items are likelier to be accepted. Countermeasures: CORE-first ordering,
   so hard opportunities are attempted first rather than deferred; `SAFE_YIELD_RATE` designated a
   diagnostic and explicitly not an objective; the standing alarm on a rising rate with rising CORE
   gaps; and G1-G4 success defined on coverage rather than yield. **Residual risk:** none of these
   stops an operator choosing easy chapters. Only the CORE coverage report makes that visible, and
   only if someone reads it.
4. **Can repeated questions be counted as coverage?** No. `REDUNDANT` items are excluded from
   `SAFE_YIELD`, and coverage is credited **per learner decision**, not per item — five items on one
   decision cover one decision. **Residual risk:** the decisive-discriminator comparison is a
   semantic judgement, and if the generating agent makes it about its own item, that is Finding 2 in
   a third gate family. §19 requires it to be role-blind; implementation must honour that or the
   whole gate is decorative.
5. **Does this put unsafe pressure on CORE topics?** No. CORE means *serious attempt*, never *must
   produce*. `NO_SAFE_ITEM_YET` is an accepted terminal state at every class including CORE, is not a
   defect, and no gate in §24 penalises it. The five invariants are unconditional and
   class-independent. **Residual risk:** a CORE objective that repeatedly yields `NO_SAFE_ITEM` is a
   genuine product gap even though the pipeline behaved correctly. §22 surfaces it; resolving it is a
   research decision about sources, not a generation decision, and this design deliberately does not
   let generation resolve it.
6. **Is allocation confused with final production count?** Two artifacts, differently named, with
   different semantics, and the generation layer never writes the frozen one. **Residual risk:**
   `AGENTS.md` still states 6,086 as a production commitment, so until it is amended under separate
   authorisation the repository holds two readings. Flagged in §15 and §28 rather than fixed
   unilaterally.
7. **Is this excessively complex?** The per-item pipeline is untouched at 21 stages. Part II adds one
   derived planning artifact, one report, one pre-generation screen, six stop rules and an
   eight-state lifecycle. **Residual risk:** the lifecycle's eight states sit alongside the
   manifest's own eight `generation_status_values`. If the implementation stores lifecycle state per
   item rather than per opportunity they will drift apart. They should be reconciled into one state
   machine, not duplicated — §28.
8. **How does token cost scale?** §25: down overall and down per accepted item, dominated by the
   source-packet queue being worked CORE-first. **Residual risk:** the novelty screen costs one small
   call per candidate including rejected ones, so a topic whose candidates are mostly redundant pays
   repeatedly; bounded by `opportunity_budget` and by STOP-2. And claim-level fact amortisation
   weakens as the bank shrinks (§25).

**What would falsify Part II.** G0 remains the falsification test for the option-set design. For the
coverage layer the test is §22: if the report returns `NARROW_TOPIC` for a study unit that a
reviewer judges to have an uncovered important learner decision, the diagnosis is not doing its job
and the priority model, not the reviewer, is wrong. That check should be run over the R4 targets'
own study units before G1.

---

## 28. Amended open questions

Carrying forward §13 items 1-5 unchanged, and adding:

6. Who authors and freezes the per-address `declared_learner_decisions[]` that coverage is credited
   against, at what point, and under what review? This is the input the whole coverage layer rests on
   (§27 item 2).
7. How do the eight opportunity lifecycle states reconcile with the manifest's eight existing
   `generation_status_values`? One state machine or two, and which artifact owns it?
8. Does `AGENTS.md` § *Allocation rules* get amended to state the density reading, and under what
   authorisation?
9. Is STOP-2's *k* = 2 right? It cannot be calibrated before a wave exists; the default should be
   revisited at G2 against observed redundancy runs.
10. Does the reachability promotion need re-running whenever the MCC objective mapping changes, and
    is that mapping frozen for the life of the bank?
