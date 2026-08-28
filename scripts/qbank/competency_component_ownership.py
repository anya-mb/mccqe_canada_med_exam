"""Validate and resolve exceptional competency-component ownership records."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import re
from typing import Any

from .errors import QbankError
from .jsonio import read_json, write_json_atomic
from .paths import resolve_root_path


COMPONENT_SCHEMA_VERSION = "1.1"
COMPONENT_SCOPE = "COMPETENCY_COMPONENT_OWNERSHIP"
_COMPONENT_ID = re.compile(r"^SU-[A-Z]+-\d{2,3}::C\d{2}$")
_ROLES = frozenset(("PRIMARY_OWNER", "CROSS_LINK", "DISTINCT_CONTEXT"))
_CHECK_NAMES = (
    "COMPONENT_ID_UNIQUE",
    "COMPONENT_PARENT_EXISTS",
    "COMPONENT_ID_MATCHES_PARENT",
    "OWNER_TARGET_EXISTS",
    "NO_COMPONENT_SELF_LINK",
    "NO_COMPONENT_OWNERSHIP_CYCLE",
    "NO_COMPONENT_CROSSLINK_CHAIN",
    "NO_COMPETING_COMPONENT_OWNER",
    "NO_WHOLE_UNIT_COMPONENT_CONTRADICTION",
    "COMPONENT_PROVENANCE_VALID",
    "COMPONENT_MODE_COMPLETE",
    "ZERO_ALLOCATION_NOT_PROMOTED",
    "DETERMINISTIC_COMPONENT_ORDER",
)


class CompetencyComponentOwnershipError(QbankError):
    """The competency-component ownership extension is invalid."""


class AllocationStatus(str, Enum):
    """Question-allocation eligibility after ownership and scope resolution."""

    ELIGIBLE = "ELIGIBLE"
    SUPPRESSED_BY_OWNERSHIP = "SUPPRESSED_BY_OWNERSHIP"
    ZERO_BY_SCOPE_METADATA = "ZERO_BY_SCOPE_METADATA"


@dataclass
class CompetencyComponentValidation:
    status: str
    checks: dict[str, str] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)


def artifact_path(root: Path) -> Path:
    return resolve_root_path(
        root,
        "research/scope/competency_component_ownership.json",
        label="competency component ownership artifact",
    )


def component_id_for(study_unit_id: str, ordinal: int) -> str:
    """Return the canonical deterministic component address for one parent."""
    if not isinstance(study_unit_id, str) or not re.fullmatch(r"SU-[A-Z]+-\d{2,3}", study_unit_id):
        raise CompetencyComponentOwnershipError(f"invalid component parent study_unit_id: {study_unit_id}")
    if not isinstance(ordinal, int) or isinstance(ordinal, bool) or ordinal < 1 or ordinal > 99:
        raise CompetencyComponentOwnershipError("component ordinal must be an integer from 1 through 99")
    return f"{study_unit_id}::C{ordinal:02d}"


def _read_object(root: Path, relative: str) -> dict[str, Any]:
    value = read_json(resolve_root_path(root, relative, label=relative))
    if not isinstance(value, dict):
        raise CompetencyComponentOwnershipError(f"{relative} must be a JSON object")
    return value


def _load(root: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    master = _read_object(root, "research/scope/master_scope_crosswalk.json")
    decisions = _read_object(root, "research/scope/global_ownership_decisions.json")
    path = artifact_path(root)
    if not path.exists():
        extension = empty_component_artifact()
    else:
        extension = _read_object(root, "research/scope/competency_component_ownership.json")
    return master, decisions, extension


def empty_component_artifact() -> dict[str, Any]:
    return {
        "schema_version": COMPONENT_SCHEMA_VERSION,
        "scope": COMPONENT_SCOPE,
        "components": [],
        "relationships": [],
    }


def _text(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _zero_allocation(entry: dict[str, Any]) -> bool:
    if entry.get("classification") in {"REFERENCE_ONLY", "CONTEXT_ONLY"}:
        return True
    planning = entry.get("question_planning")
    return isinstance(planning, dict) and planning.get("minimum_question_coverage") == 0


def _cycle(edges: dict[str, str]) -> list[str]:
    seen: set[str] = set()
    for start in sorted(edges):
        if start in seen:
            continue
        path: list[str] = []
        index: dict[str, int] = {}
        node = start
        while node in edges:
            if node in index:
                return path[index[node] :] + [node]
            if node in seen:
                break
            index[node] = len(path)
            path.append(node)
            node = edges[node]
        seen.update(path)
    return []


def _validate(master: dict[str, Any], decisions: dict[str, Any], extension: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if extension.get("schema_version") != COMPONENT_SCHEMA_VERSION or extension.get("scope") != COMPONENT_SCOPE:
        errors.append("COMPONENT_SCHEMA_VERSION: artifact must use schema 1.1")
    components = extension.get("components")
    relationships = extension.get("relationships")
    if not isinstance(components, list) or not isinstance(relationships, list):
        return [*errors, "COMPONENT_MODE_COMPLETE: components and relationships must be arrays"]
    if components != sorted(components, key=lambda item: item.get("component_id", "") if isinstance(item, dict) else ""):
        errors.append("DETERMINISTIC_COMPONENT_ORDER: components must be ordered by component_id")
    if relationships != sorted(
        relationships,
        key=lambda item: (
            item.get("candidate_group_id", ""), item.get("subject_component_id", ""), item.get("ownership_role", "")
        ) if isinstance(item, dict) else ("", "", ""),
    ):
        errors.append("DETERMINISTIC_COMPONENT_ORDER: relationships must use canonical order")

    entries = master.get("entries")
    if not isinstance(entries, list):
        return [*errors, "COMPONENT_PARENT_EXISTS: master entries are required"]
    parents = {
        entry.get("study_unit_id"): entry
        for entry in entries
        if isinstance(entry, dict) and isinstance(entry.get("study_unit_id"), str)
    }
    deferred = {
        item.get("candidate_group_id")
        for item in decisions.get("deferred_groups", [])
        if isinstance(item, dict) and isinstance(item.get("candidate_group_id"), str)
    }
    whole_primary = {
        item.get("study_unit_id")
        for item in decisions.get("decisions", [])
        if isinstance(item, dict) and item.get("ownership_role") == "PRIMARY_OWNER"
    }
    active_whole = {
        item.get("study_unit_id")
        for item in decisions.get("decisions", [])
        if isinstance(item, dict) and item.get("ownership_role") in {"PRIMARY_OWNER", "CROSS_LINK"}
    }

    component_by_id: dict[str, dict[str, Any]] = {}
    parent_components: dict[str, list[str]] = {}
    for index, component in enumerate(components):
        label = f"components[{index}]"
        if not isinstance(component, dict):
            errors.append(f"COMPONENT_MODE_COMPLETE: {label} must be an object")
            continue
        component_id = component.get("component_id")
        parent_id = component.get("study_unit_id")
        if not isinstance(component_id, str) or component_id in component_by_id:
            errors.append(f"COMPONENT_ID_UNIQUE: {label} has a duplicate or invalid component_id")
            continue
        component_by_id[component_id] = component
        if parent_id not in parents:
            errors.append(f"COMPONENT_PARENT_EXISTS: {label} references unknown parent {parent_id}")
        if not isinstance(component_id, str) or not isinstance(parent_id, str) or not _COMPONENT_ID.fullmatch(component_id) or not component_id.startswith(f"{parent_id}::"):
            errors.append(f"COMPONENT_ID_MATCHES_PARENT: {label} has invalid component identity")
        parent_components.setdefault(str(parent_id), []).append(component_id)
        if not _text(component.get("label")) or not _text(component.get("component_scope")):
            errors.append(f"COMPONENT_MODE_COMPLETE: {label} requires label and component_scope")
        basis = component.get("source_basis")
        if not isinstance(basis, dict) or not _text(basis.get("canonical_decision_ref")):
            errors.append(f"COMPONENT_PROVENANCE_VALID: {label} requires canonical source_basis")
            continue
        decision_ref = basis.get("canonical_decision_ref")
        if decision_ref not in deferred:
            errors.append(f"COMPONENT_PROVENANCE_VALID: {label} references non-deferred decision {decision_ref}")
        node_ids = basis.get("source_node_ids", [])
        keys = basis.get("crosswalk_competency_keys", [])
        if not isinstance(node_ids, list) or not isinstance(keys, list) or not node_ids and not keys:
            errors.append(f"COMPONENT_PROVENANCE_VALID: {label} requires a source-node or competency boundary")
        parent = parents.get(parent_id)
        if parent is not None:
            source_ids = set(parent.get("source_node_ids", []))
            competency_keys = set(parent.get("testable_competencies", {}).keys()) if isinstance(parent.get("testable_competencies"), dict) else set()
            if any(node not in source_ids for node in node_ids) or any(key not in competency_keys for key in keys):
                errors.append(f"COMPONENT_PROVENANCE_VALID: {label} boundary is absent from parent canonical records")

    relationship_by_subject: dict[str, dict[str, Any]] = {}
    primary_components: set[str] = set()
    cross_edges: dict[str, str] = {}
    for index, relationship in enumerate(relationships):
        label = f"relationships[{index}]"
        if not isinstance(relationship, dict):
            errors.append(f"COMPONENT_MODE_COMPLETE: {label} must be an object")
            continue
        subject = relationship.get("subject_component_id")
        role = relationship.get("ownership_role")
        if subject not in component_by_id:
            errors.append(f"COMPONENT_MODE_COMPLETE: {label} references unknown subject {subject}")
            continue
        if subject in relationship_by_subject:
            errors.append(f"NO_COMPETING_COMPONENT_OWNER: {label} duplicates ownership outcome for {subject}")
            continue
        relationship_by_subject[subject] = relationship
        if relationship.get("candidate_group_id") not in deferred:
            errors.append(f"COMPONENT_MODE_COMPLETE: {label} must reference a canonical deferred group")
        if role not in _ROLES or not _text(relationship.get("rationale")):
            errors.append(f"COMPONENT_MODE_COMPLETE: {label} has invalid role or rationale")
        target = relationship.get("primary_owner_ref")
        if role == "PRIMARY_OWNER":
            primary_components.add(subject)
            if target is not None:
                errors.append(f"NO_COMPETING_COMPONENT_OWNER: {label} PRIMARY_OWNER cannot have target")
        elif role == "DISTINCT_CONTEXT":
            if target is not None:
                errors.append(f"NO_COMPETING_COMPONENT_OWNER: {label} DISTINCT_CONTEXT cannot have target")
        elif role == "CROSS_LINK":
            if not isinstance(target, dict) or target.get("kind") not in {"STUDY_UNIT", "COMPONENT"} or not isinstance(target.get("id"), str):
                errors.append(f"OWNER_TARGET_EXISTS: {label} requires typed primary_owner_ref")
                continue
            target_id = target["id"]
            if target_id == subject:
                errors.append(f"NO_COMPONENT_SELF_LINK: {label} cannot target itself")
            if target["kind"] == "STUDY_UNIT":
                if target_id not in parents or target_id not in whole_primary:
                    errors.append(f"OWNER_TARGET_EXISTS: {label} target is not a direct whole-unit PRIMARY_OWNER")
            else:
                if target_id not in component_by_id:
                    errors.append(f"OWNER_TARGET_EXISTS: {label} target component does not exist")
                cross_edges[subject] = target_id
    for subject, target in sorted(cross_edges.items()):
        target_relationship = relationship_by_subject.get(target)
        if target_relationship is not None and target_relationship.get("ownership_role") == "CROSS_LINK":
            errors.append(f"NO_COMPONENT_CROSSLINK_CHAIN: {subject} targets cross-link {target}")
        if target not in primary_components:
            errors.append(f"OWNER_TARGET_EXISTS: {subject} target component is not a direct PRIMARY_OWNER")
    cycle = _cycle(cross_edges)
    if cycle:
        errors.append(f"NO_COMPONENT_OWNERSHIP_CYCLE: {' -> '.join(cycle)}")
    for parent_id in sorted(parent_components):
        if parent_id in active_whole:
            errors.append(f"NO_WHOLE_UNIT_COMPONENT_CONTRADICTION: {parent_id} has active whole-unit ownership")
    return errors


def validate_competency_component_ownership(root: Path) -> CompetencyComponentValidation:
    try:
        master, decisions, extension = _load(root)
    except QbankError as exc:
        return CompetencyComponentValidation("FAIL", {"canonical_inputs": "FAIL"}, [str(exc)])
    errors = _validate(master, decisions, extension)
    checks = {name: "PASS" if not errors else "FAIL" for name in _CHECK_NAMES}
    return CompetencyComponentValidation("FAIL" if errors else "PASS", checks, errors)


def build_competency_component_artifact(root: Path) -> dict[str, Any]:
    """Rewrite the exceptional artifact in canonical deterministic JSON form."""
    master, decisions, extension = _load(root)
    errors = _validate(master, decisions, extension)
    if errors:
        raise CompetencyComponentOwnershipError(f"competency components are invalid: {errors[0]}")
    canonical = {
        "schema_version": COMPONENT_SCHEMA_VERSION,
        "scope": COMPONENT_SCOPE,
        "components": sorted(extension["components"], key=lambda item: item["component_id"]),
        "relationships": sorted(
            extension["relationships"],
            key=lambda item: (item["candidate_group_id"], item["subject_component_id"], item["ownership_role"]),
        ),
    }
    write_json_atomic(artifact_path(root), canonical)
    return canonical


def resolve_allocation_status(
    root: Path, study_unit_id: str, component_id: str | None = None
) -> AllocationStatus:
    """Return the allocation eligibility for a whole-unit or component address."""
    master, decisions, extension = _load(root)
    errors = _validate(master, decisions, extension)
    if errors:
        raise CompetencyComponentOwnershipError(f"competency components are invalid: {errors[0]}")
    entries = {entry["study_unit_id"]: entry for entry in master["entries"] if isinstance(entry, dict) and isinstance(entry.get("study_unit_id"), str)}
    entry = entries.get(study_unit_id)
    if entry is None:
        raise CompetencyComponentOwnershipError(f"unknown study_unit_id: {study_unit_id}")
    components = {item["component_id"]: item for item in extension["components"]}
    parent_components = [item for item in components.values() if item["study_unit_id"] == study_unit_id]
    if parent_components:
        if component_id not in components or components[component_id]["study_unit_id"] != study_unit_id:
            raise CompetencyComponentOwnershipError(f"component mode requires a component of {study_unit_id}")
        role = next((item.get("ownership_role") for item in extension["relationships"] if item.get("subject_component_id") == component_id), None)
    else:
        if component_id is not None:
            raise CompetencyComponentOwnershipError(f"whole-unit mode does not accept component_id for {study_unit_id}")
        role = next((item.get("ownership_role") for item in decisions.get("decisions", []) if item.get("study_unit_id") == study_unit_id), None)
    if _zero_allocation(entry):
        return AllocationStatus.ZERO_BY_SCOPE_METADATA
    return AllocationStatus.SUPPRESSED_BY_OWNERSHIP if role == "CROSS_LINK" else AllocationStatus.ELIGIBLE
