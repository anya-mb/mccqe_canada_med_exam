"""Tests for the clinical contrast relation model V2.

Written before the module. The four defects this layer exists to fix are each
represented here as a regression fixture built from the frozen failure pattern
that exposed it, so a change that reintroduces one of them fails a named test
rather than a summary statistic:

* ``UNKNOWN`` is not ``ABSENT``           -- G2-PHELO-01, G2-PSY-03
* competitors are compared with each other -- G2-MED-03, G2-SURG-01, G2-PED-01
* a background fact is not an anchor       -- G2-SURG-01, G2-SURG-02
* ``ANY_OF`` is OR                         -- G2-PED-02
"""

from __future__ import annotations

import pytest

from qbank.clinical_contrast_v2 import (
    ABSENT,
    AMBIGUOUS,
    CATEGORICALLY_EXCLUDED,
    COHERENCE_RULES_V2,
    INDETERMINATE,
    INSUFFICIENT_SUPPORT,
    LIVE_BUT_INFERIOR,
    NOT_APPLICABLE,
    NOT_SATISFIED,
    PRESENT,
    SATISFIED,
    SECOND_KEY,
    UNKNOWN,
    ClinicalContrastV2Error,
    build_feature_state_map,
    classify_competitor,
    contrast_role_for,
    discriminative_class,
    evaluate_contrast_set_coherence,
    evaluate_predicate,
    feature_assertion,
    resolve_state,
    validate_contrast_relation,
    validate_predicate,
)


def leaf(feature_id, state=PRESENT):
    return {"feature_id": feature_id, "required_state": state}


def state_map(**states):
    return build_feature_state_map(
        [feature_assertion(name.replace("_", "-"), value) for name, value in states.items()]
    )


# ------------------------------------------------------- feature state model


def test_a_feature_the_map_does_not_name_resolves_unknown_not_absent():
    resolved = resolve_state(state_map(FEVER=PRESENT), "COUGH")
    assert resolved["state"] == UNKNOWN
    assert resolved["explicitness"] == "NOT_STATED"


def test_explicit_absence_and_silence_are_different_objects():
    stated = state_map(FEVER=ABSENT)
    silent = state_map(COUGH=PRESENT)
    assert resolve_state(stated, "FEVER")["state"] == ABSENT
    assert resolve_state(silent, "FEVER")["state"] == UNKNOWN
    assert evaluate_predicate(leaf("FEVER", ABSENT), stated) == SATISFIED
    assert evaluate_predicate(leaf("FEVER", ABSENT), silent) == INDETERMINATE


def test_explicit_present_satisfies_a_present_requirement():
    assert evaluate_predicate(leaf("FEVER"), state_map(FEVER=PRESENT)) == SATISFIED
    assert evaluate_predicate(leaf("FEVER"), state_map(FEVER=ABSENT)) == NOT_SATISFIED


def test_not_applicable_cannot_be_present():
    assert evaluate_predicate(leaf("FEVER"), state_map(FEVER=NOT_APPLICABLE)) == NOT_SATISFIED
    assert evaluate_predicate(
        leaf("FEVER", ABSENT), state_map(FEVER=NOT_APPLICABLE)
    ) == SATISFIED


def test_a_contradiction_pair_derives_an_implied_absence():
    derived = build_feature_state_map(
        [feature_assertion("VIRAL-PRODROME", PRESENT)],
        contradiction_pairs=[("ABRUPT-ONSET", "VIRAL-PRODROME")],
    )
    implied = resolve_state(derived, "ABRUPT-ONSET")
    assert implied["state"] == ABSENT
    assert implied["explicitness"] == "IMPLIED"
    assert implied["implied_by"] == "VIRAL-PRODROME"


def test_an_unknown_state_may_not_be_declared_explicit():
    with pytest.raises(ClinicalContrastV2Error):
        feature_assertion("FEVER", UNKNOWN, explicitness="EXPLICIT")


def test_a_contradiction_pair_may_not_overwrite_a_stated_presence():
    with pytest.raises(ClinicalContrastV2Error):
        build_feature_state_map(
            [feature_assertion("A", PRESENT), feature_assertion("B", PRESENT)],
            contradiction_pairs=[("A", "B")],
        )


