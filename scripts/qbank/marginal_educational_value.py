"""Marginal educational value: what makes one more question worth asking.

Five items on one decision cover one decision. This gate credits novelty per
learner decision, decisive discriminator, reasoning path and contrast structure,
and refuses to credit a changed name, city or age inside the same band.

The comparison deliberately does not run over vignette prose. Prose similarity is
the signal a demographic rewrite defeats, and an agent asked to judge its own
item's novelty against its own prose is the self-certification defect repeating
in a third gate family. The adjudicator sees structured tuples and is not told
which one it is being asked to admit.
"""

from __future__ import annotations

from typing import Any

from .errors import QbankError


class MarginalEducationalValueError(QbankError):
    """A novelty comparison input is unusable."""


NOVELTY_VERDICTS = (
    "NOVEL_DECISION",
    "NOVEL_REASONING",
    "NOVEL_CONTRAST",
    "NOVEL_CONTEXT_WITH_REAL_PEDAGOGIC_VALUE",
    "REDUNDANT",
)

# A context change earns novelty only when it changes the answer or the reasoning.
QUALIFYING_CONTEXT_CHANGES = frozenset({
    "PREGNANCY_CHANGES_ADMISSIBLE_AGENT",
    "AGE_BAND_CHANGES_DIFFERENTIAL",
    "AGE_BAND_CHANGES_DOSING_RULE",
    "ORGAN_IMPAIRMENT_CHANGES_AGENT",
    "JURISDICTION_CHANGES_LEGAL_DUTY",
    "COMORBIDITY_CHANGES_FIRST_ACTION",
})

NON_QUALIFYING_CONTEXT_CHANGES = frozenset({
    "PATIENT_NAME",
    "SEX_NOT_DECISION_RELEVANT",
    "AGE_INSIDE_SAME_BAND",
    "CITY_OR_SETTING",
    "OCCUPATION_NOT_DECISION_RELEVANT",
    "PRESENTING_COMPLAINT_WORDING",
    "REORDERED_VITAL_SIGNS",
})

TUPLE_FIELDS = (
    "learner_decision_id",
    "physician_activity",
    "decisive_discriminator",
    "option_set_archetype",
    "competitor_concept_ids",
)

# Consecutive redundant candidates at which a topic stops. Revisited at G2.
STOP_2_CONSECUTIVE_REDUNDANT = 2


def _validate_tuple(candidate: Any, label: str) -> dict[str, Any]:
    if not isinstance(candidate, dict):
        raise MarginalEducationalValueError(f"{label} must be an object")
    for field in TUPLE_FIELDS:
        if field not in candidate:
            raise MarginalEducationalValueError(f"{label} is missing {field}")
    concepts = candidate["competitor_concept_ids"]
    if not isinstance(concepts, list) or any(not isinstance(row, str) for row in concepts):
        raise MarginalEducationalValueError(f"{label} needs competitor concept ids")
    return candidate


def _context_verdict(candidate: dict[str, Any]) -> bool:
    changes = candidate.get("context_changes", [])
    if not isinstance(changes, list):
        raise MarginalEducationalValueError("context changes must be a list")
    for change in changes:
        if change in NON_QUALIFYING_CONTEXT_CHANGES:
            continue
        if change in QUALIFYING_CONTEXT_CHANGES:
            return True
        raise MarginalEducationalValueError(f"unknown context change class: {change}")
    return False


def assess_marginal_value(
    candidate: dict[str, Any], accepted: list[dict[str, Any]]
) -> dict[str, Any]:
    """Return the novelty verdict of one candidate against every accepted item.

    A candidate is admitted only if it is novel on at least one axis against
    *every* accepted item in the topic; being novel against one and a repeat of
    another is a repeat.
    """
    _validate_tuple(candidate, "candidate")
    for row in accepted:
        _validate_tuple(row, "accepted item")
    if not accepted:
        return {
            "verdict": "NOVEL_DECISION",
            "basis": "FIRST_ITEM_ON_THIS_TOPIC",
            "compared_against": 0,
        }

    per_item: list[dict[str, Any]] = []
    for row in accepted:
        verdict = "REDUNDANT"
        basis = "SAME_DECISION_DISCRIMINATOR_AND_CONTRAST_STRUCTURE"
        if candidate["learner_decision_id"] != row["learner_decision_id"] or (
            candidate["physician_activity"] != row["physician_activity"]
        ):
            verdict, basis = "NOVEL_DECISION", "DIFFERENT_LEARNER_DECISION"
        elif candidate["decisive_discriminator"] != row["decisive_discriminator"]:
            verdict, basis = "NOVEL_REASONING", "DIFFERENT_DECISIVE_DISCRIMINATOR"
        else:
            candidate_concepts = set(candidate["competitor_concept_ids"])
            accepted_concepts = set(row["competitor_concept_ids"])
            introduced = candidate_concepts - accepted_concepts
            changes_discrimination = bool(
                candidate.get("newly_tested_discriminations")
            )
            if len(introduced) >= 2 and changes_discrimination:
                verdict, basis = "NOVEL_CONTRAST", "AT_LEAST_TWO_NEW_COMPETITOR_CONCEPTS"
            elif _context_verdict(candidate):
                verdict = "NOVEL_CONTEXT_WITH_REAL_PEDAGOGIC_VALUE"
                basis = "CONTEXT_CHANGE_ALTERS_ANSWER_OR_REASONING"
        per_item.append({
            "compared_with": row.get("item_reference"),
            "verdict": verdict,
            "basis": basis,
        })

    if any(row["verdict"] == "REDUNDANT" for row in per_item):
        return {
            "verdict": "REDUNDANT",
            "basis": "REPEATS_AN_ALREADY_ACCEPTED_ITEM",
            "compared_against": len(accepted),
            "per_item": per_item,
        }
    ranked = [
        value
        for value in NOVELTY_VERDICTS
        if any(row["verdict"] == value for row in per_item)
    ]
    return {
        "verdict": ranked[-1],
        "basis": "NOVEL_AGAINST_EVERY_ACCEPTED_ITEM",
        "compared_against": len(accepted),
        "per_item": per_item,
    }


def should_stop_for_redundancy(recent_verdicts: list[str]) -> bool:
    """STOP-2: the topic stops after k consecutive redundant candidates."""
    if len(recent_verdicts) < STOP_2_CONSECUTIVE_REDUNDANT:
        return False
    tail = recent_verdicts[-STOP_2_CONSECUTIVE_REDUNDANT:]
    return all(value == "REDUNDANT" for value in tail)
