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


# ------------------------------------------------------------ the registry

BASELINE_SNAPSHOT_ID = "FEATURE_ANCHOR_SNAPSHOT_V1"
EXTENDED_SNAPSHOT_ID = "FEATURE_ANCHOR_SNAPSHOT_V2"

SNAPSHOTS_PATH = "research/qgen/feature_anchor_snapshots.json"
EXTENSIONS_PATH = "research/qgen/feature_anchor_extensions.json"

#: The registry is a boundary, and this is the whole of what it may say about a
#: state. V2's four, imported rather than restated.
REGISTRY_FEATURE_STATES = ("PRESENT", "ABSENT", "UNKNOWN", "NOT_APPLICABLE")

REVIEW_VERDICTS = ("APPROVED", "REJECTED", "UNCERTAIN")

#: Only APPROVED enters a snapshot. UNCERTAIN fails closed exactly as REJECTED
#: does, which is the point of naming it separately.
ADMISSIBLE_REVIEW_VERDICTS = frozenset({"APPROVED"})

EXTENSION_CLASSIFICATIONS = (
    "FEATURE_ALREADY_EXISTS",
    "NEW_FEATURE_REQUIRED",
    "ANCHOR_RELATION_ONLY",
    "INVALID_EXTENSION",
)

VERIFICATION_STATUSES = ("FROZEN_CANONICAL", "EVIDENCE_VERIFIED", "EVIDENCE_PENDING")


def canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def content_sha256(payload: Any) -> str:
    import hashlib

    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def supported_roles_for(feature_type: str) -> dict[str, str]:
    """The contrast role this feature type yields in each decision domain.

    Computed from the canonical V2 mapping and never authored, so the role
    ontology cannot grow through the registry.
    """
    from .clinical_contrast_v2 import (
        DECISION_DOMAINS,
        ClinicalContrastV2Error,
        contrast_role_for,
    )

    roles: dict[str, str] = {}
    for domain in DECISION_DOMAINS:
        try:
            roles[domain] = contrast_role_for(feature_type, decision_domain=domain)
        except ClinicalContrastV2Error:
            continue
    return roles


def _non_anchor_domains(roles: Mapping[str, str]) -> list[str]:
    from .clinical_contrast_v2 import ANCHOR_CLASSES, discriminative_class

    return sorted(
        domain for domain, role in roles.items()
        if discriminative_class(role) not in ANCHOR_CLASSES
    )


def build_feature_registry(root, *, introduced_in_version: str) -> list[dict[str, Any]]:
    """Import the frozen stem-feature vocabulary as registry feature rows.

    Nothing is reinterpreted. `feature_id`, `preferred_label` and `feature_type`
    are the frozen `stem_feature_id`, `normalized_feature` and `clinical_role`;
    `canonical_concept_id` is the feature id, which the Phase-B normalization
    inventory measured to be the resolved canonical concept for every local term.
    """
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for unit in _read(root, VOCABULARY_PATH)["anchors"]:
        study_unit = unit["anchor_study_unit_id"]
        for feature in unit["features"]:
            feature_id = feature["stem_feature_id"]
            if feature_id in seen:
                raise FeatureAnchorRegistryError(
                    f"duplicate feature id in the frozen vocabulary: {feature_id}"
                )
            seen.add(feature_id)
            roles = supported_roles_for(feature["clinical_role"])
            rows.append({
                "feature_id": feature_id,
                "canonical_concept_id": feature_id,
                "preferred_label": feature["normalized_feature"],
                "feature_type": feature["clinical_role"],
                "allowed_states": list(REGISTRY_FEATURE_STATES),
                "supported_roles": roles,
                "non_anchor_in_decision_domains": _non_anchor_domains(roles),
                "provenance": {
                    "artifact": VOCABULARY_PATH,
                    "study_unit_id": study_unit,
                    "kind": "FROZEN_STUDY_UNIT_VOCABULARY",
                },
                "verification_status": "FROZEN_CANONICAL",
                "introduced_in_version": introduced_in_version,
                "deprecated_in_version": None,
            })
    return sorted(rows, key=lambda row: row["feature_id"])


ANCHOR_IDENTITY_FIELDS = (
    "feature_id",
    "target_concept_id",
    "learner_decision",
    "decision_granularity",
    "required_state",
)


def anchor_relation_id(identity: Mapping[str, Any]) -> str:
    """Content-address an anchor relation over its identity tuple alone.

    Evidence, role and derivation prose are deliberately excluded: restating why
    a relation holds must not move the id of the relation.
    """
    missing = [field for field in ANCHOR_IDENTITY_FIELDS if not identity.get(field)]
    if missing:
        raise FeatureAnchorRegistryError(
            f"an anchor relation needs {', '.join(missing)} to have an identity"
        )
    payload = {field: identity[field] for field in ANCHOR_IDENTITY_FIELDS}
    return "AR-" + content_sha256(payload)[:16]


