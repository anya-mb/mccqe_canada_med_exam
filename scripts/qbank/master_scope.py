"""Deterministic aggregation and validation of canonical chapter scope files."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from hashlib import sha256
from pathlib import Path
import re
from typing import Any

from jsonschema import Draft202012Validator

from .errors import QbankError
from .jsonio import read_json, write_json_atomic
from .paths import resolve_root_path
from .schema import crosswalk_entry_semantic_errors
from .scope_packet import load_progress_ledger


_CLASSIFICATIONS = (
    "DIRECT", "COMPONENT", "SUPPORTING_KNOWLEDGE", "SPECIALIST_DETAIL",
    "REFERENCE_ONLY", "CROSS_DISCIPLINE", "UNCERTAIN",
)
_DEPTHS = frozenset({"CORE_ACTION", "RECOGNIZE_AND_ACT", "RECOGNIZE", "CONTEXT_ONLY", "OUT_OF_SCOPE_DETAIL"})
_STRENGTHS = ("STRONG", "MODERATE", "WEAK")
_EVIDENCE_TYPES = frozenset({"OBJECTIVE_REFERENCE", "ROLE_LEVEL_REFERENCE"})
_CROSSWALK_FIELDS = frozenset({
    "scope_schema_version", "study_unit_id", "title", "classification", "mcc_evidence",
    "scope_depth", "testable_competencies", "do_not_test", "jurisdiction",
    "question_planning", "page_mapping_precision", "clinical_source_organizations",
    "freshness", "zero_question_reason", "cross_discipline_note",
    "mcc_evidence_retention_reason", "uncertain_reason",
})
_OUTPUT_NAMES = (
    "master_scope_crosswalk.json", "master_scope_report.json",
    "global_review_candidates.json", "global_ownership_candidates.json",
    "mcc_objective_coverage.json",
)
_UNIT_ID_PATTERN = re.compile(r"\bSU-[A-Z]+-\d{2,3}\b")


class MasterScopeError(QbankError):
    """Master-scope aggregation or validation cannot safely complete."""


@dataclass
class MasterValidationResult:
    status: str
    checks: dict[str, str] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"status": self.status, "checks": self.checks, "errors": self.errors}


def output_paths(root: Path) -> dict[str, Path]:
    return {name: resolve_root_path(root, Path("research/scope") / name, label=name) for name in _OUTPUT_NAMES}


def _read_object(root: Path, relative: Path, label: str) -> dict[str, Any]:
    path = resolve_root_path(root, relative, label=label)
    if not path.is_file():
        raise MasterScopeError(f"required file is missing: {relative}")
    try:
        value = read_json(path)
    except QbankError as exc:
        raise MasterScopeError(f"invalid JSON in {relative}: {exc}") from exc
    if not isinstance(value, dict):
        raise MasterScopeError(f"{label} must be a JSON object: {relative}")
    return value


def _chapter_codes(root: Path) -> list[str]:
    ledger = load_progress_ledger(root)
    names = ledger.get("chapter_names")
    completed = ledger.get("completed_chapters")
    if not isinstance(names, dict) or not isinstance(completed, list):
        raise MasterScopeError("scope progress ledger lacks chapter_names or completed_chapters")
    codes = sorted(str(code) for code in completed)
    if len(codes) != 32 or len(set(codes)) != 32 or set(codes) != set(names):
        raise MasterScopeError("scope progress ledger does not represent exactly the expected 32 completed chapters")
    return codes


def _extract_unit_ids(value: object) -> set[str]:
    found: set[str] = set()
    if isinstance(value, dict):
        for key, child in value.items():
            if key == "study_unit_id" and isinstance(child, str):
                found.add(child)
            found |= _extract_unit_ids(child)
    elif isinstance(value, list):
        for child in value:
            found |= _extract_unit_ids(child)
    elif isinstance(value, str):
        found.update(_UNIT_ID_PATTERN.findall(value))
    return found


def _normalized_title(value: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9]+", " ", value.lower()).split())


def _join_chapter(root: Path, code: str) -> tuple[list[dict[str, Any]], set[str]]:
    base = Path("research/scope/chapters") / code
    units_doc = _read_object(root, base / "study_units.json", "study units")
    crosswalk_doc = _read_object(root, base / "crosswalk.json", "crosswalk")
    units = units_doc.get("study_units")
    crosswalk = crosswalk_doc.get("entries")
    if not isinstance(units, list) or not isinstance(crosswalk, list):
        raise MasterScopeError(f"{code}: canonical study units/crosswalk entries must be arrays")
    by_id: dict[str, dict[str, Any]] = {}
    for unit in units:
        if not isinstance(unit, dict) or not isinstance(unit.get("study_unit_id"), str):
            raise MasterScopeError(f"{code}: invalid study unit record")
        unit_id = unit["study_unit_id"]
        if unit_id in by_id:
            raise MasterScopeError(f"{code}: duplicate study_unit_id in study_units.json: {unit_id}")
        by_id[unit_id] = unit
    entries: list[dict[str, Any]] = []
    seen: set[str] = set()
    for entry in crosswalk:
        if not isinstance(entry, dict) or not isinstance(entry.get("study_unit_id"), str):
            raise MasterScopeError(f"{code}: invalid crosswalk record")
        unit_id = entry["study_unit_id"]
        if unit_id in seen:
            raise MasterScopeError(f"{code}: duplicate crosswalk study_unit_id: {unit_id}")
        seen.add(unit_id)
        unit = by_id.get(unit_id)
        if unit is None:
            raise MasterScopeError(f"{code}: crosswalk references unknown study_unit_id: {unit_id}")
        for key in ("scope_schema_version", "study_unit_id"):
            if entry.get(key) != unit.get(key):
                raise MasterScopeError(f"{code}: {unit_id} differs between study unit and crosswalk for {key}")
        merged = dict(unit)
        # The two canonical artifacts intentionally retain their own titles;
        # keep both rather than selecting or rewriting clinical wording.
        merged["study_unit_title"] = unit["title"]
        merged["study_unit_page_mapping_precision"] = unit["page_mapping_precision"]
        merged.update(entry)
        entries.append(merged)
    missing = sorted(set(by_id) - seen)
    if missing:
        raise MasterScopeError(f"{code}: study units without crosswalk entries: {missing}")
    unresolved: set[str] = set()
    for name in ("review_items.json", "unresolved_mappings.json"):
        path = resolve_root_path(root, base / name, label=name)
        if path.is_file():
            unresolved |= _extract_unit_ids(read_json(path))
    return entries, unresolved


def _report(entries: list[dict[str, Any]], chapter_codes: list[str]) -> dict[str, Any]:
    classification_counts = Counter(entry["classification"] for entry in entries)
    evidence_counts = Counter(
        evidence["mapping_strength"]
        for entry in entries for evidence in entry["mcc_evidence"]
    )
    any_weak = sum(any(ev["mapping_strength"] == "WEAK" for ev in entry["mcc_evidence"]) for entry in entries)
    only_weak = sum(
        any(ev["mapping_strength"] == "WEAK" for ev in entry["mcc_evidence"])
        and not any(ev["mapping_strength"] in {"STRONG", "MODERATE"} for ev in entry["mcc_evidence"])
        for entry in entries
    )
    return {
        "schema_version": "1.0",
        "total_chapters": len(chapter_codes),
        "total_study_units": len(entries),
        "classification_counts": {key: classification_counts[key] for key in _CLASSIFICATIONS},
        "mcc_evidence_references": {key: evidence_counts[key] for key in _STRENGTHS},
        "study_units_with_any_weak_evidence": any_weak,
        "study_units_with_only_weak_evidence": only_weak,
        "requires_scope_review_count": sum(
            any(ev.get("requires_scope_review") is True for ev in entry["mcc_evidence"])
            for entry in entries
        ),
        "role_level_reference_count": sum(
            ev["evidence_type"] == "ROLE_LEVEL_REFERENCE"
            for entry in entries for ev in entry["mcc_evidence"]
        ),
    }


def _review_candidates(entries: list[dict[str, Any]], unresolved: set[str]) -> dict[str, Any]:
    candidates = []
    for entry in entries:
        reasons: list[str] = []
        evidence = entry["mcc_evidence"]
        if entry["classification"] == "UNCERTAIN": reasons.append("UNCERTAIN")
        if any(ev["mapping_strength"] == "WEAK" for ev in evidence) and not any(ev["mapping_strength"] in {"STRONG", "MODERATE"} for ev in evidence): reasons.append("ONLY_WEAK_EVIDENCE")
        if any(ev.get("requires_scope_review") is True for ev in evidence): reasons.append("REQUIRES_SCOPE_REVIEW")
        if entry["classification"] == "CROSS_DISCIPLINE": reasons.append("CROSS_DISCIPLINE_CLASSIFICATION")
        if entry["study_unit_id"] in unresolved: reasons.append("UNRESOLVED_CHAPTER_REVIEW_ITEM")
        if entry.get("cross_discipline_note"): reasons.append("EXPLICIT_CROSS_DISCIPLINE_NOTE")
        jurisdiction = entry.get("jurisdiction")
        if (isinstance(jurisdiction, dict) and jurisdiction.get("scope") == "UNRESOLVED") or entry.get("page_mapping_precision") == "UNRESOLVED": reasons.append("UNRESOLVED_JURISDICTION_OR_SOURCE")
        if reasons:
            candidates.append({"study_unit_id": entry["study_unit_id"], "chapter_code": entry["chapter_code"], "title": entry["title"], "reason_codes": reasons})
    return {"schema_version": "1.0", "total_candidates": len(candidates), "candidates": candidates}


def _ownership_candidates(entries: list[dict[str, Any]]) -> dict[str, Any]:
    groups: list[dict[str, Any]] = []
    by_title: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for entry in entries: by_title[_normalized_title(entry["title"])].append(entry)
    for title, members in sorted(by_title.items()):
        if len({entry["chapter_code"] for entry in members}) > 1:
            groups.append({"signal": "IDENTICAL_NORMALIZED_TITLE", "normalized_title": title, "study_unit_ids": sorted(entry["study_unit_id"] for entry in members)})
    ids = {entry["study_unit_id"] for entry in entries}
    for entry in entries:
        note = entry.get("cross_discipline_note")
        linked = sorted((_extract_unit_ids(note) & ids) - {entry["study_unit_id"]}) if isinstance(note, str) else []
        if linked:
            groups.append({"signal": "EXPLICIT_CROSS_DISCIPLINE_NOTE_LINK", "study_unit_ids": sorted([entry["study_unit_id"], *linked])})
        elif entry["classification"] == "CROSS_DISCIPLINE":
            groups.append({"signal": "CROSS_DISCIPLINE_CLASSIFICATION", "study_unit_ids": [entry["study_unit_id"]]})
    for group in groups:
        payload = "|".join([group["signal"], *group["study_unit_ids"]])
        group["candidate_group_id"] = f"GOC-{sha256(payload.encode()).hexdigest()[:12]}"
    groups.sort(key=lambda item: (item["signal"], item["study_unit_ids"], item["candidate_group_id"]))
    return {"schema_version": "1.0", "assignment_status": "CANDIDATE_GROUPING_ONLY", "total_candidate_groups": len(groups), "groups": groups}


def _objective_coverage(root: Path, entries: list[dict[str, Any]]) -> dict[str, Any]:
    registry = _read_object(root, Path("research/mcc/objectives_registry.json"), "objectives registry")
    objectives = registry.get("objectives")
    if not isinstance(objectives, list): raise MasterScopeError("objectives registry objectives must be an array")
    mapped: dict[str, list[tuple[dict[str, Any], dict[str, Any]]]] = defaultdict(list)
    for entry in entries:
        for evidence in entry["mcc_evidence"]:
            if evidence["evidence_type"] == "OBJECTIVE_REFERENCE": mapped[evidence["mcc_id"]].append((entry, evidence))
    rank = {"WEAK": 1, "MODERATE": 2, "STRONG": 3}
    output = []
    for objective in sorted(objectives, key=lambda value: (str(value.get("role")), str(value.get("mcc_id")))):
        if not isinstance(objective, dict) or not (isinstance(objective.get("mcc_id"), str) or objective.get("mcc_id") is None): raise MasterScopeError("objectives registry contains invalid objective record")
        objective_id = objective["mcc_id"]
        refs = mapped.get(objective_id, []) if objective_id is not None else []
        types = sorted({evidence["evidence_type"] for _, evidence in refs})
        output.append({"objective_id": objective_id, "mapped_study_unit_count": len({entry["study_unit_id"] for entry, _ in refs}), "chapters_represented": sorted({entry["chapter_code"] for entry, _ in refs}), "strongest_evidence_strength": max((evidence["mapping_strength"] for _, evidence in refs), key=lambda value: rank[value], default=None), "evidence_types": types, "status": "MAPPED" if refs else "UNMAPPED_OBJECTIVE_CANDIDATE"})
    return {"schema_version": "1.0", "total_objectives": len(output), "mapped_objectives": sum(item["status"] == "MAPPED" for item in output), "unmapped_objective_candidates": sum(item["status"] == "UNMAPPED_OBJECTIVE_CANDIDATE" for item in output), "objectives": output}


def _aggregate(root: Path) -> dict[str, dict[str, Any]]:
    codes = _chapter_codes(root)
    entries: list[dict[str, Any]] = []
    unresolved: set[str] = set()
    for code in codes:
        chapter_entries, chapter_unresolved = _join_chapter(root, code)
        entries.extend(chapter_entries); unresolved |= chapter_unresolved
    entries.sort(key=lambda entry: entry["study_unit_id"])
    if len({entry["study_unit_id"] for entry in entries}) != len(entries):
        raise MasterScopeError("duplicate study_unit_id across canonical chapter crosswalks")
    master = {"schema_version": "1.0", "total_chapters": len(codes), "total_study_units": len(entries), "chapter_codes": codes, "entries": entries}
    return {"master_scope_crosswalk.json": master, "master_scope_report.json": _report(entries, codes), "global_review_candidates.json": _review_candidates(entries, unresolved), "global_ownership_candidates.json": _ownership_candidates(entries), "mcc_objective_coverage.json": _objective_coverage(root, entries)}


def build_master_scope(root: Path) -> dict[str, Any]:
    documents = _aggregate(root)
    for name, value in documents.items(): write_json_atomic(output_paths(root)[name], value)
    return documents["master_scope_report.json"]


def validate_master_scope(root: Path) -> MasterValidationResult:
    result = MasterValidationResult(status="PASS")
    try:
        expected = _aggregate(root)
    except QbankError as exc:
        return MasterValidationResult(status="FAIL", checks={"canonical_inputs": "FAIL"}, errors=[str(exc)])
    actual: dict[str, dict[str, Any]] = {}
    for name, path in output_paths(root).items():
        try: actual[name] = _read_object(root, path.relative_to(root), name)
        except MasterScopeError as exc: result.errors.append(str(exc))
    if result.errors:
        result.status = "FAIL"; result.checks["outputs_present"] = "FAIL"; return result
    master = actual["master_scope_crosswalk.json"]
    entries = master.get("entries")
    if not isinstance(entries, list): result.errors.append("master entries must be an array"); entries = []
    ids = [entry.get("study_unit_id") for entry in entries if isinstance(entry, dict)]
    if len(ids) != len(set(ids)): result.errors.append("duplicate study_unit_id in master scope crosswalk")
    registry = _read_object(root, Path("research/mcc/objectives_registry.json"), "objectives registry")
    valid_ids = {item.get("mcc_id") for item in registry.get("objectives", []) if isinstance(item, dict)}
    schema = _read_object(root, Path("schemas/crosswalk-entry.schema.json"), "crosswalk entry schema")
    schema_validator = Draft202012Validator(schema)
    for entry in entries:
        if not isinstance(entry, dict): result.errors.append("master entry must be an object"); continue
        crosswalk_entry = {key: value for key, value in entry.items() if key in _CROSSWALK_FIELDS}
        schema_errors = sorted(schema_validator.iter_errors(crosswalk_entry), key=lambda error: list(error.path))
        if schema_errors:
            result.errors.append(f"{entry.get('study_unit_id')}: crosswalk schema validation failed: {schema_errors[0].message}")
        semantic_errors = crosswalk_entry_semantic_errors(crosswalk_entry)
        if semantic_errors:
            result.errors.append(f"{entry.get('study_unit_id')}: crosswalk semantic validation failed: {semantic_errors[0][1]}")
        if entry.get("classification") not in _CLASSIFICATIONS: result.errors.append(f"invalid classification: {entry.get('classification')!r}")
        if entry.get("scope_depth") not in _DEPTHS: result.errors.append(f"invalid scope_depth: {entry.get('scope_depth')!r}")
        for evidence in entry.get("mcc_evidence", []):
            if not isinstance(evidence, dict): result.errors.append(f"{entry.get('study_unit_id')}: invalid evidence record"); continue
            if evidence.get("mapping_strength") not in _STRENGTHS: result.errors.append(f"{entry.get('study_unit_id')}: invalid evidence strength")
            if evidence.get("evidence_type") not in _EVIDENCE_TYPES: result.errors.append(f"{entry.get('study_unit_id')}: invalid evidence type")
            if evidence.get("evidence_type") == "OBJECTIVE_REFERENCE" and evidence.get("mcc_id") not in valid_ids: result.errors.append(f"{entry.get('study_unit_id')}: unknown mcc_id {evidence.get('mcc_id')!r}")
    result.checks["master_structure_and_evidence"] = "PASS" if not result.errors else "FAIL"
    for name, expected_value in expected.items():
        if actual[name] != expected_value: result.errors.append(f"{name} is not the deterministic aggregation of canonical chapter inputs")
    result.checks["reconciliation_and_determinism"] = "PASS" if all(actual[name] == value for name, value in expected.items()) else "FAIL"
    result.status = "FAIL" if result.errors else "PASS"
    return result
