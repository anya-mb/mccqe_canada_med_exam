import pytest

from qbank.option_set_admissibility import (
    OptionSetAdmissibilityError,
    adjudicate_option_set_admissibility,
    expand_response_tokens,
    find_realization_parity_defects,
    normalize_option_text,
    validate_role_blind_label_pool,
)


DIAGNOSIS_CONTRACT = {
    "option_set_archetype": "DIAGNOSIS_SET",
    "response_class_axis": "cardinal_syndrome_capability",
    "token_implications": {},
    "nominal_parity_axes": ["organ_system"],
}

MANAGEMENT_CONTRACT = {
    "option_set_archetype": "MANAGEMENT_STRATEGY_SET",
    "response_class_axis": "management_capability",
    "token_implications": {
        "PERCUTANEOUS_SOURCE_CONTROL": ["PROVIDES_SOURCE_CONTROL"],
        "DELAYED_OPERATIVE_SOURCE_CONTROL": ["PROVIDES_SOURCE_CONTROL"],
        "IMMEDIATE_OPERATIVE_SOURCE_CONTROL": ["PROVIDES_SOURCE_CONTROL"],
    },
    "nominal_parity_axes": ["organ_system"],
}


def pool(entries):
    return validate_role_blind_label_pool({"labels": entries})


def label(text, tokens, nominal=None, signature=None):
    entry = {
        "option_text": text,
        "response_class_tokens": tokens,
        "nominal_axis_values": nominal or {},
    }
    if signature:
        entry["action_signature"] = signature
    return entry


def options(texts, key_index):
    return [
        {"text": text, "role": "KEY" if index == key_index else "DISTRACTOR"}
        for index, text in enumerate(texts)
    ]


def test_role_blind_pool_refuses_any_field_that_reveals_the_key():
    for field in ("role", "is_key", "item_id", "option_letter"):
        entry = label("Alpha entity", ["LOCALIZED_INFLAMMATION"])
        entry[field] = "anything"
        with pytest.raises(OptionSetAdmissibilityError, match="role-blind"):
            validate_role_blind_label_pool({"labels": [entry]})


def test_identical_option_text_may_not_carry_divergent_labels():
    entries = [
        label("Alpha entity", ["LOCALIZED_INFLAMMATION"]),
        label("alpha  entity", ["SYSTEMIC_INFLAMMATORY_ILLNESS"]),
    ]
    with pytest.raises(OptionSetAdmissibilityError, match="divergent labels"):
        validate_role_blind_label_pool({"labels": entries})


def test_normalization_is_the_pool_key():
    assert normalize_option_text("Acute Viral  Bronchiolitis") == "acute viral bronchiolitis"


def test_token_closure_follows_declared_implications_and_adds_the_generic():
    closure = expand_response_tokens(
        ["PERCUTANEOUS_SOURCE_CONTROL"],
        MANAGEMENT_CONTRACT["token_implications"],
        "MANAGEMENT_STRATEGY_FOR_PRESENTATION",
    )
    assert closure == {
        "PERCUTANEOUS_SOURCE_CONTROL",
        "PROVIDES_SOURCE_CONTROL",
        "MANAGEMENT_STRATEGY_FOR_PRESENTATION",
    }


def test_identical_generator_labels_do_not_make_mismatched_options_admissible():
    """The old parity gate compared five fields the generator wrote itself.

    Here every option would have carried one identical generator label, and the
    set still fails, because admissibility is decided on what the options mean.
    """
    labels = pool([
        label("Systemic entity one", ["SYSTEMIC_INFLAMMATORY_ILLNESS"], {"organ_system": "BREAST"}),
        label("Systemic entity two", ["SYSTEMIC_INFLAMMATORY_ILLNESS"], {"organ_system": "BREAST"}),
        label("Retention collection", ["PALPABLE_MASS_OR_FLUID_COLLECTION"], {"organ_system": "BREAST"}),
        label("Systemic entity three", ["SYSTEMIC_INFLAMMATORY_ILLNESS"], {"organ_system": "BREAST"}),
    ])
    verdict = adjudicate_option_set_admissibility(
        option_set_archetype="DIAGNOSIS_SET",
        contract=DIAGNOSIS_CONTRACT,
        demanded_response_class="SYSTEMIC_INFLAMMATORY_ILLNESS",
        options=options(
            ["Systemic entity one", "Systemic entity two", "Retention collection", "Systemic entity three"],
            3,
        ),
        label_pool=labels,
    )
    assert verdict["verdict"] == "INADMISSIBLE"
    assert verdict["rule_verdicts"]["ADM_1"] == "FAIL"
    assert verdict["fail_closed_reason"] == "FAIL_CLOSED_INSUFFICIENT_ADMISSIBLE_COMPETITORS"


