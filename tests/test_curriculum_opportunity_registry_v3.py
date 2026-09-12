from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

from scripts.qbank.curriculum_opportunity_registry_v3 import (
    RELATION_RANK,
    best_relation,
    build_benchmark_granularity_audit,
    build_benchmark_matcher_calibration,
    build_blueprint_mapping_v2,
    build_copyright_audit,
    build_matcher_regression_diagnosis,
    build_matching_diagnostic_contract,
    build_normalized_benchmark_v2,
    build_gold_relation_review_input,
    build_matcher_v3_validation,
    build_milestone,
    build_semantic_review_exposure,
    build_partial_match_forensics,
    build_complete_partial_classifier,
    build_v1_preservation_audit,
    build_registry_v3,
    calibrate_monotonicity,
    classify_relation_v3,
    build_relation_graph_v3,
    canonical_json,
    content_sha256,
    validate_registry_v3,
    select_benchmark_granularity_sample,
    select_partial_forensic_sample,
)


ROOT = Path(__file__).resolve().parents[1]


def test_best_relation_is_monotonic_when_candidates_are_added():
    before = best_relation(["EQUIVALENT"])
    after = best_relation(["EQUIVALENT", "BENCHMARK_NARROWER", "NONE"])
    assert before == "EQUIVALENT"
    assert after == "EQUIVALENT"
    assert RELATION_RANK[after] >= RELATION_RANK[before]


@pytest.mark.parametrize(
    ("benchmark", "registry", "expected"),
    [
        ({"decision": "Select initial ECG"}, {"decision": "Select initial ECG"}, "EQUIVALENT"),
        ({"decision": "Recognize acute myocardial infarction"}, {"decision": "Diagnose acute myocardial infarction"}, "EQUIVALENT"),
        (
            {"decision": "Select ECG", "decision_components": ["select ECG"]},
            {"decision": "Assess chest pain", "decision_components": ["select ECG", "select troponin"]},
            "REGISTRY_BROADER_CONTAINS_BENCHMARK",
        ),
        (
            {"decision": "Assess chest pain", "decision_components": ["select ECG", "select troponin"]},
            {"decision": "Select ECG", "decision_components": ["select ECG"]},
            "REGISTRY_NARROWER_THAN_BENCHMARK",
        ),
        (
            {"decision": "Diagnose asthma", "variant_group_id": "VG1"},
            {"decision": "Recognize asthma from wheeze", "variant_group_id": "VG1"},
            "VARIANT_OF_SAME_DECISION",
        ),
        (
            {"decision": "Diagnose pneumonia", "study_unit_id": "SU1", "family": "DIAGNOSIS"},
            {"decision": "Diagnose pulmonary embolism", "study_unit_id": "SU1", "family": "DIAGNOSIS"},
            "RELATED_BUT_DISTINCT",
        ),
        (
            {"decision": "Assess suicide plan intent", "response_class": "DIAGNOSIS"},
            {"decision": "Assess suicidal intent plan", "response_class": "DIAGNOSIS"},
            "NEAR_DUPLICATE",
        ),
        (
            {"decision": "Diagnose asthma", "fingerprint": "same"},
            {"decision": "Assess asthma", "fingerprint": "same"},
            "DUPLICATE",
        ),
        ({"decision": "Treat diabetes"}, {"decision": "Counsel smoking cessation"}, "UNRELATED"),
        ({"decision": "Assess"}, {"decision": "Manage"}, "UNCERTAIN"),
    ],
)
def test_matcher_v3_relation_taxonomy(benchmark, registry, expected):
    assert classify_relation_v3(benchmark, registry) == expected


