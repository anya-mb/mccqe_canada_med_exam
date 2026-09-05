# Contrast-first, difficulty-aware item construction

Design checkpoint for a change to **generation order**, not to any safety gate.

- Status: DESIGN — approved for an isolated pilot module only.
- Supersedes nothing. Replaces no production generator.
- Starting commit: `74d6ed0`.
- Preceding decision: `RETRIEVAL_ARCHITECTURE_DECISION = RETRIEVAL_NOT_MAIN_PROBLEM`
  (`reports/qgen_clinical_retrieval_benchmark.json`).

---

## 0. Why the order is being changed

The frozen four-arm benchmark over the same 30 G2 opportunities is unambiguous.

| arm | opportunities reaching 3 viable competitors | anchor-floor refusals | recall |
|---|---|---|---|
| CURRENT_LIBRARY | 10 / 30 | 67 | 0.4935 |
| BM25 | 0 / 30 | 0 | 0.0 |
| GRAPH | 10 / 30 | 0 | 0.4935 |
| HYBRID | 10 / 30 | 67 | 0.4935 |

`NOT_RETRIEVED_AT_ALL = 0`. Nothing is missed. Every apparent recall gap was a
competitor that retrieval *did* return and a filter then refused. The residual
20 failures classify as `STEM_ANCHOR_FLOOR` 15, `ARCHETYPE_FILTER` 3,
`LEARNER_DECISION_FILTER` 2, with `NO_RELEVANT_SOURCE_CONCEPT`,
`NORMALIZATION_MISS`, `BM25_RECALL_MISS`, `GRAPH_CONNECTIVITY_MISS`,
`GRANULARITY_FILTER`, `SECOND_KEY_CEILING` and `EVIDENCE_LIMITATION` all zero.

So 15 of 20 failures are one thing: **the stem was already frozen when the
competitor arrived, and the stem states nothing that gives a candidate a reason
to consider that competitor.** A better retriever cannot undo that, because the
refusal is correct. The competitor genuinely is not live *in that stem*.

The current order is:

```
LEARNER DECISION -> STEM + KEY -> RETRIEVE COMPETITORS -> FILTER AGAINST FROZEN STEM
```

The stem is authored against the key alone. Whether it happens to contain the
findings that make a legitimate competing diagnosis or action live is left to
chance. `STEM_ANCHOR_SURVIVAL_mean = 0.4253` measures that chance.

The hypothesis under test is that the anchor floor is not a supply problem at
all but an **ordering** problem, and that it disappears — without being weakened
— if the contrast set is established first and the stem is designed to be a
clinically coherent presentation *in which those competitors are genuinely live*.

### 0.1 What this design explicitly does not claim

It does not claim that a stem may be bent around distractors. Section 8 is the
gate that refuses exactly that, and it is the single largest risk this design
carries.

It does not claim to fix the other five failures. `ARCHETYPE_FILTER` (3) is a
seed-coverage gap that reaches `indexed_count = 0`; no ordering change creates a
seed that does not exist. `LEARNER_DECISION_FILTER` (2) is a semantic refusal
that operates identically in either order. Those five are expected to fail again,
and the pilot is designed so that they can.

It does not claim the graph solves supply. Section 9 states its actual role.

---

## 1. What exactly moves before stem construction

Five things move upstream. Nothing else moves.

| # | Stage | Was | Becomes |
|---|---|---|---|
| 1 | Key decision | before stem | unchanged, before stem |
| 2 | Contrast candidate discovery | after stem | **before stem** |
| 3 | Pre-stem contrast admission (P1–P6) | after stem, as retrieval filters | **before stem, as an admission predicate** |
| 4 | Contrast matrix | did not exist | **new, before stem** |
| 5 | Stem blueprint (feature-set solve) | did not exist | **new, before stem** |

