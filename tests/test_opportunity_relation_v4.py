from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.qbank.opportunity_relation_v4 import (
    RELATIONS,
    assemble_relation_gold_v2,
    analyze_relation_reviewer_agreement,
    assemble_relation_gold_v3_waves,
    build_relation_disagreement_packet,
    build_relation_gold_v3_disagreement_packet,
    build_failed_v3_baseline,
    build_gold_v2_failure_analysis,
    build_matcher_v4_contract,
    build_matcher_v4_calibrated_contract,
    build_matcher_prediction_packet,
    build_hybrid_relation_predictions,
    compute_multiclass_metrics,
    evaluate_matcher_gate,
    evaluate_relation_class_support,
    freeze_relation_gold_v3_partitions,
    finalize_relation_gold_v3,
    freeze_relation_partitions,
    build_relation_gold_v3_review_packet,
    compare_matcher_approaches,
    mine_relation_gold_v3_candidates,
    mine_relation_review_candidates,
    deterministic_relation_predictions,
    validate_matcher_predictions,
    score_matcher_predictions,
    validate_relation_gold_v3_review,
    validate_append_only_graph,
    write_final_gold_artifacts,
    write_task1_artifacts,
)


ROOT = Path(__file__).resolve().parents[1]


def test_failed_v3_baseline_is_reproduced_without_reinterpretation():
    receipt = build_failed_v3_baseline(ROOT)
    assert receipt["status"] == "MATCHER_V3_FAILED_GENERALIZATION_BASELINE"
    assert receipt["starting_head"] == "01eff40984bee76418c7fab82a1ded9fbfa2d9e5"
    assert receipt["heldout_pairs"] == 86
    assert receipt["correct"] == 2
    assert receipt["accuracy"] == 0.023256
    assert receipt["atomic_opportunity_contract_sha256"] == "c250e20c3da4e109c06c856c573e0e0006ab959ffd26faeccd2c55ebf3237e9a"
    assert receipt["matcher_v3_sha256"] == "1673a305ecef18b1d57cd9e151f5b0c1d0c81b0ae1b78673269c0b717fb9b5c3"
    assert sum(sum(row.values()) for row in receipt["confusion_matrix"].values()) == 86
    assert receipt["medical_question_accuracy"] is None


def test_gold_v2_failure_analysis_reports_representative_support_defect_without_mutation():
    gold_path = ROOT / "research/qgen/opportunity_relation_v4/relation_gold_v2.json"
    before = gold_path.read_bytes()
    analysis = build_gold_v2_failure_analysis(ROOT)
    assert analysis["scope"] == "RELATION_GOLD_V2_FAILURE_ANALYSIS"
    assert analysis["relation_gold_v2_sha256"] == "7bff03312c9023244054f8760d75f1e706c0d13526cd2a9f3e600d4ce4b49cc3"
    assert analysis["candidate_pairs_mined"] == 81
    assert analysis["reviewed_pairs"] == 81
    assert analysis["uncertain_rate"] == 0.432099
    assert analysis["relation_counts"] == {
        "EQUIVALENT": 4,
        "REGISTRY_BROADER_CONTAINS_BENCHMARK": 0,
        "REGISTRY_NARROWER_THAN_BENCHMARK": 0,
        "VARIANT_OF_SAME_DECISION": 0,
        "RELATED_BUT_DISTINCT": 42,
        "NEAR_DUPLICATE": 0,
        "DUPLICATE": 0,
        "UNRELATED": 0,
        "UNCERTAIN": 35,
    }
    assert analysis["absent_relation_classes"] == [
        "REGISTRY_BROADER_CONTAINS_BENCHMARK",
        "REGISTRY_NARROWER_THAN_BENCHMARK",
        "VARIANT_OF_SAME_DECISION",
        "NEAR_DUPLICATE",
        "DUPLICATE",
        "UNRELATED",
    ]
    assert analysis["discipline_counts"] == {
        "MED": 20, "OBGYN": 9, "PED": 6, "PHELO": 17, "PSY": 12, "SURG": 17,
    }
    assert analysis["family_counts"]["DIAGNOSIS"] == 13
    assert analysis["family_counts"]["SCREENING"] == 8
    assert analysis["structural_mining_strategy"] == "LABEL_GUIDED_REUSE_OF_SMALL_PRIOR_REVIEW_SAMPLES"
    assert analysis["failure_reason"] == "INSUFFICIENT_REPRESENTATIVE_CLASS_SUPPORT"
    assert gold_path.read_bytes() == before


