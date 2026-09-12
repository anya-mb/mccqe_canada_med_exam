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


def load_seed_stem_anchors(root: Path, anchors_relative_path: str) -> dict[str, Any]:
    """Load the frozen, additive stem-plausibility anchors for a curated seed pack.

    An anchor is a stem datum whose presence gives a candidate a positive reason
    to *consider* this competitor, which is a different relation from the
    conditions under which it would be *correct*. Keeping the two apart is the
    whole point: the correctness conditions carry the anti-second-key ceiling and
    cannot also carry the floor, because in the frozen G2 cohort every competitor
    of every accepted item has the same correctness signature as every competitor
    of the anchorless rejections.
    """
    path = resolve_root_path(Path(root).resolve(), anchors_relative_path)
    if not path.is_file():
        raise ContrastRetrievalError(f"seed stem anchors are unavailable: {anchors_relative_path}")
    document = json.loads(path.read_text())
    if not document.get("frozen"):
        raise ContrastRetrievalError("seed stem anchors must be frozen before use")
    seeds = document.get("seeds")
    if not isinstance(seeds, list):
        raise ContrastRetrievalError("seed stem anchors carry no seeds")
    resolved: dict[str, list[str]] = {}
    for seed in seeds:
        seed_id = seed.get("seed_id")
        if not isinstance(seed_id, str) or not seed_id:
            raise ContrastRetrievalError("stem-anchor entry needs a seed id")
        if seed_id in resolved:
            raise ContrastRetrievalError(f"duplicate stem-anchor entry: {seed_id}")
        anchors = seed.get("plausibility_anchors")
        if not isinstance(anchors, list):
            raise ContrastRetrievalError(f"seed {seed_id} needs a plausibility anchor list")
        feature_ids: list[str] = []
        for anchor in anchors:
            if not isinstance(anchor, dict) or not isinstance(
                anchor.get("stem_feature_id"), str
            ):
                raise ContrastRetrievalError(f"seed {seed_id} carries a malformed anchor")
            feature_ids.append(anchor["stem_feature_id"])
        resolved[seed_id] = sorted(set(feature_ids))
    return {"anchors_pack_id": document.get("anchors_pack_id"), "seeds": resolved}


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
    seed_pack: dict[str, Any],
    enrichment: dict[str, Any],
    stem_anchors: dict[str, Any],
    *,
    feature_anchor_snapshot: dict[str, Any] | None = None,
    feature_anchor_scope: str | None = None,
    approved_additional_packs: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Build the deterministic retrieval index over curated seeds.

    Retrieval is an index lookup, not a similarity search. Generic medical
    similarity is exactly what admitted the R4 defective distractors, so it is
    not a qualifying signal anywhere in this module.

    ``feature_anchor_snapshot`` is the one seam the registry milestone adds, and
    it defaults to ``None`` on purpose. Without a pin this function is what it
    always was and reads the frozen stem-anchor pack, which is what keeps
    retrieval benchmark arm A and every historical replay bit-for-bit unchanged.
    With a pin, ``SAF_1``'s anchors come from that snapshot instead, so an
    independently approved anchor relation is visible to the production gate for
    the first time. `SAF_1`'s rule is not touched by either path.
    """
    from .feature_anchor_registry import require_snapshot, resolve_seed_anchors

    snapshot = require_snapshot(feature_anchor_snapshot)
    rows: list[dict[str, Any]] = []
    for target in seed_pack.get("targets", []):
        for seed in target.get("seeds", []):
            seed_id = seed.get("seed_id")
            tags = enrichment["seeds"].get(seed_id)
            if tags is None:
                continue
            if seed_id not in stem_anchors["seeds"]:
                raise ContrastRetrievalError(
                    f"seed {seed_id} is retrievable but carries no stem-plausibility "
                    "anchor row, so the anchor floor could not be applied to it"
                )
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
                "plausibility_anchor_feature_ids": (
                    stem_anchors["seeds"][seed_id] if snapshot is None
                    else resolve_seed_anchors(snapshot, seed_id, scope=feature_anchor_scope)
                ),
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
            if snapshot is not None:
                # Added only on the pinned path. An unpinned index must stay
                # byte-identical, because frozen reports serialize these rows.
                rows[-1]["feature_anchor_snapshot_id"] = snapshot["snapshot_id"]
    if approved_additional_packs:
        from .seed_pack_onboarding import approved_seed_scope

        seen = {row["seed_id"] for row in rows}
        for bundle in approved_additional_packs:
            additional_pack = bundle.get("seed_pack")
            if not isinstance(additional_pack, dict):
                raise ContrastRetrievalError("additional seed bundle needs a seed_pack")
            scopes = approved_seed_scope(additional_pack)
            filtered_pack = {
                **additional_pack,
                "targets": [
                    {
                        **target,
                        "seeds": [
                            seed for seed in target.get("seeds", [])
                            if seed.get("seed_id") in scopes
                        ],
                    }
                    for target in additional_pack["targets"]
                ],
            }
            new_rows = build_retrieval_index(
                filtered_pack,
                bundle.get("enrichment") or {},
                bundle.get("stem_anchors") or {},
                feature_anchor_snapshot=feature_anchor_snapshot,
                feature_anchor_scope=feature_anchor_scope,
            )
            for row in new_rows:
                if row["seed_id"] in seen:
                    raise ContrastRetrievalError(
                        f"seed appears in more than one explicit pack: {row['seed_id']}"
                    )
                seen.add(row["seed_id"])
                rows.append({**row, **scopes[row["seed_id"]]})
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


def _retrieval_scope_matches(
    row: dict[str, Any],
    *,
    learner_decision_id: str | None,
    anchor_study_unit_id: str | None,
) -> bool:
    """Apply an onboarding row's reviewed scope; historical rows are unchanged."""
    scope = row.get("retrieval_scope")
    if scope is None:
        return True
    # A caller that omits context cannot safely consume a scoped new seed.
    if learner_decision_id is None or anchor_study_unit_id is None:
        return False
    learner_decisions = scope.get("learner_decision_ids") or []
    study_units = scope.get("study_unit_ids") or []
    return (
        learner_decision_id in learner_decisions
        and anchor_study_unit_id in study_units
    )


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
    learner_decision_id: str | None = None,
    anchor_study_unit_id: str | None = None,
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
        and _retrieval_scope_matches(
            row,
            learner_decision_id=learner_decision_id,
            anchor_study_unit_id=anchor_study_unit_id,
        )
    ]
    admissible: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    anchor_refused_texts: list[str] = []
    anchor_zero = 0
    anchor_positive = 0
    anchor_fully_satisfied = 0
    for row in indexed:
        if "plausibility_anchor_feature_ids" not in row:
            raise ContrastRetrievalError(
                f"seed {row['seed_id']} carries no stem-plausibility anchors, so the "
                "anchor floor cannot be applied; rebuild the index with the anchor layer"
            )
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
        anchors = row["plausibility_anchor_feature_ids"]
        anchors_present = sum(
            1
            for feature_id in anchors
            if (features.get(feature_id) or {}).get("polarity") == "PRESENT"
        )
        if anchors_present:
            anchor_positive += 1
        else:
            anchor_zero += 1
        if anchors and anchors_present == len(anchors):
            anchor_fully_satisfied += 1
        if not anchors_present:
            # The symmetric floor. Nothing the stem states gives a candidate a
            # reason to consider this competitor, so whatever else is true of it
            # it is not a live alternative in this scenario. The ceiling above
            # stays exactly as it was: a competitor can clear the floor and still
            # be refused as a second key.
            excluded.append({
                "seed_id": row["seed_id"],
                "rule": "SAF_1",
                "reason": "STEM_PLAUSIBILITY_ANCHOR_ABSENT",
            })
            anchor_refused_texts.append(row["normalized_competitor_text"])
            continue
        admissible.append({
            **row,
            "satisfied_conditions": satisfied,
            "total_conditions": total,
            "anchors_present": anchors_present,
            "total_anchors": len(anchors),
        })

    signals = list(ranking_preference)

    def sort_key(row: dict[str, Any]) -> tuple:
        parts: list[Any] = []
        for signal in signals:
            if signal == "NEAREST_UNSATISFIED_CORRECTNESS_CONDITION":
                parts.append(-row["satisfied_conditions"])
            elif signal == "STEM_ANCHOR_STRENGTH":
                parts.append(-row["anchors_present"])
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
        # Reported whatever the outcome. A constant signal is what let the old
        # ranking collapse to seed strength and then to alphabetical seed id.
        "anchor_signal": {
            "zero": anchor_zero,
            "positive": anchor_positive,
            "fully_satisfied": anchor_fully_satisfied,
            "distinct_values": len({row["anchors_present"] for row in ranked}),
        },
        "anchor_floor_refusals": sorted(
            row["seed_id"] for row in excluded if row["rule"] == "SAF_1"
        ),
        "anchor_floor_refused_texts": sorted(set(anchor_refused_texts)),
    }
