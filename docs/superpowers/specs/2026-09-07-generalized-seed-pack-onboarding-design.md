# Generalized Seed-Pack Onboarding Design

## Status and scope

This design implements the user-approved generalized-onboarding milestone against the frozen 36-opportunity development regression set. It does not change the frozen opportunities, frozen stem-feature maps, historical seed packs, feature/anchor V5 semantics, profile V2, or existing retrieval safety gates.

## Architecture

Historical packs remain inputs in their existing three-file form. New onboarding packs use a versioned contract that records pack lineage, exact study-unit/opportunity scope, canonical candidate identity, learner-decision and response-class compatibility, relation and anchor foreign keys, evidence, author provenance, independent-review provenance, input/review hashes, and a content hash.

`build_retrieval_index` remains the single-pack historical adapter. A new explicit multi-pack adapter accepts an ordered historical bundle list plus an ordered additional onboarding bundle list. It validates every additional pack, admits only `APPROVED` rows, rejects duplicate seed identities across inputs, attaches narrow scope metadata to new rows, and delegates the actual row construction to the historical adapter. Callers must name every pack; no filesystem discovery or implicit latest-version selection exists.

Retrieval receives optional learner-decision and study-unit scope inputs. Historical rows have no onboarding scope and therefore preserve their old behavior. New rows must match their declared scope before response-class, second-key, anchor-floor, and ranking logic runs. Omitted new packs remain unavailable.

## Safety invariants

- `REJECTED` and `UNCERTAIN` rows never enter the index.
- A positive candidate anchor must be supported by a feature whose declared relation positively supports the candidate; a key-only discriminator is rejected as a backwards anchor.
- The existing `SAF_1` anchor floor and `ADM_3` second-key ceiling are unchanged.
- New packs are content-addressed and fail closed on stale input/review hashes, malformed scope, missing relation/anchor identities, or duplicate candidate/seed identities.
- Historical-only replay must be byte-identical to the pre-change index.

## Development gates

The deterministic development-12 roster is the first two opportunity IDs per discipline after excluding the four Route-A opportunities. Candidate discovery and semantic review are bounded to that roster first. Architecture expansion to the remaining frozen opportunities occurs only after at least one previously unreachable approved seed is retrieved, historical replay is identical, non-approved rows remain unavailable, scope isolation holds, and an opportunity improves over the 0/12 baseline.

All generated artifacts are labelled development validation, never a fresh holdout or production-readiness result. If no opportunity becomes contrast-ready, generation and final medical review do not run.

## Verification

Use test-first development for the root-cause reproduction, explicit additional-pack ingestion, status filtering, scope isolation, backwards-anchor rejection, historical compatibility, anchor-floor preservation, and second-key preservation. Run focused tests throughout and the full canonical suite once after the final shared-code state.
