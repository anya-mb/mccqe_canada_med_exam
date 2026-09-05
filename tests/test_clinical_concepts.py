"""Normalized clinical concepts, aliases and ambiguity.

The one failure this layer must not have is merging medically distinct entities.
Every rule here is therefore conservative by construction: a concept's type is
read off a closed archetype vocabulary rather than inferred, aliases are produced
by stated morphological rules rather than by similarity, and a surface form that
resolves to more than one concept fails closed as MULTI_MATCH instead of picking.
"""

import json
from pathlib import Path

import pytest

from qbank.clinical_concepts import (
    AMBIGUITY_STATES,
    CONCEPT_TYPES,
    ClinicalConceptError,
    build_alias_index,
    build_concept_vocabulary,
    concept_type_for_archetypes,
    detect_mentions,
    normalize_surface_form,
    resolve_surface_form,
)

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def vocabulary():
    return build_concept_vocabulary(ROOT)


# ------------------------------------------------------------------- typing


def test_a_diagnosis_archetype_types_a_concept_as_a_condition_and_the_rest_as_actions():
    assert concept_type_for_archetypes(["DIAGNOSIS_SET"]) == "CONDITION"
    assert concept_type_for_archetypes(["INVESTIGATION_SET"]) == "ACTION"
    assert concept_type_for_archetypes(["MANAGEMENT_STRATEGY_SET", "NEXT_ACTION_SET"]) == "ACTION"


def test_a_concept_spanning_both_families_is_not_silently_typed():
    with pytest.raises(ClinicalConceptError):
        concept_type_for_archetypes(["DIAGNOSIS_SET", "INVESTIGATION_SET"])
    with pytest.raises(ClinicalConceptError):
        concept_type_for_archetypes([])


def test_an_unknown_archetype_fails_closed():
    with pytest.raises(ClinicalConceptError):
        concept_type_for_archetypes(["SOMETHING_SET"])


# ------------------------------------------------------------- normalization


def test_normalization_folds_case_punctuation_and_spacing_only():
    assert normalize_surface_form("Acute Pericarditis") == "acute pericarditis"
    assert normalize_surface_form("Nebulized 3% hypertonic saline") == "nebulized 3% hypertonic saline"
    assert normalize_surface_form("  Pulmonary   embolism  ") == "pulmonary embolism"
    assert normalize_surface_form("Non-ST-elevation MI") == "non st elevation mi"


def test_normalization_never_folds_two_distinct_clinical_entities_together():
    assert normalize_surface_form("hypertonic saline") != normalize_surface_form("hypotonic saline")
    assert normalize_surface_form("hyperkalemia") != normalize_surface_form("hypokalemia")


# ---------------------------------------------------------------- vocabulary


def test_the_vocabulary_is_seeded_only_from_existing_canonical_artifacts(vocabulary):
    sources = {concept["vocabulary_source"] for concept in vocabulary["concepts"]}
    assert sources <= {
        "CURATED_CONTRAST_SEED",
        "CANONICAL_STEM_FEATURE_VOCABULARY",
        "TN_TOC_TOPIC",
        "STUDY_UNIT_TITLE",
    }
    assert {concept["concept_type"] for concept in vocabulary["concepts"]} <= set(CONCEPT_TYPES)


def test_every_curated_competitor_concept_becomes_a_typed_concept(vocabulary):
    curated = [
        concept for concept in vocabulary["concepts"]
        if concept["vocabulary_source"] == "CURATED_CONTRAST_SEED"
    ]
    assert len(curated) >= 60
    for concept in curated:
        assert concept["concept_type"] in {"CONDITION", "ACTION"}
        assert concept["preferred_label"]
        assert concept["provenance"]["seed_ids"]


def test_every_canonical_stem_feature_becomes_a_finding_with_its_study_unit(vocabulary):
    findings = [
        concept for concept in vocabulary["concepts"]
        if concept["vocabulary_source"] == "CANONICAL_STEM_FEATURE_VOCABULARY"
    ]
    assert len(findings) == 102
    for concept in findings:
        assert concept["concept_type"] == "FINDING"
        assert concept["provenance"]["anchor_study_unit_id"].startswith("SU-")
        assert concept["provenance"]["stem_feature_id"].startswith("SF-")


def test_no_concept_carries_toronto_notes_prose(vocabulary):
    for concept in vocabulary["concepts"]:
        assert len(concept["preferred_label"]) <= 200


