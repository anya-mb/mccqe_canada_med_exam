"""Deterministic read-only reconciliation for isolated source-research workers."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path
import re
import subprocess
from typing import Any

from .generation_source_state import validate_generation_queue, validate_generation_source_readiness
from .source_document_registry import validate_source_document_registry
from .source_packet_population import (
    _population_batch_id,
    _population_packets,
    load_integrated_source_packet_populations,
    validate_source_packet_research_batch,
)


_WORKER_BRANCH = re.compile(r"codex/source-research/(SRB-\d{3})$")
_FROZEN_INPUTS = (
    "research/qgen/source_packet_plan.json",
    "research/qgen/question_generation_manifest.json",
)


@dataclass
class SourceResearchCoordinatorValidation:
    status: str
    checks: dict[str, str] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)


def _git(root: Path, *args: str) -> str:
    """Run read-only Git inspection with an argument list, never a shell."""
    return subprocess.run(
        ["git", *args], cwd=root, check=True, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    ).stdout


def resolve_git_commit(root: Path, revision: str) -> str:
    """Resolve *revision* to one full immutable commit SHA."""
    return _git(Path(root).resolve(), "rev-parse", "--verify", f"{revision}^{{commit}}").strip()


def _worker_batch_id(branch: Any) -> str | None:
    match = _WORKER_BRANCH.fullmatch(branch) if isinstance(branch, str) else None
    return match.group(1) if match else None


def _worker_paths(batch_id: str) -> tuple[str, str]:
    stem = batch_id.lower().replace("-", "_")
    return (
        f"research/qgen/source_packet_population_{stem}.json",
        f"reports/source_packet_wave_{stem}_audit.json",
    )


def _git_json(root: Path, revision: str, relative: str) -> dict[str, Any]:
    try:
        value = json.loads(_git(root, "show", f"{revision}:{relative}"))
    except (json.JSONDecodeError, subprocess.CalledProcessError) as exc:
        raise ValueError(f"cannot read worker commit JSON: {relative}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"worker commit JSON must be an object: {relative}")
    return value


def _worktree_states(root: Path) -> dict[str, tuple[Path, bool]]:
    records: list[dict[str, str]] = []
    record: dict[str, str] = {}
    for line in _git(root, "worktree", "list", "--porcelain").splitlines():
        if not line:
            if record:
                records.append(record)
            record = {}
            continue
        key, _, value = line.partition(" ")
        record[key] = value
    if record:
        records.append(record)
    result: dict[str, tuple[Path, bool]] = {}
    for item in records:
        branch_ref = item.get("branch", "")
        if not branch_ref.startswith("refs/heads/") or "worktree" not in item:
            continue
        branch = branch_ref.removeprefix("refs/heads/")
        path = Path(item["worktree"])
        result[branch] = (path, bool(_git(path, "status", "--porcelain").strip()))
    return result


def validate_disjoint_worker_ownership(
    root: Path, batch_ids: list[str], integrated_populations: list[dict[str, Any]]
) -> SourceResearchCoordinatorValidation:
    """Fail closed when worker claims or integrated packet populations overlap."""
    del root
    errors: list[str] = []
    if len(batch_ids) != len(set(batch_ids)):
        errors.append("duplicate pending batch claim")
    integrated_batch_ids = [_population_batch_id(population) for population in integrated_populations]
    for batch_id in sorted(set(batch_ids) & {item for item in integrated_batch_ids if item}):
        errors.append(f"already integrated batch: {batch_id}")
    owners: dict[str, str] = {}
    for population in integrated_populations:
        batch_id = _population_batch_id(population) or "UNKNOWN"
        for packet in _population_packets([population]):
            packet_id = packet.get("source_packet_id")
            if not isinstance(packet_id, str):
                continue
            previous = owners.setdefault(packet_id, batch_id)
            if previous != batch_id:
                errors.append(f"integrated populations are not pairwise disjoint: {packet_id}")
    return SourceResearchCoordinatorValidation("FAIL" if errors else "PASS", {"DISJOINT_WORKER_OWNERSHIP": "FAIL" if errors else "PASS"}, errors)


def validate_worker_commit(root: Path, worker: dict[str, Any], canonical_commit: str) -> SourceResearchCoordinatorValidation:
    """Validate one worker's exact commit shape against canonical frozen inputs."""
    root = Path(root).resolve()
    errors: list[str] = []
    branch = worker.get("branch")
    batch_id = worker.get("batch_id")
    expected_batch_id = _worker_batch_id(branch)
    if expected_batch_id is None:
        errors.append("worker branch name is invalid")
    elif batch_id != expected_batch_id:
        errors.append("worker batch ID does not match branch name")
    if not isinstance(batch_id, str):
        errors.append("worker batch ID is missing")
    try:
        commit = resolve_git_commit(root, str(worker.get("commit", branch)))
        canonical = resolve_git_commit(root, canonical_commit)
    except subprocess.CalledProcessError:
        return SourceResearchCoordinatorValidation("FAIL", {"WORKER_COMMIT": "FAIL"}, [*errors, "worker or canonical commit cannot be resolved"])
    parents = _git(root, "rev-list", "--parents", "-n", "1", commit).split()
    if len(parents) != 2 or parents[1] != canonical:
        errors.append("worker commit must have exactly the canonical checkpoint parent")
    if isinstance(batch_id, str):
        expected_paths = set(_worker_paths(batch_id))
        changed_paths = set(_git(root, "diff-tree", "--no-commit-id", "--name-only", "-r", commit).splitlines())
        if changed_paths != expected_paths:
            errors.extend(f"unexpected changed path: {path}" for path in sorted(changed_paths - expected_paths))
            errors.extend(f"required worker output path is missing: {path}" for path in sorted(expected_paths - changed_paths))
        if not errors:
            try:
                population_path, audit_path = _worker_paths(batch_id)
                population = _git_json(root, commit, population_path)
                audit = _git_json(root, commit, audit_path)
                integrated = [item for item in load_integrated_source_packet_populations(root) if _population_batch_id(item) != batch_id]
                result = validate_source_packet_research_batch(root, population, integrated, audit)
                if result.status != "PASS":
                    errors.extend(result.errors)
            except (OSError, TypeError, ValueError, subprocess.CalledProcessError) as exc:
                errors.append(str(exc))
    return SourceResearchCoordinatorValidation("FAIL" if errors else "PASS", {"WORKER_COMMIT": "FAIL" if errors else "PASS", "WORKER_COMMIT_FILE_SCOPE": "FAIL" if errors else "PASS"}, errors)