def test_matcher_v3_graph_is_order_independent_and_preserves_many_relations():
    benchmark = [{"id": "B1", "decision": "Select ECG"}]
    registry = [
        {"id": "R2", "decision": "Assess chest pain", "decision_components": ["select ECG", "select troponin"]},
        {"id": "R1", "decision": "Select ECG"},
    ]
    forward = build_relation_graph_v3(benchmark, registry)
    reverse = build_relation_graph_v3(list(reversed(benchmark)), list(reversed(registry)))
    assert forward == reverse
    assert len(forward) == 2
    assert {row["relation"] for row in forward} == {"EQUIVALENT", "REGISTRY_BROADER_CONTAINS_BENCHMARK"}


def test_monotonicity_calibration_detects_missing_preserved_lineage():
    assert calibrate_monotonicity({"B1": {"V1"}}, {"B1": set()}, {"V1": set()}) == ["B1"]
    assert calibrate_monotonicity({"B1": {"V1"}}, {"B1": set()}, {"V1": {"V2"}}) == []


def test_matcher_diagnosis_accounts_for_every_transition_and_preserved_match():
    report = build_matcher_regression_diagnosis(ROOT)
    assert report["v1_full_matches"] == 38
    assert report["v1_full_matches_with_v2_descendants"] == 38
    assert report["v1_full_matches_with_text_identical_v2_descendants"] == 38
    assert report["v1_full_matches_downgraded"] == 33
    assert report["root_cause"] == "ADJUDICATION_CONTRACT_DRIFT_AND_LINKAGE_FAILURE"
    assert sum(report["transition_matrix"].values()) == 675
    assert report["counterfactual_monotonic_v2_full_matches"] >= 38


def test_matching_diagnostic_contract_freezes_both_comparisons_and_reproduces_metrics():
    contract = build_matching_diagnostic_contract(ROOT)
    assert contract["v1_reproduction"]["match_counts"] == {
        "EXACT_MATCH": 0,
        "SEMANTIC_MATCH": 38,
        "PARTIAL_MATCH": 415,
        "MISSING_FROM_V1": 222,
        "INVALID_BENCHMARK_OPPORTUNITY": 0,
    }
    assert contract["v2_reproduction"]["opportunity_recall"] == 0.026667
    assert contract["v2_reproduction"]["opportunity_precision"] == 0.12766
    assert contract["v1_matcher_kind"] == contract["v2_matcher_kind"] == "STATIC_SEMANTIC_REVIEW_PLUS_DETERMINISTIC_AGGREGATION"
    assert all(len(value) == 64 for value in contract["frozen_file_sha256"].values())


def test_v1_preservation_audit_covers_every_v1_row_and_exposes_semantic_changes():
    audit = build_v1_preservation_audit(ROOT)
    assert audit["v1_rows"] == audit["v1_rows_with_v2_descendants"] == 1541
    assert len(audit["rows"]) == 1541
    assert sum(audit["primary_classification_counts"].values()) == 1541
    assert audit["learner_decision_changed"] == 0
    assert audit["key_changed"] == 0
    assert audit["stage_changed"] == 47
    assert audit["normalization_changed"] > 0


def test_calibrated_matcher_reuses_edges_and_uses_one_symmetric_equivalence_graph():
    calibration = build_benchmark_matcher_calibration(ROOT)
    assert calibration["benchmark_rows"] == 675
    assert calibration["inherited_equivalent_benchmark_rows"] == 38
    assert calibration["calibrated_equivalent_benchmark_rows"] >= 38
    assert calibration["monotonicity_regressions"] == 0
    assert calibration["recall_edge_relation"] == calibration["precision_edge_relation"] == "EQUIVALENT"
    assert calibration["topic_support_reported_as_precision"] is False
    assert calibration["multi_equivalence_conflicts"] == 15
    assert calibration["precision_authorized"] is False


def test_partial_forensics_is_exhaustive_and_uses_controlled_classes():
    report = build_partial_match_forensics(ROOT)
    assert len(report["v1_partial_reviews"]) == 415
    assert len(report["v2_partial_reviews"]) == 386
    assert sum(report["v1_forensic_counts"].values()) == 415
    assert sum(report["v2_forensic_counts"].values()) == 386
    assert report["v2_forensic_counts"]["PRESERVED_EQUIVALENCE_CONTRACT_CONFLICT"] == 31
    assert report["all_rows_classified"] is True
    assert report["conclusion"] != "ADD_MORE_ENUMERATION_RULES"


