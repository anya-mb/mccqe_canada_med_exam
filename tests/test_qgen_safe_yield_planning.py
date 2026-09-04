"""Planning-layer tests: priority, opportunities, novelty, coverage and gates."""

from pathlib import Path

import pytest

from qbank.coverage_gap_report import (
    build_coverage_and_yield_report,
    build_coverage_row,
    evaluate_standing_alarms,
)
from qbank.coverage_priority import (
    apply_objective_reachability_promotion,
    build_coverage_priority_model,
    derive_priority_classes,
    load_frozen_allocation,
)
from qbank.marginal_educational_value import (
    assess_marginal_value,
    should_stop_for_redundancy,
)
from qbank.qgen_profiles import DisciplineProfileError, assert_no_quota_shaped_fields
from qbank.question_opportunity import (
    QuestionOpportunityError,
    compute_opportunity_id,
    may_reopen,
    may_retry,
    open_opportunity,
    summarize_opportunities,
    transition_opportunity,
)
from qbank.safe_yield_gates import (
    compute_safe_yield,
    evaluate_gate,
    evaluate_stop_rules,
    monitor_verdict_variance,
    safe_yield_rate,
)


ROOT = Path(__file__).resolve().parents[1]


# --- coverage priority -------------------------------------------------------


def test_priority_classes_are_derived_from_the_frozen_competency_depth():
    rows = derive_priority_classes(load_frozen_allocation(ROOT))
    counts: dict[str, int] = {}
    for row in rows.values():
        counts[row["priority_class"]] = counts.get(row["priority_class"], 0) + 1
    assert counts == {"CORE": 488, "IMPORTANT": 424, "SUPPORTING": 263, "NOT_IN_SCOPE": 332}


def test_a_non_eligible_address_keeps_a_zero_opportunity_budget():
    rows = derive_priority_classes(load_frozen_allocation(ROOT))
    suppressed = [row for row in rows.values() if row["priority_class"] == "NOT_IN_SCOPE"]
    assert suppressed
    assert all(row["maximum_opportunities"] == 0 for row in suppressed)


def test_reachability_promotion_leaves_every_mapped_objective_reachable_from_core():
    rows = derive_priority_classes(load_frozen_allocation(ROOT))
    promotion = apply_objective_reachability_promotion(rows)
    assert len(promotion["orphan_objectives"]) == 16
    assert len(promotion["promoted_address_ids"]) == 15
    core_objectives = {
        objective
        for row in rows.values()
        if row["priority_class"] == "CORE"
        for objective in row["mcc_objective_ids"]
    }
    mapped = {
        objective
        for row in rows.values()
        if row["priority_class"] != "NOT_IN_SCOPE"
        for objective in row["mcc_objective_ids"]
    }
    assert mapped - core_objectives == set()


def test_the_promotion_is_visible_rather_than_folded_in():
    model = build_coverage_priority_model(ROOT)
    promoted = [
        row
        for row in model["addresses"]
        if row["priority_class_basis"] == "OBJECTIVE_REACHABILITY_PROMOTION"
    ]
    assert len(promoted) == 15
    assert model["priority_class_counts"]["CORE"] == 503


def test_the_priority_model_carries_no_quota_shaped_field():
    assert_no_quota_shaped_fields(build_coverage_priority_model(ROOT), label="model")


def test_a_quota_shaped_field_is_refused_wherever_it_appears():
    with pytest.raises(DisciplineProfileError, match="quota-shaped"):
        assert_no_quota_shaped_fields({"rows": [{"remaining_questions": 4}]}, label="x")


# --- question opportunities --------------------------------------------------


def address(**overrides):
    row = {
        "allocation_address_id": "SU-TEST-01",
        "study_unit_id": "SU-TEST-01",
        "discipline": "MED",
        "discipline_profile_id": "MEDICINE",
        "chapter": "T",
        "mcc_objective_ids": ["101"],
        "priority_class": "CORE",
        "priority_class_basis": "DEPTH_DERIVED",
        "maximum_opportunities": 3,
        "curriculum_attention_signal": 1,
    }
    row.update(overrides)
    return row


