"""The V2 replay over the ten frozen contrast-first opportunities.

These are the regression fixtures the design requires: each of the four measured
defects is asserted here against the *real* frozen material that exposed it, not
against a synthetic set. A change that reintroduces one of them fails a named
test rather than moving a summary number.

The two accepted V1 controls are asserted to survive, which is the limb of the
precommitted gate that stops the model being tuned into refusing everything.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft7Validator

from qbank.clinical_contrast_v2 import (
    AMBIGUOUS,
    INDETERMINATE,
    INSUFFICIENT_SUPPORT,
    LIVE_BUT_INFERIOR,
    SATISFIED,
    SECOND_KEY,
)
from qbank.contrast_first_v2_pilot import (
    ACCEPTED_V1_CONTROLS,
    NON_OPTION_LAYER_REJECTIONS,
    build_counterfactual_report,
    build_relation_cache,
    build_v2_contrast_sets,
    run_counterfactual_replay,
)

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def report():
    return build_counterfactual_report(ROOT)


@pytest.fixture(scope="module")
def replay(report):
    return {row["opportunity_label"]: row for row in report["replay"]["results"]}


def states(replay, label):
    return {
        verdict["member_id"]: verdict["state"]
        for verdict in replay[label]["competitor_verdicts"]
    }


def verdict(replay, label, member_id):
    return next(
        row for row in replay[label]["competitor_verdicts"]
        if row["member_id"] == member_id
    )


# ------------------------------------------------------------------- shape


def test_all_ten_final_review_opportunities_are_replayed(report):
    assert report["counts"]["OPPORTUNITIES_REPLAYED"] == 10
    assert report["questions_generated"] == 0
    assert report["llm_api_calls"] == 0
    assert report["stems_changed"] == 0
    assert report["frozen_qgen_artifacts_changed"] == 0


def test_the_relation_cache_validates_against_its_schema(report):
    schema = json.loads(
        (ROOT / "schemas/clinical-contrast-relation-v2.schema.json").read_text()
    )
    cache = build_relation_cache(ROOT, build_v2_contrast_sets(ROOT))
    errors = list(Draft7Validator(schema).iter_errors(cache))
    assert errors == [], [error.message for error in errors[:3]]
    assert len(cache["relations"]) == 68


def test_every_relation_is_evidence_verified_and_cites_a_claim(report):
    cache = build_relation_cache(ROOT, build_v2_contrast_sets(ROOT))
    for relation in cache["relations"]:
        assert relation["verification_status"] == "EVIDENCE_VERIFIED"
        assert relation["evidence_refs"]
        for discriminator in relation["discriminators"]:
            assert discriminator["evidence_refs"]


# ------------------------------------ defect 4: a disjunction is not a conjunction


def test_ped_02_disjunctive_guideline_indications_are_second_keys(replay):
    """R2: 'The stem's own facts satisfy the guideline conditions the rationales
    say are unmet.' Under V1 both were scored 1 of 2 and treated as defeated."""
    assert states(replay, "G2-PED-02")["SEED-PED-T02-CXR"] == SECOND_KEY
    assert states(replay, "G2-PED-02")["SEED-PED-T02-VIRAL"] == SECOND_KEY


def test_ped_02_key_is_not_established_by_its_own_frozen_stem(replay):
    """The keyed answer is arguably wrong: CLM-R4-PED-CONTINUOUS reserves
    intermittent monitoring for a lower-risk infant or one who is improving, and
    this infant is hypoxaemic and failing to improve."""
    row = replay["G2-PED-02"]
    assert row["key_correctness_under_the_frozen_stem"] == INDETERMINATE
    assert "FAIL_CLOSED_KEY_NOT_ESTABLISHED_BY_THE_STEM" in row["v2_fail_closed_reasons"]


def test_ped_01_disjunctive_seeds_are_second_keys(replay):
    assert states(replay, "G2-PED-01")["SEED-PED-T01-FOREIGN-BODY"] == SECOND_KEY
    assert states(replay, "G2-PED-01")["SEED-PED-T01-PNEUMONIA"] == SECOND_KEY


def test_ped_01_asthma_is_not_turned_into_a_second_key_by_the_same_change(replay):
    """The disjunctive reading is faithful, not permissive: asthma carries an age
    precondition the stem states contrary, so it stays a live inferior option."""
    assert states(replay, "G2-PED-01")["SEED-PED-T01-ASTHMA"] == LIVE_BUT_INFERIOR


# ------------------------------------------- defect 1: silence is not absence


