"""Deterministic validation and accounting for clean Transfer V2 data.

This module does not make clinical judgments. It validates explicit reviewed
inputs against the frozen lifecycle and computes reproducible milestone
metrics.
"""

from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
import statistics
from typing import Any, Iterable, Mapping

from .qgen_exposure_registry import canonical_content_hash


class CleanTransferV2Error(ValueError):
    """A clean-transfer artifact violates the frozen experiment contract."""


FROZEN_CONTENT_PATHS = {
    "candidate_role_registry_v1": "research/qgen/contrast_supply/candidate_role_registry_v1.json",
    "catalogue_v3": "research/qgen/contrast_supply/global_candidate_concept_catalogue_v3.json",
    "anchor_candidate_universe_v2": "research/qgen/contrast_supply/anchor_candidate_universe_v2.json",
    "concept_feature_library_v2": "research/qgen/contrast_supply/concept_feature_library_v2.json",
    "conditional_next_action_v1": "research/qgen/contrast_supply/conditional_next_action_v1.json",
    "compatibility_graph_v2": "research/qgen/contrast_supply/candidate_compatibility_graph_v2.json",
    "contrast_bundles_v4": "research/qgen/contrast_supply/clinical_contrast_bundles_v4_expanded.json",
    "question_seed_v1": "research/qgen/contrast_supply/question_seed_v1.json",
}

EXPECTED_FROZEN_CONTENT_HASHES = {
    "candidate_role_registry_v1": "bfdf744fa25dab55d4e8f297dc5995b1c540ceb62bd824d72f6b5866e1fd3d81",
    "catalogue_v3": "f9e4f6d299b9c789df53cc8c338f9d2319de4792880d6d33289038b633a3b5df",
    "anchor_candidate_universe_v2": "1aa3ca135c3b22696ab0c94dbcd122fba08d48a122dbdd2973fdef74b25f8114",
    "concept_feature_library_v2": "fe76778300159bf03efd02f89875e510da24f3f0896964c0c3218823f16e748a",
    "conditional_next_action_v1": "7d13f1af8fdc6c3a0f84556522ad968a96e35017bee05c40a59d2f929188b3ab",
    "compatibility_graph_v2": "a4ecd869eeddaf730950d4a2ada50f7c4af58ba1a1fcbb9ecd9e659fc00d5c66",
    "contrast_bundles_v4": "d28d13de3f644f95406b97abef38ac2d4669c6e0a9c6a0dbd66d3c4c89c24d0f",
    "question_seed_v1": "fe994fbe67dd5c6e25818887aee15b783417f518685e4e1f60b2c938e8add7e6",
}


