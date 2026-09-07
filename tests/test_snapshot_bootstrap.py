"""Tests for the snapshot bootstrap and its three arms.

The invariants that matter here are not the numbers -- those are measurements and
may legitimately move -- but the things that must hold whatever the numbers are:

* the snapshot store is append-only, so V1 and V2 do not move when V3 is added;
* an UNCERTAIN extension is invisible to every reader of every snapshot;
* an approved extension is visible to all three readers or to none;
* only one variable moves between arms;
* every committed artifact regenerates byte for byte.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from qbank.feature_anchor_registry import (
    BOOTSTRAP_EXTENSIONS_PATH,
    BOOTSTRAP_SNAPSHOT_ID,
    EXTENDED_SNAPSHOT_ID,
    SNAPSHOTS_PATH,
    build_snapshot_store,
    load_extensions,
    load_snapshot,
    resolve_seed_anchors,
)
from qbank.snapshot_bootstrap import (
    ARM_A_SNAPSHOT,
    ARM_B_SNAPSHOT,
    ARM_C_ACQUISITION_PATH,
    DISTRACTOR_REPORT_PATH,
    FRESH_PILOT_FLOOR,
    FRESH_UNIVERSE_REPORT_PATH,
    MILESTONE_REPORT_PATH,
    ROOT_CAUSE_REPORT_PATH,
    THREE_ARM_REPORT_PATH,
    VISIBILITY_REPORT_PATH,
    approved_v3_extensions,
    build_arm_c_acquisition,
    build_distractor_diagnosis,
    build_fresh_universe_feasibility,
    build_milestone_report,
    build_never_best_overlay,
    build_root_cause_report,
    build_three_arm_report,
    build_visibility_replay,
    uncertain_v3_extensions,
)

ROOT = Path(__file__).resolve().parents[1]


def _read(relative: str):
    return json.loads((ROOT / relative).read_text())


# --------------------------------------------------------- the snapshot itself


def test_the_snapshot_store_is_append_only():
    tracked = _read(SNAPSHOTS_PATH)
    rebuilt = build_snapshot_store(ROOT)
    for snapshot_id in ("FEATURE_ANCHOR_SNAPSHOT_V1", EXTENDED_SNAPSHOT_ID):
        assert rebuilt["snapshots"][snapshot_id] == tracked["snapshots"][snapshot_id]
    assert BOOTSTRAP_SNAPSHOT_ID in rebuilt["snapshots"]


def test_v3_carries_v2s_relations_plus_exactly_the_approved_delta():
    parent = load_snapshot(ROOT, EXTENDED_SNAPSHOT_ID)
    child = load_snapshot(ROOT, BOOTSTRAP_SNAPSHOT_ID)
    approved = approved_v3_extensions(ROOT)
    assert child["feature_count"] == parent["feature_count"]
    assert child["anchor_relation_count"] == parent["anchor_relation_count"] + len(
        approved
    )
    parent_ids = {row["anchor_relation_id"] for row in parent["anchor_relations"]}
    child_ids = {row["anchor_relation_id"] for row in child["anchor_relations"]}
    assert parent_ids < child_ids
    assert child["extension_diff"]["parent_snapshot_id"] == EXTENDED_SNAPSHOT_ID
    assert child["extension_diff"]["UNCERTAIN_EXTENSIONS_ADDED"] == 0


def test_no_uncertain_extension_reaches_any_snapshot():
    uncertain = uncertain_v3_extensions(ROOT)
    assert uncertain, "the exclusion invariant needs something to exclude"
    for snapshot_id in (
        "FEATURE_ANCHOR_SNAPSHOT_V1", EXTENDED_SNAPSHOT_ID, BOOTSTRAP_SNAPSHOT_ID
    ):
        snapshot = load_snapshot(ROOT, snapshot_id)
        for extension in uncertain:
            feature_id = extension.get("feature_id") or extension["proposed_feature_id"]
            scope = (extension.get("scope_opportunity_labels") or [None])[0]
            anchors = resolve_seed_anchors(
                snapshot, extension["seed_id"], scope=scope
            )
            assert feature_id not in anchors


def test_every_uncertain_extension_records_why_it_stayed_uncertain():
    for extension in uncertain_v3_extensions(ROOT):
        review = extension["registry_review"]
        assert review["verdict"] == "UNCERTAIN"
        assert review["why_it_remained_uncertain"].strip()
        assert review["reviewer_inconsistency_or_evidence_bug"].strip()
        assert review["revisit_condition"].strip()


def test_an_uncertain_extension_cannot_be_promoted_by_the_snapshot_builder():
    from qbank.feature_anchor_registry import (
        FeatureAnchorRegistryError,
        build_snapshot,
    )

    uncertain = uncertain_v3_extensions(ROOT)[0]
    with pytest.raises(FeatureAnchorRegistryError, match="only APPROVED"):
        build_snapshot(ROOT, snapshot_id="SCRATCH", extensions=[uncertain])


def test_a_new_feature_extension_can_never_be_approved_by_this_registry():
    document = load_extensions(ROOT, path=BOOTSTRAP_EXTENSIONS_PATH)
    new_features = [
        row for row in document["extensions"]
        if row["classification"] == "NEW_FEATURE_REQUIRED"
    ]
    assert new_features
    assert all(
        row["registry_review"]["verdict"] != "APPROVED" for row in new_features
    )


# ------------------------------------------------------------- the visibility


def test_an_approved_extension_is_visible_to_all_three_readers_or_to_none():
    report = build_visibility_replay(ROOT)
    for snapshot_id, row in report["snapshots"].items():
        assert row["VISIBILITY_SET_EQUALITY"], snapshot_id
        assert row["UNCERTAIN_EXTENSIONS_VISIBLE"] == 0
    v3 = report["snapshots"][ARM_B_SNAPSHOT]
    assert v3["APPROVED_EXTENSIONS_VISIBLE_TO_SNAPSHOT"] == v3["APPROVED_EXTENSIONS"]
    v2 = report["snapshots"][ARM_A_SNAPSHOT]
    assert v2["APPROVED_EXTENSIONS_VISIBLE_TO_SNAPSHOT"] == 0


def test_the_bootstrap_precommitment_is_evaluated_not_asserted():
    criteria = build_visibility_replay(ROOT)["precommitted_bootstrap_criteria"]
    assert set(criteria) >= {
        "AT_LEAST_ONE_WITHHELD_FAILURE_CONVERTED",
        "HISTORICAL_CONTROLS_UNCHANGED",
        "NO_UNCERTAIN_EXTENSION_VISIBLE",
        "NO_SAFETY_GATE_WEAKENED",
    }
    assert criteria["HISTORICAL_CONTROLS_UNCHANGED"] is True
    assert criteria["NO_UNCERTAIN_EXTENSION_VISIBLE"] is True


# ------------------------------------------------------------------ the arms


def test_only_the_snapshot_moves_between_arm_a_and_arm_b():
    from qbank.medium_pilot import ACQUISITION_PATH, run_pilot

    arm_a = run_pilot(ROOT, snapshot_id=ARM_A_SNAPSHOT)
    arm_b = run_pilot(ROOT, snapshot_id=ARM_B_SNAPSHOT)
    assert arm_a["acquisition_path"] == arm_b["acquisition_path"] == ACQUISITION_PATH
    assert arm_a["feature_anchor_snapshot_id"] != arm_b["feature_anchor_snapshot_id"]


def test_arm_c_changes_only_how_candidates_are_typed():
    frozen = _read("research/qgen/pilot/medium-pilot-6-acquisition.json")
    arm_c = build_arm_c_acquisition(ROOT)
    assert set(arm_c["opportunities"]) == set(frozen["opportunities"])
    for label, entry in frozen["opportunities"].items():
        theirs = {row["member_id"] for row in entry["candidates"]}
        ours = {
            row["member_id"] for row in arm_c["opportunities"][label]["candidates"]
        }
        assert theirs == ours, label
    admitted = set(arm_c["ARM_C_ADMITTED_AS_NEVER_BEST"])
    for label, entry in arm_c["opportunities"].items():
        for candidate in entry["candidates"]:
            if candidate["member_id"] in admitted:
                continue
            assert candidate["review"]["verdict"] == frozen["opportunities"][label][
                "candidates"
            ][
                [row["member_id"] for row in frozen["opportunities"][label]["candidates"]]
                .index(candidate["member_id"])
            ]["review"]["verdict"]


def test_a_candidate_with_no_frozen_plausibility_anchor_stays_refused_in_arm_c():
    arm_c = build_arm_c_acquisition(ROOT)
    assert "SEED-PED-T03-HYPERTONIC" in arm_c["ARM_C_STILL_REFUSED"]
    assert "SEED-PED-T03-HYPERTONIC" not in arm_c["ARM_C_ADMITTED_AS_NEVER_BEST"]


def test_the_unchanged_coherence_gate_still_refuses_a_wrong_decision_class_candidate():
    """Arm C admits SEED-OB-T02-CRP as a candidate and CS2-3 throws it out.

    The point is which layer refuses it. The case file classifies it, but the
    verdict that removes it from the set is the unmodified response-class rule
    reading the frozen seed's own tokens.
    """
    from qbank.snapshot_bootstrap import run_arm_c

    wave = {
        row["opportunity_label"]: row for row in run_arm_c(ROOT)["wave"]["results"]
    }
    dropped = wave["G2-OBGYN-02"]["selection_after"]["dropped"]
    assert dropped.get("SEED-OB-T02-CRP") == "CS2-3"


def test_the_three_arms_move_one_variable_each_and_are_reported_together():
    report = build_three_arm_report(ROOT)
    totals = report["totals"]
    assert set(totals) == {
        "ARM_A_ORIGINAL_MEDIUM6", "ARM_B_V3_SNAPSHOT", "ARM_C_V3_PLUS_SEMANTICS",
    }
    for arm in totals.values():
        assert arm["OPPORTUNITIES"] == 6
        assert arm["CONTRAST_READY"] + arm["NO_SAFE_ITEM"] >= 6
    assert report["ALL_ACCEPTED_ITEM_SAFETY"] in (
        "PASS", "FAIL", "NO_ACCEPTED_ITEMS"
    )


def test_arm_a_reproduces_the_committed_medium_pilot():
    committed = _read("reports/qgen_medium_pilot_execution.json")
    arm_a = build_three_arm_report(ROOT)["totals"]["ARM_A_ORIGINAL_MEDIUM6"]
    assert arm_a["CONTRAST_READY"] == committed["counts"][
        "MEDIUM_POST_SUPPLY_CONTRAST_READY"
    ]
    assert arm_a["GENERATED"] == committed["counts"]["MEDIUM_GENERATED"]
    assert arm_a["NO_SAFE_ITEM"] == committed["counts"]["MEDIUM_NO_SAFE_ITEM"]


# --------------------------------------------------------- the distractor case


def test_every_diagnosed_case_is_a_frozen_curated_seed_with_its_own_review():
    overlay = build_never_best_overlay(ROOT)
    assert overlay["NEVER_CORRECT_DISTRACTOR_CASES"] == len(overlay["cases"])
    for case in overlay["cases"]:
        assert case["frozen_independent_seed_review_verdict"] == "PASS"
        assert case["frozen_prose_no_state_makes_it_correct"].strip()
        assert case["CLASSIFICATION"] in {
            "COUNTERFACTUAL_CORRECT", "PLAUSIBLE_BUT_NEVER_BEST", "DEAD_DISTRACTOR",
            "WRONG_DECISION_CLASS", "UNSAFE_OR_AMBIGUOUS",
        }


def test_every_admissible_case_satisfies_the_never_best_contract():
    from qbank.clinical_contrast_v2 import (
        PLAUSIBLE_BUT_NEVER_BEST,
        validate_never_best_contract,
    )

    for case in build_never_best_overlay(ROOT)["cases"]:
        if not case["ADMISSIBLE_UNDER_THE_CONTRACT"]:
            continue
        validate_never_best_contract({
            "member_id": case["member_id"],
            "distractor_semantics": PLAUSIBLE_BUT_NEVER_BEST,
            "never_best_contract": case["never_best_contract"],
            "supporting_features": [
                {"feature_id": feature_id, "contrast_role": "POSITIVE_SUPPORT"}
                for feature_id in case["plausibility_anchor_feature_ids"]
            ],
        })


def test_the_negative_control_is_not_swept_into_the_never_correct_class():
    overlay = build_never_best_overlay(ROOT)
    control = overlay["negative_control"]
    assert control["CLASSIFICATION"] == "COUNTERFACTUAL_CORRECT"
    assert control["member_id"] not in {row["member_id"] for row in overlay["cases"]}


def test_the_necessity_claim_is_answered_from_the_frozen_accepted_controls():
    diagnosis = build_distractor_diagnosis(ROOT)
    necessity = diagnosis["is_the_requirement_necessary_for_one_best_answer_safety"]
    assert necessity["answer"] == "NO"
    accepted = necessity["argument_from_the_accepted_controls"]
    assert accepted["verdict"] == "ACCEPTED"
    assert accepted["count"] >= 1
    assert diagnosis["CURRENT_V2_REQUIRES_COUNTERFACTUAL_CORRECTNESS"] == "YES"
    assert [row for row in diagnosis["options_considered"] if row["chosen"]] == [
        row for row in diagnosis["options_considered"]
        if row["option"].startswith("OPTION_2")
    ]


# -------------------------------------------------------------- the fresh pilot


def test_the_fresh_universe_is_measured_before_it_is_claimed():
    report = build_fresh_universe_feasibility(ROOT)
    ceiling = report["MAXIMUM_FRESH_OPPORTUNITIES_WITHOUT_LOWERING_STANDARDS"]
    assert report["FRESH_PILOT_TRIGGERED"] == (ceiling >= FRESH_PILOT_FLOOR)
    if not report["FRESH_PILOT_TRIGGERED"]:
        assert report["OPPORTUNITY_CONSTRUCTION_DIAGNOSIS"]["BINDING_LAYER"]


def test_no_opportunity_was_invented_to_reach_a_target():
    report = build_fresh_universe_feasibility(ROOT)
    funnel = report["funnel"]
    assert funnel["DECLARED_LEARNER_DECISIONS"] == (
        funnel["LEARNER_DECISIONS_ALREADY_AN_OPPORTUNITY"]
        + funnel["DECLARED_LEARNER_DECISIONS_NOT_YET_AN_OPPORTUNITY"]
    )
    assert report["MAXIMUM_FRESH_OPPORTUNITIES_WITHOUT_LOWERING_STANDARDS"] == funnel[
        "DECLARED_LEARNER_DECISIONS_NOT_YET_AN_OPPORTUNITY"
    ]


# ------------------------------------------------------------- reproducibility


@pytest.mark.parametrize(
    "relative,builder",
    [
        (ARM_C_ACQUISITION_PATH, build_arm_c_acquisition),
        (ROOT_CAUSE_REPORT_PATH, build_root_cause_report),
        (VISIBILITY_REPORT_PATH, build_visibility_replay),
        (DISTRACTOR_REPORT_PATH, build_distractor_diagnosis),
        (THREE_ARM_REPORT_PATH, build_three_arm_report),
        (FRESH_UNIVERSE_REPORT_PATH, build_fresh_universe_feasibility),
        (MILESTONE_REPORT_PATH, build_milestone_report),
    ],
)
def test_every_bootstrap_artifact_regenerates_byte_identically(relative, builder):
    assert builder(ROOT) == _read(relative)


def test_the_milestone_does_not_claim_an_accepted_item_or_a_fresh_pilot():
    milestone = build_milestone_report(ROOT)
    assert milestone["independent_review"]["REVIEWS_RUN"] == 0
    assert milestone["ALL_ACCEPTED_ITEM_SAFETY"] == "NO_ACCEPTED_ITEMS"
    assert milestone["PRODUCTION_SCALEOUT_SPEC_WRITTEN"] == "NO"
    assert milestone["snapshot"]["HISTORICAL_FROZEN_ARTIFACTS_MODIFIED"] == 0
    assert milestone["copyright"]["COPYRIGHT_AUDIT"] == "PASS"