def test_no_competitor_anywhere_is_defeated_by_silence_alone(report):
    for label, row in report["per_item"].items():
        assert row["silence_as_absence_defects_after"] == [], label
    assert report["counts"]["KNOWN_SILENCE_AS_ABSENCE_DEFECTS_AFTER"] == 0
    assert report["counts"]["KNOWN_SILENCE_AS_ABSENCE_DEFECTS_BEFORE"] > 0


def test_phelo_01_length_and_overdiagnosis_are_ambiguous_not_defeated(replay):
    """R1: randomisation excludes healthy-screenee bias but not length bias or
    overdiagnosis, and the stem supplies no case-mix or case-count data."""
    assert states(replay, "G2-PHELO-01")["SEED-PHELO-T01-LENGTH"] == AMBIGUOUS
    assert states(replay, "G2-PHELO-01")["SEED-PHELO-T01-OVERDIAGNOSIS"] == AMBIGUOUS


def test_phelo_01_healthy_screenee_is_defeated_by_a_stated_contrary(replay):
    """Randomisation into equal groups is a declared contradiction of
    self-selection, so this one is a real negation rather than a silence."""
    row = verdict(replay, "G2-PHELO-01", "SEED-PHELO-T01-HEALTHY-SCREENEE")
    assert row["state"] == LIVE_BUT_INFERIOR
    assert row["defeated_by"] == ["SF-PH07-SELF-SELECTED-GROUPS"]
    assert "SF-PH07-SELF-SELECTED-GROUPS" in replay["G2-PHELO-01"][
        "features_implied_absent_by_contradiction"
    ]


def test_psy_03_digital_cbt_is_not_defeated_by_an_unelicited_preference(replay):
    """R3: digitally delivered CBT is a second defensible key. The stem reports no
    patient preference, and the access barrier it does report is the very
    condition under which digital delivery is indicated."""
    row = verdict(replay, "G2-PSY-03", "SEED-PSY-T03-DIGITAL")
    assert row["state"] != LIVE_BUT_INFERIOR
    assert row["correctness"] == INDETERMINATE
    assert row["second_key_risk"] is True
    assert "SF-PS12-PATIENT-PREFERS-PSYCHOTHERAPY" in row["unresolved_features"]


# --------------------------------- defect 2: competitors are compared with each other


def test_med_03_the_two_preload_reducing_options_are_mutually_redundant(replay):
    """R1: furosemide and sublingual nitroglycerin are eliminated by one and the
    same preload proposition, so one option slot does no independent work."""
    violations = replay["G2-MED-03"]["assembly_coherence"]
    assert "CS2-2" in violations["violations"]
    fired = [row for row in violations["detail"] if row["rule"] == "CS2-2"]
    assert [sorted(row["pair"]) for row in fired] == [
        ["SEED-G2-MED-T02-DIURETIC", "SEED-G2-MED-T02-NITRATE"]
    ]


def test_surg_01_tubo_ovarian_abscess_nests_in_pelvic_inflammatory_disease(replay):
    violations = replay["G2-SURG-01"]["assembly_coherence"]
    assert "CS2-1" in violations["violations"]
    assert "CS2-5" in violations["violations"]


def test_ped_01_anchor_equals_condition_is_caught_before_a_stem_exists(replay):
    violations = replay["G2-PED-01"]["assembly_coherence"]
    assert "CS2-6" in violations["violations"]
    caught = {row["member_id"] for row in violations["detail"] if row["rule"] == "CS2-6"}
    assert caught == {"SEED-PED-T01-FOREIGN-BODY", "SEED-PED-T01-PNEUMONIA"}


# ------------------------------------------- defect 3: an anchor must be a finding


def test_surg_01_a_demographic_does_not_anchor_a_competitor(replay):
    """The frozen stem states only migratory pain and that the patient is a woman
    of reproductive age. All three gynaecologic competitors were live under V1."""
    assert set(states(replay, "G2-SURG-01").values()) == {INSUFFICIENT_SUPPORT}
    row = verdict(replay, "G2-SURG-01", "SEED-SURG-T01-PID")
    assert row["anchors_present"] == ["SF-GS76-FEMALE-REPRODUCTIVE-AGE"]
    assert row["presentation_anchors_present"] == []


def test_surg_02_an_availability_clause_does_not_anchor_a_competitor(replay):
    assert set(states(replay, "G2-SURG-02").values()) == {INSUFFICIENT_SUPPORT}


def test_surg_02_key_conditions_are_meta_assertions_not_findings(replay):
    """Both key correctness conditions are a suspicion band and an availability
    clause, so the stem can only declare the answer rather than show it."""
    assert "CS2-9" in replay["G2-SURG-02"]["assembly_coherence"]["violations"]


# ------------------------------------------------- the precommitted gate limbs


