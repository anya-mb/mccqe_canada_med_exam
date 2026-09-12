from __future__ import annotations

import copy
from pathlib import Path

import pytest

from scripts.qbank.clean_transfer_18_model_validation import (
    EXPECTED_TRANSFER18_SHA256,
    CleanTransfer18ModelValidationError,
    build_validation_contract,
    build_blocked_report,
    require_clean_cohort,
    verify_clean_cohort,
    verify_frozen_contract,
    write_preflight_artifacts,
)


ROOT = Path(__file__).resolve().parents[1]


def test_contract_freezes_complete_semantic_architecture_before_unblinding():
    contract = build_validation_contract(ROOT)
    assert contract["schema_version"] == "CLEAN_TRANSFER18_VALIDATION_CONTRACT_V1"
    assert contract["transfer18_sha256"] == EXPECTED_TRANSFER18_SHA256
    assert contract["frozen_before_candidate_supply_inspection"] is True
    assert contract["semantic_concurrency"] == 1
    assert contract["question_generation_policy"] == {
        "maximum_questions": 18,
        "maximum_initial_questions_per_anchor": 1,
        "attempts_per_seed": 1,
        "retries": 0,
        "post_generation_candidate_discovery": False,
    }
    assert contract["saturation_policy"] == {
        "stop_rule": "TWO_CONSECUTIVE_BOUNDED_PASSES_ZERO_NEW_POTENTIALLY_ADMISSIBLE",
        "all_proposals_require_terminal_stage2_before_pass_completion": True,
        "hard_review_ceiling_per_anchor": 24,
    }
    required = {
        "schemas/anchor-candidate-universe-v1.schema.json",
        "schemas/concept-feature-card-v1.schema.json",
        "schemas/candidate-compatibility-graph-v1.schema.json",
        "schemas/clinical-contrast-bundle-v1.schema.json",
        "schemas/question-seed-v1.schema.json",
        "scripts/qbank/candidate_universe.py",
        "scripts/qbank/contrast_supply_v6.py",
        "scripts/qbank/candidate_evidence_v2.py",
        "scripts/qbank/question_seed.py",
        "research/qgen/contrast_supply/anchor_candidate_universe_v2.json",
        "research/qgen/contrast_supply/global_candidate_concept_catalogue_v3.json",
        "research/qgen/contrast_supply/candidate_role_registry_v1.json",
        "research/qgen/contrast_supply/concept_feature_library_v2.json",
        "research/qgen/contrast_supply/conditional_next_action_v1.json",
        "research/qgen/contrast_supply/candidate_compatibility_graph_v2.json",
        "research/qgen/contrast_supply/clinical_contrast_bundles_v4_expanded.json",
        "research/qgen/contrast_supply/question_seed_v1.json",
    }
    assert required <= set(contract["semantic_input_sha256"])
    assert all(len(value) == 64 for value in contract["semantic_input_sha256"].values())
    assert len(contract["content_sha256"]) == 64


def test_cleanliness_proof_fails_closed_on_prior_cohort_overlap():
    contract = build_validation_contract(ROOT)
    proof = verify_clean_cohort(ROOT, contract)
    assert proof["transfer18_sha256"] == EXPECTED_TRANSFER18_SHA256
    assert proof["exact_roster_verified"] is True
    assert proof["cohort_size"] == 18
    assert proof["per_discipline"] == {
        "MED": 3,
        "PED": 3,
        "OBGYN": 3,
        "SURG": 3,
        "PSY": 3,
        "PHELO": 3,
    }
    assert proof["overlapping_study_unit_count"] == 18
    assert proof["material_prior_inspection_found"] is True
    assert proof["candidate_density_used_for_selection"] is False
    assert proof["transfer18_untouched_verified"] is False
    assert proof["transfer18_contaminated"] is True
    with pytest.raises(CleanTransfer18ModelValidationError, match="contaminated"):
        require_clean_cohort(proof)


def test_cleanliness_fails_closed_if_selection_was_consumed():
    contract = build_validation_contract(ROOT)
    selection = copy.deepcopy(contract["selection_metadata_snapshot"])
    selection["holdout_consumed"] = True
    with pytest.raises(CleanTransfer18ModelValidationError, match="already consumed"):
        verify_clean_cohort(ROOT, contract, selection_override=selection)


def test_frozen_contract_rejects_any_semantic_input_drift():
    contract = build_validation_contract(ROOT)
    assert verify_frozen_contract(ROOT, contract)["architecture_freeze_integrity"] == "PASS"
    changed = dict(contract["semantic_input_sha256"])
    changed["scripts/qbank/question_seed.py"] = "0" * 64
    with pytest.raises(CleanTransfer18ModelValidationError, match="semantic architecture drift"):
        verify_frozen_contract(ROOT, contract, expected_hashes_override=changed)


def test_contamination_preflight_writes_reproducible_contract_proof_and_blocked_report(tmp_path):
    first = write_preflight_artifacts(ROOT, output_root=tmp_path)
    second = write_preflight_artifacts(ROOT, output_root=tmp_path)
    assert first == second
    assert first["contract"]["content_sha256"] == second["contract"]["content_sha256"]
    assert first["proof"]["overlapping_study_unit_count"] == 18
    assert first["report"] == build_blocked_report(first["contract"], first["proof"])
    assert first["report"]["milestone_status"] == "BLOCKED"
    assert first["report"]["hard_stop_condition"] == "A_TRANSFER18_ALREADY_MATERIALLY_CONTAMINATED"
    assert first["report"]["candidate_supply_inspected"] is False
    assert first["report"]["copyright_audit"] == "PASS"
    assert first["report"]["copyright_scope"] == "PREFLIGHT_ARTIFACTS_ONLY"
    assert (tmp_path / "research/qgen/contrast_supply/clean_transfer18_validation_contract_v1.json").is_file()
    assert (tmp_path / "reports/qgen_clean_transfer18_cleanliness_proof.json").is_file()
    assert (tmp_path / "reports/qgen_clean_transfer18_model_expansion_validation.json").is_file()
