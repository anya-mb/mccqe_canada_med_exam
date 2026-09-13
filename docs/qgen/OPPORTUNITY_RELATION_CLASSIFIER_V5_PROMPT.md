# Opportunity Relation Classifier V5

Classify one supplied opportunity pair under the frozen Atomic Opportunity Contract and the Equivalent–Variant Boundary V1. Do not invent, split, merge, repair, or rewrite either endpoint. Do not infer a desired label distribution.

Inputs are limited to opportunity A, opportunity B, relevant minimal curriculum context, and the two contracts. Matcher history, source registry version, partition identity, pair identifiers beyond response bookkeeping, prior outcomes, and gold labels must remain hidden.

Direction is fixed: A is the benchmark-or-reference endpoint and B is the registry-candidate endpoint.

Return one `predicted_relation` from:

- `EQUIVALENT`
- `REGISTRY_BROADER_CONTAINS_BENCHMARK`
- `REGISTRY_NARROWER_THAN_BENCHMARK`
- `VARIANT_OF_SAME_DECISION`
- `RELATED_BUT_DISTINCT`
- `NEAR_DUPLICATE`
- `DUPLICATE`
- `UNRELATED`

Also return exactly these structured fields:

- `same_principal_decision`: `YES`, `NO`, or `UNCERTAIN`
- `same_answer_scope`: `YES`, `NO`, or `UNCERTAIN`
- `directional_containment`: `NONE`, `A_WITHIN_B`, `B_WITHIN_A`, or `UNCERTAIN`
- `independently_scoreable_difference`: `YES`, `NO`, or `UNCERTAIN`
- `context_changes_correct_action`: `YES`, `NO`, or `UNCERTAIN`
- `residual_difference`: `NONE`, `SYNONYMY_ONLY`, `WRAPPER_ONLY`, `EVIDENCE_PATH`, `ITEM_REALIZATION`, `MATERIAL`, or `UNRESOLVED`
- `near_duplicate_signal`: `YES`, `NO`, or `UNCERTAIN`
- `internal_conflict`: boolean
- `insufficient_context`: boolean
- `justification`: concise evidence-based explanation

Decision procedure:

1. Identify each endpoint’s decision operation, decision object, answer scope, material state, and required response modality. Treat generic labels as underspecified rather than automatically broad.
2. Mark internal conflict when narrative semantics disagree with family, response class, physician activity, stage, population, or severity in a way that changes the interpretation.
3. Determine whether a learner could reliably answer one endpoint correctly and the other incorrectly. If yes, the difference is independently scoreable.
4. Assert directional containment only when logical answer-scope inclusion is explicit or necessary. `A_WITHIN_B` means the registry-side B contains benchmark-side A. `B_WITHIN_A` means B is a proper subset of A. Workflow membership and topical association are not containment.
5. `EQUIVALENT` requires the same principal decision, same answer scope, no independently scoreable difference, no decision-changing context, no containment, and no residual difference beyond synonymy.
6. `VARIANT_OF_SAME_DECISION` requires those same identity conditions plus a positive non-decision-changing wrapper, evidence-path, or item-realization delta.
7. Use `NEAR_DUPLICATE` when material redundancy remains but a small unresolved modality, atomicity, semantic, or metadata conflict prevents safe equivalence or variant classification.
8. Use `RELATED_BUT_DISTINCT` for separate independently scoreable decisions or a decision-changing state, even within one topic or workflow.
9. Use `UNRELATED` only when no clinically material opportunity relationship remains.
10. Preserve uncertainty in the structured fields. The downstream deterministic policy, not this semantic step, decides whether to auto-accept or request adjudication.

Do not use pair-specific rules, memorized examples, confidence percentages, or pseudo-probabilities.
