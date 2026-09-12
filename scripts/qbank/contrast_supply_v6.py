"""Deterministic diagnostics and reusable candidate-role discovery for V6.

This module is additive. It never mutates Catalogue V2, Signature V2, the
historical Discovery V5 wave, or the consumed Transfer-18 validation result.
Reference sets are inputs to benchmarks only and are not accepted here.
"""

from __future__ import annotations

from collections import Counter
from typing import Any, Mapping, Sequence

from .contrast_supply_v5 import (
    GENERIC_CONCEPT_LABELS,
    V5_CANDIDATE_BUDGET,
    signatures_v2_compatible,
    validate_decision_signature_v2,
)
from .option_set_admissibility import RESPONSE_CLASS_AXES


V5_FUNNEL_OUTCOMES = (
    "CATALOGUE_IDENTITY",
    "RESPONSE_CLASS",
    "DECISION_GRANULARITY",
    "SIGNATURE_V2",
    "TARGET_SUBDOMAIN",
    "APPLICABILITY_CONTEXT",
    "SEMANTIC_CONTAINMENT",
    "KEY_OR_ALIAS",
    "RANKING_OR_BUDGET",
    "ACCEPTED_TO_CANDIDATE_POOL",
    "OTHER",
)

CANONICAL_RESPONSE_ROLES = frozenset({
    "DIAGNOSIS",
    "INVESTIGATION",
    "MANAGEMENT_ACTION",
    "MEDICATION_OR_THERAPY",
    "PREVENTION",
    "INTERPRETATION",
    "ETHICAL_LEGAL_ACTION",
    "COMMUNICATION_ACTION",
    "OTHER",
})

_AXIS_TO_ROLE = {
    "cardinal_syndrome_capability": "DIAGNOSIS",
    "investigation_purpose": "INVESTIGATION",
    "next_action_class": "MANAGEMENT_ACTION",
    "management_capability": "MANAGEMENT_ACTION",
    "safety_securing_class": "MANAGEMENT_ACTION",
    "explained_phenomenon_class": "INTERPRETATION",
    "value_served": "ETHICAL_LEGAL_ACTION",
    "duty_holder_class": "ETHICAL_LEGAL_ACTION",
}

_ROLE_ALIASES = {
    "DIAGNOSIS": "DIAGNOSIS",
    "DIAGNOSTIC_ENTITY": "DIAGNOSIS",
    "PLAUSIBLE_DIAGNOSTIC_ENTITY": "DIAGNOSIS",
    "INVESTIGATION": "INVESTIGATION",
    "DIAGNOSTIC_TEST": "INVESTIGATION",
    "DIAGNOSTIC_ADVANCEMENT": "INVESTIGATION",
    "MANAGEMENT": "MANAGEMENT_ACTION",
    "MANAGEMENT_ACTION": "MANAGEMENT_ACTION",
    "NEXT_ACTION": "MANAGEMENT_ACTION",
    "NEXT_ACTION_FOR_CURRENT_CARE": "MANAGEMENT_ACTION",
    "MANAGEMENT_STRATEGY_FOR_PRESENTATION": "MANAGEMENT_ACTION",
    "THERAPY": "MANAGEMENT_ACTION",
    "MEDICATION_OR_THERAPY": "MEDICATION_OR_THERAPY",
    "PREVENTION": "PREVENTION",
    "INTERPRETATION": "INTERPRETATION",
    "EXPLANATION_OF_OBSERVED_PHENOMENON": "INTERPRETATION",
    "ETHICAL_ACTION": "ETHICAL_LEGAL_ACTION",
    "LEGAL_ACTION": "ETHICAL_LEGAL_ACTION",
    "LEGAL_DUTY_ACTION": "ETHICAL_LEGAL_ACTION",
    "ETHICAL_LEGAL_ACTION": "ETHICAL_LEGAL_ACTION",
    "COMMUNICATION_ACTION": "COMMUNICATION_ACTION",
    "OTHER": "OTHER",
}


def _aliases(candidate: Mapping[str, Any]) -> set[str]:
    return {
        str(candidate.get("normalized_label", "")).casefold(),
        *(str(value).casefold() for value in candidate.get("aliases", ())),
    }


def _is_generic(candidate: Mapping[str, Any]) -> bool:
    label = str(candidate.get("normalized_label", "")).casefold()
    return bool(candidate.get("generic_concept")) or label in GENERIC_CONCEPT_LABELS


def _response_class_compatible(demanded: str, classes: set[str]) -> bool:
    compatible = {demanded}
    for definition in RESPONSE_CLASS_AXES.values():
        if demanded == definition["generic_token"]:
            compatible.update(definition["tokens"])
            break
    return bool(classes & compatible)


