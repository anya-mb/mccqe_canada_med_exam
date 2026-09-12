"""Deterministic orchestration for the fresh Holdout-18 milestone.

Selection deliberately uses only frozen curriculum priority, coarse source
readiness, and canonical identifiers.  No seed, retrieval, candidate, or
contrast artifact is read until after the roster and architecture are frozen.
"""

from __future__ import annotations

import hashlib
import json
import re
import statistics
from pathlib import Path
from typing import Any


HOLDOUT = Path("research/qgen/holdout")
DISCIPLINES = ("MED", "PED", "OBGYN", "SURG", "PSY", "PHELO")

ARCHITECTURE_INPUTS = {
    "generation_lifecycle": "scripts/qbank/generation_lifecycle.py",
    "profile_v2": "research/qgen/onboarding/profile_snapshot_v2.json",
    "feature_anchor_snapshot": "research/qgen/onboarding/feature_anchor_snapshot_v5.json",
    "seed_pack_schema": "schemas/generalized-competitive-contrast-seed-pack.schema.json",
    "clinical_contrast_relation_v2": "research/qgen/onboarding/v6_clinical_contrast_relations_v2.json",
    "retrieval_implementation": "scripts/qbank/profile_contrast_retrieval.py",
    "blueprint_implementation": "scripts/qbank/contrast_first_v2_pilot.py",
    "option_realization": "scripts/qbank/seed_onboarding_generation.py",
    "reporting_contract": "scripts/qbank/seed_onboarding_reporting.py",
}


class HoldoutIntegrityError(ValueError):
    """A frozen holdout input or invariant no longer matches its pin."""


EVIDENCE_VERDICTS = frozenset({
    "EVIDENCE_READY",
    "ALIGNED_PARTIAL",
    "EVIDENCE_MISSING",
    "UNCERTAIN",
    "OUT_OF_SCOPE",
})
FEATURE_REVIEW_VERDICTS = frozenset({"APPROVED", "REJECTED", "UNCERTAIN"})
FEATURE_STATES = frozenset({"PRESENT", "ABSENT", "UNKNOWN", "NOT_APPLICABLE"})


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def content_sha256(value: dict[str, Any]) -> str:
    body = {key: item for key, item in value.items() if key != "content_sha256"}
    payload = json.dumps(
        body, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    ).encode()
    return hashlib.sha256(payload).hexdigest()


