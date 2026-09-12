from __future__ import annotations

import json
from pathlib import Path

from scripts.qbank.expanded_candidate_milestone import build_milestone


ROOT = Path(__file__).resolve().parents[1]


def test_milestone_preserves_frozen_inputs_and_expands_proposal_universe():
    result = build_milestone(ROOT)
    report = result["report"]
    assert report["starting_head"] == "01eff40984bee76418c7fab82a1ded9fbfa2d9e5"
    assert report["reference_set_sha256"] == "fc0ad21c2d4929b147f888b114ed3171f7795a14cf7961fcfc297ee6e193ff47"
    assert report["feature_evidence_registry_v1_sha256"] == "a297ed7f79613ee6b326dc0e91ae78834a6872f1d9ca99d03b27b932f5e7d660"
    assert report["evidence_backed_bundle_v2_sha256"] == "c8e9aa10353d650679f7f55d3e59cdb924f33c1ff176bd72481f5d0602c9a26d"
    assert report["total_distinct_candidate_proposals"] == 108
    assert report["stage2_approved"] == 60
    assert report["historical_frozen_artifacts_modified"] == 0


def test_model_proposals_are_hypotheses_and_none_enter_approved_bundle_without_evidence():
    result = build_milestone(ROOT)
    model_rows = [
        candidate
        for anchor in result["universe"]["anchors"]
        for candidate in anchor["candidates"]
        if "MODEL_PROPOSED" in candidate["origins"]
    ]
    assert len(model_rows) == 36
    assert sum(row["review_stage_1"]["verdict"] == "PLAUSIBLE" for row in model_rows) == 27
    assert all(row["final_admission_state"] == "REJECTED" for row in model_rows)


def test_universe_density_remains_fail_closed_to_the_sixty_evidence_backed_candidates():
    report = build_milestone(ROOT)["report"]
    assert report["approved_candidate_universe_size"] == {
        "min": 1,
        "median": 4.0,
        "mean": 3.33,
        "max": 4,
    }
    assert report["approved_thresholds"]["3"] == 15
    assert report["approved_thresholds"]["5"] == 0


def test_next_action_context_reuses_existing_evidence_without_inventing_diagnosis_next_steps():
    result = build_milestone(ROOT)
    coverage = result["report"]["next_step_evidence"]
    assert coverage == {"required": 60, "available": 26, "missing": 34, "not_applicable": 0}
    assert result["report"]["new_evidence_requests"] == 0


def test_source_grouping_reuses_authoritative_sources_across_candidate_facts():
    report = build_milestone(ROOT)["report"]
    assert report["sources_reused_across_candidates"] > 0
    assert report["sources_reused_across_anchors"] > 0


def test_question_seed_registry_rejects_deliberate_duplicate_before_admission():
    result = build_milestone(ROOT)
    assert len(result["question_seeds"]["seeds"]) == 18
    assert result["report"]["pregen_duplicate_rejections"] == 1
    assert result["report"]["postgen_near_duplicate_rejections"] == 0
    assert result["report"]["postgen_duplicate_rejections"] == 0


def test_build_is_reproducible_and_output_hashes_validate():
    first = build_milestone(ROOT)
    second = build_milestone(ROOT)
    for name in ("universe", "cards", "graph", "bundles", "question_seeds", "report"):
        assert first[name]["content_sha256"] == second[name]["content_sha256"]


def test_runner_does_not_generate_a_new_transfer_or_new_questions():
    report = build_milestone(ROOT)["report"]
    assert report["development_items_generated"] == 0
    assert report["new_transfer_cohort_size"] == 0
    assert report["ready_for_new_clean_transfer"] == "NO"
