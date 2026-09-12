"""Deterministic contracts for candidate-specific feature evidence.

This module is append-only downstream of the frozen Discovery V6 artifacts.
It does not perform medical inference: reviewed JSON data supplies propositions
and verdicts, while this code enforces provenance, admission, and accounting.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping


APPROVED_FEATURE_ROLES = frozenset({
    "SHARED_PLAUSIBILITY",
    "CANDIDATE_SUPPORTING",
    "KEY_SUPPORTING",
    "PAIRWISE_DISCRIMINATOR",
    "HIGH_DISCRIMINATIVE",
    "ACTION_CHANGING",
    "EXCLUSIONARY",
    "WHAT_MAKES_CANDIDATE_CORRECT",
    "NEXT_STEP_IF_CANDIDATE_CORRECT",
    "RATIONALE_ONLY",
    "STEM_ELIGIBLE",
    "CONDITIONAL",
})

LOAD_BEARING_FEATURE_ROLES = frozenset({
    "SHARED_PLAUSIBILITY",
    "CANDIDATE_SUPPORTING",
    "KEY_SUPPORTING",
    "PAIRWISE_DISCRIMINATOR",
    "HIGH_DISCRIMINATIVE",
    "ACTION_CHANGING",
    "EXCLUSIONARY",
    "WHAT_MAKES_CANDIDATE_CORRECT",
    "NEXT_STEP_IF_CANDIDATE_CORRECT",
})

ENTAILMENT_STATUSES = frozenset({
    "ENTAILED", "PARTIALLY_ENTAILED", "NOT_ENTAILED", "CONFLICTING", "UNCERTAIN"
})


def canonical_content_hash(value: Mapping[str, Any]) -> str:
    """Hash canonical JSON after excluding a top-level self-hash field."""
    payload = {key: item for key, item in value.items() if key != "content_sha256"}
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def build_evidence_cohort(
    reference_set: Mapping[str, Any],
    reference_review: Mapping[str, Any],
    prerequisites: Mapping[str, Any],
) -> dict[str, Any]:
    reviews = {row["reference_candidate_id"]: row for row in reference_review["rows"]}
    prerequisite_by_anchor = {row["transfer_id"]: row for row in prerequisites["rows"]}
    candidates: list[dict[str, Any]] = []
    for anchor in reference_set["anchors"]:
        prerequisite = prerequisite_by_anchor[anchor["anchor_id"]]
        for candidate in anchor["option_candidates"]:
            review = reviews[candidate["reference_candidate_id"]]
            if review["verdict"] != "APPROVED_REFERENCE":
                continue
            candidates.append({
                "anchor_id": anchor["anchor_id"],
                "key": anchor["key"],
                "reference_candidate_id": candidate["reference_candidate_id"],
                "canonical_candidate_id": candidate["canonical_candidate_id"],
                "canonical_concept_name": candidate["canonical_concept_name"],
                "response_class": candidate["canonical_response_role"],
                "decision_granularity": prerequisite["decision_granularity"],
                "decision_signature_v2": prerequisite["decision_signature_v2"],
                "reference_verdict": review["verdict"],
            })
    result = {
        "schema_version": "FEATURE_EVIDENCE_COHORT_V1",
        "reference_set_sha256": reference_set["content_sha256"],
        "reference_review_sha256": reference_review["content_sha256"],
        "candidates": sorted(candidates, key=lambda row: row["reference_candidate_id"]),
    }
    result["content_sha256"] = canonical_content_hash(result)
    return result


def validate_evidence_cohort(cohort: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    rows = cohort.get("candidates", ())
    ids = [row.get("reference_candidate_id") for row in rows]
    if len(ids) != len(set(ids)):
        errors.append("DUPLICATE_REFERENCE_CANDIDATE_ID")
    if len(rows) != 60:
        errors.append("COHORT_SIZE_NOT_60")
    if any(row.get("reference_verdict") != "APPROVED_REFERENCE" for row in rows):
        errors.append("NON_APPROVED_REFERENCE_INCLUDED")
    required = {
        "anchor_id", "key", "reference_candidate_id", "canonical_candidate_id",
        "canonical_concept_name", "response_class", "decision_granularity",
        "decision_signature_v2", "reference_verdict",
    }
    if any(not required.issubset(row) for row in rows):
        errors.append("MISSING_COHORT_FIELD")
    if cohort.get("content_sha256") != canonical_content_hash(cohort):
        errors.append("CONTENT_SHA256_MISMATCH")
    return errors


def validate_evidence_fact(fact: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    required = {
        "evidence_fact_id", "canonical_subject_id", "canonical_subject_name",
        "normalized_clinical_proposition", "feature_roles", "response_class_relevance",
        "population_context", "clinical_stage", "target_subdomain", "source_refs",
        "source_authority", "source_date_or_version", "entailment_review_status",
        "reuse_scope", "content_sha256",
    }
    if not required.issubset(fact):
        errors.append("MISSING_REQUIRED_FIELD")
    roles = set(fact.get("feature_roles", ()))
    if roles - APPROVED_FEATURE_ROLES:
        errors.append("UNKNOWN_FEATURE_ROLE")
    if not fact.get("source_refs"):
        errors.append("MISSING_SOURCE_REF")
    status = fact.get("entailment_review_status")
    if status not in ENTAILMENT_STATUSES:
        errors.append("UNKNOWN_ENTAILMENT_STATUS")
    if status != "ENTAILED" and roles & LOAD_BEARING_FEATURE_ROLES:
        errors.append("NON_ENTAILED_LOAD_BEARING_FACT")
    if fact.get("content_sha256") != canonical_content_hash(fact):
        errors.append("CONTENT_SHA256_MISMATCH")
    return errors


def admit_candidate_to_bundle(
    profile: Mapping[str, Any], registry: Mapping[str, Mapping[str, Any]]
) -> str:
    roles: set[str] = set()
    for fact_id in profile.get("evidence_fact_ids", ()):
        fact = registry.get(str(fact_id))
        if fact and fact.get("entailment_review_status") == "ENTAILED":
            roles.update(fact.get("feature_roles", ()))
    if not roles & {"SHARED_PLAUSIBILITY", "CANDIDATE_SUPPORTING"}:
        return "MISSING_POSITIVE_PLAUSIBILITY"
    if not roles & {"PAIRWISE_DISCRIMINATOR", "HIGH_DISCRIMINATIVE", "ACTION_CHANGING", "EXCLUSIONARY"}:
        return "MISSING_DISCRIMINATOR"
    return "ADMITTED"


def validate_matrix_cell(
    cell: Mapping[str, Any], registry: Mapping[str, Mapping[str, Any]]
) -> list[str]:
    state = cell.get("state")
    if state not in {"PRESENT", "ABSENT", "UNKNOWN", "NOT_APPLICABLE"}:
        return ["UNKNOWN_MATRIX_STATE"]
    fact_ids = cell.get("evidence_fact_ids", ())
    if state != "UNKNOWN" and not fact_ids:
        return ["UNTRACED_NON_UNKNOWN_CELL"]
    if any(
        fact_id not in registry or registry[fact_id].get("entailment_review_status") != "ENTAILED"
        for fact_id in fact_ids
    ):
        return ["NON_ENTAILED_MATRIX_TRACE"]
    return []


def classify_bundle_density(candidate_count: int) -> str:
    if candidate_count >= 4:
        return "STRONG_BUNDLE"
    if candidate_count == 3:
        return "MINIMUM_GENERATABLE"
    if candidate_count:
        return "PARTIAL"
    return "NO_SAFE"


def build_reuse_metrics(facts: list[Mapping[str, Any]]) -> dict[str, int]:
    cross_anchor = 0
    cross_candidate = 0
    pairwise_reused = 0
    for fact in facts:
        scope = fact.get("reuse_scope", {})
        anchors = set(scope.get("anchor_ids", ()))
        candidates = set(scope.get("candidate_context_ids", ()))
        if len(anchors) > 1:
            cross_anchor += 1
        if len(candidates) > 1:
            cross_candidate += 1
        if "PAIRWISE_DISCRIMINATOR" in fact.get("feature_roles", ()) and len(anchors) > 1:
            pairwise_reused += 1
    return {
        "facts_reused_across_anchors": cross_anchor,
        "facts_reused_across_candidates": cross_candidate,
        "pairwise_evidence_reuse": pairwise_reused,
    }


def generation_gate(admitted_candidate_counts: list[int]) -> bool:
    return sum(count >= 3 for count in admitted_candidate_counts) >= 6


def validate_question_evidence_trace(
    question: Mapping[str, Any],
    registry: Mapping[str, Mapping[str, Any]],
    approved_candidate_ids: set[str],
) -> list[str]:
    errors: list[str] = []
    if not set(question.get("selected_candidate_ids", ())).issubset(approved_candidate_ids):
        errors.append("UNAPPROVED_CANDIDATE")
    fact_ids = [
        *question.get("stem_evidence_fact_ids", ()),
        *question.get("rationale_evidence_fact_ids", ()),
    ]
    if any(
        fact_id not in registry or registry[fact_id].get("entailment_review_status") != "ENTAILED"
        for fact_id in fact_ids
    ):
        errors.append("UNKNOWN_OR_NON_ENTAILED_FACT")
    return errors


def validate_development_question_set(rows: list[Mapping[str, Any]]) -> list[str]:
    errors: list[str] = []
    if len(rows) > 12:
        errors.append("MORE_THAN_TWELVE_QUESTIONS")
    discipline_counts: dict[str, int] = {}
    for row in rows:
        discipline = str(row.get("discipline"))
        discipline_counts[discipline] = discipline_counts.get(discipline, 0) + 1
        if int(row.get("retry_count", 0)) != 0:
            errors.append("RETRY_NOT_ALLOWED")
        if sum(value == "LIVE_BUT_INFERIOR" for value in row.get("post_stem_liveness", ())) < 3:
            errors.append("FEWER_THAN_THREE_LIVE_DISTRACTORS")
    if any(count > 2 for count in discipline_counts.values()):
        errors.append("MORE_THAN_TWO_PER_DISCIPLINE")
    return list(dict.fromkeys(errors))
