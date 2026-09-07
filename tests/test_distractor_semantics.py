"""Tests for the two distractor semantic classes V2 recognises.

Written before the module change, from the patterns the cross-discipline medium
pilot actually diagnosed rather than from invented shapes.

The pilot's largest architectural defect was that V2 could carry only one kind of
competitor: one with a state of the world in which it becomes the best answer.
Eight frozen seeds across three opportunities are options whose own reviewed prose
records no such state, and the frozen model could not represent them at all --
`validate_predicate` refuses an empty branch, so an empty correctness tree is not
a tree.

The second class added here is not a relaxation. A never-best competitor is
admitted only against a stricter contract than a counterfactual-correct one, and
each limb of that contract has a test whose fixture is a real diagnosed candidate:

* ``SEED-OB-T03-MASSAGE``    -- plausible, harmful, evidence-cited both ways
* ``SEED-OB-T03-SHIELD``     -- plausible on a different anchor
* ``SEED-PED-T03-HYPERTONIC`` -- no plausibility anchor at all, so refused
* ``SEED-OB-T02-CRP``        -- another clinical question, so refused
"""

from __future__ import annotations

import pytest

from qbank.clinical_contrast_v2 import (
    ABSENT,
    AMBIGUOUS,
    CATEGORICALLY_EXCLUDED,
    COUNTERFACTUAL_CORRECT,
    INSUFFICIENT_SUPPORT,
    LIVE_BUT_INFERIOR,
    NOT_SATISFIED,
    PLAUSIBLE_BUT_NEVER_BEST,
    PRESENT,
    SECOND_KEY,
    ClinicalContrastV2Error,
    build_feature_state_map,
    can_be_live_without_being_correct,
    classify_competitor,
    distractor_semantics,
    evaluate_contrast_set_coherence,
    feature_assertion,
    never_best_limbs,
    validate_never_best_contract,
)


def state_map(**states):
    return build_feature_state_map(
        [feature_assertion(name.replace("_", "-"), value) for name, value in states.items()]
    )


def contract(**overrides):
    """The frozen SEED-OB-T03-MASSAGE contract, read from the curated seed pack."""
    payload = {
        "positive_plausibility": {
            "feature_ids": ["SF-OB54-UNILATERAL-SEGMENTAL-ERYTHEMA"],
            "evidence_refs": ["CLM-R2-OB-LYMPHATIC"],
            "reason": (
                "A manual technique is genuinely part of recommended care, so the "
                "category is right and only the depth of pressure is wrong."
            ),
        },
        "inferiority": {
            "basis": "EVIDENCE_STATES_HARM",
            "evidence_refs": ["CLM-R2-OB-DEEP-MASSAGE"],
            "reason": (
                "Deep massage of an inflamed breast may propagate phlegmon; only light "
                "sweeping approximating lymphatic drainage is recommended."
            ),
        },
        "learner_error_mode": (
            "A candidate who does not distinguish lymphatic drainage from deep tissue "
            "massage."
        ),
    }
    for key, value in overrides.items():
        if value is None:
            payload.pop(key, None)
        else:
            payload[key] = value
    return payload


def never_best_member(**overrides):
    member = {
        "member_id": "SEED-OB-T03-MASSAGE",
        "role_in_set": "COMPETITOR",
        "concept_category": "FEEDING_OR_BREAST_CARE_INSTRUCTION",
        "response_class_tokens": ["PATIENT_INSTRUCTION"],
        "decision_granularity": "SINGLE_NEXT_ACTION",
        "distractor_semantics": PLAUSIBLE_BUT_NEVER_BEST,
        "never_best_contract": contract(),
        "supporting_features": [
            {
                "feature_id": "SF-OB54-UNILATERAL-SEGMENTAL-ERYTHEMA",
                "contrast_role": "POSITIVE_SUPPORT",
            }
        ],
        "categorical_exclusion_conditions": [],
    }
    member.update(overrides)
    return member


