from __future__ import annotations

from scripts.qbank.opportunity_relation_v5 import (
    AUTO_ACCEPT,
    NEEDS_SEMANTIC_ADJUDICATION,
    apply_selective_policy,
    build_development_packet,
    build_grouped_development_folds,
    build_selective_predictions,
    compute_selective_metrics,
    validate_structured_semantic_predictions,
)


def _analysis(relation: str, **overrides):
    row = {
        "predicted_relation": relation,
        "same_principal_decision": "YES",
        "same_answer_scope": "YES",
        "directional_containment": "NONE",
        "independently_scoreable_difference": "NO",
        "context_changes_correct_action": "NO",
        "residual_difference": "NONE",
        "near_duplicate_signal": "NO",
        "internal_conflict": False,
        "insufficient_context": False,
        "justification": "Hand-checked semantic analysis.",
    }
    row.update(overrides)
    return row


def test_selective_policy_distinguishes_equivalent_from_positive_variant_delta():
    equivalent = apply_selective_policy(_analysis("EQUIVALENT"))
    variant = apply_selective_policy(
        _analysis("VARIANT_OF_SAME_DECISION", residual_difference="WRAPPER_ONLY")
    )
    unsafe_equivalent = apply_selective_policy(
        _analysis("EQUIVALENT", residual_difference="WRAPPER_ONLY")
    )

    assert equivalent["automation_decision"] == AUTO_ACCEPT
    assert variant["automation_decision"] == NEEDS_SEMANTIC_ADJUDICATION
    assert variant["abstention_reasons"] == ["VARIANT_CLASS_REQUIRES_ADJUDICATION_DURING_LABEL_INSTABILITY"]
    assert unsafe_equivalent["automation_decision"] == NEEDS_SEMANTIC_ADJUDICATION
    assert unsafe_equivalent["abstention_reasons"] == ["EQUIVALENT_HAS_RESIDUAL_VARIANT_DELTA"]


def test_selective_policy_requires_explicit_containment_and_abstains_on_near_duplicates():
    broader = apply_selective_policy(
        _analysis(
            "REGISTRY_BROADER_CONTAINS_BENCHMARK",
            same_answer_scope="NO",
            directional_containment="A_WITHIN_B",
            independently_scoreable_difference="YES",
        )
    )
    unsupported_direction = apply_selective_policy(
        _analysis(
            "REGISTRY_NARROWER_THAN_BENCHMARK",
            same_answer_scope="NO",
            directional_containment="UNCERTAIN",
            independently_scoreable_difference="YES",
        )
    )
    near_duplicate = apply_selective_policy(
        _analysis(
            "NEAR_DUPLICATE",
            same_answer_scope="UNCERTAIN",
            near_duplicate_signal="YES",
            residual_difference="UNRESOLVED",
        )
    )

    assert broader["automation_decision"] == AUTO_ACCEPT
    assert unsupported_direction["automation_decision"] == NEEDS_SEMANTIC_ADJUDICATION
    assert "CONTAINMENT_DIRECTION_NOT_EXPLICIT" in unsupported_direction["abstention_reasons"]
    assert near_duplicate["automation_decision"] == NEEDS_SEMANTIC_ADJUDICATION
    assert near_duplicate["abstention_reasons"] == ["NEAR_DUPLICATE_REQUIRES_ADJUDICATION"]


def test_structured_prediction_validation_requires_every_pair_and_every_evidence_field():
    packet = {"content_sha256": "a" * 64, "pairs": [{"pair_id": "P1"}, {"pair_id": "P2"}]}
    predictions = {
        "matcher_id": "V5",
        "source_input_sha256": "a" * 64,
        "predictions": [
            {"pair_id": "P1", **_analysis("EQUIVALENT")},
            {"pair_id": "P2", **_analysis("UNRELATED", same_principal_decision="NO", same_answer_scope="NO")},
        ],
    }
    assert set(validate_structured_semantic_predictions(predictions, packet)) == {"P1", "P2"}

    incomplete = {**predictions, "predictions": [dict(predictions["predictions"][0]), predictions["predictions"][1]]}
    incomplete["predictions"][0].pop("residual_difference")
    try:
        validate_structured_semantic_predictions(incomplete, packet)
    except ValueError as exc:
        assert str(exc) == "MISSING_STRUCTURED_SEMANTIC_EVIDENCE"
    else:
        raise AssertionError("missing structured evidence was accepted")


