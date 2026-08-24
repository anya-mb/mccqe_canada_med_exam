import copy
from datetime import datetime, timezone
from pathlib import Path
import shutil

import pytest

import qbank.progress as progress_module
from qbank.errors import SchemaValidationError
from qbank.jsonio import read_json, write_json_atomic
from qbank.progress import build_progress, write_progress


REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURES = REPO_ROOT / "tests" / "fixtures" / "valid"
FIXED_NOW = datetime(2026, 8, 24, 12, 30, tzinfo=timezone.utc)


@pytest.fixture(autouse=True)
def selected_root_schemas(tmp_path):
    shutil.copytree(REPO_ROOT / "schemas", tmp_path / "schemas", dirs_exist_ok=True)


def _question(identifier: str, status: str) -> dict:
    question = copy.deepcopy(read_json(FIXTURES / "question.json"))
    question["id"] = identifier
    question["status"] = status
    final_status = {
        "CANDIDATE": "PENDING",
        "QA_PASS": "QA_PASS",
        "QUARANTINE": "QUARANTINE",
        "HUMAN_REVIEWED": "HUMAN_REVIEWED",
        "PUBLISHED": "PUBLISHED",
        "RETIRED": "RETIRED",
    }[status]
    question["verification"]["final_status"] = final_status
    if status in {"QA_PASS", "HUMAN_REVIEWED", "PUBLISHED", "RETIRED"}:
        question["verification"].update(
            blind_verifier_answer="A",
            blind_verifier_confidence=0.95,
            key_match=True,
            ambiguity=False,
            reference_check=True,
            guideline_check=True,
            duplicate_check=True,
        )
    if status == "HUMAN_REVIEWED":
        question["human_review"] = {
            "reviewer_name": "Synthetic Reviewer",
            "credentials": "Synthetic Credential",
            "reviewed_at": "2026-08-24T11:00:00Z",
            "scope": "Full synthetic item review",
        }
    return question


def _job(identifier: str) -> dict:
    job = copy.deepcopy(read_json(FIXTURES / "job.json"))
    job["job_id"] = identifier
    job["batch_id"] = identifier.removeprefix("JOB-GEN-")
    job["status"] = "PENDING"
    job.pop("timestamps", None)
    return job


def _populate(root: Path) -> None:
    schema = root / "schemas" / "manifest.schema.json"
    schema.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(REPO_ROOT / "schemas" / "manifest.schema.json", schema)
    manifest = read_json(FIXTURES / "manifest.json")
    write_json_atomic(root / "manifests" / "synthetic.json", manifest)
    write_json_atomic(
        root / "candidates" / "SYN-UNIT-001.json",
        _question("SYN-UNIT-001", "CANDIDATE"),
    )
    write_json_atomic(
        root / "verified" / "SYN-UNIT-002.json",
        _question("SYN-UNIT-002", "QA_PASS"),
    )
    write_json_atomic(
        root / "quarantine" / "SYN-UNIT-003.json",
        _question("SYN-UNIT-003", "QUARANTINE"),
    )
    write_json_atomic(
        root / "jobs" / "pending" / "JOB-GEN-SYN-BATCH-001.json",
        _job("JOB-GEN-SYN-BATCH-001"),
    )
    write_json_atomic(
        root / "jobs" / "pending" / "JOB-GEN-SYN-BATCH-002.json",
        _job("JOB-GEN-SYN-BATCH-002"),
    )


def test_progress_counts_filesystem_truth_by_discipline_and_chapter(tmp_path):
    """Catches reports that reuse targets or manually entered totals."""
    _populate(tmp_path)

    report = build_progress(tmp_path, now=FIXED_NOW)

    assert report["generated_at"] == "2026-08-24T12:30:00Z"
    assert report["planned"] == 40
    assert report["generated"] == 3
    assert report["blind_passed"] == 1
    assert report["qa_passed"] == 1
    assert report["quarantined"] == 1
    assert report["jobs"] == {
        "pending": 2,
        "running": 0,
        "completed": 0,
        "failed": 0,
    }
    expected_breakdown = {
        "planned": 40,
        "generated": 3,
        "blind_passed": 1,
        "qa_passed": 1,
    }
    assert report["disciplines"] == {"Synthetic Discipline": expected_breakdown}
    assert report["chapters"] == {"Synthetic Chapter": expected_breakdown}
    assert report["coverage_gaps"] == [
        "Synthetic Chapter: 39 questions remain"
    ]


def test_write_progress_emits_schema_valid_json_and_deterministic_markdown(tmp_path):
    """Catches Markdown built from a second filesystem walk or unstable ordering."""
    _populate(tmp_path)

    json_path, markdown_path = write_progress(tmp_path, now=FIXED_NOW)

    assert json_path == tmp_path / "reports" / "progress.json"
    assert read_json(json_path) == build_progress(tmp_path, now=FIXED_NOW)
    assert markdown_path.read_text(encoding="utf-8") == (
        "# Qbank Progress\n\n"
        "Generated at: 2026-08-24T12:30:00Z\n\n"
        "## Totals\n\n"
        "| Metric | Count |\n"
        "| --- | ---: |\n"
        "| Planned | 40 |\n"
        "| Generated | 3 |\n"
        "| Blind passed | 1 |\n"
        "| QA passed | 1 |\n"
        "| Human reviewed | 0 |\n"
        "| Rejected | 0 |\n"
        "| Quarantined | 1 |\n\n"
        "## Disciplines\n\n"
        "| Discipline | Planned | Generated | Blind passed | QA passed |\n"
        "| --- | ---: | ---: | ---: | ---: |\n"
        "| Synthetic Discipline | 40 | 3 | 1 | 1 |\n\n"
        "## Chapters\n\n"
        "| Chapter | Planned | Generated | Blind passed | QA passed |\n"
        "| --- | ---: | ---: | ---: | ---: |\n"
        "| Synthetic Chapter | 40 | 3 | 1 | 1 |\n\n"
        "## Jobs\n\n"
        "| State | Count |\n"
        "| --- | ---: |\n"
        "| Pending | 2 |\n"
        "| Running | 0 |\n"
        "| Completed | 0 |\n"
        "| Failed | 0 |\n\n"
        "## Coverage gaps\n\n"
        "- Synthetic Chapter: 39 questions remain\n"
    )