def _seed_rows(root) -> dict[str, dict[str, Any]]:
    """Join the three frozen packs, enrichments and anchor layers by seed id."""
    resolved: dict[str, dict[str, Any]] = {}
    for base in SEED_PACK_BASES:
        pack = _read(root, f"{base}.json")
        enrichment = {
            seed["seed_id"]: seed for seed in _read(root, f"{base}.enrichment.json")["seeds"]
        }
        anchors = {
            seed["seed_id"]: seed for seed in _read(root, f"{base}.stem_anchors.json")["seeds"]
        }
        for target in pack["targets"]:
            for seed in target["seeds"]:
                seed_id = seed["seed_id"]
                tags = enrichment.get(seed_id)
                anchor_row = anchors.get(seed_id)
                if tags is None or anchor_row is None:
                    continue
                if seed_id in resolved:
                    raise FeatureAnchorRegistryError(f"duplicate seed id: {seed_id}")
                resolved[seed_id] = {
                    "seed_id": seed_id,
                    "pack": base.rsplit("/", 1)[-1],
                    "learner_decision": target["target_id"],
                    "target_concept_id": seed.get("competitor_concept_id"),
                    "competitor_concept": seed.get("competitor_concept"),
                    "decision_granularity": seed.get("competitor_decision_granularity"),
                    "response_class_tokens": list(tags.get("response_class_tokens") or []),
                    "anchor_study_unit_id": anchor_row.get("anchor_study_unit_id"),
                    "plausibility_anchors": list(anchor_row.get("plausibility_anchors") or []),
                    "no_anchor_finding": anchor_row.get("no_anchor_finding"),
                }
    return resolved


def build_baseline_anchor_relations(
    root, features: Sequence[Mapping[str, Any]], *, introduced_in_version: str
) -> list[dict[str, Any]]:
    """Import the three frozen stem-anchor packs as typed anchor relations.

    One relation per (seed, anchor feature) pair. The derivation rule and the
    derivation sentence the frozen pack already carries are preserved verbatim,
    so a relation can always be traced back to the artifact that stated it.
    """
    by_id = {row["feature_id"]: row for row in features}
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for seed_id, seed in sorted(_seed_rows(root).items()):
        if not seed["target_concept_id"]:
            raise FeatureAnchorRegistryError(f"seed {seed_id} carries no concept id")
        for anchor in seed["plausibility_anchors"]:
            feature_id = anchor["stem_feature_id"]
            feature = by_id.get(feature_id)
            if feature is None:
                raise FeatureAnchorRegistryError(
                    f"{seed_id} anchors on {feature_id}, which is not a registered feature"
                )
            identity = {
                "feature_id": feature_id,
                "target_concept_id": seed["target_concept_id"],
                "learner_decision": seed["learner_decision"],
                "decision_granularity": seed["decision_granularity"],
                "required_state": "PRESENT",
            }
            relation_id = anchor_relation_id(identity)
            if relation_id in seen:
                raise FeatureAnchorRegistryError(
                    f"duplicate anchor relation identity: {relation_id}"
                )
            seen.add(relation_id)
            rows.append({
                "anchor_relation_id": relation_id,
                **identity,
                "seed_id": seed_id,
                "scope_opportunity_labels": None,
                "response_class": sorted(seed["response_class_tokens"]),
                "anchor_role_by_decision_domain": feature["supported_roles"],
                "declared_anchor_role": None,
                "non_anchor_in_decision_domains": feature["non_anchor_in_decision_domains"],
                "anchor_study_unit_id": seed["anchor_study_unit_id"],
                "context": {
                    "derivation_rule": anchor.get("rule"),
                    "derivation": anchor.get("derivation"),
                    "source_artifact": (
                        "research/qgen/generalization/"
                        f"{seed['pack']}.stem_anchors.json"
                    ),
                },
                "evidence_refs": [],
                "verification_status": "FROZEN_CANONICAL",
                "introduced_in_version": introduced_in_version,
                "deprecated_in_version": None,
            })
    return sorted(rows, key=lambda row: (row["seed_id"], row["feature_id"]))


def registry_hash(
    features: Sequence[Mapping[str, Any]], relations: Sequence[Mapping[str, Any]]
) -> str:
    """SHA-256 over the rows and nothing else, so a rebuild reproduces it."""
    return content_sha256({
        "features": sorted(features, key=lambda row: row["feature_id"]),
        "anchor_relations": sorted(relations, key=lambda row: row["anchor_relation_id"]),
    })


# --------------------------------------------------------------- snapshots


def validate_extension(extension: Mapping[str, Any]) -> None:
    """Schema and policy for one proposed registry extension."""
    classification = extension.get("classification")
    if classification not in EXTENSION_CLASSIFICATIONS:
        raise FeatureAnchorRegistryError(
            f"unknown extension classification: {classification}"
        )
    verdict = (extension.get("registry_review") or {}).get("verdict")
    if verdict not in REVIEW_VERDICTS:
        raise FeatureAnchorRegistryError(
            f"{extension.get('extension_id')}: an extension needs a review verdict"
        )
    if verdict in ADMISSIBLE_REVIEW_VERDICTS:
        if classification != "ANCHOR_RELATION_ONLY":
            raise FeatureAnchorRegistryError(
                f"{extension['extension_id']}: only an ANCHOR_RELATION_ONLY extension "
                "may be approved by this registry; a new feature reopens the frozen "
                "vocabulary and needs its own authorization"
            )
        if not extension.get("evidence_refs"):
            raise FeatureAnchorRegistryError(
                f"{extension['extension_id']}: an approved extension needs evidence; "
                "model memory is not evidence"
            )
        if extension.get("required_state") != "PRESENT":
            raise FeatureAnchorRegistryError(
                f"{extension['extension_id']}: anchor relations require PRESENT"
            )
        for criterion in (
            "clinically_meaningful", "mcc_level_relevant",
            "needed_for_a_validated_contrast_relation", "not_a_duplicate",
            "correctly_typed",
        ):
            if extension["registry_review"].get(criterion) is not True:
                raise FeatureAnchorRegistryError(
                    f"{extension['extension_id']}: minimality criterion {criterion} "
                    "is not satisfied, so the extension is not admissible"
                )


