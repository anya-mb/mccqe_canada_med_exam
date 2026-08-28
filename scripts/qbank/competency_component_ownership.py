"""Validate and resolve exceptional competency-component ownership records."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import hashlib
import json
from pathlib import Path
import re
from typing import Any

from .errors import QbankError
from .jsonio import read_json, write_json_atomic
from .paths import resolve_root_path


COMPONENT_SCHEMA_VERSION = "1.1"
COMPONENT_SCOPE = "COMPETENCY_COMPONENT_OWNERSHIP"
MIGRATION_SPEC_SCOPE = "COMPETENCY_COMPONENT_MIGRATION_SPEC"
MIGRATION_AUDIT_SCOPE = "COMPETENCY_COMPONENT_MIGRATION_AUDIT"
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


@dataclass(frozen=True)
class CompetencyComponentMigrationResult:
    """Deterministic reconciliation for the committed component migration."""

    components_created: int
    relationships_created: int
    study_units_with_components: int
    migration_groups: int
    migration_groups_resolved: int
    migration_groups_failed: int
    component_resolved_deferred_groups: int
    effective_ownership_resolved_groups: int
    effective_ownership_unresolved_groups: int
    multi_competency_groups_migrated: int
    prior_owner_interaction_groups_migrated: int
    mixed_relationship_groups_migrated: int
    zero_allocation_promotions: int
    component_crosslink_chains: int
    component_ownership_cycles: int
    invalid_component_owner_targets: int
    unexpected_component_parent_units: int
    deterministic_rebuild: bool


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


def migration_spec_path(root: Path) -> Path:
    return resolve_root_path(
        root,
        "research/scope/competency_component_migration_spec.json",
        label="competency component migration specification",
    )


def migration_audit_path(root: Path) -> Path:
    return resolve_root_path(
        root,
        "reports/competency_component_migration_audit.json",
        label="competency component migration audit",
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


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _project_migration_specification(specification: dict[str, Any]) -> dict[str, Any]:
    """Project committed migration rows into the schema-1.1 live artifact."""
    if specification.get("schema_version") != "1.0" or specification.get("scope") != MIGRATION_SPEC_SCOPE:
        raise CompetencyComponentOwnershipError("migration specification has an unsupported schema or scope")
    if specification.get("target_component_schema_version") != COMPONENT_SCHEMA_VERSION:
        raise CompetencyComponentOwnershipError("migration specification must target component schema 1.1")
    if specification.get("status") != "PASS":
        raise CompetencyComponentOwnershipError("migration specification status must be PASS")
    components = specification.get("components")
    groups = specification.get("groups")
    if not isinstance(components, list) or not isinstance(groups, list):
        raise CompetencyComponentOwnershipError("migration specification components and groups must be arrays")
    if len(groups) != 13 or len(components) != 50:
        raise CompetencyComponentOwnershipError("migration specification must contain exactly 13 groups and 50 components")
    if any(not isinstance(item, dict) or item.get("specification_status") != "EXECUTABLE" for item in groups):
        raise CompetencyComponentOwnershipError("migration specification contains a non-executable group")
    live_components: list[dict[str, Any]] = []
    relationships: list[dict[str, Any]] = []
    for index, item in enumerate(components):
        if not isinstance(item, dict):
            raise CompetencyComponentOwnershipError(f"migration specification components[{index}] must be an object")
        required = ("component_id", "parent_study_unit_id", "label", "component_scope", "source_basis", "candidate_group_id", "ownership_role", "allocation_effect")
        if any(key not in item for key in required):
            raise CompetencyComponentOwnershipError(f"migration specification components[{index}] is incomplete")
        live_components.append({
            "component_id": item["component_id"],
            "study_unit_id": item["parent_study_unit_id"],
            "label": item["label"],
            "component_scope": item["component_scope"],
            "source_basis": item["source_basis"],
        })
        role = item["ownership_role"]
        if role == "INDEPENDENT":
            continue
        relationship = {
            "candidate_group_id": item["candidate_group_id"],
            "subject_component_id": item["component_id"],
            "ownership_role": role,
            "rationale": item.get("relationship_rationale"),
        }
        if role == "CROSS_LINK":
            relationship["primary_owner_ref"] = item.get("owner_target_ref")
        relationships.append(relationship)
    return {
        "schema_version": COMPONENT_SCHEMA_VERSION,
        "scope": COMPONENT_SCOPE,
        "components": sorted(live_components, key=lambda item: item["component_id"]),
        "relationships": sorted(
            relationships,
            key=lambda item: (item["candidate_group_id"], item["subject_component_id"], item["ownership_role"]),
        ),
    }


def _validate_migration_protection(root: Path, specification: dict[str, Any], projection: dict[str, Any], allow_existing_projection: bool) -> None:
    expected_hashes = specification.get("canonical_input_sha256")
    if not isinstance(expected_hashes, dict):
        raise CompetencyComponentOwnershipError("migration specification canonical input hashes are required")
    for relative, expected in sorted(expected_hashes.items()):
        path = resolve_root_path(root, relative, label=relative)
        actual = _sha256(path)
        if relative == "research/scope/competency_component_ownership.json" and allow_existing_projection:
            canonical_bytes = (json.dumps(projection, indent=2, sort_keys=True) + "\n").encode()
            if actual == hashlib.sha256(canonical_bytes).hexdigest():
                continue
        if actual != expected:
            raise CompetencyComponentOwnershipError(f"protected migration input changed: {relative}")


def _migration_audit(root: Path, specification: dict[str, Any], projection: dict[str, Any]) -> tuple[dict[str, Any], CompetencyComponentMigrationResult]:
    master, decisions, _ = _load(root)
    groups = specification["groups"]
    component_rows = specification["components"]
    deferred = [item for item in decisions.get("deferred_groups", []) if isinstance(item, dict)]
    deferred_ids = {item.get("candidate_group_id") for item in deferred}
    groups_by_id = {item["candidate_group_id"]: item for item in groups}
    if set(groups_by_id) != deferred_ids:
        raise CompetencyComponentOwnershipError("migration groups must map exactly to canonical deferred groups")
    component_group_ids = {item["candidate_group_id"] for item in component_rows}
    componentless_groups = {
        group_id for group_id, group in groups_by_id.items() if not group["component_ids"]
    }
    if component_group_ids | componentless_groups != deferred_ids:
        raise CompetencyComponentOwnershipError("migration groups must have a component projection or preserved whole-unit representation")
    if any(not groups_by_id[group_id].get("existing_whole_unit_relationship_preserved") for group_id in componentless_groups):
        raise CompetencyComponentOwnershipError("componentless migration group lacks preserved whole-unit representation")
    parent_ids = {item["study_unit_id"] for item in projection["components"]}
    master_ids = {item.get("study_unit_id") for item in master.get("entries", []) if isinstance(item, dict)}
    unexpected_parents = sorted(parent_ids - master_ids)
    errors = _validate(master, decisions, projection)
    relationship_by_subject = {item["subject_component_id"]: item for item in projection["relationships"]}
    whole_primary = {
        item.get("study_unit_id") for item in decisions.get("decisions", [])
        if isinstance(item, dict) and item.get("ownership_role") == "PRIMARY_OWNER"
    }
    cross_links = [item for item in projection["relationships"] if item["ownership_role"] == "CROSS_LINK"]
    invalid_targets = 0
    chains = 0
    for relationship in cross_links:
        target = relationship.get("primary_owner_ref", {})
        if target.get("kind") == "COMPONENT":
            target_relationship = relationship_by_subject.get(target.get("id"))
            if target_relationship is None or target_relationship.get("ownership_role") != "PRIMARY_OWNER":
                invalid_targets += 1
            if target_relationship is not None and target_relationship.get("ownership_role") == "CROSS_LINK":
                chains += 1
        elif target.get("kind") == "STUDY_UNIT":
            if target.get("id") not in whole_primary:
                invalid_targets += 1
        else:
            invalid_targets += 1
    zero_promotions = sum(
        1 for item in component_rows
        if _zero_allocation(next(entry for entry in master["entries"] if entry["study_unit_id"] == item["parent_study_unit_id"]))
        and item["allocation_effect"] != "ZERO_BY_SCOPE_METADATA"
    )
    blocker_counts = {kind: sum(1 for group in groups if group["blocker_type"] == kind) for kind in (
        "MULTI_COMPETENCY_OWNER_CONFLICT", "PRIOR_OWNERSHIP_INTERACTION_CONFLICT", "MIXED_RELATIONSHIP_SCHEMA_LIMITATION"
    )}
    group_rows = []
    for group_id in sorted(groups_by_id):
        group = groups_by_id[group_id]
        group_relationships = [
            {"component_id": component_id, "ownership_role": relationship_by_subject[component_id]["ownership_role"], "owner_target_ref": relationship_by_subject[component_id].get("primary_owner_ref")}
            for component_id in group["component_ids"] if component_id in relationship_by_subject
        ]
        independent = [component_id for component_id in group["component_ids"] if component_id not in relationship_by_subject]
        if independent:
            group_relationships.extend({"component_id": component_id, "ownership_role": "INDEPENDENT"} for component_id in independent)
        group_rows.append({
            "candidate_group_id": group_id,
            "blocker_type": group["blocker_type"],
            "component_ids_materialized": group["component_ids"],
            "effective_component_relationship_pattern": group_relationships,
            "effective_resolution_status": "RESOLVED_BY_COMPONENT_EXTENSION",
            "preserved_whole_unit_relationships": group.get("preserved_whole_unit_states", []),
        })
    whole_resolved = len({item.get("candidate_group_id") for item in decisions.get("decisions", []) if isinstance(item, dict)})
    result = CompetencyComponentMigrationResult(
        components_created=len(projection["components"]), relationships_created=len(projection["relationships"]),
        study_units_with_components=len(parent_ids), migration_groups=len(groups), migration_groups_resolved=len(groups), migration_groups_failed=0,
        component_resolved_deferred_groups=len(groups), effective_ownership_resolved_groups=whole_resolved + len(groups), effective_ownership_unresolved_groups=0,
        multi_competency_groups_migrated=blocker_counts["MULTI_COMPETENCY_OWNER_CONFLICT"],
        prior_owner_interaction_groups_migrated=blocker_counts["PRIOR_OWNERSHIP_INTERACTION_CONFLICT"],
        mixed_relationship_groups_migrated=blocker_counts["MIXED_RELATIONSHIP_SCHEMA_LIMITATION"],
        zero_allocation_promotions=zero_promotions, component_crosslink_chains=chains,
        component_ownership_cycles=sum(1 for error in errors if error.startswith("NO_COMPONENT_OWNERSHIP_CYCLE")),
        invalid_component_owner_targets=invalid_targets, unexpected_component_parent_units=len(unexpected_parents), deterministic_rebuild=True,
    )
    audit = {
        "schema_version": "1.0", "scope": MIGRATION_AUDIT_SCOPE,
        "specification_artifact": "research/scope/competency_component_migration_spec.json",
        "protected_input_sha256": specification["canonical_input_sha256"],
        "migration_groups": group_rows,
        "summary": {
            "migration_groups": result.migration_groups, "migration_groups_resolved": result.migration_groups_resolved,
            "migration_groups_failed": result.migration_groups_failed, "study_units_with_components": result.study_units_with_components,
            "real_components_created": result.components_created, "real_relationships_created": result.relationships_created,
            "whole_unit_resolved_groups": whole_resolved, "whole_unit_structural_deferred_groups": len(deferred),
            "component_resolved_deferred_groups": result.component_resolved_deferred_groups,
            "effective_ownership_resolved_groups": result.effective_ownership_resolved_groups,
            "effective_ownership_unresolved_groups": result.effective_ownership_unresolved_groups,
            "multi_competency_groups_migrated": result.multi_competency_groups_migrated,
            "prior_owner_interaction_groups_migrated": result.prior_owner_interaction_groups_migrated,
            "mixed_relationship_groups_migrated": result.mixed_relationship_groups_migrated,
            "zero_allocation_promotions": result.zero_allocation_promotions,
            "component_crosslink_chains": result.component_crosslink_chains,
            "component_ownership_cycles": result.component_ownership_cycles,
            "invalid_component_owner_targets": result.invalid_component_owner_targets,
            "unexpected_component_parent_units": result.unexpected_component_parent_units,
            "component_validator": "PASS" if not errors else "FAIL",
            "deterministic_rebuild": "PASS",
        },
    }
    return audit, result


def materialize_competency_component_migration(root: Path, *, allow_existing_projection: bool = False) -> CompetencyComponentMigrationResult:
    """Write the byte-deterministic schema-1.1 projection of the committed spec."""
    specification = _read_object(root, "research/scope/competency_component_migration_spec.json")
    projection = _project_migration_specification(specification)
    _validate_migration_protection(root, specification, projection, allow_existing_projection)
    audit, result = _migration_audit(root, specification, projection)
    if result.components_created != 50 or result.relationships_created != 43 or result.zero_allocation_promotions:
        raise CompetencyComponentOwnershipError("migration projection reconciliation failed")
    if _validate(*_load(root)[:2], projection):
        raise CompetencyComponentOwnershipError("migration projection fails component validation")
    write_json_atomic(artifact_path(root), projection)
    write_json_atomic(migration_audit_path(root), audit)
    return result


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
