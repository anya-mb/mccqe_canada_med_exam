"""Build deterministic, source-packet-gated MCCQE question-generation manifests."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .errors import QbankError
from .final_question_allocation import validate_final_question_allocation
from .jsonio import read_json, write_json_atomic
from .paths import resolve_root_path
from .question_bank_targets import load_question_bank_targets


_DISCIPLINES = ("MED", "PED", "OBGYN", "SURG", "PSY", "PHELO")
_MAXIMUM_QUESTIONS_PER_JOB = 30
_PENDING_STATUS = "PENDING_SOURCE_PACKET"
_VALID_STATUSES = {
    "PENDING_SOURCE_PACKET", "SOURCE_PACKET_READY", "PENDING_GENERATION",
    "GENERATED", "PENDING_VERIFICATION", "VERIFIED", "FAILED_RETRYABLE", "BLOCKED",
}


class QuestionGenerationManifestError(QbankError):
    """The frozen allocation cannot safely be converted to generation jobs."""


@dataclass
class QuestionGenerationManifestValidation:
    status: str
    checks: dict[str, str] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)


def _path(root: Path, relative: str) -> Path:
    return resolve_root_path(root, relative, label=relative)


def _load_frozen_allocation(root: Path) -> list[dict[str, Any]]:
    allocation = read_json(_path(root, "research/scope/final_question_allocation.json"))
    audit = read_json(_path(root, "reports/final_question_allocation_audit.json"))
    result = validate_final_question_allocation(root, allocation, audit)
    if result.status != "PASS":
        raise QuestionGenerationManifestError("the committed final allocation failed validation")
    rows = allocation.get("allocation_addresses")
    if not isinstance(rows, list):
        raise QuestionGenerationManifestError("final allocation has no allocation addresses")
    positive = [row for row in rows if row.get("final_question_count", 0) > 0]
    if len(positive) != 1175 or sum(row["final_question_count"] for row in positive) != 6086:
        raise QuestionGenerationManifestError("final allocation does not contain the frozen positive work set")
    if any(row.get("allocation_status") != "ELIGIBLE" for row in positive):
        raise QuestionGenerationManifestError("non-eligible allocation address has generation work")
    return positive


def _canonical_metadata(root: Path) -> dict[str, dict[str, Any]]:
    crosswalk = read_json(_path(root, "research/scope/master_scope_crosswalk.json"))
    entries = crosswalk.get("entries", [])
    metadata: dict[str, dict[str, Any]] = {}
    for entry in entries:
        study_unit_id = entry.get("study_unit_id")
        if isinstance(study_unit_id, str):
            metadata[study_unit_id] = {
                "title": entry.get("title"),
                "source_node_ids": sorted(entry.get("source_node_ids", [])),
            }
    return metadata


def _assignment(row: dict[str, Any], metadata: dict[str, Any], question_count: int) -> dict[str, Any]:
    assignment = {
        "allocation_address_id": row["allocation_address_id"],
        "study_unit_id": row["study_unit_id"],
        "discipline": row["discipline"],
        "chapter": row["chapter"],
        "title": metadata["title"],
        "question_count": question_count,
        "classification": row["classification"],
        "depth": row["depth"],
        "coverage_weight": row["coverage_weight"],
        "mcc_objective_ids": row["mcc_objective_ids"],
        "preferred_item_forms": row["preferred_item_forms"],
        "source_node_ids": metadata["source_node_ids"],
    }
    if "component_id" in row:
        assignment["component_id"] = row["component_id"]
    return assignment


def _finish_job(
    jobs: list[dict[str, Any]], discipline: str, chapter: str, assignments: list[dict[str, Any]], slot_start: int
) -> int:
    question_count = sum(assignment["question_count"] for assignment in assignments)
    job_number = len(jobs) + 1
    source_nodes = sorted({node for assignment in assignments for node in assignment["source_node_ids"]})
    jobs.append({
        "job_id": f"QGEN-{discipline}-{job_number:03d}",
        "discipline": discipline,
        "chapter": chapter,
        "question_count": question_count,
        "question_slot_ids": [f"{discipline}-Q{index:04d}" for index in range(slot_start, slot_start + question_count)],
        "assignments": assignments,
        "source_packet_requirements": {
            "required_evidence": "CURRENT_AUTHORITATIVE_CANADIAN_EVIDENCE",
            "source_packet_status": _PENDING_STATUS,
            "canonical_source_node_ids": source_nodes,
        },
        "generation_status": _PENDING_STATUS,
    })
    return slot_start + question_count


def _build_discipline_jobs(rows: list[dict[str, Any]], metadata: dict[str, dict[str, Any]], discipline: str) -> list[dict[str, Any]]:
    jobs: list[dict[str, Any]] = []
    slot_start = 1
    current_chapter: str | None = None
    current: list[dict[str, Any]] = []
    current_count = 0
    for row in sorted((row for row in rows if row["discipline"] == discipline), key=lambda row: (row["chapter"], row["study_unit_id"], row.get("component_id", ""), row["allocation_address_id"])):
        if row["study_unit_id"] not in metadata:
            raise QuestionGenerationManifestError(f"missing canonical metadata for {row['study_unit_id']}")
        if current and current_chapter != row["chapter"]:
            slot_start = _finish_job(jobs, discipline, current_chapter, current, slot_start)
            current, current_count = [], 0
        current_chapter = row["chapter"]
        remaining = row["final_question_count"]
        while remaining:
            available = _MAXIMUM_QUESTIONS_PER_JOB - current_count
            assigned = min(remaining, available)
            current.append(_assignment(row, metadata[row["study_unit_id"]], assigned))
            current_count += assigned
            remaining -= assigned
            if current_count == _MAXIMUM_QUESTIONS_PER_JOB:
                slot_start = _finish_job(jobs, discipline, current_chapter, current, slot_start)
                current, current_count = [], 0
    if current:
        _finish_job(jobs, discipline, current_chapter, current, slot_start)
    return jobs


def _audit(rows: list[dict[str, Any]], manifest: dict[str, Any]) -> dict[str, Any]:
    jobs = manifest["jobs"]
    assignments = [assignment for job in jobs for assignment in job["assignments"]]
    expected = {row["allocation_address_id"]: row["final_question_count"] for row in rows}
    assigned = Counter()
    for assignment in assignments:
        assigned[assignment["allocation_address_id"]] += assignment["question_count"]
    sizes = [job["question_count"] for job in jobs]
    slots = [slot for job in jobs for slot in job["question_slot_ids"]]
    discipline_questions = {discipline: sum(job["question_count"] for job in jobs if job["discipline"] == discipline) for discipline in _DISCIPLINES}
    return {
        "schema_version": "1.0",
        "scope": "QUESTION_GENERATION_MANIFEST_AUDIT",
        "reconciliation": {
            "ALLOCATION_ADDRESSES_EXPECTED": len(expected),
            "ALLOCATION_ADDRESSES_MANIFESTED": len(assigned),
            "MISSING_ALLOCATION_ADDRESSES": len(set(expected) - set(assigned)),
            "OVERALLOCATED_ADDRESSES": sum(assigned[key] > expected.get(key, 0) for key in assigned),
            "QUESTION_SLOTS": len(slots),
            "TOTAL_MANIFEST_QUESTIONS": sum(sizes),
            "UNDERALLOCATED_ADDRESSES": sum(assigned.get(key, 0) < count for key, count in expected.items()),
        },
        "jobs": {"TOTAL_MANIFEST_JOBS": len(jobs), "JOBS_BY_DISCIPLINE": {discipline: sum(job["discipline"] == discipline for job in jobs) for discipline in _DISCIPLINES}},
        "questions_by_discipline": discipline_questions,
        "batch_size_distribution": {str(size): count for size, count in sorted(Counter(sizes).items())},
        "job_size_summary": {"MIN_JOB_SIZE": min(sizes), "MAX_JOB_SIZE": max(sizes), "MEAN_JOB_SIZE": sum(sizes) / len(sizes)},
        "split_allocation_addresses": sum(count > 1 for count in Counter(assignment["allocation_address_id"] for assignment in assignments).values()),
        "status_counts": dict(sorted(Counter(job["generation_status"] for job in jobs).items())),
        "safety": {
            "CROSS_DISCIPLINE_JOBS": sum(any(assignment["discipline"] != job["discipline"] for assignment in job["assignments"]) for job in jobs),
            "DUPLICATE_JOB_IDS": len(jobs) - len({job["job_id"] for job in jobs}),
            "DUPLICATE_QUESTION_SLOT_IDS": len(slots) - len(set(slots)),
            "SUPPRESSED_ADDRESSES_MANIFESTED": 0,
            "ZERO_SCOPE_ADDRESSES_MANIFESTED": 0,
        },
        "determinism": {"MANIFEST_REBUILD_DETERMINISTIC": "PASS"},
    }


def build_question_generation_manifest(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    """Convert the committed allocation into compact deterministic generation jobs."""
    root = Path(root).resolve()
    rows = _load_frozen_allocation(root)
    metadata = _canonical_metadata(root)
    jobs = [job for discipline in _DISCIPLINES for job in _build_discipline_jobs(rows, metadata, discipline)]
    manifest = {
        "schema_version": "1.0",
        "scope": "MCCQE_QUESTION_GENERATION_MANIFEST",
        "manifest_input": {"allocation_artifact": "research/scope/final_question_allocation.json", "MANIFEST_INPUT_ADDRESSES": len(rows), "MANIFEST_INPUT_QUESTIONS": sum(row["final_question_count"] for row in rows)},
        "batch_size_policy": {"algorithm": "DISCIPLINE_CHAPTER_ADDRESS_ORDER_FILL_TO_MAXIMUM", "maximum_questions_per_job": _MAXIMUM_QUESTIONS_PER_JOB},
        "generation_status_values": sorted(_VALID_STATUSES),
        "jobs": jobs,
    }
    audit = _audit(rows, manifest)
    validation = validate_question_generation_manifest(root, manifest, audit)
    if validation.status != "PASS":
        raise QuestionGenerationManifestError("built manifest failed validation: " + "; ".join(validation.errors))
    return manifest, audit


def validate_question_generation_manifest(root: Path, manifest: dict[str, Any], audit: dict[str, Any]) -> QuestionGenerationManifestValidation:
    """Validate exact frozen-allocation reconciliation and resumable job invariants."""
    root = Path(root).resolve()
    errors: list[str] = []
    rows = _load_frozen_allocation(root)
    targets = load_question_bank_targets(root)["discipline_targets"]
    jobs = manifest.get("jobs", [])
    assignments = [assignment for job in jobs if isinstance(job, dict) for assignment in job.get("assignments", [])]
    expected = {row["allocation_address_id"]: row["final_question_count"] for row in rows}
    actual = Counter()
    for assignment in assignments:
        actual[assignment.get("allocation_address_id")] += assignment.get("question_count", 0)
    slots = [slot for job in jobs for slot in job.get("question_slot_ids", [])]
    if manifest.get("scope") != "MCCQE_QUESTION_GENERATION_MANIFEST": errors.append("manifest schema is invalid")
    if manifest.get("manifest_input", {}).get("MANIFEST_INPUT_QUESTIONS") != 6086: errors.append("manifest input questions differ from frozen allocation")
    if manifest.get("manifest_input", {}).get("MANIFEST_INPUT_ADDRESSES") != 1175: errors.append("manifest input address count differs from frozen allocation")
    if any(job.get("discipline") not in _DISCIPLINES for job in jobs): errors.append("unknown job discipline")
    if any(job.get("question_count", 0) <= 0 or job.get("question_count", 0) > _MAXIMUM_QUESTIONS_PER_JOB for job in jobs): errors.append("job size violates batch policy")
    if any(sum(item.get("question_count", 0) for item in job.get("assignments", [])) != job.get("question_count") for job in jobs): errors.append("job assignment totals do not reconcile")
    if any(len(job.get("question_slot_ids", [])) != job.get("question_count") for job in jobs): errors.append("job slot totals do not reconcile")
    if any(any(item.get("discipline") != job.get("discipline") for item in job.get("assignments", [])) for job in jobs): errors.append("cross-discipline job")
    if any(job.get("generation_status") not in _VALID_STATUSES for job in jobs): errors.append("invalid generation status")
    if any(job.get("generation_status") != _PENDING_STATUS for job in jobs): errors.append("initial job status is not pending source packet")
    if len({job.get("job_id") for job in jobs}) != len(jobs): errors.append("duplicate job ids")
    if len(set(slots)) != len(slots): errors.append("duplicate question slot ids")
    if len(slots) != 6086: errors.append("question slots do not total 6086")
    if set(actual) != set(expected): errors.append("manifested allocation address set differs from frozen allocation")
    if any(actual[address] != count for address, count in expected.items()): errors.append("address question counts differ from frozen allocation")
    actual_disciplines = {discipline: sum(job.get("question_count", 0) for job in jobs if job.get("discipline") == discipline) for discipline in _DISCIPLINES}
    if actual_disciplines != targets: errors.append("discipline question counts differ from frozen targets")
    if audit.get("reconciliation", {}).get("TOTAL_MANIFEST_QUESTIONS") != 6086: errors.append("audit manifest total is invalid")
    return QuestionGenerationManifestValidation("FAIL" if errors else "PASS", {"MANIFEST_VALIDATOR": "FAIL" if errors else "PASS"}, errors)


def write_question_generation_manifest(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    root = Path(root).resolve()
    manifest, audit = build_question_generation_manifest(root)
    repeat_manifest, repeat_audit = build_question_generation_manifest(root)
    if manifest != repeat_manifest or audit != repeat_audit:
        raise QuestionGenerationManifestError("manifest rebuild is not deterministic")
    write_json_atomic(_path(root, "research/qgen/question_generation_manifest.json"), manifest)
    write_json_atomic(_path(root, "reports/question_generation_manifest_audit.json"), audit)
    return manifest, audit
