from copy import deepcopy
from pathlib import Path

import pytest

from qbank.jsonio import read_json
from qbank.source_packet_population import load_integrated_source_packet_populations


REPO = Path(__file__).resolve().parents[1]


def _plan() -> dict:
    return read_json(REPO / "research/qgen/source_packet_plan.json")


def _population(packet_statuses: dict[str, str]) -> dict:
    return {
        "research_batch_id": "SRB-001",
        "source_packets": [
            {"source_packet_id": packet_id, "status": status}
            for packet_id, status in packet_statuses.items()
        ],
    }


def test_readiness_has_exactly_one_record_for_each_of_220_manifest_jobs() -> None:
    from qbank.generation_source_state import build_generation_source_readiness

    readiness = build_generation_source_readiness(
        REPO, load_integrated_source_packet_populations(REPO)
    )

    assert len(readiness["jobs"]) == 220
    assert [record["job_id"] for record in readiness["jobs"]] == [
        job["job_id"]
        for job in read_json(REPO / "research/qgen/question_generation_manifest.json")["jobs"]
    ]
    assert all(
        {"job_id", "required_source_packet_ids", "packet_statuses", "state",
         "blocking_source_packet_ids", "blocking_reason_categories", "question_count",
         "question_slot_ids"} <= record.keys()
        for record in readiness["jobs"]
    )
    assert all(
        record["required_source_packet_ids"] == _plan()["generation_job_source_packet_ids"][record["job_id"]]
        and [item["source_packet_id"] for item in record["packet_statuses"]]
        == record["required_source_packet_ids"]
        for record in readiness["jobs"]
    )


def test_job_is_source_ready_only_when_every_required_packet_is_ready() -> None:
    from qbank.generation_source_state import build_generation_source_readiness

    required = _plan()["generation_job_source_packet_ids"]["QGEN-MED-001"]
    ready = build_generation_source_readiness(
        REPO, [_population({packet_id: "SOURCE_PACKET_READY" for packet_id in required})]
    )
    pending = build_generation_source_readiness(
        REPO, [_population({**{packet_id: "SOURCE_PACKET_READY" for packet_id in required[:-1]}, required[-1]: "PENDING_RESEARCH"})]
    )

    assert ready["jobs"][0]["state"] == "SOURCE_READY"
    assert pending["jobs"][0]["state"] == "PENDING"


def test_incomplete_required_packet_keeps_job_pending() -> None:
    from qbank.generation_source_state import build_generation_source_readiness

    required = _plan()["generation_job_source_packet_ids"]["QGEN-MED-001"]
    readiness = build_generation_source_readiness(
        REPO,
        [_population({
            **{packet_id: "SOURCE_PACKET_READY" for packet_id in required[:-1]},
            required[-1]: "INCOMPLETE_RESEARCH",
        })],
    )

    assert readiness["jobs"][0]["state"] == "PENDING"


def test_blocked_precedes_pending_and_records_packet_ids_and_reason_categories() -> None:
    from qbank.generation_source_state import build_generation_source_readiness

    required = _plan()["generation_job_source_packet_ids"]["QGEN-MED-001"]
    readiness = build_generation_source_readiness(REPO, [_population({
        required[0]: "PENDING_RESEARCH",
        required[1]: "BLOCKED_JURISDICTION",
        required[2]: "BLOCKED_EVIDENCE_CONFLICT",
    })])
    record = readiness["jobs"][0]

    assert record["state"] == "BLOCKED"
    assert record["blocking_source_packet_ids"] == [required[1], required[2]]
    assert record["blocking_reason_categories"] == ["EVIDENCE_CONFLICT", "JURISDICTION"]


def test_queue_contains_only_source_ready_jobs_in_manifest_order_then_job_id() -> None:
    from qbank.generation_source_state import (
        build_generation_queue,
        build_generation_source_readiness,
    )

    plan = _plan()
    required = {
        packet_id
        for job_id in ("QGEN-MED-001", "QGEN-MED-002")
        for packet_id in plan["generation_job_source_packet_ids"][job_id]
    }
    readiness = build_generation_source_readiness(
        REPO, [_population({packet_id: "SOURCE_PACKET_READY" for packet_id in required})]
    )
    queue = build_generation_queue(REPO, readiness)

    assert [record["job_id"] for record in queue["jobs"]] == [
        "QGEN-MED-001", "QGEN-MED-002"
    ]
    assert all(record["state"] == "SOURCE_READY" for record in queue["jobs"])


def test_readiness_and_queue_validators_reject_missing_extra_or_reordered_jobs() -> None:
    from qbank.generation_source_state import (
        build_generation_queue,
        build_generation_source_readiness,
        validate_generation_queue,
        validate_generation_source_readiness,
    )

    populations = load_integrated_source_packet_populations(REPO)
    readiness = build_generation_source_readiness(REPO, populations)
    missing = deepcopy(readiness)
    missing["jobs"] = missing["jobs"][1:]
    extra = deepcopy(readiness)
    extra["jobs"].append(deepcopy(extra["jobs"][0]))
    reordered = deepcopy(readiness)
    reordered["jobs"][:2] = reversed(reordered["jobs"][:2])

    assert validate_generation_source_readiness(REPO, populations, missing).status == "FAIL"
    assert validate_generation_source_readiness(REPO, populations, extra).status == "FAIL"
    assert validate_generation_source_readiness(REPO, populations, reordered).status == "FAIL"

    queue = build_generation_queue(REPO, readiness)
    invalid_queue = deepcopy(queue)
    invalid_queue["jobs"].append({"job_id": "QGEN-MED-001"})
    assert validate_generation_queue(REPO, readiness, invalid_queue).status == "FAIL"

    all_ready = build_generation_source_readiness(
        REPO,
        [_population({packet["source_packet_id"]: "SOURCE_PACKET_READY" for packet in _plan()["source_packets"]})],
    )
    full_queue = build_generation_queue(REPO, all_ready)
    reordered_queue = deepcopy(full_queue)
    reordered_queue["jobs"][:2] = reversed(reordered_queue["jobs"][:2])
    assert validate_generation_queue(REPO, all_ready, reordered_queue).status == "FAIL"


def test_unknown_packet_status_and_duplicate_packet_ownership_fail_closed() -> None:
    from qbank.generation_source_state import build_generation_source_readiness

    packet_id = _plan()["generation_job_source_packet_ids"]["QGEN-MED-001"][0]
    with pytest.raises(ValueError, match="unknown source packet status"):
        build_generation_source_readiness(REPO, [_population({packet_id: "UNKNOWN"})])
    with pytest.raises(ValueError, match="duplicate integrated source packet"):
        build_generation_source_readiness(
            REPO,
            [_population({packet_id: "SOURCE_PACKET_READY"}), _population({packet_id: "PENDING_RESEARCH"})],
        )
