"""Deterministic QGEN study-unit exposure accounting.

Exposure is classified from an artifact's declared contract and content, never
from its filename. Unknown contracts fail closed so that a future artifact
cannot silently leak into a clean validation cohort.
"""

from __future__ import annotations

from dataclasses import dataclass
from collections import Counter
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Mapping


AMBIGUOUS_LEVEL = 99

LEVEL_STATUS = {
    0: "INVENTORY_ONLY",
    1: "METADATA_ONLY",
    2: "RESERVED_NOT_INSPECTED",
    3: "PREREQUISITE_SEMANTICS_REVIEWED",
    4: "CANDIDATE_SUPPLY_INSPECTED",
    5: "CLINICAL_CANDIDATE_REVIEWED",
    6: "EVIDENCE_AUTHORED_OR_REVIEWED",
    7: "QUESTION_GENERATED_OR_REVIEWED",
    8: "OUTCOME_USED_FOR_ARCHITECTURE",
    AMBIGUOUS_LEVEL: "AMBIGUOUS",
}


@dataclass(frozen=True)
class ArtifactClassification:
    level: int
    status: str
    reason: str

    @property
    def clean_transfer_eligible(self) -> bool:
        return self.level in {0, 1, 2}


def _classification(level: int, reason: str) -> ArtifactClassification:
    return ArtifactClassification(level, LEVEL_STATUS[level], reason)