def counterfactual_member(**overrides):
    member = {
        "member_id": "SEED-OB-T03-DISCARD",
        "role_in_set": "COMPETITOR",
        "concept_category": "MILK_WITHHELD_FROM_INFANT",
        "response_class_tokens": ["PATIENT_INSTRUCTION"],
        "decision_granularity": "SINGLE_NEXT_ACTION",
        "supporting_features": [
            {
                "feature_id": "SF-OB54-UNILATERAL-SEGMENTAL-ERYTHEMA",
                "contrast_role": "POSITIVE_SUPPORT",
            }
        ],
        "correctness_conditions": {
            "operator": "ALL_OF",
            "conditions": [
                {
                    "feature_id": "SF-OB54-INFANT-FEEDING-CONTRAINDICATION",
                    "required_state": PRESENT,
                }
            ],
        },
        "categorical_exclusion_conditions": [],
    }
    member.update(overrides)
    return member


# ------------------------------------------- the class that already existed


def test_a_competitor_without_declared_semantics_is_still_counterfactual_correct():
    verdict = classify_competitor(
        counterfactual_member(),
        state_map(**{"SF-OB54-UNILATERAL-SEGMENTAL-ERYTHEMA": PRESENT,
                     "SF-OB54-INFANT-FEEDING-CONTRAINDICATION": ABSENT}),
    )
    assert distractor_semantics(counterfactual_member()) == COUNTERFACTUAL_CORRECT
    assert "distractor_semantics" not in verdict
    assert verdict["state"] == LIVE_BUT_INFERIOR
    assert verdict["correctness"] == NOT_SATISFIED


def test_counterfactual_correct_still_becomes_a_second_key_when_the_stem_makes_it_right():
    verdict = classify_competitor(
        counterfactual_member(),
        state_map(**{"SF-OB54-INFANT-FEEDING-CONTRAINDICATION": PRESENT}),
    )
    assert verdict["state"] == SECOND_KEY


def test_counterfactual_correct_is_still_ambiguous_when_nothing_settles_it():
    verdict = classify_competitor(
        counterfactual_member(),
        state_map(**{"SF-OB54-UNILATERAL-SEGMENTAL-ERYTHEMA": PRESENT,
                     "SF-OB54-SYSTEMIC-ILLNESS": PRESENT}),
    )
    assert verdict["state"] == AMBIGUOUS


# ------------------------------------------------------ the class being added


def test_a_never_best_competitor_with_a_stated_anchor_is_live_but_inferior():
    verdict = classify_competitor(
        never_best_member(),
        state_map(**{"SF-OB54-UNILATERAL-SEGMENTAL-ERYTHEMA": PRESENT}),
    )
    assert verdict["distractor_semantics"] == PLAUSIBLE_BUT_NEVER_BEST
    assert verdict["state"] == LIVE_BUT_INFERIOR
    assert verdict["correctness"] == NOT_SATISFIED
    assert verdict["second_key_risk"] is False


def test_a_never_best_competitor_is_never_a_second_key_whatever_the_stem_states():
    # Every feature the study unit can state, all PRESENT at once. A
    # counterfactual-correct competitor would be a second key here; this one
    # cannot be, because it carries no state of the world in which it is right.
    everything = state_map(**{
        "SF-OB54-UNILATERAL-SEGMENTAL-ERYTHEMA": PRESENT,
        "SF-OB54-INFANT-FEEDING-CONTRAINDICATION": PRESENT,
        "SF-OB54-SYSTEMIC-ILLNESS": PRESENT,
        "SF-OB54-HYPERLACTATION": PRESENT,
    })
    verdict = classify_competitor(never_best_member(), everything)
    assert verdict["state"] == LIVE_BUT_INFERIOR
    assert verdict["correctness"] == NOT_SATISFIED


def test_a_never_best_competitor_the_stem_does_not_anchor_is_insufficient_support():
    verdict = classify_competitor(
        never_best_member(), state_map(**{"SF-OB54-SYSTEMIC-ILLNESS": PRESENT})
    )
    assert verdict["state"] == INSUFFICIENT_SUPPORT


