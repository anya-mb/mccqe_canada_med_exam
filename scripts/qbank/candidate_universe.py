"""Deterministic contracts for expanded candidate universes and evidence reuse.

Semantic judgments are inputs to this module.  The code only validates,
deduplicates, admits, and accounts for independently reviewed records.
"""

from __future__ import annotations

from collections import Counter, defaultdict
import hashlib
import json
import statistics
from typing import Any, Iterable, Mapping


ALLOWED_ORIGINS = frozenset({
    "TORONTO_NOTES_DERIVED",
    "CANONICAL_CATALOGUE_DERIVED",
    "EXISTING_RELATION_DERIVED",
    "EXISTING_BUNDLE_DERIVED",
    "GUIDELINE_DERIVED",
    "MODEL_PROPOSED",
    "REVIEWER_PROPOSED",
})
SOURCE_KINDS = frozenset({"SOURCE_DERIVED", "GENERATED"})
STAGE1_VERDICTS = frozenset({"PLAUSIBLE", "REJECTED", "UNCERTAIN"})
STAGE2_VERDICTS = frozenset({"APPROVED", "REJECTED", "UNCERTAIN", "NOT_REVIEWED"})
EVIDENCE_STATUSES = frozenset({
    "MULTI_SOURCE_CONCORDANT",
    "SINGLE_AUTHORITATIVE_SOURCE",
    "ONE_SOURCE_EXCEPTION",
    "ENTAILED",
    "CONFLICTING",
    "INSUFFICIENT",
    "NOT_RESEARCHED",
})
HARD_REVIEW_CEILING = 24


class CandidateUniverseError(ValueError):
    """Raised when an input violates a fail-closed universe contract."""


def canonical_content_hash(value: Mapping[str, Any]) -> str:
    payload = {key: item for key, item in value.items() if key != "content_sha256"}
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def normalize_candidate_text(value: str) -> str:
    return " ".join(str(value).strip().casefold().split())


def _review_verdict(candidate: Mapping[str, Any], stage: int) -> str:
    return str(candidate.get(f"review_stage_{stage}", {}).get("verdict", ""))


