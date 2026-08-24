import copy
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
VALID_FIXTURES = REPO_ROOT / "tests" / "fixtures" / "valid"
COMMANDS = (
    "validate-project",
    "validate-source",
    "validate-manifests",
    "create-jobs",
    "create-blind",
    "evaluate-blind",
    "progress",
    "export",
)
EXPECTED_DISCIPLINES = (
    ("Medicine", "MED"),
    ("Obstetrics & Gynecology", "OBGYN"),
    ("Pediatrics", "PED"),
    ("PHELO", "PHELO"),
    ("Psychiatry", "PSY"),
    ("Surgery", "SURG"),
)


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run_cli(root: Path, command: str, *arguments: str) -> subprocess.CompletedProcess:
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(REPO_ROOT / "scripts")
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "qbank.cli",
            command,
            *arguments,
            "--root",
            str(root),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        env=environment,
    )


@pytest.fixture
def repo_root() -> Path:
    return REPO_ROOT


@pytest.fixture
def project_copy(tmp_path: Path) -> Path:
    for relative in (
        "app",
        "blind",
        "blind_verification",
        "candidates",
        "config",
        "jobs",
        "manifests",
        "prompts",
        "quarantine",
        "references",
        "rejected",
        "reports",
        "retired",
        "schemas",
        "tests/fixtures/valid",
        "verified",
    ):
        source = REPO_ROOT / relative
        destination = tmp_path / relative
        shutil.copytree(source, destination)
    return tmp_path


def remove_local_source(root: Path) -> None:
    (root / "config" / "project.local.json").unlink()


def install_six_manifests(
    root: Path, identities=EXPECTED_DISCIPLINES
) -> None:
    template = read_json(VALID_FIXTURES / "manifest.json")
    for index, (discipline, code) in enumerate(identities, start=1):
        manifest = copy.deepcopy(template)
        chapter = f"Synthetic Chapter {index}"
        manifest["manifest_id"] = f"MANIFEST-{code}-2026.1"
        manifest["discipline"] = discipline
        manifest["discipline_code"] = code
        manifest["sections"][0]["chapter"] = chapter
        batch = manifest["batches"][0]
        batch["batch_id"] = f"{code}-BATCH-001"
        batch["chapter"] = chapter
        batch["toronto_notes"]["chapter"] = chapter
        batch["question_ids"] = [
            f"{code}-UNIT-{number:03d}" for number in range(1, 41)
        ]
        write_json(root / "manifests" / f"{code.lower()}.json", manifest)


def test_validate_project_succeeds(repo_root):
    result = run_cli(repo_root, "validate-project")

    assert result.returncode == 0, result.stderr
    assert "PROJECT_VALID" in result.stdout
    assert "GENERATION_BLOCKED" in result.stdout
    assert result.stderr == ""


def test_validate_project_stops_on_missing_source(project_copy):
    remove_local_source(project_copy)

    result = run_cli(project_copy, "validate-project")

    assert result.returncode != 0
    assert result.stdout == ""
    assert result.stderr.startswith("SOURCE_FAILURE: ")


def test_validate_project_rejects_missing_prompt_before_source_validation(project_copy):
    (project_copy / "prompts" / "generate_batch.md").unlink()

    result = run_cli(project_copy, "validate-project")

    assert result.returncode != 0
    assert result.stderr.startswith("PROMPT_FAILURE: ")


def test_create_jobs_requires_all_six_valid_manifests(project_copy):
    result = run_cli(project_copy, "create-jobs")

    assert result.returncode != 0
    assert result.stdout == ""
    assert result.stderr.startswith("SCHEMA_FAILURE: ")
    assert "six manifests" in result.stderr.lower()


def test_six_valid_manifests_create_one_job_per_batch(project_copy):
    install_six_manifests(project_copy)

    result = run_cli(project_copy, "create-jobs")

    assert result.returncode == 0, result.stderr
    assert result.stdout == "JOBS_CREATED: 6\n"
    jobs = [
        read_json(path)
        for path in (project_copy / "jobs" / "pending").glob("*.json")
    ]
    assert len(jobs) == 6
    assert {job["inputs"]["manifest_path"] for job in jobs} == {
        f"manifests/{code.casefold()}.json" for _, code in EXPECTED_DISCIPLINES
    }
    assert all(
        (project_copy / job["inputs"]["manifest_path"]).is_file() for job in jobs
    )


@pytest.mark.parametrize("command", COMMANDS)
def test_every_command_documents_root_option(repo_root, command):
    result = run_cli(repo_root, command, "--help")

    assert result.returncode == 0, result.stderr
    assert "--root" in result.stdout


def test_validate_manifests_accepts_an_empty_foundation(project_copy):
    result = run_cli(project_copy, "validate-manifests")

    assert result.returncode == 0, result.stderr
    assert result.stdout == "MANIFESTS_VALID: 0 manifests, 0 batches, 0 questions\n"


def test_create_blind_writes_only_the_allowlisted_packet(project_copy):
    candidate = project_copy / "candidates" / "SYN-UNIT-001.json"
    value = read_json(VALID_FIXTURES / "question.json")
    value["status"] = "STRUCTURE_PASS"
    write_json(candidate, value)

    result = run_cli(project_copy, "create-blind", "candidates/SYN-UNIT-001.json")

    assert result.returncode == 0, result.stderr
    packet = read_json(project_copy / "blind" / "SYN-UNIT-001.json")
    assert packet["question_id"] == "SYN-UNIT-001"
    assert "correct_answer" not in packet
    assert "explanation" not in packet
    assert result.stdout == "BLIND_PACKET_CREATED: blind/SYN-UNIT-001.json\n"


