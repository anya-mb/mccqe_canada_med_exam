from __future__ import annotations

import pytest

from scripts.qbank.question_seed import (
    QuestionSeedError,
    classify_item_duplicate,
    classify_seed_duplicate,
    item_semantic_fingerprint,
    seed_fingerprint,
    select_candidate_subset,
    validate_question_seed,
)


def _seed(**overrides):
    row = {
        "seed_id": "SEED-1",
        "discipline": "MED",
        "toronto_notes_chapter_topic": "Dermatology",
        "study_unit_id": "SU-D-29",
        "clinical_concept": "Scabies",
        "learner_decision": "Identify scabies.",
        "response_class": "DIAGNOSIS",
        "clinical_stage": "INITIAL_RECOGNITION",
        "population": "ADULT_GENERAL",
        "key": "SCABIES",
        "mcc_blueprint_dimensions": ["38"],
        "difficulty_target": "MODERATE",
        "primary_discriminator": "household exposure and distribution",
        "candidate_universe_id": "A-1",
        "candidate_subset_strategy": "TIER_BALANCED_DISTINCT",
        "generation_family": "DIAGNOSIS",
        "decision_granularity": "DIAGNOSIS",
    }
    row.update(overrides)
    return row


def test_seed_requires_every_architecture_field():
    seed = _seed()
    seed.pop("primary_discriminator")
    assert validate_question_seed(seed) == ["MISSING_REQUIRED_FIELD:primary_discriminator"]


def test_seed_fingerprint_is_deterministic_and_ignores_seed_id():
    assert seed_fingerprint(_seed()) == seed_fingerprint(_seed(seed_id="SEED-OTHER"))


def test_seed_duplicate_uses_teaching_objective_not_wording():
    left = _seed(learner_decision="Identify scabies.")
    right = _seed(seed_id="S2", learner_decision="  identify  SCABIES ")
    assert classify_seed_duplicate(left, right) == "DUPLICATE"


def test_seed_with_distinct_decision_family_is_related_but_distinct():
    right = _seed(
        seed_id="S2",
        learner_decision="Treat scabies.",
        response_class="MANAGEMENT_ACTION",
        generation_family="INITIAL_MANAGEMENT",
        decision_granularity="SINGLE_NEXT_ACTION",
        primary_discriminator="appropriate eradication treatment",
    )
    assert classify_seed_duplicate(_seed(), right) == "RELATED_BUT_DISTINCT"


def test_seed_with_same_illness_and_distinct_clinical_stage_is_related_but_distinct():
    right = _seed(
        seed_id="S2",
        clinical_stage="POST_DIAGNOSIS_MANAGEMENT",
        primary_discriminator="treatment response after confirmed infestation",
    )
    assert classify_seed_duplicate(_seed(), right) == "RELATED_BUT_DISTINCT"


def test_subset_selection_is_reproducible_and_excludes_wrong_class_or_granularity():
    candidates = [
        {
            "canonical_candidate_id": f"C-{index}",
            "response_class": "DIAGNOSIS" if index != 4 else "MANAGEMENT_ACTION",
            "granularity": "DIAGNOSIS" if index != 3 else "SYNDROME",
            "quality_tier": "TIER_A_STRONG_DISTRACTOR" if index < 2 else "TIER_B_GOOD_DISTRACTOR",
            "final_admission_state": "ADMITTED",
        }
        for index in range(5)
    ]
    first = select_candidate_subset(_seed(), candidates, size=2)
    second = select_candidate_subset(_seed(), list(reversed(candidates)), size=2)
    assert first == second
    assert set(first).issubset({"C-0", "C-1", "C-2"})


def test_subset_selection_fails_closed_when_fewer_than_three_live_candidates():
    with pytest.raises(QuestionSeedError, match="three"):
        select_candidate_subset(_seed(), [], size=3)


def test_item_fingerprint_is_semantic_not_textual():
    item = {
        "learner_objective": "Identify scabies",
        "stem_clinical_state": "pruritic household eruption",
        "lead_in": "What is the diagnosis?",
        "correct_concept": "SCABIES",
        "primary_discriminator": "distribution",
        "option_concept_set": ["SCABIES", "ECZEMA", "CONTACT DERMATITIS"],
    }
    paraphrase = {**item, "lead_in": "Which diagnosis is most likely?", "option_concept_set": list(reversed(item["option_concept_set"]))}
    assert item_semantic_fingerprint(item) == item_semantic_fingerprint(paraphrase)
    assert classify_item_duplicate(item, paraphrase) == "DUPLICATE"


def test_item_with_same_objective_but_changed_state_is_near_duplicate():
    left = {
        "learner_objective": "Identify scabies",
        "stem_clinical_state": "household exposure",
        "lead_in": "Diagnosis?",
        "correct_concept": "SCABIES",
        "primary_discriminator": "distribution",
        "option_concept_set": ["SCABIES", "ECZEMA", "CONTACT"],
    }
    right = {**left, "stem_clinical_state": "institutional exposure"}
    assert classify_item_duplicate(left, right) == "NEAR_DUPLICATE"


def test_item_with_same_objective_and_superficially_changed_options_is_near_duplicate():
    left = {
        "learner_objective": "Identify scabies",
        "stem_clinical_state": "household exposure",
        "clinical_stage": "INITIAL_RECOGNITION",
        "lead_in": "Diagnosis?",
        "correct_concept": "SCABIES",
        "primary_discriminator": "distribution",
        "option_concept_set": ["SCABIES", "ECZEMA", "CONTACT"],
    }
    right = {
        **left,
        "stem_clinical_state": "shelter exposure",
        "primary_discriminator": "nocturnal itch",
        "option_concept_set": ["SCABIES", "BEDBUGS", "ECZEMA"],
    }
    assert classify_item_duplicate(left, right) == "NEAR_DUPLICATE"


def test_item_with_same_topic_but_distinct_clinical_stage_is_related_but_distinct():
    left = {
        "learner_objective": "Choose a goals-of-care action",
        "stem_clinical_state": "capable patient",
        "clinical_stage": "CAPABLE_PATIENT_DISCUSSION",
        "lead_in": "Action?",
        "correct_concept": "CLARIFY_GOALS",
        "primary_discriminator": "capacity",
        "option_concept_set": ["CLARIFY_GOALS", "SDM", "PALLIATIVE"],
    }
    right = {**left, "stem_clinical_state": "incapable patient", "clinical_stage": "INCAPACITY_WITH_PRIOR_WISHES"}
    assert classify_item_duplicate(left, right) == "RELATED_BUT_DISTINCT"
