from pathlib import Path

import pytest

from scripts.qbank.qgen_exposure_registry import (
    AMBIGUOUS_LEVEL,
    aggregate_registry,
    build_registry,
    classify_artifact,
)


@pytest.fixture
def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


@pytest.mark.parametrize(
    ("document", "expected_level", "expected_status"),
    [
        (
            {"scope": "QGEN_FRESH_HOLDOUT_ELIGIBLE_INVENTORY", "candidates": []},
            0,
            "INVENTORY_ONLY",
        ),
        (
            {
                "scope": "QGEN_FUTURE_UNTOUCHED_HOLDOUT_ELIGIBILITY",
                "seed_availability_inspected": False,
                "contrast_supply_inspected": False,
                "units": [],
            },
            1,
            "METADATA_ONLY",
        ),
        (
            {
                "schema_version": "NEW_CLEAN_TRANSFER_18_SELECTION_V9",
                "execution_status": "FROZEN_NOT_RUN",
                "candidate_retrieval_run": False,
                "rows": [],
            },
            2,
            "RESERVED_NOT_INSPECTED",
        ),
        (
            {"schema_version": "CLEAN_TRANSFER18_PREREQUISITES_V1", "rows": []},
            3,
            "PREREQUISITE_SEMANTICS_REVIEWED",
        ),
        (
            {"schema_version": "TRANSFER18_DISCOVERY_V6_DEVELOPMENT_WAVE_V1", "rows": []},
            4,
            "CANDIDATE_SUPPLY_INSPECTED",
        ),
        (
            {"schema_version": "TRANSFER18_DISCOVERY_V6_CLINICAL_REVIEW_V1", "rows": []},
            5,
            "CLINICAL_CANDIDATE_REVIEWED",
        ),
        (
            {"schema_version": "FEATURE_EVIDENCE_REGISTRY_V1", "facts": []},
            6,
            "EVIDENCE_AUTHORED_OR_REVIEWED",
        ),
        (
            {"schema_version": "QUESTION_SEED_DEVELOPMENT_ITEMS_V1", "items": []},
            7,
            "QUESTION_GENERATED_OR_REVIEWED",
        ),
        (
            {
                "schema_version": "MODEL_CANDIDATE_EVIDENCE_AND_CONCEPT_LIBRARY_V2_MILESTONE",
                "architecture_outcome": "USED_TO_SET_PRODUCTION_RECOMMENDATION",
                "rows": [],
            },
            8,
            "OUTCOME_USED_FOR_ARCHITECTURE",
        ),
        (
            {"scope": "REGISTRY_V2_FINAL_SEMANTIC_ADJUDICATION_INPUT", "candidates": []},
            1,
            "METADATA_ONLY",
        ),
        (
            {"scope": "REGISTRY_V2_SEMANTIC_REVIEW_EXPOSURE", "rows": []},
            3,
            "PREREQUISITE_SEMANTICS_REVIEWED",
        ),
        (
            {"scope": "V2_BENCHMARK_COMPARISON_FINAL", "architecture_outcome": "PRODUCTION_GATE"},
            8,
            "OUTCOME_USED_FOR_ARCHITECTURE",
        ),
        (
            {"scope": "V1_PARTIAL_MATCH_BLINDED_FORENSIC_SAMPLE", "pairs": []},
            1,
            "METADATA_ONLY",
        ),
        (
            {"scope": "BLINDED_BENCHMARK_GRANULARITY_SAMPLE_V1", "opportunities": []},
            1,
            "METADATA_ONLY",
        ),
        (
            {"scope": "INDEPENDENT_BENCHMARK_GRANULARITY_AUDIT_V1", "row_audits": []},
            1,
            "METADATA_ONLY",
        ),
        (
            {"scope": "INDEPENDENT_PARTIAL_MATCH_SEMANTIC_REVIEW_V1", "reviews": []},
            3,
            "PREREQUISITE_SEMANTICS_REVIEWED",
        ),
        (
            {"scope": "INDEPENDENT_BENCHMARK_GRANULARITY_SEMANTIC_REVIEW_V1", "reviews": []},
            3,
            "PREREQUISITE_SEMANTICS_REVIEWED",
        ),
        (
            {"scope": "ATOMIC_OPPORTUNITY_SEMANTIC_REVIEW_EXPOSURE_V1", "rows": []},
            3,
            "PREREQUISITE_SEMANTICS_REVIEWED",
        ),
        (
            {"scope": "V1_V2_PARTIAL_MATCH_FORENSICS", "rows": []},
            8,
            "OUTCOME_USED_FOR_ARCHITECTURE",
        ),
        (
            {"scope": "MATCHER_V3_GOLD_RELATION_BLINDED_REVIEW_INPUT", "pairs": []},
            1,
            "METADATA_ONLY",
        ),
        (
            {"scope": "MATCHER_V3_INDEPENDENT_GOLD_RELATION_SET_V1", "reviews": []},
            3,
            "PREREQUISITE_SEMANTICS_REVIEWED",
        ),
        (
            {"scope": "NORMALIZED_ATOMIC_OPPORTUNITY_BENCHMARK_V2", "opportunities": []},
            8,
            "OUTCOME_USED_FOR_ARCHITECTURE",
        ),
        (
            {"scope": "BENCHMARK_MATCHER_V3_HELDOUT_VALIDATION", "architecture_outcome": "STOP"},
            8,
            "OUTCOME_USED_FOR_ARCHITECTURE",
        ),
    ],
)
def test_artifact_semantics_map_to_required_exposure_level(
    document, expected_level, expected_status
):
    classification = classify_artifact("irrelevant/name.json", document)
    assert classification.level == expected_level
    assert classification.status == expected_status


