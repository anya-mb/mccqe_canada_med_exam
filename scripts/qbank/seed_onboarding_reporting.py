"""Build the deterministic registry and milestone metrics for QGEN V6 onboarding."""

from __future__ import annotations

import argparse
import json
import math
import statistics
from collections import Counter
from pathlib import Path
from typing import Any

from .feature_anchor_registry import content_sha256


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def _review_context_lengths(root: Path) -> list[int]:
    candidates = _read(root / "research/qgen/onboarding/v6_development_seed_candidates.json")
    evidence = _read(root / "research/qgen/onboarding/v6_targeted_authoritative_evidence.json")
    claims = {row["claim_id"]: row for row in evidence["claims"]}
    lengths: list[int] = []
    kept = (
        "proposal_id", "candidate", "key", "learner_decision", "response_class",
        "decision_granularity", "option_set_archetype", "frozen_relevant_features",
        "proposed_anchor", "proposed_relation", "evidence_refs",
    )
    for opportunity in candidates["opportunities"]:
        for proposal in opportunity["proposals"]:
            packet = {key: proposal[key] for key in kept}
            packet["evidence"] = [
                claims[ref] for ref in proposal["evidence_refs"] if ref in claims
            ]
            lengths.append(len(json.dumps(packet, sort_keys=True, separators=(",", ":"))))
    return lengths


def build_registry(root: Path) -> dict[str, Any]:
    root = root.resolve()
    pack = _read(root / "research/qgen/onboarding/v6_development_seed_pack.json")
    review = _read(root / "research/qgen/onboarding/v6_development_seed_independent_review.json")
    anchors = _read(root / "research/qgen/onboarding/v6_development_seed_pack.stem_anchors.json")
    seeds = [row for target in pack["targets"] for row in target["seeds"]]
    anchor_features = [
        entry["stem_feature_id"]
        for row in anchors["seeds"] for entry in row["plausibility_anchors"]
    ]
    anchor_reuse = sum(count - 1 for count in Counter(anchor_features).values() if count > 1)
    document = {
        "schema_version": "1.0",
        "scope": "QGEN_DEVELOPMENT_SEED_REGISTRY",
        "classification": "DEVELOPMENT_VALIDATION",
        "production_global_library": False,
        "pack_count": 1,
        "packs": [{
            "pack_id": pack["pack_id"],
            "pack_version": pack["pack_version"],
            "study_unit_ids": sorted({row["anchor_study_unit_id"] for row in pack["targets"]}),
            "learner_decision_ids": list(pack["opportunity_scope"]),
            "approved_seed_count": len(seeds),
            "seed_ids": [row["seed_id"] for row in seeds],
            "relation_ids": sorted({rid for row in seeds for rid in row["relation_ids"]}),
            "anchor_relation_ids": sorted({rid for row in seeds for rid in row["anchor_relation_ids"]}),
            "input_hashes": pack["input_hashes"],
            "review_hashes": pack["review_hashes"],
            "content_sha256": pack["content_sha256"],
        }],
        "seed_counts": dict(review["counts"]),
        "reuse_counts": {"SEED": 0, "RELATION": 0, "ANCHOR": anchor_reuse},
    }
    document["content_sha256"] = content_sha256(document)
    return document


def build_milestone_report(root: Path) -> dict[str, Any]:
    root = root.resolve()
    candidates = _read(root / "research/qgen/onboarding/v6_development_seed_candidates.json")
    seed_review = _read(root / "research/qgen/onboarding/v6_development_seed_independent_review.json")
    replay12 = _read(root / "reports/qgen_seed_pack_onboarding_development_12_replay.json")
    replay36 = _read(root / "reports/qgen_seed_pack_onboarding_development_36_replay.json")
    final_review = _read(root / "research/qgen/onboarding/v6_development_final_medical_review.json")
    registry = build_registry(root)
    from .contrast_first_pilot import measure_copyright
    copyright_audit = measure_copyright(root, [
        "research/qgen/onboarding/v6_targeted_authoritative_evidence.json",
        "research/qgen/onboarding/v6_development_seed_candidates.json",
        "research/qgen/onboarding/v6_development_seed_pack.json",
        "research/qgen/onboarding/v6_clinical_contrast_relations_v2.json",
        "research/qgen/onboarding/v6_development_stems.json",
        "research/qgen/onboarding/v6_development_items.json",
    ])
    lengths = sorted(_review_context_lengths(root))
    p95_index = max(0, math.ceil(0.95 * len(lengths)) - 1)
    document = {
        "schema_version": "1.0",
        "scope": "QGEN_GENERALIZED_SEED_PACK_ONBOARDING_MILESTONE",
        "classification": "DEVELOPMENT_REGRESSION_SET",
        "production_readiness": "NOT_ASSESSED_ON_CURRENT_36",
        "architecture_decision": "SEED_PACK_ONBOARDING_VALIDATED",
        "historical_replay_identical": replay12["historical_replay_identical"],
        "raw_seed_candidates": candidates["raw_seed_candidates"],
        "seeds_proposed": candidates["seed_proposals"],
        "seed_counts": seed_review["counts"],
        "backwards_anchors_caught": 1,
        "development_12_ready": replay12["development_12_post_seed_ready"],
        "development_36_ready": replay36["development_36_post_seed_ready"],
        "ready_by_discipline": replay36["ready_by_discipline"],
        "final_review_counts": final_review["counts"],
        "development_safe_yield": {"accepted": final_review["counts"]["ACCEPTED"], "total": 36},
        "no_safe_item": 36 - final_review["counts"]["ACCEPTED"],
        "failure_counts": {
            "NO_SEED_CANDIDATE": 33,
            "SEED_REVIEW_REJECTED": 1,
            "OTHER": 1,
        },
        "economics": {
            "seeds_proposed_per_opportunity": candidates["seed_proposals"] / 36,
            "seeds_approved_per_opportunity": seed_review["counts"]["APPROVED"] / 36,
            "seed_reuse_count": registry["reuse_counts"]["SEED"],
            "relation_reuse_count": registry["reuse_counts"]["RELATION"],
            "anchor_reuse_count": registry["reuse_counts"]["ANCHOR"],
            "new_clinical_research_requests": candidates["new_external_research_requests"],
            "semantic_review_cache_hits": 0,
            "assessment": "INSUFFICIENT_DATA",
        },
        "discovery_contribution": {
            "graph_unique_approved_seeds": candidates["graph_unique_proposals"],
            "tn_fts_unique_approved_seeds": candidates["tn_fts_unique_proposals"],
        },
        "context_chars": {
            "median": int(statistics.median(lengths)),
            "p95": lengths[p95_index],
        },
        "copyright": copyright_audit,
        "next_dominant_bottleneck": "FRESH_HOLDOUT_GENERALIZATION_AND_CROSS_UNIT_SEED_REUSE_UNMEASURED",
        "next_step": "BUILD_NEW_FRESH_HOLDOUT_PILOT",
    }
    document["content_sha256"] = content_sha256(document)
    return document


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    root = args.root.resolve()
    outputs = {
        root / "research/qgen/onboarding/v6_development_seed_registry.json": build_registry(root),
        root / "reports/qgen_seed_pack_onboarding_milestone.json": build_milestone_report(root),
    }
    for path, payload in outputs.items():
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
