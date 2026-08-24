import copy
from pathlib import Path

import pytest

from qbank.jsonio import read_json
from qbank.references import ReferenceMergeError, merge_references


FIXTURES = Path(__file__).resolve().parent / "fixtures" / "valid"


@pytest.fixture
def reference():
    return copy.deepcopy(read_json(FIXTURES / "reference.json"))


@pytest.fixture
def empty_registry():
    return {
        "version": "2026.1",
        "updated_at": "2026-08-24T12:00:00Z",
        "references": [],
    }


def test_same_canonical_guideline_reuses_stable_id(empty_registry, reference):
    registry, mapping = merge_references(empty_registry, [reference])
    duplicate = {
        **reference,
        "reference_id": "TEMP-999",
        "organization": "  SYNTHETIC  STANDARDS organization ",
        "title": " synthetic practice standard ",
        "url": "HTTPS://EXAMPLE.INVALID/synthetic-standard/",
    }

    merged, second_mapping = merge_references(registry, [duplicate])

    assert len(merged["references"]) == 1
    assert second_mapping["TEMP-999"] == mapping[reference["reference_id"]]
    assert merged["references"][0]["url"] == "https://example.invalid/synthetic-standard"


def test_claim_supports_merge_only_for_exact_normalized_pairs(empty_registry, reference):
    first, _ = merge_references(empty_registry, [reference])
    duplicate = {
        **reference,
        "reference_id": "TEMP-999",
        "supports": [
            reference["supports"][0],
            {
                "claim": "  The synthetic rule supports option A.  ",
                "locator": "Synthetic   recommendation 1",
            },
            {"claim": "The rule excludes option B.", "locator": "Recommendation 2"},
        ],
    }

    merged, _ = merge_references(first, [duplicate])

    assert merged["references"][0]["supports"] == [
        {"claim": "The rule excludes option B.", "locator": "Recommendation 2"},
        {
            "claim": "The synthetic rule supports option A.",
            "locator": "Synthetic recommendation 1",
        },
    ]


def test_distinct_canonical_urls_do_not_conflate_sources(empty_registry, reference):
    other_source = {
        **reference,
        "reference_id": "TEMP-999",
        "url": "https://other.example.invalid/synthetic-standard",
    }

    merged, mapping = merge_references(empty_registry, [reference, other_source])

    assert len(merged["references"]) == 2
    assert mapping[reference["reference_id"]] != mapping[other_source["reference_id"]]


def test_reusing_an_existing_id_for_conflicting_metadata_fails_closed(
    empty_registry, reference
):
    registry, _ = merge_references(empty_registry, [reference])
    conflicting = {
        **reference,
        "reference_id": registry["references"][0]["reference_id"],
        "title": "A different synthetic practice standard",
        "url": "https://example.invalid/different-standard",
    }

    with pytest.raises(ReferenceMergeError, match="reference_id collision"):
        merge_references(registry, [conflicting])


def test_reusing_an_incoming_id_for_conflicting_metadata_fails_closed(
    empty_registry, reference
):
    conflicting = {
        **reference,
        "title": "A different synthetic practice standard",
        "url": "https://example.invalid/different-standard",
    }

    with pytest.raises(ReferenceMergeError, match="reference_id collision"):
        merge_references(empty_registry, [reference, conflicting])


def test_registry_identity_collision_fails_closed(empty_registry, reference):
    duplicate = {
        **reference,
        "reference_id": "REF-OTHER-001",
        "url": "https://example.invalid/synthetic-standard/",
    }
    empty_registry["references"] = [reference, duplicate]

    with pytest.raises(ReferenceMergeError, match="canonical identity"):
        merge_references(empty_registry, [])
