"""Tests for the deterministic scope-chapter structural validator
(qbank.scope_validate), used by `python -m scripts.qbank validate-scope-chapter`.
"""
import json
from pathlib import Path
import shutil

import pytest

from qbank.scope_validate import validate_scope_chapter

REPO = Path(__file__).resolve().parents[1]
FIXTURE_CHAPTER = "CP"


def _project_copy(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    root.mkdir()
    (root / "reports").mkdir()
    shutil.copy(
        REPO / "reports/scope_scaling_progress.json", root / "reports/scope_scaling_progress.json"
    )
    (root / "research").mkdir()
    shutil.copytree(REPO / "research/tn2025", root / "research/tn2025")
    shutil.copytree(REPO / "research/mcc", root / "research/mcc")
    (root / "research/scope").mkdir()
    shutil.copytree(
        REPO / "research/scope/chapters" / FIXTURE_CHAPTER,
        root / "research/scope/chapters" / FIXTURE_CHAPTER,
    )
    shutil.copytree(REPO / "schemas", root / "schemas")
    return root


def _load(root: Path, name: str) -> dict:
    path = root / "research/scope/chapters" / FIXTURE_CHAPTER / name
    return json.loads(path.read_text(encoding="utf-8"))


def _save(root: Path, name: str, value: dict) -> None:
    path = root / "research/scope/chapters" / FIXTURE_CHAPTER / name
    path.write_text(json.dumps(value, indent=2), encoding="utf-8")


@pytest.fixture
def project_root(tmp_path: Path) -> Path:
    return _project_copy(tmp_path)


class TestPass:
    def test_known_good_chapter_passes(self, project_root):
        result = validate_scope_chapter(project_root, FIXTURE_CHAPTER)
        assert result.status == "PASS"
        assert result.errors == []
        assert result.counts["study_units"] > 0


class TestFail:
    def test_invalid_mcc_id_fails(self, project_root):
        crosswalk = _load(project_root, "crosswalk.json")
        entry = next(e for e in crosswalk["entries"] if e["mcc_evidence"])
        entry["mcc_evidence"][0]["mcc_id"] = "NOT-A-REAL-ID-99999"
        _save(project_root, "crosswalk.json", crosswalk)
        result = validate_scope_chapter(project_root, FIXTURE_CHAPTER)
        assert result.status == "FAIL"
        assert result.checks["mcc_ids"] == "FAIL"
        assert any("NOT-A-REAL-ID-99999" in e for e in result.errors)

    def test_missing_source_node_fails(self, project_root):
        study_units = _load(project_root, "study_units.json")
        study_units["organizational_header_nodes"] = {}
        study_units["study_units"] = [
            u for u in study_units["study_units"] if u["study_unit_id"] != "SU-CP-01"
        ]
        study_units["total_study_units"] = len(study_units["study_units"])
        _save(project_root, "study_units.json", study_units)
        crosswalk = _load(project_root, "crosswalk.json")
        crosswalk["entries"] = [
            e for e in crosswalk["entries"] if e["study_unit_id"] != "SU-CP-01"
        ]
        _save(project_root, "crosswalk.json", crosswalk)
        result = validate_scope_chapter(project_root, FIXTURE_CHAPTER)
        assert result.status == "FAIL"
        assert result.checks["source_accounting"] == "FAIL"

    def test_illegal_weak_mapping_without_review_flag_fails(self, project_root):
        crosswalk = _load(project_root, "crosswalk.json")
        entry = next(e for e in crosswalk["entries"] if e["mcc_evidence"])
        entry["mcc_evidence"][0]["mapping_strength"] = "WEAK"
        entry["mcc_evidence"][0].pop("requires_scope_review", None)
        _save(project_root, "crosswalk.json", crosswalk)
        result = validate_scope_chapter(project_root, FIXTURE_CHAPTER)
        assert result.status == "FAIL"
        assert result.checks["schema"] == "FAIL"

    def test_obsolete_target_questions_fails(self, project_root):
        crosswalk = _load(project_root, "crosswalk.json")
        crosswalk["entries"][0]["question_planning"]["target_questions"] = 5
        _save(project_root, "crosswalk.json", crosswalk)
        result = validate_scope_chapter(project_root, FIXTURE_CHAPTER)
        assert result.status == "FAIL"
        assert result.checks["question_planning"] == "FAIL"

    def test_invalid_enum_fails(self, project_root):
        study_units = _load(project_root, "study_units.json")
        study_units["study_units"][0]["extraction_confidence"] = "SUPER_HIGH"
        _save(project_root, "study_units.json", study_units)
        result = validate_scope_chapter(project_root, FIXTURE_CHAPTER)
        assert result.status == "FAIL"
        assert result.checks["schema"] == "FAIL"

    def test_cross_chapter_source_node_leak_fails(self, project_root):
        study_units = _load(project_root, "study_units.json")
        study_units["study_units"][0]["source_node_ids"] = ["A.S01"]
        _save(project_root, "study_units.json", study_units)
        result = validate_scope_chapter(project_root, FIXTURE_CHAPTER)
        assert result.status == "FAIL"
        assert result.checks["source_accounting"] == "FAIL"
        assert any("outside chapter" in e for e in result.errors)

    def test_unknown_chapter_code_fails(self, project_root):
        result = validate_scope_chapter(project_root, "ZZ_NOT_A_CHAPTER")
        assert result.status == "FAIL"


class TestWarning:
    def test_uncertain_state_is_warning_not_failure(self, project_root):
        crosswalk = _load(project_root, "crosswalk.json")
        entry = crosswalk["entries"][0]
        entry["classification"] = "UNCERTAIN"
        entry["mcc_evidence"] = []
        entry["uncertain_reason"] = "No matching objective found."
        _save(project_root, "crosswalk.json", crosswalk)
        result = validate_scope_chapter(project_root, FIXTURE_CHAPTER)
        assert result.status == "PASS"
        assert any("UNCERTAIN" in w for w in result.warnings)

    def test_section_inherited_precision_is_warning_not_failure(self, project_root):
        study_units = _load(project_root, "study_units.json")
        study_units["study_units"][0]["page_mapping_precision"] = "SECTION_INHERITED"
        _save(project_root, "study_units.json", study_units)
        result = validate_scope_chapter(project_root, FIXTURE_CHAPTER)
        assert result.status == "PASS"
        assert any("SECTION_INHERITED" in w for w in result.warnings)