# ------------------------------------------------------------ predicate logic


def test_any_of_implements_or():
    predicate = {"operator": "ANY_OF", "conditions": [leaf("A"), leaf("B")]}
    assert evaluate_predicate(predicate, state_map(A=PRESENT, B=ABSENT)) == SATISFIED
    assert evaluate_predicate(predicate, state_map(A=ABSENT, B=PRESENT)) == SATISFIED
    assert evaluate_predicate(predicate, state_map(A=ABSENT, B=ABSENT)) == NOT_SATISFIED


def test_all_of_implements_and():
    predicate = {"operator": "ALL_OF", "conditions": [leaf("A"), leaf("B")]}
    assert evaluate_predicate(predicate, state_map(A=PRESENT, B=PRESENT)) == SATISFIED
    assert evaluate_predicate(predicate, state_map(A=PRESENT, B=ABSENT)) == NOT_SATISFIED


def test_the_ped_02_disjunction_is_not_scored_as_a_conjunction():
    """The frozen regression fixture for defect 4.

    ``CLM-R2-PED-VIRAL-INDICATION`` reads "infection control purposes, or high
    risk patients". Under V1 the two predicates were counted conjunctively and a
    competitor whose first disjunct the stem states was scored 1 of 2 and treated
    as defeated. It is a second key, and V2 must say so.
    """
    disjunction = {
        "operator": "ANY_OF",
        "conditions": [
            leaf("SF-P147-INFECTION-CONTROL-NEED"),
            leaf("SF-P147-HIGH-RISK-EARLY-COURSE"),
        ],
    }
    stem = build_feature_state_map([
        feature_assertion("SF-P147-VIRAL-PRODROME", PRESENT),
        feature_assertion("SF-P147-INFECTION-CONTROL-NEED", PRESENT),
    ])
    assert evaluate_predicate(disjunction, stem) == SATISFIED
    conjunction = {"operator": "ALL_OF", "conditions": disjunction["conditions"]}
    assert evaluate_predicate(conjunction, stem) == INDETERMINATE


def test_not_negates_and_leaves_indeterminate_alone():
    negation = {"operator": "NOT", "conditions": [leaf("A")]}
    assert evaluate_predicate(negation, state_map(A=PRESENT)) == NOT_SATISFIED
    assert evaluate_predicate(negation, state_map(A=ABSENT)) == SATISFIED
    assert evaluate_predicate(negation, state_map(B=PRESENT)) == INDETERMINATE


def test_nested_predicates_compose():
    predicate = {
        "operator": "ALL_OF",
        "conditions": [
            leaf("A"),
            {"operator": "ANY_OF", "conditions": [leaf("B"), leaf("C")]},
        ],
    }
    assert evaluate_predicate(predicate, state_map(A=PRESENT, C=PRESENT)) == SATISFIED
    assert evaluate_predicate(predicate, state_map(A=ABSENT, C=PRESENT)) == NOT_SATISFIED
    assert evaluate_predicate(
        predicate, state_map(A=PRESENT, B=ABSENT, C=ABSENT)
    ) == NOT_SATISFIED


def test_at_least_n():
    predicate = {
        "operator": "AT_LEAST_N", "n": 2,
        "conditions": [leaf("A"), leaf("B"), leaf("C")],
    }
    assert evaluate_predicate(predicate, state_map(A=PRESENT, B=PRESENT)) == SATISFIED
    assert evaluate_predicate(
        predicate, state_map(A=PRESENT, B=ABSENT, C=ABSENT)
    ) == NOT_SATISFIED
    assert evaluate_predicate(predicate, state_map(A=PRESENT, B=ABSENT)) == INDETERMINATE


def test_threshold_comparison():
    predicate = {
        "operator": "THRESHOLD", "feature_id": "SATURATION",
        "comparison": "lt", "value": 90,
    }
    measured = build_feature_state_map(
        [feature_assertion("SATURATION", PRESENT, value=87, units="percent")]
    )
    assert evaluate_predicate(predicate, measured) == SATISFIED
    higher = build_feature_state_map([feature_assertion("SATURATION", PRESENT, value=95)])
    assert evaluate_predicate(predicate, higher) == NOT_SATISFIED
    assert evaluate_predicate(predicate, state_map(SATURATION=PRESENT)) == INDETERMINATE
    assert evaluate_predicate(predicate, state_map(OTHER=PRESENT)) == INDETERMINATE


