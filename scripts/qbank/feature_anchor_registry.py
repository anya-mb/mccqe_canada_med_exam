"""A versioned canonical registry for clinical feature identity and anchor relations.

The on-demand supply milestone ended on one structural finding. Its wave added a
clinically legitimate, evidence-cited plausibility anchor to two competitors of
`G2-PED-01`; the item was realized, stayed post-stem coherent and was scored zero
on all eleven independent-review dimensions -- and `SAF_1` then refused two of its
three competitors, because `retrieve_profile_aware_contrasts` reads plausibility
anchors from the frozen `*.stem_anchors.json` packs that design rule S-2 forbids
supply to edit. The anchor existed in V2's semantics and did not exist in
production's.

That is not a clinical disagreement. It is two readers of what should be one
contract, and this module is the contract.

Nothing here redefines Clinical Contrast Model V2, relaxes a gate, or edits a
frozen artifact. It introduces one versioned source of truth for

  * clinical feature identity, states and roles, and
  * plausibility-anchor *relations*, which are deliberately a separate kind of
    thing from features,

builds explicit, content-addressed snapshots of it, and lets the V2 engine,
`SAF_1`, profile-aware retrieval and the supply layer read the *same* pinned
snapshot. Historical replays keep reading their original frozen packs, byte for
byte, because a snapshot is only ever consulted when a caller pins one.

Design: docs/superpowers/specs/2026-09-06-versioned-clinical-feature-anchor-registry-design.md
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
from typing import Any, Mapping, Sequence

from .errors import QbankError
from .paths import resolve_root_path


class FeatureAnchorRegistryError(QbankError):
    """A registry artifact, snapshot pin, or extension proposal is unusable."""


# ------------------------------------------------------------------- inputs

VOCABULARY_PATH = "research/qgen/safe_yield/g2_stem_feature_vocabulary.json"

#: The three frozen curated seed packs, each with its own frozen enrichment and
#: its own frozen stem-anchor layer. Order is the order the readers use.
SEED_PACK_BASES = (
    "research/qgen/generalization/competitive_contrast_seed_pack_r4",
    "research/qgen/generalization/competitive_contrast_seed_pack_g2_targeted",
    "research/qgen/generalization/competitive_contrast_seed_pack_g2_extensions",
)

SUPPLY_ACQUISITION_PATH = "research/qgen/clinical_contrast_supply_acquisition.json"

RECONCILIATION_REPORT_PATH = "reports/qgen_feature_anchor_contract_reconciliation.json"


def _read(root, relative: str) -> Any:
    path = resolve_root_path(Path(root).resolve(), relative)
    if not path.is_file():
        raise FeatureAnchorRegistryError(f"artifact is unavailable: {relative}")
    return json.loads(path.read_text())


def _sha256_of_file(root, relative: str) -> str:
    import hashlib

    path = resolve_root_path(Path(root).resolve(), relative)
    return hashlib.sha256(path.read_bytes()).hexdigest()


# ------------------------------------------------------- Phase 0 reconciliation

#: One row per artifact that participates in feature identity or anchor
#: plausibility. `readers` is measured, not asserted: every row's `path_token` is
#: grepped over the tracked Python sources, so a reader added later shows up here
#: rather than in a stale comment.
_CONTRACT_ARTIFACTS: tuple[dict[str, Any], ...] = (
    {
        "artifact": VOCABULARY_PATH,
        "path_token": "g2_stem_feature_vocabulary.json",
        "layer": "CLINICAL_FEATURE_IDENTITY",
        "writer": "authored for the G2 profile pilot and frozen; no builder rewrites it",
        "immutable": True,
        "versioned": False,
        "current_source_of_truth": True,
        "known_mismatch": (
            "It is the only feature vocabulary and it carries no version, so a "
            "consumer cannot say which vocabulary it read. Its `clinical_role` is "
            "the sole input to V2 role typing, and three of its roles "
            "(CLINICAL_JUDGEMENT, SYSTEM_CONSTRAINT, PROGRAMME_CAPACITY) type to "
            "non-anchor classes in PATIENT_CLINICAL while the frozen anchor packs "
            "already use features of those roles as anchors."
        ),
    },
    {
        "artifact": "research/qgen/generalization/*.stem_anchors.json",
        "path_token": ".stem_anchors.json",
        "layer": "PLAUSIBILITY_ANCHOR_RELATIONS",
        "writer": "scripts/qbank/build_stem_anchor_layer.py, under rules R1-R4",
        "immutable": True,
        "versioned": False,
        "current_source_of_truth": True,
        "known_mismatch": (
            "THE DEFECT. This is the artifact `SAF_1` reads, through "
            "`profile_contrast_retrieval.build_retrieval_index` and "
            "`contrast_first_pilot.load_curated_candidates`. Supply rule S-2 "
            "forbids the supply layer to edit it, so an anchor supply adds is "
            "invisible to the production gate. It is keyed by `seed_id`, carries "
            "no anchor role, no required state and no evidence reference, and its "
            "rows are a flat list of feature ids rather than typed relations."
        ),
    },
    {
        "artifact": "research/qgen/generalization/*.enrichment.json",
        "path_token": ".enrichment.json",
        "layer": "CORRECTNESS_CONDITIONS",
        "writer": "authored for the G2 pilot and frozen",
        "immutable": True,
        "versioned": False,
        "current_source_of_truth": True,
        "known_mismatch": (
            "Correctness conditions and plausibility anchors live in two "
            "separately frozen artifacts with no shared identity, which is why "
            "`CS2-6` ANCHOR_EQUALS_CONDITION has to be recomputed by joining them."
        ),
    },
    {
        "artifact": "research/qgen/generalization/*.json (curated seed packs)",
        "path_token": "competitive_contrast_seed_pack",
        "layer": "COMPETITOR_CONCEPT_IDENTITY",
        "writer": "authored and independently reviewed per pack; frozen",
        "immutable": True,
        "versioned": True,
        "current_source_of_truth": True,
        "known_mismatch": (
            "`competitor_concept_id` is unique across all 81 retrievable seeds, so "
            "concept identity is already stable; nothing consumes it as identity, "
            "because every downstream reader keys on `seed_id` instead."
        ),
    },
    {
        "artifact": "scripts/qbank/clinical_contrast_v2.py (role and state model)",
        "path_token": "clinical_contrast_v2",
        "layer": "FEATURE_STATE_AND_ROLE_SEMANTICS",
        "writer": "code, not data: CONTRAST_ROLES and CLINICAL_ROLE_TO_CONTRAST_ROLE",
        "immutable": False,
        "versioned": False,
        "current_source_of_truth": True,
        "known_mismatch": (
            "The four states and the thirteen contrast roles are canonical and "
            "correct, but they are expressed only in code, so no artifact can "
            "record which role model it was validated against, and no anchor row "
            "can declare the role under which it is an anchor."
        ),
    },
    {
        "artifact": "research/qgen/clinical_contrast_relations_v2.json",
        "path_token": "clinical_contrast_relations_v2.json",
        "layer": "V2_CONTRAST_RELATIONS",
        "writer": "authored for the V2 milestone; 68 frozen relations",
        "immutable": True,
        "versioned": True,
        "current_source_of_truth": True,
        "known_mismatch": (
            "A relation's `b_supporting_features` carry typed contrast roles and "
            "are the V2 reading of a competitor's anchors, but they are a second, "
            "independent statement of the same relation the stem-anchor packs "
            "state untyped. Nothing reconciles the two."
        ),
    },
    {
        "artifact": SUPPLY_ACQUISITION_PATH,
        "path_token": "clinical_contrast_supply_acquisition.json",
        "layer": "PROPOSED_ANCHOR_EXTENSIONS",
        "writer": "authored for the supply wave and frozen before any generation",
        "immutable": True,
        "versioned": True,
        "current_source_of_truth": True,
        "known_mismatch": (
            "It holds the four independently approved anchor additions and has no "
            "path into any artifact `SAF_1` reads. `apply_supply_to_contrast_set` "
            "applies them to an in-memory V2 contrast set only."
        ),
    },
    {
        "artifact": "research/qgen/clinical_contrast_supply_cache.json",
        "path_token": "clinical_contrast_supply_cache.json",
        "layer": "SUPPLY_RELATION_CACHE",
        "writer": "scripts/qbank/contrast_supply.py, keyed by decision context",
        "immutable": False,
        "versioned": True,
        "current_source_of_truth": False,
        "known_mismatch": (
            "A cache entry's content hash moves when an anchor is added, which is "
            "correct, but the cache records no feature/anchor snapshot, so two "
            "entries built against different anchor populations are "
            "indistinguishable."
        ),
    },
    {
        "artifact": "research/qgen/safe_yield/g2_profile_pilot.*.json",
        "path_token": "g2_profile_pilot",
        "layer": "FROZEN_G2_EXPERIMENT",
        "writer": "the G2 wave; frozen",
        "immutable": True,
        "versioned": True,
        "current_source_of_truth": False,
        "known_mismatch": (
            "None to repair. Historical; must keep reading the frozen packs "
            "byte-identically and must not see any registry extension."
        ),
    },
    {
        "artifact": "research/qgen/contrast_first_pilot_*.json",
        "path_token": "contrast_first_pilot_",
        "layer": "FROZEN_V1_PILOT",
        "writer": "the contrast-first pilot; frozen",
        "immutable": True,
        "versioned": True,
        "current_source_of_truth": False,
        "known_mismatch": "None to repair. Historical.",
    },
    {
        "artifact": "research/qgen/safe_yield/retrieval_benchmark_reference.json",
        "path_token": "retrieval_benchmark_reference.json",
        "layer": "FROZEN_RETRIEVAL_BENCHMARK",
        "writer": "derived from the frozen semantic-admissibility record; frozen",
        "immutable": True,
        "versioned": True,
        "current_source_of_truth": False,
        "known_mismatch": (
            "None to repair, but it is the reason `retrieve_profile_aware_contrasts` "
            "must not change its rule or its verdicts: that function is benchmark "
            "arm A."
        ),
    },
)

_SOURCE_GLOBS = ("scripts/qbank/*.py", "tests/*.py")


def _measured_readers(root, token: str) -> list[str]:
    """Grep the tracked sources for a path token. Measured, not asserted."""
    canonical = Path(root).resolve()
    found: set[str] = set()
    for pattern in _SOURCE_GLOBS:
        directory, suffix = pattern.split("/*")
        for path in sorted((canonical / directory).glob("*" + suffix)):
            try:
                text = path.read_text()
            except (OSError, UnicodeDecodeError):
                continue
            if token in text:
                found.add(str(path.relative_to(canonical)))
    return sorted(found)


def _git_head(root) -> str:
    result = subprocess.run(
        ["git", "-C", str(Path(root).resolve()), "rev-parse", "HEAD"],
        capture_output=True, text=True, check=False,
    )
    return result.stdout.strip() or "UNKNOWN"


def measure_anchor_population(root) -> dict[str, Any]:
    """Measure the frozen anchor population the production gate actually reads."""
    features: dict[str, dict[str, Any]] = {}
    for unit in _read(root, VOCABULARY_PATH)["anchors"]:
        for feature in unit["features"]:
            features[feature["stem_feature_id"]] = {
                "study_unit_id": unit["anchor_study_unit_id"],
                "clinical_role": feature["clinical_role"],
            }

    pairs = 0
    seeds = 0
    empty: list[str] = []
    used_features: set[str] = set()
    per_pack: list[dict[str, Any]] = []
    for base in SEED_PACK_BASES:
        anchors = _read(root, f"{base}.stem_anchors.json")
        pack_pairs = 0
        for row in anchors["seeds"]:
            seeds += 1
            ids = {entry["stem_feature_id"] for entry in row["plausibility_anchors"]}
            if not ids:
                empty.append(row["seed_id"])
            pack_pairs += len(ids)
            used_features.update(ids)
        pairs += pack_pairs
        per_pack.append({
            "pack": base.rsplit("/", 1)[-1],
            "anchor_rows": len(anchors["seeds"]),
            "anchor_pairs": pack_pairs,
            "sha256": _sha256_of_file(root, f"{base}.stem_anchors.json"),
        })

    by_role: dict[str, int] = {}
    for feature_id in sorted(used_features):
        role = features.get(feature_id, {}).get("clinical_role", "UNKNOWN_FEATURE")
        by_role[role] = by_role.get(role, 0) + 1
    return {
        "FEATURES_IN_FROZEN_VOCABULARY": len(features),
        "STUDY_UNITS_IN_FROZEN_VOCABULARY": len({
            row["study_unit_id"] for row in features.values()
        }),
        "SEEDS_WITH_AN_ANCHOR_ROW": seeds,
        "ANCHOR_PAIRS": pairs,
        "DISTINCT_FEATURES_USED_AS_AN_ANCHOR": len(used_features),
        "SEEDS_WITH_AN_EMPTY_ANCHOR_SET": sorted(empty),
        "anchor_features_by_clinical_role": dict(sorted(by_role.items())),
        "per_pack": per_pack,
    }


def measure_supply_invisibility(root) -> dict[str, Any]:
    """The one measurement that names the defect: approved anchors not in any pack."""
    frozen: dict[str, set[str]] = {}
    for base in SEED_PACK_BASES:
        for row in _read(root, f"{base}.stem_anchors.json")["seeds"]:
            frozen[row["seed_id"]] = {
                entry["stem_feature_id"] for entry in row["plausibility_anchors"]
            }

    rows: list[dict[str, Any]] = []
    acquisition = _read(root, SUPPLY_ACQUISITION_PATH)
    for label, entry in sorted(acquisition["opportunities"].items()):
        for candidate in entry["candidates"]:
            if candidate["review"]["verdict"] != "APPROVED":
                continue
            for anchor in candidate.get("added_anchors") or []:
                member = candidate["member_id"]
                rows.append({
                    "opportunity_label": label,
                    "member_id": member,
                    "feature_id": anchor["feature_id"],
                    "contrast_role": anchor["contrast_role"],
                    "in_frozen_stem_anchor_pack": anchor["feature_id"] in frozen.get(
                        member, set()
                    ),
                    "member_has_a_frozen_anchor_row": member in frozen,
                })
    return {
        "APPROVED_ANCHOR_ADDITIONS": len(rows),
        "VISIBLE_TO_SAF1_TODAY": sum(1 for row in rows if row["in_frozen_stem_anchor_pack"]),
        "INVISIBLE_TO_SAF1_TODAY": sum(
            1 for row in rows if not row["in_frozen_stem_anchor_pack"]
        ),
        "additions": rows,
    }


def build_reconciliation(root) -> dict[str, Any]:
    """Phase 0. The dependency map, before any production code is touched."""
    artifacts = []
    for row in _CONTRACT_ARTIFACTS:
        entry = {key: value for key, value in row.items() if key != "path_token"}
        entry["ARTIFACT"] = entry.pop("artifact")
        entry["WRITER"] = entry.pop("writer")
        entry["READERS"] = _measured_readers(root, row["path_token"])
        entry["IMMUTABLE"] = entry.pop("immutable")
        entry["VERSIONED"] = entry.pop("versioned")
        entry["CURRENT_SOURCE_OF_TRUTH"] = entry.pop("current_source_of_truth")
        entry["KNOWN_MISMATCH"] = entry.pop("known_mismatch")
        artifacts.append(entry)

    return {
        "schema_version": "1.0",
        "scope": "QGEN_FEATURE_ANCHOR_CONTRACT_RECONCILIATION",
        "starting_commit": "14f4508",
        "head_commit": _git_head(root),
        "production_code_changed": False,
        "llm_api_calls": 0,
        "the_defect_in_one_sentence": (
            "V2, the supply layer and the production gate all reason over clinical "
            "features and plausibility anchors, but only the production gate's "
            "reader is bound to a frozen artifact the supply layer may not write, "
            "so a clinically legitimate, independently approved anchor exists in "
            "one reader's world and not in the other's."
        ),
        "artifacts": artifacts,
        "anchor_population": measure_anchor_population(root),
        "supply_invisibility": measure_supply_invisibility(root),
        "readers_of_the_anchor_layer": {
            "SAF_1": (
                "profile_contrast_retrieval.retrieve_profile_aware_contrasts reads "
                "row['plausibility_anchor_feature_ids'] and refuses a competitor "
                "with no anchor PRESENT. The rule is correct and is not the defect."
            ),
            "index_builders": [
                "profile_contrast_retrieval.build_retrieval_index",
                "contrast_first_pilot.load_curated_candidates",
                "contrast_first_pilot.contrast_set_retrieval_index",
            ],
            "the_seam": (
                "All three builders are where a frozen pack becomes an index row. "
                "That, not SAF_1, is where a pinned snapshot has to be consumable."
            ),
        },
        "immutability_positions": {
            "must_stay_byte_identical": [
                VOCABULARY_PATH,
                *(f"{base}.json" for base in SEED_PACK_BASES),
                *(f"{base}.enrichment.json" for base in SEED_PACK_BASES),
                *(f"{base}.stem_anchors.json" for base in SEED_PACK_BASES),
                "research/qgen/clinical_contrast_relations_v2.json",
                SUPPLY_ACQUISITION_PATH,
                "research/qgen/clinical_contrast_supply_frozen5_generated.json",
                "research/qgen/safe_yield/retrieval_benchmark_reference.json",
            ],
            "rule": (
                "A new canonical registry is introduced beside these artifacts and "
                "imports them. Nothing is appended to them."
            ),
        },
        "conclusion": {
            "PRIMARY_MISMATCH": "ANCHOR_RELATIONS_ARE_NOT_A_SHARED_VERSIONED_CONTRACT",
            "SECONDARY_MISMATCH": "ANCHOR_ROWS_ARE_UNTYPED_AND_CARRY_NO_EVIDENCE",
            "REQUIRED_CHANGE": (
                "One versioned registry of feature identity and anchor relations, "
                "built into explicit content-addressed snapshots, consumed by V2, "
                "SAF_1, profile-aware retrieval and supply through an explicit pin."
            ),
            "NOT_REQUIRED": [
                "changing the SAF_1 rule",
                "growing the frozen 102-feature vocabulary",
                "expanding the graph or the Toronto Notes index",
                "re-reviewing the four approved supply relations clinically",
            ],
        },
    }
