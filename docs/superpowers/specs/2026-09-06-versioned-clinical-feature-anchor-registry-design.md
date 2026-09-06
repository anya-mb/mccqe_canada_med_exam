# Versioned clinical feature and anchor-relation registry

Design, 2026-09-06. Starting commit `14f4508`. Diagnosis `317f965`.

## 1. What this is, and what it is not

This is a **shared-data-contract fix**. It does not redesign Clinical Contrast
Model V2, does not relax a gate, does not grow the frozen 102-feature stem-feature
vocabulary, does not expand the graph or the Toronto Notes index, and does not
introduce embeddings. It creates one versioned source of truth for clinical
feature identity and for plausibility-anchor relations, and makes the four
consumers that currently disagree read the same pinned snapshot of it.

Everything the V2 milestone decided about states, roles, Kleene logic, nested
correctness trees and `CS2-1..CS2-9` stands unchanged and is *imported* here, not
restated.

## 2. The defect, precisely

`reports/qgen_feature_anchor_contract_reconciliation.json` measures it.

The supply wave discovered fifteen candidates, independently reviewed all fifteen
and approved four. All four rest on supply rule S-4: an evidence-cited
plausibility anchor added to a candidate whose frozen anchor row equalled its own
correctness conditions. `G2-PED-01` then reached a stem, realized its blueprint
exactly, stayed post-stem coherent, and an independent review scored it **zero on
all eleven dimensions**.

`retrieve_profile_aware_contrasts` refused two of its three competitors under
`SAF_1 / STEM_PLAUSIBILITY_ANCHOR_ABSENT`.

`SAF_1` is not wrong. Its rule -- a competitor is admissible only if at least one
of its plausibility anchors is realized PRESENT -- was validated, and this design
does not touch it. What is wrong is *where its anchors come from*: the frozen
`*.stem_anchors.json` packs, which supply rule S-2 forbids the supply layer to
edit. Zero of the four approved anchors are in any pack. The knowledge exists in
V2's semantics and does not exist in production's.

The map also measures a second mismatch that had not been counted. Of the 87
features the frozen packs already use as anchors, **14 are `CLINICAL_JUDGEMENT`,
7 are `SYSTEM_CONSTRAINT` and 2 are `PROGRAMME_CAPACITY`** -- roles that type to
`BACKGROUND_CONTEXT` or `RESOURCE_AVAILABILITY` in `PATIENT_CLINICAL`, which are
outside `ANCHOR_CLASSES`. This is the pilot's already-recorded anchor-quality
finding (`SF-GS76-FEMALE-REPRODUCTIVE-AGE`, `SF-GS76-IMAGING-AVAILABLE-NOW`) with
a number on it. An anchor row is a bare feature id: it cannot state the role under
which it is an anchor, the state it requires, or the evidence that makes it one,
so no rule can see the problem.

## 3. Why a registry rather than a patch

Three repairs were considered.

1. **Append to the frozen packs.** Refused. It breaks the frozen-layer rule, moves
   `frozen_sha256` on artifacts the G2 wave, the retrieval benchmark and the
   contrast-first pilot are pinned to, and leaves the next supply wave with the
   same problem.
2. **Let the supply layer write a fourth pack.** Refused. It makes anchor supply
   unversioned and unreviewed, and gives generation an incentive to author an
   anchor whenever an item would benefit -- the exact abuse §15 forbids.
3. **A versioned registry with explicit snapshots.** Adopted.

## 4. Feature identity is not anchor identity

The single most important structural decision. A registered feature is a *thing
the vocabulary can say*. An anchor relation is a claim that, **for a named
learner decision, this feature PRESENT gives a candidate a reason to consider
that competitor**. The two are different arities and different evidence burdens.

Keeping them apart is what stops `SF-GS76-FEMALE-REPRODUCTIVE-AGE` or
`SF-GS76-IMAGING-AVAILABLE-NOW` from becoming universal anchors merely by being
registered. A feature is registered once; an anchor relation is asserted, cited
and reviewed once per (feature, competitor concept, learner decision).

## 5. The feature registry

One row per clinical feature:

| field | source |
| --- | --- |
| `feature_id` | the frozen `stem_feature_id`, unchanged |
| `canonical_concept_id` | `feature_id` at baseline; the normalization inventory measured `canonical_concept_id == local_feature_id` for all 180 resolved local terms |
| `preferred_label` | the frozen `normalized_feature` |
| `feature_type` | the frozen `clinical_role` |
| `allowed_states` | `PRESENT`, `ABSENT`, `UNKNOWN`, `NOT_APPLICABLE` -- V2's four, unchanged |
| `supported_roles` | the contrast roles `contrast_role_for` yields for this `feature_type` across the three decision domains, computed, not authored |
| `provenance` | the vocabulary artifact and the anchor study unit |
| `verification_status` | `FROZEN_CANONICAL` for every baseline feature |
| `introduced_in_version` / `deprecated_in_version` | snapshot ids |

Feature ids are stable because they are the frozen ids. No feature is created,
renamed, merged or split by this design. The normalization inventory already
proved there are no cosmetic duplicates to merge: `EXACT_LABEL_MATCHES_ACROSS_UNITS
= 0`, `POSSIBLE_ALIAS_MATCHES = 0`.

## 6. The anchor-relation registry

One row per anchor claim:

| field | meaning |
| --- | --- |
| `anchor_relation_id` | content-addressed over the **identity tuple only** |
| `feature_id` | the anchoring feature |
| `target_concept_id` | the competitor concept the anchor makes live |
| `learner_decision` | the curated `target_id` the relation was asserted for |
| `response_class` | the competitor's declared response-class tokens |
| `decision_granularity` | the competitor's granularity |
| `anchor_role` | the contrast role under which it anchors |
| `required_state` | `PRESENT` throughout; the field exists so a future relation need not be |
| `context` | derivation rule and sentence, or the supply rule and its S-4 limbs |
| `evidence_refs` | claim ids; empty for baseline rows, whose evidence is the frozen derivation |
| `verification_status` | `FROZEN_CANONICAL` or `EVIDENCE_VERIFIED` |
| `introduced_in_version` | snapshot id |
| `seed_id` | provenance and the retrieval join key |

The identity tuple is `(feature_id, target_concept_id, learner_decision,
decision_granularity, required_state)`. Evidence, role and context are deliberately
outside it, so restating the evidence for a relation does not move its id.

Measured before adopting it: across all 81 retrievable seeds,
`competitor_concept_id` is unique and `(concept_id, target_id, granularity)`
collides zero times, so the tuple is a faithful key for the seed-keyed rows it
replaces.

## 7. States and roles

`allowed_states` is V2's four states, and the registry is a boundary at which
`UNKNOWN` may never be read as `ABSENT`. `resolve_state` already defaults an
unnamed feature to `UNKNOWN`; the registry adds the guard on the other side, so a
consumer that asks the registry to treat a missing state as absence is refused
rather than answered.

`supported_roles` is computed from `CLINICAL_ROLE_TO_CONTRAST_ROLE`, not authored,
so the ontology cannot grow here. The thirteen roles §5 of the task lists are
exactly `CONTRAST_ROLES`, with one naming difference the task's list and the code
already share: the code's `SHARED_PRESENTATION_FEATURE` is the task's
`SHARED_PLAUSIBILITY_FEATURE`. The code's name is canonical and is not renamed.

## 8. Snapshots

Generation and retrieval must never read a mutable "latest". A snapshot is:

```
snapshot_id, built_from, features[], anchor_relations[],
registry_hash, feature_count, anchor_relation_count, extension_diff
```

`registry_hash` is SHA-256 over the canonical JSON of the sorted feature and
relation rows and nothing else -- not the build timestamp, not the tool version --
so a rebuild reproduces it exactly. There is no `latest` alias and no default
snapshot argument anywhere: a consumer that wants registry anchors passes a
snapshot object, and a consumer that passes nothing gets the historical frozen
packs, byte for byte.

* `FEATURE_ANCHOR_SNAPSHOT_V1` -- the baseline import, built only from the frozen
  vocabulary and the three frozen anchor packs.
* `FEATURE_ANCHOR_SNAPSHOT_V2` -- V1 plus the independently approved frozen-five
  extensions, and nothing else.

## 9. Baseline import and the regression bound