def test_unknown_propagates_to_indeterminate_through_nesting():
    predicate = {
        "operator": "ALL_OF",
        "conditions": [
            leaf("A"),
            {"operator": "ANY_OF", "conditions": [leaf("B"), leaf("C")]},
        ],
    }
    assert evaluate_predicate(predicate, state_map(A=PRESENT)) == INDETERMINATE


def test_an_empty_condition_list_fails_closed():
    with pytest.raises(ClinicalContrastV2Error):
        validate_predicate({"operator": "ALL_OF", "conditions": []})
    with pytest.raises(ClinicalContrastV2Error):
        evaluate_predicate({"operator": "ANY_OF", "conditions": []}, state_map())


def test_a_predicate_may_not_name_a_feature_outside_the_vocabulary():
    with pytest.raises(ClinicalContrastV2Error):
        validate_predicate(leaf("SF-INVENTED"), vocabulary={"SF-REAL": {}})


# ---------------------------------------------------------------- role model


def test_background_context_is_not_discriminating():
    assert discriminative_class("BACKGROUND_CONTEXT") == "NON_DISCRIMINATING"
    assert discriminative_class("RESOURCE_AVAILABILITY") == "NON_DISCRIMINATING"
    assert discriminative_class("KEY_DISCRIMINATOR") == "DISCRIMINATING"


def test_a_demographic_is_prior_only_and_an_availability_clause_is_not_an_anchor():
    """The frozen regression fixture for defect 3, from G2-SURG-01 and G2-SURG-02."""
    female = contrast_role_for("DEMOGRAPHIC", decision_domain="PATIENT_CLINICAL")
    imaging = contrast_role_for("SYSTEM_CONSTRAINT", decision_domain="PATIENT_CLINICAL")
    suspicion = contrast_role_for("CLINICAL_JUDGEMENT", decision_domain="PATIENT_CLINICAL")
    assert discriminative_class(female) == "PRIOR_ONLY"
    assert discriminative_class(imaging) == "NON_DISCRIMINATING"
    assert discriminative_class(suspicion) == "NON_DISCRIMINATING"


def test_strong_discriminator_typing_is_preserved():
    for clinical_role in ("EXAMINATION_FINDING", "INVESTIGATION_RESULT", "VITAL_SIGN"):
        role = contrast_role_for(clinical_role, decision_domain="PATIENT_CLINICAL")
        assert discriminative_class(role) == "PRESENTATION"


def test_a_programme_document_is_case_material_in_a_population_decision():
    """The same clinical_role types differently by decision domain.

    ``SF-PH07-LETTER-STATES-RELATIVE-BENEFIT-ONLY`` is the object of the decision
    in a programme item and would be furniture in a bedside one. Both accepted V1
    controls are population items anchored entirely on such features.
    """
    programme = contrast_role_for("PROGRAMME_DOCUMENT", decision_domain="POPULATION_PROGRAMME")
    bedside = contrast_role_for("PROGRAMME_DOCUMENT", decision_domain="PATIENT_CLINICAL")
    assert discriminative_class(programme) == "PRESENTATION"
    assert discriminative_class(bedside) == "NON_DISCRIMINATING"


def test_an_unknown_clinical_role_fails_closed():
    with pytest.raises(ClinicalContrastV2Error):
        contrast_role_for("INVENTED_ROLE", decision_domain="PATIENT_CLINICAL")


# ----------------------------------------------------------- relation object


