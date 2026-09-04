"""Wave execution, the restated gate criteria, and the frozen G1 result."""

import json
from pathlib import Path

import pytest

from qbank.safe_yield_gates import evaluate_gate
from qbank.safe_yield_wave import run_safe_yield_wave


ROOT = Path(__file__).resolve().parents[1]

G1_INPUTS = {
    "opportunities_relative_path": "research/qgen/safe_yield/g1_micro_pilot.opportunities.json",
    "plan_relative_path": "research/qgen/safe_yield/g1_micro_pilot.wave_plan.json",
    "items_relative_path": "research/qgen/safe_yield/g1_micro_pilot.items.json",
    "labels_relative_path": "research/qgen/safe_yield/g1_role_blind_option_labels.json",
    "assignments_relative_path": "research/qgen/safe_yield/g1_demanded_response_classes.json",
}


def wave():
    return run_safe_yield_wave(ROOT, **G1_INPUTS)


def test_the_wave_drives_every_opportunity_out_of_candidate():
    result = wave()
    assert result["pre_verification_summary"]["attempted_opportunities"] == 11
    assert result["pre_verification_summary"]["opportunity_state_counts"]["CANDIDATE"] == 0


def test_a_narrow_topic_fails_closed_with_three_different_reasons():
    """Three fail-closed reasons, not one repeated, so no reason class dominates."""
    result = wave()
    reasons = result["pre_verification_summary"]["fail_closed_by_reason"]
    assert set(reasons) == {
        "FAIL_CLOSED_ERRONEOUS_SOURCE_FACT",
        "FAIL_CLOSED_INCOHERENT_OPTION_SET_ARCHETYPE",
        "FAIL_CLOSED_UNRESOLVED_CRITICAL_FACT",
    }
    total = sum(reasons.values())
    assert max(reasons.values()) / total <= 0.6


def test_the_redundancy_probe_is_rejected_before_any_generation():
    result = wave()
    probe = next(row for row in result["results"] if row["wave_label"] == "G1-PED-02")
    assert probe["novelty_verdict"] == "REDUNDANT"
    assert probe["state"] == "REDUNDANT"
    assert "item_id" not in probe


def test_a_source_unit_error_stops_the_opportunity_rather_than_the_item():
    result = wave()
    row = next(record for record in result["results"] if record["wave_label"] == "G1-SURG-02")
    assert row["fail_closed_reason"] == "FAIL_CLOSED_ERRONEOUS_SOURCE_FACT"
    checks = {
        check
        for failure in row["critical_fact_failures"]
        for check in failure["sanity_checks"]
    }
    assert "UNIT_TRANSPOSITION_SUSPICION" in checks


def test_an_archetype_no_profile_expresses_fails_closed_rather_than_being_forced():
    result = wave()
    row = next(record for record in result["results"] if record["wave_label"] == "G1-PSY-03")
    assert row["fail_closed_reason"] == "FAIL_CLOSED_INCOHERENT_OPTION_SET_ARCHETYPE"
    assert row["reopens_on"] == "AN_AUTHORISED_PROFILE_EXTENSION"


def test_every_admissibility_positive_control_fires_on_its_own_rule():
    result = wave()
    probes = result["admissibility_probes"]
    assert len(probes) == 5
    assert {probe["targets_rule"] for probe in probes} == {
        "ADM_1", "ADM_2", "ADM_3", "ADM_4", "ADM_5"
    }
    assert all(probe["fired"] for probe in probes)


def test_no_gate_family_returns_a_constant_verdict_across_the_wave():
    result = wave()
    constant = sorted(
        family
        for family, verdicts in result["gate_verdicts"].items()
        if len(set(verdicts)) == 1
    )
    assert constant == []