def test_evaluate_blind_reports_a_matching_independent_result(project_copy):
    candidate = project_copy / "candidates" / "SYN-UNIT-001.json"
    result_path = project_copy / "blind_verification" / "SYN-UNIT-001.json"
    value = read_json(VALID_FIXTURES / "question.json")
    value["status"] = "STRUCTURE_PASS"
    write_json(candidate, value)
    shutil.copyfile(VALID_FIXTURES / "blind-verification.json", result_path)

    result = run_cli(
        project_copy,
        "evaluate-blind",
        "candidates/SYN-UNIT-001.json",
        "blind_verification/SYN-UNIT-001.json",
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout == "BLIND_DECISION: BLIND_PASS BLIND_PASS\n"


def test_progress_and_export_delegate_to_validated_filesystem_modules(project_copy):
    progress_result = run_cli(project_copy, "progress")

    assert progress_result.returncode == 0, progress_result.stderr
    assert progress_result.stdout == (
        "PROGRESS_WRITTEN: reports/progress.json reports/progress.md\n"
    )
    assert (project_copy / "reports" / "progress.json").is_file()

    export_result = run_cli(project_copy, "export", "--version", "2026.1")

    assert export_result.returncode == 0, export_result.stderr
    assert export_result.stdout == "EXPORT_COMPLETE: 0 questions, 0 references\n"
    manifest = read_json(project_copy / "app/public/data/qbank/manifest.json")
    assert manifest["question_count"] == 0


def test_schema_failure_is_machine_readable(project_copy):
    fixture = project_copy / "tests/fixtures/valid/question.json"
    value = read_json(fixture)
    value["question"]["options"].pop()
    write_json(fixture, value)

    result = run_cli(project_copy, "validate-project")

    assert result.returncode != 0
    assert result.stderr.startswith("SCHEMA_FAILURE: ")
    assert "\n" not in result.stderr.rstrip("\n")


def test_create_blind_rejects_traversal_output_without_touching_external_data(
    project_copy
):
    """Catches --output escaping the selected root via .. components."""
    candidate = project_copy / "candidates/SYN-UNIT-001.json"
    value = read_json(VALID_FIXTURES / "question.json")
    value["status"] = "STRUCTURE_PASS"
    write_json(candidate, value)
    escaped = project_copy.parent / "escaped-blind.json"

    result = run_cli(
        project_copy,
        "create-blind",
        "candidates/SYN-UNIT-001.json",
        "--output",
        "../escaped-blind.json",
    )

    assert result.returncode != 0
    assert not escaped.exists()


def test_create_blind_rejects_absolute_candidate_even_when_it_is_inside_root(
    project_copy
):
    """Catches absolute path policy being weakened to a containment check."""
    candidate = project_copy / "candidates/SYN-UNIT-001.json"
    value = read_json(VALID_FIXTURES / "question.json")
    value["status"] = "STRUCTURE_PASS"
    write_json(candidate, value)

    result = run_cli(project_copy, "create-blind", str(candidate))

    assert result.returncode != 0
    assert "absolute" in result.stderr.lower()


def test_create_blind_rejects_symlinked_output_ancestor_without_external_write(
    project_copy
):
    """Catches blind/ redirecting default output outside the selected root."""
    candidate = project_copy / "candidates/SYN-UNIT-001.json"
    value = read_json(VALID_FIXTURES / "question.json")
    value["status"] = "STRUCTURE_PASS"
    write_json(candidate, value)
    shutil.rmtree(project_copy / "blind")
    external = project_copy.parent / "external-blind"
    external.mkdir()
    (project_copy / "blind").symlink_to(external, target_is_directory=True)

    result = run_cli(project_copy, "create-blind", "candidates/SYN-UNIT-001.json")

    assert result.returncode != 0
    assert not (external / "SYN-UNIT-001.json").exists()


def test_create_jobs_rejects_six_unexpected_discipline_identities(project_copy):
    """Catches readiness based on cardinality rather than the required disciplines."""
    unexpected = tuple(
        (f"Synthetic Discipline {index}", f"S{index}")
        for index in range(1, 7)
    )
    install_six_manifests(project_copy, identities=unexpected)

    result = run_cli(project_copy, "create-jobs")

    assert result.returncode != 0
    assert result.stderr.startswith("SCHEMA_FAILURE: ")
    assert "expected discipline" in result.stderr.lower()


def test_create_jobs_rejects_duplicate_expected_discipline_identity(project_copy):
    """Catches one required discipline replacing another under a duplicate label."""
    install_six_manifests(project_copy)
    surgery_path = project_copy / "manifests/surg.json"
    surgery = read_json(surgery_path)
    surgery["discipline"] = "Medicine"
    surgery["discipline_code"] = "MED"
    write_json(surgery_path, surgery)

    result = run_cli(project_copy, "create-jobs")

    assert result.returncode != 0
    assert "discipline" in result.stderr.lower()


def test_malformed_config_has_normalized_cli_failure_class(project_copy):
    """Catches malformed config being reported as QBANK_FAILURE."""
    (project_copy / "config/project.json").write_text("{", encoding="utf-8")

    result = run_cli(project_copy, "validate-project")

    assert result.returncode != 0
    assert result.stderr.startswith("CONFIG_FAILURE: ")


def test_malformed_schema_has_normalized_cli_failure_class(project_copy):
    """Catches malformed schemas being reported as QBANK_FAILURE."""
    (project_copy / "schemas/question.schema.json").write_text("{", encoding="utf-8")

    result = run_cli(project_copy, "validate-project")

    assert result.returncode != 0
    assert result.stderr.startswith("SCHEMA_FAILURE: ")
