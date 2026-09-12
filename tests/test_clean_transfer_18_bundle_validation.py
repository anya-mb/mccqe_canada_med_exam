import copy

import pytest

from scripts.qbank.clean_transfer_18_bundle_validation import (
    CleanTransferError,
    build_bundle_cache_v2,
    build_validation_contract,
    classify_density,
    run_zero_topup_replay,
    validate_prerequisite_artifact,
    verify_architecture_freeze,
    verify_untouched_selection,
)


HASHES = {
    "transfer18": "a" * 64,
    "signature_v2": "b" * 64,
    "discovery_v5": "c" * 64,
    "bundle_cache_v1": "d" * 64,
}


def signature(subdomain="LOCALIZED_EAR"):
    return {
        "decision_intent": "IDENTIFY_DIAGNOSIS",
        "target_domain": "PEDIATRIC",
        "clinical_stage": "INITIAL_RECOGNITION",
        "target_subdomain": subdomain,
        "semantic_containment_role": "SPECIFIC_ENTITY",
    }


def opportunity(index=1):
    return {
        "transfer_id": f"T-{index}",
        "discipline": "PED",
        "study_unit_id": f"SU-{index}",
        "study_unit": f"Unit {index}",
        "allocation_address_id": f"SU-{index}",
        "mcc_objective_ids": [str(index)],
        "priority": "CORE",
        "evidence_readiness_at_selection": "CURRENT_REPOSITORY_PACKET_READY",
    }


def prerequisite(index=1):
    return {
        "transfer_id": f"T-{index}",
        "prerequisite_status": "READY",
        "decision_evidence_refs": [f"REF-{index}"],
        "feature_readiness": "READY",
        "learner_decision_family": "LOCALIZED_EAR_DIAGNOSIS",
        "learner_decision": "Identify the diagnosis",
        "key": {"canonical_identity": f"KEY-{index}", "label": "Key"},
        "key_aliases": ["Key"],
        "demanded_response_class": "PLAUSIBLE_DIAGNOSTIC_ENTITY",
        "decision_granularity": "DIAGNOSIS",
        "decision_signature_v2": signature(),
        "applicability_context": "PEDIATRIC",
        "semantic_families": ["LOCALIZED_EAR_DIAGNOSIS"],
        "chapter_code": "P",
    }


def cached_bundle(index=1, alternatives=3):
    return {
        "bundle_id": f"B-{index}",
        "learner_decision_family": "LOCALIZED_EAR_DIAGNOSIS",
        "decision_signature_v2": signature(),
        "target_subdomain": "LOCALIZED_EAR",
        "population_context_restrictions": ["PEDIATRIC"],
        "option_candidates": [
            {"candidate_id": f"C-{index}-{number}"}
            for number in range(alternatives)
        ],
    }


def test_untouched_selection_fails_closed_after_any_prior_run():
    disciplines = [
        "MED", "PED", "OBGYN", "SURG", "PSY", "PHELO"
    ]
    roster = []
    for discipline in disciplines:
        for number in range(3):
            row = opportunity(len(roster) + 1)
            row["discipline"] = discipline
            roster.append(row)
    selection = {
        "cohort_run": False,
        "candidate_retrieval_run": False,
        "cohort_size": 18,
        "per_discipline": {
            "MED": 3, "PED": 3, "OBGYN": 3,
            "SURG": 3, "PSY": 3, "PHELO": 3,
        },
        "cohort_sha256": HASHES["transfer18"],
        "opportunities": roster,
    }
    assert verify_untouched_selection(selection, HASHES["transfer18"])["untouched"] is True
    selection["candidate_retrieval_run"] = True
    with pytest.raises(CleanTransferError, match="previously run"):
        verify_untouched_selection(selection, HASHES["transfer18"])


def test_contract_is_frozen_before_lookup_and_contains_all_load_bearing_rules():
    contract = build_validation_contract(HASHES)
    assert contract["candidate_budget"] == 8
    assert contract["bundle_admission_thresholds"] == {
        "STRONG_BUNDLE": ">=4",
        "MINIMUM_GENERATABLE_BUNDLE": "==3",
        "PARTIAL_BUNDLE": "1-2",
        "NO_SAFE_BUNDLE": "0",
    }
    assert contract["matrix_states"] == ["PRESENT", "ABSENT", "UNKNOWN", "NOT_APPLICABLE"]
    assert contract["one_wave_top_up_rule"]["maximum_waves"] == 1
    assert len(contract["content_sha256"]) == 64


def test_prerequisite_validation_rejects_candidate_supply_leakage():
    selection = {"opportunities": [opportunity(1)]}
    artifact = {"rows": [prerequisite(1)]}
    result = validate_prerequisite_artifact(selection, artifact)
    assert result["ready_count"] == 1
    leaked = copy.deepcopy(artifact)
    leaked["rows"][0]["candidate_pool"] = ["C-1"]
    with pytest.raises(CleanTransferError, match="candidate-supply field"):
        validate_prerequisite_artifact(selection, leaked)


def test_zero_topup_replay_uses_exact_frozen_scope_and_counts_thresholds():
    rows = [prerequisite(1), prerequisite(2)]
    rows[1]["decision_signature_v2"] = signature("OTHER")
    cache = {"bundles": [cached_bundle(1, alternatives=4)]}
    result = run_zero_topup_replay(rows, cache)
    assert result["threshold_counts"] == {"1": 1, "2": 1, "3": 1, "4": 1, "5": 0}
    assert result["contrast_ready"] == 1
    assert result["reuse"]["bundle_reuse"] == 1
    assert result["rows"][1]["alternative_count"] == 0


def test_cache_v2_is_append_only_and_excludes_nonapproved_transfer_bundles():
    parent = {"content_sha256": HASHES["bundle_cache_v1"], "bundles": [cached_bundle(1, 3)]}
    approved = cached_bundle(2, 4)
    approved["bundle_review"] = {"verdict": "APPROVED"}
    rejected = cached_bundle(3, 4)
    rejected["bundle_review"] = {"verdict": "REJECTED"}
    original = copy.deepcopy(parent)
    child = build_bundle_cache_v2(parent, [approved, rejected])
    assert parent == original
    assert child["parent_sha256"] == HASHES["bundle_cache_v1"]
    assert child["new_bundle_count"] == 1
    assert child["new_alternative_count"] == 4
    assert len(child["bundles"]) == 2


def test_density_classification_keeps_exact_three_separate_from_four_plus():
    result = classify_density([0, 1, 2, 3, 4, 5])
    assert result["admission_counts"] == {
        "STRONG_BUNDLE": 2,
        "MINIMUM_GENERATABLE_BUNDLE": 1,
        "PARTIAL_BUNDLE": 2,
        "NO_SAFE_BUNDLE": 1,
    }
    assert result["threshold_counts"] == {"1": 5, "2": 4, "3": 3, "4": 2, "5": 1}


def test_architecture_freeze_detects_any_post_unblinding_drift():
    frozen = {"file_sha256": {"signature": "a", "discovery": "b", "schema": "c"}}
    assert verify_architecture_freeze(frozen, frozen["file_sha256"])["integrity"] == "PASS"
    with pytest.raises(CleanTransferError, match="architecture drift"):
        verify_architecture_freeze(frozen, {"signature": "a", "discovery": "changed", "schema": "c"})