def test_candidate_miner_uses_real_rows_and_blinds_prohibited_fields():
    packet = mine_relation_review_candidates(ROOT)
    assert packet["scope"] == "RELATION_GOLD_V2_BLINDED_REVIEW_INPUT"
    assert packet["atomic_contract_sha256"] == "c250e20c3da4e109c06c856c573e0e0006ab959ffd26faeccd2c55ebf3237e9a"
    assert set(packet["discipline_counts"]) == {"MED", "PED", "OBGYN", "SURG", "PSY", "PHELO"}
    assert len(packet["pairs"]) >= 48
    assert len({row["pair_id"] for row in packet["pairs"]}) == len(packet["pairs"])
    assert all(row["opportunity_a"] and row["opportunity_b"] for row in packet["pairs"])
    assert all(row["source_artifact_refs"] for row in packet["pairs"])
    serialized = json.dumps(packet).lower()
    for prohibited in ("matcher_prediction", "desired_class_balance", "historical_result"):
        assert prohibited not in serialized
    assert packet["candidate_selection_policy"] == "REAL_CANONICAL_ROWS_NO_SYNTHETIC_RELATION_EXAMPLES"


def test_gold_v3_wave1_miner_surfaces_real_structural_strata_without_semantic_labels():
    pool = mine_relation_gold_v3_candidates(ROOT, wave=1)
    assert pool["scope"] == "RELATION_GOLD_V3_WAVE_1_PRIVATE_CANDIDATE_POOL"
    assert 240 <= len(pool["pairs"]) <= 360
    assert set(pool["discipline_counts"]) == {"MED", "PED", "OBGYN", "SURG", "PSY", "PHELO"}
    assert len(pool["family_counts"]) >= 15
    assert len({row["pair_id"] for row in pool["pairs"]}) == len(pool["pairs"])
    assert len({row["unordered_semantic_signature"] for row in pool["pairs"]}) == len(pool["pairs"])
    assert all(row["source_provenance"] for row in pool["pairs"])
    assert all(row["structural_features"] for row in pool["pairs"])
    assert all(row["similarity_signals"] for row in pool["pairs"])
    assert not any("relation" in row or "label" in row for row in pool["pairs"])
    strata = {row["mining_stratum"] for row in pool["pairs"]}
    assert strata == {
        "POSSIBLE_EQUIVALENCE",
        "POSSIBLE_BROADER_NARROWER",
        "POSSIBLE_VARIANT",
        "POSSIBLE_RELATED_BUT_DISTINCT",
        "POSSIBLE_NEAR_DUPLICATE",
        "POSSIBLE_DUPLICATE",
        "HARD_UNRELATED",
    }
    for row in pool["pairs"]:
        assert row["opportunity_a"]
        assert row["opportunity_b"]
        if row["mining_stratum"] == "HARD_UNRELATED":
            assert row["opportunity_a"].get("discipline") == row["opportunity_b"].get("discipline")
            assert row["opportunity_a"].get("opportunity_family") == row["opportunity_b"].get("opportunity_family")


def test_gold_v3_review_packet_hides_mining_intent_and_freezes_contract():
    pool = mine_relation_gold_v3_candidates(ROOT, wave=1)
    packet = build_relation_gold_v3_review_packet(pool, ROOT)
    assert packet["scope"] == "RELATION_GOLD_V3_WAVE_1_BLINDED_REVIEW_INPUT"
    assert packet["source_candidate_pool_sha256"] == pool["content_sha256"]
    assert packet["atomic_opportunity_contract"]["content_sha256"] == (
        "c250e20c3da4e109c06c856c573e0e0006ab959ffd26faeccd2c55ebf3237e9a"
    )
    assert len(packet["pairs"]) == len(pool["pairs"])
    assert all(row["opportunity_a_role"] == "BENCHMARK_OR_REFERENCE" for row in packet["pairs"])
    assert all(row["opportunity_b_role"] == "REGISTRY_CANDIDATE" for row in packet["pairs"])
    serialized = json.dumps(packet).lower()
    for prohibited in (
        "mining_stratum", "structural_features", "similarity_signals", "desired_class",
        "support_target", "historical_label", "matcher_prediction", "quota",
    ):
        assert prohibited not in serialized
    assert not any(row.get("source_provenance") for row in packet["pairs"])


