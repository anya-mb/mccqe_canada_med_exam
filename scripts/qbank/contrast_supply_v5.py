"""Decision Signature V2, Discovery V5, and Clinical Contrast Bundle V1.

This module is additive to the frozen V4 implementation.  It contains only
deterministic validation, filtering, ranking, admission, and cache operations;
clinical judgements remain explicit data artifacts.
"""

from __future__ import annotations

from collections import Counter
from typing import Any, Mapping, Sequence

from .contrast_supply_v3 import canonical_content_sha256
from .contrast_supply_v4 import _response_class_compatible


SIGNATURE_V2_DIMENSIONS = (
    "decision_intent",
    "target_domain",
    "clinical_stage",
    "target_subdomain",
    "semantic_containment_role",
)
DISCOVERY_V5_VERSION = "GLOBAL_DECISION_COMPATIBLE_DISCOVERY_V5_1"
V5_CANDIDATE_BUDGET = 8
MATRIX_STATES = frozenset({"PRESENT", "ABSENT", "UNKNOWN", "NOT_APPLICABLE"})
FEATURE_TYPES = frozenset({
    "SHARED_PLAUSIBILITY",
    "KEY_SUPPORTING",
    "CANDIDATE_SUPPORTING",
    "PAIRWISE_DISCRIMINATOR",
    "HIGH_DISCRIMINATIVE",
    "ACTION_CHANGING",
    "EXCLUSIONARY",
    "RATIONALE_ONLY",
    "STEM_ELIGIBLE",
})
FEATURE_VISIBILITY = frozenset({"STEM_ELIGIBLE", "RATIONALE_ONLY", "CONDITIONAL"})
GENERIC_CONCEPT_LABELS = frozenset({
    "approach", "classification", "diagnosis", "disease", "management",
    "other", "overview", "principles", "treatment",
})


class BundleValidationError(ValueError):
    """Raised when a bundle could make an unsafe option set reachable."""


def validate_decision_signature_v2(
    signature: Mapping[str, Any],
    controlled_vocabularies: Mapping[str, Sequence[str]] | None = None,
) -> dict[str, str]:
    """Validate the closed, five-dimensional Decision Signature V2."""
    missing = [field for field in SIGNATURE_V2_DIMENSIONS if not signature.get(field)]
    if missing:
        raise ValueError(f"missing signature dimension: {missing[0]}")
    unknown = set(signature) - set(SIGNATURE_V2_DIMENSIONS)
    if unknown:
        raise ValueError(f"unknown signature field: {sorted(unknown)[0]}")
    result = {field: str(signature[field]) for field in SIGNATURE_V2_DIMENSIONS}
    if controlled_vocabularies is not None:
        for field, value in result.items():
            if value not in set(controlled_vocabularies.get(field, ())):
                raise ValueError(f"unknown {field}: {value}")
    return result


def signatures_v2_compatible(
    opportunity_signature: Mapping[str, Any],
    candidate_signature: Mapping[str, Any],
) -> dict[str, Any]:
    """Return the earliest V2 mismatch using stable ordered dimensions."""
    opportunity = validate_decision_signature_v2(opportunity_signature)
    candidate = validate_decision_signature_v2(candidate_signature)
    checks = (
        ("decision_intent", "WRONG_DECISION_INTENT"),
        ("target_domain", "WRONG_TARGET_DOMAIN"),
        ("clinical_stage", "WRONG_CLINICAL_STAGE"),
        ("target_subdomain", "WRONG_TARGET_SUBDOMAIN"),
        ("semantic_containment_role", "SEMANTIC_CONTAINMENT_MISMATCH"),
    )
    for field, reason in checks:
        if opportunity[field] != candidate[field]:
            return {"compatible": False, "reason": reason}
    return {"compatible": True, "reason": None}