def load_extensions(root) -> dict[str, Any]:
    """Load the proposed extension set. Every proposal is validated."""
    document = _read(root, EXTENSIONS_PATH)
    for extension in document["extensions"]:
        validate_extension(extension)
    return document


def approved_extensions(document: Mapping[str, Any]) -> list[dict[str, Any]]:
    return sorted(
        (
            extension for extension in document["extensions"]
            if extension["registry_review"]["verdict"] in ADMISSIBLE_REVIEW_VERDICTS
        ),
        key=lambda row: row["extension_id"],
    )


def _extension_relation(
    extension: Mapping[str, Any],
    features: Mapping[str, Mapping[str, Any]],
    *,
    introduced_in_version: str,
) -> dict[str, Any]:
    feature = features.get(extension["feature_id"])
    if feature is None:
        raise FeatureAnchorRegistryError(
            f"{extension['extension_id']}: {extension['feature_id']} is not a "
            "registered feature, so no anchor relation can name it"
        )
    identity = {
        "feature_id": extension["feature_id"],
        "target_concept_id": extension["target_concept_id"],
        "learner_decision": extension["learner_decision"],
        "decision_granularity": extension["decision_granularity"],
        "required_state": extension["required_state"],
    }
    declared = extension.get("declared_anchor_role")
    from .clinical_contrast_v2 import CONTRAST_ROLES

    if declared is not None and declared not in CONTRAST_ROLES:
        raise FeatureAnchorRegistryError(
            f"{extension['extension_id']}: unknown contrast role {declared}"
        )
    scope = sorted(extension.get("scope_opportunity_labels") or [])
    if not scope:
        raise FeatureAnchorRegistryError(
            f"{extension['extension_id']}: an approved anchor relation must name the "
            "decision contexts its review considered; an unscoped anchor is the "
            "universal-anchor failure this registry exists to prevent"
        )
    return {
        "anchor_relation_id": anchor_relation_id(identity),
        **identity,
        "seed_id": extension["seed_id"],
        "scope_opportunity_labels": scope,
        "response_class": sorted(extension.get("response_class") or []),
        "anchor_role_by_decision_domain": feature["supported_roles"],
        "declared_anchor_role": declared,
        "non_anchor_in_decision_domains": feature["non_anchor_in_decision_domains"],
        "anchor_study_unit_id": extension["anchor_study_unit_id"],
        "context": dict(extension["context"]),
        "evidence_refs": sorted(extension["evidence_refs"]),
        "verification_status": "EVIDENCE_VERIFIED",
        "introduced_in_version": introduced_in_version,
        "deprecated_in_version": None,
    }


def build_snapshot(
    root, *, snapshot_id: str, extensions: Sequence[Mapping[str, Any]] = ()
) -> dict[str, Any]:
    """Build one explicit snapshot. Deterministic and content-addressed."""
    features = build_feature_registry(root, introduced_in_version=BASELINE_SNAPSHOT_ID)
    relations = build_baseline_anchor_relations(
        root, features, introduced_in_version=BASELINE_SNAPSHOT_ID
    )
    by_feature = {row["feature_id"]: row for row in features}
    existing = {row["anchor_relation_id"] for row in relations}

    added: list[dict[str, Any]] = []
    for extension in extensions:
        validate_extension(extension)
        if extension["registry_review"]["verdict"] not in ADMISSIBLE_REVIEW_VERDICTS:
            raise FeatureAnchorRegistryError(
                f"{extension['extension_id']}: only APPROVED extensions build a snapshot"
            )
        relation = _extension_relation(
            extension, by_feature, introduced_in_version=snapshot_id
        )
        if relation["anchor_relation_id"] in existing:
            raise FeatureAnchorRegistryError(
                f"{extension['extension_id']}: this anchor relation already exists, "
                "so the extension is a duplicate rather than supply"
            )
        existing.add(relation["anchor_relation_id"])
        added.append(relation)

    relations = sorted(
        relations + added, key=lambda row: (row["seed_id"], row["feature_id"])
    )
    scope = sorted(
        (
            {
                "seed_id": seed_id,
                "target_concept_id": seed["target_concept_id"],
                "learner_decision": seed["learner_decision"],
                "decision_granularity": seed["decision_granularity"],
                "anchor_study_unit_id": seed["anchor_study_unit_id"],
                "no_anchor_finding": seed["no_anchor_finding"],
            }
            for seed_id, seed in _seed_rows(root).items()
        ),
        key=lambda row: row["seed_id"],
    )
    return {
        "snapshot_id": snapshot_id,
        "anchor_scope": scope,
        "built_from": {
            "vocabulary": VOCABULARY_PATH,
            "vocabulary_sha256": _sha256_of_file(root, VOCABULARY_PATH),
            "stem_anchor_packs": [
                {
                    "artifact": f"{base}.stem_anchors.json",
                    "sha256": _sha256_of_file(root, f"{base}.stem_anchors.json"),
                }
                for base in SEED_PACK_BASES
            ],
            "baseline_snapshot_id": (
                None if snapshot_id == BASELINE_SNAPSHOT_ID else BASELINE_SNAPSHOT_ID
            ),
        },
        "features": features,
        "anchor_relations": relations,
        "feature_count": len(features),
        "anchor_relation_count": len(relations),
        "registry_hash": registry_hash(features, relations),
        "extension_diff": {
            "FEATURES_ADDED": 0,
            "ANCHOR_RELATIONS_ADDED": len(added),
            "added_anchor_relations": sorted(
                (
                    {
                        "anchor_relation_id": row["anchor_relation_id"],
                        "feature_id": row["feature_id"],
                        "seed_id": row["seed_id"],
                        "learner_decision": row["learner_decision"],
                        "declared_anchor_role": row["declared_anchor_role"],
                        "evidence_refs": row["evidence_refs"],
                    }
                    for row in added
                ),
                key=lambda row: row["anchor_relation_id"],
            ),
            "extension_ids": sorted(row["extension_id"] for row in extensions),
        },
    }


