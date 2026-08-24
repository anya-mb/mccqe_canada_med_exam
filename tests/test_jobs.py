import copy
from pathlib import Path
import shutil

import pytest

import qbank.jobs as jobs_module
from qbank.errors import SchemaValidationError, TransitionError
from qbank.jobs import create_generation_jobs, transition_job
from qbank.jsonio import read_json, write_json_atomic
from qbank.manifests import ManifestDocument
from qbank.schema import validate_instance


REPO_ROOT = Path(__file__).resolve().parents[1]
VALID_MANIFEST = REPO_ROOT / "tests" / "fixtures" / "valid" / "manifest.json"
NOW = "2026-08-24T12:00:00Z"


@pytest.fixture
def valid_manifest():
    return copy.deepcopy(read_json(VALID_MANIFEST))


def manifest_document(value, relative_path="manifests/synthetic.json"):
    return ManifestDocument(relative_path=relative_path, value=value)


@pytest.fixture(autouse=True)
def project_schema_and_fixed_clock(tmp_path, monkeypatch):
    monkeypatch.setattr(jobs_module, "_utc_now", lambda: NOW)
    schema = tmp_path / "schemas" / "manifest.schema.json"
    schema.parent.mkdir(parents=True)
    shutil.copyfile(REPO_ROOT / "schemas" / "manifest.schema.json", schema)


@pytest.fixture
def pending_job(tmp_path, valid_manifest):
    path = create_generation_jobs(tmp_path, [manifest_document(valid_manifest)])[0]
    return read_json(path)


def test_generation_jobs_use_stable_paths_and_schema_shaped_content(
    tmp_path, valid_manifest
):
    [path] = create_generation_jobs(tmp_path, [manifest_document(valid_manifest)])
    value = read_json(path)

    assert path == tmp_path / "jobs/pending/JOB-GEN-SYN-BATCH-001.json"
    assert value["job_id"] == "JOB-GEN-SYN-BATCH-001"
    assert value["inputs"]["manifest_path"] == "manifests/synthetic.json"
    assert value["question_ids"] == valid_manifest["batches"][0]["question_ids"]
    assert value["attempt"] == 0
    assert value["max_attempts"] == 3
    assert "timestamps" not in value
    validate_instance(REPO_ROOT, "job", value)


def test_generation_jobs_are_deterministic(tmp_path, valid_manifest):
    documents = [manifest_document(valid_manifest)]
    first = create_generation_jobs(tmp_path, documents)
    first_bytes = [path.read_bytes() for path in first]

    second = create_generation_jobs(tmp_path, documents)

    assert second == first
    assert [path.read_bytes() for path in second] == first_bytes


def test_generation_jobs_use_the_project_root_revision_limit(
    tmp_path, valid_manifest
):
    write_json_atomic(
        tmp_path / "config/project.json",
        {
            "research_mode": "CODEX_NATIVE",
            "limits": {"maximum_revisions": 4},
        },
    )

    [path] = create_generation_jobs(tmp_path, [manifest_document(valid_manifest)])

    assert read_json(path)["max_attempts"] == 5


def test_generation_job_order_is_independent_of_manifest_input_order(
    tmp_path, valid_manifest
):
    other = copy.deepcopy(valid_manifest)
    other["manifest_id"] = "MANIFEST-ALT-2026.1"
    other["discipline"] = "Alternative Synthetic Discipline"
    other["discipline_code"] = "ALT"
    other["batches"][0]["batch_id"] = "ALT-BATCH-001"
    other["batches"][0]["question_ids"] = [
        f"ALT-UNIT-{number:03d}" for number in range(1, 41)
    ]

    paths = create_generation_jobs(
        tmp_path,
        [
            manifest_document(valid_manifest),
            manifest_document(other, "manifests/alternative.json"),
        ],
    )

    assert [path.stem for path in paths] == [
        "JOB-GEN-ALT-BATCH-001",
        "JOB-GEN-SYN-BATCH-001",
    ]


def test_existing_pending_job_with_different_content_is_a_conflict(
    tmp_path, valid_manifest
):
    documents = [manifest_document(valid_manifest)]
    [path] = create_generation_jobs(tmp_path, documents)
    changed = read_json(path)
    changed["artifacts"]["candidate"] = "candidates/conflicting.json"
    write_json_atomic(path, changed)

    with pytest.raises(TransitionError, match="different content"):
        create_generation_jobs(tmp_path, documents)