def _file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_validation_contract_v2(
    root: Path,
    cohort: Mapping[str, Any],
    reserved_registry: Mapping[str, Any],
    cleanliness_proof: Mapping[str, Any],
) -> dict[str, Any]:
    if cleanliness_proof.get("verdict") != "PASS" or cleanliness_proof.get("clean_cohort_overlaps") != 0:
        raise CleanTransferV2Error("CLEANLINESS_PROOF_REQUIRED")
    root = Path(root).resolve()
    observed_content = {
        name: json.loads((root / path).read_text()).get("content_sha256")
        for name, path in FROZEN_CONTENT_PATHS.items()
    }
    drift = sorted(name for name, expected in EXPECTED_FROZEN_CONTENT_HASHES.items() if observed_content.get(name) != expected)
    if drift:
        raise CleanTransferV2Error(f"FROZEN_ARCHITECTURE_HASH_DRIFT: {', '.join(drift)}")
    file_paths = {
        "discovery_v6": "scripts/qbank/contrast_supply_v6.py",
        "candidate_proposal_contract": "scripts/qbank/candidate_universe.py",
        "candidate_evidence": "scripts/qbank/candidate_evidence_v2.py",
        "question_seed": "scripts/qbank/question_seed.py",
        "duplicate_and_lifecycle": "scripts/qbank/generation_lifecycle.py",
        "exposure_registry_v1": "scripts/qbank/qgen_exposure_registry.py",
        "cohort_selector_v2": "scripts/qbank/qgen_clean_cohort_v2.py",
        "independent_cleanliness_validator_v2": "scripts/qbank/qgen_cleanliness_validator_v2.py",
        "clean_transfer_instrumentation_v2": "scripts/qbank/clean_transfer_validation_v2.py",
    }
    result: dict[str, Any] = {
        "schema_version": "CLEAN_TRANSFER_VALIDATION_CONTRACT_V2",
        "frozen_before_candidate_supply_unblinding": True,
        "exposure_registry_sha256": reserved_registry.get("parent_registry_content_sha256") or reserved_registry.get("content_sha256"),
        "reserved_registry_sha256": reserved_registry.get("content_sha256"),
        "cohort_sha256": cohort.get("content_sha256"),
        "selection_input_sha256": cohort.get("selection_input_sha256"),
        "cleanliness_proof_sha256": cleanliness_proof.get("content_sha256"),
        "frozen_architecture_content_sha256": observed_content,
        "frozen_architecture_file_sha256": {name: _file_hash(root / path) for name, path in file_paths.items()},
        "candidate_acquisition_order": [
            "ZERO_AUTHORING_LIBRARY_REUSE", "DISCOVERY_V6", "TORONTO_NOTES_STRUCTURAL",
            "EXISTING_GUIDELINE_SOURCE", "SOURCE_DERIVED_STAGE1", "MODEL_PROPOSAL",
            "MODEL_STAGE1", "PRE_EVIDENCE_SAFETY", "EVIDENCE_REUSE", "NEW_EVIDENCE",
            "ENTAILMENT", "CONDITIONAL_NEXT_ACTION", "STAGE2",
        ],
        "candidate_proposal_contract": {
            "output": "CANDIDATE_CONCEPTS_ONLY",
            "same_response_class": True,
            "same_granularity": True,
            "clinical_plausibility": True,
            "educational_distinctness": True,
            "model_output_is_evidence": False,
        },
        "saturation_contract": {
            "stop_rule": "TWO_CONSECUTIVE_BOUNDED_PASSES_ZERO_NEW_POTENTIALLY_ADMISSIBLE",
            "all_plausible_proposals_require_terminal_stage2": True,
            "hard_review_ceiling_per_anchor": 24,
        },
        "stage1_rubric": ["PLAUSIBLE", "REJECTED", "UNCERTAIN"],
        "entailment_rubric": ["ENTAILED", "PARTIALLY_ENTAILED", "NOT_ENTAILED", "CONFLICTING", "UNCERTAIN"],
        "stage2_rubric": ["APPROVED", "REJECTED", "UNCERTAIN"],
        "uncertain_fails_closed": True,
        "source_policy": {
            "toronto_notes": "STRUCTURAL_AND_CANONICAL_DISCOVERY_ONLY",
            "model_candidate_evidence": "AUTHORITATIVE_CANADIAN_PLUS_INDEPENDENT_CORROBORATION_WHERE_REASONABLY_AVAILABLE",
            "single_source_exception_requires_review": True,
        },
        "candidate_budget": {"discovery_v6_per_anchor": 8, "model_review_ceiling_per_anchor": 24},
        "review_budget": {"semantic_concurrency": 1, "question_attempts_per_ready_anchor": 1, "retries": 0},
        "bundle_contract": {"preserve_full_approved_universe": True, "contrast_ready_minimum": 3, "strong_choice_ready_minimum": 5},
        "duplicate_contract": {"question_seed_v1_fingerprint_frozen": True, "post_generation_semantic_classifier_frozen": True},
        "semantic_shared_code_change_after_unblinding": "PROHIBITED_AND_CONTAMINATES_COHORT",
    }
    result["content_sha256"] = canonical_content_hash(result)
    return result


