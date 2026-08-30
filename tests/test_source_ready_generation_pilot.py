from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

from qbank.source_ready_generation_pilot import (
    SourceReadyGenerationPilotError,
    build_generator_input,
    build_verifier_input,
    validate_generated_artifact,
    validate_verifier_verdicts,
)


REPO = Path(__file__).resolve().parents[1]
JOB_ID = "QGEN-PHELO-011"


def _generated_artifact(generator_id: str = "generator-a") -> dict:
    generator_input = build_generator_input(REPO, JOB_ID)
    packet = generator_input["source_packets"][0]
    recommendation = packet["supported_recommendations"][0]
    citation = recommendation["source_citations"][0]
    return {
        "job_id": JOB_ID,
        "generator_id": generator_id,
        "items": [
            {
                "slot_id": slot_id,
                "stem": f"Stem for {slot_id}",
                "options": [
                    {"key": "A", "text": "Correct"},
                    {"key": "B", "text": "Distractor one"},
                    {"key": "C", "text": "Distractor two"},
                    {"key": "D", "text": "Distractor three"},
                ],
                "correct_answer": "A",
                "correct_answer_rationale": "Supported correct-answer rationale.",
                "distractor_rationales": {
                    "B": "Why B is incorrect.",
                    "C": "Why C is incorrect.",
                    "D": "Why D is incorrect.",
                },
                "evidence_references": [{
                    "source_packet_id": packet["source_packet_id"],
                    "recommendation_id": recommendation["recommendation_id"],
                    "source_id": citation["source_id"],
                    "locator": citation["locator"],
                }],
            }
            for slot_id in generator_input["job"]["question_slot_ids"]
        ],
    }


def test_build_generator_input_derives_only_ready_job_slots_and_packets():
    payload = build_generator_input(REPO, JOB_ID)

    assert payload["job"]["job_id"] == JOB_ID
    assert len(payload["job"]["question_slot_ids"]) == 30
    assert [packet["source_packet_id"] for packet in payload["source_packets"]] == [
        "SRC-PHELO-006", "SRC-PHELO-007", "SRC-PHELO-008",
    ]
    assert all(packet["status"] == "SOURCE_PACKET_READY" for packet in payload["source_packets"])


def test_build_generator_input_rejects_job_that_is_not_source_ready():
    with pytest.raises(SourceReadyGenerationPilotError, match="SOURCE_READY"):
        build_generator_input(REPO, "QGEN-MED-001")


def test_generated_artifact_rejects_unsupported_item_evidence_reference():
    artifact = _generated_artifact()
    artifact["items"][0]["evidence_references"][0]["recommendation_id"] = "REC-NOT-AVAILABLE"

    with pytest.raises(SourceReadyGenerationPilotError, match="unsupported evidence reference"):
        validate_generated_artifact(REPO, JOB_ID, artifact)


def test_generated_artifact_requires_exact_slots_and_rationales():
    artifact = _generated_artifact()
    artifact["items"][0].pop("distractor_rationales")

    with pytest.raises(SourceReadyGenerationPilotError, match="rationales for every distractor"):
        validate_generated_artifact(REPO, JOB_ID, artifact)

    artifact = _generated_artifact()
    artifact["items"] = artifact["items"][:-1]
    with pytest.raises(SourceReadyGenerationPilotError, match="slot IDs"):
        validate_generated_artifact(REPO, JOB_ID, artifact)


def test_verifier_input_fingerprints_artifact_and_sources_and_verdicts_require_independence():
    artifact = _generated_artifact("generator-a")
    verifier_input = build_verifier_input(REPO, JOB_ID, artifact)

    assert verifier_input["generated_artifact_fingerprint"]["sha256"]
    assert len(verifier_input["source_packet_fingerprints"]) == 3

    verdicts = {
        "job_id": JOB_ID,
        "verifier_id": "generator-a",
        "generated_artifact_sha256": verifier_input["generated_artifact_fingerprint"]["sha256"],
        "verdicts": [{"slot_id": item["slot_id"], "verdict": "PASS"} for item in artifact["items"]],
    }
    with pytest.raises(SourceReadyGenerationPilotError, match="self-verification"):
        validate_verifier_verdicts(REPO, JOB_ID, artifact, verdicts)


def test_verified_requires_every_slot_to_pass_and_rejections_keep_slot_ids():
    artifact = _generated_artifact()
    verifier_input = build_verifier_input(REPO, JOB_ID, artifact)
    verdicts = {
        "job_id": JOB_ID,
        "verifier_id": "verifier-b",
        "generated_artifact_sha256": verifier_input["generated_artifact_fingerprint"]["sha256"],
        "verdicts": [
            {"slot_id": item["slot_id"], "verdict": "REJECT" if index == 0 else "PASS"}
            for index, item in enumerate(artifact["items"])
        ],
    }

    result = validate_verifier_verdicts(REPO, JOB_ID, artifact, verdicts)
    assert result["status"] == "PENDING_REGENERATION"
    assert result["rejected_slot_ids"] == ["PHELO-Q0287"]

    incomplete = deepcopy(verdicts)
    incomplete["verdicts"] = incomplete["verdicts"][:-1]
    with pytest.raises(SourceReadyGenerationPilotError, match="slot IDs"):
        validate_verifier_verdicts(REPO, JOB_ID, artifact, incomplete)
