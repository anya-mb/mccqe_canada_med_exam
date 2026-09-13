"""Selective opportunity-relation classification support.

Matcher V5 keeps semantic interpretation external and applies a deterministic,
fail-closed automation policy to structured evidence.  An abstention is an
automation decision, never a clinical relation label.
"""

from __future__ import annotations

from collections import Counter, defaultdict
import hashlib
from typing import Any, Mapping, Sequence

from scripts.qbank.opportunity_relation_v4 import (
    RELATIONS, _safe_ratio, compute_multiclass_metrics, validate_matcher_predictions, with_hash,
)


AUTO_ACCEPT = "AUTO_ACCEPT"
NEEDS_SEMANTIC_ADJUDICATION = "NEEDS_SEMANTIC_ADJUDICATION"
AUTOMATION_DECISIONS = (AUTO_ACCEPT, NEEDS_SEMANTIC_ADJUDICATION)

TRISTATE = {"YES", "NO", "UNCERTAIN"}
CONTAINMENT = {"NONE", "A_WITHIN_B", "B_WITHIN_A", "UNCERTAIN"}
RESIDUAL_DIFFERENCES = {
    "NONE", "SYNONYMY_ONLY", "WRAPPER_ONLY", "EVIDENCE_PATH",
    "ITEM_REALIZATION", "MATERIAL", "UNRESOLVED",
}
STRUCTURED_EVIDENCE_FIELDS = {
    "predicted_relation", "same_principal_decision", "same_answer_scope",
    "directional_containment", "independently_scoreable_difference",
    "context_changes_correct_action", "residual_difference",
    "near_duplicate_signal", "internal_conflict", "insufficient_context",
    "justification",
}
CRITICAL_RELATIONS = {
    "EQUIVALENT", "REGISTRY_BROADER_CONTAINS_BENCHMARK",
    "REGISTRY_NARROWER_THAN_BENCHMARK", "VARIANT_OF_SAME_DECISION",
    "NEAR_DUPLICATE",
}
EQUIVALENCE_IDENTITY_METADATA_FIELDS = (
    "opportunity_family", "response_class", "clinical_stage", "population_context",
    "severity_context", "MCC_physician_activity", "MCC_objective_ids",
)


def build_development_packet(*packets: Mapping[str, Any]) -> dict[str, Any]:
    """Combine already exposed prediction inputs without adding gold metadata."""
    if not packets:
        raise ValueError("DEVELOPMENT_PACKET_REQUIRES_INPUTS")
    contracts = [packet.get("atomic_opportunity_contract") for packet in packets]
    if any(contract != contracts[0] for contract in contracts[1:]):
        raise ValueError("DEVELOPMENT_INPUT_CONTRACT_MISMATCH")
    rows: dict[str, dict[str, Any]] = {}
    for packet in packets:
        for source in packet.get("pairs", []):
            pair_id = source["pair_id"]
            if pair_id in rows:
                raise ValueError("DEVELOPMENT_INPUT_PAIR_REUSED")
            rows[pair_id] = dict(source)
    return with_hash({
        "schema_version": "5.0",
        "scope": "MATCHER_V5_EXPOSED_DEVELOPMENT_INPUT",
        "source_input_sha256s": [packet.get("content_sha256") for packet in packets],
        "atomic_opportunity_contract": contracts[0],
        "gold_labels_withheld": True,
        "development_rows": len(rows),
        "pairs": [rows[pair_id] for pair_id in sorted(rows)],
    })


