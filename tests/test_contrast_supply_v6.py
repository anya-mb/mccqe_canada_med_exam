from collections import Counter
import json
from pathlib import Path

import pytest

from scripts.qbank.contrast_supply_v6 import (
    CANONICAL_RESPONSE_ROLES,
    build_filter_ablation,
    build_role_inventory,
    build_v5_funnel,
    classify_v5_terminal_outcome,
    discover_global_candidates_v6,
    normalize_response_role,
    validate_candidate_role_registry,
)


ROOT = Path(__file__).resolve().parents[1]


def load(relative: str):
    return json.loads((ROOT / relative).read_text())


@pytest.fixture(scope="module")
def catalogue():
    return load("research/qgen/contrast_supply/global_candidate_concept_catalogue_v2.json")["concepts"]


@pytest.fixture(scope="module")
def opportunities():
    return load("research/qgen/contrast_supply/clean_transfer_18_prerequisites_v1.json")["rows"]


@pytest.fixture(scope="module")
def frozen_v5_rows():
    return load("research/qgen/contrast_supply/clean_transfer_18_discovery_v5_wave_v1.json")["rows"]


def test_v5_funnel_reconciles_frozen_transfer18(catalogue, opportunities, frozen_v5_rows):
    result = build_v5_funnel(
        catalogue,
        opportunities,
        candidate_signatures={},
        frozen_observed_rows=frozen_v5_rows,
    )
    assert result["total_evaluations"] == 33_012
    assert sum(result["gate_rejection_counts"].values()) == 33_012
    assert result["gate_rejection_counts"] == {
        "CATALOGUE_IDENTITY": 54,
        "RESPONSE_CLASS": 32_941,
        "DECISION_GRANULARITY": 5,
        "SIGNATURE_V2": 8,
        "TARGET_SUBDOMAIN": 0,
        "APPLICABILITY_CONTEXT": 0,
        "SEMANTIC_CONTAINMENT": 0,
        "KEY_OR_ALIAS": 4,
        "RANKING_OR_BUDGET": 0,
        "ACCEPTED_TO_CANDIDATE_POOL": 0,
        "OTHER": 0,
    }
    assert len(result["per_anchor"]) == 18
    assert all(row["terminal_evaluations"] == 1_834 for row in result["per_anchor"])
    assert result["current_code_replay_matches_frozen"] is False
    assert result["current_code_replay_gate_rejection_counts"]["RESPONSE_CLASS"] == 32_606


def test_v5_terminal_outcome_uses_real_gate_order():
    opportunity = {
        "demanded_response_class": "PLAUSIBLE_DIAGNOSTIC_ENTITY",
        "decision_granularity": "DIAGNOSIS",
        "decision_signature_v2": {
            "decision_intent": "IDENTIFY_DIAGNOSIS",
            "target_domain": "PEDIATRIC",
            "clinical_stage": "INITIAL_RECOGNITION",
            "target_subdomain": "LOCALIZED_EAR",
            "semantic_containment_role": "SPECIFIC_ENTITY",
        },
        "applicability_context": "PEDIATRIC",
        "key_aliases": ["Acute otitis media"],
    }
    generic = {
        "canonical_candidate_id": "GENERIC",
        "normalized_label": "Diagnosis",
        "generic_concept": True,
        "response_classes": ["LOCALIZED_INFLAMMATION"],
    }
    assert classify_v5_terminal_outcome(generic, opportunity, {}) == "CATALOGUE_IDENTITY"
    key = {**generic, "canonical_candidate_id": "KEY", "normalized_label": "Acute otitis media", "generic_concept": False}
    assert classify_v5_terminal_outcome(key, opportunity, {}) == "KEY_OR_ALIAS"


def test_filter_ablation_is_monotonic_and_reconciled(catalogue, opportunities):
    result = build_filter_ablation(catalogue, opportunities, candidate_signatures={})
    assert len(result["rows"]) == 18
    for row in result["rows"]:
        counts = [row[stage] for stage in result["stages"]]
        assert counts == sorted(counts, reverse=True)
        assert counts[0] == 1_834