Stage 3 is the subtle one and must not be misread. The pre-stem admission
predicate is **not** the post-stem gate moved earlier. It is the subset of
admission conditions that are stem-independent — response class, option-set
archetype, decision granularity, learner-decision dimension, evidence support,
independent seed review. The two stem-*dependent* gates, `SAF_1` (anchor floor)
and `ADM_3` (second-key ceiling), cannot be evaluated before a stem exists and
are **not** moved. They run afterwards, unchanged, in Phase 11.

## 2. What remains after stem construction

Everything that decides whether an item is safe.

1. Blind open-ended solve on the frozen stem alone (§10).
2. **Post-stem contrast revalidation through the unchanged production
   function** `profile_contrast_retrieval.retrieve_profile_aware_contrasts` —
   `ADM_1`, `ADM_3`, `SAF_1`, `MINIMUM_ADMISSIBLE_COMPETITORS = 3`.
3. Semantic contrast admissibility (same decision, same option-set archetype,
   granularity parity).
4. Option realization under `option_set_admissibility`.
5. Rationale generation.
6. Critical-fact adjudication, evidence entailment, numeric/unit validation.
7. Independent verification by a context that did not author the item.
8. Difficulty structural review through the already-implemented
   `question_difficulty` checks.
9. Copyright / leak audit.

The load-bearing property of this design is that **step 2 calls the same
function the benchmark's arm A called, on the same code path, with the same
constants.** If contrast-first improves post-stem survival, it improves it
against an unmoved bar. No gate is relaxed, reordered, or given a pilot variant.

## 3. How a contrast set is selected

A `CONTRAST_SET` is built for one opportunity, before any stem exists:

```
key concept / action
learner decision, discipline profile
item archetype, option-set archetype, decision granularity
difficulty intent
3-6 candidate competitors, each with evidence/provenance
```

Candidates are unioned from three sources in a fixed order, and the source of
each is recorded:

1. **CURATED_LIBRARY** — seeds already independently reviewed for the target in
   the frozen contrast seed packs. This is the first source, deliberately: the
   curated library is not discarded (Phase 19).
2. **GRAPH** — typed traversal seeded at the **key concept node**, not at a stem
   (there is no stem). `CONFUSED_WITH` at depth 1–2 yields candidate
   competitors; inverted `PLAUSIBILITY_ANCHOR` yields, for each candidate, the
   stem features that would make it live. See §9.
3. **TARGETED_RESEARCH** — at most **one** bounded pass per opportunity, and only
   where fewer than three candidates survive P1–P6 from sources 1 and 2. Every
   competitor so acquired takes an independent seed review before use. No
   enrichment loops (Phase 20).

Every candidate must satisfy the pre-stem admission predicate:

| id | predicate | refusal code |
|---|---|---|
| P1 | same learner-decision dimension as the key | `PRE_STEM_LEARNER_DECISION_MISMATCH` |
| P2 | response-class closure contains the demanded class | `PRE_STEM_RESPONSE_CLASS_MISMATCH` |
| P3 | option-set archetype and item archetype both applicable | `PRE_STEM_ARCHETYPE_MISMATCH` |
| P4 | decision granularity equal to the key's | `PRE_STEM_GRANULARITY_MISMATCH` |
| P5 | MCC-level relevance, and an independent seed review verdict of PASS | `PRE_STEM_REVIEW_ABSENT` |
| P6 | at least one evidence reference for plausibility and one for discrimination | `PRE_STEM_EVIDENCE_ABSENT` |

P1–P6 are exactly the stem-independent conditions the current pipeline already
applies. Nothing new is admitted by them; they are applied earlier.

A set with fewer than 3 or more than 6 surviving candidates fails closed
(`FAIL_CLOSED_CONTRAST_SET_SIZE`). No stem is written.

## 4. Preventing a stem reverse-engineered around distractors

This is the risk the design exists to contain, and it is contained structurally
rather than by exhortation.

**R1 — the author cannot invent findings.** Every feature a blueprint may
require is drawn from the **frozen canonical stem-feature vocabulary** of the
opportunity's anchor study unit (`g2_stem_feature_vocabulary.json`: 102
features, 6 units, frozen with a SHA-256 before this task). The stem author
selects from a closed list authored for the study unit, never for the item. A
blueprint naming a feature outside the vocabulary is refused.