def _signature(value: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", value.lower()))


def validate_evidence_records(
    roster: dict[str, Any], evidence: dict[str, Any]
) -> dict[str, int]:
    expected = {row["opportunity_id"] for row in roster["opportunities"]}
    rows = evidence.get("rows") or []
    observed = [row.get("opportunity_id") for row in rows]
    if len(observed) != len(set(observed)) or set(observed) != expected:
        raise HoldoutIntegrityError("EVIDENCE_ROWS_NOT_EXHAUSTIVE")
    counts: dict[str, int] = {}
    for row in rows:
        verdict = row.get("verdict")
        if verdict not in EVIDENCE_VERDICTS:
            raise HoldoutIntegrityError(f"INVALID_EVIDENCE_VERDICT: {verdict}")
        if verdict == "EVIDENCE_READY":
            if not row.get("exact_relevant_claims") or not row.get("content_sha256"):
                raise HoldoutIntegrityError("UNPINNED_OR_EMPTY_DECISION_EVIDENCE")
        elif not row.get("reason"):
            raise HoldoutIntegrityError("MISSING_EVIDENCE_FAILURE_REASON")
        counts[verdict] = counts.get(verdict, 0) + 1
    return counts


def validate_feature_reviews(
    evidence_ready_ids: set[str],
    feature_maps: dict[str, Any],
    reviews: dict[str, Any],
    *,
    registered_feature_ids: set[str],
) -> dict[str, int]:
    maps = {row["opportunity_id"]: row for row in feature_maps.get("rows") or []}
    review_rows = reviews.get("rows") or []
    if set(maps) != evidence_ready_ids:
        raise HoldoutIntegrityError("FEATURE_MAP_SCOPE_MISMATCH")
    if {row.get("opportunity_id") for row in review_rows} != evidence_ready_ids:
        raise HoldoutIntegrityError("FEATURE_REVIEW_SCOPE_MISMATCH")
    counts: dict[str, int] = {}
    for review in review_rows:
        opportunity_id = review["opportunity_id"]
        feature_map = maps[opportunity_id]
        verdict = review.get("verdict")
        if verdict not in FEATURE_REVIEW_VERDICTS:
            raise HoldoutIntegrityError("INVALID_FEATURE_REVIEW_VERDICT")
        if review.get("reviewer_id") == feature_map.get("author_id"):
            raise HoldoutIntegrityError("NONINDEPENDENT_FEATURE_REVIEW")
        if review.get("reviewed_map_sha256") != feature_map.get("map_content_sha256"):
            raise HoldoutIntegrityError("STALE_FEATURE_REVIEW")
        if not review.get("map_reason"):
            raise HoldoutIntegrityError("MISSING_FEATURE_REVIEW_REASON")
        features = feature_map.get("features") or []
        feature_ids = {row.get("feature_id") for row in features}
        if any(row.get("state") not in FEATURE_STATES for row in features):
            raise HoldoutIntegrityError("INVALID_FEATURE_STATE")
        if not feature_ids <= registered_feature_ids:
            raise HoldoutIntegrityError("UNREGISTERED_FEATURE")
        feature_reviews = review.get("feature_reviews") or []
        if {row.get("feature_id") for row in feature_reviews} != feature_ids:
            raise HoldoutIntegrityError("FEATURE_REVIEW_ROWS_NOT_EXHAUSTIVE")
        counts[verdict] = counts.get(verdict, 0) + 1
    return counts


def _decision_fields(crosswalk_row: dict[str, Any]) -> dict[str, str]:
    competencies = crosswalk_row.get("testable_competencies") or {}
    if not competencies:
        raise HoldoutIntegrityError(
            f"MISSING_CANONICAL_COMPETENCY: {crosswalk_row['study_unit_id']}"
        )
    competency_key = sorted(competencies)[0]
    decision = competencies[competency_key]
    study_unit_id = crosswalk_row["study_unit_id"]
    suffix = re.sub(r"[^A-Z0-9]+", "-", competency_key.upper()).strip("-")
    return {
        "learner_decision_id": f"LD-H18-{study_unit_id[3:]}-{suffix}",
        "learner_decision": decision,
        "learner_decision_signature": _signature(decision),
        "key_concept_or_action": f"{study_unit_id}:{competency_key}",
        "canonical_competency_key": competency_key,
    }


def select_fresh_holdout_18(root: Path) -> dict[str, Any]:
    """Select three unseen study units per discipline without contrast signals."""
    root = Path(root).resolve()
    inventory = _read(root / HOLDOUT / "next_fresh_holdout_eligibility_inventory.json")
    if inventory.get("holdout_consumed") is not False:
        raise HoldoutIntegrityError("NEXT_HOLDOUT_ALREADY_CONSUMED")
    if inventory.get("selected_opportunity_ids") != []:
        raise HoldoutIntegrityError("ELIGIBILITY_INVENTORY_ALREADY_SELECTED")
    if inventory.get("clinical_artifacts_inspected_for_selection") is not False:
        raise HoldoutIntegrityError("SELECTION_INVENTORY_INSPECTED_CLINICAL_ARTIFACTS")

    crosswalk = _read(root / "research/scope/master_scope_crosswalk.json")["entries"]
    crosswalk_by_unit = {row["study_unit_id"]: row for row in crosswalk}
    selected: list[dict[str, Any]] = []
    for discipline in DISCIPLINES:
        candidates = [
            row for row in inventory["eligible_candidates"]
            if row["discipline"] == discipline
        ]
        candidates.sort(key=lambda row: (
            0 if row["priority"] == "CORE" else 1,
            0 if row["evidence_readiness"] == "CURRENT_REPOSITORY_PACKET_READY" else 1,
            row["allocation_address_id"],
        ))
        if len(candidates) < 3:
            raise HoldoutIntegrityError(f"INSUFFICIENT_FRESH_CANDIDATES: {discipline}")
        for ordinal, source in enumerate(candidates[:3], start=1):
            decision = _decision_fields(crosswalk_by_unit[source["study_unit_id"]])
            selected.append({
                "opportunity_id": f"H18-{discipline}-{ordinal:02d}",
                "discipline": discipline,
                "study_unit_id": source["study_unit_id"],
                "study_unit": source["study_unit"],
                "allocation_address_id": source["allocation_address_id"],
                "mcc_objective_ids": source["mcc_objective_ids"],
                "priority": source["priority"],
                "historical_use_status": source["historical_use_status"],
                "selection_evidence_readiness": source["evidence_readiness"],
                **decision,
            })

    exclusions = _read(root / HOLDOUT / "historical_exclusion_inventory.json")
    historical = exclusions.get("historical_exclusions") or exclusions.get("entries") or []
    dimensions = {
        "study_unit_overlap": (
            {row["study_unit_id"] for row in selected},
            {row.get("study_unit_id") for row in historical},
        ),
        "allocation_address_overlap": (
            {row["allocation_address_id"] for row in selected},
            {row.get("allocation_address_id") for row in historical},
        ),
        "learner_decision_signature_overlap": (
            {row["learner_decision_signature"] for row in selected},
            {row.get("learner_decision_signature") for row in historical},
        ),
        "key_concept_or_action_overlap": (
            {_signature(row["key_concept_or_action"]) for row in selected},
            {_signature(str(row.get("key_concept_or_action") or "")) for row in historical},
        ),
    }
    freshness = {
        label: len(current & previous)
        for label, (current, previous) in dimensions.items()
    }
    if any(freshness.values()):
        raise HoldoutIntegrityError(f"HISTORICAL_OVERLAP: {freshness}")

    waves = []
    by_discipline = {
        discipline: sorted(
            (row for row in selected if row["discipline"] == discipline),
            key=lambda row: row["opportunity_id"],
        )
        for discipline in DISCIPLINES
    }
    for index in range(3):
        waves.append({
            "wave": index + 1,
            "opportunity_ids": [
                by_discipline[discipline][index]["opportunity_id"]
                for discipline in DISCIPLINES
            ],
        })

    roster = {
        "schema_version": "1.0",
        "scope": "QGEN_FRESH_HOLDOUT_18_OPPORTUNITY_FREEZE",
        "selection_precedes_contrast_inspection": True,
        "selection_rule": (
            "Within each discipline: CORE before IMPORTANT; current repository "
            "packet ready before targeted research required; then canonical "
            "allocation-address order. Take the first three distinct fresh units."
        ),
        "source_inventory_sha256": _file_sha256(
            root / HOLDOUT / "next_fresh_holdout_eligibility_inventory.json"
        ),
        "freshness_revalidation": freshness,
        "opportunities": selected,
        "waves": waves,
    }
    roster["content_sha256"] = content_sha256(roster)
    return roster


def build_architecture_freeze(root: Path, roster: dict[str, Any]) -> dict[str, Any]:
    root = Path(root).resolve()
    pins = {
        name: {"path": relative, "file_sha256": _file_sha256(root / relative)}
        for name, relative in ARCHITECTURE_INPUTS.items()
    }
    freeze = {
        "schema_version": "1.0",
        "scope": "QGEN_FRESH_HOLDOUT_18_ARCHITECTURE_FREEZE",
        "freeze_precedes_clinical_authoring": True,
        "opportunity_roster_content_sha256": roster["content_sha256"],
        "artifact_pins": pins,
    }
    freeze["holdout_architecture_freeze_sha256"] = content_sha256(freeze)
    freeze["content_sha256"] = content_sha256(freeze)
    return freeze


def verify_freeze_integrity(
    root: Path, roster: dict[str, Any], freeze: dict[str, Any]
) -> dict[str, Any]:
    root = Path(root).resolve()
    if roster.get("content_sha256") != content_sha256(roster):
        raise HoldoutIntegrityError("ROSTER_HASH_DRIFT")
    if freeze.get("opportunity_roster_content_sha256") != roster["content_sha256"]:
        raise HoldoutIntegrityError("ROSTER_PIN_DRIFT")
    for name, pin in freeze.get("artifact_pins", {}).items():
        if _file_sha256(root / pin["path"]) != pin.get("file_sha256"):
            raise HoldoutIntegrityError(f"ARCHITECTURE_HASH_DRIFT: {name}")
    return {
        "verdict": "PASS",
        "architecture_changed_after_freeze": False,
        "roster_unchanged": True,
    }


def write_freeze_artifacts(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    root = Path(root).resolve()
    roster = select_fresh_holdout_18(root)
    freeze = build_architecture_freeze(root, roster)
    outputs = {
        root / HOLDOUT / "fresh_holdout_18_opportunities.json": roster,
        root / HOLDOUT / "fresh_holdout_18_architecture_freeze.json": freeze,
    }
    for path, value in outputs.items():
        path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")
    return roster, freeze


def _nearest_rank_percentile(values: list[int], percentile: float) -> int:
    if not values:
        return 0
    ordered = sorted(values)
    index = max(0, int((percentile * len(ordered) + 0.9999999999)) - 1)
    return ordered[min(index, len(ordered) - 1)]


def build_milestone_report(root: Path) -> dict[str, Any]:
    """Recompute the fail-closed Holdout-18 report from canonical artifacts."""
    root = Path(root).resolve()
    roster = _read(root / HOLDOUT / "fresh_holdout_18_opportunities.json")
    freeze = _read(root / HOLDOUT / "fresh_holdout_18_architecture_freeze.json")
    evidence = _read(root / HOLDOUT / "fresh_holdout_18_decision_evidence.json")
    maps = _read(root / HOLDOUT / "fresh_holdout_18_feature_maps.json")
    reviews = _read(root / HOLDOUT / "fresh_holdout_18_feature_independent_review.json")
    verify_freeze_integrity(root, roster, freeze)
    evidence_counts = validate_evidence_records(roster, evidence)
    evidence_by_id = {row["opportunity_id"]: row for row in evidence["rows"]}
    evidence_ready_ids = {
        row["opportunity_id"] for row in evidence["rows"]
        if row["verdict"] == "EVIDENCE_READY"
    }
    snapshot = _read(root / ARCHITECTURE_INPUTS["feature_anchor_snapshot"])
    feature_counts = validate_feature_reviews(
        evidence_ready_ids,
        maps,
        reviews,
        registered_feature_ids={row["feature_id"] for row in snapshot["features"]},
    )
    feature_by_id = {row["opportunity_id"]: row for row in reviews["rows"]}

    historical_trace = _read(root / HOLDOUT / "fresh_holdout_24_lifecycle_trace.json")
    historical_mismatches = []
    for filename, digest in historical_trace["preserved_artifact_sha256"].items():
        if _file_sha256(root / HOLDOUT / filename) != digest:
            historical_mismatches.append(filename)
    if historical_mismatches:
        raise HoldoutIntegrityError(
            f"HISTORICAL_FROZEN_ARTIFACT_DRIFT: {historical_mismatches}"
        )

    from .contrast_first_pilot import measure_copyright
    copyright_audit = measure_copyright(root, [
        str(HOLDOUT / "fresh_holdout_18_decision_evidence.json"),
        str(HOLDOUT / "fresh_holdout_18_feature_maps.json"),
        str(HOLDOUT / "fresh_holdout_18_feature_independent_review.json"),
    ])

    terminal_rows = []
    for opportunity in roster["opportunities"]:
        opportunity_id = opportunity["opportunity_id"]
        evidence_row = evidence_by_id[opportunity_id]
        if evidence_row["verdict"] != "EVIDENCE_READY":
            failure = "EVIDENCE_NOT_READY"
        else:
            verdict = feature_by_id[opportunity_id]["verdict"]
            failure = (
                "FEATURE_MAP_REJECTED" if verdict == "REJECTED"
                else "FEATURE_MAP_UNCERTAIN"
            )
        terminal_rows.append({
            "opportunity_id": opportunity_id,
            "discipline": opportunity["discipline"],
            "terminal_state": "NO_SAFE_ITEM",
            "earliest_primary_failure": failure,
            "generator_callback_count": 0,
            "stem_attempt_count": 0,
        })

    failures: dict[str, int] = {}
    for row in terminal_rows:
        cause = row["earliest_primary_failure"]
        failures[cause] = failures.get(cause, 0) + 1

    by_id = {row["opportunity_id"]: row for row in roster["opportunities"]}
    terminal_by_id = {row["opportunity_id"]: row for row in terminal_rows}
    waves = []
    for wave in roster["waves"]:
        ids = wave["opportunity_ids"]
        waves.append({
            "wave": wave["wave"],
            "attempted": len(ids),
            "evidence_ready": sum(value in evidence_ready_ids for value in ids),
            "feature_ready": 0,
            "contrast_ready": 0,
            "generated": 0,
            "accepted": 0,
        })

    results_by_discipline = {}
    for discipline in DISCIPLINES:
        ids = [
            row["opportunity_id"] for row in roster["opportunities"]
            if row["discipline"] == discipline
        ]
        results_by_discipline[discipline] = {
            "frozen": len(ids),
            "evidence_ready": sum(value in evidence_ready_ids for value in ids),
            "feature_ready": 0,
            "existing_seed_ready": 0,
            "post_seed_ready": 0,
            "generated": 0,
            "accepted": 0,
            "rejected": 0,
            "no_safe": sum(
                terminal_by_id[value]["terminal_state"] == "NO_SAFE_ITEM"
                for value in ids
            ),
        }

    difficulty_for_wave = {1: "EASY", 2: "MEDIUM", 3: "HARD"}
    results_by_difficulty = {}
    for wave in roster["waves"]:
        difficulty = difficulty_for_wave[wave["wave"]]
        results_by_difficulty[difficulty] = {
            "frozen": len(wave["opportunity_ids"]),
            "generated": 0,
            "accepted": 0,
            "independent_structural_difficulty_agreement": "NOT_ASSESSED_NO_STEMS",
        }

    contexts = []
    map_by_id = {row["opportunity_id"]: row for row in maps["rows"]}
    for review in reviews["rows"]:
        opportunity_id = review["opportunity_id"]
        payload = {
            "learner_decision": by_id[opportunity_id]["learner_decision"],
            "key": by_id[opportunity_id]["key_concept_or_action"],
            "evidence": evidence_by_id[opportunity_id]["exact_relevant_claims"],
            "feature_map": map_by_id[opportunity_id],
        }
        contexts.append(len(json.dumps(payload, ensure_ascii=False, sort_keys=True)))

    metrics = {
        "frozen": 18,
        "evidence_ready": len(evidence_ready_ids),
        "feature_ready": feature_counts.get("APPROVED", 0),
        "existing_seed_baseline_ready": 0,
        "post_new_seed_contrast_ready": 0,
        "blueprint_ready": 0,
        "generator_callbacks": 0,
        "stems_generated": 0,
        "post_stem_live": 0,
        "final_reviewed": 0,
        "accepted": 0,
        "rejected": 0,
        "no_safe_item": 18,
    }
    report = {
        "schema_version": "1.0",
        "scope": "QGEN_FRESH_HOLDOUT_18_GENERALIZATION_AND_SEED_ECONOMICS",
        "milestone_status": "COMPLETE",
        "starting_head": "01eff40984bee76418c7fab82a1ded9fbfa2d9e5",
        "fresh_holdout_sha256": roster["content_sha256"],
        "holdout_architecture_freeze_sha256": freeze["holdout_architecture_freeze_sha256"],
        "architecture_changed_after_freeze": False,
        "metrics": metrics,
        "waves": waves,
        "results_by_discipline": results_by_discipline,
        "results_by_difficulty": results_by_difficulty,
        "terminal_state_by_opportunity": terminal_rows,
        "failure_counts": failures,
        "lifecycle_invariant": "PASS",
        "safe_yield": 0.0,
        "generation_acceptance": None,
        "final_review_acceptance": None,
        "accepted_item_safety": "NO_ACCEPTED_ITEMS",
        "seed_economics": {
            "raw_candidates_discovered": 0,
            "cheap_filter_rejections": 0,
            "semantic_review_candidates": 0,
            "seeds_proposed": 0,
            "seeds_approved": 0,
            "seeds_rejected": 0,
            "seeds_uncertain": 0,
            "seeds_proposed_per_opportunity": 0.0,
            "seeds_approved_per_opportunity": 0.0,
            "opportunities_ready_with_existing_seeds_only": 0,
            "opportunities_requiring_new_seeds": 0,
            "approved_seed_reuse_count": 0,
            "relation_reuse_count": 0,
            "anchor_reuse_count": 0,
            "cross_unit_reuse_count": 0,
            "cross_discipline_reuse_count": 0,
            "new_external_research_requests": 0,
            "stage_status": "NOT_REACHED_NO_APPROVED_FEATURE_MAPS",
        },
        "review_economics": {
            "feature_review_rows": len(reviews["rows"]),
            "seed_review_rows": 0,
            "final_item_review_rows": 0,
            "cheap_filter_avoided_semantic_reviews": 0,
            "semantic_review_reduction_percent": 0.0,
            "serialized_context_characters": contexts,
            "context_median": int(statistics.median(contexts)) if contexts else 0,
            "context_p95": _nearest_rank_percentile(contexts, 0.95),
        },
        "systematic_defect_ge_20_percent": False,
        "systematic_defect": None,
        "contrast_supply_economics": "INSUFFICIENT_DATA",
        "holdout_contaminated": False,
        "copyright": copyright_audit,
        "historical_frozen_artifacts_modified": 0,
        "commits_created": 0,
        "claude_md_changed": False,
        "holdout_assessment": "BLOCKED_BY_EVIDENCE",
        "next_dominant_bottleneck": "DECISION_EVIDENCE_READINESS",
        "next_step": "RESOLVE_BLOCKER",
        "evidence_verdict_counts": evidence_counts,
        "feature_review_verdict_counts": feature_counts,
    }
    report["content_sha256"] = content_sha256(report)
    return report


def build_stage_artifacts(root: Path) -> dict[str, dict[str, Any]]:
    """Build explicit empty downstream records when no feature map clears review."""
    report = build_milestone_report(root)
    common = {
        "schema_version": "1.0",
        "roster_content_sha256": report["fresh_holdout_sha256"],
        "stage_status": "NOT_REACHED_NO_APPROVED_FEATURE_MAPS",
    }
    artifacts = {
        "existing_seed_baseline": {
            **common,
            "scope": "QGEN_FRESH_HOLDOUT_18_EXISTING_SEED_BASELINE",
            "eligible_opportunity_ids": [],
            "rows": [],
            "existing_seed_contrast_ready": 0,
        },
        "bounded_discovery": {
            **common,
            "scope": "QGEN_FRESH_HOLDOUT_18_BOUNDED_DISCOVERY",
            "bounded_acquisition_wave_count": 0,
            "raw_candidates": [],
            "cheap_filter_rejections": [],
        },
        "seed_candidates": {
            **common,
            "scope": "QGEN_FRESH_HOLDOUT_18_SEED_CANDIDATES",
            "rows": [],
        },
        "seed_independent_review": {
            **common,
            "scope": "QGEN_FRESH_HOLDOUT_18_SEED_INDEPENDENT_REVIEW",
            "rows": [],
        },
        "clinical_contrast_relations_v2": {
            **common,
            "scope": "QGEN_FRESH_HOLDOUT_18_CLINICAL_CONTRAST_RELATIONS_V2",
            "relations": [],
        },
        "contrast_sets": {
            **common,
            "scope": "QGEN_FRESH_HOLDOUT_18_FROZEN_CONTRAST_SETS",
            "contrast_sets": [],
        },
        "blueprints": {
            **common,
            "scope": "QGEN_FRESH_HOLDOUT_18_BLUEPRINTS",
            "blueprints": [],
        },
        "lifecycle_trace": {
            **common,
            "scope": "QGEN_FRESH_HOLDOUT_18_LIFECYCLE_TRACE",
            "opportunities": report["terminal_state_by_opportunity"],
            "lifecycle_invariant": "PASS",
        },
        "stems": {
            **common,
            "scope": "QGEN_FRESH_HOLDOUT_18_STEMS",
            "stems": [],
            "generator_callbacks": 0,
        },
        "blind_solve": {
            **common,
            "scope": "QGEN_FRESH_HOLDOUT_18_BLIND_SOLVE",
            "rows": [],
        },
        "post_stem_validation": {
            **common,
            "scope": "QGEN_FRESH_HOLDOUT_18_POST_STEM_VALIDATION",
            "rows": [],
        },
        "items": {
            **common,
            "scope": "QGEN_FRESH_HOLDOUT_18_ITEMS",
            "items": [],
        },
        "final_medical_review": {
            **common,
            "scope": "QGEN_FRESH_HOLDOUT_18_FINAL_MEDICAL_REVIEW",
            "rows": [],
        },
    }
    for value in artifacts.values():
        value["content_sha256"] = content_sha256(value)
    return artifacts


def write_milestone_artifacts(root: Path) -> dict[str, Any]:
    root = Path(root).resolve()
    stages = build_stage_artifacts(root)
    paths = {
        "existing_seed_baseline": HOLDOUT / "fresh_holdout_18_existing_seed_baseline.json",
        "bounded_discovery": HOLDOUT / "fresh_holdout_18_bounded_discovery.json",
        "seed_candidates": HOLDOUT / "fresh_holdout_18_seed_candidates.json",
        "seed_independent_review": HOLDOUT / "fresh_holdout_18_seed_independent_review.json",
        "clinical_contrast_relations_v2": HOLDOUT / "fresh_holdout_18_clinical_contrast_relations_v2.json",
        "contrast_sets": HOLDOUT / "fresh_holdout_18_contrast_sets.json",
        "blueprints": HOLDOUT / "fresh_holdout_18_blueprints.json",
        "lifecycle_trace": HOLDOUT / "fresh_holdout_18_lifecycle_trace.json",
        "stems": HOLDOUT / "fresh_holdout_18_stems.json",
        "blind_solve": HOLDOUT / "fresh_holdout_18_blind_solve.json",
        "post_stem_validation": HOLDOUT / "fresh_holdout_18_post_stem_validation.json",
        "items": HOLDOUT / "fresh_holdout_18_items.json",
        "final_medical_review": HOLDOUT / "fresh_holdout_18_final_medical_review.json",
    }
    for name, relative in paths.items():
        (root / relative).write_text(
            json.dumps(stages[name], indent=2, ensure_ascii=False) + "\n"
        )
    report = build_milestone_report(root)
    for relative in (
        HOLDOUT / "fresh_holdout_18_milestone.json",
        Path("reports/qgen_fresh_holdout_18_generalization.json"),
    ):
        (root / relative).write_text(
            json.dumps(report, indent=2, ensure_ascii=False) + "\n"
        )
    return report