def test_ambiguous_artifact_fails_closed():
    classification = classify_artifact(
        "research/qgen/mystery.json",
        {"schema_version": "UNKNOWN_QGEN_ARTIFACT", "rows": [{"study_unit_id": "SU-X-01"}]},
    )
    assert classification.level == AMBIGUOUS_LEVEL
    assert classification.status == "AMBIGUOUS"
    assert classification.clean_transfer_eligible is False


def test_aggregation_preserves_history_and_chooses_maximum_level():
    events = [
        {
            "event_id": "EV-LOW",
            "study_unit_id": "SU-X-01",
            "exposure_level": 0,
            "exposure_status": "INVENTORY_ONLY",
            "milestone": "inventory",
            "clinical_semantics_inspected": False,
            "candidates_inspected": False,
            "evidence_authored": False,
            "questions_generated": False,
            "outcomes_influenced_architecture": False,
        },
        {
            "event_id": "EV-HIGH",
            "study_unit_id": "SU-X-01",
            "exposure_level": 6,
            "exposure_status": "EVIDENCE_AUTHORED_OR_REVIEWED",
            "milestone": "evidence",
            "clinical_semantics_inspected": True,
            "candidates_inspected": True,
            "evidence_authored": True,
            "questions_generated": False,
            "outcomes_influenced_architecture": False,
        },
    ]
    [row] = aggregate_registry(
        [{"study_unit_id": "SU-X-01", "discipline": "MED", "study_unit": "Example"}],
        events,
    )
    assert row["max_exposure_level"] == 6
    assert row["source_event_ids"] == ["EV-LOW", "EV-HIGH"]
    assert row["ever_evidence_authored"] is True
    assert row["clean_transfer_eligible"] is False


def test_inventory_event_cannot_downgrade_prior_exposure():
    events = [
        {
            "event_id": "EV-EXPOSED",
            "study_unit_id": "SU-X-01",
            "exposure_level": 3,
            "exposure_status": "PREREQUISITE_SEMANTICS_REVIEWED",
            "milestone": "semantics",
            "clinical_semantics_inspected": True,
            "candidates_inspected": False,
            "evidence_authored": False,
            "questions_generated": False,
            "outcomes_influenced_architecture": False,
        },
        {
            "event_id": "EV-INVENTORY-LATER",
            "study_unit_id": "SU-X-01",
            "exposure_level": 0,
            "exposure_status": "INVENTORY_ONLY",
            "milestone": "later inventory",
            "clinical_semantics_inspected": False,
            "candidates_inspected": False,
            "evidence_authored": False,
            "questions_generated": False,
            "outcomes_influenced_architecture": False,
        },
    ]
    [row] = aggregate_registry(
        [{"study_unit_id": "SU-X-01", "discipline": "MED", "study_unit": "Example"}],
        events,
    )
    assert row["max_exposure_level"] == 3
    assert row["clean_transfer_eligible"] is False