**R2 — negative findings are capped and may never be the whole discriminator.**
`CO-2`: at most one `ABSENT`-polarity feature may be required at EASY or MEDIUM,
and the HARD contract already forbids any competitor being defeated by an
explicit verbal denial (`competitors_defeated_by_explicit_verbal_denial` max 0).
`CO-3`: no competitor anywhere may be defeated *only* by an `ABSENT` feature.
This is the check that would have caught the real signal already on record —
G2-PHELO-01's three competitors are each defeated by an explicit denial.

**R3 — the differentiator list is bounded above, not only below.** `CO-4` caps
required features per difficulty level. Difficulty raises *what must be
integrated*, never *how much is stated*. An overloaded stem fails the cap.

**R4 — every required feature must be a datum a clinician would plausibly have.**
`CO-1` classifies each feature by its vocabulary `clinical_role`. Roles that are
routinely available at the point of care (`SYMPTOM`, `HISTORY`, `VITAL_SIGN`,
`EXAMINATION_FINDING`, `INVESTIGATION_RESULT`, `TIME_COURSE`, `AGE`,
`DEMOGRAPHIC`, `LONGITUDINAL_COURSE`, `STUDY_RESULT`, `STUDY_DESIGN`,
`PROGRAMME_DOCUMENT`, `PROGRAMME_OBJECTIVE`, `PROGRAMME_CAPACITY`,
`SYSTEM_CONSTRAINT`, `CLINICAL_JUDGEMENT`) pass. Roles that are available only
when someone went looking (`EXPLICIT_RISK_INVENTORY`, `COLLATERAL_SOURCE`,
`PATIENT_PREFERENCE`) require a stated clinical reason for being available in
this scenario, recorded in the blueprint and reviewable.

**R5 — the stem author is option-blind.** The blueprint hands the author feature
ids, normalized feature text and clinical roles. It does not hand over competitor
option strings. The author knows *which findings the scenario must contain*; the
author does not know *how the competitors will be worded*, so wording cannot be
optimized against literal option strings.

**R6 — the stem is frozen before options exist**, and after freezing no
modification is permitted for any reason, including to rescue a competitor that
the post-stem gates then refuse. A refused competitor is lost; the item fails
closed if fewer than three survive.

**R7 — an independent reviewer scores `UNNATURAL_STEM_ENGINEERING` explicitly**,
against the five failure descriptions in Phase 8 of the task, and any non-zero
count rejects the item.

## 5. Shared features versus defeating discriminators

The two relations are already separate in the frozen data and the design keeps
them separate.

- A **shared plausibility feature** is a stem feature that is a
  `PLAUSIBILITY_ANCHOR` of a competitor: its presence gives a reasoning
  candidate a positive reason to *consider* that competitor. It never makes the
  competitor correct.
- A **defeating discriminator** is a feature whose blueprint polarity leaves at
  least one of the competitor's `CORRECTNESS_CONDITIONS` unsatisfied while the
  key's own conditions are all satisfied.

A single feature may occupy both roles for the same competitor — in the frozen
PHELO data `SF-PH07-SURVIVAL-LONGER-IN-SCREENED` is both an R1-derived anchor of
lead-time bias and one of its correctness conditions — so the design does not
require the sets to be disjoint. It requires, per competitor, the conjunction:

```
FLOOR    at least one anchor of that competitor is PRESENT in the blueprint
CEILING  at least one correctness condition of that competitor is unsatisfied
```

Both are computed pre-stem as blueprint constraints and both are re-checked
post-stem by the unchanged production gates.

## 6. Preserving one-best-answer semantics

The blueprint must satisfy, simultaneously:

- `KEY_FULLY_SUPPORTED`: every correctness condition of the key is satisfied.
- `NO_SECOND_KEY`: for every competitor, at least one correctness condition is
  unsatisfied. This is `ADM_3` expressed as a constraint instead of a filter.
