import copy
from datetime import datetime, timezone
import os
from pathlib import Path

import pytest

import qbank.export as export_module
from qbank.errors import ExportError
from qbank.export import build_production
from qbank.jsonio import read_json, write_json_atomic


REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURES = REPO_ROOT / "tests" / "fixtures" / "valid"
FIXED_NOW = datetime(2026, 8, 24, 12, 30, tzinfo=timezone.utc)
REVIEW = {
    "reviewer_name": "Synthetic Reviewer",
    "credentials": "Synthetic Credential",
    "reviewed_at": "2026-08-24T11:00:00Z",
    "scope": "Full synthetic item review",
}


def _question(identifier: str, status: str, reference_id: str = "REF-SYN-001") -> dict:
    question = copy.deepcopy(read_json(FIXTURES / "question.json"))
    question["id"] = identifier
    question["status"] = status
    question["references"] = [reference_id]
    question["verification"]["final_status"] = (
        status if status in {"QA_PASS", "HUMAN_REVIEWED"} else "PENDING"
    )
    if status in {"QA_PASS", "HUMAN_REVIEWED"}:
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
        question["human_review"] = dict(REVIEW)
    return question


def _populate(root: Path) -> None:
    registry = copy.deepcopy(read_json(FIXTURES / "reference-registry.json"))
    unused = copy.deepcopy(registry["references"][0])
    unused.update(
        reference_id="REF-UNUSED-001",
        title="Unused Synthetic Standard",
        url="https://example.invalid/unused-standard",
    )
    registry["references"].append(unused)
    write_json_atomic(root / "references" / "registry.json", registry)
    write_json_atomic(
        root / "verified" / "qa.json", _question("SYN-UNIT-001", "QA_PASS")
    )
    write_json_atomic(
        root / "verified" / "human.json",
        _question("SYN-UNIT-002", "HUMAN_REVIEWED"),
    )
    for directory, identifier, status in (
        ("candidates", "CANDIDATE-1", "CANDIDATE"),
        ("rejected", "REJECTED-1", "REJECTED"),
        ("retired", "RETIRED-1", "RETIRED"),
        ("quarantine", "QUARANTINE-1", "QUARANTINE"),
    ):
        write_json_atomic(root / directory / f"{identifier}.json", _question(identifier, status))
    write_json_atomic(
        root / "blind_verification" / "private-reasoning.json",
        {"verifier_reasoning": "must never be exported"},
    )


def _seed_live_output(root: Path) -> Path:
    marker = root / "app" / "public" / "data" / "qbank" / "old-marker.txt"
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text("old production", encoding="utf-8")
    return marker


def test_export_includes_only_verified_publication_eligible_items(tmp_path):
    """Catches exporters that crawl non-verified lifecycle directories."""
    _populate(tmp_path)

    result = build_production(tmp_path, "2026.1", FIXED_NOW)

    assert result["manifest"] == {
        "version": "2026.1",
        "generated_at": "2026-08-24T12:30:00Z",
        "question_count": 2,
        "reference_count": 1,
        "disciplines": {
            "synthetic-discipline": {
                "file": "synthetic-discipline/questions.json",
                "question_count": 2,
            }
        },
        "references_file": "references.json",
    }
    assert [question["id"] for question in result["questions"]] == [
        "SYN-UNIT-001",
        "SYN-UNIT-002",
    ]
    assert {question["status"] for question in result["questions"]} == {
        "QA_PASS",
        "HUMAN_REVIEWED",
    }
    assert all("human_review" not in question for question in result["questions"])
    output = tmp_path / "app" / "public" / "data" / "qbank"
    assert read_json(output / "synthetic-discipline" / "questions.json") == result[
        "questions"
    ]
    assert read_json(output / "references.json")["references"] == result["references"]
    assert read_json(output / "manifest.json") == result["manifest"]
    assert not any(
        name in str(path.relative_to(output))
        for path in output.rglob("*")
        for name in ("candidate", "rejected", "retired", "quarantine", "reasoning")
    )


