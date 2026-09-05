"""Tests for the contrast-first pilot module.

Written before the module. The point of the architecture is that the contrast set
and the stem blueprint are decided *before* a stem exists, and that the gates
which decide safety are the unchanged production ones, so these tests check two
things above all: that a blueprint cannot be produced unless the floor, the
ceiling and key support hold together, and that nothing here can talk a
competitor past a gate.
"""

from __future__ import annotations

import json

import pytest

from qbank.contrast_first_pilot import (
    CONTRAST_SET_MAXIMUM,
    CONTRAST_SET_MINIMUM,
    REQUIRED_FEATURE_CAP,
    ContrastFirstError,
    admit_pre_stem,
    artifact_id,
    audit_easy_item,
    audit_hard_item,
    build_contrast_matrix,
    contrast_set_retrieval_index,
    difficulty_evidence_from_blueprint,
    evaluate_clinical_coherence,
    revalidate_against_frozen_stem,
    solve_stem_blueprint,
    structural_difficulty_review,
    validate_contrast_matrix,
    validate_contrast_set,
    validate_option_realization,
)


# --------------------------------------------------------------- fixtures


VOCABULARY = {
    "SF-KEY-A": {"clinical_role": "INVESTIGATION_RESULT", "normalized_feature": "key datum A"},
    "SF-KEY-B": {"clinical_role": "TIME_COURSE", "normalized_feature": "key datum B"},
    "SF-KEY-C": {"clinical_role": "EXAMINATION_FINDING", "normalized_feature": "key datum C"},
    "SF-SHARED-1": {"clinical_role": "SYMPTOM", "normalized_feature": "shared symptom one"},
    "SF-SHARED-2": {"clinical_role": "VITAL_SIGN", "normalized_feature": "shared vital two"},
    "SF-SHARED-3": {"clinical_role": "HISTORY", "normalized_feature": "shared history three"},
    "SF-SHARED-4": {"clinical_role": "SYMPTOM", "normalized_feature": "shared symptom four"},
    "SF-ONLY-1": {"clinical_role": "INVESTIGATION_RESULT", "normalized_feature": "competitor one datum"},
    "SF-ONLY-2": {"clinical_role": "INVESTIGATION_RESULT", "normalized_feature": "competitor two datum"},
    "SF-ONLY-3": {"clinical_role": "INVESTIGATION_RESULT", "normalized_feature": "competitor three datum"},
    "SF-COLLATERAL": {"clinical_role": "COLLATERAL_SOURCE", "normalized_feature": "collateral account"},
}


def competitor(
    seed_id,
    *,
    anchors,
    conditions,
    granularity="SINGLE_DIAGNOSIS",
    tokens=("PLAUSIBLE_DIAGNOSTIC_ENTITY",),
    disciplines=("MEDICINE",),
    item_archetypes=("DIAGNOSIS",),
    option_set_archetypes=("DIAGNOSIS_SET",),
    verdict="PASS",
    same_lead_in="PASS",
    same_category="PASS",
    consideration="A partially knowledgeable candidate anchors on the shared symptom.",
    plausibility_refs=("CLM-P",),
    discrimination_refs=("CLM-D",),
    discovery_sources=("CURATED_LIBRARY",),
):
    return {
        "seed_id": seed_id,
        "competitor_concept": seed_id.replace("SEED-", "").replace("-", " ").title(),
        "competitor_concept_id": f"CONCEPT-{seed_id}",
        "competitor_study_unit_id": "SU-TEST",
        "competitor_decision_granularity": granularity,
        "response_class_tokens": list(tokens),
        "applicable_disciplines": list(disciplines),
        "applicable_item_archetypes": list(item_archetypes),
        "option_set_archetypes": list(option_set_archetypes),
        "plausibility_anchor_feature_ids": list(anchors),
        "condition_predicates": [
            {"stem_feature_id": f, "required_polarity": p} for f, p in conditions
        ],
        "shared_features_with_key": ["a shared clinical shape"],
        "candidate_visible_discriminators": ["the datum that defeats it is stated"],
        "conditions_under_which_competitor_would_be_correct": "stated for the seed",
        "why_a_minimally_competent_candidate_would_consider_it": consideration,
        "evidence_refs_for_plausibility": list(plausibility_refs),
        "evidence_refs_for_discrimination": list(discrimination_refs),
        "independent_seed_review": {
            "verdict": verdict,
            "same_lead_in_dimension": same_lead_in,
            "same_semantic_category": same_category,
            "comparable_decision_granularity": "PASS",
            "reviewed_strength": "STRONG",
        },
        "requires_terminal_exclusion_clue": False,
        "discovery_sources": list(discovery_sources),
    }


