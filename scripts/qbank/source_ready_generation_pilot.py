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
RETRY_V2_ITEM_SPEC_PATH = "research/qgen/pilot/QGEN-PHELO-011.retry-v2-10.item-spec.json"
RETRY_V2_PREFLIGHT_PATH = "reports/qgen_phelo_011_retry_v2_semantic_preflight.json"
RETRY_V2_GENERATED_ARTIFACT_PATH = "research/qgen/pilot/QGEN-PHELO-011.retry-v2-10.generated.json"
RETRY_V2_VERIFICATION_PATH = "research/qgen/pilot/QGEN-PHELO-011.retry-v2-10.verification.json"
RETRY_V2_1_MICRO_GENERATED_ARTIFACT_PATH = "research/qgen/pilot/QGEN-PHELO-011.retry-v2-1-micro-3.generated.json"
RETRY_V2_1_FULL_GENERATED_ARTIFACT_PATH = "research/qgen/pilot/QGEN-PHELO-011.retry-v2-1-10.generated.json"
RETRY_V2_1_MICRO_SEMANTIC_REVIEW_PATH = "reports/qgen_phelo_011_retry_v2_1_micro_semantic_generation_review.json"
RETRY_V2_1_FULL_SEMANTIC_REVIEW_PATH = "reports/qgen_phelo_011_retry_v2_1_semantic_generation_review.json"
FAILED_PILOT_ARTIFACT_PATH = "research/qgen/pilot/QGEN-PHELO-011.generated.json"
_RETRY_ASSERTION_PARTS = {
    "stem",
    "options",
    "correct_answer",
    "correct_answer_rationale",
    "distractor_rationales",
}
_RETRY_V2_ALLOCATION = {"SU-PH-01": 5, "SU-PH-02": 3, "SU-PH-03": 2}
_RETRY_V2_DISPOSITIONS = {
    1: "REPLACE_AS_DUPLICATIVE", 2: "KEEP_CORE_CONCEPT", 3: "REDESIGN_CONCEPT",
    4: "REDESIGN_CONCEPT", 5: "KEEP_CORE_CONCEPT", 6: "REPLACE_AS_DUPLICATIVE",
    7: "REPLACE_AS_DUPLICATIVE", 8: "REDESIGN_CONCEPT", 9: "KEEP_CORE_CONCEPT",
    10: "KEEP_CORE_CONCEPT",
}
_RETRY_V2_SPEC_FIELDS = {
    "learner_decision", "competency_demonstration", "reasoning_chain",
    "evidence_discriminants", "closest_competing_concepts", "distractor_blueprint",
    "vignette_requirements", "difficulty_mechanism", "prohibited_shortcuts",
    "rationale_requirements", "semantic_signature", "lineage",
}
_RETRY_V2_PREFLIGHT_ASSESSMENTS = {
    "evidence_alignment", "educational_decision_distinctness", "reasoning_depth",
    "vignette_necessity", "competing_concept_plausibility", "distractor_blueprint_quality",
    "set_level_duplication", "mccqe_appropriateness",
}
_RETRY_V2_FINAL_ASSESSMENTS = {
    "factual_correctness", "semantic_evidence_support", "single_best_answer",
    "distractor_plausibility", "mccqe_level_difficulty", "reasoning_quality",
    "item_spec_fidelity", "vignette_necessity", "rationale_quality",
    "item_writing_quality", "semantic_duplication",
}
_RETRY_V2_REJECTION_CATEGORIES = {
    "FACTUAL_ERROR", "UNSUPPORTED_CLAIM", "AMBIGUOUS_BEST_ANSWER", "WEAK_DISTRACTORS",
    "INAPPROPRIATE_DIFFICULTY", "PLAN_MISMATCH", "RATIONALE_DEFICIENCY",
    "ITEM_WRITING_PROBLEM", "MATERIAL_DUPLICATION", "OTHER",
}
_RETRY_V2_1_SEMANTIC_GENERATION_ASSESSMENTS = {
    "learner_decision_instantiated", "reasoning_chain_instantiated", "vignette_necessary",
    "evidence_discriminant_instantiated", "distractor_blueprint_faithful",
    "prohibited_shortcuts_absent", "rationale_requirements_met",
}


def _sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    ).hexdigest()


def _normalized_text(value: str) -> str:
    return " ".join(value.lower().split())


def retry_v2_semantic_signature(card: dict[str, Any]) -> str:
    """Return the deterministic duplicate-candidate signature; it is not semantic approval."""
    payload = {
        "learner_decision": _normalized_text(card["learner_decision"]),
        "reasoning_chain": [_normalized_text(value) for value in card["reasoning_chain"]],
        "evidence_discriminants": [
            _normalized_text(value["fact"]) for value in card["evidence_discriminants"]
        ],
        "closest_competing_concepts": [
            _normalized_text(value["label"]) for value in card["closest_competing_concepts"]
        ],
        "evidence_route": sorted([
            [
                reference.get("evidence_type") or "",
                reference.get("claim_card_id") or "",
                reference.get("source_packet_id") or "",
                reference.get("recommendation_id") or "",
            ]
            for reference in card["authorized_evidence"]
        ]),
        "answer_category": _normalized_text(card["answer_category"]),
    }
    return _sha256(payload)


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


def _actor_key(value: str) -> str:
    return _normalized_text(value)


