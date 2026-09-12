# Decision Signature V2, Discovery V5, and Clinical Contrast Bundles Design

## Scope

This development-only milestone extends the completed Catalogue V2 and Discovery V4 work. It builds a frozen compatibility benchmark, introduces the smallest reusable Decision Signature V2 semantics justified by the six known V4 failure cases, implements supply-preserving Discovery V5, and constructs at most 24 evidence-backed Clinical Contrast Bundle V1 artifacts. It does not select or run a clean transfer cohort or operational holdout, modify frozen historical artifacts, call an external LLM API, or create a commit.

## Architecture

`contrast_supply_v5.py` is an additive child of the frozen V4 implementation. It owns V2 signature validation and compatibility, V5 global candidate filtering/ranking, bundle validation, contrast-matrix validation, admission, cache lookup, and deterministic density/economics calculations. `run_contrast_supply_v5.py` binds canonical inputs by content hash and builds new artifacts without rewriting V1/V4 artifacts.

The V2 signature starts with V1's `decision_intent`, `target_domain`, and `clinical_stage`. A new dimension is admitted only when the frozen six-case forensic report proves that it distinguishes a hard negative while retaining approved positives and has reusable controlled values. Values may describe reusable subdomains, entity families, applicability contexts, or containment roles; they may not encode diseases or opportunity IDs.

Discovery V5 scans the global Catalogue V2 source. It applies response class, granularity, V2 signature, applicability, alias, and containment gates before deterministic ranking. It never generates names or uses embeddings. Every development anchor receives exactly one bounded pool of at most eight canonical candidates before review.

## Clinical contrast bundle contract

A bundle binds one learner-decision family, key, response class, granularity, V2 context, population restrictions, stage, target domain/subdomain, clinical-state entities, option candidates, and a feature matrix. Diagnosis options remain diagnoses; investigation options remain investigations; management/prevention/ethical options remain actions of their demanded class.

Every admitted candidate has a canonical identity, at least one evidence-backed positive plausibility feature, at least one evidence-backed inferiority discriminator in the key context, pairwise alias/containment/equivalence review, counterfactual correctness conditions, second-key risks, evidence references, and independent review. Matrix cells use only `PRESENT`, `ABSENT`, `UNKNOWN`, or `NOT_APPLICABLE`; silence never becomes absence. Feature visibility is `STEM_ELIGIBLE`, `RATIONALE_ONLY`, or `CONDITIONAL`.

Bundle admission is arithmetic: four or more approved alternatives is `STRONG_BUNDLE`, exactly three is `MINIMUM_GENERATABLE_BUNDLE`, one or two is `PARTIAL_BUNDLE`, and zero is `NO_SAFE_BUNDLE`. The cache reuses bundles only across matching learner-decision family, signature, subdomain, and applicability context.

## Development and review policy

The roster is frozen before bundle authoring and draws only from Build-12, the contaminated diagnostic Transfer-12 as development data, and approved historical controls. Evidence-rich anchors are preferred over discipline quotas. Candidate review and bundle review are serial. Existing verified evidence is reused first; narrowly targeted authoritative Canadian research is permitted only for load-bearing gaps. No candidate is invented to meet a quota.

Question smoke generation is conditional on at least three generatable bundles and is capped at six one-attempt development questions. It uses only frozen approved alternatives and reviewed matrix propositions, requires at least three post-stem `LIVE_BUT_INFERIOR` candidates, and passes through the existing generation lifecycle and final medical review.

## Verification and readiness

All shared behavior follows red-green TDD. Focused tests cover positive recall, hard-negative rejection, global-source retention, multi-candidate supply, bundle schema/matrix invariants, cache scoping, density, historical controls, and lifecycle safety. The canonical full suite runs once after the final shared-code change. New artifacts receive canonical content hashes and a Toronto Notes leak audit.

`READY_FOR_NEW_CLEAN_TRANSFER` is true only if copyright, historical safety, tests, positive recall, Discovery V5 safety, at least three development anchors with three approved alternatives, and at least one diagnostic-transfer development anchor with three approved alternatives all pass. If ready, a new outcome-blind cohort may be frozen but is not run.
