"""Deterministic guards and accounting for the clean Transfer-18 milestone.

Clinical prerequisite, candidate, feature, bundle, and item judgements remain
explicit data.  This module only validates chronology and frozen contracts,
performs exact-scope cache replay, builds an append-only child cache, and
computes arithmetic used by the milestone report.
"""

from __future__ import annotations

from collections import Counter
from typing import Any, Mapping, Sequence

from .contrast_supply_v3 import canonical_content_sha256
from .contrast_supply_v5 import (
    V5_CANDIDATE_BUDGET,
    classify_bundle_admission,
    lookup_contrast_bundle,
    validate_decision_signature_v2,
)


class CleanTransferError(ValueError):
    """Raised when continuing would invalidate the clean experiment."""


PREREQUISITE_REQUIRED_FIELDS = frozenset({
    "transfer_id",
    "prerequisite_status",
    "decision_evidence_refs",
    "feature_readiness",
    "learner_decision_family",
    "learner_decision",
    "key",
    "key_aliases",
    "demanded_response_class",
    "decision_granularity",
    "decision_signature_v2",
    "applicability_context",
    "semantic_families",
    "chapter_code",
})

FORBIDDEN_PREREQUISITE_TOKENS = (
    "candidate", "alternative", "bundle", "retrieval", "contrast",
)


def verify_untouched_selection(
    selection: Mapping[str, Any], expected_cohort_sha256: str,
) -> dict[str, Any]:
    if selection.get("cohort_run") or selection.get("candidate_retrieval_run"):
        raise CleanTransferError("Transfer-18 was previously run")
    if selection.get("cohort_sha256") != expected_cohort_sha256:
        raise CleanTransferError("Transfer-18 cohort hash mismatch")
    if selection.get("cohort_size") != 18 or len(selection.get("opportunities", ())) != 18:
        raise CleanTransferError("Transfer-18 must contain exactly 18 opportunities")
    expected_distribution = {
        "MED": 3, "PED": 3, "OBGYN": 3,
        "SURG": 3, "PSY": 3, "PHELO": 3,
    }
    actual = dict(Counter(str(row["discipline"]) for row in selection["opportunities"]))
    if actual != expected_distribution or selection.get("per_discipline") != expected_distribution:
        raise CleanTransferError("Transfer-18 discipline distribution mismatch")
    return {"untouched": True, "cohort_size": 18, "per_discipline": actual}


def build_validation_contract(hashes: Mapping[str, str]) -> dict[str, Any]:
    required = {"transfer18", "signature_v2", "discovery_v5", "bundle_cache_v1"}
    if set(hashes) != required or any(len(str(value)) != 64 for value in hashes.values()):
        raise CleanTransferError("validation contract requires four SHA256 values")
    contract = {
        "schema_version": "CLEAN_TRANSFER18_BUNDLE_VALIDATION_CONTRACT_V1",
        "frozen_before_candidate_lookup": True,
        "transfer18_sha256": hashes["transfer18"],
        "decision_signature_v2_sha256": hashes["signature_v2"],
        "discovery_v5_sha256": hashes["discovery_v5"],
        "bundle_cache_v1_sha256": hashes["bundle_cache_v1"],
        "candidate_budget": V5_CANDIDATE_BUDGET,
        "bundle_admission_thresholds": {
            "STRONG_BUNDLE": ">=4",
            "MINIMUM_GENERATABLE_BUNDLE": "==3",
            "PARTIAL_BUNDLE": "1-2",
            "NO_SAFE_BUNDLE": "0",
        },
        "matrix_states": ["PRESENT", "ABSENT", "UNKNOWN", "NOT_APPLICABLE"],
        "matrix_semantics": "UNKNOWN is not ABSENT; silence is UNKNOWN unless evidence establishes absence.",
        "one_wave_top_up_rule": {
            "maximum_waves": 1,
            "maximum_canonical_candidates_per_anchor": V5_CANDIDATE_BUDGET,
            "repeat_search_for_yield": False,
        },
        "question_generation_rule": {
            "minimum_approved_live_alternatives": 3,
            "maximum_questions": 12,
            "one_question_per_anchor": True,
            "retries": 0,
            "candidate_swaps_after_stem": False,
        },
    }
    contract["content_sha256"] = canonical_content_sha256(contract)
    return contract


def validate_prerequisite_artifact(
    selection: Mapping[str, Any], artifact: Mapping[str, Any],
) -> dict[str, Any]:
    roster_ids = [str(row["transfer_id"]) for row in selection.get("opportunities", ())]
    rows = list(artifact.get("rows", ()))
    if [str(row.get("transfer_id")) for row in rows] != roster_ids:
        raise CleanTransferError("prerequisite rows must match the frozen roster in canonical order")
    for row in rows:
        missing = PREREQUISITE_REQUIRED_FIELDS - set(row)
        if missing:
            raise CleanTransferError(f"prerequisite row missing {sorted(missing)[0]}")
        leaked = [
            field for field in row
            if any(token in field.casefold() for token in FORBIDDEN_PREREQUISITE_TOKENS)
        ]
        if leaked:
            raise CleanTransferError(f"candidate-supply field forbidden in prerequisites: {leaked[0]}")
        validate_decision_signature_v2(row["decision_signature_v2"])
        if row["prerequisite_status"] not in ("READY", "NOT_READY"):
            raise CleanTransferError("invalid prerequisite status")
        if row["prerequisite_status"] == "READY":
            if row["feature_readiness"] != "READY" or not row["decision_evidence_refs"]:
                raise CleanTransferError("READY prerequisite lacks evidence or feature readiness")
    ready = sum(row["prerequisite_status"] == "READY" for row in rows)
    return {"ready_count": ready, "denominator": len(roster_ids)}


