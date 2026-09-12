"""Fail-closed validation for explicit generalized contrast-seed packs.

Historical seed packs keep their frozen 1.0 contract.  This module validates
only additive 2.0 onboarding packs before the existing retrieval adapter sees
their approved rows.
"""

from __future__ import annotations

from typing import Any

from .feature_anchor_registry import content_sha256
from .profile_contrast_retrieval import ContrastRetrievalError


APPROVED = "APPROVED"
REVIEW_STATUSES = frozenset({APPROVED, "REJECTED", "UNCERTAIN"})
SCOPE_TYPES = frozenset({
    "STUDY_UNIT",
    "LEARNER_DECISION_FAMILY",
    "DISCIPLINE_ARCHETYPE",
    "JUSTIFIED_REUSABLE_CONTEXT",
})


def validate_onboarding_pack(pack: dict[str, Any]) -> dict[str, Any]:
    """Validate one frozen, content-addressed onboarding pack."""
    if pack.get("schema_version") != "2.0":
        raise ContrastRetrievalError("additional seed pack must use schema version 2.0")
    if pack.get("scope") != "GENERALIZED_COMPETITIVE_CONTRAST_SEED_PACK":
        raise ContrastRetrievalError("additional seed pack carries the wrong scope")
    for field in (
        "pack_id", "pack_version", "creation_scope", "opportunity_scope",
        "study_unit_scope", "input_hashes", "review_hashes", "targets",
        "content_sha256",
    ):
        if field not in pack:
            raise ContrastRetrievalError(f"additional seed pack is missing {field}")
    if pack.get("frozen") is not True:
        raise ContrastRetrievalError("additional seed pack must be frozen before retrieval")
    body = {key: value for key, value in pack.items() if key != "content_sha256"}
    if content_sha256(body) != pack["content_sha256"]:
        raise ContrastRetrievalError("additional seed pack content hash is stale")
    if not pack["input_hashes"] or not pack["review_hashes"]:
        raise ContrastRetrievalError("additional seed pack needs input and review hashes")

    seen_seed_ids: set[str] = set()
    seen_concepts: set[str] = set()
    for target in pack["targets"]:
        target_id = target.get("target_id")
        study_unit_id = target.get("anchor_study_unit_id")
        learner_decision_id = target.get("learner_decision_id")
        if target_id not in pack["opportunity_scope"]:
            raise ContrastRetrievalError(f"target {target_id} is outside pack opportunity scope")
        if study_unit_id not in pack["study_unit_scope"]:
            raise ContrastRetrievalError(f"target {target_id} is outside pack study-unit scope")
        seeds = target.get("seeds")
        if not isinstance(seeds, list):
            raise ContrastRetrievalError(f"target {target_id} carries no seed list")
        for seed in seeds:
            seed_id = seed.get("seed_id")
            concept_id = seed.get("competitor_concept_id")
            if not isinstance(seed_id, str) or not seed_id:
                raise ContrastRetrievalError("onboarding seed needs a canonical seed id")
            if seed_id in seen_seed_ids:
                raise ContrastRetrievalError(f"duplicate onboarding seed identity: {seed_id}")
            if not isinstance(concept_id, str) or not concept_id:
                raise ContrastRetrievalError(f"seed {seed_id} needs a candidate concept id")
            if concept_id in seen_concepts:
                raise ContrastRetrievalError(
                    f"duplicate onboarding candidate identity: {concept_id}"
                )
            seen_seed_ids.add(seed_id)
            seen_concepts.add(concept_id)
            status = seed.get("onboarding_status")
            review = seed.get("independent_seed_review") or {}
            if status not in REVIEW_STATUSES or review.get("verdict") != status:
                raise ContrastRetrievalError(
                    f"seed {seed_id} has inconsistent independent review status"
                )
            for field in (
                "competitor_concept", "preferred_label", "discipline",
                "learner_decision_id", "response_class",
                "competitor_decision_granularity", "option_set_archetype",
                "candidate_classification", "relation_ids", "anchor_relation_ids",
                "evidence_refs", "author_provenance", "retrieval_scope",
            ):
                if not seed.get(field):
                    raise ContrastRetrievalError(f"seed {seed_id} is missing {field}")
            if status == APPROVED:
                required_passes = (
                    "learner_decision_compatibility",
                    "response_class_compatibility",
                    "granularity_compatibility",
                    "positive_plausibility_support",
                    "inferior_to_key",
                    "anchor_positive_for_candidate",
                    "second_key_safety",
                    "scope_safety",
                )
                failed = [name for name in required_passes if review.get(name) != "PASS"]
                if "anchor_positive_for_candidate" in failed:
                    raise ContrastRetrievalError(
                        f"seed {seed_id} has no independently approved positive candidate anchor"
                    )
                if failed:
                    raise ContrastRetrievalError(
                        f"seed {seed_id} lacks approved seed-safety checks: {', '.join(failed)}"
                    )
            scope = seed["retrieval_scope"]
            if scope.get("scope_type") not in SCOPE_TYPES:
                raise ContrastRetrievalError(f"seed {seed_id} has an unknown retrieval scope")
            if study_unit_id not in scope.get("study_unit_ids", []):
                raise ContrastRetrievalError(f"seed {seed_id} omits its target study unit")
            if learner_decision_id not in scope.get("learner_decision_ids", []):
                raise ContrastRetrievalError(f"seed {seed_id} omits its learner decision")
    return pack


def approved_seed_scope(pack: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Return retrieval metadata for independently approved rows only."""
    validate_onboarding_pack(pack)
    return {
        seed["seed_id"]: {
            "onboarding_pack_id": pack["pack_id"],
            "onboarding_pack_version": pack["pack_version"],
            "retrieval_scope": seed["retrieval_scope"],
            "relation_ids": list(seed["relation_ids"]),
            "anchor_relation_ids": list(seed["anchor_relation_ids"]),
            "candidate_classification": seed["candidate_classification"],
        }
        for target in pack["targets"]
        for seed in target["seeds"]
        if seed["onboarding_status"] == APPROVED
    }
