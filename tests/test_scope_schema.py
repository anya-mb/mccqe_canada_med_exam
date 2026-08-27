"""Deterministic tests for the frozen scope schema (Phase 3C):
schemas/study-unit.schema.json and schemas/crosswalk-entry.schema.json,
plus the migrated Cardiology and ELOM chapter data.

These tests protect the frozen scope_schema_version="1.0" contract that
all 32 chapters must conform to - a change here requires an explicit
migration per the Phase 3C instructions, not a silent edit.
"""
import json
from pathlib import Path

import pytest

from qbank.errors import SchemaValidationError
from qbank.schema import validate_instance

REPO = Path(__file__).resolve().parents[1]
CHAPTERS_DIR = REPO / "research" / "scope" / "chapters"


def valid_study_unit(**overrides):
    base = {
        "scope_schema_version": "1.0",
        "study_unit_id": "SU-X-01",
        "title": "Example",
        "chapter_code": "X",
        "chapter_title": "Example Chapter",
        "source_node_ids": ["X.S01"],
        "tn_page_range": "X1-X2",
        "pdf_page_range": [1, 2],
        "source_hierarchy_path": ["X.S01 (Example)"],
        "structural_rationale": "Because.",
        "extraction_confidence": "HIGH",
        "page_mapping_precision": "EXACT_SECTION",
    }
    base.update(overrides)
    return base


def valid_crosswalk_entry(**overrides):
    base = {
        "scope_schema_version": "1.0",
        "study_unit_id": "SU-X-01",
        "title": "Example",
        "classification": "DIRECT",
        "mcc_evidence": [{
            "evidence_type": "OBJECTIVE_REFERENCE",
            "mcc_id": "14",
            "legacy_id": "14",
            "objective_title": "Chest pain",
            "canmeds_role": "Medical Expert",
            "official_source": "research/mcc/objectives_registry.json",
            "mapping_strength": "STRONG",
            "mapping_rationale": "Because.",
        }],
        "scope_depth": "CORE_ACTION",
        "testable_competencies": {"recognition": "Do the thing."},
        "question_planning": {
            "coverage_weight": 3,
            "minimum_question_coverage": 3,
            "preferred_item_forms": ["MOST_LIKELY_DIAGNOSIS"],
        },
        "page_mapping_precision": "EXACT_SECTION",
        "clinical_source_organizations": [],
        "freshness": {"verification_required": False},
    }
    base.update(overrides)
    return base


def valid_mcc_gap_fill_unit(**overrides):
    base = {
        "scope_schema_version": "1.0",
        "study_unit_id": "SU-MCC-001",
        "title": "Adults with developmental disabilities",
        "chapter_code": "MCC",
        "chapter_title": "MCC Objective Gap Fills",
        "source_type": "MCC_GAP_FILL",
        "source_provenance": {
            "objective_id": "21-1",
            "objective_title": "Adults with developmental disabilities",
            "role": "Medical Expert",
            "registry_path": "research/mcc/objectives_registry.json",
            "official_url": "https://mcc.ca/objectives/example/",
            "version": "March 2022",
        },
        "structural_rationale": "Canonical MCC objective not represented by a Toronto Notes study unit.",
        "extraction_confidence": "HIGH",
        "page_mapping_precision": "NOT_APPLICABLE",
    }
    base.update(overrides)
    return base


def test_mcc_gap_fill_unit_schema_accepts_mcc_provenance_without_toronto_notes_pages():
    """An MCC-derived scope unit must validate without fabricated TN nodes or pages."""
    unit = valid_mcc_gap_fill_unit()

    validate_instance(REPO, "mcc-gap-fill-unit", unit)

    assert "source_node_ids" not in unit
    assert "tn_page_range" not in unit
    assert "pdf_page_range" not in unit


