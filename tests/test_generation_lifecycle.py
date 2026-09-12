from __future__ import annotations

from copy import deepcopy

import pytest

from scripts.qbank.generation_lifecycle import (
    GenerationPreconditionError,
    assert_generation_ready,
    execute_generation,
    validate_lifecycle_transition,
)
from scripts.qbank.holdout_contamination_repair import (
    build_aom_generation_context,
    build_diagnosis_report,
    build_lifecycle_trace,
    build_next_holdout_inventory,
    build_regression_replay,
    recompute_canonical_metrics,
    validate_terminal_accounting,
)
from scripts.qbank.seed_proposal_contract import validate_seed_proposal_pre_review


ROOT = __import__("pathlib").Path(__file__).resolve().parents[1]


APPROVED = "INDEPENDENT_REVIEW_APPROVED"


def _reviewed(name: str) -> dict:
    return {
        "state": APPROVED,
        "frozen": True,
        "content_sha256": f"sha-{name}",
        "pinned_sha256": f"sha-{name}",
        "author_id": f"author-{name}",
        "reviewer_id": f"reviewer-{name}",
    }


def _ready_context() -> dict:
    competitors = []
    for index in range(3):
        competitors.append({
            "seed_id": f"SEED-{index}",
            "viable": True,
            "seed": _reviewed(f"seed-{index}"),
            "relation": _reviewed(f"relation-{index}"),
            "anchor": {**_reviewed(f"anchor-{index}"), "supports_candidate": True},
        })
    return {
        "opportunity_id": "OPP-1",
        "evidence": _reviewed("evidence"),
        "feature_map": _reviewed("feature-map"),
        "profile_snapshot": {
            **_reviewed("profile"),
            "state": "FROZEN",
        },
        "key": {"state": "FROZEN", "concept_id": "KEY-1"},
        "competitors": competitors,
        "contrast_set": {
            "state": "FROZEN",
            "content_sha256": "sha-contrast",
            "pinned_sha256": "sha-contrast",
            "coherence": "PASS",
            "second_key_risk": False,
        },
        "blueprint": {
            "state": "BLUEPRINT_READY",
            "content_sha256": "sha-blueprint",
            "pinned_sha256": "sha-blueprint",
        },
    }


@pytest.mark.parametrize(
    ("state", "reason"),
    [
        ("DRAFT", "UNAPPROVED_FEATURE_MAP"),
        ("INDEPENDENT_REVIEW_REJECTED", "REJECTED_FEATURE_MAP"),
        ("INDEPENDENT_REVIEW_UNCERTAIN", "UNCERTAIN_FEATURE_MAP"),
    ],
)
def test_unapproved_rejected_or_uncertain_feature_map_cannot_generate(state, reason):
    context = _ready_context()
    context["feature_map"]["state"] = state
    calls = []

    with pytest.raises(GenerationPreconditionError, match=reason):
        execute_generation(context, lambda: calls.append("generated"))

    assert calls == []


@pytest.mark.parametrize(
    ("state", "reason"),
    [
        ("PROPOSED", "UNAPPROVED_SEED"),
        ("INDEPENDENT_REVIEW_REJECTED", "REJECTED_SEED"),
        ("INDEPENDENT_REVIEW_UNCERTAIN", "UNCERTAIN_SEED"),
    ],
)
def test_unapproved_rejected_or_uncertain_seed_cannot_generate(state, reason):
    context = _ready_context()
    context["competitors"][0]["seed"]["state"] = state
    calls = []

    with pytest.raises(GenerationPreconditionError, match=reason):
        execute_generation(context, lambda: calls.append("generated"))

    assert calls == []


def test_unapproved_anchor_cannot_generate():
    context = _ready_context()
    context["competitors"][0]["anchor"]["state"] = "PROPOSED"

    with pytest.raises(GenerationPreconditionError, match="UNAPPROVED_ANCHOR"):
        execute_generation(context, lambda: pytest.fail("generator executed"))


def test_backwards_anchor_cannot_generate():
    context = _ready_context()
    context["competitors"][0]["anchor"]["supports_candidate"] = False

    with pytest.raises(GenerationPreconditionError, match="BACKWARDS_ANCHOR"):
        execute_generation(context, lambda: pytest.fail("generator executed"))


def test_two_approved_competitors_cannot_generate():
    context = _ready_context()
    context["competitors"] = context["competitors"][:2]

    with pytest.raises(GenerationPreconditionError, match="FEWER_THAN_THREE"):
        execute_generation(context, lambda: pytest.fail("generator executed"))


def test_unfrozen_contrast_set_cannot_generate():
    context = _ready_context()
    context["contrast_set"]["state"] = "CONTRAST_READY"

    with pytest.raises(GenerationPreconditionError, match="UNFROZEN_CONTRAST_SET"):
        execute_generation(context, lambda: pytest.fail("generator executed"))


def test_second_key_risk_cannot_generate():
    context = _ready_context()
    context["contrast_set"]["second_key_risk"] = True

    with pytest.raises(GenerationPreconditionError, match="SECOND_KEY_RISK"):
        execute_generation(context, lambda: pytest.fail("generator executed"))


