import copy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from scripts.qbank.contrast_supply_v5 import (
    BundleValidationError,
    build_contrast_bundle_cache_v1,
    classify_bundle_admission,
    discover_global_candidates_v5,
    lookup_contrast_bundle,
    signatures_v2_compatible,
    validate_contrast_bundle_v1,
    validate_decision_signature_v2,
)


VOCABULARIES = {
    "decision_intent": ["IDENTIFY_DIAGNOSIS", "SELECT_DIAGNOSTIC_ACTION"],
    "target_domain": ["MENTAL_HEALTH", "CARDIOPULMONARY"],
    "clinical_stage": ["INITIAL_RECOGNITION", "DIAGNOSTIC_WORKUP"],
    "target_subdomain": ["PRIMARY_PSYCHOTIC_DISORDERS", "MOOD_DISORDERS", "PLEURAL_AIR"],
    "semantic_containment_role": ["SPECIFIC_ENTITY", "ENTITY_FAMILY", "SPECIFIC_ACTION"],
}


def signature(**changes):
    value = {
        "decision_intent": "IDENTIFY_DIAGNOSIS",
        "target_domain": "MENTAL_HEALTH",
        "clinical_stage": "INITIAL_RECOGNITION",
        "target_subdomain": "PRIMARY_PSYCHOTIC_DISORDERS",
        "semantic_containment_role": "SPECIFIC_ENTITY",
    }
    value.update(changes)
    return value


def candidate(candidate_id, label, *, signature_, contexts=("ADULT_GENERAL",), classes=("PLAUSIBLE_DIAGNOSTIC_ENTITY",), granularities=("DIAGNOSIS",), generic=False):
    return {
        "canonical_candidate_id": candidate_id,
        "normalized_label": label,
        "response_classes": list(classes),
        "decision_granularities": list(granularities),
        "study_unit_ids": ["SU-X"],
        "chapters": ["X"],
        "semantic_families": ["FAMILY"],
        "decision_signature_v2": signature_,
        "applicability_contexts": list(contexts),
        "generic_concept": generic,
    }


def opportunity(**changes):
    value = {
        "development_id": "DEV-1",
        "study_unit_id": "SU-X",
        "chapter_code": "X",
        "demanded_response_class": "PLAUSIBLE_DIAGNOSTIC_ENTITY",
        "decision_granularity": "DIAGNOSIS",
        "key_aliases": ["schizophrenia"],
        "semantic_families": ["FAMILY"],
        "applicability_context": "ADULT_GENERAL",
        "decision_signature_v2": signature(),
    }
    value.update(changes)
    return value


def test_signature_v2_requires_small_five_dimension_contract():
    assert validate_decision_signature_v2(signature(), VOCABULARIES) == signature()
    for field in signature():
        invalid = signature()
        invalid.pop(field)
        with pytest.raises(ValueError, match=field):
            validate_decision_signature_v2(invalid, VOCABULARIES)


def test_signature_v2_rejects_wrong_target_subdomain_and_preserves_cross_chapter_peer():
    assert signatures_v2_compatible(signature(), signature())["compatible"] is True
    result = signatures_v2_compatible(
        signature(), signature(target_subdomain="MOOD_DISORDERS")
    )
    assert result == {"compatible": False, "reason": "WRONG_TARGET_SUBDOMAIN"}


def test_signature_v2_rejects_parent_or_subtype_containment_mismatch():
    result = signatures_v2_compatible(
        signature(semantic_containment_role="SPECIFIC_ACTION"),
        signature(semantic_containment_role="ENTITY_FAMILY"),
    )
    assert result == {"compatible": False, "reason": "SEMANTIC_CONTAINMENT_MISMATCH"}


def test_discovery_v5_rejects_wrong_applicability_and_generic_concepts():
    catalogue = [
        candidate("GOOD", "Schizophreniform disorder", signature_=signature()),
        candidate("WRONG-CONTEXT", "Childhood disorder", signature_=signature(), contexts=("PEDIATRIC",)),
        candidate("GENERIC", "Disease", signature_=signature(), generic=True),
    ]
    result = discover_global_candidates_v5(catalogue, opportunity=opportunity(), budget=8)
    assert [row["canonical_candidate_id"] for row in result["candidates"]] == ["GOOD"]
    assert result["rejection_counts"]["WRONG_APPLICABILITY_CONTEXT"] == 1
    assert result["rejection_counts"]["GENERIC_CONCEPT"] == 1


