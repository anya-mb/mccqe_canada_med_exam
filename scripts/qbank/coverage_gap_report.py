"""Coverage and gap reporting that separates a narrow topic from a pipeline gap.

Two study units can each hold one accepted item and mean entirely different
things: one covered its only learner decision, the other left three uncovered.
A count cannot tell them apart, so the diagnosis here does not read one, except
as a presence test in the single case of a CORE objective with nothing at all.

The report carries no target column, no percent-of-target and no under-target
flag, because a reporting surface with a hole in it is the easiest way for a
retired quota to come back.
"""

from __future__ import annotations

from typing import Any

from .errors import QbankError
from .qgen_profiles import assert_no_quota_shaped_fields


class CoverageGapReportError(QbankError):
    """A coverage row cannot be built or diagnosed."""


DIAGNOSES = ("NARROW_TOPIC", "PIPELINE_GAP", "DECISIONS_NOT_DECLARED", "NOT_ATTEMPTED")

STANDING_ALARMS = (
    "CORE_OBJECTIVE_WITH_NO_ACCEPTED_ITEM",
    "UNCOVERED_HIGH_PRIORITY_DECISION_AT_CORE",
    "NO_SAFE_ITEM_OUTSTANDING_ACROSS_WAVES",
    "RISING_YIELD_RATE_WITH_RISING_CORE_GAPS",
    "FAIL_CLOSED_CONCENTRATION",
)

FAIL_CLOSED_CONCENTRATION_THRESHOLD = 0.6


def build_coverage_row(
    *,
    address: dict[str, Any],
    mcc_objective_id: str,
    declared_learner_decisions: list[str],
    opportunities: list[dict[str, Any]],
    evidence_gaps: list[dict[str, Any]] | None = None,
    contrast_gaps: list[dict[str, Any]] | None = None,
    wave_id: str,
) -> dict[str, Any]:
    """Build one report row and diagnose it without reading its accepted count."""
    relevant = [
        row
        for row in opportunities
        if row.get("allocation_address_id") == address["allocation_address_id"]
        and row.get("mcc_objective_id") == mcc_objective_id
    ]
    covered = sorted({
        row["learner_decision_id"] for row in relevant if row.get("state") == "ACCEPTED"
    })
    no_safe_item_gaps = [
        {
            "learner_decision_id": row["learner_decision_id"],
            "reason": row.get("fail_closed_reason"),
            "reopens_on": row.get("reopens_on"),
        }
        for row in relevant
        if row.get("state") == "NO_SAFE_ITEM"
    ]
    accounted = set(covered) | {row["learner_decision_id"] for row in no_safe_item_gaps}
    uncovered = sorted(set(declared_learner_decisions) - accounted)
    state_counts: dict[str, int] = {}
    for row in relevant:
        state_counts[row["state"]] = state_counts.get(row["state"], 0) + 1

    evidence_gaps = list(evidence_gaps or [])
    contrast_gaps = list(contrast_gaps or [])

    if not declared_learner_decisions:
        # The load-bearing guard: a decision list derived from what was generated
        # would be empty by construction and every unit would read NARROW_TOPIC.
        diagnosis = "DECISIONS_NOT_DECLARED"
    elif not relevant:
        diagnosis = "NOT_ATTEMPTED"
    elif (
        address["priority_class"] == "CORE" and not covered
    ) or uncovered or no_safe_item_gaps or evidence_gaps or contrast_gaps:
        diagnosis = "PIPELINE_GAP"
    else:
        diagnosis = "NARROW_TOPIC"

    row = {
        "wave_id": wave_id,
        "mcc_objective_id": mcc_objective_id,
        "allocation_address_id": address["allocation_address_id"],
        "study_unit_id": address["study_unit_id"],
        "discipline": address["discipline"],
        "chapter": address["chapter"],
        "priority_class": address["priority_class"],
        "priority_class_basis": address["priority_class_basis"],
        "opportunities_opened": len(relevant),
        "opportunity_state_counts": dict(sorted(state_counts.items())),
        "accepted_count": len(covered),
        "covered_learner_decisions": covered,
        "uncovered_learner_decisions": uncovered,
        "no_safe_item_gaps": no_safe_item_gaps,
        "evidence_gaps": evidence_gaps,
        "contrast_gaps": contrast_gaps,
        "diagnosis": diagnosis,
    }
    assert_no_quota_shaped_fields(row, label="coverage row")
    return row