def test_catalogue_role_inventory_accounts_for_every_concept(catalogue):
    result = build_role_inventory(catalogue)
    assert result["concept_count"] == 1_834
    assert result["single_role"] == 90
    assert result["multi_role"] == 0
    assert result["untyped"] == 1_744
    assert result["ambiguous"] == 0
    assert sum(result[name] for name in ("single_role", "multi_role", "untyped", "ambiguous")) == 1_834


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("PLAUSIBLE_DIAGNOSTIC_ENTITY", "DIAGNOSIS"),
        ("DIAGNOSTIC_ADVANCEMENT", "INVESTIGATION"),
        ("NEXT_ACTION_FOR_CURRENT_CARE", "MANAGEMENT_ACTION"),
        ("MANAGEMENT_STRATEGY_FOR_PRESENTATION", "MANAGEMENT_ACTION"),
        ("ETHICAL_ACTION", "ETHICAL_LEGAL_ACTION"),
        ("LEGAL_DUTY_ACTION", "ETHICAL_LEGAL_ACTION"),
        ("DIAGNOSTIC_TEST", "INVESTIGATION"),
        ("THERAPY", "MANAGEMENT_ACTION"),
    ],
)
def test_response_role_aliases_normalize_deterministically(value, expected):
    assert normalize_response_role(value) == expected


def test_role_registry_validates_multi_role_and_fails_closed_on_unknown():
    registry = {
        "schema_version": "CANDIDATE_ROLE_REGISTRY_V1",
        "controlled_roles": sorted(CANONICAL_RESPONSE_ROLES),
        "entries": [
            {
                "candidate_id": "C1",
                "roles": ["INVESTIGATION", "MANAGEMENT_ACTION"],
                "role_provenance": [{"source": "EXPLICIT_MEDICAL_SEMANTIC_REVIEW"}],
                "scope": "GLOBAL",
                "review_status": "APPROVED",
            },
            {
                "candidate_id": "C2",
                "roles": [],
                "role_provenance": [],
                "scope": "GLOBAL",
                "review_status": "UNTYPED_FAIL_CLOSED",
            },
        ],
    }
    result = validate_candidate_role_registry(registry)
    assert result["C1"] == frozenset({"INVESTIGATION", "MANAGEMENT_ACTION"})
    assert result["C2"] == frozenset()
    with pytest.raises(ValueError, match="unknown response role"):
        validate_candidate_role_registry({**registry, "entries": [{**registry["entries"][0], "roles": ["ANCHOR_123_ONLY"]}]})


def test_discovery_v6_accepts_registered_role_and_rejects_wrong_role():
    signature = {
        "decision_intent": "IDENTIFY_DIAGNOSIS",
        "target_domain": "DERMATOLOGY",
        "clinical_stage": "INITIAL_RECOGNITION",
        "target_subdomain": "CUTANEOUS_INFESTATION",
        "semantic_containment_role": "SPECIFIC_ENTITY",
    }
    opportunity = {
        "transfer_id": "BENCHMARK-1",
        "study_unit_id": "SU-D-29",
        "chapter_code": "D",
        "demanded_response_class": "PLAUSIBLE_DIAGNOSTIC_ENTITY",
        "decision_granularity": "DIAGNOSIS",
        "decision_signature_v2": signature,
        "applicability_context": "ADULT_GENERAL",
        "key_aliases": ["Scabies"],
        "semantic_families": ["CUTANEOUS_INFESTATION_DIAGNOSIS"],
    }
    catalogue = [
        {"canonical_candidate_id": "ATOPIC", "normalized_label": "Atopic dermatitis", "aliases": [], "response_classes": [], "decision_granularities": ["DIAGNOSIS"]},
        {"canonical_candidate_id": "TEST", "normalized_label": "Skin scraping", "aliases": [], "response_classes": [], "decision_granularities": ["DIAGNOSTIC_TEST"]},
    ]
    registry = validate_candidate_role_registry({
        "schema_version": "CANDIDATE_ROLE_REGISTRY_V1",
        "controlled_roles": sorted(CANONICAL_RESPONSE_ROLES),
        "entries": [
            {"candidate_id": "ATOPIC", "roles": ["DIAGNOSIS"], "role_provenance": [{"source": "STRUCTURAL_HEADING_CONTEXT"}], "scope": "GLOBAL", "review_status": "APPROVED"},
            {"candidate_id": "TEST", "roles": ["INVESTIGATION"], "role_provenance": [{"source": "STRUCTURAL_HEADING_CONTEXT"}], "scope": "GLOBAL", "review_status": "APPROVED"},
        ],
    })
    metadata = {
        "ATOPIC": {"decision_granularities": ["DIAGNOSIS"], "decision_signatures_v2": [signature], "applicability_contexts": ["ADULT_GENERAL"]},
        "TEST": {"decision_granularities": ["DIAGNOSTIC_TEST"], "decision_signatures_v2": [signature], "applicability_contexts": ["ADULT_GENERAL"]},
    }
    result = discover_global_candidates_v6(catalogue, opportunity=opportunity, role_registry=registry, candidate_metadata=metadata, budget=8)
    assert [row["canonical_candidate_id"] for row in result["candidates"]] == ["ATOPIC"]
    assert Counter(row["reason"] for row in result["rejections"])["WRONG_RESPONSE_ROLE"] == 1


