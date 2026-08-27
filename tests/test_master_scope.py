"""Tests for deterministic master scope aggregation and validation."""

from __future__ import annotations

import copy
import json
from pathlib import Path
import shutil

from qbank.cli import _parser


REPO = Path(__file__).resolve().parents[1]


def _project_copy(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    root.mkdir()
    (root / "research").mkdir()
    shutil.copytree(REPO / "research/scope/chapters", root / "research/scope/chapters")
    shutil.copytree(REPO / "research/mcc", root / "research/mcc")
    shutil.copytree(REPO / "schemas", root / "schemas")
    (root / "reports").mkdir()
    shutil.copy(
        REPO / "reports/scope_scaling_progress.json",
        root / "reports/scope_scaling_progress.json",
    )
    return root


def _build(root: Path) -> dict:
    from qbank.master_scope import build_master_scope

    return build_master_scope(root)


def _validate(root: Path):
    from qbank.master_scope import validate_master_scope

    return validate_master_scope(root)


def _load(root: Path, filename: str) -> dict:
    return json.loads((root / "research/scope" / filename).read_text(encoding="utf-8"))


def _save(root: Path, filename: str, value: dict) -> None:
    (root / "research/scope" / filename).write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def test_build_master_scope_command_is_registered():
    commands = _parser()._subparsers._group_actions[0].choices
    assert "build-master-scope" in commands


def test_validate_master_scope_command_is_registered():
    commands = _parser()._subparsers._group_actions[0].choices
    assert "validate-master-scope" in commands


def test_build_includes_every_chapter_crosswalk_entry_once(tmp_path):
    root = _project_copy(tmp_path)
    result = _build(root)
    master = _load(root, "master_scope_crosswalk.json")
    expected = sum(
        len(json.loads(path.read_text(encoding="utf-8"))["entries"])
        for path in (root / "research/scope/chapters").glob("*/crosswalk.json")
    )
    ids = [entry["study_unit_id"] for entry in master["entries"]]
    assert result["total_study_units"] == expected
    assert len(ids) == expected
    assert len(ids) == len(set(ids))


def test_duplicate_study_unit_id_fails_validation(tmp_path):
    root = _project_copy(tmp_path)
    _build(root)
    master = _load(root, "master_scope_crosswalk.json")
    master["entries"].append(copy.deepcopy(master["entries"][0]))
    _save(root, "master_scope_crosswalk.json", master)
    result = _validate(root)
    assert result.status == "FAIL"
    assert any("duplicate study_unit_id" in error for error in result.errors)


def test_invalid_mcc_evidence_reference_fails_validation(tmp_path):
    root = _project_copy(tmp_path)
    _build(root)
    master = _load(root, "master_scope_crosswalk.json")
    entry = next(entry for entry in master["entries"] if entry["mcc_evidence"])
    evidence = next(
        item for item in entry["mcc_evidence"] if item["evidence_type"] == "OBJECTIVE_REFERENCE"
    )
    evidence["mcc_id"] = "NOT-A-REAL-MCC-ID"
    _save(root, "master_scope_crosswalk.json", master)
    result = _validate(root)
    assert result.status == "FAIL"
    assert any("NOT-A-REAL-MCC-ID" in error for error in result.errors)


def test_accounting_weak_metrics_candidates_and_coverage_reconcile(tmp_path):
    root = _project_copy(tmp_path)
    _build(root)
    master = _load(root, "master_scope_crosswalk.json")
    report = _load(root, "master_scope_report.json")
    candidates = _load(root, "global_review_candidates.json")
    coverage = _load(root, "mcc_objective_coverage.json")
    entries = master["entries"]
    classifications = report["classification_counts"]
    evidence = report["mcc_evidence_references"]
    assert sum(classifications.values()) == len(entries)
    assert sum(evidence.values()) == sum(len(entry["mcc_evidence"]) for entry in entries)
    any_weak = sum(any(item["mapping_strength"] == "WEAK" for item in entry["mcc_evidence"]) for entry in entries)
    only_weak = sum(
        any(item["mapping_strength"] == "WEAK" for item in entry["mcc_evidence"])
        and not any(item["mapping_strength"] in {"STRONG", "MODERATE"} for item in entry["mcc_evidence"])
        for entry in entries
    )
    assert report["study_units_with_any_weak_evidence"] == any_weak
    assert report["study_units_with_only_weak_evidence"] == only_weak
    entry_ids = {entry["study_unit_id"] for entry in entries}
    assert {item["study_unit_id"] for item in candidates["candidates"]} <= entry_ids
    mapped_ids = {
        evidence["mcc_id"]
        for entry in entries
        for evidence in entry["mcc_evidence"]
        if evidence["evidence_type"] == "OBJECTIVE_REFERENCE"
    }
    assert {item["objective_id"] for item in coverage["objectives"] if item["mapped_study_unit_count"]} == mapped_ids


def test_build_output_is_deterministic(tmp_path):
    root = _project_copy(tmp_path)
    _build(root)
    first = {
        name: (root / "research/scope" / name).read_bytes()
        for name in (
            "master_scope_crosswalk.json",
            "master_scope_report.json",
            "global_review_candidates.json",
            "global_ownership_candidates.json",
            "mcc_objective_coverage.json",
        )
    }
    _build(root)
    assert first == {name: (root / "research/scope" / name).read_bytes() for name in first}
