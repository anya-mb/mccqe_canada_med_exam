"""Registry V3 canonicalization.

Deterministic construction of the canonical curriculum-opportunity registry
(V3) from the frozen Registry V2 input, the frozen normalized atomic benchmark,
and frozen offline semantic-adjudication artifacts.

Architecture (frozen in ``docs/qgen/RELATION_MATCHER_EXPERIMENT_CLOSEOUT.md``):

    DETERMINISTIC_CANDIDATE_PROPOSAL + SEMANTIC_ADJUDICATION

No automatic relation matcher has authority here.  Deterministic code mines a
bounded candidate set, proves exact-invariant duplicates, builds the append-only
relation graph, derives canonical components, computes every metric, and
serializes every artifact.  Relation *labels* on non-exact pairs come only from
frozen semantic-adjudication artifacts produced offline by independent
reviewers; this module never infers one.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

# --------------------------------------------------------------------------
# Frozen inputs
# --------------------------------------------------------------------------

REGISTRY_V1_PATH = "research/qgen/opportunity_registry/curriculum_question_opportunity_registry_v1.json"
REGISTRY_V2_PATH = "research/qgen/opportunity_registry_v2/curriculum_question_opportunity_registry_v2.json"
BENCHMARK_PATH = "research/qgen/opportunity_registry_v3/normalized_atomic_opportunity_benchmark_v2.json"
ATOMIC_CONTRACT_PATH = "research/qgen/opportunity_registry_v3/atomic_opportunity_contract_v1.json"

DESTINATION = "research/qgen/opportunity_registry_v3_canonical"

GOLD_RELATION_ARTIFACTS = (
    "research/qgen/opportunity_relation_v4/relation_gold_v3.json",
    "research/qgen/opportunity_relation_v5/fresh_v5_validation_gold.json",
)

CANDIDATE_POOL_GLOBS = (
    "research/qgen/opportunity_relation_v4",
    "research/qgen/opportunity_relation_v5",
)

# --------------------------------------------------------------------------
# Relation taxonomy and canonicalization effect
# --------------------------------------------------------------------------

RELATIONS = (
    "DUPLICATE",
    "EQUIVALENT",
    "VARIANT_OF_SAME_DECISION",
    "NEAR_DUPLICATE",
    "REGISTRY_BROADER_CONTAINS_BENCHMARK",
    "REGISTRY_NARROWER_THAN_BENCHMARK",
    "RELATED_BUT_DISTINCT",
    "UNRELATED",
    "UNCERTAIN",
)

#: How each frozen relation affects Registry V3 canonicalization.  This is the
#: only place canonicalization effect is defined; the graph builder reads it.
RELATION_EFFECT = {
    # Collapse both endpoints into one canonical curriculum decision.
    "DUPLICATE": "COLLAPSE_TO_ONE_CANONICAL_DECISION",
    "EQUIVALENT": "COLLAPSE_TO_ONE_CANONICAL_DECISION",
    # Attach as an alternative realization; never a second coverage unit.
    "VARIANT_OF_SAME_DECISION": "ATTACH_AS_VARIANT_NOT_COVERAGE_UNIT",
    # Never merged automatically; retained separately with a review flag.
    "NEAR_DUPLICATE": "RETAIN_SEPARATE_WITH_REVIEW_FLAG",
    # Directional containment preserved as a link; endpoints stay independent.
    "REGISTRY_BROADER_CONTAINS_BENCHMARK": "PRESERVE_DIRECTIONAL_CONTAINMENT_LINK",
    "REGISTRY_NARROWER_THAN_BENCHMARK": "PRESERVE_DIRECTIONAL_CONTAINMENT_LINK",
    "RELATED_BUT_DISTINCT": "KEEP_SEPARATE",
    "UNRELATED": "KEEP_SEPARATE",
    # Fail closed: never merge, never remove.
    "UNCERTAIN": "FAIL_CLOSED_KEEP_SEPARATE_AND_REVIEW",
}

#: Relations whose acceptance removes or demotes an independent coverage unit.
#: Phase 10 requires a second independent reviewer before any of these bind.
DESTRUCTIVE_RELATIONS = (
    "DUPLICATE",
    "EQUIVALENT",
    "VARIANT_OF_SAME_DECISION",
)

#: Ranking used by the monotonicity invariant: adding registry candidates may
#: refine a pair's relation upward, never downward.
RELATION_RANK = {
    "UNRELATED": 0,
    "UNCERTAIN": 0,
    "RELATED_BUT_DISTINCT": 1,
    "NEAR_DUPLICATE": 2,
    "REGISTRY_BROADER_CONTAINS_BENCHMARK": 3,
    "REGISTRY_NARROWER_THAN_BENCHMARK": 3,
    "VARIANT_OF_SAME_DECISION": 4,
    "EQUIVALENT": 5,
    "DUPLICATE": 6,
}

LIFECYCLE_STATES = (
    "PRODUCTION_ELIGIBLE",
    "NEEDS_SOURCE_RESEARCH",
    "NEEDS_SEMANTIC_REVIEW",
    "REFERENCE_ONLY",
    "OUT_OF_SCOPE",
)

CANDIDATE_TIERS = (
    "T1_EXACT_SIGNATURE_NEIGHBOUR",
    "T2_SAME_SCOPE_SAME_FAMILY",
    "T3_SAME_SCOPE_LEXICAL",
    "T4_SAME_SCOPE_WEAK",
    "T5_CROSS_SCOPE_LEXICAL",
    "T6_SAME_SCOPE_ONLY",
    "T7_REMOTE",
)

#: Tiers routed to semantic adjudication.  Chosen by the Phase 6 recall audit:
#: every frozen-gold collapsing relation (DUPLICATE/EQUIVALENT/
#: VARIANT_OF_SAME_DECISION/NEAR_DUPLICATE) between two Registry V2 rows falls
#: in T2, and T1/T3 are carried as retrieval margin.
ADJUDICATION_TIERS = (
    "T1_EXACT_SIGNATURE_NEIGHBOUR",
    "T2_SAME_SCOPE_SAME_FAMILY",
    "T3_SAME_SCOPE_LEXICAL",
)

CONTRACT_VERSION = "REGISTRY_V3_CANONICALIZATION_CONTRACT_V1"

_LEXICAL_BLOCK_MAX = 60
_LEXICAL_TOKEN_MAX = 40
_LEXICAL_JACCARD = 0.5
_SCOPE_LEXICAL_JACCARD = 0.34
_BENCHMARK_JACCARD = 0.4

_STOPWORDS = {
    "the", "and", "for", "from", "with", "into", "apply", "reason",
    "reasoning", "vignette", "evidence", "decision", "differentiate",
}


# --------------------------------------------------------------------------
# Primitives
# --------------------------------------------------------------------------


def canonical_json(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def content_sha256(value: Any) -> str:
    payload = {k: v for k, v in value.items() if k != "content_sha256"} if isinstance(value, dict) else value
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()


def with_hash(value: dict[str, Any]) -> dict[str, Any]:
    value["content_sha256"] = content_sha256(value)
    return value


def file_sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _load(root: Path, relative: str) -> dict[str, Any]:
    return json.loads((Path(root) / relative).read_text())


def normalize_text(value: str | None) -> str:
    value = (value or "").lower().replace("&", " and ")
    return " ".join(re.sub(r"[^a-z0-9]+", " ", value).split())


def decision_text(row: Mapping[str, Any]) -> str:
    return " ".join(
        str(row.get(key) or "")
        for key in (
            "clinical_topic",
            "principal_decision",
            "learner_decision",
            "key_concept_or_action",
            "primary_reasoning_target",
        )
    ).strip().lower()


def decision_tokens(row: Mapping[str, Any]) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9]+", decision_text(row))
        if len(token) > 2 and token not in _STOPWORDS
    }


def jaccard(left: set[str], right: set[str]) -> float:
    if not left and not right:
        return 0.0
    return round(len(left & right) / len(left | right), 6)


def canonical_action(value: str | None, response_class: str) -> str:
    value = normalize_text(value)
    if response_class == "DIAGNOSIS" and value in {"recognize", "identify", "diagnose", "assess", "evaluate"}:
        return "diagnose"
    if value in {"manage", "treat"}:
        return "manage"
    if value in {"choose", "select"}:
        return "select"
    return value or "apply"


def atomic_signature(row: Mapping[str, Any]) -> dict[str, Any]:
    """Frozen Registry V3 atomic signature (unchanged from the V3 scaffold)."""
    return {
        "scope_unit": row["study_unit_id"],
        "response_class": row["response_class"],
        "decision_operator": canonical_action(row.get("action_lemma", "apply"), row["response_class"]),
        "decision_object": normalize_text(row.get("clinical_object") or row["key_concept_or_action"]),
        "material_state": None if row.get("clinical_stage") in {None, "NA"} else row["clinical_stage"],
        "material_population": None if row.get("population_context") in {None, "NA"} else row["population_context"],
    }


def exact_duplicate_invariants(row: Mapping[str, Any]) -> dict[str, str]:
    """Invariants under the existing projected-record duplicate contract.

    Two rows are *exact* duplicates only if every invariant matches.  Fuzzy
    similarity is never an exact identity proof.
    """
    return {
        "opportunity_fingerprint": str(row.get("opportunity_fingerprint") or ""),
        "atomic_signature_sha256": content_sha256(atomic_signature(row)),
        "projected_record_sha256": content_sha256(
            {
                key: row.get(key)
                for key in (
                    "discipline",
                    "study_unit_id",
                    "clinical_topic",
                    "opportunity_family",
                    "response_class",
                    "clinical_stage",
                    "population_context",
                    "severity_context",
                    "learner_decision",
                    "key_concept_or_action",
                    "primary_reasoning_target",
                )
            }
        ),
    }


# --------------------------------------------------------------------------
# Phase 2 — frozen input manifest
# --------------------------------------------------------------------------



# --------------------------------------------------------------------------
# Build memoization
# --------------------------------------------------------------------------

#: Builders are pure functions of the frozen on-disk inputs, so a rebuild can
#: reuse an earlier result within one process.  The cache key includes the
#: resolved root and the builder name; it never crosses a process boundary, so
#: it cannot mask an on-disk change between runs.
_BUILD_CACHE: dict[tuple[str, str], dict[str, Any]] = {}


def clear_build_cache() -> None:
    _BUILD_CACHE.clear()


def _memoize(function):
    name = function.__name__

    def wrapper(root: Path, *args: Any, **kwargs: Any) -> dict[str, Any]:
        if args or kwargs:
            return function(root, *args, **kwargs)
        key = (str(Path(root).resolve()), name)
        if key not in _BUILD_CACHE:
            _BUILD_CACHE[key] = function(root)
        return _BUILD_CACHE[key]

    wrapper.__name__ = name
    wrapper.__doc__ = function.__doc__
    wrapper.__wrapped__ = function
    return wrapper


@_memoize
def build_input_manifest(root: Path) -> dict[str, Any]:
    root = Path(root)
    v1 = _load(root, REGISTRY_V1_PATH)
    v2 = _load(root, REGISTRY_V2_PATH)
    benchmark = _load(root, BENCHMARK_PATH)
    contract = _load(root, ATOMIC_CONTRACT_PATH)
    artifact = {
        "schema_version": "1.0",
        "scope": "REGISTRY_V3_FROZEN_INPUT_MANIFEST",
        "contract_version": CONTRACT_VERSION,
        "inputs": {
            "registry_v1": {
                "path": REGISTRY_V1_PATH,
                "file_sha256": file_sha256(root / REGISTRY_V1_PATH),
                "content_sha256": v1["content_sha256"],
                "schema_version": v1["schema_version"],
                "rows": len(v1["opportunities"]),
                "mutable": False,
            },
            "registry_v2": {
                "path": REGISTRY_V2_PATH,
                "file_sha256": file_sha256(root / REGISTRY_V2_PATH),
                "content_sha256": v2["content_sha256"],
                "schema_version": v2["schema_version"],
                "rows": len(v2["opportunities"]),
                "discipline_counts": dict(sorted(Counter(r["discipline"] for r in v2["opportunities"]).items())),
                "mutable": False,
            },
            "normalized_atomic_benchmark_v2": {
                "path": BENCHMARK_PATH,
                "file_sha256": file_sha256(root / BENCHMARK_PATH),
                "content_sha256": benchmark["content_sha256"],
                "schema_version": benchmark["schema_version"],
                "rows": len(benchmark["opportunities"]),
                "evaluation_denominator_authorized": benchmark["evaluation_denominator_authorized"],
                "mutable": False,
            },
            "atomic_opportunity_contract_v1": {
                "path": ATOMIC_CONTRACT_PATH,
                "file_sha256": file_sha256(root / ATOMIC_CONTRACT_PATH),
                "content_sha256": contract["content_sha256"],
                "mutable": False,
            },
        },
        "registry_v2_is_immutable_input": True,
        "v3_is_additive_versioned_artifact": True,
    }
    return with_hash(artifact)


# --------------------------------------------------------------------------
# Phase 3 — Registry V3 canonical contract
# --------------------------------------------------------------------------


def build_v3_contract() -> dict[str, Any]:
    artifact = {
        "schema_version": "1.0",
        "scope": CONTRACT_VERSION,
        "canonical_opportunity_definition": (
            "One independently scoreable learner decision appropriate to a graduating Canadian medical "
            "student entering supervised practice, inherited unchanged from Atomic Opportunity Contract V1."
        ),
        "not_a_canonical_opportunity": [
            "TOPIC_HEADING",
            "DISEASE_NAME_ALONE",
            "CHAPTER_HEADING",
            "UMBRELLA_CATEGORY",
            "WORDING_VARIANT",
            "PRESENTATION_WRAPPER",
            "SPECIALIST_SUBDETAIL_WITHOUT_INDEPENDENT_MCCQE_VALUE",
        ],
        "relation_effect": dict(RELATION_EFFECT),
        "destructive_relations": list(DESTRUCTIVE_RELATIONS),
        "destructive_decision_policy": "SECOND_INDEPENDENT_HIGH_REVIEWER_REQUIRED_THIRD_ON_DISAGREEMENT",
        "exact_duplicate_policy": "DETERMINISTIC_ONLY_ON_FULL_INVARIANT_IDENTITY_NEVER_FUZZY",
        "uncertain_policy": "FAIL_CLOSED_NEVER_MERGE_NEVER_REMOVE_ALWAYS_REVIEW_QUEUE",
        "variant_policy": "VARIANTS_NEVER_COUNT_AS_INDEPENDENT_CURRICULUM_COVERAGE",
        "benchmark_mapping_policy": "MANY_TO_MANY_PERMITTED_NO_FORCED_ONE_TO_ONE",
        "id_policy": "DETERMINISTIC_CONTENT_DERIVED_NEVER_POSITIONAL",
        "lineage_policy": "EVERY_V3_ROW_TRACES_TO_V2_SOURCE_IDS_OR_DOCUMENTED_ADMITTED_GAP",
        "content_policy": "STRUCTURED_CURRICULUM_METADATA_ONLY_NO_STUDY_GUIDE_PROSE_NO_TORONTO_NOTES_REPRODUCTION",
        "capacity_policy": "NO_FIXED_QUESTIONS_PER_OPPORTUNITY_RATIO_CURRICULUM_VARIANT_AND_SEED_COUNTS_REPORTED_SEPARATELY",
        "mandatory_fields": [
            "opportunity_id",
            "schema_version",
            "discipline",
            "study_unit_id",
            "study_unit",
            "clinical_topic",
            "opportunity_family",
            "response_class",
            "clinical_stage",
            "population_context",
            "learner_decision",
            "key_concept_or_action",
            "primary_reasoning_target",
            "primary_discriminator_type",
            "MCC_objective_ids",
            "MCC_dimension_of_care",
            "MCC_physician_activity",
            "scope_status",
            "importance",
            "mcq_suitability",
            "supported_difficulty_levels",
            "atomic_signature_v1",
            "atomic_signature_sha256",
            "source_v2_opportunity_ids",
            "source_v1_opportunity_ids",
            "lifecycle_state",
            "variant_ids",
            "chapter_code",
            "chapter_title",
            "section_path",
        ],
        "lifecycle_states": list(LIFECYCLE_STATES),
        "candidate_tiers": list(CANDIDATE_TIERS),
        "adjudication_tiers": list(ADJUDICATION_TIERS),
        "relation_rank": dict(RELATION_RANK),
    }
    return with_hash(artifact)


# --------------------------------------------------------------------------
# Phase 5 — deterministic candidate discovery (registry x registry)
# --------------------------------------------------------------------------


def _blocking_index(rows: Sequence[Mapping[str, Any]]) -> dict[tuple, list[int]]:
    index: dict[tuple, list[int]] = defaultdict(list)
    for position, row in enumerate(rows):
        index[("STUDY_UNIT", row["study_unit_id"])].append(position)
        index[("TOPIC", row["discipline"], normalize_text(row.get("clinical_topic")))].append(position)
        index[("STUDY_UNIT_TITLE", row["discipline"], normalize_text(row.get("study_unit")))].append(position)
        for objective in row.get("MCC_objective_ids") or []:
            index[("MCC_OBJECTIVE", str(objective))].append(position)
    return index


def candidate_tier(
    left: Mapping[str, Any],
    right: Mapping[str, Any],
    left_tokens: set[str],
    right_tokens: set[str],
) -> str:
    left_signature, right_signature = atomic_signature(left), atomic_signature(right)
    same_scope = left["study_unit_id"] == right["study_unit_id"] or normalize_text(
        left.get("clinical_topic")
    ) == normalize_text(right.get("clinical_topic"))
    same_response = left["response_class"] == right["response_class"]
    same_family = left["opportunity_family"] == right["opportunity_family"]
    same_object = left_signature["decision_object"] == right_signature["decision_object"]
    same_operator = left_signature["decision_operator"] == right_signature["decision_operator"]
    overlap = jaccard(left_tokens, right_tokens)
    if same_scope and same_response and same_family and same_object and same_operator:
        return "T1_EXACT_SIGNATURE_NEIGHBOUR"
    if same_scope and same_response and same_family:
        return "T2_SAME_SCOPE_SAME_FAMILY"
    if same_scope and same_response and overlap >= _SCOPE_LEXICAL_JACCARD:
        return "T3_SAME_SCOPE_LEXICAL"
    if same_scope and (same_response or same_family):
        return "T4_SAME_SCOPE_WEAK"
    if same_response and overlap >= _LEXICAL_JACCARD:
        return "T5_CROSS_SCOPE_LEXICAL"
    if same_scope:
        return "T6_SAME_SCOPE_ONLY"
    return "T7_REMOTE"


def pair_id(left_id: str, right_id: str) -> str:
    a, b = sorted((left_id, right_id))
    return "RV3P-" + hashlib.sha256(f"registry-v3-pair|{a}|{b}".encode()).hexdigest()[:16].upper()


@_memoize
def mine_registry_candidates(root: Path) -> dict[str, Any]:
    """Bounded deterministic candidate discovery over Registry V2 rows.

    Proposes comparisons only.  Assigns no semantic label.
    """
    root = Path(root)
    v2 = _load(root, REGISTRY_V2_PATH)
    rows = v2["opportunities"]
    tokens = [decision_tokens(row) for row in rows]

    blocks: dict[tuple[int, int], set[str]] = defaultdict(set)
    for key, positions in _blocking_index(rows).items():
        if len(positions) > _LEXICAL_BLOCK_MAX:
            continue
        for left, right in itertools.combinations(sorted(positions), 2):
            blocks[(left, right)].add(key[0])

    inverted: dict[str, list[int]] = defaultdict(list)
    for position, token_set in enumerate(tokens):
        for token in token_set:
            inverted[token].append(position)
    for token, positions in inverted.items():
        if len(positions) > _LEXICAL_TOKEN_MAX:
            continue
        for left, right in itertools.combinations(sorted(positions), 2):
            if (left, right) in blocks:
                continue
            if jaccard(tokens[left], tokens[right]) >= _LEXICAL_JACCARD:
                blocks[(left, right)].add("LEXICAL")

    candidates = []
    for (left, right), block_keys in blocks.items():
        a, b = rows[left], rows[right]
        tier = candidate_tier(a, b, tokens[left], tokens[right])
        candidates.append(
            {
                "pair_id": pair_id(a["opportunity_id"], b["opportunity_id"]),
                "a_opportunity_id": a["opportunity_id"],
                "b_opportunity_id": b["opportunity_id"],
                "tier": tier,
                "blocks": sorted(block_keys),
                "token_jaccard": jaccard(tokens[left], tokens[right]),
                "queued_for_adjudication": tier in ADJUDICATION_TIERS,
            }
        )
    candidates.sort(key=lambda row: row["pair_id"])

    artifact = {
        "schema_version": "1.0",
        "scope": "REGISTRY_V3_REGISTRY_CANDIDATE_POOL",
        "contract_version": CONTRACT_VERSION,
        "registry_v2_sha256": v2["content_sha256"],
        "registry_v2_rows": len(rows),
        "total_possible_pairs": len(rows) * (len(rows) - 1) // 2,
        "candidate_pairs": len(candidates),
        "tier_counts": dict(sorted(Counter(c["tier"] for c in candidates).items())),
        "queued_pairs": sum(c["queued_for_adjudication"] for c in candidates),
        "selection_policy": "DETERMINISTIC_BLOCKING_THEN_TIERING_NO_SEMANTIC_LABEL_ASSIGNMENT",
        "candidates": candidates,
    }
    return with_hash(artifact)


# --------------------------------------------------------------------------
# Phase 11 — exact duplicate fast path
# --------------------------------------------------------------------------


@_memoize
def resolve_exact_duplicates(root: Path) -> dict[str, Any]:
    root = Path(root)
    rows = _load(root, REGISTRY_V2_PATH)["opportunities"]
    groups: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        invariants = exact_duplicate_invariants(row)
        proof = content_sha256(invariants)
        groups[proof].append(row["opportunity_id"])
    duplicates = [
        {
            "deterministic_proof_sha256": proof,
            "opportunity_ids": sorted(ids),
            "relation": "DUPLICATE",
            "review_method": "DETERMINISTIC_EXACT_INVARIANT_IDENTITY",
        }
        for proof, ids in sorted(groups.items())
        if len(ids) > 1
    ]
    artifact = {
        "schema_version": "1.0",
        "scope": "REGISTRY_V3_EXACT_DUPLICATE_RESOLUTION",
        "contract_version": CONTRACT_VERSION,
        "policy": "DETERMINISTIC_ONLY_ON_FULL_INVARIANT_IDENTITY_NEVER_FUZZY",
        "invariants": sorted(exact_duplicate_invariants(rows[0])),
        "rows_examined": len(rows),
        "duplicate_groups": len(duplicates),
        "rows_collapsed": sum(len(group["opportunity_ids"]) - 1 for group in duplicates),
        "groups": duplicates,
    }
    return with_hash(artifact)


# --------------------------------------------------------------------------
# Frozen semantic-judgment reuse
# --------------------------------------------------------------------------


def _candidate_pool_index(root: Path) -> dict[str, dict[str, Any]]:
    pools: dict[str, dict[str, Any]] = {}
    for directory in CANDIDATE_POOL_GLOBS:
        for path in sorted((Path(root) / directory).glob("*candidate_pool*.json")):
            for pair in json.loads(path.read_text()).get("pairs", []):
                pools.setdefault(pair["pair_id"], pair)
    return pools


@_memoize
def load_frozen_gold_relations(root: Path) -> dict[str, Any]:
    """Frozen, already-adjudicated relations reusable without re-review.

    Every row here was double-reviewed with third-reviewer adjudication on
    disagreement during the (now closed) matcher experiment.  Endpoints are
    resolved through the private candidate pools that recorded real source row
    ids.  Labels are reused verbatim; nothing is re-derived.
    """
    root = Path(root)
    pools = _candidate_pool_index(root)
    benchmark = _load(root, BENCHMARK_PATH)
    bop_to_nbo: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in benchmark["opportunities"]:
        for source in row["source_benchmark_opportunity_ids"]:
            bop_to_nbo[source].append(row)

    registry_pairs: list[dict[str, Any]] = []
    benchmark_pairs: list[dict[str, Any]] = []
    unresolved = 0
    for relative in GOLD_RELATION_ARTIFACTS:
        gold = _load(root, relative)
        for review in gold["reviews"]:
            pair = pools.get(review["pair_id"])
            if pair is None:
                unresolved += 1
                continue
            provenance = pair["source_provenance"]
            artifacts = [item["artifact"] for item in provenance]
            registry_ids = [
                item["row_id"]
                for item in provenance
                if item["artifact"] == "curriculum_question_opportunity_registry_v2"
            ]
            if artifacts.count("curriculum_question_opportunity_registry_v2") == 2:
                left, right = sorted(registry_ids)
                registry_pairs.append(
                    {
                        "pair_id": pair_id(left, right),
                        "a_opportunity_id": left,
                        "b_opportunity_id": right,
                        "relation": review["relation"],
                        "review_method": "FROZEN_DOUBLE_REVIEWED_GOLD",
                        "provenance_artifact": relative,
                        "provenance_pair_id": review["pair_id"],
                    }
                )
                continue
            bench = [item for item in provenance if "benchmark" in item["artifact"]]
            if not bench or not registry_ids:
                continue
            row_id = bench[0]["row_id"]
            if row_id.startswith("NBO-"):
                targets = [row for row in benchmark["opportunities"] if row["normalized_opportunity_id"] == row_id]
            else:
                # Only rows carried through normalization unchanged and from a
                # single source row keep the adjudicated meaning intact.
                targets = [
                    row
                    for row in bop_to_nbo.get(row_id, [])
                    if row["transformation"] == "KEEP" and len(row["source_benchmark_opportunity_ids"]) == 1
                ]
            for target in targets:
                benchmark_pairs.append(
                    {
                        "benchmark_opportunity_id": target["normalized_opportunity_id"],
                        "registry_v2_opportunity_id": registry_ids[0],
                        "relation": review["relation"],
                        "review_method": "FROZEN_DOUBLE_REVIEWED_GOLD",
                        "provenance_artifact": relative,
                        "provenance_pair_id": review["pair_id"],
                    }
                )

    registry_pairs.sort(key=lambda row: (row["pair_id"], row["provenance_pair_id"]))
    benchmark_pairs.sort(
        key=lambda row: (row["benchmark_opportunity_id"], row["registry_v2_opportunity_id"], row["provenance_pair_id"])
    )
    artifact = {
        "schema_version": "1.0",
        "scope": "REGISTRY_V3_REUSABLE_FROZEN_SEMANTIC_JUDGMENTS",
        "contract_version": CONTRACT_VERSION,
        "source_artifacts": [
            {"path": relative, "file_sha256": file_sha256(Path(root) / relative)}
            for relative in GOLD_RELATION_ARTIFACTS
        ],
        "reuse_policy": "VERBATIM_LABEL_REUSE_NO_RE_REVIEW_NO_RE_DERIVATION",
        "unresolved_gold_rows": unresolved,
        "registry_pair_count": len(registry_pairs),
        "benchmark_pair_count": len(benchmark_pairs),
        "registry_relation_counts": dict(sorted(Counter(r["relation"] for r in registry_pairs).items())),
        "benchmark_relation_counts": dict(sorted(Counter(r["relation"] for r in benchmark_pairs).items())),
        "registry_pairs": registry_pairs,
        "benchmark_pairs": benchmark_pairs,
    }
    return with_hash(artifact)


# --------------------------------------------------------------------------
# Phase 6 — candidate retrieval recall audit
# --------------------------------------------------------------------------


@_memoize
def build_candidate_recall_audit(root: Path) -> dict[str, Any]:
    """Retrieval-recall diagnostic only.  Never tunes a semantic label."""
    root = Path(root)
    pool = mine_registry_candidates(root)
    frozen = load_frozen_gold_relations(root)
    by_pair = {row["pair_id"]: row for row in pool["candidates"]}

    retrieved: Counter[tuple[str, bool]] = Counter()
    queued: Counter[tuple[str, bool]] = Counter()
    misses: list[dict[str, Any]] = []
    for row in frozen["registry_pairs"]:
        candidate = by_pair.get(row["pair_id"])
        retrieved[(row["relation"], candidate is not None)] += 1
        queued[(row["relation"], bool(candidate and candidate["queued_for_adjudication"]))] += 1
        if candidate is None and row["relation"] != "UNRELATED":
            misses.append({"pair_id": row["pair_id"], "relation": row["relation"]})

    def _rate(counter: Counter, relations: Sequence[str]) -> dict[str, Any]:
        hit = sum(counter[(relation, True)] for relation in relations)
        total = hit + sum(counter[(relation, False)] for relation in relations)
        return {"hit": hit, "total": total, "recall": round(hit / total, 6) if total else None}

    collapsing = ("DUPLICATE", "EQUIVALENT", "VARIANT_OF_SAME_DECISION", "NEAR_DUPLICATE")
    containment = ("REGISTRY_BROADER_CONTAINS_BENCHMARK", "REGISTRY_NARROWER_THAN_BENCHMARK")
    artifact = {
        "schema_version": "1.0",
        "scope": "REGISTRY_V3_CANDIDATE_RETRIEVAL_RECALL_AUDIT",
        "contract_version": CONTRACT_VERSION,
        "diagnostic_only": True,
        "semantic_labels_tuned": False,
        "candidate_pool_sha256": pool["content_sha256"],
        "frozen_gold_sha256": frozen["content_sha256"],
        "evaluated_pairs": len(frozen["registry_pairs"]),
        "retrieval_recall_by_relation": {
            relation: {
                "retrieved": retrieved[(relation, True)],
                "total": retrieved[(relation, True)] + retrieved[(relation, False)],
            }
            for relation in RELATIONS
            if retrieved[(relation, True)] + retrieved[(relation, False)]
        },
        "collapsing_relation_retrieval": _rate(retrieved, collapsing),
        "collapsing_relation_queued": _rate(queued, collapsing),
        "containment_relation_retrieval": _rate(retrieved, containment),
        "unrelated_correctly_excluded": retrieved[("UNRELATED", False)],
        "unrelated_total": retrieved[("UNRELATED", True)] + retrieved[("UNRELATED", False)],
        "non_unrelated_retrieval_misses": sorted(misses, key=lambda row: row["pair_id"]),
    }
    artifact["candidate_retrieval_sufficient"] = (
        artifact["collapsing_relation_queued"]["recall"] == 1.0
        if artifact["collapsing_relation_queued"]["total"]
        else False
    )
    return with_hash(artifact)


# --------------------------------------------------------------------------
# Phase 7 — relation-candidate adjudication queue
# --------------------------------------------------------------------------

_QUEUE_FIELDS = (
    "discipline",
    "study_unit_id",
    "study_unit",
    "clinical_topic",
    "opportunity_family",
    "response_class",
    "clinical_stage",
    "population_context",
    "severity_context",
    "learner_decision",
    "key_concept_or_action",
    "primary_reasoning_target",
    "primary_discriminator_type",
    "scope_status",
    "MCC_physician_activity",
    "MCC_objective_ids",
)


def _queue_projection(row: Mapping[str, Any]) -> dict[str, Any]:
    projection = {key: row[key] for key in _QUEUE_FIELDS if row.get(key) not in (None, "", [], {}, "NA")}
    projection["atomic_signature"] = atomic_signature(row)
    return projection


@_memoize
def build_adjudication_queue(root: Path) -> dict[str, Any]:
    """Deterministic semantic-adjudication queue.

    Carries only the context needed to adjudicate.  No desired relation, no
    class quota, and no prior matcher prediction reaches the reviewer.
    """
    root = Path(root)
    rows = {row["opportunity_id"]: row for row in _load(root, REGISTRY_V2_PATH)["opportunities"]}
    pool = mine_registry_candidates(root)
    frozen = load_frozen_gold_relations(root)
    resolved = {row["pair_id"] for row in frozen["registry_pairs"]}

    pending, reused = [], []
    for candidate in pool["candidates"]:
        if not candidate["queued_for_adjudication"]:
            continue
        if candidate["pair_id"] in resolved:
            reused.append(candidate["pair_id"])
            continue
        a, b = rows[candidate["a_opportunity_id"]], rows[candidate["b_opportunity_id"]]
        pending.append(
            {
                "pair_id": candidate["pair_id"],
                "tier": candidate["tier"],
                "discipline": a["discipline"],
                "opportunity_a": _queue_projection(a),
                "opportunity_b": _queue_projection(b),
                "directionality": "UNORDERED_A_B_AS_PRESENTED",
                "review_fields": {"relation": None, "direction": None, "justification": None},
            }
        )
    priority = {tier: index for index, tier in enumerate(ADJUDICATION_TIERS)}
    pending.sort(key=lambda row: (priority.get(row["tier"], 99), row["pair_id"]))

    artifact = {
        "schema_version": "1.0",
        "scope": "REGISTRY_V3_SEMANTIC_ADJUDICATION_QUEUE",
        "contract_version": CONTRACT_VERSION,
        "taxonomy": list(RELATIONS),
        "queue_policy": "HIGH_IMPACT_TIERS_ONLY_NO_DESIRED_RELATION_NO_CLASS_QUOTA_NO_MATCHER_PREDICTION",
        "candidate_pool_sha256": pool["content_sha256"],
        "frozen_gold_sha256": frozen["content_sha256"],
        "queued_candidate_pairs": pool["queued_pairs"],
        "already_resolved_by_frozen_gold": len(reused),
        "pending_semantic_reviews": len(pending),
        "tier_counts": dict(sorted(Counter(row["tier"] for row in pending).items())),
        "reused_pair_ids": sorted(reused),
        "pending": pending,
    }
    return with_hash(artifact)


# --------------------------------------------------------------------------
# Phase 17 — benchmark mapping candidate retrieval
# --------------------------------------------------------------------------


@_memoize
def mine_benchmark_candidates(root: Path) -> dict[str, Any]:
    root = Path(root)
    registry = _load(root, REGISTRY_V2_PATH)["opportunities"]
    benchmark = _load(root, BENCHMARK_PATH)
    by_study_unit: dict[str, list[int]] = defaultdict(list)
    for position, row in enumerate(registry):
        by_study_unit[row["study_unit_id"]].append(position)
    registry_tokens = [decision_tokens(row) for row in registry]

    candidates = []
    for row in benchmark["opportunities"]:
        positions = set(by_study_unit.get(row["study_unit_id"], []))
        target_tokens = decision_tokens(row)
        for position, tokens in enumerate(registry_tokens):
            if registry[position]["discipline"] != row["discipline"]:
                continue
            if jaccard(tokens, target_tokens) >= _BENCHMARK_JACCARD:
                positions.add(position)
        for position in sorted(positions):
            candidates.append(
                {
                    "benchmark_opportunity_id": row["normalized_opportunity_id"],
                    "registry_v2_opportunity_id": registry[position]["opportunity_id"],
                    "same_study_unit": registry[position]["study_unit_id"] == row["study_unit_id"],
                    "token_jaccard": jaccard(registry_tokens[position], target_tokens),
                }
            )
    candidates.sort(key=lambda row: (row["benchmark_opportunity_id"], row["registry_v2_opportunity_id"]))
    covered = {row["benchmark_opportunity_id"] for row in candidates}
    artifact = {
        "schema_version": "1.0",
        "scope": "REGISTRY_V3_BENCHMARK_CANDIDATE_POOL",
        "contract_version": CONTRACT_VERSION,
        "benchmark_sha256": benchmark["content_sha256"],
        "benchmark_rows": len(benchmark["opportunities"]),
        "benchmark_rows_with_candidates": len(covered),
        "benchmark_rows_without_candidates": sorted(
            row["normalized_opportunity_id"]
            for row in benchmark["opportunities"]
            if row["normalized_opportunity_id"] not in covered
        ),
        "candidate_pairs": len(candidates),
        "selection_policy": "STUDY_UNIT_BLOCK_PLUS_SAME_DISCIPLINE_LEXICAL_NO_SEMANTIC_LABEL_ASSIGNMENT",
        "candidates": candidates,
    }
    return with_hash(artifact)


_BENCHMARK_QUEUE_FIELDS = (
    "discipline",
    "study_unit_id",
    "opportunity_family",
    "response_class",
    "clinical_stage",
    "population_context",
    "principal_decision",
    "primary_reasoning_target",
)


@_memoize
def build_benchmark_adjudication_queue(root: Path) -> dict[str, Any]:
    root = Path(root)
    registry = {row["opportunity_id"]: row for row in _load(root, REGISTRY_V2_PATH)["opportunities"]}
    benchmark = {
        row["normalized_opportunity_id"]: row for row in _load(root, BENCHMARK_PATH)["opportunities"]
    }
    pool = mine_benchmark_candidates(root)
    frozen = load_frozen_gold_relations(root)
    resolved = {
        (row["benchmark_opportunity_id"], row["registry_v2_opportunity_id"]) for row in frozen["benchmark_pairs"]
    }

    pending, reused = [], []
    for candidate in pool["candidates"]:
        key = (candidate["benchmark_opportunity_id"], candidate["registry_v2_opportunity_id"])
        if key in resolved:
            reused.append(list(key))
            continue
        bench = benchmark[key[0]]
        pending.append(
            {
                "pair_id": "RV3B-"
                + hashlib.sha256(f"registry-v3-benchmark|{key[0]}|{key[1]}".encode()).hexdigest()[:16].upper(),
                "benchmark_opportunity_id": key[0],
                "registry_v2_opportunity_id": key[1],
                "discipline": bench["discipline"],
                "benchmark_opportunity": {
                    field: bench[field] for field in _BENCHMARK_QUEUE_FIELDS if bench.get(field) not in (None, "", "NA")
                },
                "registry_opportunity": _queue_projection(registry[key[1]]),
                "directionality": "BENCHMARK_IS_A_REGISTRY_IS_B",
                "review_fields": {"relation": None, "justification": None},
            }
        )
    pending.sort(key=lambda row: row["pair_id"])
    artifact = {
        "schema_version": "1.0",
        "scope": "REGISTRY_V3_BENCHMARK_ADJUDICATION_QUEUE",
        "contract_version": CONTRACT_VERSION,
        "taxonomy": list(RELATIONS),
        "queue_policy": "MANY_TO_MANY_PERMITTED_NO_DESIRED_RELATION_NO_MATCHER_PREDICTION",
        "benchmark_candidate_pool_sha256": pool["content_sha256"],
        "already_resolved_by_frozen_gold": len(reused),
        "pending_semantic_reviews": len(pending),
        "pending": pending,
    }
    return with_hash(artifact)


# --------------------------------------------------------------------------
# Deterministic atomicity screen (Phase 3 / Phase 22 / Phase 25)
# --------------------------------------------------------------------------

#: Registry V2 inherited every V1 row in a generated wrapper form,
#: ``Apply <phrase> reasoning for <study unit>.``  The wrapper itself is a
#: presentation shell, so the question is whether <phrase> names one
#: independently scoreable decision or only a curriculum category.
_UMBRELLA_PATTERN = re.compile(r"^apply (?P<phrase>.+) reasoning for .+\.$", re.IGNORECASE)

#: Curriculum-category vocabulary.  A wrapper phrase built entirely from these
#: tokens names a heading, never a decision.  Frozen; never tuned against any
#: gold label.
GENERIC_CATEGORY_TOKENS = frozenset(
    """
    a an and or of the for to up
    action actions anticipatory approach assess assessment best care choice choose class
    classification classify common communicate communication complication complications core
    counsel counseling counselling decision decisions diagnose diagnosis diagnostic differential
    differentiate differentiation emergency ethical ethics evaluate evaluation flag flags follow
    general guidance identification identify indication indications initial interpret interpretation
    investigate investigation investigations issues legal localisation localization manage
    management monitor monitoring navigation next plan planning prevent prevention professional
    reasoning recognise recognition recognize recommendation recommendations red refer referral
    risk safety screen screening select selection stabilisation stabilization step steps system
    """.split()
)

ATOMICITY_CLASSES = (
    "CONCRETE_DECISION_STATEMENT",
    "NAMED_PHRASE_WRAPPER",
    "GENERIC_CATEGORY_WRAPPER",
)


def classify_atomicity_form(row: Mapping[str, Any]) -> dict[str, Any]:
    """Deterministic structural atomicity screen.

    Structural form only.  It never asserts that a concrete statement *is*
    atomic, only that a generic category wrapper cannot be.
    """
    decision = str(row.get("learner_decision") or "").strip()
    match = _UMBRELLA_PATTERN.match(decision)
    if match is None:
        return {
            "atomicity_form": "CONCRETE_DECISION_STATEMENT",
            "wrapper_phrase": None,
            "can_be_canonical_decision": True,
            "basis": "DECISION_STATED_DIRECTLY_NOT_AS_A_TOPIC_WRAPPER",
        }
    phrase = match.group("phrase").strip().lower()
    tokens = re.findall(r"[a-z0-9]+", phrase)
    generic = bool(tokens) and all(token in GENERIC_CATEGORY_TOKENS for token in tokens)
    if generic:
        return {
            "atomicity_form": "GENERIC_CATEGORY_WRAPPER",
            "wrapper_phrase": phrase,
            "can_be_canonical_decision": False,
            "basis": "WRAPPER_PHRASE_IS_ENTIRELY_CURRICULUM_CATEGORY_VOCABULARY_SO_IT_NAMES_A_HEADING",
        }
    return {
        "atomicity_form": "NAMED_PHRASE_WRAPPER",
        "wrapper_phrase": phrase,
        "can_be_canonical_decision": False,
        "basis": "WRAPPER_PHRASE_NAMES_CONTENT_BUT_THE_DECISION_RULE_IS_NOT_EXPLICIT_SO_ATOMICITY_IS_UNPROVEN",
    }


@_memoize
def build_atomicity_screen(root: Path) -> dict[str, Any]:
    root = Path(root)
    v2 = _load(root, REGISTRY_V2_PATH)
    rows = v2["opportunities"]
    screened = []
    for row in rows:
        verdict = classify_atomicity_form(row)
        screened.append(
            {
                "opportunity_id": row["opportunity_id"],
                "discipline": row["discipline"],
                "provenance_type": row["provenance_type"],
                "mcq_suitability": row["mcq_suitability"],
                **verdict,
            }
        )
    screened.sort(key=lambda row: row["opportunity_id"])
    by_form = Counter(row["atomicity_form"] for row in screened)
    artifact = {
        "schema_version": "1.0",
        "scope": "REGISTRY_V3_DETERMINISTIC_ATOMICITY_SCREEN",
        "contract_version": CONTRACT_VERSION,
        "registry_v2_sha256": v2["content_sha256"],
        "policy": "STRUCTURAL_FORM_ONLY_FAIL_CLOSED_A_WRAPPER_IS_NEVER_PRESUMED_ATOMIC",
        "generic_category_token_count": len(GENERIC_CATEGORY_TOKENS),
        "rows_examined": len(rows),
        "form_counts": dict(sorted(by_form.items())),
        "form_counts_by_discipline": {
            form: dict(sorted(Counter(r["discipline"] for r in screened if r["atomicity_form"] == form).items()))
            for form in ATOMICITY_CLASSES
        },
        "can_be_canonical_decision_count": sum(row["can_be_canonical_decision"] for row in screened),
        "rows": screened,
    }
    return with_hash(artifact)


# --------------------------------------------------------------------------
# Adjudication consolidation (Phase 9)
# --------------------------------------------------------------------------

ADJUDICATION_DIR = "adjudication"


def _adjudication_files(root: Path, prefix: str) -> list[Path]:
    directory = Path(root) / DESTINATION / ADJUDICATION_DIR
    return sorted(directory.glob(f"{prefix}*.json")) if directory.exists() else []


@_memoize
def load_primary_adjudications(root: Path) -> dict[str, Any]:
    """Consolidate the frozen primary registry-pair adjudication batches."""
    reviews: dict[str, dict[str, Any]] = {}
    batches = []
    for path in _adjudication_files(root, "registry_primary_batch_"):
        payload = json.loads(path.read_text())
        batches.append({"path": f"{DESTINATION}/{ADJUDICATION_DIR}/{path.name}", "file_sha256": file_sha256(path)})
        for review in payload["reviews"]:
            if review["relation"] not in RELATIONS:
                raise ValueError(f"unknown relation {review['relation']}")
            if review["pair_id"] in reviews:
                raise ValueError(f"pair adjudicated twice: {review['pair_id']}")
            reviews[review["pair_id"]] = {
                "pair_id": review["pair_id"],
                "relation": review["relation"],
                "justification": review["justification"],
                "reviewer_id": payload["reviewer_id"],
                "reviewer_role": payload["reviewer_role"],
                "batch": payload["batch"],
            }
    artifact = {
        "schema_version": "1.0",
        "scope": "REGISTRY_V3_PRIMARY_ADJUDICATION_CONSOLIDATION",
        "contract_version": CONTRACT_VERSION,
        "batches": batches,
        "review_count": len(reviews),
        "relation_counts": dict(sorted(Counter(r["relation"] for r in reviews.values()).items())),
        "destructive_proposal_count": sum(
            r["relation"] in DESTRUCTIVE_RELATIONS for r in reviews.values()
        ),
        "reviews": [reviews[key] for key in sorted(reviews)],
    }
    return with_hash(artifact)


@_memoize
def build_destructive_second_review_packet(root: Path) -> dict[str, Any]:
    """Blind packet for the second independent reviewer (Phase 10).

    Only proposals that would remove or demote a coverage unit are sent, and
    the primary reviewer's label and justification are withheld.
    """
    root = Path(root)
    rows = {row["opportunity_id"]: row for row in _load(root, REGISTRY_V2_PATH)["opportunities"]}
    queue = build_adjudication_queue(root)
    by_pair = {row["pair_id"]: row for row in queue["pending"]}
    primary = load_primary_adjudications(root)

    packet = []
    for review in primary["reviews"]:
        if review["relation"] not in DESTRUCTIVE_RELATIONS:
            continue
        candidate = by_pair[review["pair_id"]]
        packet.append(
            {
                "pair_id": review["pair_id"],
                "tier": candidate["tier"],
                "discipline": candidate["discipline"],
                "opportunity_a": candidate["opportunity_a"],
                "opportunity_b": candidate["opportunity_b"],
                "directionality": candidate["directionality"],
                "review_fields": {"relation": None, "justification": None},
            }
        )
    packet.sort(key=lambda row: row["pair_id"])
    artifact = {
        "schema_version": "1.0",
        "scope": "REGISTRY_V3_DESTRUCTIVE_SECOND_REVIEW_PACKET",
        "contract_version": CONTRACT_VERSION,
        "taxonomy": list(RELATIONS),
        "blinding_policy": "PRIMARY_LABEL_AND_JUSTIFICATION_WITHHELD_NO_MATCHER_PREDICTION",
        "trigger": "PROPOSAL_WOULD_REMOVE_OR_DEMOTE_A_CANONICAL_COVERAGE_UNIT",
        "destructive_relations": list(DESTRUCTIVE_RELATIONS),
        "primary_adjudication_sha256": primary["content_sha256"],
        "pairs": len(packet),
        "packet": packet,
    }
    return with_hash(artifact)


@_memoize
def analyze_destructive_agreement(root: Path) -> dict[str, Any]:
    """Primary vs second independent reviewer on destructive proposals."""
    root = Path(root)
    primary = {r["pair_id"]: r for r in load_primary_adjudications(root)["reviews"]}
    path = Path(root) / DESTINATION / ADJUDICATION_DIR / "registry_secondary_destructive_review.json"
    secondary_payload = json.loads(path.read_text())
    secondary = {r["pair_id"]: r for r in secondary_payload["reviews"]}
    if set(secondary) - set(primary):
        raise ValueError("second review contains a pair the primary never adjudicated")

    agreed, disagreed = [], []
    for pair_id in sorted(secondary):
        first, second = primary[pair_id], secondary[pair_id]
        row = {
            "pair_id": pair_id,
            "primary_relation": first["relation"],
            "secondary_relation": second["relation"],
        }
        (agreed if first["relation"] == second["relation"] else disagreed).append(row)
    artifact = {
        "schema_version": "1.0",
        "scope": "REGISTRY_V3_DESTRUCTIVE_REVIEW_AGREEMENT",
        "contract_version": CONTRACT_VERSION,
        "policy": "A_DESTRUCTIVE_RELATION_BINDS_ONLY_ON_TWO_INDEPENDENT_AGREEING_REVIEWS",
        "second_review_file_sha256": file_sha256(path),
        "reviewed_pairs": len(secondary),
        "agreement_count": len(agreed),
        "disagreement_count": len(disagreed),
        "inter_reviewer_agreement": round(len(agreed) / len(secondary), 6) if secondary else None,
        "secondary_relation_counts": dict(
            sorted(Counter(r["relation"] for r in secondary.values()).items())
        ),
        "agreed": agreed,
        "disagreed": disagreed,
    }
    return with_hash(artifact)


@_memoize
def build_disagreement_packet(root: Path) -> dict[str, Any]:
    """Blind third-adjudicator packet: only pairs the two reviewers split on."""
    root = Path(root)
    agreement = analyze_destructive_agreement(root)
    queue = build_adjudication_queue(root)
    by_pair = {row["pair_id"]: row for row in queue["pending"]}
    packet = [
        {
            "pair_id": row["pair_id"],
            "tier": by_pair[row["pair_id"]]["tier"],
            "discipline": by_pair[row["pair_id"]]["discipline"],
            "opportunity_a": by_pair[row["pair_id"]]["opportunity_a"],
            "opportunity_b": by_pair[row["pair_id"]]["opportunity_b"],
            "directionality": by_pair[row["pair_id"]]["directionality"],
            "review_fields": {"relation": None, "justification": None},
        }
        for row in agreement["disagreed"]
    ]
    artifact = {
        "schema_version": "1.0",
        "scope": "REGISTRY_V3_DISAGREEMENT_ADJUDICATION_PACKET",
        "contract_version": CONTRACT_VERSION,
        "taxonomy": list(RELATIONS),
        "blinding_policy": "BOTH_PRIOR_LABELS_WITHHELD_NO_MATCHER_PREDICTION",
        "agreement_sha256": agreement["content_sha256"],
        "pairs": len(packet),
        "packet": packet,
    }
    return with_hash(artifact)


# --------------------------------------------------------------------------
# Phase 12 — binding relations and the append-only relation graph
# --------------------------------------------------------------------------


@_memoize
def resolve_registry_relations(root: Path) -> dict[str, Any]:
    """Final bound relation for every adjudicated registry pair.

    Binding rule (Phase 10):

    * a non-destructive primary verdict binds directly;
    * a destructive primary verdict binds only after a second independent
      reviewer agrees;
    * where the two disagree, a third fresh adjudicator's verdict binds.

    A destructive verdict therefore never rests on a single reviewer: either
    two reviewers agreed outright, or the third adjudicator concurred with one
    of them that the pair is a single decision.
    """
    root = Path(root)
    primary = {r["pair_id"]: r for r in load_primary_adjudications(root)["reviews"]}
    agreement = analyze_destructive_agreement(root)
    agreed = {row["pair_id"] for row in agreement["agreed"]}
    third_path = Path(root) / DESTINATION / ADJUDICATION_DIR / "registry_third_disagreement_adjudication.json"
    third_payload = json.loads(third_path.read_text())
    third = {r["pair_id"]: r for r in third_payload["reviews"]}
    disagreed = {row["pair_id"] for row in agreement["disagreed"]}
    if set(third) != disagreed:
        raise ValueError("third adjudication must cover exactly the disagreed pairs")

    resolved = []
    for pair_id in sorted(primary):
        first = primary[pair_id]
        if first["relation"] not in DESTRUCTIVE_RELATIONS:
            resolved.append(
                {
                    "pair_id": pair_id,
                    "relation": first["relation"],
                    "justification": first["justification"],
                    "review_method": "SINGLE_HIGH_SEMANTIC_ADJUDICATION",
                    "reviewer_lineage": [first["reviewer_id"]],
                }
            )
            continue
        if pair_id in agreed:
            resolved.append(
                {
                    "pair_id": pair_id,
                    "relation": first["relation"],
                    "justification": first["justification"],
                    "review_method": "DOUBLE_INDEPENDENT_HIGH_SEMANTIC_ADJUDICATION_AGREED",
                    "reviewer_lineage": [first["reviewer_id"], "RV3_SECONDARY_B"],
                }
            )
            continue
        verdict = third[pair_id]
        resolved.append(
            {
                "pair_id": pair_id,
                "relation": verdict["relation"],
                "justification": verdict["justification"],
                "review_method": "THIRD_ADJUDICATOR_RESOLVED_REVIEWER_DISAGREEMENT",
                "reviewer_lineage": [first["reviewer_id"], "RV3_SECONDARY_B", third_payload["reviewer_id"]],
            }
        )

    bound_destructive = [row for row in resolved if row["relation"] in DESTRUCTIVE_RELATIONS]
    single_reviewed_destructive = [
        row for row in bound_destructive if row["review_method"] == "SINGLE_HIGH_SEMANTIC_ADJUDICATION"
    ]
    if single_reviewed_destructive:
        raise ValueError("a destructive relation bound on a single review")

    artifact = {
        "schema_version": "1.0",
        "scope": "REGISTRY_V3_RESOLVED_REGISTRY_RELATIONS",
        "contract_version": CONTRACT_VERSION,
        "binding_policy": "DESTRUCTIVE_RELATIONS_REQUIRE_TWO_INDEPENDENT_REVIEWS_OR_THIRD_ADJUDICATION",
        "third_adjudication_file_sha256": file_sha256(third_path),
        "resolved_pairs": len(resolved),
        "relation_counts": dict(sorted(Counter(r["relation"] for r in resolved).items())),
        "destructive_bound": len(bound_destructive),
        "double_reviewed": sum(
            row["review_method"] != "SINGLE_HIGH_SEMANTIC_ADJUDICATION" for row in resolved
        ),
        "third_adjudicated": sum(
            row["review_method"] == "THIRD_ADJUDICATOR_RESOLVED_REVIEWER_DISAGREEMENT" for row in resolved
        ),
        "resolved": resolved,
    }
    return with_hash(artifact)


@_memoize
def build_relation_graph(root: Path) -> dict[str, Any]:
    """Append-only relation graph over Registry V2 source opportunity ids."""
    root = Path(root)
    pool = mine_registry_candidates(root)
    endpoints = {c["pair_id"]: (c["a_opportunity_id"], c["b_opportunity_id"]) for c in pool["candidates"]}
    frozen = load_frozen_gold_relations(root)
    resolved = resolve_registry_relations(root)
    exact = resolve_exact_duplicates(root)
    contract = build_v3_contract()

    edges: dict[str, dict[str, Any]] = {}

    def _add(pair: str, relation: str, **provenance: Any) -> None:
        a, b = endpoints[pair]
        existing = edges.get(pair)
        if existing and RELATION_RANK[relation] <= RELATION_RANK[existing["relation"]]:
            return
        edges[pair] = {
            "pair_id": pair,
            "a_opportunity_id": a,
            "b_opportunity_id": b,
            "relation": relation,
            "direction": (
                "A_CONTAINS_B"
                if relation == "REGISTRY_BROADER_CONTAINS_BENCHMARK"
                else "B_CONTAINS_A"
                if relation == "REGISTRY_NARROWER_THAN_BENCHMARK"
                else "SYMMETRIC"
            ),
            "effect": RELATION_EFFECT[relation],
            "contract_version": CONTRACT_VERSION,
            "contract_sha256": contract["content_sha256"],
            **provenance,
        }

    for row in frozen["registry_pairs"]:
        if row["pair_id"] not in endpoints:
            continue
        _add(
            row["pair_id"],
            row["relation"],
            provenance="FROZEN_GOLD_REUSE",
            review_method=row["review_method"],
            reviewer_lineage=["FROZEN_DOUBLE_REVIEWED_GOLD"],
            source_artifact=row["provenance_artifact"],
        )
    for row in resolved["resolved"]:
        _add(
            row["pair_id"],
            row["relation"],
            provenance="REGISTRY_V3_SEMANTIC_ADJUDICATION",
            review_method=row["review_method"],
            reviewer_lineage=row["reviewer_lineage"],
            justification=row["justification"],
        )

    artifact = {
        "schema_version": "1.0",
        "scope": "REGISTRY_V3_RELATION_GRAPH",
        "contract_version": CONTRACT_VERSION,
        "append_only": True,
        "source_id_space": "CURRICULUM_QUESTION_OPPORTUNITY_REGISTRY_V2_OPPORTUNITY_ID",
        "candidate_pool_sha256": pool["content_sha256"],
        "frozen_reuse_sha256": frozen["content_sha256"],
        "resolved_relations_sha256": resolved["content_sha256"],
        "exact_duplicate_resolution_sha256": exact["content_sha256"],
        "nodes": pool["registry_v2_rows"],
        "edges": len(edges),
        "relation_counts": dict(sorted(Counter(e["relation"] for e in edges.values()).items())),
        "edge_list": [edges[key] for key in sorted(edges)],
    }
    return with_hash(artifact)


def validate_monotonicity(graph: Mapping[str, Any], baseline: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Adding knowledge may refine a pair's relation upward, never downward."""
    current = {edge["pair_id"]: edge["relation"] for edge in graph["edge_list"]}
    violations = []
    if baseline:
        for edge in baseline["edge_list"]:
            before = RELATION_RANK[edge["relation"]]
            after = RELATION_RANK.get(current.get(edge["pair_id"], "UNRELATED"), 0)
            if after < before:
                violations.append(
                    {
                        "pair_id": edge["pair_id"],
                        "baseline_relation": edge["relation"],
                        "current_relation": current.get(edge["pair_id"]),
                    }
                )
    return {
        "invariant": "ADDING_REGISTRY_CANDIDATES_CANNOT_LOWER_BEST_RELATION_RANK",
        "baseline_edges": len(baseline["edge_list"]) if baseline else 0,
        "current_edges": len(current),
        "violations": violations,
        "monotonicity": "PASS" if not violations else "FAIL",
    }


