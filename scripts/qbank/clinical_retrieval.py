"""Hybrid clinical contrast retrieval: BM25, typed graph, and their union.

The single most important property of this module is what it does *not* contain.
There is no second copy of the stem-anchor floor and no second copy of the ADM-3
second-key ceiling. Every arm's job ends at building candidate rows; the rows are
then handed to the same ``retrieve_profile_aware_contrasts`` the production wave
calls, so all four arms run the identical, already-validated safety code. A
reimplementation, however careful, would be free to drift, and the floor took a
diagnosis and a controlled retest to get right.

Arm A is the current curated library, unmodified, and is the benchmark reference.
Arms B, C and D may only change *which rows enter the index*, never what the
filters do with them.
"""

from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path
from typing import Any, Sequence

from .errors import QbankError
from .option_set_admissibility import (
    ARCHETYPE_RESPONSE_AXIS,
    RESPONSE_CLASS_AXES,
    normalize_option_text,
)
from .paths import resolve_root_path
from .profile_contrast_retrieval import (
    build_retrieval_index,
    load_seed_enrichment,
    load_seed_stem_anchors,
    retrieve_profile_aware_contrasts,
)


class ClinicalRetrievalError(QbankError):
    """A retrieval request, arm, or scenario is unusable."""


ARMS = ("CURRENT_LIBRARY", "BM25", "GRAPH", "HYBRID")

SEED_PACKS = (
    "research/qgen/generalization/competitive_contrast_seed_pack_r4",
    "research/qgen/generalization/competitive_contrast_seed_pack_g2_targeted",
    "research/qgen/generalization/competitive_contrast_seed_pack_g2_extensions",
)
DEMANDED_CLASSES_RELATIVE_PATH = (
    "research/qgen/safe_yield/g2_demanded_response_classes.json"
)
PROFILE_RELATIVE_PATH = "research/qgen/profiles/{profile}.profile.json"

BM25_LIMIT = 60
GRAPH_MAX_DEPTH = 2
MAX_PACKET_COMPETITORS = 6

# Terms that carry no discriminating power in a medical term index. Kept short and
# explicit; an aggressive stop list would silently drop clinical words.
_STOPWORDS = frozenset({
    "a", "an", "and", "are", "as", "at", "be", "been", "but", "by", "for", "from",
    "has", "have", "in", "is", "it", "its", "of", "on", "or", "that", "the", "this",
    "to", "was", "were", "with", "not", "no", "any", "his", "her", "their", "which",
    "there", "than", "then", "when", "where", "who", "whom", "while", "during",
})
_WORD = re.compile(r"[a-z][a-z0-9-]{2,}")


def _load(root: Path, relative: str) -> Any:
    path = resolve_root_path(Path(root).resolve(), relative)
    if not path.is_file():
        raise ClinicalRetrievalError(f"canonical artifact is unavailable: {relative}")
    return json.loads(path.read_text())


# ------------------------------------------------------------------ queries


def build_query(scenario: dict[str, Any]) -> dict[str, Any]:
    """Build a deterministic text query from canonical opportunity data only.

    Built from the realized stem's PRESENT features and the anchor study unit, and
    from nothing else. In particular the key never enters the query: a retriever
    that is told the answer is not measuring retrieval.
    """
    features = scenario["stem_feature_map"].get("features") or []
    present = [
        feature for feature in features if feature.get("polarity") == "PRESENT"
    ]
    terms: list[str] = []
    for feature in present:
        for word in _WORD.findall((feature.get("feature_id") or "").lower().replace("-", " ")):
            if word not in _STOPWORDS and word not in {"sf"}:
                terms.append(word)
    for word in _WORD.findall((scenario.get("anchor_study_unit_id") or "").lower()):
        if word not in _STOPWORDS:
            terms.append(word)
    ordered = sorted(set(terms))
    return {
        "arm_input": "CANONICAL_OPPORTUNITY_ONLY",
        "anchor_study_unit_id": scenario.get("anchor_study_unit_id"),
        "learner_decision_id": scenario.get("learner_decision_id"),
        "item_archetype": scenario.get("item_archetype"),
        "option_set_archetype": scenario.get("option_set_archetype"),
        "present_feature_ids": [feature["feature_id"] for feature in present],
        "terms": ordered,
        "match_expression": " OR ".join(f'"{term}"' for term in ordered),
    }