def test_valid_same_archetype_option_set_is_accepted():
    labels = pool([
        label("Alpha entity", ["SYSTEMIC_INFLAMMATORY_ILLNESS"], {"organ_system": "BREAST"}),
        label("Beta entity", ["SYSTEMIC_INFLAMMATORY_ILLNESS"], {"organ_system": "BREAST"}),
        label("Gamma entity", ["SYSTEMIC_INFLAMMATORY_ILLNESS"], {"organ_system": "BREAST"}),
        label("Delta entity", ["SYSTEMIC_INFLAMMATORY_ILLNESS"], {"organ_system": "BREAST"}),
    ])
    verdict = adjudicate_option_set_admissibility(
        option_set_archetype="DIAGNOSIS_SET",
        contract=DIAGNOSIS_CONTRACT,
        demanded_response_class="SYSTEMIC_INFLAMMATORY_ILLNESS",
        options=options(["Alpha entity", "Beta entity", "Gamma entity", "Delta entity"], 1),
        label_pool=labels,
    )
    assert verdict["verdict"] == "ADMISSIBLE"
    assert verdict["admissible_competitor_count"] == 3


def test_lone_key_response_class_is_rejected_on_a_nominal_axis():
    labels = pool([
        label("Alpha entity", ["ACUTE_ABDOMINAL_OR_PELVIC_PAIN"], {"organ_system": "REPRODUCTIVE"}),
        label("Beta entity", ["ACUTE_ABDOMINAL_OR_PELVIC_PAIN"], {"organ_system": "REPRODUCTIVE"}),
        label("Gamma entity", ["ACUTE_ABDOMINAL_OR_PELVIC_PAIN"], {"organ_system": "REPRODUCTIVE"}),
        label("Delta entity", ["ACUTE_ABDOMINAL_OR_PELVIC_PAIN"], {"organ_system": "GASTROINTESTINAL"}),
    ])
    verdict = adjudicate_option_set_admissibility(
        option_set_archetype="DIAGNOSIS_SET",
        contract=DIAGNOSIS_CONTRACT,
        demanded_response_class="ACUTE_ABDOMINAL_OR_PELVIC_PAIN",
        options=options(["Alpha entity", "Beta entity", "Gamma entity", "Delta entity"], 3),
        label_pool=labels,
    )
    assert verdict["rule_verdicts"]["ADM_2"] == "FAIL"
    assert "KEY_ONLY_ORGAN_SYSTEM" in verdict["nominal_parity_defects"]


def test_severity_mismatched_strategy_is_rejected_while_two_rungs_apart_survive():
    """Distance on an ordinal ladder is the wrong primitive.

    Percutaneous drainage sits well below immediate operation and is admitted;
    a pharmacologic-only strategy sits adjacent to it and is not, because the
    demanded class is a capability rather than a rung.
    """
    labels = pool([
        label("Antibiotics alone", ["PHARMACOLOGIC_ONLY"], {"organ_system": "GASTROINTESTINAL"}),
        label("Percutaneous drainage", ["PERCUTANEOUS_SOURCE_CONTROL"], {"organ_system": "GASTROINTESTINAL"}),
        label("Delayed operation", ["DELAYED_OPERATIVE_SOURCE_CONTROL"], {"organ_system": "GASTROINTESTINAL"}),
        label("Immediate operation", ["IMMEDIATE_OPERATIVE_SOURCE_CONTROL"], {"organ_system": "GASTROINTESTINAL"}),
    ])
    verdict = adjudicate_option_set_admissibility(
        option_set_archetype="MANAGEMENT_STRATEGY_SET",
        contract=MANAGEMENT_CONTRACT,
        demanded_response_class="PROVIDES_SOURCE_CONTROL",
        options=options(
            ["Antibiotics alone", "Percutaneous drainage", "Delayed operation", "Immediate operation"], 3
        ),
        label_pool=labels,
    )
    rejected = {row["option_text"] for row in verdict["inadmissible_options"]}
    assert rejected == {"Antibiotics alone"}
    assert verdict["fail_closed_reason"] == "FAIL_CLOSED_INSUFFICIENT_ADMISSIBLE_COMPETITORS"