def test_progress_rejects_human_review_without_complete_reviewer_metadata(tmp_path):
    """Catches HUMAN_REVIEWED counts derived from status without review evidence."""
    _populate(tmp_path)
    human = _question("SYN-UNIT-004", "HUMAN_REVIEWED")
    human["human_review"] = {
        "reviewer_name": "Synthetic Reviewer",
        "credentials": "   ",
        "reviewed_at": "2026-08-24T11:00:00Z",
        "scope": "Full synthetic item review",
    }
    write_json_atomic(tmp_path / "verified" / "SYN-UNIT-004.json", human)

    with pytest.raises(SchemaValidationError, match="human review metadata"):
        build_progress(tmp_path, now=FIXED_NOW)


def test_progress_rejects_qa_pass_question_under_candidates(tmp_path):
    """Catches publication coverage inferred from status in the wrong lifecycle tree."""
    _populate(tmp_path)
    write_json_atomic(
        tmp_path / "candidates" / "SYN-UNIT-004.json",
        _question("SYN-UNIT-004", "QA_PASS"),
    )

    with pytest.raises(SchemaValidationError, match="candidates.*QA_PASS"):
        build_progress(tmp_path, now=FIXED_NOW)


def test_retired_question_has_a_persistable_directory_and_verification_contract(
    tmp_path,
):
    """Catches retirement discarding the item's completed verification history."""
    _populate(tmp_path)
    write_json_atomic(
        tmp_path / "retired" / "SYN-UNIT-004.json",
        _question("SYN-UNIT-004", "RETIRED"),
    )

    report = build_progress(tmp_path, now=FIXED_NOW)

    assert report["generated"] == 4
    assert report["blind_passed"] == 2
    assert report["qa_passed"] == 2
    assert report["coverage_gaps"] == ["Synthetic Chapter: 39 questions remain"]


def test_progress_rejects_status_that_disagrees_with_verification_final_status(
    tmp_path,
):
    """Catches QA coverage inferred without matching final verification evidence."""
    _populate(tmp_path)
    question_path = tmp_path / "verified" / "SYN-UNIT-002.json"
    question = read_json(question_path)
    question["verification"]["final_status"] = "PENDING"
    write_json_atomic(question_path, question)

    with pytest.raises(SchemaValidationError, match="final_status.*QA_PASS"):
        build_progress(tmp_path, now=FIXED_NOW)


def test_progress_rejects_relabelled_candidate_as_qa_coverage(tmp_path):
    """Catches coverage counts based only on spoofed status labels."""
    _populate(tmp_path)
    relabelled = read_json(
        REPO_ROOT / "tests/fixtures/adversarial/relabeled-candidate.json"
    )
    write_json_atomic(tmp_path / "verified/relabelled.json", relabelled)

    with pytest.raises(SchemaValidationError, match="publication eligibility"):
        build_progress(tmp_path, now=FIXED_NOW)


def test_progress_uses_selected_root_question_schema(tmp_path):
    """Catches lifecycle validation against module-relative question schemas."""
    _populate(tmp_path)
    schema_path = tmp_path / "schemas/question.schema.json"
    schema = read_json(schema_path)
    schema["required"].append("selected_root_marker")
    write_json_atomic(schema_path, schema)

    with pytest.raises(SchemaValidationError, match="selected_root_marker"):
        build_progress(tmp_path, now=FIXED_NOW)


def test_markdown_failure_leaves_canonical_progress_json_unchanged(
    tmp_path, monkeypatch
):
    """Catches half-written report pairs with a newer canonical JSON snapshot."""
    _populate(tmp_path)
    json_path = tmp_path / "reports/progress.json"
    write_json_atomic(json_path, {"sentinel": "old canonical report"})

    def fail_markdown(*_args, **_kwargs):
        raise OSError("synthetic markdown failure")

    monkeypatch.setattr(progress_module, "_write_text_atomic", fail_markdown)

    with pytest.raises(OSError, match="markdown failure"):
        write_progress(tmp_path, now=FIXED_NOW)

    assert read_json(json_path) == {"sentinel": "old canonical report"}


def test_progress_rejects_symlinked_report_ancestor_without_external_write(tmp_path):
    """Catches reports/ redirecting canonical progress writes externally."""
    _populate(tmp_path)
    reports = tmp_path / "reports"
    if reports.exists():
        shutil.rmtree(reports)
    external = tmp_path.parent / f"{tmp_path.name}-external-reports"
    external.mkdir()
    marker = external / "marker.txt"
    marker.write_text("external unchanged", encoding="utf-8")
    reports.symlink_to(external, target_is_directory=True)

    with pytest.raises(SchemaValidationError, match="symlink"):
        write_progress(tmp_path, now=FIXED_NOW)

    assert marker.read_text(encoding="utf-8") == "external unchanged"
    assert not (external / "progress.json").exists()