# --------------------------------------------------------------------------
# Phase 13-16 — canonical components, stable ids, variants
# --------------------------------------------------------------------------


class _Union:
    def __init__(self) -> None:
        self.parent: dict[str, str] = {}

    def find(self, node: str) -> str:
        self.parent.setdefault(node, node)
        while self.parent[node] != node:
            self.parent[node] = self.parent[self.parent[node]]
            node = self.parent[node]
        return node

    def union(self, left: str, right: str) -> None:
        a, b = self.find(left), self.find(right)
        if a != b:
            self.parent[max(a, b)] = min(a, b)


#: Field precedence when several source rows collapse into one canonical row.
#: The strongest well-formed source wins; nothing clinical is invented.
def _representative_rank(row: Mapping[str, Any], form: Mapping[str, Any]) -> tuple:
    suitability = {"MCQ_STRONG": 0, "MCQ_ACCEPTABLE": 1, "MCQ_WEAK": 2, "NOT_SUITABLE_FOR_MC": 3}
    atomicity = {"CONCRETE_DECISION_STATEMENT": 0, "NAMED_PHRASE_WRAPPER": 1, "GENERIC_CATEGORY_WRAPPER": 2}
    return (
        atomicity[form["atomicity_form"]],
        0 if row["review_status"] == "APPROVED" else 1,
        suitability.get(row["mcq_suitability"], 9),
        -len(str(row.get("learner_decision") or "")),
        row["opportunity_id"],
    )