def classify_v5_terminal_outcome(
    candidate: Mapping[str, Any],
    opportunity: Mapping[str, Any],
    candidate_signatures: Mapping[str, Mapping[str, Any]] | None = None,
) -> str:
    """Return the exact earliest V5 terminal outcome for one row/anchor pair."""
    candidate_id = str(candidate["canonical_candidate_id"])
    if _is_generic(candidate):
        return "CATALOGUE_IDENTITY"
    key_aliases = {str(value).casefold() for value in opportunity.get("key_aliases", ())}
    if _aliases(candidate) & key_aliases:
        return "KEY_OR_ALIAS"
    demanded = str(opportunity["demanded_response_class"])
    if not _response_class_compatible(demanded, set(candidate.get("response_classes", ()))):
        return "RESPONSE_CLASS"
    granularity = str(opportunity["decision_granularity"])
    granularities = set(candidate.get("decision_granularities", ()))
    if granularities and granularity not in granularities:
        return "DECISION_GRANULARITY"
    signature = (
        candidate_signatures.get(candidate_id)
        if candidate_signatures is not None
        else candidate.get("decision_signature_v2")
    )
    if signature is None:
        return "SIGNATURE_V2"
    opportunity_signature = validate_decision_signature_v2(opportunity["decision_signature_v2"])
    candidate_signature = validate_decision_signature_v2(signature)
    for field in ("decision_intent", "target_domain", "clinical_stage"):
        if opportunity_signature[field] != candidate_signature[field]:
            return "SIGNATURE_V2"
    if opportunity_signature["target_subdomain"] != candidate_signature["target_subdomain"]:
        return "TARGET_SUBDOMAIN"
    contexts = {str(value) for value in candidate.get("applicability_contexts", ())}
    if str(opportunity["applicability_context"]) not in contexts:
        return "APPLICABILITY_CONTEXT"
    if opportunity_signature["semantic_containment_role"] != candidate_signature["semantic_containment_role"]:
        return "SEMANTIC_CONTAINMENT"
    if candidate.get("contains_candidate_ids") or candidate.get("contained_by_candidate_ids"):
        return "SEMANTIC_CONTAINMENT"
    return "ACCEPTED_TO_CANDIDATE_POOL"


