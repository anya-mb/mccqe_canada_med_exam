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
