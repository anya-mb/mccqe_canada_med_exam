"""Question opportunities: a meaningful decision, not a slot with room in it.

A fixed question slot says how many items an address was allocated. An
opportunity says which decision a physician actually makes there. The difference
matters because the first can be filled by a weak item and the second cannot: an
opportunity that cannot be answered safely ends in ``NO_SAFE_ITEM`` and that is a
correct, reportable outcome rather than a shortfall.

Nothing here compares an accepted count against a budget, and no state or field
expresses a deficit.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from .errors import QbankError
from .qgen_profiles import assert_no_quota_shaped_fields


class QuestionOpportunityError(QbankError):
    """An opportunity, a transition, or a budget use is invalid."""


OPPORTUNITY_STATES = (
    "CANDIDATE",
    "EVIDENCE_READY",
    "CONTRAST_READY",
    "GENERATABLE",
    "ACCEPTED",
    "REJECTED",
    "NO_SAFE_ITEM",
    "REDUNDANT",
)

TERMINAL_STATES = frozenset({"ACCEPTED", "REJECTED", "NO_SAFE_ITEM", "REDUNDANT"})

PERMITTED_TRANSITIONS: dict[str, frozenset[str]] = {
    "CANDIDATE": frozenset({"EVIDENCE_READY", "REDUNDANT", "NO_SAFE_ITEM"}),
    "EVIDENCE_READY": frozenset({"CONTRAST_READY", "NO_SAFE_ITEM"}),
    "CONTRAST_READY": frozenset({"GENERATABLE", "NO_SAFE_ITEM"}),
    "GENERATABLE": frozenset({"ACCEPTED", "REJECTED", "NO_SAFE_ITEM", "REDUNDANT"}),
    "ACCEPTED": frozenset(),
    "REJECTED": frozenset(),
    "NO_SAFE_ITEM": frozenset(),
    "REDUNDANT": frozenset(),
}

FAIL_CLOSED_REASONS: dict[str, str] = {
    "FAIL_CLOSED_INSUFFICIENT_EVIDENCE": "A_NEW_SOURCE_PACKET",
    "FAIL_CLOSED_UNRESOLVED_CRITICAL_FACT": "A_COMPLETED_LEVEL_3_ADJUDICATION",
    "FAIL_CLOSED_ERRONEOUS_SOURCE_FACT": "A_CORRECTED_OR_SUPERSEDING_SOURCE",
    "FAIL_CLOSED_INSUFFICIENT_ADMISSIBLE_COMPETITORS": "NEW_SEEDS_OR_A_PROFILE_VOCABULARY_ENTRY",
    # Retrieval raised three competitors and judgement against the realised stem
    # left fewer than three. The cause is different from a supply shortfall and is
    # reported as itself rather than as an absent item.
    "FAIL_CLOSED_INSUFFICIENT_SEMANTICALLY_ADMISSIBLE_COMPETITORS": (
        "NEW_SEEDS_OR_A_PROFILE_VOCABULARY_ENTRY"
    ),
    # An authored item rests on a competitor the stem-anchor floor refuses. The
    # option was retrieved and is real, but nothing the realised stem states gives
    # a candidate a reason to consider it, so the item cannot be realised as
    # written. It is a stem-alignment outcome, not a supply shortfall and not the
    # freehand-distractor construction error, so it carries its own reason.
    "FAIL_CLOSED_REALIZED_COMPETITOR_LACKS_STEM_ANCHOR": (
        "A_STEM_THAT_ANCHORS_THE_COMPETITOR_OR_A_DIFFERENT_COMPETITOR"
    ),
    "FAIL_CLOSED_INCOHERENT_OPTION_SET_ARCHETYPE": "AN_AUTHORISED_PROFILE_EXTENSION",
    "FAIL_CLOSED_ANSWER_AMBIGUITY": "NEVER_BY_RETRY",
    "FAIL_CLOSED_REDUNDANT": "A_DIFFERENT_OPPORTUNITY",
    "FAIL_CLOSED_UNINSTANTIABLE_REASONING": "A_RESCOPED_OPPORTUNITY",
}

# A retry is permitted only where the recorded failure was about wording. An
# evidence, fact, admissibility or ambiguity failure is not a wording problem and
# regenerating it is how a quota used to get filled.
RETRYABLE_FAILURE_LEVELS = frozenset({"REALIZATION"})
MAXIMUM_RETRIES = 1

PHYSICIAN_ACTIVITIES = {
    "Assessment/Diagnosis",
    "Management",
    "Communication",
    "Professional Behaviours",
}


def compute_opportunity_id(
    *,
    anchor_study_unit_id: str,
    learner_decision_id: str,
    physician_activity: str,
    item_archetype: str,
    option_set_archetype: str,
    discipline_profile_id: str,
) -> str:
    """Return the deterministic identity of one question opportunity."""
    if physician_activity not in PHYSICIAN_ACTIVITIES:
        raise QuestionOpportunityError(
            f"physician activity is not canonical: {physician_activity}"
        )
    parts = [
        anchor_study_unit_id,
        learner_decision_id,
        physician_activity,
        item_archetype,
        option_set_archetype,
        discipline_profile_id,
    ]
    for part in parts:
        if not isinstance(part, str) or not part:
            raise QuestionOpportunityError("opportunity identity components must be strings")
    digest = hashlib.sha256("".join(parts).encode("utf-8")).hexdigest()
    return f"QOPP-{digest[:24]}"


def open_opportunity(
    *,
    address: dict[str, Any],
    learner_decision_id: str,
    physician_activity: str,
    item_archetype: str,
    option_set_archetype: str,
    educational_purpose: str,
    declared_learner_decisions: list[str],
    existing_opportunities: list[dict[str, Any]],
    anchor_tn_source: str,
    mcc_objective_id: str,
) -> dict[str, Any]:
    """Open one opportunity, or refuse to.

    The existence rule is the whole point: an opportunity may be opened because a
    physician makes this decision at this study unit, and never because the
    address's budget has room left in it.
    """
    if address.get("priority_class") == "NOT_IN_SCOPE":
        raise QuestionOpportunityError(
            "a non-eligible allocation address may never open an opportunity"
        )
    if learner_decision_id not in declared_learner_decisions:
        raise QuestionOpportunityError(
            "learner decision is not in the address's frozen declared decisions: "
            f"{learner_decision_id}"
        )
    if mcc_objective_id not in address.get("mcc_objective_ids", []):
        raise QuestionOpportunityError(
            f"MCC objective is not owned by this address: {mcc_objective_id}"
        )
    budget = int(address.get("maximum_opportunities", 0))
    if len(existing_opportunities) >= budget:
        raise QuestionOpportunityError(
            "opportunities opened would exceed the address's maximum"
        )
    opportunity_id = compute_opportunity_id(
        anchor_study_unit_id=address["study_unit_id"],
        learner_decision_id=learner_decision_id,
        physician_activity=physician_activity,
        item_archetype=item_archetype,
        option_set_archetype=option_set_archetype,
        discipline_profile_id=address["discipline_profile_id"],
    )
    if any(row["opportunity_id"] == opportunity_id for row in existing_opportunities):
        raise QuestionOpportunityError(f"opportunity already exists: {opportunity_id}")
    return {
        "opportunity_id": opportunity_id,
        "allocation_address_id": address["allocation_address_id"],
        "anchor_study_unit_id": address["study_unit_id"],
        "anchor_tn_source": anchor_tn_source,
        "mcc_objective_id": mcc_objective_id,
        "physician_activity": physician_activity,
        "learner_decision_id": learner_decision_id,
        "discipline": address["discipline"],
        "discipline_profile_id": address["discipline_profile_id"],
        "item_archetype": item_archetype,
        "option_set_archetype": option_set_archetype,
        "educational_purpose": educational_purpose,
        "priority_class": address["priority_class"],
        "state": "CANDIDATE",
        "state_history": ["CANDIDATE"],
        "decisive_discriminator": None,
        "retry_count": 0,
    }


def transition_opportunity(
    opportunity: dict[str, Any],
    target_state: str,
    *,
    reason: str | None = None,
    decisive_discriminator: str | None = None,
) -> dict[str, Any]:
    """Move one opportunity to a permitted next state, recording why."""
    current = opportunity.get("state")
    if current not in OPPORTUNITY_STATES:
        raise QuestionOpportunityError(f"unknown current state: {current}")
    if target_state not in PERMITTED_TRANSITIONS[current]:
        raise QuestionOpportunityError(
            f"illegal opportunity transition: {current} to {target_state}"
        )
    if target_state == "NO_SAFE_ITEM":
        if reason not in FAIL_CLOSED_REASONS:
            raise QuestionOpportunityError(
                f"NO_SAFE_ITEM needs a canonical fail-closed reason, got: {reason}"
            )
        opportunity["fail_closed_reason"] = reason
        opportunity["reopens_on"] = FAIL_CLOSED_REASONS[reason]
    if target_state == "EVIDENCE_READY":
        if not decisive_discriminator:
            raise QuestionOpportunityError(
                "EVIDENCE_READY requires a declared decisive discriminator"
            )
        opportunity["decisive_discriminator"] = decisive_discriminator
    if target_state in {"REJECTED", "REDUNDANT"} and reason:
        opportunity["terminal_reason"] = reason
    opportunity["state"] = target_state
    opportunity["state_history"] = list(opportunity.get("state_history", [])) + [target_state]
    return opportunity


def may_retry(opportunity: dict[str, Any], failure_level: str) -> bool:
    """Return whether one realization-level retry is still permitted."""
    if failure_level not in RETRYABLE_FAILURE_LEVELS:
        return False
    return int(opportunity.get("retry_count", 0)) < MAXIMUM_RETRIES


def may_reopen(opportunity: dict[str, Any], new_input: str | None) -> bool:
    """A fail-closed opportunity reopens on a new input and never on a re-run."""
    if opportunity.get("state") != "NO_SAFE_ITEM":
        return False
    expected = opportunity.get("reopens_on")
    if expected in (None, "NEVER_BY_RETRY"):
        return False
    return new_input == expected


def summarize_opportunities(opportunities: list[dict[str, Any]]) -> dict[str, Any]:
    """Summarise a wave without ever reporting a difference from a budget."""
    counts = {state: 0 for state in OPPORTUNITY_STATES}
    for row in opportunities:
        state = row.get("state")
        if state not in counts:
            raise QuestionOpportunityError(f"unknown opportunity state: {state}")
        counts[state] += 1
    fail_closed: dict[str, int] = {}
    for row in opportunities:
        if row.get("state") == "NO_SAFE_ITEM":
            reason = row.get("fail_closed_reason", "UNKNOWN")
            fail_closed[reason] = fail_closed.get(reason, 0) + 1
    summary = {
        "attempted_opportunities": len(opportunities),
        "accepted": counts["ACCEPTED"],
        "no_safe_item": counts["NO_SAFE_ITEM"],
        "rejected": counts["REJECTED"],
        "redundant": counts["REDUNDANT"],
        "in_flight": sum(
            counts[state] for state in OPPORTUNITY_STATES if state not in TERMINAL_STATES
        ),
        "opportunity_state_counts": counts,
        "fail_closed_by_reason": dict(sorted(fail_closed.items())),
    }
    assert_no_quota_shaped_fields(summary, label="opportunity summary")
    return summary


def serialize_opportunity_plan(rows: list[dict[str, Any]]) -> str:
    """Serialize a plan deterministically for hashing or storage."""
    return json.dumps(rows, indent=2, sort_keys=True) + "\n"
