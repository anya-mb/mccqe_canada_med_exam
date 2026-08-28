from pathlib import Path

from qbank.question_generation_manifest import (
    build_question_generation_manifest,
    validate_question_generation_manifest,
)


REPO = Path(__file__).resolve().parents[1]


def test_manifest_reconciles_frozen_allocation_and_initializes_resumable_jobs():
    manifest, audit = build_question_generation_manifest(REPO)
    result = validate_question_generation_manifest(REPO, manifest, audit)

    assert result.status == "PASS"
    assert audit["reconciliation"] == {
        "ALLOCATION_ADDRESSES_EXPECTED": 1175,
        "ALLOCATION_ADDRESSES_MANIFESTED": 1175,
        "MISSING_ALLOCATION_ADDRESSES": 0,
        "OVERALLOCATED_ADDRESSES": 0,
        "QUESTION_SLOTS": 6086,
        "TOTAL_MANIFEST_QUESTIONS": 6086,
        "UNDERALLOCATED_ADDRESSES": 0,
    }
    assert audit["questions_by_discipline"] == {
        "MED": 1086, "PED": 1000, "OBGYN": 1000,
        "SURG": 1000, "PSY": 1000, "PHELO": 1000,
    }
    assert all(job["generation_status"] == "PENDING_SOURCE_PACKET" for job in manifest["jobs"])
    assert all(job["discipline"] in {"MED", "PED", "OBGYN", "SURG", "PSY", "PHELO"} for job in manifest["jobs"])


def test_manifest_is_deterministic_preserves_metadata_and_splits_large_addresses():
    first_manifest, first_audit = build_question_generation_manifest(REPO)
    second_manifest, second_audit = build_question_generation_manifest(REPO)

    assert first_manifest == second_manifest
    assert first_audit == second_audit
    assert first_manifest["batch_size_policy"] == {
        "algorithm": "DISCIPLINE_CHAPTER_ADDRESS_ORDER_FILL_TO_MAXIMUM",
        "maximum_questions_per_job": 30,
    }
    assignments = [assignment for job in first_manifest["jobs"] for assignment in job["assignments"]]
    assert all("preferred_item_forms" in assignment for assignment in assignments)
    assert all("source_node_ids" in assignment for assignment in assignments)
    assert all(len(job["question_slot_ids"]) == job["question_count"] for job in first_manifest["jobs"])
    assert len({slot for job in first_manifest["jobs"] for slot in job["question_slot_ids"]}) == 6086
    assert first_audit["split_allocation_addresses"] > 0


def test_manifest_excludes_non_generation_rows_and_enforces_single_discipline_jobs():
    manifest, audit = build_question_generation_manifest(REPO)

    manifested = {
        assignment["allocation_address_id"]
        for job in manifest["jobs"]
        for assignment in job["assignments"]
    }
    assert len(manifested) == 1175
    assert audit["safety"] == {
        "CROSS_DISCIPLINE_JOBS": 0,
        "DUPLICATE_JOB_IDS": 0,
        "DUPLICATE_QUESTION_SLOT_IDS": 0,
        "SUPPRESSED_ADDRESSES_MANIFESTED": 0,
        "ZERO_SCOPE_ADDRESSES_MANIFESTED": 0,
    }
