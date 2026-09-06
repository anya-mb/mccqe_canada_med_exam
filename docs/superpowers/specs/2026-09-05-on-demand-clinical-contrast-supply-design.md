# On-demand clinical contrast supply

Design date: 2026-09-05.
Baseline: `b591226`, Clinical Contrast Relation Model V2 (`58066e9`).
Diagnosis: `reports/qgen_v2_contrast_supply_diagnosis.json`, commit `02cfa58`.

## 1. What this is, and what it is not

The V2 replay over the ten frozen opportunities accepted four, rejected one and
refused five before a stem existed. Those five refusals are the model working.
`NEXT_DOMINANT_BOTTLENECK = CONTRAST_SUPPLY` names the open question they leave:

> can the supply of independently validated, evidence-backed
> `LIVE_BUT_INFERIOR` competitors be raised, per opportunity and on demand,
> without weakening one V2 semantic rule?

This is a **supply layer upstream of V2**. It is not a redesign of V2, not a
replacement for the production generator, not a broad question bank, not a
whole-book GraphRAG, and it adds no embeddings. Every candidate it admits is
handed to the unmodified `evaluate_contrast_set_coherence` and to the unmodified
`retrieve_profile_aware_contrasts`. If those refuse it, it is refused.

The target is **not more candidates**. A candidate that the gate refuses is not
supply; it is noise with an id.

## 2. The pipeline

```
QUESTION OPPORTUNITY (frozen)
        v
LEARNER DECISION + KEY CONCEPT/ACTION (frozen)
        v
CANDIDATE DISCOVERY          <- ordered sources, section 4
        v
CANDIDATE DEDUPLICATION      <- canonical concept ids, section 6
        v
PAIRWISE V2 RELATION ACQUISITION   <- the existing V2 relation object
        v
INDEPENDENT ADMISSIBILITY REVIEW   <- APPROVED / REJECTED / UNCERTAIN
        v
VALIDATED CONTRAST CACHE     <- decision-context keyed, section 7
        v
CONTRAST SET ASSEMBLY        <- hands off to the unmodified V2 gate
```

Stages 1, 2 and the last arrow are V2's. Only the middle five are new.

## 3. What the diagnosis says the supply layer must actually do

Measured, not assumed. Across the five refusals there are six competitor drops:

| rule | count | what it means |
| --- | --- | --- |
| `CS2-6` ANCHOR_EQUALS_CONDITION | 4 | every usable plausibility anchor also completes the competitor's own correctness signature |
| `CS2-7` NO_USABLE_ANCHOR | 1 | every declared anchor types to `PRIOR_ONLY` or `RESOURCE_AVAILABILITY` |
| `CS2-1` nesting | 1 | an evidence-backed `COMPLICATION_OF` pair |

Five of the six are properties of the **frozen stem-anchor layer** -- which
features were recorded as making a seed plausible -- and not of the clinical
concept. So the first thing on-demand supply must be able to do is not to find a
new disease. It is to record, with evidence, that a competitor already in the
library is made *considerable* by a presentation feature that does not make it
*correct*.

That is a sharp knife. Rule S-4 below is its handle.

## 4. Discovery sources, in order

1. existing independently approved V2 contrast relations (`clinical_contrast_relations_v2.json`);
2. the curated contrast library (`chapter_global_contrast_library.json`);
3. the curated seed packs, filtered by anchor study unit, decision granularity and demanded response class;
4. the typed clinical graph;
5. Toronto Notes FTS5, structure-aware chunks;
6. targeted authoritative source research, only where a load-bearing relation has no admitted claim.

A source lower in the list is consulted only when the ones above it have not
produced enough admissible supply. Model memory is **not** a source: a reasoner
may propose a search concept, and that proposal is worth nothing until it is
grounded in one of the six and independently reviewed.

## 5. Retrieval query construction

A retrieval request is built deterministically from the opportunity's own fields
-- learner decision, key concept, demanded response class, decision granularity,
anchor study unit, and the normalized text of the frozen stem features for that
unit. Never from the whole stem prose, and never as one giant generic query.

Toronto Notes retrieval is bounded: 5 to 15 chunks per discovery operation, never
a chapter. Toronto Notes remains `TOPIC_DISCOVERY_SOURCE`. Anything that changes
-- thresholds, doses, intervals, immunizations, legal obligations -- still
resolves to `CURRENT_CLINICAL_AUTHORITY`.

## 6. Deduplication

Candidates are keyed by canonical concept id. Removed before review: aliases of
one concept, a parent beside its own subtype where the option set cannot hold
both, near-identical management actions, the same intervention reworded, and the
same concept arriving from two sources. Duplicates are never counted as supply.

## 7. Cache identity

A cache entry is keyed by

```
sorted(concept_a_id, concept_b_id)
  + learner_decision_id
  + demanded_response_class
  + decision_granularity
  + anchor_study_unit_id
  + decision_domain
```