def test_discovery_v6_has_no_opportunity_specific_whitelist():
    source = (ROOT / "scripts/qbank/contrast_supply_v6.py").read_text()
    assert "NEW-T18-" not in source
    assert "REFERENCE-" not in source


def test_milestone_builder_has_all_18_reference_anchors():
    from scripts.qbank.run_contrast_supply_v6 import build_milestone

    result = build_milestone(ROOT, write_outputs=False)
    assert result["status"]["transfer18_status"] == "EX_CLEAN_TRANSFER_NOW_DEVELOPMENT_DIAGNOSTIC"
    assert len(result["reference_set"]["anchors"]) == 18
    assert sum(len(row["option_candidates"]) for row in result["reference_set"]["anchors"]) >= 54
    assert result["funnel"]["total_evaluations"] == 33_012
    assert result["role_registry_review"]["verdict"] == "APPROVED"
    assert result["discovery_v6"]["waves_per_anchor"] == 1
    assert result["discovery_v6"]["repeat_search_performed"] is False
    verdicts = Counter(row["verdict"] for row in result["reference_review"]["rows"])
    assert verdicts == {"APPROVED_REFERENCE": 60, "REJECTED": 10, "UNCERTAIN": 2}
    admissions = Counter(row["admission"] for row in result["pairwise"]["rows"])
    assert admissions == {"REFERENCE_STRONG": 10, "REFERENCE_MINIMUM": 5, "REFERENCE_PARTIAL": 3}
    assert len(result["v5_failure"]["rows"]) == 60
    assert sum(result["v5_failure"]["counts"].values()) == 60
    assert len(result["features"]["features"]) == 180
    assert len({row["reference_candidate_id"] for row in result["features"]["features"]}) == 60


@pytest.mark.parametrize(
    ("candidate_id", "demanded", "granularity", "context", "signature"),
    [
        ("CONCEPT-V6-AOM-OME", "PLAUSIBLE_DIAGNOSTIC_ENTITY", "DIAGNOSIS", "PEDIATRIC", {"decision_intent": "IDENTIFY_DIAGNOSIS", "target_domain": "PEDIATRIC", "clinical_stage": "INITIAL_RECOGNITION", "target_subdomain": "LOCALIZED_EAR", "semantic_containment_role": "SPECIFIC_ENTITY"}),
        ("RDY-PED-04__hba1c_diagnostic_criteria", "DIAGNOSTIC_ADVANCEMENT", "SINGLE_NEXT_ACTION", "PEDIATRIC", {"decision_intent": "SELECT_DIAGNOSTIC_ACTION", "target_domain": "ENDOCRINE_METABOLIC", "clinical_stage": "DIAGNOSTIC_WORKUP", "target_subdomain": "PEDIATRIC_METABOLIC", "semantic_containment_role": "SPECIFIC_ACTION"}),
        ("RDY-SURG-03__tte", "DIAGNOSTIC_ADVANCEMENT", "DIAGNOSTIC_TEST", "ADULT_GENERAL", {"decision_intent": "SELECT_DIAGNOSTIC_ACTION", "target_domain": "CARDIOPULMONARY", "clinical_stage": "DIAGNOSTIC_WORKUP", "target_subdomain": "ACUTE_CARDIOPULMONARY", "semantic_containment_role": "SPECIFIC_ACTION"}),
        ("CONCEPT-R4-SU-R-05-CXR", "DIAGNOSTIC_ADVANCEMENT", "DIAGNOSTIC_TEST", "PEDIATRIC", {"decision_intent": "SELECT_DIAGNOSTIC_ACTION", "target_domain": "PEDIATRIC", "clinical_stage": "DIAGNOSTIC_WORKUP", "target_subdomain": "PEDIATRIC_ACUTE_RESPIRATORY", "semantic_containment_role": "SPECIFIC_ACTION"}),
    ],
)
def test_v6_preserves_named_historical_positive_controls(candidate_id, demanded, granularity, context, signature, catalogue):
    candidate = next(row for row in catalogue if row["canonical_candidate_id"] == candidate_id)
    role = normalize_response_role(demanded)
    opportunity = {"opportunity_id": "HISTORICAL-CONTROL", "study_unit_id": "CONTROL", "chapter_code": "CONTROL", "demanded_response_class": demanded, "decision_granularity": granularity, "decision_signature_v2": signature, "applicability_context": context, "key_aliases": [], "semantic_families": []}
    result = discover_global_candidates_v6([candidate], opportunity=opportunity, role_registry={candidate_id: frozenset({role})}, candidate_metadata={candidate_id: {"decision_granularities": [granularity], "decision_signatures_v2": [signature], "applicability_contexts": [context]}}, budget=8)
    assert [row["canonical_candidate_id"] for row in result["candidates"]] == [candidate_id]