def validate_candidate(candidate: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    required = (
        "canonical_candidate_id", "normalized_candidate_text", "candidate_concept",
        "origin", "source_kind", "response_class", "granularity",
        "applicability_context", "proposal_stage", "review_stage_1",
        "evidence_status", "review_stage_2", "second_key_status",
        "pairwise_distinctness",
    )
    for field in required:
        if candidate.get(field) in (None, ""):
            errors.append(f"MISSING_REQUIRED_FIELD:{field}")
    if candidate.get("origin") not in ALLOWED_ORIGINS:
        errors.append("UNKNOWN_OR_MISSING_ORIGIN")
    if candidate.get("source_kind") not in SOURCE_KINDS:
        errors.append("UNKNOWN_SOURCE_KIND")
    if _review_verdict(candidate, 1) not in STAGE1_VERDICTS:
        errors.append("UNKNOWN_STAGE1_VERDICT")
    if _review_verdict(candidate, 2) not in STAGE2_VERDICTS:
        errors.append("UNKNOWN_STAGE2_VERDICT")
    if candidate.get("evidence_status") not in EVIDENCE_STATUSES:
        errors.append("UNKNOWN_EVIDENCE_STATUS")
    return errors


def _admission(candidate: Mapping[str, Any], anchor: Mapping[str, Any]) -> str:
    if _review_verdict(candidate, 1) != "PLAUSIBLE":
        return "REJECTED"
    if _review_verdict(candidate, 2) != "APPROVED":
        return "REJECTED"
    if candidate.get("evidence_status") not in {
        "MULTI_SOURCE_CONCORDANT", "SINGLE_AUTHORITATIVE_SOURCE",
        "ONE_SOURCE_EXCEPTION", "ENTAILED",
    }:
        return "REJECTED"
    if candidate.get("response_class") != anchor.get("response_class"):
        return "REJECTED"
    if candidate.get("granularity") != anchor.get("granularity"):
        return "REJECTED"
    if candidate.get("second_key_status") not in {"NO_IDENTIFIED_RISK", "CONTEXT_CONTROLLED"}:
        return "REJECTED"
    if candidate.get("pairwise_distinctness") not in {"DISTINCT", "CONTEXTUALLY_DISTINCT"}:
        return "REJECTED"
    return "ADMITTED"


def _merge_duplicate(existing: dict[str, Any], incoming: Mapping[str, Any]) -> dict[str, Any]:
    existing["origins"] = sorted(set(existing["origins"]) | {str(incoming["origin"])})
    existing["proposal_ids"] = sorted(
        set(existing.get("proposal_ids", ()))
        | {str(incoming.get("proposal_id", incoming["canonical_candidate_id"]))}
    )
    return existing


def build_candidate_universe(
    anchors: Iterable[Mapping[str, Any]],
    candidates_by_anchor: Mapping[str, Iterable[Mapping[str, Any]]],
    *,
    hard_review_ceiling: int = HARD_REVIEW_CEILING,
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for anchor_input in anchors:
        anchor = dict(anchor_input)
        anchor_id = str(anchor["anchor_id"])
        proposals = [dict(row) for row in candidates_by_anchor.get(anchor_id, ())]
        if len(proposals) > hard_review_ceiling:
            raise CandidateUniverseError(
                f"anchor {anchor_id} exceeds hard review ceiling {hard_review_ceiling}"
            )
        invalid = [(row, validate_candidate(row)) for row in proposals]
        invalid = [(row, errors) for row, errors in invalid if errors]
        if invalid:
            raise CandidateUniverseError(f"invalid candidate; origin and review fields required: {invalid[0][1]}")
        proposals.sort(key=lambda row: (int(row["proposal_stage"]), str(row["canonical_candidate_id"])))
        deduplicated: dict[str, dict[str, Any]] = {}
        for proposal in proposals:
            normalized = normalize_candidate_text(proposal["normalized_candidate_text"])
            if normalized in deduplicated:
                _merge_duplicate(deduplicated[normalized], proposal)
                continue
            proposal["normalized_candidate_text"] = normalized
            proposal["origins"] = [proposal.pop("origin")]
            proposal["proposal_ids"] = [str(proposal.get("proposal_id", proposal["canonical_candidate_id"]))]
            proposal["final_admission_state"] = _admission(proposal, anchor)
            deduplicated[normalized] = proposal
        candidates = sorted(deduplicated.values(), key=lambda row: row["canonical_candidate_id"])
        rows.append({
            **anchor,
            "candidate_universe_id": anchor_id,
            "hard_review_ceiling": hard_review_ceiling,
            "saturation_stop": anchor.get("saturation_stop", "SOURCE_POOL_FROZEN_AND_REMAINING_PROPOSALS_REVIEWED"),
            "candidates": candidates,
        })
    result = {"schema_version": "ANCHOR_CANDIDATE_UNIVERSE_V1", "anchors": rows}
    result["content_sha256"] = canonical_content_hash(result)
    return result


def candidate_density_metrics(universe: Mapping[str, Any]) -> dict[str, Any]:
    sizes = [
        sum(row.get("final_admission_state") == "ADMITTED" for row in anchor["candidates"])
        for anchor in universe["anchors"]
    ]
    summary = {
        "min": min(sizes, default=0),
        "median": statistics.median(sizes) if sizes else 0,
        "mean": round(statistics.mean(sizes), 2) if sizes else 0.0,
        "max": max(sizes, default=0),
    }
    return {
        "approved_sizes": summary,
        "thresholds": {str(value): sum(size >= value for size in sizes) for value in (3, 4, 5, 6, 8, 10, 12, 16, 20)},
    }


def build_concept_cards(
    registry: Mapping[str, Any], candidates: Iterable[Mapping[str, Any]]
) -> dict[str, Any]:
    candidate_by_concept = {str(row["canonical_candidate_id"]): row for row in candidates}
    facts_by_concept: defaultdict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for fact in registry.get("facts", ()):
        concept_id = str(fact["canonical_subject_id"])
        if concept_id in candidate_by_concept and fact.get("entailment_review_status") == "ENTAILED":
            facts_by_concept[concept_id].append(fact)
    cards = []
    for concept_id in sorted(candidate_by_concept):
        candidate = candidate_by_concept[concept_id]
        facts = sorted(facts_by_concept.get(concept_id, ()), key=lambda row: row["evidence_fact_id"])
        source_refs = sorted({ref for fact in facts for ref in fact.get("source_refs", ())})
        anchors = sorted({anchor for fact in facts for anchor in fact.get("reuse_scope", {}).get("anchor_ids", ())})
        contexts = sorted({context for fact in facts for context in fact.get("reuse_scope", {}).get("candidate_context_ids", ())})
        populations = sorted({item for fact in facts for item in fact.get("population_context", ())})
        stages = sorted({item for fact in facts for item in fact.get("clinical_stage", ())})
        roles = {role for fact in facts for role in fact.get("feature_roles", ())}
        response_class = str(candidate.get("response_class", ""))
        if response_class in {"MANAGEMENT_ACTION", "INVESTIGATION", "ETHICAL_LEGAL_ACTION"} and "WHAT_MAKES_CANDIDATE_CORRECT" in roles:
            next_step_status = "AVAILABLE"
            next_step_kind = "NEXT_ACTION_IF_THIS_CONTEXT_WERE_PRESENT"
        elif response_class == "DIAGNOSIS":
            next_step_status = "MISSING"
            next_step_kind = "NEXT_STEP_IF_CANDIDATE_CORRECT"
        else:
            next_step_status = "NOT_APPLICABLE"
            next_step_kind = None
        verification = (
            "MULTI_SOURCE_CONCORDANT" if len(source_refs) >= 2
            else "SINGLE_AUTHORITATIVE_SOURCE" if len(source_refs) == 1
            else "INSUFFICIENT"
        )
        cards.append({
            "concept_id": concept_id,
            "concept_name": candidate.get("candidate_concept", candidate.get("canonical_concept_name")),
            "response_class": response_class,
            "evidence_fact_ids": [row["evidence_fact_id"] for row in facts],
            "facts": [
                {
                    "evidence_fact_id": row["evidence_fact_id"],
                    "feature_roles": row["feature_roles"],
                    "anchor_ids": sorted(set(row.get("reuse_scope", {}).get("anchor_ids", ()))),
                    "candidate_context_ids": sorted(set(row.get("reuse_scope", {}).get("candidate_context_ids", ()))),
                }
                for row in facts
            ],
            "source_refs": source_refs,
            "feature_roles": sorted(roles),
            "applicability_scope": {"population_context": populations, "clinical_stage": stages},
            "reuse_scope": {"anchor_ids": anchors, "candidate_context_ids": contexts},
            "multi_source_verification": verification,
            "next_step_status": next_step_status,
            "next_step_kind": next_step_kind,
        })
    result = {"schema_version": "CONCEPT_FEATURE_CARD_V1", "cards": cards}
    result["content_sha256"] = canonical_content_hash(result)
    return result


def _rejection_relation(candidate: Mapping[str, Any]) -> str | None:
    codes = set(candidate.get("review_stage_1", {}).get("reason_codes", ())) | set(
        candidate.get("review_stage_2", {}).get("reason_codes", ())
    )
    if codes & {"ALIAS_KEY", "ALIAS", "DUPLICATE_KEY"}:
        return "ALIAS_OF"
    if codes & {"NESTED_ACTION", "KEY_SUBTYPE", "KEY_SUPERTYPE", "PARENT_OF", "SUBTYPE_OF"}:
        return "SECOND_KEY_RISK"
    if codes & {"CO_KEY_RISK", "SECOND_KEY_RISK", "CONCURRENT_MANDATORY_ACTION"}:
        return "SECOND_KEY_RISK"
    return None


def build_compatibility_graph(
    universe: Mapping[str, Any],
    discriminator_fact_ids: Mapping[str, Iterable[str]],
) -> dict[str, Any]:
    nodes: dict[str, dict[str, Any]] = {}
    edge_map: dict[tuple[str, str, str], dict[str, Any]] = {}
    for anchor in universe["anchors"]:
        key_id = str(anchor["key"]["canonical_identity"])
        nodes[key_id] = {"node_id": key_id, "label": anchor["key"]["label"], "kind": "KEY_OR_CANDIDATE"}
        for candidate in anchor["candidates"]:
            candidate_id = str(candidate["canonical_candidate_id"])
            nodes[candidate_id] = {"node_id": candidate_id, "label": candidate["candidate_concept"], "kind": "KEY_OR_CANDIDATE"}
            if candidate.get("final_admission_state") == "ADMITTED" and discriminator_fact_ids.get(candidate_id):
                relation = "KEY_SUPERIOR_UNDER_CONTEXT"
            else:
                relation = _rejection_relation(candidate)
            if relation is None:
                continue
            edge_key = (key_id, candidate_id, relation)
            if edge_key not in edge_map:
                edge_map[edge_key] = {
                    "edge_id": "EDGE-" + hashlib.sha256("|".join(edge_key).encode()).hexdigest()[:16].upper(),
                    "from_node": key_id,
                    "to_node": candidate_id,
                    "relation": relation,
                    "anchor_ids": [],
                    "evidence_fact_ids": sorted(set(discriminator_fact_ids.get(candidate_id, ()))),
                    "review_status": "REVIEWED",
                    "reuse_count": 0,
                }
            edge_map[edge_key]["anchor_ids"].append(anchor["anchor_id"])
            edge_map[edge_key]["reuse_count"] += 1
    edges = sorted(edge_map.values(), key=lambda row: row["edge_id"])
    result = {"schema_version": "CANDIDATE_COMPATIBILITY_GRAPH_V1", "nodes": sorted(nodes.values(), key=lambda row: row["node_id"]), "edges": edges}
    result["content_sha256"] = canonical_content_hash(result)
    return result


def evidence_economy_metrics(
    cards: Mapping[str, Any], graph: Mapping[str, Any], *, new_evidence_requests: int
) -> dict[str, int]:
    facts = {fact_id for card in cards.get("cards", ()) for fact_id in card.get("evidence_fact_ids", ())}
    return {
        "feature_facts_total": len(facts),
        "feature_facts_reused_across_anchors": sum(
            len(set(fact.get("anchor_ids", ()))) > 1
            for card in cards.get("cards", ()) for fact in card.get("facts", ())
        ),
        "feature_facts_reused_across_candidates": sum(
            len(set(fact.get("candidate_context_ids", ()))) > 1
            for card in cards.get("cards", ()) for fact in card.get("facts", ())
        ),
        "pairwise_edges_total": len(graph.get("edges", ())),
        "pairwise_edges_reused": sum(int(edge.get("reuse_count", 0)) > 1 for edge in graph.get("edges", ())),
        "new_evidence_requests": int(new_evidence_requests),
    }