def test_adm_3_rejects_a_competitor_defeated_only_by_a_planted_negation():
    labels = pool([
        label("Alpha entity", ["SYSTEMIC_INFLAMMATORY_ILLNESS"], {"organ_system": "BREAST"}),
        label("Beta entity", ["SYSTEMIC_INFLAMMATORY_ILLNESS"], {"organ_system": "BREAST"}),
        label("Gamma entity", ["SYSTEMIC_INFLAMMATORY_ILLNESS"], {"organ_system": "BREAST"}),
        label("Delta entity", ["SYSTEMIC_INFLAMMATORY_ILLNESS"], {"organ_system": "BREAST"}),
    ])
    stem_features = {
        "features": [
            {"feature_id": "F-PLANTED", "polarity": "ABSENT", "inference_type": "ABSENT_FINDING"},
            {"feature_id": "F-REAL", "polarity": "PRESENT", "inference_type": "EXPLICIT_FINDING"},
        ]
    }
    verdict = adjudicate_option_set_admissibility(
        option_set_archetype="DIAGNOSIS_SET",
        contract=DIAGNOSIS_CONTRACT,
        demanded_response_class="SYSTEMIC_INFLAMMATORY_ILLNESS",
        options=options(["Alpha entity", "Beta entity", "Gamma entity", "Delta entity"], 3),
        label_pool=labels,
        stem_feature_map=stem_features,
        competitor_condition_predicates={
            "alpha entity": [{"stem_feature_id": "F-PLANTED", "defeated": True}],
            "beta entity": [{"stem_feature_id": "F-REAL", "defeated": True}],
            "gamma entity": [{"stem_feature_id": "F-REAL", "defeated": True}],
        },
        key_grounding_feature_ids=["F-REAL"],
    )
    assert verdict["rule_verdicts"]["ADM_3"] == "FAIL"
    assert [row["option_text"] for row in verdict["inadmissible_options"]] == ["alpha entity"]


def test_adm_3_does_not_fire_on_a_positively_decisive_finding():
    labels = pool([
        label("Alpha entity", ["SYSTEMIC_INFLAMMATORY_ILLNESS"], {"organ_system": "BREAST"}),
        label("Beta entity", ["SYSTEMIC_INFLAMMATORY_ILLNESS"], {"organ_system": "BREAST"}),
        label("Gamma entity", ["SYSTEMIC_INFLAMMATORY_ILLNESS"], {"organ_system": "BREAST"}),
        label("Delta entity", ["SYSTEMIC_INFLAMMATORY_ILLNESS"], {"organ_system": "BREAST"}),
    ])
    stem_features = {
        "features": [
            {"feature_id": "F-DECISIVE", "polarity": "PRESENT", "inference_type": "EXPLICIT_FINDING"},
        ]
    }
    verdict = adjudicate_option_set_admissibility(
        option_set_archetype="DIAGNOSIS_SET",
        contract=DIAGNOSIS_CONTRACT,
        demanded_response_class="SYSTEMIC_INFLAMMATORY_ILLNESS",
        options=options(["Alpha entity", "Beta entity", "Gamma entity", "Delta entity"], 3),
        label_pool=labels,
        stem_feature_map=stem_features,
        competitor_condition_predicates={
            "alpha entity": [{"stem_feature_id": "F-DECISIVE", "defeated": True}],
        },
        key_grounding_feature_ids=[],
    )
    assert verdict["rule_verdicts"]["ADM_3"] == "PASS"


def test_adm_4_rejects_an_option_the_stem_says_is_already_being_done():
    labels = pool([
        label("Continue the same practice", ["PATIENT_INSTRUCTION"], {},
              {"head": "pump", "objects": ["affected_breast"]}),
        label("Beta instruction", ["PATIENT_INSTRUCTION"], {},
              {"head": "feed", "objects": ["on_demand"]}),
        label("Gamma instruction", ["PATIENT_INSTRUCTION"], {},
              {"head": "apply", "objects": ["warm_compress"]}),
        label("Delta instruction", ["PATIENT_INSTRUCTION"], {},
              {"head": "rest", "objects": ["between_feeds"]}),
    ])
    contract = {
        "option_set_archetype": "NEXT_ACTION_SET",
        "response_class_axis": "next_action_class",
        "token_implications": {},
        "nominal_parity_axes": [],
    }
    verdict = adjudicate_option_set_admissibility(
        option_set_archetype="NEXT_ACTION_SET",
        contract=contract,
        demanded_response_class="PATIENT_INSTRUCTION",
        options=options(
            ["Continue the same practice", "Beta instruction", "Gamma instruction", "Delta instruction"], 1
        ),
        label_pool=labels,
        enacted_action_signatures=[{"heads": ["pump"], "objects": ["affected_breast"]}],
    )
    assert verdict["rule_verdicts"]["ADM_4"] == "FAIL"
    assert [row["option_text"] for row in verdict["inadmissible_options"]] == [
        "Continue the same practice"
    ]