def build_v5_funnel(
    catalogue: Sequence[Mapping[str, Any]],
    opportunities: Sequence[Mapping[str, Any]],
    candidate_signatures: Mapping[str, Mapping[str, Any]] | None = None,
    *,
    budget: int = V5_CANDIDATE_BUDGET,
    frozen_observed_rows: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Reconstruct every V5 row decision, including post-compatibility budget."""
    totals: Counter[str] = Counter()
    per_anchor: list[dict[str, Any]] = []
    for opportunity in opportunities:
        preliminary: list[tuple[Mapping[str, Any], str]] = []
        for candidate in catalogue:
            outcome = classify_v5_terminal_outcome(candidate, opportunity, candidate_signatures)
            preliminary.append((candidate, outcome))
        accepted = [candidate for candidate, outcome in preliminary if outcome == "ACCEPTED_TO_CANDIDATE_POOL"]
        wanted = set(opportunity.get("semantic_families", ()))
        ranked = sorted(
            accepted,
            key=lambda row: (
                0 if wanted & set(row.get("semantic_families", ())) else 1,
                0 if opportunity.get("study_unit_id") in set(row.get("study_unit_ids", ())) else 1,
                0 if opportunity.get("chapter_code") in set(row.get("chapters", ())) else 1,
                str(row["canonical_candidate_id"]),
            ),
        )
        selected_ids = {str(row["canonical_candidate_id"]) for row in ranked[:budget]}
        counts: Counter[str] = Counter()
        for candidate, outcome in preliminary:
            if outcome == "ACCEPTED_TO_CANDIDATE_POOL" and str(candidate["canonical_candidate_id"]) not in selected_ids:
                outcome = "RANKING_OR_BUDGET"
            counts[outcome] += 1
            totals[outcome] += 1
        per_anchor.append({
            "anchor_id": opportunity.get("transfer_id") or opportunity.get("opportunity_id"),
            "demanded_response_class": opportunity["demanded_response_class"],
            "terminal_evaluations": len(catalogue),
            "gate_rejection_counts": {name: counts[name] for name in V5_FUNNEL_OUTCOMES},
        })
    replay = {
        "total_evaluations": len(catalogue) * len(opportunities),
        "gate_rejection_counts": {name: totals[name] for name in V5_FUNNEL_OUTCOMES},
        "per_anchor": per_anchor,
    }
    if frozen_observed_rows is None:
        return replay
    if len(frozen_observed_rows) != len(opportunities):
        raise ValueError("frozen V5 rows do not match opportunity count")
    reason_to_gate = {
        "GENERIC_CONCEPT": "CATALOGUE_IDENTITY",
        "WRONG_RESPONSE_CLASS": "RESPONSE_CLASS",
        "WRONG_GRANULARITY": "DECISION_GRANULARITY",
        "MISSING_CANDIDATE_SIGNATURE": "SIGNATURE_V2",
        "WRONG_DECISION_INTENT": "SIGNATURE_V2",
        "WRONG_TARGET_DOMAIN": "SIGNATURE_V2",
        "WRONG_CLINICAL_STAGE": "SIGNATURE_V2",
        "WRONG_TARGET_SUBDOMAIN": "TARGET_SUBDOMAIN",
        "WRONG_APPLICABILITY_CONTEXT": "APPLICABILITY_CONTEXT",
        "SEMANTIC_CONTAINMENT_MISMATCH": "SEMANTIC_CONTAINMENT",
        "PARENT_SUBTYPE_COLLISION": "SEMANTIC_CONTAINMENT",
        "KEY_ALIAS": "KEY_OR_ALIAS",
    }
    observed_totals: Counter[str] = Counter()
    observed_per_anchor = []
    for opportunity, frozen in zip(opportunities, frozen_observed_rows, strict=True):
        anchor_id = opportunity.get("transfer_id") or opportunity.get("opportunity_id")
        if frozen.get("transfer_id", anchor_id) != anchor_id:
            raise ValueError(f"frozen V5 row order mismatch for {anchor_id}")
        counts: Counter[str] = Counter()
        for reason, count in frozen.get("rejection_counts", {}).items():
            counts[reason_to_gate.get(str(reason), "OTHER")] += int(count)
        accepted = len(frozen.get("candidates", ()))
        counts["ACCEPTED_TO_CANDIDATE_POOL"] += accepted
        scanned = int(frozen.get("scanned", len(catalogue)))
        if sum(counts.values()) != scanned:
            raise ValueError(f"frozen V5 row does not reconcile for {anchor_id}")
        observed_totals.update(counts)
        observed_per_anchor.append({
            "anchor_id": anchor_id,
            "demanded_response_class": opportunity["demanded_response_class"],
            "terminal_evaluations": scanned,
            "gate_rejection_counts": {name: counts[name] for name in V5_FUNNEL_OUTCOMES},
            "source": "FROZEN_CANONICAL_V5_OBSERVATION",
        })
    observed = {name: observed_totals[name] for name in V5_FUNNEL_OUTCOMES}
    return {
        "total_evaluations": sum(row["terminal_evaluations"] for row in observed_per_anchor),
        "gate_rejection_counts": observed,
        "per_anchor": observed_per_anchor,
        "current_code_replay_matches_frozen": observed == replay["gate_rejection_counts"],
        "current_code_replay_gate_rejection_counts": replay["gate_rejection_counts"],
        "reproducibility_note": (
            "The frozen canonical V5 wave stores per-anchor reason counts but not candidate-level "
            "decisions. The current V5 helper admits more generic-axis tokens to later gates than "
            "the frozen observation; canonical observed counts remain authoritative."
        ),
    }


def build_role_inventory(catalogue: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Inventory current V2 role metadata by response-class axis."""
    role_counts: Counter[str] = Counter()
    category_counts: Counter[str] = Counter()
    rows = []
    for candidate in catalogue:
        classes = set(candidate.get("response_classes", ()))
        roles = set()
        unknown = set(classes)
        for axis, definition in RESPONSE_CLASS_AXES.items():
            tokens = set(definition["tokens"]) | {str(definition["generic_token"])}
            if classes & tokens:
                roles.add(_AXIS_TO_ROLE[axis])
                unknown -= tokens
        if not classes:
            category = "untyped"
        elif unknown:
            category = "ambiguous"
        elif len(roles) == 1:
            category = "single_role"
        else:
            category = "multi_role"
        category_counts[category] += 1
        for role in roles:
            role_counts[role] += 1
        rows.append({
            "candidate_id": candidate["canonical_candidate_id"],
            "current_response_classes": sorted(classes),
            "canonical_roles": sorted(roles),
            "inventory_class": category.upper(),
        })
    return {
        "concept_count": len(catalogue),
        "single_role": category_counts["single_role"],
        "multi_role": category_counts["multi_role"],
        "untyped": category_counts["untyped"],
        "ambiguous": category_counts["ambiguous"],
        "canonical_role_counts": dict(sorted(role_counts.items())),
        "rows": rows,
    }


def _ablation_counts(
    catalogue: Sequence[Mapping[str, Any]],
    opportunity: Mapping[str, Any],
    candidate_signatures: Mapping[str, Mapping[str, Any]] | None,
    budget: int,
) -> dict[str, int]:
    current = list(catalogue)
    result = {"A_CATALOGUE_ONLY": len(current)}
    key_aliases = {str(value).casefold() for value in opportunity.get("key_aliases", ())}
    current = [row for row in current if not _is_generic(row) and not (_aliases(row) & key_aliases)]
    current = [row for row in current if _response_class_compatible(str(opportunity["demanded_response_class"]), set(row.get("response_classes", ())))]
    result["B_RESPONSE_CLASS"] = len(current)
    granularity = str(opportunity["decision_granularity"])
    current = [row for row in current if not row.get("decision_granularities") or granularity in set(row["decision_granularities"])]
    result["C_DECISION_GRANULARITY"] = len(current)
    signatures = {}
    for row in current:
        candidate_id = str(row["canonical_candidate_id"])
        signature = candidate_signatures.get(candidate_id) if candidate_signatures is not None else row.get("decision_signature_v2")
        if signature is not None:
            signatures[candidate_id] = validate_decision_signature_v2(signature)
    opportunity_signature = validate_decision_signature_v2(opportunity["decision_signature_v2"])
    current = [row for row in current if str(row["canonical_candidate_id"]) in signatures and all(signatures[str(row["canonical_candidate_id"])][field] == opportunity_signature[field] for field in ("decision_intent", "target_domain", "clinical_stage"))]
    result["D_SIGNATURE_V2"] = len(current)
    current = [row for row in current if signatures[str(row["canonical_candidate_id"])]["target_subdomain"] == opportunity_signature["target_subdomain"]]
    result["E_TARGET_SUBDOMAIN"] = len(current)
    context = str(opportunity["applicability_context"])
    current = [row for row in current if context in set(str(value) for value in row.get("applicability_contexts", ()))]
    result["F_APPLICABILITY"] = len(current)
    current = [row for row in current if signatures[str(row["canonical_candidate_id"])]["semantic_containment_role"] == opportunity_signature["semantic_containment_role"] and not row.get("contains_candidate_ids") and not row.get("contained_by_candidate_ids")]
    result["G_CONTAINMENT"] = len(current)
    result["H_RANKING_OR_BUDGET"] = min(len(current), budget)
    return result


def build_filter_ablation(
    catalogue: Sequence[Mapping[str, Any]],
    opportunities: Sequence[Mapping[str, Any]],
    candidate_signatures: Mapping[str, Mapping[str, Any]] | None = None,
    *,
    budget: int = V5_CANDIDATE_BUDGET,
) -> dict[str, Any]:
    stages = [
        "A_CATALOGUE_ONLY", "B_RESPONSE_CLASS", "C_DECISION_GRANULARITY",
        "D_SIGNATURE_V2", "E_TARGET_SUBDOMAIN", "F_APPLICABILITY",
        "G_CONTAINMENT", "H_RANKING_OR_BUDGET",
    ]
    rows = []
    for opportunity in opportunities:
        counts = _ablation_counts(catalogue, opportunity, candidate_signatures, budget)
        first_collapse = next((stages[index] for index in range(1, len(stages)) if counts[stages[index]] < counts[stages[index - 1]]), None)
        rows.append({
            "anchor_id": opportunity.get("transfer_id") or opportunity.get("opportunity_id"),
            "demanded_response_class": opportunity["demanded_response_class"],
            **counts,
            "first_collapse_gate": first_collapse,
        })
    return {"stages": stages, "rows": rows}


def normalize_response_role(value: str) -> str:
    token = str(value).strip().upper()
    if token in _ROLE_ALIASES:
        return _ROLE_ALIASES[token]
    for axis, definition in RESPONSE_CLASS_AXES.items():
        if token in set(definition["tokens"]):
            return _AXIS_TO_ROLE[axis]
    raise ValueError(f"unknown response role: {value}")


def validate_candidate_role_registry(registry: Mapping[str, Any]) -> dict[str, frozenset[str]]:
    if registry.get("schema_version") != "CANDIDATE_ROLE_REGISTRY_V1":
        raise ValueError("candidate role registry schema mismatch")
    if set(registry.get("controlled_roles", ())) != CANONICAL_RESPONSE_ROLES:
        raise ValueError("candidate role registry controlled vocabulary mismatch")
    result: dict[str, frozenset[str]] = {}
    for entry in registry.get("entries", ()):
        candidate_id = str(entry.get("candidate_id", ""))
        if not candidate_id or candidate_id in result:
            raise ValueError("candidate role registry ids must be non-empty and unique")
        roles = frozenset(str(value) for value in entry.get("roles", ()))
        unknown = roles - CANONICAL_RESPONSE_ROLES
        if unknown:
            raise ValueError(f"unknown response role: {sorted(unknown)[0]}")
        if roles and not entry.get("role_provenance"):
            raise ValueError(f"role provenance is required for {candidate_id}")
        if entry.get("scope") != "GLOBAL":
            raise ValueError("opportunity-specific role scope is forbidden")
        if entry.get("review_status") not in {"APPROVED", "UNTYPED_FAIL_CLOSED"}:
            raise ValueError(f"unapproved role registry entry: {candidate_id}")
        result[candidate_id] = roles
    return result


def discover_global_candidates_v6(
    catalogue: Sequence[Mapping[str, Any]],
    *,
    opportunity: Mapping[str, Any],
    role_registry: Mapping[str, frozenset[str]],
    candidate_metadata: Mapping[str, Mapping[str, Any]],
    budget: int = V5_CANDIDATE_BUDGET,
) -> dict[str, Any]:
    """Retrieve by reusable role metadata while retaining V5 safety filters."""
    if not 1 <= budget <= V5_CANDIDATE_BUDGET:
        raise ValueError(f"candidate budget must be between 1 and {V5_CANDIDATE_BUDGET}")
    demanded_role = normalize_response_role(str(opportunity["demanded_response_class"]))
    opportunity_signature = validate_decision_signature_v2(opportunity["decision_signature_v2"])
    key_aliases = {str(value).casefold() for value in opportunity.get("key_aliases", ())}
    granularity = str(opportunity["decision_granularity"])
    context = str(opportunity["applicability_context"])
    wanted_families = set(opportunity.get("semantic_families", ()))
    rejections = []
    ranked = []

    def reject(candidate_id: str, reason: str) -> None:
        rejections.append({"candidate_id": candidate_id, "reason": reason})

    for original in catalogue:
        candidate_id = str(original["canonical_candidate_id"])
        if _is_generic(original):
            reject(candidate_id, "CATALOGUE_IDENTITY")
            continue
        if _aliases(original) & key_aliases:
            reject(candidate_id, "KEY_ALIAS")
            continue
        if demanded_role not in role_registry.get(candidate_id, frozenset()):
            reject(candidate_id, "WRONG_RESPONSE_ROLE")
            continue
        metadata = candidate_metadata.get(candidate_id)
        if metadata is None:
            reject(candidate_id, "MISSING_CANDIDATE_METADATA")
            continue
        granularities = set(metadata.get("decision_granularities", original.get("decision_granularities", ())))
        if granularities and granularity not in granularities:
            reject(candidate_id, "WRONG_GRANULARITY")
            continue
        signatures = metadata.get("decision_signatures_v2", ())
        compatible_signature = next((signature for signature in signatures if signatures_v2_compatible(opportunity_signature, signature)["compatible"]), None)
        if compatible_signature is None:
            reject(candidate_id, "SIGNATURE_V2")
            continue
        if context not in set(str(value) for value in metadata.get("applicability_contexts", ())):
            reject(candidate_id, "WRONG_APPLICABILITY_CONTEXT")
            continue
        if metadata.get("contains_candidate_ids") or metadata.get("contained_by_candidate_ids"):
            reject(candidate_id, "SEMANTIC_CONTAINMENT")
            continue
        same_unit = opportunity.get("study_unit_id") in set(original.get("study_unit_ids", ()))
        same_chapter = opportunity.get("chapter_code") in set(original.get("chapters", ()))
        family_match = bool(wanted_families & set(original.get("semantic_families", ())))
        row = dict(original)
        row["candidate_roles_v1"] = sorted(role_registry[candidate_id])
        row["decision_signature_v2"] = dict(compatible_signature)
        ranked.append(((0 if family_match else 1, 0 if same_unit else 1, 0 if same_chapter else 1, candidate_id), row))
    compatible = [row for _, row in sorted(ranked, key=lambda item: item[0])]
    return {
        "discovery_v6_version": "GLOBAL_ROLE_REGISTRY_DISCOVERY_V6_1",
        "candidate_budget": budget,
        "global_catalogue_rows_scanned": len(catalogue),
        "compatible_before_budget_count": len(compatible),
        "rejection_counts": dict(sorted(Counter(row["reason"] for row in rejections).items())),
        "rejections": rejections,
        "candidates": compatible[:budget],
    }