def build_snapshot_store(root) -> dict[str, Any]:
    """Build every canonical snapshot, in one deterministic pass."""
    extensions = load_extensions(root)
    baseline = build_snapshot(root, snapshot_id=BASELINE_SNAPSHOT_ID)
    extended = build_snapshot(
        root,
        snapshot_id=EXTENDED_SNAPSHOT_ID,
        extensions=approved_extensions(extensions),
    )
    return {
        "schema_version": "1.0",
        "scope": "QGEN_FEATURE_ANCHOR_REGISTRY_SNAPSHOTS",
        "there_is_no_latest": (
            "Snapshots are addressed by id. No consumer may resolve a snapshot "
            "implicitly, and no consumer reads this file's ordering."
        ),
        "extension_set_id": extensions["extension_set_id"],
        "snapshots": {
            BASELINE_SNAPSHOT_ID: baseline,
            EXTENDED_SNAPSHOT_ID: extended,
        },
    }


def load_snapshot(root, snapshot_id: str) -> dict[str, Any]:
    """Load one snapshot by explicit id, and verify its hash before returning it.

    There is no default and no `latest`: an implicit read is the failure mode the
    whole design exists to prevent, so asking for one raises.
    """
    if not isinstance(snapshot_id, str) or not snapshot_id:
        raise FeatureAnchorRegistryError(
            "a snapshot must be pinned by explicit id; there is no latest"
        )
    if snapshot_id.upper() in {"LATEST", "CURRENT", "HEAD"}:
        raise FeatureAnchorRegistryError(
            f"{snapshot_id} is not a snapshot id; pin an explicit snapshot"
        )
    store = _read(root, SNAPSHOTS_PATH)
    snapshot = store["snapshots"].get(snapshot_id)
    if snapshot is None:
        raise FeatureAnchorRegistryError(f"unknown feature/anchor snapshot: {snapshot_id}")
    recomputed = registry_hash(snapshot["features"], snapshot["anchor_relations"])
    if recomputed != snapshot["registry_hash"]:
        raise FeatureAnchorRegistryError(
            f"{snapshot_id}: registry hash does not match its rows"
        )
    return snapshot


def snapshot_anchor_index(
    snapshot: Mapping[str, Any], *, scope: str | None = None
) -> dict[str, list[str]]:
    """Anchor feature ids per seed, which is the join key retrieval already uses.

    The relation's identity is the concept, the learner decision and the
    granularity; `seed_id` is provenance. Because `competitor_concept_id` is
    unique across all 81 retrievable seeds and the identity tuple collides zero
    times, projecting onto the seed is lossless, and a collision is refused
    rather than merged.
    """
    index: dict[str, set[str]] = {
        row["seed_id"]: set() for row in snapshot.get("anchor_scope") or []
    }
    identities: dict[str, tuple[str, str, str]] = {
        row["seed_id"]: (
            row["target_concept_id"], row["learner_decision"], row["decision_granularity"]
        )
        for row in snapshot.get("anchor_scope") or []
    }
    for relation in snapshot["anchor_relations"]:
        seed_id = relation["seed_id"]
        limited_to = relation.get("scope_opportunity_labels")
        if limited_to is not None and scope not in limited_to:
            # An anchor relation reviewed for one decision does not anchor the
            # same competitor in another. Without a named scope it applies
            # nowhere, which is the fail-closed direction.
            continue
        identity = (
            relation["target_concept_id"],
            relation["learner_decision"],
            relation["decision_granularity"],
        )
        if identities.setdefault(seed_id, identity) != identity:
            raise FeatureAnchorRegistryError(
                f"{seed_id} carries anchor relations for two different identities"
            )
        index.setdefault(seed_id, set()).add(relation["feature_id"])
    return {seed_id: sorted(features) for seed_id, features in sorted(index.items())}