def opened(**overrides):
    kwargs = {
        "address": address(),
        "learner_decision_id": "LD-1",
        "physician_activity": "Assessment/Diagnosis",
        "item_archetype": "DIAGNOSIS",
        "option_set_archetype": "DIAGNOSIS_SET",
        "educational_purpose": "The candidate can separate two entities on one axis.",
        "declared_learner_decisions": ["LD-1", "LD-2"],
        "existing_opportunities": [],
        "anchor_tn_source": "T.S01.T01",
        "mcc_objective_id": "101",
    }
    kwargs.update(overrides)
    return open_opportunity(**kwargs)


def test_opportunity_identity_is_deterministic_and_activity_bound():
    first = compute_opportunity_id(
        anchor_study_unit_id="SU-1", learner_decision_id="LD-1",
        physician_activity="Management", item_archetype="DIAGNOSIS",
        option_set_archetype="DIAGNOSIS_SET", discipline_profile_id="MEDICINE",
    )
    second = compute_opportunity_id(
        anchor_study_unit_id="SU-1", learner_decision_id="LD-1",
        physician_activity="Management", item_archetype="DIAGNOSIS",
        option_set_archetype="DIAGNOSIS_SET", discipline_profile_id="MEDICINE",
    )
    assert first == second
    with pytest.raises(QuestionOpportunityError, match="not canonical"):
        compute_opportunity_id(
            anchor_study_unit_id="SU-1", learner_decision_id="LD-1",
            physician_activity="Vibes", item_archetype="DIAGNOSIS",
            option_set_archetype="DIAGNOSIS_SET", discipline_profile_id="MEDICINE",
        )


def test_a_decision_outside_the_frozen_declared_list_may_not_open_an_opportunity():
    with pytest.raises(QuestionOpportunityError, match="frozen declared decisions"):
        opened(learner_decision_id="LD-INVENTED")


def test_a_suppressed_address_may_never_open_an_opportunity():
    with pytest.raises(QuestionOpportunityError, match="non-eligible"):
        opened(address=address(priority_class="NOT_IN_SCOPE", maximum_opportunities=0))


def test_the_budget_is_an_upper_bound_and_falling_short_of_it_is_not_reported():
    row = opened()
    summary = summarize_opportunities([row])
    assert summary["attempted_opportunities"] == 1
    assert "maximum_opportunities" not in summary
    assert all("remaining" not in key for key in summary)


def test_an_unused_allocation_slot_is_a_valid_outcome():
    """A budget of thirty against one accepted item is a topic, not a shortfall."""
    row = opened(address=address(maximum_opportunities=30))
    row = transition_opportunity(row, "EVIDENCE_READY", decisive_discriminator="D")
    row = transition_opportunity(row, "CONTRAST_READY")
    row = transition_opportunity(row, "GENERATABLE")
    row = transition_opportunity(row, "ACCEPTED")
    summary = summarize_opportunities([row])
    assert summary["accepted"] == 1
    assert summary["attempted_opportunities"] == 1


def test_an_illegal_lifecycle_transition_is_refused():
    row = opened()
    with pytest.raises(QuestionOpportunityError, match="illegal opportunity transition"):
        transition_opportunity(row, "ACCEPTED")


def test_no_safe_item_requires_a_canonical_reason_and_records_what_reopens_it():
    row = opened()
    row = transition_opportunity(row, "EVIDENCE_READY", decisive_discriminator="D")
    with pytest.raises(QuestionOpportunityError, match="canonical fail-closed reason"):
        transition_opportunity(row, "NO_SAFE_ITEM", reason="BECAUSE")
    row = transition_opportunity(
        row, "NO_SAFE_ITEM", reason="FAIL_CLOSED_INSUFFICIENT_ADMISSIBLE_COMPETITORS"
    )
    assert row["reopens_on"] == "NEW_SEEDS_OR_A_PROFILE_VOCABULARY_ENTRY"