- `EVERY_COMPETITOR_LIVE`: for every competitor, at least one anchor is PRESENT.
  This is `SAF_1` expressed as a constraint instead of a filter.

A blueprint that cannot satisfy all three fails closed
(`FAIL_CLOSED_BLUEPRINT_UNSATISFIABLE`) and **no stem is written**. That is the
intended outcome when a contrast set is genuinely incoherent: the failure moves
earlier and costs less, rather than being discovered after a stem exists.

The ceiling is the constraint contrast-first makes *harder*, not easier. Adding
anchors so that every competitor is live pushes toward satisfying competitors'
correctness conditions. The design therefore predicts a trade: anchor-floor
failures should fall, and second-key refusals should be the pressure point. That
prediction is falsifiable and is measured (§12).

## 7. How difficulty intent is encoded

`DIFFICULTY_INTENT ∈ {EASY, MEDIUM, HARD}`, authored, never empirical. The
checks already exist and are **reused unmodified** from
`scripts/qbank/question_difficulty.py`:

| check | EASY | MEDIUM | HARD |
|---|---|---|---|
| `key_discriminator_count` | 1..1 | 1..2 | >= 2 |
| `load_bearing_stem_feature_count` | 1..2 | 2..3 | >= 3 |
| `live_competitors_after_floor` | >= 3 | >= 3 | >= 3 |
| `competitors_defeated_by_explicit_verbal_denial` | <= 1 | <= 1 | 0 |
| `mean_anchors_present_per_competitor` | >= 1.0 | >= 1.0 | >= 2.0 |

Contrast-first can *target* a level, which stem-first could not: the blueprint
solver chooses how many discriminators and how many anchors per competitor the
stem will carry. Difficulty is therefore a property of the contrast set and the
blueprint, decided before authoring.

Difficulty is manipulated only through `DISCRIMINATOR_SALIENCE`,
`NUMBER_OF_FEATURES_TO_INTEGRATE`, `COMPETITOR_SIMILARITY`,
`TEMPORAL_REASONING`, `SEVERITY_REASONING`, `SEQUENCING_DEMAND` and
`CONTEXTUAL_COMPLEXITY`. The nine `PROHIBITED_DIFFICULTY_SOURCES` remain refused
by the existing rationale screen, in either their named or euphemised form.

`competitor_similarity` is measured, not asserted: it is the mean of
`satisfied_conditions / total_conditions` over admitted competitors — how close
each competitor comes to being correct without being correct. That is the
honest operationalisation of "strongly plausible alternative".

EASY is subject to the extra audit in Phase 22 of the task and is the level most
at risk of becoming a bad item; the `live_competitors_after_floor >= 3` and
`mean_anchors_present_per_competitor >= 1.0` limbs are what stop EASY degrading
into a lone plausible option.

## 8. Clinical coherence gate

Applied to the blueprint before authoring, and to the frozen stem after.

| id | constraint |
|---|---|
| CO-1 | every required feature's `clinical_role` is routinely available, or carries a stated availability reason |
| CO-2 | required `ABSENT`-polarity features <= 1 (EASY, MEDIUM), and HARD admits no competitor defeated by verbal denial |
| CO-3 | no competitor is defeated only by an `ABSENT` feature |
| CO-4 | total required features within the level's cap (EASY <= 6, MEDIUM <= 8, HARD <= 11) |
| CO-5 | every required feature belongs to the anchor study unit's frozen vocabulary |
| CO-6 | the feature set contains no two features that are mutually contradictory |

CO-6 is enforced from declared contradiction pairs in the blueprint contract, not
inferred; a pair the pilot has not declared cannot be silently assumed
compatible, so the module refuses a blueprint that requires both members of a
declared pair.

The post-stem limb is human/reviewer judgement, scored as
`UNNATURAL_STEM_ENGINEERING` in independent review, and a non-zero score rejects.

## 9. How graph retrieval participates

