import copy
from collections import Counter
from pathlib import Path

import pytest

from scripts.qbank.fresh_holdout_18 import (
    HoldoutIntegrityError,
    build_architecture_freeze,
    build_milestone_report,
    build_stage_artifacts,
    select_fresh_holdout_18,
    validate_evidence_records,
    validate_feature_reviews,
    verify_freeze_integrity,
)


ROOT = Path(__file__).resolve().parents[1]


EXPECTED_UNITS = {
    "MED": ["SU-A-03", "SU-A-15", "SU-C-03"],
    "PED": ["SU-P-002", "SU-P-004", "SU-P-009"],
    "OBGYN": ["SU-GY-05", "SU-GY-07", "SU-GY-12"],
    "SURG": ["SU-GS-02", "SU-GS-04", "SU-GS-06"],
    "PSY": ["SU-PS-01", "SU-PS-02", "SU-PS-05"],
    "PHELO": ["SU-ELOM-21", "SU-PH-03", "SU-PH-04"],
}


def test_selection_freezes_three_per_discipline_without_contrast_signals():
    """Catches an outcome-aware selector or a discipline-imbalanced roster."""
    roster = select_fresh_holdout_18(ROOT)
    rows = roster["opportunities"]

    assert len(rows) == 18
    assert Counter(row["discipline"] for row in rows) == {
        "MED": 3,
        "PED": 3,
        "OBGYN": 3,
        "SURG": 3,
        "PSY": 3,
        "PHELO": 3,
    }
    assert {
        discipline: [
            row["study_unit_id"]
            for row in rows
            if row["discipline"] == discipline
        ]
        for discipline in EXPECTED_UNITS
    } == EXPECTED_UNITS
    forbidden = {"seed", "candidate", "contrast", "retrieval", "yield"}
    assert not any(
        any(token in key.lower() for token in forbidden)
        for row in rows
        for key in row
    )


def test_selection_has_complete_freshness_signatures_and_three_frozen_waves():
    """Catches opportunity-ID-only freshness checks and mutable wave assignment."""
    roster = select_fresh_holdout_18(ROOT)
    rows = roster["opportunities"]

    for field in (
        "opportunity_id",
        "study_unit_id",
        "allocation_address_id",
        "learner_decision_id",
        "learner_decision_signature",
        "key_concept_or_action",
    ):
        values = [row[field] for row in rows]
        assert all(values)
        assert len(values) == len(set(values))

    waves = roster["waves"]
    assert [len(wave["opportunity_ids"]) for wave in waves] == [6, 6, 6]
    by_id = {row["opportunity_id"]: row for row in rows}
    for wave_number, wave in enumerate(waves, start=1):
        assert wave["wave"] == wave_number
        assert Counter(by_id[value]["discipline"] for value in wave["opportunity_ids"]) == {
            discipline: 1 for discipline in EXPECTED_UNITS
        }


def test_selection_revalidates_all_historical_freshness_dimensions():
    """Catches reuse hidden behind a newly minted opportunity identifier."""
    roster = select_fresh_holdout_18(ROOT)
    rows = roster["opportunities"]
    assert roster["freshness_revalidation"] == {
        "study_unit_overlap": 0,
        "allocation_address_overlap": 0,
        "learner_decision_signature_overlap": 0,
        "key_concept_or_action_overlap": 0,
    }
    assert all(row["historical_use_status"] == "FRESH_STUDY_UNIT" for row in rows)


def test_architecture_freeze_detects_manifest_or_roster_drift():
    """Catches continuing a holdout after a pinned architecture input changes."""
    roster = select_fresh_holdout_18(ROOT)
    freeze = build_architecture_freeze(ROOT, roster)
    receipt = verify_freeze_integrity(ROOT, roster, freeze)
    assert receipt["verdict"] == "PASS"
    assert receipt["architecture_changed_after_freeze"] is False
    assert len(freeze["artifact_pins"]) >= 8

    changed = copy.deepcopy(freeze)
    changed["artifact_pins"]["generation_lifecycle"]["file_sha256"] = "0" * 64
    with pytest.raises(HoldoutIntegrityError, match="ARCHITECTURE_HASH_DRIFT"):
        verify_freeze_integrity(ROOT, roster, changed)


def test_evidence_gate_is_exhaustive_and_only_ready_rows_proceed():
    """Catches SOURCE_PACKET_READY being treated as decision entailment."""
    roster = {"opportunities": [
        {"opportunity_id": "A"},
        {"opportunity_id": "B"},
    ]}
    evidence = {"rows": [
        {
            "opportunity_id": "A",
            "verdict": "EVIDENCE_READY",
            "exact_relevant_claims": [{"claim_id": "C1", "statement": "Exact."}],
            "content_sha256": "a" * 64,
        },
        {
            "opportunity_id": "B",
            "verdict": "ALIGNED_PARTIAL",
            "exact_relevant_claims": [],
            "reason": "The packet does not entail the frozen decision.",
        },
    ]}
    receipt = validate_evidence_records(roster, evidence)
    assert receipt == {"EVIDENCE_READY": 1, "ALIGNED_PARTIAL": 1}

    evidence["rows"][1]["verdict"] = "SOURCE_PACKET_READY"
    with pytest.raises(HoldoutIntegrityError, match="INVALID_EVIDENCE_VERDICT"):
        validate_evidence_records(roster, evidence)