def test_ready_context_executes_generator_once_and_returns_gate_receipt():
    calls = []
    context = _ready_context()

    result = execute_generation(context, lambda: calls.append("generated") or "ITEM")

    assert calls == ["generated"]
    assert result["generated"] == "ITEM"
    assert result["precondition"]["verdict"] == "PASS"
    assert result["precondition"] == assert_generation_ready(deepcopy(context))


def test_canonical_reporting_never_counts_physical_drafts_as_generated():
    report = build_diagnosis_report(ROOT)

    assert report["original_reported_metrics"] == {
        "feature_maps_approved": 0,
        "seeds_approved": 0,
        "contrast_ready": 0,
        "stems_generated": 12,
    }
    assert report["recomputed_canonical_metrics"] == {
        "feature_maps_approved": 0,
        "seeds_approved": 0,
        "contrast_ready": 0,
        "stems_generated": 0,
    }
    assert report["generated_12_forensic_classification"] == {
        "VALID_GENERATION_PATH": 0,
        "PREMATURE_GENERATION": 12,
        "DIAGNOSTIC_DRAFT_MISCOUNTED_AS_GENERATED": 0,
        "REPORTING_ERROR": 0,
        "OTHER": 0,
    }


def test_lifecycle_trace_reconstructs_all_24_and_preserves_the_physical_12():
    trace = build_lifecycle_trace(ROOT)

    assert trace["classification"] == "CONTAMINATED_DEVELOPMENT_REGRESSION_SET"
    assert len(trace["opportunities"]) == 24
    assert sum(row["historical_physical_stem_exists"] for row in trace["opportunities"]) == 12
    assert all(row["canonical_generation_precondition"] == "FAIL" for row in trace["opportunities"])
    assert all(
        row["historical_generation_classification"] == "PREMATURE_GENERATION"
        for row in trace["opportunities"]
        if row["historical_physical_stem_exists"]
    )


def test_regression_replay_accounting_is_exhaustive_and_lifecycle_ordered():
    replay = build_regression_replay(ROOT)

    assert replay["metrics"] == {
        "attempted": 24,
        "feature_ready": 0,
        "seed_ready": 0,
        "contrast_ready": 0,
        "stems_generated": 0,
        "final_reviewed": 0,
        "accepted": 0,
        "rejected": 0,
        "no_safe_item": 24,
    }
    assert replay["lifecycle_invariant"] == "PASS"
    assert replay["metrics"]["stems_generated"] <= replay["metrics"]["contrast_ready"]
    assert replay["metrics"]["contrast_ready"] <= replay["metrics"]["feature_ready"]
    assert replay["metrics"]["accepted"] + replay["metrics"]["rejected"] + replay["metrics"]["no_safe_item"] == 24
    assert not any(
        row["contrast_ready"] is False and row["stem_generated"] is True
        for row in replay["opportunities"]
    )


def test_reporting_counts_only_final_approvals_frozen_contrasts_and_gate_receipts():
    metrics = recompute_canonical_metrics(
        feature_reviews=[
            {"state": "PROPOSED"},
            {"state": APPROVED},
            {"state": "INDEPENDENT_REVIEW_REJECTED"},
        ],
        seed_reviews=[
            {"state": "PROPOSED"},
            {"state": APPROVED},
            {"state": "INDEPENDENT_REVIEW_UNCERTAIN"},
        ],
        contrast_sets=[
            {"state": "CONTRAST_READY", "coherence": "PASS", "second_key_risk": False},
            {"state": "FROZEN", "coherence": "PASS", "second_key_risk": False},
            {"state": "FROZEN", "coherence": "FAIL", "second_key_risk": False},
        ],
        generation_receipts=[
            {"precondition": {"verdict": "PASS"}, "generator_executed": True},
            {"precondition": {"verdict": "FAIL"}, "generator_executed": True},
            {"precondition": {"verdict": "PASS"}, "generator_executed": False},
        ],
    )

    assert metrics == {
        "feature_maps_approved": 1,
        "seeds_approved": 1,
        "contrast_ready": 1,
        "stems_generated": 1,
    }


def test_terminal_accounting_rejects_overlap_or_missing_opportunities():
    with pytest.raises(ValueError, match="exactly one terminal state"):
        validate_terminal_accounting(
            attempted_ids={"A", "B"},
            accepted_ids={"A"},
            rejected_ids={"A"},
            no_safe_item_ids={"B"},
        )