def test_a_fail_closed_opportunity_reopens_on_a_new_input_and_never_on_a_rerun():
    row = opened()
    row = transition_opportunity(row, "CANDIDATE" and "EVIDENCE_READY", decisive_discriminator="D")
    row = transition_opportunity(row, "NO_SAFE_ITEM", reason="FAIL_CLOSED_INSUFFICIENT_EVIDENCE")
    assert may_reopen(row, "A_NEW_SOURCE_PACKET") is True
    assert may_reopen(row, None) is False
    assert may_reopen(row, "SAME_INPUTS_AGAIN") is False


def test_answer_ambiguity_never_reopens():
    row = opened()
    row = transition_opportunity(row, "EVIDENCE_READY", decisive_discriminator="D")
    row = transition_opportunity(row, "CONTRAST_READY")
    row = transition_opportunity(row, "GENERATABLE")
    row = transition_opportunity(row, "NO_SAFE_ITEM", reason="FAIL_CLOSED_ANSWER_AMBIGUITY")
    assert may_reopen(row, "A_NEW_SOURCE_PACKET") is False


def test_only_one_realization_level_retry_is_permitted():
    row = opened()
    assert may_retry(row, "REALIZATION") is True
    assert may_retry(row, "EVIDENCE") is False
    assert may_retry(row, "ADMISSIBILITY") is False
    row["retry_count"] = 1
    assert may_retry(row, "REALIZATION") is False


# --- marginal educational value ---------------------------------------------


def tuple_row(**overrides):
    row = {
        "item_reference": "ITEM-A",
        "learner_decision_id": "LD-1",
        "physician_activity": "Assessment/Diagnosis",
        "decisive_discriminator": "DISC-1",
        "option_set_archetype": "DIAGNOSIS_SET",
        "competitor_concept_ids": ["C1", "C2", "C3"],
    }
    row.update(overrides)
    return row


def test_a_demographic_change_alone_is_redundant():
    verdict = assess_marginal_value(
        tuple_row(context_changes=["PATIENT_NAME", "CITY_OR_SETTING", "AGE_INSIDE_SAME_BAND"]),
        [tuple_row()],
    )
    assert verdict["verdict"] == "REDUNDANT"


def test_a_context_change_that_alters_the_answer_is_novel():
    verdict = assess_marginal_value(
        tuple_row(context_changes=["PREGNANCY_CHANGES_ADMISSIBLE_AGENT"]), [tuple_row()]
    )
    assert verdict["verdict"] == "NOVEL_CONTEXT_WITH_REAL_PEDAGOGIC_VALUE"


def test_swapping_one_competitor_is_not_a_novel_contrast():
    verdict = assess_marginal_value(
        tuple_row(competitor_concept_ids=["C1", "C2", "C9"], newly_tested_discriminations=["X"]),
        [tuple_row()],
    )
    assert verdict["verdict"] == "REDUNDANT"


def test_two_new_competitors_that_change_the_discrimination_are_novel():
    verdict = assess_marginal_value(
        tuple_row(
            competitor_concept_ids=["C1", "C8", "C9"], newly_tested_discriminations=["X"]
        ),
        [tuple_row()],
    )
    assert verdict["verdict"] == "NOVEL_CONTRAST"


def test_a_different_decision_is_novel_and_a_different_discriminator_is_novel_reasoning():
    assert assess_marginal_value(tuple_row(learner_decision_id="LD-2"), [tuple_row()])[
        "verdict"
    ] == "NOVEL_DECISION"
    assert assess_marginal_value(tuple_row(decisive_discriminator="DISC-2"), [tuple_row()])[
        "verdict"
    ] == "NOVEL_REASONING"