class TestStudyUnitSchema:
    def test_valid_minimal_unit_passes(self):
        validate_instance(REPO, "study-unit", valid_study_unit())

    def test_missing_required_field_fails(self):
        unit = valid_study_unit()
        del unit["structural_rationale"]
        with pytest.raises(SchemaValidationError):
            validate_instance(REPO, "study-unit", unit)

    def test_wrong_schema_version_fails(self):
        with pytest.raises(SchemaValidationError):
            validate_instance(REPO, "study-unit", valid_study_unit(scope_schema_version="2.0"))

    def test_invalid_page_precision_fails(self):
        with pytest.raises(SchemaValidationError):
            validate_instance(REPO, "study-unit", valid_study_unit(page_mapping_precision="APPROXIMATE"))

    def test_empty_source_node_ids_fails(self):
        with pytest.raises(SchemaValidationError):
            validate_instance(REPO, "study-unit", valid_study_unit(source_node_ids=[]))

    def test_unknown_property_rejected(self):
        unit = valid_study_unit()
        unit["target_questions"] = 30  # retired field must not leak into study units
        with pytest.raises(SchemaValidationError):
            validate_instance(REPO, "study-unit", unit)


class TestCrosswalkEntrySchema:
    def test_valid_minimal_entry_passes(self):
        validate_instance(REPO, "crosswalk-entry", valid_crosswalk_entry())

    def test_invalid_classification_fails(self):
        with pytest.raises(SchemaValidationError):
            validate_instance(REPO, "crosswalk-entry", valid_crosswalk_entry(classification="MAYBE"))

    def test_weak_mapping_without_scope_review_flag_fails(self):
        entry = valid_crosswalk_entry()
        entry["mcc_evidence"][0]["mapping_strength"] = "WEAK"
        with pytest.raises(SchemaValidationError):
            validate_instance(REPO, "crosswalk-entry", entry)

    def test_weak_mapping_with_scope_review_flag_passes(self):
        entry = valid_crosswalk_entry()
        entry["mcc_evidence"][0]["mapping_strength"] = "WEAK"
        entry["mcc_evidence"][0]["requires_scope_review"] = True
        validate_instance(REPO, "crosswalk-entry", entry)

    def test_role_level_reference_with_fabricated_id_fails(self):
        entry = valid_crosswalk_entry()
        entry["mcc_evidence"][0]["evidence_type"] = "ROLE_LEVEL_REFERENCE"
        entry["mcc_evidence"][0]["canmeds_role"] = "Leader/Manager"
        # mcc_id still "14" - a fabricated ID for a role-level reference
        with pytest.raises(SchemaValidationError):
            validate_instance(REPO, "crosswalk-entry", entry)

    def test_role_level_reference_with_null_id_passes(self):
        entry = valid_crosswalk_entry()
        entry["mcc_evidence"][0]["evidence_type"] = "ROLE_LEVEL_REFERENCE"
        entry["mcc_evidence"][0]["canmeds_role"] = "Leader/Manager"
        entry["mcc_evidence"][0]["mcc_id"] = None
        entry["mcc_evidence"][0]["legacy_id"] = None
        validate_instance(REPO, "crosswalk-entry", entry)

    def test_objective_reference_requires_non_null_id(self):
        entry = valid_crosswalk_entry()
        entry["mcc_evidence"][0]["mcc_id"] = None
        with pytest.raises(SchemaValidationError):
            validate_instance(REPO, "crosswalk-entry", entry)

    def test_non_testable_classification_with_evidence_and_no_reason_fails(self):
        entry = valid_crosswalk_entry(classification="SPECIALIST_DETAIL")
        # mcc_evidence still populated from the base fixture, no retention reason
        with pytest.raises(SchemaValidationError):
            validate_instance(REPO, "crosswalk-entry", entry)

    def test_non_testable_classification_with_empty_evidence_passes(self):
        entry = valid_crosswalk_entry(classification="SPECIALIST_DETAIL", mcc_evidence=[])
        validate_instance(REPO, "crosswalk-entry", entry)

    def test_non_testable_classification_with_documented_retention_passes(self):
        entry = valid_crosswalk_entry(classification="SPECIALIST_DETAIL")
        entry["mcc_evidence_retention_reason"] = "Documented reason for keeping this citation."
        validate_instance(REPO, "crosswalk-entry", entry)

    def test_zero_coverage_without_reason_fails(self):
        entry = valid_crosswalk_entry()
        entry["question_planning"]["minimum_question_coverage"] = 0
        with pytest.raises(SchemaValidationError):
            validate_instance(REPO, "crosswalk-entry", entry)

    def test_zero_coverage_with_reason_passes(self):
        entry = valid_crosswalk_entry()
        entry["question_planning"]["minimum_question_coverage"] = 0
        entry["zero_question_reason"] = "Reference material only."
        validate_instance(REPO, "crosswalk-entry", entry)

    def test_uncertain_classification_without_reason_fails(self):
        with pytest.raises(SchemaValidationError):
            validate_instance(REPO, "crosswalk-entry", valid_crosswalk_entry(classification="UNCERTAIN", mcc_evidence=[]))

    def test_uncertain_classification_with_reason_passes(self):
        entry = valid_crosswalk_entry(classification="UNCERTAIN", mcc_evidence=[])
        entry["uncertain_reason"] = "No matching objective found."
        validate_instance(REPO, "crosswalk-entry", entry)

    def test_coverage_weight_out_of_range_fails(self):
        entry = valid_crosswalk_entry()
        entry["question_planning"]["coverage_weight"] = 6
        with pytest.raises(SchemaValidationError):
            validate_instance(REPO, "crosswalk-entry", entry)

    def test_jurisdiction_is_optional(self):
        # base fixture has no jurisdiction key at all - must still pass
        validate_instance(REPO, "crosswalk-entry", valid_crosswalk_entry())

    def test_jurisdiction_when_present_must_be_well_formed(self):
        entry = valid_crosswalk_entry()
        entry["jurisdiction"] = {"scope": "NOT_A_REAL_SCOPE", "province_required_in_question": False}
        with pytest.raises(SchemaValidationError):
            validate_instance(REPO, "crosswalk-entry", entry)

    def test_retired_target_questions_field_rejected(self):
        entry = valid_crosswalk_entry()
        entry["target_questions"] = 30
        with pytest.raises(SchemaValidationError):
            validate_instance(REPO, "crosswalk-entry", entry)