def test_discovery_v5_preserves_global_source_and_four_candidate_supply():
    catalogue = [
        candidate(f"C-{index}", f"Candidate {index}", signature_=signature())
        for index in range(5)
    ]
    catalogue[3]["study_unit_ids"] = ["SU-OTHER"]
    catalogue[3]["chapters"] = ["OTHER"]
    result = discover_global_candidates_v5(catalogue, opportunity=opportunity(), budget=8)
    assert len(result["candidates"]) == 5
    assert any(row["cross_chapter"] for row in result["candidates"])
    assert result["global_catalogue_rows_scanned"] == 5


def feature(feature_id, *, key="PRESENT", candidate_state="PRESENT", tags=None, visibility="STEM_ELIGIBLE"):
    return {
        "feature_id": feature_id,
        "category": "history",
        "normalized_proposition": feature_id.replace("-", " "),
        "type_tags": tags or ["SHARED_PLAUSIBILITY"],
        "visibility": visibility,
        "evidence_refs": ["REF-1"],
        "states": {"KEY": key, "CAND-1": candidate_state},
    }


def valid_bundle():
    return {
        "schema_version": "CLINICAL_CONTRAST_BUNDLE_V1",
        "bundle_id": "BUNDLE-1",
        "learner_decision_family": "FAMILY-1",
        "opportunity_ids": ["DEV-1"],
        "key": {"canonical_identity": "KEY-1", "label": "Key"},
        "response_class": "PLAUSIBLE_DIAGNOSTIC_ENTITY",
        "decision_granularity": "DIAGNOSIS",
        "decision_signature_v2": signature(),
        "population_context_restrictions": ["ADULT_GENERAL"],
        "clinical_stage": "INITIAL_RECOGNITION",
        "target_domain": "MENTAL_HEALTH",
        "target_subdomain": "PRIMARY_PSYCHOTIC_DISORDERS",
        "clinical_state_entities": ["KEY-1", "CAND-1"],
        "evidence": [{"ref_id": "REF-1", "source_title": "Authoritative source", "url": "https://example.test/source", "authority": "AUTHORITATIVE", "verification_status": "VERIFIED"}],
        "option_candidates": [{
            "candidate_id": "CAND-1",
            "canonical_identity": "CAND-1",
            "label": "Candidate",
            "response_class": "PLAUSIBLE_DIAGNOSTIC_ENTITY",
            "granularity": "DIAGNOSIS",
            "decision_signature_v2": signature(),
            "applicability_context": "ADULT_GENERAL",
            "positive_candidate_anchor_ids": ["F-SHARED"],
            "shared_plausibility_feature_ids": ["F-SHARED"],
            "candidate_supporting_feature_ids": ["F-SHARED"],
            "key_vs_candidate_discriminator_ids": ["F-INFERIOR"],
            "candidate_vs_other_candidate_discriminator_ids": [],
            "high_discriminative_feature_ids": ["F-INFERIOR"],
            "action_changing_feature_ids": [],
            "features_making_candidate_correct": ["F-CORRECT"],
            "features_making_candidate_inferior": ["F-INFERIOR"],
            "second_key_risks": [],
            "containment_parent_subtype_risks": [],
            "next_step_if_correct": "Use the candidate-specific pathway.",
            "evidence_refs": ["REF-1"],
            "review_status": "APPROVED_FOR_BUNDLE",
        }],
        "feature_matrix": [
            feature("F-SHARED"),
            feature("F-INFERIOR", key="PRESENT", candidate_state="ABSENT", tags=["PAIRWISE_DISCRIMINATOR", "HIGH_DISCRIMINATIVE"]),
            feature("F-CORRECT", key="ABSENT", candidate_state="PRESENT", tags=["CANDIDATE_SUPPORTING", "ACTION_CHANGING"], visibility="RATIONALE_ONLY"),
        ],
        "pairwise_review": [],
        "bundle_review": {"verdict": "APPROVED", "coherent_option_class": "PASS", "granularity_consistency": "PASS", "candidate_diversity": "PASS", "no_second_keys": "PASS", "educational_usefulness": "PASS"},
    }