def test_novelty_must_hold_against_every_accepted_item_not_merely_one():
    verdict = assess_marginal_value(
        tuple_row(learner_decision_id="LD-2"),
        [tuple_row(item_reference="A"), tuple_row(item_reference="B", learner_decision_id="LD-2")],
    )
    assert verdict["verdict"] == "REDUNDANT"


def test_the_topic_stops_after_two_consecutive_redundant_candidates():
    assert should_stop_for_redundancy(["NOVEL_DECISION", "REDUNDANT"]) is False
    assert should_stop_for_redundancy(["REDUNDANT", "REDUNDANT"]) is True


# --- coverage and gap reporting ---------------------------------------------


def coverage_address(**overrides):
    row = {
        "allocation_address_id": "SU-TEST-01",
        "study_unit_id": "SU-TEST-01",
        "discipline": "MED",
        "chapter": "T",
        "priority_class": "CORE",
        "priority_class_basis": "DEPTH_DERIVED",
    }
    row.update(overrides)
    return row


def opportunity_row(state, decision, **overrides):
    row = {
        "allocation_address_id": "SU-TEST-01",
        "mcc_objective_id": "101",
        "learner_decision_id": decision,
        "state": state,
    }
    row.update(overrides)
    return row


def test_a_narrow_topic_and_a_pipeline_gap_are_distinguished_without_reading_a_count():
    narrow = build_coverage_row(
        address=coverage_address(),
        mcc_objective_id="101",
        declared_learner_decisions=["LD-1"],
        opportunities=[opportunity_row("ACCEPTED", "LD-1")],
        wave_id="W1",
    )
    gap = build_coverage_row(
        address=coverage_address(),
        mcc_objective_id="101",
        declared_learner_decisions=["LD-1", "LD-2", "LD-3"],
        opportunities=[opportunity_row("ACCEPTED", "LD-1")],
        wave_id="W1",
    )
    assert narrow["diagnosis"] == "NARROW_TOPIC"
    assert gap["diagnosis"] == "PIPELINE_GAP"
    assert narrow["accepted_count"] == gap["accepted_count"] == 1


def test_an_address_with_no_declared_decisions_is_never_diagnosed_narrow():
    row = build_coverage_row(
        address=coverage_address(),
        mcc_objective_id="101",
        declared_learner_decisions=[],
        opportunities=[opportunity_row("ACCEPTED", "LD-1")],
        wave_id="W1",
    )
    assert row["diagnosis"] == "DECISIONS_NOT_DECLARED"


def test_a_fail_closed_decision_is_covered_accounting_but_still_a_reported_gap():
    row = build_coverage_row(
        address=coverage_address(),
        mcc_objective_id="101",
        declared_learner_decisions=["LD-1"],
        opportunities=[
            opportunity_row(
                "NO_SAFE_ITEM", "LD-1",
                fail_closed_reason="FAIL_CLOSED_INSUFFICIENT_EVIDENCE",
                reopens_on="A_NEW_SOURCE_PACKET",
            )
        ],
        wave_id="W1",
    )
    assert row["uncovered_learner_decisions"] == []
    assert row["no_safe_item_gaps"][0]["reopens_on"] == "A_NEW_SOURCE_PACKET"
    assert row["diagnosis"] == "PIPELINE_GAP"


def test_the_report_carries_no_target_or_percent_of_target_column():
    report = build_coverage_and_yield_report(
        wave_id="W1",
        rows=[
            build_coverage_row(
                address=coverage_address(),
                mcc_objective_id="101",
                declared_learner_decisions=["LD-1"],
                opportunities=[opportunity_row("ACCEPTED", "LD-1")],
                wave_id="W1",
            )
        ],
        fail_closed_by_reason={},
    )
    serialized = str(report)
    for forbidden in ("percent_of_target", "under_target", "target_questions"):
        assert forbidden not in serialized


