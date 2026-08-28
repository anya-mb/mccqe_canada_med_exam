"""Plan pending current-Canadian evidence packets from frozen generation demand."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Any

from .errors import QbankError
from .final_question_allocation import validate_final_question_allocation
from .jsonio import read_json, write_json_atomic
from .paths import resolve_root_path
from .question_generation_manifest import validate_question_generation_manifest


_DISCIPLINES = ("MED", "PED", "OBGYN", "SURG", "PSY", "PHELO")
_PENDING = "PENDING_RESEARCH"
_FRESHNESS = ("HIGH", "MODERATE", "LOW")
_JURISDICTIONS = (
    "CANADA_NATIONAL", "PROVINCIAL_OR_TERRITORIAL", "MIXED",
    "NOT_JURISDICTION_SENSITIVE",
)
_LEGAL_FORMS = {
    "CONFIDENTIALITY_DECISION", "CONSENT_CAPACITY_DECISION", "ETHICAL_LEGAL_ACTION",
    "PROFESSIONAL_RESPONSE", "SYSTEM_ORGANIZATIONAL_DECISION",
}
_FORM_TYPES = {
    "ADVERSE_EFFECT_RECOGNITION": {"MEDICATION"},
    "CLINICAL_MANAGEMENT": {"MANAGEMENT"},
    "COMMUNICATION_RESPONSE": {"COMMUNICATION"},
    "COMPLICATION_RECOGNITION": {"MANAGEMENT"},
    "CONFIDENTIALITY_DECISION": {"LEGAL_ETHICAL"},
    "CONSENT_CAPACITY_DECISION": {"LEGAL_ETHICAL"},
    "DATA_INTERPRETATION": {"INVESTIGATION"},
    "DISPOSITION": {"FOLLOW_UP"},
    "EMERGENCY_STABILIZATION": {"EMERGENCY_STABILIZATION"},
    "ETHICAL_LEGAL_ACTION": {"LEGAL_ETHICAL"},
    "IMAGE_INTERPRETATION": {"INVESTIGATION"},
    "INITIAL_INVESTIGATION": {"INVESTIGATION"},
    "INITIAL_MANAGEMENT": {"MANAGEMENT"},
    "INTERPRET_RESULTS": {"INVESTIGATION"},
    "LABORATORY_INTERPRETATION": {"INVESTIGATION"},
    "MOST_APPROPRIATE_ACTION": {"MANAGEMENT"},
    "MOST_APPROPRIATE_NEXT_STEP": {"MANAGEMENT"},
    "MOST_LIKELY_CAUSE": {"DIAGNOSIS"},
    "MOST_LIKELY_DIAGNOSIS": {"DIAGNOSIS"},
    "NEXT_BEST_STEP": {"MANAGEMENT"},
    "NEXT_STEP": {"MANAGEMENT"},
    "NEXT_STEP_MANAGEMENT": {"MANAGEMENT"},
    "OCCUPATIONAL_HISTORY": {"DIAGNOSIS"},
    "PATTERN_RECOGNITION": {"DIAGNOSIS"},
    "PREVENTION_COUNSELLING": {"PREVENTION"},
    "PROFESSIONAL_RESPONSE": {"LEGAL_ETHICAL", "COMMUNICATION"},
    "SAFETY_COUNSELLING": {"PREVENTION", "COMMUNICATION"},
    "SAFETY_RISK_ACTION": {"PREVENTION"},
    "SYSTEM_ORGANIZATIONAL_DECISION": {"LEGAL_ETHICAL"},
    "URGENT_REFERRAL": {"FOLLOW_UP"},
    "acute presentation": {"EMERGENCY_STABILIZATION"},
    "clinical recognition": {"DIAGNOSIS"},
    "complication recognition": {"MANAGEMENT"},
    "counselling": {"COMMUNICATION"},
    "emergency presentation": {"EMERGENCY_STABILIZATION"},
    "initial investigation": {"INVESTIGATION"},
    "initial management": {"MANAGEMENT"},
    "initial stabilization": {"EMERGENCY_STABILIZATION"},
    "initial_management": {"MANAGEMENT"},
    "investigation_interpretation": {"INVESTIGATION"},
    "next_best_step": {"MANAGEMENT"},
    "risk assessment": {"DIAGNOSIS"},
    "short-answer clinical reasoning": {"DIAGNOSIS"},
    "short-answer differential": {"DIAGNOSIS"},
    "short-answer emergency management": {"EMERGENCY_STABILIZATION"},
}
_FAMILY_BY_DISCIPLINE = {
    "MED": "CANADIAN_SPECIALTY_SOCIETY",
    "PED": "CANADIAN_PAEDIATRIC_SOCIETY",
    "OBGYN": "SOCIETY_OF_OBSTETRICIANS_AND_GYNAECOLOGISTS_OF_CANADA",
    "SURG": "CANADIAN_SURGICAL_OR_SPECIALTY_SOCIETY",
    "PSY": "CANADIAN_PSYCHIATRIC_OR_ADDICTION_GUIDANCE",
    "PHELO": "MCC_HEALTH_CANADA_PHAC_CTFPHC_CMA_CMPA_OR_PROVINCIAL_AUTHORITY",
}
_CANONICAL_VERIFICATION_TYPES = {
    "CLINICAL_GUIDELINE": "MANAGEMENT", "LEGAL_REGULATORY": "LEGAL_ETHICAL",
    "MEDICATION": "MEDICATION", "SCREENING": "SCREENING", "IMMUNIZATION": "IMMUNIZATION",
    "PUBLIC_HEALTH": "PUBLIC_HEALTH",
}


class SourcePacketPlanError(QbankError):
    """Frozen generation demand cannot safely be planned into source packets."""


@dataclass
class SourcePacketPlanValidation:
    status: str
    checks: dict[str, str] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)


def _path(root: Path, relative: str) -> Path:
    return resolve_root_path(root, relative, label=relative)


def _load_inputs(root: Path) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, dict[str, Any]]]:
    manifest = read_json(_path(root, "research/qgen/question_generation_manifest.json"))
    manifest_audit = read_json(_path(root, "reports/question_generation_manifest_audit.json"))
    allocation = read_json(_path(root, "research/scope/final_question_allocation.json"))
    allocation_audit = read_json(_path(root, "reports/final_question_allocation_audit.json"))
    if not isinstance(manifest, dict) or not isinstance(manifest_audit, dict):
        raise SourcePacketPlanError("generation manifest artifacts must be objects")
    if not isinstance(allocation, dict) or not isinstance(allocation_audit, dict):
        raise SourcePacketPlanError("final allocation artifacts must be objects")
    if validate_question_generation_manifest(root, manifest, manifest_audit).status != "PASS":
        raise SourcePacketPlanError("committed generation manifest failed validation")
    if validate_final_question_allocation(root, allocation, allocation_audit).status != "PASS":
        raise SourcePacketPlanError("committed final allocation failed validation")
    rows = [row for row in allocation.get("allocation_addresses", []) if row.get("final_question_count", 0) > 0]
    if len(rows) != 1175:
        raise SourcePacketPlanError("frozen allocation does not contain 1175 positive addresses")
    crosswalk = read_json(_path(root, "research/scope/master_scope_crosswalk.json"))
    if not isinstance(crosswalk, dict) or not isinstance(crosswalk.get("entries"), list):
        raise SourcePacketPlanError("master scope crosswalk is invalid")
    metadata = {
        entry["study_unit_id"]: entry.get("freshness", {})
        for entry in crosswalk["entries"] if isinstance(entry, dict) and isinstance(entry.get("study_unit_id"), str)
    }
    return manifest, rows, metadata


def _requirement_types(forms: list[str]) -> list[str]:
    types = {kind for form in forms for kind in _FORM_TYPES.get(form, set())}
    return sorted(types or {"DIAGNOSIS"})


def _freshness(types: list[str]) -> str:
    if set(types) & {"MEDICATION", "SCREENING", "PREVENTION", "IMMUNIZATION", "LEGAL_ETHICAL", "EMERGENCY_STABILIZATION"}:
        return "HIGH"
    if set(types) & {"MANAGEMENT", "INVESTIGATION", "FOLLOW_UP"}:
        return "MODERATE"
    return "LOW"


def _jurisdiction(forms: list[str], types: list[str]) -> tuple[str, bool]:
    if set(forms) & _LEGAL_FORMS or "LEGAL_ETHICAL" in types:
        return "MIXED", True
    if "PREVENTION" in types:
        return "CANADA_NATIONAL", False
    return "NOT_JURISDICTION_SENSITIVE", False


def _source_families(discipline: str, types: list[str]) -> list[str]:
    families = {_FAMILY_BY_DISCIPLINE[discipline]}
    if set(types) & {"PREVENTION", "IMMUNIZATION"}:
        families.add("HEALTH_CANADA_OR_PUBLIC_HEALTH_AGENCY_OF_CANADA")
    if "LEGAL_ETHICAL" in types:
        families.add("PROVINCIAL_COLLEGE_CMPA_OR_LEGISLATION")
    return sorted(families)


def _key(assignment: dict[str, Any], requirement_type: str, verification_types: set[str]) -> str:
    """Use exact frozen evidence signatures; never infer semantic equivalence."""
    nodes = ",".join(sorted(assignment["source_node_ids"]))
    objectives = ",".join(sorted(assignment["mcc_objective_ids"]))
    verification = ",".join(sorted(verification_types))
    return f"{assignment['discipline']}|{requirement_type}|NODES={nodes}|MCC={objectives}|VERIFY={verification}"


def _requirements(manifest: dict[str, Any], metadata: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for job in manifest["jobs"]:
        for assignment in job["assignments"]:
            freshness_metadata = metadata.get(assignment["study_unit_id"], {})
            verification_types = set(freshness_metadata.get("verification_types", []))
            types = sorted(set(_requirement_types(assignment["preferred_item_forms"])) | {_CANONICAL_VERIFICATION_TYPES[value] for value in verification_types if value in _CANONICAL_VERIFICATION_TYPES})
            jurisdiction, resolution = _jurisdiction(assignment["preferred_item_forms"], types)
            if "JURISDICTION" in verification_types:
                jurisdiction, resolution = "MIXED", True
            for requirement_type in types:
                result.append({
                    "key": _key(assignment, requirement_type, verification_types),
                    "discipline": assignment["discipline"],
                    "requirement_type": requirement_type,
                    "address_id": assignment["allocation_address_id"],
                    "job_id": job["job_id"],
                    "source_node_ids": sorted(assignment["source_node_ids"]),
                    "mcc_objective_ids": sorted(assignment["mcc_objective_ids"]),
                    "source_family_targets": _source_families(assignment["discipline"], [requirement_type]),
                    "freshness": "HIGH" if requirement_type in {"MEDICATION", "SCREENING", "IMMUNIZATION", "LEGAL_ETHICAL", "PUBLIC_HEALTH"} else _freshness([requirement_type]),
                    "jurisdiction": jurisdiction if requirement_type == types[0] else _jurisdiction([], [requirement_type])[0],
                    "jurisdiction_resolution_required": resolution if requirement_type == types[0] else requirement_type == "LEGAL_ETHICAL",
                })
    return result


def _packets(requirements: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, list[str]], dict[str, list[str]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for requirement in requirements:
        grouped[requirement["key"]].append(requirement)
    numbered = {discipline: 0 for discipline in _DISCIPLINES}
    packets: list[dict[str, Any]] = []
    address_map: dict[str, set[str]] = defaultdict(set)
    job_map: dict[str, set[str]] = defaultdict(set)
    for key in sorted(grouped, key=lambda value: (value.split("|", 1)[0], value)):
        group = grouped[key]
        discipline = group[0]["discipline"]
        numbered[discipline] += 1
        packet_id = f"SRC-{discipline}-{numbered[discipline]:03d}"
        addresses = sorted({item["address_id"] for item in group})
        jobs = sorted({item["job_id"] for item in group})
        for address in addresses:
            address_map[address].add(packet_id)
        for job in jobs:
            job_map[job].add(packet_id)
        packets.append({
            "source_packet_id": packet_id,
            "status": _PENDING,
            "discipline": discipline,
            "evidence_requirement_key": key,
            "cross_address_reuse_basis": "EXACT_CANONICAL_SOURCE_NODES_AND_MCC_OBJECTIVES" if len(addresses) > 1 else "",
            "covered_allocation_address_ids": addresses,
            "covered_generation_job_ids": jobs,
            "evidence_requirement_types": [group[0]["requirement_type"]],
            "source_family_targets": group[0]["source_family_targets"],
            "freshness": group[0]["freshness"],
            "jurisdiction": group[0]["jurisdiction"],
            "jurisdiction_resolution_required": group[0]["jurisdiction_resolution_required"],
            "toronto_notes_current_guidance_authority": False,
            "authoritative_sources": [],
            "source_dates": [],
            "retrieval_dates": [],
            "guideline_versions": [],
            "supported_recommendations": [],
            "important_contraindications_or_exceptions": [],
            "disagreements_or_ambiguities": [],
            "source_citations": [],
            "verification_status": "NOT_STARTED",
            "claim_traceability_contract": [
                "CORRECT_ANSWER", "CORRECT_ANSWER_RATIONALE", "MAJOR_MANAGEMENT_OR_DIAGNOSTIC_CLAIM", "GUIDELINE_SENSITIVE_DISTRACTOR_RATIONALE",
            ],
            "knowledge_requirement": "CURRENT_RECOMMENDATION_REQUIRED" if group[0]["freshness"] != "LOW" else "STABLE_BACKGROUND_KNOWLEDGE",
        })
    return packets, {key: sorted(value) for key, value in sorted(address_map.items())}, {key: sorted(value) for key, value in sorted(job_map.items())}


def _batches(packets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str], list[str]] = defaultdict(list)
    for packet in packets:
        groups[(packet["discipline"], packet["jurisdiction"])].append(packet["source_packet_id"])
    batches: list[dict[str, Any]] = []
    for (discipline, jurisdiction), packet_ids in sorted(groups.items()):
        for offset in range(0, len(packet_ids), 10):
            number = len(batches) + 1
            batches.append({
                "research_batch_id": f"SRB-{number:03d}", "discipline": discipline,
                "jurisdiction": jurisdiction, "source_packet_ids": packet_ids[offset:offset + 10],
                "research_status": _PENDING,
            })
    return batches


def _audit(plan: dict[str, Any], expected_addresses: set[str], expected_jobs: set[str]) -> dict[str, Any]:
    packets = plan["source_packets"]
    batches = plan["research_batches"]
    sizes = [len(batch["source_packet_ids"]) for batch in batches]
    shared_jobs = [packet for packet in packets if len(packet["covered_generation_job_ids"]) > 1]
    shared_addresses = [packet for packet in packets if len(packet["covered_allocation_address_ids"]) > 1]
    split_reused = sum(
        len(job_ids) > 1
        for job_ids in plan["allocation_address_generation_job_ids"].values()
    )
    return {
        "schema_version": "1.0", "scope": "SOURCE_PACKET_PLAN_AUDIT",
        "reconciliation": {
            "GENERATION_JOBS_EXPECTED": len(expected_jobs), "GENERATION_JOBS_MAPPED": len(plan["generation_job_source_packet_ids"]),
            "ALLOCATION_ADDRESSES_EXPECTED": len(expected_addresses), "ALLOCATION_ADDRESSES_MAPPED": len(plan["allocation_address_source_packet_ids"]),
            "SOURCE_REQUIREMENT_GAPS": len(expected_jobs - set(plan["generation_job_source_packet_ids"])) + len(expected_addresses - set(plan["allocation_address_source_packet_ids"])),
        },
        "packets": {
            "TOTAL_SOURCE_PACKETS": len(packets),
            "SOURCE_PACKETS_BY_DISCIPLINE": {discipline: sum(packet["discipline"] == discipline for packet in packets) for discipline in _DISCIPLINES},
            "SOURCE_PACKETS_BY_FRESHNESS": dict(sorted(Counter(packet["freshness"] for packet in packets).items())),
            "SOURCE_PACKETS_BY_JURISDICTION": dict(sorted(Counter(packet["jurisdiction"] for packet in packets).items())),
            "PACKETS_WITHOUT_EVIDENCE_REQUIREMENTS": sum(not packet["evidence_requirement_types"] for packet in packets),
            "PACKETS_WITHOUT_FRESHNESS_CLASSIFICATION": sum(packet["freshness"] not in _FRESHNESS for packet in packets),
            "PACKETS_WITHOUT_JURISDICTION_CLASSIFICATION": sum(packet["jurisdiction"] not in _JURISDICTIONS for packet in packets),
            "DUPLICATE_PACKET_IDS": len(packets) - len({packet["source_packet_id"] for packet in packets}),
        },
        "reuse": {
            "SOURCE_PACKETS_REUSED_ACROSS_JOBS": len(shared_jobs), "SOURCE_PACKETS_REUSED_ACROSS_ADDRESSES": len(shared_addresses),
            "JOBS_USING_SHARED_PACKETS": len({job for packet in shared_jobs for job in packet["covered_generation_job_ids"]}),
            "ADDRESSES_USING_MULTIPLE_PACKETS": sum(len(ids) > 1 for ids in plan["allocation_address_source_packet_ids"].values()),
            "SPLIT_ADDRESSES_REUSING_SOURCE_PACKETS": split_reused,
            "PACKETS_WITH_UNSUPPORTED_REUSE": sum(len(packet["covered_allocation_address_ids"]) > 1 and not packet["cross_address_reuse_basis"] for packet in packets),
        },
        "research_batches": {"RESEARCH_BATCH_COUNT": len(batches), "MIN_PACKETS_PER_RESEARCH_BATCH": min(sizes), "MAX_PACKETS_PER_RESEARCH_BATCH": max(sizes), "MEAN_PACKETS_PER_RESEARCH_BATCH": sum(sizes) / len(sizes)},
        "determinism": {"SOURCE_PLAN_REBUILD_DETERMINISTIC": "PASS"},
    }


def build_source_packet_plan(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    root = Path(root).resolve()
    manifest, allocation_rows, metadata = _load_inputs(root)
    requirements = _requirements(manifest, metadata)
    packets, address_map, job_map = _packets(requirements)
    expected_addresses = {row["allocation_address_id"] for row in allocation_rows}
    expected_jobs = {job["job_id"] for job in manifest["jobs"]}
    plan = {
        "schema_version": "1.0", "scope": "MCCQE_CURRENT_CANADIAN_SOURCE_PACKET_PLAN",
        "plan_input": {"generation_manifest_artifact": "research/qgen/question_generation_manifest.json", "final_allocation_artifact": "research/scope/final_question_allocation.json", "TORONTO_NOTES_CURRENT_GUIDANCE_AUTHORITY": False},
        "source_priority_hierarchy": ["CANADIAN_NATIONAL_OR_PROVINCIAL_GUIDELINE_OR_REGULATOR", "CANADIAN_SPECIALTY_SOCIETY", "HEALTH_CANADA_OR_PHAC", "CANADIAN_TASK_FORCE_ON_PREVENTIVE_HEALTH_CARE", "PROVINCIAL_COLLEGE_CMPA_OR_LEGISLATION", "INTERNATIONAL_SPECIALTY_GUIDELINE_IF_CANADIAN_GUIDANCE_UNAVAILABLE", "PEER_REVIEWED_EVIDENCE_IF_GUIDELINE_UNAVAILABLE"],
        "source_packets": packets, "generation_job_source_packet_ids": job_map,
        "allocation_address_source_packet_ids": address_map, "research_batches": _batches(packets),
        "allocation_address_generation_job_ids": {
            address_id: sorted({item["job_id"] for item in requirements if item["address_id"] == address_id})
            for address_id in sorted(expected_addresses)
        },
    }
    audit = _audit(plan, expected_addresses, expected_jobs)
    validation = validate_source_packet_plan(root, plan, audit)
    if validation.status != "PASS":
        raise SourcePacketPlanError("built source packet plan failed validation: " + "; ".join(validation.errors))
    return plan, audit


def validate_source_packet_plan(root: Path, plan: dict[str, Any], audit: dict[str, Any]) -> SourcePacketPlanValidation:
    root = Path(root).resolve()
    errors: list[str] = []
    manifest, allocation_rows, _ = _load_inputs(root)
    packets = plan.get("source_packets", [])
    address_map = plan.get("allocation_address_source_packet_ids", {})
    job_map = plan.get("generation_job_source_packet_ids", {})
    packet_ids = {packet.get("source_packet_id") for packet in packets}
    expected_addresses = {row["allocation_address_id"] for row in allocation_rows}
    expected_jobs = {job["job_id"] for job in manifest["jobs"]}
    if plan.get("scope") != "MCCQE_CURRENT_CANADIAN_SOURCE_PACKET_PLAN": errors.append("source-plan schema is invalid")
    if len(expected_jobs) != 220 or len(expected_addresses) != 1175: errors.append("frozen source-plan demand cardinality changed")
    if set(address_map) != expected_addresses: errors.append("unknown or unmapped allocation address")
    if set(job_map) != expected_jobs: errors.append("unknown or unmapped generation job")
    if any(not ids or not set(ids) <= packet_ids for ids in address_map.values()): errors.append("invalid allocation-address packet mapping")
    if any(not ids or not set(ids) <= packet_ids for ids in job_map.values()): errors.append("invalid generation-job packet mapping")
    if len(packet_ids) != len(packets): errors.append("duplicate packet ids")
    if any(not set(packet.get("covered_allocation_address_ids", [])) <= expected_addresses for packet in packets): errors.append("packet contains unknown allocation address")
    if any(not set(packet.get("covered_generation_job_ids", [])) <= expected_jobs for packet in packets): errors.append("packet contains unknown generation job")
    if any(packet.get("status") != _PENDING for packet in packets): errors.append("packets are not initialized pending research")
    if any(not packet.get("covered_allocation_address_ids") or not packet.get("covered_generation_job_ids") or not packet.get("evidence_requirement_types") for packet in packets): errors.append("packet lacks required coverage or evidence requirement")
    if any(packet.get("freshness") not in _FRESHNESS for packet in packets): errors.append("packet lacks freshness classification")
    if any(packet.get("jurisdiction") not in _JURISDICTIONS for packet in packets): errors.append("packet lacks jurisdiction classification")
    if any(len(packet.get("covered_allocation_address_ids", [])) > 1 and not packet.get("cross_address_reuse_basis") for packet in packets): errors.append("unsupported cross-address packet reuse")
    if any(packet.get("authoritative_sources") != [] or packet.get("supported_recommendations") != [] for packet in packets): errors.append("unverified sources or recommendations were populated")
    if any(packet.get("toronto_notes_current_guidance_authority") is not False for packet in packets): errors.append("Toronto Notes was incorrectly made current guidance authority")
    if audit.get("reconciliation", {}).get("GENERATION_JOBS_MAPPED") != 220 or audit.get("reconciliation", {}).get("ALLOCATION_ADDRESSES_MAPPED") != 1175: errors.append("audit mapping counts are invalid")
    if audit.get("reconciliation", {}).get("SOURCE_REQUIREMENT_GAPS") != 0: errors.append("source requirement gaps remain")
    if audit.get("reuse", {}).get("PACKETS_WITH_UNSUPPORTED_REUSE") != 0: errors.append("audit reports unsupported packet reuse")
    return SourcePacketPlanValidation("FAIL" if errors else "PASS", {"SOURCE_PLAN_VALIDATOR": "FAIL" if errors else "PASS"}, errors)


def write_source_packet_plan(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    root = Path(root).resolve()
    plan, audit = build_source_packet_plan(root)
    repeat_plan, repeat_audit = build_source_packet_plan(root)
    first = json.dumps(plan, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    second = json.dumps(repeat_plan, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    first_audit = json.dumps(audit, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    second_audit = json.dumps(repeat_audit, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if first != second or first_audit != second_audit:
        raise SourcePacketPlanError("source-plan rebuild is not byte-identical")
    write_json_atomic(_path(root, "research/qgen/source_packet_plan.json"), plan)
    write_json_atomic(_path(root, "reports/source_packet_plan_audit.json"), audit)
    return plan, audit