def test_v6_rejects_wrong_signature_and_containment(catalogue):
    candidate = next(row for row in catalogue if row["canonical_candidate_id"] == "CONCEPT-V6-AOM-OME")
    signature = {"decision_intent": "IDENTIFY_DIAGNOSIS", "target_domain": "PEDIATRIC", "clinical_stage": "INITIAL_RECOGNITION", "target_subdomain": "LOCALIZED_EAR", "semantic_containment_role": "SPECIFIC_ENTITY"}
    opportunity = {"opportunity_id": "NEGATIVE", "demanded_response_class": "PLAUSIBLE_DIAGNOSTIC_ENTITY", "decision_granularity": "DIAGNOSIS", "decision_signature_v2": signature, "applicability_context": "PEDIATRIC", "key_aliases": [], "semantic_families": []}
    wrong = {**signature, "target_subdomain": "PEDIATRIC_ACUTE_RESPIRATORY"}
    result = discover_global_candidates_v6([candidate], opportunity=opportunity, role_registry={candidate["canonical_candidate_id"]: frozenset({"DIAGNOSIS"})}, candidate_metadata={candidate["canonical_candidate_id"]: {"decision_granularities": ["DIAGNOSIS"], "decision_signatures_v2": [wrong], "applicability_contexts": ["PEDIATRIC"]}})
    assert result["rejection_counts"] == {"SIGNATURE_V2": 1}
    result = discover_global_candidates_v6([candidate], opportunity=opportunity, role_registry={candidate["canonical_candidate_id"]: frozenset({"DIAGNOSIS"})}, candidate_metadata={candidate["canonical_candidate_id"]: {"decision_granularities": ["DIAGNOSIS"], "decision_signatures_v2": [signature], "applicability_contexts": ["PEDIATRIC"], "contains_candidate_ids": ["CHILD"]}})
    assert result["rejection_counts"] == {"SEMANTIC_CONTAINMENT": 1}


def test_final_report_reconciles_metrics_and_refuses_new_clean_transfer():
    from scripts.qbank.run_contrast_supply_v6 import build_final_report, build_milestone

    result = build_milestone(ROOT, write_outputs=False)
    report = build_final_report(
        ROOT,
        result,
        focused={"passed": 21, "failed": 0},
        full_suite={"passed": 1803, "failed": 1, "known_preexisting_failures": 1, "new_test_failures": 0},
        copyright_status="PASS",
    )
    assert report["reference_option_candidates_approved"] == 60
    assert sum(report["reference_v5_failure_attribution"].values()) == 60
    assert report["root_cause"] == "MULTIPLE_COMPARABLE_CAUSES"
    assert report["ready_for_new_clean_transfer"] is False
    assert report["next_step"] == "IMPROVE_FEATURE_EVIDENCE_PIPELINE"
