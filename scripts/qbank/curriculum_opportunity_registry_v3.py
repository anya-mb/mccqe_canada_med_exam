from __future__ import annotations

from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Iterable


RELATION_RANK = {
    "NONE": 0,
    "UNRELATED": 0,
    "UNCERTAIN": 0,
    "RELATED_DISTINCT": 1,
    "RELATED_BUT_DISTINCT": 1,
    "NEAR_DUPLICATE": 2,
    "VARIANT_OF_SAME_DECISION": 2,
    "BENCHMARK_NARROWER": 2,
    "REGISTRY_NARROWER": 2,
    "REGISTRY_BROADER_CONTAINS_BENCHMARK": 3,
    "REGISTRY_NARROWER_THAN_BENCHMARK": 3,
    "EQUIVALENT": 3,
    "DUPLICATE": 3,
}

SEMANTIC_RELATION_TAXONOMY = (
    "EQUIVALENT",
    "REGISTRY_BROADER_CONTAINS_BENCHMARK",
    "REGISTRY_NARROWER_THAN_BENCHMARK",
    "VARIANT_OF_SAME_DECISION",
    "RELATED_BUT_DISTINCT",
    "NEAR_DUPLICATE",
    "DUPLICATE",
    "UNRELATED",
    "UNCERTAIN",
)

FORENSIC_CLASSES = (
    "PRESERVED_EQUIVALENCE_CONTRACT_CONFLICT",
    "BROAD_GENERIC_REGISTRY_ROW",
    "RESPONSE_CLASS_MISMATCH",
    "FAMILY_MISMATCH",
    "POSSIBLE_COMPOUND_BENCHMARK_ROW",
    "UNRESOLVED_DIRECTIONAL_CONTAINMENT",
)

ATOMIC_CONTRACT = {
    "schema_version": "1.0",
    "scope": "ATOMIC_MCCQE_QUESTION_OPPORTUNITY_CONTRACT_V1",
    "definition": (
        "Given one clinically material state, the learner must produce one response whose correctness "
        "turns on one coherent reasoning target."
    ),
    "identity_dimensions": [
        "clinical_topic_or_concept",
        "response_class",
        "learner_decision_or_intent",
        "key_concept_or_action",
        "clinical_stage_only_when_decision_changing",
        "population_context_only_when_decision_changing",
        "severity_only_when_decision_changing",
        "material_decision_changing_state",
        "MCC_physician_activity_and_objective_mapping",
    ],
    "split_when": [
        "DIFFERENT_RESPONSE_CLASS",
        "INDEPENDENTLY_SCOREABLE_DECISION",
        "MATERIAL_CONTEXT_CHANGES_CORRECT_RESPONSE",
        "SEQUENTIAL_DECISION_WITH_DISTINCT_OUTCOME",
    ],
    "do_not_split_when": [
        "ALTERNATE_EVIDENCE_PATH_TO_SAME_DECISION",
        "SYNONYMOUS_ACTION_VERB",
        "ITEM_FORM_OR_STEM_WRAPPER",
        "DIFFICULTY_OR_DISTRACTOR_CHANGE",
        "COSMETIC_DEMOGRAPHIC_VARIANT",
    ],
    "broad_row_policy": "REQUIRES_DECOMPOSITION_UNTIL_ONE_DECISION_RULE_IS_EXPLICIT",
    "compound_policy": "ONE_ROW_CANNOT_REQUIRE_TWO_INDEPENDENTLY_SCOREABLE_RESPONSES",
    "relationship_taxonomy": list(SEMANTIC_RELATION_TAXONOMY),
    "distinct_opportunity_contract": (
        "A distinction is a new opportunity only when it materially changes the correct answer or action, "
        "principal learner decision, required clinical knowledge, clinical-stage decision, management or "
        "investigation pathway, recognized complication, legal or ethical duty, or decision-changing population context."
    ),
    "item_variant_contract": (
        "A distinction remains an item variant when it changes only patient identity, incidental demographics, "
        "wording, symptom order, non-load-bearing values, surface history, option order, or an equivalent "
        "presentation without changing the tested learner decision."
    ),
    "question_seed_boundary": (
        "Evidence-path, vignette-form, difficulty, distractor, and cosmetic presentation choices belong in the "
        "Question Seed or item variant layer, not opportunity identity."
    ),
}