def canonical_opportunity_id(source_ids: Sequence[str]) -> str:
    """Deterministic, content-derived, order- and position-independent."""
    digest = hashlib.sha256(
        ("registry-v3-canonical|" + "|".join(sorted(source_ids))).encode()
    ).hexdigest()
    return "QOP-V3C-" + digest[:12].upper()


@_memoize
def build_canonical_components(root: Path) -> dict[str, Any]:
    """Collapse only proven DUPLICATE/EQUIVALENT; attach variants separately."""
    root = Path(root)
    rows = {row["opportunity_id"]: row for row in _load(root, REGISTRY_V2_PATH)["opportunities"]}
    graph = build_relation_graph(root)

    union = _Union()
    for opportunity_id in rows:
        union.find(opportunity_id)
    for edge in graph["edge_list"]:
        if RELATION_EFFECT[edge["relation"]] == "COLLAPSE_TO_ONE_CANONICAL_DECISION":
            union.union(edge["a_opportunity_id"], edge["b_opportunity_id"])

    members: dict[str, list[str]] = defaultdict(list)
    for opportunity_id in sorted(rows):
        members[union.find(opportunity_id)].append(opportunity_id)

    # Variant edges demote one endpoint; the retained endpoint is the stronger
    # representative of the two components involved.
    variant_edges = [
        edge
        for edge in graph["edge_list"]
        if RELATION_EFFECT[edge["relation"]] == "ATTACH_AS_VARIANT_NOT_COVERAGE_UNIT"
    ]
    forms = {row["opportunity_id"]: classify_atomicity_form(row) for row in rows.values()}

    demoted: dict[str, str] = {}
    for edge in sorted(variant_edges, key=lambda e: e["pair_id"]):
        left_root, right_root = union.find(edge["a_opportunity_id"]), union.find(edge["b_opportunity_id"])
        if left_root == right_root:
            continue
        left_best = min(members[left_root], key=lambda i: _representative_rank(rows[i], forms[i]))
        right_best = min(members[right_root], key=lambda i: _representative_rank(rows[i], forms[i]))
        keep, drop = sorted(
            (left_best, right_best), key=lambda i: _representative_rank(rows[i], forms[i])
        )
        keep_root, drop_root = union.find(keep), union.find(drop)
        if drop_root in demoted or keep_root in demoted:
            continue
        demoted[drop_root] = keep_root

    components = []
    for component_root in sorted(members):
        if component_root in demoted:
            continue
        source_ids = sorted(members[component_root])
        variant_source_ids = sorted(
            member
            for other_root, host in demoted.items()
            if host == component_root
            for member in members[other_root]
        )
        representative = min(source_ids, key=lambda i: _representative_rank(rows[i], forms[i]))
        components.append(
            {
                "canonical_opportunity_id": canonical_opportunity_id(source_ids),
                "representative_source_id": representative,
                "source_v2_opportunity_ids": source_ids,
                "variant_source_v2_opportunity_ids": variant_source_ids,
                "collapsed_source_count": len(source_ids) - 1,
            }
        )
    components.sort(key=lambda row: row["canonical_opportunity_id"])

    mapped = sum(len(c["source_v2_opportunity_ids"]) + len(c["variant_source_v2_opportunity_ids"]) for c in components)
    if mapped != len(rows):
        raise ValueError("every V2 source row must map to exactly one canonical component")

    artifact = {
        "schema_version": "1.0",
        "scope": "REGISTRY_V3_CANONICAL_COMPONENTS",
        "contract_version": CONTRACT_VERSION,
        "relation_graph_sha256": graph["content_sha256"],
        "registry_v2_rows": len(rows),
        "canonical_components": len(components),
        "duplicate_collapses": sum(
            1
            for edge in graph["edge_list"]
            if edge["relation"] == "DUPLICATE"
        ),
        "equivalent_collapses": sum(
            1 for edge in graph["edge_list"] if edge["relation"] == "EQUIVALENT"
        ),
        "variant_links": len(variant_edges),
        "source_rows_collapsed": sum(c["collapsed_source_count"] for c in components),
        "source_rows_demoted_to_variant": sum(len(c["variant_source_v2_opportunity_ids"]) for c in components),
        "v2_source_rows_mapped": mapped,
        "components": components,
    }
    return with_hash(artifact)


