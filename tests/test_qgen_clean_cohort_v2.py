import copy
import json

import pytest

from scripts.qbank.qgen_clean_cohort_v2 import (
    CleanCohortSelectionError,
    release_uninspected,
    reserve_selected_units,
    select_clean_cohort,
)
from scripts.qbank.qgen_cleanliness_validator_v2 import validate_clean_cohort


DISCIPLINES = ("MED", "PED", "OBGYN", "SURG", "PSY", "PHELO")


def _registry(per_discipline: int) -> dict:
    rows = []
    for discipline in DISCIPLINES:
        for ordinal in range(per_discipline):
            rows.append({
                "study_unit_id": f"SU-{discipline}-{ordinal:02d}",
                "discipline": discipline,
                "study_unit": f"{discipline} unit {ordinal}",
                "max_exposure_level": 1,
                "exposure_status": "METADATA_ONLY",
                "clean_transfer_eligible": True,
                "reservation_status": "AVAILABLE",
                "source_event_ids": [f"EV-{discipline}-{ordinal:02d}"],
            })
    return {"schema_version": "QGEN_EXPOSURE_REGISTRY_V1", "content_sha256": "registry-hash", "rows": rows}


def test_selector_prefers_balanced_18_by_canonical_order():
    registry = _registry(4)
    result = select_clean_cohort(registry)
    assert result["cohort_size"] == 18
    assert result["per_discipline"] == {discipline: 3 for discipline in DISCIPLINES}
    assert [row["study_unit_id"] for row in result["rows"] if row["discipline"] == "MED"] == [
        "SU-MED-00", "SU-MED-01", "SU-MED-02"
    ]


def test_selector_falls_back_to_balanced_12():
    registry = _registry(3)
    registry["rows"] = [
        row for row in registry["rows"]
        if not (row["discipline"] == "PSY" and row["study_unit_id"].endswith("02"))
    ]
    result = select_clean_cohort(registry)
    assert result["cohort_size"] == 12
    assert result["per_discipline"] == {discipline: 2 for discipline in DISCIPLINES}


def test_selector_refuses_unbalanced_cohort_when_any_discipline_has_fewer_than_two():
    registry = _registry(2)
    registry["rows"] = [row for row in registry["rows"] if row["discipline"] != "PSY" or row["study_unit_id"].endswith("00")]
    with pytest.raises(CleanCohortSelectionError, match="INSUFFICIENT_CLEAN_UNITS: PSY=1"):
        select_clean_cohort(registry)


def test_selector_ignores_prohibited_outcome_fields():
    left = _registry(3)
    right = copy.deepcopy(left)
    for index, row in enumerate(left["rows"]):
        row.update(candidate_count=index, bundle_readiness="HIGH", model_proposal_yield=99)
    for index, row in enumerate(right["rows"]):
        row.update(candidate_count=1000 - index, bundle_readiness="LOW", model_proposal_yield=0)
    assert select_clean_cohort(left)["content_sha256"] == select_clean_cohort(right)["content_sha256"]


def test_reservation_marks_only_selected_available_rows():
    registry = _registry(3)
    cohort = select_clean_cohort(registry)
    reserved = reserve_selected_units(registry, cohort)
    selected = {row["study_unit_id"] for row in cohort["rows"]}
    for row in reserved["rows"]:
        expected = "RESERVED_FOR_CLEAN_VALIDATION" if row["study_unit_id"] in selected else "AVAILABLE"
        assert row["reservation_status"] == expected


def test_release_requires_affirmative_never_inspected_proof():
    registry = _registry(3)
    cohort = select_clean_cohort(registry)
    reserved = reserve_selected_units(registry, cohort)
    study_unit_id = cohort["rows"][0]["study_unit_id"]
    with pytest.raises(CleanCohortSelectionError, match="RELEASE_PROOF_INCOMPLETE"):
        release_uninspected(reserved, study_unit_id, {"never_semantically_unblinded": True})
    released = release_uninspected(reserved, study_unit_id, {
        "never_semantically_unblinded": True,
        "no_candidate_supply_inspection": True,
        "no_evidence_authoring": True,
        "no_question_generation": True,
        "no_architecture_use": True,
        "not_abandoned_due_to_outcome_information": True,
    })
    row = next(row for row in released["rows"] if row["study_unit_id"] == study_unit_id)
    assert row["reservation_status"] == "RELEASED_UNINSPECTED"


def test_independent_validator_catches_direct_historical_semantic_overlap(tmp_path):
    registry = _registry(3)
    cohort = select_clean_cohort(registry)
    reserved = reserve_selected_units(registry, cohort)
    clean = validate_clean_cohort(tmp_path, cohort, reserved)
    assert clean["verdict"] == "PASS"
    assert clean["clean_cohort_overlaps"] == 0

    path = tmp_path / "research/qgen/history/prerequisites.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({
        "schema_version": "CLEAN_TRANSFER18_PREREQUISITES_V1",
        "rows": [{"study_unit_id": cohort["rows"][0]["study_unit_id"]}],
    }))
    failed = validate_clean_cohort(tmp_path, cohort, reserved)
    assert failed["verdict"] == "FAIL"
    assert failed["clean_cohort_overlaps"] == 1
    assert failed["direct_historical_overlap"][0]["artifact_path"] == "research/qgen/history/prerequisites.json"
