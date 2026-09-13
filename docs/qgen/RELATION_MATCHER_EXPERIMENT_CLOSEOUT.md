# Relation Matcher Experiment Closeout (V3 → V4 → V4.1 → V4.2 → V5)

## Decision

Do not build a Matcher V6. Stop the automatic-opportunity-relation-matcher line of
research. Further matcher R&D is not required before question generation resumes.

## Evidence chain

- Matcher V3: 2/86 held-out accuracy (`0.023256`). Failed.
- Matcher V4.1 (corrected calibration, 167 pairs): accuracy `0.898204`, EQUIVALENT F1
  `0.571429`. Failed.
- Matcher V4.2 (calibration-only refinement): calibration passed (accuracy `0.916168`,
  macro F1 `0.889833`); the single permitted run on 65 blinded validation rows failed
  (accuracy `0.907692`, EQUIVALENT F1 `0.571429`, VARIANT F1 `0.0` on support 2).
- Matcher V5 (selective: `AUTO_ACCEPT` or `NEEDS_SEMANTIC_ADJUDICATION`), development
  evidence (232 rows, `matcher_v5_development_cross_validation.json`,
  `content_sha256=0923a960c7d5a9d414074d9bae07be58ec18a42317881949d32d5a60b15409bc`):
  auto-resolved 108/232 (coverage `0.465517`), auto-accuracy `0.981481`, auto-critical
  precision `1.0`, 0 catastrophic errors. Looked promising, but development-only.
- Matcher V5, genuinely fresh validation (185 previously unseen pairs, two blinded
  reviewers + third-reviewer adjudication + two supplement waves,
  `fresh_v5_validation_gold.json` `content_sha256=41d392b480749b622b9c0f6c7e1127d1f9f8e1516dd2d79936771d5a100342dc`,
  frozen before the V5 contract was ever run against it, contract
  `content_sha256=d32e983fbad4273a1f463529abf6559568a0d00f1b7d8a4602cace6fe91a7045`):
  auto-resolved 64/185 (coverage `0.345946`), auto-accuracy `0.890625`, auto-critical
  precision `0.5`, 0 catastrophic dedupe-class errors
  (`fresh_v5_validation_auto_metrics.json`).

The predeclared fresh-validation safety floors (auto-critical precision ≥ 0.95,
auto-resolved accuracy ≥ 0.95) were violated. Development metrics did not generalize.
This is not "promising" — it is a failed selective architecture.

## Why the 121 abstained pairs were not adjudicated

The frozen selective policy and its AUTO metrics are already computed and immutable
from the 185-pair fresh validation set. Labeling the 121 pairs the matcher abstained on
cannot change `auto_resolved`, `auto_coverage`, `auto_accuracy`, or
`auto_critical_precision` — those are defined only over the 64 pairs the matcher chose
to resolve automatically. Completing adjudication would only describe how well a human
(or a further semantic pass) could do on the abstained remainder, which is not in
question: the architecture already failed on its automated component. Spending further
quota on that adjudication before recording the result would not change the verdict.

Two partial adjudication batches exist on disk
(`fresh_v5_validation_abstention_adjudication_batch_1_predictions.json` and
`..._batch_2_predictions.json`, 40 pairs each, adjudicator id
`FRESH_V5_ABSTENTION_ADJUDICATOR`); batches 3 and 4 (40 and 1 pairs) have inputs but no
predictions. These partial outputs are **not used** anywhere in this closeout or in any
canonical metric: `fresh_v5_validation_auto_metrics.json`'s
`source_prediction_sha256` matches `fresh_v5_validation_selective_predictions.json`'s
own `content_sha256` directly, with no dependency on any adjudication artifact. No
on-disk marker distinguishes a "disqualified, truncated-instruction" adjudicator run
from a "replacement" one — both existing batches share the same `adjudicator_id` and
show no structural corruption — so this closeout does not assert which of the two
described spawns produced which batch; it asserts only that neither batch's labels are
consumed by any frozen result. Status: `INVALID_NOT_USED` / `PARTIAL_NOT_USED` for both
batches 1 and 2; batches 3 and 4 were never run.

## Final heldout

The 67-row `FINAL_HELDOUT` partition of corrected Gold V3
(`relation_gold_v3_frozen_partitions.json`) remains unopened for V5: no V5 script,
test, or artifact references it. It stays sealed for a future architecture, if one is
ever justified.

## Production relation strategy going forward

`DETERMINISTIC_CANDIDATE_PROPOSAL_PLUS_SEMANTIC_ADJUDICATION`:

1. Deterministic retrieval/mining proposes candidate opportunity relations.
2. Exact projected-record duplicates are resolved deterministically only when exact
   invariants prove identity (this is the one deterministic override V5 already used
   safely).
3. Nontrivial semantic relations are never forced by an automatic matcher.
4. Relations affecting curriculum coverage or deduplication are adjudicated
   semantically offline, in bounded batches.
5. Critical classes requiring adjudication include at minimum: `EQUIVALENT`,
   `VARIANT_OF_SAME_DECISION`, `NEAR_DUPLICATE`, `REGISTRY_BROADER_CONTAINS_BENCHMARK`,
   `REGISTRY_NARROWER_THAN_BENCHMARK`.
6. `UNCERTAIN` remains fail-closed.
7. Independent confirmation/adjudication is required wherever a relation materially
   affects registry atomicity, deduplication, or coverage.

This is offline curriculum construction; runtime speed is not the objective and was
never the constraint. Trustworthiness is. Three matcher generations (V3, V4-family, V5)
spanning multiple fresh-validation cycles have now shown that automatic relation
classification does not clear safety floors on genuinely unseen data, while the
registry-construction step this feeds is a one-time/offline build. Continued matcher
engineering has diminishing returns relative to simply routing critical relations to
semantic adjudication from here.

## What still blocks question generation

Benchmark atomicity/enumeration work (Atomic Opportunity Contract V1, Registry V1/V2)
is complete and frozen; the outstanding gap was never atomicity itself but a
trustworthy way to classify *relations between* enumerated opportunities so Registry V3
can be deduplicated without an unsafe automatic matcher. With the matcher question
closed, Registry V3 is buildable now using deterministic proposal + semantic
adjudication, with no further relation-matcher research required first.