def rollup(rows: list[dict[str, Any]], key: str) -> dict[str, dict[str, Any]]:
    """Roll rows up by any grouping key, carrying the companion set every time."""
    grouped: dict[str, dict[str, Any]] = {}
    for row in rows:
        bucket = grouped.setdefault(
            str(row.get(key)),
            {
                "opportunities_opened": 0,
                "accepted": 0,
                "no_safe_item": 0,
                "uncovered_learner_decisions": 0,
                "evidence_gaps": 0,
                "contrast_gaps": 0,
                "diagnoses": {},
            },
        )
        bucket["opportunities_opened"] += row["opportunities_opened"]
        bucket["accepted"] += row["accepted_count"]
        bucket["no_safe_item"] += len(row["no_safe_item_gaps"])
        bucket["uncovered_learner_decisions"] += len(row["uncovered_learner_decisions"])
        bucket["evidence_gaps"] += len(row["evidence_gaps"])
        bucket["contrast_gaps"] += len(row["contrast_gaps"])
        bucket["diagnoses"][row["diagnosis"]] = (
            bucket["diagnoses"].get(row["diagnosis"], 0) + 1
        )
    return dict(sorted(grouped.items()))


def evaluate_standing_alarms(
    rows: list[dict[str, Any]],
    *,
    fail_closed_by_reason: dict[str, int],
    previous_wave_metrics: dict[str, Any] | None = None,
    outstanding_no_safe_item_waves: dict[str, int] | None = None,
) -> list[dict[str, Any]]:
    """Return every standing alarm that fires for this wave."""
    alarms: list[dict[str, Any]] = []
    core_objectives_without_items = sorted({
        row["mcc_objective_id"]
        for row in rows
        if row["priority_class"] == "CORE" and row["accepted_count"] == 0
    })
    accepted_objectives = {
        row["mcc_objective_id"] for row in rows if row["accepted_count"] > 0
    }
    truly_absent = [
        objective
        for objective in core_objectives_without_items
        if objective not in accepted_objectives
    ]
    if truly_absent:
        alarms.append({
            "alarm": "CORE_OBJECTIVE_WITH_NO_ACCEPTED_ITEM",
            "mcc_objective_ids": truly_absent,
        })
    uncovered_core = sorted({
        decision
        for row in rows
        if row["priority_class"] == "CORE"
        for decision in row["uncovered_learner_decisions"]
    })
    if uncovered_core:
        alarms.append({
            "alarm": "UNCOVERED_HIGH_PRIORITY_DECISION_AT_CORE",
            "learner_decision_ids": uncovered_core,
        })
    outstanding = outstanding_no_safe_item_waves or {}
    persistent = sorted(key for key, waves in outstanding.items() if waves > 1)
    if persistent:
        alarms.append({
            "alarm": "NO_SAFE_ITEM_OUTSTANDING_ACROSS_WAVES",
            "opportunity_ids": persistent,
        })

    total_fail_closed = sum(fail_closed_by_reason.values())
    if total_fail_closed:
        for reason, count in sorted(fail_closed_by_reason.items()):
            if count / total_fail_closed > FAIL_CLOSED_CONCENTRATION_THRESHOLD:
                alarms.append({
                    "alarm": "FAIL_CLOSED_CONCENTRATION",
                    "reason": reason,
                    "share": round(count / total_fail_closed, 4),
                })

    if previous_wave_metrics:
        previous_rate = previous_wave_metrics.get("safe_yield_rate")
        previous_gaps = previous_wave_metrics.get("uncovered_core_decisions")
        attempted = sum(row["opportunities_opened"] for row in rows)
        accepted = sum(row["accepted_count"] for row in rows)
        current_rate = (accepted / attempted) if attempted else 0.0
        if (
            previous_rate is not None
            and previous_gaps is not None
            and current_rate > previous_rate
            and len(uncovered_core) > previous_gaps
        ):
            alarms.append({
                "alarm": "RISING_YIELD_RATE_WITH_RISING_CORE_GAPS",
                "previous_rate": previous_rate,
                "current_rate": round(current_rate, 4),
            })
    return alarms


def build_coverage_and_yield_report(
    *,
    wave_id: str,
    rows: list[dict[str, Any]],
    fail_closed_by_reason: dict[str, int],
    previous_wave_metrics: dict[str, Any] | None = None,
    outstanding_no_safe_item_waves: dict[str, int] | None = None,
) -> dict[str, Any]:
    """Assemble the whole deterministic coverage and yield report."""
    report = {
        "schema_version": "1.0",
        "scope": "QBANK_COVERAGE_AND_YIELD",
        "wave_id": wave_id,
        "rows": sorted(
            rows, key=lambda row: (row["allocation_address_id"], row["mcc_objective_id"])
        ),
        "rollups": {
            "by_discipline": rollup(rows, "discipline"),
            "by_chapter": rollup(rows, "chapter"),
            "by_priority_class": rollup(rows, "priority_class"),
            "by_study_unit": rollup(rows, "study_unit_id"),
        },
        "fail_closed_by_reason": dict(sorted(fail_closed_by_reason.items())),
        "standing_alarms": evaluate_standing_alarms(
            rows,
            fail_closed_by_reason=fail_closed_by_reason,
            previous_wave_metrics=previous_wave_metrics,
            outstanding_no_safe_item_waves=outstanding_no_safe_item_waves,
        ),
    }
    assert_no_quota_shaped_fields(report, label="coverage and yield report")
    return report