def contrast_set(competitors=None, *, difficulty_intent="MEDIUM", key_conditions=None):
    return {
        "contrast_set_id": "CFS-TEST-01",
        "opportunity_label": "T-TEST-01",
        "discipline_profile_id": "MEDICINE",
        "learner_decision_id": "LD-TEST-01",
        "item_archetype": "DIAGNOSIS",
        "option_set_archetype": "DIAGNOSIS_SET",
        "demanded_response_class": "PLAUSIBLE_DIAGNOSTIC_ENTITY",
        "decision_granularity": "SINGLE_DIAGNOSIS",
        "difficulty_intent": difficulty_intent,
        "anchor_study_unit_id": "SU-TEST",
        "priority_class": "CORE",
        "key": {
            "key_concept": "The keyed diagnosis",
            "key_concept_id": "CONCEPT-KEY",
            "correctness_conditions": key_conditions
            or [
                {"stem_feature_id": "SF-KEY-A", "required_polarity": "PRESENT"},
                {"stem_feature_id": "SF-KEY-B", "required_polarity": "PRESENT"},
            ],
            "evidence_refs": ["CLM-KEY"],
        },
        "competitors": competitors
        if competitors is not None
        else [
            competitor(
                "SEED-ONE",
                anchors=["SF-SHARED-1"],
                conditions=[("SF-ONLY-1", "PRESENT"), ("SF-SHARED-1", "PRESENT")],
            ),
            competitor(
                "SEED-TWO",
                anchors=["SF-SHARED-2"],
                conditions=[("SF-ONLY-2", "PRESENT"), ("SF-SHARED-2", "PRESENT")],
            ),
            competitor(
                "SEED-THREE",
                anchors=["SF-SHARED-3"],
                conditions=[("SF-ONLY-3", "PRESENT"), ("SF-SHARED-3", "PRESENT")],
            ),
        ],
    }


KEY_CONTEXT = {
    "discipline_profile_id": "MEDICINE",
    "item_archetype": "DIAGNOSIS",
    "option_set_archetype": "DIAGNOSIS_SET",
    "demanded_response_class": "PLAUSIBLE_DIAGNOSTIC_ENTITY",
    "decision_granularity": "SINGLE_DIAGNOSIS",
}


# --------------------------------------------- pre-stem admission predicate


def test_a_well_formed_candidate_is_admitted_before_any_stem_exists():
    verdict = admit_pre_stem(competitor("SEED-ONE", anchors=["SF-SHARED-1"],
                                        conditions=[("SF-ONLY-1", "PRESENT")]),
                             key_context=KEY_CONTEXT)
    assert verdict["admitted"] is True
    assert verdict["refusals"] == []


def test_same_decision_is_enforced_before_the_stem():
    candidate = competitor("SEED-ONE", anchors=["SF-SHARED-1"],
                           conditions=[("SF-ONLY-1", "PRESENT")], same_lead_in="FAIL")
    verdict = admit_pre_stem(candidate, key_context=KEY_CONTEXT)
    assert verdict["admitted"] is False
    assert "PRE_STEM_LEARNER_DECISION_MISMATCH" in verdict["refusals"]


def test_response_class_closure_is_enforced_before_the_stem():
    candidate = competitor("SEED-ONE", anchors=["SF-SHARED-1"],
                           conditions=[("SF-ONLY-1", "PRESENT")],
                           tokens=("ETHICAL_ACTION",))
    verdict = admit_pre_stem(candidate, key_context=KEY_CONTEXT)
    assert "PRE_STEM_RESPONSE_CLASS_MISMATCH" in verdict["refusals"]


def test_archetype_is_enforced_before_the_stem():
    candidate = competitor("SEED-ONE", anchors=["SF-SHARED-1"],
                           conditions=[("SF-ONLY-1", "PRESENT")],
                           option_set_archetypes=("NEXT_ACTION_SET",))
    verdict = admit_pre_stem(candidate, key_context=KEY_CONTEXT)
    assert "PRE_STEM_ARCHETYPE_MISMATCH" in verdict["refusals"]


def test_granularity_parity_is_enforced_before_the_stem():
    candidate = competitor("SEED-ONE", anchors=["SF-SHARED-1"],
                           conditions=[("SF-ONLY-1", "PRESENT")],
                           granularity="COMPLETE_MANAGEMENT_STRATEGY")
    verdict = admit_pre_stem(candidate, key_context=KEY_CONTEXT)
    assert "PRE_STEM_GRANULARITY_MISMATCH" in verdict["refusals"]


def test_a_candidate_without_an_independent_review_is_refused():
    candidate = competitor("SEED-ONE", anchors=["SF-SHARED-1"],
                           conditions=[("SF-ONLY-1", "PRESENT")], verdict="FAIL")
    assert "PRE_STEM_REVIEW_ABSENT" in admit_pre_stem(candidate, key_context=KEY_CONTEXT)["refusals"]


def test_a_candidate_without_evidence_on_both_sides_is_refused():
    candidate = competitor("SEED-ONE", anchors=["SF-SHARED-1"],
                           conditions=[("SF-ONLY-1", "PRESENT")], discrimination_refs=())
    assert "PRE_STEM_EVIDENCE_ABSENT" in admit_pre_stem(candidate, key_context=KEY_CONTEXT)["refusals"]


def test_a_competitor_nobody_could_seriously_consider_is_removed_before_the_stem():
    candidate = competitor("SEED-ONE", anchors=["SF-SHARED-1"],
                           conditions=[("SF-ONLY-1", "PRESENT")], consideration="  ")
    verdict = admit_pre_stem(candidate, key_context=KEY_CONTEXT)
    assert verdict["admitted"] is False
    assert "FAIL_CLOSED_COMPETITOR_NOT_CONSIDERABLE" in verdict["refusals"]


# ------------------------------------------------------ contrast-set schema


def test_a_valid_contrast_set_validates():
    validate_contrast_set(contrast_set())


def test_a_contrast_set_below_the_minimum_fails_closed():
    small = contrast_set()
    small["competitors"] = small["competitors"][:CONTRAST_SET_MINIMUM - 1]
    with pytest.raises(ContrastFirstError, match="FAIL_CLOSED_CONTRAST_SET_SIZE"):
        validate_contrast_set(small)


