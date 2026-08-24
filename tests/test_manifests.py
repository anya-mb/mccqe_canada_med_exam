import copy
from pathlib import Path

import pytest

from qbank.errors import SchemaValidationError
from qbank.jsonio import read_json
from qbank.manifests import ManifestSummary, validate_manifest_set


REPO_ROOT = Path(__file__).resolve().parents[1]
VALID_MANIFEST = REPO_ROOT / "tests" / "fixtures" / "valid" / "manifest.json"


@pytest.fixture
def valid_manifest():
    return copy.deepcopy(read_json(VALID_MANIFEST))


def second_manifest(manifest):
    value = copy.deepcopy(manifest)
    value["manifest_id"] = "MANIFEST-ALT-2026.1"
    value["discipline"] = "Alternative Synthetic Discipline"
    value["discipline_code"] = "ALT"
    value["batches"][0]["batch_id"] = "ALT-BATCH-001"
    value["batches"][0]["question_ids"] = [
        f"ALT-UNIT-{number:03d}" for number in range(1, 41)
    ]
    return value


def resize_single_batch(manifest, size):
    manifest["target_questions"] = size
    manifest["sections"][0]["target_questions"] = size
    manifest["batches"][0]["target_questions"] = size
    manifest["batches"][0]["question_ids"] = [
        f"SYN-UNIT-{number:03d}" for number in range(1, size + 1)
    ]


def test_manifest_set_returns_totals_derived_from_valid_manifests(valid_manifest):
    summary = validate_manifest_set([valid_manifest, second_manifest(valid_manifest)])

    assert summary == ManifestSummary(
        manifest_count=2,
        batch_count=2,
        target_questions=80,
        question_count=80,
    )


def test_manifest_set_applies_the_canonical_schema(valid_manifest):
    valid_manifest["batches"][0].pop("mcc_objectives")

    with pytest.raises(SchemaValidationError, match="mcc_objectives"):
        validate_manifest_set([valid_manifest])


@pytest.mark.parametrize("size", [39, 61])
def test_manifest_set_rejects_batch_targets_outside_40_to_60(valid_manifest, size):
    resize_single_batch(valid_manifest, size)

    with pytest.raises(SchemaValidationError, match="40 and 60"):
        validate_manifest_set([valid_manifest])


def test_manifest_set_rejects_target_and_question_id_count_mismatch(valid_manifest):
    valid_manifest["batches"][0]["question_ids"].pop()

    with pytest.raises(SchemaValidationError, match="target/question ID count"):
        validate_manifest_set([valid_manifest])


@pytest.mark.parametrize("field", ["tn_pages", "pdf_pages"])
def test_manifest_set_rejects_missing_page_mappings(valid_manifest, field):
    valid_manifest["batches"][0]["toronto_notes"].pop(field)

    with pytest.raises(SchemaValidationError, match=field):
        validate_manifest_set([valid_manifest])


def test_manifest_set_rejects_duplicate_manifest_id(valid_manifest):
    duplicate = second_manifest(valid_manifest)
    duplicate["manifest_id"] = valid_manifest["manifest_id"]

    with pytest.raises(SchemaValidationError, match="duplicate manifest ID"):
        validate_manifest_set([valid_manifest, duplicate])


def test_manifest_set_rejects_duplicate_batch_id_across_manifests(valid_manifest):
    duplicate = second_manifest(valid_manifest)
    duplicate["batches"][0]["batch_id"] = valid_manifest["batches"][0]["batch_id"]

    with pytest.raises(SchemaValidationError, match="duplicate batch ID"):
        validate_manifest_set([valid_manifest, duplicate])


def test_manifest_set_rejects_cross_discipline_id_collision(valid_manifest):
    duplicate = second_manifest(valid_manifest)
    duplicate["batches"][0]["question_ids"][0] = valid_manifest["batches"][0][
        "question_ids"
    ][0]

    with pytest.raises(SchemaValidationError, match="duplicate question ID"):
        validate_manifest_set([valid_manifest, duplicate])


def test_manifest_set_rejects_manifest_target_that_disagrees_with_sections(
    valid_manifest,
):
    valid_manifest["target_questions"] = 41

    with pytest.raises(SchemaValidationError, match="section target total"):
        validate_manifest_set([valid_manifest])


def test_manifest_set_rejects_manifest_target_that_disagrees_with_batches(
    valid_manifest,
):
    valid_manifest["target_questions"] = 41
    valid_manifest["sections"][0]["target_questions"] = 41

    with pytest.raises(SchemaValidationError, match="batch target total"):
        validate_manifest_set([valid_manifest])


def test_manifest_set_rejects_section_without_matching_batch_allocation(valid_manifest):
    valid_manifest["sections"][0]["chapter"] = "Unallocated Synthetic Chapter"

    with pytest.raises(SchemaValidationError, match="section/batch target total"):
        validate_manifest_set([valid_manifest])


def test_manifest_set_rejects_non_contiguous_question_ids(valid_manifest):
    valid_manifest["batches"][0]["question_ids"][20] = "SYN-UNIT-099"

    with pytest.raises(SchemaValidationError, match="contiguous question IDs"):
        validate_manifest_set([valid_manifest])