`FEATURE_ANCHOR_SNAPSHOT_V1` must reproduce existing behaviour, not approximate
it. The binding test is not that the counts match; it is that for **every one of
the 81 retrievable seeds**, the anchor feature-id set the snapshot yields is
`==` the set the frozen pack yields. Anything else is a silent reinterpretation
of frozen data.

Above that sits the behavioural regression: the four frozen G2 accepted controls,
the four flagship anchorless rejections, and the eight second-key controls must
return the same verdicts under V1 as under no snapshot at all.

## 10. Migration seams

`SAF_1`'s rule is not the seam and does not change. The seam is the three places
a frozen pack becomes an index row:

* `profile_contrast_retrieval.build_retrieval_index`
* `contrast_first_pilot.load_curated_candidates`
* `contrast_first_pilot.contrast_set_retrieval_index`

Each gains one keyword-only `snapshot` argument, defaulting to `None`. With
`None` the function is bit-for-bit what it was, which is what keeps
`retrieve_profile_aware_contrasts` -- retrieval benchmark arm A -- unchanged.
With a snapshot, anchors come from the pinned registry and the row records which
snapshot supplied them.

`retrieve_profile_aware_contrasts` itself is not modified at all: it reads
`row["plausibility_anchor_feature_ids"]` as it always has. V2 and the supply layer
resolve anchors through the same snapshot, so there is one feature-identity system
and not two.

## 11. Extensions: append-only, evidence-bound, independently reviewed

The supply layer may **propose** and may not apply. The workflow is

```
propose extension -> evidence validation -> independent review
  -> approved extension set -> deterministic new snapshot build -> replay
```

Every proposal is classified `FEATURE_ALREADY_EXISTS`, `NEW_FEATURE_REQUIRED`,
`ANCHOR_RELATION_ONLY` or `INVALID_EXTENSION`, and carries a review verdict of
`APPROVED`, `REJECTED` or `UNCERTAIN`. **`UNCERTAIN` fails closed** and never
enters a snapshot; so does `REJECTED`. Model memory is not evidence: an extension
must rest on an existing validated V2 relation, an existing source or foundational
claim, or targeted authoritative evidence.

Minimality, §15, is a precondition and not a tiebreak. A proposal must be
clinically meaningful, MCC-level relevant, needed for a validated contrast
relation, evidence-backed, not a duplicate and correctly typed. **Question yield
is not evidence for adding a feature**, and the reviewer is instructed to refuse
on that ground alone.

## 12. Success rule, precommitted

`CONTRACT_RECONCILIATION_PASS` requires all six:

1. every approved extension anchor is visible to V2;
2. the same anchors are visible to `SAF_1`;
3. the same anchors are available to profile-aware retrieval;
4. historical controls are unchanged;
5. no rejected or uncertain extension enters a snapshot;
6. no safety gate is weakened -- the `ADM_1`, `ADM_3`/`CS2` second-key ceiling and
   `SAF_1` rules are byte-identical and their verdicts on the historical controls
   are unchanged.

Generation does not run if this fails.

## 13. `G2-PED-01` as the positive control

The item's stem, options, key, evidence and rationales are **not touched**. It is
the cleanest available isolation of the registry fix: an item an independent
review passed on all eleven dimensions, refused by the anchor contract alone. The
question the replay answers is narrow -- does the same item, unchanged, now pass
the same rule against a snapshot that contains the anchors its review already
approved?

## 14. What this design does not fix

Named, so it is not later claimed. The out-of-set second-key gate V2 lacks is not
built here. `G2-SURG-01` remains inexpressible: the frozen `SU-GS-76` vocabulary
has no feature for a chronic bowel history, and this design deliberately does not
grow the vocabulary, so the five `NEW_FEATURE_REQUIRED` proposals stay refused.
`G2-SURG-02` fails `CS2-9` on its own frozen key and no anchor supply reaches
that. Difficulty calibration is untouched.

## 15. Copyright

The registry stores normalized feature statements already present in the frozen
vocabulary, concept ids, claim ids and derivation sentences quoting the seeds'
own frozen prose. No Toronto Notes prose enters it. The existing leak check runs
over every artifact this milestone creates.