def test_selective_metrics_exclude_abstentions_from_auto_accuracy_and_count_catastrophes():
    rows = [
        {"pair_id": "P1", "relation": "DUPLICATE"},
        {"pair_id": "P2", "relation": "VARIANT_OF_SAME_DECISION"},
        {"pair_id": "P3", "relation": "EQUIVALENT"},
        {"pair_id": "P4", "relation": "UNRELATED"},
    ]
    predictions = [
        {"pair_id": "P1", "predicted_relation": "DUPLICATE", "automation_decision": AUTO_ACCEPT},
        {"pair_id": "P2", "predicted_relation": "EQUIVALENT", "automation_decision": AUTO_ACCEPT},
        {"pair_id": "P3", "predicted_relation": "VARIANT_OF_SAME_DECISION", "automation_decision": NEEDS_SEMANTIC_ADJUDICATION},
        {"pair_id": "P4", "predicted_relation": "UNRELATED", "automation_decision": AUTO_ACCEPT},
    ]
    metrics = compute_selective_metrics(rows, predictions)

    assert metrics["auto_resolved"] == 3
    assert metrics["auto_coverage"] == 0.75
    assert metrics["auto_accuracy"] == 0.666667
    assert metrics["abstention_rate"] == 0.25
    assert metrics["catastrophic_errors"] == [
        {"pair_id": "P2", "actual": "VARIANT_OF_SAME_DECISION", "predicted": "EQUIVALENT"}
    ]


def test_grouped_development_folds_never_split_a_leakage_component():
    rows = [
        {"pair_id": "P1", "relation": "EQUIVALENT", "leakage_group": "G1"},
        {"pair_id": "P2", "relation": "VARIANT_OF_SAME_DECISION", "leakage_group": "G1"},
        {"pair_id": "P3", "relation": "RELATED_BUT_DISTINCT", "leakage_group": "G2"},
        {"pair_id": "P4", "relation": "UNRELATED", "leakage_group": "G3"},
    ]
    folds = build_grouped_development_folds(rows, fold_count=2)
    membership = {
        pair_id: fold["fold"]
        for fold in folds
        for pair_id in fold["pair_ids"]
    }

    assert set(membership) == {"P1", "P2", "P3", "P4"}
    assert membership["P1"] == membership["P2"]


def test_development_packet_combines_exposed_inputs_without_partition_or_gold_fields():
    first = {"content_sha256": "1" * 64, "atomic_opportunity_contract": {"definition": "one decision"}, "pairs": [
        {"pair_id": "P1", "opportunity_a": {"learner_decision": "A"}, "opportunity_b": {"learner_decision": "B"}}
    ]}
    second = {"content_sha256": "2" * 64, "atomic_opportunity_contract": {"definition": "one decision"}, "pairs": [
        {"pair_id": "P2", "opportunity_a": {"learner_decision": "C"}, "opportunity_b": {"learner_decision": "D"}}
    ]}
    packet = build_development_packet(first, second)

    assert [row["pair_id"] for row in packet["pairs"]] == ["P1", "P2"]
    assert packet["development_rows"] == 2
    assert packet["source_input_sha256s"] == ["1" * 64, "2" * 64]
    assert all("relation" not in row and "partition" not in row for row in packet["pairs"])