def _gold_v3_review_fixture():
    packet = {
        "wave": 1,
        "content_sha256": "a" * 64,
        "pairs": [
            {"pair_id": "V3-P1", "opportunity_a": {"discipline": "MED"}, "opportunity_b": {"discipline": "MED"}, "curriculum_context": {"discipline": "MED", "study_unit_id_a": "SU1", "study_unit_id_b": "SU1", "family_a": "DIAGNOSIS", "family_b": "DIAGNOSIS"}},
            {"pair_id": "V3-P2", "opportunity_a": {"discipline": "PED"}, "opportunity_b": {"discipline": "PED"}, "curriculum_context": {"discipline": "PED", "study_unit_id_a": "SU2", "study_unit_id_b": "SU2", "family_a": "MANAGEMENT", "family_b": "MANAGEMENT"}},
            {"pair_id": "V3-P3", "opportunity_a": {"discipline": "SURG"}, "opportunity_b": {"discipline": "SURG"}, "curriculum_context": {"discipline": "SURG", "study_unit_id_a": "SU3", "study_unit_id_b": "SU4", "family_a": "DIAGNOSIS", "family_b": "DIAGNOSIS"}},
        ],
    }
    primary = {
        "reviewer_id": "V3-R1", "source_input_sha256": "a" * 64,
        "reviews": [
            {"pair_id": "V3-P1", "relation": "EQUIVALENT", "justification": "The same atomic diagnostic decision is stated."},
            {"pair_id": "V3-P2", "relation": "VARIANT_OF_SAME_DECISION", "justification": "Only a non-decision-changing presentation differs."},
            {"pair_id": "V3-P3", "relation": "UNRELATED", "justification": "The decisions share a family but have no material relationship."},
        ],
    }
    secondary = {
        "reviewer_id": "V3-R2", "source_input_sha256": "a" * 64,
        "reviews": [
            {"pair_id": "V3-P1", "relation": "EQUIVALENT", "justification": "Both endpoints require the same response."},
            {"pair_id": "V3-P2", "relation": "RELATED_BUT_DISTINCT", "justification": "The contexts change the independently scoreable action."},
            {"pair_id": "V3-P3", "relation": "UNRELATED", "justification": "No clinically material relationship is supplied."},
        ],
    }
    return packet, primary, secondary


def test_gold_v3_review_validation_and_agreement_metrics_are_exact_and_classwise():
    packet, primary, secondary = _gold_v3_review_fixture()
    assert set(validate_relation_gold_v3_review(primary, packet)) == {"V3-P1", "V3-P2", "V3-P3"}
    analysis = analyze_relation_reviewer_agreement(packet, primary, secondary)
    assert analysis["reviewed_pairs"] == 3
    assert analysis["exact_agreement"] == 2
    assert analysis["disagreements"] == 1
    assert analysis["inter_reviewer_agreement"] == 0.666667
    assert analysis["confusion_matrix"]["VARIANT_OF_SAME_DECISION"] == {"RELATED_BUT_DISTINCT": 1}
    assert analysis["per_class_agreement"]["EQUIVALENT"]["agreement_rate"] == 1.0


def test_gold_v3_disagreement_packet_contains_peer_verdicts_only_for_disagreements():
    packet, primary, secondary = _gold_v3_review_fixture()
    disagreement = build_relation_gold_v3_disagreement_packet(packet, primary, secondary)
    assert disagreement["disagreement_count"] == 1
    assert [row["pair_id"] for row in disagreement["pairs"]] == ["V3-P2"]
    assert disagreement["pairs"][0]["primary_verdict"]["relation"] == "VARIANT_OF_SAME_DECISION"
    assert disagreement["pairs"][0]["secondary_verdict"]["relation"] == "RELATED_BUT_DISTINCT"
    assert "matcher" not in json.dumps(disagreement).lower()


def test_gold_v3_wave_assembly_requires_fresh_exact_disagreement_adjudication():
    packet, primary, secondary = _gold_v3_review_fixture()
    disagreement = build_relation_gold_v3_disagreement_packet(packet, primary, secondary)
    adjudication = {
        "reviewer_id": "V3-R3", "source_input_sha256": disagreement["content_sha256"],
        "reviews": [{"pair_id": "V3-P2", "relation": "VARIANT_OF_SAME_DECISION", "justification": "The response remains unchanged; the context is cosmetic."}],
    }
    gold = assemble_relation_gold_v3_waves([(packet, primary, secondary, adjudication)])
    assert gold["reviewed_pairs"] == 3
    assert gold["disagreement_count"] == 1
    assert gold["adjudication_count"] == 1
    assert gold["relation_counts"]["EQUIVALENT"] == 1
    assert gold["relation_counts"]["VARIANT_OF_SAME_DECISION"] == 1
    assert gold["relation_counts"]["UNRELATED"] == 1
    assert gold["uncertain_count"] == 0
    with pytest.raises(ValueError, match="ADJUDICATION_MUST_CONTAIN_ONLY_ALL_DISAGREEMENTS"):
        assemble_relation_gold_v3_waves([(packet, primary, secondary, {**adjudication, "reviews": []})])
    with pytest.raises(ValueError, match="NONINDEPENDENT_DISAGREEMENT_ADJUDICATOR"):
        assemble_relation_gold_v3_waves([(packet, primary, secondary, {**adjudication, "reviewer_id": "V3-R1"})])