def _retry_v2_evidence_objects(
    root: Path,
    job_id: str,
    card: dict[str, Any],
    *,
    packets: list[dict[str, Any]] | None = None,
    claim_by_id: dict[str, dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    references = card.get("authorized_evidence")
    if (
        not isinstance(references, list)
        or not references
        or any(not isinstance(reference, dict) for reference in references)
        or len({_retry_reference_key(reference) for reference in references}) != len(references)
    ):
        raise SourceReadyGenerationPilotError("retry V2 authorized evidence is invalid")
    if packets is None:
        _, _, packets = _job_context(root, job_id)
    packet_by_id = {packet["source_packet_id"]: packet for packet in packets}
    if claim_by_id is None:
        registry = _object(root, "research/qgen/foundational_evidence_claim_cards.json")
        claim_by_id = {
            claim.get("claim_card_id"): claim
            for claim in registry.get("claim_cards", []) if isinstance(claim, dict)
        }
    selected: list[dict[str, Any]] = []
    for reference in references:
        if reference.get("evidence_type") == "FOUNDATIONAL_CLAIM":
            claim = claim_by_id.get(reference.get("claim_card_id"))
            scoped_units = {
                scope.get("study_unit_id")
                for scope in claim.get("scope_references", []) if isinstance(scope, dict)
            } if isinstance(claim, dict) else set()
            if (
                claim is None
                or claim.get("verification_status") != "VERIFIED_COMPLETE"
                or card.get("study_unit_id") not in scoped_units
            ):
                raise SourceReadyGenerationPilotError("retry V2 authorized evidence is outside the slot scope")
            selected.append(claim)
            continue
        if reference.get("evidence_type") == "CURRENT_PACKET_RECOMMENDATION":
            packet = packet_by_id.get(reference.get("source_packet_id"))
            if (
                packet is None
                or packet.get("status") != "SOURCE_PACKET_READY"
                or packet.get("verification_status") != "VERIFIED_COMPLETE"
                or card.get("allocation_address_id") not in packet.get("covered_allocation_address_ids", [])
                or job_id not in packet.get("covered_generation_job_ids", [])
            ):
                raise SourceReadyGenerationPilotError("retry V2 authorized evidence is outside the slot scope")
            recommendations = [
                recommendation for recommendation in packet.get("supported_recommendations", [])
                if isinstance(recommendation, dict)
                and recommendation.get("recommendation_id") == reference.get("recommendation_id")
            ]
            if len(recommendations) != 1:
                raise SourceReadyGenerationPilotError("retry V2 authorized evidence is unavailable")
            selected.append({"source_packet_id": packet["source_packet_id"], **recommendations[0]})
            continue
        raise SourceReadyGenerationPilotError("retry V2 authorized evidence type is invalid")
    return selected


def _retry_v2_evidence_refs_valid(
    references: Any, authorized: set[tuple[Any, ...]], label: str
) -> None:
    if (
        not isinstance(references, list)
        or not references
        or any(
            not isinstance(reference, dict) or _retry_reference_key(reference) not in authorized
            for reference in references
        )
    ):
        raise SourceReadyGenerationPilotError(f"retry V2 {label} uses unauthorized evidence")


def _retry_v2_nonempty_strings(value: Any, label: str, *, minimum: int = 1) -> list[str]:
    if (
        not isinstance(value, list)
        or len(value) < minimum
        or any(not isinstance(entry, str) or not entry.strip() for entry in value)
    ):
        raise SourceReadyGenerationPilotError(f"retry V2 {label} is invalid")
    return value


def validate_retry_v2_item_specs(
    root: Path, job_id: str, artifact: dict[str, Any]
) -> dict[str, Any]:
    """Validate mechanically provable V2 structure, allocation, signatures, and lineage."""
    root = Path(root).resolve()
    if (
        not isinstance(artifact, dict)
        or artifact.get("schema_version") != "2.0"
        or artifact.get("scope") != "STRUCTURED_ITEM_SPEC_V2"
        or artifact.get("job_id") != job_id
        or not isinstance(artifact.get("author_id"), str)
        or not artifact["author_id"].strip()
    ):
        raise SourceReadyGenerationPilotError("retry V2 item-spec artifact identity is invalid")
    if artifact.get("allocation_apportionment") != _RETRY_V2_ALLOCATION:
        raise SourceReadyGenerationPilotError("retry V2 item specs must preserve exact 5/3/2 allocation")
    cards = artifact.get("cards")
    v1_plan = _object(root, RETRY_CONCEPT_PLAN_PATH)
    v1_cards = v1_plan.get("concept_cards")
    if not isinstance(cards, list) or len(cards) != 10 or not isinstance(v1_cards, list) or len(v1_cards) != 10:
        raise SourceReadyGenerationPilotError("retry V2 item specs must contain exactly 10 cards")
    if any(not isinstance(card, dict) for card in cards):
        raise SourceReadyGenerationPilotError("retry V2 item-spec cards are invalid")
    expected_slots = [card["retry_slot_id"] for card in v1_cards]
    if [card.get("retry_slot_id") for card in cards] != expected_slots:
        raise SourceReadyGenerationPilotError("retry V2 slots must exactly match immutable V1 slots")
    if [card.get("study_unit_id") for card in cards].count("SU-PH-01") != 5 or [card.get("study_unit_id") for card in cards].count("SU-PH-02") != 3 or [card.get("study_unit_id") for card in cards].count("SU-PH-03") != 2:
        raise SourceReadyGenerationPilotError("retry V2 item specs must preserve exact 5/3/2 allocation")
    ids = [card.get("v2_item_spec_id") for card in cards]
    if any(not isinstance(value, str) or not value for value in ids) or len(set(ids)) != 10:
        raise SourceReadyGenerationPilotError("retry V2 item-spec IDs must be unique")
    v1_plan_sha = _sha256(v1_plan)
    _, _, packets = _job_context(root, job_id)
    registry = _object(root, "research/qgen/foundational_evidence_claim_cards.json")
    claim_by_id = {
        claim.get("claim_card_id"): claim
        for claim in registry.get("claim_cards", []) if isinstance(claim, dict)
    }
    signatures: list[str] = []
    for index, (card, v1_card) in enumerate(zip(cards, v1_cards, strict=True), start=1):
        if not _RETRY_V2_SPEC_FIELDS.issubset(card):
            raise SourceReadyGenerationPilotError("retry V2 card is missing required V2 fields")
        required_strings = (
            "learner_decision", "competency_demonstration", "difficulty_mechanism", "answer_category",
        )
        if any(not isinstance(card.get(field), str) or not card[field].strip() for field in required_strings):
            raise SourceReadyGenerationPilotError("retry V2 card required V2 fields are invalid")
        if (
            card.get("disposition") != _RETRY_V2_DISPOSITIONS[index]
            or card.get("allocation_address_id") != v1_card.get("allocation_address_id")
            or card.get("study_unit_id") != v1_card.get("study_unit_id")
            or card.get("target_competency") != v1_card.get("target_competency")
        ):
            raise SourceReadyGenerationPilotError("retry V2 card violates disposition or frozen 5/3/2 slot binding")
        _retry_v2_nonempty_strings(card.get("reasoning_chain"), "reasoning chain", minimum=2)
        _retry_v2_nonempty_strings(card.get("prohibited_shortcuts"), "prohibited shortcuts", minimum=4)
        evidence_objects = _retry_v2_evidence_objects(
            root, job_id, card, packets=packets, claim_by_id=claim_by_id
        )
        authorized = {_retry_reference_key(reference) for reference in card["authorized_evidence"]}
        discriminants = card.get("evidence_discriminants")
        if not isinstance(discriminants, list) or not discriminants:
            raise SourceReadyGenerationPilotError("retry V2 evidence discriminants are invalid")
        for discriminant in discriminants:
            if not isinstance(discriminant, dict) or not isinstance(discriminant.get("fact"), str) or not discriminant["fact"].strip():
                raise SourceReadyGenerationPilotError("retry V2 evidence discriminants are invalid")
            _retry_v2_evidence_refs_valid(discriminant.get("evidence_refs"), authorized, "evidence discriminant")
        competitors = card.get("closest_competing_concepts")
        if not isinstance(competitors, list) or len(competitors) != 3:
            raise SourceReadyGenerationPilotError("retry V2 closest competing concepts must contain exactly three alternatives")
        competitor_ids: list[str] = []
        for competitor in competitors:
            if (
                not isinstance(competitor, dict)
                or any(not isinstance(competitor.get(field), str) or not competitor[field].strip() for field in ("concept_id", "label", "why_plausible"))
            ):
                raise SourceReadyGenerationPilotError("retry V2 closest competing concept is invalid")
            competitor_ids.append(competitor["concept_id"])
            _retry_v2_evidence_refs_valid(competitor.get("evidence_refs"), authorized, "competing concept")
        if len(set(competitor_ids)) != 3:
            raise SourceReadyGenerationPilotError("retry V2 competing-concept IDs must be unique")
        blueprint = card.get("distractor_blueprint")
        if not isinstance(blueprint, list) or len(blueprint) != 3:
            raise SourceReadyGenerationPilotError("retry V2 distractor blueprint must contain exactly three distractors")
        blueprint_concepts: list[str] = []
        distractor_ids: list[str] = []
        for distractor in blueprint:
            if (
                not isinstance(distractor, dict)
                or any(
                    not isinstance(distractor.get(field), str) or not distractor[field].strip()
                    for field in ("distractor_id", "competing_concept_id", "temptation", "scenario_feature", "evidence_discriminator")
                )
            ):
                raise SourceReadyGenerationPilotError("retry V2 distractor blueprint entry is invalid")
            distractor_ids.append(distractor["distractor_id"])
            blueprint_concepts.append(distractor["competing_concept_id"])
            _retry_v2_evidence_refs_valid(distractor.get("evidence_refs"), authorized, "distractor blueprint")
        if len(set(distractor_ids)) != 3 or set(blueprint_concepts) != set(competitor_ids):
            raise SourceReadyGenerationPilotError("retry V2 distractor blueprint does not match competing concepts")
        vignette = card.get("vignette_requirements")
        if not isinstance(vignette, dict) or not isinstance(vignette.get("required"), bool) or not isinstance(vignette.get("necessity"), str) or not vignette["necessity"].strip():
            raise SourceReadyGenerationPilotError("retry V2 vignette requirements are invalid")
        facts = vignette.get("facts")
        if not isinstance(facts, list) or (vignette["required"] and not facts):
            raise SourceReadyGenerationPilotError("retry V2 required vignette facts are missing")
        requirement_ids: list[str] = []
        for fact in facts:
            if not isinstance(fact, dict) or any(not isinstance(fact.get(field), str) or not fact[field].strip() for field in ("requirement_id", "fact")):
                raise SourceReadyGenerationPilotError("retry V2 vignette fact is invalid")
            requirement_ids.append(fact["requirement_id"])
            _retry_v2_evidence_refs_valid(fact.get("evidence_refs"), authorized, "vignette fact")
        if len(set(requirement_ids)) != len(requirement_ids):
            raise SourceReadyGenerationPilotError("retry V2 vignette requirement IDs must be unique")
        rationales = card.get("rationale_requirements")
        if not isinstance(rationales, dict) or not isinstance(rationales.get("best_answer"), str) or not rationales["best_answer"].strip():
            raise SourceReadyGenerationPilotError("retry V2 rationale requirements are invalid")
        alternatives = rationales.get("alternatives")
        if not isinstance(alternatives, list) or [value.get("competing_concept_id") for value in alternatives if isinstance(value, dict)] != competitor_ids:
            raise SourceReadyGenerationPilotError("retry V2 rationale alternatives do not match competing concepts")
        for alternative in alternatives:
            if not isinstance(alternative.get("required_discriminator"), str) or not alternative["required_discriminator"].strip():
                raise SourceReadyGenerationPilotError("retry V2 rationale alternative is invalid")
            _retry_v2_evidence_refs_valid(alternative.get("evidence_refs"), authorized, "rationale alternative")
        expected_signature = retry_v2_semantic_signature(card)
        if card.get("semantic_signature") != expected_signature:
            raise SourceReadyGenerationPilotError("retry V2 semantic signature does not match its deterministic payload")
        signatures.append(expected_signature)
        lineage = card.get("lineage")
        if not isinstance(lineage, dict):
            raise SourceReadyGenerationPilotError("retry V2 lineage is invalid")
        if lineage.get("v1_concept_plan_path") != RETRY_CONCEPT_PLAN_PATH or lineage.get("v1_concept_plan_sha256") != v1_plan_sha:
            raise SourceReadyGenerationPilotError("retry V2 V1 concept plan fingerprint is invalid")
        if lineage.get("v1_concept_card_id") != v1_card.get("concept_card_id") or lineage.get("v1_concept_card_sha256") != _sha256(v1_card):
            raise SourceReadyGenerationPilotError("retry V2 V1 concept card fingerprint is invalid")
        fingerprints = lineage.get("authorized_evidence_fingerprints")
        expected_fingerprints = [
            {"reference": reference, "sha256": _sha256(evidence)}
            for reference, evidence in zip(card["authorized_evidence"], evidence_objects, strict=True)
        ]
        if fingerprints != expected_fingerprints:
            raise SourceReadyGenerationPilotError("retry V2 authorized evidence fingerprints are invalid")
        if not isinstance(lineage.get("revision"), int) or lineage["revision"] < 0 or lineage["revision"] > 2:
            raise SourceReadyGenerationPilotError("retry V2 lineage revision is invalid")
    if len(set(signatures)) != 10:
        raise SourceReadyGenerationPilotError("retry V2 semantic signatures contain duplicate candidates")
    return artifact


def build_retry_v2_preflight_input(
    root: Path, job_id: str, item_specs: dict[str, Any]
) -> dict[str, Any]:
    """Build a fresh-review packet with specs, exact authorized evidence, and level context only."""
    root = Path(root).resolve()
    validated = validate_retry_v2_item_specs(root, job_id, item_specs)
    _, _, packets = _job_context(root, job_id)
    registry = _object(root, "research/qgen/foundational_evidence_claim_cards.json")
    claim_by_id = {
        claim.get("claim_card_id"): claim
        for claim in registry.get("claim_cards", []) if isinstance(claim, dict)
    }
    evidence = []
    for card in validated["cards"]:
        evidence.append({
            "v2_item_spec_id": card["v2_item_spec_id"],
            "authorized_evidence": [
                {"reference": reference, "evidence": value}
                for reference, value in zip(
                    card["authorized_evidence"],
                    _retry_v2_evidence_objects(
                        root, job_id, card, packets=packets, claim_by_id=claim_by_id
                    ),
                    strict=True,
                )
            ],
        })
    return {
        "schema_version": "2.0",
        "scope": "RETRY_V2_SEMANTIC_PREFLIGHT_INPUT",
        "job_id": job_id,
        "item_specs": validated,
        "item_spec_fingerprint": {"sha256": _sha256(validated)},
        "authorized_evidence_by_card": evidence,
        "canonical_level_context": {
            "assessment": "MCCQE_PART_I",
            "item_format": "single-best-answer",
            "toronto_notes_authority": "TOPIC_CONTEXT_ONLY",
        },
        "excluded_context": ["AUTHOR_SELF_EVALUATION", "GENERATOR_OUTPUT", "WEB"],
    }


def validate_retry_v2_semantic_preflight(
    root: Path,
    job_id: str,
    item_specs: dict[str, Any],
    artifact: dict[str, Any],
) -> dict[str, Any]:
    """Validate that a fresh reviewer approved every exact V2 card before generation."""
    validated_specs = validate_retry_v2_item_specs(root, job_id, item_specs)
    if (
        not isinstance(artifact, dict)
        or artifact.get("schema_version") != "2.0"
        or artifact.get("scope") != "RETRY_V2_SEMANTIC_PREFLIGHT"
        or artifact.get("job_id") != job_id
    ):
        raise SourceReadyGenerationPilotError("retry V2 semantic preflight identity is invalid")
    reviewer_id = artifact.get("reviewer_id")
    if not isinstance(reviewer_id, str) or not reviewer_id.strip():
        raise SourceReadyGenerationPilotError("retry V2 semantic preflight reviewer is required")
    if _actor_key(reviewer_id) == _actor_key(validated_specs["author_id"]) or artifact.get("item_spec_author_id") != validated_specs["author_id"]:
        raise SourceReadyGenerationPilotError("retry V2 semantic preflight self-review is forbidden")
    if artifact.get("item_spec_path") != RETRY_V2_ITEM_SPEC_PATH or artifact.get("item_spec_sha256") != _sha256(validated_specs):
        raise SourceReadyGenerationPilotError("retry V2 semantic preflight item-spec fingerprint is invalid")
    if not isinstance(artifact.get("revision_pass"), int) or artifact["revision_pass"] < 0 or artifact["revision_pass"] > 2:
        raise SourceReadyGenerationPilotError("retry V2 semantic preflight revision pass is invalid")
    if artifact.get("independent_context") != "PASS" or set(artifact.get("included_context", [])) != {"V2_ITEM_SPECS", "AUTHORIZED_EVIDENCE", "CANONICAL_MCCQE_LEVEL"}:
        raise SourceReadyGenerationPilotError("retry V2 semantic preflight independent context is invalid")
    if artifact.get("set_level_duplication") not in {"NONE", "LOW"}:
        raise SourceReadyGenerationPilotError("retry V2 semantic preflight found material set-level duplication")
    rows = artifact.get("verdicts")
    expected = [(card["v2_item_spec_id"], card["retry_slot_id"]) for card in validated_specs["cards"]]
    actual = [(row.get("v2_item_spec_id"), row.get("retry_slot_id")) for row in rows if isinstance(row, dict)] if isinstance(rows, list) else []
    if len(rows) != 10 if isinstance(rows, list) else True:
        raise SourceReadyGenerationPilotError("retry V2 semantic preflight verdicts must exactly match all cards")
    if actual != expected:
        raise SourceReadyGenerationPilotError("retry V2 semantic preflight verdicts must exactly match all cards")
    for row in rows:
        if row.get("verdict") not in {"APPROVED_FOR_GENERATION", "REJECTED_FOR_SPEC_REVISION"}:
            raise SourceReadyGenerationPilotError("retry V2 semantic preflight verdict is invalid")
        assessments = row.get("assessments")
        if not isinstance(assessments, dict) or set(assessments) != _RETRY_V2_PREFLIGHT_ASSESSMENTS or any(value not in {"PASS", "FAIL"} for value in assessments.values()):
            raise SourceReadyGenerationPilotError("retry V2 semantic preflight assessments are invalid")
        if not isinstance(row.get("rationale"), str) or not row["rationale"].strip():
            raise SourceReadyGenerationPilotError("retry V2 semantic preflight rationale is required")
        if row["verdict"] == "APPROVED_FOR_GENERATION" and any(value != "PASS" for value in assessments.values()):
            raise SourceReadyGenerationPilotError("retry V2 semantic preflight approval contains failed assessment")
    if any(row["verdict"] != "APPROVED_FOR_GENERATION" for row in rows):
        raise SourceReadyGenerationPilotError("retry V2 item specs are not approved for generation")
    return artifact


def build_retry_v2_generator_input(
    root: Path,
    job_id: str,
    item_specs: dict[str, Any],
    semantic_preflight: dict[str, Any],
) -> dict[str, Any]:
    """Build generator context only after every exact V2 spec passes fresh preflight."""
    root = Path(root).resolve()
    validated_specs = validate_retry_v2_item_specs(root, job_id, item_specs)
    validated_preflight = validate_retry_v2_semantic_preflight(
        root, job_id, validated_specs, semantic_preflight
    )
    preflight_input = build_retry_v2_preflight_input(root, job_id, validated_specs)
    return {
        "schema_version": "2.0",
        "scope": "RETRY_V2_GENERATOR_INPUT",
        "job_id": job_id,
        "item_specs": validated_specs,
        "item_spec_fingerprint": {"sha256": _sha256(validated_specs)},
        "semantic_preflight": validated_preflight,
        "semantic_preflight_fingerprint": {"sha256": _sha256(validated_preflight)},
        "authorized_evidence_by_card": preflight_input["authorized_evidence_by_card"],
        "generation_policy": {
            "slot_scoped_evidence_only": True,
            "subjective_quality_requires_independent_verification": True,
            "web_or_model_memory_completion_forbidden": True,
        },
    }


def validate_retry_v2_output_path(root: Path, output_path: str) -> str:
    """Permit only the new V2 derivative path, never a V1 artifact."""
    if output_path != RETRY_V2_GENERATED_ARTIFACT_PATH:
        raise SourceReadyGenerationPilotError("retry V2 output path must be new and must not overwrite V1")
    resolve_root_path(Path(root).resolve(), output_path, label="retry V2 output path")
    return output_path


def validate_retry_v2_generated_artifact(
    root: Path,
    job_id: str,
    item_specs: dict[str, Any],
    semantic_preflight: dict[str, Any],
    artifact: dict[str, Any],
    *,
    previous_artifact: dict[str, Any] | None = None,
    previous_verification: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Validate exact V2 plan lineage, blueprint mapping, and slot-scoped evidence closure."""
    root = Path(root).resolve()
    generator_input = build_retry_v2_generator_input(
        root, job_id, item_specs, semantic_preflight
    )
    specs = generator_input["item_specs"]
    if (
        not isinstance(artifact, dict)
        or artifact.get("schema_version") != "2.0"
        or artifact.get("scope") != "RETRY_V2_GENERATED_QUESTIONS"
        or artifact.get("job_id") != job_id
        or not isinstance(artifact.get("generator_id"), str)
        or not artifact["generator_id"].strip()
    ):
        raise SourceReadyGenerationPilotError("retry V2 generated artifact identity is invalid")
    if _actor_key(artifact["generator_id"]) in {
        _actor_key(specs["author_id"]), _actor_key(semantic_preflight["reviewer_id"])
    }:
        raise SourceReadyGenerationPilotError("retry V2 generator must be independent of authorship and preflight")
    if artifact.get("item_spec_path") != RETRY_V2_ITEM_SPEC_PATH or artifact.get("item_spec_sha256") != _sha256(specs):
        raise SourceReadyGenerationPilotError("retry V2 generated item-spec fingerprint is invalid")
    if artifact.get("semantic_preflight_path") != RETRY_V2_PREFLIGHT_PATH or artifact.get("semantic_preflight_sha256") != _sha256(semantic_preflight):
        raise SourceReadyGenerationPilotError("retry V2 generated preflight fingerprint is invalid")
    revision_cycle = artifact.get("revision_cycle")
    revised_ids = artifact.get("revised_item_spec_ids")
    if revision_cycle not in {0, 1} or not isinstance(revised_ids, list) or len(set(revised_ids)) != len(revised_ids):
        raise SourceReadyGenerationPilotError("retry V2 generated revision lineage is invalid")
    valid_spec_ids = {card["v2_item_spec_id"] for card in specs["cards"]}
    if revision_cycle == 0:
        if (
            revised_ids
            or "previous_generated_artifact_sha256" in artifact
            or "previous_verification_sha256" in artifact
            or previous_artifact is not None
            or previous_verification is not None
        ):
            raise SourceReadyGenerationPilotError("retry V2 initial generation has invalid revision lineage")
    else:
        if previous_artifact is None:
            raise SourceReadyGenerationPilotError("retry V2 revision requires the previous generated artifact")
        if previous_verification is None:
            raise SourceReadyGenerationPilotError("retry V2 revision requires the previous verification")
        validate_retry_v2_generated_artifact(
            root, job_id, specs, semantic_preflight, previous_artifact
        )
        validate_retry_v2_verification(
            root,
            job_id,
            specs,
            semantic_preflight,
            previous_artifact,
            previous_verification,
        )
        rejected_spec_ids = [
            row["v2_item_spec_id"]
            for row in previous_verification["verdicts"]
            if row["verdict"] == "REJECTED_FOR_REVISION"
        ]
        if (
            previous_artifact.get("revision_cycle") != 0
            or previous_verification.get("local_failure_determination") != "LOCAL"
            or previous_verification.get("systemic_failure") is not False
            or not 1 <= len(rejected_spec_ids) <= 2
            or revised_ids != rejected_spec_ids
            or not set(revised_ids).issubset(valid_spec_ids)
            or artifact.get("previous_generated_artifact_sha256") != _sha256(previous_artifact)
            or artifact.get("previous_verification_sha256") != _sha256(previous_verification)
        ):
            raise SourceReadyGenerationPilotError("retry V2 revision previous generated artifact lineage is invalid")
    items = artifact.get("items")
    expected = [(card["v2_item_spec_id"], card["retry_slot_id"]) for card in specs["cards"]]
    actual = [(item.get("v2_item_spec_id"), item.get("retry_slot_id")) for item in items if isinstance(item, dict)] if isinstance(items, list) else []
    if not isinstance(items, list) or len(items) != 10 or actual != expected:
        raise SourceReadyGenerationPilotError("retry V2 generated items must exactly match all item specs")
    stems: list[str] = []
    correct_answers: list[str] = []
    for card, item in zip(specs["cards"], items, strict=True):
        if (
            item.get("item_spec_sha256") != _sha256(card)
            or item.get("semantic_signature") != card["semantic_signature"]
            or item.get("learner_decision") != card["learner_decision"]
            or item.get("answer_category") != card["answer_category"]
            or item.get("realized_reasoning_steps") != card["reasoning_chain"]
        ):
            raise SourceReadyGenerationPilotError("retry V2 generated item does not preserve its item-spec fingerprint or fields")
        if not isinstance(item.get("stem"), str) or not item["stem"].strip():
            raise SourceReadyGenerationPilotError("retry V2 generated item requires a stem")
        stems.append(_normalized_text(item["stem"]))
        options = item.get("options")
        if not isinstance(options, list) or len(options) != 4 or any(not isinstance(option, dict) for option in options):
            raise SourceReadyGenerationPilotError("retry V2 generated item requires exactly four options")
        keys = [option.get("key") for option in options]
        if keys != ["A", "B", "C", "D"] or any(not isinstance(option.get("text"), str) or not option["text"].strip() for option in options):
            raise SourceReadyGenerationPilotError("retry V2 generated options are invalid")
        correct_answer = item.get("correct_answer")
        if correct_answer not in keys:
            raise SourceReadyGenerationPilotError("retry V2 generated item must have one clearly keyed best answer")
        correct_answers.append(correct_answer)
        correct_options = [option for option in options if option.get("blueprint_role") == "BEST_ANSWER"]
        if len(correct_options) != 1 or correct_options[0]["key"] != correct_answer:
            raise SourceReadyGenerationPilotError("retry V2 generated item must have one clearly keyed best answer")
        expected_blueprint = [
            (entry["distractor_id"], entry["competing_concept_id"])
            for entry in card["distractor_blueprint"]
        ]
        actual_blueprint = [
            (option.get("distractor_id"), option.get("competing_concept_id"))
            for option in options if option["key"] != correct_answer
        ]
        if actual_blueprint != expected_blueprint:
            raise SourceReadyGenerationPilotError("retry V2 generated distractor blueprint does not match the approved spec")
        rationales = item.get("distractor_rationales")
        if (
            not isinstance(item.get("correct_answer_rationale"), str)
            or not item["correct_answer_rationale"].strip()
            or not isinstance(rationales, dict)
            or set(rationales) != set(keys) - {correct_answer}
            or any(not isinstance(value, str) or not value.strip() for value in rationales.values())
        ):
            raise SourceReadyGenerationPilotError("retry V2 generated item requires complete rationales")
        required_vignette_ids = [
            fact["requirement_id"] for fact in card["vignette_requirements"]["facts"]
        ] if card["vignette_requirements"]["required"] else []
        if item.get("vignette_requirement_ids_used") != required_vignette_ids:
            raise SourceReadyGenerationPilotError("retry V2 generated item does not realize approved vignette requirements")
        authorized = {_retry_reference_key(reference) for reference in card["authorized_evidence"]}
        _retry_v2_evidence_refs_valid(item.get("evidence_references"), authorized, "generated item")
        closure = item.get("assertion_evidence")
        if not isinstance(closure, dict) or set(closure) != _RETRY_ASSERTION_PARTS:
            raise SourceReadyGenerationPilotError("retry V2 generated item requires complete assertion evidence closure")
        for part, references in closure.items():
            _retry_v2_evidence_refs_valid(references, authorized, f"generated {part} assertion")
    if len(set(stems)) != 10:
        raise SourceReadyGenerationPilotError("retry V2 generated items contain an exact duplicate stem")
    if {key: correct_answers.count(key) for key in "ABCD"} != {"A": 3, "B": 3, "C": 2, "D": 2}:
        raise SourceReadyGenerationPilotError("retry V2 answer keys must use the balanced 3/3/2/2 distribution")
    if revision_cycle == 1 and previous_artifact is not None:
        previous_by_id = {item["v2_item_spec_id"]: item for item in previous_artifact["items"]}
        changed_ids = {
            item["v2_item_spec_id"]
            for item in items
            if item != previous_by_id[item["v2_item_spec_id"]]
        }
        if changed_ids != set(revised_ids):
            raise SourceReadyGenerationPilotError("retry V2 changed items do not match the local revision set")
        for item in items:
            if item["v2_item_spec_id"] not in revised_ids and item != previous_by_id[item["v2_item_spec_id"]]:
                raise SourceReadyGenerationPilotError("retry V2 revision changed an item outside the local revision set")
    return artifact


def retry_v2_1_generation_candidate_sha256(artifact: dict[str, Any]) -> str:
    """Fingerprint candidate content independently of its later semantic-review receipt."""
    candidate = dict(artifact)
    candidate.pop("semantic_generation_review_path", None)
    candidate.pop("semantic_generation_review_sha256", None)
    return _sha256(candidate)


def build_retry_v2_1_generator_input(
    root: Path,
    job_id: str,
    item_specs: dict[str, Any],
    semantic_preflight: dict[str, Any],
    selected_v2_item_spec_ids: list[str],
) -> dict[str, Any]:
    """Build a V2.1 execution contract for an exact non-empty subset of approved specs."""
    root = Path(root).resolve()
    base = build_retry_v2_generator_input(root, job_id, item_specs, semantic_preflight)
    valid_ids = [card["v2_item_spec_id"] for card in base["item_specs"]["cards"]]
    if (
        not isinstance(selected_v2_item_spec_ids, list)
        or not 1 <= len(selected_v2_item_spec_ids) <= 10
        or len(set(selected_v2_item_spec_ids)) != len(selected_v2_item_spec_ids)
        or any(identifier not in valid_ids for identifier in selected_v2_item_spec_ids)
        or selected_v2_item_spec_ids != [identifier for identifier in valid_ids if identifier in selected_v2_item_spec_ids]
    ):
        raise SourceReadyGenerationPilotError("retry V2.1 selected item specs are invalid")
    selected = [
        card for card in base["item_specs"]["cards"]
        if card["v2_item_spec_id"] in selected_v2_item_spec_ids
    ]
    return {
        **base,
        "schema_version": "2.1",
        "scope": "RETRY_V2_1_GENERATOR_INPUT",
        "selected_v2_item_spec_ids": selected_v2_item_spec_ids,
        "item_specs": {**base["item_specs"], "cards": selected},
        "generation_policy": {
            **base["generation_policy"],
            "semantic_instantiation_review_required": True,
            "definition_or_keyword_flattening_forbidden": True,
            "reasoning_chain_scenario_mapping_required": True,
            "vignette_ablation_review_required": True,
            "evidence_discriminant_location_required": True,
            "distractor_instantiation_required": True,
            "prohibited_shortcuts_must_be_reviewed": True,
            "rationale_discriminators_required": True,
        },
    }


def _retry_v2_1_expected_items(
    root: Path,
    job_id: str,
    item_specs: dict[str, Any],
    semantic_preflight: dict[str, Any],
    artifact: dict[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    selected_ids = artifact.get("selected_v2_item_spec_ids") if isinstance(artifact, dict) else None
    context = build_retry_v2_1_generator_input(
        root, job_id, item_specs, semantic_preflight, selected_ids
    )
    cards = context["item_specs"]["cards"]
    if (
        artifact.get("schema_version") != "2.1"
        or artifact.get("scope") != "RETRY_V2_1_GENERATED_QUESTIONS"
        or artifact.get("job_id") != job_id
        or not isinstance(artifact.get("generator_id"), str)
        or not artifact["generator_id"].strip()
        or artifact.get("item_spec_path") != RETRY_V2_ITEM_SPEC_PATH
        or artifact.get("item_spec_sha256") != _sha256(item_specs)
        or artifact.get("semantic_preflight_path") != RETRY_V2_PREFLIGHT_PATH
        or artifact.get("semantic_preflight_sha256") != _sha256(semantic_preflight)
    ):
        raise SourceReadyGenerationPilotError("retry V2.1 generated artifact identity or lineage is invalid")
    if _actor_key(artifact["generator_id"]) in {
        _actor_key(item_specs["author_id"]), _actor_key(semantic_preflight["reviewer_id"])
    }:
        raise SourceReadyGenerationPilotError("retry V2.1 generator must be independent of authorship and preflight")
    items = artifact.get("items")
    expected = [(card["v2_item_spec_id"], card["retry_slot_id"]) for card in cards]
    actual = [(item.get("v2_item_spec_id"), item.get("retry_slot_id")) for item in items if isinstance(item, dict)] if isinstance(items, list) else []
    if not isinstance(items, list) or actual != expected:
        raise SourceReadyGenerationPilotError("retry V2.1 generated items must exactly match selected item specs")
    return context, cards


def _retry_v2_1_validate_instantiation(card: dict[str, Any], item: dict[str, Any]) -> None:
    mapping = item.get("spec_instantiation")
    if not isinstance(mapping, dict) or mapping.get("learner_decision") != card["learner_decision"]:
        raise SourceReadyGenerationPilotError("retry V2.1 learner-decision instantiation is invalid")
    reasoning = mapping.get("reasoning_chain")
    expected_steps = card["reasoning_chain"]
    if (
        not isinstance(reasoning, list)
        or [entry.get("step") for entry in reasoning if isinstance(entry, dict)] != expected_steps
        or len(reasoning) != len(expected_steps)
        or any(not isinstance(entry.get("scenario_fact"), str) or not entry["scenario_fact"].strip() or entry.get("location") not in {"stem", "options"} for entry in reasoning)
    ):
        raise SourceReadyGenerationPilotError("retry V2.1 reasoning instantiation is invalid")
    discriminants = mapping.get("evidence_discriminants")
    expected_discriminants = card["evidence_discriminants"]
    if (
        not isinstance(discriminants, list)
        or [entry.get("fact") for entry in discriminants if isinstance(entry, dict)] != [entry["fact"] for entry in expected_discriminants]
        or len(discriminants) != len(expected_discriminants)
    ):
        raise SourceReadyGenerationPilotError("retry V2.1 evidence-discriminant instantiation is invalid")
    for actual, expected in zip(discriminants, expected_discriminants, strict=True):
        if (
            not isinstance(actual.get("scenario_fact"), str) or not actual["scenario_fact"].strip()
            or actual.get("location") not in {"stem", "options"}
            or actual.get("evidence_references") != expected["evidence_refs"]
        ):
            raise SourceReadyGenerationPilotError("retry V2.1 evidence-discriminant instantiation is invalid")
    distractors = mapping.get("distractor_instantiations")
    blueprint = card["distractor_blueprint"]
    if not isinstance(distractors, list) or len(distractors) != len(blueprint):
        raise SourceReadyGenerationPilotError("retry V2.1 distractor instantiation is invalid")
    for actual, expected in zip(distractors, blueprint, strict=True):
        if not isinstance(actual, dict) or any(actual.get(key) != expected[source] for key, source in {
            "distractor_id": "distractor_id", "competing_concept_id": "competing_concept_id",
            "tempting_feature": "temptation", "scenario_feature": "scenario_feature",
            "disqualifying_discriminant": "evidence_discriminator", "evidence_references": "evidence_refs",
        }.items()):
            raise SourceReadyGenerationPilotError("retry V2.1 distractor instantiation is invalid")
    ablation = mapping.get("vignette_ablation")
    required_facts = [fact["fact"] for fact in card["vignette_requirements"]["facts"]]
    if (
        not isinstance(ablation, dict)
        or ablation.get("scenario_facts") != required_facts
        or ablation.get("answerable_without_scenario") is not False
        or not isinstance(ablation.get("explanation"), str)
        or not ablation["explanation"].strip()
    ):
        raise SourceReadyGenerationPilotError("retry V2.1 vignette ablation is invalid")
    shortcuts = mapping.get("prohibited_shortcuts_checked")
    if not isinstance(shortcuts, dict) or shortcuts.get("checked") != card["prohibited_shortcuts"] or shortcuts.get("detected") != []:
        raise SourceReadyGenerationPilotError("retry V2.1 prohibited shortcuts are invalid")
    rationale = mapping.get("rationale_mapping")
    best = rationale.get("best_answer") if isinstance(rationale, dict) else None
    alternatives = rationale.get("distractors") if isinstance(rationale, dict) else None
    if (
        not isinstance(best, dict)
        or not all(isinstance(best.get(key), str) and best[key].strip() for key in {"positive_evidence", "decisive_discriminant"})
        or not isinstance(alternatives, list)
        or [entry.get("distractor_id") for entry in alternatives if isinstance(entry, dict)] != [entry["distractor_id"] for entry in blueprint]
        or len(alternatives) != len(blueprint)
        or any(not all(isinstance(entry.get(key), str) and entry[key].strip() for key in {"plausibility", "discriminator"}) for entry in alternatives)
    ):
        raise SourceReadyGenerationPilotError("retry V2.1 rationale instantiation is invalid")


def validate_retry_v2_1_semantic_generation_review(
    root: Path,
    job_id: str,
    item_specs: dict[str, Any],
    semantic_preflight: dict[str, Any],
    artifact: dict[str, Any],
    review: dict[str, Any],
) -> dict[str, Any]:
    """Bind a fresh semantic reviewer to the exact V2.1 candidate without self-approval."""
    root = Path(root).resolve()
    _, cards = _retry_v2_1_expected_items(root, job_id, item_specs, semantic_preflight, artifact)
    if (
        not isinstance(review, dict)
        or review.get("schema_version") != "2.1"
        or review.get("scope") != "RETRY_V2_1_SEMANTIC_GENERATION_REVIEW"
        or review.get("job_id") != job_id
        or review.get("generated_candidate_sha256") != retry_v2_1_generation_candidate_sha256(artifact)
        or not isinstance(review.get("reviewer_id"), str)
        or not review["reviewer_id"].strip()
    ):
        raise SourceReadyGenerationPilotError("retry V2.1 semantic generation review identity is invalid")
    excluded = {
        _actor_key(item_specs["author_id"]), _actor_key(semantic_preflight["reviewer_id"]),
        _actor_key(artifact["generator_id"]),
    }
    if _actor_key(review["reviewer_id"]) in excluded:
        raise SourceReadyGenerationPilotError("retry V2.1 semantic generation reviewer must be fresh")
    rows = review.get("verdicts")
    expected = [(card["v2_item_spec_id"], card["retry_slot_id"]) for card in cards]
    actual = [(row.get("v2_item_spec_id"), row.get("retry_slot_id")) for row in rows if isinstance(row, dict)] if isinstance(rows, list) else []
    if not isinstance(rows, list) or actual != expected:
        raise SourceReadyGenerationPilotError("retry V2.1 semantic generation review must cover every candidate")
    for row in rows:
        assessments = row.get("assessments")
        if (
            row.get("verdict") not in {"ACCEPT_GENERATED_ITEM", "REGENERATE_FROM_SAME_SPEC"}
            or not isinstance(assessments, dict)
            or set(assessments) != _RETRY_V2_1_SEMANTIC_GENERATION_ASSESSMENTS
            or any(value not in {"PASS", "FAIL"} for value in assessments.values())
            or not isinstance(row.get("explanation"), str)
            or not row["explanation"].strip()
        ):
            raise SourceReadyGenerationPilotError("retry V2.1 semantic generation review row is invalid")
        if row["verdict"] == "ACCEPT_GENERATED_ITEM" and any(value != "PASS" for value in assessments.values()):
            raise SourceReadyGenerationPilotError("retry V2.1 accepted semantic review contains a failure")
        if row["verdict"] == "REGENERATE_FROM_SAME_SPEC" and all(value == "PASS" for value in assessments.values()):
            raise SourceReadyGenerationPilotError("retry V2.1 rejected semantic review lacks a concrete failure")
    return review


def validate_retry_v2_1_generated_artifact(
    root: Path,
    job_id: str,
    item_specs: dict[str, Any],
    semantic_preflight: dict[str, Any],
    artifact: dict[str, Any],
    semantic_review: dict[str, Any],
) -> dict[str, Any]:
    """Fail closed unless every V2.1 item maps to its spec and is semantically accepted fresh."""
    root = Path(root).resolve()
    _, cards = _retry_v2_1_expected_items(root, job_id, item_specs, semantic_preflight, artifact)
    allowed_paths = {RETRY_V2_1_MICRO_SEMANTIC_REVIEW_PATH, RETRY_V2_1_FULL_SEMANTIC_REVIEW_PATH}
    if artifact.get("semantic_generation_review_path") not in allowed_paths or artifact.get("semantic_generation_review_sha256") != _sha256(semantic_review):
        raise SourceReadyGenerationPilotError("retry V2.1 semantic generation review receipt is invalid")
    review = validate_retry_v2_1_semantic_generation_review(
        root, job_id, item_specs, semantic_preflight, artifact, semantic_review
    )
    if any(row["verdict"] != "ACCEPT_GENERATED_ITEM" for row in review["verdicts"]):
        raise SourceReadyGenerationPilotError("retry V2.1 semantic generation review acceptance is required")
    for card, item in zip(cards, artifact["items"], strict=True):
        if (
            item.get("item_spec_sha256") != _sha256(card)
            or item.get("semantic_signature") != card["semantic_signature"]
            or item.get("learner_decision") != card["learner_decision"]
            or item.get("answer_category") != card["answer_category"]
            or item.get("realized_reasoning_steps") != card["reasoning_chain"]
            or not isinstance(item.get("stem"), str)
            or not item["stem"].strip()
        ):
            raise SourceReadyGenerationPilotError("retry V2.1 generated item does not preserve its approved spec")
        options = item.get("options")
        if not isinstance(options, list) or len(options) != 4 or [option.get("key") for option in options if isinstance(option, dict)] != ["A", "B", "C", "D"]:
            raise SourceReadyGenerationPilotError("retry V2.1 generated options are invalid")
        correct = item.get("correct_answer")
        best = [option for option in options if option.get("blueprint_role") == "BEST_ANSWER"]
        if correct not in {"A", "B", "C", "D"} or len(best) != 1 or best[0].get("key") != correct:
            raise SourceReadyGenerationPilotError("retry V2.1 generated item requires one best answer")
        actual_blueprint = [(option.get("distractor_id"), option.get("competing_concept_id")) for option in options if option.get("key") != correct]
        expected_blueprint = [(entry["distractor_id"], entry["competing_concept_id"]) for entry in card["distractor_blueprint"]]
        if actual_blueprint != expected_blueprint:
            raise SourceReadyGenerationPilotError("retry V2.1 generated distractor blueprint is invalid")
        rationales = item.get("distractor_rationales")
        if not isinstance(item.get("correct_answer_rationale"), str) or not item["correct_answer_rationale"].strip() or not isinstance(rationales, dict) or set(rationales) != ({"A", "B", "C", "D"} - {correct}) or any(not isinstance(value, str) or not value.strip() for value in rationales.values()):
            raise SourceReadyGenerationPilotError("retry V2.1 generated rationales are invalid")
        required_vignettes = [fact["requirement_id"] for fact in card["vignette_requirements"]["facts"]]
        if item.get("vignette_requirement_ids_used") != required_vignettes:
            raise SourceReadyGenerationPilotError("retry V2.1 generated vignette requirements are invalid")
        authorized = {_retry_reference_key(reference) for reference in card["authorized_evidence"]}
        _retry_v2_evidence_refs_valid(item.get("evidence_references"), authorized, "V2.1 generated item")
        closure = item.get("assertion_evidence")
        if not isinstance(closure, dict) or set(closure) != _RETRY_ASSERTION_PARTS:
            raise SourceReadyGenerationPilotError("retry V2.1 generated assertion closure is invalid")
        for part, references in closure.items():
            _retry_v2_evidence_refs_valid(references, authorized, f"V2.1 generated {part} assertion")
        _retry_v2_1_validate_instantiation(card, item)
    return artifact


def build_retry_v2_verifier_input(
    root: Path,
    job_id: str,
    item_specs: dict[str, Any],
    semantic_preflight: dict[str, Any],
    generated_artifact: dict[str, Any],
    *,
    previous_generated_artifact: dict[str, Any] | None = None,
    previous_verification: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build fresh final-review context bound to exact specs, evidence, and generated bytes."""
    root = Path(root).resolve()
    validated = validate_retry_v2_generated_artifact(
        root,
        job_id,
        item_specs,
        semantic_preflight,
        generated_artifact,
        previous_artifact=previous_generated_artifact,
        previous_verification=previous_verification,
    )
    preflight_input = build_retry_v2_preflight_input(root, job_id, item_specs)
    return {
        "schema_version": "2.0",
        "scope": "RETRY_V2_INDEPENDENT_VERIFIER_INPUT",
        "job_id": job_id,
        "item_specs": item_specs,
        "item_spec_fingerprint": {"sha256": _sha256(item_specs)},
        "generated_artifact": validated,
        "generated_artifact_fingerprint": {"sha256": _sha256(validated)},
        "semantic_preflight_fingerprint": {"sha256": _sha256(semantic_preflight)},
        "authorized_evidence_by_card": preflight_input["authorized_evidence_by_card"],
        "canonical_level_context": preflight_input["canonical_level_context"],
        "excluded_context": ["GENERATOR_SELF_EVALUATION", "PREFLIGHT_SELF_EVALUATION", "WEB"],
    }


def validate_retry_v2_verification(
    root: Path,
    job_id: str,
    item_specs: dict[str, Any],
    semantic_preflight: dict[str, Any],
    generated_artifact: dict[str, Any],
    artifact: dict[str, Any],
    *,
    previous_generated_artifact: dict[str, Any] | None = None,
    previous_verification: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Validate fresh verdicts and deterministically evaluate the user-approved 9/10 pilot gate."""
    root = Path(root).resolve()
    validate_retry_v2_item_specs(root, job_id, item_specs)
    validate_retry_v2_semantic_preflight(root, job_id, item_specs, semantic_preflight)
    validate_retry_v2_generated_artifact(
        root,
        job_id,
        item_specs,
        semantic_preflight,
        generated_artifact,
        previous_artifact=previous_generated_artifact,
        previous_verification=previous_verification,
    )
    if (
        not isinstance(artifact, dict)
        or artifact.get("schema_version") != "2.0"
        or artifact.get("scope") != "RETRY_V2_INDEPENDENT_VERIFICATION"
        or artifact.get("job_id") != job_id
    ):
        raise SourceReadyGenerationPilotError("retry V2 verification identity is invalid")
    verifier_id = artifact.get("verifier_id")
    excluded_reviewers = {
        _actor_key(item_specs["author_id"]),
        _actor_key(semantic_preflight["reviewer_id"]),
        _actor_key(generated_artifact["generator_id"]),
    }
    if not isinstance(verifier_id, str) or not verifier_id.strip() or _actor_key(verifier_id) in excluded_reviewers:
        raise SourceReadyGenerationPilotError("retry V2 independent verifier must be fresh")
    fingerprints = (
        artifact.get("item_spec_path") == RETRY_V2_ITEM_SPEC_PATH
        and artifact.get("item_spec_sha256") == _sha256(item_specs)
        and artifact.get("semantic_preflight_path") == RETRY_V2_PREFLIGHT_PATH
        and artifact.get("semantic_preflight_sha256") == _sha256(semantic_preflight)
        and artifact.get("generated_artifact_path") == RETRY_V2_GENERATED_ARTIFACT_PATH
        and artifact.get("generated_artifact_sha256") == _sha256(generated_artifact)
    )
    if not fingerprints:
        raise SourceReadyGenerationPilotError("retry V2 verification artifact fingerprints are invalid")
    if artifact.get("independent_context") not in {"PASS", "FAIL"} or artifact.get("evidence_traceability") not in {"PASS", "FAIL"}:
        raise SourceReadyGenerationPilotError("retry V2 verification context or evidence status is invalid")
    if artifact.get("set_level_duplication") not in {"NONE", "LOW", "MODERATE", "HIGH"}:
        raise SourceReadyGenerationPilotError("retry V2 verification set-level duplication is invalid")
    if not isinstance(artifact.get("systemic_failure"), bool) or not isinstance(artifact.get("systemic_failure_reasons"), list):
        raise SourceReadyGenerationPilotError("retry V2 verification systemic assessment is invalid")
    if artifact["systemic_failure"] != bool(artifact["systemic_failure_reasons"]) or any(not isinstance(reason, str) or not reason.strip() for reason in artifact["systemic_failure_reasons"]):
        raise SourceReadyGenerationPilotError("retry V2 verification systemic assessment is inconsistent")
    if artifact.get("local_failure_determination") not in {"NONE", "LOCAL", "SYSTEMIC"}:
        raise SourceReadyGenerationPilotError("retry V2 verification failure determination is invalid")
    if artifact.get("final_revision_cycle_used") != (generated_artifact.get("revision_cycle") == 1):
        raise SourceReadyGenerationPilotError("retry V2 verification revision-cycle status is invalid")
    rows = artifact.get("verdicts")
    expected = [(card["v2_item_spec_id"], card["retry_slot_id"]) for card in item_specs["cards"]]
    actual = [(row.get("v2_item_spec_id"), row.get("retry_slot_id")) for row in rows if isinstance(row, dict)] if isinstance(rows, list) else []
    if not isinstance(rows, list) or len(rows) != 10 or actual != expected:
        raise SourceReadyGenerationPilotError("retry V2 verification verdicts must exactly match all items")
    category_counts = {category: 0 for category in _RETRY_V2_REJECTION_CATEGORIES}
    passed = 0
    fatal_dimension_failures = {"factual_correctness": 0, "semantic_evidence_support": 0}
    material_duplication_failures = 0
    for row in rows:
        verdict = row.get("verdict")
        categories = row.get("reason_categories")
        assessments = row.get("dimension_assessments")
        if verdict not in {"PASS", "REJECTED_FOR_REVISION"}:
            raise SourceReadyGenerationPilotError("retry V2 verification verdict is invalid")
        if not isinstance(categories, list) or len(set(categories)) != len(categories) or any(category not in _RETRY_V2_REJECTION_CATEGORIES for category in categories):
            raise SourceReadyGenerationPilotError("retry V2 verification rejection categories are invalid")
        if not isinstance(assessments, dict) or set(assessments) != _RETRY_V2_FINAL_ASSESSMENTS or any(value not in {"PASS", "FAIL"} for value in assessments.values()):
            raise SourceReadyGenerationPilotError("retry V2 verification dimension assessments are invalid")
        if not isinstance(row.get("explanation"), str) or not row["explanation"].strip():
            raise SourceReadyGenerationPilotError("retry V2 verification explanation is required")
        if verdict == "PASS":
            if categories or any(value != "PASS" for value in assessments.values()):
                raise SourceReadyGenerationPilotError("retry V2 PASS verdict contains a failure")
            passed += 1
        elif not categories or all(value == "PASS" for value in assessments.values()):
            raise SourceReadyGenerationPilotError("retry V2 rejected verdict lacks a concrete failure")
        if assessments["factual_correctness"] == "FAIL":
            fatal_dimension_failures["factual_correctness"] += 1
            if "FACTUAL_ERROR" not in categories:
                raise SourceReadyGenerationPilotError("retry V2 factual failure must use FACTUAL_ERROR")
        elif "FACTUAL_ERROR" in categories:
            raise SourceReadyGenerationPilotError("retry V2 FACTUAL_ERROR requires a factual failure")
        if assessments["semantic_evidence_support"] == "FAIL":
            fatal_dimension_failures["semantic_evidence_support"] += 1
            if "UNSUPPORTED_CLAIM" not in categories:
                raise SourceReadyGenerationPilotError("retry V2 unsupported evidence failure must use UNSUPPORTED_CLAIM")
        elif "UNSUPPORTED_CLAIM" in categories:
            raise SourceReadyGenerationPilotError("retry V2 UNSUPPORTED_CLAIM requires an unsupported evidence failure")
        if assessments["semantic_duplication"] == "FAIL":
            material_duplication_failures += 1
            if "MATERIAL_DUPLICATION" not in categories:
                raise SourceReadyGenerationPilotError("retry V2 semantic duplication failure must use MATERIAL_DUPLICATION")
        elif "MATERIAL_DUPLICATION" in categories:
            raise SourceReadyGenerationPilotError("retry V2 MATERIAL_DUPLICATION requires a semantic duplication failure")
        for category in categories:
            category_counts[category] += 1
    rejected = 10 - passed
    if artifact.get("questions_passed") != passed or artifact.get("questions_rejected") != rejected:
        raise SourceReadyGenerationPilotError("retry V2 verification question counts are inconsistent")
    if artifact.get("rejection_categories") != category_counts:
        raise SourceReadyGenerationPilotError("retry V2 verification category counts are inconsistent")
    if rejected == 0 and (artifact["local_failure_determination"] != "NONE" or artifact["systemic_failure"]):
        raise SourceReadyGenerationPilotError("retry V2 verification failure determination is inconsistent")
    if rejected and not artifact["systemic_failure"] and artifact["local_failure_determination"] != "LOCAL":
        raise SourceReadyGenerationPilotError("retry V2 verification failure determination must be LOCAL")
    if artifact["systemic_failure"] and artifact["local_failure_determination"] != "SYSTEMIC":
        raise SourceReadyGenerationPilotError("retry V2 verification failure determination must be SYSTEMIC")
    accepted = (
        passed >= 9
        and category_counts["FACTUAL_ERROR"] == 0
        and category_counts["UNSUPPORTED_CLAIM"] == 0
        and fatal_dimension_failures["factual_correctness"] == 0
        and fatal_dimension_failures["semantic_evidence_support"] == 0
        and category_counts["MATERIAL_DUPLICATION"] == 0
        and material_duplication_failures == 0
        and artifact["evidence_traceability"] == "PASS"
        and artifact["independent_context"] == "PASS"
        and artifact["set_level_duplication"] in {"NONE", "LOW"}
        and not artifact["systemic_failure"]
    )
    return {
        "job_id": job_id,
        "status": "PILOT_ACCEPTED" if accepted else "PILOT_NOT_ACCEPTED",
        "questions_passed": passed,
        "questions_rejected": rejected,
        "rejection_categories": category_counts,
        "set_level_duplication": artifact["set_level_duplication"],
    }


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
