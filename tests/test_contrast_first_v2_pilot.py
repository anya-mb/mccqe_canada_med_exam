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
