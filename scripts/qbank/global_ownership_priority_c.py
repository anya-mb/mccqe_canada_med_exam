"""Deterministic review design for unadjudicated Priority-C ownership groups.

This module characterizes existing ownership candidates and review workload only.
It deliberately does not assign, alter, or infer any ownership decision.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .errors import QbankError
from .jsonio import read_json, write_json_atomic
from .master_scope import _extract_unit_ids, _normalized_title
from .paths import resolve_root_path


_OUTPUT_NAMES = ("global_ownership_priority_c_triage.json", "global_ownership_priority_c_batches.json")
_WORK_TYPES = (
    "C_TITLE_COLLISION", "C_COMPLEX_MULTI_UNIT", "C_EXISTING_OWNERSHIP_INTERACTION",
    "C_POSSIBLE_MULTI_COMPETENCY", "C_WEAK_SIGNAL_OVERLAP",
    "C_TARGETED_COUNTERPART_NEEDED", "C_OTHER",
)
_SUBPRIORITIES = ("C1", "C2", "C3")
_BATCH_LIMITS = {"C1": 8, "C2": 6, "C3": 4}
_FORBIDDEN_DECISION_FIELDS = {"ownership_role", "decision_status", "primary_owner_study_unit_id"}


class GlobalOwnershipPriorityCError(QbankError):
    """Priority-C review design cannot safely be built or validated."""


@dataclass
class GlobalOwnershipPriorityCValidation:
    status: str
    checks: dict[str, str] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)


def output_paths(root: Path) -> dict[str, Path]:
    return {name: resolve_root_path(root, Path("research/scope") / name, label=name) for name in _OUTPUT_NAMES}


def _read(root: Path, relative: str) -> dict[str, Any]:
    value = read_json(resolve_root_path(root, relative, label=relative))
    if not isinstance(value, dict):
        raise GlobalOwnershipPriorityCError(f"{relative} must be a JSON object")
    return value


def _objective_ids(entry: dict[str, Any]) -> list[str]:
    return sorted({
        evidence["mcc_id"] for evidence in entry.get("mcc_evidence", [])
        if isinstance(evidence, dict) and evidence.get("evidence_type") == "OBJECTIVE_REFERENCE"
        and isinstance(evidence.get("mcc_id"), str)
    })


def _counterpart_note(entry: dict[str, Any]) -> dict[str, Any] | None:
    note = entry.get("cross_discipline_note")
    if not isinstance(note, str) or not note.strip():
        return None
    counterpart_ids = sorted(_extract_unit_ids(note) - {entry["study_unit_id"]})
    return {"study_unit_id": entry["study_unit_id"], "counterpart_study_unit_ids": counterpart_ids, "note": " ".join(note.split())}


def _existing_relationships(decisions: dict[str, Any]) -> dict[str, list[dict[str, str]]]:
    result: dict[str, list[dict[str, str]]] = defaultdict(list)
    for item in decisions.get("decisions", []):
        if not isinstance(item, dict) or not isinstance(item.get("study_unit_id"), str):
            continue
        role = item.get("ownership_role")
        group_id = item.get("candidate_group_id")
        if role not in {"PRIMARY_OWNER", "CROSS_LINK", "DISTINCT_CONTEXT"} or not isinstance(group_id, str):
            continue
        record = {"candidate_group_id": group_id, "ownership_role": role}
        target = item.get("primary_owner_study_unit_id")
        if isinstance(target, str):
            record["primary_owner_study_unit_id"] = target
        result[item["study_unit_id"]].append(record)
    for values in result.values():
        values.sort(key=lambda value: (value["candidate_group_id"], value["ownership_role"], value.get("primary_owner_study_unit_id", "")))
    return result


def _work_type(source_signal: str, ids: list[str], relationships: list[dict[str, Any]]) -> tuple[str, str]:
    if relationships:
        return "C_EXISTING_OWNERSHIP_INTERACTION", "existing Priority-A/B ownership relationship requires graph-aware review"
    if len(ids) >= 3:
        return "C_COMPLEX_MULTI_UNIT", "three or more candidate units require relational ownership review"
    if source_signal == "IDENTICAL_NORMALIZED_TITLE":
        return "C_TITLE_COLLISION", "identical normalized titles are the sole candidate-generation signal"
    if len(ids) == 1:
        return "C_TARGETED_COUNTERPART_NEEDED", "singleton cross-discipline candidate requires a narrow counterpart lookup"
    return "C_OTHER", "no deterministic Priority-C work-type rule applies"


def _subpriority(work_type: str) -> str:
    if work_type == "C_TARGETED_COUNTERPART_NEEDED":
        return "C1"
    if work_type == "C_TITLE_COLLISION":
        return "C2"
    return "C3"


def _title_evidence_level(shared_objectives: list[str], counterpart_notes: list[dict[str, Any]], classifications: list[str], depths: list[str], relationships: list[dict[str, Any]]) -> str | None:
    signals = sum((
        bool(shared_objectives),
        bool(counterpart_notes),
        len(set(classifications)) == 1 and len(set(depths)) == 1,
        bool(relationships),
    ))
    if signals == 0:
        return "TITLE_ONLY"
    if signals == 1:
        return "TITLE_PLUS_ONE_SIGNAL"
    return "TITLE_PLUS_MULTIPLE_SIGNALS"


def _documents(root: Path) -> dict[str, dict[str, Any]]:
    master = _read(root, "research/scope/master_scope_crosswalk.json")
    candidates = _read(root, "research/scope/global_ownership_candidates.json")
    ownership_triage = _read(root, "research/scope/global_ownership_triage.json")
    decisions = _read(root, "research/scope/global_ownership_decisions.json")
    entries = master.get("entries")
    if not isinstance(entries, list) or master.get("total_study_units") != 1487:
        raise GlobalOwnershipPriorityCError("master scope must contain the required 1487 study units")
    by_id = {entry.get("study_unit_id"): entry for entry in entries if isinstance(entry, dict) and isinstance(entry.get("study_unit_id"), str)}
    if len(by_id) != len(entries):
        raise GlobalOwnershipPriorityCError("master study_unit_ids must be unique")
    original = {item.get("candidate_group_id"): item for item in candidates.get("groups", []) if isinstance(item, dict) and isinstance(item.get("candidate_group_id"), str)}
    priority_c = [item for item in ownership_triage.get("groups", []) if isinstance(item, dict) and item.get("priority") == "PRIORITY_C"]
    if len(priority_c) != 29 or len({item.get("group_id") for item in priority_c}) != 29:
        raise GlobalOwnershipPriorityCError("canonical ownership triage must contain exactly 29 unique Priority-C groups")
    relationships_by_unit = _existing_relationships(decisions)
    groups: list[dict[str, Any]] = []
    for item in sorted(priority_c, key=lambda value: value["group_id"]):
        group_id = item["group_id"]
        source = original.get(group_id)
        ids = item.get("study_unit_ids")
        if not isinstance(source, dict) or not isinstance(ids, list) or ids != sorted(set(ids)) or any(unit_id not in by_id for unit_id in ids):
            raise GlobalOwnershipPriorityCError(f"{group_id}: invalid or stale canonical candidate membership")
        members = [by_id[unit_id] for unit_id in ids]
        chapters = sorted({entry["chapter_code"] for entry in members})
        titles = [entry["title"] for entry in members]
        normalized_titles = [_normalized_title(title) for title in titles]
        objective_sets = [set(_objective_ids(entry)) for entry in members]
        shared_objectives = sorted(set.intersection(*objective_sets)) if objective_sets else []
        counterpart_notes = [note for entry in members if (note := _counterpart_note(entry))]
        relationships = [
            {"study_unit_id": unit_id, **relationship}
            for unit_id in ids for relationship in relationships_by_unit.get(unit_id, [])
        ]
        relationships.sort(key=lambda value: (value["study_unit_id"], value["candidate_group_id"], value["ownership_role"]))
        work_type, rationale = _work_type(str(source.get("signal")), ids, relationships)
        classifications = [entry["classification"] for entry in members]
        depths = [entry["scope_depth"] for entry in members]
        multi_competency_ids = [entry["study_unit_id"] for entry in members if len(_objective_ids(entry)) >= 2]
        record: dict[str, Any] = {
            "candidate_group_id": group_id,
            "original_candidate_type": item["candidate_type"],
            "original_candidate_signal": source.get("signal"),
            "work_type": work_type,
            "subpriority": _subpriority(work_type),
            "study_unit_ids": ids,
            "candidate_unit_count": len(ids),
            "candidate_shape": "SINGLETON" if len(ids) == 1 else "PAIR" if len(ids) == 2 else "THREE_OR_MORE_UNITS",
            "chapter_codes": chapters,
            "chapter_count": len(chapters),
            "titles": titles,
            "normalized_titles": normalized_titles,
            "normalized_titles_equal": len(set(normalized_titles)) == 1,
            "shared_mcc_objective_ids": shared_objectives,
            "objective_overlap_count": len(shared_objectives),
            "classifications": classifications,
            "depths": depths,
            "evidence_strengths": item.get("evidence_strengths", []),
            "explicit_cross_discipline_counterpart_notes": counterpart_notes,
            "external_counterpart_metadata_exists": any(note["counterpart_study_unit_ids"] for note in counterpart_notes),
            "existing_ownership_relationships": relationships,
            "potential_ownership_graph_interaction": bool(relationships),
            "one_unit_one_owner_representation_may_be_insufficient": bool(multi_competency_ids),
            "possible_multi_competency_study_unit_ids": multi_competency_ids,
            "rationale": rationale,
        }
        if work_type == "C_TITLE_COLLISION":
            record["title_collision_evidence_level"] = _title_evidence_level(shared_objectives, counterpart_notes, classifications, depths, relationships)
        groups.append(record)
    work_counts = Counter(group["work_type"] for group in groups)
    subpriority_counts = Counter(group["subpriority"] for group in groups)
    title_counts = Counter(group.get("title_collision_evidence_level") for group in groups if group["work_type"] == "C_TITLE_COLLISION")
    multi_pattern_count = sum(bool(group["possible_multi_competency_study_unit_ids"]) for group in groups)
    triage = {
        "schema_version": "1.0",
        "scope": "DETERMINISTIC_PRIORITY_C_OWNERSHIP_REVIEW_DESIGN_ONLY",
        "priority_c_groups": len(groups),
        "work_type_counts": {work_type: work_counts[work_type] for work_type in _WORK_TYPES},
        "title_collision_evidence_counts": {key: title_counts[key] for key in ("TITLE_ONLY", "TITLE_PLUS_ONE_SIGNAL", "TITLE_PLUS_MULTIPLE_SIGNALS")},
        "subpriority_counts": {key: subpriority_counts[key] for key in _SUBPRIORITIES},
        "priority_c_groups_matching_multi_competency_pattern": multi_pattern_count,
        "model_recommendations": {"C1": "BALANCED_MEDIUM", "C2": "BALANCED_MEDIUM", "C3": "STRONG_HIGH"},
        "schema_extension_timing": "DEFER_SCHEMA_EXTENSION_UNTIL_AFTER_PRIORITY_C",
        "groups": groups,
    }
    batches = []
    for subpriority in _SUBPRIORITIES:
        selected = [group for group in groups if group["subpriority"] == subpriority]
        for start in range(0, len(selected), _BATCH_LIMITS[subpriority]):
            batch = selected[start:start + _BATCH_LIMITS[subpriority]]
            batches.append({"batch_id": f"{subpriority}-B{start // _BATCH_LIMITS[subpriority] + 1:02d}", "subpriority": subpriority, "group_ids": [group["candidate_group_id"] for group in batch]})
    return {
        "global_ownership_priority_c_triage.json": triage,
        "global_ownership_priority_c_batches.json": {"schema_version": "1.0", "scope": "DETERMINISTIC_PRIORITY_C_SEMANTIC_BATCHES_ONLY", "batch_size_maximum": _BATCH_LIMITS, "total_batches": len(batches), "batches": batches},
    }


def build_global_ownership_priority_c_triage(root: Path) -> dict[str, Any]:
    documents = _documents(root)
    for name, document in documents.items():
        write_json_atomic(output_paths(root)[name], document)
    return documents["global_ownership_priority_c_triage.json"]


def validate_global_ownership_priority_c_triage(root: Path) -> GlobalOwnershipPriorityCValidation:
    result = GlobalOwnershipPriorityCValidation(status="PASS")
    try:
        expected = _documents(root)
        actual = {name: read_json(path) for name, path in output_paths(root).items()}
    except QbankError as exc:
        return GlobalOwnershipPriorityCValidation(status="FAIL", checks={"outputs_present": "FAIL"}, errors=[str(exc)])
    triage = actual["global_ownership_priority_c_triage.json"]
    batches = actual["global_ownership_priority_c_batches.json"]
    groups = triage.get("groups", [])
    if actual != expected:
        result.errors.append("Priority-C triage outputs are not the deterministic result of canonical inputs")
    if len(groups) != 29 or triage.get("priority_c_groups") != 29:
        result.errors.append("exactly 29 Priority-C groups must be accounted for")
    if sum(triage.get("work_type_counts", {}).values()) != len(groups) or any(group.get("work_type") not in _WORK_TYPES for group in groups):
        result.errors.append("each Priority-C group must have exactly one work type")
    if sum(triage.get("subpriority_counts", {}).values()) != len(groups) or any(group.get("subpriority") not in _SUBPRIORITIES for group in groups):
        result.errors.append("each Priority-C group must have exactly one subpriority")
    group_ids = [group.get("candidate_group_id") for group in groups]
    batch_ids = [group_id for batch in batches.get("batches", []) for group_id in batch.get("group_ids", [])]
    if set(group_ids) != set(batch_ids) or len(batch_ids) != len(set(batch_ids)):
        result.errors.append("Priority-C semantic batches do not reconcile to triage groups")
    if any(len(batch.get("group_ids", [])) > _BATCH_LIMITS.get(batch.get("subpriority"), 0) for batch in batches.get("batches", [])):
        result.errors.append("Priority-C semantic batch size exceeds its subpriority limit")
    if any(_FORBIDDEN_DECISION_FIELDS & set(group) for group in groups if isinstance(group, dict)):
        result.errors.append("Priority-C triage introduced ownership-decision fields")
    result.checks["deterministic_reconciliation"] = "PASS" if not result.errors else "FAIL"
    result.status = "FAIL" if result.errors else "PASS"
    return result