def test_bundle_requires_positive_anchor_and_inferiority_discriminator():
    assert validate_contrast_bundle_v1(valid_bundle())["bundle_id"] == "BUNDLE-1"
    for field in ("positive_candidate_anchor_ids", "features_making_candidate_inferior"):
        invalid = valid_bundle()
        invalid["option_candidates"][0][field] = []
        with pytest.raises(BundleValidationError, match=field):
            validate_contrast_bundle_v1(invalid)


def test_bundle_never_infers_absent_from_missing_matrix_cell():
    invalid = valid_bundle()
    del invalid["feature_matrix"][0]["states"]["CAND-1"]
    with pytest.raises(BundleValidationError, match="matrix state"):
        validate_contrast_bundle_v1(invalid)


def test_bundle_rejects_response_class_mismatch_and_unreviewed_candidate():
    invalid = valid_bundle()
    invalid["option_candidates"][0]["response_class"] = "PHARMACOLOGIC_ACTION"
    with pytest.raises(BundleValidationError, match="response class"):
        validate_contrast_bundle_v1(invalid)
    invalid = valid_bundle()
    invalid["option_candidates"][0]["review_status"] = "UNCERTAIN"
    with pytest.raises(BundleValidationError, match="review_status"):
        validate_contrast_bundle_v1(invalid)


@pytest.mark.parametrize("count,expected", [(0, "NO_SAFE_BUNDLE"), (1, "PARTIAL_BUNDLE"), (2, "PARTIAL_BUNDLE"), (3, "MINIMUM_GENERATABLE_BUNDLE"), (4, "STRONG_BUNDLE"), (6, "STRONG_BUNDLE")])
def test_bundle_admission_arithmetic(count, expected):
    assert classify_bundle_admission(count) == expected


def test_bundle_cache_is_context_scoped_and_excludes_nonapproved_bundle():
    approved = valid_bundle()
    cache = build_contrast_bundle_cache_v1([approved])
    hit = lookup_contrast_bundle(
        cache,
        learner_decision_family="FAMILY-1",
        decision_signature_v2=signature(),
        target_subdomain="PRIMARY_PSYCHOTIC_DISORDERS",
        applicability_context="ADULT_GENERAL",
    )
    assert hit["bundle_id"] == "BUNDLE-1"
    assert lookup_contrast_bundle(
        cache,
        learner_decision_family="FAMILY-1",
        decision_signature_v2=signature(),
        target_subdomain="PRIMARY_PSYCHOTIC_DISORDERS",
        applicability_context="PEDIATRIC",
    ) is None
    rejected = copy.deepcopy(approved)
    rejected["bundle_id"] = "BUNDLE-2"
    rejected["bundle_review"]["verdict"] = "REJECTED"
    cache = build_contrast_bundle_cache_v1([approved, rejected])
    assert cache["bundle_count"] == 1


def test_clinical_contrast_bundle_v1_json_schema_accepts_contract():
    schema_path = Path("schemas/clinical-contrast-bundle-v1.schema.json")
    schema = json.loads(schema_path.read_text())
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(valid_bundle())


def test_repository_v2_benchmark_preserves_positives_and_rejects_hard_negatives():
    benchmark = json.loads(Path("research/qgen/contrast_supply/decision_signature_v2_compatibility_benchmark.json").read_text())
    assert benchmark["positive_pair_count"] >= 80
    assert benchmark["hard_negative_count"] == 6
    assert benchmark["positive_recall"] == 1.0
    assert benchmark["hard_negative_rejection_rate"] == 1.0


