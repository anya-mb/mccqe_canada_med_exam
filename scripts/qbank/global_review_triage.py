"""Deterministic triage of global scope-review candidates.

This module classifies existing canonical metadata only.  It does not alter
chapter mappings or make semantic/ownership decisions.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
import re
from typing import Any

from .errors import QbankError
from .jsonio import read_json, write_json_atomic
from .master_scope import _extract_unit_ids
from .paths import resolve_root_path


_OUTPUT_NAMES = (
    "global_review_triage.json",
    "global_review_tier1.json",
    "global_review_tier2.json",
    "global_review_tier3.json",
    "global_review_batches.json",
)
_ACTIVE_TIERS = ("TIER_1_CRITICAL", "TIER_2_MAPPING", "TIER_3_SECONDARY")
_CATEGORIES = (*_ACTIVE_TIERS, "OWNERSHIP_ONLY", "NO_CURRENT_SEMANTIC_REVIEW")
_REVIEW_RECORD_STATUSES = frozenset({
    "RESOLVED", "OPEN_SOURCE", "OPEN_MAPPING", "DEFERRED_OWNERSHIP",
    "INFORMATIONAL", "INSUFFICIENT_METADATA",
})
_UNIT_ID_PATTERN = re.compile(r"\bSU-[A-Z]+-\d{2,3}\b")
_STRUCTURAL_ISSUE = re.compile(r"(?:structural|toc|heading|ocr|page|source|body_recovered|merged|wrapped)", re.I)


class GlobalReviewTriageError(QbankError):
    """Global review triage cannot safely be built or validated."""


@dataclass
class GlobalReviewTriageValidation:
    status: str
    checks: dict[str, str] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)


def output_paths(root: Path) -> dict[str, Path]:
    return {
        name: resolve_root_path(root, Path("research/scope") / name, label=name)
        for name in _OUTPUT_NAMES
    }


def _read(root: Path, name: str) -> dict[str, Any]:
    path = resolve_root_path(root, Path("research/scope") / name, label=name)
    value = read_json(path)
    if not isinstance(value, dict):
        raise GlobalReviewTriageError(f"{name} must be a JSON object")
    return value


def _compact(text: object, limit: int = 420) -> str | None:
    if not isinstance(text, str):
        return None
    normalized = " ".join(text.split())
    return normalized if len(normalized) <= limit else normalized[: limit - 1].rstrip() + "…"


def _direct_ids(item: dict[str, Any]) -> set[str]:
    value = item.get("study_unit_id")
    return set(_UNIT_ID_PATTERN.findall(value)) if isinstance(value, str) else set()


def _is_resolved(status: object) -> bool:
    value = str(status or "").upper()
    return bool(value) and not value.startswith("UNRESOLVED") and ("RESOLVED" in value or "NO ACTION" in value)


def _is_unresolved(status: object) -> bool:
    return "UNRESOLVED" in str(status or "").upper()


def _review_record_status(item: dict[str, Any]) -> str | None:
    """Return an explicit canonical status, preserving legacy conventions."""
    status = str(item.get("resolution_status") or "").upper()
    if status in _REVIEW_RECORD_STATUSES:
        return status
    if _is_resolved(status) or "resolved_via_body_evidence" in str(item.get("issue_type") or "").lower():
        return "RESOLVED"
    return None


def _is_open_review_item(item: dict[str, Any]) -> bool:
    """Use only its recorded status/severity; do not interpret clinical text."""
    explicit_status = _review_record_status(item)
    if explicit_status in {"RESOLVED", "INFORMATIONAL", "DEFERRED_OWNERSHIP"}:
        return False
    if explicit_status in {"OPEN_SOURCE", "OPEN_MAPPING", "INSUFFICIENT_METADATA"}:
        return True
    if _is_unresolved(item.get("resolution_status")):
        return True
    if "resolved_via_body_evidence" in str(item.get("issue_type") or "").lower():
        return False
    if item.get("resolution_status"):
        return False
    severity = str(item.get("severity") or "").lower()
    return any(token in severity for token in ("review", "flagged", "high", "medium"))


def _review_metadata(root: Path) -> tuple[dict[str, list[dict[str, Any]]], dict[str, list[dict[str, Any]]]]:
    unresolved: dict[str, list[dict[str, Any]]] = defaultdict(list)
    resolved: dict[str, list[dict[str, Any]]] = defaultdict(list)
    chapters = resolve_root_path(root, Path("research/scope/chapters"), label="chapter scope directory")
    for path in sorted(chapters.glob("*/review_items.json")):
        doc = read_json(path)
        if not isinstance(doc, dict) or not isinstance(doc.get("items"), list):
            raise GlobalReviewTriageError(f"{path}: review items must be an array")
        for item in doc["items"]:
            if not isinstance(item, dict):
                continue
            for unit_id in _direct_ids(item):
                record = {key: item.get(key) for key in ("issue_type", "resolution_status", "recommended_action", "summary")}
                record["review_record_status"] = _review_record_status(item)
                (unresolved if _is_open_review_item(item) else resolved)[unit_id].append(record)
    for path in sorted(chapters.glob("*/unresolved_mappings.json")):
        doc = read_json(path)
        if not isinstance(doc, dict):
            raise GlobalReviewTriageError(f"{path}: unresolved mappings must be an object")
        items = doc.get("unresolved_mappings", [])
        if not isinstance(items, list):
            raise GlobalReviewTriageError(f"{path}: unresolved mappings must be an array")
        for item in items:
            if not isinstance(item, dict):
                continue
            for unit_id in _direct_ids(item):
                unresolved[unit_id].append({
                    "issue_type": item.get("issue") or "unresolved_mapping",
                    "resolution_status": "UNRESOLVED_CHAPTER_MAPPING",
                    "recommended_action": item.get("recommended_action"),
                    "summary": item.get("reason") or item.get("uncertain_reason"),
                    "review_record_status": "OPEN_MAPPING",
                })
    persistent_ids = {
        unit_id
        for unit_id, records in resolved.items()
        if any(
            record.get("issue_type") == "persistent_global_scope_uncertainty"
            and record.get("review_record_status") == "INFORMATIONAL"
            for record in records
        )
    }
    for unit_id in persistent_ids:
        unresolved[unit_id] = [
            record for record in unresolved[unit_id]
            if record.get("review_record_status") != "OPEN_MAPPING"
        ]
    return unresolved, resolved


def _ownership_ids(ownership: dict[str, Any]) -> set[str]:
    groups = ownership.get("groups")
    if not isinstance(groups, list):
        raise GlobalReviewTriageError("global ownership groups must be an array")
    return {unit_id for group in groups if isinstance(group, dict) for unit_id in group.get("study_unit_ids", []) if isinstance(unit_id, str)}


def _reasons(entry: dict[str, Any], original_reasons: list[str], unresolved: list[dict[str, Any]], resolved: list[dict[str, Any]], ownership_ids: set[str]) -> list[str]:
    evidence = entry.get("mcc_evidence", [])
    strengths = {item.get("mapping_strength") for item in evidence if isinstance(item, dict)}
    reasons: list[str] = []
    persistent_scope_uncertainty = any(
        item.get("issue_type") == "persistent_global_scope_uncertainty"
        and item.get("review_record_status") == "INFORMATIONAL"
        for item in resolved
    )
    if entry.get("classification") == "UNCERTAIN":
        reasons.append(
            "PERSISTENT_GLOBAL_SCOPE_UNCERTAINTY"
            if persistent_scope_uncertainty else "UNCERTAIN_PRIMARY"
        )
    if strengths == {"WEAK"}: reasons.append("ONLY_WEAK_EVIDENCE")
    elif "WEAK" in strengths: reasons.append("ANY_WEAK_EVIDENCE")
    if any(item.get("requires_scope_review") is True for item in evidence if isinstance(item, dict)): reasons.append("REQUIRES_SCOPE_REVIEW")
    statuses = {item.get("review_record_status") for item in unresolved}
    resolved_statuses = {item.get("review_record_status") for item in resolved}
    source_metadata_resolved = any(
        item.get("issue_type") == "source_review_other_metadata_triage"
        and item.get("review_record_status") in {"RESOLVED", "INFORMATIONAL", "DEFERRED_OWNERSHIP"}
        for item in resolved
    )
    if unresolved: reasons.append("UNRESOLVED_CHAPTER_REVIEW_ITEM")
    if "OPEN_SOURCE" in statuses: reasons.append("OPEN_SOURCE_REVIEW_ITEM")
    if "OPEN_MAPPING" in statuses: reasons.append("OPEN_MAPPING_REVIEW_ITEM")
    if "INSUFFICIENT_METADATA" in statuses: reasons.append("STATUS_REQUIRES_ADJUDICATION")
    if "RESOLVED" in resolved_statuses or ("UNRESOLVED_CHAPTER_REVIEW_ITEM" in original_reasons and not unresolved): reasons.append("RESOLVED_CHAPTER_REVIEW_ITEM")
    if "INFORMATIONAL" in resolved_statuses: reasons.append("INFORMATIONAL_CHAPTER_REVIEW_ITEM")
    if "DEFERRED_OWNERSHIP" in resolved_statuses: reasons.append("DEFERRED_OWNERSHIP_REVIEW_ITEM")
    if (
        "OPEN_SOURCE" in statuses
        or (
            not source_metadata_resolved
            and any(_STRUCTURAL_ISSUE.search(str(item.get("issue_type") or "")) for item in unresolved if not item.get("review_record_status"))
        )
        or (entry.get("page_mapping_precision") == "UNRESOLVED" and not source_metadata_resolved)
    ):
        reasons.append("SOURCE_AMBIGUITY_UNRESOLVED")
    jurisdiction = entry.get("jurisdiction")
    if isinstance(jurisdiction, dict) and jurisdiction.get("scope") == "UNRESOLVED": reasons.append("JURISDICTION_UNRESOLVED")
    freshness = entry.get("freshness")
    if isinstance(freshness, dict) and freshness: reasons.append("FRESHNESS_FLAG_ONLY")
    if entry.get("classification") == "CROSS_DISCIPLINE": reasons.append("PRIMARY_CROSS_DISCIPLINE")
    if entry.get("cross_discipline_note"): reasons.append("CROSS_DISCIPLINE_NOTE_ONLY")
    if entry.get("study_unit_id") in ownership_ids: reasons.append("OWNERSHIP_ONLY")
    if any(_STRUCTURAL_ISSUE.search(str(item.get("issue_type") or "")) for item in resolved): reasons.append("STRUCTURAL_HISTORY_RESOLVED")
    if not reasons: reasons.append("OTHER")
    return reasons


def _category(reasons: list[str]) -> str:
    values = set(reasons)
    if values & {"UNCERTAIN_PRIMARY", "SOURCE_AMBIGUITY_UNRESOLVED", "JURISDICTION_UNRESOLVED", "OPEN_SOURCE_REVIEW_ITEM", "STATUS_REQUIRES_ADJUDICATION"}:
        return "TIER_1_CRITICAL"
    if values & {"ONLY_WEAK_EVIDENCE", "REQUIRES_SCOPE_REVIEW"}:
        return "TIER_2_MAPPING"
    if "ANY_WEAK_EVIDENCE" in values or "UNRESOLVED_CHAPTER_REVIEW_ITEM" in values or "OPEN_MAPPING_REVIEW_ITEM" in values:
        return "TIER_3_SECONDARY"
    if values & {"PRIMARY_CROSS_DISCIPLINE", "CROSS_DISCIPLINE_NOTE_ONLY", "OWNERSHIP_ONLY", "DEFERRED_OWNERSHIP_REVIEW_ITEM"}:
        return "OWNERSHIP_ONLY"
    return "NO_CURRENT_SEMANTIC_REVIEW"


def _compact_entry(entry: dict[str, Any], reasons: list[str], unresolved: list[dict[str, Any]], category: str) -> dict[str, Any]:
    evidence = [
        {key: value for key, value in {
            "mcc_id": item.get("mcc_id"), "evidence_type": item.get("evidence_type"),
            "mapping_strength": item.get("mapping_strength"),
        }.items() if value is not None}
        for item in entry.get("mcc_evidence", []) if isinstance(item, dict)
    ]
    rationale = next((_compact(item.get("mapping_rationale")) for item in entry.get("mcc_evidence", []) if isinstance(item, dict) and item.get("mapping_rationale")), None)
    note = next((_compact(item.get("recommended_action")) or _compact(item.get("summary")) for item in unresolved), None)
    return {key: value for key, value in {
        "study_unit_id": entry["study_unit_id"], "chapter_code": entry["chapter_code"], "title": entry["title"],
        "current_classification": entry["classification"], "depth": entry["scope_depth"],
        "mcc_evidence": evidence, "mapping_rationale": rationale, "review_reasons": reasons,
        "unresolved_review_note": note, "primary_triage_category": category,
    }.items() if value is not None}


def _documents(root: Path) -> dict[str, dict[str, Any]]:
    master = _read(root, "master_scope_crosswalk.json")
    candidates = _read(root, "global_review_candidates.json")
    ownership = _read(root, "global_ownership_candidates.json")
    entries = master.get("entries")
    candidate_rows = candidates.get("candidates")
    if not isinstance(entries, list) or not isinstance(candidate_rows, list):
        raise GlobalReviewTriageError("master entries and review candidates must be arrays")
    by_id = {item.get("study_unit_id"): item for item in entries if isinstance(item, dict) and isinstance(item.get("study_unit_id"), str)}
    candidate_ids = [item.get("study_unit_id") for item in candidate_rows if isinstance(item, dict)]
    candidate_reasons = {item["study_unit_id"]: item.get("reason_codes", []) for item in candidate_rows if isinstance(item, dict) and isinstance(item.get("study_unit_id"), str) and isinstance(item.get("reason_codes"), list)}
    if len(candidate_ids) != len(set(candidate_ids)) or any(unit_id not in by_id for unit_id in candidate_ids):
        raise GlobalReviewTriageError("review candidates must be unique master study units")
    unresolved, resolved = _review_metadata(root)
    ownership_ids = _ownership_ids(ownership)
    triaged = []
    for unit_id in sorted(candidate_ids):
        entry = by_id[unit_id]
        reasons = _reasons(entry, candidate_reasons.get(unit_id, []), unresolved[unit_id], resolved[unit_id], ownership_ids)
        triaged.append(_compact_entry(entry, reasons, unresolved[unit_id], _category(reasons)))
    counts = Counter(item["primary_triage_category"] for item in triaged)
    result = {"schema_version": "1.0", "original_candidates": len(triaged), "category_counts": {category: counts[category] for category in _CATEGORIES}, "entries": triaged}
    docs = {"global_review_triage.json": result}
    for tier, filename in zip(_ACTIVE_TIERS, _OUTPUT_NAMES[1:4], strict=True):
        items = [item for item in triaged if item["primary_triage_category"] == tier]
        docs[filename] = {"schema_version": "1.0", "tier": tier, "total_study_units": len(items), "entries": items}
    batches = []
    for tier in _ACTIVE_TIERS:
        items = [item for item in triaged if item["primary_triage_category"] == tier]
        for start in range(0, len(items), 25):
            members = items[start:start + 25]
            batches.append({"batch_id": f"{tier}-B{start // 25 + 1:02d}", "tier": tier, "study_unit_ids": [item["study_unit_id"] for item in members], "chapter_codes": sorted({item["chapter_code"] for item in members}), "reason_counts": dict(sorted(Counter(reason for item in members for reason in item["review_reasons"]).items()))})
    docs["global_review_batches.json"] = {"schema_version": "1.0", "batch_size_maximum": 25, "total_batches": len(batches), "batches": batches}
    return docs


def build_global_review_triage(root: Path) -> dict[str, Any]:
    docs = _documents(root)
    for name, value in docs.items(): write_json_atomic(output_paths(root)[name], value)
    return docs["global_review_triage.json"]


def validate_global_review_triage(root: Path) -> GlobalReviewTriageValidation:
    result = GlobalReviewTriageValidation(status="PASS")
    try:
        expected = _documents(root)
        actual = {name: read_json(path) for name, path in output_paths(root).items()}
    except QbankError as exc:
        return GlobalReviewTriageValidation(status="FAIL", checks={"outputs_present": "FAIL"}, errors=[str(exc)])
    result.checks["deterministic_reconciliation"] = "PASS" if actual == expected else "FAIL"
    if actual != expected: result.errors.append("triage outputs are not the deterministic result of canonical inputs")
    triage = actual["global_review_triage.json"]
    batches = actual["global_review_batches.json"]
    entries = triage.get("entries", [])
    categories = [item.get("primary_triage_category") for item in entries if isinstance(item, dict)]
    if len(entries) != triage.get("original_candidates") or any(category not in _CATEGORIES for category in categories): result.errors.append("each original candidate must have exactly one primary category")
    if sum(triage.get("category_counts", {}).values()) != len(entries): result.errors.append("category counts do not reconcile")
    semantic_ids = {item["study_unit_id"] for item in entries if item.get("primary_triage_category") in _ACTIVE_TIERS}
    batch_ids = [unit_id for batch in batches.get("batches", []) for unit_id in batch.get("study_unit_ids", [])]
    if any(len(batch.get("study_unit_ids", [])) > 25 for batch in batches.get("batches", [])): result.errors.append("batch size exceeds 25")
    if set(batch_ids) != semantic_ids or len(batch_ids) != len(set(batch_ids)): result.errors.append("semantic batches do not reconcile to active tiers")
    if any(item.get("primary_triage_category") == "OWNERSHIP_ONLY" and item["study_unit_id"] in batch_ids for item in entries): result.errors.append("ownership-only item entered semantic batches")
    if any(item.get("primary_triage_category") == "NO_CURRENT_SEMANTIC_REVIEW" and item["study_unit_id"] in batch_ids for item in entries): result.errors.append("resolved-only item entered semantic batches")
    result.checks["accounting_and_batching"] = "PASS" if not result.errors else "FAIL"
    result.status = "FAIL" if result.errors else "PASS"
    return result