def discover_global_candidates_v5(
    catalogue: Sequence[Mapping[str, Any]], *, opportunity: Mapping[str, Any],
    candidate_signatures: Mapping[str, Mapping[str, Any]] | None = None,
    budget: int = V5_CANDIDATE_BUDGET,
) -> dict[str, Any]:
    """Discover globally, then apply response, granularity, V2, and context gates."""
    if not 1 <= budget <= V5_CANDIDATE_BUDGET:
        raise ValueError(f"candidate budget must be between 1 and {V5_CANDIDATE_BUDGET}")
    opportunity_signature = validate_decision_signature_v2(
        opportunity["decision_signature_v2"]
    )
    demanded = str(opportunity["demanded_response_class"])
    granularity = str(opportunity["decision_granularity"])
    applicability = str(opportunity["applicability_context"])
    key_aliases = {str(value).casefold() for value in opportunity.get("key_aliases", ())}
    wanted_families = set(opportunity.get("semantic_families", ()))
    rejection_counts: Counter[str] = Counter()
    rejections: list[dict[str, str]] = []
    ranked: list[tuple[tuple[int, int, int, str], dict[str, Any]]] = []

    def reject(candidate_id: str, reason: str) -> None:
        rejection_counts[reason] += 1
        rejections.append({"candidate_id": candidate_id, "reason": reason})

    for original in catalogue:
        candidate_id = str(original["canonical_candidate_id"])
        label = str(original["normalized_label"])
        aliases = {label.casefold(), *(str(value).casefold() for value in original.get("aliases", ()))}
        if original.get("generic_concept") or label.casefold() in GENERIC_CONCEPT_LABELS:
            reject(candidate_id, "GENERIC_CONCEPT")
            continue
        if aliases & key_aliases:
            reject(candidate_id, "KEY_ALIAS")
            continue
        if not _response_class_compatible(demanded, set(original.get("response_classes", ()))):
            reject(candidate_id, "WRONG_RESPONSE_CLASS")
            continue
        granularities = set(original.get("decision_granularities", ()))
        if granularities and granularity not in granularities:
            reject(candidate_id, "WRONG_GRANULARITY")
            continue
        signature = (
            candidate_signatures.get(candidate_id)
            if candidate_signatures is not None
            else original.get("decision_signature_v2")
        )
        if signature is None:
            reject(candidate_id, "MISSING_CANDIDATE_SIGNATURE")
            continue
        compatibility = signatures_v2_compatible(opportunity_signature, signature)
        if not compatibility["compatible"]:
            reject(candidate_id, str(compatibility["reason"]))
            continue
        contexts = set(str(value) for value in original.get("applicability_contexts", ()))
        if applicability not in contexts:
            reject(candidate_id, "WRONG_APPLICABILITY_CONTEXT")
            continue
        parent_ids = set(str(value) for value in original.get("contains_candidate_ids", ()))
        subtype_ids = set(str(value) for value in original.get("contained_by_candidate_ids", ()))
        if parent_ids or subtype_ids:
            reject(candidate_id, "PARENT_SUBTYPE_COLLISION")
            continue
        same_unit = opportunity.get("study_unit_id") in set(original.get("study_unit_ids", ()))
        same_chapter = opportunity.get("chapter_code") in set(original.get("chapters", ()))
        family_match = bool(wanted_families & set(original.get("semantic_families", ())))
        row = dict(original)
        row["decision_signature_v2"] = dict(signature)
        row["cross_study_unit"] = not same_unit
        row["cross_chapter"] = not same_chapter
        row["ranking_signals_v5"] = {
            "response_class_match": True,
            "granularity_match": True,
            "decision_signature_v2_match": True,
            "applicability_context_match": True,
            "semantic_family_match": family_match,
            "same_study_unit": same_unit,
            "same_chapter": same_chapter,
        }
        ranked.append(((0 if family_match else 1, 0 if same_unit else 1,
                        0 if same_chapter else 1, candidate_id), row))
    all_compatible = [row for _, row in sorted(ranked, key=lambda item: item[0])]
    return {
        "discovery_v5_version": DISCOVERY_V5_VERSION,
        "candidate_budget": budget,
        "global_catalogue_rows_scanned": len(catalogue),
        "compatible_before_budget_count": len(all_compatible),
        "rejection_counts": dict(sorted(rejection_counts.items())),
        "rejections": rejections,
        "candidates": all_compatible[:budget],
    }


def classify_bundle_admission(approved_alternative_count: int) -> str:
    if approved_alternative_count < 0:
        raise BundleValidationError("approved alternative count cannot be negative")
    if approved_alternative_count >= 4:
        return "STRONG_BUNDLE"
    if approved_alternative_count == 3:
        return "MINIMUM_GENERATABLE_BUNDLE"
    if approved_alternative_count:
        return "PARTIAL_BUNDLE"
    return "NO_SAFE_BUNDLE"


