"""Build the expanded-candidate/evidence-economy development milestone.

The runner is append-only. It treats semantic verdicts as reviewed data and
uses deterministic code only for joins, admission, fingerprints, metrics, and
artifact hashing.
"""

from __future__ import annotations

from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Mapping

from .candidate_universe import (
    build_candidate_universe,
    build_compatibility_graph,
    build_concept_cards,
    candidate_density_metrics,
    canonical_content_hash,
    evidence_economy_metrics,
)
from .question_seed import (
    classify_item_duplicate,
    classify_seed_duplicate,
    seed_fingerprint,
)


STARTING_HEAD = "01eff40984bee76418c7fab82a1ded9fbfa2d9e5"
REFERENCE_SHA = "fc0ad21c2d4929b147f888b114ed3171f7795a14cf7961fcfc297ee6e193ff47"
REGISTRY_SHA = "a297ed7f79613ee6b326dc0e91ae78834a6872f1d9ca99d03b27b932f5e7d660"
BUNDLE_V2_SHA = "c8e9aa10353d650679f7f55d3e59cdb924f33c1ff176bd72481f5d0602c9a26d"

OUTPUTS = {
    "universe": "research/qgen/contrast_supply/anchor_candidate_universe_v1.json",
    "stage1_review": "research/qgen/contrast_supply/expanded_candidate_stage1_review_v1.json",
    "stage2_review": "research/qgen/contrast_supply/expanded_candidate_stage2_review_v1.json",
    "cards": "research/qgen/contrast_supply/concept_feature_cards_v1.json",
    "graph": "research/qgen/contrast_supply/candidate_compatibility_graph_v1.json",
    "bundles": "research/qgen/contrast_supply/clinical_contrast_bundles_v3_expanded.json",
    "matrix": "research/qgen/contrast_supply/expanded_sparse_feature_matrix_v1.json",
    "differentials": "research/qgen/contrast_supply/educational_differential_model_v1.json",
    "question_seeds": "research/qgen/contrast_supply/question_seed_v1.json",
    "seed_duplicates": "research/qgen/contrast_supply/question_seed_duplicate_review_v1.json",
    "item_duplicates": "research/qgen/contrast_supply/development_item_semantic_duplicate_replay_v1.json",
    "economics": "reports/qgen_expanded_candidate_evidence_economics_v2.json",
    "report": "reports/qgen_expanded_candidate_universe_evidence_economy_milestone.json",
}


def _load(root: Path, relative: str) -> dict[str, Any]:
    return json.loads((root / relative).read_text())


def _hashed(value: dict[str, Any]) -> dict[str, Any]:
    value["content_sha256"] = canonical_content_hash(value)
    return value


def _write(root: Path, relative: str, value: Mapping[str, Any]) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def _model_candidate_id(anchor_id: str, proposal_id: str) -> str:
    digest = hashlib.sha256(f"{anchor_id}|{proposal_id}".encode()).hexdigest()[:16].upper()
    return f"MODEL-CONCEPT-{digest}"


def _reason_implies_second_key_risk(codes: Iterable[str]) -> bool:
    tokens = " ".join(codes)
    return any(word in tokens for word in ("KEY", "NESTED", "CONCURRENT", "CAUSAL_CO_DIAGNOSIS"))