def test_core_decision_coverage_is_a_g2_criterion_and_not_a_g1_one():
    """G1 asks whether the pipeline can produce something safe and refuse the rest.

    Applying G2's coverage bar at G1 would fail every micro pilot that attempts a
    hard CORE decision, which is the opposite of the behaviour the design wants.
    """
    uncovered = [
        {
            "priority_class": "CORE",
            "uncovered_learner_decisions": ["LD-X"],
            "opportunities_opened": 1,
            "accepted_count": 0,
            "mcc_objective_id": "1",
            "no_safe_item_gaps": [],
            "evidence_gaps": [],
            "contrast_gaps": [],
        }
    ]
    common = {
        "summary": {"attempted_opportunities": 4, "no_safe_item": 1, "fail_closed_by_reason": {}},
        "safe_yield": {"safe_yield": 2, "accepted_item_ids": ["A", "B"], "excluded_items": []},
        "defect_counts_in_accepted": {},
        "evidence_entailment": "PASS",
        "verdict_variance": {"verdict_variance": "PASS"},
        "coverage_rows": uncovered,
    }
    assert evaluate_gate("G1", **common)["result"] == "PASS"
    g2 = evaluate_gate("G2", redundancy_positive_control_rejected=True, **common)
    assert "CORE_DECISION_NEITHER_ACCEPTED_NOR_FAIL_CLOSED" in g2["failures"]


def test_the_recorded_g1_outcome_matches_the_committed_reports():
    execution = json.loads(
        (ROOT / "reports/qgen_g1_safe_yield_micro_pilot_execution.json").read_text()
    )
    verification = json.loads(
        (ROOT / "reports/qgen_g1_safe_yield_independent_verification.json").read_text()
    )
    reported = execution["reported"]
    assert reported["attempted_opportunities"] == 11
    assert reported["accepted_safe_yield"] == 5
    assert reported["no_safe_item"] == 3
    assert reported["rejected"] == 2
    assert reported["redundant"] == 1
    assert verification["defect_counts_in_accepted"]["FACTUAL_ERRORS"] == 0
    assert verification["defect_counts_in_accepted"]["NUMERIC_ERRORS"] == 0
    assert verification["defect_counts_in_accepted"]["UNSUPPORTED_CLAIMS"] == 0
    assert verification["defect_counts_in_accepted"]["AMBIGUOUS_BEST_ANSWERS"] == 0
    assert execution["gate_evaluation"]["result"] == "PASS"


def test_a_rejected_item_was_not_retried_to_raise_the_yield():
    execution = json.loads(
        (ROOT / "reports/qgen_g1_safe_yield_micro_pilot_execution.json").read_text()
    )
    assert execution["retry_decisions"]
    assert all(row["retry_permitted"] is False for row in execution["retry_decisions"])


def test_the_coverage_report_separates_a_narrow_topic_from_a_pipeline_gap():
    report = json.loads((ROOT / "reports/qbank_coverage_and_yield.json").read_text())
    diagnoses = {row["study_unit_id"]: row["diagnosis"] for row in report["rows"]}
    assert diagnoses["SU-OB-54"] == "NARROW_TOPIC"
    assert diagnoses["SU-P-147"] == "PIPELINE_GAP"
    alarms = {row["alarm"] for row in report["standing_alarms"]}
    assert "CORE_OBJECTIVE_WITH_NO_ACCEPTED_ITEM" in alarms
    assert "UNCOVERED_HIGH_PRIORITY_DECISION_AT_CORE" in alarms


def test_the_g0_report_records_a_clean_separation():
    report = json.loads((ROOT / "reports/qgen_g0_r4_admissibility_replay.json").read_text())
    assert report["result"] == "PASS"
    assert report["failed_items_rejected"] == 8
    assert report["passed_items_accepted"] == 7
    assert report["false_acceptances"] == []
    assert report["false_rejections"] == []


def test_the_frozen_allocation_artifacts_are_untouched_by_the_planning_layer():
    allocation = json.loads((ROOT / "research/scope/final_question_allocation.json").read_text())
    targets = json.loads((ROOT / "research/scope/question_bank_targets.json").read_text())
    assert allocation["total_target_questions"] == 6086
    assert len(allocation["allocation_addresses"]) == 1507
    assert targets is not None