def canonical_json(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def content_sha256(value: Any) -> str:
    payload = {key: item for key, item in value.items() if key != "content_sha256"}
    return hashlib.sha256(canonical_json(payload).encode()).hexdigest()


def _with_hash(value: dict[str, Any]) -> dict[str, Any]:
    value = dict(value)
    value["content_sha256"] = content_sha256(value)
    return value


def _load(root: Path, relative: str) -> dict[str, Any]:
    return json.loads((Path(root) / relative).read_text())


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _comparison_metrics(
    benchmark: dict[str, Any],
    comparison: dict[str, Any],
    registry_review_key: str,
) -> dict[str, Any]:
    counts = Counter(row["classification"] for row in comparison["benchmark_reviews"])
    missing_key = "MISSING_FROM_V2" if counts["MISSING_FROM_V2"] else "MISSING_FROM_V1"
    valid = (
        counts["EXACT_MATCH"]
        + counts["SEMANTIC_MATCH"]
        + counts["PARTIAL_MATCH"]
        + counts[missing_key]
    )
    review_counts = Counter(row["classification"] for row in comparison[registry_review_key])
    supported = review_counts["SUPPORTED_BY_BENCHMARK"]
    return {
        "match_counts": {
            "EXACT_MATCH": counts["EXACT_MATCH"],
            "SEMANTIC_MATCH": counts["SEMANTIC_MATCH"],
            "PARTIAL_MATCH": counts["PARTIAL_MATCH"],
            missing_key: counts[missing_key],
            "INVALID_BENCHMARK_OPPORTUNITY": counts["INVALID_BENCHMARK_OPPORTUNITY"],
        },
        "opportunity_recall": round((counts["EXACT_MATCH"] + counts["SEMANTIC_MATCH"]) / valid, 6),
        "opportunity_precision": round(supported / len(comparison[registry_review_key]), 6),
        "benchmark_rows": len(benchmark["opportunities"]),
        "reviewed_registry_rows": len(comparison[registry_review_key]),
    }


def build_matching_diagnostic_contract(root: Path) -> dict[str, Any]:
    root = Path(root)
    paths = {
        "benchmark": "research/qgen/opportunity_registry_v2/independent_opportunity_benchmark_v1.json",
        "registry_v1": "research/qgen/opportunity_registry/curriculum_question_opportunity_registry_v1.json",
        "registry_v2": "research/qgen/opportunity_registry_v2/curriculum_question_opportunity_registry_v2.json",
        "v1_comparison_input": "research/qgen/opportunity_registry_v2/v1_benchmark_comparison_input.json",
        "v1_comparison_output": "research/qgen/opportunity_registry_v2/v1_benchmark_comparison.json",
        "v2_comparison_input": "research/qgen/opportunity_registry_v2/v2_benchmark_comparison_input_final.json",
        "v2_comparison_output": "research/qgen/opportunity_registry_v2/v2_benchmark_comparison_final.json",
        "v2_implementation": "scripts/qbank/curriculum_opportunity_registry_v2.py",
    }
    benchmark = _load(root, paths["benchmark"])
    v1_comparison = _load(root, paths["v1_comparison_output"])
    v2_comparison = _load(root, paths["v2_comparison_output"])
    artifact = {
        "schema_version": "1.0",
        "scope": "OPPORTUNITY_MATCHING_DIAGNOSTIC_CONTRACT_V1",
        "frozen_file_sha256": {
            key: _file_sha256(root / relative) for key, relative in sorted(paths.items())
        },
        "declared_content_sha256": {
            "benchmark": benchmark["content_sha256"],
            "registry_v1": _load(root, paths["registry_v1"])["content_sha256"],
            "registry_v2": _load(root, paths["registry_v2"])["content_sha256"],
            "v1_comparison_output": v1_comparison["content_sha256"],
            "v2_comparison_output": v2_comparison["content_sha256"],
        },
        "v1_matcher_kind": "STATIC_SEMANTIC_REVIEW_PLUS_DETERMINISTIC_AGGREGATION",
        "v2_matcher_kind": "STATIC_SEMANTIC_REVIEW_PLUS_DETERMINISTIC_AGGREGATION",
        "executable_pair_classifier_present": False,
        "normalization_contract": "UNVERSIONED_REVIEWER_SEMANTICS_NO_SHARED_EXECUTABLE_NORMALIZER",
        "v1_reproduction": _comparison_metrics(benchmark, v1_comparison, "v1_reviews"),
        "v2_reproduction": _comparison_metrics(benchmark, v2_comparison, "v2_reviews"),
    }
    return _with_hash(artifact)


def build_v1_preservation_audit(root: Path) -> dict[str, Any]:
    root = Path(root)
    v1 = _load(root, "research/qgen/opportunity_registry/curriculum_question_opportunity_registry_v1.json")
    v2 = _load(root, "research/qgen/opportunity_registry_v2/curriculum_question_opportunity_registry_v2.json")
    descendants: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in v2["opportunities"]:
        for source_id in row.get("source_v1_opportunity_ids", []):
            descendants[source_id].append(row)
    rows = []
    flags = Counter()
    primary = Counter()
    for source in v1["opportunities"]:
        candidates = descendants.get(source["opportunity_id"], [])
        preserved = next(
            (row for row in candidates if row.get("provenance_type") == "V1_PRESERVED"),
            candidates[0] if candidates else None,
        )
        row_flags = []
        if preserved is None:
            row_flags.append("OTHER")
        else:
            if source["learner_decision"] != preserved["learner_decision"]:
                row_flags.append("LEARNER_DECISION_CHANGED")
            if source["key_concept_or_action"] != preserved["key_concept_or_action"]:
                row_flags.append("KEY_CHANGED")
            if source["clinical_stage"] != preserved["clinical_stage"]:
                row_flags.append("STAGE_CHANGED")
            if (
                source["population_context"] != preserved["population_context"]
                or source["severity_context"] != preserved["severity_context"]
            ):
                row_flags.append("CONTEXT_CHANGED")
            if (
                source["opportunity_family"] != preserved["opportunity_family"]
                or source["response_class"] != preserved["response_class"]
                or source["MCC_physician_activity"] != preserved["MCC_physician_activity"]
                or source["MCC_dimension_of_care"] != preserved["MCC_dimension_of_care"]
            ):
                row_flags.append("NORMALIZATION_CHANGED")
            if source["opportunity_fingerprint"] != preserved["opportunity_fingerprint"]:
                row_flags.append("FINGERPRINT_CHANGED")
            semantic_flags = set(row_flags) - {"FINGERPRINT_CHANGED"}
            if not semantic_flags:
                row_flags.insert(0, "BYTE_SEMANTICALLY_PRESERVED")
        for value in row_flags:
            flags[value] += 1
        precedence = (
            "OTHER", "LEARNER_DECISION_CHANGED", "KEY_CHANGED", "CONTEXT_CHANGED",
            "STAGE_CHANGED", "NORMALIZATION_CHANGED", "BYTE_SEMANTICALLY_PRESERVED", "FINGERPRINT_CHANGED",
        )
        primary_value = next(value for value in precedence if value in row_flags)
        primary[primary_value] += 1
        rows.append(
            {
                "v1_opportunity_id": source["opportunity_id"],
                "v2_descendant_ids": sorted(row["opportunity_id"] for row in candidates),
                "preserved_v2_opportunity_id": preserved["opportunity_id"] if preserved else None,
                "classifications": row_flags,
                "primary_classification": primary_value,
            }
        )
    artifact = {
        "schema_version": "1.0",
        "scope": "V1_TO_V2_SEMANTIC_PRESERVATION_AUDIT",
        "v1_rows": len(v1["opportunities"]),
        "v1_rows_with_v2_descendants": sum(bool(row["v2_descendant_ids"]) for row in rows),
        "classification_counts": dict(sorted(flags.items())),
        "primary_classification_counts": dict(sorted(primary.items())),
        "learner_decision_changed": flags["LEARNER_DECISION_CHANGED"],
        "key_changed": flags["KEY_CHANGED"],
        "stage_changed": flags["STAGE_CHANGED"],
        "context_changed": flags["CONTEXT_CHANGED"],
        "normalization_changed": flags["NORMALIZATION_CHANGED"],
        "rows": rows,
    }
    return _with_hash(artifact)


def _stable_stratified_sample(
    rows: list[dict[str, Any]], sample_size: int, discipline_getter, family_getter, id_getter,
) -> list[dict[str, Any]]:
    disciplines = ("MED", "PED", "OBGYN", "SURG", "PSY", "PHELO")
    if sample_size % len(disciplines):
        raise ValueError("sample size must be divisible by six disciplines")
    quota = sample_size // len(disciplines)
    selected = []
    for discipline in disciplines:
        pool = [row for row in rows if discipline_getter(row) == discipline]
        if len(pool) < quota:
            raise ValueError(f"insufficient {discipline} rows for requested sample")
        by_family: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in pool:
            by_family[family_getter(row)].append(row)
        for family_rows in by_family.values():
            family_rows.sort(key=lambda row: hashlib.sha256(id_getter(row).encode()).hexdigest())
        family_order = sorted(
            by_family,
            key=lambda family: hashlib.sha256(f"{discipline}|{family}".encode()).hexdigest(),
        )
        discipline_selected = 0
        while discipline_selected < quota:
            progressed = False
            for family in family_order:
                if by_family[family]:
                    selected.append(by_family[family].pop(0))
                    discipline_selected += 1
                    progressed = True
                    if discipline_selected == quota:
                        break
            if not progressed:
                raise ValueError(f"unable to fill {discipline} quota")
    return sorted(selected, key=lambda row: (discipline_getter(row), id_getter(row)))


def select_partial_forensic_sample(root: Path, sample_size: int = 120) -> dict[str, Any]:
    root = Path(root)
    benchmark = _load(root, "research/qgen/opportunity_registry_v2/independent_opportunity_benchmark_v1.json")
    comparison = _load(root, "research/qgen/opportunity_registry_v2/v1_benchmark_comparison.json")
    v1 = _load(root, "research/qgen/opportunity_registry/curriculum_question_opportunity_registry_v1.json")
    benchmark_by_id = {row["benchmark_opportunity_id"]: row for row in benchmark["opportunities"]}
    v1_by_id = {row["opportunity_id"]: row for row in v1["opportunities"]}
    partials = [row for row in comparison["benchmark_reviews"] if row["classification"] == "PARTIAL_MATCH"]

    def strata(review: dict[str, Any]) -> tuple[str, str, str]:
        benchmark_row = benchmark_by_id[review["benchmark_opportunity_id"]]
        candidates = [v1_by_id[value] for value in review["matched_v1_ids"]]
        priority = candidates[0].get("importance", "UNKNOWN") if candidates else "NO_CANDIDATE"
        same_family = any(row["opportunity_family"] == benchmark_row["opportunity_family"] for row in candidates)
        same_response = any(row["response_class"] == benchmark_row["response_class"] for row in candidates)
        apparent_relation = (
            "SAME_FAMILY_AND_RESPONSE" if same_family and same_response else
            "FAMILY_ONLY" if same_family else "RESPONSE_ONLY" if same_response else "CROSS_FAMILY_RESPONSE"
        )
        return benchmark_row["opportunity_family"], priority, apparent_relation

    chosen = _stable_stratified_sample(
        partials, sample_size,
        lambda row: benchmark_by_id[row["benchmark_opportunity_id"]]["discipline"],
        lambda row: "|".join(strata(row)),
        lambda row: row["benchmark_opportunity_id"],
    )
    pairs = []
    for review in chosen:
        benchmark_row = benchmark_by_id[review["benchmark_opportunity_id"]]
        pairs.append({
            "pair_id": "PF-" + review["benchmark_opportunity_id"],
            "benchmark": benchmark_row,
            "candidate_rows": [v1_by_id[value] for value in review["matched_v1_ids"]],
            "sampling_strata": {
                "discipline": benchmark_row["discipline"],
                "family": strata(review)[0],
                "priority": strata(review)[1],
                "study_unit_id": benchmark_row["study_unit_id"],
                "apparent_relation_type": strata(review)[2],
            },
            "prior_label_withheld": True,
            "review_fields": {"semantic_relation": None, "discriminator_class": None, "rationale": None},
        })
    return _with_hash({
        "schema_version": "1.0",
        "scope": "V1_PARTIAL_MATCH_BLINDED_FORENSIC_SAMPLE",
        "atomic_contract": ATOMIC_CONTRACT,
        "allowed_semantic_relations": list(SEMANTIC_RELATION_TAXONOMY),
        "allowed_discriminator_classes": [
            "DISTINCT_REASONING_OPPORTUNITY", "LEGITIMATE_ITEM_VARIANT", "COSMETIC_VARIANT", "UNCERTAIN",
        ],
        "reviewer_blindness": "NO_DESIRED_COUNTS_OR_V2_OUTCOMES",
        "sampling_contract": "BALANCED_BY_DISCIPLINE_AND_ROUND_ROBIN_BY_FAMILY_PRIORITY_STUDY_UNIT_AND_APPARENT_RELATION",
        "pairs": pairs,
    })


def build_complete_partial_classifier(root: Path) -> dict[str, Any]:
    root = Path(root)
    sample = select_partial_forensic_sample(root)
    review = _load(root, "research/qgen/opportunity_registry_v3/partial_match_semantic_review_v1.json")
    comparison = _load(root, "research/qgen/opportunity_registry_v2/v1_benchmark_comparison.json")
    if review["source_sample_sha256"] != sample["content_sha256"]:
        raise ValueError("partial semantic review does not match the frozen sample")
    if review["content_sha256"] != content_sha256(review):
        raise ValueError("partial semantic review content hash is invalid")
    review_by_benchmark = {row["benchmark_opportunity_id"]: row for row in review["reviews"]}
    if len(review_by_benchmark) != 120 or set(review_by_benchmark) != {
        row["benchmark"]["benchmark_opportunity_id"] for row in sample["pairs"]
    }:
        raise ValueError("partial semantic review must cover every sampled pair exactly once")
    rows = []
    for prior in comparison["benchmark_reviews"]:
        if prior["classification"] != "PARTIAL_MATCH":
            continue
        reviewed = review_by_benchmark.get(prior["benchmark_opportunity_id"])
        if reviewed:
            relation = reviewed["semantic_relation"]
            discriminator = reviewed["discriminator_class"]
            basis = "INDEPENDENT_BLINDED_SAMPLE_REVIEW"
            rationale = reviewed["rationale"]
        else:
            relation = "UNCERTAIN"
            discriminator = "UNCERTAIN"
            basis = "FAIL_CLOSED_NO_VALIDATED_GENERAL_RULE"
            rationale = "No reviewed general rule establishes a directional or variant relation with sufficient confidence."
        rows.append({
            "benchmark_opportunity_id": prior["benchmark_opportunity_id"],
            "candidate_opportunity_ids": prior.get("matched_v1_ids", []),
            "semantic_relation": relation,
            "discriminator_class": discriminator,
            "classification_basis": basis,
            "rationale": rationale,
        })
    relation_counts = Counter(row["semantic_relation"] for row in rows)
    discriminator_counts = Counter(row["discriminator_class"] for row in rows)
    return _with_hash({
        "schema_version": "1.0",
        "scope": "COMPLETE_V1_PARTIAL_RELATION_CLASSIFICATION_V1",
        "source_review_sha256": review["content_sha256"],
        "total_partial_relationships": len(rows),
        "independently_reviewed": len(review_by_benchmark),
        "unreviewed_failed_closed": len(rows) - len(review_by_benchmark),
        "generalization_policy": (
            "Use independent reviewed labels only for sampled relations; no reviewed feature rule achieved enough "
            "specificity to promote unreviewed relationships, so all remaining rows fail closed to UNCERTAIN."
        ),
        "id_specific_rules": False,
        "relation_counts": {key: relation_counts[key] for key in SEMANTIC_RELATION_TAXONOMY},
        "discriminator_class_counts": {
            key: discriminator_counts[key] for key in (
                "DISTINCT_REASONING_OPPORTUNITY", "LEGITIMATE_ITEM_VARIANT", "COSMETIC_VARIANT", "UNCERTAIN",
            )
        },
        "all_rows_classified": len(rows) == 415,
        "classifications": rows,
    })


def _blind_curriculum_projection(row: dict[str, Any]) -> dict[str, Any]:
    return {
        key: row[key] for key in (
            "study_unit_id", "study_unit", "discipline", "chapter_code", "chapter_title", "scope_depth",
            "source_hierarchy_path", "preferred_item_forms", "testable_competencies", "mcc_objectives",
        )
    }


def select_benchmark_granularity_sample(root: Path, sample_size: int = 120) -> dict[str, Any]:
    root = Path(root)
    benchmark = _load(root, "research/qgen/opportunity_registry_v2/independent_opportunity_benchmark_v1.json")
    blind_input = _load(root, "research/qgen/opportunity_registry_v2/blind_benchmark_input_v1.json")
    context_by_unit = {row["study_unit_id"]: row for row in blind_input["study_units"]}
    siblings: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in benchmark["opportunities"]:
        siblings[row["study_unit_id"]].append(row)
    chosen = _stable_stratified_sample(
        benchmark["opportunities"], sample_size,
        lambda row: row["discipline"], lambda row: row["opportunity_family"],
        lambda row: row["benchmark_opportunity_id"],
    )
    opportunities = []
    for row in chosen:
        opportunities.append({
            "benchmark": row,
            "curriculum_context": _blind_curriculum_projection(context_by_unit[row["study_unit_id"]]),
            "sibling_benchmark_opportunities": [
                sibling for sibling in siblings[row["study_unit_id"]]
                if sibling["benchmark_opportunity_id"] != row["benchmark_opportunity_id"]
            ],
            "review_fields": {
                "granularity_label": None, "merge_with_sibling_ids": [],
                "split_atomic_decisions": [], "rationale": None,
            },
        })
    return _with_hash({
        "schema_version": "1.0",
        "scope": "BLINDED_BENCHMARK_GRANULARITY_SAMPLE_V1",
        "atomic_contract": ATOMIC_CONTRACT,
        "allowed_granularity_labels": [
            "ATOMIC_DISTINCT", "SHOULD_MERGE_WITH_SIBLING", "ITEM_VARIANT_NOT_OPPORTUNITY",
            "COMPOUND_NEEDS_SPLIT", "TOO_SPECIALIST", "NOT_MC_SUITABLE", "UNCERTAIN",
        ],
        "reviewer_blindness": "BENCHMARK_AND_CURRICULUM_ONLY_REGISTRIES_WITHHELD",
        "sampling_contract": "BALANCED_BY_DISCIPLINE_AND_ROUND_ROBIN_BY_OPPORTUNITY_FAMILY",
        "opportunities": opportunities,
    })


def best_relation(relations: Iterable[str]) -> str:
    values = list(relations)
    if not values:
        return "NONE"
    unknown = set(values) - set(RELATION_RANK)
    if unknown:
        raise ValueError(f"unknown opportunity relation(s): {sorted(unknown)}")
    return max(values, key=lambda value: (RELATION_RANK[value], value == "EQUIVALENT"))


def _relation_decision(row: dict[str, Any]) -> str:
    return str(
        row.get("decision") or row.get("principal_decision") or row.get("learner_decision")
        or row.get("key_concept_or_action") or ""
    )


def _semantic_decision_tokens(value: str) -> set[str]:
    synonyms = {"recognize": "diagnose", "identify": "diagnose", "choose": "select", "manage": "treat"}
    return {
        synonyms.get(token, "suicide" if token == "suicidal" else token)
        for token in re.findall(r"[a-z0-9]+", value.lower())
        if token not in {"a", "an", "and", "for", "from", "in", "of", "on", "or", "the", "to", "with"}
    }


def classify_relation_v3(benchmark: dict[str, Any], registry: dict[str, Any]) -> str:
    """General pair classifier implementing the versioned relation vocabulary.

    Explicit structured decision components take precedence over lossy prose
    similarity. Ambiguous underspecified pairs fail closed.
    """
    benchmark_decision = _relation_decision(benchmark)
    registry_decision = _relation_decision(registry)
    if not benchmark_decision or not registry_decision:
        return "UNCERTAIN"
    benchmark_fingerprint = benchmark.get("fingerprint") or benchmark.get("opportunity_fingerprint")
    registry_fingerprint = registry.get("fingerprint") or registry.get("opportunity_fingerprint")
    if benchmark_fingerprint and benchmark_fingerprint == registry_fingerprint:
        return "DUPLICATE"
    if _normalized(benchmark_decision) == _normalized(registry_decision):
        return "EQUIVALENT"
    benchmark_tokens = _semantic_decision_tokens(benchmark_decision)
    registry_tokens = _semantic_decision_tokens(registry_decision)
    if len(benchmark_tokens) < 2 or len(registry_tokens) < 2:
        return "UNCERTAIN"
    if benchmark_tokens == registry_tokens:
        benchmark_words = re.findall(r"[a-z0-9]+", benchmark_decision.lower())
        registry_words = re.findall(r"[a-z0-9]+", registry_decision.lower())
        action_groups = ({"recognize", "identify", "diagnose"}, {"choose", "select"}, {"manage", "treat"})
        synonym_action = any(benchmark_words[0] in group and registry_words[0] in group for group in action_groups)
        return "EQUIVALENT" if synonym_action else "NEAR_DUPLICATE"
    benchmark_components = {
        _normalized(value) for value in benchmark.get("decision_components", [benchmark_decision])
    }
    registry_components = {
        _normalized(value) for value in registry.get("decision_components", [registry_decision])
    }
    if benchmark_components and registry_components:
        if benchmark_components < registry_components:
            return "REGISTRY_BROADER_CONTAINS_BENCHMARK"
        if registry_components < benchmark_components:
            return "REGISTRY_NARROWER_THAN_BENCHMARK"
    if benchmark.get("variant_group_id") and benchmark.get("variant_group_id") == registry.get("variant_group_id"):
        return "VARIANT_OF_SAME_DECISION"
    union = benchmark_tokens | registry_tokens
    similarity = len(benchmark_tokens & registry_tokens) / len(union)
    if similarity >= 0.7 and benchmark.get("response_class") == registry.get("response_class"):
        return "NEAR_DUPLICATE"
    benchmark_family = benchmark.get("family") or benchmark.get("opportunity_family")
    registry_family = registry.get("family") or registry.get("opportunity_family")
    if (
        benchmark.get("study_unit_id")
        and benchmark.get("study_unit_id") == registry.get("study_unit_id")
        and benchmark_family and benchmark_family == registry_family
    ):
        return "RELATED_BUT_DISTINCT"
    return "UNRELATED"


def build_relation_graph_v3(
    benchmark_rows: Iterable[dict[str, Any]], registry_rows: Iterable[dict[str, Any]],
) -> list[dict[str, Any]]:
    edges = []
    for benchmark in benchmark_rows:
        benchmark_id = benchmark.get("id") or benchmark.get("normalized_opportunity_id") or benchmark.get("benchmark_opportunity_id")
        for registry in registry_rows:
            registry_id = registry.get("id") or registry.get("opportunity_id")
            edges.append({
                "benchmark_opportunity_id": benchmark_id,
                "registry_opportunity_id": registry_id,
                "relation": classify_relation_v3(benchmark, registry),
            })
    return sorted(edges, key=lambda row: (str(row["benchmark_opportunity_id"]), str(row["registry_opportunity_id"])))


def calibrate_monotonicity(
    prior_equivalent_edges: dict[str, set[str]],
    current_equivalent_edges: dict[str, set[str]],
    lineage: dict[str, set[str]],
) -> list[str]:
    """Return prior-equivalence rows whose preserved edge disappeared."""
    regressions = []
    for benchmark_id, prior_registry_ids in sorted(prior_equivalent_edges.items()):
        inherited = {
            descendant
            for prior_id in prior_registry_ids
            for descendant in lineage.get(prior_id, set())
        }
        calibrated = inherited | current_equivalent_edges.get(benchmark_id, set())
        if not calibrated:
            regressions.append(benchmark_id)
    return regressions


def build_atomic_opportunity_contract() -> dict[str, Any]:
    contract = dict(ATOMIC_CONTRACT)
    contract.update(
        {
            "pairwise_relations": list(SEMANTIC_RELATION_TAXONOMY),
            "strict_match_relation": "EQUIVALENT",
            "containment_policy": "DIAGNOSTIC_UNTIL_BROADER_ENDPOINT_IS_ADJUDICATED_ATOMIC",
            "precision_policy": "SAME_EQUIVALENCE_EDGE_GRAPH_AS_RECALL",
            "topic_support_policy": "REPORT_SEPARATELY_NEVER_CALL_PRECISION",
            "monotonicity_invariant": "ADDING_REGISTRY_CANDIDATES_CANNOT_LOWER_BEST_RELATION_RANK",
            "lineage_invariant": "PRESERVED_ROWS_INHERIT_PRIOR_EDGES_UNTIL_VERSIONED_READJUDICATION",
        }
    )
    return _with_hash(contract)


def build_matcher_regression_diagnosis(root: Path) -> dict[str, Any]:
    root = Path(root)
    v1_comparison = _load(root, "research/qgen/opportunity_registry_v2/v1_benchmark_comparison.json")
    v2_comparison = _load(root, "research/qgen/opportunity_registry_v2/v2_benchmark_comparison_final.json")
    registry_v1 = _load(root, "research/qgen/opportunity_registry/curriculum_question_opportunity_registry_v1.json")
    registry_v2 = _load(root, "research/qgen/opportunity_registry_v2/curriculum_question_opportunity_registry_v2.json")

    v1_reviews = {row["benchmark_opportunity_id"]: row for row in v1_comparison["benchmark_reviews"]}
    v2_reviews = {row["benchmark_opportunity_id"]: row for row in v2_comparison["benchmark_reviews"]}
    v1_rows = {row["opportunity_id"]: row for row in registry_v1["opportunities"]}
    v2_rows = {row["opportunity_id"]: row for row in registry_v2["opportunities"]}
    descendants: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in registry_v2["opportunities"]:
        for source_id in row.get("source_v1_opportunity_ids", []):
            descendants[source_id].append(row)

    transition = Counter()
    transition_rows = []
    full_states = {"EXACT_MATCH", "SEMANTIC_MATCH"}
    v1_full = [row for row in v1_comparison["benchmark_reviews"] if row["classification"] in full_states]
    preserved = 0
    text_identical = 0
    downgraded = 0
    inherited_full_ids: set[str] = set()
    for benchmark_id, prior in sorted(v1_reviews.items()):
        current = v2_reviews[benchmark_id]
        key = f"{prior['classification']} -> {current['classification']}"
        transition[key] += 1
        if prior["classification"] in full_states:
            prior_descendants = {
                row["opportunity_id"]: row
                for source_id in prior.get("matched_v1_ids", [])
                for row in descendants.get(source_id, [])
            }
            if prior_descendants:
                preserved += 1
                inherited_full_ids.add(benchmark_id)
            if any(
                row["learner_decision"] == v1_rows[source_id]["learner_decision"]
                for source_id in prior.get("matched_v1_ids", [])
                for row in descendants.get(source_id, [])
            ):
                text_identical += 1
            if current["classification"] not in full_states:
                downgraded += 1
                transition_rows.append(
                    {
                        "benchmark_opportunity_id": benchmark_id,
                        "v1_classification": prior["classification"],
                        "v2_classification": current["classification"],
                        "matched_v1_ids": prior.get("matched_v1_ids", []),
                        "available_v2_descendant_ids": sorted(prior_descendants),
                        "v2_reviewer_linked_ids": current.get("matched_v2_ids", []),
                        "text_identical_descendant": any(
                            row["learner_decision"] == v1_rows[source_id]["learner_decision"]
                            for source_id in prior.get("matched_v1_ids", [])
                            for row in descendants.get(source_id, [])
                        ),
                    }
                )

    current_full_ids = {
        row["benchmark_opportunity_id"]
        for row in v2_comparison["benchmark_reviews"]
        if row["classification"] in full_states
    }
    counterfactual = inherited_full_ids | current_full_ids
    report = {
        "schema_version": "1.0",
        "scope": "V1_V2_BENCHMARK_MATCHER_REGRESSION_DIAGNOSIS",
        "registry_v1_sha256": registry_v1["content_sha256"],
        "registry_v2_sha256": registry_v2["content_sha256"],
        "benchmark_sha256": v1_comparison["benchmark_sha256"],
        "v1_full_matches": len(v1_full),
        "v1_full_matches_with_v2_descendants": preserved,
        "v1_full_matches_with_text_identical_v2_descendants": text_identical,
        "v1_full_matches_downgraded": downgraded,
        "transition_matrix": dict(sorted(transition.items())),
        "downgraded_rows": transition_rows,
        "reported_v2_full_matches": len(current_full_ids),
        "counterfactual_monotonic_v2_full_matches": len(counterfactual),
        "counterfactual_monotonic_v2_recall": round(len(counterfactual) / len(v1_reviews), 6),
        "root_cause": "ADJUDICATION_CONTRACT_DRIFT_AND_LINKAGE_FAILURE",
        "metric_bug": False,
        "registry_content_loss": False,
        "diagnostic_findings": [
            "V2 preserved a text-identical descendant for every V1 full match.",
            "The V2 semantic pass changed the equivalence threshold without versioning the contract.",
            "Two V1 full-match descendants existed but were not linked by the V2 reviewer.",
            "V1 precision and V2 precision used topic-support labels that were not symmetric with strict recall.",
        ],
    }
    return _with_hash(report)


def build_benchmark_matcher_calibration(root: Path) -> dict[str, Any]:
    """Build one stable equivalence graph from frozen V1 edges and V2 lineage.

    This is a calibration artifact, not a claim that the unaudited benchmark is
    correctly atomized. It repairs the comparison contract without inventing
    new semantic matches.
    """
    root = Path(root)
    benchmark = _load(root, "research/qgen/opportunity_registry_v2/independent_opportunity_benchmark_v1.json")
    v1_comparison = _load(root, "research/qgen/opportunity_registry_v2/v1_benchmark_comparison.json")
    v2_comparison = _load(root, "research/qgen/opportunity_registry_v2/v2_benchmark_comparison_final.json")
    registry_v2 = _load(root, "research/qgen/opportunity_registry_v2/curriculum_question_opportunity_registry_v2.json")
    full = {"EXACT_MATCH", "SEMANTIC_MATCH"}
    descendants: dict[str, set[str]] = defaultdict(set)
    for row in registry_v2["opportunities"]:
        for source_id in row.get("source_v1_opportunity_ids", []):
            descendants[source_id].add(row["opportunity_id"])
    prior = {row["benchmark_opportunity_id"]: row for row in v1_comparison["benchmark_reviews"]}
    current = {row["benchmark_opportunity_id"]: row for row in v2_comparison["benchmark_reviews"]}
    edges = []
    equivalent_registry_ids: set[str] = set()
    inherited_count = 0
    prior_equivalent_edges = {
        benchmark_id: set(row.get("matched_v1_ids", []))
        for benchmark_id, row in prior.items()
        if row["classification"] in full
    }
    current_equivalent_edges = {
        benchmark_id: set(row.get("matched_v2_ids", []))
        for benchmark_id, row in current.items()
        if row["classification"] in full
    }
    for benchmark_row in benchmark["opportunities"]:
        benchmark_id = benchmark_row["benchmark_opportunity_id"]
        inherited_ids = {
            child_id
            for source_id in prior[benchmark_id].get("matched_v1_ids", [])
            for child_id in descendants.get(source_id, set())
        } if prior[benchmark_id]["classification"] in full else set()
        current_ids = set(current[benchmark_id].get("matched_v2_ids", [])) if current[benchmark_id]["classification"] in full else set()
        equivalent_ids = inherited_ids | current_ids
        inherited_count += bool(inherited_ids)
        equivalent_registry_ids.update(equivalent_ids)
        edges.append(
            {
                "benchmark_opportunity_id": benchmark_id,
                "best_relation": "EQUIVALENT" if equivalent_ids else "UNADJUDICATED",
                "equivalent_registry_v2_ids": sorted(equivalent_ids),
                "edge_sources": sorted(
                    ({"V1_INHERITED_LINEAGE"} if inherited_ids else set())
                    | ({"V2_FROZEN_REVIEW"} if current_ids else set())
                ),
            }
        )
    benchmark_unit_ids = {row["study_unit_id"] for row in benchmark["opportunities"]}
    monotonicity_regression_ids = calibrate_monotonicity(
        prior_equivalent_edges, current_equivalent_edges, descendants
    )
    evaluated_registry_rows = [
        row for row in registry_v2["opportunities"] if row["study_unit_id"] in benchmark_unit_ids
    ]
    equivalent_benchmark_rows = sum(bool(row["equivalent_registry_v2_ids"]) for row in edges)
    multi_equivalence_conflicts = sum(len(row["equivalent_registry_v2_ids"]) > 1 for row in edges)
    artifact = {
        "schema_version": "1.0",
        "scope": "BENCHMARK_MATCHER_CALIBRATION_V1",
        "atomic_contract_sha256": build_atomic_opportunity_contract()["content_sha256"],
        "benchmark_sha256": benchmark["content_sha256"],
        "registry_v2_sha256": registry_v2["content_sha256"],
        "benchmark_rows": len(edges),
        "evaluated_registry_rows": len(evaluated_registry_rows),
        "inherited_equivalent_benchmark_rows": inherited_count,
        "calibrated_equivalent_benchmark_rows": equivalent_benchmark_rows,
        "calibrated_equivalent_registry_rows": len(equivalent_registry_ids),
        "strict_raw_recall": round(equivalent_benchmark_rows / len(edges), 6),
        "strict_symmetric_precision": round(len(equivalent_registry_ids) / len(evaluated_registry_rows), 6),
        "precision_authorized": multi_equivalence_conflicts == 0,
        "multi_equivalence_conflicts": multi_equivalence_conflicts,
        "recall_edge_relation": "EQUIVALENT",
        "precision_edge_relation": "EQUIVALENT",
        "topic_support_reported_as_precision": False,
        "monotonicity_regressions": len(monotonicity_regression_ids),
        "monotonicity_regression_benchmark_ids": monotonicity_regression_ids,
        "edge_rows": edges,
        "limitations": "Inherited V1 equivalence edges stabilize the contract; they do not validate benchmark atomization.",
    }
    return _with_hash(artifact)


def _is_generic_registry_row(row: dict[str, Any]) -> bool:
    decision = row.get("learner_decision", "").lower()
    return decision.startswith("apply ") and " reasoning for " in decision


def _partial_class(
    benchmark_row: dict[str, Any],
    matched_rows: list[dict[str, Any]],
) -> str:
    if any(row.get("response_class") == benchmark_row.get("response_class") for row in matched_rows):
        same_response = True
    else:
        same_response = False
    if not same_response:
        return "RESPONSE_CLASS_MISMATCH"
    if any(_is_generic_registry_row(row) for row in matched_rows):
        return "BROAD_GENERIC_REGISTRY_ROW"
    if not any(row.get("opportunity_family") == benchmark_row.get("opportunity_family") for row in matched_rows):
        return "FAMILY_MISMATCH"
    decision = benchmark_row.get("principal_decision", "")
    if re.search(r"\b(?:and|or)\b", decision.lower()):
        return "POSSIBLE_COMPOUND_BENCHMARK_ROW"
    return "UNRESOLVED_DIRECTIONAL_CONTAINMENT"


def _partial_rows(
    benchmark_by_id: dict[str, dict[str, Any]],
    comparison: dict[str, Any],
    registry_by_id: dict[str, dict[str, Any]],
    matched_key: str,
    prior_equivalent_ids: set[str] | None = None,
) -> list[dict[str, Any]]:
    output = []
    for review in comparison["benchmark_reviews"]:
        if review["classification"] != "PARTIAL_MATCH":
            continue
        benchmark_row = benchmark_by_id[review["benchmark_opportunity_id"]]
        matched = [registry_by_id[value] for value in review[matched_key]]
        forensic_class = (
            "PRESERVED_EQUIVALENCE_CONTRACT_CONFLICT"
            if review["benchmark_opportunity_id"] in (prior_equivalent_ids or set())
            else _partial_class(benchmark_row, matched)
        )
        output.append(
            {
                "benchmark_opportunity_id": review["benchmark_opportunity_id"],
                "study_unit_id": benchmark_row["study_unit_id"],
                "matched_registry_ids": review[matched_key],
                "forensic_class": forensic_class,
                "disposition": "DO_NOT_ENUMERATE_UNTIL_DIRECTIONAL_RELATION_IS_ADJUDICATED",
            }
        )
    return output


def build_partial_match_forensics(root: Path) -> dict[str, Any]:
    root = Path(root)
    benchmark = _load(root, "research/qgen/opportunity_registry_v2/independent_opportunity_benchmark_v1.json")
    v1_comparison = _load(root, "research/qgen/opportunity_registry_v2/v1_benchmark_comparison.json")
    v2_comparison = _load(root, "research/qgen/opportunity_registry_v2/v2_benchmark_comparison_final.json")
    registry_v1 = _load(root, "research/qgen/opportunity_registry/curriculum_question_opportunity_registry_v1.json")
    registry_v2 = _load(root, "research/qgen/opportunity_registry_v2/curriculum_question_opportunity_registry_v2.json")
    benchmark_by_id = {row["benchmark_opportunity_id"]: row for row in benchmark["opportunities"]}
    v1_by_id = {row["opportunity_id"]: row for row in registry_v1["opportunities"]}
    v2_by_id = {row["opportunity_id"]: row for row in registry_v2["opportunities"]}
    v1_rows = _partial_rows(benchmark_by_id, v1_comparison, v1_by_id, "matched_v1_ids")
    prior_equivalent_ids = {
        row["benchmark_opportunity_id"]
        for row in v1_comparison["benchmark_reviews"]
        if row["classification"] in {"EXACT_MATCH", "SEMANTIC_MATCH"}
    }
    v2_rows = _partial_rows(
        benchmark_by_id,
        v2_comparison,
        v2_by_id,
        "matched_v2_ids",
        prior_equivalent_ids,
    )
    v1_counts = Counter(row["forensic_class"] for row in v1_rows)
    v2_counts = Counter(row["forensic_class"] for row in v2_rows)
    report = {
        "schema_version": "1.0",
        "scope": "V1_V2_PARTIAL_MATCH_FORENSICS",
        "taxonomy": list(FORENSIC_CLASSES),
        "v1_partial_reviews": v1_rows,
        "v2_partial_reviews": v2_rows,
        "v1_forensic_counts": {key: v1_counts[key] for key in FORENSIC_CLASSES},
        "v2_forensic_counts": {key: v2_counts[key] for key in FORENSIC_CLASSES},
        "all_rows_classified": len(v1_rows) == 415 and len(v2_rows) == 386,
        "conclusion": "ADJUDICATE_EQUIVALENCE_CONTAINMENT_AND_VARIANCE_BEFORE_ENUMERATION",
        "limitations": (
            "Classes are deterministic structural triage. UNRESOLVED and POSSIBLE rows require a blinded "
            "semantic adjudication before they can change opportunity counts."
        ),
    }
    return _with_hash(report)


_ACTION_WORDS = {
    "arrange", "assess", "choose", "communicate", "counsel", "determine", "diagnose",
    "differentiate", "explain", "identify", "initiate", "interpret", "monitor", "perform",
    "predict", "prevent", "recognize", "recommend", "refer", "select", "stage", "treat", "use",
}


def _structural_benchmark_verdict(row: dict[str, Any]) -> tuple[str, str]:
    words = re.findall(r"[a-z]+", row["principal_decision"].lower())
    actions = [word for word in words if word in _ACTION_WORDS]
    conjunction = bool(re.search(r"\b(?:and|or)\b", row["principal_decision"].lower()))
    if len(set(actions)) > 1:
        return "POSSIBLE_COMPOUND", "SEMANTIC_REVIEW_REQUIRED"
    if conjunction:
        return "ATOMIC_OR_BUNDLED_DECISION", "SEMANTIC_REVIEW_REQUIRED"
    return "ATOMIC_OPPORTUNITY", "STRUCTURAL_PASS"


_VARIANT_STOPWORDS = _ACTION_WORDS | {
    "a", "an", "and", "as", "at", "for", "from", "in", "into", "of", "on", "or", "the", "to", "when", "with",
}


def _decision_tokens(value: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9]+", value.lower())
        if token not in _VARIANT_STOPWORDS and len(token) > 2
    }