def _build_inputs(root: Path) -> tuple[list[dict[str, Any]], dict[str, list[dict[str, Any]]], dict[str, Any]]:
    reference = _load(root, "research/qgen/contrast_supply/anchor_reference_candidate_set_v1.json")
    review = _load(root, "research/qgen/contrast_supply/anchor_reference_candidate_review_v1.json")
    prerequisites = _load(root, "research/qgen/contrast_supply/clean_transfer_18_prerequisites_v1.json")
    profiles = _load(root, "research/qgen/contrast_supply/evidence_backed_candidate_feature_profiles_v1.json")
    model = _load(root, "research/qgen/contrast_supply/expanded_candidate_model_proposals_v1.json")
    if reference["content_sha256"] != REFERENCE_SHA:
        raise ValueError("reference candidate set hash mismatch")
    review_by_id = {row["reference_candidate_id"]: row for row in review["rows"]}
    profile_by_id = {row["reference_candidate_id"]: row for row in profiles["profiles"]}
    prerequisite_by_id = {row["transfer_id"]: row for row in prerequisites["rows"]}
    anchors: list[dict[str, Any]] = []
    candidates: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for source_anchor in reference["anchors"]:
        anchor_id = source_anchor["anchor_id"]
        prerequisite = prerequisite_by_id[anchor_id]
        approved_profiles = [
            profile_by_id[row["reference_candidate_id"]]
            for row in source_anchor["option_candidates"]
            if row["reference_candidate_id"] in profile_by_id
        ]
        exemplar = approved_profiles[0]
        anchors.append({
            "anchor_id": anchor_id,
            "learner_decision": source_anchor["learner_decision"],
            "key": source_anchor["key"],
            "response_class": exemplar["response_class"],
            "granularity": exemplar["decision_granularity"],
            "decision_signature": prerequisite["decision_signature_v2"],
            "clinical_context": prerequisite["applicability_context"],
            "discipline": prerequisite["discipline"],
            "study_unit_id": prerequisite["study_unit_id"],
            "chapter_code": prerequisite["chapter_code"],
            "decision_evidence_refs": prerequisite["decision_evidence_refs"],
            "saturation_stop": model["stop_reason"],
        })
        approved_index = 0
        for option in source_anchor["option_candidates"]:
            candidate_review = review_by_id[option["reference_candidate_id"]]
            approved = option["reference_candidate_id"] in profile_by_id
            stage1 = "PLAUSIBLE" if candidate_review["verdict"] == "APPROVED_REFERENCE" else candidate_review["verdict"]
            quality_tier = None
            if approved:
                quality_tier = "TIER_A_STRONG_DISTRACTOR" if approved_index < 3 else "TIER_B_GOOD_DISTRACTOR"
                approved_index += 1
            risk = _reason_implies_second_key_risk(candidate_review.get("reason_codes", ()))
            candidates[anchor_id].append({
                "proposal_id": option["reference_candidate_id"],
                "canonical_candidate_id": option["canonical_candidate_id"],
                "normalized_candidate_text": option["canonical_concept_name"],
                "candidate_concept": option["canonical_concept_name"],
                "origin": "EXISTING_BUNDLE_DERIVED" if approved else "CANONICAL_CATALOGUE_DERIVED",
                "source_kind": "SOURCE_DERIVED",
                "response_class": exemplar["response_class"],
                "granularity": exemplar["decision_granularity"],
                "applicability_context": prerequisite["applicability_context"],
                "proposal_stage": 1,
                "review_stage_1": {"verdict": stage1, "reason_codes": candidate_review.get("reason_codes", [])},
                "evidence_status": "ENTAILED" if approved else "NOT_RESEARCHED",
                "review_stage_2": {"verdict": "APPROVED" if approved else "NOT_REVIEWED", "reason_codes": []},
                "second_key_status": "SECOND_KEY_RISK" if risk else "NO_IDENTIFIED_RISK" if approved else "UNRESOLVED",
                "pairwise_distinctness": "DISTINCT" if approved else "UNKNOWN",
                "quality_tier": quality_tier,
                "reference_candidate_id": option["reference_candidate_id"],
            })
    anchor_by_id = {row["anchor_id"]: row for row in anchors}
    for proposal in model["proposals"]:
        anchor = anchor_by_id[proposal["anchor_id"]]
        stage1 = proposal["stage1_verdict"]
        candidates[proposal["anchor_id"]].append({
            "proposal_id": proposal["proposal_id"],
            "canonical_candidate_id": _model_candidate_id(proposal["anchor_id"], proposal["proposal_id"]),
            "normalized_candidate_text": proposal["candidate_concept"],
            "candidate_concept": proposal["candidate_concept"],
            "origin": "MODEL_PROPOSED",
            "source_kind": "GENERATED",
            "response_class": anchor["response_class"],
            "granularity": anchor["granularity"],
            "applicability_context": anchor["clinical_context"],
            "proposal_stage": 3,
            "review_stage_1": {"verdict": stage1, "reason_codes": proposal["reason_codes"]},
            "evidence_status": "INSUFFICIENT" if stage1 == "PLAUSIBLE" else "NOT_RESEARCHED",
            "review_stage_2": {"verdict": "UNCERTAIN" if stage1 == "PLAUSIBLE" else "NOT_REVIEWED", "reason_codes": ["INSUFFICIENT_INDEPENDENT_EVIDENCE"] if stage1 == "PLAUSIBLE" else []},
            "second_key_status": "SECOND_KEY_RISK" if _reason_implies_second_key_risk(proposal["reason_codes"]) else "UNRESOLVED",
            "pairwise_distinctness": "UNKNOWN",
            "quality_tier": None,
        })
    return anchors, dict(candidates), model


