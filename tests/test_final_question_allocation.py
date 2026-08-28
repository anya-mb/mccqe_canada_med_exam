from pathlib import Path

from qbank.final_question_allocation import (
    build_final_question_allocation,
    hamilton_allocate,
    validate_final_question_allocation,
)


REPO = Path(__file__).resolve().parents[1]


def test_hamilton_allocation_uses_address_id_for_exact_remainder_ties():
    rows = [
        {"allocation_address_id": "SU-X-02", "coverage_weight": 1},
        {"allocation_address_id": "SU-X-01", "coverage_weight": 1},
        {"allocation_address_id": "SU-X-03", "coverage_weight": 1},
    ]

    assert hamilton_allocate(rows, 2) == {"SU-X-01": 1, "SU-X-02": 1, "SU-X-03": 0}


def test_final_allocation_obeys_frozen_budgets_and_minima():
    allocation, audit = build_final_question_allocation(REPO)

    assert audit["reconciliation"]["TOTAL_ALLOCATED_QUESTIONS"] == 6086
    assert audit["discipline_budgets"] == {
        "MED": 1086, "PED": 1000, "OBGYN": 1000,
        "SURG": 1000, "PSY": 1000, "PHELO": 1000,
    }
    assert audit["minimum_totals"] == {
        "MED": 1086, "PED": 187, "OBGYN": 131,
        "SURG": 424, "PSY": 106, "PHELO": 138,
        "TOTAL_EFFECTIVE_MINIMUM": 2072,
    }
    med_rows = [row for row in allocation["allocation_addresses"] if row["discipline"] == "MED"]
    assert all(row["final_question_count"] == row["effective_minimum"] for row in med_rows)


def test_final_allocation_preserves_scope_ownership_component_and_mcc_safety():
    allocation, audit = build_final_question_allocation(REPO)
    result = validate_final_question_allocation(REPO, allocation, audit)

    assert result.status == "PASS"
    assert audit["address_counts"] == {
        "TOTAL_ALLOCATION_ADDRESSES": 1507,
        "ELIGIBLE_ALLOCATION_ADDRESSES": 1175,
        "SUPPRESSED_ALLOCATION_ADDRESSES": 31,
        "ZERO_SCOPE_ALLOCATION_ADDRESSES": 301,
    }
    assert audit["planning_conflicts"]["PLANNING_CONFLICTS"] == 18
    assert audit["ownership_safety"]["OWNERSHIP_SUPPRESSION_VIOLATIONS"] == 0
    assert audit["component_safety"]["COMPONENT_PARENT_DOUBLE_ALLOCATION"] == 0
    assert audit["mcc_coverage"]["TRUE_MCC_ALLOCATION_GAPS"] == 0
    assert audit["determinism"]["ALLOCATION_REBUILD_DETERMINISTIC"] == "PASS"
    assert all(
        row["final_question_count"] == 0
        for row in allocation["allocation_addresses"]
        if row["allocation_status"] != "ELIGIBLE"
    )


def test_final_allocation_is_byte_stable_and_uses_committed_mi_routes():
    first_allocation, first_audit = build_final_question_allocation(REPO)
    second_allocation, second_audit = build_final_question_allocation(REPO)

    assert first_allocation == second_allocation
    assert first_audit == second_audit
    mi = {
        row["allocation_address_id"]: row["discipline"]
        for row in first_allocation["allocation_addresses"]
        if row["chapter"] == "MI" and row["allocation_status"] == "ELIGIBLE"
    }
    assert sum(discipline == "MED" for discipline in mi.values()) == 18
    assert sum(discipline == "SURG" for discipline in mi.values()) == 8
    assert all(
        row["final_question_count"] == 0
        for row in first_allocation["allocation_addresses"]
        if row["allocation_status"] == "ZERO_BY_SCOPE_METADATA"
        and row["raw_minimum_question_coverage"] > 0
    )
