"""Deterministic durable job creation and queue state transitions."""

from copy import deepcopy
from datetime import datetime, timezone
import os
from pathlib import Path
import re

from .config import load_config
from .errors import SchemaValidationError, TransitionError
from .jsonio import read_json, write_json_atomic
from .manifests import validate_manifest_set
from .schema import validate_instance


_REPO_ROOT = Path(__file__).resolve().parents[2]
_QUEUE_STATES = ("pending", "running", "completed", "failed")
_JOB_ID = re.compile(r"^[A-Z0-9]+(?:-[A-Z0-9]+)+$")
_TRANSITIONS = {
    "pending": frozenset({"running", "failed"}),
    "running": frozenset({"completed", "failed"}),
    "failed": frozenset({"pending"}),
    "completed": frozenset(),
}
_SCHEMA_ONLY_TIMESTAMPS = {
    "created_at": "1970-01-01T00:00:00Z",
    "updated_at": "1970-01-01T00:00:00Z",
    "started_at": None,
    "completed_at": None,
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _validate_job(value: object) -> None:
    """Validate a job, adapting deterministic pending storage to the schema.

    Pending files deliberately omit timestamps.  The canonical schema still
    requires the timestamp object, so validation uses a private in-memory
    placeholder without changing the durable bytes.
    """
    candidate = deepcopy(value)
    if (
        isinstance(candidate, dict)
        and candidate.get("status") == "PENDING"
        and "timestamps" not in candidate
    ):
        candidate["timestamps"] = deepcopy(_SCHEMA_ONLY_TIMESTAMPS)
    validate_instance(_REPO_ROOT, "job", candidate)


def _max_attempts(root: Path) -> int:
    config_root = root if (root / "config" / "project.json").is_file() else _REPO_ROOT
    config = load_config(config_root)
    maximum_revisions = config.get("limits", {}).get("maximum_revisions")
    if not isinstance(maximum_revisions, int) or isinstance(maximum_revisions, bool):
        raise SchemaValidationError(
            "project limits.maximum_revisions must be an integer"
        )
    return maximum_revisions + 1


def _generation_job(manifest: dict, batch: dict, max_attempts: int) -> dict:
    batch_id = batch["batch_id"]
    return {
        "job_id": f"JOB-GEN-{batch_id}",
        "batch_id": batch_id,
        "job_type": "GENERATION",
        "status": "PENDING",
        "attempt": 0,
        "max_attempts": max_attempts,
        "inputs": {
            "manifest_path": f"manifests/{manifest['manifest_id']}.json",
            "toronto_notes_pages": batch["toronto_notes"]["tn_pages"],
            "mcc_objectives": list(batch["mcc_objectives"]),
            "prompt_template": "prompts/generate_batch.md",
        },
        "question_ids": list(batch["question_ids"]),
        "requested_roles": ["source-researcher", "question-writer"],
        "artifacts": {
            "candidate": f"candidates/{batch_id}.json",
            "log": f"batches/{batch_id}/generation.log",
        },
        "failure": None,
    }


def _job_paths(root: Path, job_id: str) -> list[Path]:
    return [root / "jobs" / state / f"{job_id}.json" for state in _QUEUE_STATES]


def _existing_job_paths(root: Path, job_id: str) -> list[Path]:
    return [path for path in _job_paths(root, job_id) if path.exists()]


def create_generation_jobs(root: Path, manifests: list[dict]) -> list[Path]:
    """Create deterministic pending generation jobs, idempotently."""
    root = Path(root)
    validate_manifest_set(manifests)
    max_attempts = _max_attempts(root)

    expected_jobs = sorted(
        (
            _generation_job(manifest, batch, max_attempts)
            for manifest in manifests
            for batch in manifest["batches"]
        ),
        key=lambda job: job["job_id"],
    )

    planned: list[tuple[Path, dict, bool]] = []
    for job in expected_jobs:
        _validate_job(job)
        pending_path = root / "jobs" / "pending" / f"{job['job_id']}.json"
        existing = _existing_job_paths(root, job["job_id"])
        if len(existing) > 1:
            raise TransitionError(
                f"job {job['job_id']!r} exists in multiple queue directories"
            )
        if existing:
            existing_path = existing[0]
            existing_value = read_json(existing_path)
            _validate_job(existing_value)
            if existing_path != pending_path:
                raise TransitionError(
                    f"job {job['job_id']!r} already exists in "
                    f"{existing_path.parent.name!r}"
                )
            if existing_value != job:
                raise TransitionError(
                    f"pending job {job['job_id']!r} has different content"
                )
            planned.append((pending_path, job, False))
        else:
            planned.append((pending_path, job, True))

    for pending_path, job, needs_write in planned:
        if needs_write:
            write_json_atomic(pending_path, job)
    return [pending_path for pending_path, _, _ in planned]


def _normalize_target(target: str) -> str:
    if not isinstance(target, str) or target.lower() not in _QUEUE_STATES:
        raise TransitionError(f"unknown job target status: {target!r}")
    return target.lower()


def _load_source_job(root: Path, job_id: str) -> tuple[Path, dict, str]:
    if not isinstance(job_id, str) or _JOB_ID.fullmatch(job_id) is None:
        raise TransitionError(f"invalid job ID: {job_id!r}")
    existing = _existing_job_paths(root, job_id)
    if not existing:
        raise TransitionError(f"job not found: {job_id!r}")
    if len(existing) > 1:
        raise TransitionError(f"job {job_id!r} exists in multiple queue directories")

    source = existing[0]
    source_state = source.parent.name
    value = read_json(source)
    _validate_job(value)
    if not isinstance(value, dict):
        raise SchemaValidationError(f"job {job_id!r} must be a JSON object")
    if value["job_id"] != job_id:
        raise SchemaValidationError(
            f"job filename {job_id!r} disagrees with document ID {value['job_id']!r}"
        )
    if value["status"] != source_state.upper():
        raise SchemaValidationError(
            f"job {job_id!r} status {value['status']!r} disagrees with "
            f"queue directory {source_state!r}"
        )
    return source, value, source_state


def _transitioned_value(
    value: dict, source_state: str, target: str, failure: dict | None
) -> dict:
    if target not in _TRANSITIONS[source_state]:
        if source_state == "completed":
            raise TransitionError("completed job is immutable")
        raise TransitionError(
            f"job transition not allowed: {source_state} -> {target}"
        )
    if target == "failed":
        if failure is None:
            raise TransitionError("failed transition requires failure classification")
    elif failure is not None:
        raise TransitionError("failure classification is only valid for failed jobs")
    if target == "pending" and value["attempt"] >= value["max_attempts"]:
        raise TransitionError("job has exhausted its maximum attempts")

    transitioned = deepcopy(value)
    transitioned["status"] = target.upper()
    transitioned["failure"] = deepcopy(failure) if target == "failed" else None
    if target == "failed":
        transitioned["attempt"] += 1

    if target == "pending":
        transitioned.pop("timestamps", None)
    else:
        now = _utc_now()
        old_timestamps = value.get("timestamps")
        if not isinstance(old_timestamps, dict):
            old_timestamps = {}
        started_at = old_timestamps.get("started_at")
        if target == "running" and started_at is None:
            started_at = now
        transitioned["timestamps"] = {
            "created_at": old_timestamps.get("created_at", now),
            "updated_at": now,
            "started_at": started_at,
            "completed_at": now if target == "completed" else None,
        }

    _validate_job(transitioned)
    return transitioned


def transition_job(
    root: Path, job_id: str, target: str, failure: dict | None = None
) -> Path:
    """Validate, atomically update, and move one job between queue states."""
    root = Path(root)
    target = _normalize_target(target)
    source, value, source_state = _load_source_job(root, job_id)
    transitioned = _transitioned_value(value, source_state, target, failure)
    destination = root / "jobs" / target / f"{job_id}.json"
    if destination.exists():
        raise TransitionError(f"destination job already exists: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)

    write_json_atomic(source, transitioned)
    try:
        os.replace(source, destination)
    except OSError as exc:
        write_json_atomic(source, value)
        raise TransitionError(
            f"unable to move job {job_id!r} from {source_state} to {target}: {exc}"
        ) from exc
    return destination