def test_the_standing_alarms_fire():
    rows = [
        build_coverage_row(
            address=coverage_address(),
            mcc_objective_id="101",
            declared_learner_decisions=["LD-1", "LD-2"],
            opportunities=[opportunity_row("REJECTED", "LD-1")],
            wave_id="W1",
        )
    ]
    alarms = evaluate_standing_alarms(
        rows,
        fail_closed_by_reason={"FAIL_CLOSED_INSUFFICIENT_EVIDENCE": 9, "FAIL_CLOSED_REDUNDANT": 1},
        previous_wave_metrics={"safe_yield_rate": 0.0, "uncovered_core_decisions": 0},
        outstanding_no_safe_item_waves={"QOPP-X": 3},
    )
    fired = {row["alarm"] for row in alarms}
    assert "CORE_OBJECTIVE_WITH_NO_ACCEPTED_ITEM" in fired
    assert "UNCOVERED_HIGH_PRIORITY_DECISION_AT_CORE" in fired
    assert "NO_SAFE_ITEM_OUTSTANDING_ACROSS_WAVES" in fired
    assert "FAIL_CLOSED_CONCENTRATION" in fired


# --- safe yield and gates ----------------------------------------------------


def accepted_item(**overrides):
    row = {
        "item_id": "ITEM-1",
        "common_core_gates_pass": True,
        "unresolved_critical_facts": [],
        "erroneous_source_value_reached_surface": False,
        "admissibility_verdict": "ADMISSIBLE",
        "independent_verification": "PASS",
        "novelty_verdict": "NOVEL_DECISION",
        "repaired_after_independent_review": False,
        "accepted_only_by_uninformative_gate": False,
    }
    row.update(overrides)
    return row


def test_safe_yield_excludes_repaired_redundant_and_uninformatively_accepted_items():
    result = compute_safe_yield([
        accepted_item(item_id="A"),
        accepted_item(item_id="B", repaired_after_independent_review=True),
        accepted_item(item_id="C", novelty_verdict="REDUNDANT"),
        accepted_item(item_id="D", accepted_only_by_uninformative_gate=True),
        accepted_item(item_id="E", independent_verification="FAIL"),
    ])
    assert result["safe_yield"] == 1
    assert result["accepted_item_ids"] == ["A"]


def test_a_gate_family_with_one_distinct_verdict_is_uninformative():
    variance = monitor_verdict_variance({"ADM_1": ["PASS"] * 10, "ADM_2": ["PASS", "FAIL"]})
    assert variance["verdict_variance"] == "GATE_UNINFORMATIVE"
    assert variance["uninformative_gate_families"] == ["ADM_1"]


def test_a_wave_that_accepted_nothing_fails_however_well_reasoned_its_refusals():
    result = evaluate_gate(
        "G1",
        summary={"attempted_opportunities": 5, "no_safe_item": 5, "fail_closed_by_reason": {}},
        safe_yield={"safe_yield": 0, "accepted_item_ids": [], "excluded_items": []},
        defect_counts_in_accepted={},
        evidence_entailment="PASS",
        verdict_variance={"verdict_variance": "PASS"},
    )
    assert result["result"] == "FAIL"
    assert "SAFE_YIELD_IS_ZERO" in result["failures"]


def test_a_breached_invariant_fails_a_gate_regardless_of_yield():
    result = evaluate_gate(
        "G1",
        summary={"attempted_opportunities": 4, "no_safe_item": 0, "fail_closed_by_reason": {}},
        safe_yield={"safe_yield": 4, "accepted_item_ids": list("ABCD"), "excluded_items": []},
        defect_counts_in_accepted={"NUMERIC_ERRORS": 1},
        evidence_entailment="PASS",
        verdict_variance={"verdict_variance": "PASS"},
    )
    assert result["result"] == "FAIL"
    assert "INVARIANT_BREACHED: NUMERIC_ERRORS" in result["failures"]