def test_a_contrast_set_above_the_maximum_fails_closed():
    big = contrast_set()
    big["competitors"] = [
        competitor(f"SEED-{n}", anchors=["SF-SHARED-1"], conditions=[("SF-ONLY-1", "PRESENT")])
        for n in range(CONTRAST_SET_MAXIMUM + 1)
    ]
    with pytest.raises(ContrastFirstError, match="FAIL_CLOSED_CONTRAST_SET_SIZE"):
        validate_contrast_set(big)


def test_a_contrast_set_carrying_an_inadmissible_competitor_fails_closed():
    bad = contrast_set()
    bad["competitors"][1] = competitor(
        "SEED-TWO", anchors=["SF-SHARED-2"], conditions=[("SF-ONLY-2", "PRESENT")],
        granularity="COMPLETE_MANAGEMENT_STRATEGY",
    )
    with pytest.raises(ContrastFirstError, match="PRE_STEM_GRANULARITY_MISMATCH"):
        validate_contrast_set(bad)


def test_the_key_may_not_appear_among_its_own_competitors():
    bad = contrast_set()
    bad["competitors"][0]["competitor_concept_id"] = "CONCEPT-KEY"
    with pytest.raises(ContrastFirstError, match="key"):
        validate_contrast_set(bad)


def test_a_contrast_set_without_key_correctness_conditions_fails_closed():
    bad = contrast_set()
    bad["key"]["correctness_conditions"] = []
    with pytest.raises(ContrastFirstError, match="correctness"):
        validate_contrast_set(bad)


# ---------------------------------------------------------- contrast matrix


def test_the_matrix_records_every_required_block_for_every_competitor():
    matrix = build_contrast_matrix(contrast_set())
    assert len(matrix["rows"]) == 3
    for row in matrix["rows"]:
        for block in (
            "SHARED_PLAUSIBILITY_FEATURES",
            "SUPPORTING_FEATURES",
            "DEFEATING_DISCRIMINATORS",
            "CORRECTNESS_CONDITIONS",
            "SECOND_KEY_RISK",
            "CATEGORICAL_EXCLUSION_RISK",
            "DECISION_RELEVANCE",
            "EVIDENCE_PROVENANCE",
            "WHY_A_MINIMALLY_COMPETENT_CANDIDATE_WOULD_CONSIDER_IT",
        ):
            assert block in row, block


def test_shared_feature_support_is_required_of_every_matrix_row():
    weak = contrast_set()
    weak["competitors"][0]["plausibility_anchor_feature_ids"] = []
    weak["competitors"][0]["shared_features_with_key"] = []
    matrix = build_contrast_matrix(weak)
    with pytest.raises(ContrastFirstError, match="SHARED_PLAUSIBILITY_FEATURES"):
        validate_contrast_matrix(matrix)


def test_defeating_discriminator_support_is_required_of_every_matrix_row():
    weak = contrast_set()
    weak["competitors"][0]["candidate_visible_discriminators"] = []
    weak["competitors"][0]["condition_predicates"] = []
    matrix = build_contrast_matrix(weak)
    with pytest.raises(ContrastFirstError, match="DEFEATING_DISCRIMINATORS"):
        validate_contrast_matrix(matrix)


def test_evidence_provenance_is_persisted_on_every_matrix_row():
    matrix = build_contrast_matrix(contrast_set())
    for row in matrix["rows"]:
        provenance = row["EVIDENCE_PROVENANCE"]
        assert provenance["plausibility"] and provenance["discrimination"]
        assert row["DISCOVERY_SOURCES"]


def test_a_matrix_row_whose_evidence_is_missing_fails_closed():
    weak = contrast_set()
    weak["competitors"][2]["evidence_refs_for_plausibility"] = []
    matrix = build_contrast_matrix(weak)
    with pytest.raises(ContrastFirstError, match="EVIDENCE"):
        validate_contrast_matrix(matrix)


# -------------------------------------------------------- blueprint solving


def test_the_blueprint_makes_every_competitor_live_and_keeps_the_key_supported():
    blueprint = solve_stem_blueprint(
        build_contrast_matrix(contrast_set()), vocabulary=VOCABULARY
    )
    assert blueprint["fail_closed_reason"] is None
    assert blueprint["key_fully_supported"] is True
    assert blueprint["every_competitor_live"] is True
    assert blueprint["no_second_key"] is True
    required = {row["stem_feature_id"] for row in blueprint["required_features"]}
    assert {"SF-KEY-A", "SF-KEY-B"} <= required
    for anchor in ("SF-SHARED-1", "SF-SHARED-2", "SF-SHARED-3"):
        assert anchor in required


def test_the_blueprint_may_only_name_features_from_the_frozen_vocabulary():
    stray = contrast_set()
    stray["competitors"][0]["plausibility_anchor_feature_ids"] = ["SF-NOT-IN-VOCABULARY"]
    with pytest.raises(ContrastFirstError, match="vocabulary"):
        solve_stem_blueprint(build_contrast_matrix(stray), vocabulary=VOCABULARY)