def relation(**overrides):
    payload = {
        "learner_decision_id": "LD-X-01",
        "response_class": "PLAUSIBLE_DIAGNOSTIC_ENTITY",
        "decision_granularity": "SINGLE_DIAGNOSIS",
        "concept_a": {"concept_id": "C-KEY", "concept": "Key", "role_in_set": "KEY"},
        "concept_b": {
            "concept_id": "C-COMP", "concept": "Competitor",
            "role_in_set": "COMPETITOR", "seed_id": "SEED-X",
        },
        "shared_features": [
            {"feature_id": "SF-SHARED", "contrast_role": "SHARED_PRESENTATION_FEATURE"}
        ],
        "a_supporting_features": [
            {"feature_id": "SF-KEY", "contrast_role": "INVESTIGATION_FINDING"}
        ],
        "b_supporting_features": [
            {"feature_id": "SF-SHARED", "contrast_role": "SHARED_PRESENTATION_FEATURE"}
        ],
        "discriminators": [{
            "feature_id": "SF-KEY", "favours": "A", "required_state": PRESENT,
            "contrast_role": "KEY_DISCRIMINATOR", "salience": "SALIENT",
            "evidence_refs": ["CLM-X"],
        }],
        "correctness_conditions_a": leaf("SF-KEY"),
        "correctness_conditions_b": leaf("SF-COMP-ONLY"),
        "second_key_conditions": [],
        "categorical_exclusion_conditions": [],
        "nesting_relation": "NONE",
        "confusability": "HIGH",
        "mcc_relevance": "tested at the MCC level",
        "evidence_refs": ["CLM-X"],
        "verification_status": "EVIDENCE_VERIFIED",
    }
    payload.update(overrides)
    return payload


def test_a_discriminator_without_evidence_fails_closed():
    broken = relation(discriminators=[{
        "feature_id": "SF-KEY", "favours": "A", "required_state": PRESENT,
        "contrast_role": "KEY_DISCRIMINATOR", "salience": "SALIENT", "evidence_refs": [],
    }])
    with pytest.raises(ClinicalContrastV2Error):
        validate_contrast_relation(broken)


def test_a_feature_may_not_be_shared_and_discriminating_in_the_same_relation():
    broken = relation(discriminators=[{
        "feature_id": "SF-SHARED", "favours": "A", "required_state": PRESENT,
        "contrast_role": "KEY_DISCRIMINATOR", "salience": "SALIENT",
        "evidence_refs": ["CLM-X"],
    }])
    with pytest.raises(ClinicalContrastV2Error):
        validate_contrast_relation(broken)


def test_a_valid_relation_validates():
    validate_contrast_relation(relation())


# --------------------------------------------------------- competitor states


def competitor(**overrides):
    payload = {
        "member_id": "SEED-X",
        "supporting_features": [
            {"feature_id": "SF-SHARED", "contrast_role": "SHARED_PRESENTATION_FEATURE"}
        ],
        "correctness_conditions": leaf("SF-COMP-ONLY"),
        "categorical_exclusion_conditions": [],
    }
    payload.update(overrides)
    return payload


KEY_DISCRIMINATOR = {
    "feature_id": "SF-KEY", "favours": "A", "required_state": PRESENT,
    "contrast_role": "KEY_DISCRIMINATOR", "salience": "SALIENT", "evidence_refs": ["CLM-X"],
}


def test_a_competitor_defeated_by_a_stated_contrary_is_live_but_inferior():
    verdict = classify_competitor(
        competitor(),
        state_map(**{"SF_SHARED": PRESENT, "SF_COMP_ONLY": ABSENT}),
        discriminators=[KEY_DISCRIMINATOR],
    )
    assert verdict["state"] == LIVE_BUT_INFERIOR
    assert verdict["defeated_by"] == ["SF-COMP-ONLY"]


def test_a_competitor_whose_condition_the_stem_satisfies_is_a_second_key():
    verdict = classify_competitor(
        competitor(),
        state_map(**{"SF_SHARED": PRESENT, "SF_COMP_ONLY": PRESENT}),
        discriminators=[KEY_DISCRIMINATOR],
    )
    assert verdict["state"] == SECOND_KEY


def test_silence_alone_never_defeats_a_competitor():
    """The frozen regression fixture for defect 1, from G2-PHELO-01 and G2-PSY-03.

    Under V1 an unassigned feature counted as unsatisfied, so ``no_second_key``
    passed over competitors the stem never addressed. Under V2 the competitor is
    ``AMBIGUOUS`` and the item fails closed.
    """
    verdict = classify_competitor(
        competitor(),
        state_map(**{"SF_SHARED": PRESENT}),
        discriminators=[],
    )
    assert verdict["state"] == AMBIGUOUS
    assert verdict["correctness"] == INDETERMINATE
    assert verdict["unresolved_features"] == ["SF-COMP-ONLY"]