def test_a_high_fail_closed_count_with_complete_coverage_passes():
    rows = [
        build_coverage_row(
            address=coverage_address(),
            mcc_objective_id="101",
            declared_learner_decisions=["LD-1", "LD-2"],
            opportunities=[
                opportunity_row("ACCEPTED", "LD-1"),
                opportunity_row(
                    "NO_SAFE_ITEM", "LD-2",
                    fail_closed_reason="FAIL_CLOSED_INSUFFICIENT_EVIDENCE",
                    reopens_on="A_NEW_SOURCE_PACKET",
                ),
            ],
            wave_id="W1",
        )
    ]
    result = evaluate_gate(
        "G1",
        summary={
            "attempted_opportunities": 6,
            "no_safe_item": 4,
            "fail_closed_by_reason": {
                "FAIL_CLOSED_INSUFFICIENT_EVIDENCE": 2,
                "FAIL_CLOSED_INSUFFICIENT_ADMISSIBLE_COMPETITORS": 2,
            },
        },
        safe_yield={"safe_yield": 2, "accepted_item_ids": ["A", "B"], "excluded_items": []},
        defect_counts_in_accepted={},
        evidence_entailment="PASS",
        verdict_variance={"verdict_variance": "PASS"},
        coverage_rows=rows,
    )
    assert result["result"] == "PASS"


def test_fail_closed_concentration_above_sixty_percent_blocks_a_gate():
    result = evaluate_gate(
        "G1",
        summary={
            "attempted_opportunities": 10,
            "no_safe_item": 10,
            "fail_closed_by_reason": {"FAIL_CLOSED_REDUNDANT": 9, "FAIL_CLOSED_INSUFFICIENT_EVIDENCE": 1},
        },
        safe_yield={"safe_yield": 1, "accepted_item_ids": ["A"], "excluded_items": []},
        defect_counts_in_accepted={},
        evidence_entailment="PASS",
        verdict_variance={"verdict_variance": "PASS"},
    )
    assert any(row.startswith("FAIL_CLOSED_CONCENTRATION") for row in result["failures"])


def test_the_stop_rules_fire_and_an_unused_slot_is_not_a_reason_to_continue():
    fired = evaluate_stop_rules(
        high_priority_decisions_settled=True,
        consecutive_redundant=2,
        redundancy_stop_k=2,
        admissible_competitors_remaining=5,
        remaining_needs_new_evidence_for_supporting_only=False,
        remaining_novel_only_on_non_qualifying_context=False,
        opportunities_opened=1,
        maximum_opportunities=30,
    )
    assert "STOP_1_DECISION_COVERAGE" in fired
    assert "STOP_2_REDUNDANCY" in fired
    assert "STOP_6_BUDGET" not in fired


def test_the_yield_rate_is_reported_as_a_diagnostic_and_is_none_without_attempts():
    assert safe_yield_rate({"attempted_opportunities": 0}, {"safe_yield": 0}) is None
    assert safe_yield_rate({"attempted_opportunities": 4}, {"safe_yield": 1}) == 0.25


# --- required regression coverage -------------------------------------------


def test_a_safe_numeric_derivation_is_accepted_rather_than_escalated():
    """Recomputation that agrees is not a reason to fail anything closed."""
    from decimal import Decimal

    from qbank.chapter_staged_generation import compute_derived_value
    from qbank.critical_fact_adjudication import (
        adjudicate_claim,
        load_reference_constants,
        load_source_authority_registry,
    )

    derived = compute_derived_value(
        "ARR",
        [
            {"component": "control_event_rate", "value": "0.20", "units": "proportion"},
            {"component": "experimental_event_rate", "value": "0.15", "units": "proportion"},
        ],
    )
    assert derived == Decimal("0.05")

    record = adjudicate_claim(
        {
            "claim_id": "CLM-DERIVED",
            "statement": (
                "The absolute risk reduction is 5 percent, giving a number needed to "
                "treat of 20 over one year."
            ),
            "verification_status": "VERIFIED_COMPLETE",
            "source_refs": [{"source_id": "SRC-A"}],
            "quantities": [
                {"quantity_id": "ABSOLUTE_RISK_REDUCTION", "value": 5, "unit": "%"}
            ],
        },
        sources={"SRC-A": {"issuing_organization": "Canadian Paediatric Society"}},
        authority_registry=load_source_authority_registry(ROOT),
        constants=load_reference_constants(ROOT),
        profile_risk_classes={},
    )
    assert record["usable_in_generation"] is True
    assert record["fact_status"] == "PRIMARY_AUTHORITY"
    assert record["sanity_findings"] == []