def test_repository_signature_v2_preserves_v1_dimensions_and_is_not_opportunity_specific():
    v1 = json.loads(Path("research/qgen/contrast_supply/decision_signature_v1.json").read_text())
    v2 = json.loads(Path("research/qgen/contrast_supply/decision_signature_v2.json").read_text())
    v1_by_id = {row["opportunity_id"]: row["signature"] for row in v1["opportunity_signatures"]}
    v2_by_id = {row["opportunity_id"]: row["signature"] for row in v2["opportunity_signatures"]}
    shared = set(v1_by_id) & set(v2_by_id)
    assert shared
    for opportunity_id in shared:
        assert {
            field: v2_by_id[opportunity_id][field]
            for field in ("decision_intent", "target_domain", "clinical_stage")
        } == v1_by_id[opportunity_id]
    assert len(v2["controlled_vocabularies"]["target_subdomain"]) <= 12
    assert len(v2["controlled_vocabularies"]["target_subdomain"]) < len(v2["opportunity_signatures"]) / 2


def test_repository_bundle_cache_is_schema_valid_and_has_development_density():
    cache = json.loads(Path("research/qgen/contrast_supply/clinical_contrast_bundle_cache_v1.json").read_text())
    assert cache["roster_anchor_count"] == 24
    assert cache["bundle_count"] >= 20
    assert sum(bundle["admission_class"] in ("STRONG_BUNDLE", "MINIMUM_GENERATABLE_BUNDLE") for bundle in cache["bundles"]) >= 3
    for bundle in cache["bundles"]:
        validate_contrast_bundle_v1(bundle)
        assert all(
            not candidate["next_step_if_correct"].lower().startswith("not correct")
            for candidate in bundle["option_candidates"]
        )


def test_independent_bundle_review_approved_counts_match_cached_options():
    review = json.loads(Path("research/qgen/contrast_supply/clinical_contrast_bundle_independent_review_v1.json").read_text())
    for row in review["rows"]:
        assert sum(
            candidate["verdict"] == "APPROVED_FOR_BUNDLE"
            for candidate in row["candidate_reviews"]
        ) == row["approved_alternatives"]


def test_ready_milestone_freezes_but_does_not_run_outcome_blind_transfer18():
    milestone = json.loads(Path("reports/qgen_signature_v2_discovery_v5_contrast_bundles_milestone.json").read_text())
    selection = json.loads(Path("research/qgen/contrast_supply/new_clean_transfer_18_selection_v1.json").read_text())
    assert milestone["ready_for_new_clean_transfer"] is True
    assert selection["cohort_size"] == 18
    assert selection["per_discipline"] == {"MED": 3, "OBGYN": 3, "PED": 3, "PHELO": 3, "PSY": 3, "SURG": 3}
    assert selection["selection_uses_candidate_or_bundle_outcomes"] is False
    assert selection["cohort_run"] is False


def test_new_transfer18_excludes_every_development_bundle_study_unit():
    roster = json.loads(Path("research/qgen/contrast_supply/development_bundle_roster_v1.json").read_text())
    selection = json.loads(Path("research/qgen/contrast_supply/new_clean_transfer_18_selection_v1.json").read_text())
    development_units = {row["study_unit_id"] for row in roster["anchors"]}
    selected_units = {row["study_unit_id"] for row in selection["opportunities"]}
    assert selected_units.isdisjoint(development_units)
    assert selection["development_roster_study_units_excluded"] == len(development_units)


def test_new_transfer18_is_disjoint_from_every_prior_selection_artifact():
    prior_paths = [Path(value) for value in json.loads(
        Path("research/qgen/contrast_supply/new_clean_transfer_18_selection_v1.json").read_text()
    )["prior_selection_artifacts_excluded"]]
    used = set()

    def collect(value):
        if isinstance(value, dict):
            if isinstance(value.get("study_unit_id"), str):
                used.add(value["study_unit_id"])
            for nested in value.values():
                collect(nested)
        elif isinstance(value, list):
            for nested in value:
                collect(nested)

    for path in prior_paths:
        collect(json.loads(path.read_text()))
    selection = json.loads(Path("research/qgen/contrast_supply/new_clean_transfer_18_selection_v1.json").read_text())
    assert {row["study_unit_id"] for row in selection["opportunities"]}.isdisjoint(used)
