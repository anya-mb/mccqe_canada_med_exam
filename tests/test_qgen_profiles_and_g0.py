"""Profile validation, the anti-hard-coding invariant, and the G0 frozen replay."""

import copy
import json
from pathlib import Path

import pytest

from qbank.g0_replay import run_g0_replay
from qbank.option_set_admissibility import NOMINAL_PARITY_AXES, RESPONSE_CLASS_AXES
from qbank.qgen_profiles import (
    DisciplineProfileError,
    PROFILE_IDS,
    load_discipline_profiles,
    resolve_option_set_contract,
    validate_discipline_profile,
)


ROOT = Path(__file__).resolve().parents[1]

G0_INPUTS = {
    "staged_relative_path": "research/qgen/generalization/cross_discipline_generalization_15_r4.staged.json",
    "evidence_relative_path": "research/qgen/generalization/cross_discipline_generalization_15_r4.evidence.json",
    "labels_relative_path": "research/qgen/g0/r4_role_blind_option_labels.json",
    "assignments_relative_path": "research/qgen/g0/r4_demanded_response_classes.json",
    "enacted_relative_path": "research/qgen/g0/r4_stem_enacted_action_signatures.json",
    "independent_verification_relative_path": "reports/qgen_cross_discipline_generalization_15_r4_independent_verification.json",
}

PRODUCTION_MODULES = (
    "scripts/qbank/option_set_admissibility.py",
    "scripts/qbank/qgen_profiles.py",
    "scripts/qbank/critical_fact_adjudication.py",
    "scripts/qbank/coverage_priority.py",
    "scripts/qbank/question_opportunity.py",
    "scripts/qbank/marginal_educational_value.py",
    "scripts/qbank/profile_contrast_retrieval.py",
    "scripts/qbank/coverage_gap_report.py",
    "scripts/qbank/safe_yield_gates.py",
    "scripts/qbank/g0_replay.py",
)


def raw_profile(profile_id):
    path = ROOT / f"research/qgen/profiles/{profile_id}.profile.json"
    return json.loads(path.read_text())


def test_all_six_discipline_profiles_load_and_validate():
    profiles = load_discipline_profiles(ROOT)
    assert sorted(profiles) == sorted(PROFILE_IDS)
    assert profiles["MEDICINE"]["r4_status"] == "UNTESTED_IN_R4"


def test_a_profile_naming_a_canonical_clinical_study_unit_is_refused():
    document = raw_profile("SURGERY")
    document["option_set_contracts"][0]["justification"] = (
        "Only offer entities capable of appendicitis."
    )
    with pytest.raises(DisciplineProfileError, match="canonical clinical"):
        validate_discipline_profile(document, clinical_terms={"appendicitis"})


def test_a_profile_may_not_invent_a_response_class_token():
    document = raw_profile("SURGERY")
    document["option_set_contracts"][0]["token_implications"] = {
        "IMAGINARY_TOKEN": ["PLAUSIBLE_DIAGNOSTIC_ENTITY"]
    }
    with pytest.raises(DisciplineProfileError, match="implication source"):
        validate_discipline_profile(document, clinical_terms=set())


def test_a_profile_may_not_declare_one_axis_as_both_response_class_and_parity():
    document = raw_profile("SURGERY")
    for contract in document["option_set_contracts"]:
        if contract["option_set_archetype"] == "INVESTIGATION_SET":
            contract["nominal_parity_axes"] = ["investigation_purpose"]
    with pytest.raises(DisciplineProfileError, match="may not also be a nominal parity axis"):
        validate_discipline_profile(document, clinical_terms=set())


def test_seed_strength_may_not_lead_the_competitor_ranking():
    document = raw_profile("PEDIATRICS")
    document["competitor_ranking_preference"] = [
        "REVIEWED_SEED_STRENGTH",
        "NEAREST_UNSATISFIED_CORRECTNESS_CONDITION",
    ]
    with pytest.raises(DisciplineProfileError, match="near-miss preference"):
        validate_discipline_profile(document, clinical_terms=set())


def test_every_profile_axis_comes_from_the_closed_common_core_vocabulary():
    profiles = load_discipline_profiles(ROOT)
    for profile in profiles.values():
        for contract in profile["option_set_contracts"].values():
            assert contract["response_class_axis"] in RESPONSE_CLASS_AXES
            for axis in contract["nominal_parity_axes"]:
                assert axis in NOMINAL_PARITY_AXES


def test_an_option_set_archetype_outside_the_item_archetype_needs_an_exception():
    profiles = load_discipline_profiles(ROOT)
    with pytest.raises(DisciplineProfileError, match="is not permitted for"):
        resolve_option_set_contract(profiles["PEDIATRICS"], "AGE_BANDED_DIAGNOSIS", "DISPOSITION_SET")