def discover_source_research_workers(root: Path, canonical_commit: str) -> list[dict[str, Any]]:
    """Classify canonical worker branches; branch existence alone is never completion."""
    root = Path(root).resolve()
    canonical = resolve_git_commit(root, canonical_commit)
    integrated = {_population_batch_id(item) for item in load_integrated_source_packet_populations(root)}
    worktrees = _worktree_states(root)
    refs = _git(root, "for-each-ref", "--format=%(refname:short) %(objectname)", "refs/heads/codex/source-research/")
    workers: list[dict[str, Any]] = []
    for line in refs.splitlines():
        branch, _, commit = line.partition(" ")
        batch_id = _worker_batch_id(branch)
        if batch_id is None or not commit:
            continue
        path, dirty = worktrees.get(branch, (None, False))
        worker: dict[str, Any] = {"branch": branch, "batch_id": batch_id, "commit": commit, "canonical_commit": canonical}
        if path is not None:
            worker["worktree"] = str(path)
        if dirty:
            worker["state"] = "RETRY_RESUME"
        elif batch_id in integrated:
            worker["state"] = "INTEGRATED"
        else:
            validation = validate_worker_commit(root, worker, canonical)
            worker.update({"validation": validation.status, "errors": validation.errors, "state": "AWAITING_INTEGRATION" if validation.status == "PASS" else "INVALID"})
        workers.append(worker)
    return sorted(workers, key=lambda item: (item["batch_id"], item["branch"]))


def _sha256_json(value: Any) -> str:
    data = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n"
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def _frozen_input_fingerprints(root: Path) -> list[dict[str, str]]:
    return [{"path": relative, "sha256": hashlib.sha256((root / relative).read_bytes()).hexdigest()} for relative in _FROZEN_INPUTS]


def _canonical_frozen_input_fingerprints(root: Path, canonical: str) -> list[dict[str, str]]:
    return [
        {"path": relative, "sha256": hashlib.sha256(_git(root, "show", f"{canonical}:{relative}").encode("utf-8")).hexdigest()}
        for relative in _FROZEN_INPUTS
    ]


def _ready_packet_fingerprints(populations: list[dict[str, Any]]) -> list[dict[str, str]]:
    return sorted(({"source_packet_id": packet["source_packet_id"], "sha256": _sha256_json(packet)} for packet in _population_packets(populations) if packet.get("status") == "SOURCE_PACKET_READY" and isinstance(packet.get("source_packet_id"), str)), key=lambda item: item["source_packet_id"])


def _canonical_ready_packet_fingerprints(root: Path, canonical: str) -> list[dict[str, str]]:
    paths = [
        path for path in _git(root, "ls-tree", "-r", "--name-only", canonical, "research/qgen").splitlines()
        if re.fullmatch(r"research/qgen/source_packet_population_srb_\d{3}\.json", path)
    ]
    populations = [_git_json(root, canonical, path) for path in paths]
    return _ready_packet_fingerprints(populations)


def _validation_result(callback: Any) -> tuple[str, list[str]]:
    try:
        result = callback()
        return result.status, list(result.errors)
    except (OSError, TypeError, ValueError) as exc:
        return "FAIL", [str(exc)]


