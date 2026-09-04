"""SAFE_YIELD accounting and the restated scale gates.

A wave does not succeed by generating every planned opportunity and does not fail
by failing many closed. It succeeds when everything it accepted is safe, its
coverage accounting is honest, and its refusals carry reasons.

Two accounting rules exist because of what R4 showed. An item accepted only by a
gate family that returned one verdict all wave does not count, because such a
family predicted nothing. And a wave that accepted nothing fails regardless of
how well-reasoned its refusals were, because a gate that rejects everything is as
uninformative as one that accepts everything.
"""

from __future__ import annotations

from typing import Any

from .errors import QbankError
from .qgen_profiles import assert_no_quota_shaped_fields


class SafeYieldGateError(QbankError):
    """A gate input is unusable."""


INVARIANTS = (
    "FACTUAL_ERRORS",
    "NUMERIC_ERRORS",
    "UNSUPPORTED_CLAIMS",
    "AMBIGUOUS_BEST_ANSWERS",
)

GATES = ("G0", "G1", "G2", "G3", "G4")

FAIL_CLOSED_CONCENTRATION_THRESHOLD = 0.6
# A wave with one or two fail-closed outcomes cannot have a concentration
# problem: one refusal is trivially 100 per cent of one refusal. The alarm is
# about a reason class dominating a wave, so it needs a wave to dominate.
FAIL_CLOSED_CONCENTRATION_MINIMUM = 3

STOP_RULES = (
    "STOP_1_DECISION_COVERAGE",
    "STOP_2_REDUNDANCY",
    "STOP_3_COMPETITOR_EXHAUSTION",
    "STOP_4_EVIDENCE_COST",
    "STOP_5_MARGINAL_VALUE",
    "STOP_6_BUDGET",
)


def monitor_verdict_variance(gate_verdicts: dict[str, list[str]]) -> dict[str, Any]:
    """Report any gate family that returned a single distinct verdict all wave.

    This is finding 1 turned into an accounting rule: a gate whose output is
    constant across the outcome it is meant to predict has no discriminating
    power, whatever its pass rate looks like.
    """
    uninformative = sorted(
        family
        for family, verdicts in gate_verdicts.items()
        if verdicts and len(set(verdicts)) == 1
    )
    return {
        "gate_families": dict(sorted(
            (family, sorted(set(verdicts))) for family, verdicts in gate_verdicts.items()
        )),
        "uninformative_gate_families": uninformative,
        "verdict_variance": "PASS" if not uninformative else "GATE_UNINFORMATIVE",
    }


def compute_safe_yield(items: list[dict[str, Any]]) -> dict[str, Any]:
    """Count independently accepted items, and say what was excluded and why."""
    accepted: list[str] = []
    excluded: list[dict[str, Any]] = []
    for item in items:
        item_id = item.get("item_id")
        if not isinstance(item_id, str) or not item_id:
            raise SafeYieldGateError("safe-yield item needs an id")
        reasons: list[str] = []
        if not item.get("common_core_gates_pass"):
            reasons.append("COMMON_CORE_GATE_FAILED")
        if item.get("unresolved_critical_facts"):
            reasons.append("UNRESOLVED_CRITICAL_FACT")
        if item.get("erroneous_source_value_reached_surface"):
            reasons.append("ERRONEOUS_SOURCE_VALUE_REACHED_SURFACE")
        if item.get("admissibility_verdict") != "ADMISSIBLE":
            reasons.append("OPTION_SET_INADMISSIBLE")
        if item.get("independent_verification") != "PASS":
            reasons.append("INDEPENDENT_VERIFICATION_FAILED")
        if item.get("novelty_verdict") == "REDUNDANT":
            reasons.append("REDUNDANT")
        if item.get("repaired_after_independent_review"):
            reasons.append("REPAIRED_AFTER_INDEPENDENT_REVIEW")
        if item.get("accepted_only_by_uninformative_gate"):
            reasons.append("ACCEPTED_ONLY_BY_UNINFORMATIVE_GATE")
        if reasons:
            excluded.append({"item_id": item_id, "reasons": sorted(reasons)})
        else:
            accepted.append(item_id)
    return {
        "safe_yield": len(accepted),
        "accepted_item_ids": sorted(accepted),
        "excluded_items": sorted(excluded, key=lambda row: row["item_id"]),
    }


def evaluate_stop_rules(
    *,
    high_priority_decisions_settled: bool,
    consecutive_redundant: int,
    redundancy_stop_k: int,
    admissible_competitors_remaining: int,
    remaining_needs_new_evidence_for_supporting_only: bool,
    remaining_novel_only_on_non_qualifying_context: bool,
    opportunities_opened: int,
    maximum_opportunities: int,
) -> list[str]:
    """Return every stop rule that fires. An unused slot is never a reason to go on."""
    fired: list[str] = []
    if high_priority_decisions_settled:
        fired.append("STOP_1_DECISION_COVERAGE")
    if consecutive_redundant >= redundancy_stop_k:
        fired.append("STOP_2_REDUNDANCY")
    if admissible_competitors_remaining < 3:
        fired.append("STOP_3_COMPETITOR_EXHAUSTION")
    if remaining_needs_new_evidence_for_supporting_only:
        fired.append("STOP_4_EVIDENCE_COST")
    if remaining_novel_only_on_non_qualifying_context:
        fired.append("STOP_5_MARGINAL_VALUE")
    if opportunities_opened >= maximum_opportunities:
        fired.append("STOP_6_BUDGET")
    return fired


