"""Validate exceptional final-bank discipline routing without changing clinical scope."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .competency_component_ownership import AllocationStatus
from .errors import QbankError
from .jsonio import read_json
from .paths import resolve_root_path


_ROUTING_PATH = "research/scope/allocation_discipline_routing.json"
_ALLOWED_DISCIPLINES = frozenset(("MED", "SURG"))
_ALLOWED_CONFIDENCE = frozenset(("HIGH", "MODERATE", "LOW"))
_CHAPTER_DISCIPLINES = {
    "A": "MED", "C": "MED", "CP": "MED", "D": "MED", "E": "MED",
    "ELOM": "PHELO", "ER": "MED", "FM": "MED", "G": "MED", "GM": "MED",
    "GS": "SURG", "GY": "OBGYN", "H": "MED", "ID": "MED", "MG": "MED",
    "N": "MED", "NP": "MED", "NS": "SURG", "OB": "OBGYN", "OP": "SURG",
    "OR": "SURG", "OT": "SURG", "P": "PED", "PH": "PHELO", "PL": "SURG",
    "MCC": "MED", "PM": "MED", "PS": "PSY", "R": "MED", "RH": "MED", "U": "SURG", "VS": "SURG",
}


class AllocationDisciplineRoutingError(QbankError):
    """Exceptional allocation-discipline routing is malformed or inconsistent."""


@dataclass
class AllocationDisciplineRoutingValidation:
    status: str
    checks: dict[str, str] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    summary: dict[str, int] = field(default_factory=dict)


@dataclass(frozen=True)
class AllocationDisciplinePreflight:
    total_allocation_addresses: int
    eligible_allocation_addresses: int
    suppressed_allocation_addresses: int
    zero_scope_allocation_addresses: int
    medical_imaging_ambiguous_addresses: int
    unassigned_eligible_addresses: int
    multi_assigned_eligible_addresses: int


def routing_artifact_path(root: Path) -> Path:
    return resolve_root_path(root, _ROUTING_PATH, label="allocation discipline routing artifact")


def load_allocation_discipline_routing(root: Path) -> dict[str, Any]:
    value = read_json(routing_artifact_path(root))
    if not isinstance(value, dict):
        raise AllocationDisciplineRoutingError("allocation discipline routing must be a JSON object")
    return value


def _canonical_inputs(root: Path) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any]]:
    master = read_json(resolve_root_path(root, "research/scope/master_scope_crosswalk.json", label="master scope"))
    decisions = read_json(resolve_root_path(root, "research/scope/global_ownership_decisions.json", label="ownership decisions"))
    components = read_json(resolve_root_path(root, "research/scope/competency_component_ownership.json", label="component ownership"))
    if not isinstance(master, dict) or not isinstance(decisions, dict) or not isinstance(components, dict):
        raise AllocationDisciplineRoutingError("canonical allocation inputs must be JSON objects")
    entries = master.get("entries")
    if not isinstance(entries, list) or not all(isinstance(entry, dict) for entry in entries):
        raise AllocationDisciplineRoutingError("master scope entries must be objects")
    return entries, decisions, components


def _zero_by_scope(entry: dict[str, Any]) -> bool:
    planning = entry.get("question_planning")
    return (
        entry.get("classification") in {"REFERENCE_ONLY", "CONTEXT_ONLY"}
        or entry.get("scope_depth") == "CONTEXT_ONLY"
        or isinstance(planning, dict) and planning.get("minimum_question_coverage") == 0
    )


def _addresses(root: Path) -> list[tuple[str, dict[str, Any], AllocationStatus]]:
    entries, decisions, extension = _canonical_inputs(root)
    components = extension.get("components")
    relationships = extension.get("relationships")
    if not isinstance(components, list) or not isinstance(relationships, list):
        raise AllocationDisciplineRoutingError("component ownership arrays are required")
    component_parents = {item.get("study_unit_id") for item in components if isinstance(item, dict)}
    component_roles = {
        item.get("subject_component_id"): item.get("ownership_role")
        for item in relationships if isinstance(item, dict)
    }
    whole_roles = {
        item.get("study_unit_id"): item.get("ownership_role")
        for item in decisions.get("decisions", []) if isinstance(item, dict)
    }
    rows: list[tuple[str, dict[str, Any], AllocationStatus]] = []
    for entry in entries:
        study_unit_id = entry.get("study_unit_id")
        if not isinstance(study_unit_id, str):
            raise AllocationDisciplineRoutingError("master scope entry has no study_unit_id")
        address_ids = [
            item.get("component_id") for item in components
            if isinstance(item, dict) and item.get("study_unit_id") == study_unit_id
        ] if study_unit_id in component_parents else [study_unit_id]
        for address_id in address_ids:
            if not isinstance(address_id, str):
                raise AllocationDisciplineRoutingError("component has no component_id")
            role = component_roles.get(address_id) if study_unit_id in component_parents else whole_roles.get(study_unit_id)
            status = AllocationStatus.ZERO_BY_SCOPE_METADATA if _zero_by_scope(entry) else (
                AllocationStatus.SUPPRESSED_BY_OWNERSHIP if role == "CROSS_LINK" else AllocationStatus.ELIGIBLE
            )
            rows.append((address_id, entry, status))
    return rows


def _candidate_ids(root: Path) -> set[str]:
    return {
        address_id for address_id, entry, status in _addresses(root)
        if entry.get("chapter_code") == "MI" and status is AllocationStatus.ELIGIBLE
    }


def validate_allocation_discipline_routing(
    root: Path, routing: dict[str, Any] | None = None
) -> AllocationDisciplineRoutingValidation:
    errors: list[str] = []
    try:
        artifact = load_allocation_discipline_routing(root) if routing is None else routing
        candidates = _candidate_ids(root)
    except (OSError, QbankError, TypeError) as exc:
        return AllocationDisciplineRoutingValidation("FAIL", {"canonical_inputs": "FAIL"}, [str(exc)])
    rows = artifact.get("routing_overrides") if isinstance(artifact, dict) else None
    if artifact.get("schema_version") != "1.0" or artifact.get("scope") != "EXCEPTIONAL_ALLOCATION_DISCIPLINE_ROUTING":
        errors.append("routing artifact has an unsupported schema or scope")
    if not isinstance(rows, list):
        errors.append("routing_overrides must be an array")
        rows = []
    ids: list[str] = []
    disciplines: Counter[str] = Counter()
    confidences: Counter[str] = Counter()
    for index, row in enumerate(rows):
        label = f"routing_overrides[{index}]"
        if not isinstance(row, dict):
            errors.append(f"{label} must be an object")
            continue
        address_id = row.get("allocation_address_id")
        discipline = row.get("canonical_allocation_discipline")
        confidence = row.get("confidence")
        if not isinstance(address_id, str):
            errors.append(f"{label} requires allocation_address_id")
            continue
        ids.append(address_id)
        if discipline not in _ALLOWED_DISCIPLINES:
            errors.append(f"{label} has invalid canonical_allocation_discipline")
        else:
            disciplines[discipline] += 1
        if confidence not in _ALLOWED_CONFIDENCE or confidence == "LOW":
            errors.append(f"{label} must use HIGH or MODERATE confidence for a final route")
        else:
            confidences[confidence] += 1
        if not isinstance(row.get("routing_basis"), str) or not row["routing_basis"].strip():
            errors.append(f"{label} requires routing_basis")
        if not isinstance(row.get("rationale"), str) or not row["rationale"].strip():
            errors.append(f"{label} requires rationale")
    if len(ids) != len(set(ids)):
        errors.append("routing_overrides contains duplicate allocation_address_id values")
    if set(ids) != candidates:
        errors.append("routing_overrides must contain exactly the eligible Medical Imaging ambiguous addresses")
    checks = {
        "ROUTING_CANDIDATES": "PASS" if len(candidates) == 26 else "FAIL",
        "EXACT_ELIGIBLE_MI_ADDRESSES": "PASS" if set(ids) == candidates else "FAIL",
        "UNIQUE_ADDRESS_IDS": "PASS" if len(ids) == len(set(ids)) else "FAIL",
        "FINAL_DISCIPLINES_VALID": "PASS" if not any("canonical_allocation_discipline" in error for error in errors) else "FAIL",
        "CONFIDENCE_VALID": "PASS" if not any("confidence" in error for error in errors) else "FAIL",
    }
    return AllocationDisciplineRoutingValidation(
        "FAIL" if errors else "PASS", checks, errors,
        {
            "routing_candidates": len(candidates),
            "routed_med": disciplines["MED"],
            "routed_surg": disciplines["SURG"],
            "deferred_routing": 0,
            "high_confidence": confidences["HIGH"],
            "moderate_confidence": confidences["MODERATE"],
            "low_confidence": 0,
        },
    )


def preflight_allocation_disciplines(
    root: Path, routing: dict[str, Any] | None = None
) -> AllocationDisciplinePreflight:
    artifact = load_allocation_discipline_routing(root) if routing is None else routing
    routes = {
        row["allocation_address_id"]: row["canonical_allocation_discipline"]
        for row in artifact.get("routing_overrides", []) if isinstance(row, dict)
        and isinstance(row.get("allocation_address_id"), str)
        and row.get("canonical_allocation_discipline") in _ALLOWED_DISCIPLINES
    }
    rows = _addresses(root)
    counts = Counter(status for _, _, status in rows)
    unassigned = 0
    multi = 0
    ambiguous = 0
    for address_id, entry, status in rows:
        if status is not AllocationStatus.ELIGIBLE:
            continue
        chapter = entry.get("chapter_code")
        if chapter == "MI":
            ambiguous += 1
            disciplines = (routes[address_id],) if address_id in routes else ("MED", "SURG")
        else:
            discipline = _CHAPTER_DISCIPLINES.get(chapter)
            disciplines = () if discipline is None else (discipline,)
        if not disciplines:
            unassigned += 1
        elif len(disciplines) > 1:
            multi += 1
    return AllocationDisciplinePreflight(
        total_allocation_addresses=len(rows),
        eligible_allocation_addresses=counts[AllocationStatus.ELIGIBLE],
        suppressed_allocation_addresses=counts[AllocationStatus.SUPPRESSED_BY_OWNERSHIP],
        zero_scope_allocation_addresses=counts[AllocationStatus.ZERO_BY_SCOPE_METADATA],
        medical_imaging_ambiguous_addresses=ambiguous,
        unassigned_eligible_addresses=unassigned,
        multi_assigned_eligible_addresses=multi,
    )