def anchor_feature_ids(
    snapshot: Mapping[str, Any],
    *,
    target_concept_id: str,
    learner_decision: str,
    scope: str | None = None,
) -> list[str]:
    """The anchors this snapshot asserts for one competitor under one decision.

    Registration is not entitlement: a feature the registry knows about anchors
    nothing until a relation says it does, for this decision.
    """
    return sorted({
        relation["feature_id"]
        for relation in snapshot["anchor_relations"]
        if relation["target_concept_id"] == target_concept_id
        and relation["learner_decision"] == learner_decision
        and (
            relation.get("scope_opportunity_labels") is None
            or scope in relation["scope_opportunity_labels"]
        )
    })


def registry_state(
    snapshot: Mapping[str, Any], state_map: Mapping[str, Any], feature_id: str
) -> str:
    """Resolve a feature's state at the registry boundary.

    The one rule this boundary enforces on its own behalf: a feature the map does
    not name is `UNKNOWN`, and no consumer may ask the registry to read that as
    `ABSENT`. A feature the registry does not know is refused rather than
    silently resolved, because an unregistered id is a contract error and not an
    unstated finding.
    """
    if feature_id not in {row["feature_id"] for row in snapshot["features"]}:
        raise FeatureAnchorRegistryError(
            f"{feature_id} is not in snapshot {snapshot['snapshot_id']}"
        )
    entry = state_map.get(feature_id)
    if entry is None:
        return "UNKNOWN"
    state = entry.get("state", entry.get("polarity"))
    if state not in REGISTRY_FEATURE_STATES:
        raise FeatureAnchorRegistryError(f"{feature_id}: unknown state {state}")
    return state


# ------------------------------------------------------------- consumer adapter


def resolve_seed_anchors(
    snapshot: Mapping[str, Any], seed_id: str, *, scope: str | None = None
) -> list[str]:
    """The anchors a pinned snapshot asserts for one curated seed.

    A seed the snapshot's scope does not contain is refused rather than silently
    given the frozen pack's row: falling back is how the two readers drifted in
    the first place. ``scope`` names the decision context, and an extension
    relation reviewed for another one does not apply here.
    """
    index = snapshot_anchor_index(snapshot, scope=scope)
    if seed_id not in index:
        raise FeatureAnchorRegistryError(
            f"{seed_id} is outside snapshot {snapshot['snapshot_id']}, so its "
            "plausibility anchors are not pinned; there is no fallback"
        )
    return list(index[seed_id])


def require_snapshot(snapshot: Mapping[str, Any] | None) -> Mapping[str, Any] | None:
    """Validate a snapshot pin a consumer passed. `None` means the frozen packs."""
    if snapshot is None:
        return None
    if not isinstance(snapshot, Mapping) or not snapshot.get("snapshot_id"):
        raise FeatureAnchorRegistryError(
            "a feature/anchor snapshot must be a loaded snapshot with an id"
        )
    if registry_hash(
        snapshot["features"], snapshot["anchor_relations"]
    ) != snapshot["registry_hash"]:
        raise FeatureAnchorRegistryError(
            f"{snapshot['snapshot_id']}: registry hash does not match its rows"
        )
    return snapshot


# ------------------------------------- Phases 16, 19, 20 and 21: gate replay

GATE_REPLAY_REPORT_PATH = "reports/qgen_feature_anchor_registry_gate_replay.json"

#: The positive control. An item an independent review scored zero on all eleven
#: dimensions, refused by the anchor contract alone. Nothing about it is edited.
POSITIVE_CONTROL_LABEL = "G2-PED-01"


def _arm_a_verdicts(root, snapshot: Mapping[str, Any] | None) -> dict[str, Any]:
    """Run the 30 frozen G2 scenarios through arm A under one anchor pin."""
    from .clinical_retrieval import retrieve_competitors
    from .retrieval_benchmark import build_frozen_reference_set, load_scenarios

    reference = build_frozen_reference_set(Path(root).resolve())
    rows: dict[str, Any] = {}
    for scenario in load_scenarios(Path(root).resolve()):
        label = scenario["wave_label"]
        result = retrieve_competitors(
            None, scenario, arm="CURRENT_LIBRARY", root=Path(root).resolve(),
            feature_anchor_snapshot=snapshot, feature_anchor_scope=label,
        )
        retrieval = result["retrieval"]
        ranked = [row["seed_id"] for row in retrieval["ranked_competitors"]]
        excluded: dict[str, list[str]] = {}
        for row in retrieval["excluded"]:
            excluded.setdefault(row["rule"], []).append(row["seed_id"])
        known_anchorless = set(
            reference["negative_controls"]["KNOWN_ANCHORLESS"].get(label, [])
        )
        known_second_key = set(
            reference["negative_controls"]["KNOWN_SECOND_KEY"].get(label, [])
        )
        rows[label] = {
            "ranked": ranked,
            "excluded_by_rule": {
                rule: sorted(seeds) for rule, seeds in sorted(excluded.items())
            },
            "reaches_three_viable": len(ranked) >= 3,
            "known_anchorless_returned": sorted(known_anchorless & set(ranked)),
            "known_second_key_returned": sorted(known_second_key & set(ranked)),
            "known_anchorless_controls": len(known_anchorless),
            "known_second_key_controls": len(known_second_key),
            "reference_admitted_preserved": sorted(
                set(reference["reference_admitted_competitors"].get(label, []))
                & set(ranked)
            ),
            "reference_admitted": sorted(
                reference["reference_admitted_competitors"].get(label, [])
            ),
        }
    return rows


