# Equivalent–Variant Boundary V1

This contract applies after the frozen Atomic Opportunity Contract has established the comparison unit. It separates opportunity-relation identity from item-realization differences.

`EQUIVALENT` requires all four conditions:

1. The principal learner decision is materially the same.
2. The clinically correct response and answer scope are materially the same.
3. Neither endpoint requires an additional discriminating inference.
4. No supplied difference is independently educationally scoreable or represents a distinct item realization. Synonymy and purely redundant wording are permitted.

`VARIANT_OF_SAME_DECISION` requires the same principal decision and correct answer scope, but also requires a positive realization difference: an alternate non-decision-changing evidence path, wrapper, presentation, or discriminator that could support a legitimate alternate item without creating a separate curriculum decision.

The absence of a decision-changing difference is necessary but not sufficient for `VARIANT_OF_SAME_DECISION`. A classifier must identify the positive realization delta. Conversely, a non-decision-changing delta is not permission to collapse the pair to `EQUIVALENT`.

`NEAR_DUPLICATE` is materially redundant content with a small unresolved semantic, modality, atomicity, or metadata conflict that prevents safe equivalence or variant classification. Because the conflict is load-bearing, Matcher V5 always routes this relation to semantic adjudication.

`RELATED_BUT_DISTINCT` requires a different independently scoreable decision or a material context change that changes the correct response. Shared topic, shared workflow, or lexical similarity is insufficient.

Synthetic abstractions:

- “Choose the first-line test for condition X” and “Select the initial investigation for condition X” are equivalent when the supplied state and answer domain are coextensive.
- The same diagnostic decision presented once through a classic symptom pattern and once through a non-decision-changing laboratory pattern is a same-decision variant.
- “Recognize instability” and “stabilize the unstable patient” are related but distinct sequential decisions.
- Two records that appear to target the same monitoring decision but disagree coherently about whether the response is diagnosis or longitudinal planning are near-duplicates until the modality conflict is adjudicated.

Raw field inequality never determines the boundary by itself. Stage, population, severity, family, and response-class differences must be classified as decision-changing, wrapper-only, or unresolved. Unresolved evidence requires abstention.