so that *A versus B for DIAGNOSIS* can never be served as *A versus B for
MANAGEMENT*. The cache stores the V2 relation object unchanged, plus its
discovery provenance and its review verdict. `UNCERTAIN` entries are stored and
never served: they fail closed.

## 8. The five rules that keep this honest

**S-1 Frozen vocabulary is read-only.** A candidate states its correctness
conditions and its anchors in `g2_stem_feature_vocabulary.json` feature ids and
in nothing else. Where a discovered competitor cannot be expressed there, it is
refused and the refusal is recorded as a finding, not worked around.

**S-2 Additive artifacts only.** No frozen pack, reading, opportunity, key,
evidence packet or V1/V2 report is edited. Acquisition writes new files.

**S-3 Evidence before admission.** Every acquired relation cites at least one
claim already admitted to an evidence packet, or a new claim researched under
Phase 14's one-wave bound. `verification_status` is carried on the relation and
`UNVERIFIED` never enters the cache.

**S-4 Anchor provenance.** The supply layer may author a plausibility-anchor set
for a candidate only from features that are

  (a) in the frozen vocabulary for that anchor study unit, and
  (b) named by a cited claim as a presentation feature the candidate shares with
      the key, or as a recognized reason to consider the candidate, and
  (c) not on their own sufficient to satisfy the candidate's correctness
      conditions.

For a candidate that already carries a frozen stem-anchor row, supply may only
**add**; it may never remove. Limb (c) is the load-bearing one: an added anchor
can move a competitor past `CS2-6` only when it genuinely makes the competitor
live without making it correct, which is exactly the property `CS2-6` tests. An
anchor added to defeat the rule rather than to state a shared finding is the
failure mode, and the independent review in section 9 exists to catch it.

**S-5 One bounded wave.** One acquisition wave per opportunity. If fewer than
three admissible competitors stand after it, `NO_SAFE_ITEM` is the correct
answer and is kept. No enrichment until a question becomes possible.

## 9. Independent admissibility review

Every new relation is reviewed before it enters the cache, against: clinical
plausibility; MCC-level relevance; same learner decision; same response class;
same decision granularity; shared-feature support; discriminator validity;
Boolean correctness of the condition tree; evidence support; second-key risk;
categorical exclusion; and pairwise usefulness inside the proposed set. For an
added anchor the reviewer answers limb (b) and limb (c) of S-4 separately.

Verdicts are `APPROVED`, `REJECTED`, `UNCERTAIN`. `UNCERTAIN` fails closed.

## 10. Competitor versus competitor

Supply is not finished when key-versus-candidate relations exist. For a proposed
set `KEY, A, B, C` the pairs `A-B`, `A-C`, `B-C` are evaluated too. That is
already `CS2-1`, `CS2-2`, `CS2-5` and `CS2-8` in the unmodified V2 gate, so the
supply layer does not re-implement it; it assembles the set and asks the gate.

## 11. Set assembly

Deterministic, one pass, drop-only, and stated here before any outcome was seen:

1. take every approved candidate for the opportunity, ordered by member id;
2. hand the set to `evaluate_contrast_set_coherence` and then to
   `select_admissible_subset`, both unmodified;
3. if the blueprint solver names a competitor it cannot settle and at least three
   competitors would remain without it, drop that one competitor and solve once
   more;
4. otherwise fail closed.

Step 3 drops; it never re-ranks, never searches, and never runs twice. It is the
same shape as `select_admissible_subset`, which already drops the members the
coherence gate refuses.

## 12. What is measured

`CANDIDATES_DISCOVERED`, `CANDIDATES_DEDUPLICATED`, `CANDIDATES_SEMANTICALLY_REVIEWED`,
`RELATIONS_APPROVED / REJECTED / UNCERTAIN`, opportunities with three valid
competitors before and after, the source that uniquely contributed each approved
relation, cache hits against new relations created, and per-stage context in
characters against V2's median 8,481 / p95 9,123.

Safety of new supply must be zero on all of: unsupported relations, second keys
admitted, categorically excluded relations admitted, learner-decision mismatches,
response-class mismatches, granularity mismatches, Boolean logic defects,
silence-as-absence defects.

## 13. Known limits of this design

- It cannot help an opportunity whose **key** is the defect. `G2-SURG-02` fails
  `CS2-9` on its own frozen key and no competitor supply changes that.
- It cannot invent vocabulary. `G2-SURG-01` needs a non-gynaecologic differential
  and `SU-GS-76` has no feature in which one could state a correctness condition
  without being its own sole anchor.
- Rule S-4 is the only mechanism by which an already-refused competitor can
  become supply, and it is therefore the mechanism most likely to be abused. Any
  recovery that rests on it should be reported as a weaker result than a recovery
  that rests on a genuinely new, independently reviewed concept.