def test_a_competitor_that_cannot_be_made_live_fails_closed_before_any_stem():
    unlivable = contrast_set()
    unlivable["competitors"][0]["plausibility_anchor_feature_ids"] = []
    blueprint = solve_stem_blueprint(
        build_contrast_matrix(unlivable), vocabulary=VOCABULARY
    )
    assert blueprint["fail_closed_reason"] == "FAIL_CLOSED_BLUEPRINT_UNSATISFIABLE"


def test_a_second_key_is_detected_before_any_stem_is_written():
    # Every correctness condition of SEED-ONE is a key correctness condition, so
    # any stem supporting the key makes SEED-ONE correct too.
    second_key = contrast_set()
    second_key["competitors"][0]["condition_predicates"] = [
        {"stem_feature_id": "SF-KEY-A", "required_polarity": "PRESENT"},
        {"stem_feature_id": "SF-KEY-B", "required_polarity": "PRESENT"},
    ]
    second_key["competitors"][0]["plausibility_anchor_feature_ids"] = ["SF-KEY-A"]
    blueprint = solve_stem_blueprint(
        build_contrast_matrix(second_key), vocabulary=VOCABULARY
    )
    assert blueprint["fail_closed_reason"] == "FAIL_CLOSED_BLUEPRINT_UNSATISFIABLE"
    assert blueprint["no_second_key"] is False


def test_the_blueprint_names_the_features_that_would_create_second_key_risk():
    blueprint = solve_stem_blueprint(
        build_contrast_matrix(contrast_set()), vocabulary=VOCABULARY
    )
    forbidden = {row["stem_feature_id"] for row in blueprint["forbidden_features"]}
    # Each competitor has exactly one unsatisfied condition; stating it would
    # complete that competitor's correctness signature.
    assert {"SF-ONLY-1", "SF-ONLY-2", "SF-ONLY-3"} <= forbidden


def test_the_blueprint_is_deterministic_over_the_same_matrix():
    matrix = build_contrast_matrix(contrast_set())
    first = solve_stem_blueprint(matrix, vocabulary=VOCABULARY)
    second = solve_stem_blueprint(matrix, vocabulary=VOCABULARY)
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)


def test_a_declared_contradiction_pair_cannot_both_be_required():
    matrix = build_contrast_matrix(contrast_set())
    blueprint = solve_stem_blueprint(
        matrix, vocabulary=VOCABULARY,
        contradiction_pairs=[("SF-KEY-A", "SF-SHARED-1")],
    )
    assert blueprint["fail_closed_reason"] in {
        "FAIL_CLOSED_BLUEPRINT_UNSATISFIABLE", "FAIL_CLOSED_CLINICAL_COHERENCE"
    }


# ------------------------------------------------------- coherence contract


def test_a_coherent_blueprint_passes_the_coherence_gate():
    blueprint = solve_stem_blueprint(
        build_contrast_matrix(contrast_set()), vocabulary=VOCABULARY
    )
    verdict = evaluate_clinical_coherence(blueprint, vocabulary=VOCABULARY)
    assert verdict["coherent"] is True
    assert verdict["violations"] == []


def test_a_feature_available_only_when_someone_went_looking_needs_a_stated_reason():
    blueprint = solve_stem_blueprint(
        build_contrast_matrix(contrast_set()), vocabulary=VOCABULARY
    )
    blueprint["required_features"].append({
        "stem_feature_id": "SF-COLLATERAL", "polarity": "PRESENT",
        "roles": ["OPTIONAL_CONTEXT"], "anchors_for": [],
        "clinical_role": "COLLATERAL_SOURCE",
    })
    assert "CO-1" in evaluate_clinical_coherence(blueprint, vocabulary=VOCABULARY)["violations"]
    ok = evaluate_clinical_coherence(
        blueprint, vocabulary=VOCABULARY,
        availability_reasons={"SF-COLLATERAL": "a parent accompanied the patient"},
    )
    assert "CO-1" not in ok["violations"]


def test_stacked_explicit_denials_violate_the_coherence_gate():
    blueprint = solve_stem_blueprint(
        build_contrast_matrix(contrast_set()), vocabulary=VOCABULARY
    )
    for feature in ("SF-ONLY-1", "SF-ONLY-2"):
        blueprint["required_features"].append({
            "stem_feature_id": feature, "polarity": "ABSENT",
            "roles": ["EXPLICIT_DENIAL"], "anchors_for": [],
            "clinical_role": "INVESTIGATION_RESULT",
        })
    assert "CO-2" in evaluate_clinical_coherence(blueprint, vocabulary=VOCABULARY)["violations"]


def test_an_overloaded_blueprint_violates_the_feature_cap():
    blueprint = solve_stem_blueprint(
        build_contrast_matrix(contrast_set(difficulty_intent="EASY")),
        vocabulary=VOCABULARY, difficulty_intent="EASY",
    )
    while len(blueprint["required_features"]) <= REQUIRED_FEATURE_CAP["EASY"]:
        blueprint["required_features"].append({
            "stem_feature_id": f"SF-SHARED-{len(blueprint['required_features'])}",
            "polarity": "PRESENT", "roles": ["OPTIONAL_CONTEXT"], "anchors_for": [],
            "clinical_role": "SYMPTOM",
        })
    assert "CO-4" in evaluate_clinical_coherence(blueprint, vocabulary=VOCABULARY)["violations"]