def test_the_accepted_v1_controls_survive(report, replay):
    assert report["counts"]["ACCEPTED_V1_CONTROLS_PRESERVED"] == "2/2"
    for label in ACCEPTED_V1_CONTROLS:
        row = replay[label]
        assert row["v2_terminal_state"] == "READY_FOR_STEM", label
        assert row["key_correctness_under_the_frozen_stem"] == SATISFIED, label
        assert set(states(replay, label).values()) == {LIVE_BUT_INFERIOR}, label


def test_the_one_option_layer_rejection_is_not_intercepted(report):
    """G2-OBGYN-01's cause was two rationale claims authored at realization. A
    contrast-relation model has nothing to say about it and must not pretend to."""
    assert report["per_item"]["G2-OBGYN-01"]["V2_TERMINAL_STATE"] == "READY_FOR_STEM"
    assert "G2-OBGYN-01" not in NON_OPTION_LAYER_REJECTIONS


def test_every_non_option_rejection_is_intercepted_before_final_review(report):
    assert report["counts"][
        "NON_OPTION_REJECTIONS_INTERCEPTED_PRE_FINAL_REVIEW"
    ] == "7/7"
    assert report["counts"]["not_intercepted"] == []


def test_the_precommitted_counterfactual_gate_passes(report):
    assert report["gate"]["COUNTERFACTUAL_GATE"] == "PASS"
    assert all(report["gate"]["limbs"].values())


def test_the_reports_regenerate_byte_identically_from_committed_artifacts():
    rebuilt = build_counterfactual_report(ROOT)
    contrast_sets = rebuilt.pop("contrast_sets")
    for relative, value in (
        ("reports/qgen_clinical_contrast_v2_counterfactual.json", rebuilt),
        ("research/qgen/pilot/contrast-first-v2-frozen-10-relations.json", contrast_sets),
        ("research/qgen/clinical_contrast_relations_v2.json",
         build_relation_cache(ROOT, contrast_sets)),
    ):
        committed = json.loads((ROOT / relative).read_text())
        assert committed == value, relative


def test_the_replay_reads_the_frozen_stems_and_writes_nothing(replay):
    for label, row in replay.items():
        assert row["stem_asserted_features"], label
        assert set(row["features_implied_absent_by_contradiction"]).isdisjoint(
            row["stem_asserted_features"]
        ), label


# ---------------------------------------------------------------- the replay


@pytest.fixture(scope="module")
def v2_replay():
    from qbank.contrast_first_v2_pilot import run_v2_replay

    return {row["opportunity_label"]: row for row in run_v2_replay(ROOT)["results"]}


@pytest.fixture(scope="module")
def verification(v2_replay):
    from qbank.contrast_first_v2_pilot import build_verification_report, run_v2_replay

    return build_verification_report(ROOT, run_v2_replay(ROOT))


def test_one_attempt_per_opportunity_and_no_prose_for_a_refused_set(v2_replay):
    for label, row in v2_replay.items():
        if row["terminal_state"] == "NO_SAFE_ITEM":
            assert "stem" not in row, label
            assert row["fail_closed_reason"], label
        else:
            assert row["stem"], label


def test_every_realized_stem_realizes_its_blueprint_exactly(v2_replay):
    for label, row in v2_replay.items():
        if row["stage_reached"] != "INDEPENDENT_REVIEW":
            continue
        assert row["stem_realizes_the_blueprint_exactly"], label


def test_every_realized_item_clears_the_unchanged_production_gate(v2_replay):
    for label, row in v2_replay.items():
        if row["stage_reached"] != "INDEPENDENT_REVIEW":
            continue
        gate = row["production_gate"]
        assert gate["post_stem_3_viable"], label
        assert gate["gate_is_the_production_gate"] == (
            "profile_contrast_retrieval.retrieve_profile_aware_contrasts"
        )
        for rule, excluded in gate["excluded_by_rule"].items():
            assert excluded == [], (label, rule)


def test_every_realized_competitor_is_live_but_inferior(v2_replay):
    from qbank.clinical_contrast_v2 import LIVE_BUT_INFERIOR

    for label, row in v2_replay.items():
        if row["stage_reached"] != "INDEPENDENT_REVIEW":
            continue
        for verdict in row["competitor_verdicts"]:
            assert verdict["state"] == LIVE_BUT_INFERIOR, (label, verdict["member_id"])
            assert verdict["second_key_risk"] is False, (label, verdict["member_id"])


