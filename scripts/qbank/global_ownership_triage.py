"""Deterministic triage of global ownership candidate groups.

This module only characterizes pre-existing candidate groups.  It never
assigns an owner, cross-link, distinct context, or changes a clinical map.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
import re
from typing import Any

from .errors import QbankError
from .jsonio import read_json, write_json_atomic
from .master_scope import _extract_unit_ids, _normalized_title
from .paths import resolve_root_path


_OUTPUT_NAMES = ("global_ownership_triage.json", "global_ownership_batches.json")
_CANDIDATE_TYPES = (
    "EXACT_DUPLICATE_CANDIDATE", "EXPLICIT_CROSS_LINK_CANDIDATE",
    "SHARED_OBJECTIVE_OVERLAP", "CONTEXT_VARIANT_CANDIDATE",
    "TITLE_ONLY_COLLISION", "COMPLEX_MULTI_CHAPTER_GROUP", "INSUFFICIENT_SIGNAL",
)
_PRIORITIES = ("PRIORITY_A", "PRIORITY_B", "PRIORITY_C")
_CONTEXT_QUALIFIER = re.compile(
    r"\b(?:adult(?:s)?|pediatric(?:s)?|paediatric(?:s)?|child(?:ren)?|adolescent(?:s)?|"
    r"pregnan(?:t|cy)|postpartum|neonat(?:al|e|es)?|elderly|geriatric|emergency|acute|"
    r"outpatient|inpatient|primary care|rural|urban)\b",
    re.IGNORECASE,
)


class GlobalOwnershipTriageError(QbankError):
    """Ownership triage cannot safely be built or validated."""


@dataclass
class GlobalOwnershipTriageValidation:
    status: str
    checks: dict[str, str] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)


def output_paths(root: Path) -> dict[str, Path]:
    return {
        name: resolve_root_path(root, Path("research/scope") / name, label=name)
        for name in _OUTPUT_NAMES
    }


def _read(root: Path, name: str) -> dict[str, Any]:
    value = read_json(resolve_root_path(root, Path("research/scope") / name, label=name))
    if not isinstance(value, dict):
        raise GlobalOwnershipTriageError(f"{name} must be a JSON object")
    return value


def _compact(value: object, limit: int = 420) -> str | None:
    if not isinstance(value, str):
        return None
    text = " ".join(value.split())
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def _context_variant(titles: list[str]) -> bool:
    """Detect title-only contextual qualifiers without interpreting clinical content."""
    if len(set(titles)) < 2:
        return False
    bases = {
        _normalized_title(_CONTEXT_QUALIFIER.sub(" ", title))
        for title in titles
    }
    return len(bases) == 1 and all(_CONTEXT_QUALIFIER.search(title) for title in titles)


def _candidate_type_and_priority(group: dict[str, Any]) -> tuple[str, str]:
    """Return workload triage only; this is intentionally not an ownership decision."""
    unit_count = len(group["study_unit_ids"])
    chapter_count = len(group["chapter_codes"])
    if unit_count >= 3 or chapter_count >= 3:
        return "COMPLEX_MULTI_CHAPTER_GROUP", "PRIORITY_C"
    if group.get("source_signal") == "EXPLICIT_CROSS_DISCIPLINE_NOTE_LINK":
        return "EXPLICIT_CROSS_LINK_CANDIDATE", "PRIORITY_A"
    if (
        group.get("normalized_titles_equal")
        and group.get("shared_mcc_objective_ids")
        and group.get("shared_direct_or_component_evidence")
    ):
        return "EXACT_DUPLICATE_CANDIDATE", "PRIORITY_A"
    if group.get("context_variant"):
        return "CONTEXT_VARIANT_CANDIDATE", "PRIORITY_B"
    if group.get("shared_mcc_objective_ids"):
        return "SHARED_OBJECTIVE_OVERLAP", "PRIORITY_B"
    if group.get("normalized_titles_equal"):
        return "TITLE_ONLY_COLLISION", "PRIORITY_C"
    return "INSUFFICIENT_SIGNAL", "PRIORITY_C"


def _group_record(group: dict[str, Any], by_id: dict[str, dict[str, Any]]) -> dict[str, Any]:
    group_id = group.get("candidate_group_id")
    ids = group.get("study_unit_ids")
    if not isinstance(group_id, str) or not isinstance(ids, list) or not ids or not all(isinstance(value, str) for value in ids):
        raise GlobalOwnershipTriageError("ownership candidate group has invalid identity fields")
    if ids != sorted(set(ids)):
        raise GlobalOwnershipTriageError(f"{group_id}: study_unit_ids must be sorted and unique")
    missing = sorted(set(ids) - set(by_id))
    if missing:
        raise GlobalOwnershipTriageError(f"{group_id}: references unknown master study_unit_id(s): {missing}")
    members = [by_id[unit_id] for unit_id in ids]
    chapters = sorted({str(entry["chapter_code"]) for entry in members})
    titles = [str(entry["title"]) for entry in members]
    objective_sets = [
        {
            evidence.get("mcc_id")
            for evidence in entry.get("mcc_evidence", [])
            if isinstance(evidence, dict) and evidence.get("evidence_type") == "OBJECTIVE_REFERENCE"
            and isinstance(evidence.get("mcc_id"), str)
        }
        for entry in members
    ]
    shared_objectives = sorted(set.intersection(*objective_sets)) if objective_sets else []
    direct_component = [
        {
            evidence.get("mcc_id")
            for evidence in entry.get("mcc_evidence", [])
            if isinstance(evidence, dict) and evidence.get("evidence_type") == "OBJECTIVE_REFERENCE"
            and isinstance(evidence.get("mcc_id"), str)
            and entry.get("classification") in {"DIRECT", "COMPONENT"}
        }
        for entry in members
    ]
    shared_direct_component = bool(direct_component) and bool(set.intersection(*direct_component))
    note_records = []
    for entry in members:
        note = _compact(entry.get("cross_discipline_note"))
        if note:
            linked = sorted((_extract_unit_ids(note) & set(ids)) - {entry["study_unit_id"]})
            if linked:
                note_records.append({"study_unit_id": entry["study_unit_id"], "linked_study_unit_ids": linked, "note": note})
    rationales = []
    for entry in members:
        rationale = next((_compact(evidence.get("mapping_rationale")) for evidence in entry.get("mcc_evidence", []) if isinstance(evidence, dict) and evidence.get("mapping_rationale")), None)
        if rationale:
            rationales.append({"study_unit_id": entry["study_unit_id"], "rationale": rationale})
    signals: dict[str, Any] = {
        "source_signal": group.get("signal"), "study_unit_ids": ids, "chapter_codes": chapters,
        "normalized_titles_equal": len({_normalized_title(title) for title in titles}) == 1,
        "shared_mcc_objective_ids": shared_objectives,
        "shared_direct_or_component_evidence": shared_direct_component,
        "context_variant": _context_variant(titles),
    }
    candidate_type, priority = _candidate_type_and_priority(signals)
    return {
        "group_id": group_id,
        "candidate_type": candidate_type,
        "priority": priority,
        "study_unit_ids": ids,
        "chapter_codes": chapters,
        "titles": titles,
        "current_classifications": [entry["classification"] for entry in members],
        "depths": [entry["scope_depth"] for entry in members],
        "shared_mcc_objective_ids": shared_objectives,
        "evidence_strengths": sorted({evidence["mapping_strength"] for entry in members for evidence in entry.get("mcc_evidence", []) if isinstance(evidence, dict) and isinstance(evidence.get("mapping_strength"), str)}),
        "explicit_cross_discipline_notes": note_records,
        "existing_rationale": rationales,
        "source_type": sorted({entry.get("source_type", "TORONTO_NOTES") for entry in members}),
    }


def _documents(root: Path) -> dict[str, dict[str, Any]]:
    master = _read(root, "master_scope_crosswalk.json")
    candidates = _read(root, "global_ownership_candidates.json")
    entries = master.get("entries")
    groups = candidates.get("groups")
    if not isinstance(entries, list) or not isinstance(groups, list):
        raise GlobalOwnershipTriageError("master entries and ownership groups must be arrays")
    by_id = {entry.get("study_unit_id"): entry for entry in entries if isinstance(entry, dict) and isinstance(entry.get("study_unit_id"), str)}
    if len(by_id) != len(entries) or master.get("total_study_units") != len(by_id):
        raise GlobalOwnershipTriageError("master scope must contain unique, reconciled study_unit_ids")
    if len(by_id) != 1487:
        raise GlobalOwnershipTriageError("master scope does not contain the required 1487 study units")
    if candidates.get("total_candidate_groups") != len(groups):
        raise GlobalOwnershipTriageError("ownership candidate group count does not reconcile")
    records = [_group_record(group, by_id) for group in groups if isinstance(group, dict)]
    if len(records) != len(groups) or len({record["group_id"] for record in records}) != len(records):
        raise GlobalOwnershipTriageError("ownership candidate groups must be unique objects with unique IDs")
    records.sort(key=lambda record: record["group_id"])
    type_counts = Counter(record["candidate_type"] for record in records)
    priority_counts = Counter(record["priority"] for record in records)
    triage = {
        "schema_version": "1.0", "scope": "DETERMINISTIC_OWNERSHIP_TRIAGE_ONLY",
        "ownership_candidate_groups": len(records),
        "ownership_candidate_study_units": len({unit_id for record in records for unit_id in record["study_unit_ids"]}),
        "candidate_type_counts": {value: type_counts[value] for value in _CANDIDATE_TYPES},
        "priority_counts": {value: priority_counts[value] for value in _PRIORITIES},
        "deterministic_invalid_or_stale_groups": [],
        "su_mcc_001_in_ownership_candidates": any("SU-MCC-001" in record["study_unit_ids"] for record in records),
        "groups": records,
    }
    batches = []
    for priority in _PRIORITIES:
        members = [record for record in records if record["priority"] == priority]
        for start in range(0, len(members), 10):
            selected = members[start:start + 10]
            batches.append({"batch_id": f"{priority}-B{start // 10 + 1:02d}", "priority": priority, "group_ids": [record["group_id"] for record in selected]})
    return {
        "global_ownership_triage.json": triage,
        "global_ownership_batches.json": {"schema_version": "1.0", "batch_size_maximum": 10, "total_batches": len(batches), "batches": batches},
    }


def build_global_ownership_triage(root: Path) -> dict[str, Any]:
    docs = _documents(root)
    for name, document in docs.items():
        write_json_atomic(output_paths(root)[name], document)
    return docs["global_ownership_triage.json"]


def validate_global_ownership_triage(root: Path) -> GlobalOwnershipTriageValidation:
    result = GlobalOwnershipTriageValidation(status="PASS")
    try:
        expected = _documents(root)
        actual = {name: read_json(path) for name, path in output_paths(root).items()}
    except QbankError as exc:
        return GlobalOwnershipTriageValidation(status="FAIL", checks={"outputs_present": "FAIL"}, errors=[str(exc)])
    if actual != expected:
        result.errors.append("ownership triage outputs are not the deterministic result of canonical inputs")
    triage = actual["global_ownership_triage.json"]
    batches = actual["global_ownership_batches.json"]
    groups = triage.get("groups", [])
    if len(groups) != triage.get("ownership_candidate_groups"):
        result.errors.append("every original ownership candidate group must be accounted for")
    if sum(triage.get("candidate_type_counts", {}).values()) != len(groups) or any(group.get("candidate_type") not in _CANDIDATE_TYPES for group in groups):
        result.errors.append("each group must have exactly one candidate type")
    if sum(triage.get("priority_counts", {}).values()) != len(groups) or any(group.get("priority") not in _PRIORITIES for group in groups):
        result.errors.append("each group must have exactly one priority")
    batch_ids = [group_id for batch in batches.get("batches", []) for group_id in batch.get("group_ids", [])]
    group_ids = [group.get("group_id") for group in groups]
    if any(len(batch.get("group_ids", [])) > 10 for batch in batches.get("batches", [])):
        result.errors.append("semantic batch size exceeds 10 candidate groups")
    if set(batch_ids) != set(group_ids) or len(batch_ids) != len(set(batch_ids)):
        result.errors.append("semantic batches do not reconcile to ownership candidate groups")
    forbidden = {"PRIMARY_OWNER", "CROSS_LINK", "DISTINCT_CONTEXT"}
    if any(forbidden & set(group) for group in groups if isinstance(group, dict)):
        result.errors.append("ownership decision fields were introduced")
    result.checks["deterministic_reconciliation"] = "PASS" if not result.errors else "FAIL"
    result.status = "FAIL" if result.errors else "PASS"
    return result