def test_a_feature_outside_the_vocabulary_violates_the_coherence_gate():
    blueprint = solve_stem_blueprint(
        build_contrast_matrix(contrast_set()), vocabulary=VOCABULARY
    )
    blueprint["required_features"].append({
        "stem_feature_id": "SF-INVENTED", "polarity": "PRESENT",
        "roles": ["OPTIONAL_CONTEXT"], "anchors_for": [], "clinical_role": "SYMPTOM",
    })
    assert "CO-5" in evaluate_clinical_coherence(blueprint, vocabulary=VOCABULARY)["violations"]


# ------------------------------------------------------------- difficulty


def test_difficulty_evidence_is_derived_from_the_blueprint_not_asserted():
    matrix = build_contrast_matrix(contrast_set())
    blueprint = solve_stem_blueprint(matrix, vocabulary=VOCABULARY)
    evidence = difficulty_evidence_from_blueprint(blueprint, matrix)
    assert evidence["live_competitors_after_floor"] == 3
    assert evidence["competitors_with_at_least_one_anchor_present"] == 3
    assert evidence["key_discriminator_count"] == 2
    assert evidence["mean_anchors_present_per_competitor"] >= 1.0
    assert evidence["competitors_defeated_by_explicit_verbal_denial"] == 0


def test_a_declared_difficulty_intent_is_checked_against_that_evidence():
    matrix = build_contrast_matrix(contrast_set())
    blueprint = solve_stem_blueprint(matrix, vocabulary=VOCABULARY)
    evidence = difficulty_evidence_from_blueprint(blueprint, matrix)
    evidence["rationale"] = (
        "Two key conditions must be integrated and each competitor is live on one "
        "shared finding."
    )
    review = structural_difficulty_review(evidence, declared_intent="MEDIUM")
    assert review["STRUCTURAL_DIFFICULTY_REVIEW"] in {"EASY", "MEDIUM", "HARD"}
    assert review["MATCH"] in {"YES", "NO", "UNCERTAIN"}


def test_an_unmeetable_difficulty_target_fails_closed_rather_than_degrading_options():
    matrix = build_contrast_matrix(contrast_set())
    blueprint = solve_stem_blueprint(matrix, vocabulary=VOCABULARY)
    evidence = difficulty_evidence_from_blueprint(blueprint, matrix)
    evidence["rationale"] = "Only one shared finding supports each competitor."
    review = structural_difficulty_review(evidence, declared_intent="HARD")
    assert review["MATCH"] == "NO"
    assert review["option_set_was_not_degraded"] is True


# ------------------------------------------ post-stem anchor revalidation


def _stem_feature_map(assignments):
    return {"features": [
        {"feature_id": feature, "polarity": polarity, "clinical_role": "SYMPTOM"}
        for feature, polarity in sorted(assignments.items())
    ]}


def test_a_stem_realizing_the_blueprint_keeps_three_viable_competitors():
    matrix = build_contrast_matrix(contrast_set())
    blueprint = solve_stem_blueprint(matrix, vocabulary=VOCABULARY)
    realized = {row["stem_feature_id"]: row["polarity"] for row in blueprint["required_features"]}
    result = revalidate_against_frozen_stem(
        contrast_set=contrast_set(),
        stem_feature_map=_stem_feature_map(realized),
        ranking_preference=["STEM_ANCHOR_STRENGTH", "SHARED_FEATURE_COUNT"],
    )
    assert result["post_stem_3_viable"] is True
    assert result["retrieval"]["fail_closed_reason"] is None
    assert result["retrieval"]["anchor_floor_refusals"] == []


def test_a_stem_that_drops_the_blueprint_anchors_loses_its_competitors():
    result = revalidate_against_frozen_stem(
        contrast_set=contrast_set(),
        stem_feature_map=_stem_feature_map({"SF-KEY-A": "PRESENT", "SF-KEY-B": "PRESENT"}),
        ranking_preference=["STEM_ANCHOR_STRENGTH"],
    )
    assert result["post_stem_3_viable"] is False
    assert result["retrieval"]["fail_closed_reason"] == (
        "FAIL_CLOSED_INSUFFICIENT_ADMISSIBLE_COMPETITORS"
    )
    assert len(result["retrieval"]["anchor_floor_refusals"]) == 3


def test_revalidation_uses_the_unchanged_production_second_key_ceiling():
    # Stating a competitor's remaining correctness condition turns it into a
    # second key, and the production ADM_3 rule must be what refuses it.
    result = revalidate_against_frozen_stem(
        contrast_set=contrast_set(),
        stem_feature_map=_stem_feature_map({
            "SF-KEY-A": "PRESENT", "SF-KEY-B": "PRESENT",
            "SF-SHARED-1": "PRESENT", "SF-SHARED-2": "PRESENT",
            "SF-SHARED-3": "PRESENT", "SF-ONLY-1": "PRESENT",
        }),
        ranking_preference=["STEM_ANCHOR_STRENGTH"],
    )
    refusals = [row for row in result["retrieval"]["excluded"] if row["rule"] == "ADM_3"]
    assert [row["seed_id"] for row in refusals] == ["SEED-ONE"]
    assert result["post_stem_3_viable"] is False


def test_the_retrieval_index_rows_carry_every_field_the_production_gate_reads():
    rows = contrast_set_retrieval_index(contrast_set())
    for row in rows:
        for field in (
            "seed_id", "response_class_tokens", "condition_predicates",
            "plausibility_anchor_feature_ids", "normalized_competitor_text",
            "applicable_disciplines", "applicable_item_archetypes",
            "option_set_archetypes", "shared_features_with_key", "reviewed_strength",
        ):
            assert field in row, field


