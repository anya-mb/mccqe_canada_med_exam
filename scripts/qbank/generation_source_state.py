"""Derive source-packet-gated generation readiness and execution queue state."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from pathlib import Path
from typing import Any

from .jsonio import read_json, write_json_atomic
from .paths import resolve_root_path
from .question_generation_manifest import build_question_generation_manifest
from .source_packet_plan import build_source_packet_plan


BLOCKED_STATUSES = {"BLOCKED_EVIDENCE_CONFLICT", "BLOCKED_JURISDICTION"}
_PACKET_STATUSES = {
    "PENDING_RESEARCH",
    "SOURCE_PACKET_READY",
    "INCOMPLETE_RESEARCH",
    *BLOCKED_STATUSES,
}
_READINESS_PATH = "research/qgen/generation_source_readiness.json"
_QUEUE_PATH = "research/qgen/generation_queue.json"
_BLOCKING_REASON_CATEGORIES = {
    "BLOCKED_EVIDENCE_CONFLICT": "EVIDENCE_CONFLICT",
    "BLOCKED_JURISDICTION": "JURISDICTION",
}


@dataclass
class GenerationSourceStateValidation:
    status: str
    checks: dict[str, str] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)


def _artifact(root: Path, relative: str) -> tuple[dict[str, Any], bytes]:
    path = resolve_root_path(root, relative, label=relative)
    value = read_json(path)
    if not isinstance(value, dict):
        raise ValueError(f"{relative} must be an object")
    return value, path.read_bytes()


def _canonical_inputs(root: Path) -> tuple[dict[str, Any], dict[str, Any], str, str]:
    manifest, manifest_bytes = _artifact(root, "research/qgen/question_generation_manifest.json")
    plan, plan_bytes = _artifact(root, "research/qgen/source_packet_plan.json")
    rebuilt_manifest, _ = build_question_generation_manifest(root)
    rebuilt_plan, _ = build_source_packet_plan(root)
    if manifest != rebuilt_manifest:
        raise ValueError("question generation manifest is not deterministic-rebuild equivalent")
    if plan != rebuilt_plan:
        raise ValueError("source packet plan is not deterministic-rebuild equivalent")
    return (
        manifest,
        plan,
        hashlib.sha256(manifest_bytes).hexdigest(),
        hashlib.sha256(plan_bytes).hexdigest(),
    )


def _requirements(manifest: dict[str, Any], plan: dict[str, Any]) -> dict[str, list[str]]:
    jobs = manifest.get("jobs")
    mappings = plan.get("generation_job_source_packet_ids")
    packets = plan.get("source_packets")
    if not isinstance(jobs, list) or not isinstance(mappings, dict) or not isinstance(packets, list):
        raise ValueError("manifest or source packet plan mappings are invalid")
    job_ids = [job.get("job_id") for job in jobs if isinstance(job, dict)]
    if len(job_ids) != len(jobs) or any(not isinstance(job_id, str) or not job_id for job_id in job_ids):
        raise ValueError("manifest contains an invalid generation job ID")
    if len(set(job_ids)) != len(job_ids) or set(mappings) != set(job_ids):
        raise ValueError("generation job source-packet requirements do not exactly map manifest jobs")
    packet_ids = [packet.get("source_packet_id") for packet in packets if isinstance(packet, dict)]
    if len(packet_ids) != len(packets) or len(set(packet_ids)) != len(packet_ids):
        raise ValueError("source packet plan contains duplicate or invalid packet IDs")
    known_packet_ids = set(packet_ids)
    inverse: dict[str, list[str]] = {job_id: [] for job_id in job_ids}
    for packet in packets:
        packet_id = packet["source_packet_id"]
        covered_jobs = packet.get("covered_generation_job_ids")
        if not isinstance(covered_jobs, list) or not covered_jobs:
            raise ValueError(f"{packet_id}: source packet generation-job coverage is missing")
        if len(set(covered_jobs)) != len(covered_jobs) or not set(covered_jobs) <= set(job_ids):
            raise ValueError(f"{packet_id}: source packet generation-job coverage is inconsistent")
        for job_id in covered_jobs:
            inverse[job_id].append(packet_id)
    result: dict[str, list[str]] = {}
    for job_id in job_ids:
        required = mappings[job_id]
        if not isinstance(required, list) or not required or len(set(required)) != len(required):
            raise ValueError(f"{job_id}: source packet requirements are missing or duplicated")
        if not set(required) <= known_packet_ids or set(required) != set(inverse[job_id]):
            raise ValueError(f"{job_id}: source packet requirements are inconsistent")
        result[job_id] = list(required)
    return result


def _packet_statuses(plan: dict[str, Any], populations: list[dict[str, Any]]) -> dict[str, str]:
    packets = plan.get("source_packets", [])
    statuses = {packet["source_packet_id"]: "PENDING_RESEARCH" for packet in packets}
    if not isinstance(populations, list):
        raise ValueError("integrated source packet populations must be a list")
    integrated_ids: set[str] = set()
    for population in populations:
        if not isinstance(population, dict) or not isinstance(population.get("source_packets"), list):
            raise ValueError("integrated source packet population is invalid")
        for packet in population["source_packets"]:
            if not isinstance(packet, dict):
                raise ValueError("integrated source packet is invalid")
            packet_id = packet.get("source_packet_id")
            status = packet.get("status")
            if packet_id not in statuses:
                raise ValueError(f"unknown integrated source packet: {packet_id}")
            if packet_id in integrated_ids:
                raise ValueError(f"duplicate integrated source packet: {packet_id}")
            if status not in _PACKET_STATUSES:
                raise ValueError(f"{packet_id}: unknown source packet status: {status}")
            integrated_ids.add(packet_id)
            statuses[packet_id] = status
    return statuses


def _job_state(packet_statuses: list[dict[str, str]]) -> tuple[str, list[str], list[str]]:
    blocked_ids = [item["source_packet_id"] for item in packet_statuses if item["status"] in BLOCKED_STATUSES]
    if blocked_ids:
        categories = sorted({_BLOCKING_REASON_CATEGORIES[item["status"]] for item in packet_statuses if item["status"] in BLOCKED_STATUSES})
        return "BLOCKED", blocked_ids, categories
    if any(item["status"] in {"PENDING_RESEARCH", "INCOMPLETE_RESEARCH"} for item in packet_statuses):
        return "PENDING", [], []
    if all(item["status"] == "SOURCE_PACKET_READY" for item in packet_statuses):
        return "SOURCE_READY", [], []
    raise ValueError("source packet readiness state cannot be derived")


def build_generation_source_readiness(root: Path, populations: list[dict[str, Any]]) -> dict[str, Any]:
    """Build one fail-closed readiness record per frozen manifest job."""
    root = Path(root).resolve()
    manifest, plan, manifest_sha256, plan_sha256 = _canonical_inputs(root)
    requirements = _requirements(manifest, plan)
    statuses = _packet_statuses(plan, populations)
    records: list[dict[str, Any]] = []
    for job in manifest["jobs"]:
        job_id = job["job_id"]
        required = requirements[job_id]
        ordered_statuses = [
            {"source_packet_id": packet_id, "status": statuses[packet_id]}
            for packet_id in required
        ]
        state, blocking_ids, blocking_categories = _job_state(ordered_statuses)
        question_slots = job.get("question_slot_ids")
        if not isinstance(question_slots, list) or job.get("question_count") != len(question_slots):
            raise ValueError(f"{job_id}: manifest question slots are inconsistent")
        records.append({
            "job_id": job_id,
            "required_source_packet_ids": required,
            "packet_statuses": ordered_statuses,
            "state": state,
            "blocking_source_packet_ids": blocking_ids,
            "blocking_reason_categories": blocking_categories,
            "question_count": job["question_count"],
            "question_slot_ids": question_slots,
        })
    return {
        "schema_version": "1.0",
        "scope": "GENERATION_SOURCE_READINESS",
        "manifest_input": {"path": "research/qgen/question_generation_manifest.json", "sha256": manifest_sha256},
        "source_packet_plan_input": {"path": "research/qgen/source_packet_plan.json", "sha256": plan_sha256},
        "summary": {
            "GENERATION_JOBS_TOTAL": len(records),
            "GENERATION_JOBS_SOURCE_READY": sum(item["state"] == "SOURCE_READY" for item in records),
            "GENERATION_JOBS_PENDING": sum(item["state"] == "PENDING" for item in records),
            "GENERATION_JOBS_BLOCKED": sum(item["state"] == "BLOCKED" for item in records),
            "QUESTION_SLOTS_TOTAL": sum(item["question_count"] for item in records),
            "QUESTION_SLOTS_SOURCE_READY": sum(item["question_count"] for item in records if item["state"] == "SOURCE_READY"),
        },
        "jobs": records,
    }


def _validate_readiness_shape(root: Path, readiness: dict[str, Any]) -> None:
    manifest, plan, manifest_sha256, plan_sha256 = _canonical_inputs(root)
    requirements = _requirements(manifest, plan)
    if readiness.get("schema_version") != "1.0" or readiness.get("scope") != "GENERATION_SOURCE_READINESS":
        raise ValueError("generation source readiness metadata is invalid")
    if readiness.get("manifest_input") != {"path": "research/qgen/question_generation_manifest.json", "sha256": manifest_sha256}:
        raise ValueError("generation source readiness manifest input is invalid")
    if readiness.get("source_packet_plan_input") != {"path": "research/qgen/source_packet_plan.json", "sha256": plan_sha256}:
        raise ValueError("generation source readiness source packet plan input is invalid")
    records = readiness.get("jobs")
    if not isinstance(records, list) or [item.get("job_id") for item in records if isinstance(item, dict)] != [job["job_id"] for job in manifest["jobs"]]:
        raise ValueError("generation source readiness jobs are missing, extra, or reordered")
    status_by_job: list[dict[str, Any]] = []
    for record, job in zip(records, manifest["jobs"], strict=True):
        if not isinstance(record, dict):
            raise ValueError("generation source readiness record is invalid")
        required = requirements[job["job_id"]]
        ordered = record.get("packet_statuses")
        if record.get("required_source_packet_ids") != required or not isinstance(ordered, list):
            raise ValueError(f"{job['job_id']}: readiness requirements are invalid")
        if [item.get("source_packet_id") for item in ordered if isinstance(item, dict)] != required:
            raise ValueError(f"{job['job_id']}: readiness packet statuses are invalid")
        if any(item.get("status") not in _PACKET_STATUSES for item in ordered if isinstance(item, dict)) or len(ordered) != len(required):
            raise ValueError(f"{job['job_id']}: readiness includes an unknown packet status")
        state, blocked_ids, categories = _job_state(ordered)
        if (record.get("state"), record.get("blocking_source_packet_ids"), record.get("blocking_reason_categories")) != (state, blocked_ids, categories):
            raise ValueError(f"{job['job_id']}: readiness state is invalid")
        if record.get("question_count") != job["question_count"] or record.get("question_slot_ids") != job["question_slot_ids"]:
            raise ValueError(f"{job['job_id']}: readiness question slots are invalid")
        status_by_job.append(record)
    summary = readiness.get("summary")
    expected_summary = {
        "GENERATION_JOBS_TOTAL": len(status_by_job),
        "GENERATION_JOBS_SOURCE_READY": sum(item["state"] == "SOURCE_READY" for item in status_by_job),
        "GENERATION_JOBS_PENDING": sum(item["state"] == "PENDING" for item in status_by_job),
        "GENERATION_JOBS_BLOCKED": sum(item["state"] == "BLOCKED" for item in status_by_job),
        "QUESTION_SLOTS_TOTAL": sum(item["question_count"] for item in status_by_job),
        "QUESTION_SLOTS_SOURCE_READY": sum(item["question_count"] for item in status_by_job if item["state"] == "SOURCE_READY"),
    }
    if summary != expected_summary:
        raise ValueError("generation source readiness summary is invalid")


def build_generation_queue(root: Path, readiness: dict[str, Any]) -> dict[str, Any]:
    """Build the frozen-manifest-ordered execution queue from ready jobs only."""
    root = Path(root).resolve()
    _validate_readiness_shape(root, readiness)
    jobs = [record for record in readiness["jobs"] if record["state"] == "SOURCE_READY"]
    return {
        "schema_version": "1.0",
        "scope": "GENERATION_QUEUE",
        "readiness_input": {
            "manifest_input": readiness["manifest_input"],
            "source_packet_plan_input": readiness["source_packet_plan_input"],
        },
        "summary": {
            "GENERATION_QUEUE_JOBS": len(jobs),
            "QUESTION_SLOTS_QUEUED": sum(item["question_count"] for item in jobs),
        },
        "jobs": jobs,
    }


def validate_generation_source_readiness(root: Path, populations: list[dict[str, Any]], artifact: dict[str, Any]) -> GenerationSourceStateValidation:
    """Fail closed when readiness is not exactly deterministic rebuild output."""
    try:
        expected = build_generation_source_readiness(root, populations)
    except (TypeError, ValueError) as exc:
        return GenerationSourceStateValidation("FAIL", {"GENERATION_SOURCE_READINESS": "FAIL"}, [str(exc)])
    errors = [] if artifact == expected else ["generation source readiness does not match deterministic rebuild"]
    return GenerationSourceStateValidation("FAIL" if errors else "PASS", {"GENERATION_SOURCE_READINESS": "FAIL" if errors else "PASS"}, errors)


def validate_generation_queue(root: Path, readiness: dict[str, Any], artifact: dict[str, Any]) -> GenerationSourceStateValidation:
    """Fail closed when the queue is not the exact ready-job subset."""
    try:
        expected = build_generation_queue(root, readiness)
    except (TypeError, ValueError) as exc:
        return GenerationSourceStateValidation("FAIL", {"GENERATION_QUEUE": "FAIL"}, [str(exc)])
    errors = [] if artifact == expected else ["generation queue does not match deterministic rebuild"]
    return GenerationSourceStateValidation("FAIL" if errors else "PASS", {"GENERATION_QUEUE": "FAIL" if errors else "PASS"}, errors)


def write_generation_source_state(root: Path, populations: list[dict[str, Any]]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Build, validate, and atomically write both derived source-state artifacts."""
    root = Path(root).resolve()
    readiness = build_generation_source_readiness(root, populations)
    queue = build_generation_queue(root, readiness)
    if validate_generation_source_readiness(root, populations, readiness).status != "PASS":
        raise ValueError("generation source readiness validation failed")
    if validate_generation_queue(root, readiness, queue).status != "PASS":
        raise ValueError("generation queue validation failed")
    write_json_atomic(resolve_root_path(root, _READINESS_PATH, label="generation source readiness"), readiness)
    write_json_atomic(resolve_root_path(root, _QUEUE_PATH, label="generation queue"), queue)
    return readiness, queue