def test_an_indeterminate_competitor_with_a_satisfied_key_discriminator_is_inferior():
    verdict = classify_competitor(
        competitor(),
        state_map(**{"SF_SHARED": PRESENT, "SF_KEY": PRESENT}),
        discriminators=[KEY_DISCRIMINATOR],
    )
    assert verdict["state"] == LIVE_BUT_INFERIOR
    assert verdict["decided_by_discriminators"] == ["SF-KEY"]


def test_an_unsatisfied_key_discriminator_does_not_rescue_an_indeterminate_competitor():
    verdict = classify_competitor(
        competitor(),
        state_map(**{"SF_SHARED": PRESENT, "SF_KEY": ABSENT}),
        discriminators=[KEY_DISCRIMINATOR],
    )
    assert verdict["state"] == AMBIGUOUS


def test_a_competitor_with_no_presentation_anchor_present_has_insufficient_support():
    """The frozen regression fixture for defect 3, from G2-SURG-02.

    ``SF-GS76-IMAGING-AVAILABLE-NOW`` is a system-constraint fact that the frozen
    anchor layer counted as a plausibility anchor and a human reviewer did not.
    """
    verdict = classify_competitor(
        competitor(supporting_features=[
            {"feature_id": "SF-AVAILABLE", "contrast_role": "RESOURCE_AVAILABILITY"},
            {"feature_id": "SF-DEMOGRAPHIC", "contrast_role": "PRIOR_PROBABILITY_FEATURE"},
        ]),
        state_map(**{"SF_AVAILABLE": PRESENT, "SF_DEMOGRAPHIC": PRESENT}),
        discriminators=[KEY_DISCRIMINATOR],
    )
    assert verdict["state"] == INSUFFICIENT_SUPPORT
    assert verdict["anchors_present"] == ["SF-AVAILABLE", "SF-DEMOGRAPHIC"]
    assert verdict["presentation_anchors_present"] == []


def test_categorical_exclusion_requires_explicit_evidence_and_never_silence():
    exclusion = {
        "predicate": leaf("SF-CONTRAINDICATED"),
        "basis": "EXPLICIT_CONTRAINDICATION",
        "evidence_refs": ["CLM-X"],
    }
    stated = classify_competitor(
        competitor(categorical_exclusion_conditions=[exclusion]),
        state_map(**{"SF_SHARED": PRESENT, "SF_CONTRAINDICATED": PRESENT}),
        discriminators=[KEY_DISCRIMINATOR],
    )
    assert stated["state"] == CATEGORICALLY_EXCLUDED
    silent = classify_competitor(
        competitor(categorical_exclusion_conditions=[exclusion]),
        state_map(**{"SF_SHARED": PRESENT, "SF_COMP_ONLY": ABSENT}),
        discriminators=[KEY_DISCRIMINATOR],
    )
    assert silent["state"] == LIVE_BUT_INFERIOR


def test_an_exclusion_without_evidence_fails_closed():
    with pytest.raises(ClinicalContrastV2Error):
        classify_competitor(
            competitor(categorical_exclusion_conditions=[
                {"predicate": leaf("SF-X"), "basis": "EXPLICIT_CONTRAINDICATION",
                 "evidence_refs": []}
            ]),
            state_map(**{"SF_SHARED": PRESENT}),
            discriminators=[],
        )


# ------------------------------------------------------ contrast-set coherence


def member(member_id, role_in_set, **overrides):
    payload = {
        "member_id": member_id,
        "role_in_set": role_in_set,
        "concept_id": f"C-{member_id}",
        "concept": member_id.title(),
        "concept_category": "GENERIC",
        "response_class_tokens": ["DIAGNOSTIC"],
        "decision_granularity": "SINGLE_DIAGNOSIS",
        "supporting_features": [
            {"feature_id": f"SF-{member_id}", "contrast_role": "POSITIVE_SUPPORT"}
        ],
        "correctness_conditions": leaf(f"SF-{member_id}-COND"),
        "categorical_exclusion_conditions": [],
        "evidence_refs": ["CLM-X"],
    }
    payload.update(overrides)
    return payload


