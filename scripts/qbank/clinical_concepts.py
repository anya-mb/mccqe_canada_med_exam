"""Normalized clinical concepts, aliases and ambiguity handling.

Seeded only from vocabularies the repository already owns and has already
reviewed: the curated contrast seeds, the frozen canonical stem-feature
vocabulary, the Toronto Notes TOC topics and the study-unit titles. Nothing here
invents a clinical entity, and nothing here decides that two entities are the
same thing on the strength of how similar their names look.

The single failure this layer must not have is merging medically distinct
entities, so every rule is conservative and stated:

- a concept's type is read off the closed option-set archetype vocabulary that
  already governs admissibility, never inferred from its name;
- aliases are produced by three named morphological rules and by nothing else;
- a surface form owned by more than one concept resolves to MULTI_MATCH and is
  never silently assigned to one of them.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Iterable

from .errors import QbankError
from .option_set_admissibility import OPTION_SET_ARCHETYPES
from .paths import resolve_root_path


class ClinicalConceptError(QbankError):
    """A vocabulary source, a concept typing, or a resolution is unusable."""


CONCEPT_TYPES = ("CONDITION", "FINDING", "ACTION", "POPULATION", "TOPIC")
AMBIGUITY_STATES = ("RESOLVED", "MULTI_MATCH", "UNRESOLVED")
ALIAS_RULES = ("EXACT", "PLURAL_S", "HYPHEN_FOLDED")

# The one archetype whose options are diagnostic entities. Everything else on the
# closed vocabulary demands an act -- an investigation, a next step, a management
# strategy, a disposition, a statistical reading, an ethical or a legal action.
CONDITION_ARCHETYPES = frozenset({"DIAGNOSIS_SET"})

SEED_PACK_RELATIVE_PATHS = (
    "research/qgen/generalization/competitive_contrast_seed_pack_r4.json",
    "research/qgen/generalization/competitive_contrast_seed_pack_g2_targeted.json",
    "research/qgen/generalization/competitive_contrast_seed_pack_g2_extensions.json",
)
STEM_FEATURE_VOCABULARY_RELATIVE_PATH = (
    "research/qgen/safe_yield/g2_stem_feature_vocabulary.json"
)
TOC_RELATIVE_PATH = "research/tn2025/toc_inventory.json"
SCOPE_RELATIVE_PATH = "research/scope/master_scope_crosswalk.json"

_NON_LABEL = re.compile(r"[^0-9a-z%]+")


def _load(root: Path, relative: str) -> Any:
    path = resolve_root_path(Path(root).resolve(), relative)
    if not path.is_file():
        raise ClinicalConceptError(f"vocabulary source is unavailable: {relative}")
    return json.loads(path.read_text())


# ------------------------------------------------------------------- typing


def concept_type_for_archetypes(archetypes: Iterable[str]) -> str:
    """Type a curated competitor concept from the archetypes it may populate.

    Fails closed rather than choosing. A concept that can populate both a
    diagnosis set and an action set is either two concepts or a tagging error,
    and both cases need a person, not a default.
    """
    values = list(archetypes)
    if not values:
        raise ClinicalConceptError("a concept carries no option-set archetype to type it")
    unknown = sorted(set(values) - set(OPTION_SET_ARCHETYPES))
    if unknown:
        raise ClinicalConceptError(f"unknown option-set archetype: {', '.join(unknown)}")
    families = {
        "CONDITION" if value in CONDITION_ARCHETYPES else "ACTION" for value in values
    }
    if len(families) != 1:
        raise ClinicalConceptError(
            "a concept spans both the diagnostic and the action families and cannot "
            f"be typed deterministically: {sorted(set(values))}"
        )
    return families.pop()


# ------------------------------------------------------------- normalization


def normalize_surface_form(text: str) -> str:
    """Fold case, punctuation and spacing, and nothing clinical.

    Deliberately shallow. Stemming or synonym folding here would merge
    hyperkalemia with hypokalemia and hypertonic with hypotonic saline, which is
    exactly the mistake this layer exists to avoid.
    """
    return " ".join(_NON_LABEL.sub(" ", str(text).lower()).split())


# ---------------------------------------------------------------- vocabulary


def _concept_id(prefix: str, label: str) -> str:
    import hashlib

    digest = hashlib.sha256(normalize_surface_form(label).encode("utf-8")).hexdigest()
    return f"{prefix}-{digest[:16]}"


def build_concept_vocabulary(root: Path) -> dict[str, Any]:
    """Build the normalized concept vocabulary from existing canonical artifacts."""
    root = Path(root).resolve()
    concepts: dict[str, dict[str, Any]] = {}
    unresolved: list[dict[str, Any]] = []

    def register(concept: dict[str, Any]) -> dict[str, Any]:
        existing = concepts.get(concept["concept_id"])
        if existing is None:
            concepts[concept["concept_id"]] = concept
            return concept
        if existing["concept_type"] != concept["concept_type"]:
            # Same normalized label, two different clinical types. Never merged.
            unresolved.append({
                "normalized_label": normalize_surface_form(concept["preferred_label"]),
                "reason": "TYPE_CONFLICT_BETWEEN_VOCABULARY_SOURCES",
                "types": sorted({existing["concept_type"], concept["concept_type"]}),
            })
            return existing
        # A TOC topic and a study-unit title carrying the identical normalized label
        # name the same textbook topic in two structural registers. Keeping them
        # apart would report 972 false MULTI_MATCHes and hide the real ones, so the
        # structural provenance is accumulated onto one discovery concept. This is
        # deduplicating a string, not deciding that two clinical entities are one.
        if existing["concept_type"] == "TOPIC":
            existing["provenance"].setdefault("locations", []).append(
                {"vocabulary_source": concept["vocabulary_source"], **concept["provenance"]}
            )
        return existing

    # 1. Curated contrast seeds -- the only already-reviewed competitor concepts.
    for relative in SEED_PACK_RELATIVE_PATHS:
        pack = _load(root, relative)
        enrichment = _load(root, relative.replace(".json", ".enrichment.json"))
        tags = {seed["seed_id"]: seed for seed in enrichment.get("seeds", [])}
        for target in pack.get("targets", []):
            for seed in target.get("seeds", []):
                seed_id = seed.get("seed_id")
                tag = tags.get(seed_id)
                if tag is None:
                    continue
                label = seed.get("competitor_concept")
                if not label:
                    continue
                try:
                    concept_type = concept_type_for_archetypes(
                        tag.get("option_set_archetypes") or []
                    )
                except ClinicalConceptError as exc:
                    unresolved.append({
                        "seed_id": seed_id, "reason": "UNTYPEABLE", "detail": str(exc)
                    })
                    continue
                concept_id = seed.get("competitor_concept_id") or _concept_id("CONCEPT", label)
                registered = register({
                    "concept_id": concept_id,
                    "preferred_label": label,
                    "concept_type": concept_type,
                    "vocabulary_source": "CURATED_CONTRAST_SEED",
                    "provenance": {
                        "seed_ids": [],
                        "study_unit_id": seed.get("competitor_study_unit_id"),
                        "decision_granularity": seed.get("competitor_decision_granularity"),
                        "option_set_archetypes": sorted(tag.get("option_set_archetypes") or []),
                        "source_packs": [],
                    },
                })
                provenance = registered["provenance"]
                if seed_id not in provenance["seed_ids"]:
                    provenance["seed_ids"].append(seed_id)
                if relative not in provenance["source_packs"]:
                    provenance["source_packs"].append(relative)

    # 2. The frozen canonical stem-feature vocabulary -- the FINDING nodes.
    vocabulary = _load(root, STEM_FEATURE_VOCABULARY_RELATIVE_PATH)
    if not vocabulary.get("frozen"):
        raise ClinicalConceptError("the stem-feature vocabulary must be frozen before use")
    for anchor in vocabulary.get("anchors", []):
        study_unit = anchor["anchor_study_unit_id"]
        for feature in anchor.get("features", []):
            register({
                "concept_id": feature["stem_feature_id"],
                "preferred_label": feature["normalized_feature"],
                "concept_type": "FINDING",
                "vocabulary_source": "CANONICAL_STEM_FEATURE_VOCABULARY",
                "provenance": {
                    "stem_feature_id": feature["stem_feature_id"],
                    "anchor_study_unit_id": study_unit,
                    "clinical_role": feature.get("clinical_role"),
                },
            })

    # 3 and 4. Toronto Notes topics and study-unit titles. Discovery vocabulary
    # only: these name where a concept is discussed, never that a claim is current.
    for node in _load(root, TOC_RELATIVE_PATH)["nodes"]:
        title = (node.get("title") or "").strip()
        if not title or node.get("structural_type") != "topic":
            continue
        register({
            "concept_id": _concept_id("TOPIC", title),
            "preferred_label": title,
            "concept_type": "TOPIC",
            "vocabulary_source": "TN_TOC_TOPIC",
            "provenance": {
                "tn_node_id": node["node_id"],
                "chapter_code": node.get("chapter_code"),
                "start_pdf_page": node.get("start_pdf_page"),
                "end_pdf_page": node.get("end_pdf_page"),
                "authority_role": "TOPIC_DISCOVERY_SOURCE",
                "locations": [],
            },
        })
    for entry in _load(root, SCOPE_RELATIVE_PATH)["entries"]:
        title = (entry.get("study_unit_title") or "").strip()
        if not title:
            continue
        register({
            "concept_id": _concept_id("TOPIC", title),
            "preferred_label": title,
            "concept_type": "TOPIC",
            "vocabulary_source": "STUDY_UNIT_TITLE",
            "provenance": {
                "study_unit_id": entry["study_unit_id"],
                "chapter_code": entry.get("chapter_code"),
                "authority_role": "TOPIC_DISCOVERY_SOURCE",
            },
        })

    return {
        "schema_version": "1.0",
        "scope": "NORMALIZED_CLINICAL_CONCEPT_VOCABULARY",
        "concepts": sorted(concepts.values(), key=lambda concept: concept["concept_id"]),
        "unresolved": sorted(unresolved, key=lambda row: json.dumps(row, sort_keys=True)),
    }


# ------------------------------------------------------------------ aliases


def build_alias_index(vocabulary: dict[str, Any]) -> dict[str, Any]:
    """Build the surface-form index under three stated morphological rules."""
    aliases: dict[str, list[dict[str, Any]]] = {}

    def add(surface: str, concept_id: str, rule: str) -> None:
        normalized = normalize_surface_form(surface)
        if not normalized:
            return
        bucket = aliases.setdefault(normalized, [])
        if any(entry["concept_id"] == concept_id for entry in bucket):
            return
        bucket.append({"concept_id": concept_id, "rule": rule})

    for concept in vocabulary["concepts"]:
        label = concept["preferred_label"]
        concept_id = concept["concept_id"]
        add(label, concept_id, "EXACT")
        normalized = normalize_surface_form(label)
        if normalized.endswith("s") and len(normalized) > 4:
            add(normalized[:-1], concept_id, "PLURAL_S")
        else:
            add(normalized + "s", concept_id, "PLURAL_S")
        if "-" in label:
            add(label.replace("-", " "), concept_id, "HYPHEN_FOLDED")

    return {
        "aliases": {key: sorted(value, key=lambda row: row["concept_id"])
                    for key, value in sorted(aliases.items())},
        "concepts": {concept["concept_id"]: concept for concept in vocabulary["concepts"]},
    }


def resolve_surface_form(index: dict[str, Any], surface: str) -> dict[str, Any]:
    """Resolve a surface form, failing closed on ambiguity rather than choosing."""
    normalized = normalize_surface_form(surface)
    entries = index["aliases"].get(normalized)
    if not entries:
        return {"state": "UNRESOLVED", "normalized_surface_form": normalized}
    if len(entries) > 1:
        return {
            "state": "MULTI_MATCH",
            "normalized_surface_form": normalized,
            "candidate_concept_ids": sorted(entry["concept_id"] for entry in entries),
        }
    return {
        "state": "RESOLVED",
        "normalized_surface_form": normalized,
        "concept_id": entries[0]["concept_id"],
        "rule": entries[0]["rule"],
    }


def detect_mentions(index: dict[str, Any], text: str) -> list[dict[str, Any]]:
    """Detect word-bounded concept mentions in normalized text.

    Exact token-sequence matching only. A substring match would happily find
    "pulmonary embolism" inside "prepulmonary embolismic", so matching is anchored
    to token boundaries rather than to character offsets in the raw string.
    """
    normalized = normalize_surface_form(text)
    tokens = normalized.split()
    if not tokens:
        return []
    starts: list[int] = []
    cursor = 0
    for token in tokens:
        cursor = normalized.index(token, cursor)
        starts.append(cursor)
        cursor += len(token)

    by_length: dict[int, list[str]] = {}
    for alias in index["aliases"]:
        by_length.setdefault(len(alias.split()), []).append(alias)

    hits: list[dict[str, Any]] = []
    for length, candidates in sorted(by_length.items()):
        lookup = set(candidates)
        for position in range(0, len(tokens) - length + 1):
            window = " ".join(tokens[position:position + length])
            if window not in lookup:
                continue
            for entry in index["aliases"][window]:
                hits.append({
                    "concept_id": entry["concept_id"],
                    "rule": entry["rule"],
                    "matched_surface_form": window,
                    "start": starts[position],
                    "end": starts[position + length - 1] + len(tokens[position + length - 1]),
                })
    return sorted(hits, key=lambda hit: (hit["start"], hit["concept_id"]))
