"""Cheap structural validation before independent semantic seed review."""

from __future__ import annotations

from typing import Any


REQUIRED_REVIEW_FIELDS = (
    "positive_candidate_anchor",
    "inferiority_discriminator",
    "evidence_entailment",
    "population_scope",
    "second_key_analysis",
)


def validate_seed_proposal_pre_review(proposal: dict[str, Any]) -> dict[str, Any]:
    """Reject only deterministic defects; leave clinical merit to a reviewer."""
    if proposal.get("candidate_concept_id") == proposal.get("key_concept_id"):
        raise ValueError("DUPLICATE_OR_ALIAS")
    if proposal.get("response_class") != proposal.get("required_response_class"):
        raise ValueError("WRONG_RESPONSE_CLASS")
    if proposal.get("decision_granularity") != proposal.get(
        "required_decision_granularity"
    ):
        raise ValueError("WRONG_GRANULARITY")
    for field in REQUIRED_REVIEW_FIELDS:
        if not proposal.get(field):
            raise ValueError(f"MISSING_{field.upper()}")
    anchor_refs = proposal["positive_candidate_anchor"].get("evidence_refs") or []
    discriminator_refs = proposal["inferiority_discriminator"].get("evidence_refs") or []
    entailment_refs = proposal["evidence_entailment"].get("evidence_refs") or []
    if not anchor_refs or not discriminator_refs or not entailment_refs:
        raise ValueError("MISSING_EVIDENCE_BINDING")
    if not set(anchor_refs + discriminator_refs) <= set(entailment_refs):
        raise ValueError("EVIDENCE_SCOPE_MISMATCH")
    return {"verdict": "PASS_TO_SEMANTIC_REVIEW"}