def build_historical_regression(root) -> dict[str, Any]:
    """Phase 16. The baseline snapshot must reproduce behaviour, not approximate it."""
    baseline = load_snapshot(root, BASELINE_SNAPSHOT_ID)
    extended = load_snapshot(root, EXTENDED_SNAPSHOT_ID)
    unpinned = _arm_a_verdicts(root, None)
    pinned_v1 = _arm_a_verdicts(root, baseline)
    pinned_v2 = _arm_a_verdicts(root, extended)

    extension_admissions = {
        (row["scope"], row["seed_id"])
        for extension in approved_extensions(load_extensions(root))
        for row in [
            {"scope": scope, "seed_id": extension["seed_id"]}
            for scope in extension["scope_opportunity_labels"]
        ]
    }

    def _totals(rows: Mapping[str, Any]) -> dict[str, int]:
        return {
            "OPPORTUNITIES_WITH_THREE_VIABLE": sum(
                1 for row in rows.values() if row["reaches_three_viable"]
            ),
            "KNOWN_ANCHORLESS_CONTROLS": sum(
                row["known_anchorless_controls"] for row in rows.values()
            ),
            "KNOWN_ANCHORLESS_RETURNED": sum(
                len(row["known_anchorless_returned"]) for row in rows.values()
            ),
            "KNOWN_ANCHORLESS_RETURNED_BY_AN_APPROVED_EXTENSION": sum(
                1
                for label, row in rows.items()
                for seed_id in row["known_anchorless_returned"]
                if (label, seed_id) in extension_admissions
            ),
            "KNOWN_ANCHORLESS_RETURNED_WITHOUT_AN_APPROVED_EXTENSION": sum(
                1
                for label, row in rows.items()
                for seed_id in row["known_anchorless_returned"]
                if (label, seed_id) not in extension_admissions
            ),
            "KNOWN_SECOND_KEY_CONTROLS": sum(
                row["known_second_key_controls"] for row in rows.values()
            ),
            "KNOWN_SECOND_KEY_RETURNED": sum(
                len(row["known_second_key_returned"]) for row in rows.values()
            ),
            "SECOND_KEY_REFUSALS": sum(
                len(row["excluded_by_rule"].get("ADM_3", [])) for row in rows.values()
            ),
            "ANCHOR_FLOOR_REFUSALS": sum(
                len(row["excluded_by_rule"].get("SAF_1", [])) for row in rows.values()
            ),
            "ACCEPTED_CONTROLS": sum(
                len(row["reference_admitted"]) for row in rows.values()
            ),
            "ACCEPTED_CONTROLS_PRESERVED": sum(
                len(row["reference_admitted_preserved"]) for row in rows.values()
            ),
        }

    v2_differences = sorted(
        label for label in unpinned
        if unpinned[label]["ranked"] != pinned_v2[label]["ranked"]
    )
    scoped_labels = {
        scope
        for extension in approved_extensions(load_extensions(root))
        for scope in extension["scope_opportunity_labels"]
    }
    return {
        "population": "the 30 frozen G2 opportunities, through retrieval benchmark arm A",
        "BASELINE_REPRODUCES_LEGACY_EXACTLY": unpinned == pinned_v1,
        "what_unchanged_means_here": (
            "Two things, and the strict equality is reported beside them rather "
            "than replaced by them. First, the baseline snapshot must reproduce the "
            "legacy frozen packs exactly, on every one of the 30 opportunities: an "
            "import that quietly reinterpreted the frozen data would fail here. "
            "Second, under the extended snapshot no opportunity's ranked set may "
            "move except one an approved extension names in its own reviewed scope. "
            "An extension that moved nothing anywhere would mean the milestone did "
            "nothing; an extension that moved an opportunity no reviewer considered "
            "is the leak the strict rule caught in G2-PSY-04 and the scope fixed."
        ),
        "STRICT_EQUALITY_LEGACY_TO_EXTENDED": unpinned == pinned_v2,
        "EVERY_MOVED_OPPORTUNITY_IS_IN_AN_APPROVED_EXTENSION_SCOPE": all(
            label in scoped_labels for label in v2_differences
        ),
        "approved_extension_scopes": sorted(scoped_labels),
        "legacy_unpinned": _totals(unpinned),
        "pinned_baseline_v1": _totals(pinned_v1),
        "pinned_extended_v2": _totals(pinned_v2),
        "opportunities_whose_ranked_set_moves_under_v2": v2_differences,
        "per_opportunity": {
            label: {
                "legacy_unpinned": unpinned[label],
                "pinned_baseline_v1": pinned_v1[label],
                "pinned_extended_v2": pinned_v2[label],
            }
            for label in sorted(unpinned)
        },
    }