def classify_artifact(path: str, document: Mapping[str, Any]) -> ArtifactClassification:
    """Classify declared artifact semantics; ``path`` is provenance only."""
    del path
    schema = str(document.get("schema_version") or "").upper()
    scope = str(document.get("scope") or "").upper()
    identity = f"{schema} {scope}"

    if any(token in identity for token in (
        "NORMALIZED_ATOMIC_OPPORTUNITY_BENCHMARK",
        "BENCHMARK_MATCHER_V3_HELDOUT_VALIDATION",
        "V1_V2_PARTIAL_MATCH_FORENSICS",
    )):
        return _classification(8, "reviewed semantic outcome used for matcher architecture or a stop gate")
    if any(token in identity for token in (
        "V1_BENCHMARK_COMPARISON",
        "V2_BENCHMARK_COMPARISON_INITIAL",
        "V2_BENCHMARK_COMPARISON_FINAL",
    )):
        return _classification(8, "independent benchmark outcome used for the registry architecture or production gate")
    if any(token in identity for token in (
        "REGISTRY_V2_SEMANTIC_REVIEW_EXPOSURE",
        "INDEPENDENT_OPPORTUNITY_BENCHMARK",
        "REGISTRY_V1_BLIND_SUITABILITY_BLUEPRINT_FAMILY_AUDIT",
        "REGISTRY_V1_SEMANTIC_DUPLICATE_STRESS_TEST",
        "INDEPENDENT_PARTIAL_MATCH_SEMANTIC_REVIEW",
        "INDEPENDENT_BENCHMARK_GRANULARITY_SEMANTIC_REVIEW",
        "MATCHER_V3_INDEPENDENT_GOLD_RELATION_SET",
        "ATOMIC_OPPORTUNITY_SEMANTIC_REVIEW_EXPOSURE",
    )):
        return _classification(3, "unit-specific opportunity semantics reviewed without candidate inspection")
    if any(token in identity for token in (
        "REGISTRY_V2_FINAL_SEMANTIC_ADJUDICATION_INPUT",
        "INDEPENDENT_COMPLETENESS_BENCHMARK_BLIND_INPUT",
        "FROZEN_INDEPENDENT_BENCHMARK_REVIEW_INPUT",
        "BLIND_SUITABILITY_BLUEPRINT_FAMILY_AUDIT_SAMPLE",
        "SEMANTIC_DUPLICATE_BLIND_STRESS_SAMPLE",
        "V1_PARTIAL_MATCH_BLINDED_FORENSIC_SAMPLE",
        "BLINDED_BENCHMARK_GRANULARITY_SAMPLE",
        "INDEPENDENT_BENCHMARK_GRANULARITY_AUDIT",
        "MATCHER_V3_GOLD_RELATION_BLINDED_REVIEW_INPUT",
    )):
        return _classification(1, "deterministic curriculum decision metadata prepared for blinded review")
    if "COMPLETENESS_BENCHMARK_ROSTER" in identity:
        return _classification(2, "development benchmark roster frozen before semantic review")

    # Curriculum-wide planning artifacts restate already-frozen scope metadata;
    # their presence is not evidence that candidates, clinical evidence, items,
    # or outcomes were inspected. The separate count-blind opportunity review is
    # unit-specific semantic inspection and is therefore level 3, not a candidate
    # clinical review (level 5).
    if "INDEPENDENT_OPPORTUNITY_REVIEW" in identity:
        return _classification(3, "unit-specific opportunity semantics reviewed without candidate inspection")
    if "CURRICULUM_QUESTION_OPPORTUNITY_REGISTRY" in identity:
        return _classification(1, "deterministic curriculum decision metadata derived from frozen scope")
    if any(token in identity for token in (
        "CURRICULUM_INPUT_SNAPSHOT",
        "CURRICULUM_OPPORTUNITY_COVERAGE_MATRIX",
        "QUESTION_BANK_ALLOCATION_PLAN",
        "QUESTION_SEED_POPULATION_PLAN",
        "QUESTION_IDENTITY_GRAPH",
        "PRODUCTION_QUEUE",
    )):
        return _classification(0, "broad deterministic curriculum planning metadata without QGEN outcome inspection")

    if any(token in identity for token in (
        "QUESTION_GENERATION_MANIFEST",
        "SOURCE_PACKET_PLAN",
        "FRESH_UNIVERSE_READINESS_INVENTORY",
    )):
        return _classification(0, "broad planning inventory without unit-specific QGEN outcome inspection")
    if "ELIGIBLE_INVENTORY" in identity:
        return _classification(0, "broad eligibility inventory without unit-specific semantic inspection")
    if "NEXT_FRESH_HOLDOUT_ELIGIBILITY_ONLY" in identity:
        if document.get("clinical_artifacts_inspected_for_selection") is False:
            return _classification(1, "holdout eligibility metadata with clinical artifacts affirmatively blinded")
    if "FUTURE_UNTOUCHED_HOLDOUT_ELIGIBILITY" in identity:
        if document.get("seed_availability_inspected") is False and document.get("contrast_supply_inspected") is False:
            return _classification(1, "eligibility metadata inspected with candidate and contrast supply blinded")
    if "SELECTION" in identity and (
        document.get("execution_status") == "FROZEN_NOT_RUN"
        or (
            document.get("candidate_retrieval_run") is False
            and document.get("cohort_run") is False
        )
    ):
        return _classification(2, "cohort reserved with affirmative no-run and no-retrieval evidence")
    if any(token in identity for token in (
        "ANCHOR_CANDIDATE_UNIVERSE",
        "FRESH_OPERATIONAL_HOLDOUT_18",
        "FRESH_HOLDOUT_18",
        "FRESH_HOLDOUT_24",
        "CROSS_DISCIPLINE_GENERALIZATION",
        "FEATURE_ANCHOR_SNAPSHOT",
        "READINESS_DEVELOPMENT",
        "QUESTION_SEED_V1",
    )):
        return _classification(8, "completed development or holdout outcomes informed the frozen QGEN architecture")
    if "MILESTONE" in identity and document.get("architecture_outcome"):
        return _classification(8, "observed unit outcomes explicitly used for an architecture decision")
    if "PREREQUISITE" in identity or "OPPORTUNITY_SEMANTICS" in identity or "DECISION_EVIDENCE_AUDIT" in identity:
        return _classification(3, "unit-specific learner-decision or prerequisite semantics recorded")
    if "CLINICAL_REVIEW" in identity or "INDEPENDENT_REVIEW" in identity or "CANDIDATE_REVIEW" in identity:
        return _classification(5, "candidate plausibility or clinical review recorded")
    if "DISCOVERY" in identity or "RETRIEVAL" in identity or "RAW_SUPPLY" in identity:
        return _classification(4, "candidate retrieval or supply observed")
    if "EVIDENCE" in identity or "FEATURE_MAP" in identity or "FEATURE_ANCHOR" in identity:
        return _classification(6, "unit-specific evidence or clinical feature content authored or reviewed")
    if any(token in identity for token in ("QUESTION_SEED_DEVELOPMENT_ITEMS", "GENERATED", "STAGED", "BLIND_SOLVE", "LIVENESS", "FINAL_MEDICAL_REVIEW")):
        return _classification(7, "question generation or review occurred")
    return _classification(AMBIGUOUS_LEVEL, "artifact contract does not prove a safe exposure interpretation")