The benchmark's honest finding is that the graph did **not** increase supply. It
did three other things: zero anchor-floor refusals against arm A's 67, retained
provenance, and reached arm A's sets by an independent path.

In contrast-first the graph is used **upstream only**, for two jobs the curated
library index cannot do without a stem:

1. **Contrast discovery from the key.** Traversal seeded at the key concept node
   over `CONFUSED_WITH` (and `BELONGS_TO` within the anchor study unit) yields
   candidate competitors before any stem exists. Arm C's traversal seeds at the
   stem's PRESENT features and is unusable here by construction.
2. **Competitor -> stem-feature relationship support.** `PLAUSIBILITY_ANCHOR`
   edges give, for each candidate competitor, the stem features that would make
   it live. This is precisely the input the blueprint solver needs, and it is the
   graph's real contribution to this architecture.

Every candidate reached by the graph is recorded with its edge path. Whether the
graph contributed a candidate or a relationship the curated library alone would
not have surfaced is measured, not assumed
(`GRAPH_UNIQUE_USEFUL_CONTRIBUTIONS`). A contribution of zero is a reportable
result, not a failure to be engineered away.

Toronto Notes edges remain `TOPIC_DISCOVERY_SOURCE` and may never justify a
clinical claim. No embeddings are added.

## 10. Blind solving

Before any option is realized, a context that has not seen the key, the contrast
matrix, the blueprint or the author's rationale receives **the frozen stem and
lead-in only** and returns: most likely answer or action, reasoning summary,
confidence, important alternatives, and any missing information.

- The intended key must be supported by the solver's answer or named as its
  leading alternative.
- If the solver converges on a different answer, the item fails closed
  (`FAIL_CLOSED_BLIND_SOLVE_DISAGREEMENT`) or returns to blueprint analysis.
  The stem is **not** silently patched.
- A solver naming a genuinely missing datum is a coherence finding against the
  blueprint, not a licence to add the datum after freezing.

## 11. Which existing safeguards remain unchanged

Unchanged, byte for byte, and none given a pilot variant:

`LIVE_BUT_INFERIOR` standard · `STEM_ANCHOR_FLOOR` (`SAF_1`) ·
`SECOND_KEY_CEILING` (`ADM_3`) · `MINIMUM_ADMISSIBLE_COMPETITORS = 3` ·
same-decision requirement · same-option-set-archetype requirement ·
decision-granularity parity · response-class closure (`ADM_1`) ·
critical-fact adjudication · evidence entailment · numeric and unit validation ·
independent blind solving · independent final verification · fail-closed
behaviour · the copyright and originality contract.

`profile_contrast_retrieval.py`, `safe_yield_wave.py`, `question_opportunity.py`,
`option_set_admissibility.py` and `question_difficulty.py` are **read, imported
and called** by the pilot module. None is edited. `profile_contrast_retrieval.py`
in particular must stay untouched because it *is* benchmark arm A.

## 12. Metrics, frozen before any outcome is examined

Per arm (STEM_FIRST archived, CONTRAST_FIRST new):

`OPPORTUNITIES_ATTEMPTED` · `PRE_STEM_VALID_CONTRAST_SET` ·
`POST_STEM_3_VIABLE` · `ITEMS_REALIZED` · `ACCEPTED` · `NO_SAFE_ITEM` ·
`REJECTED` · `STEM_ANCHOR_FLOOR_FAILURES` · `SECOND_KEY_FAILURES` ·
`ARCHETYPE_FAILURES` · `LEARNER_DECISION_FAILURES` ·
`OPTION_REALIZATION_FAILURES` · `EVIDENCE_FAILURES`.

Accepted-item safety, all of which must be **0**: `FACTUAL_ERRORS` ·
`NUMERIC_ERRORS` · `UNSUPPORTED_CLAIMS` · `AMBIGUOUS_BEST_ANSWERS` ·
`CRITICAL_FACT_SAFETY_FAILURES` · `MATERIAL_REDUNDANCY` ·
`COMPETITOR_WITHOUT_STEM_ANCHOR` · `SECOND_KEY_RISK` ·
`UNNATURAL_STEM_ENGINEERING`.

