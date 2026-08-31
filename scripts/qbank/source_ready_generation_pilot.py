"""Deterministic in-memory contracts for one SOURCE_READY generation job."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .jsonio import read_json
from .paths import resolve_root_path
from .generation_source_state import validate_generation_source_readiness
from .source_packet_population import load_integrated_source_packet_populations


class SourceReadyGenerationPilotError(ValueError):
    """A supplied job, generation artifact, or verifier artifact is unsafe."""


RETRY_CONCEPT_PLAN_PATH = "research/qgen/pilot/QGEN-PHELO-011.retry-10.concept-plan.json"
RETRY_GENERATED_ARTIFACT_PATH = "research/qgen/pilot/QGEN-PHELO-011.retry-10.generated.json"
FAILED_PILOT_ARTIFACT_PATH = "research/qgen/pilot/QGEN-PHELO-011.generated.json"
_RETRY_ASSERTION_PARTS = {
    "stem",
    "options",
    "correct_answer",
    "correct_answer_rationale",
    "distractor_rationales",
}


def _sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    ).hexdigest()


def _object(root: Path, relative: str) -> dict[str, Any]:
    value = read_json(resolve_root_path(root, relative, label=relative))
    if not isinstance(value, dict):
        raise SourceReadyGenerationPilotError(f"{relative} must be an object")
    return value


def _job_context(root: Path, job_id: str) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    if not isinstance(job_id, str) or not job_id:
        raise SourceReadyGenerationPilotError("job_id is required")
    manifest = _object(root, "research/qgen/question_generation_manifest.json")
    readiness = _object(root, "research/qgen/generation_source_readiness.json")
    populations = load_integrated_source_packet_populations(root)
    validation = validate_generation_source_readiness(root, populations, readiness)
    if validation.status != "PASS":
        raise SourceReadyGenerationPilotError(
            "generation source readiness artifact failed validation: "
            + "; ".join(validation.errors)
        )
    jobs = [job for job in manifest.get("jobs", []) if isinstance(job, dict) and job.get("job_id") == job_id]
    states = [state for state in readiness.get("jobs", []) if isinstance(state, dict) and state.get("job_id") == job_id]
    if len(jobs) != 1 or len(states) != 1:
        raise SourceReadyGenerationPilotError(f"unknown or ambiguous job_id: {job_id}")
    job, state = jobs[0], states[0]
    slots = job.get("question_slot_ids")
    if not isinstance(slots, list) or not slots or len(slots) != job.get("question_count") or any(not isinstance(slot, str) or not slot for slot in slots) or len(set(slots)) != len(slots):
        raise SourceReadyGenerationPilotError(f"{job_id}: manifest question slots are invalid")
    if state.get("state") != "SOURCE_READY":
        raise SourceReadyGenerationPilotError(f"{job_id} is not currently SOURCE_READY")
    if state.get("question_slot_ids") != slots or state.get("question_count") != job["question_count"]:
        raise SourceReadyGenerationPilotError(f"{job_id}: readiness slots do not match manifest")
    required = state.get("required_source_packet_ids")
    statuses = state.get("packet_statuses")
    if not isinstance(required, list) or not required or len(set(required)) != len(required) or not isinstance(statuses, list):
        raise SourceReadyGenerationPilotError(f"{job_id}: readiness source-packet requirements are invalid")
    if [entry.get("source_packet_id") for entry in statuses if isinstance(entry, dict)] != required or len(statuses) != len(required) or any(entry.get("status") != "SOURCE_PACKET_READY" for entry in statuses if isinstance(entry, dict)):
        raise SourceReadyGenerationPilotError(f"{job_id}: required source packets are not READY")
    packets = {
        packet.get("source_packet_id"): packet
        for population in populations if isinstance(population, dict)
        for packet in population.get("source_packets", []) if isinstance(packet, dict)
    }
    selected = [packets.get(packet_id) for packet_id in required]
    if any(packet is None or packet.get("status") != "SOURCE_PACKET_READY" for packet in selected):
        raise SourceReadyGenerationPilotError(f"{job_id}: required READY source packets are unavailable")
    return job, state, selected


def build_generator_input(root: Path, job_id: str) -> dict[str, Any]:
    """Build one validated, job-specific generator input without writing artifacts."""
    root = Path(root).resolve()
    job, state, packets = _job_context(root, job_id)
    return {
        "schema_version": "1.0",
        "scope": "SOURCE_READY_GENERATOR_INPUT",
        "job": job,
        "readiness": state,
        "source_packets": packets,
        "source_packet_fingerprints": [
            {"source_packet_id": packet["source_packet_id"], "sha256": _sha256(packet)}
            for packet in packets
        ],
    }


def _retry_card_fields(card: dict[str, Any], job_id: str) -> None:
    required_strings = (
        "retry_slot_id", "concept_card_id", "allocation_address_id", "study_unit_id",
        "reasoning_task", "concept_target", "intended_item_form", "evidence_route",
    )
    if card.get("original_job_id") != job_id or any(
        not isinstance(card.get(field), str) or not card[field] for field in required_strings
    ):
        raise SourceReadyGenerationPilotError("retry concept card identifiers are invalid")
    competency = card.get("target_competency")
    notes = card.get("toronto_notes_context")
    if (
        not isinstance(competency, dict)
        or any(not isinstance(competency.get(field), str) or not competency[field] for field in ("mcc_objective_id", "competency_key"))
        or not isinstance(notes, dict)
        or not isinstance(notes.get("node_ids"), list)
        or not notes["node_ids"]
        or any(not isinstance(node_id, str) or not node_id for node_id in notes["node_ids"])
        or not isinstance(notes.get("tn_page_range"), str)
        or not notes["tn_page_range"]
    ):
        raise SourceReadyGenerationPilotError("retry concept card competency or Toronto Notes context is invalid")
    for field in ("foundational_claim_ids", "current_packet_references"):
        if not isinstance(card.get(field), list):
            raise SourceReadyGenerationPilotError(f"retry concept card {field} is invalid")
    if (
        any(not isinstance(claim_id, str) or not claim_id for claim_id in card["foundational_claim_ids"])
        or len(set(card["foundational_claim_ids"])) != len(card["foundational_claim_ids"])
    ):
        raise SourceReadyGenerationPilotError("retry concept card foundational claim IDs are invalid")
    route = card["evidence_route"]
    if route == "FOUNDATIONAL_ONLY" and (not card["foundational_claim_ids"] or card["current_packet_references"]):
        raise SourceReadyGenerationPilotError("FOUNDATIONAL_ONLY retry card has invalid evidence route")
    if route == "READY_PACKET_ONLY" and (card["foundational_claim_ids"] or not card["current_packet_references"]):
        raise SourceReadyGenerationPilotError("READY_PACKET_ONLY retry card has invalid evidence route")
    if route not in {"FOUNDATIONAL_ONLY", "READY_PACKET_ONLY"}:
        raise SourceReadyGenerationPilotError("retry concept card evidence route is invalid")


def _retry_foundational_claims(root: Path, card: dict[str, Any]) -> list[dict[str, Any]]:
    registry = _object(root, "research/qgen/foundational_evidence_claim_cards.json")
    claims = {claim.get("claim_card_id"): claim for claim in registry.get("claim_cards", []) if isinstance(claim, dict)}
    selected = [claims.get(claim_id) for claim_id in card["foundational_claim_ids"]]
    if any(
        claim is None
        or claim.get("verification_status") != "VERIFIED_COMPLETE"
        or card["study_unit_id"] not in {
            reference.get("study_unit_id") for reference in claim.get("scope_references", []) if isinstance(reference, dict)
        }
        for claim in selected
    ):
        raise SourceReadyGenerationPilotError("retry card references missing or unverified foundational claim")
    return selected


def _retry_packet_recommendations(
    packets: list[dict[str, Any]], card: dict[str, Any]
) -> list[dict[str, Any]]:
    by_id = {packet.get("source_packet_id"): packet for packet in packets}
    selected: list[dict[str, Any]] = []
    for reference in card["current_packet_references"]:
        if not isinstance(reference, dict):
            raise SourceReadyGenerationPilotError("retry card packet reference is invalid")
        packet_id, recommendation_id = reference.get("source_packet_id"), reference.get("recommendation_id")
        packet = by_id.get(packet_id)
        if packet is None or packet.get("status") != "SOURCE_PACKET_READY" or packet.get("verification_status") != "VERIFIED_COMPLETE":
            raise SourceReadyGenerationPilotError("retry card references unavailable READY packet")
        if (
            card["allocation_address_id"] not in packet.get("covered_allocation_address_ids", [])
            or card["original_job_id"] not in packet.get("covered_generation_job_ids", [])
        ):
            raise SourceReadyGenerationPilotError("retry card packet is outside card scope")
        recommendations = [
            recommendation for recommendation in packet.get("supported_recommendations", [])
            if isinstance(recommendation, dict) and recommendation.get("recommendation_id") == recommendation_id
        ]
        if len(recommendations) != 1:
            raise SourceReadyGenerationPilotError("retry card references unsupported packet recommendation")
        selected.append({"source_packet_id": packet_id, **recommendations[0]})
    return selected


def _retry_evidence_references(
    claims: list[dict[str, Any]], recommendations: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    return (
        [{"evidence_type": "FOUNDATIONAL_CLAIM", "claim_card_id": claim["claim_card_id"]} for claim in claims]
        + [
            {
                "evidence_type": "CURRENT_PACKET_RECOMMENDATION",
                "source_packet_id": recommendation["source_packet_id"],
                "recommendation_id": recommendation["recommendation_id"],
            }
            for recommendation in recommendations
        ]
    )


def build_retry_generator_input(root: Path, job_id: str) -> dict[str, Any]:
    """Build exact, slot-isolated context for the approved ten-item retry only."""
    root = Path(root).resolve()
    job, _, packets = _job_context(root, job_id)
    plan = _object(root, RETRY_CONCEPT_PLAN_PATH)
    cards = plan.get("concept_cards")
    if plan.get("scope") != "QGEN_PHELO_011_RETRY_10_CONCEPT_PLAN" or plan.get("job_id") != job_id or not isinstance(cards, list) or len(cards) != 10:
        raise SourceReadyGenerationPilotError("retry concept plan must contain exactly 10 cards for the job")
    if plan.get("toronto_notes_authority") != "TOPIC_CONTEXT_ONLY":
        raise SourceReadyGenerationPilotError("retry Toronto Notes authority must be TOPIC_CONTEXT_ONLY")
    if any(not isinstance(card, dict) for card in cards):
        raise SourceReadyGenerationPilotError("retry concept cards are invalid")
    for card in cards:
        _retry_card_fields(card, job_id)
    slot_ids = [card["retry_slot_id"] for card in cards]
    card_ids = [card["concept_card_id"] for card in cards]
    if len(set(slot_ids)) != 10 or len(set(card_ids)) != 10:
        raise SourceReadyGenerationPilotError("retry concept card IDs must be unique")
    scoped_cards = []
    for card in cards:
        claims = _retry_foundational_claims(root, card)
        recommendations = _retry_packet_recommendations(packets, card)
        scoped_cards.append({
            **card,
            "foundational_claims": claims,
            "current_packet_recommendations": recommendations,
            "authorized_evidence": _retry_evidence_references(claims, recommendations),
        })
    return {
        "schema_version": "1.0",
        "scope": "SOURCE_READY_RETRY_GENERATOR_INPUT",
        "job": {"job_id": job["job_id"]},
        "concept_plan_path": RETRY_CONCEPT_PLAN_PATH,
        "toronto_notes_authority": "TOPIC_CONTEXT_ONLY",
        "concept_cards": scoped_cards,
    }


def validate_retry_output_path(root: Path, output_path: str) -> str:
    """Permit only the new canonical retry artifact, never the failed pilot output."""
    if output_path == FAILED_PILOT_ARTIFACT_PATH:
        raise SourceReadyGenerationPilotError("failed pilot artifact path is forbidden for retry output")
    if output_path != RETRY_GENERATED_ARTIFACT_PATH:
        raise SourceReadyGenerationPilotError("retry output path must be the canonical new retry artifact path")
    resolve_root_path(Path(root).resolve(), output_path, label="retry output path")
    return output_path


def _retry_reference_key(reference: dict[str, Any]) -> tuple[Any, ...]:
    evidence_type = reference.get("evidence_type")
    if evidence_type == "FOUNDATIONAL_CLAIM":
        return evidence_type, reference.get("claim_card_id")
    if evidence_type == "CURRENT_PACKET_RECOMMENDATION":
        return evidence_type, reference.get("source_packet_id"), reference.get("recommendation_id")
    return (evidence_type,)


def _retry_item_evidence_is_authorized(item: dict[str, Any], authorized: set[tuple[Any, ...]]) -> None:
    references = item.get("evidence_references")
    if not isinstance(references, list) or not references:
        raise SourceReadyGenerationPilotError("each retry item requires item-level evidence references")
    if any(not isinstance(reference, dict) or _retry_reference_key(reference) not in authorized for reference in references):
        raise SourceReadyGenerationPilotError("evidence reference is not authorized for retry slot")
    closure = item.get("assertion_evidence")
    if not isinstance(closure, dict) or set(closure) != _RETRY_ASSERTION_PARTS:
        raise SourceReadyGenerationPilotError("retry item requires evidence closure for every factual assertion part")
    for references_for_part in closure.values():
        if not isinstance(references_for_part, list) or not references_for_part or any(
            not isinstance(reference, dict) or _retry_reference_key(reference) not in authorized
            for reference in references_for_part
        ):
            raise SourceReadyGenerationPilotError("evidence reference is not authorized for retry slot")


def validate_retry_generated_artifact(root: Path, job_id: str, artifact: dict[str, Any]) -> dict[str, Any]:
    """Fail closed unless every retry item preserves its plan and card-scoped evidence closure."""
    if not isinstance(artifact, dict) or artifact.get("job_id") != job_id or not isinstance(artifact.get("generator_id"), str) or not artifact["generator_id"]:
        raise SourceReadyGenerationPilotError("retry generated artifact job_id or generator_id is invalid")
    cards = build_retry_generator_input(root, job_id)["concept_cards"]
    items = artifact.get("items")
    expected_slots = [card["retry_slot_id"] for card in cards]
    if not isinstance(items, list) or [item.get("retry_slot_id") for item in items if isinstance(item, dict)] != expected_slots or len(items) != 10:
        raise SourceReadyGenerationPilotError("retry generated artifact must exactly match the 10 retry slots")
    required_item_strings = ("stem", "correct_answer_rationale")
    plan_fields = ("concept_card_id", "allocation_address_id", "study_unit_id", "reasoning_task", "concept_target", "intended_item_form")
    for item, card in zip(items, cards, strict=True):
        if not isinstance(item, dict) or any(not isinstance(item.get(field), str) or not item[field].strip() for field in required_item_strings):
            raise SourceReadyGenerationPilotError("each retry item requires stem and correct-answer rationale")
        if any(item.get(field) != card[field] for field in plan_fields) or item.get("planned_competency") != card["target_competency"]:
            raise SourceReadyGenerationPilotError("retry item plan identifier does not match concept card")
        options = item.get("options")
        keys = [option.get("key") for option in options] if isinstance(options, list) and all(isinstance(option, dict) for option in options) else []
        if len(keys) < 2 or len(set(keys)) != len(keys) or item.get("correct_answer") not in keys:
            raise SourceReadyGenerationPilotError("each retry item requires keyed options and a correct answer")
        distractors = item.get("distractor_rationales")
        if not isinstance(distractors, dict) or set(distractors) != set(keys) - {item["correct_answer"]} or any(not isinstance(value, str) or not value.strip() for value in distractors.values()):
            raise SourceReadyGenerationPilotError("each retry item requires rationales for every distractor")
        _retry_item_evidence_is_authorized(item, {_retry_reference_key(reference) for reference in card["authorized_evidence"]})
    return artifact


def _supported_references(packets: list[dict[str, Any]]) -> set[tuple[str, str, str, str]]:
    supported: set[tuple[str, str, str, str]] = set()
    for packet in packets:
        packet_id = packet["source_packet_id"]
        for recommendation in packet.get("supported_recommendations", []):
            if not isinstance(recommendation, dict) or not isinstance(recommendation.get("recommendation_id"), str):
                continue
            for citation in recommendation.get("source_citations", []):
                if isinstance(citation, dict) and isinstance(citation.get("source_id"), str) and isinstance(citation.get("locator"), str):
                    supported.add((packet_id, recommendation["recommendation_id"], citation["source_id"], citation["locator"]))
    return supported


def validate_generated_artifact(root: Path, job_id: str, artifact: dict[str, Any]) -> dict[str, Any]:
    """Fail closed unless an artifact covers each frozen slot with supported evidence."""
    if not isinstance(artifact, dict):
        raise SourceReadyGenerationPilotError("generated artifact must be an object")
    generator_input = build_generator_input(root, job_id)
    if artifact.get("job_id") != job_id or not isinstance(artifact.get("generator_id"), str) or not artifact["generator_id"]:
        raise SourceReadyGenerationPilotError("generated artifact job_id or generator_id is invalid")
    items = artifact.get("items")
    expected_slots = generator_input["job"]["question_slot_ids"]
    if not isinstance(items, list) or [item.get("slot_id") for item in items if isinstance(item, dict)] != expected_slots or len(items) != len(expected_slots):
        raise SourceReadyGenerationPilotError("generated artifact slot IDs must exactly match the job")
    supported = _supported_references(generator_input["source_packets"])
    for item in items:
        if not isinstance(item, dict) or not isinstance(item.get("stem"), str) or not item["stem"].strip():
            raise SourceReadyGenerationPilotError("each item requires a non-empty stem")
        options = item.get("options")
        if not isinstance(options, list) or len(options) < 2 or any(not isinstance(option, dict) or not isinstance(option.get("key"), str) or not option["key"] or not isinstance(option.get("text"), str) or not option["text"].strip() for option in options):
            raise SourceReadyGenerationPilotError("each item requires keyed options")
        keys = [option["key"] for option in options]
        if len(set(keys)) != len(keys) or item.get("correct_answer") not in keys:
            raise SourceReadyGenerationPilotError("each item requires one keyed correct answer")
        if not isinstance(item.get("correct_answer_rationale"), str) or not item["correct_answer_rationale"].strip():
            raise SourceReadyGenerationPilotError("each item requires a correct-answer rationale")
        distractors = item.get("distractor_rationales")
        expected_distractors = set(keys) - {item["correct_answer"]}
        if not isinstance(distractors, dict) or set(distractors) != expected_distractors or any(not isinstance(value, str) or not value.strip() for value in distractors.values()):
            raise SourceReadyGenerationPilotError("each item requires rationales for every distractor")
        references = item.get("evidence_references")
        if not isinstance(references, list) or not references:
            raise SourceReadyGenerationPilotError("each item requires item-level evidence references")
        for reference in references:
            if not isinstance(reference, dict):
                raise SourceReadyGenerationPilotError("unsupported evidence reference")
            record = tuple(reference.get(key) for key in ("source_packet_id", "recommendation_id", "source_id", "locator"))
            if record not in supported:
                raise SourceReadyGenerationPilotError("unsupported evidence reference")
    return artifact


def build_verifier_input(root: Path, job_id: str, artifact: dict[str, Any]) -> dict[str, Any]:
    """Build an independent-verifier packet tied to exact generated/source bytes."""
    validated = validate_generated_artifact(root, job_id, artifact)
    generator_input = build_generator_input(root, job_id)
    return {
        "schema_version": "1.0",
        "scope": "SOURCE_READY_INDEPENDENT_VERIFIER_INPUT",
        "job_id": job_id,
        "generated_artifact": validated,
        "generated_artifact_fingerprint": {"sha256": _sha256(validated)},
        "source_packet_fingerprints": generator_input["source_packet_fingerprints"],
    }


def validate_verifier_verdicts(root: Path, job_id: str, artifact: dict[str, Any], verdicts: dict[str, Any]) -> dict[str, Any]:
    """Validate independent verdicts; VERIFIED is possible only when every slot passes."""
    if not isinstance(verdicts, dict):
        raise SourceReadyGenerationPilotError("verifier verdicts must be an object")
    verifier_input = build_verifier_input(root, job_id, artifact)
    if verdicts.get("job_id") != job_id or verdicts.get("generated_artifact_sha256") != verifier_input["generated_artifact_fingerprint"]["sha256"]:
        raise SourceReadyGenerationPilotError("verifier verdicts do not match the generated artifact")
    verifier_id = verdicts.get("verifier_id")
    if not isinstance(verifier_id, str) or not verifier_id:
        raise SourceReadyGenerationPilotError("verifier_id is required")
    if verifier_id == artifact["generator_id"]:
        raise SourceReadyGenerationPilotError("generator self-verification is forbidden")
    rows = verdicts.get("verdicts")
    expected_slots = [item["slot_id"] for item in artifact["items"]]
    if not isinstance(rows, list) or [row.get("slot_id") for row in rows if isinstance(row, dict)] != expected_slots or len(rows) != len(expected_slots):
        raise SourceReadyGenerationPilotError("verifier verdict slot IDs must exactly match the job")
    if any(row.get("verdict") not in {"PASS", "REJECT"} for row in rows if isinstance(row, dict)):
        raise SourceReadyGenerationPilotError("verifier verdict must be PASS or REJECT")
    rejected = [row["slot_id"] for row in rows if row["verdict"] == "REJECT"]
    return {"job_id": job_id, "status": "VERIFIED" if not rejected else "PENDING_REGENERATION", "rejected_slot_ids": rejected}