def canonical_content_hash(value: Mapping[str, Any]) -> str:
    body = {key: item for key, item in value.items() if key != "content_sha256"}
    payload = json.dumps(body, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()


def _collect_study_unit_ids(value: Any) -> set[str]:
    found: set[str] = set()
    if isinstance(value, Mapping):
        for key, child in value.items():
            if key == "study_unit_id" and isinstance(child, str):
                found.add(child)
            else:
                found.update(_collect_study_unit_ids(child))
    elif isinstance(value, list):
        for child in value:
            found.update(_collect_study_unit_ids(child))
    return found


def _artifact_paths(root: Path) -> list[Path]:
    research = [
        path for path in (root / "research/qgen").rglob("*.json")
        if "research/qgen/exposure" not in path.as_posix()
    ]
    reports = list((root / "reports").glob("qgen*.json"))
    return sorted({path.resolve() for path in research + reports})


def _event_flags(level: int) -> dict[str, bool]:
    return {
        "clinical_semantics_inspected": 3 <= level <= 8,
        "candidates_inspected": 4 <= level <= 8,
        "evidence_authored": 6 <= level <= 8,
        "questions_generated": 7 <= level <= 8,
        "outcomes_influenced_architecture": level == 8,
    }


def build_registry(root: Path) -> dict[str, Any]:
    """Build the canonical registry from current historical QGEN artifacts."""
    root = Path(root).resolve()
    inventory_path = root / "research/qgen/holdout/eligible_fresh_study_units.json"
    inventory = json.loads(inventory_path.read_text())
    units_by_id: dict[str, dict[str, Any]] = {}
    for row in inventory["candidates"]:
        units_by_id.setdefault(str(row["study_unit_id"]), {
            "study_unit_id": row["study_unit_id"],
            "discipline": row["discipline"],
            "study_unit": row["study_unit"],
        })

    events: list[dict[str, Any]] = []
    artifact_inventory: list[dict[str, Any]] = []
    for path in _artifact_paths(root):
        try:
            document = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        unit_ids = sorted(_collect_study_unit_ids(document) & set(units_by_id))
        if not unit_ids:
            continue
        relative = path.relative_to(root).as_posix()
        file_hash = hashlib.sha256(path.read_bytes()).hexdigest()
        classification = classify_artifact(relative, document)
        milestone = str(document.get("scope") or document.get("schema_version") or "UNDECLARED")
        artifact_inventory.append({
            "artifact_path": relative,
            "artifact_content_sha256": file_hash,
            "milestone": milestone,
            "study_unit_count": len(unit_ids),
            "exposure_level": classification.level,
            "exposure_status": classification.status,
            "reason": classification.reason,
        })
        for study_unit_id in unit_ids:
            event_key = f"{relative}\0{file_hash}\0{study_unit_id}\0{classification.level}".encode()
            events.append({
                "event_id": f"QEE-{hashlib.sha256(event_key).hexdigest()[:16]}",
                "study_unit_id": study_unit_id,
                "artifact_path": relative,
                "artifact_content_sha256": file_hash,
                "milestone": milestone,
                "family": str(document.get("schema_version") or milestone),
                "event_type": classification.status,
                "exposure_level": classification.level,
                "exposure_status": classification.status,
                **_event_flags(classification.level),
                "confidence": "LOW" if classification.level == AMBIGUOUS_LEVEL else "HIGH",
                "reason": classification.reason,
            })
    events.sort(key=lambda row: (row["study_unit_id"], row["artifact_path"], row["event_id"]))
    rows = aggregate_registry(units_by_id.values(), events)
    counts = Counter(row["exposure_status"] for row in rows)
    result: dict[str, Any] = {
        "schema_version": "QGEN_EXPOSURE_REGISTRY_V1",
        "canonical_population": "QGEN_FRESH_HOLDOUT_ELIGIBLE_INVENTORY",
        "canonical_population_path": inventory_path.relative_to(root).as_posix(),
        "canonical_population_file_sha256": hashlib.sha256(inventory_path.read_bytes()).hexdigest(),
        "exposure_order": [LEVEL_STATUS[level] for level in range(9)],
        "unknown_exposure_policy": "FAIL_CLOSED",
        "artifact_inventory": artifact_inventory,
        "events": events,
        "rows": rows,
        "counts": {LEVEL_STATUS[level]: counts.get(LEVEL_STATUS[level], 0) for level in range(9)} | {"AMBIGUOUS": counts.get("AMBIGUOUS", 0)},
    }
    result["content_sha256"] = canonical_content_hash(result)
    return result


def aggregate_registry(
    canonical_units: Iterable[Mapping[str, Any]],
    events: Iterable[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Aggregate append-only events without discarding lower-level history."""
    by_unit: dict[str, list[Mapping[str, Any]]] = {}
    for event in events:
        by_unit.setdefault(str(event["study_unit_id"]), []).append(event)

    rows: list[dict[str, Any]] = []
    for unit in canonical_units:
        study_unit_id = str(unit["study_unit_id"])
        history = by_unit.get(study_unit_id, [])
        ordered = list(history)
        levels = [int(row["exposure_level"]) for row in ordered]
        ambiguous = AMBIGUOUS_LEVEL in levels
        verified_levels = [level for level in levels if level != AMBIGUOUS_LEVEL]
        verified_max = max(verified_levels, default=0)
        max_level = AMBIGUOUS_LEVEL if ambiguous and verified_max < 3 else verified_max
        milestones = [str(row["milestone"]) for row in ordered]
        eligible = not ambiguous and max_level <= 2
        rows.append({
            "study_unit_id": study_unit_id,
            "discipline": unit["discipline"],
            "study_unit": unit.get("study_unit") or unit.get("study_unit_title") or study_unit_id,
            "max_exposure_level": max_level,
            "exposure_status": LEVEL_STATUS[max_level],
            "source_event_ids": [str(row["event_id"]) for row in ordered],
            "first_exposure_milestone": milestones[0] if milestones else None,
            "most_recent_exposure_milestone": milestones[-1] if milestones else None,
            "used_for_architecture": any(bool(row.get("outcomes_influenced_architecture")) for row in ordered),
            "ever_candidate_inspected": any(bool(row.get("candidates_inspected")) for row in ordered),
            "ever_evidence_authored": any(bool(row.get("evidence_authored")) for row in ordered),
            "ever_question_generated": any(bool(row.get("questions_generated")) for row in ordered),
            "clean_transfer_eligible": eligible,
            "eligibility_reason": (
                "ELIGIBLE_INVENTORY_METADATA_OR_PROVEN_UNINSPECTED_RESERVATION"
                if eligible
                else "AMBIGUOUS_EXPOSURE_FAIL_CLOSED" if ambiguous
                else f"EXPOSED_AT_LEVEL_{max_level}"
            ),
            "reservation_status": "AVAILABLE" if eligible else "CONSUMED",
        })
    return sorted(rows, key=lambda row: (row["discipline"], row["study_unit_id"]))
