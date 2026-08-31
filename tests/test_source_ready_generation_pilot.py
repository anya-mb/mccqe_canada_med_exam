from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

from qbank.source_ready_generation_pilot import (
    RETRY_GENERATED_ARTIFACT_PATH,
    SourceReadyGenerationPilotError,
    build_generator_input,
    build_retry_generator_input,
    build_verifier_input,
    validate_retry_generated_artifact,
    validate_retry_output_path,
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


def _retry_generated_artifact() -> dict:
    retry_input = build_retry_generator_input(REPO, JOB_ID)
    items = []
    for card in retry_input["concept_cards"]:
        references = card["authorized_evidence"]
        items.append({
            "retry_slot_id": card["retry_slot_id"],
            "concept_card_id": card["concept_card_id"],
            "allocation_address_id": card["allocation_address_id"],
            "study_unit_id": card["study_unit_id"],
            "planned_competency": card["target_competency"],
            "reasoning_task": card["reasoning_task"],
            "concept_target": card["concept_target"],
            "intended_item_form": card["intended_item_form"],
            "stem": "Evidence-bounded stem.",
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
            "evidence_references": references,
            "assertion_evidence": {
                "stem": references,
                "options": references,
                "correct_answer": references,
                "correct_answer_rationale": references,
                "distractor_rationales": references,
            },
        })
    return {"job_id": JOB_ID, "generator_id": "retry-generator", "items": items}


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


def test_retry_input_uses_exactly_concept_plan_slots_not_original_manifest_slots():
    payload = build_retry_generator_input(REPO, JOB_ID)

    assert [card["retry_slot_id"] for card in payload["concept_cards"]] == [
        f"QGEN-PHELO-011-RETRY-{number:02d}" for number in range(1, 11)
    ]
    assert len(payload["concept_cards"]) == 10
    assert "question_slot_ids" not in payload["job"]


def test_retry_input_loads_only_each_cards_foundational_claims_and_ready_recommendations():
    payload = build_retry_generator_input(REPO, JOB_ID)
    foundational = payload["concept_cards"][0]
    packet = payload["concept_cards"][4]

    assert [claim["claim_card_id"] for claim in foundational["foundational_claims"]] == ["FNDCLM-PHELO-011-01A"]
    assert foundational["current_packet_recommendations"] == []
    assert packet["foundational_claims"] == []
    assert [reference["recommendation_id"] for reference in packet["current_packet_recommendations"]] == ["REC-SRC-PHELO-006-01"]


def test_retry_item_rejects_cross_slot_evidence_missing_claim_and_unsupported_recommendation():
    artifact = _retry_generated_artifact()
    artifact["items"][0]["evidence_references"] = artifact["items"][1]["evidence_references"]
    with pytest.raises(SourceReadyGenerationPilotError, match="not authorized for retry slot"):
        validate_retry_generated_artifact(REPO, JOB_ID, artifact)

    artifact = _retry_generated_artifact()
    artifact["items"][0]["evidence_references"] = [{"evidence_type": "FOUNDATIONAL_CLAIM", "claim_card_id": "FNDCLM-NOT-VERIFIED"}]
    with pytest.raises(SourceReadyGenerationPilotError, match="not authorized for retry slot"):
        validate_retry_generated_artifact(REPO, JOB_ID, artifact)

    artifact = _retry_generated_artifact()
    artifact["items"][4]["evidence_references"] = [{"evidence_type": "CURRENT_PACKET_RECOMMENDATION", "source_packet_id": "SRC-PHELO-006", "recommendation_id": "REC-NOT-SUPPORTED"}]
    with pytest.raises(SourceReadyGenerationPilotError, match="not authorized for retry slot"):
        validate_retry_generated_artifact(REPO, JOB_ID, artifact)


def test_retry_item_preserves_plan_identifiers_and_requires_slot_scoped_evidence_closure():
    artifact = _retry_generated_artifact()
    assert validate_retry_generated_artifact(REPO, JOB_ID, artifact) == artifact

    artifact["items"][0]["planned_competency"] = {"mcc_objective_id": "wrong"}
    with pytest.raises(SourceReadyGenerationPilotError, match="does not match concept card"):
        validate_retry_generated_artifact(REPO, JOB_ID, artifact)

    artifact = _retry_generated_artifact()
    artifact["items"][0]["assertion_evidence"]["stem"] = [{"evidence_type": "TORONTO_NOTES", "node_id": "PH.S01.T01"}]
    with pytest.raises(SourceReadyGenerationPilotError, match="not authorized for retry slot"):
        validate_retry_generated_artifact(REPO, JOB_ID, artifact)


def test_retry_output_path_is_new_and_failed_pilot_path_is_rejected():
    assert validate_retry_output_path(REPO, RETRY_GENERATED_ARTIFACT_PATH) == RETRY_GENERATED_ARTIFACT_PATH
    with pytest.raises(SourceReadyGenerationPilotError, match="failed pilot"):
        validate_retry_output_path(REPO, "research/qgen/pilot/QGEN-PHELO-011.generated.json")


def test_existing_non_retry_generator_behavior_remains_valid():
    assert validate_generated_artifact(REPO, JOB_ID, _generated_artifact())["job_id"] == JOB_ID
