import pytest
from pathlib import Path
import json

from scripts.qbank.clean_transfer_validation_v2 import (
    CleanTransferV2Error,
    build_validation_contract_v2,
    summarize_clean_run,
    validate_clean_run,
)


ROOT = Path(__file__).resolve().parents[1]


def _cohort():
    return {
        "content_sha256": "cohort-hash",
        "rows": [
            {"cohort_row_id": "C1", "study_unit_id": "SU-1", "discipline": "MED"},
            {"cohort_row_id": "C2", "study_unit_id": "SU-2", "discipline": "PED"},
        ],
    }


def _run():
    candidate = {
        "candidate_id": "M1",
        "candidate_concept": "Candidate",
        "origin": "MODEL_PROPOSED",
        "stage1_verdict": "PLAUSIBLE",
        "deterministic_rejected": False,
        "evidence_researched": True,
        "source_ids": ["S1", "S2"],
        "source_status": "MULTI_SOURCE_CONCORDANT",
        "entailment_verdict": "ENTAILED",
        "stage2_verdict": "APPROVED",
        "second_key_risk": False,
        "quality_tier": "TIER_A_STRONG_DISTRACTOR",
        "concept_facts_reused": 1,
        "concept_facts_new": 0,
        "next_action_branches_reused": 1,
        "next_action_branches_new": 0,
    }
    anchors = []
    for row in _cohort()["rows"]:
        anchors.append({
            "cohort_row_id": row["cohort_row_id"],
            "study_unit_id": row["study_unit_id"],
            "discipline": row["discipline"],
            "learner_decision": "Choose the diagnosis",
            "key": "Key",
            "response_class": "DIAGNOSIS",
            "granularity": "DIAGNOSIS",
            "decision_signature": {"decision_intent": "IDENTIFY_DIAGNOSIS"},
            "population": "GENERAL",
            "clinical_stage": "INITIAL_RECOGNITION",
            "target_subdomain": "EXAMPLE",
            "zero_authoring_reuse": {"candidate_ids": [], "concept_fact_ids": [], "next_action_ids": [], "compatibility_edge_ids": [], "bundle_ids": []},
            "discovery_v6_candidates": [],
            "tn_source_first": [],
            "source_candidates": [],
            "model_candidates": [{**candidate, "candidate_id": f"M-{row['cohort_row_id']}"}],
            "saturation_passes": [
                {"pass": 1, "new_proposals": 1, "stage1_plausible": 1, "stage2_approved": 1},
                {"pass": 2, "new_proposals": 0, "stage1_plausible": 0, "stage2_approved": 0},
                {"pass": 3, "new_proposals": 0, "stage1_plausible": 0, "stage2_approved": 0},
            ],
            "compatibility_edges": [],
            "bundle_candidate_ids": [f"M-{row['cohort_row_id']}"],
            "question_seed": None,
            "question": None,
        })
    return {"schema_version": "CLEAN_TRANSFER_V2_CLINICAL_INPUT_V1", "cohort_sha256": "cohort-hash", "sources": [{"source_id": "S1"}, {"source_id": "S2"}], "anchors": anchors}


def test_validation_rejects_approved_candidate_without_entailed_evidence():
    run = _run()
    run["anchors"][0]["model_candidates"][0]["entailment_verdict"] = "PARTIALLY_ENTAILED"
    with pytest.raises(CleanTransferV2Error, match="APPROVED_WITHOUT_ENTAILED_EVIDENCE"):
        validate_clean_run(_cohort(), run)


def test_validation_requires_full_immutable_denominator():
    run = _run()
    run["anchors"].pop()
    with pytest.raises(CleanTransferV2Error, match="ANCHOR_DENOMINATOR_MISMATCH"):
        validate_clean_run(_cohort(), run)


def test_summary_counts_model_results_and_density():
    run = _run()
    validate_clean_run(_cohort(), run)
    summary = summarize_clean_run(run)
    assert summary["model_proposed_clean"]["proposed"] == 2
    assert summary["model_proposed_clean"]["stage2_approved"] == 2
    assert summary["clean_model_approval_rate"] == 1.0
    assert summary["clean_candidate_universe_size"] == {"min": 1, "median": 1.0, "mean": 1.0, "max": 1}
    assert summary["saturation_status"] == "SATURATED"
    assert summary["marginal_stage2_approved_per_pass"] == [2, 0, 0]


def test_contract_requires_independent_cleanliness_pass():
    with pytest.raises(CleanTransferV2Error, match="CLEANLINESS_PROOF_REQUIRED"):
        build_validation_contract_v2(ROOT, _cohort(), {"content_sha256": "registry"}, {"verdict": "FAIL"})


def test_contract_pins_frozen_architecture_hashes():
    cohort = json.loads((ROOT / "research/qgen/exposure/qgen_clean_cohort_selection_v2.json").read_text())
    registry = json.loads((ROOT / "research/qgen/exposure/qgen_exposure_registry_v1_reserved.json").read_text())
    proof = json.loads((ROOT / "reports/qgen_clean_cohort_v2_cleanliness_proof.json").read_text())
    contract = build_validation_contract_v2(ROOT, cohort, registry, proof)
    assert contract["frozen_architecture_content_sha256"]["candidate_role_registry_v1"] == "bfdf744fa25dab55d4e8f297dc5995b1c540ceb62bd824d72f6b5866e1fd3d81"
    assert contract["frozen_architecture_content_sha256"]["catalogue_v3"] == "f9e4f6d299b9c789df53cc8c338f9d2319de4792880d6d33289038b633a3b5df"
    assert contract["frozen_architecture_file_sha256"]["discovery_v6"] == "20ba89b4d5dfc5c58e8f2af431138d2ca7fee6d17fe0d3cd8cdf2f73e97257df"
    assert contract["cohort_sha256"] == cohort["content_sha256"]
    assert contract["cleanliness_proof_sha256"] == proof["content_sha256"]
