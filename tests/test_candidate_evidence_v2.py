from __future__ import annotations

from collections import Counter
import json
from pathlib import Path

import pytest

from scripts.qbank.candidate_evidence_v2 import (
    CandidateEvidenceV2Error,
    build_milestone,
    scope_compatible,
)


ROOT = Path(__file__).resolve().parents[1]


def test_frozen_model_cohort_has_exact_backlog_membership_and_terminal_reviews():
    result = build_milestone(ROOT)
    assert len(result["cohort"]["rows"]) == 27
    assert result["pre_screen"]["counts"] == {
        "eligible_for_research": 21,
        "deterministic_reject": 6,
        "uncertain": 0,
    }
    assert result["stage2"]["counts"] == {
        "approved": 19,
        "rejected": 8,
        "uncertain": 0,
    }
    assert all(row["verdict"] in {"APPROVED", "REJECTED"} for row in result["stage2"]["rows"])


def test_review_input_fails_closed_if_a_backlog_member_is_missing(tmp_path):
    inputs = json.loads((ROOT / "research/qgen/contrast_supply/model_candidate_review_inputs_v1.json").read_text())
    inputs["rows"].pop()
    path = tmp_path / "review.json"
    path.write_text(json.dumps(inputs))
    with pytest.raises(CandidateEvidenceV2Error, match="exactly match"):
        build_milestone(ROOT, review_input_path=path)


def test_multi_origin_provenance_retains_model_and_existing_routes_without_double_counting():
    result = build_milestone(ROOT)
    rows = result["provenance"]["candidates"]
    assert len({row["candidate_occurrence_id"] for row in rows}) == len(rows)
    dermatitis = next(
        row for row in rows
        if row["anchor_id"] == "NEW-T18-MED-02" and row["candidate_label"] == "Dermatitis herpetiformis"
    )
    assert "MODEL_PROPOSED" in dermatitis["all_origins"]
    assert "EXISTING_BUNDLE_DERIVED" in dermatitis["all_origins"]


def test_scope_compatibility_fails_closed_on_unknown_or_mismatched_dimensions():
    fact_scope = {"population": ["ADULT_GENERAL"], "stage": ["INITIAL_RECOGNITION"], "severity": ["ANY"], "setting": ["ANY"]}
    assert scope_compatible(fact_scope, {"population": "ADULT_GENERAL", "stage": "INITIAL_RECOGNITION", "severity": "MILD", "setting": "OUTPATIENT"})
    assert not scope_compatible(fact_scope, {"population": "UNKNOWN", "stage": "INITIAL_RECOGNITION", "severity": "MILD", "setting": "OUTPATIENT"})
    assert not scope_compatible(fact_scope, {"population": "PEDIATRIC", "stage": "INITIAL_RECOGNITION", "severity": "MILD", "setting": "OUTPATIENT"})


def test_concept_library_has_entailed_load_bearing_facts_and_safe_reuse():
    result = build_milestone(ROOT)
    library = result["concept_library"]
    assert all(fact["entailment_verdict"] == "ENTAILED" for fact in library["facts"])
    assert result["report"]["evidence_reuse_v2"]["concept_facts_reused_across_anchors"] > 0
    assert result["report"]["evidence_reuse_v2"]["concept_facts_reused_across_candidates"] > 0


def test_v2_universe_is_additive_and_bundles_preserve_all_approved_reserves():
    result = build_milestone(ROOT)
    v1 = json.loads((ROOT / "research/qgen/contrast_supply/anchor_candidate_universe_v1.json").read_text())
    assert result["universe_v2"]["parent_content_sha256"] == v1["content_sha256"]
    assert sum(row["review_stage_2"]["verdict"] == "APPROVED" for anchor in result["universe_v2"]["anchors"] for row in anchor["candidates"]) == 79
    for bundle in result["bundles_v4"]["bundles"]:
        assert bundle["approved_candidate_count"] == len(bundle["approved_candidate_ids"])
        assert bundle["reserves_preserved"] is True


def test_question_seed_runs_end_to_end_and_duplicate_controls_precede_generation():
    result = build_milestone(ROOT)
    report = result["report"]
    assert report["question_seed_end_to_end"] == "PASS"
    assert report["development_seeds_generated"] >= 6
    assert report["development_items_generated"] == 6
    assert report["development_items_accepted"] == 6
    assert report["pregen_duplicates_rejected"] >= 1
    assert report["same_topic_distinct_item_pairs"] >= 1
    assert report["same_topic_duplicate_item_pairs"] == 0
    assert report["postgen_near_duplicates_rejected"] == 0
    assert report["postgen_duplicates_rejected"] == 0
    assert not ({row["anchor_id"] for row in result["development_items"]["questions"]} & {
        "NEW-T18-MED-01", "NEW-T18-MED-03", "NEW-T18-PED-01", "NEW-T18-PED-02",
        "NEW-T18-OBGYN-01", "NEW-T18-OBGYN-03", "NEW-T18-SURG-02", "NEW-T18-SURG-03",
        "NEW-T18-PSY-01", "NEW-T18-PSY-02",
    })
    for item in result["development_items"]["questions"]:
        assert len(item["rationale"]["distractors"]) == 3
        for rationale in item["rationale"]["distractors"]:
            assert rationale["why_plausible"]
            assert rationale["why_inferior"]
            assert rationale["what_would_make_correct"]
            assert rationale["evidence_fact_ids"]
            assert rationale["conditional_next_actions"]
    assert all(row["selected_candidate_ids"] for row in result["development_seeds"]["admitted_seeds"])


def test_milestone_is_reproducible_and_freezes_but_does_not_run_transfer_cohort():
    first = build_milestone(ROOT)
    second = build_milestone(ROOT)
    for name in (
        "cohort", "pre_screen", "provenance", "evidence_packets", "stage2",
        "concept_library", "next_actions", "universe_v2", "graph_v2",
        "bundles_v4", "development_seeds", "development_items", "transfer_cohort", "report",
    ):
        assert first[name]["content_sha256"] == second[name]["content_sha256"]
    assert first["report"]["new_transfer_cohort_size"] == 18
    assert first["transfer_cohort"]["execution_status"] == "FROZEN_NOT_RUN"
    assert Counter(row["discipline"] for row in first["transfer_cohort"]["rows"]) == {
        "MED": 3, "PED": 3, "OBGYN": 3, "SURG": 3, "PSY": 3, "PHELO": 3,
    }
