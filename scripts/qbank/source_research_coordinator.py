"""Deterministic read-only reconciliation for isolated source-research workers."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path
import re
import subprocess
from typing import Any

from .generation_source_state import (
    build_generation_queue,
    build_generation_source_readiness,
    validate_generation_queue,
    validate_generation_source_readiness,
)
from .jsonio import read_json, write_json_atomic
from .paths import resolve_root_path
from .source_document_registry import (
    build_source_document_registry,
    validate_source_document_registry,
)
from .source_packet_population import (
    _population_batch_id,
    _population_packets,
    build_source_packet_research_progress,
    load_integrated_source_packet_populations,
    validate_source_packet_population,
    validate_source_packet_research_batch,
)


_WORKER_BRANCH = re.compile(r"codex/source-research/(SRB-\d{3})$")
_FROZEN_INPUTS = (
    "research/qgen/source_packet_plan.json",
    "research/qgen/question_generation_manifest.json",
    "research/scope",
)
_STATE_OUTPUTS = (
    ("registry", "research/qgen/source_document_registry.json"),
    ("readiness", "research/qgen/generation_source_readiness.json"),
    ("queue", "research/qgen/generation_queue.json"),
    ("progress", "reports/source_packet_research_progress.json"),
    ("audit", "reports/source_research_integration_audit.json"),
)

_NEXT_ACTIONS = (
    "INTEGRATE_SOURCE_RESEARCH_WORKERS",
    "RESUME_SOURCE_RESEARCH_BATCH",
    "PLAN_SOURCE_READY_GENERATION",
    "CONTINUE_SOURCE_PACKET_RESEARCH",
    "RESOLVE_SOURCE_PACKET_BLOCKERS",
    "SOURCE_RESEARCH_COMPLETE",
)


@dataclass
class SourceResearchCoordinatorValidation:
    status: str
    checks: dict[str, str] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class SourceResearchState:
    """Fully reconciled, write-ready coordinator artifacts."""

    progress: dict[str, Any]
    registry: dict[str, Any]
    readiness: dict[str, Any]
    queue: dict[str, Any]
    audit: dict[str, Any]


def derive_next_source_research_action(
    progress: dict[str, Any], queue: dict[str, Any], workers: list[dict[str, Any]]
) -> str:
    """Derive the one authorized operational action from validated state only."""
    if not isinstance(progress, dict) or not isinstance(queue, dict) or not isinstance(workers, list):
        raise ValueError("source research resume inputs must be objects and a worker list")
    summary = queue.get("summary")
    jobs = queue.get("jobs")
    if not isinstance(summary, dict) or not isinstance(jobs, list):
        raise ValueError("generation queue is malformed")
    queue_jobs = summary.get("GENERATION_QUEUE_JOBS")
    pending = progress.get("SOURCE_PACKETS_PENDING")
    blocked = progress.get("SOURCE_PACKETS_BLOCKED")
    if any(not isinstance(value, int) or isinstance(value, bool) or value < 0 for value in (queue_jobs, pending, blocked)):
        raise ValueError("source research resume counts are invalid")
    if queue_jobs != len(jobs):
        raise ValueError("generation queue count disagrees with queue jobs")
    states: list[str] = []
    for worker in workers:
        if not isinstance(worker, dict) or not isinstance(worker.get("state"), str):
            raise ValueError("source research worker state is malformed")
        states.append(worker["state"])
    known_worker_states = {"AWAITING_INTEGRATION", "RETRY_RESUME", "INTEGRATED"}
    unknown_states = sorted(set(states) - known_worker_states)
    if unknown_states:
        raise ValueError("unreconciled source research worker state: " + ", ".join(unknown_states))
    if "AWAITING_INTEGRATION" in states:
        return _NEXT_ACTIONS[0]
    if "RETRY_RESUME" in states:
        return _NEXT_ACTIONS[1]
    if queue_jobs:
        return _NEXT_ACTIONS[2]
    if pending:
        return _NEXT_ACTIONS[3]
    if blocked:
        return _NEXT_ACTIONS[4]
    return _NEXT_ACTIONS[5]


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


def _git_integrated_source_packet_populations(
    root: Path, revision: str
) -> list[dict[str, Any]]:
    """Load the exact integrated population snapshot at an immutable revision."""
    plan = _git_json(root, revision, "research/qgen/source_packet_plan.json")
    order = {
        batch.get("research_batch_id"): index
        for index, batch in enumerate(plan.get("research_batches", []))
        if isinstance(batch, dict) and isinstance(batch.get("research_batch_id"), str)
    }
    paths = [
        path
        for path in _git(
            root, "ls-tree", "-r", "--name-only", revision, "research/qgen"
        ).splitlines()
        if re.fullmatch(r"research/qgen/source_packet_population_srb_\d{3}\.json", path)
    ]
    populations = [_git_json(root, revision, path) for path in paths]
    return sorted(
        populations,
        key=lambda population: (
            order.get(_population_batch_id(population), len(order)),
            _population_batch_id(population) or "",
        ),
    )


def _population_introduction_parent(
    root: Path, revision: str, batch_id: str
) -> str:
    """Resolve the immutable snapshot immediately before a population was added."""
    population_path, _ = _worker_paths(batch_id)
    additions = _git(
        root,
        "log",
        "--diff-filter=A",
        "--format=%H %P",
        revision,
        "--",
        population_path,
    ).splitlines()
    if not additions:
        raise ValueError(
            f"population introduction commit is missing: {population_path}"
        )
    commit_and_parents = additions[0].split()
    if len(commit_and_parents) != 2:
        raise ValueError(
            f"population introduction must have one parent: {population_path}"
        )
    return commit_and_parents[1]


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
                audit_base = _git_integrated_source_packet_populations(root, canonical)
                result = validate_source_packet_research_batch(
                    root,
                    population,
                    integrated,
                    audit,
                    audit_base_populations=audit_base,
                )
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


def _frozen_paths(root: Path) -> list[str]:
    paths: list[str] = []
    for relative in _FROZEN_INPUTS:
        path = root / relative
        if path.is_file():
            paths.append(relative)
        elif path.is_dir():
            paths.extend(item.relative_to(root).as_posix() for item in path.rglob("*") if item.is_file())
        else:
            raise ValueError(f"frozen input is missing: {relative}")
    return sorted(paths)


def _frozen_input_fingerprints(root: Path) -> list[dict[str, str]]:
    return [
        {"path": relative, "sha256": hashlib.sha256((root / relative).read_bytes()).hexdigest()}
        for relative in _frozen_paths(root)
    ]


def _canonical_frozen_input_fingerprints(root: Path, canonical: str) -> list[dict[str, str]]:
    paths: list[str] = []
    for relative in _FROZEN_INPUTS:
        entries = _git(root, "ls-tree", "-r", "--name-only", canonical, relative).splitlines()
        if not entries:
            raise ValueError(f"canonical frozen input is missing: {relative}")
        paths.extend(entries)
    return [
        {"path": relative, "sha256": hashlib.sha256(_git(root, "show", f"{canonical}:{relative}").encode("utf-8")).hexdigest()}
        for relative in sorted(paths)
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
    selected_batch_ids: list[str] = []
    worker_errors: list[str] = []
    for worker in sorted(workers, key=lambda item: (str(item.get("batch_id", "")), str(item.get("branch", "")))):
        validation_base = canonical
        if worker.get("state") == "INTEGRATED":
            try:
                worker_commit = resolve_git_commit(
                    root, str(worker.get("commit", worker.get("branch", "")))
                )
                commit_and_parents = _git(
                    root, "rev-list", "--parents", "-n", "1", worker_commit
                ).split()
                if len(commit_and_parents) == 2:
                    validation_base = commit_and_parents[1]
            except subprocess.CalledProcessError:
                pass
        validation = validate_worker_commit(root, worker, validation_base)
        worker_records.append({"branch": worker.get("branch"), "batch_id": worker.get("batch_id"), "commit": worker.get("commit"), "state": worker.get("state"), "validation": validation.status, "errors": validation.errors})
        worker_errors.extend(validation.errors)
        if (
            validation.status == "PASS"
            and worker.get("state") != "INTEGRATED"
            and isinstance(worker.get("batch_id"), str)
        ):
            path, _ = _worker_paths(worker["batch_id"])
            selected_populations.append(_git_json(root, str(worker.get("commit")), path))
            selected_batch_ids.append(worker["batch_id"])
    ownership = validate_disjoint_worker_ownership(
        root,
        selected_batch_ids,
        [*populations, *selected_populations],
    )
    registry_status, registry_errors = _validation_result(lambda: validate_source_document_registry(root, populations, registry))
    readiness_status, readiness_errors = _validation_result(lambda: validate_generation_source_readiness(root, populations, readiness))
    queue_status, queue_errors = _validation_result(lambda: validate_generation_queue(root, readiness, queue))
    frozen_current = _frozen_input_fingerprints(root)
    frozen_canonical = _canonical_frozen_input_fingerprints(root, canonical)
    ready_canonical = _canonical_ready_packet_fingerprints(root, canonical)
    canonical_ready_ids = {
        item["source_packet_id"] for item in ready_canonical
    }
    ready_current = [
        item
        for item in _ready_packet_fingerprints(populations)
        if item["source_packet_id"] in canonical_ready_ids
    ]
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
    errors = [*ownership.errors, *worker_errors, *registry_errors, *readiness_errors, *queue_errors]
    return {
        "schema_version": "1.0", "scope": "SOURCE_RESEARCH_INTEGRATION_AUDIT",
        "canonical_base_checkpoint": canonical,
        "coordinator_input_commit": canonical,
        "selected_batch_ids": sorted(item["batch_id"] for item in workers if isinstance(item.get("batch_id"), str)),
        "workers": worker_records,
        "packet_ownership": [{"source_packet_id": packet.get("source_packet_id"), "research_batch_id": _population_batch_id(population)} for population in populations for packet in _population_packets([population]) if isinstance(packet.get("source_packet_id"), str)],
        "prior_ready_packet_fingerprints": ready_current,
        "canonical_prior_ready_packet_fingerprints": ready_canonical,
        "frozen_input_fingerprints": frozen_current,
        "canonical_frozen_input_fingerprints": frozen_canonical,
        "checks": checks,
        "errors": errors,
        "status": "PASS" if not errors and all(status == "PASS" for status in checks.values()) else "FAIL",
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


def _population_audit(root: Path, population: dict[str, Any]) -> dict[str, Any]:
    batch_id = _population_batch_id(population)
    if not batch_id:
        raise ValueError("integrated source packet population batch ID is missing")
    stem = batch_id.lower().replace("-", "_")
    relative = (
        f"reports/source_packet_pilot_{stem}_audit.json"
        if batch_id == "SRB-089"
        else f"reports/source_packet_wave_{stem}_audit.json"
    )
    audit = read_json(resolve_root_path(root, relative, label="source packet population audit"))
    if not isinstance(audit, dict):
        raise ValueError(f"source packet population audit must be an object: {relative}")
    return audit


def _validate_integrated_populations(
    root: Path,
    populations: list[dict[str, Any]],
    canonical_commit: str,
) -> None:
    errors: list[str] = []
    canonical_populations = _git_integrated_source_packet_populations(
        root, canonical_commit
    )
    canonical_batch_ids = {
        _population_batch_id(item) for item in canonical_populations
    }
    for population in populations:
        audit = _population_audit(root, population)
        if _population_batch_id(population) == "SRB-089":
            result = validate_source_packet_population(root, population, audit)
        else:
            batch_id = _population_batch_id(population)
            if not isinstance(batch_id, str):
                errors.append("integrated source packet population batch ID is missing")
                continue
            audit_base_revision = (
                _population_introduction_parent(root, canonical_commit, batch_id)
                if batch_id in canonical_batch_ids
                else canonical_commit
            )
            audit_base = _git_integrated_source_packet_populations(
                root, audit_base_revision
            )
            result = validate_source_packet_research_batch(
                root,
                population,
                [other for other in populations if other is not population],
                audit,
                audit_base_populations=audit_base,
            )
        errors.extend(result.errors)
    if errors:
        raise ValueError("integrated source packet validation failed: " + "; ".join(errors))


def _validate_source_research_state(
    root: Path, state: SourceResearchState, populations: list[dict[str, Any]], workers: list[dict[str, Any]]
) -> None:
    errors: list[str] = []
    if state.progress != build_source_packet_research_progress(root, populations):
        errors.append("source packet research progress does not match deterministic rebuild")
    for result in (
        validate_source_document_registry(root, populations, state.registry),
        validate_generation_source_readiness(root, populations, state.readiness),
        validate_generation_queue(root, state.readiness, state.queue),
        validate_source_research_integration_audit(
            root, state.audit, populations, state.registry, state.readiness, state.queue, workers
        ),
    ):
        errors.extend(result.errors)
    if state.audit.get("status") != "PASS":
        errors.append("source research integration audit is not PASS")
    if errors:
        raise ValueError("source research state validation failed: " + "; ".join(errors))


def build_source_research_state(root: Path, coordinator_input_commit: str) -> SourceResearchState:
    """Build and validate the entire deterministic coordinator state in memory."""
    root = Path(root).resolve()
    canonical = resolve_git_commit(root, coordinator_input_commit)
    populations = load_integrated_source_packet_populations(root)
    _validate_integrated_populations(root, populations, canonical)
    registry = build_source_document_registry(root, populations)
    readiness = build_generation_source_readiness(root, populations)
    queue = build_generation_queue(root, readiness)
    workers = discover_source_research_workers(root, canonical)
    audit = build_source_research_integration_audit(
        root, canonical, populations, registry, readiness, queue, workers
    )
    state = SourceResearchState(
        progress=build_source_packet_research_progress(root, populations),
        registry=registry,
        readiness=readiness,
        queue=queue,
        audit=audit,
    )
    _validate_source_research_state(root, state, populations, workers)
    return state


def write_source_research_state(root: Path, coordinator_input_commit: str) -> SourceResearchState:
    """Validate every derived artifact before atomically materializing any of them."""
    root = Path(root).resolve()
    state = build_source_research_state(root, coordinator_input_commit)
    write_validated_source_research_state(root, state)
    return state


def write_validated_source_research_state(root: Path, state: SourceResearchState) -> None:
    """Materialize a state that has already passed complete in-memory validation."""
    root = Path(root).resolve()
    for _, relative in _STATE_OUTPUTS:
        resolve_root_path(root, relative, label="source research state output")
    for name, relative in _STATE_OUTPUTS:
        write_json_atomic(resolve_root_path(root, relative, label="source research state output"), getattr(state, name))