def _candidates(anchor: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    for field in ("discovery_v6_candidates", "source_candidates", "model_candidates"):
        yield from anchor.get(field, [])


def validate_clean_run(cohort: Mapping[str, Any], run: Mapping[str, Any]) -> None:
    if run.get("cohort_sha256") != cohort.get("content_sha256"):
        raise CleanTransferV2Error("COHORT_HASH_MISMATCH")
    expected = {row["cohort_row_id"] for row in cohort.get("rows", [])}
    anchors = run.get("anchors", [])
    observed = [row.get("cohort_row_id") for row in anchors]
    if len(observed) != len(set(observed)) or set(observed) != expected:
        raise CleanTransferV2Error("ANCHOR_DENOMINATOR_MISMATCH")
    source_ids = {row["source_id"] for row in run.get("sources", [])}
    for anchor in anchors:
        for field in (
            "study_unit_id", "discipline", "learner_decision", "key",
            "response_class", "granularity", "decision_signature",
            "population", "clinical_stage", "target_subdomain",
        ):
            if not anchor.get(field):
                raise CleanTransferV2Error(f"MISSING_PREREQUISITE_FIELD: {field}")
        candidate_rows = list(_candidates(anchor))
        ids = [row.get("candidate_id") for row in candidate_rows]
        if None in ids or len(ids) != len(set(ids)):
            raise CleanTransferV2Error("CANDIDATE_IDS_MUST_BE_UNIQUE_PER_ANCHOR")
        approved_ids = set(anchor.get("zero_authoring_reuse", {}).get("candidate_ids", []))
        for candidate in candidate_rows:
            stage1 = candidate.get("stage1_verdict")
            if stage1 not in {"PLAUSIBLE", "REJECTED", "UNCERTAIN"}:
                raise CleanTransferV2Error("INVALID_STAGE1_VERDICT")
            if stage1 == "PLAUSIBLE" and candidate.get("deterministic_rejected") is not True:
                if candidate.get("evidence_researched") is not True:
                    raise CleanTransferV2Error("PLAUSIBLE_CANDIDATE_WITHOUT_EVIDENCE_RESEARCH")
                if not set(candidate.get("source_ids", [])) <= source_ids:
                    raise CleanTransferV2Error("UNKNOWN_EVIDENCE_SOURCE")
                if candidate.get("stage2_verdict") not in {"APPROVED", "REJECTED", "UNCERTAIN"}:
                    raise CleanTransferV2Error("MISSING_TERMINAL_STAGE2")
            if candidate.get("stage2_verdict") == "APPROVED":
                if candidate.get("entailment_verdict") != "ENTAILED":
                    raise CleanTransferV2Error("APPROVED_WITHOUT_ENTAILED_EVIDENCE")
                if candidate.get("second_key_risk") is not False:
                    raise CleanTransferV2Error("APPROVED_WITH_SECOND_KEY_RISK")
                approved_ids.add(candidate["candidate_id"])
        if not set(anchor.get("bundle_candidate_ids", [])) <= approved_ids:
            raise CleanTransferV2Error("BUNDLE_CONTAINS_UNAPPROVED_CANDIDATE")
        question = anchor.get("question")
        if question is not None:
            if len(anchor.get("bundle_candidate_ids", [])) < 3:
                raise CleanTransferV2Error("QUESTION_WITHOUT_CONTRAST_READY_BUNDLE")
            for field in ("blind_solve", "liveness", "final_medical_review", "postgen_duplicate"):
                if field not in question:
                    raise CleanTransferV2Error(f"INCOMPLETE_QUESTION_LIFECYCLE: {field}")


def _sum_candidate_field(anchors: Iterable[Mapping[str, Any]], field: str) -> int:
    return sum(int(candidate.get(field, 0)) for anchor in anchors for candidate in _candidates(anchor))


def summarize_clean_run(run: Mapping[str, Any]) -> dict[str, Any]:
    anchors = list(run.get("anchors", []))
    model = [candidate for anchor in anchors for candidate in anchor.get("model_candidates", [])]
    source = [candidate for anchor in anchors for candidate in anchor.get("source_candidates", [])]
    discovery = [candidate for anchor in anchors for candidate in anchor.get("discovery_v6_candidates", [])]
    model_counts = {
        "proposed": len(model),
        "stage1_plausible": sum(row.get("stage1_verdict") == "PLAUSIBLE" for row in model),
        "deterministic_rejected": sum(row.get("deterministic_rejected") is True for row in model),
        "evidence_researched": sum(row.get("evidence_researched") is True for row in model),
        "multi_source_concordant": sum(row.get("source_status") == "MULTI_SOURCE_CONCORDANT" for row in model),
        "single_source_exception": sum(row.get("source_status") == "SINGLE_SOURCE_EXCEPTION" for row in model),
        "stage2_approved": sum(row.get("stage2_verdict") == "APPROVED" for row in model),
        "stage2_rejected": sum(row.get("stage2_verdict") == "REJECTED" for row in model),
        "stage2_uncertain": sum(row.get("stage2_verdict") == "UNCERTAIN" for row in model),
        "second_key_risk": sum(row.get("second_key_risk") is True for row in model),
    }
    approved_denominator = model_counts["stage2_approved"] + model_counts["stage2_rejected"] + model_counts["stage2_uncertain"]
    universe_sizes = []
    bundle_sizes = []
    for anchor in anchors:
        approved = set(anchor.get("zero_authoring_reuse", {}).get("candidate_ids", []))
        approved.update(candidate["candidate_id"] for candidate in _candidates(anchor) if candidate.get("stage2_verdict") == "APPROVED")
        universe_sizes.append(len(approved))
        bundle_sizes.append(len(anchor.get("bundle_candidate_ids", [])))
    pass_numbers = sorted({row["pass"] for anchor in anchors for row in anchor.get("saturation_passes", [])})
    marginal = [
        sum(row["stage2_approved"] for anchor in anchors for row in anchor.get("saturation_passes", []) if row["pass"] == number)
        for number in pass_numbers
    ]
    terminal_zero = len(marginal) >= 2 and marginal[-2:] == [0, 0]
    questions = [anchor.get("question") for anchor in anchors if anchor.get("question") is not None]
    tn_rows = [row for anchor in anchors for row in anchor.get("tn_source_first", [])]
    compatibility = [row for anchor in anchors for row in anchor.get("compatibility_edges", [])]
    zero = [anchor.get("zero_authoring_reuse", {}) for anchor in anchors]
    result = {
        "zero_authoring_reuse": {
            "anchors_with_1_plus_candidate": sum(bool(row.get("candidate_ids")) for row in zero),
            "anchors_with_3_plus_candidates": sum(len(row.get("candidate_ids", [])) >= 3 for row in zero),
            "anchors_with_5_plus_candidates": sum(len(row.get("candidate_ids", [])) >= 5 for row in zero),
            "concept_facts_reused": sum(len(row.get("concept_fact_ids", [])) for row in zero),
            "next_actions_reused": sum(len(row.get("next_action_ids", [])) for row in zero),
            "compatibility_edges_reused": sum(len(row.get("compatibility_edge_ids", [])) for row in zero),
            "bundles_reused": sum(len(row.get("bundle_ids", [])) for row in zero),
        },
        "discovery_v6_clean": {
            "candidates_retrieved": len(discovery),
            "clinically_plausible": sum(row.get("stage1_verdict") == "PLAUSIBLE" for row in discovery),
            "anchors_with_1_plus": sum(len(anchor.get("discovery_v6_candidates", [])) >= 1 for anchor in anchors),
            "anchors_with_3_plus": sum(len(anchor.get("discovery_v6_candidates", [])) >= 3 for anchor in anchors),
            "anchors_with_5_plus": sum(len(anchor.get("discovery_v6_candidates", [])) >= 5 for anchor in anchors),
        },
        "tn_source_first_clean": {
            "identities_found": len(tn_rows),
            "already_known": sum(row.get("classification") == "ALREADY_KNOWN" for row in tn_rows),
            "genuinely_new": sum(row.get("classification") == "GENUINELY_NEW" for row in tn_rows),
            "invalid": sum(row.get("classification") == "INVALID" for row in tn_rows),
            "ambiguous": sum(row.get("classification") == "AMBIGUOUS" for row in tn_rows),
        },
        "source_derived_clean": {
            "proposed": len(source),
            "stage1_plausible": sum(row.get("stage1_verdict") == "PLAUSIBLE" for row in source),
            "stage2_approved": sum(row.get("stage2_verdict") == "APPROVED" for row in source),
        },
        "model_proposed_clean": model_counts,
        "clean_model_approval_rate": (model_counts["stage2_approved"] / approved_denominator) if approved_denominator else 0.0,
        "clean_candidate_universe_size": {
            "min": min(universe_sizes, default=0),
            "median": statistics.median(universe_sizes) if universe_sizes else 0,
            "mean": round(statistics.mean(universe_sizes), 2) if universe_sizes else 0,
            "max": max(universe_sizes, default=0),
        },
        "clean_anchors_with_3_plus": sum(value >= 3 for value in universe_sizes),
        "clean_anchors_with_5_plus": sum(value >= 5 for value in universe_sizes),
        "clean_anchors_with_8_plus": sum(value >= 8 for value in universe_sizes),
        "clean_anchors_with_10_plus": sum(value >= 10 for value in universe_sizes),
        "saturation_status": "SATURATED" if terminal_zero else "STILL_EXPANDING",
        "saturation_passes": len(pass_numbers),
        "marginal_stage2_approved_per_pass": marginal,
        "clean_evidence_reuse": {
            "concept_facts_reused": _sum_candidate_field(anchors, "concept_facts_reused"),
            "concept_facts_new": _sum_candidate_field(anchors, "concept_facts_new"),
            "source_retrievals_reused": _sum_candidate_field(anchors, "source_retrievals_reused"),
            "source_retrievals_new": _sum_candidate_field(anchors, "source_retrievals_new"),
            "pairwise_requests_avoided": _sum_candidate_field(anchors, "pairwise_requests_avoided"),
        },
        "clean_next_action": {
            "branches_reused": _sum_candidate_field(anchors, "next_action_branches_reused"),
            "branches_new": _sum_candidate_field(anchors, "next_action_branches_new"),
            "candidates_with_1_plus_branch": sum(
                int(candidate.get("next_action_branches_reused", 0)) + int(candidate.get("next_action_branches_new", 0)) >= 1
                for anchor in anchors for candidate in _candidates(anchor) if candidate.get("stage2_verdict") == "APPROVED"
            ),
            "missing": sum(
                int(candidate.get("next_action_branches_reused", 0)) + int(candidate.get("next_action_branches_new", 0)) == 0
                for anchor in anchors for candidate in _candidates(anchor) if candidate.get("stage2_verdict") == "APPROVED"
            ),
        },
        "clean_compatibility": {
            "edges_reused": sum(row.get("origin") == "REUSED" for row in compatibility),
            "edges_new": sum(row.get("origin") == "NEW" for row in compatibility),
            "edges_derived_without_new_pairwise_research": sum(row.get("derived_without_pairwise_research") is True for row in compatibility),
            "pairwise_research_requests": sum(row.get("pairwise_research_required") is True for row in compatibility),
        },
        "clean_bundle_density": {
            "with_3_plus": sum(value >= 3 for value in bundle_sizes),
            "with_5_plus": sum(value >= 5 for value in bundle_sizes),
            "with_8_plus": sum(value >= 8 for value in bundle_sizes),
            "with_10_plus": sum(value >= 10 for value in bundle_sizes),
        },
        "question_results": {
            "seeds_proposed": sum(anchor.get("question_seed") is not None for anchor in anchors),
            "pregeneration_duplicates": sum(anchor.get("question_seed", {}).get("duplicate_verdict") in {"NEAR_DUPLICATE", "DUPLICATE"} for anchor in anchors if anchor.get("question_seed")),
            "items_generated": len(questions),
            "blind_solve_passes": sum(row.get("blind_solve") == "PASS" for row in questions),
            "liveness_passes": sum(row.get("liveness") == "PASS" for row in questions),
            "final_review_passes": sum(row.get("final_medical_review") == "PASS" for row in questions),
            "accepted": sum(row.get("admission") == "ACCEPTED" for row in questions),
            "rejected": sum(row.get("admission") == "REJECTED" for row in questions),
            "postgen_near_duplicates": sum(row.get("postgen_duplicate") == "NEAR_DUPLICATE" for row in questions),
            "postgen_duplicates": sum(row.get("postgen_duplicate") == "DUPLICATE" for row in questions),
        },
    }
    return result
