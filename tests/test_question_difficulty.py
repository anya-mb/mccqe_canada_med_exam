"""Difficulty intent, its falsifiable checks, and the empirical psychometric schema.

Two boundaries are load-bearing and are asserted rather than documented. Authored
difficulty is never presented as measured difficulty: DIFFICULTY_INTENT and
EMPIRICAL_DIFFICULTY are separate fields that cannot overwrite one another, and
every empirical field is null until a learner answers. And difficulty is never
produced by trickery: a classification that rests on stem length, option count,
rarity or obscure vocabulary is refused, because the MCC's own item-writing
guidance calls that irrelevant difficulty.
"""

import json
from pathlib import Path

import pytest

from qbank.question_difficulty import (
    DIFFICULTY_DIMENSIONS,
    DIFFICULTY_INTENTS,
    EMPIRICAL_FIELDS,
    ITEM_STATUSES,
    LIBRARY_DIFFICULTY_POLICY,
    PROHIBITED_DIFFICULTY_SOURCES,
    DifficultyError,
    classify_difficulty,
    empty_psychometric_record,
    evaluate_difficulty_checks,
    validate_difficulty_record,
)

ROOT = Path(__file__).resolve().parents[1]


def evidence(**overrides):
    """A structured difficulty-evidence record, of the shape the pipeline produces."""
    base = {
        "key_discriminator_count": 2,
        "load_bearing_stem_feature_count": 3,
        "live_competitors_after_floor": 3,
        "competitors_defeated_by_explicit_verbal_denial": 0,
        "competitors_with_at_least_one_anchor_present": 3,
        "mean_anchors_present_per_competitor": 2.0,
        "has_sequencing_or_threshold_constraint": True,
        "dimensions": {name: 2 for name in DIFFICULTY_DIMENSIONS},
        "rationale": (
            "Three stem features must be integrated and the most salient datum does "
            "not meet its own threshold; every competitor is anchored on a different "
            "stated datum."
        ),
    }
    base.update(overrides)
    return base


# ------------------------------------------------------------------ policy


def test_the_library_mix_is_labelled_as_policy_and_not_as_an_mcc_distribution():
    assert LIBRARY_DIFFICULTY_POLICY["EASY"] == 20
    assert LIBRARY_DIFFICULTY_POLICY["MEDIUM"] == 55
    assert LIBRARY_DIFFICULTY_POLICY["HARD"] == 25
    assert LIBRARY_DIFFICULTY_POLICY["POLICY_STATUS"] == "INITIAL_LEARNING_DESIGN_POLICY"
    assert LIBRARY_DIFFICULTY_POLICY["DERIVED_FROM_MCC_DISTRIBUTION"] is False


def test_the_three_intents_and_seven_dimensions_are_the_declared_ones():
    assert DIFFICULTY_INTENTS == ("EASY", "MEDIUM", "HARD")
    assert set(DIFFICULTY_DIMENSIONS) == {
        "discriminator_salience", "feature_integration_count", "competitor_similarity",
        "sequencing_demand", "timing_severity_demand", "comorbidity_context",
        "data_interpretation_demand",
    }


# ------------------------------------------------------------ classification


def test_a_hard_item_meets_the_hard_checks():
    verdict = evaluate_difficulty_checks("HARD", evidence())
    assert verdict["satisfied"] is True
    assert verdict["failed_checks"] == []


def test_a_claimed_hard_item_whose_stem_switches_its_competitors_off_is_not_hard():
    """The design's own check: HARD permits zero explicit verbal denials."""
    verdict = evaluate_difficulty_checks(
        "HARD", evidence(competitors_defeated_by_explicit_verbal_denial=2)
    )
    assert verdict["satisfied"] is False
    assert "competitors_defeated_by_explicit_verbal_denial" in verdict["failed_checks"]


def test_no_level_may_fall_below_three_live_competitors():
    for intent in DIFFICULTY_INTENTS:
        verdict = evaluate_difficulty_checks(
            intent, evidence(live_competitors_after_floor=2,
                             competitors_with_at_least_one_anchor_present=2)
        )
        assert verdict["satisfied"] is False, intent