def test_every_competitor_is_settled_by_a_named_route_never_by_silence(v2_replay):
    from qbank.contrast_first_v2_pilot import SETTLEMENT_ROUTES

    for label, row in v2_replay.items():
        if row["stage_reached"] != "INDEPENDENT_REVIEW":
            continue
        settlement = row["stem_blueprint_v2"]["competitor_settlement"]
        assert settlement, label
        for member_id, route in settlement.items():
            assert route["route"] in SETTLEMENT_ROUTES, (label, member_id)
            assert route["features"], (label, member_id)


def test_no_rationale_uses_the_v1_template_clause(v2_replay):
    for label, row in v2_replay.items():
        if row["stage_reached"] != "INDEPENDENT_REVIEW":
            continue
        for option in row["options"]:
            assert "condition is not met here" not in option["rationale"].lower(), label


def test_distractor_option_text_is_the_frozen_seed_string_verbatim(v2_replay):
    from qbank.contrast_first_v2_pilot import build_v2_contrast_sets

    concepts = {
        member["member_id"]: member["concept"]
        for record in build_v2_contrast_sets(ROOT)["results"]
        for member in record["contrast_set"]["members"]
    }
    for label, row in v2_replay.items():
        if row["stage_reached"] != "INDEPENDENT_REVIEW":
            continue
        for option in row["options"]:
            if option["is_key"]:
                continue
            assert option["text"] == concepts[option["source"]], (label, option["source"])


def test_accepted_item_safety_is_perfect(verification):
    assert verification["ACCEPTED_ITEM_SAFETY"] == "PASS"
    assert all(value == 0 for value in verification["accepted_item_safety"].values())


def test_the_v2_outcome_over_the_same_ten_opportunities(verification):
    assert verification["counts"] == {
        "ITEMS_REALIZED": 5,
        "ACCEPTED": 4,
        "REJECTED": 1,
        "NO_SAFE_ITEM": 5,
        "accepted": ["G2-MED-03", "G2-PHELO-01", "G2-PHELO-02", "G2-PHELO-03"],
        "rejected": ["G2-OBGYN-01"],
        "no_safe_item": [
            "G2-PED-01", "G2-PED-02", "G2-PSY-03", "G2-SURG-01", "G2-SURG-02",
        ],
    }


def test_the_specified_medium_pilot_cannot_be_built_from_canonical_material():
    from qbank.contrast_first_v2_pilot import measure_medium_pilot_supply

    supply = measure_medium_pilot_supply(ROOT)
    assert supply["FEASIBLE"] is False
    assert supply["FROZEN_OPPORTUNITY_UNIVERSE"] == 30
    assert supply["OPPORTUNITIES_WITH_AN_AUTHORED_OPTION_SET_CONTRACT"] == 18
    assert supply["REMAINING_UNUSED"] == 6


def test_the_v2_reports_regenerate_byte_identically_from_committed_artifacts():
    from qbank.contrast_first_pilot import measure_copyright
    from qbank.contrast_first_v2_pilot import (
        V2_TRACKED_ARTIFACTS,
        build_comparison_report,
        build_counterfactual_report,
        build_difficulty_report,
        build_verification_report,
        decide_v2_assessment,
        measure_medium_pilot_supply,
        measure_v2_context,
        run_v2_replay,
    )

    rebuilt = run_v2_replay(ROOT)
    verification = build_verification_report(ROOT, rebuilt)
    counterfactual = build_counterfactual_report(ROOT)
    counterfactual.pop("contrast_sets")
    comparison = build_comparison_report(ROOT, rebuilt, verification, counterfactual)
    supply = measure_medium_pilot_supply(ROOT)
    decision = decide_v2_assessment(verification, comparison, counterfactual, supply)
    verification.update({
        "decision": decision,
        "difficulty": build_difficulty_report(ROOT, rebuilt, verification),
        "context_characters": measure_v2_context(ROOT, rebuilt),
        "copyright": measure_copyright(ROOT, V2_TRACKED_ARTIFACTS),
        "replay": rebuilt,
    })
    comparison["medium_pilot_feasibility"] = supply
    comparison["decision"] = decision
    for relative, value in (
        ("reports/qgen_clinical_contrast_v2_pilot_verification.json", verification),
        ("reports/qgen_clinical_contrast_v1_vs_v2.json", comparison),
    ):
        assert json.loads((ROOT / relative).read_text()) == value, relative


def test_no_toronto_notes_text_is_reproduced():
    from qbank.contrast_first_pilot import measure_copyright
    from qbank.contrast_first_v2_pilot import V2_TRACKED_ARTIFACTS

    audit = measure_copyright(ROOT, V2_TRACKED_ARTIFACTS)
    assert audit["COPYRIGHT_AUDIT"] == "PASS"
    assert audit["longest_verbatim_toronto_notes_run_words"] == 0