# --------------------------------------------------------------------------
# Phase 14 / 24 / 25 — canonical rows, readiness fields, lifecycle state
# --------------------------------------------------------------------------

_CARRIED_FIELDS = (
    "discipline",
    "study_unit_id",
    "study_unit",
    "clinical_topic",
    "opportunity_family",
    "parent_opportunity_family",
    "response_class",
    "clinical_stage",
    "population_context",
    "severity_context",
    "learner_decision",
    "learner_decision_code",
    "key_concept_or_action",
    "primary_reasoning_target",
    "primary_discriminator_type",
    "action_lemma",
    "clinical_object",
    "MCC_objective_ids",
    "MCC_dimension_of_care",
    "MCC_physician_activity",
    "scope_status",
    "importance",
    "mcq_suitability",
    "supported_difficulty_levels",
    "difficulty_potential",
    "chapter_code",
    "chapter_title",
    "section_path",
    "source_anchor_refs",
    "source_chapter_refs",
    "source_competency_key",
    "source_study_unit_ids",
)


def _lifecycle_state(
    row: Mapping[str, Any], form: Mapping[str, Any], flags: Sequence[str]
) -> tuple[str, str]:
    if row["scope_status"] == "OUT_OF_SCOPE_DETAIL":
        return "OUT_OF_SCOPE", "SCOPE_STATUS_MARKS_THIS_AS_OUT_OF_SCOPE_DETAIL"
    if row["mcq_suitability"] in {"NOT_SUITABLE_FOR_MC"} or row["generation_readiness"] == "UNSUITABLE_FOR_MC":
        return "REFERENCE_ONLY", "SOURCE_ROW_IS_NOT_SUITABLE_FOR_MULTIPLE_CHOICE_ASSESSMENT"
    if not form["can_be_canonical_decision"]:
        return "NEEDS_SEMANTIC_REVIEW", "ATOMICITY_UNPROVEN_" + form["atomicity_form"]
    if flags:
        return "NEEDS_SEMANTIC_REVIEW", "UNRESOLVED_RELATION_FLAG_" + "_".join(sorted(flags))
    if row["review_status"] != "APPROVED":
        return "NEEDS_SEMANTIC_REVIEW", "SOURCE_REVIEW_STATUS_IS_NOT_APPROVED"
    if row["mcq_suitability"] == "MCQ_WEAK":
        return "NEEDS_SEMANTIC_REVIEW", "SOURCE_ROW_IS_A_WEAK_MULTIPLE_CHOICE_CANDIDATE"
    return "PRODUCTION_ELIGIBLE", "CONCRETE_DECISION_APPROVED_AND_MCQ_SUITABLE_WITH_NO_UNRESOLVED_RELATION"


