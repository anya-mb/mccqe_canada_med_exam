"""Reproducible deterministic builders for the V3/cache/Transfer milestone."""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path
from typing import Any

from .contrast_supply_v3 import (
    DISCOVERY_V3_VERSION,
    V3_CANDIDATE_BUDGET,
    build_global_candidate_catalogue,
    canonical_content_sha256,
    discover_global_typed_candidates,
)


LEGACY_GRANULARITY_NORMALIZATION = {
    "SINGLE_DIAGNOSIS": "DIAGNOSIS",
    "SINGLE_NEXT_ASSESSMENT": "DIAGNOSTIC_TEST",
    "SINGLE_NEXT_INVESTIGATION": "DIAGNOSTIC_TEST",
    "SINGLE_NEXT_DIAGNOSTIC_STEP": "DIAGNOSTIC_TEST",
    "INITIAL_TREATMENT_PLAN": "MANAGEMENT_STRATEGY",
    "COMPLETE_MANAGEMENT_STRATEGY": "MANAGEMENT_STRATEGY",
}

BUILD12_KEY_ALIASES = {
    "RDY-MED-01": ["urgent escalation", "critical care", "intubation"],
    "RDY-PED-04": ["glucose", "ketones", "point-of-care glucose and ketones"],
    "RDY-OBGYN-01": ["empiric broad-spectrum treatment", "antibiotics"],
    "RDY-SURG-03": ["thoracic point-of-care ultrasound", "POCUS"],
    "RDY-SURG-05": ["elective laparoscopic cholecystectomy", "elective surgical referral"],
    "RDY-PSY-03": ["schizophrenia"],
    "RDY-PHELO-02": ["primary prevention", "secondary prevention", "tertiary prevention"],
    "RDY-PHELO-08": ["capacity assessment", "assess capacity"],
}


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def _write(path: Path, value: dict[str, Any]) -> None:
    value["content_sha256"] = canonical_content_sha256(value)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def reviewed_identity_inputs(root: Path) -> list[dict[str, Any]]:
    reviewed: list[dict[str, Any]] = []
    generalization = root / "research/qgen/generalization"
    for stem in (
        "competitive_contrast_seed_pack_r4",
        "competitive_contrast_seed_pack_g2_extensions",
        "competitive_contrast_seed_pack_g2_targeted",
    ):
        pack_path = generalization / f"{stem}.json"
        if not pack_path.exists():
            continue
        pack = _load(pack_path)
        enrichment_path = generalization / f"{stem}.enrichment.json"
        enrichment = _load(enrichment_path) if enrichment_path.exists() else {"seeds": []}
        typed = {row["seed_id"]: row for row in enrichment.get("seeds", [])}
        for target in pack.get("targets", []):
            for seed in target.get("seeds", []):
                if seed.get("independent_seed_review", {}).get("verdict") not in {"PASS", "APPROVED"}:
                    continue
                typing = typed.get(seed["seed_id"], {})
                granularity = seed.get("competitor_decision_granularity") or target.get("decision_granularity")
                granularity = LEGACY_GRANULARITY_NORMALIZATION.get(granularity, granularity)
                reviewed.append({
                    "candidate_id": seed["competitor_concept_id"],
                    "normalized_label": seed["competitor_concept"],
                    "aliases": [],
                    "study_unit_ids": [seed["competitor_study_unit_id"]] if seed.get("competitor_study_unit_id") else [],
                    "semantic_families": [seed.get("competitor_semantic_category", "")],
                    "response_classes": typing.get("response_class_tokens", []),
                    "decision_granularities": [granularity] if granularity else [],
                    "provenance": [{"source": "INDEPENDENTLY_APPROVED_SEED", "pack_id": pack.get("pack_id"), "seed_id": seed["seed_id"]}],
                })

    aom = _load(root / "research/qgen/onboarding/v6_development_seed_pack.json")
    for target in aom["targets"]:
        for seed in target["seeds"]:
            if seed.get("independent_seed_review", {}).get("verdict") != "APPROVED":
                continue
            reviewed.append({
                "candidate_id": seed["competitor_concept_id"],
                "normalized_label": seed["preferred_label"],
                "aliases": [],
                "study_unit_ids": [seed["competitor_study_unit_id"]],
                "semantic_families": [seed["competitor_semantic_category"]],
                "response_classes": [seed["response_class"]],
                "decision_granularities": [seed["competitor_decision_granularity"]],
                "provenance": [{"source": "INDEPENDENTLY_APPROVED_AOM_CONTROL", "pack_id": aom["pack_id"], "seed_id": seed["seed_id"]}],
            })

    pack = _load(root / "research/qgen/contrast_supply/development_12_seed_pack_v2.json")
    relations = {row["relation_id"]: row for row in pack["relations_authored"]}
    semantics = _load(root / "research/qgen/contrast_supply/development_12_opportunity_semantics_v1.json")
    study_units = {row["development_id"]: row["study_unit_id"] for row in semantics["opportunities"]}
    for seed in pack["seeds"]:
        relation = relations[seed["relation_id"]]
        reviewed.append({
            "candidate_id": seed["candidate_id"],
            "normalized_label": relation["candidate_canonical_identity"],
            "aliases": [],
            "source_ids": [seed["anchor_id"]],
            "study_unit_ids": [study_units[seed["opportunity_id"]]],
            "semantic_families": [seed["response_class"]],
            "response_classes": [seed["response_class"]],
            "decision_granularities": [seed["decision_granularity"]],
            "provenance": [{"source": "REUSABLE_CONTRAST_CACHE_V1", "seed_id": seed["seed_id"], "relation_id": seed["relation_id"]}],
        })
    return reviewed