def test_selective_predictions_use_only_exact_projected_record_for_duplicate_auto_override():
    packet = {
        "content_sha256": "b" * 64,
        "pairs": [
            {"pair_id": "D", "opportunity_a": {"learner_decision": "same"}, "opportunity_b": {"learner_decision": "same"}},
            {"pair_id": "N", "opportunity_a": {"learner_decision": "left"}, "opportunity_b": {"learner_decision": "right"}},
        ],
    }
    semantic = {
        "matcher_id": "V5-SEMANTIC",
        "source_input_sha256": "b" * 64,
        "predictions": [
            {"pair_id": "D", **_analysis("EQUIVALENT")},
            {"pair_id": "N", **_analysis("NEAR_DUPLICATE", same_answer_scope="UNCERTAIN", residual_difference="UNRESOLVED", near_duplicate_signal="YES")},
        ],
    }
    result = build_selective_predictions(packet, semantic, matcher_id="V5-SELECTIVE")
    by_id = {row["pair_id"]: row for row in result["predictions"]}

    assert by_id["D"]["predicted_relation"] == "DUPLICATE"
    assert by_id["D"]["automation_decision"] == AUTO_ACCEPT
    assert by_id["D"]["decision_source"] == "DETERMINISTIC_EXACT_PROJECTED_RECORD_OVERRIDE"
    assert by_id["N"]["automation_decision"] == NEEDS_SEMANTIC_ADJUDICATION


def test_selective_predictions_abstain_when_frozen_v4_2_and_structured_v5_disagree():
    packet = {
        "content_sha256": "c" * 64,
        "pairs": [{"pair_id": "P", "opportunity_a": {"learner_decision": "left"}, "opportunity_b": {"learner_decision": "right"}}],
    }
    semantic = {
        "matcher_id": "V5-SEMANTIC",
        "source_input_sha256": "c" * 64,
        "predictions": [{"pair_id": "P", **_analysis("RELATED_BUT_DISTINCT", same_principal_decision="NO", same_answer_scope="NO", independently_scoreable_difference="YES")}],
    }
    corroborating = {
        "matcher_id": "V4.2-FROZEN",
        "source_input_sha256": "c" * 64,
        "predictions": [{"pair_id": "P", "relation": "UNRELATED", "justification": "No direct opportunity relationship."}],
    }
    result = build_selective_predictions(
        packet, semantic, matcher_id="V5-SELECTIVE", corroborating_predictions=corroborating
    )

    assert result["predictions"][0]["automation_decision"] == NEEDS_SEMANTIC_ADJUDICATION
    assert result["predictions"][0]["abstention_reasons"] == ["SEMANTIC_CLASSIFIER_DISAGREEMENT"]


def test_selective_predictions_block_auto_equivalence_when_identity_metadata_differs():
    packet = {
        "content_sha256": "d" * 64,
        "pairs": [{
            "pair_id": "P",
            "opportunity_a": {"learner_decision": "same", "opportunity_family": "PROFESSIONALISM"},
            "opportunity_b": {"learner_decision": "same", "opportunity_family": "ETHICAL_LEGAL_ACTION"},
        }],
    }
    semantic = {
        "matcher_id": "V5-SEMANTIC",
        "source_input_sha256": "d" * 64,
        "predictions": [{"pair_id": "P", **_analysis("EQUIVALENT", residual_difference="SYNONYMY_ONLY")}],
    }
    corroborating = {
        "matcher_id": "V4.2-FROZEN",
        "source_input_sha256": "d" * 64,
        "predictions": [{"pair_id": "P", "relation": "EQUIVALENT", "justification": "Same decision."}],
    }
    result = build_selective_predictions(
        packet, semantic, matcher_id="V5-SELECTIVE", corroborating_predictions=corroborating
    )

    assert result["predictions"][0]["automation_decision"] == NEEDS_SEMANTIC_ADJUDICATION
    assert result["predictions"][0]["abstention_reasons"] == ["EQUIVALENT_IDENTITY_METADATA_DELTA"]