def test_gold_v3_finalization_separates_uncertain_from_terminal_gold():
    packet, primary, secondary = _gold_v3_review_fixture()
    disagreement = build_relation_gold_v3_disagreement_packet(packet, primary, secondary)
    adjudication = {
        "reviewer_id": "V3-R3",
        "source_input_sha256": disagreement["content_sha256"],
        "reviews": [{"pair_id": "V3-P2", "relation": "UNCERTAIN", "justification": "The supplied context cannot resolve whether the response changes."}],
    }
    assembled = assemble_relation_gold_v3_waves([(packet, primary, secondary, adjudication)])
    terminal, uncertain = finalize_relation_gold_v3(assembled)
    assert terminal["scope"] == "RELATION_GOLD_V3"
    assert uncertain["scope"] == "RELATION_GOLD_V3_UNCERTAIN"
    assert terminal["reviewed_pairs"] == 2
    assert terminal["relation_counts"]["UNCERTAIN"] == 0
    assert uncertain["uncertain_count"] == 1
    assert [row["pair_id"] for row in uncertain["reviews"]] == ["V3-P2"]


def test_gold_v3_support_gate_uses_real_critical_class_floors_and_reports_exact_deficits():
    passing_counts = {
        "EQUIVALENT": 12,
        "REGISTRY_BROADER_CONTAINS_BENCHMARK": 12,
        "REGISTRY_NARROWER_THAN_BENCHMARK": 8,
        "VARIANT_OF_SAME_DECISION": 12,
        "RELATED_BUT_DISTINCT": 20,
        "NEAR_DUPLICATE": 0,
        "DUPLICATE": 0,
        "UNRELATED": 12,
        "UNCERTAIN": 5,
    }
    passed = evaluate_relation_class_support({"relation_counts": passing_counts})
    assert passed["gate"] == "PASS"
    assert passed["critical_class_deficits"] == {}
    failing_counts = {**passing_counts, "VARIANT_OF_SAME_DECISION": 9, "UNRELATED": 4}
    failed = evaluate_relation_class_support({"relation_counts": failing_counts})
    assert failed["gate"] == "FAIL"
    assert failed["critical_class_deficits"] == {"UNRELATED": 8, "VARIANT_OF_SAME_DECISION": 3}


def test_gold_v3_partition_is_disjoint_grouped_and_preserves_variant_heldout_support():
    relations = {
        "EQUIVALENT": 12,
        "REGISTRY_BROADER_CONTAINS_BENCHMARK": 16,
        "REGISTRY_NARROWER_THAN_BENCHMARK": 12,
        "VARIANT_OF_SAME_DECISION": 16,
        "RELATED_BUT_DISTINCT": 28,
        "UNRELATED": 16,
    }
    rows = []
    index = 0
    for relation, count in relations.items():
        for _ in range(count):
            rows.append({
                "pair_id": f"RG3-SYN-{index:03d}", "wave": 1, "relation": relation,
                "discipline": ("MED", "PED", "OBGYN", "SURG", "PSY", "PHELO")[index % 6],
                "family_a": f"F{index % 10}", "family_b": f"F{index % 10}",
                "study_unit_id_a": f"SU-{index:03d}", "study_unit_id_b": f"SU-{index:03d}",
            })
            index += 1
    frozen = freeze_relation_gold_v3_partitions({"content_sha256": "b" * 64, "reviews": rows})
    assert sum(frozen["partition_counts"].values()) == len(rows)
    assert set(frozen["partition_counts"]) == {"CALIBRATION", "VALIDATION", "FINAL_HELDOUT"}
    assert abs(frozen["partition_counts"]["CALIBRATION"] - 50) <= 3
    assert abs(frozen["partition_counts"]["VALIDATION"] - 25) <= 3
    assert abs(frozen["partition_counts"]["FINAL_HELDOUT"] - 25) <= 3
    assert len({row["pair_id"] for row in frozen["rows"]}) == len(rows)
    assert frozen["partition_relation_counts"]["FINAL_HELDOUT"]["VARIANT_OF_SAME_DECISION"] >= 4
    assert frozen["partition_relation_counts"]["FINAL_HELDOUT"]["EQUIVALENT"] >= 4
    assert frozen["heldout_support_gate"] == "PASS"
    assignment = {}
    for row in frozen["rows"]:
        assert assignment.setdefault(row["study_unit_id_a"], row["partition"]) == row["partition"]