def test_a_declared_archetype_exception_is_honoured_and_leaves_a_record():
    profiles = load_discipline_profiles(ROOT)
    profile = copy.deepcopy(profiles["PEDIATRICS"])
    profile["permitted_archetype_exceptions"] = [
        {
            "item_archetype": "INVESTIGATION_SELECTION",
            "option_set_archetypes": ["MANAGEMENT_STRATEGY_SET"],
            "authorised_by": "PROFILE_OWNER",
        }
    ]
    contract = resolve_option_set_contract(
        profile, "INVESTIGATION_SELECTION", "MANAGEMENT_STRATEGY_SET"
    )
    assert contract["option_set_archetype"] == "MANAGEMENT_STRATEGY_SET"


# --- G0 ---------------------------------------------------------------------


def test_g0_separates_the_frozen_cohort_with_no_false_verdict_either_way():
    result = run_g0_replay(ROOT, **G0_INPUTS)
    assert result["failed_items_rejected"] == result["failed_items_total"] == 8
    assert result["passed_items_accepted"] == result["passed_items_total"] == 7
    assert result["false_acceptances"] == []
    assert result["false_rejections"] == []
    assert result["result"] == "PASS"


def test_g0_rejections_are_attributed_to_named_general_rules():
    result = run_g0_replay(ROOT, **G0_INPUTS)
    by_item = {row["item_id"]: row["rejected_by"] for row in result["items"]}
    assert "ADM_1" in by_item["QGEN-GEN4-OBGYN-I01"]
    assert "ADM_1" in by_item["QGEN-GEN4-OBGYN-I02"]
    assert "ADM_4" in by_item["QGEN-GEN4-OBGYN-I03"]
    assert "CRITICAL_FACT_ADJUDICATION" in by_item["QGEN-GEN4-SURG-I01"]
    assert "ADM_2" in by_item["QGEN-GEN4-SURG-I01"]
    assert "ADM_1" in by_item["QGEN-GEN4-SURG-I03"]
    assert {"ADM_1", "ADM_2"} <= set(by_item["QGEN-GEN4-PSY-I02"])
    assert by_item["QGEN-GEN4-PSY-I03"] == ["CRITICAL_FACT_ADJUDICATION"]
    assert "ADM_1" in by_item["QGEN-GEN4-PHELO-I02"]


def test_the_replay_gate_families_are_not_uniformly_constant():
    """Finding 1 was a gate that returned one value 250 times.

    Four of five admissibility rules and the fact layer each return two distinct
    values across the cohort. ADM-3 is constant here, and that is expected rather
    than hidden: no R4 failure is attributed to explicit stem negation as its
    earliest causal layer, and the rule is exercised on general inputs elsewhere.
    """
    result = run_g0_replay(ROOT, **G0_INPUTS)
    informative = [
        rule for rule, values in result["rule_verdict_values"].items() if len(values) > 1
    ]
    assert set(informative) == {"ADM_1", "ADM_2", "ADM_4", "ADM_5", "CRITICAL_FACT_ADJUDICATION"}
    assert result["rule_verdict_values"]["ADM_3"] == ["PASS"]


def test_no_production_module_names_a_replayed_item_or_its_clinical_content():
    """The separation must come from general rules, not from knowing the answers."""
    staged = json.loads((ROOT / G0_INPUTS["staged_relative_path"]).read_text())
    item_ids = [item["item_id"] for item in staged["items"]]
    option_texts = [
        option["text"].lower()
        for item in staged["items"]
        for option in item["assembly"]["options"]
    ]
    for relative in PRODUCTION_MODULES:
        source = (ROOT / relative).read_text()
        lowered = source.lower()
        for item_id in item_ids:
            assert item_id not in source, f"{relative} names {item_id}"
        for text in option_texts:
            assert text not in lowered, f"{relative} contains replayed option text"


def test_the_label_pool_cannot_express_a_role_an_item_or_a_position():
    document = json.loads((ROOT / G0_INPUTS["labels_relative_path"]).read_text())
    for entry in document["labels"]:
        assert not {"role", "is_key", "item_id", "option_letter", "position"} & set(entry)


def test_the_demanded_class_artifact_carries_no_option_text():
    staged = json.loads((ROOT / G0_INPUTS["staged_relative_path"]).read_text())
    assignments = (ROOT / G0_INPUTS["assignments_relative_path"]).read_text().lower()
    for item in staged["items"]:
        for option in item["assembly"]["options"]:
            assert option["text"].lower() not in assignments


def test_identical_option_text_resolves_to_one_label_everywhere():
    from qbank.option_set_admissibility import validate_role_blind_label_pool

    document = json.loads((ROOT / G0_INPUTS["labels_relative_path"]).read_text())
    resolved = validate_role_blind_label_pool(document)
    assert len(resolved) == len(document["labels"])