def test_partial_forensic_sample_is_stratified_blind_and_at_least_120():
    sample = select_partial_forensic_sample(ROOT, sample_size=120)
    assert len(sample["pairs"]) == 120
    assert set(row["benchmark"]["discipline"] for row in sample["pairs"]) == {"MED", "PED", "OBGYN", "SURG", "PSY", "PHELO"}
    assert len({row["benchmark"]["opportunity_family"] for row in sample["pairs"]}) >= 12
    assert all("desired" not in canonical_json(row).lower() for row in sample["pairs"])
    assert sample["reviewer_blindness"] == "NO_DESIRED_COUNTS_OR_V2_OUTCOMES"


def test_complete_partial_classifier_uses_reviewed_labels_and_fails_closed_elsewhere():
    report = build_complete_partial_classifier(ROOT)
    assert report["total_partial_relationships"] == 415
    assert report["independently_reviewed"] == 120
    assert report["unreviewed_failed_closed"] == 295
    assert sum(report["relation_counts"].values()) == 415
    assert sum(report["discriminator_class_counts"].values()) == 415
    assert report["relation_counts"]["UNCERTAIN"] >= 295
    assert report["all_rows_classified"] is True
    assert report["id_specific_rules"] is False


def test_benchmark_granularity_audit_conserves_rows_and_clusters():
    audit = build_benchmark_granularity_audit(ROOT)
    assert audit["raw_benchmark_rows"] == 675
    assert sum(audit["granularity_verdict_counts"].values()) == 675
    assert len(audit["row_audits"]) == 675
    assert audit["audited_cluster_count"] is None
    assert audit["audited_opportunity_denominator"] is None
    assert all(row["audit_status"] in {"STRUCTURAL_PASS", "SEMANTIC_REVIEW_REQUIRED"} for row in audit["row_audits"])
    assert audit["granularity_verdict_counts"] == {"UNRESOLVED_GRANULARITY": 675}
    assert all(row["canonical_cluster_id"] is None for row in audit["row_audits"])
    assert audit["benchmark_remains_frozen"] is True
    assert len(audit["possible_variant_pair_reviews"]) > 0
    assert {row["provisional_relation"] for row in audit["possible_variant_pair_reviews"]} <= {
        "EVIDENCE_PATH_VARIANT", "ITEM_VARIANT", "COSMETIC_VARIANT"
    }


def test_benchmark_granularity_sample_is_blind_balanced_and_contains_sibling_context():
    sample = select_benchmark_granularity_sample(ROOT, sample_size=120)
    assert len(sample["opportunities"]) == 120
    assert set(row["benchmark"]["discipline"] for row in sample["opportunities"]) == {"MED", "PED", "OBGYN", "SURG", "PSY", "PHELO"}
    assert all("registry" not in canonical_json(row).lower() for row in sample["opportunities"])
    assert all(row["sibling_benchmark_opportunities"] for row in sample["opportunities"])
    assert sample["reviewer_blindness"] == "BENCHMARK_AND_CURRICULUM_ONLY_REGISTRIES_WITHHELD"


def test_normalized_benchmark_uses_only_reviewed_transformations_and_preserves_provenance():
    normalized = build_normalized_benchmark_v2(ROOT)
    quality = normalized["quality_metrics"]
    assert quality == {
        "original_benchmark_opportunities": 675,
        "atomic_kept": 105,
        "merged_variant_rows": 4,
        "compound_source_rows": 16,
        "compound_splits": 40,
        "excluded": 5,
        "uncertain": 545,
        "final_normalized_atomic_opportunities": 145,
    }
    assert len(normalized["opportunities"]) == 145
    assert all(row["source_benchmark_opportunity_ids"] for row in normalized["opportunities"])
    assert all(row["normalization_evidence"] == "INDEPENDENT_BLINDED_SEMANTIC_REVIEW" for row in normalized["opportunities"])
    represented = {value for row in normalized["opportunities"] for value in row["source_benchmark_opportunity_ids"]}
    assert len(represented) == 125  # 95 kept + 16 compound + 4 variants + 10 reviewed siblings
    assert normalized["evaluation_denominator_authorized"] is True