def test_a_never_best_competitor_is_still_categorically_excludable():
    member = never_best_member(categorical_exclusion_conditions=[{
        "basis": "MUTUALLY_EXCLUSIVE_CLINICAL_STATE",
        "evidence_refs": ["CLM-R2-OB-CONTINUE-FEEDING"],
        "predicate": {"feature_id": "SF-OB54-NOT-LACTATING", "required_state": PRESENT},
    }])
    verdict = classify_competitor(
        member,
        state_map(**{"SF-OB54-UNILATERAL-SEGMENTAL-ERYTHEMA": PRESENT,
                     "SF-OB54-NOT-LACTATING": PRESENT}),
    )
    assert verdict["state"] == CATEGORICALLY_EXCLUDED


# ----------------------------------------- the contract, limb by named limb


def test_a_never_best_competitor_may_not_also_carry_a_correctness_tree():
    member = never_best_member(
        correctness_conditions={
            "operator": "ALL_OF",
            "conditions": [{"feature_id": "SF-OB54-HYPERLACTATION",
                            "required_state": PRESENT}],
        }
    )
    with pytest.raises(ClinicalContrastV2Error, match="correctness"):
        classify_competitor(member, state_map())


def test_positive_plausibility_support_is_required():
    member = never_best_member(never_best_contract=contract(positive_plausibility=None))
    with pytest.raises(ClinicalContrastV2Error, match="positive plausibility"):
        validate_never_best_contract(member)


def test_positive_plausibility_support_must_cite_evidence():
    member = never_best_member(never_best_contract=contract(positive_plausibility={
        "feature_ids": ["SF-OB54-UNILATERAL-SEGMENTAL-ERYTHEMA"],
        "evidence_refs": [],
        "reason": "it looks reasonable",
    }))
    with pytest.raises(ClinicalContrastV2Error, match="evidence"):
        validate_never_best_contract(member)


def test_positive_plausibility_must_name_a_feature_the_member_actually_carries():
    member = never_best_member(never_best_contract=contract(positive_plausibility={
        "feature_ids": ["SF-OB54-HYPERLACTATION"],
        "evidence_refs": ["CLM-R2-OB-LYMPHATIC"],
        "reason": "an anchor the member does not have",
    }))
    with pytest.raises(ClinicalContrastV2Error, match="supporting feature"):
        validate_never_best_contract(member)


def test_an_explicit_inferiority_reason_is_required():
    member = never_best_member(never_best_contract=contract(inferiority=None))
    with pytest.raises(ClinicalContrastV2Error, match="inferior"):
        validate_never_best_contract(member)


def test_the_inferiority_reason_must_cite_evidence():
    member = never_best_member(never_best_contract=contract(inferiority={
        "basis": "EVIDENCE_STATES_HARM",
        "evidence_refs": [],
        "reason": "everyone knows this",
    }))
    with pytest.raises(ClinicalContrastV2Error, match="evidence"):
        validate_never_best_contract(member)


def test_silence_cannot_supply_the_inferiority_reason():
    # The whole silence-as-absence defect, arriving from the distractor side.
    # There is no basis in the closed set that means "the stem does not say so",
    # so the shape cannot be encoded at all.
    member = never_best_member(never_best_contract=contract(inferiority={
        "basis": "THE_STEM_DOES_NOT_STATE_ITS_PRECONDITION",
        "evidence_refs": ["CLM-R2-OB-DEEP-MASSAGE"],
        "reason": "the stem is silent on the indication",
    }))
    with pytest.raises(ClinicalContrastV2Error, match="basis"):
        validate_never_best_contract(member)


def test_a_common_clinical_error_mode_is_required():
    member = never_best_member(never_best_contract=contract(learner_error_mode=""))
    with pytest.raises(ClinicalContrastV2Error, match="error"):
        validate_never_best_contract(member)


# ------------------------------------------- what the class must still refuse