def _invariant_failures(defect_counts: dict[str, int]) -> list[str]:
    return sorted(
        invariant
        for invariant in INVARIANTS
        if int(defect_counts.get(invariant, 0)) != 0
    )


def evaluate_gate(
    gate: str,
    *,
    summary: dict[str, Any],
    safe_yield: dict[str, Any],
    defect_counts_in_accepted: dict[str, int],
    evidence_entailment: str,
    verdict_variance: dict[str, Any],
    coverage_rows: list[dict[str, Any]] | None = None,
    redundancy_positive_control_rejected: bool | None = None,
    non_accepted_reasons_valid: bool = True,
    lone_key_option_category_failures: int = 0,
    accepted_items_cover_their_declared_decision: bool = True,
    severity_or_category_mismatch_failures: int = 0,
) -> dict[str, Any]:
    """Evaluate one restated scale gate."""
    if gate not in GATES:
        raise SafeYieldGateError(f"unknown gate: {gate}")
    failures: list[str] = []
    for invariant in _invariant_failures(defect_counts_in_accepted):
        failures.append(f"INVARIANT_BREACHED: {invariant}")
    if evidence_entailment != "PASS":
        failures.append("INVARIANT_BREACHED: EVIDENCE_ENTAILMENT")
    if verdict_variance.get("verdict_variance") != "PASS":
        failures.append("GATE_UNINFORMATIVE")

    if gate != "G0":
        if safe_yield["safe_yield"] < 1:
            failures.append("SAFE_YIELD_IS_ZERO")
        if not non_accepted_reasons_valid:
            failures.append("NON_ACCEPTED_OPPORTUNITY_LACKS_A_VALID_REASON")
        fail_closed = summary.get("fail_closed_by_reason", {})
        total = sum(fail_closed.values())
        if total >= FAIL_CLOSED_CONCENTRATION_MINIMUM:
            for reason, count in fail_closed.items():
                if count / total > FAIL_CLOSED_CONCENTRATION_THRESHOLD:
                    failures.append(f"FAIL_CLOSED_CONCENTRATION: {reason}")
    if gate in {"G1", "G3"} and lone_key_option_category_failures:
        failures.append("LONE_KEY_OPTION_CATEGORY_PRESENT")
    if gate == "G3" and severity_or_category_mismatch_failures:
        failures.append("SEVERITY_OR_CATEGORY_MISMATCH_PRESENT")
    if gate in {"G2", "G3"} and redundancy_positive_control_rejected is not True:
        failures.append("REDUNDANCY_POSITIVE_CONTROL_DID_NOT_FIRE")
    if gate == "G1" and accepted_items_cover_their_declared_decision is not True:
        failures.append("AN_ACCEPTED_ITEM_DOES_NOT_COVER_ITS_DECLARED_DECISION")
    # CORE decision coverage is a G2 criterion and above. G1 is a three-item
    # feasibility probe against a bounded pool: it asks whether the pipeline can
    # produce something safe and refuse the rest with reasons, not whether a
    # topic has been covered. Applying the coverage bar here would make every
    # micro pilot that attempts a hard CORE decision fail for attempting it.
    if gate in {"G2", "G3", "G4"} and coverage_rows is not None:
        unresolved = [
            row
            for row in coverage_rows
            if row["priority_class"] == "CORE" and row["uncovered_learner_decisions"]
        ]
        if unresolved:
            failures.append("CORE_DECISION_NEITHER_ACCEPTED_NOR_FAIL_CLOSED")

    result = {
        "gate": gate,
        "result": "PASS" if not failures else "FAIL",
        "failures": sorted(set(failures)),
        "reported": {
            "attempted_opportunities": summary.get("attempted_opportunities"),
            "accepted": safe_yield["safe_yield"],
            "fail_closed_count": summary.get("no_safe_item"),
            "fail_closed_by_reason": summary.get("fail_closed_by_reason", {}),
            "rejected_count": summary.get("rejected"),
            "redundant_count": summary.get("redundant"),
        },
        "verdict_variance": verdict_variance,
    }
    assert_no_quota_shaped_fields(result, label=f"gate {gate} result")
    return result


def safe_yield_rate(summary: dict[str, Any], safe_yield: dict[str, Any]) -> float | None:
    """A diagnostic, never an objective.

    The cheapest way to raise this number is to attempt only easy opportunities,
    which is why it is reported per priority class and why a rising rate beside
    rising uncovered CORE decisions is a defined alarm rather than a success.
    """
    attempted = int(summary.get("attempted_opportunities", 0))
    if not attempted:
        return None
    return round(safe_yield["safe_yield"] / attempted, 4)