def test_gold_relation_input_has_24_units_and_keeps_units_out_of_both_partitions():
    packet = build_gold_relation_review_input(ROOT)
    assert len(packet["study_unit_ids"]) == 24
    assert packet["study_units_per_discipline"] == {
        "MED": 4, "OBGYN": 4, "PED": 4, "PHELO": 4, "PSY": 4, "SURG": 4,
    }
    assert set(packet["calibration_study_unit_ids"]).isdisjoint(packet["heldout_study_unit_ids"])
    assert set(packet["calibration_study_unit_ids"]) | set(packet["heldout_study_unit_ids"]) == set(packet["study_unit_ids"])
    assert len(packet["pairs"]) == 171
    assert all(row["candidate_generation"] == "SAME_STUDY_UNIT_COMPLETE_CROSS_PRODUCT" for row in packet["pairs"])


def test_matcher_v3_validation_fails_gate_when_accuracy_and_relation_coverage_are_inadequate():
    report = build_matcher_v3_validation(ROOT)
    assert report["heldout_pairs"] == 86
    assert report["heldout_accuracy"] == 0.023256
    assert report["required_relation_coverage"]["VARIANT_OF_SAME_DECISION"] is False
    assert report["matcher_validation_gate"] == "FAIL"
    assert report["proceed_to_registry_redesign"] is False
    assert sum(sum(row.values()) for row in report["heldout_confusion"].values()) == 86


def test_registry_v3_scaffold_preserves_v2_lineage_and_is_not_canonicalized():
    registry = build_registry_v3(ROOT)
    validate_registry_v3(registry)
    assert registry["canonicalization_authorized"] is False
    assert registry["blocked_by"] == "MATCHER_V3_HELDOUT_VALIDATION_GATE"
    v2 = json.loads((ROOT / "research/qgen/opportunity_registry_v2/curriculum_question_opportunity_registry_v2.json").read_text())
    assert len(registry["opportunities"]) == len(v2["opportunities"]) == 2001
    assert {row["source_v2_opportunity_id"] for row in registry["opportunities"]} == {
        row["opportunity_id"] for row in v2["opportunities"]
    }
    assert all("BOP-" not in canonical_json(row) for row in registry["opportunities"])
    for row in registry["opportunities"]:
        if row["atomicity_status"] != "CANONICAL_ATOMIC":
            assert row["recommended_item_capacity"] == 0
            assert row["generation_readiness"] == "ATOMICITY_REVIEW_REQUIRED"
            assert row["blueprint_mapping_v2"]["allocation_authority"] is False
    assert registry["atomicity_status_counts"] == {"REQUIRES_ATOMICITY_REVIEW": 2001}
    vsd = next(row for row in registry["opportunities"] if "surgical closure" in row["learner_decision"].lower())
    assert vsd["atomicity_status"] == "REQUIRES_ATOMICITY_REVIEW"
    assert vsd["recommended_item_capacity"] == 0


def test_registry_v3_conforms_to_schema():
    registry = build_registry_v3(ROOT)
    schema = json.loads((ROOT / "schemas/curriculum-question-opportunity-v3.schema.json").read_text())
    jsonschema.validate(registry, schema)