def test_pre_review_filter_catches_only_structural_contract_failures():
    proposal = {
        "candidate_concept_id": "KEY-1",
        "key_concept_id": "KEY-1",
        "response_class": "DIAGNOSIS",
        "required_response_class": "DIAGNOSIS",
        "decision_granularity": "DIAGNOSIS",
        "required_decision_granularity": "DIAGNOSIS",
        "positive_candidate_anchor": {"feature_id": "F-1", "evidence_refs": ["C-1"]},
        "inferiority_discriminator": {"feature_id": "F-2", "evidence_refs": ["C-2"]},
        "evidence_entailment": {"verdict": "CLAIMED", "evidence_refs": ["C-1", "C-2"]},
        "population_scope": {"study_unit_ids": ["SU-1"]},
        "second_key_analysis": {"status": "NO_SECOND_KEY_IDENTIFIED"},
    }
    with pytest.raises(ValueError, match="DUPLICATE_OR_ALIAS"):
        validate_seed_proposal_pre_review(proposal)

    valid = deepcopy(proposal)
    valid["candidate_concept_id"] = "CANDIDATE-1"
    assert validate_seed_proposal_pre_review(valid)["verdict"] == "PASS_TO_SEMANTIC_REVIEW"


@pytest.mark.parametrize(
    ("field", "value", "reason"),
    [
        ("response_class", "MANAGEMENT", "WRONG_RESPONSE_CLASS"),
        ("decision_granularity", "MANAGEMENT_STRATEGY", "WRONG_GRANULARITY"),
        ("positive_candidate_anchor", None, "MISSING_POSITIVE_CANDIDATE_ANCHOR"),
        ("inferiority_discriminator", None, "MISSING_INFERIORITY_DISCRIMINATOR"),
        ("evidence_entailment", None, "MISSING_EVIDENCE_ENTAILMENT"),
        ("population_scope", None, "MISSING_POPULATION_SCOPE"),
        ("second_key_analysis", None, "MISSING_SECOND_KEY_ANALYSIS"),
    ],
)
def test_pre_review_contract_requires_author_fields_used_by_reviewer(field, value, reason):
    proposal = {
        "candidate_concept_id": "CANDIDATE-1",
        "key_concept_id": "KEY-1",
        "response_class": "DIAGNOSIS",
        "required_response_class": "DIAGNOSIS",
        "decision_granularity": "DIAGNOSIS",
        "required_decision_granularity": "DIAGNOSIS",
        "positive_candidate_anchor": {"feature_id": "F-1", "evidence_refs": ["C-1"]},
        "inferiority_discriminator": {"feature_id": "F-2", "evidence_refs": ["C-2"]},
        "evidence_entailment": {"verdict": "CLAIMED", "evidence_refs": ["C-1", "C-2"]},
        "population_scope": {"study_unit_ids": ["SU-1"]},
        "second_key_analysis": {"status": "NO_SECOND_KEY_IDENTIFIED"},
    }
    proposal[field] = value

    with pytest.raises(ValueError, match=reason):
        validate_seed_proposal_pre_review(proposal)


def test_next_holdout_inventory_is_eligibility_only_and_unconsumed():
    inventory = build_next_holdout_inventory(ROOT)

    assert inventory["recommended_n"] == 18
    assert inventory["selected_opportunity_ids"] == []
    assert inventory["holdout_consumed"] is False
    assert inventory["clinical_artifacts_inspected_for_selection"] is False
    assert len(inventory["eligible_candidates"]) > 18


def test_aom_development_control_passes_centralized_generation_precondition():
    receipt = assert_generation_ready(build_aom_generation_context(ROOT))

    assert receipt["verdict"] == "PASS"
    assert receipt["approved_competitor_count"] == 3
    assert receipt["opportunity_id"] == "LD-ONB2-PED-AOM-DX"


def test_lifecycle_state_machine_rejects_skipping_independent_review():
    assert validate_lifecycle_transition("PROPOSED", APPROVED) == APPROVED
    with pytest.raises(GenerationPreconditionError, match="INVALID_LIFECYCLE_TRANSITION"):
        validate_lifecycle_transition("DRAFT", "FROZEN")


def test_seed_taxonomy_fails_closed_when_review_reasons_were_not_serialized():
    report = build_diagnosis_report(ROOT)

    assert sum(report["seed_rejection_taxonomy"].values()) == 48
    assert report["seed_rejection_taxonomy"]["DUPLICATE_OR_ALIAS"] == 12
    assert report["seed_rejection_taxonomy"]["INSUFFICIENT_INFORMATION"] == 36
    assert report["rejections_now_catchable_pre_review"] == 12
    assert report["semantic_review_reduction_percent"] == pytest.approx(26.7)


def test_aom_development_control_passes_the_same_central_precondition():
    receipt = assert_generation_ready(build_aom_generation_context(ROOT))

    assert receipt["verdict"] == "PASS"
    assert receipt["approved_competitor_count"] == 3


def test_next_holdout_inventory_is_eligibility_only_and_selects_nothing():
    inventory = build_next_holdout_inventory(ROOT)
    serialized = __import__("json").dumps(inventory).casefold()

    assert inventory["classification"] == "UNCONSUMED_FRESH_HOLDOUT_ELIGIBILITY_INVENTORY"
    assert inventory["selected_opportunity_ids"] == []
    assert inventory["holdout_consumed"] is False
    assert len(inventory["eligible_candidates"]) >= 18
    assert "seed_ids" not in serialized
    assert "retrieval" not in serialized
