# Retry V2 Quality Design

Date: 2026-08-31

## Purpose and failure mode

`STRUCTURED_ITEM_SPEC_V2` is the approved design for a second, 10-question retry pilot of `QGEN-PHELO-011`. It addresses the V1 retry failure in which evidence-correct items still had shallow or cosmetic scenarios, weak/nonparallel distractors, plan mismatch, and material set-level duplication. Structure alone did not ensure a distinct, evidence-supported educational decision.

This is a future design contract, not authorization to create item specs, generate questions, research evidence, or implement validators.

## V1 lessons and preserved disposition

The V1 retry's evidence traceability and independent context passed, but the independent review rejected nine items. V2 therefore makes the learner decision, competing concepts, required reasoning, scenario necessity, and distractor logic explicit before generation. `QGEN-PHELO-011-RETRY-10` is the positive-control design example: its educational decision, plausible neighboring concepts, evidence-bounded teaching points, and non-cosmetic scenario are design properties to emulate; its question text must never be copied.

The approved card dispositions remain:

| Card | Disposition |
| --- | --- |
| 01 | `REPLACE_AS_DUPLICATIVE` |
| 02 | `KEEP_CORE_CONCEPT` |
| 03 | `REDESIGN_CONCEPT` |
| 04 | `REDESIGN_CONCEPT` |
| 05 | `KEEP_CORE_CONCEPT` |
| 06 | `REPLACE_AS_DUPLICATIVE` |
| 07 | `REPLACE_AS_DUPLICATIVE` |
| 08 | `REDESIGN_CONCEPT` |
| 09 | `KEEP_CORE_CONCEPT` |
| 10 | `KEEP_CORE_CONCEPT` |

`REPLACE_AS_DUPLICATIVE` does not approve a replacement concept. In particular, exploratory replacements for cards 06 and 07 are not canonical facts. Each future replacement must independently satisfy the evidence-alignment and semantic-preflight gates.

## V2 item-spec schema

Each proposed V2 card is a `STRUCTURED_ITEM_SPEC_V2` record, bound to one retry slot, allocation address/study unit, competency, and the exact authorized foundational claim cards and/or READY recommendations it uses. It includes:

- `learner_decision`: the single educational choice or judgment the learner must make.
- `competency_demonstration`: observable application of the assigned competency, rather than a label-only assertion.
- `reasoning_chain`: the necessary ordered inferences from scenario facts to the best answer.
- `evidence_discriminants`: evidence-supported facts that distinguish the answer from its closest alternatives.
- `closest_competing_concepts`: plausible, distinct alternatives a knowledgeable learner could reasonably consider.
- `distractor_blueprint`: one conceptual basis for each distractor and why it is wrong for this scenario.
- `vignette_requirements`: facts the scenario must contain and how removing them would impair the decision.
- `difficulty_mechanism`: the intended reasoning challenge; it cannot be mere obscure recall, wording trickery, or option-pattern cueing.
- `prohibited_shortcuts`: facts, wording, or option structures that would reveal the answer without the stated reasoning.
- `rationale_requirements`: the required explanation of the decision, evidence discriminants, and why each competing concept is not best.
- `semantic_signature`: a normalized, deterministic duplicate-candidate signal derived from the item's decision, reasoning, evidence route, competing concepts, and answer category.
- `lineage`: stable references and fingerprints for the retry slot, immutable V1 concept plan, authorized evidence, review decisions, generated item, and independent verification.

The pilot remains exactly 10 cards with deterministic study-unit allocation `5/3/2`. A card cannot be moved across study units to improve variety.

## Evidence-alignment contract

Before approval for generation, every proposed card must receive a semantic evidence-alignment check. Its `learner_decision`, `reasoning_chain`, `evidence_discriminants`, `closest_competing_concepts`, and `distractor_blueprint` must be supportable by the exact existing authorized evidence in its lineage. Toronto Notes remains topic context only.

The check may not choose a more interesting concept merely because it is in the same study unit, or stretch a foundational claim or READY recommendation beyond its support. If a proposed card fails, it is rejected; another evidence-supported concept in the same study unit may be proposed while preserving `5/3/2`. No new evidence research is permitted for V2.

## Semantic diversity and pre-generation review

Semantic diversity requires distinct educational decisions, non-cosmetic scenario necessity, plausible competing concepts, and materially different reasoning pathways across the ten-card set. A deterministic `semantic_signature` may flag duplicate candidates, but cannot claim to determine full semantic equivalence.

The required future sequence is:

`V2 ITEM SPEC` → `deterministic structural/semantic-signature validation` → `FRESH SEMANTIC PREFLIGHT REVIEW` → `generation` → `generated-item quality validation` → `fresh independent final verification`.

The fresh semantic-preflight reviewer assesses educational-decision distinctness, evidence-to-item-spec alignment, scenario necessity, plausibility of competing concepts, reasoning depth, and set-level semantic duplication. The reviewer is fresh relative to item-spec authorship and generation. Any unresolved semantic-quality concern fails closed before generation.

## Generator and validation contracts

The future generator may produce only an item that realizes the approved V2 spec: it must require the stated reasoning chain, use scenario facts materially, make the key and every rationale claim traceable to authorized evidence, and use distractors from the approved blueprint. It must not add claims from model memory, turn definitions into answer-revealing recall, substitute cosmetic framing for a necessary scenario, or collapse multiple cards into the same decision rule.

Deterministic validation is limited to schema, required fields, allocation counts, stable IDs, lineage/fingerprint integrity, evidence-reference presence, and duplicate-candidate flags from `semantic_signature`. Semantic suitability, evidence support in context, scenario necessity, plausibility, and true equivalence require the designated fresh human/LLM semantic reviews. Generated-item validation checks specification fidelity and mechanically auditable provenance; final verification remains independent of generation and preflight.

## Lineage, immutability, and fail-closed behavior

Every V2 record and derivative artifact must preserve a navigable lineage from retry slot and disposition through immutable V1 concept-plan references, assigned study unit/competency, exact authorized evidence identifiers and fingerprints, V2 review outcomes, generation output, generated-item validation, and independent final verification. This creates a new V2 lineage; it does not revise V1.

The following remain immutable: V1 concept plan, V1 generated questions, V1 independent verification, frozen study-unit allocation and its `5/3/2` retry apportionment, foundational evidence, READY packet evidence, and all upstream scope, mapping, ownership, routing, and allocation artifacts. No replacement, preflight decision, or V2 item may alter them.

Missing or mismatched lineage, unavailable authorized evidence, unsupported reasoning/discriminants/distractors, allocation drift, a structural failure, a material duplicate concern, an unresolved semantic concern, or a failed generated-item/final review prevents progression. Failure does not authorize evidence research or a cross-study-unit substitution.

## Second-pilot success criteria

The second 10-question pilot succeeds only if all ten items have evidence-traceability PASS and independent-context PASS; no item contains unsupported claims; no material set-level duplication remains; and at least seven of ten items pass fresh independent final review. The outcome must also show that scenarios, competing concepts, and reasoning depth meet their approved V2 specs, not merely that the artifact validates structurally.

Whether this pilot result warrants scale-up, and any scale-up threshold, is a separate decision requiring explicit approval.