def validate_structured_semantic_predictions(
    predictions: Mapping[str, Any], packet: Mapping[str, Any],
) -> dict[str, dict[str, Any]]:
    if predictions.get("source_input_sha256") != packet.get("content_sha256"):
        raise ValueError("MATCHER_PREDICTION_INPUT_HASH_MISMATCH")
    if not predictions.get("matcher_id"):
        raise ValueError("MISSING_MATCHER_ID")
    rows = predictions.get("predictions", [])
    by_id = {row.get("pair_id"): row for row in rows}
    expected = {row["pair_id"] for row in packet.get("pairs", [])}
    if None in by_id or len(by_id) != len(rows) or set(by_id) != expected:
        raise ValueError("MATCHER_PREDICTIONS_MUST_COVER_EVERY_PAIR_EXACTLY_ONCE")
    for row in rows:
        if not STRUCTURED_EVIDENCE_FIELDS.issubset(row):
            raise ValueError("MISSING_STRUCTURED_SEMANTIC_EVIDENCE")
        if row["predicted_relation"] not in RELATIONS[:-1]:
            raise ValueError("INVALID_PREDICTED_RELATION")
        if any(row[field] not in TRISTATE for field in (
            "same_principal_decision", "same_answer_scope",
            "independently_scoreable_difference", "context_changes_correct_action",
            "near_duplicate_signal",
        )):
            raise ValueError("INVALID_TRISTATE_SEMANTIC_EVIDENCE")
        if row["directional_containment"] not in CONTAINMENT:
            raise ValueError("INVALID_DIRECTIONAL_CONTAINMENT")
        if row["residual_difference"] not in RESIDUAL_DIFFERENCES:
            raise ValueError("INVALID_RESIDUAL_DIFFERENCE")
        if not isinstance(row["internal_conflict"], bool) or not isinstance(row["insufficient_context"], bool):
            raise ValueError("INVALID_SEMANTIC_BOOLEAN")
        if not str(row["justification"]).strip():
            raise ValueError("MISSING_SEMANTIC_JUSTIFICATION")
    return by_id


def apply_selective_policy(analysis: Mapping[str, Any]) -> dict[str, Any]:
    """Return an automation decision justified by relation-specific invariants."""
    relation = analysis["predicted_relation"]
    reasons: list[str] = []
    if analysis.get("internal_conflict"):
        reasons.append("INTERNAL_SEMANTIC_CONFLICT")
    if analysis.get("insufficient_context"):
        reasons.append("INSUFFICIENT_CONTEXT")

    if not reasons:
        if relation == "DUPLICATE":
            reasons.append("DUPLICATE_REQUIRES_DETERMINISTIC_IDENTITY")
        elif relation == "EQUIVALENT":
            if analysis["residual_difference"] not in {"NONE", "SYNONYMY_ONLY"}:
                reasons.append("EQUIVALENT_HAS_RESIDUAL_VARIANT_DELTA")
            if not _matches(analysis, same_principal_decision="YES", same_answer_scope="YES",
                            independently_scoreable_difference="NO", context_changes_correct_action="NO",
                            directional_containment="NONE", near_duplicate_signal="NO"):
                reasons.append("EQUIVALENCE_INVARIANTS_NOT_SATISFIED")
        elif relation == "VARIANT_OF_SAME_DECISION":
            reasons.append("VARIANT_CLASS_REQUIRES_ADJUDICATION_DURING_LABEL_INSTABILITY")
        elif relation in {"REGISTRY_BROADER_CONTAINS_BENCHMARK", "REGISTRY_NARROWER_THAN_BENCHMARK"}:
            required_direction = (
                "A_WITHIN_B" if relation == "REGISTRY_BROADER_CONTAINS_BENCHMARK" else "B_WITHIN_A"
            )
            if analysis["directional_containment"] != required_direction:
                reasons.append("CONTAINMENT_DIRECTION_NOT_EXPLICIT")
            if analysis["same_answer_scope"] != "NO" or analysis["independently_scoreable_difference"] != "YES":
                reasons.append("CONTAINMENT_SCOPE_INVARIANTS_NOT_SATISFIED")
            if analysis["context_changes_correct_action"] == "UNCERTAIN":
                reasons.append("CONTEXT_EFFECT_UNRESOLVED")
        elif relation == "NEAR_DUPLICATE":
            reasons.append("NEAR_DUPLICATE_REQUIRES_ADJUDICATION")
        elif relation == "RELATED_BUT_DISTINCT":
            if analysis["independently_scoreable_difference"] != "YES":
                reasons.append("DISTINCTNESS_NOT_ESTABLISHED")
            if analysis["directional_containment"] != "NONE":
                reasons.append("DISTINCTNESS_CONFLICTS_WITH_CONTAINMENT")
        elif relation == "UNRELATED":
            if not _matches(analysis, same_principal_decision="NO", same_answer_scope="NO",
                            directional_containment="NONE"):
                reasons.append("UNRELATEDNESS_NOT_ESTABLISHED")

    return {
        "predicted_relation": relation,
        "automation_decision": NEEDS_SEMANTIC_ADJUDICATION if reasons else AUTO_ACCEPT,
        "abstention_reasons": reasons,
    }