def contrast_set(members, relations=(), **overrides):
    payload = {
        "opportunity_label": "TEST-01",
        "learner_decision_id": "LD-X-01",
        "demanded_response_class": "DIAGNOSTIC",
        "decision_granularity": "SINGLE_DIAGNOSIS",
        "difficulty_intent": "MEDIUM",
        "decision_domain": "PATIENT_CLINICAL",
        "anchor_study_unit_id": "SU-X-01",
        "members": members,
        "relations": list(relations),
    }
    payload.update(overrides)
    return payload


def healthy_set(**overrides):
    members = overrides.pop("members", None) or [
        member("key", "KEY"),
        member("alpha", "COMPETITOR"),
        member("beta", "COMPETITOR"),
        member("gamma", "COMPETITOR"),
    ]
    return contrast_set(members, **overrides)


def test_a_healthy_set_is_coherent():
    report = evaluate_contrast_set_coherence(healthy_set())
    assert report["coherent"], report["violations"]
    assert report["rules_applied"] == list(COHERENCE_RULES_V2)
    assert report["pairs_evaluated"] == 6


def test_every_pair_is_evaluated_including_competitor_against_competitor():
    report = evaluate_contrast_set_coherence(healthy_set())
    pairs = {tuple(sorted(row["pair"])) for row in report["pairwise"]}
    assert ("alpha", "beta") in pairs
    assert ("beta", "gamma") in pairs
    assert ("alpha", "key") in pairs


def test_a_nested_competitor_is_refused():
    """G2-SURG-01: tubo-ovarian abscess is a complication of pelvic inflammatory disease."""
    report = evaluate_contrast_set_coherence(healthy_set(relations=[{
        "concept_a": {"member_id": "alpha"}, "concept_b": {"member_id": "beta"},
        "nesting_relation": "COMPLICATION_OF",
        "evidence_refs": ["CLM-X"],
    }]))
    assert "CS2-1" in report["violations"]


def test_two_competitors_defeated_by_the_same_proposition_are_redundant():
    """G2-MED-03: furosemide and nitroglycerin die on one preload proposition."""
    report = evaluate_contrast_set_coherence(contrast_set([
        member("key", "KEY", correctness_conditions=leaf("SF-PRELOAD")),
        member("alpha", "COMPETITOR", correctness_conditions=leaf("SF-PRELOAD", ABSENT)),
        member("beta", "COMPETITOR", correctness_conditions=leaf("SF-PRELOAD", ABSENT)),
        member("gamma", "COMPETITOR"),
    ]))
    assert "CS2-2" in report["violations"]
    assert "CS2-8" in report["violations"]


def test_a_response_class_mismatch_is_refused():
    report = evaluate_contrast_set_coherence(healthy_set(members=[
        member("key", "KEY"),
        member("alpha", "COMPETITOR"),
        member("beta", "COMPETITOR"),
        member("gamma", "COMPETITOR", response_class_tokens=["THERAPEUTIC"]),
    ]))
    assert "CS2-3" in report["violations"]


def test_a_granularity_mismatch_is_refused():
    report = evaluate_contrast_set_coherence(healthy_set(members=[
        member("key", "KEY"),
        member("alpha", "COMPETITOR"),
        member("beta", "COMPETITOR"),
        member("gamma", "COMPETITOR", decision_granularity="DIAGNOSTIC_CATEGORY"),
    ]))
    assert "CS2-4" in report["violations"]


def test_a_lone_key_category_is_refused():
    report = evaluate_contrast_set_coherence(healthy_set(members=[
        member("key", "KEY", concept_category="NON_GYNAECOLOGIC"),
        member("alpha", "COMPETITOR", concept_category="GYNAECOLOGIC"),
        member("beta", "COMPETITOR", concept_category="GYNAECOLOGIC"),
        member("gamma", "COMPETITOR", concept_category="GYNAECOLOGIC"),
    ]))
    assert "CS2-5" in report["violations"]