def test_confirmed_exposure_is_not_hidden_by_an_ambiguous_event():
    base = {
        "study_unit_id": "SU-X-01",
        "clinical_semantics_inspected": False,
        "candidates_inspected": False,
        "evidence_authored": False,
        "questions_generated": False,
        "outcomes_influenced_architecture": False,
    }
    events = [
        {**base, "event_id": "EV-UNKNOWN", "exposure_level": AMBIGUOUS_LEVEL, "exposure_status": "AMBIGUOUS", "milestone": "unknown"},
        {**base, "event_id": "EV-EXPOSED", "exposure_level": 8, "exposure_status": "OUTCOME_USED_FOR_ARCHITECTURE", "milestone": "development", "outcomes_influenced_architecture": True},
    ]
    [row] = aggregate_registry(
        [{"study_unit_id": "SU-X-01", "discipline": "MED", "study_unit": "Example"}],
        events,
    )
    assert row["max_exposure_level"] == 8
    assert row["exposure_status"] == "OUTCOME_USED_FOR_ARCHITECTURE"
    assert row["clean_transfer_eligible"] is False


def test_transfer_in_filename_does_not_determine_exposure():
    classification = classify_artifact(
        "research/qgen/transfer_results_scary_name.json",
        {"scope": "QGEN_FRESH_HOLDOUT_ELIGIBLE_INVENTORY", "candidates": []},
    )
    assert classification.level == 0
    assert classification.status == "INVENTORY_ONLY"


def test_repository_positive_controls_and_registry_v2_semantic_exposure(repo_root):
    registry = build_registry(repo_root)
    by_id = {row["study_unit_id"]: row for row in registry["rows"]}

    assert by_id["SU-D-29"]["max_exposure_level"] == 8
    assert by_id["SU-C-08"]["max_exposure_level"] >= 3
    assert by_id["SU-A-04"]["max_exposure_level"] == 3
    assert by_id["SU-A-04"]["clean_transfer_eligible"] is False


def test_curriculum_planning_metadata_is_not_misclassified_as_semantic_outcome_exposure():
    inventory = classify_artifact(
        "research/qgen/opportunity_registry/curriculum_input_snapshot_v1.json",
        {"schema_version": "1.0", "scope": "CURRICULUM_INPUT_SNAPSHOT_V1"},
    )
    registry = classify_artifact(
        "research/qgen/opportunity_registry/curriculum_question_opportunity_registry_v1.json",
        {"schema_version": "1.0", "scope": "CURRICULUM_QUESTION_OPPORTUNITY_REGISTRY_V1"},
    )
    review = classify_artifact(
        "research/qgen/opportunity_registry/opportunity_independent_review_v1.json",
        {"schema_version": "1.0", "scope": "INDEPENDENT_OPPORTUNITY_REVIEW_V1"},
    )
    assert inventory.level == 0
    assert registry.level == 1
    assert review.level == 3


def test_blocked_422740_cohort_is_exposed_by_semantic_events(repo_root):
    registry = build_registry(repo_root)
    by_id = {row["study_unit_id"]: row for row in registry["rows"]}
    blocked = __import__("json").loads(
        (repo_root / "research/qgen/contrast_supply/new_clean_transfer_18_selection_v2.json").read_text()
    )
    rows = [by_id[row["study_unit_id"]] for row in blocked["rows"]]
    assert len(rows) == 18
    assert all(row["max_exposure_level"] >= 3 for row in rows)
    assert all(row["clean_transfer_eligible"] is False for row in rows)