def run_zero_topup_replay(
    prerequisite_rows: Sequence[Mapping[str, Any]], cache_v1: Mapping[str, Any],
) -> dict[str, Any]:
    rows = []
    reused_candidate_ids: set[str] = set()
    cross_unit = 0
    cross_discipline = 0
    for prerequisite in prerequisite_rows:
        if prerequisite.get("prerequisite_status") != "READY":
            rows.append({
                "transfer_id": prerequisite["transfer_id"],
                "bundle_id": None,
                "alternative_count": 0,
                "contrast_ready": False,
            })
            continue
        signature = prerequisite["decision_signature_v2"]
        bundle = lookup_contrast_bundle(
            cache_v1,
            learner_decision_family=str(prerequisite["learner_decision_family"]),
            decision_signature_v2=signature,
            target_subdomain=str(signature["target_subdomain"]),
            applicability_context=str(prerequisite["applicability_context"]),
        )
        candidates = list((bundle or {}).get("option_candidates", ()))
        reused_candidate_ids.update(str(row["candidate_id"]) for row in candidates)
        if bundle and prerequisite.get("study_unit_id") not in set(bundle.get("study_unit_ids", ())):
            cross_unit += 1
        if bundle and prerequisite.get("discipline") not in set(bundle.get("disciplines", ())):
            cross_discipline += 1
        rows.append({
            "transfer_id": prerequisite["transfer_id"],
            "bundle_id": (bundle or {}).get("bundle_id"),
            "alternative_count": len(candidates),
            "contrast_ready": len(candidates) >= 3,
        })
    counts = [row["alternative_count"] for row in rows]
    return {
        "rows": rows,
        "threshold_counts": {
            str(threshold): sum(count >= threshold for count in counts)
            for threshold in range(1, 6)
        },
        "contrast_ready": sum(count >= 3 for count in counts),
        "reuse": {
            "seed_reuse": len(reused_candidate_ids),
            "relation_reuse": len(reused_candidate_ids),
            "anchor_reuse": len(reused_candidate_ids),
            "feature_profile_reuse": len(reused_candidate_ids),
            "bundle_reuse": sum(bool(row["bundle_id"]) for row in rows),
            "cross_unit_reuse": cross_unit,
            "cross_discipline_reuse": cross_discipline,
        },
    }


def build_bundle_cache_v2(
    cache_v1: Mapping[str, Any], transfer_bundles: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    approved = [
        copy_mapping(bundle) for bundle in transfer_bundles
        if (bundle.get("bundle_review") or {}).get("verdict") == "APPROVED"
    ]
    approved.sort(key=lambda row: str(row["bundle_id"]))
    baseline = [copy_mapping(bundle) for bundle in cache_v1.get("bundles", ())]
    value = {
        "schema_version": "CLINICAL_CONTRAST_BUNDLE_CACHE_V2",
        "parent_sha256": cache_v1["content_sha256"],
        "baseline_bundle_count": len(baseline),
        "new_bundle_count": len(approved),
        "new_alternative_count": sum(len(row.get("option_candidates", ())) for row in approved),
        "bundles": baseline + approved,
    }
    value["content_sha256"] = canonical_content_sha256(value)
    return value


def copy_mapping(value: Mapping[str, Any]) -> dict[str, Any]:
    """Deep-copy JSON-compatible mappings without sharing child-cache state."""
    import copy
    return copy.deepcopy(dict(value))


def classify_density(alternative_counts: Sequence[int]) -> dict[str, Any]:
    classes = [classify_bundle_admission(int(count)) for count in alternative_counts]
    return {
        "threshold_counts": {
            str(threshold): sum(count >= threshold for count in alternative_counts)
            for threshold in range(1, 6)
        },
        "admission_counts": {
            name: classes.count(name) for name in (
                "STRONG_BUNDLE", "MINIMUM_GENERATABLE_BUNDLE",
                "PARTIAL_BUNDLE", "NO_SAFE_BUNDLE",
            )
        },
    }


def verify_architecture_freeze(
    freeze: Mapping[str, Any], current_file_sha256: Mapping[str, str],
) -> dict[str, Any]:
    expected = dict(freeze.get("file_sha256", {}))
    actual = dict(current_file_sha256)
    if expected != actual:
        changed = sorted(set(expected) | set(actual))
        changed = [key for key in changed if expected.get(key) != actual.get(key)]
        raise CleanTransferError(f"architecture drift after unblinding: {', '.join(changed)}")
    return {"integrity": "PASS", "file_count": len(expected)}