def test_a_dead_distractor_with_no_plausibility_anchor_is_refused():
    # SEED-PED-T03-HYPERTONIC, exactly as the frozen layer records it: plausible
    # in prose, and carrying no anchor the study unit's vocabulary can state.
    member = never_best_member(
        member_id="SEED-PED-T03-HYPERTONIC",
        supporting_features=[],
        never_best_contract=contract(positive_plausibility={
            "feature_ids": [],
            "evidence_refs": ["CLM-R4-PED-HYPERTONIC"],
            "reason": "a nebulized supportive measure in the same illness",
        }),
    )
    with pytest.raises(ClinicalContrastV2Error, match="positive plausibility"):
        validate_never_best_contract(member)


def test_a_wrong_decision_class_candidate_is_refused_by_the_set_contract():
    # SEED-OB-T02-CRP: its frozen response class is BIOCHEMICAL, and the set
    # demands DIAGNOSTIC_ADVANCEMENT. Being never best does not exempt it.
    limbs = never_best_limbs(
        never_best_member(
            member_id="SEED-OB-T02-CRP",
            response_class_tokens=["BIOCHEMICAL"],
        ),
        demanded_response_class="DIAGNOSTIC_ADVANCEMENT",
        decision_granularity="SINGLE_NEXT_ACTION",
        state_map=state_map(**{"SF-OB54-UNILATERAL-SEGMENTAL-ERYTHEMA": PRESENT}),
    )
    assert limbs["SAME_DECISION_CLASS"] == "FAIL"
    assert limbs["admissible"] is False


def test_a_granularity_mismatch_is_refused():
    limbs = never_best_limbs(
        never_best_member(decision_granularity="COMPLETE_MANAGEMENT_STRATEGY"),
        demanded_response_class="PATIENT_INSTRUCTION",
        decision_granularity="SINGLE_NEXT_ACTION",
        state_map=state_map(**{"SF-OB54-UNILATERAL-SEGMENTAL-ERYTHEMA": PRESENT}),
    )
    assert limbs["NO_GRANULARITY_MISMATCH"] == "FAIL"
    assert limbs["admissible"] is False


def test_all_seven_limbs_pass_for_the_diagnosed_frozen_candidate():
    limbs = never_best_limbs(
        never_best_member(),
        demanded_response_class="PATIENT_INSTRUCTION",
        decision_granularity="SINGLE_NEXT_ACTION",
        state_map=state_map(**{"SF-OB54-UNILATERAL-SEGMENTAL-ERYTHEMA": PRESENT}),
    )
    assert limbs["admissible"] is True
    assert set(limbs) == {
        "POSITIVE_PLAUSIBILITY_SUPPORT",
        "EXPLICIT_INFERIORITY_REASON",
        "COMMON_CLINICAL_CONFUSION_OR_ERROR",
        "SAME_DECISION_CLASS",
        "NO_SECOND_KEY",
        "NO_CATEGORY_MISMATCH",
        "NO_GRANULARITY_MISMATCH",
        "admissible",
    }
    assert all(
        value == "PASS" for key, value in limbs.items() if key != "admissible"
    )


# ------------------------------------------------- interaction with coherence


def test_cs2_6_does_not_fire_on_a_never_best_competitor():
    # CS2-6 refuses a competitor whose every anchor completes its own correctness
    # signature. A competitor with no correctness signature cannot have that
    # defect, and the rule must not fire vacuously.
    assert can_be_live_without_being_correct(
        never_best_member(), ["SF-OB54-UNILATERAL-SEGMENTAL-ERYTHEMA"]
    ) is True


