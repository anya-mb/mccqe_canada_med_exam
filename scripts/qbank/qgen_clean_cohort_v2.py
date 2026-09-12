"""Outcome-blind clean cohort selection and reservation transitions."""

from __future__ import annotations

import copy
from collections import Counter
from typing import Any, Mapping

from .qgen_exposure_registry import canonical_content_hash


DISCIPLINES = ("MED", "PED", "OBGYN", "SURG", "PSY", "PHELO")


class CleanCohortSelectionError(ValueError):
    """The registry cannot safely supply the requested balanced cohort."""


def _eligible_input_rows(registry: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for row in registry.get("rows", []):
        if row.get("clean_transfer_eligible") is not True:
            continue
        if row.get("reservation_status") not in {"AVAILABLE", "RELEASED_UNINSPECTED"}:
            continue
        rows.append({
            "study_unit_id": row["study_unit_id"],
            "discipline": row["discipline"],
            "study_unit": row["study_unit"],
            "max_exposure_level": row["max_exposure_level"],
            "exposure_status": row["exposure_status"],
            "reservation_status": row["reservation_status"],
            "source_event_ids": list(row.get("source_event_ids", [])),
        })
    return sorted(rows, key=lambda row: (row["discipline"], row["study_unit_id"]))


def select_clean_cohort(registry: Mapping[str, Any]) -> dict[str, Any]:
    """Select three, or if necessary two, clean units per discipline."""
    eligible = _eligible_input_rows(registry)
    by_discipline = {
        discipline: [row for row in eligible if row["discipline"] == discipline]
        for discipline in DISCIPLINES
    }
    insufficient = {discipline: len(rows) for discipline, rows in by_discipline.items() if len(rows) < 2}
    if insufficient:
        details = ", ".join(f"{discipline}={count}" for discipline, count in insufficient.items())
        raise CleanCohortSelectionError(f"INSUFFICIENT_CLEAN_UNITS: {details}")
    per_discipline = 3 if all(len(rows) >= 3 for rows in by_discipline.values()) else 2
    selected = []
    for discipline in DISCIPLINES:
        for ordinal, row in enumerate(by_discipline[discipline][:per_discipline], start=1):
            selected.append({
                "cohort_row_id": f"CLEAN-V2-{discipline}-{ordinal:02d}",
                **row,
            })
    normalized_input = {
        "registry_content_sha256": registry.get("content_sha256"),
        "eligible_rows": eligible,
    }
    result: dict[str, Any] = {
        "schema_version": "QGEN_CLEAN_COHORT_SELECTION_V2",
        "selector_version": "COHORT_SELECTOR_V2",
        "selection_rule": "AVAILABLE_CLEAN_THEN_DISCIPLINE_THEN_CANONICAL_STUDY_UNIT_ID",
        "selection_visibility": "EXPOSURE_AND_STABLE_IDENTITY_METADATA_ONLY",
        "prohibited_outcome_fields_inspected": False,
        "exposure_registry_sha256": registry.get("content_sha256"),
        "selection_input_sha256": canonical_content_hash(normalized_input),
        "cohort_size": len(selected),
        "per_discipline": dict(Counter(row["discipline"] for row in selected)),
        "balanced": True,
        "execution_status": "RESERVED_NOT_UNBLINDED",
        "rows": selected,
    }
    result["content_sha256"] = canonical_content_hash(result)
    return result


def reserve_selected_units(registry: Mapping[str, Any], cohort: Mapping[str, Any]) -> dict[str, Any]:
    selected = {row["study_unit_id"] for row in cohort.get("rows", [])}
    result = copy.deepcopy(dict(registry))
    for row in result.get("rows", []):
        if row["study_unit_id"] in selected:
            if row.get("reservation_status") not in {"AVAILABLE", "RELEASED_UNINSPECTED"}:
                raise CleanCohortSelectionError(f"UNIT_NOT_AVAILABLE: {row['study_unit_id']}")
            row["reservation_status"] = "RESERVED_FOR_CLEAN_VALIDATION"
            row["reservation_cohort_sha256"] = cohort["content_sha256"]
    result["schema_version"] = "QGEN_EXPOSURE_REGISTRY_V1_RESERVED"
    result["parent_registry_content_sha256"] = registry.get("content_sha256")
    result["reserved_cohort_content_sha256"] = cohort["content_sha256"]
    result["content_sha256"] = canonical_content_hash(result)
    return result


def release_uninspected(
    registry: Mapping[str, Any], study_unit_id: str, proof: Mapping[str, Any]
) -> dict[str, Any]:
    required = {
        "never_semantically_unblinded",
        "no_candidate_supply_inspection",
        "no_evidence_authoring",
        "no_question_generation",
        "no_architecture_use",
        "not_abandoned_due_to_outcome_information",
    }
    if any(proof.get(field) is not True for field in required):
        raise CleanCohortSelectionError("RELEASE_PROOF_INCOMPLETE")
    result = copy.deepcopy(dict(registry))
    row = next((row for row in result.get("rows", []) if row["study_unit_id"] == study_unit_id), None)
    if row is None or row.get("reservation_status") != "RESERVED_FOR_CLEAN_VALIDATION":
        raise CleanCohortSelectionError(f"UNIT_NOT_RESERVED: {study_unit_id}")
    row["reservation_status"] = "RELEASED_UNINSPECTED"
    row["release_proof"] = {field: True for field in sorted(required)}
    result["content_sha256"] = canonical_content_hash(result)
    return result
