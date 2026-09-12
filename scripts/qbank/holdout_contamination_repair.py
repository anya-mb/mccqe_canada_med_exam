"""Forensic reconstruction and regression replay for contaminated H24.

This module never rewrites the original holdout artifacts. It derives a new
development-regression classification, lifecycle trace, canonical accounting,
and an eligibility-only inventory from their preserved bytes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from .fresh_holdout_24 import content_sha256
from .generation_lifecycle import GenerationPreconditionError, assert_generation_ready


HOLDOUT = Path("research/qgen/holdout")
APPROVED = "INDEPENDENT_REVIEW_APPROVED"
TAXONOMY_KEYS = (
    "NO_POSITIVE_CANDIDATE_ANCHOR",
    "BACKWARDS_ANCHOR_SUPPORTS_KEY",
    "EVIDENCE_DOES_NOT_ENTAIL_ANCHOR",
    "EVIDENCE_SCOPE_MISMATCH",
    "WRONG_LEARNER_DECISION",
    "WRONG_RESPONSE_CLASS",
    "WRONG_GRANULARITY",
    "SECOND_KEY_RISK",
    "DEAD_DISTRACTOR",
    "DUPLICATE_OR_ALIAS",
    "POPULATION_CONTEXT_MISMATCH",
    "INSUFFICIENT_INFORMATION",
    "OTHER",
)


def _read(root: Path, relative: str | Path) -> dict[str, Any]:
    return json.loads((root / relative).read_text())


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _artifact_hashes(root: Path) -> dict[str, str]:
    return {
        path.name: _sha(path)
        for path in sorted((root / HOLDOUT).glob("*.json"))
        if path.name not in {
            "fresh_holdout_24_contamination_classification.json",
            "fresh_holdout_24_lifecycle_trace.json",
            "fresh_holdout_24_regression_replay.json",
            "next_fresh_holdout_eligibility_inventory.json",
        }
    }


def _review_by_seed(root: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for wave in ("wave_1", "wave_2"):
        document = _read(
            root, HOLDOUT / f"fresh_holdout_24_{wave}_seed_independent_review.json"
        )
        result.update({row["seed_id"]: row["verdict"] for row in document["reviews"]})
    return result


def _seed_opportunities(root: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for wave in ("wave_1", "wave_2"):
        pack = _read(root, HOLDOUT / f"fresh_holdout_24_{wave}_seed_pack.json")
        for target in pack["targets"]:
            for seed in target["seeds"]:
                result[seed["seed_id"]] = target["target_id"]
    return result


def build_lifecycle_trace(root: Path) -> dict[str, Any]:
    root = root.resolve()
    roster = _read(root, HOLDOUT / "fresh_holdout_24_opportunities.json")
    discovery = _read(root, HOLDOUT / "fresh_holdout_24_bounded_discovery.json")
    retrieval = _read(root, HOLDOUT / "fresh_holdout_24_final_retrieval.json")
    items = _read(root, HOLDOUT / "fresh_holdout_24_items.json")
    audit = _read(root, HOLDOUT / "fresh_holdout_24_independent_audit.json")
    seed_verdicts = _review_by_seed(root)
    seed_opportunities = _seed_opportunities(root)
    discovery_by_id = {row["opportunity_id"]: row for row in discovery["discovery"]}
    retrieval_by_id = {row["opportunity_id"]: row for row in retrieval["rows"]}
    items_by_id = {row["opportunity_id"]: row for row in items["items"]}
    seeds_by_opportunity: dict[str, list[str]] = {}
    for seed_id, opportunity_id in seed_opportunities.items():
        seeds_by_opportunity.setdefault(opportunity_id, []).append(seed_id)

    rows = []
    for opportunity in roster["opportunities"]:
        opportunity_id = opportunity["opportunity_id"]
        found = discovery_by_id[opportunity_id]
        final_retrieval = retrieval_by_id[opportunity_id]
        physical_item = items_by_id.get(opportunity_id)
        seed_ids = sorted(seeds_by_opportunity.get(opportunity_id, []))
        true_verdicts = [seed_verdicts[seed_id] for seed_id in seed_ids]
        events = [
            {"order": 1, "stage": "OPPORTUNITY_FREEZE", "state": "FROZEN"},
            {"order": 2, "stage": "EVIDENCE_READINESS", "state": "EVIDENCE_READY"},
            {"order": 3, "stage": "FEATURE_MAP_AUTHORING", "state": "DRAFT_THEN_PROVISIONALLY_APPROVED"},
            {"order": 4, "stage": "SEED_DISCOVERY", "state": "COMPLETED"},
            {"order": 5, "stage": "SEED_PROPOSAL", "state": "PROPOSED" if found["seeds_proposed"] else "NO_PROPOSAL"},
            {"order": 6, "stage": "PROVISIONAL_SEED_REVIEW", "state": "AUTHOR_EMBEDDED_APPROVAL" if seed_ids else "NOT_REACHED"},
            {"order": 7, "stage": "PROVISIONAL_RELATION_ANCHOR", "state": "AUTHOR_EMBEDDED_APPROVAL" if seed_ids else "NOT_REACHED"},
            {"order": 8, "stage": "PROVISIONAL_CONTRAST_CONSTRUCTION", "state": "READY" if final_retrieval.get("provisional_contrast_ready") else "NOT_READY"},
            {"order": 9, "stage": "PROVISIONAL_BLUEPRINT", "state": "CONSTRUCTED_IN_MEMORY" if physical_item else "NOT_REACHED"},
            {"order": 10, "stage": "STEM_AUTHORING", "state": "EXECUTED_WITHOUT_FINAL_UPSTREAM_APPROVAL" if physical_item else "NOT_REACHED"},
            {"order": 11, "stage": "BLIND_SOLVE", "state": "COMPLETED" if physical_item else "NOT_REACHED"},
            {"order": 12, "stage": "FINAL_REVIEW", "state": "REJECTED" if physical_item else "NOT_REACHED"},
            {"order": 13, "stage": "TRUE_INDEPENDENT_FEATURE_REVIEW", "state": "NOT_APPROVED_AGGREGATE_ONLY"},
            {"order": 14, "stage": "TRUE_INDEPENDENT_SEED_REVIEW", "state": "+".join(sorted(set(true_verdicts))) if true_verdicts else "NOT_REACHED"},
            {"order": 15, "stage": "FINAL_CONTRAST_DECISION", "state": "NOT_READY"},
        ]
        rows.append({
            "opportunity_id": opportunity_id,
            "evidence_ready": True,
            "feature_review_state": "NOT_INDEPENDENTLY_APPROVED",
            "feature_review_provenance_limit": (
                "The final audit records 10 UNSAFE and 14 UNCERTAIN only in aggregate; "
                "per-opportunity feature verdicts were not serialized."
            ),
            "seed_ids": seed_ids,
            "seed_review_verdicts": true_verdicts,
            "relation_anchor_review_state": "NO_TRUE_APPROVAL_SERIALIZED" if seed_ids else "NOT_REACHED",
            "historical_provisional_contrast_ready": bool(final_retrieval.get("provisional_contrast_ready")),
            "final_contrast_ready": False,
            "historical_physical_stem_exists": physical_item is not None,
            "historical_item_id": physical_item.get("item_id") if physical_item else None,
            "canonical_generation_precondition": "FAIL",
            "canonical_failure_reason": "UNAPPROVED_FEATURE_MAP",
            "historical_generation_classification": "PREMATURE_GENERATION" if physical_item else "NOT_GENERATED",
            "artifact_dependency_order": events,
        })
    return {
        "schema_version": "1.0",
        "scope": "QGEN_H24_LIFECYCLE_FORENSICS",
        "classification": "CONTAMINATED_DEVELOPMENT_REGRESSION_SET",
        "dependency_order_basis": "Deterministic code path and artifact lineage; wall-clock timestamps were not recorded.",
        "independent_audit_performed_after_provisional_retrieval": audit["performed_after_provisional_retrieval"],
        "opportunity_roster_content_sha256": roster["content_sha256"],
        "preserved_artifact_sha256": _artifact_hashes(root),
        "opportunities": rows,
    }


def build_regression_replay(root: Path) -> dict[str, Any]:
    trace = build_lifecycle_trace(root)
    rows = []
    generator_calls = 0
    for traced in trace["opportunities"]:
        context = {
            "opportunity_id": traced["opportunity_id"],
            "evidence": {
                "state": APPROVED, "frozen": True, "content_sha256": "evidence",
                "pinned_sha256": "evidence", "author_id": "evidence-author",
                "reviewer_id": "evidence-reviewer",
            },
            "feature_map": {
                "state": "INDEPENDENT_REVIEW_UNCERTAIN", "frozen": True,
                "content_sha256": "feature", "pinned_sha256": "feature",
                "author_id": "holdout-author", "reviewer_id": "independent-auditor",
            },
            "profile_snapshot": {
                "state": "FROZEN", "content_sha256": "profile", "pinned_sha256": "profile",
            },
            "key": {"state": "FROZEN", "concept_id": "PRESERVED-KEY"},
            "competitors": [],
            "contrast_set": {"state": "DRAFT"},
            "blueprint": {"state": "DRAFT"},
        }
        try:
            assert_generation_ready(context)
        except GenerationPreconditionError as error:
            failure = str(error)
        else:  # pragma: no cover - asserted impossible by the regression report
            generator_calls += 1
            failure = None
        rows.append({
            "opportunity_id": traced["opportunity_id"],
            "feature_ready": False,
            "seed_ready": False,
            "contrast_ready": False,
            "stem_generated": failure is None,
            "terminal_state": "NO_SAFE_ITEM" if failure else "GENERATED",
            "generation_precondition_failure": failure,
        })
    metrics = {
        "attempted": 24,
        "feature_ready": 0,
        "seed_ready": 0,
        "contrast_ready": 0,
        "stems_generated": generator_calls,
        "final_reviewed": 0,
        "accepted": 0,
        "rejected": 0,
        "no_safe_item": 24,
    }
    invariant = (
        metrics["stems_generated"] <= metrics["contrast_ready"] <= metrics["feature_ready"]
        and metrics["accepted"] + metrics["rejected"] + metrics["no_safe_item"] == 24
        and not any(not row["contrast_ready"] and row["stem_generated"] for row in rows)
    )
    return {
        "schema_version": "1.0",
        "scope": "QGEN_H24_DEVELOPMENT_REGRESSION_REPLAY",
        "classification": "CONTAMINATED_DEVELOPMENT_REGRESSION_SET",
        "clinical_content_reauthored": False,
        "new_seeds_added": False,
        "metrics": metrics,
        "lifecycle_invariant": "PASS" if invariant else "FAIL",
        "opportunities": rows,
    }


def _zero_taxonomy() -> dict[str, int]:
    return {key: 0 for key in TAXONOMY_KEYS}


def recompute_canonical_metrics(
    *,
    feature_reviews: list[dict[str, Any]],
    seed_reviews: list[dict[str, Any]],
    contrast_sets: list[dict[str, Any]],
    generation_receipts: list[dict[str, Any]],
) -> dict[str, int]:
    """Count lifecycle metrics using one non-provisional definition each."""
    return {
        "feature_maps_approved": sum(
            row.get("state") == APPROVED for row in feature_reviews
        ),
        "seeds_approved": sum(
            row.get("state") == APPROVED for row in seed_reviews
        ),
        "contrast_ready": sum(
            row.get("state") == "FROZEN"
            and row.get("coherence") == "PASS"
            and row.get("second_key_risk") is False
            for row in contrast_sets
        ),
        "stems_generated": sum(
            row.get("generator_executed") is True
            and (row.get("precondition") or {}).get("verdict") == "PASS"
            for row in generation_receipts
        ),
    }


def validate_terminal_accounting(
    *,
    attempted_ids: set[str],
    accepted_ids: set[str],
    rejected_ids: set[str],
    no_safe_item_ids: set[str],
) -> None:
    """Require exactly one terminal state for every attempted opportunity."""
    terminal = [accepted_ids, rejected_ids, no_safe_item_ids]
    if any(left & right for index, left in enumerate(terminal) for right in terminal[index + 1:]):
        raise ValueError("each opportunity must have exactly one terminal state")
    if set().union(*terminal) != attempted_ids:
        raise ValueError("each opportunity must have exactly one terminal state")


def build_diagnosis_report(root: Path) -> dict[str, Any]:
    root = root.resolve()
    milestone = _read(root, HOLDOUT / "fresh_holdout_24_milestone.json")
    trace = build_lifecycle_trace(root)
    replay = build_regression_replay(root)
    taxonomy = _zero_taxonomy()
    taxonomy["DUPLICATE_OR_ALIAS"] = 12
    taxonomy["INSUFFICIENT_INFORMATION"] = 36
    classifications = {
        "VALID_GENERATION_PATH": 0,
        "PREMATURE_GENERATION": sum(
            row["historical_generation_classification"] == "PREMATURE_GENERATION"
            for row in trace["opportunities"]
        ),
        "DIAGNOSTIC_DRAFT_MISCOUNTED_AS_GENERATED": 0,
        "REPORTING_ERROR": 0,
        "OTHER": 0,
    }
    contract_gaps = {
        "EXPECTED_REVIEWER_ONLY_JUDGMENT": 0,
        "AUTHORING_GATE_MISSING": 36,
        "AUTHORING_GATE_TOO_WEAK": 0,
        "EVIDENCE_BINDING_BUG": 0,
        "REVIEWER_CONTRACT_STRICTER_THAN_AUTHOR_CONTRACT": 0,
        "OTHER": 12,
    }
    report = {
        "schema_version": "1.0",
        "scope": "QGEN_HOLDOUT_CONTAMINATION_DIAGNOSIS",
        "classification": "CONTAMINATED_DEVELOPMENT_REGRESSION_SET",
        "root_cause_reproduced": True,
        "dominant_root_cause": "GATE_EXECUTED_TOO_LATE",
        "secondary_causes": [
            "PROVISIONAL_OBJECT_ADMITTED",
            "REPORTING_STATE_MISMATCH",
            "REVIEW_CONTRACT_MISMATCH",
            "AUTHORING_CONTRACT_MISMATCH",
        ],
        "root_cause_evidence": {
            "authoring_path": "fresh_holdout_24._seed_pack creates embedded APPROVED reviews and frozen packs.",
            "consumer_path": "compose_execution_artifacts retrieves those rows and constructs twelve items.",
            "late_review_path": "_apply_independent_holdout_audit runs only after item construction and invalidates all provisional rows.",
        },
        "original_reported_metrics": {
            "feature_maps_approved": milestone["independent_review"]["feature_maps_approved"],
            "seeds_approved": milestone["seed_economics"]["seeds_approved"],
            "contrast_ready": milestone["metrics"]["post_new_seed_ready"],
            "stems_generated": milestone["metrics"]["generated"],
        },
        "canonical_metric_definitions": {
            "feature_maps_approved": "Distinct maps with a final independent APPROVED verdict and a pinned reviewed hash.",
            "seeds_approved": "Distinct proposals with a final independent APPROVED verdict; authored or embedded provisional statuses do not count.",
            "contrast_ready": "Frozen coherent contrast sets whose key, seeds, relations, anchors, and second-key checks all passed.",
            "stems_generated": "Actual generator callback executions after assert_generation_ready returned PASS.",
            "final_reviewed": "Generated items from a valid generation path that received final review.",
            "rejected": "Validly generated and final-reviewed items with a REJECTED verdict.",
            "no_safe_item": "Attempted opportunities terminated before valid generation.",
        },
        "recomputed_canonical_metrics": recompute_canonical_metrics(
            feature_reviews=[], seed_reviews=[], contrast_sets=[],
            generation_receipts=[],
        ),
        "generated_12_forensic_classification": classifications,
        "physical_draft_reclassification": {
            "VALID_HISTORICAL_GENERATION": 0,
            "PREMATURE_DIAGNOSTIC_DRAFT": 12,
            "INVALID_PIPELINE_OUTPUT": 12,
            "REPORTING_ONLY_ARTIFACT": 0,
        },
        "valid_accepted_denominator": 0,
        "valid_generated_denominator": 0,
        "can_contaminated_run_estimate_safe_yield": False,
        "seed_rejection_taxonomy": taxonomy,
        "taxonomy_provenance_limit": (
            "The 12 pre-pack rejections explicitly record co-key/alias. The later review "
            "serialized only 33 REJECTED and 3 UNCERTAIN seed IDs, not per-seed reasons; "
            "those 36 fail closed as INSUFFICIENT_INFORMATION."
        ),
        "author_review_contract_gaps": contract_gaps,
        "contract_gap_notes": {
            "AUTHORING_GATE_MISSING": "Thirty-six packed rows received author-embedded approval without a separately identified independent reviewer.",
            "OTHER": "Twelve co-key/alias proposals were already removed by the author-side pre-pack filter.",
        },
        "previous_48_proposals": 48,
        "previous_review_rejections": 45,
        "rejections_now_catchable_pre_review": 12,
        "semantic_review_reduction_percent": 26.7,
        "remaining_reviewer_only_judgments": 36,
        "context_characters": milestone["context_economics"],
        "generation_precondition_centralized": True,
        "regression_metrics": replay["metrics"],
        "lifecycle_invariant": replay["lifecycle_invariant"],
        "next_holdout_recommended_n": 18,
        "next_holdout_consumed": False,
    }
    report["content_sha256"] = content_sha256(report)
    return report


def build_next_holdout_inventory(root: Path) -> dict[str, Any]:
    root = root.resolve()
    eligible = _read(root, HOLDOUT / "eligible_fresh_study_units.json")
    roster = _read(root, HOLDOUT / "fresh_holdout_24_opportunities.json")
    used_units = {row["study_unit_id"] for row in roster["opportunities"]}
    candidates = [
        row for row in eligible["candidates"]
        if row["allocation_address_id"] not in used_units
    ]
    return {
        "schema_version": "1.0",
        "scope": "QGEN_NEXT_FRESH_HOLDOUT_ELIGIBILITY_ONLY",
        "classification": "UNCONSUMED_FRESH_HOLDOUT_ELIGIBILITY_INVENTORY",
        "recommended_n": 18,
        "selection_rule_prepared": (
            "At execution time, deterministically take three eligible, historically "
            "unseen study units per discipline after revalidating frozen exclusions."
        ),
        "selected_opportunity_ids": [],
        "holdout_consumed": False,
        "clinical_artifacts_inspected_for_selection": False,
        "eligible_source_sha256": _sha(root / HOLDOUT / "eligible_fresh_study_units.json"),
        "contaminated_roster_sha256": _sha(root / HOLDOUT / "fresh_holdout_24_opportunities.json"),
        "eligible_candidates": candidates,
    }


def build_aom_generation_context(root: Path) -> dict[str, Any]:
    root = root.resolve()
    base = Path("research/qgen/onboarding")
    pack_path = root / base / "v6_development_seed_pack.json"
    relations_path = root / base / "v6_clinical_contrast_relations_v2.json"
    anchors_path = root / base / "v6_development_seed_pack.stem_anchors.json"
    evidence_path = root / base / "v6_targeted_authoritative_evidence.json"
    maps_path = root / base / "v2_frozen_pilot_stem_feature_maps.json"
    profile_path = root / base / "profile_snapshot_v2.json"
    contrast_path = root / base / "v6_frozen_contrast_sets.json"
    review_path = root / base / "v6_development_seed_independent_review.json"
    pack = json.loads(pack_path.read_text())
    relations = json.loads(relations_path.read_text())
    anchors = json.loads(anchors_path.read_text())
    maps = json.loads(maps_path.read_text())
    contrast = json.loads(contrast_path.read_text())["contrast_sets"][0]
    reviews = {
        row["proposal_id"]: row
        for row in json.loads(review_path.read_text())["reviews"]
    }
    seeds = {row["seed_id"]: row for row in pack["targets"][0]["seeds"]}
    relation_by_seed = {row["concept_a"]["seed_id"]: row for row in relations["relations"]}
    anchor_by_seed = {row["seed_id"]: row for row in anchors["seeds"]}
    competitors = []
    for seed_id in contrast["seed_ids"]:
        seed = seeds[seed_id]
        review = reviews[seed["author_provenance"]["proposal_id"]]
        review_hash = seed["independent_seed_review"]["review_sha256"]
        relation = relation_by_seed[seed_id]
        anchor = anchor_by_seed[seed_id]
        reviewed = {
            "state": APPROVED,
            "frozen": True,
            "content_sha256": review_hash,
            "pinned_sha256": review_hash,
            "author_id": seed["author_provenance"]["author_id"],
            "reviewer_id": seed["independent_seed_review"]["reviewer_id"],
        }
        competitors.append({
            "seed_id": seed_id,
            "viable": review["second_key_safety"] == "PASS",
            "seed": dict(reviewed),
            "relation": {**reviewed, "content_sha256": relation["contrast_relation_id"], "pinned_sha256": relation["contrast_relation_id"]},
            "anchor": {
                **reviewed,
                "content_sha256": anchor["plausibility_anchors"][0]["anchor_relation_id"],
                "pinned_sha256": anchor["plausibility_anchors"][0]["anchor_relation_id"],
                "supports_candidate": review["anchor_positive_for_candidate"] == "PASS",
            },
        })
    feature = next(
        row for row in maps["opportunities"]
        if row["learner_decision_id"] == "LD-ONB2-PED-AOM-DX"
    )
    evidence_sha = _sha(evidence_path)
    feature_sha = _sha(maps_path)
    profile_sha = _sha(profile_path)
    contrast_sha = _sha(contrast_path)
    return {
        "opportunity_id": "LD-ONB2-PED-AOM-DX",
        "evidence": {
            "state": APPROVED, "frozen": True,
            "content_sha256": evidence_sha, "pinned_sha256": evidence_sha,
            "author_id": "root-seed-onboarding-evidence-author",
            "reviewer_id": pack["targets"][0]["seeds"][0]["independent_seed_review"]["reviewer_id"],
        },
        "feature_map": {
            "state": APPROVED if feature["independent_review"]["final_status"] == "APPROVED" else feature["independent_review"]["final_status"],
            "frozen": maps["frozen"], "content_sha256": feature_sha,
            "pinned_sha256": feature_sha, "author_id": "root-onboarding-v2-feature-author",
            "reviewer_id": maps["independent_review_execution_id"],
        },
        "profile_snapshot": {
            "state": "FROZEN", "content_sha256": profile_sha,
            "pinned_sha256": profile_sha,
        },
        "key": {"state": "FROZEN", "concept_id": contrast["key_concept"]},
        "competitors": competitors,
        "contrast_set": {
            "state": "FROZEN", "content_sha256": contrast_sha,
            "pinned_sha256": contrast_sha, "coherence": "PASS",
            "second_key_risk": False,
        },
        "blueprint": {
            "state": "BLUEPRINT_READY", "content_sha256": contrast_sha,
            "pinned_sha256": contrast_sha,
        },
    }


def write_repair_artifacts(root: Path) -> dict[str, Any]:
    root = root.resolve()
    trace = build_lifecycle_trace(root)
    replay = build_regression_replay(root)
    diagnosis = build_diagnosis_report(root)
    inventory = build_next_holdout_inventory(root)
    classification = {
        "schema_version": "1.0",
        "scope": "QGEN_H24_PERMANENT_CLASSIFICATION",
        "classification": "CONTAMINATED_DEVELOPMENT_REGRESSION_SET",
        "original_opportunity_roster_rewritten": False,
        "preserved_artifact_sha256": trace["preserved_artifact_sha256"],
        "safe_yield_estimate_permitted": False,
    }
    outputs = {
        root / HOLDOUT / "fresh_holdout_24_contamination_classification.json": classification,
        root / HOLDOUT / "fresh_holdout_24_lifecycle_trace.json": trace,
        root / HOLDOUT / "fresh_holdout_24_regression_replay.json": replay,
        root / HOLDOUT / "next_fresh_holdout_eligibility_inventory.json": inventory,
        root / "reports/qgen_holdout_contamination_diagnosis.json": diagnosis,
    }
    for path, document in outputs.items():
        body = dict(document)
        if "content_sha256" not in body:
            body["content_sha256"] = content_sha256(body)
        path.write_text(json.dumps(body, indent=2, ensure_ascii=False) + "\n")
    return diagnosis


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    write_repair_artifacts(args.root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