def test_matcher_prediction_packet_contains_frozen_endpoints_without_gold_labels():
    partitions = json.loads((ROOT / "research/qgen/opportunity_relation_v4/relation_gold_v3_frozen_partitions.json").read_text())
    packets = [json.loads((ROOT / "research/qgen/opportunity_relation_v4/relation_gold_v3_wave_1_review_input.json").read_text())]
    calibration = build_matcher_prediction_packet(partitions, packets, "CALIBRATION")
    assert calibration["scope"] == "MATCHER_V4_CALIBRATION_PREDICTION_INPUT"
    assert len(calibration["pairs"]) == partitions["partition_counts"]["CALIBRATION"]
    assert len({row["pair_id"] for row in calibration["pairs"]}) == len(calibration["pairs"])
    assert all(set(row) == {"pair_id", "opportunity_a_role", "opportunity_b_role", "opportunity_a", "opportunity_b", "curriculum_context"} for row in calibration["pairs"])
    assert not any("relation" in row or "gold_label" in row or "justification" in row for row in calibration["pairs"])


def test_matcher_prediction_validator_requires_exact_frozen_packet_coverage():
    packet = {"content_sha256": "c" * 64, "pairs": [{"pair_id": "M1"}, {"pair_id": "M2"}]}
    predictions = {
        "matcher_id": "M-V4", "source_input_sha256": "c" * 64,
        "predictions": [
            {"pair_id": "M1", "relation": "EQUIVALENT", "justification": "same atomic decision"},
            {"pair_id": "M2", "relation": "UNRELATED", "justification": "no material relationship"},
        ],
    }
    assert set(validate_matcher_predictions(predictions, packet)) == {"M1", "M2"}
    with pytest.raises(ValueError, match="MATCHER_PREDICTIONS_MUST_COVER_EVERY_PAIR_EXACTLY_ONCE"):
        validate_matcher_predictions({**predictions, "predictions": predictions["predictions"][:1]}, packet)


def test_deterministic_relation_predictions_use_structural_evidence_without_gold_access():
    packet = {
        "content_sha256": "d" * 64,
        "pairs": [
            {"pair_id": "DUP", "opportunity_a": {"discipline": "MED", "study_unit_id": "SU1", "opportunity_family": "DIAGNOSIS", "response_class": "DIAGNOSIS", "clinical_stage": "ASSESSMENT", "learner_decision": "Diagnose asthma."}, "opportunity_b": {"discipline": "MED", "study_unit_id": "SU1", "opportunity_family": "DIAGNOSIS", "response_class": "DIAGNOSIS", "clinical_stage": "ASSESSMENT", "learner_decision": "Diagnose asthma."}},
            {"pair_id": "REL", "opportunity_a": {"discipline": "MED", "study_unit_id": "SU2", "opportunity_family": "DIAGNOSIS", "response_class": "DIAGNOSIS", "learner_decision": "Diagnose pneumonia."}, "opportunity_b": {"discipline": "MED", "study_unit_id": "SU2", "opportunity_family": "INITIAL_MANAGEMENT", "response_class": "ACTION", "learner_decision": "Treat pneumonia."}},
            {"pair_id": "UNR", "opportunity_a": {"discipline": "MED", "study_unit_id": "SU3", "opportunity_family": "DIAGNOSIS", "response_class": "DIAGNOSIS", "learner_decision": "Diagnose anemia."}, "opportunity_b": {"discipline": "MED", "study_unit_id": "SU4", "opportunity_family": "DIAGNOSIS", "response_class": "DIAGNOSIS", "learner_decision": "Diagnose glaucoma."}},
        ],
    }
    result = deterministic_relation_predictions(packet, matcher_id="DETERMINISTIC-CALIBRATION")
    by_id = {row["pair_id"]: row["relation"] for row in result["predictions"]}
    assert by_id == {"DUP": "DUPLICATE", "REL": "RELATED_BUT_DISTINCT", "UNR": "UNRELATED"}
    assert result["source_input_sha256"] == packet["content_sha256"]


