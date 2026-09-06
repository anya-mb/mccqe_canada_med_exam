"""The consumers of the pinned snapshot: V2, `SAF_1` and profile-aware retrieval.

`SAF_1`'s rule is not tested here because it did not change. What is tested is
that all three consumers now resolve anchors from one snapshot, that an unpinned
consumer is bit-for-bit what it was, and that an anchor approved for one decision
does not silently anchor the same competitor in another.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from scripts.qbank.clinical_retrieval import build_current_library_index
from scripts.qbank.contrast_first_pilot import load_curated_candidates
from scripts.qbank.feature_anchor_registry import (
    BASELINE_SNAPSHOT_ID,
    EXTENDED_SNAPSHOT_ID,
    GATE_REPLAY_REPORT_PATH,
    POSITIVE_CONTROL_LABEL,
    FeatureAnchorRegistryError,
    build_gate_replay,
    load_snapshot,
    resolve_seed_anchors,
    snapshot_anchor_index,
)

ROOT = Path(__file__).resolve().parents[1]

#: The two anchor additions the supply wave approved for the positive control.
PED_01_SUPPLIED = ("SEED-PED-T01-FOREIGN-BODY", "SEED-PED-T01-PNEUMONIA")
SUPPLIED_FEATURE = "SF-P147-MODERATE-SEVERE-DISTRESS"


@pytest.fixture(scope="module")
def baseline():
    return load_snapshot(ROOT, BASELINE_SNAPSHOT_ID)


@pytest.fixture(scope="module")
def extended():
    return load_snapshot(ROOT, EXTENDED_SNAPSHOT_ID)


@pytest.fixture(scope="module")
def replay():
    return build_gate_replay(ROOT)


# ------------------------------------------------- the unpinned path is inert


def test_an_unpinned_curated_candidate_is_byte_identical():
    """Frozen reports serialize these rows, so the unpinned path adds no field."""
    unpinned = load_curated_candidates(ROOT)
    assert unpinned
    for row in unpinned:
        assert "feature_anchor_snapshot_id" not in row


def test_an_unpinned_arm_a_index_is_byte_identical():
    assert all(
        "feature_anchor_snapshot_id" not in row
        for row in build_current_library_index(ROOT)
    )


def test_the_baseline_snapshot_reproduces_the_unpinned_index_exactly(baseline):
    unpinned = {row["seed_id"]: row for row in build_current_library_index(ROOT)}
    pinned = {
        row["seed_id"]: row
        for row in build_current_library_index(ROOT, feature_anchor_snapshot=baseline)
    }
    assert set(unpinned) == set(pinned)
    for seed_id, row in unpinned.items():
        assert (
            row["plausibility_anchor_feature_ids"]
            == pinned[seed_id]["plausibility_anchor_feature_ids"]
        )


# ------------------------------------------------------------- visibility


def test_an_approved_extension_is_visible_to_v2(extended):
    for seed_id in PED_01_SUPPLIED:
        assert SUPPLIED_FEATURE in snapshot_anchor_index(
            extended, scope=POSITIVE_CONTROL_LABEL
        )[seed_id]


def test_an_approved_extension_is_visible_to_profile_retrieval(extended):
    rows = {
        row["seed_id"]: row
        for row in load_curated_candidates(
            ROOT,
            feature_anchor_snapshot=extended,
            feature_anchor_scope=POSITIVE_CONTROL_LABEL,
        )
    }
    for seed_id in PED_01_SUPPLIED:
        assert SUPPLIED_FEATURE in rows[seed_id]["plausibility_anchor_feature_ids"]
        assert rows[seed_id]["feature_anchor_snapshot_id"] == EXTENDED_SNAPSHOT_ID


def test_an_approved_extension_is_visible_to_saf1(replay):
    """SAF_1's own verdict, not an index field: the rule stops refusing the seeds."""
    gates = replay["frozen_five_gates"]
    legacy = gates["LEGACY_FROZEN_STEM_ANCHOR_PACK"][POSITIVE_CONTROL_LABEL]
    new = gates[EXTENDED_SNAPSHOT_ID][POSITIVE_CONTROL_LABEL]
    assert sorted(legacy["excluded_by_rule"]["SAF_1"]) == sorted(PED_01_SUPPLIED)
    assert new["excluded_by_rule"]["SAF_1"] == []