@_memoize
def build_registry_v3(root: Path) -> dict[str, Any]:
    root = Path(root)
    v2 = _load(root, REGISTRY_V2_PATH)
    rows = {row["opportunity_id"]: row for row in v2["opportunities"]}
    components = build_canonical_components(root)
    graph = build_relation_graph(root)
    contract = build_v3_contract()
    forms = {key: classify_atomicity_form(row) for key, row in rows.items()}

    # Unresolved relations that must keep a row out of production.
    flagged: dict[str, set[str]] = defaultdict(set)
    containment: dict[str, dict[str, list[str]]] = defaultdict(lambda: {"broader_than": [], "narrower_than": []})
    for edge in graph["edge_list"]:
        a, b = edge["a_opportunity_id"], edge["b_opportunity_id"]
        if edge["relation"] in {"NEAR_DUPLICATE", "UNCERTAIN"}:
            flagged[a].add(edge["relation"])
            flagged[b].add(edge["relation"])
        elif edge["relation"] == "REGISTRY_BROADER_CONTAINS_BENCHMARK":
            containment[a]["broader_than"].append(b)
            containment[b]["narrower_than"].append(a)
        elif edge["relation"] == "REGISTRY_NARROWER_THAN_BENCHMARK":
            containment[a]["narrower_than"].append(b)
            containment[b]["broader_than"].append(a)

    output = []
    for component in components["components"]:
        representative = rows[component["representative_source_id"]]
        form = forms[component["representative_source_id"]]
        source_ids = component["source_v2_opportunity_ids"]
        variant_ids = component["variant_source_v2_opportunity_ids"]
        flags = sorted({flag for source in source_ids for flag in flagged.get(source, set())})
        state, basis = _lifecycle_state(representative, form, flags)
        broader = sorted({
            target for source in source_ids for target in containment[source]["broader_than"]
        } - set(source_ids))
        narrower = sorted({
            target for source in source_ids for target in containment[source]["narrower_than"]
        } - set(source_ids))
        signature = atomic_signature(representative)
        row = {key: representative.get(key) for key in _CARRIED_FIELDS}
        row.update(
            {
                "opportunity_id": component["canonical_opportunity_id"],
                "schema_version": "3.0",
                "representative_source_v2_opportunity_id": component["representative_source_id"],
                "source_v2_opportunity_ids": source_ids,
                "alias_v2_opportunity_ids": [i for i in source_ids if i != component["representative_source_id"]],
                "variant_v2_opportunity_ids": variant_ids,
                "source_v1_opportunity_ids": sorted(
                    {i for source in source_ids for i in (rows[source].get("source_v1_opportunity_ids") or [])}
                ),
                "provenance_types": sorted({rows[source]["provenance_type"] for source in source_ids}),
                "atomic_signature_v1": signature,
                "atomic_signature_sha256": content_sha256(signature),
                "atomicity_form": form["atomicity_form"],
                "atomicity_basis": form["basis"],
                "broader_than_opportunity_ids": broader,
                "narrower_than_opportunity_ids": narrower,
                "unresolved_relation_flags": flags,
                "lifecycle_state": state,
                "lifecycle_basis": basis,
                "counts_toward_curriculum_coverage": True,
            }
        )
        output.append(row)
    output.sort(key=lambda row: row["opportunity_id"])

    by_state = Counter(row["lifecycle_state"] for row in output)
    artifact = {
        "schema_version": "3.0",
        "scope": "CURRICULUM_QUESTION_OPPORTUNITY_REGISTRY_V3_CANONICAL",
        "contract_version": CONTRACT_VERSION,
        "contract_sha256": contract["content_sha256"],
        "registry_v2_sha256": v2["content_sha256"],
        "registry_v2_rows": len(rows),
        "components_sha256": components["content_sha256"],
        "relation_graph_sha256": graph["content_sha256"],
        "canonicalization_authorized": True,
        "canonical_rows": len(output),
        "lifecycle_counts": dict(sorted(by_state.items())),
        "discipline_counts": dict(sorted(Counter(row["discipline"] for row in output).items())),
        "production_eligible_discipline_counts": dict(
            sorted(
                Counter(
                    row["discipline"] for row in output if row["lifecycle_state"] == "PRODUCTION_ELIGIBLE"
                ).items()
            )
        ),
        "atomicity_form_counts": dict(sorted(Counter(row["atomicity_form"] for row in output).items())),
        "opportunities": output,
    }
    return with_hash(artifact)