def build_selective_predictions(
    packet: Mapping[str, Any], semantic_predictions: Mapping[str, Any], *, matcher_id: str,
    corroborating_predictions: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    semantic = validate_structured_semantic_predictions(semantic_predictions, packet)
    corroborating = (
        validate_matcher_predictions(corroborating_predictions, packet)
        if corroborating_predictions is not None else None
    )
    predictions = []
    for pair in sorted(packet.get("pairs", []), key=lambda row: row["pair_id"]):
        pair_id = pair["pair_id"]
        analysis = semantic[pair_id]
        if pair.get("opportunity_a") == pair.get("opportunity_b"):
            policy = {
                "predicted_relation": "DUPLICATE",
                "automation_decision": AUTO_ACCEPT,
                "abstention_reasons": [],
            }
            source = "DETERMINISTIC_EXACT_PROJECTED_RECORD_OVERRIDE"
        else:
            policy = apply_selective_policy(analysis)
            if (
                policy["predicted_relation"] == "EQUIVALENT"
                and any(
                    pair.get("opportunity_a", {}).get(field) != pair.get("opportunity_b", {}).get(field)
                    for field in EQUIVALENCE_IDENTITY_METADATA_FIELDS
                )
            ):
                policy = {
                    **policy,
                    "automation_decision": NEEDS_SEMANTIC_ADJUDICATION,
                    "abstention_reasons": sorted(set([
                        *policy["abstention_reasons"], "EQUIVALENT_IDENTITY_METADATA_DELTA",
                    ])),
                }
            if corroborating is not None and corroborating[pair_id]["relation"] != policy["predicted_relation"]:
                policy = {
                    **policy,
                    "automation_decision": NEEDS_SEMANTIC_ADJUDICATION,
                    "abstention_reasons": sorted(set([
                        *policy["abstention_reasons"], "SEMANTIC_CLASSIFIER_DISAGREEMENT",
                    ])),
                }
            source = "STRUCTURED_SEMANTIC_EVIDENCE_PLUS_DETERMINISTIC_POLICY"
        predictions.append({
            "pair_id": pair_id,
            **policy,
            "decision_source": source,
            "structured_semantic_analysis": {
                field: analysis[field] for field in sorted(STRUCTURED_EVIDENCE_FIELDS)
            },
        })
    return with_hash({
        "schema_version": "5.0",
        "scope": f"{matcher_id}_PREDICTIONS",
        "matcher_id": matcher_id,
        "architecture": "SELECTIVE_HYBRID",
        "source_input_sha256": packet["content_sha256"],
        "semantic_prediction_sha256": semantic_predictions.get("content_sha256"),
        "corroborating_prediction_sha256": (
            corroborating_predictions.get("content_sha256") if corroborating_predictions else None
        ),
        "deterministic_override": "EXACT_PROJECTED_RECORD_DUPLICATE_ONLY",
        "automation_decisions": list(AUTOMATION_DECISIONS),
        "predictions": predictions,
    })


def _matches(analysis: Mapping[str, Any], **expected: str) -> bool:
    return all(analysis.get(field) == value for field, value in expected.items())


def compute_selective_metrics(
    gold_rows: Sequence[Mapping[str, Any]], predictions: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    gold = {row["pair_id"]: row["relation"] for row in gold_rows}
    guessed = {row["pair_id"]: row for row in predictions}
    if len(gold) != len(gold_rows) or len(guessed) != len(predictions) or set(gold) != set(guessed):
        raise ValueError("SELECTIVE_METRICS_PAIR_COVERAGE_MISMATCH")
    auto_ids = sorted(
        pair_id for pair_id, row in guessed.items() if row["automation_decision"] == AUTO_ACCEPT
    )
    auto_actual = [gold[pair_id] for pair_id in auto_ids]
    auto_predicted = [guessed[pair_id]["predicted_relation"] for pair_id in auto_ids]
    supported_labels = sorted(set(auto_actual) | set(auto_predicted))
    class_metrics = (
        compute_multiclass_metrics(auto_actual, auto_predicted, labels=supported_labels, minimum_support=1)
        if auto_ids else {
            "pairs": 0, "accuracy": 0.0, "macro_precision": 0.0, "macro_recall": 0.0,
            "macro_f1": 0.0, "per_class": {}, "confusion_matrix": {},
        }
    )
    critical_predicted_ids = [
        pair_id for pair_id in auto_ids if guessed[pair_id]["predicted_relation"] in CRITICAL_RELATIONS
    ]
    critical_correct = sum(
        gold[pair_id] == guessed[pair_id]["predicted_relation"] for pair_id in critical_predicted_ids
    )
    catastrophic = []
    for pair_id in auto_ids:
        actual, predicted = gold[pair_id], guessed[pair_id]["predicted_relation"]
        if (
            {actual, predicted} == {"EQUIVALENT", "VARIANT_OF_SAME_DECISION"}
            or (actual in {"REGISTRY_BROADER_CONTAINS_BENCHMARK", "REGISTRY_NARROWER_THAN_BENCHMARK"}
                and predicted in {"REGISTRY_BROADER_CONTAINS_BENCHMARK", "REGISTRY_NARROWER_THAN_BENCHMARK"}
                and actual != predicted)
            or (actual == "EQUIVALENT" and predicted in {"RELATED_BUT_DISTINCT", "UNRELATED"})
        ):
            catastrophic.append({"pair_id": pair_id, "actual": actual, "predicted": predicted})
    return {
        "pairs": len(gold),
        "auto_resolved": len(auto_ids),
        "abstained": len(gold) - len(auto_ids),
        "auto_coverage": _safe_ratio(len(auto_ids), len(gold)),
        "abstention_rate": _safe_ratio(len(gold) - len(auto_ids), len(gold)),
        "adjudication_rate": _safe_ratio(len(gold) - len(auto_ids), len(gold)),
        "auto_accuracy": class_metrics["accuracy"],
        "auto_macro_precision": class_metrics["macro_precision"],
        "auto_macro_recall": class_metrics["macro_recall"],
        "auto_macro_f1": class_metrics["macro_f1"],
        "auto_per_class": class_metrics["per_class"],
        "auto_confusion_matrix": class_metrics["confusion_matrix"],
        "auto_critical_precision": _safe_ratio(critical_correct, len(critical_predicted_ids)),
        "auto_critical_predictions": len(critical_predicted_ids),
        "catastrophic_errors": catastrophic,
    }


def build_grouped_development_folds(
    rows: Sequence[Mapping[str, Any]], *, fold_count: int = 5,
) -> list[dict[str, Any]]:
    if fold_count < 2:
        raise ValueError("DEVELOPMENT_FOLD_COUNT_TOO_SMALL")
    groups: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[str(row.get("leakage_group") or row["pair_id"])].append(row)
    fold_rows: list[list[Mapping[str, Any]]] = [[] for _ in range(fold_count)]
    fold_counts = [Counter() for _ in range(fold_count)]
    for group_id, group_rows in sorted(
        groups.items(),
        key=lambda item: (-len(item[1]), hashlib.sha256(f"v5-fold|{item[0]}".encode()).hexdigest()),
    ):
        relation_counts = Counter(row["relation"] for row in group_rows)
        selected = min(
            range(fold_count),
            key=lambda index: (
                sum((fold_counts[index][label] + count) ** 2 for label, count in relation_counts.items()),
                len(fold_rows[index]), index,
            ),
        )
        fold_rows[selected].extend(group_rows)
        fold_counts[selected].update(relation_counts)
    return [
        {
            "fold": index + 1,
            "pair_ids": sorted(row["pair_id"] for row in assigned),
            "relation_counts": dict(sorted(Counter(row["relation"] for row in assigned).items())),
        }
        for index, assigned in enumerate(fold_rows)
    ]
