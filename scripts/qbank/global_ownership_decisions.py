"""Validate incremental global ownership decisions without changing clinical scope."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
import re
from typing import Any

from .errors import QbankError
from .jsonio import read_json, write_json_atomic
from .paths import resolve_root_path


_ALLOWED_ROLES = ("PRIMARY_OWNER", "CROSS_LINK", "DISTINCT_CONTEXT")
_CONFIDENCE = ("HIGH", "MODERATE", "LOW")
_BATCH_ID = re.compile(r"PRIORITY_([ABC])-B(\d+)$")


class GlobalOwnershipDecisionError(QbankError):
    """The incremental ownership layer is malformed or inconsistent."""


@dataclass
class GlobalOwnershipDecisionValidation:
    status: str
    checks: dict[str, str] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)


def _read_object(root: Path, relative: str) -> dict[str, Any]:
    value = read_json(resolve_root_path(root, relative, label=relative))
    if not isinstance(value, dict):
        raise GlobalOwnershipDecisionError(f"{relative} must be a JSON object")
    return value


def _inputs(root: Path) -> dict[str, dict[str, Any]]:
    return {
        "master": _read_object(root, "research/scope/master_scope_crosswalk.json"),
        "batches": _read_object(root, "research/scope/global_ownership_batches.json"),
        "triage": _read_object(root, "research/scope/global_ownership_triage.json"),
        "decisions": _read_object(root, "research/scope/global_ownership_decisions.json"),
    }


def audit_path(root: Path, batch_id: str) -> Path:
    match = _BATCH_ID.fullmatch(batch_id)
    if not match:
        raise GlobalOwnershipDecisionError(f"invalid ownership batch_id: {batch_id}")
    priority, number = match.groups()
    filename = (
        f"global_ownership_priority_{priority.lower()}_batch_{int(number)}_audit.json"
    )
    return resolve_root_path(root, Path("reports") / filename, label="ownership audit")


def _nonempty_text(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _cycle_nodes(edges: dict[str, str]) -> list[str]:
    """Return one deterministic ownership cycle, if present."""
    visited: set[str] = set()
    for start in sorted(edges):
        if start in visited:
            continue
        path: list[str] = []
        positions: dict[str, int] = {}
        node = start
        while node in edges:
            if node in positions:
                return path[positions[node] :] + [node]
            if node in visited:
                break
            positions[node] = len(path)
            path.append(node)
            node = edges[node]
        visited.update(path)
    return []


def _validate_core(documents: dict[str, dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    master = documents["master"]
    batch_doc = documents["batches"]
    triage = documents["triage"]
    artifact = documents["decisions"]

    entries = master.get("entries")
    batches = batch_doc.get("batches")
    groups = triage.get("groups")
    decisions = artifact.get("decisions")
    deferred = artifact.get("deferred_groups")
    adjudicated_batches = artifact.get("adjudicated_batches")
    if not isinstance(entries, list) or not isinstance(batches, list) or not isinstance(groups, list):
        return ["canonical master, batch, and triage arrays are required"]
    if not isinstance(decisions, list) or not isinstance(deferred, list):
        return ["ownership decisions and deferred_groups must be arrays"]
    if not isinstance(adjudicated_batches, list) or not all(
        isinstance(value, str) for value in adjudicated_batches
    ):
        return ["adjudicated_batches must be an array of batch IDs"]
    if len(adjudicated_batches) != len(set(adjudicated_batches)):
        errors.append("adjudicated_batches contains duplicates")
    if artifact.get("schema_version") != "1.0" or artifact.get("scope") != "GLOBAL_OWNERSHIP_DECISIONS":
        errors.append("ownership decision artifact has an unsupported schema or scope")

    master_ids = {
        entry.get("study_unit_id")
        for entry in entries
        if isinstance(entry, dict) and isinstance(entry.get("study_unit_id"), str)
    }
    if len(master_ids) != len(entries) or master.get("total_study_units") != len(master_ids):
        errors.append("master study_unit_ids must be unique and reconciled")

    batch_by_id = {
        batch.get("batch_id"): batch
        for batch in batches
        if isinstance(batch, dict) and isinstance(batch.get("batch_id"), str)
    }
    if len(batch_by_id) != len(batches):
        errors.append("canonical ownership batches must have unique batch IDs")
    unknown_batches = sorted(set(adjudicated_batches) - set(batch_by_id))
    if unknown_batches:
        errors.append(f"adjudicated_batches references unknown batch IDs: {unknown_batches}")

    triage_by_id = {
        group.get("group_id"): group
        for group in groups
        if isinstance(group, dict) and isinstance(group.get("group_id"), str)
    }
    if len(triage_by_id) != len(groups):
        errors.append("canonical ownership triage groups must have unique group IDs")
    group_to_batch: dict[str, str] = {}
    for batch_id, batch in batch_by_id.items():
        group_ids = batch.get("group_ids")
        if not isinstance(group_ids, list) or not all(isinstance(value, str) for value in group_ids):
            errors.append(f"{batch_id}: group_ids must be an array of strings")
            continue
        for group_id in group_ids:
            if group_id in group_to_batch:
                errors.append(f"{group_id}: appears in multiple ownership batches")
            group_to_batch[group_id] = batch_id
            if group_id not in triage_by_id:
                errors.append(f"{batch_id}: references unknown triage group {group_id}")

    assignments_by_group: dict[str, list[dict[str, Any]]] = defaultdict(list)
    roles_by_unit: dict[str, set[str]] = defaultdict(set)
    targets_by_unit: dict[str, set[str]] = defaultdict(set)
    seen_group_units: set[tuple[str, str]] = set()
    cross_links: dict[str, str] = {}
    for index, decision in enumerate(decisions):
        label = f"decisions[{index}]"
        if not isinstance(decision, dict):
            errors.append(f"{label}: must be an object")
            continue
        group_id = decision.get("candidate_group_id")
        unit_id = decision.get("study_unit_id")
        role = decision.get("ownership_role")
        batch_id = decision.get("adjudication_batch")
        confidence = decision.get("confidence")
        group = triage_by_id.get(group_id)
        if group is None:
            errors.append(f"{label}: references unknown candidate_group_id {group_id}")
            continue
        expected_batch = group_to_batch.get(group_id)
        if batch_id != expected_batch:
            errors.append(f"{label}: adjudication_batch does not match canonical batch")
        if batch_id not in adjudicated_batches:
            errors.append(f"{label}: records a decision for an unreviewed batch")
        if decision.get("candidate_type") != group.get("candidate_type"):
            errors.append(f"{label}: candidate_type does not match canonical triage")
        if unit_id not in master_ids:
            errors.append(f"{label}: unknown study_unit_id {unit_id}")
        group_unit_ids = group.get("study_unit_ids", [])
        is_targeted_external_owner = (
            unit_id not in group_unit_ids
            and len(group_unit_ids) == 1
            and role == "PRIMARY_OWNER"
        )
        if unit_id not in group_unit_ids and not is_targeted_external_owner:
            errors.append(f"{label}: study_unit_id is not a member of {group_id}")
        if role not in _ALLOWED_ROLES:
            errors.append(f"{label}: disallowed ownership_role {role}")
        if decision.get("decision_status") != "RESOLVED":
            errors.append(f"{label}: decision_status must be RESOLVED")
        if confidence not in _CONFIDENCE or confidence == "LOW":
            errors.append(f"{label}: resolved decisions require HIGH or MODERATE confidence")
        if not _nonempty_text(decision.get("rationale")):
            errors.append(f"{label}: concise rationale is required")
        key = (str(group_id), str(unit_id))
        if key in seen_group_units:
            errors.append(f"{label}: duplicate decision for {group_id}/{unit_id}")
        seen_group_units.add(key)
        assignments_by_group[str(group_id)].append(decision)
        if isinstance(unit_id, str) and role in _ALLOWED_ROLES:
            roles_by_unit[unit_id].add(role)
        owner = decision.get("primary_owner_study_unit_id")
        if role == "CROSS_LINK":
            if not isinstance(owner, str):
                errors.append(f"{label}: CROSS_LINK requires primary_owner_study_unit_id")
            else:
                if owner == unit_id:
                    errors.append(f"{label}: ownership self-link is not allowed")
                if isinstance(unit_id, str):
                    targets_by_unit[unit_id].add(owner)
                    cross_links[unit_id] = owner
        elif owner is not None:
            errors.append(f"{label}: only CROSS_LINK may set primary_owner_study_unit_id")

    deferred_by_group: dict[str, dict[str, Any]] = {}
    for index, item in enumerate(deferred):
        label = f"deferred_groups[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{label}: must be an object")
            continue
        group_id = item.get("candidate_group_id")
        group = triage_by_id.get(group_id)
        if group is None:
            errors.append(f"{label}: references unknown candidate_group_id {group_id}")
            continue
        if group_id in deferred_by_group:
            errors.append(f"{label}: duplicate deferred group {group_id}")
        deferred_by_group[str(group_id)] = item
        batch_id = item.get("adjudication_batch")
        if batch_id != group_to_batch.get(group_id):
            errors.append(f"{label}: adjudication_batch does not match canonical batch")
        if batch_id not in adjudicated_batches:
            errors.append(f"{label}: records a deferral for an unreviewed batch")
        if item.get("candidate_type") != group.get("candidate_type"):
            errors.append(f"{label}: candidate_type does not match canonical triage")
        if item.get("study_unit_ids") != group.get("study_unit_ids"):
            errors.append(f"{label}: study_unit_ids do not match canonical triage")
        if item.get("decision_status") != "DEFERRED_COMPLEX_OWNERSHIP":
            errors.append(f"{label}: invalid deferred decision_status")
        if item.get("confidence") != "LOW":
            errors.append(f"{label}: deferred ownership requires LOW confidence")
        if not _nonempty_text(item.get("rationale")):
            errors.append(f"{label}: concise rationale is required")

    expected_reviewed_groups = {
        group_id
        for batch_id in adjudicated_batches
        for group_id in batch_by_id.get(batch_id, {}).get("group_ids", [])
    }
    resolved_groups = set(assignments_by_group)
    deferred_groups = set(deferred_by_group)
    if resolved_groups & deferred_groups:
        errors.append("a candidate group cannot be both resolved and deferred")
    if resolved_groups | deferred_groups != expected_reviewed_groups:
        errors.append("reviewed and deferred group counts do not reconcile with adjudicated batches")

    for group_id in sorted(resolved_groups):
        group = triage_by_id.get(group_id, {})
        assignments = assignments_by_group[group_id]
        expected_ids = set(group.get("study_unit_ids", []))
        actual_ids = {item.get("study_unit_id") for item in assignments}
        external_ids = actual_ids - expected_ids
        if (
            not expected_ids.issubset(actual_ids)
            or len(assignments) != len(actual_ids)
            or len(external_ids) > 1
            or (external_ids and len(expected_ids) != 1)
        ):
            errors.append(f"{group_id}: resolved assignments do not reconcile to group members")
        confidences = {item.get("confidence") for item in assignments}
        if len(confidences) != 1:
            errors.append(f"{group_id}: decision confidence must be consistent within the group")
        roles = [item.get("ownership_role") for item in assignments]
        if "DISTINCT_CONTEXT" in roles:
            if set(roles) != {"DISTINCT_CONTEXT"}:
                errors.append(f"{group_id}: DISTINCT_CONTEXT cannot suppress or mix with shared ownership")
        elif roles.count("PRIMARY_OWNER") != 1 or roles.count("CROSS_LINK") != len(roles) - 1:
            errors.append(f"{group_id}: shared ownership requires one PRIMARY_OWNER and direct CROSS_LINKs")
        else:
            group_primary = next(
                item["study_unit_id"]
                for item in assignments
                if item["ownership_role"] == "PRIMARY_OWNER"
            )
            if any(
                item.get("primary_owner_study_unit_id") != group_primary
                for item in assignments
                if item["ownership_role"] == "CROSS_LINK"
            ):
                errors.append(
                    f"{group_id}: every CROSS_LINK must reference the group PRIMARY_OWNER"
                )

    for unit_id, roles in sorted(roles_by_unit.items()):
        if {"PRIMARY_OWNER", "CROSS_LINK"}.issubset(roles):
            errors.append(f"{unit_id}: contradictory ownership roles {sorted(roles)}")
    for unit_id, targets in sorted(targets_by_unit.items()):
        if len(targets) > 1:
            errors.append(f"{unit_id}: contradictory primary owners {sorted(targets)}")
    primary_ids = {
        unit_id
        for unit_id, roles in roles_by_unit.items()
        if "PRIMARY_OWNER" in roles and "CROSS_LINK" not in roles
    }
    for unit_id, owner in sorted(cross_links.items()):
        if owner not in primary_ids:
            errors.append(f"{unit_id}: CROSS_LINK does not reference a PRIMARY_OWNER ({owner})")
    cycle = _cycle_nodes(cross_links)
    if cycle:
        errors.append(f"ownership cycle detected: {' -> '.join(cycle)}")
    return errors


def _audit_document(
    documents: dict[str, dict[str, Any]], batch_id: str
) -> dict[str, Any]:
    artifact = documents["decisions"]
    batches = documents["batches"].get("batches", [])
    triage = documents["triage"].get("groups", [])
    batch = next((item for item in batches if item.get("batch_id") == batch_id), None)
    if batch is None:
        raise GlobalOwnershipDecisionError(f"unknown ownership batch: {batch_id}")
    if batch_id not in artifact.get("adjudicated_batches", []):
        raise GlobalOwnershipDecisionError(f"cannot build audit for unreviewed batch: {batch_id}")
    triage_by_id = {item["group_id"]: item for item in triage}
    decisions_by_group: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for decision in artifact.get("decisions", []):
        if decision.get("adjudication_batch") == batch_id:
            decisions_by_group[decision["candidate_group_id"]].append(decision)
    deferred_by_group = {
        item["candidate_group_id"]: item
        for item in artifact.get("deferred_groups", [])
        if item.get("adjudication_batch") == batch_id
    }
    audit_groups = []
    assignment_counts: Counter[str] = Counter()
    confidence_counts: Counter[str] = Counter()
    resolved = 0
    for group_id in batch.get("group_ids", []):
        packet = triage_by_id[group_id]
        assignments = sorted(
            decisions_by_group.get(group_id, []), key=lambda item: item["study_unit_id"]
        )
        if assignments:
            resolved += 1
            confidence = assignments[0]["confidence"]
            confidence_counts[confidence] += 1
            assignment_counts.update(item["ownership_role"] for item in assignments)
            primary = next(
                (
                    item["study_unit_id"]
                    for item in assignments
                    if item["ownership_role"] == "PRIMARY_OWNER"
                ),
                None,
            )
            audit_groups.append(
                {
                    "candidate_group_id": group_id,
                    "candidate_type": packet["candidate_type"],
                    "study_unit_ids": packet["study_unit_ids"],
                    "final_ownership_roles": [
                        {
                            key: item[key]
                            for key in (
                                "study_unit_id",
                                "ownership_role",
                                "primary_owner_study_unit_id",
                            )
                            if key in item
                        }
                        for item in assignments
                    ],
                    "primary_owner_study_unit_id": primary,
                    "confidence": confidence,
                    "rationale": next(
                        item["rationale"]
                        for item in assignments
                        if item["ownership_role"] != "CROSS_LINK"
                    ),
                    "decision_status": "RESOLVED",
                }
            )
        else:
            item = deferred_by_group[group_id]
            confidence_counts[item["confidence"]] += 1
            audit_groups.append(
                {
                    "candidate_group_id": group_id,
                    "candidate_type": packet["candidate_type"],
                    "study_unit_ids": packet["study_unit_ids"],
                    "final_ownership_roles": [],
                    "primary_owner_study_unit_id": None,
                    "confidence": item["confidence"],
                    "rationale": item["rationale"],
                    "decision_status": "DEFERRED_COMPLEX_OWNERSHIP",
                }
            )
    reviewed = len(audit_groups)
    return {
        "schema_version": "1.0",
        "scope": "GLOBAL_OWNERSHIP_BATCH_AUDIT",
        "priority": batch["priority"],
        "batch_id": batch_id,
        "groups_reviewed": reviewed,
        "groups_resolved": resolved,
        "groups_deferred": reviewed - resolved,
        "assignment_counts": {
            role: assignment_counts[role] for role in _ALLOWED_ROLES
        },
        "confidence_counts": {
            confidence: confidence_counts[confidence] for confidence in _CONFIDENCE
        },
        "groups": audit_groups,
    }


def build_global_ownership_batch_audit(root: Path, batch_id: str) -> dict[str, Any]:
    documents = _inputs(root)
    errors = _validate_core(documents)
    if errors:
        raise GlobalOwnershipDecisionError(
            f"ownership decisions are invalid: {errors[0]}"
        )
    audit = _audit_document(documents, batch_id)
    write_json_atomic(audit_path(root, batch_id), audit)
    return audit


def validate_global_ownership_decisions(
    root: Path,
) -> GlobalOwnershipDecisionValidation:
    result = GlobalOwnershipDecisionValidation(status="PASS")
    try:
        documents = _inputs(root)
    except QbankError as exc:
        return GlobalOwnershipDecisionValidation(
            status="FAIL", checks={"canonical_inputs": "FAIL"}, errors=[str(exc)]
        )
    result.errors.extend(_validate_core(documents))
    if not result.errors:
        for batch_id in documents["decisions"].get("adjudicated_batches", []):
            expected = _audit_document(documents, batch_id)
            try:
                actual = read_json(audit_path(root, batch_id))
            except (OSError, QbankError) as exc:
                result.errors.append(f"{batch_id}: ownership audit unavailable: {exc}")
                continue
            if actual != expected:
                result.errors.append(
                    f"{batch_id}: batch audit is not the deterministic projection of ownership decisions"
                )
    result.checks = {
        "canonical_inputs": "PASS",
        "incremental_batch_reconciliation": "PASS" if not result.errors else "FAIL",
        "ownership_references_and_cycles": "PASS" if not result.errors else "FAIL",
        "global_role_consistency": "PASS" if not result.errors else "FAIL",
        "deterministic_batch_audits": "PASS" if not result.errors else "FAIL",
    }
    result.status = "FAIL" if result.errors else "PASS"
    return result