def test_the_three_visibility_sets_reconcile(replay):
    assert replay["visibility"]["the_sets_reconcile"] is True
    assert replay["visibility"]["APPROVED_ANCHOR_RELATIONS"] == 4
    for key in ("visible_to_v2", "visible_to_saf1", "visible_to_profile_retrieval"):
        assert len(replay["visibility"][key]) == 4


# ----------------------------------------------------------------- scoping


def test_an_anchor_reviewed_for_one_decision_does_not_anchor_in_another(extended):
    """The regression the strict historical rule caught, pinned as a test.

    `SEED-PSY-T03-COMBINED`'s anchor was approved for `G2-PSY-03`. `G2-PSY-04` is
    a different learner decision whose stem also states moderate severity, and no
    reviewer considered the combination there.
    """
    in_scope = snapshot_anchor_index(extended, scope="G2-PSY-03")
    out_of_scope = snapshot_anchor_index(extended, scope="G2-PSY-04")
    assert "SF-PS12-MODERATE-SEVERITY" in in_scope["SEED-PSY-T03-COMBINED"]
    assert "SF-PS12-MODERATE-SEVERITY" not in out_of_scope["SEED-PSY-T03-COMBINED"]


def test_an_unscoped_read_of_an_extended_snapshot_applies_no_extension(extended, baseline):
    """No scope means no extension, which is the fail-closed direction."""
    assert snapshot_anchor_index(extended) == snapshot_anchor_index(baseline)


def test_an_extension_without_a_reviewed_scope_is_refused():
    from scripts.qbank.feature_anchor_registry import (
        approved_extensions, build_snapshot, load_extensions,
    )

    unscoped = copy.deepcopy(approved_extensions(load_extensions(ROOT))[0])
    unscoped["scope_opportunity_labels"] = []
    with pytest.raises(FeatureAnchorRegistryError, match="universal-anchor"):
        build_snapshot(ROOT, snapshot_id="TEST", extensions=[unscoped])


def test_a_seed_outside_the_snapshot_is_refused_rather_than_falling_back(baseline):
    with pytest.raises(FeatureAnchorRegistryError, match="no fallback"):
        resolve_seed_anchors(baseline, "SEED-NOT-IN-ANY-PACK")


def test_a_snapshot_whose_hash_does_not_match_its_rows_is_refused(baseline):
    tampered = copy.deepcopy(baseline)
    tampered["anchor_relations"].pop()
    with pytest.raises(FeatureAnchorRegistryError, match="registry hash"):
        load_curated_candidates(ROOT, feature_anchor_snapshot=tampered)


# ----------------------------------------------- historical replay and control


def test_the_historical_replay_is_unchanged(replay):
    regression = replay["historical_regression"]
    assert regression["BASELINE_REPRODUCES_LEGACY_EXACTLY"] is True
    assert regression["EVERY_MOVED_OPPORTUNITY_IS_IN_AN_APPROVED_EXTENSION_SCOPE"] is True
    assert regression["opportunities_whose_ranked_set_moves_under_v2"] == ["G2-PSY-03"]


def test_no_safety_gate_is_weakened(replay):
    regression = replay["historical_regression"]
    legacy = regression["legacy_unpinned"]
    extended = regression["pinned_extended_v2"]
    assert legacy["KNOWN_ANCHORLESS_RETURNED"] == 0
    assert extended["KNOWN_ANCHORLESS_RETURNED_WITHOUT_AN_APPROVED_EXTENSION"] == 0
    assert legacy["KNOWN_SECOND_KEY_RETURNED"] == extended["KNOWN_SECOND_KEY_RETURNED"] == 0
    assert legacy["SECOND_KEY_REFUSALS"] == extended["SECOND_KEY_REFUSALS"] == 8
    assert extended["ACCEPTED_CONTROLS_PRESERVED"] >= legacy["ACCEPTED_CONTROLS_PRESERVED"]


def test_g2_ped_01_is_refused_by_the_legacy_contract_and_passes_the_new_one(replay):
    """The positive control, isolating the registry fix and nothing else."""
    control = replay["positive_control"]
    assert control["G2_PED_01_LEGACY_SAF1"] == "FAIL"
    assert control["G2_PED_01_NEW_SAF1"] == "PASS"
    assert control["new_gate"]["ranked_competitors"] == [
        "SEED-PED-T01-ASTHMA", "SEED-PED-T01-FOREIGN-BODY", "SEED-PED-T01-PNEUMONIA"
    ]
    assert control["new_gate"]["feature_anchor_snapshot_id"] == EXTENDED_SNAPSHOT_ID