# ------------------------------------------------- option realization


def _options(key="The keyed diagnosis"):
    return [
        {"label": "A", "text": key, "is_key": True, "source": "KEY"},
        {"label": "B", "text": "Seed One", "is_key": False, "source": "SEED-ONE"},
        {"label": "C", "text": "Seed Two", "is_key": False, "source": "SEED-TWO"},
        {"label": "D", "text": "Seed Three", "is_key": False, "source": "SEED-THREE"},
    ]


def test_options_drawn_only_from_the_matrix_and_the_key_are_admissible():
    matrix = build_contrast_matrix(contrast_set())
    verdict = validate_option_realization(_options(), matrix, key_option_text="The keyed diagnosis")
    assert verdict["admissible"] is True
    assert verdict["violations"] == []


def test_an_option_introducing_a_clinical_claim_absent_from_the_matrix_is_refused():
    matrix = build_contrast_matrix(contrast_set())
    options = _options()
    options[2]["source"] = "AUTHORED_FREEHAND"
    verdict = validate_option_realization(options, matrix, key_option_text="The keyed diagnosis")
    assert verdict["admissible"] is False
    assert "OPTION_NOT_TRACEABLE_TO_THE_CONTRAST_MATRIX" in verdict["violations"]


def test_an_option_length_giveaway_is_refused():
    matrix = build_contrast_matrix(contrast_set())
    options = _options(
        key="The keyed diagnosis, established by the documented investigation result "
            "together with the stated time course and the examination finding"
    )
    verdict = validate_option_realization(
        options, matrix,
        key_option_text=(
            "The keyed diagnosis, established by the documented investigation result "
            "together with the stated time course and the examination finding"
        ),
    )
    assert "OPTION_LENGTH_GIVEAWAY" in verdict["violations"]


def test_an_unsupported_qualifier_in_an_option_is_refused():
    matrix = build_contrast_matrix(contrast_set())
    options = _options()
    options[1]["text"] = "Seed One in all cases"
    verdict = validate_option_realization(options, matrix, key_option_text="The keyed diagnosis")
    assert "UNSUPPORTED_QUALIFIER" in verdict["violations"]


def test_a_lone_key_category_is_refused():
    matrix = build_contrast_matrix(contrast_set())
    options = _options()
    for option in options[1:]:
        option["response_class"] = "DIFFERENT_CLASS"
    options[0]["response_class"] = "PLAUSIBLE_DIAGNOSTIC_ENTITY"
    verdict = validate_option_realization(options, matrix, key_option_text="The keyed diagnosis")
    assert "LONE_KEY_CATEGORY" in verdict["violations"]


# ------------------------------------------------ easy and hard item safety


def test_an_easy_item_whose_competitors_are_not_live_is_rejected():
    evidence = {
        "live_competitors_after_floor": 3,
        "competitors_with_at_least_one_anchor_present": 1,
        "competitors_defeated_by_explicit_verbal_denial": 0,
        "key_is_the_only_option_in_its_category": False,
        "stem_explicitly_negates_every_competitor": False,
        "key_copies_stem_language": False,
        "only_one_option_has_appropriate_specificity": False,
    }
    verdict = audit_easy_item(evidence)
    assert verdict["accepted"] is False
    assert "COMPETITORS_NOT_LIVE" in verdict["violations"]


def test_an_easy_item_whose_key_copies_the_stem_is_rejected():
    evidence = {
        "live_competitors_after_floor": 3,
        "competitors_with_at_least_one_anchor_present": 3,
        "competitors_defeated_by_explicit_verbal_denial": 0,
        "key_is_the_only_option_in_its_category": False,
        "stem_explicitly_negates_every_competitor": False,
        "key_copies_stem_language": True,
        "only_one_option_has_appropriate_specificity": False,
    }
    assert "KEY_COPIES_STEM_LANGUAGE" in audit_easy_item(evidence)["violations"]


def test_a_genuinely_easy_item_is_accepted():
    evidence = {
        "live_competitors_after_floor": 3,
        "competitors_with_at_least_one_anchor_present": 3,
        "competitors_defeated_by_explicit_verbal_denial": 0,
        "key_is_the_only_option_in_its_category": False,
        "stem_explicitly_negates_every_competitor": False,
        "key_copies_stem_language": False,
        "only_one_option_has_appropriate_specificity": False,
    }
    assert audit_easy_item(evidence)["accepted"] is True


def test_a_hard_item_resting_on_obscurity_is_rejected():
    evidence = {
        "difficulty_sources": ["COMPETITOR_SIMILARITY", "OBSCURE_TRIVIA"],
        "competing_keys_are_ambiguous": False,
        "information_required_to_decide_is_present": True,
        "gratuitous_calculation": False,
        "trick_wording": False,
    }
    verdict = audit_hard_item(evidence)
    assert verdict["accepted"] is False
    assert "PROHIBITED_DIFFICULTY_SOURCE:OBSCURE_TRIVIA" in verdict["violations"]


def test_a_hard_item_with_missing_information_is_rejected():
    evidence = {
        "difficulty_sources": ["SEQUENCING_DEMAND"],
        "competing_keys_are_ambiguous": False,
        "information_required_to_decide_is_present": False,
        "gratuitous_calculation": False,
        "trick_wording": False,
    }
    assert "MISSING_INFORMATION" in audit_hard_item(evidence)["violations"]