def build_source_research_integration_audit(root: Path, canonical_commit: str, populations: list[dict[str, Any]], registry: dict[str, Any], readiness: dict[str, Any], queue: dict[str, Any], workers: list[dict[str, Any]]) -> dict[str, Any]:
    """Build a deterministic, fail-closed coordinator reconciliation record."""
    root = Path(root).resolve()
    canonical = resolve_git_commit(root, canonical_commit)
    worker_records: list[dict[str, Any]] = []
    selected_populations: list[dict[str, Any]] = []
    worker_errors: list[str] = []
    for worker in sorted(workers, key=lambda item: (str(item.get("batch_id", "")), str(item.get("branch", "")))):
        validation = validate_worker_commit(root, worker, canonical)
        worker_records.append({"branch": worker.get("branch"), "batch_id": worker.get("batch_id"), "commit": worker.get("commit"), "state": worker.get("state"), "validation": validation.status, "errors": validation.errors})
        worker_errors.extend(validation.errors)
        if validation.status == "PASS" and isinstance(worker.get("batch_id"), str):
            path, _ = _worker_paths(worker["batch_id"])
            selected_populations.append(_git_json(root, str(worker.get("commit")), path))
    ownership = validate_disjoint_worker_ownership(root, [item["batch_id"] for item in workers if isinstance(item.get("batch_id"), str)], [*populations, *selected_populations])
    registry_status, registry_errors = _validation_result(lambda: validate_source_document_registry(root, populations, registry))
    readiness_status, readiness_errors = _validation_result(lambda: validate_generation_source_readiness(root, populations, readiness))
    queue_status, queue_errors = _validation_result(lambda: validate_generation_queue(root, readiness, queue))
    frozen_current = _frozen_input_fingerprints(root)
    frozen_canonical = _canonical_frozen_input_fingerprints(root, canonical)
    ready_current = _ready_packet_fingerprints(populations)
    ready_canonical = _canonical_ready_packet_fingerprints(root, canonical)
    checks = {
        "CANONICAL_BASE_CHECKPOINT": "PASS",
        "DISJOINT_WORKER_OWNERSHIP": ownership.checks["DISJOINT_WORKER_OWNERSHIP"],
        "WORKER_COMMIT_FILE_SCOPES": "FAIL" if worker_errors else "PASS",
        "PRIOR_READY_PACKET_IMMUTABILITY": "PASS" if ready_current == ready_canonical else "FAIL",
        "FROZEN_INPUT_FINGERPRINTS": "PASS" if frozen_current == frozen_canonical else "FAIL",
        "SOURCE_DOCUMENT_REGISTRY": registry_status,
        "GENERATION_SOURCE_READINESS": readiness_status,
        "GENERATION_QUEUE": queue_status,
    }
    return {
        "schema_version": "1.0", "scope": "SOURCE_RESEARCH_INTEGRATION_AUDIT",
        "canonical_base_checkpoint": canonical,
        "selected_batch_ids": sorted(item["batch_id"] for item in workers if isinstance(item.get("batch_id"), str)),
        "workers": worker_records,
        "packet_ownership": [{"source_packet_id": packet.get("source_packet_id"), "research_batch_id": _population_batch_id(population)} for population in populations for packet in _population_packets([population]) if isinstance(packet.get("source_packet_id"), str)],
        "prior_ready_packet_fingerprints": ready_current,
        "canonical_prior_ready_packet_fingerprints": ready_canonical,
        "frozen_input_fingerprints": frozen_current,
        "canonical_frozen_input_fingerprints": frozen_canonical,
        "checks": checks,
        "errors": [*ownership.errors, *worker_errors, *registry_errors, *readiness_errors, *queue_errors],
    }


def validate_source_research_integration_audit(root: Path, audit: dict[str, Any], populations: list[dict[str, Any]], registry: dict[str, Any], readiness: dict[str, Any], queue: dict[str, Any], workers: list[dict[str, Any]]) -> SourceResearchCoordinatorValidation:
    """Require an audit to be exactly the current deterministic reconciliation."""
    canonical = audit.get("canonical_base_checkpoint") if isinstance(audit, dict) else None
    errors: list[str] = []
    if not isinstance(canonical, str):
        errors.append("integration audit canonical base checkpoint is missing")
    else:
        try:
            expected = build_source_research_integration_audit(Path(root), canonical, populations, registry, readiness, queue, workers)
            if audit != expected:
                errors.append("integration audit does not match deterministic rebuild")
            errors.extend(f"integration audit check failed: {name}" for name, status in expected["checks"].items() if status != "PASS")
        except (OSError, TypeError, ValueError, subprocess.CalledProcessError) as exc:
            errors.append(str(exc))
    return SourceResearchCoordinatorValidation("FAIL" if errors else "PASS", {"SOURCE_RESEARCH_INTEGRATION_AUDIT": "FAIL" if errors else "PASS"}, errors)