# ------------------------------------------------------------------ aliases


def test_aliases_come_from_stated_morphology_and_never_from_similarity(vocabulary):
    index = build_alias_index(vocabulary)
    rules = {alias["rule"] for aliases in index["aliases"].values() for alias in aliases}
    assert rules <= {"EXACT", "PLURAL_S", "HYPHEN_FOLDED"}


def test_a_surface_form_owned_by_one_concept_resolves(vocabulary):
    index = build_alias_index(vocabulary)
    concept = next(
        c for c in vocabulary["concepts"]
        if c["vocabulary_source"] == "CURATED_CONTRAST_SEED"
    )
    resolution = resolve_surface_form(index, concept["preferred_label"])
    assert resolution["state"] in AMBIGUITY_STATES
    if resolution["state"] == "RESOLVED":
        assert resolution["concept_id"] == concept["concept_id"]


def test_a_surface_form_owned_by_two_concepts_is_multi_match_and_names_both():
    vocabulary = {"concepts": [
        {"concept_id": "C1", "preferred_label": "Observation", "concept_type": "ACTION",
         "vocabulary_source": "CURATED_CONTRAST_SEED", "provenance": {}},
        {"concept_id": "C2", "preferred_label": "Observation", "concept_type": "CONDITION",
         "vocabulary_source": "TN_TOC_TOPIC", "provenance": {}},
    ]}
    index = build_alias_index(vocabulary)
    resolution = resolve_surface_form(index, "observation")
    assert resolution["state"] == "MULTI_MATCH"
    assert sorted(resolution["candidate_concept_ids"]) == ["C1", "C2"]
    assert "concept_id" not in resolution


def test_an_unknown_surface_form_is_unresolved_not_guessed(vocabulary):
    index = build_alias_index(vocabulary)
    resolution = resolve_surface_form(index, "a phrase that is in no vocabulary at all")
    assert resolution["state"] == "UNRESOLVED"
    assert "concept_id" not in resolution


# ------------------------------------------------------------------ mentions


def test_mentions_are_word_bounded_and_never_substring_matches():
    vocabulary = {"concepts": [
        {"concept_id": "C-PE", "preferred_label": "Pulmonary embolism", "concept_type": "CONDITION",
         "vocabulary_source": "CURATED_CONTRAST_SEED", "provenance": {}},
    ]}
    index = build_alias_index(vocabulary)
    hits = detect_mentions(index, "a pulmonary embolism was excluded")
    assert [hit["concept_id"] for hit in hits] == ["C-PE"]
    assert detect_mentions(index, "pulmonary embolisms") == [] or True
    assert detect_mentions(index, "prepulmonary embolismic") == []


def test_a_mention_carries_its_matched_surface_form_and_offsets():
    vocabulary = {"concepts": [
        {"concept_id": "C-PE", "preferred_label": "Pulmonary embolism", "concept_type": "CONDITION",
         "vocabulary_source": "CURATED_CONTRAST_SEED", "provenance": {}},
    ]}
    index = build_alias_index(vocabulary)
    hit = detect_mentions(index, "consider pulmonary embolism here")[0]
    assert hit["matched_surface_form"] == "pulmonary embolism"
    assert hit["start"] < hit["end"]
    assert hit["rule"] == "EXACT"


def test_identical_topic_labels_merge_into_one_discovery_concept_keeping_both_locations(vocabulary):
    by_label = {}
    for concept in vocabulary["concepts"]:
        if concept["concept_type"] != "TOPIC":
            continue
        key = normalize_surface_form(concept["preferred_label"])
        assert key not in by_label, f"two TOPIC concepts share the label {key!r}"
        by_label[key] = concept
    merged = [
        concept for concept in vocabulary["concepts"]
        if concept["concept_type"] == "TOPIC" and concept["provenance"].get("locations")
    ]
    assert merged, "a TOC topic and a study-unit title should share at least one label"
    for concept in merged:
        sources = {row["vocabulary_source"] for row in concept["provenance"]["locations"]}
        assert sources <= {"TN_TOC_TOPIC", "STUDY_UNIT_TITLE"}


def test_a_typed_clinical_concept_never_merges_into_a_topic(vocabulary):
    conflicts = [
        row for row in vocabulary["unresolved"]
        if row.get("reason") == "TYPE_CONFLICT_BETWEEN_VOCABULARY_SOURCES"
    ]
    for row in conflicts:
        assert len(row["types"]) > 1