# ------------------------------------------------------------- typed rows


def _load_typed_rows(root: Path) -> dict[str, dict[str, Any]]:
    """Every curated competitor row, keyed by concept id, in the arm-A row shape."""
    rows: dict[str, dict[str, Any]] = {}
    for base in SEED_PACKS:
        pack = _load(root, f"{base}.json")
        enrichment = load_seed_enrichment(root, f"{base}.enrichment.json")
        anchors = load_seed_stem_anchors(root, f"{base}.stem_anchors.json")
        for row in build_retrieval_index(pack, enrichment, anchors):
            row = {**row, "source_pack": f"{base}.json"}
            rows.setdefault(row["competitor_concept_id"], row)
    return rows


def build_current_library_index(
    root: Path,
    *,
    feature_anchor_snapshot: dict[str, Any] | None = None,
    feature_anchor_scope: str | None = None,
) -> list[dict[str, Any]]:
    """Arm A. The curated index exactly as the production wave builds it.

    Unpinned this is the benchmark arm and must not move. The pin exists so the
    same 30 frozen scenarios can be scored against a registry snapshot without a
    second implementation of the funnel.
    """
    index: list[dict[str, Any]] = []
    for base in SEED_PACKS:
        pack = _load(root, f"{base}.json")
        enrichment = load_seed_enrichment(root, f"{base}.enrichment.json")
        anchors = load_seed_stem_anchors(root, f"{base}.stem_anchors.json")
        for row in build_retrieval_index(
            pack, enrichment, anchors,
            feature_anchor_snapshot=feature_anchor_snapshot,
            feature_anchor_scope=feature_anchor_scope,
        ):
            index.append({**row, "source_pack": f"{base}.json"})
    return sorted(index, key=lambda row: row["seed_id"])


def _untyped_row(concept_id: str, label: str, provenance: dict[str, Any]) -> dict[str, Any]:
    """A concept an arm genuinely discovered but that carries no typed relations.

    Reported as what it is. Giving it a manufactured anchor set to let it clear
    the floor would be exactly the anchorless-distractor defect the floor exists
    to refuse, arrived at from the other direction.
    """
    return {
        "seed_id": f"UNTYPED-{concept_id}",
        "target_id": None,
        "competitor_concept": label,
        "competitor_concept_id": concept_id,
        "competitor_study_unit_id": provenance.get("study_unit_id"),
        "normalized_competitor_text": normalize_option_text(label),
        "conditions_under_which_competitor_would_be_correct": None,
        "condition_predicates": [],
        "plausibility_anchor_feature_ids": [],
        "response_class_tokens": [],
        "nominal_axis_values": {},
        "applicable_disciplines": [],
        "applicable_item_archetypes": [],
        "option_set_archetypes": [],
        "decision_granularity": None,
        "shared_features_with_key": [],
        "reviewed_strength": None,
        "source_pack": None,
        "typing_state": "DISCOVERED_BUT_UNTYPED",
    }


# ------------------------------------------------------------------- arm B