def test_a_legitimately_hard_item_is_accepted():
    evidence = {
        "difficulty_sources": ["COMPETITOR_SIMILARITY", "TIMING_SEVERITY_DEMAND"],
        "competing_keys_are_ambiguous": False,
        "information_required_to_decide_is_present": True,
        "gratuitous_calculation": False,
        "trick_wording": False,
    }
    assert audit_hard_item(evidence)["accepted"] is True


# ------------------------------------------------------ deterministic ids


def test_artifact_ids_are_content_addressed_and_reproducible():
    payload = {"b": 2, "a": [1, 2, 3]}
    assert artifact_id("CFS", payload) == artifact_id("CFS", {"a": [1, 2, 3], "b": 2})
    assert artifact_id("CFS", payload) != artifact_id("CFB", payload)
    assert artifact_id("CFS", payload).startswith("CFS-")


def test_a_changed_payload_changes_the_artifact_id():
    assert artifact_id("CFS", {"a": 1}) != artifact_id("CFS", {"a": 2})


# ------------------------------------------- difficulty-aware anchor targeting


def _rich_contrast_set(intent):
    """Three competitors that each carry two anchors, so HARD is reachable."""
    return contrast_set(
        difficulty_intent=intent,
        key_conditions=[
            {"stem_feature_id": "SF-KEY-A", "required_polarity": "PRESENT"},
            {"stem_feature_id": "SF-KEY-B", "required_polarity": "PRESENT"},
            {"stem_feature_id": "SF-KEY-C", "required_polarity": "PRESENT"},
        ],
        competitors=[
            competitor("SEED-ONE", anchors=["SF-SHARED-1", "SF-SHARED-4"],
                       conditions=[("SF-ONLY-1", "PRESENT"), ("SF-SHARED-1", "PRESENT")]),
            competitor("SEED-TWO", anchors=["SF-SHARED-2", "SF-SHARED-4"],
                       conditions=[("SF-ONLY-2", "PRESENT"), ("SF-SHARED-2", "PRESENT")]),
            competitor("SEED-THREE", anchors=["SF-SHARED-3", "SF-SHARED-4"],
                       conditions=[("SF-ONLY-3", "PRESENT"), ("SF-SHARED-3", "PRESENT")]),
        ],
    )


def test_a_hard_target_raises_anchor_density_instead_of_stem_length():
    matrix = build_contrast_matrix(_rich_contrast_set("HARD"))
    blueprint = solve_stem_blueprint(matrix, vocabulary=VOCABULARY)
    evidence = difficulty_evidence_from_blueprint(blueprint, matrix)
    assert evidence["mean_anchors_present_per_competitor"] >= 2.0
    assert evidence["key_discriminator_count"] == 3
    assert len(blueprint["required_features"]) <= REQUIRED_FEATURE_CAP["HARD"]
    assert blueprint["fail_closed_reason"] is None


def test_an_easy_target_does_not_inflate_anchor_density():
    easy = contrast_set(
        difficulty_intent="EASY",
        key_conditions=[{"stem_feature_id": "SF-KEY-A", "required_polarity": "PRESENT"}],
    )
    matrix = build_contrast_matrix(easy)
    blueprint = solve_stem_blueprint(matrix, vocabulary=VOCABULARY)
    evidence = difficulty_evidence_from_blueprint(blueprint, matrix)
    assert evidence["mean_anchors_present_per_competitor"] == 1.0
    assert evidence["key_discriminator_count"] == 1
    review = structural_difficulty_review(evidence, declared_intent="EASY")
    assert review["MATCH"] == "YES"


def test_anchor_targeting_never_creates_a_second_key():
    # SF-SHARED-4 is an anchor of every competitor and also the last outstanding
    # correctness condition of SEED-TWO, so a HARD target may not state it.
    risky = _rich_contrast_set("HARD")
    risky["competitors"][1]["condition_predicates"] = [
        {"stem_feature_id": "SF-SHARED-2", "required_polarity": "PRESENT"},
        {"stem_feature_id": "SF-SHARED-4", "required_polarity": "PRESENT"},
    ]
    blueprint = solve_stem_blueprint(build_contrast_matrix(risky), vocabulary=VOCABULARY)
    required = {row["stem_feature_id"] for row in blueprint["required_features"]}
    if "SF-SHARED-2" in required:
        assert "SF-SHARED-4" not in required
    assert blueprint["no_second_key"] is True


def test_anchor_targeting_respects_the_required_feature_cap():
    matrix = build_contrast_matrix(_rich_contrast_set("EASY"))
    blueprint = solve_stem_blueprint(matrix, vocabulary=VOCABULARY, difficulty_intent="EASY")
    assert len(blueprint["required_features"]) <= REQUIRED_FEATURE_CAP["EASY"]


# ------------------------------------- profile token implications in P2


