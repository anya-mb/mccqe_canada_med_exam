"""Deterministic structural validation for one completed scope chapter.

Checks JSON Schema conformance, source-node accounting, MCC evidence
referential integrity, and question-planning/lifecycle hygiene rules for
`research/scope/chapters/<CODE>/`. This module makes no medical judgment
about whether a mapping is semantically correct - that remains Claude or
human reviewer work.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import json

from .errors import QbankError, SchemaValidationError
from .jsonio import read_json
from .paths import resolve_root_path
from .schema import validate_instance
from .scope_packet import load_progress_ledger, load_toc_nodes, select_chapter_nodes


class ScopeValidationError(QbankError):
    """A scope-chapter validation run could not complete."""


_CANONICAL_FILES = ("study_units.json", "crosswalk.json")
_HOME_PATH_MARKERS = ("/Users/", "/home/", "C:\\Users\\")
_QUESTION_CONTENT_KEYS = frozenset({"stem", "options", "correct_answer", "answer_choices"})


@dataclass
class ValidationResult:
    chapter: str
    status: str
    checks: dict[str, str] = field(default_factory=dict)
    counts: dict[str, int] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "chapter": self.chapter,
            "status": self.status,
            "checks": self.checks,
            "counts": self.counts,
            "errors": self.errors,
            "warnings": self.warnings,
        }


def _read_object(root: Path, relative: Path | str, *, label: str) -> dict:
    path = resolve_root_path(root, relative, label=label)
    if not path.is_file():
        raise ScopeValidationError(f"required file is missing: {relative}")
    try:
        value = read_json(path)
    except QbankError as exc:
        raise ScopeValidationError(f"invalid JSON in {relative}: {exc}") from exc
    if not isinstance(value, dict):
        raise ScopeValidationError(f"{label} must be a JSON object: {relative}")
    return value


def _leak_scan(value: object, path_hint: str, hits: list[str]) -> None:
    if isinstance(value, str):
        for marker in _HOME_PATH_MARKERS:
            if marker in value:
                hits.append(f"{path_hint}: absolute/private path leak ({marker.strip('/')})")
    elif isinstance(value, dict):
        for key, child in value.items():
            if key in _QUESTION_CONTENT_KEYS:
                hits.append(f"{path_hint}.{key}: generated question content field present")
            _leak_scan(child, f"{path_hint}.{key}", hits)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _leak_scan(child, f"{path_hint}[{index}]", hits)


def validate_scope_chapter(root: Path, chapter_code: str) -> ValidationResult:
    result = ValidationResult(chapter=chapter_code, status="PASS")

    ledger = load_progress_ledger(root)
    names = ledger.get("chapter_names", {})
    if chapter_code not in names:
        result.status = "FAIL"
        result.checks["source_accounting"] = "FAIL"
        result.errors.append(f"unknown chapter code (not in progress ledger): {chapter_code}")
        return result

    chapter_dir = Path("research/scope/chapters") / chapter_code
    try:
        directory = resolve_root_path(root, chapter_dir, label="chapter output directory")
    except QbankError as exc:
        result.status = "FAIL"
        result.errors.append(str(exc))
        return result
    if not directory.is_dir():
        result.status = "FAIL"
        result.errors.append(f"chapter output directory does not exist: {chapter_dir}")
        return result

    errors: list[str] = []
    warnings: list[str] = []
    checks: dict[str, str] = {}

    # --- schema: JSON parses + canonical files present ---
    study_units_doc = None
    crosswalk_doc = None
    try:
        for name in _CANONICAL_FILES:
            _read_object(root, chapter_dir / name, label=name)
        study_units_doc = _read_object(root, chapter_dir / "study_units.json", label="study units")
        crosswalk_doc = _read_object(root, chapter_dir / "crosswalk.json", label="crosswalk")
        checks["schema"] = "PASS"
    except ScopeValidationError as exc:
        checks["schema"] = "FAIL"
        errors.append(str(exc))

    if study_units_doc is None or crosswalk_doc is None:
        result.status = "FAIL"
        result.checks = checks
        result.errors = errors
        return result

    if study_units_doc.get("chapter_code") != chapter_code:
        errors.append(
            f"study_units.json chapter_code {study_units_doc.get('chapter_code')!r} "
            f"does not match requested chapter {chapter_code!r}"
        )
    if crosswalk_doc.get("chapter_code") != chapter_code:
        errors.append(
            f"crosswalk.json chapter_code {crosswalk_doc.get('chapter_code')!r} "
            f"does not match requested chapter {chapter_code!r}"
        )

    study_units = study_units_doc.get("study_units")
    crosswalk_entries = crosswalk_doc.get("entries")
    if not isinstance(study_units, list):
        errors.append("study_units.json study_units must be a list")
        study_units = []
    if not isinstance(crosswalk_entries, list):
        errors.append("crosswalk.json entries must be a list")
        crosswalk_entries = []

    for index, unit in enumerate(study_units):
        try:
            validate_instance(root, "study-unit", unit)
        except SchemaValidationError as exc:
            checks["schema"] = "FAIL"
            errors.append(f"study_units[{index}]: {exc}")

    for index, entry in enumerate(crosswalk_entries):
        try:
            validate_instance(root, "crosswalk-entry", entry)
        except SchemaValidationError as exc:
            checks["schema"] = "FAIL"
            errors.append(f"crosswalk[{index}]: {exc}")

    checks.setdefault("schema", "PASS")

    # --- source accounting ---
    all_nodes = load_toc_nodes(root)
    try:
        chapter_nodes = select_chapter_nodes(all_nodes, chapter_code)
    except QbankError as exc:
        chapter_nodes = []
        errors.append(str(exc))
    chapter_node_ids = {n.get("node_id") for n in chapter_nodes if isinstance(n, dict)}

    accounted: set[str] = set()
    accounted |= set(study_units_doc.get("organizational_header_nodes") or {})
    accounted |= set(study_units_doc.get("excluded_artifact_nodes") or {})

    study_unit_ids: list[str] = []
    seen_unit_ids: set[str] = set()
    cross_chapter_leak = False
    for index, unit in enumerate(study_units):
        if not isinstance(unit, dict):
            continue
        unit_id = unit.get("study_unit_id")
        if isinstance(unit_id, str):
            if unit_id in seen_unit_ids:
                errors.append(f"duplicate study_unit_id: {unit_id}")
            seen_unit_ids.add(unit_id)
            study_unit_ids.append(unit_id)
        for source_node_id in unit.get("source_node_ids") or []:
            accounted.add(source_node_id)
            if isinstance(source_node_id, str) and source_node_id.startswith("UNCATALOGUED:"):
                # Documented convention: a heading with no toc_inventory.json
                # node gets a synthetic id, recorded in
                # unresolved_heading_resolution / structural_rationale.
                continue
            if source_node_id not in chapter_node_ids:
                cross_chapter_leak = True
                errors.append(
                    f"study_units[{index}] ({unit_id}) references source_node_id "
                    f"{source_node_id!r} outside chapter {chapter_code}"
                )

    unaccounted = sorted(chapter_node_ids - accounted)
    if unaccounted:
        errors.append(f"unaccounted source nodes for chapter {chapter_code}: {unaccounted}")

    # crosswalk <-> study unit referential integrity
    crosswalk_unit_ids: list[str] = []
    seen_crosswalk_ids: set[str] = set()
    for index, entry in enumerate(crosswalk_entries):
        if not isinstance(entry, dict):
            continue
        unit_id = entry.get("study_unit_id")
        if isinstance(unit_id, str):
            if unit_id in seen_crosswalk_ids:
                errors.append(f"duplicate crosswalk study_unit_id: {unit_id}")
            seen_crosswalk_ids.add(unit_id)
            crosswalk_unit_ids.append(unit_id)
            if unit_id not in seen_unit_ids:
                errors.append(
                    f"crosswalk[{index}] references unknown study_unit_id: {unit_id}"
                )

    orphan_units = sorted(set(study_unit_ids) - seen_crosswalk_ids)
    if orphan_units:
        errors.append(f"study units with no crosswalk classification entry: {orphan_units}")

    checks["source_accounting"] = "FAIL" if (unaccounted or cross_chapter_leak or orphan_units) else "PASS"

    # --- MCC evidence referential integrity ---
    objectives_doc = _read_object(
        root, "research/mcc/objectives_registry.json", label="objectives registry"
    )
    objectives = objectives_doc.get("objectives") or []
    objectives_by_id = {o.get("mcc_id"): o for o in objectives if isinstance(o, dict)}

    weak_count = 0
    uncertain_count = 0
    strong_evidence_count = 0
    moderate_evidence_count = 0
    weak_evidence_count = 0
    mcc_ids_ok = True
    for index, entry in enumerate(crosswalk_entries):
        if not isinstance(entry, dict):
            continue
        if entry.get("classification") == "WEAK" or any(
            ev.get("mapping_strength") == "WEAK" for ev in entry.get("mcc_evidence") or [] if isinstance(ev, dict)
        ):
            weak_count += 1
        if entry.get("classification") == "UNCERTAIN":
            uncertain_count += 1
        for ev in entry.get("mcc_evidence") or []:
            if not isinstance(ev, dict):
                continue
            strength = ev.get("mapping_strength")
            if strength == "STRONG":
                strong_evidence_count += 1
            elif strength == "MODERATE":
                moderate_evidence_count += 1
            elif strength == "WEAK":
                weak_evidence_count += 1
        for ev_index, evidence in enumerate(entry.get("mcc_evidence") or []):
            if not isinstance(evidence, dict):
                continue
            if evidence.get("evidence_type") != "OBJECTIVE_REFERENCE":
                continue
            mcc_id = evidence.get("mcc_id")
            objective = objectives_by_id.get(mcc_id)
            if objective is None:
                mcc_ids_ok = False
                errors.append(
                    f"crosswalk[{index}].mcc_evidence[{ev_index}]: unknown mcc_id {mcc_id!r} "
                    "not present in objectives_registry.json"
                )
                continue
            legacy_id = evidence.get("legacy_id")
            if legacy_id is not None and legacy_id != objective.get("legacy_id"):
                mcc_ids_ok = False
                errors.append(
                    f"crosswalk[{index}].mcc_evidence[{ev_index}]: legacy_id {legacy_id!r} "
                    f"does not match registry legacy_id {objective.get('legacy_id')!r} for mcc_id {mcc_id!r}"
                )
            title = evidence.get("objective_title")
            if title and title != objective.get("title"):
                warnings.append(
                    f"crosswalk[{index}].mcc_evidence[{ev_index}]: objective_title {title!r} "
                    f"differs from current registry title {objective.get('title')!r} for mcc_id {mcc_id!r}"
                )

    checks["mcc_ids"] = "PASS" if mcc_ids_ok else "FAIL"

    # --- mapping/classification hygiene (schema semantic checks already ran above) ---
    checks["mapping_hygiene"] = "FAIL" if any("mcc_evidence" in e or "classification" in e for e in errors) else "PASS"

    # --- question planning: obsolete field check ---
    target_questions_hits: list[str] = []
    _scan_for_key(crosswalk_entries, "target_questions", "crosswalk.entries", target_questions_hits)
    _scan_for_key(study_units, "target_questions", "study_units.study_units", target_questions_hits)
    if target_questions_hits:
        errors.extend(target_questions_hits)
    checks["question_planning"] = "FAIL" if target_questions_hits else "PASS"

    # --- jurisdiction/freshness: covered structurally by crosswalk-entry schema ---
    checks["jurisdiction"] = "PASS" if checks["schema"] == "PASS" else "FAIL"

    # --- freshness/precision warnings ---
    for unit in study_units:
        if isinstance(unit, dict) and unit.get("page_mapping_precision") == "SECTION_INHERITED":
            warnings.append(
                f"{unit.get('study_unit_id')}: SECTION_INHERITED page precision (legal, flagged for awareness)"
            )
    for entry in crosswalk_entries:
        if isinstance(entry, dict) and entry.get("classification") == "UNCERTAIN":
            warnings.append(f"{entry.get('study_unit_id')}: UNCERTAIN classification (legal state)")

    # --- safety ---
    leak_hits: list[str] = []
    _leak_scan(study_units_doc, "study_units.json", leak_hits)
    _leak_scan(crosswalk_doc, "crosswalk.json", leak_hits)
    if leak_hits:
        errors.extend(leak_hits)
    checks["safety"] = "FAIL" if leak_hits else "PASS"

    for entry in crosswalk_entries:
        if not isinstance(entry, dict):
            continue
        for evidence in entry.get("mcc_evidence") or []:
            if not isinstance(evidence, dict):
                continue
            rationale = evidence.get("mapping_rationale") or ""
            if isinstance(rationale, str) and len(rationale) > 1500:
                warnings.append(
                    f"{entry.get('study_unit_id')}: unusually long mapping_rationale "
                    f"({len(rationale)} chars) - verify it is not a source-text dump"
                )

    result.checks = checks
    result.errors = errors
    result.warnings = warnings
    result.counts = {
        "source_nodes": len(chapter_node_ids),
        "study_units": len(study_units),
        "weak_mappings": weak_count,
        "uncertain": uncertain_count,
        "strong_evidence": strong_evidence_count,
        "moderate_evidence": moderate_evidence_count,
        "weak_evidence": weak_evidence_count,
    }
    result.status = "FAIL" if errors else "PASS"
    return result


def _scan_for_key(value: object, key: str, path_hint: str, hits: list[str]) -> None:
    if isinstance(value, dict):
        if key in value:
            hits.append(f"{path_hint}: obsolete field {key!r} present")
        for child_key, child in value.items():
            _scan_for_key(child, key, f"{path_hint}.{child_key}", hits)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _scan_for_key(child, key, f"{path_hint}[{index}]", hits)


def report_output_path(root: Path, chapter_code: str) -> Path:
    return resolve_root_path(
        root,
        Path("reports/chapter_validation") / f"{chapter_code}.json",
        label="chapter validation report output",
    )