def test_hybrid_predictions_use_deterministic_exact_duplicate_override_and_semantic_elsewhere():
    packet = {"content_sha256": "e" * 64, "allowed_relations": list(RELATIONS[:-1]), "pairs": [{"pair_id": "P1"}, {"pair_id": "P2"}]}
    deterministic = {
        "matcher_id": "D", "source_input_sha256": "e" * 64,
        "predictions": [
            {"pair_id": "P1", "relation": "DUPLICATE", "justification": "identical record"},
            {"pair_id": "P2", "relation": "UNRELATED", "justification": "low overlap"},
        ],
    }
    semantic = {
        "matcher_id": "S", "source_input_sha256": "e" * 64,
        "predictions": [
            {"pair_id": "P1", "relation": "EQUIVALENT", "justification": "same decision"},
            {"pair_id": "P2", "relation": "RELATED_BUT_DISTINCT", "justification": "related decisions"},
        ],
    }
    hybrid = build_hybrid_relation_predictions(packet, deterministic, semantic, matcher_id="H")
    assert {row["pair_id"]: row["relation"] for row in hybrid["predictions"]} == {
        "P1": "DUPLICATE", "P2": "RELATED_BUT_DISTINCT",
    }
    assert hybrid["architecture"] == "HYBRID"


def test_matcher_scoring_uses_only_named_partition_gold_and_classwise_metrics():
    partitions = {
        "content_sha256": "f" * 64,
        "rows": [
            {"pair_id": "P1", "partition": "CALIBRATION", "relation": "EQUIVALENT"},
            {"pair_id": "P2", "partition": "CALIBRATION", "relation": "UNRELATED"},
            {"pair_id": "P3", "partition": "FINAL_HELDOUT", "relation": "DUPLICATE"},
        ],
    }
    packet = {"content_sha256": "1" * 64, "pairs": [{"pair_id": "P1"}, {"pair_id": "P2"}]}
    predictions = {
        "matcher_id": "M", "source_input_sha256": "1" * 64,
        "predictions": [
            {"pair_id": "P1", "relation": "EQUIVALENT", "justification": "same"},
            {"pair_id": "P2", "relation": "RELATED_BUT_DISTINCT", "justification": "related"},
        ],
    }
    result = score_matcher_predictions(partitions, "CALIBRATION", packet, predictions)
    assert result["pairs"] == 2
    assert result["accuracy"] == 0.5
    assert result["confusion_matrix"]["UNRELATED"] == {"RELATED_BUT_DISTINCT": 1}
    assert result["partition"] == "CALIBRATION"


def test_matcher_approach_comparison_selects_best_calibration_macro_f1_without_id_rules():
    actual = list(RELATIONS[:-1]) * 2
    partitions = {
        "content_sha256": "2" * 64,
        "rows": [
            {"pair_id": f"P{i}", "partition": "CALIBRATION", "relation": relation}
            for i, relation in enumerate(actual)
        ],
    }
    packet = {
        "content_sha256": "3" * 64,
        "allowed_relations": list(RELATIONS[:-1]),
        "pairs": [{"pair_id": f"P{i}"} for i in range(len(actual))],
    }

    def predictions(matcher_id, architecture, labels):
        return {
            "matcher_id": matcher_id,
            "architecture": architecture,
            "source_input_sha256": "3" * 64,
            "predictions": [
                {"pair_id": f"P{i}", "relation": relation, "justification": "bounded classifier result"}
                for i, relation in enumerate(labels)
            ],
        }

    comparison = compare_matcher_approaches(
        partitions,
        packet,
        {
            "DETERMINISTIC": predictions("D", "DETERMINISTIC", ["UNRELATED"] * len(actual)),
            "SEMANTIC": predictions("S", "SEMANTIC", [*actual[:-1], "RELATED_BUT_DISTINCT"]),
            "HYBRID": predictions("H", "HYBRID", actual),
        },
    )
    assert comparison["selected_architecture"] == "HYBRID"
    assert comparison["approaches"]["HYBRID"]["macro_f1"] == 1.0
    assert comparison["id_specific_rules"] is False


