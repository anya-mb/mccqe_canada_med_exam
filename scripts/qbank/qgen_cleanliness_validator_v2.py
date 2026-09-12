"""Independent defense-in-depth validation for a selected clean cohort."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from .qgen_exposure_registry import AMBIGUOUS_LEVEL, canonical_content_hash


def _ids(value: Any) -> set[str]:
    found: set[str] = set()
    if isinstance(value, Mapping):
        for key, child in value.items():
            if key == "study_unit_id" and isinstance(child, str):
                found.add(child)
            else:
                found.update(_ids(child))
    elif isinstance(value, list):
        for child in value:
            found.update(_ids(child))
    return found


def _independent_level(document: Mapping[str, Any]) -> int:
    identity = f"{document.get('schema_version', '')} {document.get('scope', '')}".upper()
    if any(token in identity for token in (
        "ELIGIBLE_INVENTORY", "QUESTION_GENERATION_MANIFEST",
        "SOURCE_PACKET_PLAN", "FRESH_UNIVERSE_READINESS_INVENTORY",
    )):
        return 0
    if "FUTURE_UNTOUCHED_HOLDOUT_ELIGIBILITY" in identity or "NEXT_FRESH_HOLDOUT_ELIGIBILITY_ONLY" in identity:
        return 1
    if "SELECTION" in identity and (
        document.get("execution_status") == "FROZEN_NOT_RUN"
        or (document.get("candidate_retrieval_run") is False and document.get("cohort_run") is False)
    ):
        return 2
    unsafe_markers = (
        "PREREQUISITE", "OPPORTUNITY_SEMANTICS", "DISCOVERY", "RETRIEVAL",
        "RAW_SUPPLY", "CLINICAL_REVIEW", "INDEPENDENT_REVIEW", "CANDIDATE_REVIEW",
        "EVIDENCE", "FEATURE_MAP", "FEATURE_ANCHOR", "QUESTION_SEED",
        "GENERATED", "STAGED", "BLIND_SOLVE", "LIVENESS", "FINAL_MEDICAL_REVIEW",
        "ANCHOR_CANDIDATE_UNIVERSE", "FRESH_HOLDOUT", "FRESH_OPERATIONAL_HOLDOUT",
        "CROSS_DISCIPLINE_GENERALIZATION", "DEVELOPMENT",
    )
    if any(marker in identity for marker in unsafe_markers):
        return 3
    return AMBIGUOUS_LEVEL


def _historical_paths(root: Path) -> list[Path]:
    paths = []
    research = root / "research/qgen"
    if research.exists():
        paths.extend(path for path in research.rglob("*.json") if "research/qgen/exposure" not in path.as_posix())
    reports = root / "reports"
    if reports.exists():
        paths.extend(reports.glob("qgen*.json"))
    return sorted({path.resolve() for path in paths})


def validate_clean_cohort(
    root: Path, cohort: Mapping[str, Any], reserved_registry: Mapping[str, Any]
) -> dict[str, Any]:
    root = Path(root).resolve()
    selected = {row["study_unit_id"] for row in cohort.get("rows", [])}
    registry_by_id = {row["study_unit_id"]: row for row in reserved_registry.get("rows", [])}
    registry_failures = []
    for study_unit_id in sorted(selected):
        row = registry_by_id.get(study_unit_id)
        reasons = []
        if row is None:
            reasons.append("MISSING_REGISTRY_ROW")
        else:
            if row.get("clean_transfer_eligible") is not True:
                reasons.append("NOT_CLEAN_ELIGIBLE")
            if row.get("max_exposure_level", AMBIGUOUS_LEVEL) >= 3:
                reasons.append("LEVEL_3_PLUS_OR_AMBIGUOUS")
            if row.get("reservation_status") != "RESERVED_FOR_CLEAN_VALIDATION":
                reasons.append("NOT_RESERVED_FOR_THIS_VALIDATION")
            if any(row.get(field) for field in (
                "used_for_architecture", "ever_candidate_inspected",
                "ever_evidence_authored", "ever_question_generated",
            )):
                reasons.append("MATERIAL_EXPOSURE_FLAG")
        if reasons:
            registry_failures.append({"study_unit_id": study_unit_id, "reasons": reasons})

    direct_overlap = []
    overlap_ids: set[str] = set()
    for path in _historical_paths(root):
        try:
            document = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        matched = sorted(selected & _ids(document))
        if not matched:
            continue
        level = _independent_level(document)
        if level >= 3:
            overlap_ids.update(matched)
            direct_overlap.append({
                "artifact_path": path.relative_to(root).as_posix(),
                "artifact_file_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "independent_exposure_level": level,
                "study_unit_ids": matched,
            })
    all_failed = overlap_ids | {row["study_unit_id"] for row in registry_failures}
    result: dict[str, Any] = {
        "schema_version": "QGEN_CLEAN_COHORT_INDEPENDENT_CLEANLINESS_PROOF_V2",
        "cohort_sha256": cohort.get("content_sha256"),
        "reserved_registry_sha256": reserved_registry.get("content_sha256"),
        "cohort_size": len(selected),
        "registry_failures": registry_failures,
        "direct_historical_overlap": direct_overlap,
        "overlapping_study_unit_ids": sorted(all_failed),
        "clean_cohort_overlaps": len(all_failed),
        "verdict": "PASS" if not all_failed else "FAIL",
    }
    result["content_sha256"] = canonical_content_hash(result)
    return result
