"""Deterministic support for independent opportunity-relation calibration.

Semantic labels are deliberately external to this module.  It mines real
canonical pairs, blinds their provenance/version, validates adjudications,
and computes reproducible multiclass metrics and append-only graph checks.
"""

from __future__ import annotations

from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Iterable, Mapping, Sequence


RELATIONS = (
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

BASELINE_HEAD = "01eff40984bee76418c7fab82a1ded9fbfa2d9e5"
CONTRACT_SHA256 = "c250e20c3da4e109c06c856c573e0e0006ab959ffd26faeccd2c55ebf3237e9a"
MATCHER_V3_SHA256 = "1673a305ecef18b1d57cd9e151f5b0c1d0c81b0ae1b78673269c0b717fb9b5c3"


def canonical_json(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def content_sha256(value: Mapping[str, Any]) -> str:
    payload = {key: item for key, item in value.items() if key != "content_sha256"}
    return hashlib.sha256(canonical_json(payload).encode()).hexdigest()


def with_hash(value: Mapping[str, Any]) -> dict[str, Any]:
    result = dict(value)
    result["content_sha256"] = content_sha256(result)
    return result


def _read(root: Path, relative: str) -> dict[str, Any]:
    return json.loads((Path(root) / relative).read_text())


def build_failed_v3_baseline(root: Path) -> dict[str, Any]:
    milestone = _read(root, "reports/atomic_opportunity_contract_v1_registry_v3_milestone.json")
    validation = _read(root, "research/qgen/opportunity_registry_v3/matcher_v3_validation_v1.json")
    confusion = validation["heldout_confusion"]
    correct = sum(row.get(actual, 0) for actual, row in confusion.items())
    if milestone["MATCHER_V3_SHA256"] != MATCHER_V3_SHA256:
        raise ValueError("MATCHER_V3_BASELINE_HASH_DRIFT")
    if milestone["ATOMIC_OPPORTUNITY_CONTRACT_SHA256"] != CONTRACT_SHA256:
        raise ValueError("ATOMIC_OPPORTUNITY_CONTRACT_HASH_DRIFT")
    return with_hash({
        "schema_version": "1.0",
        "scope": "MATCHER_V3_FAILED_GENERALIZATION_BASELINE",
        "status": "MATCHER_V3_FAILED_GENERALIZATION_BASELINE",
        "starting_head": BASELINE_HEAD,
        "atomic_opportunity_contract_sha256": CONTRACT_SHA256,
        "matcher_v3_sha256": MATCHER_V3_SHA256,
        "heldout_pairs": validation["heldout_pairs"],
        "correct": correct,
        "accuracy": validation["heldout_accuracy"],
        "confusion_matrix": confusion,
        "medical_question_accuracy": None,
        "interpretation": "OPPORTUNITY_RELATIONSHIP_CLASSIFICATION_ONLY",
    })


def build_gold_v2_failure_analysis(root: Path) -> dict[str, Any]:
    """Describe the frozen Gold V2 support failure without reopening it."""
    packet = _read(root, "research/qgen/opportunity_relation_v4/relation_gold_v2_review_input.json")
    gold = _read(root, "research/qgen/opportunity_relation_v4/relation_gold_v2.json")
    reviews = gold["reviews"]
    family_counts = Counter(
        row["curriculum_context"].get("family_a")
        or row["curriculum_context"].get("family_b")
        or "UNKNOWN"
        for row in packet["pairs"]
    )
    counts = {label: int(gold["relation_counts"].get(label, 0)) for label in RELATIONS}
    absent = [label for label in RELATIONS if label != "UNCERTAIN" and counts[label] == 0]
    return with_hash({
        "schema_version": "1.0",
        "scope": "RELATION_GOLD_V2_FAILURE_ANALYSIS",
        "relation_gold_v2_sha256": gold["content_sha256"],
        "review_input_sha256": packet["content_sha256"],
        "candidate_pairs_mined": len(packet["pairs"]),
        "reviewed_pairs": len(reviews),
        "relation_counts": counts,
        "uncertain_rate": _safe_ratio(counts["UNCERTAIN"], len(reviews)),
        "absent_relation_classes": absent,
        "discipline_counts": dict(sorted(packet["discipline_counts"].items())),
        "family_counts": dict(sorted(family_counts.items())),
        "family_count": len(family_counts),
        "structural_mining_strategy": "LABEL_GUIDED_REUSE_OF_SMALL_PRIOR_REVIEW_SAMPLES",
        "strategy_limit": "PRIOR_LABELS_INDEXED_CANDIDATE_SHAPES_BUT_DID_NOT_YIELD_REPRESENTATIVE_REAL_CLASS_SUPPORT",
        "failure_reason": "INSUFFICIENT_REPRESENTATIVE_CLASS_SUPPORT",
    })


_PROJECT_FIELDS = (
    "discipline", "study_unit_id", "study_unit", "clinical_topic",
    "opportunity_family", "response_class", "clinical_stage",
    "population_context", "severity_context", "principal_decision",
    "learner_decision", "key_concept_or_action", "primary_reasoning_target",
    "MCC_physician_activity", "MCC_objective_ids",
)


def _blind_projection(row: Mapping[str, Any]) -> dict[str, Any]:
    return {key: row[key] for key in _PROJECT_FIELDS if row.get(key) not in (None, "", [], {})}


def _opaque_source_ref(artifact: Mapping[str, Any]) -> str:
    digest = artifact.get("content_sha256") or content_sha256(artifact)
    return f"CANONICAL_SOURCE_SHA256:{digest}"


def _stable_rank(value: str) -> str:
    return hashlib.sha256(f"relation-gold-v2|{value}".encode()).hexdigest()


def _candidate(
    left: Mapping[str, Any], right: Mapping[str, Any], *, source_refs: Sequence[str], salt: str,
) -> dict[str, Any]:
    a, b = _blind_projection(left), _blind_projection(right)
    signature = canonical_json({"a": a, "b": b})
    return {
        "pair_id": "RG2-" + hashlib.sha256(f"{salt}|{signature}".encode()).hexdigest()[:16].upper(),
        "opportunity_a": a,
        "opportunity_b": b,
        "curriculum_context": {
            "discipline": a.get("discipline") or b.get("discipline"),
            "study_unit_id": a.get("study_unit_id") or b.get("study_unit_id"),
            "family_a": a.get("opportunity_family"),
            "family_b": b.get("opportunity_family"),
        },
        "source_artifact_refs": list(source_refs),
        "review_fields": {"relation": None, "justification": None},
    }


def mine_relation_review_candidates(root: Path) -> dict[str, Any]:
    """Mine a bounded representative packet without exposing prior labels.

    Prior independently reviewed artifacts are used only as a discovery index
    for genuinely observed rare candidate shapes.  Their labels never enter the
    reviewer packet.  Fresh reviewers must adjudicate every pair from scratch.
    """
    root = Path(root)
    partial_input = _read(root, "research/qgen/opportunity_registry_v3/partial_match_forensic_sample_v1.json")
    partial_review = _read(root, "research/qgen/opportunity_registry_v3/partial_match_semantic_review_v1.json")
    gold_input = _read(root, "research/qgen/opportunity_registry_v3/matcher_v3_gold_relation_review_input_v1.json")
    gold_review = _read(root, "research/qgen/opportunity_registry_v3/matcher_v3_gold_relation_set_v1.json")
    stress_input = _read(root, "research/qgen/opportunity_registry_v2/semantic_duplicate_stress_input_v1.json")
    stress_review = _read(root, "research/qgen/opportunity_registry_v2/semantic_duplicate_stress_test_v1.json")

    pairs: list[dict[str, Any]] = []
    partial_by_id = {row["pair_id"]: row for row in partial_input["pairs"]}
    partial_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for review in partial_review["reviews"]:
        partial_groups[review["semantic_relation"]].append(review)
    partial_limits = {
        "EQUIVALENT": 8,
        "REGISTRY_BROADER_CONTAINS_BENCHMARK": 12,
        "REGISTRY_NARROWER_THAN_BENCHMARK": 1,
        "VARIANT_OF_SAME_DECISION": 3,
        "RELATED_BUT_DISTINCT": 12,
        "UNCERTAIN": 1,
    }
    partial_refs = [_opaque_source_ref(partial_input), _opaque_source_ref(partial_review)]
    for relation, limit in partial_limits.items():
        for review in sorted(partial_groups.get(relation, []), key=lambda row: _stable_rank(row["pair_id"]))[:limit]:
            source = partial_by_id[review["pair_id"]]
            pairs.append(_candidate(
                source["benchmark"], source["candidate_rows"][0], source_refs=partial_refs,
                salt=f"partial|{source['pair_id']}",
            ))

    gold_by_id = {row["pair_id"]: row for row in gold_input["pairs"]}
    gold_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for review in gold_review["reviews"]:
        gold_groups[review["semantic_relation"]].append(review)
    gold_refs = [_opaque_source_ref(gold_input), _opaque_source_ref(gold_review)]
    for relation, limit in {
        "EQUIVALENT": 6,
        "REGISTRY_BROADER_CONTAINS_BENCHMARK": 8,
        "RELATED_BUT_DISTINCT": 12,
        "UNRELATED": 10,
    }.items():
        for review in sorted(gold_groups.get(relation, []), key=lambda row: _stable_rank(row["pair_id"]))[:limit]:
            source = gold_by_id[review["pair_id"]]
            pairs.append(_candidate(
                source["normalized_benchmark_opportunity"], source["registry_candidate"],
                source_refs=gold_refs, salt=f"gold|{source['pair_id']}",
            ))

    stress_by_id = {row["pair_id"]: row for row in stress_input["pairs"]}
    stress_refs = [_opaque_source_ref(stress_input), _opaque_source_ref(stress_review)]
    near_ids = [row["pair_id"] for row in stress_review["reviews"] if row["classification"] == "NEAR_DUPLICATE"]
    for pair_id in sorted(near_ids, key=_stable_rank):
        source = stress_by_id[pair_id]
        pairs.append(_candidate(source["left"], source["right"], source_refs=stress_refs, salt=f"stress|{pair_id}"))

    # Deduplicate on blinded semantic content; endpoint source/version IDs are intentionally absent.
    unique: dict[str, dict[str, Any]] = {}
    for row in pairs:
        signature = canonical_json({"a": row["opportunity_a"], "b": row["opportunity_b"]})
        unique.setdefault(signature, row)
    selected = sorted(unique.values(), key=lambda row: row["pair_id"])
    discipline_counts = Counter(
        row["curriculum_context"].get("discipline") for row in selected
        if row["curriculum_context"].get("discipline")
    )
    missing = {"MED", "PED", "OBGYN", "SURG", "PSY", "PHELO"} - set(discipline_counts)
    if missing:
        raise ValueError(f"RELATION_GOLD_DISCIPLINE_COVERAGE_MISSING:{sorted(missing)}")
    return with_hash({
        "schema_version": "2.0",
        "scope": "RELATION_GOLD_V2_BLINDED_REVIEW_INPUT",
        "atomic_contract_sha256": CONTRACT_SHA256,
        "allowed_relations": list(RELATIONS),
        "candidate_selection_policy": "REAL_CANONICAL_ROWS_NO_SYNTHETIC_RELATION_EXAMPLES",
        "reviewer_blindness": "PREDICTIONS_LABEL_TARGETS_SOURCE_VERSIONS_AND_PRIOR_OUTCOMES_WITHHELD",
        "discipline_counts": dict(sorted(discipline_counts.items())),
        "family_count": len({row["curriculum_context"].get("family_a") for row in selected}),
        "rare_class_policy": "REPORT_ZERO_OR_INSUFFICIENT_SUPPORT_NEVER_FABRICATE",
        "pairs": selected,
    })


def _relation_text(row: Mapping[str, Any]) -> str:
    return " ".join(
        str(row.get(key) or "")
        for key in (
            "clinical_topic", "principal_decision", "learner_decision",
            "key_concept_or_action", "primary_reasoning_target",
        )
    ).strip().lower()


def _relation_tokens(row: Mapping[str, Any]) -> set[str]:
    return {
        token for token in re.findall(r"[a-z0-9]+", _relation_text(row))
        if len(token) > 2 and token not in {
            "the", "and", "for", "from", "with", "into", "apply", "reason",
            "reasoning", "vignette", "evidence", "decision", "differentiate",
        }
    }


def _jaccard(left: Mapping[str, Any], right: Mapping[str, Any]) -> float:
    a, b = _relation_tokens(left), _relation_tokens(right)
    return round(len(a & b) / len(a | b), 6) if a or b else 0.0


def _semantic_signature(left: Mapping[str, Any], right: Mapping[str, Any]) -> str:
    endpoints = sorted((canonical_json(_blind_projection(left)), canonical_json(_blind_projection(right))))
    return hashlib.sha256((endpoints[0] + "\n" + endpoints[1]).encode()).hexdigest()


def _row_id(row: Mapping[str, Any]) -> str:
    for key in ("benchmark_opportunity_id", "normalized_opportunity_id", "opportunity_id"):
        if row.get(key):
            return str(row[key])
    return hashlib.sha256(canonical_json(_blind_projection(row)).encode()).hexdigest()[:20]


def _v3_candidate(
    left: Mapping[str, Any],
    right: Mapping[str, Any],
    *,
    wave: int,
    stratum: str,
    provenance: Sequence[Mapping[str, str]],
) -> dict[str, Any]:
    a, b = _blind_projection(left), _blind_projection(right)
    signature = _semantic_signature(a, b)
    pair_id = "RG3-W%d-" % wave + hashlib.sha256(
        f"gold-v3|{wave}|{stratum}|{signature}".encode()
    ).hexdigest()[:16].upper()
    same = lambda key: bool(a.get(key)) and a.get(key) == b.get(key)
    a_tokens, b_tokens = _relation_tokens(a), _relation_tokens(b)
    return {
        "pair_id": pair_id,
        "unordered_semantic_signature": signature,
        "mining_stratum": stratum,
        "opportunity_a": a,
        "opportunity_b": b,
        "structural_features": {
            "same_discipline": same("discipline"),
            "same_study_unit": same("study_unit_id"),
            "same_topic": same("clinical_topic"),
            "same_family": same("opportunity_family"),
            "same_response_class": same("response_class"),
            "same_stage": same("clinical_stage"),
            "same_population_context": same("population_context"),
            "same_learner_decision": same("learner_decision") or same("principal_decision"),
            "same_key_action": same("key_concept_or_action"),
        },
        "similarity_signals": {
            "token_jaccard": _jaccard(a, b),
            "shared_content_tokens": len(a_tokens & b_tokens),
            "a_content_tokens": len(a_tokens),
            "b_content_tokens": len(b_tokens),
        },
        "source_provenance": [dict(item) for item in provenance],
    }


def _diverse_take(rows: Sequence[Mapping[str, Any]], limit: int, *, wave: int) -> list[dict[str, Any]]:
    buckets: dict[tuple[str, str], list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        endpoint = row["opportunity_a"]
        key = (str(endpoint.get("discipline") or "UNKNOWN"), str(endpoint.get("opportunity_family") or "UNKNOWN"))
        buckets[key].append(row)
    for values in buckets.values():
        values.sort(key=lambda row: hashlib.sha256(f"gold-v3-wave-{wave}|{row['pair_id']}".encode()).hexdigest())
    selected: list[dict[str, Any]] = []
    keys = sorted(buckets, key=lambda key: hashlib.sha256(f"gold-v3-bucket|{wave}|{key}".encode()).hexdigest())
    while len(selected) < limit and keys:
        next_keys = []
        for key in keys:
            if len(selected) >= limit:
                break
            if buckets[key]:
                selected.append(dict(buckets[key].pop(0)))
            if buckets[key]:
                next_keys.append(key)
        keys = next_keys
    return selected


def mine_relation_gold_v3_candidates(
    root: Path, *, wave: int, prior_pair_ids: Iterable[str] = (),
) -> dict[str, Any]:
    """Mine real relation candidates using private structural strata only."""
    if wave not in {1, 2, 3}:
        raise ValueError("RELATION_GOLD_V3_WAVE_MUST_BE_1_TO_3")
    root = Path(root)
    benchmark_artifact = _read(root, "research/qgen/opportunity_registry_v2/independent_opportunity_benchmark_v1.json")
    normalized_artifact = _read(root, "research/qgen/opportunity_registry_v3/normalized_atomic_opportunity_benchmark_v2.json")
    v1_artifact = _read(root, "research/qgen/opportunity_registry/curriculum_question_opportunity_registry_v1.json")
    v2_artifact = _read(root, "research/qgen/opportunity_registry_v2/curriculum_question_opportunity_registry_v2.json")
    old_packet = _read(root, "research/qgen/opportunity_relation_v4/relation_gold_v2_review_input.json")

    benchmarks = list(benchmark_artifact["opportunities"]) + list(normalized_artifact["opportunities"])
    v1_rows = list(v1_artifact["opportunities"])
    v2_rows = list(v2_artifact["opportunities"])
    v1_by_id = {row["opportunity_id"]: row for row in v1_rows}
    benchmarks_by_unit: dict[str, list[dict[str, Any]]] = defaultdict(list)
    v2_by_unit: dict[str, list[dict[str, Any]]] = defaultdict(list)
    v2_by_discipline_family: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in benchmarks:
        benchmarks_by_unit[str(row.get("study_unit_id"))].append(row)
    for row in v2_rows:
        v2_by_unit[str(row.get("study_unit_id"))].append(row)
        v2_by_discipline_family[(str(row.get("discipline")), str(row.get("opportunity_family")))].append(row)

    provenance = {
        "benchmark": {"artifact": "independent_opportunity_benchmark_v1", "sha256": benchmark_artifact["content_sha256"]},
        "normalized": {"artifact": "normalized_atomic_opportunity_benchmark_v2", "sha256": normalized_artifact["content_sha256"]},
        "v1": {"artifact": "curriculum_question_opportunity_registry_v1", "sha256": v1_artifact["content_sha256"]},
        "v2": {"artifact": "curriculum_question_opportunity_registry_v2", "sha256": v2_artifact["content_sha256"]},
    }
    pools: dict[str, list[dict[str, Any]]] = defaultdict(list)

    # Cross-artifact preserved lineage: exact records are real duplicate candidates;
    # non-identical descendants are equivalence/near-duplicate candidates.
    for current in v2_rows:
        for source_id in current.get("source_v1_opportunity_ids", []):
            source = v1_by_id.get(source_id)
            if not source:
                continue
            same_projection = _blind_projection(source) == _blind_projection(current)
            similarity = _jaccard(source, current)
            if same_projection:
                stratum = "POSSIBLE_DUPLICATE"
            elif similarity >= 0.72:
                stratum = "POSSIBLE_NEAR_DUPLICATE"
            else:
                stratum = "POSSIBLE_EQUIVALENCE"
            pools[stratum].append(_v3_candidate(
                source, current, wave=wave, stratum=stratum,
                provenance=[{**provenance["v1"], "row_id": source_id}, {**provenance["v2"], "row_id": _row_id(current)}],
            ))

    # Benchmark-to-registry comparisons preserve direction: A benchmark/reference, B registry.
    for study_unit_id, benchmark_rows in benchmarks_by_unit.items():
        for benchmark in benchmark_rows:
            for registry in v2_by_unit.get(study_unit_id, []):
                same_response = benchmark.get("response_class") == registry.get("response_class")
                same_family = benchmark.get("opportunity_family") == registry.get("opportunity_family")
                similarity = _jaccard(benchmark, registry)
                if same_response and same_family and similarity >= 0.55:
                    stratum = "POSSIBLE_EQUIVALENCE"
                elif same_response and (same_family or similarity >= 0.18):
                    stratum = "POSSIBLE_BROADER_NARROWER"
                elif same_family and benchmark.get("clinical_stage") == registry.get("clinical_stage"):
                    stratum = "POSSIBLE_VARIANT"
                else:
                    stratum = "POSSIBLE_RELATED_BUT_DISTINCT"
                benchmark_source = "normalized" if benchmark.get("normalized_opportunity_id") else "benchmark"
                pools[stratum].append(_v3_candidate(
                    benchmark, registry, wave=wave, stratum=stratum,
                    provenance=[
                        {**provenance[benchmark_source], "row_id": _row_id(benchmark)},
                        {**provenance["v2"], "row_id": _row_id(registry)},
                    ],
                ))

    # Same-context pairs surface genuine variant and near-duplicate shapes without labels.
    for study_unit_id, rows in v2_by_unit.items():
        ordered = sorted(rows, key=_row_id)
        for index, left in enumerate(ordered):
            for right in ordered[index + 1:]:
                same_family = left.get("opportunity_family") == right.get("opportunity_family")
                same_response = left.get("response_class") == right.get("response_class")
                same_stage = left.get("clinical_stage") == right.get("clinical_stage")
                similarity = _jaccard(left, right)
                if same_family and same_response and same_stage and similarity >= 0.72:
                    stratum = "POSSIBLE_NEAR_DUPLICATE"
                elif same_family and same_response and same_stage:
                    stratum = "POSSIBLE_VARIANT"
                else:
                    stratum = "POSSIBLE_RELATED_BUT_DISTINCT"
                pools[stratum].append(_v3_candidate(
                    left, right, wave=wave, stratum=stratum,
                    provenance=[
                        {**provenance["v2"], "row_id": _row_id(left)},
                        {**provenance["v2"], "row_id": _row_id(right)},
                    ],
                ))

    # Hard negatives stay inside discipline and family but cross topic/unit.
    for (discipline, family), rows in v2_by_discipline_family.items():
        ordered = sorted(rows, key=_row_id)
        if len(ordered) < 2:
            continue
        for index, left in enumerate(ordered):
            candidates = [
                right for right in ordered[index + 1:]
                if left.get("study_unit_id") != right.get("study_unit_id")
                and left.get("clinical_topic") != right.get("clinical_topic")
                and _jaccard(left, right) <= 0.12
            ]
            if not candidates:
                continue
            right = min(candidates, key=lambda row: hashlib.sha256(
                f"hard-unrelated|{wave}|{_row_id(left)}|{_row_id(row)}".encode()
            ).hexdigest())
            pools["HARD_UNRELATED"].append(_v3_candidate(
                left, right, wave=wave, stratum="HARD_UNRELATED",
                provenance=[
                    {**provenance["v2"], "row_id": _row_id(left)},
                    {**provenance["v2"], "row_id": _row_id(right)},
                ],
            ))

    old_signatures = {
        _semantic_signature(row["opportunity_a"], row["opportunity_b"])
        for row in old_packet["pairs"]
    }
    prior_ids = set(prior_pair_ids)
    quotas = {
        "POSSIBLE_EQUIVALENCE": 42,
        "POSSIBLE_BROADER_NARROWER": 72,
        "POSSIBLE_VARIANT": 48,
        "POSSIBLE_RELATED_BUT_DISTINCT": 54,
        "POSSIBLE_NEAR_DUPLICATE": 30,
        "POSSIBLE_DUPLICATE": 24,
        "HARD_UNRELATED": 30,
    }
    selected: list[dict[str, Any]] = []
    seen = set(old_signatures)
    for stratum, quota in quotas.items():
        unique = []
        for row in pools[stratum]:
            if row["pair_id"] in prior_ids or row["unordered_semantic_signature"] in seen:
                continue
            seen.add(row["unordered_semantic_signature"])
            unique.append(row)
        selected.extend(_diverse_take(unique, quota, wave=wave))
    if len(selected) < 240:
        raise ValueError(f"INSUFFICIENT_REAL_RELATION_CANDIDATES:{len(selected)}")
    selected = sorted(selected[:300], key=lambda row: row["pair_id"])
    discipline_counts = Counter(row["opportunity_a"].get("discipline") for row in selected)
    family_counts = Counter(row["opportunity_a"].get("opportunity_family") or "UNKNOWN" for row in selected)
    stratum_counts = Counter(row["mining_stratum"] for row in selected)
    return with_hash({
        "schema_version": "3.0",
        "scope": f"RELATION_GOLD_V3_WAVE_{wave}_PRIVATE_CANDIDATE_POOL",
        "wave": wave,
        "atomic_contract_sha256": CONTRACT_SHA256,
        "candidate_selection_policy": "REAL_CANONICAL_ROWS_STRUCTURAL_STRATA_NO_SEMANTIC_LABEL_ASSIGNMENT",
        "discipline_counts": dict(sorted(discipline_counts.items())),
        "family_counts": dict(sorted(family_counts.items())),
        "mining_stratum_counts": dict(sorted(stratum_counts.items())),
        "pairs": selected,
    })


def build_relation_gold_v3_review_packet(pool: Mapping[str, Any], root: Path) -> dict[str, Any]:
    contract = _read(root, "research/qgen/opportunity_registry_v3/atomic_opportunity_contract_v1.json")
    if contract.get("content_sha256") != CONTRACT_SHA256:
        raise ValueError("ATOMIC_OPPORTUNITY_CONTRACT_HASH_DRIFT")
    wave = int(pool["wave"])
    pairs = [{
        "pair_id": row["pair_id"],
        "opportunity_a_role": "BENCHMARK_OR_REFERENCE",
        "opportunity_b_role": "REGISTRY_CANDIDATE",
        "opportunity_a": row["opportunity_a"],
        "opportunity_b": row["opportunity_b"],
        "curriculum_context": {
            "discipline": row["opportunity_a"].get("discipline") or row["opportunity_b"].get("discipline"),
            "study_unit_id_a": row["opportunity_a"].get("study_unit_id"),
            "study_unit_id_b": row["opportunity_b"].get("study_unit_id"),
            "family_a": row["opportunity_a"].get("opportunity_family"),
            "family_b": row["opportunity_b"].get("opportunity_family"),
        },
    } for row in pool["pairs"]]
    return with_hash({
        "schema_version": "3.0",
        "scope": f"RELATION_GOLD_V3_WAVE_{wave}_BLINDED_REVIEW_INPUT",
        "wave": wave,
        "source_candidate_pool_sha256": pool["content_sha256"],
        "atomic_opportunity_contract": contract,
        "allowed_relations": list(RELATIONS),
        "direction_contract": "A_IS_BENCHMARK_OR_REFERENCE_SIDE_AND_B_IS_REGISTRY_CANDIDATE_SIDE",
        "reviewer_blindness": "PRIVATE_MINING_SIGNALS_PROVENANCE_PRIOR_OUTCOMES_AND_MATCHER_OUTPUTS_WITHHELD",
        "pairs": pairs,
    })


def validate_relation_gold_v3_review(
    review: Mapping[str, Any], packet: Mapping[str, Any],
) -> dict[str, dict[str, Any]]:
    if review.get("source_input_sha256") != packet.get("content_sha256"):
        raise ValueError("REVIEW_INPUT_HASH_MISMATCH")
    if not review.get("reviewer_id"):
        raise ValueError("MISSING_RELATION_REVIEWER_ID")
    rows = review.get("reviews", [])
    result = {row.get("pair_id"): row for row in rows}
    expected = {row["pair_id"] for row in packet["pairs"]}
    if None in result or len(result) != len(rows) or set(result) != expected:
        raise ValueError("REVIEW_MUST_COVER_EVERY_PAIR_EXACTLY_ONCE")
    for row in rows:
        justification = row.get("justification")
        if row.get("relation") not in RELATIONS or not isinstance(justification, str) or not justification.strip():
            raise ValueError("INVALID_RELATION_REVIEW")
        if len(justification) > 800:
            raise ValueError("RELATION_REVIEW_JUSTIFICATION_NOT_CONCISE")
    return result


def analyze_relation_reviewer_agreement(
    packet: Mapping[str, Any], primary: Mapping[str, Any], secondary: Mapping[str, Any],
) -> dict[str, Any]:
    if primary.get("reviewer_id") == secondary.get("reviewer_id"):
        raise ValueError("NONINDEPENDENT_RELATION_REVIEWERS")
    first = validate_relation_gold_v3_review(primary, packet)
    second = validate_relation_gold_v3_review(secondary, packet)
    confusion: dict[str, Counter[str]] = defaultdict(Counter)
    exact = 0
    per_class: dict[str, dict[str, Any]] = {}
    for pair_id in sorted(first):
        a, b = first[pair_id]["relation"], second[pair_id]["relation"]
        confusion[a][b] += 1
        exact += a == b
    for relation in RELATIONS:
        primary_count = sum(row["relation"] == relation for row in first.values())
        secondary_count = sum(row["relation"] == relation for row in second.values())
        agreement_count = sum(
            first[pair_id]["relation"] == relation == second[pair_id]["relation"]
            for pair_id in first
        )
        union_count = sum(
            first[pair_id]["relation"] == relation or second[pair_id]["relation"] == relation
            for pair_id in first
        )
        per_class[relation] = {
            "primary_count": primary_count,
            "secondary_count": secondary_count,
            "agreement_count": agreement_count,
            "union_count": union_count,
            "agreement_rate": _safe_ratio(agreement_count, union_count),
        }
    return with_hash({
        "schema_version": "3.0",
        "scope": f"RELATION_GOLD_V3_WAVE_{packet.get('wave')}_INTER_REVIEWER_AGREEMENT",
        "source_input_sha256": packet["content_sha256"],
        "primary_reviewer_id": primary["reviewer_id"],
        "secondary_reviewer_id": secondary["reviewer_id"],
        "reviewed_pairs": len(first),
        "exact_agreement": exact,
        "disagreements": len(first) - exact,
        "inter_reviewer_agreement": _safe_ratio(exact, len(first)),
        "primary_uncertain_rate": _safe_ratio(
            sum(row["relation"] == "UNCERTAIN" for row in first.values()), len(first)
        ),
        "secondary_uncertain_rate": _safe_ratio(
            sum(row["relation"] == "UNCERTAIN" for row in second.values()), len(second)
        ),
        "per_class_agreement": per_class,
        "confusion_matrix": {
            relation: dict(sorted(confusion[relation].items()))
            for relation in RELATIONS if confusion[relation]
        },
    })


def build_relation_gold_v3_disagreement_packet(
    packet: Mapping[str, Any], primary: Mapping[str, Any], secondary: Mapping[str, Any],
) -> dict[str, Any]:
    if primary.get("reviewer_id") == secondary.get("reviewer_id"):
        raise ValueError("NONINDEPENDENT_RELATION_REVIEWERS")
    first = validate_relation_gold_v3_review(primary, packet)
    second = validate_relation_gold_v3_review(secondary, packet)
    source = {row["pair_id"]: row for row in packet["pairs"]}
    disagreements = []
    for pair_id in sorted(first):
        if first[pair_id]["relation"] == second[pair_id]["relation"]:
            continue
        disagreements.append({
            **source[pair_id],
            "primary_verdict": {
                "relation": first[pair_id]["relation"],
                "justification": first[pair_id]["justification"],
            },
            "secondary_verdict": {
                "relation": second[pair_id]["relation"],
                "justification": second[pair_id]["justification"],
            },
        })
    return with_hash({
        "schema_version": "3.0",
        "scope": f"RELATION_GOLD_V3_WAVE_{packet.get('wave')}_DISAGREEMENT_ADJUDICATION_INPUT",
        "source_input_sha256": packet["content_sha256"],
        "atomic_opportunity_contract": packet.get("atomic_opportunity_contract"),
        "allowed_relations": list(RELATIONS),
        "primary_reviewer_id": primary["reviewer_id"],
        "secondary_reviewer_id": secondary["reviewer_id"],
        "disagreement_count": len(disagreements),
        "pairs": disagreements,
    })


def assemble_relation_gold_v3_waves(
    waves: Sequence[tuple[Mapping[str, Any], Mapping[str, Any], Mapping[str, Any], Mapping[str, Any]]],
) -> dict[str, Any]:
    reviews: list[dict[str, Any]] = []
    wave_metrics = []
    seen_pair_ids: set[str] = set()
    total_agreement = total_disagreement = total_adjudication = 0
    for packet, primary, secondary, adjudication in waves:
        if primary.get("reviewer_id") == secondary.get("reviewer_id"):
            raise ValueError("NONINDEPENDENT_RELATION_REVIEWERS")
        if adjudication.get("reviewer_id") in {primary.get("reviewer_id"), secondary.get("reviewer_id")}:
            raise ValueError("NONINDEPENDENT_DISAGREEMENT_ADJUDICATOR")
        first = validate_relation_gold_v3_review(primary, packet)
        second = validate_relation_gold_v3_review(secondary, packet)
        disagreement_packet = build_relation_gold_v3_disagreement_packet(packet, primary, secondary)
        if adjudication.get("source_input_sha256") != disagreement_packet["content_sha256"]:
            raise ValueError("ADJUDICATION_INPUT_HASH_MISMATCH")
        adjudication_rows = adjudication.get("reviews", [])
        adjudicated = {row.get("pair_id"): row for row in adjudication_rows}
        expected_disagreements = {row["pair_id"] for row in disagreement_packet["pairs"]}
        if None in adjudicated or len(adjudicated) != len(adjudication_rows) or set(adjudicated) != expected_disagreements:
            raise ValueError("ADJUDICATION_MUST_CONTAIN_ONLY_ALL_DISAGREEMENTS")
        for row in adjudication_rows:
            if row.get("relation") not in RELATIONS or not str(row.get("justification") or "").strip():
                raise ValueError("INVALID_DISAGREEMENT_ADJUDICATION")
        source = {row["pair_id"]: row for row in packet["pairs"]}
        metrics = analyze_relation_reviewer_agreement(packet, primary, secondary)
        wave_metrics.append(metrics)
        total_agreement += metrics["exact_agreement"]
        total_disagreement += metrics["disagreements"]
        total_adjudication += len(adjudicated)
        for pair_id in sorted(first):
            if pair_id in seen_pair_ids:
                raise ValueError("RELATION_GOLD_V3_PAIR_REUSED_ACROSS_WAVES")
            seen_pair_ids.add(pair_id)
            agreed = first[pair_id]["relation"] == second[pair_id]["relation"]
            terminal = first[pair_id] if agreed else adjudicated[pair_id]
            context = source[pair_id].get("curriculum_context", {})
            reviews.append({
                "pair_id": pair_id,
                "wave": packet.get("wave"),
                "relation": terminal["relation"],
                "justification": terminal["justification"],
                "primary_relation": first[pair_id]["relation"],
                "secondary_relation": second[pair_id]["relation"],
                "adjudicated": not agreed,
                "discipline": context.get("discipline"),
                "study_unit_id_a": context.get("study_unit_id_a"),
                "study_unit_id_b": context.get("study_unit_id_b"),
                "family_a": context.get("family_a"),
                "family_b": context.get("family_b"),
            })
    counts = Counter(row["relation"] for row in reviews)
    reviews.sort(key=lambda row: row["pair_id"])
    return with_hash({
        "schema_version": "3.0",
        "scope": "RELATION_GOLD_DATASET_V3",
        "waves": len(waves),
        "reviewed_pairs": len(reviews),
        "agreement_count": total_agreement,
        "disagreement_count": total_disagreement,
        "adjudication_count": total_adjudication,
        "inter_reviewer_agreement": _safe_ratio(total_agreement, len(reviews)),
        "uncertain_count": counts["UNCERTAIN"],
        "relation_counts": {label: counts[label] for label in RELATIONS},
        "wave_agreement_metrics": wave_metrics,
        "reviews": reviews,
    })


GOLD_V3_CRITICAL_SUPPORT_FLOORS = {
    "EQUIVALENT": 12,
    "REGISTRY_BROADER_CONTAINS_BENCHMARK": 12,
    "REGISTRY_NARROWER_THAN_BENCHMARK": 8,
    "VARIANT_OF_SAME_DECISION": 12,
    "RELATED_BUT_DISTINCT": 20,
    "UNRELATED": 12,
}

GOLD_V3_HELDOUT_SUPPORT_FLOORS = {
    "EQUIVALENT": 4,
    "REGISTRY_BROADER_CONTAINS_BENCHMARK": 4,
    "REGISTRY_NARROWER_THAN_BENCHMARK": 3,
    "VARIANT_OF_SAME_DECISION": 4,
    "RELATED_BUT_DISTINCT": 6,
    "UNRELATED": 4,
}


def evaluate_relation_class_support(gold: Mapping[str, Any]) -> dict[str, Any]:
    counts = gold.get("relation_counts", {})
    deficits = {
        relation: floor - int(counts.get(relation, 0))
        for relation, floor in GOLD_V3_CRITICAL_SUPPORT_FLOORS.items()
        if int(counts.get(relation, 0)) < floor
    }
    return with_hash({
        "schema_version": "3.0",
        "scope": "RELATION_GOLD_V3_REAL_CLASS_SUPPORT_GATE",
        "gate": "PASS" if not deficits else "FAIL",
        "critical_class_floors": dict(GOLD_V3_CRITICAL_SUPPORT_FLOORS),
        "observed_relation_counts": {label: int(counts.get(label, 0)) for label in RELATIONS},
        "critical_class_deficits": dict(sorted(deficits.items())),
        "synthetic_examples_counted": 0,
    })


def finalize_relation_gold_v3(assembled: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    uncertain_rows = [dict(row) for row in assembled.get("reviews", []) if row.get("relation") == "UNCERTAIN"]
    terminal_rows = [dict(row) for row in assembled.get("reviews", []) if row.get("relation") != "UNCERTAIN"]
    uncertain = with_hash({
        "schema_version": "3.0",
        "scope": "RELATION_GOLD_V3_UNCERTAIN",
        "source_assembled_gold_sha256": assembled.get("content_sha256"),
        "uncertain_count": len(uncertain_rows),
        "policy": "FAIL_CLOSED_EXCLUDED_FROM_TERMINAL_GOLD_AND_MATCHER_PARTITIONS",
        "reviews": uncertain_rows,
    })
    counts = Counter(row["relation"] for row in terminal_rows)
    terminal = with_hash({
        "schema_version": "3.0",
        "scope": "RELATION_GOLD_V3",
        "source_assembled_gold_sha256": assembled.get("content_sha256"),
        "uncertain_artifact_sha256": uncertain["content_sha256"],
        "waves": assembled.get("waves"),
        "candidate_pairs_reviewed": assembled.get("reviewed_pairs"),
        "reviewed_pairs": len(terminal_rows),
        "agreement_count": assembled.get("agreement_count"),
        "disagreement_count": assembled.get("disagreement_count"),
        "adjudication_count": assembled.get("adjudication_count"),
        "inter_reviewer_agreement": assembled.get("inter_reviewer_agreement"),
        "relation_counts": {label: counts[label] for label in RELATIONS},
        "wave_agreement_metrics": assembled.get("wave_agreement_metrics", []),
        "reviews": terminal_rows,
    })
    return terminal, uncertain


def _gold_v3_group_key(row: Mapping[str, Any]) -> str:
    unit_a = str(row.get("study_unit_id_a") or "")
    unit_b = str(row.get("study_unit_id_b") or "")
    if unit_a and unit_a == unit_b:
        return f"SAME_STUDY_UNIT:{unit_a}"
    return f"CROSS_UNIT_PAIR:{row['pair_id']}"


def freeze_relation_gold_v3_partitions(gold: Mapping[str, Any]) -> dict[str, Any]:
    rows = [row for row in gold.get("reviews", []) if row.get("relation") != "UNCERTAIN"]
    if len({row["pair_id"] for row in rows}) != len(rows):
        raise ValueError("RELATION_GOLD_V3_DUPLICATE_PAIR_ID")
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[_gold_v3_group_key(row)].append(dict(row))
    total_by_relation = Counter(row["relation"] for row in rows)
    partitions = ("CALIBRATION", "VALIDATION", "FINAL_HELDOUT")
    weights = {"CALIBRATION": 0.50, "VALIDATION": 0.25, "FINAL_HELDOUT": 0.25}
    targets = {
        partition: {relation: total_by_relation[relation] * weights[partition] for relation in RELATIONS[:-1]}
        for partition in partitions
    }
    current = {partition: Counter() for partition in partitions}
    current_sizes = Counter()
    total_rows = len(rows)
    assigned: list[dict[str, Any]] = []
    remaining_groups = dict(groups)

    def assign_group(group_key: str, group_rows: Sequence[Mapping[str, Any]], partition: str) -> None:
        group_counts = Counter(row["relation"] for row in group_rows)
        current[partition].update(group_counts)
        current_sizes[partition] += len(group_rows)
        assigned.extend({**dict(row), "partition": partition, "leakage_group": group_key} for row in group_rows)

    # Heldout evidence floors override the nominal 25% split. Seed whole
    # leakage groups before general balancing so a minimum-support class is
    # never left one example short merely because 25% rounds down.
    for relation, floor in GOLD_V3_HELDOUT_SUPPORT_FLOORS.items():
        while current["FINAL_HELDOUT"][relation] < floor:
            options = [
                (key, group_rows) for key, group_rows in remaining_groups.items()
                if any(row["relation"] == relation for row in group_rows)
            ]
            if not options:
                break

            def heldout_seed_score(item: tuple[str, list[dict[str, Any]]]) -> tuple[int, int, str]:
                key, group_rows = item
                group_counts = Counter(row["relation"] for row in group_rows)
                useful = sum(
                    min(
                        max(0, required - current["FINAL_HELDOUT"][candidate_relation]),
                        group_counts[candidate_relation],
                    )
                    for candidate_relation, required in GOLD_V3_HELDOUT_SUPPORT_FLOORS.items()
                )
                return (-useful, len(group_rows), hashlib.sha256(f"heldout-seed|{key}".encode()).hexdigest())

            group_key, group_rows = min(options, key=heldout_seed_score)
            assign_group(group_key, group_rows, "FINAL_HELDOUT")
            del remaining_groups[group_key]

    ordered_groups = sorted(
        remaining_groups.items(),
        key=lambda item: (
            min(total_by_relation[row["relation"]] for row in item[1]),
            -len(item[1]),
            hashlib.sha256(f"gold-v3-partition|{item[0]}".encode()).hexdigest(),
        ),
    )
    for group_key, group_rows in ordered_groups:
        group_counts = Counter(row["relation"] for row in group_rows)

        def assignment_cost(partition: str) -> tuple[float, int]:
            cost = 0.0
            for candidate_partition in partitions:
                for relation in RELATIONS[:-1]:
                    target = targets[candidate_partition][relation]
                    after = current[candidate_partition][relation]
                    if candidate_partition == partition:
                        after += group_counts[relation]
                    cost += ((after - target) / max(1.0, total_by_relation[relation])) ** 2
                size_target = total_rows * weights[candidate_partition]
                size_after = current_sizes[candidate_partition]
                if candidate_partition == partition:
                    size_after += len(group_rows)
                cost += ((size_after - size_target) / max(1.0, total_rows)) ** 2
            tie = int(hashlib.sha256(f"{group_key}|{partition}".encode()).hexdigest()[:8], 16)
            return round(cost, 12), tie

        partition = min(partitions, key=assignment_cost)
        assign_group(group_key, group_rows, partition)
    assigned.sort(key=lambda row: row["pair_id"])
    partition_counts = Counter(row["partition"] for row in assigned)
    relation_counts = {
        partition: {label: current[partition][label] for label in RELATIONS[:-1]}
        for partition in partitions
    }
    heldout_deficits = {
        relation: floor - relation_counts["FINAL_HELDOUT"][relation]
        for relation, floor in GOLD_V3_HELDOUT_SUPPORT_FLOORS.items()
        if relation_counts["FINAL_HELDOUT"][relation] < floor
    }
    return with_hash({
        "schema_version": "3.0",
        "scope": "RELATION_GOLD_V3_FROZEN_PARTITIONS",
        "source_gold_sha256": gold.get("content_sha256"),
        "frozen_before_matcher_development": True,
        "split_unit": "SAME_STUDY_UNIT_GROUP_OTHERWISE_CROSS_UNIT_PAIR",
        "stratification_dimensions": ["RELATION", "DISCIPLINE", "FAMILY_WHERE_POSSIBLE"],
        "partition_counts": {partition: partition_counts[partition] for partition in partitions},
        "partition_relation_counts": relation_counts,
        "heldout_support_floors": dict(GOLD_V3_HELDOUT_SUPPORT_FLOORS),
        "heldout_support_deficits": dict(sorted(heldout_deficits.items())),
        "heldout_support_gate": "PASS" if not heldout_deficits else "FAIL",
        "rows": assigned,
    })


def build_matcher_prediction_packet(
    partitions: Mapping[str, Any],
    review_packets: Sequence[Mapping[str, Any]],
    partition: str,
) -> dict[str, Any]:
    if partition not in {"CALIBRATION", "VALIDATION", "FINAL_HELDOUT"}:
        raise ValueError("UNKNOWN_MATCHER_PARTITION")
    source_by_id: dict[str, Mapping[str, Any]] = {}
    for packet in review_packets:
        for row in packet.get("pairs", []):
            if row["pair_id"] in source_by_id:
                raise ValueError("MATCHER_SOURCE_PAIR_REUSED_ACROSS_WAVES")
            source_by_id[row["pair_id"]] = row
    expected_ids = sorted(
        row["pair_id"] for row in partitions.get("rows", []) if row.get("partition") == partition
    )
    if any(pair_id not in source_by_id for pair_id in expected_ids):
        raise ValueError("MATCHER_PARTITION_PAIR_MISSING_SOURCE_ENDPOINTS")
    pairs = []
    for pair_id in expected_ids:
        source = source_by_id[pair_id]
        pairs.append({
            key: source[key] for key in (
                "pair_id", "opportunity_a_role", "opportunity_b_role",
                "opportunity_a", "opportunity_b", "curriculum_context",
            )
        })
    contract = review_packets[0].get("atomic_opportunity_contract") if review_packets else None
    return with_hash({
        "schema_version": "4.0",
        "scope": f"MATCHER_V4_{partition}_PREDICTION_INPUT",
        "source_partition_sha256": partitions.get("content_sha256"),
        "atomic_opportunity_contract": contract,
        "direction_contract": "A_IS_BENCHMARK_OR_REFERENCE_SIDE_AND_B_IS_REGISTRY_CANDIDATE_SIDE",
        "allowed_relations": list(RELATIONS[:-1]),
        "gold_labels_withheld": True,
        "pairs": pairs,
    })


def validate_matcher_predictions(
    predictions: Mapping[str, Any], packet: Mapping[str, Any],
) -> dict[str, dict[str, Any]]:
    if predictions.get("source_input_sha256") != packet.get("content_sha256"):
        raise ValueError("MATCHER_PREDICTION_INPUT_HASH_MISMATCH")
    if not predictions.get("matcher_id"):
        raise ValueError("MISSING_MATCHER_ID")
    rows = predictions.get("predictions", [])
    result = {row.get("pair_id"): row for row in rows}
    expected = {row["pair_id"] for row in packet.get("pairs", [])}
    if None in result or len(result) != len(rows) or set(result) != expected:
        raise ValueError("MATCHER_PREDICTIONS_MUST_COVER_EVERY_PAIR_EXACTLY_ONCE")
    allowed = set(packet.get("allowed_relations") or RELATIONS[:-1])
    for row in rows:
        if row.get("relation") not in allowed or not str(row.get("justification") or "").strip():
            raise ValueError("INVALID_MATCHER_PREDICTION")
    return result


def deterministic_relation_predictions(
    packet: Mapping[str, Any], *, matcher_id: str,
) -> dict[str, Any]:
    predictions = []
    for row in packet.get("pairs", []):
        a, b = row["opportunity_a"], row["opportunity_b"]
        a_tokens, b_tokens = _relation_tokens(a), _relation_tokens(b)
        same_unit = bool(a.get("study_unit_id")) and a.get("study_unit_id") == b.get("study_unit_id")
        same_topic = bool(a.get("clinical_topic")) and a.get("clinical_topic") == b.get("clinical_topic")
        same_family = bool(a.get("opportunity_family")) and a.get("opportunity_family") == b.get("opportunity_family")
        same_response = bool(a.get("response_class")) and a.get("response_class") == b.get("response_class")
        same_decision = bool(a.get("learner_decision")) and a.get("learner_decision") == b.get("learner_decision")
        if a == b:
            relation, reason = "DUPLICATE", "The projected records are structurally identical."
        elif same_family and same_response and same_decision:
            material_context_keys = ("clinical_stage", "population_context", "severity_context")
            if any(a.get(key) != b.get(key) for key in material_context_keys):
                relation, reason = "VARIANT_OF_SAME_DECISION", "The learner decision is unchanged and only contextual metadata differs."
            else:
                relation, reason = "EQUIVALENT", "The learner decision, response class, and material context are the same."
        elif same_family and same_response and a_tokens and a_tokens < b_tokens:
            relation, reason = "REGISTRY_BROADER_CONTAINS_BENCHMARK", "The registry-side content structurally contains the benchmark-side content."
        elif same_family and same_response and b_tokens and b_tokens < a_tokens:
            relation, reason = "REGISTRY_NARROWER_THAN_BENCHMARK", "The registry-side content is a structural subset of the benchmark-side content."
        elif same_family and same_response and _jaccard(a, b) >= 0.80:
            relation, reason = "NEAR_DUPLICATE", "The endpoints have high structural overlap with a remaining metadata distinction."
        elif same_unit or same_topic:
            relation, reason = "RELATED_BUT_DISTINCT", "The endpoints share a curriculum context but require structurally different responses."
        elif a.get("discipline") == b.get("discipline") and same_family and _jaccard(a, b) <= 0.12:
            relation, reason = "UNRELATED", "The endpoints share only a broad discipline/family wrapper and no material decision content."
        else:
            relation, reason = "UNRELATED", "No direct structural opportunity relationship is present."
        predictions.append({"pair_id": row["pair_id"], "relation": relation, "justification": reason})
    result = with_hash({
        "schema_version": "4.0",
        "scope": f"{matcher_id}_PREDICTIONS",
        "matcher_id": matcher_id,
        "architecture": "DETERMINISTIC",
        "source_input_sha256": packet["content_sha256"],
        "predictions": predictions,
    })
    validate_matcher_predictions(result, packet)
    return result


def build_hybrid_relation_predictions(
    packet: Mapping[str, Any],
    deterministic: Mapping[str, Any],
    semantic: Mapping[str, Any],
    *,
    matcher_id: str,
) -> dict[str, Any]:
    structural = validate_matcher_predictions(deterministic, packet)
    meaning = validate_matcher_predictions(semantic, packet)
    predictions = []
    for pair_id in sorted(structural):
        if structural[pair_id]["relation"] == "DUPLICATE":
            chosen = structural[pair_id]
            source = "DETERMINISTIC_EXACT_RECORD_OVERRIDE"
        else:
            chosen = meaning[pair_id]
            source = "CONSTRAINED_SEMANTIC_CLASSIFIER"
        predictions.append({
            "pair_id": pair_id,
            "relation": chosen["relation"],
            "justification": chosen["justification"],
            "decision_source": source,
        })
    result = with_hash({
        "schema_version": "4.0",
        "scope": f"{matcher_id}_PREDICTIONS",
        "matcher_id": matcher_id,
        "architecture": "HYBRID",
        "source_input_sha256": packet["content_sha256"],
        "deterministic_override": "EXACT_PROJECTED_RECORD_DUPLICATE_ONLY",
        "semantic_default": True,
        "predictions": predictions,
    })
    validate_matcher_predictions(result, packet)
    return result


def score_matcher_predictions(
    partitions: Mapping[str, Any],
    partition: str,
    packet: Mapping[str, Any],
    predictions: Mapping[str, Any],
) -> dict[str, Any]:
    guesses = validate_matcher_predictions(predictions, packet)
    gold_rows = {
        row["pair_id"]: row["relation"]
        for row in partitions.get("rows", []) if row.get("partition") == partition
    }
    if set(gold_rows) != set(guesses):
        raise ValueError("MATCHER_SCORE_PARTITION_COVERAGE_MISMATCH")
    pair_ids = sorted(gold_rows)
    metrics = compute_multiclass_metrics(
        [gold_rows[pair_id] for pair_id in pair_ids],
        [guesses[pair_id]["relation"] for pair_id in pair_ids],
        labels=RELATIONS[:-1],
        minimum_support=2,
    )
    return with_hash({
        "schema_version": "4.0",
        "scope": f"MATCHER_V4_{partition}_METRICS",
        "partition": partition,
        "source_partition_sha256": partitions.get("content_sha256"),
        "source_prediction_sha256": predictions.get("content_sha256"),
        **metrics,
    })


def compare_matcher_approaches(
    partitions: Mapping[str, Any],
    calibration_packet: Mapping[str, Any],
    predictions_by_architecture: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    required = {"DETERMINISTIC", "SEMANTIC", "HYBRID"}
    if set(predictions_by_architecture) != required:
        raise ValueError("MATCHER_APPROACH_COMPARISON_REQUIRES_THREE_ARCHITECTURES")
    approaches = {}
    for architecture in sorted(required):
        metrics = score_matcher_predictions(
            partitions, "CALIBRATION", calibration_packet, predictions_by_architecture[architecture]
        )
        approaches[architecture] = {**metrics, "gate_evaluation": evaluate_matcher_gate(metrics)}
    critical = tuple(GOLD_V3_CRITICAL_SUPPORT_FLOORS)
    tie_priority = {"DETERMINISTIC": 0, "SEMANTIC": 1, "HYBRID": 2}

    def selection_key(architecture: str) -> tuple[int, float, float, int]:
        row = approaches[architecture]
        supported_critical_f1 = [
            row["per_class"][label]["f1"]
            for label in critical
            if row["per_class"][label]["support_status"] == "SUFFICIENT"
        ]
        return (
            int(row["gate_evaluation"]["gate"] == "PASS"),
            row["macro_f1"],
            min(supported_critical_f1) if supported_critical_f1 else 0.0,
            tie_priority[architecture],
        )

    selected = max(sorted(required), key=selection_key)
    return with_hash({
        "schema_version": "4.0",
        "scope": "MATCHER_V4_CALIBRATION_APPROACH_COMPARISON",
        "source_partition_sha256": partitions.get("content_sha256"),
        "source_calibration_input_sha256": calibration_packet.get("content_sha256"),
        "selection_policy": "PASS_GATE_THEN_MACRO_F1_THEN_MINIMUM_SUPPORTED_CRITICAL_F1_WITH_FROZEN_V4_HYBRID_TIE_PREFERENCE",
        "selected_architecture": selected,
        "selected_calibration_gate": approaches[selected]["gate_evaluation"]["gate"],
        "id_specific_rules": False,
        "approaches": approaches,
    })


def _safe_ratio(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 6) if denominator else 0.0


def compute_multiclass_metrics(
    actual: Sequence[str], predicted: Sequence[str], *, labels: Sequence[str] = RELATIONS,
    minimum_support: int = 2,
) -> dict[str, Any]:
    if len(actual) != len(predicted):
        raise ValueError("ACTUAL_PREDICTED_LENGTH_MISMATCH")
    allowed = set(labels)
    if (set(actual) | set(predicted)) - allowed:
        raise ValueError("UNKNOWN_RELATION_LABEL")
    confusion: dict[str, Counter[str]] = defaultdict(Counter)
    for truth, guess in zip(actual, predicted):
        confusion[truth][guess] += 1
    per_class: dict[str, dict[str, Any]] = {}
    for label in labels:
        tp = confusion[label][label]
        support = sum(confusion[label].values())
        predicted_count = sum(confusion[truth][label] for truth in labels)
        precision = _safe_ratio(tp, predicted_count)
        recall = _safe_ratio(tp, support)
        f1 = _safe_ratio(2 * precision * recall, precision + recall)
        per_class[label] = {
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "support": support,
            "support_status": "SUFFICIENT" if support >= minimum_support else "INSUFFICIENT_CLASS_SUPPORT",
        }
    return {
        "pairs": len(actual),
        "accuracy": _safe_ratio(sum(a == p for a, p in zip(actual, predicted)), len(actual)),
        "macro_precision": _safe_ratio(sum(row["precision"] for row in per_class.values()), len(labels)),
        "macro_recall": _safe_ratio(sum(row["recall"] for row in per_class.values()), len(labels)),
        "macro_f1": _safe_ratio(sum(row["f1"] for row in per_class.values()), len(labels)),
        "per_class": per_class,
        "confusion_matrix": {
            truth: dict(sorted(confusion[truth].items())) for truth in labels if confusion[truth]
        },
    }


def validate_append_only_graph(
    prior: Iterable[Mapping[str, Any]], current: Iterable[Mapping[str, Any]],
) -> list[str]:
    def edge(row: Mapping[str, Any]) -> str:
        return f"{row['opportunity_a_id']}|{row['opportunity_b_id']}|{row['relation']}"
    return sorted({edge(row) for row in prior} - {edge(row) for row in current})


def _validated_review_map(review: Mapping[str, Any], packet: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    if review.get("source_input_sha256") != packet.get("content_sha256"):
        raise ValueError("REVIEW_INPUT_HASH_MISMATCH")
    rows = review.get("reviews", [])
    result = {row.get("pair_id"): row for row in rows}
    expected = {row["pair_id"] for row in packet["pairs"]}
    if None in result or len(result) != len(rows) or set(result) != expected:
        raise ValueError("REVIEW_MUST_COVER_EVERY_PAIR_EXACTLY_ONCE")
    for row in rows:
        if row.get("relation") not in RELATIONS or not row.get("justification"):
            raise ValueError("INVALID_RELATION_REVIEW")
    return result


def assemble_relation_gold_v2(
    packet: Mapping[str, Any], primary: Mapping[str, Any], secondary: Mapping[str, Any],
    adjudication: Mapping[str, Any] | None,
) -> dict[str, Any]:
    if not primary.get("reviewer_id") or primary.get("reviewer_id") == secondary.get("reviewer_id"):
        raise ValueError("NONINDEPENDENT_RELATION_REVIEWERS")
    first = _validated_review_map(primary, packet)
    second = _validated_review_map(secondary, packet)
    disagreements = {pair_id for pair_id in first if first[pair_id]["relation"] != second[pair_id]["relation"]}
    adjudicated: dict[str, dict[str, Any]] = {}
    if adjudication is not None:
        if adjudication.get("reviewer_id") in {primary.get("reviewer_id"), secondary.get("reviewer_id")}:
            raise ValueError("NONINDEPENDENT_DISAGREEMENT_ADJUDICATOR")
        if adjudication.get("source_input_sha256") != packet.get("content_sha256"):
            raise ValueError("ADJUDICATION_INPUT_HASH_MISMATCH")
        rows = adjudication.get("reviews", [])
        adjudicated = {row.get("pair_id"): row for row in rows}
        if None in adjudicated or len(adjudicated) != len(rows) or set(adjudicated) != disagreements:
            raise ValueError("ADJUDICATION_MUST_CONTAIN_ONLY_ALL_DISAGREEMENTS")
        for row in rows:
            if row.get("relation") not in RELATIONS or not row.get("justification"):
                raise ValueError("INVALID_DISAGREEMENT_ADJUDICATION")
    packet_by_id = {row["pair_id"]: row for row in packet["pairs"]}
    reviews = []
    for pair_id in sorted(first):
        context = packet_by_id[pair_id]["curriculum_context"]
        agreed = pair_id not in disagreements
        final = first[pair_id] if agreed else adjudicated.get(pair_id)
        reviews.append({
            "pair_id": pair_id,
            "relation": final["relation"] if final else "UNCERTAIN",
            "justification": final["justification"] if final else "Independent reviewers disagreed and no fresh adjudication was available.",
            "primary_relation": first[pair_id]["relation"],
            "secondary_relation": second[pair_id]["relation"],
            "adjudicated": bool(final and not agreed),
            "discipline": context.get("discipline"),
            "study_unit_id": context.get("study_unit_id"),
            "family": context.get("family_a") or context.get("family_b"),
        })
    counts = Counter(row["relation"] for row in reviews)
    agreement_count = len(reviews) - len(disagreements)
    return with_hash({
        "schema_version": "2.0", "scope": "RELATION_GOLD_DATASET_V2",
        "source_input_sha256": packet["content_sha256"],
        "primary_reviewer_id": primary["reviewer_id"], "secondary_reviewer_id": secondary["reviewer_id"],
        "adjudicator_id": adjudication.get("reviewer_id") if adjudication else None,
        "agreement_count": agreement_count, "disagreement_count": len(disagreements),
        "adjudication_count": len(adjudicated),
        "inter_reviewer_agreement": _safe_ratio(agreement_count, len(reviews)),
        "relation_counts": {label: counts[label] for label in RELATIONS},
        "reviews": reviews,
    })


def build_relation_disagreement_packet(
    packet: Mapping[str, Any],
    primary: Mapping[str, Any],
    secondary: Mapping[str, Any],
) -> dict[str, Any]:
    """Return blinded source rows only for pairs with conflicting review labels."""
    first = _validated_review_map(primary, packet)
    second = _validated_review_map(secondary, packet)
    disputed_ids = sorted(pair_id for pair_id in first if first[pair_id]["relation"] != second[pair_id]["relation"])
    source_by_id = {row["pair_id"]: row for row in packet["pairs"]}
    return with_hash({
        "schema_version": "2.0",
        "scope": "RELATION_GOLD_V2_BLINDED_DISAGREEMENT_ADJUDICATION_INPUT",
        "source_input_sha256": packet["content_sha256"],
        "disagreement_count": len(disputed_ids),
        "pairs": [source_by_id[pair_id] for pair_id in disputed_ids],
    })


def write_post_review_artifacts(root: Path, destination: Path) -> dict[str, str]:
    destination = Path(destination)
    packet = json.loads((destination / "relation_gold_v2_review_input.json").read_text())
    primary = json.loads((destination / "relation_gold_v2_primary_review.json").read_text())
    secondary = json.loads((destination / "relation_gold_v2_secondary_review.json").read_text())
    artifact = build_relation_disagreement_packet(packet, primary, secondary)
    path = destination / "relation_gold_v2_disagreement_input.json"
    path.write_text(canonical_json(artifact))
    return {path.name: artifact["content_sha256"]}


def write_final_gold_artifacts(destination: Path) -> dict[str, str]:
    destination = Path(destination)
    packet = json.loads((destination / "relation_gold_v2_review_input.json").read_text())
    primary = json.loads((destination / "relation_gold_v2_primary_review.json").read_text())
    secondary = json.loads((destination / "relation_gold_v2_secondary_review.json").read_text())
    adjudication = json.loads((destination / "relation_gold_v2_disagreement_adjudication.json").read_text())
    gold = assemble_relation_gold_v2(packet, primary, secondary, adjudication)
    partitions = freeze_relation_partitions(gold["reviews"])
    artifacts = {
        "relation_gold_v2.json": gold,
        "relation_gold_v2_frozen_partitions.json": partitions,
    }
    for name, artifact in artifacts.items():
        (destination / name).write_text(canonical_json(artifact))
    return {name: artifact["content_sha256"] for name, artifact in artifacts.items()}


def freeze_relation_partitions(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    groups: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[str(row.get("study_unit_id") or row["pair_id"])].append(row)
    partitions = ("CALIBRATION", "VALIDATION", "FINAL_HELDOUT")
    ordered_groups = sorted(
        groups.items(),
        key=lambda item: hashlib.sha256(
            f"relation-v4-split|{item[0]}|{','.join(sorted(str(r.get('relation')) for r in item[1]))}".encode()
        ).hexdigest(),
    )
    assigned: list[dict[str, Any]] = []
    for index, (_, group_rows) in enumerate(ordered_groups):
        partition = partitions[index % len(partitions)]
        assigned.extend({**dict(row), "partition": partition} for row in group_rows)
    assigned.sort(key=lambda row: row["pair_id"])
    counts = Counter(row["partition"] for row in assigned)
    relation_counts = {
        partition: dict(sorted(Counter(row["relation"] for row in assigned if row["partition"] == partition).items()))
        for partition in partitions
    }
    return with_hash({
        "schema_version": "2.0", "scope": "RELATION_GOLD_V2_FROZEN_PARTITIONS",
        "split_unit": "STUDY_UNIT_OR_PAIR_WHEN_UNIT_ABSENT",
        "stratification_dimensions": ["RELATION", "DISCIPLINE", "FAMILY_WHERE_POSSIBLE"],
        "frozen_before_matcher_development": True,
        "partition_counts": {partition: counts[partition] for partition in partitions},
        "partition_relation_counts": relation_counts, "rows": assigned,
    })


def evaluate_matcher_gate(metrics: Mapping[str, Any]) -> dict[str, Any]:
    critical = (
        "EQUIVALENT", "REGISTRY_BROADER_CONTAINS_BENCHMARK",
        "REGISTRY_NARROWER_THAN_BENCHMARK", "VARIANT_OF_SAME_DECISION",
        "RELATED_BUT_DISTINCT", "UNRELATED",
    )
    insufficient = [
        label for label in critical
        if metrics["per_class"][label]["support_status"] != "SUFFICIENT"
    ]
    weak = [
        label for label in critical
        if metrics["per_class"][label]["support_status"] == "SUFFICIENT"
        and metrics["per_class"][label]["f1"] < 0.70
    ]
    passed = metrics["macro_f1"] >= 0.80 and not insufficient and not weak
    return {
        "gate": "PASS" if passed else "FAIL", "macro_f1_floor": 0.80,
        "critical_class_f1_floor": 0.70, "insufficient_critical_class_support": insufficient,
        "critical_classes_below_floor": weak,
    }


def build_matcher_v4_contract(root: Path) -> dict[str, Any]:
    prompt = Path(root) / "docs/qgen/OPPORTUNITY_RELATION_CLASSIFIER_V4_PROMPT.md"
    return with_hash({
        "schema_version": "4.0", "scope": "OPPORTUNITY_RELATION_MATCHER_V4_CONTRACT",
        "architecture": "HYBRID", "frozen": True,
        "atomic_opportunity_contract_sha256": CONTRACT_SHA256,
        "deterministic_stage": "RECALL_ORIENTED_CANDIDATE_PREFILTER_ONLY",
        "semantic_stage": "CONSTRAINED_ATOMIC_CONTRACT_RELATION_CLASSIFICATION",
        "candidate_graph": "MANY_TO_MANY_APPEND_ONLY",
        "monotonicity": "PRIOR_VALID_RELATION_EDGE_SET_MUST_BE_SUBSET_AFTER_REGISTRY_APPEND",
        "classifier_prompt_sha256": hashlib.sha256(prompt.read_bytes()).hexdigest(),
        "id_specific_rules": False, "opportunity_invention_allowed": False,
        "final_heldout_tuning_allowed": False,
    })


def build_matcher_v4_calibrated_contract(root: Path) -> dict[str, Any]:
    root = Path(root)
    prompt = root / "docs/qgen/OPPORTUNITY_RELATION_CLASSIFIER_V4_CALIBRATED_PROMPT.md"
    error_analysis = root / "research/qgen/opportunity_relation_v4/matcher_v4_calibration_error_analysis.json"
    return with_hash({
        "schema_version": "4.1",
        "scope": "OPPORTUNITY_RELATION_MATCHER_V4_CALIBRATED_CONTRACT",
        "architecture": "HYBRID",
        "frozen": True,
        "parent_matcher_v4_sha256": "41f48e744e51e910f621c448a33cc8d2666ac6b0e9810b18accd70bceec24335",
        "atomic_opportunity_contract_sha256": CONTRACT_SHA256,
        "classifier_prompt_sha256": hashlib.sha256(prompt.read_bytes()).hexdigest(),
        "calibration_error_analysis_file_sha256": hashlib.sha256(error_analysis.read_bytes()).hexdigest(),
        "calibration_change": "PROMPT_PRECEDENCE_CLARIFICATION_ONLY",
        "semantic_contract_changed": False,
        "deterministic_stage": "EXACT_PROJECTED_RECORD_DUPLICATE_OVERRIDE",
        "semantic_stage": "CONSTRAINED_ATOMIC_CONTRACT_RELATION_CLASSIFICATION",
        "candidate_graph": "MANY_TO_MANY_APPEND_ONLY",
        "monotonicity": "PRIOR_VALID_RELATION_EDGE_SET_MUST_BE_SUBSET_AFTER_REGISTRY_APPEND",
        "id_specific_rules": False,
        "opportunity_invention_allowed": False,
        "final_heldout_tuning_allowed": False,
    })


def write_task1_artifacts(root: Path, destination: Path) -> dict[str, str]:
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    artifacts = {
        "matcher_v3_failed_generalization_baseline.json": build_failed_v3_baseline(root),
        "matcher_v4_contract.json": build_matcher_v4_contract(root),
        "relation_gold_v2_review_input.json": mine_relation_review_candidates(root),
    }
    for name, artifact in artifacts.items():
        (destination / name).write_text(canonical_json(artifact))
    return {name: artifact["content_sha256"] for name, artifact in artifacts.items()}


if __name__ == "__main__":
    repository_root = Path(__file__).resolve().parents[2]
    output_dir = repository_root / "research/qgen/opportunity_relation_v4"
    print(canonical_json(write_task1_artifacts(repository_root, output_dir)), end="")