def test_adm_4_does_not_fire_when_only_a_participant_is_shared():
    signature = [{"heads": ["pump"], "objects": ["affected_breast"]}]
    labels = pool([
        label("Feed on demand from the affected breast", ["PATIENT_INSTRUCTION"], {},
              {"head": "feed", "objects": ["on_demand", "affected_breast"]}),
        label("Beta instruction", ["PATIENT_INSTRUCTION"], {}, {"head": "apply", "objects": ["compress"]}),
        label("Gamma instruction", ["PATIENT_INSTRUCTION"], {}, {"head": "rest", "objects": ["between_feeds"]}),
        label("Delta instruction", ["PATIENT_INSTRUCTION"], {}, {"head": "review", "objects": ["latch"]}),
    ])
    contract = {
        "option_set_archetype": "NEXT_ACTION_SET",
        "response_class_axis": "next_action_class",
        "token_implications": {},
        "nominal_parity_axes": [],
    }
    verdict = adjudicate_option_set_admissibility(
        option_set_archetype="NEXT_ACTION_SET",
        contract=contract,
        demanded_response_class="PATIENT_INSTRUCTION",
        options=options(
            ["Feed on demand from the affected breast", "Beta instruction", "Gamma instruction", "Delta instruction"],
            0,
        ),
        label_pool=labels,
        enacted_action_signatures=signature,
    )
    assert verdict["rule_verdicts"]["ADM_4"] == "PASS"


def test_adm_5_finds_the_sole_paired_and_sole_multi_figure_option():
    rows = [
        {"text": "A benefit of 3 in 100 alongside a recall of 12 in 100"},
        {"text": "A single figure of 3"},
        {"text": "Another single figure of 4"},
        {"text": "A third single figure of 5"},
    ]
    defects = find_realization_parity_defects(rows)
    assert "SOLE_PAIRED_QUANTITY_OPTION" in defects
    assert "SOLE_MULTI_FIGURE_OPTION" in defects


def test_adm_5_is_silent_when_no_option_carries_a_figure():
    rows = [{"text": "Alpha"}, {"text": "Beta"}, {"text": "Gamma"}, {"text": "Delta"}]
    assert find_realization_parity_defects(rows) == []


def test_a_response_class_axis_may_not_also_be_a_nominal_parity_axis():
    labels = pool([
        label("Alpha entity", ["SYSTEMIC_INFLAMMATORY_ILLNESS"], {"organ_system": "BREAST"}),
        label("Beta entity", ["SYSTEMIC_INFLAMMATORY_ILLNESS"], {"organ_system": "BREAST"}),
        label("Gamma entity", ["SYSTEMIC_INFLAMMATORY_ILLNESS"], {"organ_system": "BREAST"}),
    ])
    contract = dict(DIAGNOSIS_CONTRACT, nominal_parity_axes=["cardinal_syndrome_capability"])
    with pytest.raises(OptionSetAdmissibilityError, match="may not be both"):
        adjudicate_option_set_admissibility(
            option_set_archetype="DIAGNOSIS_SET",
            contract=contract,
            demanded_response_class="SYSTEMIC_INFLAMMATORY_ILLNESS",
            options=options(["Alpha entity", "Beta entity", "Gamma entity"], 0),
            label_pool=labels,
        )


def test_an_option_with_no_role_blind_label_fails_closed():
    labels = pool([label("Alpha entity", ["SYSTEMIC_INFLAMMATORY_ILLNESS"], {"organ_system": "BREAST"})])
    with pytest.raises(OptionSetAdmissibilityError, match="no role-blind label"):
        adjudicate_option_set_admissibility(
            option_set_archetype="DIAGNOSIS_SET",
            contract=DIAGNOSIS_CONTRACT,
            demanded_response_class="SYSTEMIC_INFLAMMATORY_ILLNESS",
            options=options(["Alpha entity", "Unlabelled entity", "Another entity"], 0),
            label_pool=labels,
        )
