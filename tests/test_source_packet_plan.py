from pathlib import Path
from copy import deepcopy

from qbank.source_packet_plan import (
    build_source_packet_plan,
    validate_source_packet_plan,
)


REPO = Path(__file__).resolve().parents[1]


def test_source_plan_maps_every_frozen_job_and_address():
    plan, audit = build_source_packet_plan(REPO)
    result = validate_source_packet_plan(REPO, plan, audit)

    assert result.status == "PASS"
    assert audit["reconciliation"] == {
        "GENERATION_JOBS_EXPECTED": 220,
        "GENERATION_JOBS_MAPPED": 220,
        "ALLOCATION_ADDRESSES_EXPECTED": 1175,
        "ALLOCATION_ADDRESSES_MAPPED": 1175,
        "SOURCE_REQUIREMENT_GAPS": 0,
    }


def test_source_plan_is_deterministic_and_reuses_complete_split_address_requirements():
    first_plan, first_audit = build_source_packet_plan(REPO)
    second_plan, second_audit = build_source_packet_plan(REPO)

    assert first_plan == second_plan
    assert first_audit == second_audit
    assert all(
        packet_ids == first_plan["allocation_address_source_packet_ids"][address_id]
        for address_id, packet_ids in first_plan["allocation_address_source_packet_ids"].items()
    )
    assert first_audit["reuse"]["SPLIT_ADDRESSES_REUSING_SOURCE_PACKETS"] == 158


def test_every_packet_is_pending_and_contains_later_research_contract():
    plan, _ = build_source_packet_plan(REPO)

    for packet in plan["source_packets"]:
        assert packet["status"] == "PENDING_RESEARCH"
        assert packet["evidence_requirement_key"]
        assert packet["covered_allocation_address_ids"]
        assert packet["covered_generation_job_ids"]
        assert packet["evidence_requirement_types"]
        assert packet["source_family_targets"]
        assert packet["freshness"] in {"HIGH", "MODERATE", "LOW"}
        assert packet["jurisdiction"] in {
            "CANADA_NATIONAL",
            "PROVINCIAL_OR_TERRITORIAL",
            "MIXED",
            "NOT_JURISDICTION_SENSITIVE",
        }
        assert packet["authoritative_sources"] == []
        assert packet["supported_recommendations"] == []


def test_cross_address_packet_reuse_has_a_canonical_recorded_basis():
    plan, audit = build_source_packet_plan(REPO)

    reused = [
        packet for packet in plan["source_packets"]
        if len(packet["covered_allocation_address_ids"]) > 1
    ]
    assert all(packet["cross_address_reuse_basis"] for packet in reused)
    assert audit["reuse"]["PACKETS_WITH_UNSUPPORTED_REUSE"] == 0


def test_research_batches_are_deterministic_and_bounded():
    plan, audit = build_source_packet_plan(REPO)

    packet_ids = [packet_id for batch in plan["research_batches"] for packet_id in batch["source_packet_ids"]]
    assert len(packet_ids) == len(set(packet_ids)) == len(plan["source_packets"])
    assert all(1 <= len(batch["source_packet_ids"]) <= 10 for batch in plan["research_batches"])
    assert audit["research_batches"]["RESEARCH_BATCH_COUNT"] == len(plan["research_batches"])


def test_validator_rejects_unknown_packet_coverage_references():
    plan, audit = build_source_packet_plan(REPO)
    invalid = deepcopy(plan)
    invalid["source_packets"][0]["covered_allocation_address_ids"].append("UNKNOWN-ADDRESS")
    invalid["source_packets"][0]["cross_address_reuse_basis"] = "EXACT_CANONICAL_SOURCE_NODES_AND_MCC_OBJECTIVES"

    assert validate_source_packet_plan(REPO, invalid, audit).status == "FAIL"


def test_source_priority_and_current_guidance_policy_are_explicit():
    plan, _ = build_source_packet_plan(REPO)

    assert plan["plan_input"]["TORONTO_NOTES_CURRENT_GUIDANCE_AUTHORITY"] is False
    assert plan["source_priority_hierarchy"][:2] == [
        "CANADIAN_NATIONAL_OR_PROVINCIAL_GUIDELINE_OR_REGULATOR",
        "CANADIAN_SPECIALTY_SOCIETY",
    ]


def test_validator_rejects_an_audit_that_reports_unsupported_reuse():
    plan, audit = build_source_packet_plan(REPO)
    invalid_audit = deepcopy(audit)
    invalid_audit["reuse"]["PACKETS_WITH_UNSUPPORTED_REUSE"] = 1

    assert validate_source_packet_plan(REPO, plan, invalid_audit).status == "FAIL"


def test_canonical_freshness_metadata_controls_screening_requirements():
    plan, _ = build_source_packet_plan(REPO)
    address_packet_ids = plan["allocation_address_source_packet_ids"]["SU-FM-03"]
    packets = {packet["source_packet_id"]: packet for packet in plan["source_packets"]}
    screening_packets = [packets[packet_id] for packet_id in address_packet_ids if "SCREENING" in packets[packet_id]["evidence_requirement_types"]]

    assert screening_packets
    assert all(packet["freshness"] == "HIGH" for packet in screening_packets)