def build_bm25_rows(
    connection: sqlite3.Connection,
    scenario: dict[str, Any],
    *,
    limit: int = BM25_LIMIT,
    typed_rows: dict[str, dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Arm B. Lexical discovery over Toronto Notes chunks, then concept resolution."""
    typed_rows = typed_rows if typed_rows is not None else {}
    query = build_query(scenario)
    if not query["match_expression"]:
        return []
    try:
        hits = connection.execute(
            "SELECT c.chunk_id, c.pdf_page, c.tn_node_id, c.subheading, bm25(chunks_fts) "
            "FROM chunks_fts JOIN chunks c ON c.rowid = chunks_fts.rowid "
            "WHERE chunks_fts MATCH ? ORDER BY bm25(chunks_fts) LIMIT ?",
            (query["match_expression"], limit),
        ).fetchall()
    except sqlite3.OperationalError as exc:
        raise ClinicalRetrievalError(f"text query is unusable: {exc}") from exc

    discovered: dict[str, dict[str, Any]] = {}
    for chunk_id, page, tn_node_id, subheading, score in hits:
        mentions = connection.execute(
            "SELECT m.concept_id, c.preferred_label, c.provenance "
            "FROM concept_mentions m JOIN concepts c ON c.concept_id = m.concept_id "
            "WHERE m.chunk_id = ? ORDER BY m.concept_id",
            (chunk_id,),
        ).fetchall()
        for concept_id, label, provenance in mentions:
            entry = discovered.setdefault(concept_id, {
                "concept_id": concept_id, "label": label,
                "provenance": json.loads(provenance), "hits": [], "best_score": score,
            })
            entry["hits"].append({
                "chunk_id": chunk_id, "pdf_page": page, "tn_node_id": tn_node_id,
                "subheading": subheading, "bm25": score,
            })
            entry["best_score"] = min(entry["best_score"], score)

    rows: list[dict[str, Any]] = []
    for concept_id, entry in sorted(discovered.items()):
        base = typed_rows.get(concept_id)
        row = dict(base) if base else _untyped_row(
            concept_id, entry["label"], entry["provenance"]
        )
        row.setdefault("typing_state", "TYPED")
        row["retrieval_provenance"] = {
            "arm": "BM25",
            "text_hits": entry["hits"][:5],
            "best_bm25": entry["best_score"],
            "graph_paths": [],
        }
        rows.append(row)
    return rows


# ------------------------------------------------------------------- arm C


def build_graph_rows(
    connection: sqlite3.Connection,
    scenario: dict[str, Any],
    *,
    max_depth: int = GRAPH_MAX_DEPTH,
    typed_rows: dict[str, dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Arm C. Typed traversal from the realized stem's PRESENT features.

    The traversal starts at what the stem actually says, not at the chapter or
    the study unit, because "related to the topic" is precisely the signal that
    produced the anchorless competitors G1 and G2 kept rejecting.
    """
    typed_rows = typed_rows if typed_rows is not None else {}
    query = build_query(scenario)
    present = query["present_feature_ids"]
    if not present:
        return []

    placeholders = ",".join("?" for _ in present)
    reached: dict[str, list[list[dict[str, Any]]]] = {}

    # Step 1: PLAUSIBILITY_ANCHOR inverted. Which competitors does a candidate have
    # a positive reason to consider, given the findings this stem states PRESENT?
    for concept_id, edge_id, feature_id in connection.execute(
        f"SELECT source_node, edge_id, target_node FROM edges "
        f"WHERE relation = 'PLAUSIBILITY_ANCHOR' AND target_node IN ({placeholders}) "
        "ORDER BY edge_id",
        present,
    ):
        reached.setdefault(concept_id, []).append([{
            "relation": "PLAUSIBILITY_ANCHOR", "edge_id": edge_id,
            "from": feature_id, "to": concept_id, "depth": 1,
        }])

    # Step 2: CONFUSED_WITH from what step 1 reached, bounded.
    if max_depth >= 2 and reached:
        anchored = sorted(reached)
        marks = ",".join("?" for _ in anchored)
        for left, edge_id, right in connection.execute(
            f"SELECT source_node, edge_id, target_node FROM edges "
            f"WHERE relation = 'CONFUSED_WITH' AND source_node IN ({marks}) ORDER BY edge_id",
            anchored,
        ):
            if right in reached:
                continue
            reached.setdefault(right, []).append(
                reached[left][0] + [{
                    "relation": "CONFUSED_WITH", "edge_id": edge_id,
                    "from": left, "to": right, "depth": 2,
                }]
            )

    rows: list[dict[str, Any]] = []
    for concept_id, paths in sorted(reached.items()):
        base = typed_rows.get(concept_id)
        if base:
            row = dict(base)
            row.setdefault("typing_state", "TYPED")
        else:
            label = connection.execute(
                "SELECT label FROM nodes WHERE node_id = ?", (concept_id,)
            ).fetchone()
            row = _untyped_row(concept_id, (label or [concept_id])[0], {})
        row["retrieval_provenance"] = {
            "arm": "GRAPH", "text_hits": [], "graph_paths": paths[:3],
        }
        rows.append(row)
    return rows


# ------------------------------------------------------------------ scoring


def _component_scores(
    competitor: dict[str, Any], scenario: dict[str, Any]
) -> dict[str, Any]:
    """Interpretable dimensions, kept apart rather than collapsed into one number.

    Averaging these would hide exactly the distinctions the benchmark exists to
    make -- a candidate that is textually close but archetype-wrong is a different
    failure from one that is archetype-right but anchorless.
    """
    provenance = competitor.get("retrieval_provenance") or {}
    total = competitor.get("total_conditions") or 0
    return {
        "decision_match": competitor.get("decision_granularity")
        == scenario.get("decision_granularity"),
        "archetype_match": scenario.get("option_set_archetype")
        in (competitor.get("option_set_archetypes") or []),
        "granularity_match": bool(competitor.get("decision_granularity")),
        "stem_anchor_support": competitor.get("anchors_present", 0),
        "text_relevance": provenance.get("best_bm25"),
        "graph_relation_strength": len(provenance.get("graph_paths") or []),
        "source_confidence": competitor.get("reviewed_strength"),
        "second_key_risk": (competitor.get("satisfied_conditions", 0) / total)
        if total else 0.0,
        "categorical_exclusion": False,
    }


def retrieve_competitors(
    connection: sqlite3.Connection,
    scenario: dict[str, Any],
    *,
    arm: str = "HYBRID",
    root: Path | None = None,
    demanded_response_class: str | None = None,
    feature_anchor_snapshot: dict[str, Any] | None = None,
    feature_anchor_scope: str | None = None,
) -> dict[str, Any]:
    """Retrieve competitors for one realized scenario under one arm.

    Whatever the arm, the rows end up in the same filter. The floor and the
    ceiling are not parameters of this function and cannot be relaxed by it, and
    ``feature_anchor_snapshot`` does not change that either: it selects which
    pinned registry snapshot supplies `SAF_1`'s anchors, and nothing else. Left
    unpinned, every arm reads the frozen packs and the benchmark is unmoved.
    """
    if arm not in ARMS:
        raise ClinicalRetrievalError(f"unknown retrieval arm: {arm}")
    root = Path(root or Path.cwd()).resolve()

    typed_rows = _load_typed_rows(root)
    library = build_current_library_index(
        root,
        feature_anchor_snapshot=feature_anchor_snapshot,
        feature_anchor_scope=feature_anchor_scope,
    )

    if arm == "CURRENT_LIBRARY":
        index = library
    elif arm == "BM25":
        index = build_bm25_rows(connection, scenario, typed_rows=typed_rows)
    elif arm == "GRAPH":
        index = build_graph_rows(connection, scenario, typed_rows=typed_rows)
    else:
        merged: dict[str, dict[str, Any]] = {}
        for row in build_graph_rows(connection, scenario, typed_rows=typed_rows):
            merged[row["competitor_concept_id"]] = row
        for row in build_bm25_rows(connection, scenario, typed_rows=typed_rows):
            existing = merged.get(row["competitor_concept_id"])
            if existing is None:
                merged[row["competitor_concept_id"]] = row
                continue
            # Union, with both provenances kept. A candidate found by both arms is
            # a stronger result than one found by either, and the report should be
            # able to say so.
            existing["retrieval_provenance"] = {
                "arm": "HYBRID",
                "text_hits": row["retrieval_provenance"]["text_hits"],
                "best_bm25": row["retrieval_provenance"].get("best_bm25"),
                "graph_paths": existing["retrieval_provenance"]["graph_paths"],
            }
        for row in library:
            merged.setdefault(row["competitor_concept_id"], {
                **row, "typing_state": "TYPED",
                "retrieval_provenance": {
                    "arm": "CURRENT_LIBRARY", "text_hits": [], "graph_paths": []
                },
            })
        index = [merged[key] for key in sorted(merged)]

    discovered_but_untyped = sorted({
        row["competitor_concept_id"] for row in index
        if row.get("typing_state") == "DISCOVERED_BUT_UNTYPED"
    })

    archetype = scenario["option_set_archetype"]
    axis = ARCHETYPE_RESPONSE_AXIS[archetype]
    if demanded_response_class is None:
        assignments = {
            row["opportunity_label"]: row
            for row in _load(root, DEMANDED_CLASSES_RELATIVE_PATH)["assignments"]
        }
        assignment = assignments.get(scenario["wave_label"])
        if assignment is None:
            raise ClinicalRetrievalError(
                f"no frozen demanded response class for {scenario['wave_label']}"
            )
        demanded_response_class = assignment["demanded_response_class"]

    profile = _load(
        root, PROFILE_RELATIVE_PATH.format(profile=scenario["discipline_profile_id"])
    )
    contract = _load(root, DEMANDED_CLASSES_RELATIVE_PATH).get("assignment_contract")
    token_implications = (
        contract.get("token_implications", {}) if isinstance(contract, dict) else {}
    )

    retrieval = retrieve_profile_aware_contrasts(
        index=index,
        discipline_profile_id=scenario["discipline_profile_id"],
        item_archetype=scenario["item_archetype"],
        option_set_archetype=archetype,
        demanded_response_class=demanded_response_class,
        token_implications=token_implications,
        generic_token=RESPONSE_CLASS_AXES[axis]["generic_token"],
        stem_feature_map=scenario["stem_feature_map"],
        ranking_preference=profile["competitor_ranking_preference"],
    )
    for competitor in retrieval["ranked_competitors"]:
        competitor["component_scores"] = _component_scores(competitor, scenario)
    retrieval["ranked_seed_ids"] = [
        row["seed_id"] for row in retrieval["ranked_competitors"]
    ]
    return {
        "arm": arm,
        "wave_label": scenario["wave_label"],
        "query": build_query(scenario),
        "candidates_entering_the_index": len(index),
        "discovered_but_untyped": discovered_but_untyped,
        "retrieval": retrieval,
    }


# ------------------------------------------------------------------ packet


def build_context_packet(
    connection: sqlite3.Connection,
    scenario: dict[str, Any],
    result: dict[str, Any],
) -> dict[str, Any]:
    """Assemble the low-token context packet and measure it.

    Typed rows and identifiers, never prose. The size is measured from the
    serialized packet rather than estimated, because the design labelled its own
    token budget an ENGINEERING_ESTIMATE and said the benchmark is where real
    sizes get measured.
    """
    competitors = result["retrieval"]["ranked_competitors"][:MAX_PACKET_COMPETITORS]
    features = scenario["stem_feature_map"].get("features") or []
    packet: dict[str, Any] = {
        "wave_label": scenario["wave_label"],
        "learner_decision_id": scenario.get("learner_decision_id"),
        "anchor_study_unit_id": scenario.get("anchor_study_unit_id"),
        "item_archetype": scenario["item_archetype"],
        "option_set_archetype": scenario["option_set_archetype"],
        "difficulty_intent": scenario.get("difficulty_intent"),
        "stem_features": [
            {"feature_id": feature["feature_id"], "polarity": feature["polarity"]}
            for feature in features
        ],
        "competitors": [
            {
                "seed_id": competitor["seed_id"],
                "concept_id": competitor["competitor_concept_id"],
                "label": competitor["competitor_concept"],
                "anchors_present": competitor["anchors_present"],
                "total_anchors": competitor["total_anchors"],
                "satisfied_conditions": competitor["satisfied_conditions"],
                "total_conditions": competitor["total_conditions"],
                "component_scores": competitor["component_scores"],
                "provenance": {
                    "arm": (competitor.get("retrieval_provenance") or {}).get("arm"),
                    "source_pack": competitor.get("source_pack"),
                    "graph_edge_ids": [
                        step["edge_id"]
                        for path in (competitor.get("retrieval_provenance") or {}).get(
                            "graph_paths", []
                        )
                        for step in path
                    ],
                    "chunk_ids": [
                        hit["chunk_id"]
                        for hit in (competitor.get("retrieval_provenance") or {}).get(
                            "text_hits", []
                        )
                    ],
                },
            }
            for competitor in competitors
        ],
        "source_refs": sorted({
            row[0] for row in connection.execute(
                "SELECT source_id FROM sources WHERE authority_class != 'OTHER' "
                "ORDER BY source_id"
            )
        })[:8],
    }
    # Measured over the payload, deliberately excluding the size block itself, so
    # the number is stable rather than a self-referential fixed point.
    serialized = json.dumps(packet, sort_keys=True)
    packet["size"] = {
        "measurement": "MEASURED",
        "measured_over": "PACKET_PAYLOAD_EXCLUDING_THE_SIZE_BLOCK",
        "characters": len(serialized),
        "words": len(serialized.split()),
        # No token count is reported. The repository has no local tokenizer, and
        # the design already labelled its own token budget an ENGINEERING_ESTIMATE.
        "tokens": None,
    }
    return packet