def test_failed_job_preserves_artifacts_and_increments_attempt(
    tmp_path, pending_job
):
    log = tmp_path / pending_job["artifacts"]["log"]
    candidate = tmp_path / pending_job["artifacts"]["candidate"]
    log.parent.mkdir(parents=True)
    candidate.parent.mkdir(parents=True)
    log.write_text("synthetic failure log\n", encoding="utf-8")
    candidate.write_text("synthetic partial artifact\n", encoding="utf-8")

    failed = transition_job(
        tmp_path,
        pending_job["job_id"],
        "failed",
        {"class": "SOURCE_FAILURE", "message": "unavailable"},
    )
    value = read_json(failed)

    assert failed == tmp_path / f"jobs/failed/{pending_job['job_id']}.json"
    assert not (tmp_path / f"jobs/pending/{pending_job['job_id']}.json").exists()
    assert value["attempt"] == 1
    assert value["failure"]["class"] == "SOURCE_FAILURE"
    assert value["artifacts"] == pending_job["artifacts"]
    assert log.read_text(encoding="utf-8") == "synthetic failure log\n"
    assert candidate.read_text(encoding="utf-8") == "synthetic partial artifact\n"
    validate_instance(REPO_ROOT, "job", value)


def test_failure_requires_a_schema_valid_classification(tmp_path, pending_job):
    with pytest.raises(SchemaValidationError, match="failure"):
        transition_job(
            tmp_path,
            pending_job["job_id"],
            "failed",
            {"class": "UNKNOWN", "message": "unavailable"},
        )

    assert (tmp_path / f"jobs/pending/{pending_job['job_id']}.json").is_file()
    assert not (tmp_path / f"jobs/failed/{pending_job['job_id']}.json").exists()


def test_retry_is_a_schema_valid_timestamp_free_pending_job(tmp_path, pending_job):
    transition_job(
        tmp_path,
        pending_job["job_id"],
        "failed",
        {"class": "SOURCE_FAILURE", "message": "unavailable"},
    )

    retried = transition_job(tmp_path, pending_job["job_id"], "pending")
    value = read_json(retried)

    assert value["status"] == "PENDING"
    assert value["attempt"] == 1
    assert "timestamps" not in value
    validate_instance(REPO_ROOT, "job", value)


def test_transition_moves_atomically_and_adds_deterministic_timestamps(
    tmp_path, pending_job
):
    running = transition_job(tmp_path, pending_job["job_id"], "running")
    running_value = read_json(running)

    assert running_value["status"] == "RUNNING"
    assert running_value["timestamps"] == {
        "created_at": NOW,
        "updated_at": NOW,
        "started_at": NOW,
        "completed_at": None,
    }
    assert not (tmp_path / f"jobs/pending/{pending_job['job_id']}.json").exists()
    validate_instance(REPO_ROOT, "job", read_json(running))

    completed = transition_job(tmp_path, pending_job["job_id"], "completed")
    completed_value = read_json(completed)

    assert completed_value["status"] == "COMPLETED"
    assert completed_value["timestamps"]["started_at"] == NOW
    assert completed_value["timestamps"]["completed_at"] == NOW
    assert not running.exists()
    validate_instance(REPO_ROOT, "job", completed_value)


def test_completed_job_and_artifacts_are_never_mutated(tmp_path, pending_job):
    transition_job(tmp_path, pending_job["job_id"], "running")
    completed = transition_job(tmp_path, pending_job["job_id"], "completed")
    artifact = tmp_path / pending_job["artifacts"]["candidate"]
    artifact.parent.mkdir(parents=True)
    artifact.write_text("synthetic completed artifact\n", encoding="utf-8")
    before = completed.read_bytes()

    with pytest.raises(TransitionError, match="completed job"):
        transition_job(
            tmp_path,
            pending_job["job_id"],
            "failed",
            {"class": "TECHNICAL_FAILURE", "message": "late failure"},
        )

    assert completed.read_bytes() == before
    assert artifact.read_text(encoding="utf-8") == "synthetic completed artifact\n"


@pytest.mark.parametrize(
    ("target", "failure"),
    [
        ("completed", None),
        ("pending", None),
        ("running", {"class": "SOURCE_FAILURE", "message": "unexpected"}),
    ],
)
def test_invalid_job_transitions_leave_source_unchanged(
    tmp_path, pending_job, target, failure
):
    source = tmp_path / f"jobs/pending/{pending_job['job_id']}.json"
    before = source.read_bytes()

    with pytest.raises(TransitionError):
        transition_job(tmp_path, pending_job["job_id"], target, failure)

    assert source.read_bytes() == before