def test_feature_review_gate_requires_registered_features_and_independence():
    """Catches an approved map that bypasses frozen vocabulary or review identity."""
    evidence_ready = {"A"}
    feature_maps = {"rows": [{
        "opportunity_id": "A",
        "author_id": "author",
        "map_content_sha256": "b" * 64,
        "features": [{"feature_id": "F1", "state": "UNKNOWN"}],
    }]}
    reviews = {"rows": [{
        "opportunity_id": "A",
        "reviewer_id": "reviewer",
        "reviewed_map_sha256": "b" * 64,
        "verdict": "APPROVED",
        "map_reason": "Sufficient.",
        "feature_reviews": [{"feature_id": "F1", "verdict": "APPROVED", "reason": "Grounded."}],
    }]}
    assert validate_feature_reviews(
        evidence_ready, feature_maps, reviews, registered_feature_ids={"F1"}
    ) == {"APPROVED": 1}

    reviews["rows"][0]["reviewer_id"] = "author"
    with pytest.raises(HoldoutIntegrityError, match="NONINDEPENDENT_FEATURE_REVIEW"):
        validate_feature_reviews(
            evidence_ready, feature_maps, reviews, registered_feature_ids={"F1"}
        )

    reviews["rows"][0]["reviewer_id"] = "reviewer"
    with pytest.raises(HoldoutIntegrityError, match="UNREGISTERED_FEATURE"):
        validate_feature_reviews(
            evidence_ready, feature_maps, reviews, registered_feature_ids=set()
        )


def test_fail_closed_milestone_accounting_uses_earliest_failure_only():
    """Catches invented downstream yield after evidence or feature failure."""
    report = build_milestone_report(ROOT)
    assert report["metrics"] == {
        "frozen": 18,
        "evidence_ready": 3,
        "feature_ready": 0,
        "existing_seed_baseline_ready": 0,
        "post_new_seed_contrast_ready": 0,
        "blueprint_ready": 0,
        "generator_callbacks": 0,
        "stems_generated": 0,
        "post_stem_live": 0,
        "final_reviewed": 0,
        "accepted": 0,
        "rejected": 0,
        "no_safe_item": 18,
    }
    assert report["failure_counts"] == {
        "EVIDENCE_NOT_READY": 15,
        "FEATURE_MAP_REJECTED": 3,
    }
    assert sum(report["failure_counts"].values()) == 18
    assert report["lifecycle_invariant"] == "PASS"
    assert report["holdout_contaminated"] is False


def test_wave_and_discipline_rollups_reconcile_to_the_frozen_roster():
    """Catches reporting rows that disagree with terminal opportunity states."""
    report = build_milestone_report(ROOT)
    assert report["waves"] == [
        {"wave": 1, "attempted": 6, "evidence_ready": 2, "feature_ready": 0, "contrast_ready": 0, "generated": 0, "accepted": 0},
        {"wave": 2, "attempted": 6, "evidence_ready": 0, "feature_ready": 0, "contrast_ready": 0, "generated": 0, "accepted": 0},
        {"wave": 3, "attempted": 6, "evidence_ready": 1, "feature_ready": 0, "contrast_ready": 0, "generated": 0, "accepted": 0},
    ]
    assert all(row["frozen"] == 3 for row in report["results_by_discipline"].values())
    assert sum(row["no_safe"] for row in report["results_by_discipline"].values()) == 18
    assert report["holdout_assessment"] == "BLOCKED_BY_EVIDENCE"
    assert report["next_step"] == "RESOLVE_BLOCKER"


def test_downstream_artifacts_are_explicitly_empty_after_feature_gate():
    """Catches a provisional seed, contrast, blueprint, or stem leaking forward."""
    artifacts = build_stage_artifacts(ROOT)
    assert artifacts["existing_seed_baseline"]["eligible_opportunity_ids"] == []
    assert artifacts["bounded_discovery"]["raw_candidates"] == []
    assert artifacts["seed_independent_review"]["rows"] == []
    assert artifacts["contrast_sets"]["contrast_sets"] == []
    assert artifacts["blueprints"]["blueprints"] == []
    assert artifacts["stems"]["stems"] == []
    assert artifacts["final_medical_review"]["rows"] == []
    assert sum(
        row["generator_callback_count"]
        for row in artifacts["lifecycle_trace"]["opportunities"]
    ) == 0


def test_integrity_and_economics_are_reported_without_invented_costs():
    """Catches omitted integrity pins or fabricated token/dollar economics."""
    report = build_milestone_report(ROOT)
    assert report["historical_frozen_artifacts_modified"] == 0
    assert report["commits_created"] == 0
    assert report["claude_md_changed"] is False
    assert report["copyright"]["COPYRIGHT_AUDIT"] == "PASS"
    assert report["copyright"]["longest_verbatim_toronto_notes_run_words"] == 0
    assert report["results_by_difficulty"] == {
        "EASY": {"frozen": 6, "generated": 0, "accepted": 0, "independent_structural_difficulty_agreement": "NOT_ASSESSED_NO_STEMS"},
        "MEDIUM": {"frozen": 6, "generated": 0, "accepted": 0, "independent_structural_difficulty_agreement": "NOT_ASSESSED_NO_STEMS"},
        "HARD": {"frozen": 6, "generated": 0, "accepted": 0, "independent_structural_difficulty_agreement": "NOT_ASSESSED_NO_STEMS"},
    }
    assert "token" not in report["review_economics"]
    assert "dollar" not in report["review_economics"]