def test_a_competitor_whose_only_anchor_is_its_own_condition_is_refused():
    """G2-PED-01: the only available anchor is also a correctness condition."""
    report = evaluate_contrast_set_coherence(healthy_set(members=[
        member("key", "KEY"),
        member("alpha", "COMPETITOR",
               supporting_features=[
                   {"feature_id": "SF-ONLY", "contrast_role": "POSITIVE_SUPPORT"}
               ],
               correctness_conditions=leaf("SF-ONLY")),
        member("beta", "COMPETITOR"),
        member("gamma", "COMPETITOR"),
    ]))
    assert "CS2-6" in report["violations"]


def test_a_set_anchored_only_on_background_facts_is_refused():
    """G2-SURG-02: every competitor lives on 'imaging is available now'."""
    background = [{"feature_id": "SF-AVAILABLE", "contrast_role": "RESOURCE_AVAILABILITY"}]
    report = evaluate_contrast_set_coherence(healthy_set(members=[
        member("key", "KEY"),
        member("alpha", "COMPETITOR", supporting_features=background),
        member("beta", "COMPETITOR", supporting_features=background),
        member("gamma", "COMPETITOR", supporting_features=background),
    ]))
    assert "CS2-7" in report["violations"]


def test_a_key_with_no_observable_correctness_condition_is_refused():
    """G2-SURG-02: both key conditions are meta-assertions, not findings."""
    report = evaluate_contrast_set_coherence(healthy_set(
        members=[
            member("key", "KEY", correctness_conditions={
                "operator": "ALL_OF",
                "conditions": [leaf("SF-SUSPICION"), leaf("SF-AVAILABLE")],
            }),
            member("alpha", "COMPETITOR"),
            member("beta", "COMPETITOR"),
            member("gamma", "COMPETITOR"),
        ],
        feature_roles={
            "SF-SUSPICION": "BACKGROUND_CONTEXT",
            "SF-AVAILABLE": "RESOURCE_AVAILABILITY",
        },
    ))
    assert "CS2-9" in report["violations"]


def test_the_realized_state_map_is_used_for_anchor_degeneracy_when_supplied():
    """G2-SURG-01 post-stem: only the demographic anchor was actually stated."""
    report = evaluate_contrast_set_coherence(
        healthy_set(members=[
            member("key", "KEY"),
            member("alpha", "COMPETITOR", supporting_features=[
                {"feature_id": "SF-EXAM", "contrast_role": "POSITIVE_SUPPORT"},
                {"feature_id": "SF-FEMALE", "contrast_role": "PRIOR_PROBABILITY_FEATURE"},
            ]),
            member("beta", "COMPETITOR", supporting_features=[
                {"feature_id": "SF-EXAM", "contrast_role": "POSITIVE_SUPPORT"},
                {"feature_id": "SF-FEMALE", "contrast_role": "PRIOR_PROBABILITY_FEATURE"},
            ]),
            member("gamma", "COMPETITOR", supporting_features=[
                {"feature_id": "SF-MASS", "contrast_role": "INVESTIGATION_FINDING"},
                {"feature_id": "SF-FEMALE", "contrast_role": "PRIOR_PROBABILITY_FEATURE"},
            ]),
        ]),
        state_map=state_map(**{"SF_FEMALE": PRESENT}),
    )
    assert "CS2-7" in report["violations"]


def test_set_coherence_is_stem_independent_when_no_state_map_is_supplied():
    report = evaluate_contrast_set_coherence(healthy_set())
    assert report["state_map_supplied"] is False
    assert report["coherent"]


def test_a_set_below_the_minimum_fails_closed():
    with pytest.raises(ClinicalContrastV2Error):
        evaluate_contrast_set_coherence(contrast_set([
            member("key", "KEY"), member("alpha", "COMPETITOR"),
        ]))


def test_a_set_needs_exactly_one_key():
    with pytest.raises(ClinicalContrastV2Error):
        evaluate_contrast_set_coherence(contrast_set([
            member("key", "KEY"), member("other", "KEY"),
            member("alpha", "COMPETITOR"), member("beta", "COMPETITOR"),
        ]))