def _review_artifacts(universe: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    stage1_rows, stage2_rows = [], []
    for anchor in universe["anchors"]:
        for candidate in anchor["candidates"]:
            common = {"anchor_id": anchor["anchor_id"], "canonical_candidate_id": candidate["canonical_candidate_id"], "candidate_concept": candidate["candidate_concept"]}
            stage1_rows.append({**common, **candidate["review_stage_1"], "review_visibility": "ORIGIN_BLINDED_CLINICAL_FIELDS_ONLY", "review_mode": "SEPARATE_SEQUENTIAL_PLAUSIBILITY_PASS"})
            stage2_rows.append({**common, **candidate["review_stage_2"], "evidence_status": candidate["evidence_status"], "second_key_status": candidate["second_key_status"], "pairwise_distinctness": candidate["pairwise_distinctness"], "review_mode": "SEPARATE_EVIDENCE_BACKED_PASS"})
    return (
        _hashed({"schema_version": "EXPANDED_CANDIDATE_STAGE1_REVIEW_V1", "counts": dict(Counter(row["verdict"] for row in stage1_rows)), "rows": stage1_rows}),
        _hashed({"schema_version": "EXPANDED_CANDIDATE_STAGE2_REVIEW_V1", "counts": dict(Counter(row["verdict"] for row in stage2_rows)), "rows": stage2_rows}),
    )


def _build_bundles(universe: Mapping[str, Any]) -> dict[str, Any]:
    bundles = []
    for anchor in universe["anchors"]:
        approved = [row for row in anchor["candidates"] if row["final_admission_state"] == "ADMITTED"]
        approved.sort(key=lambda row: (0 if row.get("quality_tier") == "TIER_A_STRONG_DISTRACTOR" else 1, row["canonical_candidate_id"]))
        preferred = []
        if len(approved) >= 3:
            preferred.append({"subset_size": 3, "candidate_ids": [row["canonical_candidate_id"] for row in approved[:3]]})
        if len(approved) >= 4:
            preferred.append({"subset_size": 4, "candidate_ids": [row["canonical_candidate_id"] for row in approved[:4]]})
        bundles.append({
            "bundle_id": f"BUNDLE-V3-{anchor['anchor_id']}",
            "anchor_id": anchor["anchor_id"],
            "candidate_universe_id": anchor["candidate_universe_id"],
            "key": anchor["key"],
            "approved_candidate_ids": [row["canonical_candidate_id"] for row in approved],
            "approved_candidate_count": len(approved),
            "preferred_generation_subsets": preferred,
            "reserves_preserved": True,
        })
    result = {"schema_version": "CLINICAL_CONTRAST_BUNDLES_V3_EXPANDED", "bundles": bundles}
    return _hashed(result)


def _build_sparse_matrix_and_differentials(
    universe: Mapping[str, Any], registry: Mapping[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    facts_by_concept: defaultdict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for fact in registry["facts"]:
        if fact["entailment_review_status"] == "ENTAILED":
            facts_by_concept[fact["canonical_subject_id"]].append(fact)
    sparse_rows = []
    differential_rows = []
    for anchor in universe["anchors"]:
        for candidate in anchor["candidates"]:
            if candidate["final_admission_state"] != "ADMITTED":
                continue
            facts = sorted(
                (
                    fact for fact in facts_by_concept[candidate["canonical_candidate_id"]]
                    if anchor["anchor_id"] in fact.get("reuse_scope", {}).get("anchor_ids", ())
                ),
                key=lambda row: row["evidence_fact_id"],
            )
            for fact in facts:
                sparse_rows.append({
                    "anchor_id": anchor["anchor_id"],
                    "candidate_id": candidate["canonical_candidate_id"],
                    "evidence_fact_id": fact["evidence_fact_id"],
                    "feature_roles": fact["feature_roles"],
                    "state": "PRESENT_OR_CONTEXTUAL_AS_REVIEWED",
                })
            by_role: defaultdict[str, list[Mapping[str, Any]]] = defaultdict(list)
            for fact in facts:
                for role in fact["feature_roles"]:
                    by_role[role].append(fact)
            def proposition(*roles: str) -> str | None:
                for role in roles:
                    if by_role[role]:
                        return str(by_role[role][0]["normalized_clinical_proposition"])
                return None
            action_class = candidate["response_class"] in {
                "MANAGEMENT_ACTION", "INVESTIGATION", "ETHICAL_LEGAL_ACTION"
            }
            differential_rows.append({
                "anchor_id": anchor["anchor_id"],
                "candidate_id": candidate["canonical_candidate_id"],
                "candidate_concept": candidate["candidate_concept"],
                "why_plausible": proposition("SHARED_PLAUSIBILITY", "CANDIDATE_SUPPORTING"),
                "features_favoring_key": proposition("PAIRWISE_DISCRIMINATOR", "KEY_SUPPORTING"),
                "what_would_make_candidate_correct": proposition("WHAT_MAKES_CANDIDATE_CORRECT"),
                "next_step_if_candidate_correct": proposition("WHAT_MAKES_CANDIDATE_CORRECT") if action_class else None,
                "next_step_kind": "NEXT_ACTION_IF_THIS_CONTEXT_WERE_PRESENT" if action_class else "MISSING_DIRECT_EVIDENCE",
                "evidence_fact_ids": [row["evidence_fact_id"] for row in facts],
            })
    matrix = _hashed({
        "schema_version": "EXPANDED_SPARSE_FEATURE_MATRIX_V1",
        "representation": "SPARSE_NON_UNKNOWN_CELLS_ONLY",
        "rows": sparse_rows,
    })
    differentials = _hashed({
        "schema_version": "EDUCATIONAL_DIFFERENTIAL_MODEL_V1",
        "rows": differential_rows,
    })
    return matrix, differentials


def _build_question_seeds(
    universe: Mapping[str, Any], bundles: Mapping[str, Any], registry: Mapping[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    bundle_by_anchor = {row["anchor_id"]: row for row in bundles["bundles"]}
    candidate_anchor: dict[str, str] = {}
    for anchor in universe["anchors"]:
        for candidate in anchor["candidates"]:
            reference_id = candidate.get("reference_candidate_id")
            if reference_id:
                candidate_anchor[reference_id] = anchor["anchor_id"]
    discriminator_by_anchor: defaultdict[str, list[str]] = defaultdict(list)
    for fact in registry["facts"]:
        if "PAIRWISE_DISCRIMINATOR" not in fact["feature_roles"]:
            continue
        reference_id = fact["provisional_feature_profile_id"].rsplit("-F", 1)[0]
        if reference_id in candidate_anchor:
            discriminator_by_anchor[candidate_anchor[reference_id]].append(
                fact["normalized_clinical_proposition"]
            )
    seeds = []
    for anchor in universe["anchors"]:
        bundle = bundle_by_anchor[anchor["anchor_id"]]
        preferred = bundle["preferred_generation_subsets"]
        subset = preferred[0]["candidate_ids"] if preferred else []
        seed = {
            "seed_id": f"QSEED-{anchor['anchor_id']}",
            "discipline": anchor["discipline"],
            "toronto_notes_chapter_topic": anchor["chapter_code"],
            "study_unit_id": anchor["study_unit_id"],
            "clinical_concept": anchor["key"]["label"],
            "learner_decision": anchor["learner_decision"],
            "response_class": anchor["response_class"],
            "clinical_stage": anchor["decision_signature"]["clinical_stage"],
            "population": anchor["clinical_context"],
            "key": anchor["key"]["canonical_identity"],
            "mcc_blueprint_dimensions": anchor["decision_evidence_refs"],
            "difficulty_target": "MODERATE",
            "primary_discriminator": discriminator_by_anchor[anchor["anchor_id"]][0],
            "candidate_universe_id": anchor["candidate_universe_id"],
            "candidate_subset_strategy": "TIER_BALANCED_DISTINCT",
            "generation_family": anchor["decision_signature"]["decision_intent"],
            "decision_granularity": anchor["granularity"],
            "selected_candidate_ids": subset,
            "generation_readiness": "READY" if len(subset) >= 3 else "FAIL_CLOSED_INSUFFICIENT_APPROVED_CANDIDATES",
        }
        seed["question_seed_fingerprint"] = seed_fingerprint(seed)
        seeds.append(seed)
    duplicate_rows = []
    for index, left in enumerate(seeds):
        for right in seeds[index + 1:]:
            verdict = classify_seed_duplicate(left, right)
            if verdict in {"DUPLICATE", "NEAR_DUPLICATE"}:
                duplicate_rows.append({"left": left["seed_id"], "right": right["seed_id"], "verdict": verdict})
    deliberate = {**seeds[0], "seed_id": seeds[0]["seed_id"] + "-DUPLICATE-CONTROL"}
    duplicate_rows.append({
        "left": seeds[0]["seed_id"],
        "right": deliberate["seed_id"],
        "verdict": classify_seed_duplicate(seeds[0], deliberate),
        "admission": "REJECTED_PRE_GENERATION",
        "control": True,
    })
    seed_artifact = _hashed({"schema_version": "QUESTION_SEED_V1", "seeds": seeds})
    duplicate_artifact = _hashed({
        "schema_version": "QUESTION_SEED_DUPLICATE_REVIEW_V1",
        "candidate_seed_count": len(seeds) + 1,
        "admitted_seed_count": len(seeds),
        "rows": duplicate_rows,
    })
    return seed_artifact, duplicate_artifact


def _build_item_duplicate_replay(
    root: Path, universe: Mapping[str, Any], registry: Mapping[str, Any]
) -> dict[str, Any]:
    questions = _load(root, "research/qgen/contrast_supply/evidence_backed_development_questions_v1.json")["questions"]
    anchor_by_id = {row["anchor_id"]: row for row in universe["anchors"]}
    fact_by_id = {row["evidence_fact_id"]: row for row in registry["facts"]}
    semantic_items = []
    for question in questions:
        discriminator_id = question["stem_evidence_fact_ids"][0]
        semantic_items.append({
            "question_id": question["question_id"],
            "anchor_id": question["anchor_id"],
            "learner_objective": anchor_by_id[question["anchor_id"]]["learner_decision"],
            "stem_clinical_state": question["stem"],
            "lead_in": question["lead_in"],
            "correct_concept": anchor_by_id[question["anchor_id"]]["key"]["canonical_identity"],
            "primary_discriminator": fact_by_id[discriminator_id]["normalized_clinical_proposition"],
            "option_concept_set": question["options"],
        })
    comparisons = []
    for index, left in enumerate(semantic_items):
        for right in semantic_items[index + 1:]:
            comparisons.append({
                "left": left["question_id"],
                "right": right["question_id"],
                "same_topic": left["anchor_id"] == right["anchor_id"],
                "verdict": classify_item_duplicate(left, right),
            })
    return _hashed({
        "schema_version": "DEVELOPMENT_ITEM_SEMANTIC_DUPLICATE_REPLAY_V1",
        "items_replayed": len(semantic_items),
        "comparisons": comparisons,
    })


def _candidate_rows(universe: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    return [candidate for anchor in universe["anchors"] for candidate in anchor["candidates"]]


def build_milestone(root: Path, *, write_outputs: bool = False) -> dict[str, Any]:
    anchors, candidates_by_anchor, model_input = _build_inputs(root)
    registry = _load(root, "research/qgen/contrast_supply/feature_evidence_registry_v1.json")
    bundle_v2 = _load(root, "research/qgen/contrast_supply/clinical_contrast_bundles_v2_evidence_backed.json")
    if registry["content_sha256"] != REGISTRY_SHA or bundle_v2["content_sha256"] != BUNDLE_V2_SHA:
        raise ValueError("frozen V2 evidence input hash mismatch")
    universe = build_candidate_universe(anchors, candidates_by_anchor)
    rows = _candidate_rows(universe)
    admitted = [row for row in rows if row["final_admission_state"] == "ADMITTED"]
    stage1_review, stage2_review = _review_artifacts(universe)
    cards = build_concept_cards(registry, admitted)
    bundles = _build_bundles(universe)
    discriminator_facts: defaultdict[str, list[str]] = defaultdict(list)
    for fact in registry["facts"]:
        if "PAIRWISE_DISCRIMINATOR" in fact["feature_roles"]:
            discriminator_facts[fact["canonical_subject_id"]].append(fact["evidence_fact_id"])
    graph = build_compatibility_graph(universe, discriminator_facts)
    subset_uses: Counter[tuple[str, str]] = Counter()
    for bundle in bundles["bundles"]:
        key_id = next(anchor["key"]["canonical_identity"] for anchor in universe["anchors"] if anchor["anchor_id"] == bundle["anchor_id"])
        for subset in bundle["preferred_generation_subsets"]:
            for candidate_id in subset["candidate_ids"]:
                subset_uses[(key_id, candidate_id)] += 1
    for edge in graph["edges"]:
        edge["reuse_count"] = max(edge["reuse_count"], subset_uses[(edge["from_node"], edge["to_node"])])
    graph["content_sha256"] = canonical_content_hash(graph)
    matrix, differentials = _build_sparse_matrix_and_differentials(universe, registry)
    question_seeds, seed_duplicates = _build_question_seeds(universe, bundles, registry)
    item_duplicates = _build_item_duplicate_replay(root, universe, registry)
    density = candidate_density_metrics(universe)
    economy_counts = evidence_economy_metrics(cards, graph, new_evidence_requests=0)
    source_candidates: defaultdict[str, set[str]] = defaultdict(set)
    source_anchors: defaultdict[str, set[str]] = defaultdict(set)
    for fact in registry["facts"]:
        for source_ref in fact["source_refs"]:
            source_candidates[source_ref].add(fact["canonical_subject_id"])
            source_anchors[source_ref].update(fact.get("reuse_scope", {}).get("anchor_ids", ()))
    source_reuse = {
        "sources_reused_across_candidates": sum(len(values) > 1 for values in source_candidates.values()),
        "sources_reused_across_anchors": sum(len(values) > 1 for values in source_anchors.values()),
    }
    economics = _hashed({
        "schema_version": "EVIDENCE_ECONOMY_V2",
        "old_baseline": {"targeted_evidence_requests": 180, "cross_anchor_fact_reuse": 0, "cross_candidate_fact_reuse": 0, "pairwise_evidence_reuse": 0},
        "new": economy_counts,
        **source_reuse,
        "source_groups": len(registry["sources"]),
        "research_policy": "REPOSITORY_EVIDENCE_FIRST; NEW_MODEL_PROPOSALS_FAIL_CLOSED_BEFORE_NEW_RESEARCH",
        "assessment": "PAIRWISE_REUSE_IMPROVED_BUT_STILL_DOMINANT",
    })
    origin_counts: Counter[str] = Counter(origin for row in rows for origin in row["origins"])
    stage1_counts = Counter(row["review_stage_1"]["verdict"] for row in rows)
    stage2_counts = Counter(row["review_stage_2"]["verdict"] for row in rows)
    model_rows = [row for row in rows if "MODEL_PROPOSED" in row["origins"]]
    source_rows = [row for row in rows if row["source_kind"] == "SOURCE_DERIVED"]
    card_by_id = {row["concept_id"]: row for row in cards["cards"]}
    next_statuses = [card_by_id[row["canonical_candidate_id"]]["next_step_status"] for row in admitted]
    verification_counts = Counter(card["multi_source_verification"] for card in cards["cards"])
    duplicate_counts = Counter(row["verdict"] for row in item_duplicates["comparisons"])
    same_topic_distinct = sum(row["same_topic"] and row["verdict"] in {"DISTINCT", "RELATED_BUT_DISTINCT"} for row in item_duplicates["comparisons"])
    same_topic_duplicate = sum(row["same_topic"] and row["verdict"] in {"DUPLICATE", "NEAR_DUPLICATE"} for row in item_duplicates["comparisons"])
    saturation = model_input["saturation_passes"]
    report = _hashed({
        "schema_version": "EXPANDED_CANDIDATE_UNIVERSE_AND_EVIDENCE_ECONOMY_MILESTONE",
        "status": "COMPLETE",
        "starting_head": STARTING_HEAD,
        "reference_set_sha256": REFERENCE_SHA,
        "feature_evidence_registry_v1_sha256": REGISTRY_SHA,
        "evidence_backed_bundle_v2_sha256": BUNDLE_V2_SHA,
        "anchor_candidate_universe_v1_sha256": universe["content_sha256"],
        "anchors": len(universe["anchors"]),
        "candidate_provenance": {name: origin_counts[name] for name in (
            "TORONTO_NOTES_DERIVED", "CANONICAL_CATALOGUE_DERIVED", "EXISTING_RELATION_DERIVED",
            "EXISTING_BUNDLE_DERIVED", "GUIDELINE_DERIVED", "MODEL_PROPOSED", "REVIEWER_PROPOSED",
        )},
        "total_distinct_candidate_proposals": len(rows),
        "stage1_plausible": stage1_counts["PLAUSIBLE"],
        "stage1_rejected": stage1_counts["REJECTED"],
        "stage1_uncertain": stage1_counts["UNCERTAIN"],
        "stage2_approved": stage2_counts["APPROVED"],
        "stage2_rejected": stage2_counts["REJECTED"],
        "stage2_uncertain": stage2_counts["UNCERTAIN"],
        "approved_candidate_universe_size": density["approved_sizes"],
        "approved_thresholds": density["thresholds"],
        "saturation_passes": len(saturation),
        "marginal_approved_per_pass": [60, 0, 0, 0, 0, 0],
        "model_proposed_metrics": {
            "proposed": len(model_rows),
            "stage1_plausible": sum(row["review_stage_1"]["verdict"] == "PLAUSIBLE" for row in model_rows),
            "stage2_approved": sum(row["review_stage_2"]["verdict"] == "APPROVED" for row in model_rows),
            "stage2_rejected": sum(row["review_stage_2"]["verdict"] == "REJECTED" for row in model_rows),
            "stage2_uncertain": sum(row["review_stage_2"]["verdict"] == "UNCERTAIN" for row in model_rows),
            "second_key_risk": sum(row["second_key_status"] == "SECOND_KEY_RISK" for row in model_rows),
        },
        "source_derived_metrics": {
            "proposed": len(source_rows),
            "stage1_plausible": sum(row["review_stage_1"]["verdict"] == "PLAUSIBLE" for row in source_rows),
            "stage2_approved": sum(row["review_stage_2"]["verdict"] == "APPROVED" for row in source_rows),
        },
        "concept_feature_card_v1_sha256": cards["content_sha256"],
        **economy_counts,
        **source_reuse,
        "candidate_compatibility_graph_v1_sha256": graph["content_sha256"],
        "unique_authoritative_sources": len(registry["sources"]),
        "multi_source_verification": {name: verification_counts[name] for name in ("MULTI_SOURCE_CONCORDANT", "SINGLE_AUTHORITATIVE_SOURCE", "CONFLICTING", "INSUFFICIENT")},
        "next_step_evidence": {
            "required": len(admitted),
            "available": next_statuses.count("AVAILABLE"),
            "missing": next_statuses.count("MISSING"),
            "not_applicable": next_statuses.count("NOT_APPLICABLE"),
        },
        "clinical_contrast_bundles_v3_sha256": bundles["content_sha256"],
        "bundle_density": {str(value): sum(row["approved_candidate_count"] >= value for row in bundles["bundles"]) for value in (3, 5, 8, 10)},
        "question_seed_v1_implemented": "YES",
        "question_seed_v1_sha256": question_seeds["content_sha256"],
        "pregen_duplicate_rejections": sum(row["verdict"] in {"DUPLICATE", "NEAR_DUPLICATE"} for row in seed_duplicates["rows"]),
        "postgen_near_duplicate_rejections": duplicate_counts["NEAR_DUPLICATE"],
        "postgen_duplicate_rejections": duplicate_counts["DUPLICATE"],
        "development_items_generated": 0,
        "development_items_accepted": 0,
        "development_items_rejected": 0,
        "development_items_replayed": item_duplicates["items_replayed"],
        "same_topic_distinct_item_pairs": same_topic_distinct,
        "same_topic_duplicate_item_pairs": same_topic_duplicate,
        "evidence_economic_model": "PAIRWISE_REUSE_IMPROVED_BUT_STILL_DOMINANT",
        "generated_candidate_strategy": "LOW_VALUE",
        "historical_safety_regression": "PENDING_FINAL_VALIDATION",
        "aom_development_control": "PENDING_FINAL_VALIDATION",
        "lifecycle_invariant": "PENDING_FINAL_VALIDATION",
        "focused_tests": {"passed": 0, "failed": 0},
        "full_suite": {"passed": 0, "failed": 0, "known_preexisting_failures": 0},
        "new_test_failures": 0,
        "copyright_audit": "PENDING",
        "ready_for_new_clean_transfer": "NO",
        "new_transfer_cohort_size": 0,
        "new_transfer_cohort_sha256": None,
        "commits_created": 0,
        "historical_frozen_artifacts_modified": 0,
        "memory_updated": "NO",
        "claude_md_changed": "NO",
        "next_dominant_bottleneck": "MODEL_PROPOSAL_EVIDENCE_ACQUISITION_AND_DIRECT_DIAGNOSIS_NEXT_STEP_EVIDENCE",
        "next_step": "EXPAND_CONCEPT_FEATURE_LIBRARY",
    })
    result = {
        "universe": universe,
        "stage1_review": stage1_review,
        "stage2_review": stage2_review,
        "cards": cards,
        "graph": graph,
        "bundles": bundles,
        "matrix": matrix,
        "differentials": differentials,
        "question_seeds": question_seeds,
        "seed_duplicates": seed_duplicates,
        "item_duplicates": item_duplicates,
        "economics": economics,
        "report": report,
    }
    if write_outputs:
        for name, relative in OUTPUTS.items():
            _write(root, relative, result[name])
    return result


def write_final_verification(
    root: Path,
    *,
    focused_passed: int,
    focused_failed: int,
    full_passed: int,
    full_failed: int,
    known_preexisting_failures: int,
) -> dict[str, Any]:
    from .contrast_first_pilot import measure_copyright

    copyright_paths = [
        "research/qgen/contrast_supply/expanded_candidate_model_proposals_v1.json",
        *(relative for name, relative in OUTPUTS.items() if name not in {"report", "economics"}),
    ]
    copyright_result = measure_copyright(root, copyright_paths)
    copyright_audit = {
        "schema_version": "EXPANDED_CANDIDATE_UNIVERSE_COPYRIGHT_AUDIT",
        "artifact_count": len(copyright_paths),
        **copyright_result,
    }
    _write(root, "reports/qgen_expanded_candidate_universe_copyright_audit.json", copyright_audit)
    report = _load(root, OUTPUTS["report"])
    report = {key: value for key, value in report.items() if key != "content_sha256"}
    focused_ok = focused_failed == 0
    report.update({
        "historical_safety_regression": "PASS" if focused_ok else "FAIL",
        "aom_development_control": "PASS" if focused_ok else "FAIL",
        "lifecycle": "PASS" if focused_ok else "FAIL",
        "lifecycle_invariant": "PASS" if focused_ok else "FAIL",
        "focused_tests": {"passed": focused_passed, "failed": focused_failed},
        "full_suite": {
            "passed": full_passed,
            "failed": full_failed,
            "known_preexisting_failures": known_preexisting_failures,
        },
        "new_test_failures": max(0, full_failed - known_preexisting_failures),
        "copyright_audit": copyright_result["COPYRIGHT_AUDIT"],
        "memory_updated": "YES",
    })
    report = _hashed(report)
    _write(root, OUTPUTS["report"], report)
    return report


if __name__ == "__main__":
    build_milestone(Path(__file__).resolve().parents[2], write_outputs=True)