def test_registry_v3_validators_enforce_fail_closed_readiness_and_mapping_authority():
    registry = build_registry_v3(ROOT)
    row = registry["opportunities"][0]
    row["generation_readiness"] = "READY_FOR_PRODUCTION"
    row["blueprint_mapping_v2"]["allocation_authority"] = True
    registry["content_sha256"] = content_sha256(registry)
    with pytest.raises((ValueError, jsonschema.ValidationError)):
        validate_registry_v3(registry)


def test_registry_v3_is_reproducible():
    assert canonical_json(build_registry_v3(ROOT)) == canonical_json(build_registry_v3(ROOT))


def test_blueprint_mapping_v2_is_general_fail_closed_and_evaluated_on_holdout():
    mapping = build_blueprint_mapping_v2(ROOT)
    assert mapping["audit_rows"] == 120
    assert mapping["calibration_rows"] + mapping["holdout_rows"] == 120
    assert all("QOP-" not in rule["rule_id"] and "SU-" not in rule["rule_id"] for rule in mapping["rules"])
    assert mapping["calibration"]["dimension_high_confidence_accuracy"] >= 0.8
    assert mapping["calibration"]["activity_high_confidence_accuracy"] >= 0.8
    assert mapping["holdout"]["dimension_high_confidence_accuracy"] >= 0.8
    assert mapping["holdout"]["activity_high_confidence_accuracy"] >= 0.8
    assert mapping["holdout"]["dimension_high_confidence_coverage"] > 0.05
    assert mapping["holdout"]["activity_high_confidence_coverage"] > 0.05
    assert mapping["ambiguous_mapping_policy"] == "REVIEW_REQUIRED_NO_ALLOCATION_AUTHORITY"
    assert all("allowed_secondary_dimensions" in row for row in mapping["sample_assignments"])
    assert all("objective_context_ids" in row for row in mapping["sample_assignments"])


def test_copyright_audit_records_only_lineage_copy_and_new_methodological_prose():
    audit = build_copyright_audit(ROOT)
    assert audit["COPYRIGHT_AUDIT"] == "PASS"
    assert audit["new_clinical_prose_authored"] == 40
    assert audit["new_clinical_prose_kind"] == "INDEPENDENT_CONCISE_ATOMIC_SPLIT_LABELS"
    assert len(audit["normalized_benchmark_v2_sha256"]) == 64
    assert len(audit["matcher_v3_validation_sha256"]) == 64
    assert audit["registry_v2_sha256"] == "d1625711d9efd7db50a47ab54dd90a83de56302108775ecbac31f38afcd309c8"
    assert audit["benchmark_sha256"] == "4d6da8293535244d76361e034dd9b0ad4265c681c960b1e0d3dd281385d2c6e2"


def test_milestone_stops_at_failed_matcher_gate_without_authorizing_registry_or_production():
    milestone = build_milestone(ROOT)
    assert milestone["ATOMIC_OPPORTUNITY_AND_MATCHER_CALIBRATION"] == "BLOCKED"
    assert milestone["MATCHER_V3_HELDOUT_ACCURACY"] == 0.023256
    assert milestone["ENUMERATION_V3_IMPLEMENTED"] is False
    assert milestone["REGISTRY_V3_CANONICALIZED"] is False
    assert milestone["PRODUCTION_PILOT_GATE"] == "FAIL"
    assert milestone["PRODUCTION_QUESTIONS_GENERATED"] == 0
    assert milestone["NEXT_STEP"] == "REFINE_MATCHER_V3"


def test_semantic_review_exposure_links_all_three_reviews_to_study_units():
    exposure = build_semantic_review_exposure(ROOT)
    assert exposure["reviewed_relation_counts"] == {
        "BENCHMARK_GRANULARITY": 120,
        "GOLD_RELATION": 171,
        "PARTIAL_MATCH": 120,
    }
    assert {row["review_kind"] for row in exposure["rows"]} == {
        "BENCHMARK_GRANULARITY", "GOLD_RELATION", "PARTIAL_MATCH",
    }
    assert all(row["study_unit_id"].startswith("SU-") for row in exposure["rows"])