The comparison reports absolute and relative differences. "Materially improves"
is **not** defined after the fact; both differences are recorded and the verdict
states which criterion each limb met.

The stem-first baseline is **archived, not regenerated**: the same 30
opportunities already carry a frozen arm-A funnel and a frozen terminal state
(`reports/qgen_g2_stem_anchor_retest_execution.json`). Regenerating a baseline
after seeing contrast-first results would be the clearest possible way to
manufacture a favourable comparison, so it is forbidden.

## 13. Fail-closed states

| state | when |
|---|---|
| `FAIL_CLOSED_CONTRAST_SET_SIZE` | fewer than 3 or more than 6 candidates survive P1–P6 |
| `FAIL_CLOSED_COMPETITOR_NOT_CONSIDERABLE` | no answer to "why would a minimally competent candidate seriously consider this?" |
| `FAIL_CLOSED_BLUEPRINT_UNSATISFIABLE` | no feature set satisfies floor, ceiling and key support together |
| `FAIL_CLOSED_CLINICAL_COHERENCE` | a blueprint violates CO-1..CO-6 |
| `FAIL_CLOSED_DIFFICULTY_TARGET_NOT_MET` | the level's checks cannot be met from admissible competitors |
| `FAIL_CLOSED_BLIND_SOLVE_DISAGREEMENT` | the blind solver converges elsewhere |
| `FAIL_CLOSED_INSUFFICIENT_ADMISSIBLE_COMPETITORS` | fewer than 3 survive the unchanged post-stem gates |
| `FAIL_CLOSED_EVIDENCE` | a load-bearing relationship resolves to no admissible source |
| `CONTRAST_FIRST_FAILURE` | pilot-only label for a contrast-first attempt that produced no safe item |

Fail-closed is never repaired by weakening a gate, by re-authoring a stem after
freezing, or by substituting an easier opportunity. **No question is better than
a weak question.**

## 14. Source contract

Every load-bearing clinical relationship in a contrast matrix must resolve to an
existing evidence packet claim, a graph edge whose `authority_role` is
`CURRENT_CLINICAL_AUTHORITY`, or one bounded targeted research pass. LLM memory
is never sufficient. Toronto Notes supports topic, differential and contrast
*discovery* only; currentness-sensitive clinical claims require current
authoritative sources. Existing evidence is used where sufficient; broad research
is not performed.

## 15. Integration boundary

`CONTRAST_FIRST_PILOT` is an isolated module. It imports production code and
edits none of it. It writes only new artifacts under `research/qgen/` and
`reports/`, and overwrites no frozen G1/G2 artifact. `LLM_API_CALLS = 0`. After
the pilot the work **stops for user review**; production integration is a
separate, later decision.

## 16. Design self-review

Three weaknesses, stated rather than discovered later.

1. **The pilot cannot separate ordering from authoring.** The same party designs
   the contrast set and authors the stem. Independence is preserved where it
   matters most — blind solving and final verification are fresh contexts — but a
   fully blind authoring separation is not achievable in one pilot. The bounds
   that do hold are structural: the closed feature vocabulary (R1), the option-
   blind blueprint (R5), the freeze (R6), and the unchanged post-stem gates.

2. **The sample is small and confined.** Eighteen opportunities over six anchor
   study units, all within the frozen 30 whose baseline is archived. A result
   here is evidence about generation order in six well-characterised units. It is
   not evidence about the 1,487-unit curriculum, and the design forbids reading
   it that way.

3. **Contrast-first could succeed on supply and fail on coherence.** The failure
   mode this design is most likely to produce is a stem that satisfies every
   constraint and reads like an assembled checklist. §8 and the independent
   `UNNATURAL_STEM_ENGINEERING` score are the only defences, and one of them is
   a judgement. If accepted items pass every count and still read badly, the
   correct verdict is `CONTRAST_FIRST_UNSAFE`, not a lowered coherence bar.