def test_a_declared_token_implication_admits_a_candidate_the_bare_token_would_refuse():
    context = dict(KEY_CONTEXT, option_set_archetype="DISPOSITION_SET",
                   demanded_response_class="SECURES_IMMEDIATE_SAFETY",
                   item_archetype="SAFETY_ASSESSMENT",
                   decision_granularity="SINGLE_NEXT_ACTION")
    candidate = competitor(
        "SEED-SAFETY", anchors=["SF-SHARED-1"], conditions=[("SF-ONLY-1", "PRESENT")],
        tokens=("COMMUNITY_SAFETY_MEASURE",), item_archetypes=("SAFETY_ASSESSMENT",),
        option_set_archetypes=("DISPOSITION_SET",), granularity="SINGLE_NEXT_ACTION",
    )
    bare = admit_pre_stem(candidate, key_context=context)
    assert "PRE_STEM_RESPONSE_CLASS_MISMATCH" in bare["refusals"]
    implied = admit_pre_stem(
        candidate, key_context=context,
        token_implications={"COMMUNITY_SAFETY_MEASURE": ["SECURES_IMMEDIATE_SAFETY"]},
    )
    assert implied["admitted"] is True


def test_an_implication_cannot_admit_a_token_outside_the_axis():
    context = dict(KEY_CONTEXT, option_set_archetype="DISPOSITION_SET",
                   demanded_response_class="SECURES_IMMEDIATE_SAFETY",
                   item_archetype="SAFETY_ASSESSMENT",
                   decision_granularity="SINGLE_NEXT_ACTION")
    candidate = competitor(
        "SEED-STRAY", anchors=["SF-SHARED-1"], conditions=[("SF-ONLY-1", "PRESENT")],
        tokens=("PLAUSIBLE_DIAGNOSTIC_ENTITY",), item_archetypes=("SAFETY_ASSESSMENT",),
        option_set_archetypes=("DISPOSITION_SET",), granularity="SINGLE_NEXT_ACTION",
    )
    verdict = admit_pre_stem(
        candidate, key_context=context,
        token_implications={"PLAUSIBLE_DIAGNOSTIC_ENTITY": ["SECURES_IMMEDIATE_SAFETY"]},
    )
    assert "PRE_STEM_RESPONSE_CLASS_MISMATCH" in verdict["refusals"]


# --------------------------------------------- author-declared context features


def test_declared_context_features_enter_the_blueprint_and_are_checked():
    matrix = build_contrast_matrix(contrast_set())
    blueprint = solve_stem_blueprint(
        matrix, vocabulary=VOCABULARY, context_features=["SF-KEY-C"]
    )
    required = {row["stem_feature_id"] for row in blueprint["required_features"]}
    assert "SF-KEY-C" in required
    assert blueprint["fail_closed_reason"] is None
    row = next(r for r in blueprint["required_features"] if r["stem_feature_id"] == "SF-KEY-C")
    assert row["roles"] == ["OPTIONAL_CONTEXT"]


def test_a_context_feature_that_would_complete_a_competitor_is_refused():
    matrix = build_contrast_matrix(contrast_set())
    blueprint = solve_stem_blueprint(
        matrix, vocabulary=VOCABULARY, context_features=["SF-ONLY-1"]
    )
    assert blueprint["fail_closed_reason"] == "FAIL_CLOSED_BLUEPRINT_UNSATISFIABLE"


def test_a_context_feature_outside_the_vocabulary_is_refused():
    matrix = build_contrast_matrix(contrast_set())
    with pytest.raises(ContrastFirstError, match="vocabulary"):
        solve_stem_blueprint(matrix, vocabulary=VOCABULARY, context_features=["SF-INVENTED"])


# ------------------------------- what counts as an explicit verbal denial


def test_a_competitor_defeated_by_a_positive_finding_is_not_defeated_by_a_denial():
    # The competitor needs the finding ABSENT and the stem states it PRESENT.
    # That is the strongest legitimate discriminator there is, and it must not be
    # counted as the verbal denial CO-3 exists to refuse.
    positive = contrast_set()
    positive["competitors"][0]["condition_predicates"] = [
        {"stem_feature_id": "SF-KEY-A", "required_polarity": "ABSENT"},
    ]
    blueprint = solve_stem_blueprint(
        build_contrast_matrix(positive), vocabulary=VOCABULARY
    )
    status = blueprint["competitor_status"]["SEED-ONE"]
    assert status["unsatisfied_conditions"] == ["SF-KEY-A"]
    assert status["defeated_by_explicit_denial"] is False
    verdict = evaluate_clinical_coherence(blueprint, vocabulary=VOCABULARY)
    assert "CO-3" not in verdict["violations"]


def test_a_competitor_defeated_only_by_a_stated_absence_is_flagged():
    denied = contrast_set()
    denied["key"]["correctness_conditions"] = [
        {"stem_feature_id": "SF-KEY-A", "required_polarity": "PRESENT"},
        {"stem_feature_id": "SF-ONLY-1", "required_polarity": "ABSENT"},
    ]
    blueprint = solve_stem_blueprint(
        build_contrast_matrix(denied), vocabulary=VOCABULARY
    )
    status = blueprint["competitor_status"]["SEED-ONE"]
    assert status["defeated_by_explicit_denial"] is True
    assert "CO-3" in evaluate_clinical_coherence(
        blueprint, vocabulary=VOCABULARY
    )["violations"]


def test_a_context_feature_may_be_declared_absent():
    matrix = build_contrast_matrix(contrast_set())
    blueprint = solve_stem_blueprint(
        matrix, vocabulary=VOCABULARY,
        context_features=[{"stem_feature_id": "SF-KEY-C", "polarity": "ABSENT"}],
    )
    row = next(r for r in blueprint["required_features"] if r["stem_feature_id"] == "SF-KEY-C")
    assert row["polarity"] == "ABSENT"
    assert blueprint["fail_closed_reason"] is None
