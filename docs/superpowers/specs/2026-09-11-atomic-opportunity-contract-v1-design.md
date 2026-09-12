# Atomic Opportunity Contract V1 Design

## Problem

Registry V2 preserved every V1 decision, yet the reported strict recall fell from 38/675 to 18/675. The comparison artifacts used independently authored, unversioned semantic verdicts. Of the 38 V1 full matches, all 38 have text-identical V2 descendants, but 31 were relabelled partial and two were relabelled missing. The evaluation therefore changed the matching standard while changing the registry.

The 675-row benchmark is also not entitled to define granularity by assertion. Its rows can be atomic coverage obligations, alternative evidence paths to one obligation, item variants, cosmetic variants, compounds, or unsupported decisions. Registry rows have the same possible defects.

## Definition

One educationally distinct MCCQE question opportunity is one assessable decision rule:

> Given a clinically material state, the learner must produce one response whose correctness turns on one coherent reasoning target.

An opportunity is identified by the tuple `(scope unit, response class, decision operator, decision object, material state, material population)`. Wording, item form, distractors, difficulty, alternate supporting clues, and cosmetic demographics are not identity dimensions.

Split two candidates only when at least one of the following is true:

1. They demand different response classes.
2. They demand independently scoreable decisions, such that a learner can reliably get one right and the other wrong.
3. A named stage, severity, population, or contraindication changes the correct response.
4. They are sequential decisions with different outcomes, such as recognizing instability and stabilizing it.

Do not split when candidates differ only by an alternate clue supporting the same inference, a synonymous action verb, an interchangeable stem wrapper, difficulty, distractors, or a non-material demographic. A row is compound when one answer must demonstrate two independent decisions. A broad curriculum statement is not automatically an atomic opportunity; it remains `REQUIRES_DECOMPOSITION` until its single decision rule is explicit.

## Matcher contract

Pairwise comparison uses five directional relations:

- `EQUIVALENT`: the same decision rule; wording and evidence path may differ.
- `BENCHMARK_NARROWER`: the benchmark is an item/evidence variant inside a broader registry decision.
- `REGISTRY_NARROWER`: the registry is one branch inside a broader benchmark decision.
- `RELATED_DISTINCT`: same topic, different independently scoreable decision.
- `NONE`: no educational coverage relationship.

Only `EQUIVALENT` counts as strict raw recall. Directional containment counts as coverage only after the broader endpoint passes atomicity adjudication; otherwise it is a granularity diagnostic. The matcher takes the maximum relation rank over candidates and can never downgrade an existing edge merely because more registry rows were added. A preserved row inherits its previously adjudicated edges until a versioned re-adjudication explicitly names the changed contract and reason.

Precision is calculated from the same edge graph and the same equivalence rule as recall. Topic support is reported separately and is never called precision.

## Benchmark granularity

The frozen benchmark remains byte-identical. A companion audit may assign a benchmark row `ATOMIC_OPPORTUNITY`, `EVIDENCE_PATH_VARIANT`, `ITEM_VARIANT`, `COSMETIC_VARIANT`, `COMPOUND`, or `UNSUPPORTED_OR_OUT_OF_SCOPE` only when the evidence establishes that verdict. Otherwise it must assign `UNRESOLVED_GRANULARITY`, leave the canonical cluster null, and withhold an audited denominator. Non-independent rows share a canonical cluster only after blinded semantic adjudication. The original 675-row denominator is always retained; an audited cluster denominator exists only after every included row has a supported final verdict.

No benchmark row is deleted. Unresolved rows remain in the raw evaluation and are excluded from claims of normalized completeness.

## Registry V3

Registry V3 is a canonicalization layer over V2, not a third enumeration pass. It preserves lineage and source evidence, adds the V1 atomic signature and atomicity status, records variant/containment relationships, and refuses allocatable capacity for unresolved, compound, unsupported, or variant-only rows. It does not use benchmark IDs to create curriculum decisions.

The initial V3 may contain `REQUIRES_ATOMICITY_REVIEW` rows. That is preferable to falsely certifying legacy broad rows. V3 does not supersede V2 for production until matcher calibration, benchmark-granularity audit, duplicate review, suitability review, and Blueprint Mapping V2 all pass their independent gates.

## Blueprint Mapping V2

Blueprint labels are mappings, not intrinsic opportunity identity. Mapping V2 records a primary label, allowed secondary labels, a rule identifier, and confidence. Family-only heuristics are forbidden. The mapper considers the assessed response, temporal care context, prevention purpose, psychosocial/legal context, and source MCC objective. Ambiguous mappings fail closed to `REVIEW_REQUIRED` and have no production allocation authority.

The existing 120-row blind audit is calibration evidence, not a licence to memorize opportunity IDs. Calibration and holdout partitions are deterministic and rule IDs contain no row or study-unit identifiers.

## Gates

The milestone passes scientifically when the recall paradox is explained, monotonic matcher invariants pass, partial matches have a complete forensic taxonomy, benchmark granularity uncertainty is explicit, V3 is reproducible and lineage-complete, and Blueprint Mapping V2 reports honest calibration/holdout performance. Production remains closed regardless of those results in this milestone, and no production question is generated.