def build_gate_replay(root) -> dict[str, Any]:
    """Phases 19 to 21. The same frozen-five supply results, three anchor pins."""
    from .contrast_supply import run_acquisition_wave, run_frozen5_replay

    baseline = load_snapshot(root, BASELINE_SNAPSHOT_ID)
    extended = load_snapshot(root, EXTENDED_SNAPSHOT_ID)
    wave = run_acquisition_wave(root)

    replays = {
        "LEGACY_FROZEN_STEM_ANCHOR_PACK": run_frozen5_replay(root, wave),
        BASELINE_SNAPSHOT_ID: run_frozen5_replay(
            root, wave, feature_anchor_snapshot=baseline
        ),
        EXTENDED_SNAPSHOT_ID: run_frozen5_replay(
            root, wave, feature_anchor_snapshot=extended
        ),
    }

    def _gates(replay: Mapping[str, Any]) -> dict[str, Any]:
        return {
            row["opportunity_label"]: row["production_gate"]
            for row in replay["results"] if row.get("production_gate")
        }

    gates = {name: _gates(replay) for name, replay in replays.items()}

    approved = approved_extensions(load_extensions(root))
    added = {row["anchor_relation_id"] for row in extended["extension_diff"][
        "added_anchor_relations"
    ]}
    added_rows = [
        row for row in extended["anchor_relations"] if row["anchor_relation_id"] in added
    ]

    # Visibility, measured at each of the three consumers rather than asserted.
    visible_to_v2 = [
        row for row in added_rows
        if any(
            row["feature_id"] in snapshot_anchor_index(extended, scope=scope)[
                row["seed_id"]
            ]
            for scope in row["scope_opportunity_labels"]
        )
    ]
    visible_to_retrieval = [
        row for row in added_rows
        if any(
            row["feature_id"] in {
                entry["seed_id"]: entry
                for entry in _library_rows(
                    root, feature_anchor_snapshot=extended, feature_anchor_scope=scope
                )
            }[row["seed_id"]]["plausibility_anchor_feature_ids"]
            for scope in row["scope_opportunity_labels"]
        )
    ]
    visible_to_saf1 = _saf1_visibility(root, added_rows, gates)

    regression = build_historical_regression(root)
    control = {
        name: gate.get(POSITIVE_CONTROL_LABEL) for name, gate in gates.items()
    }
    legacy_control = control["LEGACY_FROZEN_STEM_ANCHOR_PACK"]
    new_control = control[EXTENDED_SNAPSHOT_ID]

    reconciliation = {
        "APPROVED_EXTENSIONS_VISIBLE_TO_V2": f"{len(visible_to_v2)}/{len(added_rows)}",
        "APPROVED_EXTENSIONS_VISIBLE_TO_SAF1": (
            f"{len(visible_to_saf1)}/{len(added_rows)}"
        ),
        "APPROVED_EXTENSIONS_VISIBLE_TO_PROFILE_RETRIEVAL": (
            f"{len(visible_to_retrieval)}/{len(added_rows)}"
        ),
        "HISTORICAL_CONTROLS_UNCHANGED": (
            regression["BASELINE_REPRODUCES_LEGACY_EXACTLY"]
            and regression["EVERY_MOVED_OPPORTUNITY_IS_IN_AN_APPROVED_EXTENSION_SCOPE"]
            and regression["legacy_unpinned"]["KNOWN_SECOND_KEY_RETURNED"]
            == regression["pinned_extended_v2"]["KNOWN_SECOND_KEY_RETURNED"]
            and regression["pinned_extended_v2"][
                "KNOWN_ANCHORLESS_RETURNED_WITHOUT_AN_APPROVED_EXTENSION"
            ] == 0
        ),
        "NO_REJECTED_OR_UNCERTAIN_EXTENSION_IN_THE_SNAPSHOT": (
            len(approved) == len(added_rows)
            and all(
                row["registry_review"]["verdict"] == "APPROVED" for row in approved
            )
        ),
        "NO_SAFETY_GATE_WEAKENED": _no_gate_weakened(regression),
    }
    limbs = {
        "all_approved_anchors_visible_to_v2": len(visible_to_v2) == len(added_rows),
        "the_same_anchors_visible_to_saf1": len(visible_to_saf1) == len(added_rows),
        "the_same_anchors_available_to_profile_retrieval": (
            len(visible_to_retrieval) == len(added_rows)
        ),
        "historical_controls_unchanged": reconciliation["HISTORICAL_CONTROLS_UNCHANGED"],
        "no_rejected_or_uncertain_extension_entered": reconciliation[
            "NO_REJECTED_OR_UNCERTAIN_EXTENSION_IN_THE_SNAPSHOT"
        ],
        "no_safety_gate_weakened": reconciliation["NO_SAFETY_GATE_WEAKENED"],
    }
    return {
        "schema_version": "1.0",
        "scope": "QGEN_FEATURE_ANCHOR_REGISTRY_GATE_REPLAY",
        "starting_commit": "14f4508",
        "llm_api_calls": 0,
        "what_varied": (
            "The feature/anchor snapshot the production gate consumes, and nothing "
            "else. Same frozen-five supply results, same opportunities, same keys, "
            "same evidence, same contrast relations, same difficulty, same item."
        ),
        "snapshots": {
            BASELINE_SNAPSHOT_ID: {
                "registry_hash": baseline["registry_hash"],
                "features": baseline["feature_count"],
                "anchor_relations": baseline["anchor_relation_count"],
            },
            EXTENDED_SNAPSHOT_ID: {
                "registry_hash": extended["registry_hash"],
                "features": extended["feature_count"],
                "anchor_relations": extended["anchor_relation_count"],
            },
        },
        "historical_regression": regression,
        "frozen_five_gates": gates,
        "visibility": {
            "APPROVED_ANCHOR_RELATIONS": len(added_rows),
            "visible_to_v2": sorted(row["anchor_relation_id"] for row in visible_to_v2),
            "visible_to_saf1": sorted(
                row["anchor_relation_id"] for row in visible_to_saf1
            ),
            "visible_to_profile_retrieval": sorted(
                row["anchor_relation_id"] for row in visible_to_retrieval
            ),
            "the_sets_reconcile": (
                {row["anchor_relation_id"] for row in visible_to_v2}
                == {row["anchor_relation_id"] for row in visible_to_saf1}
                == {row["anchor_relation_id"] for row in visible_to_retrieval}
            ),
        },
        "positive_control": {
            "opportunity_label": POSITIVE_CONTROL_LABEL,
            "item_unchanged": True,
            "what_was_not_touched": ["stem", "options", "key", "evidence", "rationale"],
            "G2_PED_01_LEGACY_SAF1": (
                "PASS" if legacy_control and legacy_control["post_stem_3_viable"]
                else "FAIL"
            ),
            "G2_PED_01_NEW_SAF1": (
                "PASS" if new_control and new_control["post_stem_3_viable"] else "FAIL"
            ),
            "legacy_gate": legacy_control,
            "new_gate": new_control,
        },
        "CONTRACT_RECONCILIATION": "PASS" if all(limbs.values()) else "FAIL",
        "precommitted_limbs": limbs,
        "reconciliation": reconciliation,
    }