def validate_contrast_bundle_v1(bundle: Mapping[str, Any]) -> dict[str, Any]:
    """Fail closed on bundle structure or semantics needed for safe generation."""
    required = (
        "bundle_id", "learner_decision_family", "opportunity_ids", "key",
        "response_class", "decision_granularity", "decision_signature_v2",
        "population_context_restrictions", "clinical_stage", "target_domain",
        "target_subdomain", "clinical_state_entities", "evidence",
        "option_candidates", "feature_matrix", "pairwise_review", "bundle_review",
    )
    for field in required:
        if field not in bundle:
            raise BundleValidationError(f"bundle missing {field}")
    validate_decision_signature_v2(bundle["decision_signature_v2"])
    evidence_ids = {row.get("ref_id") for row in bundle["evidence"] if row.get("ref_id")}
    if not evidence_ids:
        raise BundleValidationError("bundle has no evidence references")
    candidate_ids = [str(row.get("candidate_id", "")) for row in bundle["option_candidates"]]
    if not all(candidate_ids) or len(candidate_ids) != len(set(candidate_ids)):
        raise BundleValidationError("candidate ids must be non-empty and unique")
    feature_by_id: dict[str, Mapping[str, Any]] = {}
    for feature in bundle["feature_matrix"]:
        feature_id = str(feature.get("feature_id", ""))
        if not feature_id or feature_id in feature_by_id:
            raise BundleValidationError("feature ids must be non-empty and unique")
        tags = set(feature.get("type_tags", ()))
        if not tags or not tags <= FEATURE_TYPES:
            raise BundleValidationError(f"invalid feature type for {feature_id}")
        if feature.get("visibility") not in FEATURE_VISIBILITY:
            raise BundleValidationError(f"invalid feature visibility for {feature_id}")
        if not set(feature.get("evidence_refs", ())) <= evidence_ids:
            raise BundleValidationError(f"unknown evidence ref for {feature_id}")
        states = feature.get("states", {})
        expected_columns = {"KEY", *candidate_ids}
        if set(states) != expected_columns or any(value not in MATRIX_STATES for value in states.values()):
            raise BundleValidationError(f"matrix state missing or invalid for {feature_id}")
        feature_by_id[feature_id] = feature
    for candidate in bundle["option_candidates"]:
        candidate_id = str(candidate["candidate_id"])
        if candidate.get("canonical_identity") != candidate_id:
            raise BundleValidationError(f"canonical identity mismatch for {candidate_id}")
        if candidate.get("response_class") != bundle["response_class"]:
            raise BundleValidationError(f"response class mismatch for {candidate_id}")
        if candidate.get("granularity") != bundle["decision_granularity"]:
            raise BundleValidationError(f"granularity mismatch for {candidate_id}")
        if candidate.get("review_status") != "APPROVED_FOR_BUNDLE":
            raise BundleValidationError(f"review_status is not approved for {candidate_id}")
        validate_decision_signature_v2(candidate["decision_signature_v2"])
        compatibility = signatures_v2_compatible(
            bundle["decision_signature_v2"], candidate["decision_signature_v2"]
        )
        if not compatibility["compatible"]:
            raise BundleValidationError(f"signature mismatch for {candidate_id}")
        for field in ("positive_candidate_anchor_ids", "features_making_candidate_inferior"):
            if not candidate.get(field):
                raise BundleValidationError(f"{field} is required for {candidate_id}")
        referenced_features = set()
        for field in (
            "positive_candidate_anchor_ids", "shared_plausibility_feature_ids",
            "candidate_supporting_feature_ids", "key_vs_candidate_discriminator_ids",
            "candidate_vs_other_candidate_discriminator_ids",
            "high_discriminative_feature_ids", "action_changing_feature_ids",
            "features_making_candidate_correct", "features_making_candidate_inferior",
        ):
            referenced_features.update(candidate.get(field, ()))
        unknown_features = referenced_features - set(feature_by_id)
        if unknown_features:
            raise BundleValidationError(
                f"candidate {candidate_id} references unknown feature {sorted(unknown_features)[0]}"
            )
        if not set(candidate.get("evidence_refs", ())) <= evidence_ids:
            raise BundleValidationError(f"unknown candidate evidence ref for {candidate_id}")
    review = bundle["bundle_review"]
    for field in (
        "coherent_option_class", "granularity_consistency", "candidate_diversity",
        "no_second_keys", "educational_usefulness",
    ):
        if review.get(field) != "PASS":
            raise BundleValidationError(f"bundle review did not pass {field}")
    result = dict(bundle)
    result["admission_class"] = classify_bundle_admission(len(candidate_ids))
    return result


def build_contrast_bundle_cache_v1(
    bundles: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    admitted = []
    for bundle in bundles:
        if (bundle.get("bundle_review") or {}).get("verdict") != "APPROVED":
            continue
        admitted.append(validate_contrast_bundle_v1(bundle))
    admitted.sort(key=lambda row: row["bundle_id"])
    value = {
        "schema_version": "CLINICAL_CONTRAST_BUNDLE_CACHE_V1",
        "bundle_count": len(admitted),
        "lookup_scope": [
            "learner_decision_family", "decision_signature_v2",
            "target_subdomain", "applicability_context",
        ],
        "bundles": admitted,
    }
    value["content_sha256"] = canonical_content_sha256(value)
    return value


def lookup_contrast_bundle(
    cache: Mapping[str, Any], *, learner_decision_family: str,
    decision_signature_v2: Mapping[str, Any], target_subdomain: str,
    applicability_context: str,
) -> dict[str, Any] | None:
    wanted_signature = validate_decision_signature_v2(decision_signature_v2)
    for bundle in cache.get("bundles", ()):
        if bundle["learner_decision_family"] != learner_decision_family:
            continue
        if bundle["decision_signature_v2"] != wanted_signature:
            continue
        if bundle["target_subdomain"] != target_subdomain:
            continue
        if applicability_context not in bundle["population_context_restrictions"]:
            continue
        return dict(bundle)
    return None
