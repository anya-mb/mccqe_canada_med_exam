"""Tests for the cross-discipline medium pilot run against one pinned snapshot.

The properties under test are the ones that make the pilot a measurement rather
than an outcome: the snapshot is pinned by explicit id and never resolved
implicitly, it does not move inside the batch, an anchor relation the snapshot
does not assert is invisible to every item in the batch, the historical replays
are byte-identical, and the reports regenerate from the committed artifacts.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.qbank.feature_anchor_registry import (
    FeatureAnchorRegistryError,
    load_snapshot,
    registry_hash,
    resolve_seed_anchors,
)
from scripts.qbank.medium_pilot import (
    ACQUISITION_PATH,
    EXECUTION_REPORT_PATH,
    FREEZE_PATH,
    GENERATED_PATH,
    MILESTONE_REPORT_PATH,
    PILOT_SNAPSHOT_ID,
    READINGS_PATH,
    REVIEWS_PATH,
    REVIEW_REPORT_PATH,
    build_execution_report,
    build_milestone_report,
    build_pilot_freeze,
    build_review_report,
    enforce_pinned_snapshot,
    measure_eligible_unconsumed,
    run_pilot,
)

ROOT = Path(__file__).resolve().parents[1]


def _read(relative: str):
    return json.loads((ROOT / relative).read_text())


# ------------------------------------------------------- the pin is explicit


def test_the_pilot_names_one_snapshot_and_there_is_no_latest():
    freeze = _read(FREEZE_PATH)
    assert freeze["feature_anchor_snapshot_id"] == PILOT_SNAPSHOT_ID
    for row in freeze["opportunities"]:
        assert row["feature_anchor_snapshot_id"] == PILOT_SNAPSHOT_ID
    for word in ("LATEST", "CURRENT", "HEAD"):
        with pytest.raises(FeatureAnchorRegistryError):
            load_snapshot(ROOT, word)


def test_every_pilot_artifact_pins_the_same_snapshot():
    ids = {
        _read(path)["feature_anchor_snapshot_id"]
        for path in (FREEZE_PATH, READINGS_PATH, ACQUISITION_PATH, GENERATED_PATH,
                     EXECUTION_REPORT_PATH)
    }
    assert ids == {PILOT_SNAPSHOT_ID}


def test_the_pinned_snapshot_hash_is_stable_and_verified_on_load():
    snapshot = load_snapshot(ROOT, PILOT_SNAPSHOT_ID)
    assert registry_hash(
        snapshot["features"], snapshot["anchor_relations"]
    ) == snapshot["registry_hash"]
    assert _read(EXECUTION_REPORT_PATH)["feature_anchor_registry_hash"] == snapshot[
        "registry_hash"
    ]


# ------------------------------------- the snapshot does not move inside the batch


def test_an_anchor_the_snapshot_does_not_assert_is_withheld_from_the_whole_batch():
    snapshot = load_snapshot(ROOT, PILOT_SNAPSHOT_ID)
    eligible, proposed = enforce_pinned_snapshot(
        ROOT, _read(ACQUISITION_PATH), snapshot
    )
    assert proposed, "the wave proposed nothing, so the rule is untested"
    for entry in eligible["opportunities"].values():
        for candidate in entry["candidates"]:
            pinned = set(resolve_seed_anchors(snapshot, candidate["member_id"]))
            for anchor in candidate.get("added_anchors") or []:
                assert anchor["feature_id"] in pinned
    for row in proposed:
        assert row["eligible_in_this_batch"] is False


def test_enforcement_never_edits_the_committed_acquisition():
    before = _read(ACQUISITION_PATH)
    enforce_pinned_snapshot(ROOT, before, load_snapshot(ROOT, PILOT_SNAPSHOT_ID))
    assert _read(ACQUISITION_PATH) == before


def test_the_report_records_that_the_snapshot_was_not_mutated():
    report = _read(EXECUTION_REPORT_PATH)
    assert report["SNAPSHOT_MUTATED_DURING_PILOT"] is False
    assert report["PROPOSED_EXTENSIONS_FOR_NEXT_SNAPSHOT"]
    for row in report["PROPOSED_EXTENSIONS_FOR_NEXT_SNAPSHOT"]:
        assert row["eligible_in_this_batch"] is False


def test_the_withheld_relations_are_exactly_what_the_counterfactual_buys():
    report = _read(EXECUTION_REPORT_PATH)
    assert report["counts"]["MEDIUM_POST_SUPPLY_CONTRAST_READY"] == 1
    assert report["counts"]["COUNTERFACTUAL_CONTRAST_READY"] == 3
    assert report["counts"]["MEDIUM_GENERATED"] == 0
    assert report["counts"]["COUNTERFACTUAL_GENERATED"] == 1


# ------------------------------------------------- eligibility is not weakened


def test_the_pilot_size_is_measured_and_the_shortfall_is_reported():
    eligibility = measure_eligible_unconsumed(ROOT)
    assert eligibility["MEDIUM_PILOT_N"] == eligibility["TOTAL_ELIGIBLE_UNCONSUMED"]
    assert eligibility["MEDIUM_PILOT_N"] <= eligibility["SPECIFIED_PILOT_SIZE"]
    assert eligibility["BELOW_THE_STATED_FLOOR_OF_24"] is True
    assert eligibility["selection_criteria_unchanged"] is True
    assert sum(
        eligibility["ELIGIBLE_UNCONSUMED_BY_DISCIPLINE"].values()
    ) == eligibility["TOTAL_ELIGIBLE_UNCONSUMED"]


def test_no_opportunity_is_replaced_and_the_denominator_is_the_freeze():
    freeze = _read(FREEZE_PATH)
    report = _read(EXECUTION_REPORT_PATH)
    assert len(report["per_opportunity"]) == freeze["MEDIUM_PILOT_N"]
    assert [row["opportunity_label"] for row in report["per_opportunity"]] == [
        row["opportunity_label"] for row in freeze["opportunities"]
    ]


def test_every_pilot_opportunity_is_eligible_and_unconsumed():
    consumed = set(_read(
        "research/qgen/pilot/contrast-first-v2-frozen-10-readings.json"
    )["opportunities"])
    labels = {row["opportunity_label"] for row in _read(FREEZE_PATH)["opportunities"]}
    assert not labels & consumed


# ----------------------------------------------- the historical path is unchanged


def test_the_frozen_ten_replay_is_unchanged_by_the_pilot_parameterization():
    from scripts.qbank.contrast_first_v2_pilot import (
        V2_READINGS_PATH,
        build_v2_contrast_sets,
    )

    assert build_v2_contrast_sets(ROOT) == build_v2_contrast_sets(
        ROOT, readings_path=V2_READINGS_PATH
    )


def test_the_frozen_five_recovery_report_still_regenerates_byte_identically():
    from scripts.qbank.contrast_supply import build_frozen5_recovery_report

    assert build_frozen5_recovery_report(ROOT) == _read(
        "reports/qgen_v2_frozen5_supply_recovery.json"
    )


def test_the_registry_gate_replay_still_regenerates_byte_identically():
    from scripts.qbank.feature_anchor_registry import build_gate_replay

    assert build_gate_replay(ROOT) == _read(
        "reports/qgen_feature_anchor_registry_gate_replay.json"
    )


def test_an_under_size_set_is_still_refused_not_admitted():
    """Reporting the size failure instead of raising must not admit anything."""
    from scripts.qbank.contrast_first_v2_pilot import build_v2_contrast_sets

    sets = build_v2_contrast_sets(ROOT, readings_path=READINGS_PATH)
    undersized = [
        row for row in sets["results"] if row["assembly_coherence"] is None
    ]
    assert undersized
    for row in undersized:
        assert row["terminal_state_at_assembly"] == "NO_SAFE_ITEM"
        assert row["fail_closed_reason_at_assembly"] == "FAIL_CLOSED_CONTRAST_SET_SIZE"


# ----------------------------------------------------- the reports are derived


def test_the_pilot_reports_regenerate_byte_identically():
    assert build_pilot_freeze(ROOT) == _read(FREEZE_PATH)
    assert build_execution_report(ROOT) == _read(EXECUTION_REPORT_PATH)
    assert build_review_report(ROOT) == _read(REVIEW_REPORT_PATH)
    assert build_milestone_report(ROOT) == _read(MILESTONE_REPORT_PATH)


def test_the_pilot_run_is_deterministic():
    first = run_pilot(ROOT)
    second = run_pilot(ROOT)
    assert first["replay"] == second["replay"]
    assert first["proposed_extensions"] == second["proposed_extensions"]


def test_nothing_was_accepted_so_no_accepted_item_safety_is_claimed():
    review = _read(REVIEW_REPORT_PATH)
    assert review["MEDIUM_ACCEPTED"] == 0
    assert review["MEDIUM_ACCEPTED_ITEM_SAFETY"] == "NO_ACCEPTED_ITEMS"
    assert _read(MILESTONE_REPORT_PATH)["PRODUCTION_SCALEOUT_SPEC_WRITTEN"] == "NO"


def test_the_systematic_defect_gate_is_computed_from_the_measured_population():
    taxonomy = _read(EXECUTION_REPORT_PATH)["failure_taxonomy"]
    assert taxonomy["population"] == 6
    assert taxonomy["SYSTEMATIC_DEFECT_GE_20_PERCENT"] == "YES"
    assert taxonomy["SYSTEMATIC_DEFECT_PERCENT"] >= 20.0
    assert sum(taxonomy["architectural_defects"].values()) == taxonomy["population"]


def test_no_llm_api_call_is_recorded_anywhere_in_the_pilot():
    for path in (FREEZE_PATH, READINGS_PATH, ACQUISITION_PATH, GENERATED_PATH,
                 REVIEWS_PATH, EXECUTION_REPORT_PATH, REVIEW_REPORT_PATH,
                 MILESTONE_REPORT_PATH):
        document = _read(path)
        recorded = document.get("llm_api_calls", document.get("authorship", {}))
        if isinstance(recorded, dict):
            recorded = recorded.get("llm_api_calls", 0)
        assert recorded == 0


def test_the_copyright_audit_finds_no_verbatim_toronto_notes_run():
    audit = _read(MILESTONE_REPORT_PATH)["copyright"]
    assert audit["COPYRIGHT_AUDIT"] == "PASS"
    assert audit["longest_verbatim_toronto_notes_run_words"] == 0