def test_multiclass_metrics_reports_classwise_and_insufficient_support():
    actual = ["EQUIVALENT", "EQUIVALENT", "VARIANT_OF_SAME_DECISION", "UNRELATED"]
    predicted = ["EQUIVALENT", "RELATED_BUT_DISTINCT", "VARIANT_OF_SAME_DECISION", "UNRELATED"]
    result = compute_multiclass_metrics(actual, predicted, labels=RELATIONS[:-1], minimum_support=2)
    assert result["confusion_matrix"]["EQUIVALENT"] == {"EQUIVALENT": 1, "RELATED_BUT_DISTINCT": 1}
    assert result["per_class"]["EQUIVALENT"]["precision"] == 1.0
    assert result["per_class"]["EQUIVALENT"]["recall"] == 0.5
    assert result["per_class"]["EQUIVALENT"]["f1"] == pytest.approx(2 / 3, abs=1e-6)
    assert result["per_class"]["VARIANT_OF_SAME_DECISION"]["support_status"] == "INSUFFICIENT_CLASS_SUPPORT"
    assert result["macro_f1"] >= 0


def test_append_only_relation_graph_is_monotonic_many_to_many():
    prior = [
        {"opportunity_a_id": "A1", "opportunity_b_id": "B1", "relation": "EQUIVALENT"},
        {"opportunity_a_id": "A1", "opportunity_b_id": "B2", "relation": "RELATED_BUT_DISTINCT"},
    ]
    current = prior + [
        {"opportunity_a_id": "A1", "opportunity_b_id": "B3", "relation": "VARIANT_OF_SAME_DECISION"}
    ]
    assert validate_append_only_graph(prior, current) == []
    assert validate_append_only_graph(prior, current[1:]) == ["A1|B1|EQUIVALENT"]


def test_task1_writer_emits_only_new_v4_artifacts(tmp_path):
    outputs = write_task1_artifacts(ROOT, tmp_path)
    assert set(outputs) == {
        "matcher_v3_failed_generalization_baseline.json",
        "matcher_v4_contract.json",
        "relation_gold_v2_review_input.json",
    }
    for name, digest in outputs.items():
        artifact = json.loads((tmp_path / name).read_text())
        assert artifact["content_sha256"] == digest


def _review_fixture():
    packet = {
        "content_sha256": "1" * 64,
        "pairs": [
            {"pair_id": "P1", "curriculum_context": {"discipline": "MED", "study_unit_id": "SU1", "family_a": "DX"}},
            {"pair_id": "P2", "curriculum_context": {"discipline": "PED", "study_unit_id": "SU2", "family_a": "TX"}},
        ],
    }
    primary = {"reviewer_id": "R1", "source_input_sha256": "1" * 64, "reviews": [
        {"pair_id": "P1", "relation": "EQUIVALENT", "justification": "same decision"},
        {"pair_id": "P2", "relation": "RELATED_BUT_DISTINCT", "justification": "different decision"},
    ]}
    secondary = {"reviewer_id": "R2", "source_input_sha256": "1" * 64, "reviews": [
        {"pair_id": "P1", "relation": "EQUIVALENT", "justification": "same decision"},
        {"pair_id": "P2", "relation": "UNRELATED", "justification": "no relation"},
    ]}
    return packet, primary, secondary


def test_gold_assembly_routes_only_disagreements_and_fails_closed_when_unresolved():
    packet, primary, secondary = _review_fixture()
    result = assemble_relation_gold_v2(packet, primary, secondary, adjudication=None)
    by_id = {row["pair_id"]: row for row in result["reviews"]}
    assert by_id["P1"]["relation"] == "EQUIVALENT"
    assert by_id["P2"]["relation"] == "UNCERTAIN"
    assert result["agreement_count"] == 1
    assert result["disagreement_count"] == 1
    assert result["adjudication_count"] == 0
    adjudication = {"reviewer_id": "R3", "source_input_sha256": "1" * 64, "reviews": [
        {"pair_id": "P2", "relation": "RELATED_BUT_DISTINCT", "justification": "shared topic, separate decision"}
    ]}
    resolved = assemble_relation_gold_v2(packet, primary, secondary, adjudication)
    assert {row["pair_id"] for row in resolved["reviews"] if row["adjudicated"]} == {"P2"}


def test_disagreement_packet_contains_only_disputed_pairs_and_no_peer_rationales():
    packet, primary, secondary = _review_fixture()
    result = build_relation_disagreement_packet(packet, primary, secondary)
    assert [row["pair_id"] for row in result["pairs"]] == ["P2"]
    assert result["disagreement_count"] == 1
    serialized = json.dumps(result)
    assert "different decision" not in serialized
    assert "no relation" not in serialized
    assert result["source_input_sha256"] == packet["content_sha256"]