def test_a_mixed_set_is_evaluated_by_the_unchanged_coherence_contract():
    contrast_set = {
        "opportunity_label": "G2-OBGYN-03",
        "decision_domain": "PATIENT_CLINICAL",
        "demanded_response_class": "PATIENT_INSTRUCTION",
        "decision_granularity": "SINGLE_NEXT_ACTION",
        "difficulty_intent": "HARD",
        "feature_roles": {
            "SF-OB54-UNILATERAL-SEGMENTAL-ERYTHEMA": "POSITIVE_SUPPORT",
            "SF-OB54-HYPERLACTATION": "POSITIVE_SUPPORT",
            "SF-OB54-NEEDLE-LIKE-BURNING-PAIN-BLEBS": "POSITIVE_SUPPORT",
            "SF-OB54-SYSTEMIC-ILLNESS": "POSITIVE_SUPPORT",
        },
        "relations": [],
        "members": [
            {
                "member_id": "KEY",
                "role_in_set": "KEY",
                "concept_category": "CONTINUED_PHYSIOLOGICAL_MILK_REMOVAL",
                "response_class_tokens": ["PATIENT_INSTRUCTION"],
                "decision_granularity": "SINGLE_NEXT_ACTION",
                "supporting_features": [],
                "correctness_conditions": {
                    "operator": "ALL_OF",
                    "conditions": [
                        {"feature_id": "SF-OB54-UNILATERAL-SEGMENTAL-ERYTHEMA",
                         "required_state": PRESENT},
                        {"feature_id": "SF-OB54-SYSTEMIC-ILLNESS",
                         "required_state": PRESENT},
                    ],
                },
                "categorical_exclusion_conditions": [],
            },
            counterfactual_member(),
            never_best_member(),
            never_best_member(
                member_id="SEED-OB-T03-SHIELD",
                concept_category="FEEDING_OR_BREAST_CARE_INSTRUCTION_LATCH",
                supporting_features=[{
                    "feature_id": "SF-OB54-NEEDLE-LIKE-BURNING-PAIN-BLEBS",
                    "contrast_role": "POSITIVE_SUPPORT",
                }],
                never_best_contract=contract(
                    positive_plausibility={
                        "feature_ids": ["SF-OB54-NEEDLE-LIKE-BURNING-PAIN-BLEBS"],
                        "evidence_refs": ["CLM-R4-OB-NIPPLE-SHIELD"],
                        "reason": (
                            "A nipple shield is a standard tool offered for painful "
                            "feeding, and pain with latch is part of this presentation."
                        ),
                    },
                    inferiority={
                        "basis": "EVIDENCE_STATES_NO_BENEFIT",
                        "evidence_refs": ["CLM-R4-OB-NIPPLE-SHIELD"],
                        "reason": (
                            "Neither safety nor effectiveness has been demonstrated and "
                            "shields result in inadequate milk extraction."
                        ),
                    },
                    learner_error_mode="A candidate who treats the pain rather than the "
                                       "physiology.",
                ),
            ),
        ],
    }
    result = evaluate_contrast_set_coherence(contrast_set)
    # No rule fires vacuously on the members that carry no correctness tree.
    assert "CS2-6" not in result["violations"]
    assert "CS2-8" not in result["violations"]
    assert result["usable_anchors_per_competitor"]["SEED-OB-T03-MASSAGE"] == [
        "SF-OB54-UNILATERAL-SEGMENTAL-ERYTHEMA"
    ]


# --------------------------------------------------- the accepted controls hold


def test_the_frozen_accepted_controls_are_untouched_by_the_new_class():
    """Nothing historical declares the new semantics, so nothing historical moves.

    This is the invariant that makes the extension safe to add rather than a
    change of model: absence of ``distractor_semantics`` means exactly what it
    meant before, and the default is asserted here rather than assumed.
    """
    member = counterfactual_member()
    assert "distractor_semantics" not in member
    verdict = classify_competitor(
        member,
        state_map(**{"SF-OB54-UNILATERAL-SEGMENTAL-ERYTHEMA": PRESENT,
                     "SF-OB54-INFANT-FEEDING-CONTRAINDICATION": ABSENT}),
    )
    assert distractor_semantics(member) == COUNTERFACTUAL_CORRECT
    # And the verdict carries no new key at all, so every frozen replay
    # serializes byte for byte as it did before the second class existed.
    assert "distractor_semantics" not in verdict
    assert "never_best_inferiority" not in verdict
    assert verdict["admissible_as_distractor"] is True