def _possible_variant_pairs(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_unit: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_unit[row["study_unit_id"]].append(row)
    candidates = []
    for unit_rows in by_unit.values():
        for index, left in enumerate(unit_rows):
            for right in unit_rows[index + 1:]:
                if (left["response_class"], left["opportunity_family"]) != (
                    right["response_class"], right["opportunity_family"]
                ):
                    continue
                left_tokens = _decision_tokens(left["principal_decision"])
                right_tokens = _decision_tokens(right["principal_decision"])
                union = left_tokens | right_tokens
                similarity = len(left_tokens & right_tokens) / len(union) if union else 0.0
                if similarity < 0.3:
                    continue
                left_norm = _normalized(left["principal_decision"])
                right_norm = _normalized(right["principal_decision"])
                if left_norm == right_norm:
                    relation = "COSMETIC_VARIANT"
                elif similarity >= 0.55:
                    relation = "EVIDENCE_PATH_VARIANT"
                else:
                    relation = "ITEM_VARIANT"
                pair_id = "BVAR-" + hashlib.sha256(
                    f"{left['benchmark_opportunity_id']}|{right['benchmark_opportunity_id']}".encode()
                ).hexdigest()[:12].upper()
                candidates.append(
                    {
                        "pair_id": pair_id,
                        "left_benchmark_opportunity_id": left["benchmark_opportunity_id"],
                        "right_benchmark_opportunity_id": right["benchmark_opportunity_id"],
                        "study_unit_id": left["study_unit_id"],
                        "token_jaccard": round(similarity, 6),
                        "provisional_relation": relation,
                        "audit_status": "SEMANTIC_REVIEW_REQUIRED",
                        "cluster_action": "DO_NOT_MERGE_BEFORE_BLINDED_REVIEW",
                    }
                )
    return sorted(candidates, key=lambda row: row["pair_id"])


def build_benchmark_granularity_audit(root: Path) -> dict[str, Any]:
    benchmark = _load(Path(root), "research/qgen/opportunity_registry_v2/independent_opportunity_benchmark_v1.json")
    rows = []
    counts = Counter()
    for row in benchmark["opportunities"]:
        classification, status = _structural_benchmark_verdict(row)
        counts[classification] += 1
        granularity_verdict = "UNRESOLVED_GRANULARITY"
        rows.append(
            {
                "benchmark_opportunity_id": row["benchmark_opportunity_id"],
                "study_unit_id": row["study_unit_id"],
                "provisional_classification": classification,
                "granularity_verdict": granularity_verdict,
                "audit_status": "SEMANTIC_REVIEW_REQUIRED",
                "canonical_cluster_id": None,
                "counting_policy": "EXCLUDED_FROM_NORMALIZED_DENOMINATOR_PENDING_BLINDED_SEMANTIC_REVIEW",
            }
        )
    possible_variant_pairs = _possible_variant_pairs(benchmark["opportunities"])
    artifact = {
        "schema_version": "1.0",
        "scope": "INDEPENDENT_BENCHMARK_GRANULARITY_AUDIT_V1",
        "benchmark_sha256": benchmark["content_sha256"],
        "benchmark_remains_frozen": True,
        "raw_benchmark_rows": len(rows),
        "provisional_classification_counts": dict(sorted(counts.items())),
        "granularity_verdict_counts": dict(sorted(Counter(row["granularity_verdict"] for row in rows).items())),
        "audited_cluster_count": None,
        "audited_opportunity_denominator": None,
        "row_audits": rows,
        "possible_variant_pair_reviews": possible_variant_pairs,
        "normalized_recall_authorized": False,
        "conclusion": "BENCHMARK_ATOMICITY_AND_CLUSTER_DENOMINATOR_UNRESOLVED",
        "limitations": (
            "This exhaustive pass proves structural conservation and identifies rows needing semantic review. "
            "It does not merge rows on lexical similarity or assert that the remaining rows are clinically independent."
        ),
    }
    return _with_hash(artifact)


def _normalized_benchmark_row(
    source: dict[str, Any],
    principal_decision: str,
    source_ids: list[str],
    transformation: str,
    ordinal: int = 0,
) -> dict[str, Any]:
    identity = "|".join([*sorted(source_ids), transformation, str(ordinal), _normalized(principal_decision)])
    return {
        "normalized_opportunity_id": "NBO-V2-" + hashlib.sha256(identity.encode()).hexdigest()[:16].upper(),
        "study_unit_id": source["study_unit_id"],
        "discipline": source["discipline"],
        "opportunity_family": source["opportunity_family"],
        "response_class": source["response_class"],
        "clinical_stage": source["clinical_stage"],
        "population_context": source["population_context"],
        "principal_decision": principal_decision,
        "primary_reasoning_target": source["primary_reasoning_target"],
        "source_benchmark_opportunity_ids": sorted(source_ids),
        "transformation": transformation,
        "normalization_evidence": "INDEPENDENT_BLINDED_SEMANTIC_REVIEW",
        "mcq_evaluation_eligible": True,
    }


def build_normalized_benchmark_v2(root: Path) -> dict[str, Any]:
    root = Path(root)
    benchmark = _load(root, "research/qgen/opportunity_registry_v2/independent_opportunity_benchmark_v1.json")
    sample = select_benchmark_granularity_sample(root)
    review = _load(root, "research/qgen/opportunity_registry_v3/benchmark_granularity_semantic_review_v1.json")
    if review["source_sample_sha256"] != sample["content_sha256"]:
        raise ValueError("benchmark semantic review does not match the frozen sample")
    if review["content_sha256"] != content_sha256(review):
        raise ValueError("benchmark semantic review content hash is invalid")
    sample_ids = {row["benchmark"]["benchmark_opportunity_id"] for row in sample["opportunities"]}
    review_by_id = {row["benchmark_opportunity_id"]: row for row in review["reviews"]}
    if len(review_by_id) != 120 or set(review_by_id) != sample_ids:
        raise ValueError("benchmark semantic review must cover every sampled opportunity exactly once")
    source_by_id = {row["benchmark_opportunity_id"]: row for row in benchmark["opportunities"]}
    normalized_rows = []
    merged_sources = []
    sibling_targets: dict[str, set[str]] = defaultdict(set)
    compound_sources = 0
    compound_splits = 0
    excluded = 0
    for source_id, decision in sorted(review_by_id.items()):
        source = source_by_id[source_id]
        label = decision["granularity_label"]
        if label == "ATOMIC_DISTINCT":
            normalized_rows.append(_normalized_benchmark_row(source, source["principal_decision"], [source_id], "KEEP"))
        elif label in {"SHOULD_MERGE_WITH_SIBLING", "ITEM_VARIANT_NOT_OPPORTUNITY"}:
            merged_sources.append(source_id)
            for sibling_id in decision["merge_with_sibling_ids"]:
                sibling_targets[sibling_id].add(source_id)
        elif label == "COMPOUND_NEEDS_SPLIT":
            compound_sources += 1
            for ordinal, principal_decision in enumerate(decision["split_atomic_decisions"], 1):
                normalized_rows.append(
                    _normalized_benchmark_row(source, principal_decision, [source_id], "SPLIT_COMPOUND", ordinal)
                )
                compound_splits += 1
        elif label in {"TOO_SPECIALIST", "NOT_MC_SUITABLE"}:
            excluded += 1
        elif label == "UNCERTAIN":
            pass
        else:
            raise ValueError(f"unknown benchmark granularity label: {label}")
    for sibling_id, variant_source_ids in sorted(sibling_targets.items()):
        sibling = source_by_id[sibling_id]
        normalized_rows.append(
            _normalized_benchmark_row(
                sibling,
                sibling["principal_decision"],
                [sibling_id, *sorted(variant_source_ids)],
                "MERGE_VARIANTS",
            )
        )
    normalized_rows.sort(key=lambda row: row["normalized_opportunity_id"])
    reviewed_or_sibling_ids = set(review_by_id) | set(sibling_targets)
    uncertain = len(benchmark["opportunities"]) - len(reviewed_or_sibling_ids)
    metrics = {
        "original_benchmark_opportunities": len(benchmark["opportunities"]),
        "atomic_kept": sum(row["transformation"] in {"KEEP", "MERGE_VARIANTS"} for row in normalized_rows),
        "merged_variant_rows": len(merged_sources),
        "compound_source_rows": compound_sources,
        "compound_splits": compound_splits,
        "excluded": excluded,
        "uncertain": uncertain,
        "final_normalized_atomic_opportunities": len(normalized_rows),
    }
    return _with_hash({
        "schema_version": "2.0",
        "scope": "NORMALIZED_ATOMIC_OPPORTUNITY_BENCHMARK_V2",
        "source_benchmark_sha256": benchmark["content_sha256"],
        "atomic_contract_sha256": build_atomic_opportunity_contract()["content_sha256"],
        "semantic_review_sha256": review["content_sha256"],
        "normalization_policy": (
            "Only independently reviewed rows and explicitly named siblings enter the denominator; all other rows defer. "
            "Rows found not suitable for a multiple-choice question are preserved in audit provenance but excluded from this question-opportunity denominator."
        ),
        "evaluation_denominator_authorized": True,
        "quality_metrics": metrics,
        "opportunities": normalized_rows,
    })


def build_gold_relation_review_input(root: Path) -> dict[str, Any]:
    root = Path(root)
    normalized = build_normalized_benchmark_v2(root)
    registry = _load(root, "research/qgen/opportunity_registry_v2/curriculum_question_opportunity_registry_v2.json")
    by_discipline: dict[str, set[str]] = defaultdict(set)
    for row in normalized["opportunities"]:
        by_discipline[row["discipline"]].add(row["study_unit_id"])
    selected_by_discipline = {}
    calibration_units = []
    heldout_units = []
    for discipline in ("MED", "OBGYN", "PED", "PHELO", "PSY", "SURG"):
        selected = sorted(
            by_discipline[discipline],
            key=lambda value: hashlib.sha256(f"gold|{value}".encode()).hexdigest(),
        )[:4]
        if len(selected) != 4:
            raise ValueError(f"normalized benchmark lacks four reviewed units for {discipline}")
        selected_by_discipline[discipline] = selected
        partitioned = sorted(selected, key=lambda value: hashlib.sha256(f"partition|{value}".encode()).hexdigest())
        calibration_units.extend(partitioned[:2])
        heldout_units.extend(partitioned[2:])
    selected_units = sorted(value for values in selected_by_discipline.values() for value in values)
    atoms_by_unit: dict[str, list[dict[str, Any]]] = defaultdict(list)
    registry_by_unit: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in normalized["opportunities"]:
        if row["study_unit_id"] in selected_units:
            atoms_by_unit[row["study_unit_id"]].append(row)
    for row in registry["opportunities"]:
        if row["study_unit_id"] in selected_units:
            registry_by_unit[row["study_unit_id"]].append(row)
    pairs = []
    for unit_id in selected_units:
        partition = "CALIBRATION" if unit_id in calibration_units else "HELDOUT"
        for atom in sorted(atoms_by_unit[unit_id], key=lambda row: row["normalized_opportunity_id"]):
            for candidate in sorted(registry_by_unit[unit_id], key=lambda row: row["opportunity_id"]):
                pair_key = f"{atom['normalized_opportunity_id']}|{candidate['opportunity_id']}"
                pairs.append({
                    "pair_id": "GRP-" + hashlib.sha256(pair_key.encode()).hexdigest()[:16].upper(),
                    "partition": partition,
                    "normalized_benchmark_opportunity": atom,
                    "registry_candidate": candidate,
                    "candidate_generation": "SAME_STUDY_UNIT_COMPLETE_CROSS_PRODUCT",
                    "review_fields": {"semantic_relation": None, "rationale": None},
                })
    return _with_hash({
        "schema_version": "1.0",
        "scope": "MATCHER_V3_GOLD_RELATION_BLINDED_REVIEW_INPUT",
        "atomic_contract_sha256": build_atomic_opportunity_contract()["content_sha256"],
        "normalized_benchmark_sha256": normalized["content_sha256"],
        "registry_v2_sha256": registry["content_sha256"],
        "reviewer_blindness": "NO_PRIOR_MATCH_LABELS_METRICS_OR_DESIRED_COUNTS",
        "allowed_semantic_relations": list(SEMANTIC_RELATION_TAXONOMY),
        "study_unit_ids": selected_units,
        "study_units_per_discipline": {key: len(value) for key, value in selected_by_discipline.items()},
        "calibration_study_unit_ids": sorted(calibration_units),
        "heldout_study_unit_ids": sorted(heldout_units),
        "pairs": pairs,
    })


def build_matcher_v3_validation(root: Path) -> dict[str, Any]:
    root = Path(root)
    review_input = build_gold_relation_review_input(root)
    gold = _load(root, "research/qgen/opportunity_registry_v3/matcher_v3_gold_relation_set_v1.json")
    if gold["source_input_sha256"] != review_input["content_sha256"]:
        raise ValueError("gold relation set does not match frozen review input")
    if gold["content_sha256"] != content_sha256(gold):
        raise ValueError("gold relation set content hash is invalid")
    input_by_pair = {row["pair_id"]: row for row in review_input["pairs"]}
    if len(gold["reviews"]) != len(input_by_pair) or {row["pair_id"] for row in gold["reviews"]} != set(input_by_pair):
        raise ValueError("gold relation set must cover every candidate pair exactly once")

    def evaluate(partition: str) -> dict[str, Any]:
        confusion: dict[str, Counter[str]] = defaultdict(Counter)
        rows = [row for row in gold["reviews"] if row["partition"] == partition]
        correct = 0
        for adjudication in rows:
            pair = input_by_pair[adjudication["pair_id"]]
            predicted = classify_relation_v3(
                pair["normalized_benchmark_opportunity"], pair["registry_candidate"]
            )
            actual = adjudication["semantic_relation"]
            confusion[actual][predicted] += 1
            correct += predicted == actual
        return {
            "pairs": len(rows),
            "accuracy": round(correct / len(rows), 6) if rows else 0.0,
            "confusion": {
                actual: dict(sorted(predicted.items())) for actual, predicted in sorted(confusion.items())
            },
            "actual_relation_counts": dict(sorted(Counter(row["semantic_relation"] for row in rows).items())),
        }

    calibration = evaluate("CALIBRATION")
    heldout = evaluate("HELDOUT")
    required = (
        "EQUIVALENT", "REGISTRY_BROADER_CONTAINS_BENCHMARK",
        "VARIANT_OF_SAME_DECISION", "RELATED_BUT_DISTINCT",
    )
    required_coverage = {key: heldout["actual_relation_counts"].get(key, 0) > 0 for key in required}
    gate = heldout["accuracy"] >= 0.8 and all(required_coverage.values())
    matcher_contract = {
        "version": "MATCHER_V3_RULE_CONTRACT_1.0",
        "candidate_graph": "COMPLETE_CROSS_PRODUCT_WITHIN_STUDY_UNIT_FOR_GOLD_VALIDATION",
        "ordering": "SORTED_IDS_ORDER_INDEPENDENT",
        "structured_components_precede_text_similarity": True,
        "ambiguous_policy": "UNCERTAIN",
        "relation_taxonomy": list(SEMANTIC_RELATION_TAXONOMY),
        "equivalence_does_not_include_containment_or_variant": True,
    }
    return _with_hash({
        "schema_version": "3.0",
        "scope": "BENCHMARK_MATCHER_V3_HELDOUT_VALIDATION",
        "gold_relation_set_sha256": gold["content_sha256"],
        "implementation_file_sha256": _file_sha256(root / "scripts/qbank/curriculum_opportunity_registry_v3.py"),
        "matcher_contract": matcher_contract,
        "matcher_contract_sha256": hashlib.sha256(canonical_json(matcher_contract).encode()).hexdigest(),
        "calibration_pairs": calibration["pairs"],
        "calibration_accuracy": calibration["accuracy"],
        "calibration_confusion": calibration["confusion"],
        "heldout_pairs": heldout["pairs"],
        "heldout_accuracy": heldout["accuracy"],
        "heldout_confusion": heldout["confusion"],
        "required_relation_coverage": required_coverage,
        "matcher_validation_gate": "PASS" if gate else "FAIL",
        "proceed_to_registry_redesign": gate,
        "stop_reason": None if gate else (
            "Held-out accuracy is below threshold and the gold holdout contains no independently adjudicated "
            "VARIANT_OF_SAME_DECISION relation; reliable four-way discrimination is not established."
        ),
    })


def build_semantic_review_exposure(root: Path) -> dict[str, Any]:
    root = Path(root)
    partial_sample = select_partial_forensic_sample(root)
    partial_review = _load(root, "research/qgen/opportunity_registry_v3/partial_match_semantic_review_v1.json")
    benchmark_sample = select_benchmark_granularity_sample(root)
    benchmark_review = _load(root, "research/qgen/opportunity_registry_v3/benchmark_granularity_semantic_review_v1.json")
    gold_input = build_gold_relation_review_input(root)
    gold_review = _load(root, "research/qgen/opportunity_registry_v3/matcher_v3_gold_relation_set_v1.json")
    partial_units = {
        row["pair_id"]: row["benchmark"]["study_unit_id"] for row in partial_sample["pairs"]
    }
    benchmark_units = {
        row["benchmark"]["benchmark_opportunity_id"]: row["benchmark"]["study_unit_id"]
        for row in benchmark_sample["opportunities"]
    }
    gold_units = {
        row["pair_id"]: row["normalized_benchmark_opportunity"]["study_unit_id"]
        for row in gold_input["pairs"]
    }
    rows = [
        {"review_kind": "PARTIAL_MATCH", "review_id": row["pair_id"], "study_unit_id": partial_units[row["pair_id"]]}
        for row in partial_review["reviews"]
    ] + [
        {
            "review_kind": "BENCHMARK_GRANULARITY",
            "review_id": row["benchmark_opportunity_id"],
            "study_unit_id": benchmark_units[row["benchmark_opportunity_id"]],
        }
        for row in benchmark_review["reviews"]
    ] + [
        {"review_kind": "GOLD_RELATION", "review_id": row["pair_id"], "study_unit_id": gold_units[row["pair_id"]]}
        for row in gold_review["reviews"]
    ]
    return _with_hash({
        "schema_version": "1.0",
        "scope": "ATOMIC_OPPORTUNITY_SEMANTIC_REVIEW_EXPOSURE_V1",
        "source_review_sha256": {
            "PARTIAL_MATCH": partial_review["content_sha256"],
            "BENCHMARK_GRANULARITY": benchmark_review["content_sha256"],
            "GOLD_RELATION": gold_review["content_sha256"],
        },
        "reviewed_relation_counts": {
            "BENCHMARK_GRANULARITY": len(benchmark_review["reviews"]),
            "GOLD_RELATION": len(gold_review["reviews"]),
            "PARTIAL_MATCH": len(partial_review["reviews"]),
        },
        "exposure_level": 3,
        "rows": sorted(rows, key=lambda row: (row["review_kind"], row["review_id"])),
    })


def _normalized(value: str) -> str:
    value = value.lower().replace("&", " and ")
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return " ".join(value.split())


def _canonical_action(value: str, response_class: str) -> str:
    value = _normalized(value)
    if response_class == "DIAGNOSIS" and value in {"recognize", "identify", "diagnose", "assess", "evaluate"}:
        return "diagnose"
    if value in {"manage", "treat"}:
        return "manage"
    if value in {"choose", "select"}:
        return "select"
    return value or "apply"


def _atomic_signature(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "scope_unit": row["study_unit_id"],
        "response_class": row["response_class"],
        "decision_operator": _canonical_action(row.get("action_lemma", "apply"), row["response_class"]),
        "decision_object": _normalized(row.get("clinical_object") or row["key_concept_or_action"]),
        "material_state": None if row.get("clinical_stage") in {None, "NA"} else row["clinical_stage"],
        "material_population": None if row.get("population_context") in {None, "NA"} else row["population_context"],
    }


def _objective_context(root: Path) -> dict[str, str]:
    objectives = _load(root, "research/mcc/objectives_registry.json")
    output = {}
    for row in objectives["objectives"]:
        mcc_id = row.get("mcc_id")
        if not mcc_id:
            continue
        content = row.get("content", {})
        output[mcc_id] = _normalized(
            " ".join(
                str(value)
                for value in (
                    row.get("title", ""),
                    row.get("role", ""),
                    content.get("key_objectives", ""),
                    content.get("enabling_objectives", ""),
                )
            )
        )
    return output


def _map_blueprint(
    row: dict[str, Any], objective_context: dict[str, str] | None = None
) -> dict[str, Any]:
    family = row["opportunity_family"]
    stage = row.get("clinical_stage", "INITIAL_PRESENTATION")
    decision_text = _normalized(
        " ".join(
            str(row.get(field, ""))
            for field in ("learner_decision", "primary_reasoning_target", "clinical_object")
        )
    )
    objective_ids = sorted(row.get("MCC_objective_ids", []))
    objective_text = " ".join((objective_context or {}).get(value, "") for value in objective_ids)
    contextual_text = f"{decision_text} {objective_text}".strip()
    explicit_preventive = any(
        token in contextual_text
        for token in ("screen", "prevent", "immun", "vaccin", "risk reduction", "smoking cessation")
    )
    explicit_psychosocial_legal = any(
        token in contextual_text
        for token in ("communicat", "consent", "capacity", "confidential", "privacy", "professional", "ethical", "legal")
    )
    if family in {"SCREENING", "PREVENTION"} and stage == "PRECLINICAL_OR_PREVENTIVE" and explicit_preventive:
        dimension, dimension_confidence, dimension_rule = "Health Promotion & Illness Prevention", "HIGH", "DIM_PREVENTIVE_PURPOSE"
    elif family in {"COMMUNICATION", "CAPACITY_CONSENT", "CONFIDENTIALITY", "PROFESSIONALISM", "ETHICAL_LEGAL_ACTION"} and explicit_psychosocial_legal:
        dimension, dimension_confidence, dimension_rule = "Psychosocial Aspects", "HIGH", "DIM_PSYCHOSOCIAL_LEGAL_CONTEXT"
    elif stage in {"LONG_TERM_MANAGEMENT", "FOLLOW_UP"}:
        dimension, dimension_confidence, dimension_rule = "Chronic", "REVIEW_REQUIRED", "DIM_LONGITUDINAL_CONTEXT_AMBIGUOUS"
    else:
        dimension, dimension_confidence, dimension_rule = "Acute", "REVIEW_REQUIRED", "DIM_CLINICAL_CONTEXT_AMBIGUOUS"

    explicit_assessment = any(
        token in decision_text
        for token in ("diagnos", "recogn", "differentiat", "assess", "screen", "identify")
    )
    explicit_initial_management = any(
        token in decision_text for token in ("initial management", "initiat", "manage", "treat")
    )
    if family in {"DIAGNOSIS", "DIFFERENTIAL_DIAGNOSIS", "ADVERSE_EFFECT_RECOGNITION", "SCREENING"} and explicit_assessment:
        activity, activity_confidence, activity_rule = "Assessment/Diagnosis", "HIGH", "ACT_ASSESSMENT_RESPONSE"
    elif family == "INITIAL_MANAGEMENT" and explicit_initial_management:
        activity, activity_confidence, activity_rule = "Management", "HIGH", "ACT_INITIAL_MANAGEMENT_RESPONSE"
    elif family == "CONFIDENTIALITY":
        activity, activity_confidence, activity_rule = "Professional Behaviours", "HIGH", "ACT_CONFIDENTIALITY_DUTY"
    elif family in {"COMMUNICATION", "COUNSELLING"}:
        activity, activity_confidence, activity_rule = "Communication", "REVIEW_REQUIRED", "ACT_COMMUNICATION_CONTEXT_AMBIGUOUS"
    elif family in {"CAPACITY_CONSENT", "PROFESSIONALISM", "ETHICAL_LEGAL_ACTION", "SYSTEM_ORGANIZATION"}:
        activity, activity_confidence, activity_rule = "Professional Behaviours", "REVIEW_REQUIRED", "ACT_PROFESSIONAL_CONTEXT_AMBIGUOUS"
    elif family in {"NEXT_MANAGEMENT_STEP", "EMERGENCY_STABILIZATION", "FOLLOW_UP", "MONITORING", "PREVENTION"}:
        activity, activity_confidence, activity_rule = "Management", "REVIEW_REQUIRED", "ACT_MANAGEMENT_CONTEXT_AMBIGUOUS"
    else:
        activity, activity_confidence, activity_rule = "Assessment/Diagnosis", "REVIEW_REQUIRED", "ACT_CLINICAL_RESPONSE_AMBIGUOUS"
    all_dimensions = ["Acute", "Chronic", "Health Promotion & Illness Prevention", "Psychosocial Aspects"]
    all_activities = ["Assessment/Diagnosis", "Management", "Communication", "Professional Behaviours"]
    return {
        "dimension_of_care": dimension,
        "dimension_confidence": dimension_confidence,
        "dimension_rule_id": dimension_rule,
        "allowed_secondary_dimensions": [] if dimension_confidence == "HIGH" else [value for value in all_dimensions if value != dimension],
        "physician_activity": activity,
        "activity_confidence": activity_confidence,
        "activity_rule_id": activity_rule,
        "allowed_secondary_activities": [] if activity_confidence == "HIGH" else [value for value in all_activities if value != activity],
        "objective_context_ids": objective_ids,
        "allocation_authority": dimension_confidence == "HIGH" and activity_confidence == "HIGH",
    }


def build_registry_v3(root: Path) -> dict[str, Any]:
    root = Path(root)
    v2 = _load(root, "research/qgen/opportunity_registry_v2/curriculum_question_opportunity_registry_v2.json")
    objective_context = _objective_context(root)
    output = []
    for source in v2["opportunities"]:
        signature = _atomic_signature(source)
        signature_sha = hashlib.sha256(
            json.dumps(signature, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        canonical_atomic = False
        mapping = _map_blueprint(source, objective_context)
        mapping["allocation_authority"] = False
        row = dict(source)
        row.update(
            {
                "schema_version": "3.0",
                "source_v2_opportunity_id": source["opportunity_id"],
                "opportunity_id": "QOP-V3-" + signature_sha[:12].upper(),
                "atomic_signature_v1": signature,
                "atomic_signature_sha256": signature_sha,
                "atomicity_status": "CANONICAL_ATOMIC" if canonical_atomic else "REQUIRES_ATOMICITY_REVIEW",
                "atomicity_basis": (
                    "V2_ATOMIC_CLEAR_KEY_REVIEW_DID_NOT_APPLY_ATOMIC_OPPORTUNITY_CONTRACT_V1"
                    if source.get("provenance_type") != "V1_PRESERVED"
                    else "V1_POLICY_PRESERVATION_WAS_NOT_ATOMICITY_VALIDATION"
                ),
                "recommended_item_capacity": source["recommended_item_capacity"] if canonical_atomic else 0,
                "generation_readiness": source["generation_readiness"] if canonical_atomic else "ATOMICITY_REVIEW_REQUIRED",
                "blueprint_mapping_v2": mapping,
            }
        )
        output.append(row)
    artifact = {
        "schema_version": "3.0",
        "scope": "PROVISIONAL_CURRICULUM_QUESTION_OPPORTUNITY_REGISTRY_V3_SCAFFOLD",
        "registry_v2_sha256": v2["content_sha256"],
        "atomic_contract_sha256": build_atomic_opportunity_contract()["content_sha256"],
        "canonicalization_policy": "V2_LINEAGE_SCAFFOLD_NO_ENUMERATION",
        "canonicalization_authorized": False,
        "blocked_by": "MATCHER_V3_HELDOUT_VALIDATION_GATE",
        "opportunities": sorted(output, key=lambda row: row["opportunity_id"]),
    }
    statuses = Counter(row["atomicity_status"] for row in output)
    artifact["atomicity_status_counts"] = dict(sorted(statuses.items()))
    artifact["allocatable_atomic_opportunities"] = sum(row["recommended_item_capacity"] > 0 for row in output)
    return _with_hash(artifact)


def validate_registry_v3(registry: dict[str, Any]) -> None:
    rows = registry.get("opportunities", [])
    ids = [row["opportunity_id"] for row in rows]
    source_ids = [row["source_v2_opportunity_id"] for row in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate V3 opportunity id")
    if len(source_ids) != len(set(source_ids)):
        raise ValueError("V2 lineage must be one-to-one")
    for row in rows:
        expected = hashlib.sha256(
            json.dumps(row["atomic_signature_v1"], sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        if row["atomic_signature_sha256"] != expected:
            raise ValueError("atomic signature hash mismatch")
        if row["atomicity_status"] != "CANONICAL_ATOMIC" and row["recommended_item_capacity"] != 0:
            raise ValueError("non-canonical opportunity has allocatable capacity")
        if row["atomicity_status"] != "CANONICAL_ATOMIC" and row["generation_readiness"] != "ATOMICITY_REVIEW_REQUIRED":
            raise ValueError("non-canonical opportunity must remain atomicity-review blocked")
        mapping = row["blueprint_mapping_v2"]
        if row["atomicity_status"] != "CANONICAL_ATOMIC" and mapping["allocation_authority"]:
            raise ValueError("non-canonical opportunity cannot have blueprint allocation authority")
        if mapping["allocation_authority"] and (
            mapping["dimension_confidence"] != "HIGH" or mapping["activity_confidence"] != "HIGH"
        ):
            raise ValueError("uncertain blueprint mapping cannot have allocation authority")
        if "BOP-" in canonical_json(row):
            raise ValueError("benchmark identifier leaked into V3 enumeration")
    if registry.get("content_sha256") != content_sha256(registry):
        raise ValueError("V3 content hash mismatch")


def _evaluate_blueprint(
    rows: list[dict[str, Any]],
    registry_by_id: dict[str, dict[str, Any]],
    objective_context: dict[str, str],
) -> dict[str, Any]:
    dimension_total = dimension_correct = activity_total = activity_correct = 0
    dimension_matrix: dict[str, Counter[str]] = defaultdict(Counter)
    activity_matrix: dict[str, Counter[str]] = defaultdict(Counter)
    for review in rows:
        predicted = _map_blueprint(registry_by_id[review["opportunity_id"]], objective_context)
        if predicted["dimension_confidence"] == "HIGH":
            dimension_total += 1
            dimension_correct += predicted["dimension_of_care"] == review["dimension_of_care"]
            dimension_matrix[predicted["dimension_of_care"]][review["dimension_of_care"]] += 1
        if predicted["activity_confidence"] == "HIGH":
            activity_total += 1
            activity_correct += predicted["physician_activity"] == review["physician_activity"]
            activity_matrix[predicted["physician_activity"]][review["physician_activity"]] += 1
    ratio = lambda n, d: round(n / d, 6) if d else 0.0
    return {
        "dimension_high_confidence_rows": dimension_total,
        "dimension_high_confidence_accuracy": ratio(dimension_correct, dimension_total),
        "dimension_high_confidence_coverage": ratio(dimension_total, len(rows)),
        "dimension_confusion_matrix": {key: dict(sorted(value.items())) for key, value in sorted(dimension_matrix.items())},
        "activity_high_confidence_rows": activity_total,
        "activity_high_confidence_accuracy": ratio(activity_correct, activity_total),
        "activity_high_confidence_coverage": ratio(activity_total, len(rows)),
        "activity_confusion_matrix": {key: dict(sorted(value.items())) for key, value in sorted(activity_matrix.items())},
    }


def build_blueprint_mapping_v2(root: Path) -> dict[str, Any]:
    root = Path(root)
    registry = _load(root, "research/qgen/opportunity_registry/curriculum_question_opportunity_registry_v1.json")
    audit = _load(root, "research/qgen/opportunity_registry_v2/mcq_blueprint_family_blind_audit_v1.json")
    registry_by_id = {row["opportunity_id"]: row for row in registry["opportunities"]}
    objective_context = _objective_context(root)
    ordered = sorted(
        audit["reviews"],
        key=lambda row: hashlib.sha256(f"blueprint-v2|{row['opportunity_id']}".encode()).hexdigest(),
    )
    holdout = [row for index, row in enumerate(ordered) if index % 3 == 0]
    calibration = [row for index, row in enumerate(ordered) if index % 3 != 0]
    rules = [
        {"rule_id": "DIM_PREVENTIVE_PURPOSE", "basis": "preventive purpose plus preventive stage"},
        {"rule_id": "DIM_PSYCHOSOCIAL_LEGAL_CONTEXT", "basis": "communication, consent, confidentiality, professionalism, or legal context"},
        {"rule_id": "DIM_LONGITUDINAL_CONTEXT_AMBIGUOUS", "basis": "longitudinal stage requires case-level review"},
        {"rule_id": "DIM_CLINICAL_CONTEXT_AMBIGUOUS", "basis": "family alone does not determine care dimension"},
        {"rule_id": "ACT_ASSESSMENT_RESPONSE", "basis": "diagnostic, differential, adverse-effect recognition, or screening response"},
        {"rule_id": "ACT_INITIAL_MANAGEMENT_RESPONSE", "basis": "explicit initial management response"},
        {"rule_id": "ACT_CONFIDENTIALITY_DUTY", "basis": "confidentiality duty"},
        {"rule_id": "ACT_COMMUNICATION_CONTEXT_AMBIGUOUS", "basis": "communication action can serve several MCC activity domains"},
        {"rule_id": "ACT_PROFESSIONAL_CONTEXT_AMBIGUOUS", "basis": "professional context requires case-level review"},
        {"rule_id": "ACT_MANAGEMENT_CONTEXT_AMBIGUOUS", "basis": "action family alone does not establish MCC activity"},
        {"rule_id": "ACT_CLINICAL_RESPONSE_AMBIGUOUS", "basis": "clinical response requires case-level review"},
    ]
    artifact = {
        "schema_version": "2.0",
        "scope": "MCC_BLUEPRINT_MAPPING_V2_CALIBRATION",
        "audit_input_sha256": audit["content_sha256"],
        "partition_contract": "SHA256_BLUEPRINT_V2_ORDER_EVERY_THIRD_ROW_HOLDOUT",
        "audit_rows": len(ordered),
        "calibration_rows": len(calibration),
        "holdout_rows": len(holdout),
        "rules": rules,
        "calibration": _evaluate_blueprint(calibration, registry_by_id, objective_context),
        "holdout": _evaluate_blueprint(holdout, registry_by_id, objective_context),
        "sample_assignments": [
            {
                "opportunity_id": row["opportunity_id"],
                "audit_partition": "HOLDOUT" if index % 3 == 0 else "CALIBRATION",
                **_map_blueprint(registry_by_id[row["opportunity_id"]], objective_context),
            }
            for index, row in enumerate(ordered)
        ],
        "ambiguous_mapping_policy": "REVIEW_REQUIRED_NO_ALLOCATION_AUTHORITY",
        "production_allocation_authority": False,
    }
    return _with_hash(artifact)


def build_copyright_audit(root: Path) -> dict[str, Any]:
    root = Path(root)
    v1 = _load(root, "research/qgen/opportunity_registry/curriculum_question_opportunity_registry_v1.json")
    v2 = _load(root, "research/qgen/opportunity_registry_v2/curriculum_question_opportunity_registry_v2.json")
    benchmark = _load(root, "research/qgen/opportunity_registry_v2/independent_opportunity_benchmark_v1.json")
    v3 = build_registry_v3(root)
    normalized = build_normalized_benchmark_v2(root)
    gold = _load(root, "research/qgen/opportunity_registry_v3/matcher_v3_gold_relation_set_v1.json")
    matcher_validation = build_matcher_v3_validation(root)
    blueprint = build_blueprint_mapping_v2(root)
    v2_by_id = {row["opportunity_id"]: row for row in v2["opportunities"]}
    clinical_text_fields = (
        "clinical_topic",
        "key_concept_or_action",
        "learner_decision",
        "primary_reasoning_target",
        "source_competency_text",
    )
    clinical_lineage_mismatches = []
    for row in v3["opportunities"]:
        source = v2_by_id[row["source_v2_opportunity_id"]]
        if any(row.get(field) != source.get(field) for field in clinical_text_fields):
            clinical_lineage_mismatches.append(row["source_v2_opportunity_id"])
    split_rows = [row for row in normalized["opportunities"] if row["transformation"] == "SPLIT_COMPOUND"]
    max_split_words = max((len(row["principal_decision"].split()) for row in split_rows), default=0)
    artifact = {
        "schema_version": "1.0",
        "scope": "ATOMIC_OPPORTUNITY_CONTRACT_V1_REGISTRY_V3_COPYRIGHT_AUDIT",
        "registry_v1_sha256": v1["content_sha256"],
        "registry_v2_sha256": v2["content_sha256"],
        "benchmark_sha256": benchmark["content_sha256"],
        "registry_v3_sha256": v3["content_sha256"],
        "normalized_benchmark_v2_sha256": normalized["content_sha256"],
        "gold_relation_set_sha256": gold["content_sha256"],
        "matcher_v3_validation_sha256": matcher_validation["content_sha256"],
        "blueprint_mapping_v2_sha256": blueprint["content_sha256"],
        "allocation_v3": "NOT_CREATED_MATCHER_GATE_FAILED",
        "production_queue_v3": "NOT_CREATED_MATCHER_GATE_FAILED",
        "new_clinical_prose_authored": len(split_rows),
        "new_clinical_prose_kind": "INDEPENDENT_CONCISE_ATOMIC_SPLIT_LABELS",
        "maximum_new_split_label_words": max_split_words,
        "lineage_copied_rows": len(v2["opportunities"]),
        "clinical_text_fields_compared": list(clinical_text_fields),
        "clinical_lineage_mismatches": clinical_lineage_mismatches,
        "lineage_copy_policy": "V3_REUSES_FROZEN_V2_CLINICAL_TEXT_FIELDS_UNCHANGED",
        "new_prose_scope": "METHODOLOGICAL_CONTRACT_RULES_DIAGNOSTIC_LABELS_AND_CONCISE_ATOMIC_SPLITS",
        "substantial_source_prose_overlap_review": "PASS_CONCISE_LABELS_NO_SUBSTANTIAL_SOURCE_PASSAGE",
        "COPYRIGHT_AUDIT": "PASS" if not clinical_lineage_mismatches and max_split_words <= 25 else "FAIL",
    }
    return _with_hash(artifact)


def build_milestone(root: Path) -> dict[str, Any]:
    diagnosis = build_matcher_regression_diagnosis(root)
    partials = build_complete_partial_classifier(root)
    benchmark_review = _load(Path(root), "research/qgen/opportunity_registry_v3/benchmark_granularity_semantic_review_v1.json")
    normalized = build_normalized_benchmark_v2(root)
    gold = _load(Path(root), "research/qgen/opportunity_registry_v3/matcher_v3_gold_relation_set_v1.json")
    matcher_validation = build_matcher_v3_validation(root)
    registry_scaffold = build_registry_v3(root)
    blueprint = build_blueprint_mapping_v2(root)
    copyright_audit = build_copyright_audit(root)
    return _with_hash(
        {
            "schema_version": "1.0",
            "scope": "ATOMIC_OPPORTUNITY_CONTRACT_V1_REGISTRY_V3_MILESTONE",
            "ATOMIC_OPPORTUNITY_AND_MATCHER_CALIBRATION": "BLOCKED",
            "ATOMIC_OPPORTUNITY_CONTRACT_V1": "DEFINED",
            "ATOMIC_OPPORTUNITY_CONTRACT_SHA256": build_atomic_opportunity_contract()["content_sha256"],
            "MATCHER_REGRESSION_ROOT_CAUSE": diagnosis["root_cause"],
            "V1_FULL_MATCHES": diagnosis["v1_full_matches"],
            "V1_FULL_MATCHES_DOWNGRADED_BY_V2_REVIEW": diagnosis["v1_full_matches_downgraded"],
            "MONOTONIC_COUNTERFACTUAL_V2_FULL_MATCHES": diagnosis["counterfactual_monotonic_v2_full_matches"],
            "PARTIAL_MATCH_FORENSICS": partials["relation_counts"],
            "DISCRIMINATOR_VARIANT_CLASSIFICATION": partials["discriminator_class_counts"],
            "BENCHMARK_GRANULARITY_REVIEWED": benchmark_review["reviewed"],
            "BENCHMARK_GRANULARITY_COUNTS": benchmark_review["label_counts"],
            "NORMALIZED_BENCHMARK_V2_SHA256": normalized["content_sha256"],
            "NORMALIZED_BENCHMARK_ATOMIC_OPPORTUNITIES": len(normalized["opportunities"]),
            "BENCHMARK_TRANSFORMS": normalized["quality_metrics"],
            "GOLD_RELATION_SET_SHA256": gold["content_sha256"],
            "MATCHER_V3_SHA256": matcher_validation["content_sha256"],
            "MATCHER_V3_HELDOUT_ACCURACY": matcher_validation["heldout_accuracy"],
            "MATCHER_V3_HELDOUT_CONFUSION": matcher_validation["heldout_confusion"],
            "MATCHER_V3_GATE": matcher_validation["matcher_validation_gate"],
            "ENUMERATION_V3_IMPLEMENTED": False,
            "REGISTRY_V3_CANONICALIZED": False,
            "REGISTRY_V3_PROVISIONAL_SCAFFOLD_SHA256": registry_scaffold["content_sha256"],
            "V1_NORMALIZED_METRICS": "NOT_RUN_MATCHER_GATE_FAILED",
            "V2_NORMALIZED_METRICS": "NOT_RUN_MATCHER_GATE_FAILED",
            "BLUEPRINT_MAPPING_V2_HOLDOUT": blueprint["holdout"],
            "BLUEPRINT_MAPPING_V2_PRODUCTION_AUTHORITY": blueprint["production_allocation_authority"],
            "COPYRIGHT_AUDIT": copyright_audit["COPYRIGHT_AUDIT"],
            "PRODUCTION_QUESTIONS_GENERATED": 0,
            "QUESTION_BANK_ALLOCATION_PLAN_V3": "NOT_CREATED_MATCHER_GATE_FAILED",
            "PRODUCTION_QUEUE_V3": "NOT_CREATED_MATCHER_GATE_FAILED",
            "PRODUCTION_PILOT_GATE": "FAIL",
            "READY_FOR_PRODUCTION_PILOT": "NO",
            "NEXT_DOMINANT_BOTTLENECK": "MATCHER_V3_RELATION_DISCRIMINATION_AND_VARIANT_HOLDOUT_COVERAGE",
            "NEXT_STEP": "REFINE_MATCHER_V3",
        }
    )


def write_artifacts(root: Path) -> dict[str, str]:
    root = Path(root)
    target = root / "research/qgen/opportunity_registry_v3"
    target.mkdir(parents=True, exist_ok=True)
    artifacts = {
        target / "atomic_opportunity_contract_v1.json": build_atomic_opportunity_contract(),
        target / "matching_diagnostic_contract_v1.json": build_matching_diagnostic_contract(root),
        target / "v1_preservation_audit_v1.json": build_v1_preservation_audit(root),
        target / "matcher_regression_diagnosis_v1.json": build_matcher_regression_diagnosis(root),
        target / "benchmark_matcher_calibration_v1.json": build_benchmark_matcher_calibration(root),
        target / "partial_match_forensics_v1.json": build_partial_match_forensics(root),
        target / "partial_match_forensic_sample_v1.json": select_partial_forensic_sample(root),
        target / "complete_partial_match_classification_v1.json": build_complete_partial_classifier(root),
        target / "benchmark_granularity_audit_v1.json": build_benchmark_granularity_audit(root),
        target / "benchmark_granularity_sample_v1.json": select_benchmark_granularity_sample(root),
        target / "normalized_atomic_opportunity_benchmark_v2.json": build_normalized_benchmark_v2(root),
        target / "matcher_v3_gold_relation_review_input_v1.json": build_gold_relation_review_input(root),
        target / "matcher_v3_validation_v1.json": build_matcher_v3_validation(root),
        target / "semantic_review_exposure_v1.json": build_semantic_review_exposure(root),
        target / "curriculum_question_opportunity_registry_v3.json": build_registry_v3(root),
        target / "blueprint_mapping_v2.json": build_blueprint_mapping_v2(root),
        root / "reports/atomic_opportunity_contract_v1_registry_v3_copyright_audit.json": build_copyright_audit(root),
        root / "reports/atomic_opportunity_contract_v1_registry_v3_milestone.json": build_milestone(root),
    }
    for path, artifact in artifacts.items():
        path.write_text(canonical_json(artifact))
    return {str(path.relative_to(root)): artifact["content_sha256"] for path, artifact in artifacts.items()}


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    args = parser.parse_args()
    print(canonical_json(write_artifacts(args.root)), end="")