def test_relation_partition_freeze_prevents_study_unit_leakage():
    rows = []
    for index in range(18):
        rows.append({"pair_id": f"P{index}", "relation": RELATIONS[index % 6], "discipline": ("MED", "PED", "OBGYN", "SURG", "PSY", "PHELO")[index % 6], "family": f"F{index % 4}", "study_unit_id": f"SU{index}"})
    frozen = freeze_relation_partitions(rows)
    assert set(frozen["partition_counts"]) == {"CALIBRATION", "VALIDATION", "FINAL_HELDOUT"}
    seen = {}
    for row in frozen["rows"]:
        assert seen.setdefault(row["study_unit_id"], row["partition"]) == row["partition"]
    assert frozen["frozen_before_matcher_development"] is True


def test_final_gold_writer_persists_adjudicated_gold_and_frozen_split(tmp_path):
    packet, primary, secondary = _review_fixture()
    adjudication = {"reviewer_id": "R3", "source_input_sha256": "1" * 64, "reviews": [
        {"pair_id": "P2", "relation": "RELATED_BUT_DISTINCT", "justification": "shared topic, separate decision"}
    ]}
    for name, payload in (
        ("relation_gold_v2_review_input.json", packet),
        ("relation_gold_v2_primary_review.json", primary),
        ("relation_gold_v2_secondary_review.json", secondary),
        ("relation_gold_v2_disagreement_adjudication.json", adjudication),
    ):
        (tmp_path / name).write_text(json.dumps(payload))
    outputs = write_final_gold_artifacts(tmp_path)
    assert set(outputs) == {"relation_gold_v2.json", "relation_gold_v2_frozen_partitions.json"}
    gold = json.loads((tmp_path / "relation_gold_v2.json").read_text())
    assert gold["adjudication_count"] == 1
    assert json.loads((tmp_path / "relation_gold_v2_frozen_partitions.json").read_text())["frozen_before_matcher_development"] is True


def test_matcher_gate_uses_macro_and_critical_class_metrics():
    perfect = compute_multiclass_metrics(list(RELATIONS[:-1]) * 2, list(RELATIONS[:-1]) * 2, labels=RELATIONS[:-1])
    assert evaluate_matcher_gate(perfect)["gate"] == "PASS"
    weak = compute_multiclass_metrics(["EQUIVALENT", "EQUIVALENT"], ["UNRELATED", "UNRELATED"], labels=RELATIONS[:-1])
    assert evaluate_matcher_gate(weak)["gate"] == "FAIL"
    unrelated_unsupported = compute_multiclass_metrics(
        [label for label in RELATIONS[:-1] if label != "UNRELATED"] * 2,
        [label for label in RELATIONS[:-1] if label != "UNRELATED"] * 2,
        labels=RELATIONS[:-1],
    )
    result = evaluate_matcher_gate(unrelated_unsupported)
    assert result["gate"] == "FAIL"
    assert "UNRELATED" in result["insufficient_critical_class_support"]


def test_matcher_v4_contract_is_hybrid_frozen_and_contains_no_id_rules():
    contract = build_matcher_v4_contract(ROOT)
    assert contract["architecture"] == "HYBRID"
    assert contract["frozen"] is True
    assert contract["deterministic_stage"] == "RECALL_ORIENTED_CANDIDATE_PREFILTER_ONLY"
    assert contract["semantic_stage"] == "CONSTRAINED_ATOMIC_CONTRACT_RELATION_CLASSIFICATION"
    assert contract["id_specific_rules"] is False
    assert len(contract["classifier_prompt_sha256"]) == 64


def test_matcher_v4_calibrated_contract_preserves_semantics_and_pins_parent_lineage():
    contract = build_matcher_v4_calibrated_contract(ROOT)
    assert contract["schema_version"] == "4.1"
    assert contract["architecture"] == "HYBRID"
    assert contract["parent_matcher_v4_sha256"] == "41f48e744e51e910f621c448a33cc8d2666ac6b0e9810b18accd70bceec24335"
    assert contract["semantic_contract_changed"] is False
    assert contract["calibration_change"] == "PROMPT_PRECEDENCE_CLARIFICATION_ONLY"
    assert contract["id_specific_rules"] is False
    assert contract["frozen"] is True
    assert len(contract["classifier_prompt_sha256"]) == 64
