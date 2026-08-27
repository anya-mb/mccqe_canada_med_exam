"""Deterministically decompose Tier-1 global review work without remapping."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .errors import QbankError
from .global_review_triage import _review_metadata
from .jsonio import read_json, write_json_atomic
from .paths import resolve_root_path


_OUTPUT_NAMES = (
    "tier1_source_review.json",
    "tier1_mapping_review.json",
    "tier1_jurisdiction_review.json",
    "tier1_status_adjudication.json",
)
_WORK_TYPES = (
    "SOURCE_REVIEW",
    "MAPPING_REVIEW",
    "JURISDICTION_REVIEW",
    "STATUS_ADJUDICATION",
    "OTHER",
)
_MAPPING_ISSUES = ("UNCERTAIN_PRIMARY", "ONLY_WEAK", "OTHER_MAPPING_ISSUE")
_SOURCE_REASONS = {"SOURCE_AMBIGUITY_UNRESOLVED", "OPEN_SOURCE_REVIEW_ITEM"}
_MAPPING_REASONS = {
    "UNCERTAIN_PRIMARY", "ONLY_WEAK_EVIDENCE", "ANY_WEAK_EVIDENCE",
    "REQUIRES_SCOPE_REVIEW", "OPEN_MAPPING_REVIEW_ITEM",
}
_REASON_LABELS = {
    "OPEN_SOURCE_REVIEW_ITEM": "OPEN_SOURCE",
    "OPEN_MAPPING_REVIEW_ITEM": "OPEN_MAPPING",
    "ONLY_WEAK_EVIDENCE": "ONLY_WEAK",
}


class Tier1DecompositionError(QbankError):
    """Tier-1 review packets cannot be built or reconciled safely."""


@dataclass
class Tier1DecompositionValidation:
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
        raise Tier1DecompositionError(f"{name} must be a JSON object")
    return value


def _compact(value: object, limit: int = 420) -> str | None:
    if not isinstance(value, str):
        return None
    value = " ".join(value.split())
    return value if len(value) <= limit else value[: limit - 1].rstrip() + "…"


def _work_type(reasons: list[str]) -> str:
    """Use a fixed non-semantic precedence for overlapping Tier-1 flags."""
    values = set(reasons)
    if values & _SOURCE_REASONS:
        return "SOURCE_REVIEW"
    if "JURISDICTION_UNRESOLVED" in values:
        return "JURISDICTION_REVIEW"
    if "STATUS_REQUIRES_ADJUDICATION" in values:
        return "STATUS_ADJUDICATION"
    if values & _MAPPING_REASONS:
        return "MAPPING_REVIEW"
    return "OTHER"


def _mapping_issue(reasons: list[str]) -> str | None:
    values = set(reasons)
    if "UNCERTAIN_PRIMARY" in values:
        return "UNCERTAIN_PRIMARY"
    if "ONLY_WEAK_EVIDENCE" in values:
        return "ONLY_WEAK"
    if values & _MAPPING_REASONS:
        return "OTHER_MAPPING_ISSUE"
    return None


def _reason_counts(entries: list[dict[str, Any]]) -> dict[str, int]:
    return dict(sorted(Counter(
        _REASON_LABELS.get(reason, reason)
        for entry in entries for reason in entry["review_reasons"]
    ).items()))


def _evidence(entry: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {key: item[key] for key in ("mcc_id", "evidence_type", "mapping_strength") if key in item}
        for item in entry.get("mcc_evidence", []) if isinstance(item, dict)
    ]


def _review_statuses(records: list[dict[str, Any]]) -> list[str]:
    return sorted({status for item in records if (status := item.get("review_record_status"))})


def _rationale(entry: dict[str, Any]) -> str | None:
    evidence = entry.get("mcc_evidence", [])
    if isinstance(evidence, list):
        for item in evidence:
            if isinstance(item, dict) and (value := _compact(item.get("mapping_rationale"))):
                return value
    return None


def _source_provenance(entry: dict[str, Any], records: list[dict[str, Any]]) -> dict[str, Any]:
    note = next((_compact(item.get("recommended_action")) or _compact(item.get("summary")) for item in records), None)
    return {
        key: value for key, value in {
            "source_node_ids": entry.get("source_node_ids"),
            "page_mapping_precision": entry.get("page_mapping_precision"),
            "pdf_page_range": entry.get("pdf_page_range"),
            "toronto_notes_page_range": entry.get("tn_page_range"),
            "unresolved_heading_or_review_note": note,
        }.items() if value is not None
    }


def _packet_entry(entry: dict[str, Any], records: list[dict[str, Any]], work_type: str) -> dict[str, Any]:
    result = {
        "study_unit_id": entry["study_unit_id"],
        "chapter_code": entry["chapter_code"],
        "title": entry["title"],
        "current_classification": entry["current_classification"],
        "current_depth": entry["depth"],
        "mcc_evidence": _evidence(entry),
        "review_reasons": entry["review_reasons"],
        "standardized_review_status": _review_statuses(records),
        "existing_rationale": _rationale(entry),
        "existing_review_note": _compact(entry.get("unresolved_review_note")),
        "primary_work_type": work_type,
    }
    if work_type == "SOURCE_REVIEW":
        result["source_provenance"] = _source_provenance(entry, records)
    if work_type == "MAPPING_REVIEW":
        result["mapping_review_issue"] = _mapping_issue(entry["review_reasons"])
    return {key: value for key, value in result.items() if value is not None}


def _documents(root: Path) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    tier1 = _read(root, "global_review_tier1.json")
    master = _read(root, "master_scope_crosswalk.json")
    entries = tier1.get("entries")
    master_entries = master.get("entries")
    if not isinstance(entries, list) or not isinstance(master_entries, list):
        raise Tier1DecompositionError("Tier-1 and master entries must be arrays")
    master_ids = {
        item.get("study_unit_id") for item in master_entries
        if isinstance(item, dict) and isinstance(item.get("study_unit_id"), str)
    }
    if any(not isinstance(item, dict) or item.get("primary_triage_category") != "TIER_1_CRITICAL" for item in entries):
        raise Tier1DecompositionError("Tier-1 packet contains a non-Tier-1 entry")
    tier1_ids = [item.get("study_unit_id") for item in entries if isinstance(item, dict)]
    if len(tier1_ids) != len(set(tier1_ids)) or any(unit_id not in master_ids for unit_id in tier1_ids):
        raise Tier1DecompositionError("Tier-1 entries must be unique master study units")
    unresolved, _ = _review_metadata(root)
    by_type = {work_type: [] for work_type in _WORK_TYPES}
    for entry in entries:
        work_type = _work_type(entry["review_reasons"])
        by_type[work_type].append(_packet_entry(entry, unresolved[entry["study_unit_id"]], work_type))
    for items in by_type.values(): items.sort(key=lambda item: item["study_unit_id"])
    reason_counts = {work_type: _reason_counts(items) for work_type, items in by_type.items()}
    mapping_counts = {
        issue: sum(entry.get("mapping_review_issue") == issue for entry in by_type["MAPPING_REVIEW"])
        for issue in _MAPPING_ISSUES
    }
    source_counts = {
        "OPEN_SOURCE": sum("OPEN_SOURCE_REVIEW_ITEM" in entry["review_reasons"] for entry in by_type["SOURCE_REVIEW"]),
        "OTHER": sum("OPEN_SOURCE_REVIEW_ITEM" not in entry["review_reasons"] for entry in by_type["SOURCE_REVIEW"]),
    }
    documents = {
        "tier1_source_review.json": {
            "schema_version": "1.0", "work_type": "SOURCE_REVIEW",
            "total_study_units": len(by_type["SOURCE_REVIEW"]),
            "reason_counts": reason_counts["SOURCE_REVIEW"],
            "source_review_counts": source_counts, "entries": by_type["SOURCE_REVIEW"],
        },
        "tier1_mapping_review.json": {
            "schema_version": "1.0", "work_type": "MAPPING_REVIEW",
            "total_study_units": len(by_type["MAPPING_REVIEW"]),
            "reason_counts": reason_counts["MAPPING_REVIEW"],
            "mapping_review_counts": mapping_counts, "entries": by_type["MAPPING_REVIEW"],
        },
        "tier1_jurisdiction_review.json": {
            "schema_version": "1.0", "work_type": "JURISDICTION_REVIEW",
            "total_study_units": len(by_type["JURISDICTION_REVIEW"]),
            "reason_counts": reason_counts["JURISDICTION_REVIEW"], "entries": by_type["JURISDICTION_REVIEW"],
        },
        "tier1_status_adjudication.json": {
            "schema_version": "1.0", "work_type": "STATUS_ADJUDICATION",
            "total_study_units": len(by_type["STATUS_ADJUDICATION"]),
            "reason_counts": reason_counts["STATUS_ADJUDICATION"], "entries": by_type["STATUS_ADJUDICATION"],
        },
    }
    summary = {
        "total_study_units": len(entries),
        "work_type_counts": {work_type: len(by_type[work_type]) for work_type in _WORK_TYPES},
        "reason_counts": reason_counts,
        "mapping_review_counts": mapping_counts,
        "source_review_counts": source_counts,
    }
    return documents, summary


def build_tier1_decomposition(root: Path) -> dict[str, Any]:
    documents, summary = _documents(root)
    for name, value in documents.items():
        write_json_atomic(output_paths(root)[name], value)
    return summary


def validate_tier1_decomposition(root: Path) -> Tier1DecompositionValidation:
    result = Tier1DecompositionValidation(status="PASS")
    try:
        expected, summary = _documents(root)
        actual = {name: read_json(path) for name, path in output_paths(root).items()}
    except QbankError as exc:
        return Tier1DecompositionValidation("FAIL", {"outputs_present": "FAIL"}, [str(exc)])
    if actual != expected:
        result.errors.append("Tier-1 packets are not the deterministic result of canonical inputs")
    packet_ids = [
        entry.get("study_unit_id")
        for document in actual.values() for entry in document.get("entries", [])
        if isinstance(entry, dict)
    ]
    tier1_ids = [
        entry.get("study_unit_id") for entry in _read(root, "global_review_tier1.json").get("entries", [])
        if isinstance(entry, dict)
    ]
    if set(packet_ids) != set(tier1_ids) or len(packet_ids) != len(set(packet_ids)):
        result.errors.append("packets must account for every Tier-1 study unit exactly once")
    if len(packet_ids) + summary["work_type_counts"]["OTHER"] != len(tier1_ids):
        result.errors.append("Tier-1 work-type counts do not reconcile")
    result.checks["deterministic_reconciliation"] = "PASS" if actual == expected else "FAIL"
    result.checks["accounting_and_isolation"] = "PASS" if not result.errors else "FAIL"
    result.status = "FAIL" if result.errors else "PASS"
    return result