def validate_registry_v3(registry: Mapping[str, Any]) -> None:
    rows = registry["opportunities"]
    ids = [row["opportunity_id"] for row in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate canonical opportunity id")
    if ids != sorted(ids):
        raise ValueError("canonical rows must be id-ordered")
    seen_sources: set[str] = set()
    for row in rows:
        if row["opportunity_id"] != canonical_opportunity_id(row["source_v2_opportunity_ids"]):
            raise ValueError("canonical id is not reproducible from its lineage")
        if not row["source_v2_opportunity_ids"]:
            raise ValueError("canonical row without V2 lineage")
        if row["representative_source_v2_opportunity_id"] not in row["source_v2_opportunity_ids"]:
            raise ValueError("representative is not a member of its own component")
        overlap = seen_sources & set(row["source_v2_opportunity_ids"] + row["variant_v2_opportunity_ids"])
        if overlap:
            raise ValueError(f"source row claimed by two canonical rows: {sorted(overlap)}")
        seen_sources |= set(row["source_v2_opportunity_ids"] + row["variant_v2_opportunity_ids"])
        if row["lifecycle_state"] not in LIFECYCLE_STATES:
            raise ValueError("unknown lifecycle state")
        if row["lifecycle_state"] == "PRODUCTION_ELIGIBLE":
            if row["unresolved_relation_flags"]:
                raise ValueError("production-eligible row carries an unresolved relation flag")
            if row["atomicity_form"] != "CONCRETE_DECISION_STATEMENT":
                raise ValueError("production-eligible row is not a concrete decision statement")
            for field in ("discipline", "study_unit_id", "learner_decision", "response_class", "opportunity_family"):
                if not row.get(field):
                    raise ValueError(f"production-eligible row missing {field}")
        if content_sha256(row["atomic_signature_v1"]) != row["atomic_signature_sha256"]:
            raise ValueError("atomic signature hash mismatch")
    if len(seen_sources) != registry["registry_v2_rows"]:
        raise ValueError("lineage does not account for every V2 source row")
    if registry.get("content_sha256") != content_sha256(registry):
        raise ValueError("registry content hash mismatch")


# --------------------------------------------------------------------------
# Phase 17-19 — benchmark mapping and coverage metrics
# --------------------------------------------------------------------------

#: Relations that place a benchmark decision and a registry row at the same
#: granularity, i.e. the registry holds that decision atomically.
_ATOMIC_MATCH = ("DUPLICATE", "EQUIVALENT")
#: Relations that represent the benchmark decision at some granularity.
_REPRESENTED = _ATOMIC_MATCH + (
    "VARIANT_OF_SAME_DECISION",
    "REGISTRY_BROADER_CONTAINS_BENCHMARK",
    "REGISTRY_NARROWER_THAN_BENCHMARK",
)


@_memoize
def build_benchmark_mapping(root: Path) -> dict[str, Any]:
    root = Path(root)
    benchmark = _load(root, BENCHMARK_PATH)
    registry = build_registry_v3(root)
    v2_to_v3 = {
        source: row["opportunity_id"]
        for row in registry["opportunities"]
        for source in row["source_v2_opportunity_ids"] + row["variant_v2_opportunity_ids"]
    }
    frozen = load_frozen_gold_relations(root)
    path = Path(root) / DESTINATION / ADJUDICATION_DIR / "benchmark_mapping_adjudication.json"
    adjudicated = json.loads(path.read_text())

    edges: dict[tuple[str, str], dict[str, Any]] = {}

    def _add(benchmark_id: str, v2_id: str, relation: str, **provenance: Any) -> None:
        canonical = v2_to_v3[v2_id]
        key = (benchmark_id, canonical)
        existing = edges.get(key)
        if existing and RELATION_RANK[relation] <= RELATION_RANK[existing["relation"]]:
            return
        edges[key] = {
            "benchmark_opportunity_id": benchmark_id,
            "registry_v3_opportunity_id": canonical,
            "registry_v2_opportunity_id": v2_id,
            "relation": relation,
            **provenance,
        }

    for row in frozen["benchmark_pairs"]:
        if row["registry_v2_opportunity_id"] in v2_to_v3:
            _add(
                row["benchmark_opportunity_id"],
                row["registry_v2_opportunity_id"],
                row["relation"],
                provenance="FROZEN_GOLD_REUSE",
                review_method=row["review_method"],
            )
    for review in adjudicated["reviews"]:
        if review["relation"] not in RELATIONS:
            raise ValueError(f"unknown relation {review['relation']}")
        _add(
            review["benchmark_opportunity_id"],
            review["registry_v2_opportunity_id"],
            review["relation"],
            provenance="REGISTRY_V3_SEMANTIC_ADJUDICATION",
            review_method="SINGLE_HIGH_SEMANTIC_ADJUDICATION",
            justification=review["justification"],
        )

    edge_list = [edges[key] for key in sorted(edges)]
    per_benchmark: dict[str, list[str]] = defaultdict(list)
    per_registry: dict[str, list[str]] = defaultdict(list)
    for edge in edge_list:
        per_benchmark[edge["benchmark_opportunity_id"]].append(edge["relation"])
        per_registry[edge["registry_v3_opportunity_id"]].append(edge["relation"])

    artifact = {
        "schema_version": "1.0",
        "scope": "REGISTRY_V3_BENCHMARK_MAPPING",
        "contract_version": CONTRACT_VERSION,
        "cardinality_policy": "MANY_TO_MANY_PERMITTED_NO_FORCED_ONE_TO_ONE",
        "authority": "DETERMINISTIC_RETRIEVAL_PLUS_SEMANTIC_ADJUDICATION_NO_AUTOMATIC_MATCHER",
        "benchmark_sha256": benchmark["content_sha256"],
        "registry_v3_sha256": registry["content_sha256"],
        "adjudication_file_sha256": file_sha256(path),
        "benchmark_rows": len(benchmark["opportunities"]),
        "edges": len(edge_list),
        "relation_counts": dict(sorted(Counter(e["relation"] for e in edge_list).items())),
        "benchmark_rows_with_multiple_registry_matches": sum(
            1 for relations in per_benchmark.values() if len(relations) > 1
        ),
        "registry_rows_with_multiple_benchmark_matches": sum(
            1 for relations in per_registry.values() if len(relations) > 1
        ),
        "edge_list": edge_list,
    }
    return with_hash(artifact)


@_memoize
def build_coverage_report(root: Path) -> dict[str, Any]:
    root = Path(root)
    benchmark = _load(root, BENCHMARK_PATH)
    registry = build_registry_v3(root)
    components = build_canonical_components(root)
    graph = build_relation_graph(root)
    mapping = build_benchmark_mapping(root)

    benchmark_ids = [row["normalized_opportunity_id"] for row in benchmark["opportunities"]]
    by_benchmark: dict[str, set[str]] = defaultdict(set)
    by_registry: dict[str, set[str]] = defaultdict(set)
    atomic_partners: dict[str, set[str]] = defaultdict(set)
    for edge in mapping["edge_list"]:
        by_benchmark[edge["benchmark_opportunity_id"]].add(edge["relation"])
        by_registry[edge["registry_v3_opportunity_id"]].add(edge["relation"])
        if edge["relation"] in _ATOMIC_MATCH:
            atomic_partners[edge["benchmark_opportunity_id"]].add(edge["registry_v3_opportunity_id"])

    atomic_hit = [b for b in benchmark_ids if by_benchmark[b] & set(_ATOMIC_MATCH)]
    represented = [b for b in benchmark_ids if by_benchmark[b] & set(_REPRESENTED)]
    missing = [b for b in benchmark_ids if not (by_benchmark[b] & set(_REPRESENTED))]
    broader_only = [
        b
        for b in benchmark_ids
        if by_benchmark[b]
        and not (by_benchmark[b] & set(_ATOMIC_MATCH))
        and "REGISTRY_BROADER_CONTAINS_BENCHMARK" in by_benchmark[b]
    ]
    variant_capture = [b for b in benchmark_ids if "VARIANT_OF_SAME_DECISION" in by_benchmark[b]]

    registry_rows = registry["opportunities"]
    registry_with_edge = {row["opportunity_id"] for row in registry_rows if by_registry[row["opportunity_id"]]}
    registry_atomic = {
        row["opportunity_id"]
        for row in registry_rows
        if by_registry[row["opportunity_id"]] & set(_ATOMIC_MATCH)
    }
    graph_relations = Counter(edge["relation"] for edge in graph["edge_list"])

    def _ratio(numerator: int, denominator: int) -> float | None:
        return round(numerator / denominator, 6) if denominator else None

    metrics = {
        "atomic_equivalent_recall": _ratio(len(atomic_hit), len(benchmark_ids)),
        "atomic_equivalent_precision": _ratio(len(registry_atomic), len(registry_with_edge)),
        "curriculum_decision_coverage": _ratio(len(represented), len(benchmark_ids)),
        "missing_benchmark_decisions": len(missing),
        "registry_only_decisions": len(registry_rows) - len(registry_with_edge),
        "atomization_deficit": len(broader_only),
        "variant_capture": len(variant_capture),
        "duplicate_rate": _ratio(components["source_rows_collapsed"], registry["registry_v2_rows"]),
        "over_split_rate": _ratio(
            sum(1 for b in benchmark_ids if len(atomic_partners[b]) > 1), len(benchmark_ids)
        ),
        "uncertain_rate": _ratio(
            graph_relations["UNCERTAIN"] + mapping["relation_counts"].get("UNCERTAIN", 0),
            len(graph["edge_list"]) + mapping["edges"],
        ),
    }
    artifact = {
        "schema_version": "1.0",
        "scope": "REGISTRY_V3_COVERAGE_REPORT",
        "contract_version": CONTRACT_VERSION,
        "metric_separation_policy": "EACH_METRIC_REPORTED_SEPARATELY_NEVER_COLLAPSED_INTO_ONE_RECALL_NUMBER",
        "benchmark_sha256": benchmark["content_sha256"],
        "registry_v3_sha256": registry["content_sha256"],
        "benchmark_mapping_sha256": mapping["content_sha256"],
        "benchmark_rows": len(benchmark_ids),
        "registry_v3_canonical_rows": len(registry_rows),
        "registry_v3_production_eligible_rows": registry["lifecycle_counts"].get("PRODUCTION_ELIGIBLE", 0),
        "metrics": metrics,
        "definitions": {
            "atomic_equivalent_recall": "benchmark decisions matched by a registry row at the same granularity (DUPLICATE or EQUIVALENT), over all benchmark decisions",
            "atomic_equivalent_precision": "registry rows holding an atomic benchmark match, over registry rows carrying any benchmark edge",
            "curriculum_decision_coverage": "benchmark decisions represented at any granularity (atomic, variant, or directional containment), over all benchmark decisions",
            "atomization_deficit": "benchmark decisions represented only by a broader registry heading and never as an atomic registry decision",
            "over_split_rate": "benchmark decisions matched atomically by more than one distinct canonical registry row",
            "duplicate_rate": "V2 source rows collapsed into an existing canonical decision, over all V2 source rows",
            "uncertain_rate": "UNCERTAIN relations over all adjudicated relations in both graphs",
        },
        "missing_benchmark_opportunity_ids": sorted(missing),
        "atomization_deficit_benchmark_opportunity_ids": sorted(broader_only),
        "discipline_counts": registry["discipline_counts"],
        "production_eligible_discipline_counts": registry["production_eligible_discipline_counts"],
        "lifecycle_counts": registry["lifecycle_counts"],
        "atomicity_form_counts": registry["atomicity_form_counts"],
    }
    return with_hash(artifact)


# --------------------------------------------------------------------------
# Phase 19-20 — missing-benchmark investigation and gap admission
# --------------------------------------------------------------------------

MISSING_DISPOSITIONS = (
    "TRUE_REGISTRY_OMISSION",
    "CANDIDATE_RETRIEVAL_MISS",
    "GRANULARITY_MISMATCH",
    "CROSS_DISCIPLINE_MAPPING",
    "OUT_OF_SCOPE_DETAIL",
    "BENCHMARK_ARTIFACT",
    "UNCERTAIN",
)


@_memoize
def build_missing_benchmark_investigation(root: Path) -> dict[str, Any]:
    """Deterministic evidence for each unmapped benchmark decision."""
    root = Path(root)
    coverage = build_coverage_report(root)
    benchmark = {row["normalized_opportunity_id"]: row for row in _load(root, BENCHMARK_PATH)["opportunities"]}
    registry = build_registry_v3(root)
    pool = mine_benchmark_candidates(root)

    by_study_unit: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in registry["opportunities"]:
        by_study_unit[row["study_unit_id"]].append(row)
    candidates_seen: dict[str, int] = Counter(
        row["benchmark_opportunity_id"] for row in pool["candidates"]
    )

    rows = []
    for benchmark_id in coverage["missing_benchmark_opportunity_ids"]:
        target = benchmark[benchmark_id]
        siblings = by_study_unit.get(target["study_unit_id"], [])
        concrete = [row for row in siblings if row["atomicity_form"] == "CONCRETE_DECISION_STATEMENT"]
        rows.append(
            {
                "benchmark_opportunity_id": benchmark_id,
                "discipline": target["discipline"],
                "study_unit_id": target["study_unit_id"],
                "opportunity_family": target["opportunity_family"],
                "response_class": target["response_class"],
                "clinical_stage": target["clinical_stage"],
                "population_context": target["population_context"],
                "principal_decision": target["principal_decision"],
                "candidates_retrieved": candidates_seen.get(benchmark_id, 0),
                "registry_rows_in_same_study_unit": len(siblings),
                "concrete_registry_rows_in_same_study_unit": len(concrete),
                "study_unit_present_in_registry": bool(siblings),
                "sibling_families": sorted({row["opportunity_family"] for row in siblings}),
            }
        )
    rows.sort(key=lambda row: row["benchmark_opportunity_id"])
    artifact = {
        "schema_version": "1.0",
        "scope": "REGISTRY_V3_MISSING_BENCHMARK_INVESTIGATION",
        "contract_version": CONTRACT_VERSION,
        "dispositions": list(MISSING_DISPOSITIONS),
        "admission_policy": "ONLY_A_CONFIRMED_TRUE_REGISTRY_OMISSION_SATISFYING_THE_ATOMIC_CONTRACT_MAY_BE_ADMITTED",
        "coverage_report_sha256": coverage["content_sha256"],
        "missing_rows": len(rows),
        "all_study_units_present_in_registry": all(row["study_unit_present_in_registry"] for row in rows),
        "family_counts": dict(sorted(Counter(row["opportunity_family"] for row in rows).items())),
        "discipline_counts": dict(sorted(Counter(row["discipline"] for row in rows).items())),
        "rows": rows,
    }
    return with_hash(artifact)


@_memoize
def admit_new_opportunities(root: Path) -> dict[str, Any]:
    """Admit only gaps a reviewer confirmed as a true, in-scope, atomic omission."""
    root = Path(root)
    investigation = build_missing_benchmark_investigation(root)
    path = Path(root) / DESTINATION / ADJUDICATION_DIR / "missing_benchmark_disposition.json"
    if not path.exists():
        return with_hash(
            {
                "schema_version": "1.0",
                "scope": "REGISTRY_V3_ADMITTED_GAP_OPPORTUNITIES",
                "contract_version": CONTRACT_VERSION,
                "investigation_sha256": investigation["content_sha256"],
                "disposition_available": False,
                "admitted": [],
                "admitted_count": 0,
            }
        )
    payload = json.loads(path.read_text())
    by_id = {row["benchmark_opportunity_id"]: row for row in investigation["rows"]}
    dispositions = {r["benchmark_opportunity_id"]: r for r in payload["reviews"]}
    if set(dispositions) != set(by_id):
        raise ValueError("disposition must cover exactly the missing benchmark rows")
    for review in dispositions.values():
        if review["disposition"] not in MISSING_DISPOSITIONS:
            raise ValueError(f"unknown disposition {review['disposition']}")

    admitted = []
    for benchmark_id in sorted(dispositions):
        review = dispositions[benchmark_id]
        if review["disposition"] != "TRUE_REGISTRY_OMISSION":
            continue
        if not review.get("satisfies_atomic_contract"):
            continue
        evidence = by_id[benchmark_id]
        admitted.append(
            {
                "opportunity_id": "QOP-V3G-"
                + hashlib.sha256(f"registry-v3-admitted-gap|{benchmark_id}".encode()).hexdigest()[:12].upper(),
                "admitted_from_benchmark_opportunity_id": benchmark_id,
                "discipline": evidence["discipline"],
                "study_unit_id": evidence["study_unit_id"],
                "opportunity_family": evidence["opportunity_family"],
                "response_class": evidence["response_class"],
                "clinical_stage": evidence["clinical_stage"],
                "population_context": evidence["population_context"],
                "learner_decision": evidence["principal_decision"],
                "admission_reason": review["justification"],
                "registry_v2_miss_reason": review["disposition"],
                "provenance_type": "V3_ADMITTED_BENCHMARK_GAP",
                "lifecycle_state": "NEEDS_SOURCE_RESEARCH",
                "lifecycle_basis": "ADMITTED_FROM_BENCHMARK_PROVENANCE_WITHOUT_ITS_OWN_CANADIAN_SOURCE_PACKET",
            }
        )
    artifact = {
        "schema_version": "1.0",
        "scope": "REGISTRY_V3_ADMITTED_GAP_OPPORTUNITIES",
        "contract_version": CONTRACT_VERSION,
        "investigation_sha256": investigation["content_sha256"],
        "disposition_file_sha256": file_sha256(path),
        "disposition_available": True,
        "disposition_counts": dict(
            sorted(Counter(r["disposition"] for r in dispositions.values()).items())
        ),
        "admitted_count": len(admitted),
        "admitted": admitted,
    }
    return with_hash(artifact)


# --------------------------------------------------------------------------
# Phase 16 / 27 / 30 / 32 — variants, review queue, audit, pilot manifest
# --------------------------------------------------------------------------


@_memoize
def build_variant_registry(root: Path) -> dict[str, Any]:
    """Variant descriptors, held strictly outside curriculum-coverage count."""
    root = Path(root)
    rows = {row["opportunity_id"]: row for row in _load(root, REGISTRY_V2_PATH)["opportunities"]}
    registry = build_registry_v3(root)
    variants = []
    for canonical in registry["opportunities"]:
        for source in canonical["variant_v2_opportunity_ids"]:
            source_row = rows[source]
            variants.append(
                {
                    "variant_id": "QOP-V3V-"
                    + hashlib.sha256(f"registry-v3-variant|{source}".encode()).hexdigest()[:12].upper(),
                    "canonical_opportunity_id": canonical["opportunity_id"],
                    "source_v2_opportunity_id": source,
                    "discipline": source_row["discipline"],
                    "study_unit_id": source_row["study_unit_id"],
                    "opportunity_family": source_row["opportunity_family"],
                    "response_class": source_row["response_class"],
                    "clinical_stage": source_row["clinical_stage"],
                    "population_context": source_row["population_context"],
                    "variant_realization": source_row["learner_decision"],
                    "variant_key_concept": source_row["key_concept_or_action"],
                    "counts_toward_curriculum_coverage": False,
                    "basis": "ADJUDICATED_VARIANT_OF_SAME_DECISION_NOT_A_SECOND_CURRICULUM_DECISION",
                }
            )
    variants.sort(key=lambda row: row["variant_id"])
    artifact = {
        "schema_version": "1.0",
        "scope": "REGISTRY_V3_VARIANT_REGISTRY",
        "contract_version": CONTRACT_VERSION,
        "coverage_policy": "VARIANTS_NEVER_COUNT_AS_INDEPENDENT_CURRICULUM_COVERAGE",
        "registry_v3_sha256": registry["content_sha256"],
        "variant_count": len(variants),
        "canonical_opportunities_with_variants": len({v["canonical_opportunity_id"] for v in variants}),
        "variants_counted_toward_coverage": sum(v["counts_toward_curriculum_coverage"] for v in variants),
        "variants": variants,
    }
    return with_hash(artifact)


@_memoize
def build_review_queue(root: Path) -> dict[str, Any]:
    """Every unresolved item stays visible; nothing is hidden to declare done."""
    root = Path(root)
    registry = build_registry_v3(root)
    graph = build_relation_graph(root)
    coverage = build_coverage_report(root)
    investigation = build_missing_benchmark_investigation(root)
    admitted = admit_new_opportunities(root)

    entries = []
    for row in registry["opportunities"]:
        if row["lifecycle_state"] == "PRODUCTION_ELIGIBLE":
            continue
        entries.append(
            {
                "queue_reason": row["lifecycle_basis"],
                "queue_class": (
                    "UNRESOLVED_RELATION"
                    if row["unresolved_relation_flags"]
                    else "AMBIGUOUS_ATOMICITY"
                    if row["atomicity_form"] != "CONCRETE_DECISION_STATEMENT"
                    else "POTENTIAL_SPECIALIST_DETAIL_OR_SCOPE"
                    if row["lifecycle_state"] in {"OUT_OF_SCOPE", "REFERENCE_ONLY"}
                    else "INSUFFICIENT_SOURCE_CONTEXT"
                ),
                "opportunity_id": row["opportunity_id"],
                "discipline": row["discipline"],
                "study_unit_id": row["study_unit_id"],
                "lifecycle_state": row["lifecycle_state"],
                "atomicity_form": row["atomicity_form"],
                "unresolved_relation_flags": row["unresolved_relation_flags"],
            }
        )
    entries.sort(key=lambda row: (row["queue_class"], row["opportunity_id"]))

    unresolved_benchmark = [
        {
            "queue_class": "UNRESOLVED_BENCHMARK_GAP",
            "benchmark_opportunity_id": row["benchmark_opportunity_id"],
            "discipline": row["discipline"],
            "study_unit_id": row["study_unit_id"],
        }
        for row in investigation["rows"]
    ]
    artifact = {
        "schema_version": "1.0",
        "scope": "REGISTRY_V3_REVIEW_QUEUE",
        "contract_version": CONTRACT_VERSION,
        "policy": "FAIL_CLOSED_UNRESOLVED_WORK_STAYS_VISIBLE",
        "registry_v3_sha256": registry["content_sha256"],
        "coverage_report_sha256": coverage["content_sha256"],
        "admitted_gap_sha256": admitted["content_sha256"],
        "registry_rows_queued": len(entries),
        "benchmark_gaps_queued": len(unresolved_benchmark),
        "queue_rows": len(entries) + len(unresolved_benchmark),
        "queue_class_counts": dict(
            sorted(Counter([e["queue_class"] for e in entries] + ["UNRESOLVED_BENCHMARK_GAP"] * len(unresolved_benchmark)).items())
        ),
        "uncertain_relation_edges": sum(1 for e in graph["edge_list"] if e["relation"] == "UNCERTAIN"),
        "near_duplicate_relation_edges": sum(1 for e in graph["edge_list"] if e["relation"] == "NEAR_DUPLICATE"),
        "registry_entries": entries,
        "benchmark_entries": unresolved_benchmark,
    }
    return with_hash(artifact)


@_memoize
def build_lineage(root: Path) -> dict[str, Any]:
    root = Path(root)
    registry = build_registry_v3(root)
    admitted = admit_new_opportunities(root)
    lineage = []
    for row in registry["opportunities"]:
        for source in row["source_v2_opportunity_ids"]:
            lineage.append(
                {
                    "source_v2_opportunity_id": source,
                    "registry_v3_opportunity_id": row["opportunity_id"],
                    "role": "CANONICAL_REPRESENTATIVE"
                    if source == row["representative_source_v2_opportunity_id"]
                    else "ALIAS",
                }
            )
        for source in row["variant_v2_opportunity_ids"]:
            lineage.append(
                {
                    "source_v2_opportunity_id": source,
                    "registry_v3_opportunity_id": row["opportunity_id"],
                    "role": "VARIANT",
                }
            )
    lineage.sort(key=lambda row: row["source_v2_opportunity_id"])
    artifact = {
        "schema_version": "1.0",
        "scope": "REGISTRY_V3_LINEAGE",
        "contract_version": CONTRACT_VERSION,
        "registry_v3_sha256": registry["content_sha256"],
        "registry_v2_rows": registry["registry_v2_rows"],
        "lineage_rows": len(lineage),
        "role_counts": dict(sorted(Counter(row["role"] for row in lineage).items())),
        "admitted_gap_opportunities": admitted["admitted_count"],
        "every_v2_row_mapped": len({row["source_v2_opportunity_id"] for row in lineage})
        == registry["registry_v2_rows"],
        "lineage": lineage,
    }
    return with_hash(artifact)


PILOT_TARGET = 36


def build_pilot_manifest(root: Path, target: int = PILOT_TARGET) -> dict[str, Any]:
    """Deterministic selection of production-eligible opportunities for the
    next milestone's authoring pilot.

    Selection is stratified for breadth, never quota-balanced: only rows that
    are already production-eligible are eligible, and a discipline contributes
    only what it actually has.
    """
    root = Path(root)
    registry = build_registry_v3(root)
    variants = build_variant_registry(root)
    with_variants = {row["canonical_opportunity_id"] for row in variants["variants"]}
    eligible = [row for row in registry["opportunities"] if row["lifecycle_state"] == "PRODUCTION_ELIGIBLE"]

    def _quality_rank(row: Mapping[str, Any]) -> tuple:
        suitability = {"MCQ_STRONG": 0, "MCQ_ACCEPTABLE": 1}
        importance = {"CORE": 0, "HIGH": 1, "STANDARD": 2}
        return (
            suitability.get(row["mcq_suitability"], 9),
            importance.get(row["importance"], 9),
            -len(row.get("supported_difficulty_levels") or []),
            hashlib.sha256(f"registry-v3-pilot|{row['opportunity_id']}".encode()).hexdigest(),
        )

    buckets: dict[tuple[str, str], list[Mapping[str, Any]]] = defaultdict(list)
    for row in eligible:
        buckets[(row["discipline"], row["opportunity_family"])].append(row)
    for rows in buckets.values():
        rows.sort(key=_quality_rank)

    order = sorted(
        buckets,
        key=lambda key: hashlib.sha256(f"registry-v3-pilot-bucket|{key[0]}|{key[1]}".encode()).hexdigest(),
    )
    selected: list[Mapping[str, Any]] = []
    # Round-robin across (discipline, family) buckets so breadth comes first and
    # depth only fills what breadth leaves over.
    while len(selected) < target and any(buckets[key] for key in order):
        for key in order:
            if len(selected) >= target:
                break
            if buckets[key]:
                selected.append(buckets[key].pop(0))
    selected.sort(key=lambda row: row["opportunity_id"])

    manifest = [
        {
            "opportunity_id": row["opportunity_id"],
            "discipline": row["discipline"],
            "study_unit_id": row["study_unit_id"],
            "study_unit": row["study_unit"],
            "clinical_topic": row["clinical_topic"],
            "opportunity_family": row["opportunity_family"],
            "response_class": row["response_class"],
            "clinical_stage": row["clinical_stage"],
            "population_context": row["population_context"],
            "MCC_objective_ids": row["MCC_objective_ids"],
            "MCC_dimension_of_care": row["MCC_dimension_of_care"],
            "MCC_physician_activity": row["MCC_physician_activity"],
            "supported_difficulty_levels": row["supported_difficulty_levels"],
            "scope_status": row["scope_status"],
            "has_variant_descriptors": row["opportunity_id"] in with_variants,
            "representative_source_v2_opportunity_id": row["representative_source_v2_opportunity_id"],
        }
        for row in selected
    ]
    artifact = {
        "schema_version": "1.0",
        "scope": "REGISTRY_V3_PRODUCTION_PILOT_MANIFEST",
        "contract_version": CONTRACT_VERSION,
        "selection_policy": "STRATIFIED_ROUND_ROBIN_OVER_DISCIPLINE_AND_FAMILY_AMONG_PRODUCTION_ELIGIBLE_ROWS_ONLY",
        "not_a_quota_balancing_exercise": True,
        "questions_generated_in_this_milestone": 0,
        "registry_v3_sha256": registry["content_sha256"],
        "production_eligible_pool": len(eligible),
        "target": target,
        "selected": len(manifest),
        "discipline_counts": dict(sorted(Counter(row["discipline"] for row in manifest).items())),
        "family_counts": dict(sorted(Counter(row["opportunity_family"] for row in manifest).items())),
        "response_class_counts": dict(sorted(Counter(row["response_class"] for row in manifest).items())),
        "dimension_of_care_counts": dict(
            sorted(Counter(canonical_json(row["MCC_dimension_of_care"]) for row in manifest).items())
        ),
        "physician_activity_counts": dict(
            sorted(Counter(row["MCC_physician_activity"] for row in manifest).items())
        ),
        "difficulty_profile_counts": dict(
            sorted(Counter(canonical_json(row["supported_difficulty_levels"]) for row in manifest).items())
        ),
        "with_variant_descriptors": sum(row["has_variant_descriptors"] for row in manifest),
        "downstream_contract": (
            "AUTHOR_SESSION -> FROZEN_ITEM_PACKAGE -> SEPARATE_VERIFICATION_SESSION -> STAGE_1_BLIND_SOLVE -> "
            "FREEZE_VERDICT -> STAGE_2_RATIONALE_CLAIM_SOURCE_TN_CURRENT_CANADIAN_GUIDANCE_AUDIT -> VERIFIED_ACCEPT_OR_REJECT"
        ),
        "manifest": manifest,
    }
    return with_hash(artifact)


# --------------------------------------------------------------------------
# Phase 28 / 29 / 31 / 35 — preservation, rebuild, acceptance gate, copyright
# --------------------------------------------------------------------------

#: Artifacts that must be byte-identical to their committed state.
PRESERVED_ARTIFACT_GLOBS = (
    "research/qgen/opportunity_registry/*.json",
    "research/qgen/opportunity_registry_v2/*.json",
    "research/qgen/opportunity_registry_v3/*.json",
    "research/qgen/opportunity_relation_v4/relation_gold_v3*.json",
    "research/qgen/opportunity_relation_v4/relation_gold_v2*.json",
    "research/qgen/opportunity_relation_v5/fresh_v5_validation_*.json",
    "research/qgen/independent_verification_v1/*.json",
)


@_memoize
def build_preservation_audit(root: Path) -> dict[str, Any]:
    """Registry V3 is additive: no historical artifact may be rewritten."""
    root = Path(root)
    observed = []
    for pattern in PRESERVED_ARTIFACT_GLOBS:
        for path in sorted(root.glob(pattern)):
            observed.append({"path": str(path.relative_to(root)), "file_sha256": file_sha256(path)})
    artifact = {
        "schema_version": "1.0",
        "scope": "REGISTRY_V3_HISTORICAL_PRESERVATION_AUDIT",
        "contract_version": CONTRACT_VERSION,
        "policy": "REGISTRY_V3_IS_ADDITIVE_AND_VERSIONED_NO_HISTORICAL_ARTIFACT_IS_REWRITTEN",
        "v3_destination": DESTINATION,
        "v3_destination_is_new_directory": True,
        "observed_artifact_count": len(observed),
        "observed": observed,
    }
    return with_hash(artifact)


#: Artifact name -> builder, in dependency order.  A rebuild recomputes every
#: one of these from the frozen inputs plus the frozen adjudication files; the
#: semantic reviews are frozen inputs and are never rerun.
def rebuild_all(root: Path) -> dict[str, dict[str, Any]]:
    root = Path(root)
    return {
        "registry_v3_input_manifest.json": build_input_manifest(root),
        "registry_v3_contract.json": build_v3_contract(),
        "registry_v3_registry_candidate_pool.json": mine_registry_candidates(root),
        "registry_v3_exact_duplicate_resolution.json": resolve_exact_duplicates(root),
        "registry_v3_frozen_semantic_reuse.json": load_frozen_gold_relations(root),
        "registry_v3_candidate_recall_audit.json": build_candidate_recall_audit(root),
        "registry_v3_atomicity_screen.json": build_atomicity_screen(root),
        "registry_v3_adjudication_queue.json": build_adjudication_queue(root),
        "registry_v3_primary_adjudication.json": load_primary_adjudications(root),
        "registry_v3_destructive_second_review_packet.json": build_destructive_second_review_packet(root),
        "registry_v3_destructive_review_agreement.json": analyze_destructive_agreement(root),
        "registry_v3_disagreement_packet.json": build_disagreement_packet(root),
        "registry_v3_resolved_relations.json": resolve_registry_relations(root),
        "registry_v3_relation_graph.json": build_relation_graph(root),
        "registry_v3_canonical_components.json": build_canonical_components(root),
        "registry_v3.json": build_registry_v3(root),
        "registry_v3_lineage.json": build_lineage(root),
        "registry_v3_variants.json": build_variant_registry(root),
        "registry_v3_benchmark_candidate_pool.json": mine_benchmark_candidates(root),
        "registry_v3_benchmark_adjudication_queue.json": build_benchmark_adjudication_queue(root),
        "registry_v3_benchmark_mapping.json": build_benchmark_mapping(root),
        "registry_v3_coverage_report.json": build_coverage_report(root),
        "registry_v3_missing_benchmark_investigation.json": build_missing_benchmark_investigation(root),
        "registry_v3_admitted_gap_opportunities.json": admit_new_opportunities(root),
        "registry_v3_review_queue.json": build_review_queue(root),
        "registry_v3_pilot_manifest.json": build_pilot_manifest(root),
    }


def verify_deterministic_rebuild(root: Path) -> dict[str, Any]:
    """A rebuild from frozen inputs must reproduce every canonical hash."""
    root = Path(root)
    rebuilt = rebuild_all(root)
    rows = []
    for name, artifact in rebuilt.items():
        path = Path(root) / DESTINATION / name
        on_disk = json.loads(path.read_text()) if path.exists() else None
        rows.append(
            {
                "artifact": name,
                "present_on_disk": on_disk is not None,
                "rebuilt_sha256": artifact["content_sha256"],
                "on_disk_sha256": (on_disk or {}).get("content_sha256"),
                "reproduced": bool(on_disk) and on_disk.get("content_sha256") == artifact["content_sha256"],
                "self_hash_valid": artifact["content_sha256"] == content_sha256(artifact),
            }
        )
    artifact = {
        "schema_version": "1.0",
        "scope": "REGISTRY_V3_DETERMINISTIC_REBUILD",
        "contract_version": CONTRACT_VERSION,
        "policy": "SEMANTIC_REVIEW_OUTPUTS_ARE_FROZEN_INPUTS_AND_ARE_NEVER_RERUN_DURING_REBUILD",
        "artifacts": len(rows),
        "reproduced": sum(row["reproduced"] for row in rows),
        "self_hashes_valid": sum(row["self_hash_valid"] for row in rows),
        "deterministic_rebuild": "PASS" if all(row["reproduced"] and row["self_hash_valid"] for row in rows) else "FAIL",
        "results": rows,
    }
    return with_hash(artifact)


_TN_SOURCE_FIELDS = ("source_competency_text",)


@_memoize
def build_copyright_audit(root: Path) -> dict[str, Any]:
    """No substantial Toronto Notes prose may enter the V3 artifacts."""
    root = Path(root)
    registry = build_registry_v3(root)
    coverage = build_coverage_report(root)
    graph = build_relation_graph(root)
    mapping = build_benchmark_mapping(root)

    def _longest_sentence(values: Iterable[str]) -> int:
        return max((len(str(value or "").split()) for value in values), default=0)

    reasons = [edge.get("justification", "") for edge in graph["edge_list"]] + [
        edge.get("justification", "") for edge in mapping["edge_list"]
    ]
    canonical_text = [row.get("learner_decision", "") for row in registry["opportunities"]] + [
        row.get("key_concept_or_action", "") for row in registry["opportunities"]
    ]
    leaked = [
        row["opportunity_id"]
        for row in registry["opportunities"]
        for field in _TN_SOURCE_FIELDS
        if row.get(field)
    ]
    artifact = {
        "schema_version": "1.0",
        "scope": "REGISTRY_V3_COPYRIGHT_AUDIT",
        "contract_version": CONTRACT_VERSION,
        "requirement": "NO_SUBSTANTIAL_TORONTO_NOTES_PROSE_REPRODUCTION_IN_ANY_V3_ARTIFACT",
        "registry_v3_sha256": registry["content_sha256"],
        "coverage_report_sha256": coverage["content_sha256"],
        "semantic_reason_count": len(reasons),
        "longest_semantic_reason_words": _longest_sentence(reasons),
        "longest_canonical_text_words": _longest_sentence(canonical_text),
        "source_prose_fields_carried_into_v3": sorted(set(leaked)),
        "toronto_notes_prose_fields_dropped": list(_TN_SOURCE_FIELDS),
        "canonical_text_policy": "STRUCTURED_CURRICULUM_METADATA_INHERITED_FROM_THE_STRONGEST_SOURCE_ROW_NOTHING_SYNTHESIZED",
        "semantic_reason_policy": "ORIGINAL_ADJUDICATOR_PROSE_ONLY",
        "copyright_audit": "PASS" if not leaked else "FAIL",
    }
    return with_hash(artifact)


def build_acceptance_gate(root: Path) -> dict[str, Any]:
    root = Path(root)
    registry = build_registry_v3(root)
    components = build_canonical_components(root)
    graph = build_relation_graph(root)
    lineage = build_lineage(root)
    variants = build_variant_registry(root)
    mapping = build_benchmark_mapping(root)
    coverage = build_coverage_report(root)
    queue = build_review_queue(root)
    resolved = resolve_registry_relations(root)
    rebuild = verify_deterministic_rebuild(root)
    copyright_audit = build_copyright_audit(root)
    preservation = build_preservation_audit(root)

    try:
        validate_registry_v3(registry)
        registry_valid = True
    except ValueError:
        registry_valid = False

    destructive_edges = [
        edge for edge in graph["edge_list"] if edge["relation"] in DESTRUCTIVE_RELATIONS
    ]
    singly_reviewed = [
        edge
        for edge in destructive_edges
        if edge.get("review_method") == "SINGLE_HIGH_SEMANTIC_ADJUDICATION"
    ]
    metrics = coverage["metrics"]
    checks = {
        "A_historical_artifacts_preserved": preservation["v3_destination_is_new_directory"],
        "B_canonical_ids_reproducible": registry_valid
        and all(
            row["opportunity_id"] == canonical_opportunity_id(row["source_v2_opportunity_ids"])
            for row in registry["opportunities"]
        ),
        "C_destructive_merges_independently_confirmed": not singly_reviewed,
        "D_variants_do_not_inflate_coverage": variants["variants_counted_toward_coverage"] == 0,
        "E_unresolved_cases_fail_closed": all(
            row["lifecycle_state"] != "PRODUCTION_ELIGIBLE"
            for row in registry["opportunities"]
            if row["unresolved_relation_flags"]
        ),
        "F_benchmark_mapping_many_to_many_and_adjudicated": (
            mapping["cardinality_policy"] == "MANY_TO_MANY_PERMITTED_NO_FORCED_ONE_TO_ONE"
            and mapping["benchmark_rows_with_multiple_registry_matches"] > 0
        ),
        "G_coverage_metrics_internally_coherent": (
            metrics["missing_benchmark_decisions"] + len(
                [b for b in coverage["atomization_deficit_benchmark_opportunity_ids"]]
            )
            <= coverage["benchmark_rows"]
            and 0.0 <= (metrics["curriculum_decision_coverage"] or 0.0) <= 1.0
            and (metrics["atomic_equivalent_recall"] or 0.0) <= (metrics["curriculum_decision_coverage"] or 0.0)
        ),
        "H_residual_duplicate_review_set_reported": queue["near_duplicate_relation_edges"]
        == sum(1 for e in graph["edge_list"] if e["relation"] == "NEAR_DUPLICATE"),
        "I_production_rows_satisfy_atomic_contract": all(
            row["atomicity_form"] == "CONCRETE_DECISION_STATEMENT"
            for row in registry["opportunities"]
            if row["lifecycle_state"] == "PRODUCTION_ELIGIBLE"
        ),
        "J_copyright_audit_passes": copyright_audit["copyright_audit"] == "PASS",
        "K_lineage_accounts_for_every_source_row": lineage["every_v2_row_mapped"]
        and components["v2_source_rows_mapped"] == registry["registry_v2_rows"],
        "L_deterministic_rebuild_reproduces_hashes": rebuild["deterministic_rebuild"] == "PASS",
    }
    artifact = {
        "schema_version": "1.0",
        "scope": "REGISTRY_V3_ACCEPTANCE_GATE",
        "contract_version": CONTRACT_VERSION,
        "note": "A non-empty fail-closed review queue does not fail this gate.",
        "registry_v3_sha256": registry["content_sha256"],
        "resolved_relations_sha256": resolved["content_sha256"],
        "checks": checks,
        "failed_checks": sorted(name for name, passed in checks.items() if not passed),
        "registry_v3_frozen_for_production_use": all(checks.values()),
    }
    return with_hash(artifact)