def test_a_narrow_topic_with_two_excellent_items_is_a_complete_safe_yield():
    """Two accepted items covering both declared decisions is a finished topic."""
    from qbank.safe_yield_gates import evaluate_stop_rules

    row = build_coverage_row(
        address=coverage_address(),
        mcc_objective_id="101",
        declared_learner_decisions=["LD-1", "LD-2"],
        opportunities=[
            opportunity_row("ACCEPTED", "LD-1"),
            opportunity_row("ACCEPTED", "LD-2"),
        ],
        wave_id="W1",
    )
    assert row["diagnosis"] == "NARROW_TOPIC"
    assert row["uncovered_learner_decisions"] == []
    fired = evaluate_stop_rules(
        high_priority_decisions_settled=True,
        consecutive_redundant=2,
        redundancy_stop_k=2,
        admissible_competitors_remaining=5,
        remaining_needs_new_evidence_for_supporting_only=False,
        remaining_novel_only_on_non_qualifying_context=False,
        opportunities_opened=2,
        maximum_opportunities=30,
    )
    # A budget of thirty against two accepted items is a complete stop, not a
    # shortfall, and nothing reports the difference.
    assert "STOP_1_DECISION_COVERAGE" in fired
    assert "STOP_2_REDUNDANCY" in fired
    assert "STOP_6_BUDGET" not in fired


def test_a_core_topic_with_no_safe_item_is_not_forced_into_generation():
    row = opened(address=address(priority_class="CORE"))
    row = transition_opportunity(row, "EVIDENCE_READY", decisive_discriminator="D")
    row = transition_opportunity(
        row, "NO_SAFE_ITEM", reason="FAIL_CLOSED_INSUFFICIENT_EVIDENCE"
    )
    assert row["state"] == "NO_SAFE_ITEM"
    assert row["reopens_on"] == "A_NEW_SOURCE_PACKET"
    summary = summarize_opportunities([row])
    assert summary["no_safe_item"] == 1
    coverage = build_coverage_row(
        address=coverage_address(),
        mcc_objective_id="101",
        declared_learner_decisions=["LD-1"],
        opportunities=[
            opportunity_row(
                "NO_SAFE_ITEM", "LD-1",
                fail_closed_reason="FAIL_CLOSED_INSUFFICIENT_EVIDENCE",
                reopens_on="A_NEW_SOURCE_PACKET",
            )
        ],
        wave_id="W1",
    )
    # CORE raises effort and ordering priority; it never lowers a standard, and
    # no gate penalises the fail-closed outcome.
    assert coverage["no_safe_item_gaps"][0]["reason"] == "FAIL_CLOSED_INSUFFICIENT_EVIDENCE"
    result = evaluate_gate(
        "G1",
        summary={"attempted_opportunities": 3, "no_safe_item": 1,
                 "fail_closed_by_reason": {"FAIL_CLOSED_INSUFFICIENT_EVIDENCE": 1}},
        safe_yield={"safe_yield": 2, "accepted_item_ids": ["A", "B"], "excluded_items": []},
        defect_counts_in_accepted={},
        evidence_entailment="PASS",
        verdict_variance={"verdict_variance": "PASS"},
    )
    assert result["result"] == "PASS"
