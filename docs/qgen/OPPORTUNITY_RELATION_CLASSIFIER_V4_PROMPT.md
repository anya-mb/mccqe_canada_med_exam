# Opportunity Relation Classifier V4

Classify one supplied pair under the frozen Atomic Opportunity Contract. Do not invent, split, merge, or rewrite opportunities. Do not infer a desired class balance.

Inputs are limited to opportunity A, opportunity B, relevant curriculum context, and the frozen contract. Matcher predictions, source registry version, partition identity, historical outcomes, and gold labels must remain hidden.

Return exactly one relation plus a concise justification:

- `EQUIVALENT`: the same atomic learner decision and material state, allowing synonymous wording.
- `REGISTRY_BROADER_CONTAINS_BENCHMARK`: B contains A's decision but also additional independently scoreable scope.
- `REGISTRY_NARROWER_THAN_BENCHMARK`: B is a proper atomic subset of A's broader scope.
- `VARIANT_OF_SAME_DECISION`: the learner decision and correct response are unchanged; only a non-decision-changing evidence path, wrapper, difficulty, distractor, or cosmetic presentation differs.
- `RELATED_BUT_DISTINCT`: related topic/context but a different independently scoreable decision or decision-changing state.
- `NEAR_DUPLICATE`: materially redundant opportunity identity with a small unresolved semantic distinction that is not merely an item variant.
- `DUPLICATE`: duplicate opportunity record, not merely semantic equivalence across distinct provenance.
- `UNRELATED`: no clinically material opportunity relationship.
- `UNCERTAIN`: evidence is insufficient or the boundary cannot be resolved safely.

Direction is fixed: opportunity A is the benchmark-side endpoint and opportunity B is the registry-side endpoint. A broad or compound endpoint remains broad; do not silently repair it during classification. Use `UNCERTAIN` when the supplied context cannot support a direct classification.