def test_no_level_may_carry_an_anchorless_competitor():
    verdict = evaluate_difficulty_checks(
        "EASY", evidence(key_discriminator_count=1, load_bearing_stem_feature_count=1,
                         mean_anchors_present_per_competitor=1.0,
                         has_sequencing_or_threshold_constraint=False,
                         competitors_with_at_least_one_anchor_present=2)
    )
    assert verdict["satisfied"] is False
    assert "competitors_with_at_least_one_anchor_present" in verdict["failed_checks"]


def test_an_easy_item_is_still_a_real_item():
    verdict = evaluate_difficulty_checks(
        "EASY", evidence(key_discriminator_count=1, load_bearing_stem_feature_count=1,
                         mean_anchors_present_per_competitor=1.0,
                         competitors_defeated_by_explicit_verbal_denial=1,
                         has_sequencing_or_threshold_constraint=False)
    )
    assert verdict["satisfied"] is True


def test_classification_requires_a_rationale():
    with pytest.raises(DifficultyError):
        classify_difficulty(evidence(rationale=""))
    with pytest.raises(DifficultyError):
        classify_difficulty(evidence(rationale=None))


# --------------------------------------------------- prohibited difficulty


@pytest.mark.parametrize("source", PROHIBITED_DIFFICULTY_SOURCES)
def test_a_rationale_resting_on_a_prohibited_difficulty_source_is_refused(source):
    record = evidence(rationale=f"This item is hard because of {source.lower()}.")
    with pytest.raises(DifficultyError) as caught:
        classify_difficulty(record, declared_intent="HARD")
    assert source in str(caught.value)


def test_difficulty_cannot_be_claimed_from_stem_length_option_count_or_rarity():
    for phrase in (
        "the stem is very long", "there are five options rather than four",
        "the condition is rare", "the terminology is obscure",
    ):
        with pytest.raises(DifficultyError):
            classify_difficulty(evidence(rationale=phrase), declared_intent="HARD")


def test_a_difficulty_target_that_cannot_be_met_fails_closed_rather_than_degrading():
    result = classify_difficulty(
        evidence(competitors_defeated_by_explicit_verbal_denial=3),
        declared_intent="HARD",
        fail_closed=True,
    )
    assert result["verdict"] == "FAIL_CLOSED_DIFFICULTY_TARGET_NOT_MET"
    assert result["option_set_was_not_degraded"] is True


# --------------------------------------------------------------- records


def test_a_valid_difficulty_record_round_trips_against_its_schema():
    record = classify_difficulty(evidence(), declared_intent="HARD")
    validate_difficulty_record(record)
    assert record["difficulty_intent"] == "HARD"
    assert record["difficulty_rationale"]
    assert set(record["difficulty_dimensions"]) == set(DIFFICULTY_DIMENSIONS)


def test_intent_and_empirical_difficulty_are_separate_and_never_overwrite(tmp_path):
    record = classify_difficulty(evidence(), declared_intent="HARD")
    psychometrics = empty_psychometric_record()
    assert record["difficulty_intent"] == "HARD"
    assert psychometrics["empirical_difficulty"] is None
    assert "difficulty_intent" not in psychometrics
    assert "empirical_difficulty" not in record


# ------------------------------------------------------------ psychometrics


def test_a_new_item_enters_beta_with_every_empirical_field_null():
    record = empty_psychometric_record()
    assert record["item_status"] == "BETA"
    for field in EMPIRICAL_FIELDS:
        assert record[field] is None, field
    assert record["response_count"] == 0


def test_the_item_lifecycle_is_the_declared_one():
    assert ITEM_STATUSES == ("DRAFT", "BETA", "ACTIVE", "FLAGGED", "RETIRED")


def test_no_empirical_value_can_be_fabricated_without_responses():
    with pytest.raises(DifficultyError):
        empty_psychometric_record(percent_correct=0.62)
    with pytest.raises(DifficultyError):
        empty_psychometric_record(response_count=0, item_discrimination=0.3)


def test_an_empirical_value_is_accepted_once_responses_exist():
    record = empty_psychometric_record(response_count=140, percent_correct=0.62)
    assert record["response_count"] == 140
    assert record["percent_correct"] == 0.62
    assert record["item_status"] == "BETA"
    assert record["achieved_n_recorded_alongside_every_value"] is True


def test_no_minimum_sample_size_is_invented():
    record = empty_psychometric_record()
    assert record["minimum_sample_size"] is None
    assert "POLICY_DECISION_ONCE_DATA_EXISTS" in record["minimum_sample_size_note"]
