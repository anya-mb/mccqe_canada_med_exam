"""Deterministic durable job creation and queue state transitions."""

from copy import deepcopy
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import os
from pathlib import Path
import re

from .config import load_config
from .errors import SchemaValidationError, TransitionError
from .jsonio import read_json, write_json_atomic
from .manifests import ManifestDocument, validate_manifest_set
from .paths import RootPathError, canonical_root, resolve_root_path
from .schema import validate_instance


_QUEUE_STATES = ("pending", "running", "completed", "failed")
_JOB_ID = re.compile(r"^[A-Z0-9]+(?:-[A-Z0-9]+)+$")
_TRANSITIONS = {
    "pending": frozenset({"running", "failed"}),
    "running": frozenset({"completed", "failed"}),
    "failed": frozenset({"pending"}),
    "completed": frozenset(),
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _max_attempts(root: Path) -> int:
    config = load_config(root)
    maximum_revisions = config.get("limits", {}).get("maximum_revisions")
    if not isinstance(maximum_revisions, int) or isinstance(maximum_revisions, bool):
        raise SchemaValidationError(
            "project limits.maximum_revisions must be an integer"
        )
    return maximum_revisions + 1


def _generation_job(
    document: ManifestDocument, batch: dict, max_attempts: int
) -> dict:
    manifest = document.value
    batch_id = batch["batch_id"]
    return {
        "job_id": f"JOB-GEN-{batch_id}",
        "batch_id": batch_id,
        "job_type": "GENERATION",
        "status": "PENDING",
        "attempt": 0,
        "max_attempts": max_attempts,
        "inputs": {
            "manifest_path": document.relative_path,
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
    try:
        return [
            resolve_root_path(
                root,
                Path("jobs") / state / f"{job_id}.json",
                label="job queue path",
            )
            for state in _QUEUE_STATES
        ]
    except RootPathError as exc:
        raise TransitionError(str(exc)) from exc


def _existing_job_paths(root: Path, job_id: str) -> list[Path]:
    return [path for path in _job_paths(root, job_id) if path.exists()]


def create_generation_jobs(
    root: Path, manifests: list[ManifestDocument]
) -> list[Path]:
    """Create deterministic pending generation jobs, idempotently."""
    try:
        root = canonical_root(root)
    except RootPathError as exc:
        raise TransitionError(str(exc)) from exc
    validate_manifest_set(root, [document.value for document in manifests])
    max_attempts = _max_attempts(root)

    expected_jobs = sorted(
        (
            _generation_job(document, batch, max_attempts)
            for document in manifests
            for batch in document.value["batches"]
        ),
        key=lambda job: job["job_id"],
    )

    planned: list[tuple[Path, dict, bool]] = []
    for job in expected_jobs:
        validate_instance(root, "job", job)
        pending_path = _job_paths(root, job["job_id"])[0]
        existing = _existing_job_paths(root, job["job_id"])
        if len(existing) > 1:
            raise TransitionError(
                f"job {job['job_id']!r} exists in multiple queue directories"
            )
        if existing:
            existing_path = existing[0]
            existing_value = read_json(existing_path)
            validate_instance(root, "job", existing_value)
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


def _validate_job_id(job_id: object) -> str:
    if not isinstance(job_id, str) or _JOB_ID.fullmatch(job_id) is None:
        raise TransitionError(f"invalid job ID: {job_id!r}")
    return job_id


@contextmanager
def _job_lock(root: Path, job_id: str):
    """Claim one job non-blockingly for the complete read/transition/move."""
    try:
        lock_path = resolve_root_path(
            root,
            Path("jobs") / ".locks" / f"{job_id}.lock",
            label="job lock path",
        )
    except RootPathError as exc:
        raise TransitionError(str(exc)) from exc
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o600)
    except OSError as exc:
        raise TransitionError(f"unable to open job lock: {lock_path}") from exc
    with os.fdopen(descriptor, "a+") as lock_file:
        try:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise TransitionError(f"job {job_id!r} transition already in progress") from exc
        except OSError as exc:
            raise TransitionError(f"unable to claim job {job_id!r}") from exc
        try:
            yield
        finally:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


def _load_source_job(root: Path, job_id: str) -> tuple[Path, dict, str]:
    _validate_job_id(job_id)
    existing = _existing_job_paths(root, job_id)
    if not existing:
        raise TransitionError(f"job not found: {job_id!r}")
    if len(existing) > 1:
        raise TransitionError(f"job {job_id!r} exists in multiple queue directories")

    source = existing[0]
    source_state = source.parent.name
    value = read_json(source)
    validate_instance(root, "job", value)
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

    return transitioned


def _validate_transitioned_value(root: Path, transitioned: dict) -> None:
    validate_instance(root, "job", transitioned)


def transition_job(
    root: Path, job_id: str, target: str, failure: dict | None = None
) -> Path:
    """Validate, atomically update, and move one job between queue states."""
    try:
        root = canonical_root(root)
    except RootPathError as exc:
        raise TransitionError(str(exc)) from exc
    job_id = _validate_job_id(job_id)
    target = _normalize_target(target)
    with _job_lock(root, job_id):
        source, value, source_state = _load_source_job(root, job_id)
        transitioned = _transitioned_value(value, source_state, target, failure)
        _validate_transitioned_value(root, transitioned)
        destination = _job_paths(root, job_id)[_QUEUE_STATES.index(target)]
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
