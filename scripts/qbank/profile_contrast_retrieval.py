"""Profile-aware retrieval over the curated contrast library, which is not rebuilt.

R4's one clear positive result was that competitor supply is solved: every target
cleared three independently approved competitors and no target failed closed for
want of seeds. What was missing was a way to ask whether an approved seed is a
competitor *for this realized stem*. That question is answered here, from the
seed field that already refutes six of the eight R4 defective distractors and was
never joined against anything.

Enrichment is additive and frozen separately from the pack. The generator may not
author the predicates for a seed it is about to use; if it could, the whole stage
collapses back into self-certification.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .errors import QbankError
from .option_set_admissibility import normalize_option_text
from .paths import resolve_root_path


class ContrastRetrievalError(QbankError):
    """A seed pack, its enrichment, or a retrieval request is unusable."""


RETRIEVAL_INDEX_FIELDS = (
    "discipline_profile_id",
    "item_archetype",
    "option_set_archetype",
    "learner_decision_id",
    "decision_granularity",
)

MINIMUM_ADMISSIBLE_COMPETITORS = 3


def load_seed_enrichment(root: Path, enrichment_relative_path: str) -> dict[str, Any]:
    """Load the frozen, additive enrichment tags for a curated seed pack."""
    path = resolve_root_path(Path(root).resolve(), enrichment_relative_path)
    if not path.is_file():
        raise ContrastRetrievalError(f"seed enrichment is unavailable: {enrichment_relative_path}")
    document = json.loads(path.read_text())
    if not document.get("frozen"):
        raise ContrastRetrievalError("seed enrichment must be frozen before use")
    seeds = document.get("seeds")
    if not isinstance(seeds, list) or not seeds:
        raise ContrastRetrievalError("seed enrichment carries no seeds")
    resolved: dict[str, dict[str, Any]] = {}
    for seed in seeds:
        seed_id = seed.get("seed_id")
        if not isinstance(seed_id, str) or not seed_id:
            raise ContrastRetrievalError("enrichment entry needs a seed id")
        if seed_id in resolved:
            raise ContrastRetrievalError(f"duplicate enrichment entry: {seed_id}")
        predicates = seed.get("condition_predicates")
        if not isinstance(predicates, list):
            raise ContrastRetrievalError(f"seed {seed_id} needs condition predicates")
        for predicate in predicates:
            if not isinstance(predicate, dict) or not isinstance(
                predicate.get("required_polarity"), str
            ):
                raise ContrastRetrievalError(
                    f"seed {seed_id} carries a malformed condition predicate"
                )
        resolved[seed_id] = seed
    return {"enrichment_id": document.get("enrichment_id"), "seeds": resolved}


def build_retrieval_index(
    seed_pack: dict[str, Any], enrichment: dict[str, Any]
) -> list[dict[str, Any]]:
    """Build the deterministic retrieval index over curated seeds.

    Retrieval is an index lookup, not a similarity search. Generic medical
    similarity is exactly what admitted the R4 defective distractors, so it is
    not a qualifying signal anywhere in this module.
    """
    rows: list[dict[str, Any]] = []
    for target in seed_pack.get("targets", []):
        for seed in target.get("seeds", []):
            seed_id = seed.get("seed_id")
            tags = enrichment["seeds"].get(seed_id)
            if tags is None:
                continue
            rows.append({
                "seed_id": seed_id,
                "target_id": target.get("target_id"),
                "competitor_concept": seed.get("competitor_concept"),
                "competitor_concept_id": seed.get("competitor_concept_id"),
                "competitor_study_unit_id": seed.get("competitor_study_unit_id"),
                "normalized_competitor_text": normalize_option_text(
                    seed.get("competitor_concept", "")
                ),
                "conditions_under_which_competitor_would_be_correct": seed.get(
                    "conditions_under_which_competitor_would_be_correct"
                ),
                "condition_predicates": tags["condition_predicates"],
                "response_class_tokens": tags.get("response_class_tokens", []),
                "nominal_axis_values": tags.get("nominal_axis_values", {}),
                "applicable_disciplines": tags.get("applicable_disciplines", []),
                "applicable_item_archetypes": tags.get("applicable_item_archetypes", []),
                "option_set_archetypes": tags.get("option_set_archetypes", []),
                "decision_granularity": seed.get("competitor_decision_granularity"),
                "shared_features_with_key": seed.get("shared_features_with_key", []),
                "reviewed_strength": (seed.get("independent_seed_review") or {}).get(
                    "reviewed_strength"
                ),
            })
    return sorted(rows, key=lambda row: row["seed_id"])


def _satisfied_predicate_count(
    predicates: list[dict[str, Any]], stem_features: dict[str, dict[str, Any]]
) -> tuple[int, int]:
    """Return (satisfied, total) for a competitor's correctness conditions."""
    satisfied = 0
    for predicate in predicates:
        feature = stem_features.get(predicate.get("stem_feature_id"))
        if feature is not None and feature.get("polarity") == predicate.get(
            "required_polarity"
        ):
            satisfied += 1
    return satisfied, len(predicates)


