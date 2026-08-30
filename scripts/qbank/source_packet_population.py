"""Validate one plan-bound pilot of populated current-source packets."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
import hashlib
from pathlib import Path
from typing import Any

from .jsonio import read_json
from .paths import resolve_root_path
from .source_packet_plan import build_source_packet_plan


_PILOT_BATCH_ID = "SRB-089"
_READY = "SOURCE_PACKET_READY"
_INCOMPLETE = "INCOMPLETE_RESEARCH"
_BLOCKED = {
    "BLOCKED_EVIDENCE_CONFLICT",
    "BLOCKED_JURISDICTION",
}
_CURRENTNESS = {"CURRENT", "CURRENT_WITH_CONTEXT"}
_PLANNING_FIELDS = (
    "source_packet_id",
    "discipline",
    "evidence_requirement_key",
    "cross_address_reuse_basis",
    "covered_allocation_address_ids",
    "covered_generation_job_ids",
    "evidence_requirement_types",
    "source_family_targets",
    "freshness",
    "jurisdiction",
    "jurisdiction_resolution_required",
    "toronto_notes_current_guidance_authority",
    "claim_traceability_contract",
    "knowledge_requirement",
)


@dataclass
class SourcePacketPopulationValidation:
    status: str
    checks: dict[str, str] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)


def _path(root: Path, relative: str) -> Path:
    return resolve_root_path(root, relative, label=relative)


def _canonical_context(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    plan_path = _path(root, "research/qgen/source_packet_plan.json")
    plan = read_json(plan_path)
    if not isinstance(plan, dict):
        raise TypeError("source packet plan must be an object")
    rebuilt, _ = build_source_packet_plan(root)
    return plan, rebuilt


def _pilot_packet_ids(plan: dict[str, Any]) -> list[str]:
    batch = next(
        (
            item for item in plan.get("research_batches", [])
            if item.get("research_batch_id") == _PILOT_BATCH_ID
        ),
        None,
    )
    if not isinstance(batch, dict):
        return []
    return list(batch.get("source_packet_ids", []))


def _supported_requirement_count(packet: dict[str, Any]) -> int:
    supported = {
        requirement_type
        for recommendation in packet.get("supported_recommendations", [])
        if isinstance(recommendation, dict)
        for requirement_type in recommendation.get("evidence_requirement_types", [])
        if isinstance(requirement_type, str)
    }
    return sum(
        requirement_type in supported
        for requirement_type in packet.get("evidence_requirement_types", [])
    )


def _source_metadata_errors(packet_id: str, source: Any) -> list[str]:
    if not isinstance(source, dict):
        return [f"{packet_id}: authoritative source must be an object"]
    required_text = (
        "source_id",
        "title",
        "issuing_organization",
        "source_family",
        "source_type",
        "url",
        "retrieval_date",
        "jurisdiction",
        "date_status",
        "version_status",
        "currentness_status",
        "currentness_notes",
    )
    if any(
        not isinstance(source.get(field_name), str) or not source[field_name].strip()
        for field_name in required_text
    ):
        return [f"{packet_id}: source metadata is incomplete"]
    errors: list[str] = []
    if not source["url"].startswith("https://"):
        errors.append(f"{packet_id}: authoritative source URL must use HTTPS")
    if source.get("is_canadian") not in {True, False}:
        errors.append(f"{packet_id}: source Canadian classification is missing")
    if source.get("international_fallback") not in {True, False}:
        errors.append(f"{packet_id}: source fallback classification is missing")
    if source["date_status"] == "AVAILABLE":
        if not any(
            isinstance(source.get(field_name), str) and source[field_name].strip()
            for field_name in ("publication_date", "update_date")
        ):
            errors.append(f"{packet_id}: available source date is not recorded")
    elif source["date_status"] != "NOT_STATED":
        errors.append(f"{packet_id}: source date status is invalid")
    if source["version_status"] == "AVAILABLE":
        if not isinstance(source.get("guideline_version"), str) or not source[
            "guideline_version"
        ].strip():
            errors.append(f"{packet_id}: available guideline version is not recorded")
    elif source["version_status"] != "NOT_STATED":
        errors.append(f"{packet_id}: source version status is invalid")
    if source["currentness_status"] not in _CURRENTNESS:
        errors.append(f"{packet_id}: source currentness is not resolved")
    return errors


def _citation_errors(
    packet_id: str,
    citations: Any,
    source_ids: set[str],
    *,
    empty_message: str,
) -> list[str]:
    if not isinstance(citations, list) or not citations:
        return [f"{packet_id}: {empty_message}"]
    errors: list[str] = []
    for citation in citations:
        if not isinstance(citation, dict):
            errors.append(f"{packet_id}: citation must be an object")
            continue
        if citation.get("source_id") not in source_ids:
            errors.append(f"{packet_id}: citation references unknown source")
        if not isinstance(citation.get("locator"), str) or not citation["locator"].strip():
            errors.append(f"{packet_id}: citation locator is missing")
    return errors


def _claim_traceability_errors(
    packet_id: str, packet: dict[str, Any], source_ids: set[str]
) -> list[str]:
    errors: list[str] = []
    requirements = set(packet.get("evidence_requirement_types", []))
    contract = set(packet.get("claim_traceability_contract", []))
    traced_uses: set[str] = set()
    recommendations = packet.get("supported_recommendations", [])
    for recommendation in recommendations:
        if not isinstance(recommendation, dict):
            errors.append(f"{packet_id}: supported recommendation must be an object")
            continue
        if not isinstance(recommendation.get("recommendation_id"), str) or not recommendation[
            "recommendation_id"
        ].strip():
            errors.append(f"{packet_id}: recommendation ID is missing")
        if not isinstance(recommendation.get("statement"), str) or not recommendation[
            "statement"
        ].strip():
            errors.append(f"{packet_id}: recommendation statement is missing")
        claimed_types = recommendation.get("evidence_requirement_types", [])
        if not isinstance(claimed_types, list) or not claimed_types or not set(
            claimed_types
        ) <= requirements:
            errors.append(f"{packet_id}: recommendation evidence type is unsupported")
        intended_uses = recommendation.get("intended_uses", [])
        if not isinstance(intended_uses, list) or not intended_uses or not set(
            intended_uses
        ) <= contract:
            errors.append(f"{packet_id}: recommendation intended use is invalid")
        else:
            traced_uses.update(intended_uses)
        errors.extend(
            _citation_errors(
                packet_id,
                recommendation.get("source_citations"),
                source_ids,
                empty_message="important recommendation is uncited",
            )
        )
    if traced_uses != contract:
        errors.append(f"{packet_id}: claim traceability contract is incomplete")

    boundaries = packet.get("evidence_boundaries", [])
    if not isinstance(boundaries, list) or not boundaries:
        errors.append(f"{packet_id}: distractor-support evidence boundary is missing")
    else:
        for boundary in boundaries:
            if not isinstance(boundary, dict):
                errors.append(f"{packet_id}: evidence boundary must be an object")
                continue
            if not isinstance(boundary.get("boundary_id"), str) or not boundary[
                "boundary_id"
            ].strip():
                errors.append(f"{packet_id}: evidence boundary ID is missing")
            if not isinstance(boundary.get("statement"), str) or not boundary[
                "statement"
            ].strip():
                errors.append(f"{packet_id}: evidence boundary statement is missing")
            errors.extend(
                _citation_errors(
                    packet_id,
                    boundary.get("source_citations"),
                    source_ids,
                    empty_message="evidence boundary is uncited",
                )
            )
    errors.extend(
        _citation_errors(
            packet_id,
            packet.get("source_citations"),
            source_ids,
            empty_message="packet source citations are missing",
        )
    )
    exceptions = packet.get("important_contraindications_or_exceptions", [])
    if not isinstance(exceptions, list):
        errors.append(f"{packet_id}: important exceptions must be a list")
    else:
        for exception in exceptions:
            if not isinstance(exception, dict):
                errors.append(f"{packet_id}: important exception must be an object")
                continue
            if not isinstance(exception.get("exception_id"), str) or not exception[
                "exception_id"
            ].strip():
                errors.append(f"{packet_id}: important exception ID is missing")
            if not isinstance(exception.get("statement"), str) or not exception[
                "statement"
            ].strip():
                errors.append(f"{packet_id}: important exception statement is missing")
            errors.extend(
                _citation_errors(
                    packet_id,
                    exception.get("source_citations"),
                    source_ids,
                    empty_message="important exception is uncited",
                )
            )
    if not isinstance(packet.get("evidence_notes"), list) or not packet[
        "evidence_notes"
    ]:
        errors.append(f"{packet_id}: evidence notes are missing")
    return errors


def build_source_packet_population_audit(
    root: Path, population: dict[str, Any]
) -> dict[str, Any]:
    plan, _ = _canonical_context(Path(root).resolve())
    pilot_ids = set(_pilot_packet_ids(plan))
    packets = [
        packet for packet in population.get("source_packets", [])
        if isinstance(packet, dict)
    ]
    statuses = Counter(packet.get("status") for packet in packets)
    requirement_total = sum(
        len(packet.get("evidence_requirement_types", [])) for packet in packets
    )
    requirement_supported = sum(
        _supported_requirement_count(packet) for packet in packets
    )
    sources = [
        source
        for packet in packets
        for source in packet.get("authoritative_sources", [])
        if isinstance(source, dict)
    ]
    blocked_total = sum(statuses[status] for status in _BLOCKED)
    return {
        "schema_version": "1.0",
        "scope": "SOURCE_PACKET_PILOT_AUDIT",
        "PILOT_RESEARCH_BATCH_ID": population.get("pilot_research_batch_id"),
        "PILOT_PACKETS_TOTAL": len(packets),
        "PILOT_PACKETS_READY": statuses[_READY],
        "PILOT_PACKETS_BLOCKED": blocked_total,
        "PILOT_PACKETS_INCOMPLETE": len(packets) - statuses[_READY] - blocked_total,
        "AUTHORITATIVE_SOURCES_TOTAL": len(sources),
        "CANADIAN_AUTHORITATIVE_SOURCES": sum(
            source.get("is_canadian") is True for source in sources
        ),
        "INTERNATIONAL_FALLBACK_SOURCES": sum(
            source.get("international_fallback") is True for source in sources
        ),
        "PACKETS_WITH_SOURCE_DISAGREEMENT": sum(
            packet.get("disagreement_present") is True for packet in packets
        ),
        "PACKETS_WITH_UNRESOLVED_CONFLICT": sum(
            packet.get("unresolved_evidence_conflict") is True for packet in packets
        ),
        "PACKETS_WITH_JURISDICTION_BLOCKER": statuses["BLOCKED_JURISDICTION"],
        "EVIDENCE_REQUIREMENTS_TOTAL": requirement_total,
        "EVIDENCE_REQUIREMENTS_SUPPORTED": requirement_supported,
        "UNSUPPORTED_EVIDENCE_REQUIREMENTS": requirement_total - requirement_supported,
        "NON_PILOT_PACKETS_CHANGED": sum(
            packet.get("source_packet_id") not in pilot_ids for packet in packets
        ),
    }


def _population_packets(populations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        packet
        for population in populations
        for packet in population.get("source_packets", [])
        if isinstance(packet, dict)
    ]


def _population_batch_id(population: dict[str, Any]) -> str | None:
    batch_id = population.get("research_batch_id", population.get("pilot_research_batch_id"))
    return batch_id if isinstance(batch_id, str) else None


def load_integrated_source_packet_populations(root: Path) -> list[dict[str, Any]]:
    """Load committed packet populations in frozen research-batch order."""
    root = Path(root).resolve()
    plan, _ = _canonical_context(root)
    order = {
        batch.get("research_batch_id"): index
        for index, batch in enumerate(plan.get("research_batches", []))
        if isinstance(batch, dict) and isinstance(batch.get("research_batch_id"), str)
    }
    populations: list[dict[str, Any]] = []
    for path in (root / "research/qgen").glob("source_packet_population_srb_*.json"):
        population = read_json(path)
        if not isinstance(population, dict):
            raise TypeError(f"source packet population must be an object: {path}")
        populations.append(population)
    return sorted(
        populations,
        key=lambda population: (order.get(_population_batch_id(population), len(order)), _population_batch_id(population) or ""),
    )


def _batch_packet_semantic_errors(
    packet_id: str, packet: dict[str, Any], canonical: dict[str, Any]
) -> list[str]:
    """Apply the established packet-state and ready-packet evidence gates."""
    errors: list[str] = []
    status = packet.get("status")
    if status not in {_READY, _INCOMPLETE, *_BLOCKED}:
        return [f"{packet_id}: population status is invalid"]
    disagreements = packet.get("disagreements_or_ambiguities", [])
    sources = [source for source in packet.get("authoritative_sources", []) if isinstance(source, dict)]
    source_ids = {source.get("source_id") for source in sources if isinstance(source.get("source_id"), str)}
    if status == "BLOCKED_EVIDENCE_CONFLICT" and not (
        packet.get("disagreement_present") is True
        and packet.get("unresolved_evidence_conflict") is True
        and isinstance(disagreements, list)
        and disagreements
        and packet.get("verification_status") == "BLOCKED_EVIDENCE_CONFLICT"
    ):
        errors.append(f"{packet_id}: conflict block lacks unresolved disagreement")
    if status == "BLOCKED_JURISDICTION":
        if canonical.get("jurisdiction_resolution_required") is not True:
            errors.append(f"{packet_id}: canonical packet does not require jurisdiction resolution")
        if not (packet.get("jurisdiction_resolved") is False and packet.get("verification_status") == "BLOCKED_JURISDICTION"):
            errors.append(f"{packet_id}: jurisdiction block state is inconsistent")
    if status == _INCOMPLETE and packet.get("verification_status") != _INCOMPLETE:
        errors.append(f"{packet_id}: incomplete research state is inconsistent")
    if packet.get("disagreement_present") is True:
        if not isinstance(disagreements, list) or not disagreements:
            errors.append(f"{packet_id}: disagreement details are missing")
        else:
            for disagreement in disagreements:
                if not isinstance(disagreement, dict):
                    errors.append(f"{packet_id}: disagreement must be an object")
                    continue
                if any(not isinstance(disagreement.get(name), str) or not disagreement[name].strip() for name in ("disagreement_id", "summary", "resolution_status", "canadian_mccqe_applicability")):
                    errors.append(f"{packet_id}: disagreement details are incomplete")
                linked = disagreement.get("source_ids", [])
                if not isinstance(linked, list) or not linked or not set(linked) <= source_ids:
                    errors.append(f"{packet_id}: disagreement source linkage is invalid")
            unresolved = any(isinstance(item, dict) and item.get("resolution_status") == "UNRESOLVED" for item in disagreements)
            if unresolved != (packet.get("unresolved_evidence_conflict") is True):
                errors.append(f"{packet_id}: disagreement resolution state is inconsistent")
    elif disagreements:
        errors.append(f"{packet_id}: disagreement flag is inconsistent")
    if status != _READY:
        return errors
    if not sources:
        errors.append(f"{packet_id}: ready packet lacks authoritative source")
    if not packet.get("supported_recommendations"):
        errors.append(f"{packet_id}: ready packet lacks supported recommendation")
    if _supported_requirement_count(packet) != len(packet.get("evidence_requirement_types", [])):
        errors.append(f"{packet_id}: ready packet has unsupported evidence requirement")
    if packet.get("jurisdiction_resolved") is not True:
        errors.append(f"{packet_id}: ready packet jurisdiction is unresolved")
    if packet.get("unresolved_evidence_conflict") is not False:
        errors.append(f"{packet_id}: ready packet has unresolved evidence conflict")
    if packet.get("verification_status") != "VERIFIED_COMPLETE":
        errors.append(f"{packet_id}: ready packet verification is incomplete")
    for source in sources:
        errors.extend(_source_metadata_errors(packet_id, source))
    if len(source_ids) != len(sources):
        errors.append(f"{packet_id}: authoritative source IDs are not unique")
    expected_dates = sorted({value for source in sources for value in (source.get("publication_date"), source.get("update_date")) if isinstance(value, str) and value.strip()})
    expected_retrieval = sorted({source.get("retrieval_date") for source in sources if isinstance(source.get("retrieval_date"), str) and source["retrieval_date"].strip()})
    expected_versions = sorted({source.get("guideline_version") for source in sources if isinstance(source.get("guideline_version"), str) and source["guideline_version"].strip()})
    if packet.get("source_dates") != expected_dates or packet.get("retrieval_dates") != expected_retrieval or packet.get("guideline_versions") != expected_versions:
        errors.append(f"{packet_id}: source metadata rollups are incomplete")
    errors.extend(_claim_traceability_errors(packet_id, packet, source_ids))
    covered = {source.get("source_family") for source in sources}
    missing = set(packet.get("source_family_targets", [])) - covered
    by_id = {source.get("source_id"): source for source in sources}
    assessed = {item.get("source_family_target") for item in packet.get("source_family_target_assessments", []) if isinstance(item, dict) and item.get("status") == "CANADIAN_ALTERNATIVE_USED" and isinstance(item.get("source_ids"), list) and item["source_ids"] and set(item["source_ids"]) <= source_ids and all(by_id[source_id].get("is_canadian") is True and by_id[source_id].get("international_fallback") is False for source_id in item["source_ids"]) and isinstance(item.get("rationale"), str) and item["rationale"].strip()}
    if missing != assessed:
        errors.append(f"{packet_id}: canonical source-family target is unsupported")
    fallback_ids = {source.get("source_id") for source in sources if source.get("international_fallback") is True}
    if packet.get("canadian_guidance_not_found") is not False or packet.get("international_fallbacks") not in ([], None) or fallback_ids or any(source.get("is_canadian") is not True for source in sources):
        errors.append(f"{packet_id}: ready packet has undocumented international fallback")
    return errors


def validate_source_packet_research_batch(
    root: Path,
    population: dict[str, Any],
    integrated_populations: list[dict[str, Any]],
    audit: dict[str, Any],
    *,
    audit_base_populations: list[dict[str, Any]] | None = None,
) -> SourcePacketPopulationValidation:
    """Validate one isolated worker population against all other integrated packets."""
    root = Path(root).resolve()
    plan, rebuilt = _canonical_context(root)
    plan_path = _path(root, "research/qgen/source_packet_plan.json")
    errors: list[str] = []
    batch_id = _population_batch_id(population)
    batch = next((item for item in plan.get("research_batches", []) if isinstance(item, dict) and item.get("research_batch_id") == batch_id), None)
    packets = population.get("source_packets", [])
    canonical = {item.get("source_packet_id"): item for item in plan.get("source_packets", []) if isinstance(item, dict)}
    if plan != rebuilt:
        errors.append("canonical source packet plan is not byte-rebuild equivalent")
    if not isinstance(batch, dict):
        errors.append("research batch is invalid")
        expected_ids: list[str] = []
    else:
        expected_ids = list(batch.get("source_packet_ids", []))
    expected_scope = "MCCQE_CURRENT_CANADIAN_SOURCE_PACKET_PILOT" if batch_id == _PILOT_BATCH_ID else "MCCQE_CURRENT_CANADIAN_SOURCE_PACKET_RESEARCH_WAVE"
    if population.get("scope") != expected_scope:
        errors.append("research batch population scope is invalid")
    if population.get("plan_artifact") != "research/qgen/source_packet_plan.json" or population.get("source_packet_plan_sha256") != hashlib.sha256(plan_path.read_bytes()).hexdigest():
        errors.append("research batch is not bound to the canonical source packet plan")
    if not isinstance(packets, list):
        errors.append("research batch source packets must be a list")
        packets = []
    packet_ids = [packet.get("source_packet_id") for packet in packets if isinstance(packet, dict)]
    if packet_ids != expected_ids:
        errors.append("research batch packet IDs do not exactly match canonical batch order")
    integrated_ids = {packet.get("source_packet_id") for packet in _population_packets(integrated_populations)}
    if integrated_ids & set(packet_ids):
        errors.append("research batch attempts to modify previously populated packet")
    for packet in packets:
        if not isinstance(packet, dict):
            errors.append("research batch packet must be an object")
            continue
        packet_id = packet.get("source_packet_id")
        frozen = canonical.get(packet_id)
        if not isinstance(frozen, dict):
            errors.append(f"unknown research batch packet: {packet_id}")
            continue
        for field_name in _PLANNING_FIELDS:
            if packet.get(field_name) != frozen.get(field_name):
                errors.append(f"{packet_id}: canonical planning field changed: {field_name}")
        errors.extend(_batch_packet_semantic_errors(str(packet_id), packet, frozen))
    batch_order = {
        item.get("research_batch_id"): index
        for index, item in enumerate(plan.get("research_batches", []))
        if isinstance(item, dict)
    }
    batch_order[_PILOT_BATCH_ID] = -1
    audit_candidates = (
        integrated_populations
        if audit_base_populations is None
        else audit_base_populations
    )
    prior = [
        item
        for item in audit_candidates
        if batch_order.get(_population_batch_id(item), -1) < batch_order.get(batch_id, -1)
    ]
    expected_audit = build_source_packet_research_wave_audit(root, population, prior)
    if audit != expected_audit:
        errors.append("research batch audit does not match deterministic rebuild")
    return SourcePacketPopulationValidation("FAIL" if errors else "PASS", {"SOURCE_PACKET_VALIDATOR": "FAIL" if errors else "PASS"}, errors)


def build_source_packet_research_progress(
    root: Path, populations: list[dict[str, Any]]
) -> dict[str, Any]:
    """Build the canonical, plan-bound progress counts across populated waves."""
    plan, _ = _canonical_context(Path(root).resolve())
    packets = _population_packets(populations)
    statuses = Counter(packet.get("status") for packet in packets)
    populated_ids = {packet.get("source_packet_id") for packet in packets}
    sources = [
        source
        for packet in packets
        for source in packet.get("authoritative_sources", [])
        if isinstance(source, dict)
    ]
    sources_by_id = {
        source.get("source_id"): source
        for packet in packets
        for source in packet.get("authoritative_sources", [])
        if isinstance(source, dict) and isinstance(source.get("source_id"), str)
    }
    batch_ids = {
        population.get("research_batch_id", population.get("pilot_research_batch_id"))
        for population in populations
    }
    complete_batches = 0
    partial_batches = 0
    for batch in plan.get("research_batches", []):
        ids = set(batch.get("source_packet_ids", []))
        populated = ids & populated_ids
        if populated == ids and batch.get("research_batch_id") in batch_ids:
            complete_batches += 1
        elif populated:
            partial_batches += 1
    blocked = sum(statuses[status] for status in _BLOCKED)
    return {
        "schema_version": "1.0",
        "scope": "SOURCE_PACKET_RESEARCH_PROGRESS_AUDIT",
        "TOTAL_SOURCE_PACKETS": len(plan.get("source_packets", [])),
        "SOURCE_PACKETS_READY": statuses[_READY],
        "SOURCE_PACKETS_PENDING": len(plan.get("source_packets", [])) - len(packets),
        "SOURCE_PACKETS_BLOCKED": blocked,
        "SOURCE_PACKETS_INCOMPLETE": statuses[_INCOMPLETE],
        "RESEARCH_BATCHES_TOTAL": len(plan.get("research_batches", [])),
        "RESEARCH_BATCHES_COMPLETE": complete_batches,
        "RESEARCH_BATCHES_PARTIAL": partial_batches,
        "RESEARCH_BATCHES_PENDING": len(plan.get("research_batches", [])) - complete_batches - partial_batches,
        "AUTHORITATIVE_SOURCE_RECORDS": len(sources),
        "CANADIAN_SOURCE_RECORDS": sum(source.get("is_canadian") is True for source in sources),
        "INTERNATIONAL_FALLBACK_SOURCE_RECORDS": sum(source.get("international_fallback") is True for source in sources),
        "PACKETS_WITH_SOURCE_DISAGREEMENT": sum(packet.get("disagreement_present") is True for packet in packets),
        "PACKETS_WITH_UNRESOLVED_CONFLICT": sum(packet.get("unresolved_evidence_conflict") is True for packet in packets),
        "PREVIOUS_READY_PACKETS_CHANGED": 0,
        "NON_SELECTED_PACKETS_CHANGED": 0,
    }


def build_source_packet_research_wave_audit(
    root: Path, population: dict[str, Any], prior_populations: list[dict[str, Any]]
) -> dict[str, Any]:
    packets = _population_packets([population])
    statuses = Counter(packet.get("status") for packet in packets)
    requirements_total = sum(len(packet.get("evidence_requirement_types", [])) for packet in packets)
    requirements_supported = sum(_supported_requirement_count(packet) for packet in packets)
    progress = build_source_packet_research_progress(root, [*prior_populations, population])
    return {
        "schema_version": "1.0",
        "scope": "SOURCE_PACKET_RESEARCH_WAVE_AUDIT",
        "RESEARCH_BATCH_ID": population.get("research_batch_id"),
        "SELECTED_SOURCE_PACKET_COUNT": len(packets),
        "NEWLY_READY_PACKETS": statuses[_READY],
        "NEWLY_BLOCKED_PACKETS": sum(statuses[status] for status in _BLOCKED),
        "NEWLY_INCOMPLETE_PACKETS": statuses[_INCOMPLETE],
        "NEW_AUTHORITATIVE_SOURCES": sum(len(packet.get("authoritative_sources", [])) for packet in packets),
        "NEW_CANADIAN_AUTHORITATIVE_SOURCES": sum(source.get("is_canadian") is True for packet in packets for source in packet.get("authoritative_sources", []) if isinstance(source, dict)),
        "NEW_INTERNATIONAL_FALLBACK_SOURCES": sum(source.get("international_fallback") is True for packet in packets for source in packet.get("authoritative_sources", []) if isinstance(source, dict)),
        "NEW_PACKETS_WITH_DISAGREEMENT": sum(packet.get("disagreement_present") is True for packet in packets),
        "NEW_PACKETS_WITH_UNRESOLVED_CONFLICT": sum(packet.get("unresolved_evidence_conflict") is True for packet in packets),
        "UNSUPPORTED_READY_PACKET_CLAIMS": sum(1 for packet in packets if packet.get("status") == _READY and _supported_requirement_count(packet) != len(packet.get("evidence_requirement_types", []))),
        "READY_PACKETS_WITH_MISSING_EVIDENCE": sum(1 for packet in packets if packet.get("status") == _READY and not packet.get("supported_recommendations")),
        **progress,
        "scope": "SOURCE_PACKET_RESEARCH_WAVE_AUDIT",
    }


def validate_source_packet_research_wave(
    root: Path, population: dict[str, Any], prior_populations: list[dict[str, Any]], audit: dict[str, Any]
) -> SourcePacketPopulationValidation:
    """Validate a non-pilot population wave without reopening the pilot."""
    root = Path(root).resolve()
    plan, rebuilt = _canonical_context(root)
    plan_path = _path(root, "research/qgen/source_packet_plan.json")
    errors: list[str] = []
    batch_id = population.get("research_batch_id")
    batch = next((item for item in plan.get("research_batches", []) if item.get("research_batch_id") == batch_id), None)
    canonical_packets = {packet.get("source_packet_id"): packet for packet in plan.get("source_packets", [])}
    packets = population.get("source_packets", [])
    prior_ids = {packet.get("source_packet_id") for packet in _population_packets(prior_populations)}
    if plan != rebuilt:
        errors.append("canonical source packet plan is not byte-rebuild equivalent")
    if population.get("scope") != "MCCQE_CURRENT_CANADIAN_SOURCE_PACKET_RESEARCH_WAVE":
        errors.append("research wave population scope is invalid")
    if population.get("plan_artifact") != "research/qgen/source_packet_plan.json" or population.get("source_packet_plan_sha256") != hashlib.sha256(plan_path.read_bytes()).hexdigest():
        errors.append("research wave is not bound to the canonical source packet plan")
    if not isinstance(batch, dict) or batch_id == _PILOT_BATCH_ID:
        errors.append("research wave batch is invalid")
        expected_ids = []
    else:
        expected_ids = list(batch.get("source_packet_ids", []))
    if not isinstance(packets, list):
        errors.append("research wave source packets must be a list")
        packets = []
    packet_ids = [packet.get("source_packet_id") for packet in packets if isinstance(packet, dict)]
    if packet_ids != expected_ids:
        errors.append("research wave packet IDs do not exactly match canonical batch order")
    if prior_ids & set(packet_ids):
        errors.append("research wave attempts to modify previously populated packet")
    for packet in packets:
        if not isinstance(packet, dict):
            errors.append("research wave packet must be an object")
            continue
        packet_id = packet.get("source_packet_id")
        canonical = canonical_packets.get(packet_id)
        if canonical is None:
            errors.append(f"unknown research wave packet: {packet_id}")
            continue
        for field_name in _PLANNING_FIELDS:
            if packet.get(field_name) != canonical.get(field_name):
                errors.append(f"{packet_id}: canonical planning field changed: {field_name}")
        if packet.get("status") != _READY:
            errors.append(f"{packet_id}: selected wave packet is not ready")
            continue
        if packet.get("jurisdiction_resolved") is not True or packet.get("unresolved_evidence_conflict") is not False or packet.get("verification_status") != "VERIFIED_COMPLETE":
            errors.append(f"{packet_id}: ready packet status gate is incomplete")
        sources = packet.get("authoritative_sources", [])
        source_ids = {source.get("source_id") for source in sources if isinstance(source, dict) and isinstance(source.get("source_id"), str)}
        if not sources:
            errors.append(f"{packet_id}: ready packet lacks authoritative source")
        for source in sources:
            errors.extend(_source_metadata_errors(packet_id, source))
        expected_source_dates = sorted({
            value for source in sources if isinstance(source, dict)
            for value in (source.get("publication_date"), source.get("update_date"))
            if isinstance(value, str) and value.strip()
        })
        expected_retrieval_dates = sorted({source.get("retrieval_date") for source in sources if isinstance(source, dict) and isinstance(source.get("retrieval_date"), str) and source["retrieval_date"].strip()})
        expected_versions = sorted({source.get("guideline_version") for source in sources if isinstance(source, dict) and isinstance(source.get("guideline_version"), str) and source["guideline_version"].strip()})
        if (packet.get("source_dates") != expected_source_dates or packet.get("retrieval_dates") != expected_retrieval_dates or packet.get("guideline_versions") != expected_versions):
            errors.append(f"{packet_id}: source metadata rollups are incomplete")
        if _supported_requirement_count(packet) != len(packet.get("evidence_requirement_types", [])):
            errors.append(f"{packet_id}: ready packet has unsupported evidence requirement")
        errors.extend(_claim_traceability_errors(packet_id, packet, source_ids))
        covered_families = {source.get("source_family") for source in sources if isinstance(source, dict)}
        missing = set(packet.get("source_family_targets", [])) - covered_families
        assessments = packet.get("source_family_target_assessments", [])
        sources_by_id = {source.get("source_id"): source for source in sources if isinstance(source, dict)}
        assessed = {
            item.get("source_family_target") for item in assessments
            if isinstance(item, dict) and item.get("status") == "CANADIAN_ALTERNATIVE_USED"
            and isinstance(item.get("source_ids"), list) and item["source_ids"]
            and set(item["source_ids"]) <= source_ids
            and all(sources_by_id[source_id].get("is_canadian") is True and sources_by_id[source_id].get("international_fallback") is False for source_id in item["source_ids"])
            and isinstance(item.get("rationale"), str) and item["rationale"].strip()
        }
        if missing != assessed:
            errors.append(f"{packet_id}: canonical source-family target is unsupported")
        if packet.get("disagreement_present") is not False or packet.get("unresolved_evidence_conflict") is not False or packet.get("disagreements_or_ambiguities") not in ([], None):
            errors.append(f"{packet_id}: selected wave contains an unresolved or undocumented disagreement")
        if (packet.get("canadian_guidance_not_found") is not False or packet.get("international_fallbacks") not in ([], None) or any(source.get("international_fallback") is not False or source.get("is_canadian") is not True for source in sources if isinstance(source, dict))):
            errors.append(f"{packet_id}: selected wave contains an undocumented international fallback")
    expected = build_source_packet_research_wave_audit(root, population, prior_populations)
    if audit != expected:
        errors.append("research wave audit does not match deterministic rebuild")
    return SourcePacketPopulationValidation("FAIL" if errors else "PASS", {"SOURCE_PACKET_VALIDATOR": "FAIL" if errors else "PASS"}, errors)


def validate_source_packet_population(
    root: Path,
    population: dict[str, Any],
    audit: dict[str, Any],
) -> SourcePacketPopulationValidation:
    root = Path(root).resolve()
    errors: list[str] = []
    plan, rebuilt = _canonical_context(root)
    plan_path = _path(root, "research/qgen/source_packet_plan.json")
    pilot_ids = _pilot_packet_ids(plan)
    canonical_packets = {
        packet["source_packet_id"]: packet for packet in plan.get("source_packets", [])
    }
    packets = population.get("source_packets", [])

    if plan != rebuilt:
        errors.append("canonical source packet plan is not byte-rebuild equivalent")
    if population.get("scope") != "MCCQE_CURRENT_CANADIAN_SOURCE_PACKET_PILOT":
        errors.append("pilot population scope is invalid")
    if population.get("plan_artifact") != "research/qgen/source_packet_plan.json":
        errors.append("pilot population is not bound to the canonical plan path")
    plan_sha256 = hashlib.sha256(plan_path.read_bytes()).hexdigest()
    if population.get("source_packet_plan_sha256") != plan_sha256:
        errors.append("pilot population source-plan hash does not match")
    if population.get("pilot_research_batch_id") != _PILOT_BATCH_ID:
        errors.append("pilot population batch is not SRB-089")
    if not isinstance(packets, list):
        errors.append("pilot source packets must be a list")
        packets = []
    packet_ids = [
        packet.get("source_packet_id") for packet in packets
        if isinstance(packet, dict)
    ]
    if packet_ids != pilot_ids:
        errors.append("pilot packet IDs do not exactly match canonical SRB-089 order")

    for packet in packets:
        if not isinstance(packet, dict):
            errors.append("pilot packet must be an object")
            continue
        packet_id = packet.get("source_packet_id")
        canonical = canonical_packets.get(packet_id)
        if canonical is None:
            errors.append(f"unknown pilot packet: {packet_id}")
            continue
        for field_name in _PLANNING_FIELDS:
            if packet.get(field_name) != canonical.get(field_name):
                errors.append(f"{packet_id}: canonical planning field changed: {field_name}")
        if packet.get("status") not in {_READY, _INCOMPLETE, *_BLOCKED}:
            errors.append(f"{packet_id}: population status is invalid")
        disagreements = packet.get("disagreements_or_ambiguities", [])
        packet_source_ids = {
            source.get("source_id")
            for source in packet.get("authoritative_sources", [])
            if isinstance(source, dict) and isinstance(source.get("source_id"), str)
        }
        if packet.get("status") == "BLOCKED_EVIDENCE_CONFLICT":
            if not (
                packet.get("disagreement_present") is True
                and packet.get("unresolved_evidence_conflict") is True
                and isinstance(disagreements, list)
                and disagreements
                and packet.get("verification_status") == "BLOCKED_EVIDENCE_CONFLICT"
            ):
                errors.append(
                    f"{packet_id}: conflict block lacks unresolved disagreement"
                )
        if packet.get("status") == "BLOCKED_JURISDICTION":
            if canonical.get("jurisdiction_resolution_required") is not True:
                errors.append(
                    f"{packet_id}: canonical packet does not require jurisdiction resolution"
                )
            if not (
                packet.get("jurisdiction_resolved") is False
                and packet.get("verification_status") == "BLOCKED_JURISDICTION"
            ):
                errors.append(f"{packet_id}: jurisdiction block state is inconsistent")
        if packet.get("status") == _INCOMPLETE and packet.get(
            "verification_status"
        ) != _INCOMPLETE:
            errors.append(f"{packet_id}: incomplete research state is inconsistent")
        if packet.get("disagreement_present") is True:
            if not isinstance(disagreements, list) or not disagreements:
                errors.append(f"{packet_id}: disagreement details are missing")
            else:
                for disagreement in disagreements:
                    if not isinstance(disagreement, dict):
                        errors.append(f"{packet_id}: disagreement must be an object")
                        continue
                    required_disagreement_text = (
                        "disagreement_id",
                        "summary",
                        "resolution_status",
                        "canadian_mccqe_applicability",
                    )
                    if any(
                        not isinstance(disagreement.get(field_name), str)
                        or not disagreement[field_name].strip()
                        for field_name in required_disagreement_text
                    ):
                        errors.append(f"{packet_id}: disagreement details are incomplete")
                    disagreement_source_ids = disagreement.get("source_ids", [])
                    if (
                        not isinstance(disagreement_source_ids, list)
                        or not disagreement_source_ids
                        or not set(disagreement_source_ids) <= packet_source_ids
                    ):
                        errors.append(
                            f"{packet_id}: disagreement source linkage is invalid"
                        )
                any_unresolved = any(
                    isinstance(disagreement, dict)
                    and disagreement.get("resolution_status") == "UNRESOLVED"
                    for disagreement in disagreements
                )
                if any_unresolved != (
                    packet.get("unresolved_evidence_conflict") is True
                ):
                    errors.append(
                        f"{packet_id}: disagreement resolution state is inconsistent"
                    )
        elif disagreements:
            errors.append(f"{packet_id}: disagreement flag is inconsistent")
        if packet.get("status") == _READY:
            if not packet.get("authoritative_sources"):
                errors.append(f"{packet_id}: ready packet lacks authoritative source")
            if not packet.get("supported_recommendations"):
                errors.append(f"{packet_id}: ready packet lacks supported recommendation")
            if _supported_requirement_count(packet) != len(
                packet.get("evidence_requirement_types", [])
            ):
                errors.append(f"{packet_id}: ready packet has unsupported evidence requirement")
            if packet.get("jurisdiction_resolved") is not True:
                errors.append(f"{packet_id}: ready packet jurisdiction is unresolved")
            if packet.get("unresolved_evidence_conflict") is not False:
                errors.append(f"{packet_id}: ready packet has unresolved evidence conflict")
            if packet.get("verification_status") != "VERIFIED_COMPLETE":
                errors.append(f"{packet_id}: ready packet verification is incomplete")
            source_ids: list[str] = []
            for source in packet.get("authoritative_sources", []):
                errors.extend(_source_metadata_errors(packet_id, source))
                if isinstance(source, dict) and isinstance(source.get("source_id"), str):
                    source_ids.append(source["source_id"])
            if len(source_ids) != len(set(source_ids)):
                errors.append(f"{packet_id}: authoritative source IDs are not unique")
            sources = [
                source for source in packet.get("authoritative_sources", [])
                if isinstance(source, dict)
            ]
            expected_source_dates = sorted({
                value
                for source in sources
                for value in (source.get("publication_date"), source.get("update_date"))
                if isinstance(value, str) and value.strip()
            })
            expected_retrieval_dates = sorted({
                source["retrieval_date"]
                for source in sources
                if isinstance(source.get("retrieval_date"), str)
                and source["retrieval_date"].strip()
            })
            expected_versions = sorted({
                source["guideline_version"]
                for source in sources
                if isinstance(source.get("guideline_version"), str)
                and source["guideline_version"].strip()
            })
            if (
                packet.get("source_dates") != expected_source_dates
                or packet.get("retrieval_dates") != expected_retrieval_dates
                or packet.get("guideline_versions") != expected_versions
            ):
                errors.append(f"{packet_id}: source metadata rollups are incomplete")
            covered_families = {
                source.get("source_family")
                for source in packet.get("authoritative_sources", [])
                if isinstance(source, dict)
            }
            missing_families = set(packet.get("source_family_targets", [])) - covered_families
            fallback_source_ids = {
                source.get("source_id")
                for source in packet.get("authoritative_sources", [])
                if isinstance(source, dict)
                and source.get("international_fallback") is True
            }
            sources_by_id = {
                source.get("source_id"): source
                for source in packet.get("authoritative_sources", [])
                if isinstance(source, dict)
            }
            assessments = packet.get("source_family_target_assessments", [])
            assessed_missing_families: set[str] = set()
            if not isinstance(assessments, list):
                errors.append(f"{packet_id}: source-family assessments must be a list")
                assessments = []
            for assessment in assessments:
                if not isinstance(assessment, dict):
                    errors.append(f"{packet_id}: source-family assessment must be an object")
                    continue
                target = assessment.get("source_family_target")
                status = assessment.get("status")
                linked_ids = assessment.get("source_ids", [])
                rationale = assessment.get("rationale")
                if target not in missing_families or status not in {
                    "CANADIAN_ALTERNATIVE_USED",
                    "INTERNATIONAL_FALLBACK_USED",
                }:
                    errors.append(f"{packet_id}: source-family assessment is invalid")
                    continue
                if (
                    not isinstance(linked_ids, list)
                    or not linked_ids
                    or not set(linked_ids) <= set(sources_by_id)
                    or not isinstance(rationale, str)
                    or not rationale.strip()
                ):
                    errors.append(f"{packet_id}: source-family assessment is incomplete")
                    continue
                linked_sources = [sources_by_id[source_id] for source_id in linked_ids]
                if status == "CANADIAN_ALTERNATIVE_USED" and not all(
                    source.get("is_canadian") is True
                    and source.get("international_fallback") is False
                    for source in linked_sources
                ):
                    errors.append(f"{packet_id}: Canadian alternative linkage is invalid")
                    continue
                if status == "INTERNATIONAL_FALLBACK_USED" and not all(
                    source_id in fallback_source_ids for source_id in linked_ids
                ):
                    errors.append(f"{packet_id}: international target fallback linkage is invalid")
                    continue
                assessed_missing_families.add(target)
            if missing_families != assessed_missing_families:
                errors.append(
                    f"{packet_id}: canonical source-family target is unsupported"
                )
            fallback_records = packet.get("international_fallbacks", [])
            if fallback_source_ids and (
                packet.get("canadian_guidance_not_found") is not True
                or not isinstance(fallback_records, list)
                or not fallback_records
            ):
                errors.append(f"{packet_id}: international fallback is not documented")
            if packet.get("canadian_guidance_not_found") is True and not fallback_source_ids:
                errors.append(f"{packet_id}: Canadian guidance gap has no fallback source")
            if isinstance(fallback_records, list):
                for fallback in fallback_records:
                    if not isinstance(fallback, dict):
                        errors.append(f"{packet_id}: fallback record must be an object")
                        continue
                    if not isinstance(fallback.get("reason"), str) or not fallback[
                        "reason"
                    ].strip():
                        errors.append(f"{packet_id}: fallback reason is missing")
                    recorded_ids = fallback.get("source_ids", [])
                    if not isinstance(recorded_ids, list) or not recorded_ids or not set(
                        recorded_ids
                    ) <= fallback_source_ids:
                        errors.append(f"{packet_id}: fallback source linkage is invalid")
                    uncovered = fallback.get("uncovered_source_family_targets", [])
                    if not isinstance(uncovered, list) or not set(uncovered) <= set(
                        packet.get("source_family_targets", [])
                    ):
                        errors.append(f"{packet_id}: fallback family linkage is invalid")
            errors.extend(
                _claim_traceability_errors(packet_id, packet, set(source_ids))
            )

    expected_audit = build_source_packet_population_audit(root, population)
    if audit != expected_audit:
        errors.append("pilot population audit does not match deterministic rebuild")
    if expected_audit["NON_PILOT_PACKETS_CHANGED"] != 0:
        errors.append("pilot population contains non-pilot packet changes")
    return SourcePacketPopulationValidation(
        "FAIL" if errors else "PASS",
        {"SOURCE_PACKET_VALIDATOR": "FAIL" if errors else "PASS"},
        errors,
    )