def _library_rows(
    root,
    *,
    feature_anchor_snapshot: Mapping[str, Any] | None,
    feature_anchor_scope: str | None = None,
):
    from .contrast_first_pilot import load_curated_candidates

    return load_curated_candidates(
        root,
        feature_anchor_snapshot=feature_anchor_snapshot,
        feature_anchor_scope=feature_anchor_scope,
    )


def _saf1_visibility(
    root, added_rows: Sequence[Mapping[str, Any]], gates: Mapping[str, Any]
) -> list[dict[str, Any]]:
    """An anchor is visible to SAF_1 only if the rule stops refusing its seed.

    Measured from the gate's own verdicts rather than from the index, because an
    anchor present in a row that `SAF_1` still refuses would not be visible in any
    sense that matters.
    """
    legacy = gates["LEGACY_FROZEN_STEM_ANCHOR_PACK"]
    extended = gates[EXTENDED_SNAPSHOT_ID]
    visible: list[dict[str, Any]] = []
    for row in added_rows:
        for label, gate in extended.items():
            refused_before = row["seed_id"] in (
                legacy.get(label, {}).get("excluded_by_rule", {}).get("SAF_1", [])
            )
            refused_now = row["seed_id"] in gate["excluded_by_rule"].get("SAF_1", [])
            if refused_before and not refused_now:
                visible.append(row)
                break
        else:
            # The seed reaches no realized stem in this replay, so `SAF_1` never
            # judged it. Fall back to the index, and say which test was used.
            snapshot = load_snapshot(root, EXTENDED_SNAPSHOT_ID)
            reached = any(
                row["feature_id"] in {
                    entry["seed_id"]: entry
                    for entry in _library_rows(
                        root, feature_anchor_snapshot=snapshot,
                        feature_anchor_scope=scope,
                    )
                }[row["seed_id"]]["plausibility_anchor_feature_ids"]
                for scope in row["scope_opportunity_labels"]
            )
            if reached:
                visible.append({**row, "measured_by": "INDEX_ROW_NO_REALIZED_STEM"})
    return visible


def _no_gate_weakened(regression: Mapping[str, Any]) -> bool:
    """No control the gate used to refuse is now admitted, except by an approved
    extension in the decision context that extension was reviewed for.

    The distinction matters and is not a softening after the fact. The
    `KNOWN_ANCHORLESS` list is *derived from the old floor's own verdicts*, so for
    the one competitor an independent review approved an evidence-cited anchor
    for, "still refused" and "the milestone did nothing" are the same statement.
    The non-circular part of the control set -- every anchorless control no
    extension names, and all eight second-key controls -- must stay at zero, and
    the strict count is reported beside this one rather than replaced by it.
    """
    legacy = regression["legacy_unpinned"]
    extended = regression["pinned_extended_v2"]
    return (
        extended["KNOWN_ANCHORLESS_RETURNED_WITHOUT_AN_APPROVED_EXTENSION"] == 0
        and legacy["KNOWN_ANCHORLESS_RETURNED"] == 0
        and extended["KNOWN_SECOND_KEY_RETURNED"] == legacy["KNOWN_SECOND_KEY_RETURNED"] == 0
        and extended["SECOND_KEY_REFUSALS"] == legacy["SECOND_KEY_REFUSALS"]
        and extended["ACCEPTED_CONTROLS_PRESERVED"] >= legacy["ACCEPTED_CONTROLS_PRESERVED"]
    )