def test_human_review_without_reviewer_metadata_fails_without_altering_live_output(
    tmp_path,
):
    """Catches HUMAN_REVIEWED admission based on status alone."""
    _populate(tmp_path)
    marker = _seed_live_output(tmp_path)
    human_path = tmp_path / "verified" / "human.json"
    human = read_json(human_path)
    del human["human_review"]["credentials"]
    write_json_atomic(human_path, human)

    with pytest.raises(ExportError, match="human review metadata"):
        build_production(tmp_path, "2026.1", FIXED_NOW)

    assert marker.read_text(encoding="utf-8") == "old production"


def test_complete_human_review_may_include_non_private_reviewer_identity(tmp_path):
    """Catches treating the four required reviewer fields as an exact envelope."""
    _populate(tmp_path)
    human_path = tmp_path / "verified" / "human.json"
    human = read_json(human_path)
    human["human_review"]["reviewer_id"] = "SYNTHETIC-REVIEWER-001"
    write_json_atomic(human_path, human)

    result = build_production(tmp_path, "2026.1", FIXED_NOW)

    exported = next(
        question for question in result["questions"] if question["status"] == "HUMAN_REVIEWED"
    )
    assert "human_review" not in exported


def test_unknown_reference_blocks_export_without_altering_live_output(tmp_path):
    """Catches dangling public references and validate-after-replace implementations."""
    _populate(tmp_path)
    marker = _seed_live_output(tmp_path)
    question_path = tmp_path / "verified" / "qa.json"
    question = read_json(question_path)
    question["references"] = ["REF-UNKNOWN"]
    write_json_atomic(question_path, question)

    with pytest.raises(ExportError, match="unknown reference"):
        build_production(tmp_path, "2026.1", FIXED_NOW)

    assert marker.read_text(encoding="utf-8") == "old production"


def test_malformed_eligible_question_fails_closed_before_replacement(tmp_path):
    """Catches eligible records copied without canonical question validation."""
    _populate(tmp_path)
    marker = _seed_live_output(tmp_path)
    question_path = tmp_path / "verified" / "qa.json"
    question = read_json(question_path)
    question["question"]["options"].pop()
    write_json_atomic(question_path, question)

    with pytest.raises(ExportError, match="invalid verified question"):
        build_production(tmp_path, "2026.1", FIXED_NOW)

    assert marker.read_text(encoding="utf-8") == "old production"


def test_recursive_private_field_scan_blocks_verifier_reasoning(tmp_path):
    """Catches schema projections that overlook nested private QA material."""
    _populate(tmp_path)
    marker = _seed_live_output(tmp_path)
    question_path = tmp_path / "verified" / "qa.json"
    question = read_json(question_path)
    question["question"]["private_qa"] = {
        "verifier_reasoning": "must remain private"
    }
    write_json_atomic(question_path, question)

    with pytest.raises(ExportError, match="forbidden private field"):
        build_production(tmp_path, "2026.1", FIXED_NOW)

    assert marker.read_text(encoding="utf-8") == "old production"


def test_private_qa_reasoning_field_fails_before_schema_projection(tmp_path):
    """Catches private QA reasoning reported only as a generic schema failure."""
    _populate(tmp_path)
    marker = _seed_live_output(tmp_path)
    question_path = tmp_path / "verified" / "qa.json"
    question = read_json(question_path)
    question["qa_reasoning"] = "private reasoning must not reach production"
    write_json_atomic(question_path, question)

    with pytest.raises(ExportError, match="forbidden private field"):
        build_production(tmp_path, "2026.1", FIXED_NOW)

    assert marker.read_text(encoding="utf-8") == "old production"


def test_stage_rename_failure_restores_live_output(tmp_path, monkeypatch):
    """Catches replacement code that removes live output before staging succeeds."""
    _populate(tmp_path)
    marker = _seed_live_output(tmp_path)
    target = marker.parent
    real_replace = os.replace

    def fail_stage_install(source, destination):
        source_path = Path(source)
        destination_path = Path(destination)
        if source_path.name.startswith(".qbank-stage-") and destination_path == target:
            raise OSError("synthetic stage install failure")
        return real_replace(source, destination)

    monkeypatch.setattr(export_module.os, "replace", fail_stage_install)

    with pytest.raises(ExportError, match="restore"):
        build_production(tmp_path, "2026.1", FIXED_NOW)

    assert marker.read_text(encoding="utf-8") == "old production"
