# Opportunity Relation Classifier V4.2

Classify one supplied pair under the frozen Atomic Opportunity Contract. Do not invent, split, merge, or rewrite opportunities. Do not infer a desired class balance.

Inputs are limited to opportunity A, opportunity B, relevant curriculum context, and the frozen contract. Matcher predictions, source registry version, partition identity, historical outcomes, and gold labels must remain hidden.

Return exactly one relation plus a concise justification:

- `EQUIVALENT`: the same atomic learner decision and material state, allowing synonymous wording and nonindependent explanatory detail.
- `REGISTRY_BROADER_CONTAINS_BENCHMARK`: registry-side B contains benchmark-side A's decision and adds independently scoreable scope.
- `REGISTRY_NARROWER_THAN_BENCHMARK`: registry-side B is a proper atomic subset of benchmark-side A's broader decision scope.
- `VARIANT_OF_SAME_DECISION`: the learner decision and correct response are unchanged; only a non-decision-changing evidence path, stage/family wrapper, difficulty, distractor, or cosmetic presentation differs.
- `RELATED_BUT_DISTINCT`: the endpoints share a topic or workflow but require different independently scoreable decisions or a decision-changing state.
- `NEAR_DUPLICATE`: the represented opportunity identity is materially redundant, but a small supplied semantic or metadata conflict prevents safe equivalence and is not merely an item variant.
- `DUPLICATE`: duplicate opportunity records, not merely semantic equivalence across distinct legitimate provenance.
- `UNRELATED`: no clinically material opportunity relationship.

Direction is fixed: opportunity A is the benchmark-or-reference-side endpoint and opportunity B is the registry-candidate-side endpoint. A broad or compound endpoint remains broad; do not silently repair it during classification.

Apply this decision order:

1. Compare the independently scoreable learner decisions and material states before categorical metadata. Response class, family, physician activity, and stage are evidence, but a metadata conflict alone does not prove distinctness.
2. Use directional containment only when both endpoints express the same kind of decision and one scope logically includes the other. Shared topic, workflow sequence, or one action occurring inside a broader clinical process is not containment when the responses remain independently scoreable.
3. If B is a specified proper subset of A, choose `REGISTRY_NARROWER_THAN_BENCHMARK`. If B contains A plus additional independently scoreable scope, choose `REGISTRY_BROADER_CONTAINS_BENCHMARK`. A generic broad endpoint does not make a clear direction uncertain.
4. Distinguish restriction from elaboration. A named subtype, complication, or subdecision that limits a generic endpoint can create a proper subset. Named comparators, evidence, or descriptors that only make the same decision explicit do not add independently scoreable scope and may remain `EQUIVALENT`.
5. Choose `VARIANT_OF_SAME_DECISION` rather than `EQUIVALENT` when only a non-decision-changing wrapper, evidence path, difficulty, distractor, or cosmetic presentation differs.
6. Choose `NEAR_DUPLICATE` only when the endpoints are materially redundant yet a small supplied conflict genuinely prevents safe equivalence or variant classification. Clear containment and clearly separate decisions take precedence over `NEAR_DUPLICATE`.
7. Assign `EQUIVALENT` only when the semantic target and material state are coextensive and no unresolved conflict remains about the required response modality.
8. When the narrative target is materially identical but response class, opportunity family, and physician activity coherently encode incompatible response modalities, assign `NEAR_DUPLICATE` unless the supplied semantics resolve the conflict.
9. Do not use `NEAR_DUPLICATE` merely because broad labels are lexically close or their scope is unclear. If the labels denote different reasoning operations that can receive separate correct responses, assign `RELATED_BUT_DISTINCT`.
10. Directional containment requires logical answer-scope nesting: answering the narrower endpoint must answer a restricted instance or explicit component of the broader endpoint. Workflow membership, evidentiary contribution, or topical association is insufficient.
11. When A supplies a generic or compound semantic scope and B explicitly selects one member, subtype, or independently identifiable subdecision within it, assign `REGISTRY_NARROWER_THAN_BENCHMARK` even if categorical metadata differs.
12. When B supplies a generic umbrella and A names one stage or subdecision within it, assign `REGISTRY_BROADER_CONTAINS_BENCHMARK` only when the wording establishes inclusion and both endpoints operate in the same semantic response domain.
13. Do not infer containment solely from generic workflow terms such as management, assessment, emergency, or diagnosis. Require an explicit or logically necessary scope relation in the supplied text.
14. Treat an explicit list as `EQUIVALENT` to a generic label only when the list is a coextensive paraphrase. If it selects less than the generic scope, use directional containment; if it supplies a separately scoreable decision, use `RELATED_BUT_DISTINCT`.
15. Evaluate categorical metadata after establishing semantic scope. Metadata cannot create containment, but a coherent unresolved modality conflict can prevent `EQUIVALENT`.

The semantic contract and relation taxonomy are unchanged from V4.1. These rules clarify general precedence boundaries only. This matcher run must choose one of the eight terminal relations above and may not return `UNCERTAIN`.