def test_the_positive_controls_item_was_not_edited():
    """No stem, option, key, evidence or rationale may move for this control."""
    generated = json.loads(
        (ROOT / "research/qgen/clinical_contrast_supply_frozen5_generated.json").read_text()
    )
    item = generated["items"][POSITIVE_CONTROL_LABEL]
    assert item["key_concept"] == "Acute viral bronchiolitis"
    assert item["stem"].startswith("A 7-month-old girl is brought to hospital.")
    assert sorted(item["distractor_rationales"]) == [
        "SEED-PED-T01-ASTHMA", "SEED-PED-T01-FOREIGN-BODY", "SEED-PED-T01-PNEUMONIA"
    ]


def test_contract_reconciliation_passes_on_every_precommitted_limb(replay):
    assert replay["CONTRACT_RECONCILIATION"] == "PASS"
    assert all(replay["precommitted_limbs"].values())


def test_the_gate_replay_report_regenerates_byte_identically():
    committed = json.loads((ROOT / GATE_REPLAY_REPORT_PATH).read_text())
    assert build_gate_replay(ROOT) == committed


# ------------------------------------------------ frozen-five replay and decision


@pytest.fixture(scope="module")
def frozen5():
    from scripts.qbank.feature_anchor_registry import build_frozen5_registry_replay

    return build_frozen5_registry_replay(ROOT)


def test_only_the_anchor_contract_moved_in_the_frozen_five_replay(frozen5):
    """The two blueprint refusals are untouched, which is the correct outcome."""
    rows = frozen5["per_opportunity"]
    for label in ("G2-PED-02", "G2-PSY-03", "G2-SURG-01", "G2-SURG-02"):
        assert rows[label]["legacy"] == rows[label]["new_snapshot"]
    assert rows["G2-PED-01"]["legacy"]["passes_the_production_anchor_contract"] is False
    assert rows["G2-PED-01"]["new_snapshot"]["passes_the_production_anchor_contract"] is True


def test_the_frozen_five_before_and_after_accounting(frozen5):
    counts = frozen5["counts"]
    assert counts["FROZEN5_WITH_3_VALID_BEFORE_SUPPLY"] == "1/5"
    assert counts["FROZEN5_WITH_3_VALID_AFTER_SUPPLY"] == "3/5"
    assert counts["FROZEN5_VISIBLE_TO_LEGACY_SAF1"] == "0/5"
    assert counts["FROZEN5_VISIBLE_TO_NEW_SAF1"] == "1/5"
    assert counts["FROZEN5_GENERATED_BEFORE_REGISTRY_FIX"] == 1
    assert counts["FROZEN5_GENERATED_AFTER_REGISTRY_FIX"] == 1
    assert counts["FROZEN5_ACCEPTED_BEFORE_REGISTRY_FIX"] == 0
    assert counts["FROZEN5_ACCEPTED_AFTER_REGISTRY_FIX"] == 1
    assert counts["NEW_GENERATION_ATTEMPTS_RUN"] == 0


def test_accepted_item_safety_is_perfect(frozen5):
    assert frozen5["ACCEPTED_ITEM_SAFETY"] == "PASS"
    assert set(frozen5["accepted_item_safety"].values()) == {0}
    assert len(frozen5["accepted_item_safety"]) == 11


def test_the_supply_context_cost_did_not_move(frozen5):
    """The registry adds no serialization, so the recorded figures must hold."""
    supply = frozen5["context_characters"]["supply_layer_only"]
    assert supply["TOTAL_PER_OPPORTUNITY"] == {"median": 35824, "p95": 42860}


def test_the_medium36_trigger_is_met_and_the_pilot_is_still_unbuildable():
    from scripts.qbank.feature_anchor_registry import build_milestone_report

    milestone = build_milestone_report(ROOT)
    assert milestone["medium36"]["ALL_TRIGGER_LIMBS_MET"] is True
    assert milestone["medium36"]["PILOT_IS_BUILDABLE"] is False
    assert milestone["medium36"]["MEDIUM36_TRIGGERED"] == "NO"
    assert milestone["medium36"]["feasibility"]["FROZEN_OPPORTUNITY_UNIVERSE"] == 30


def test_the_frozen_five_replay_report_regenerates_byte_identically():
    from scripts.qbank.feature_anchor_registry import (
        FROZEN5_REPLAY_REPORT_PATH, build_frozen5_registry_replay,
    )

    committed = json.loads((ROOT / FROZEN5_REPLAY_REPORT_PATH).read_text())
    assert build_frozen5_registry_replay(ROOT) == committed