@pytest.mark.parametrize("chapter_code", ["C", "ELOM", "A", "CP"])
class TestMigratedChapterData:
    def test_all_study_units_validate(self, chapter_code):
        with open(CHAPTERS_DIR / chapter_code / "study_units.json") as f:
            data = json.load(f)
        for unit in data["study_units"]:
            validate_instance(REPO, "study-unit", unit)

    def test_all_crosswalk_entries_validate(self, chapter_code):
        with open(CHAPTERS_DIR / chapter_code / "crosswalk.json") as f:
            data = json.load(f)
        for entry in data["entries"]:
            validate_instance(REPO, "crosswalk-entry", entry)

    def test_mcc_evidence_hygiene_across_chapter(self, chapter_code):
        with open(CHAPTERS_DIR / chapter_code / "crosswalk.json") as f:
            data = json.load(f)
        non_testable = {"SUPPORTING_KNOWLEDGE", "SPECIALIST_DETAIL", "REFERENCE_ONLY"}
        violations = [
            e["study_unit_id"] for e in data["entries"]
            if e["classification"] in non_testable
            and e["mcc_evidence"]
            and not e.get("mcc_evidence_retention_reason")
        ]
        assert not violations, f"Non-testable units with undocumented mcc_evidence: {violations}"

    def test_every_study_unit_has_a_crosswalk_entry(self, chapter_code):
        with open(CHAPTERS_DIR / chapter_code / "study_units.json") as f:
            su_data = json.load(f)
        with open(CHAPTERS_DIR / chapter_code / "crosswalk.json") as f:
            cw_data = json.load(f)
        su_ids = {u["study_unit_id"] for u in su_data["study_units"]}
        cw_ids = {e["study_unit_id"] for e in cw_data["entries"]}
        assert su_ids == cw_ids, f"Mismatch: {su_ids.symmetric_difference(cw_ids)}"

    def test_no_duplicate_study_unit_ids(self, chapter_code):
        with open(CHAPTERS_DIR / chapter_code / "study_units.json") as f:
            data = json.load(f)
        ids = [u["study_unit_id"] for u in data["study_units"]]
        assert len(ids) == len(set(ids))