def retrieve_profile_aware_contrasts(
    *,
    index: list[dict[str, Any]],
    discipline_profile_id: str,
    item_archetype: str,
    option_set_archetype: str,
    demanded_response_class: str,
    token_implications: dict[str, list[str]],
    generic_token: str,
    stem_feature_map: dict[str, Any],
    ranking_preference: list[str],
) -> dict[str, Any]:
    """Retrieve, filter and rank competitors for one realized scenario."""
    from .option_set_admissibility import expand_response_tokens

    features = {
        feature["feature_id"]: feature
        for feature in (stem_feature_map.get("features") or [])
        if isinstance(feature, dict) and isinstance(feature.get("feature_id"), str)
    }
    indexed = [
        row
        for row in index
        if discipline_profile_id in row["applicable_disciplines"]
        and item_archetype in row["applicable_item_archetypes"]
        and option_set_archetype in row["option_set_archetypes"]
    ]
    admissible: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    for row in indexed:
        closure = expand_response_tokens(
            row["response_class_tokens"], token_implications, generic_token
        )
        if demanded_response_class not in closure:
            excluded.append({
                "seed_id": row["seed_id"],
                "rule": "ADM_1",
                "reason": "RESPONSE_CLASS_NOT_DEMANDED",
            })
            continue
        satisfied, total = _satisfied_predicate_count(row["condition_predicates"], features)
        if total and satisfied == total:
            # Every condition under which this competitor would be correct is
            # satisfied by the stem: it is not a distractor, it is a second key.
            excluded.append({
                "seed_id": row["seed_id"],
                "rule": "ADM_3",
                "reason": "CORRECTNESS_CONDITION_FULLY_SATISFIED",
            })
            continue
        admissible.append({
            **row,
            "satisfied_conditions": satisfied,
            "total_conditions": total,
        })

    signals = list(ranking_preference)

    def sort_key(row: dict[str, Any]) -> tuple:
        parts: list[Any] = []
        for signal in signals:
            if signal == "NEAREST_UNSATISFIED_CORRECTNESS_CONDITION":
                parts.append(-row["satisfied_conditions"])
            elif signal == "SHARED_FEATURE_COUNT":
                parts.append(-len(row["shared_features_with_key"]))
            elif signal == "REVIEWED_SEED_STRENGTH":
                parts.append(0 if row["reviewed_strength"] == "STRONG" else 1)
        parts.append(row["seed_id"])
        return tuple(parts)

    ranked = sorted(admissible, key=sort_key)
    fail_closed = (
        "FAIL_CLOSED_INSUFFICIENT_ADMISSIBLE_COMPETITORS"
        if len(ranked) < MINIMUM_ADMISSIBLE_COMPETITORS
        else None
    )
    return {
        "indexed_count": len(indexed),
        "admissible_count": len(ranked),
        "ranked_competitors": ranked,
        "excluded": sorted(excluded, key=lambda row: (row["rule"], row["seed_id"])),
        "fail_closed_reason": fail_closed,
    }