def build_catalogue(root: Path) -> dict[str, Any]:
    connection = sqlite3.connect(root / "derived/tn_index/tn_index.sqlite3")
    concepts = build_global_candidate_catalogue(connection, reviewed_identities=reviewed_identity_inputs(root))
    value = {
        "schema_version": "GLOBAL_CANDIDATE_CONCEPT_CATALOGUE_V1",
        "scope": "STRUCTURAL_AND_CANONICAL_CANDIDATE_IDENTITIES_NOT_APPROVED_DISTRACTOR_LIBRARY",
        "source_policy": "Canonical concepts, concept mentions, structural TOC metadata, and independently approved seed identities only; no chunk prose.",
        "concept_count": len(concepts),
        "typed_concept_count": sum(bool(row["response_classes"]) for row in concepts),
        "concepts": concepts,
    }
    _write(root / "research/qgen/contrast_supply/global_candidate_concept_catalogue_v1.json", value)
    return value


def build_build12_discovery(root: Path) -> dict[str, Any]:
    catalogue = _load(root / "research/qgen/contrast_supply/global_candidate_concept_catalogue_v1.json")
    semantics = _load(root / "research/qgen/contrast_supply/development_12_opportunity_semantics_v1.json")
    connection = sqlite3.connect(root / "derived/tn_index/tn_index.sqlite3")
    chapters = dict(connection.execute("SELECT study_unit_id, chapter_code FROM study_units"))
    by_opportunity = []
    for source in semantics["opportunities"]:
        if not source.get("prerequisite_ready"):
            continue
        opportunity = dict(source)
        opportunity["chapter_code"] = chapters.get(source["study_unit_id"])
        opportunity["key_aliases"] = BUILD12_KEY_ALIASES[source["development_id"]]
        opportunity["semantic_families"] = []
        candidates = discover_global_typed_candidates(catalogue["concepts"], opportunity=opportunity)
        by_opportunity.append({
            "development_id": source["development_id"],
            "study_unit_id": source["study_unit_id"],
            "demanded_response_class": source["demanded_response_class"],
            "decision_granularity": source["decision_granularity"],
            "candidate_count": len(candidates),
            "candidates": candidates,
        })
    value = {
        "schema_version": "BUILD_12_DISCOVERY_V3_WAVE_V1",
        "scope": "BUILD_12_ONLY",
        "discovery_v3_version": DISCOVERY_V3_VERSION,
        "catalogue_content_sha256": catalogue["content_sha256"],
        "candidate_budget_per_opportunity": V3_CANDIDATE_BUDGET,
        "waves_per_opportunity": 1,
        "frozen_before_semantic_review": True,
        "opportunities": by_opportunity,
        "unique_candidate_count": sum(row["candidate_count"] for row in by_opportunity),
    }
    _write(root / "research/qgen/contrast_supply/build_12_discovery_v3.json", value)
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--stage", choices=("catalogue", "build12"), required=True)
    args = parser.parse_args()
    value = build_catalogue(args.root) if args.stage == "catalogue" else build_build12_discovery(args.root)
    print(json.dumps({"content_sha256": value["content_sha256"], "stage": args.stage}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
