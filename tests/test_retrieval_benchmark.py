"""The frozen-G2 retrieval benchmark: pre-registration and metric integrity.

These tests exist to stop the two ways a benchmark quietly stops being one: a
reference set that drifts toward the results, and a pass rule that is relaxed
after the results are visible.
"""

import json
from pathlib import Path

import pytest

from qbank.retrieval_benchmark import (
    ARMS,
    HYBRID_BENCHMARK_PASS_RULE,
    METRIC_DEFINITIONS,
    RetrievalBenchmarkError,
    build_frozen_reference_set,
    evaluate_hybrid_pass_rule,
    load_scenarios,
    score_opportunity,
    summarize_arm,
)

ROOT = Path(__file__).resolve().parents[1]
FROZEN = ROOT / "research/qgen/safe_yield/retrieval_benchmark_reference.json"
REPORT = ROOT / "reports/qgen_clinical_retrieval_benchmark.json"


def test_the_reference_set_is_derived_from_frozen_records_not_authored():
    reference = build_frozen_reference_set(ROOT)
    assert reference["frozen_before_any_arm_ran"] is True
    assert "semantic_admissibility" in reference["derived_from"]
    assert reference["negative_control_totals"]["KNOWN_SECOND_KEY"] == 8
    assert reference["negative_control_totals"]["KNOWN_ANCHORLESS"] > 0


def test_the_committed_reference_set_still_reproduces_from_its_frozen_inputs():
    """If a frozen input changed, the benchmark is no longer the benchmark."""
    committed = json.loads(FROZEN.read_text())
    rebuilt = build_frozen_reference_set(ROOT)
    assert rebuilt["reference_admitted_competitors"] == \
        committed["reference_admitted_competitors"]
    assert rebuilt["negative_controls"] == committed["negative_controls"]


def test_the_pass_rule_was_frozen_before_evaluation_and_is_conjunctive():
    assert HYBRID_BENCHMARK_PASS_RULE["frozen_before_evaluation"] is True
    assert len(HYBRID_BENCHMARK_PASS_RULE["all_of"]) >= 6


def test_the_pass_rule_can_actually_fail():
    """A rule that cannot be lost is not a rule."""
    current = {
        "OPPORTUNITIES_WITH_3_VIABLE": 10, "SAME_DECISION_PRECISION_mean": 0.9,
        "GRANULARITY_PRECISION_mean": 1.0, "SECOND_KEY_REFUSAL_total": 8,
        "SOURCE_TRACEABILITY_mean": 1.0, "known_bad_returned_total": 0,
        "CONTEXT_SIZE_median_characters": 1700,
    }
    losing = evaluate_hybrid_pass_rule({"CURRENT_LIBRARY": current, "HYBRID": current})
    assert losing["HYBRID_BENCHMARK_PASS"] is False
    winning = evaluate_hybrid_pass_rule({
        "CURRENT_LIBRARY": current,
        "HYBRID": {**current, "OPPORTUNITIES_WITH_3_VIABLE": 14},
    })
    assert winning["HYBRID_BENCHMARK_PASS"] is True


def test_every_reported_metric_carries_a_written_definition():
    report = json.loads(REPORT.read_text())
    definitions = report["reference"]["metric_definitions"]
    assert definitions == METRIC_DEFINITIONS
    for name in (
        "CANDIDATE_RECALL", "SAME_DECISION_PRECISION", "STEM_ANCHOR_SURVIVAL",
        "SECOND_KEY_REFUSAL", "KNOWN_BAD_RETRIEVAL_RATE", "DISCOVERED_BUT_UNTYPED",
        "SOURCE_TRACEABILITY", "CONTEXT_SIZE",
    ):
        assert name in definitions


def test_the_population_is_the_thirty_frozen_opportunities():
    scenarios = load_scenarios(ROOT)
    assert len(scenarios) == 30
    for scenario in scenarios:
        assert scenario["stem_feature_map"]["features"]


def test_no_arm_returned_a_known_bad_control():
    report = json.loads(REPORT.read_text())
    for arm in ARMS:
        assert report["summary_by_arm"][arm]["known_bad_returned_total"] == 0, arm


def test_the_second_key_ceiling_is_unchanged_from_the_frozen_baseline():
    report = json.loads(REPORT.read_text())
    for arm in ("CURRENT_LIBRARY", "GRAPH", "HYBRID"):
        assert report["summary_by_arm"][arm]["SECOND_KEY_REFUSAL_total"] == 8, arm


def test_the_recall_miss_diagnosis_is_computed_not_asserted():
    report = json.loads(REPORT.read_text())
    diagnosis = report["recall_miss_diagnosis"]
    assert diagnosis["NOT_RETRIEVED_AT_ALL"] == 0
    assert sum(diagnosis["counts"].values()) == len(diagnosis["rows"])
    for row in diagnosis["rows"]:
        assert row["refused_by"] in {"SAF_1", "ADM_1", "ADM_3", "NOT_RETRIEVED_AT_ALL"}


def test_the_benchmark_records_zero_llm_calls():
    assert json.loads(REPORT.read_text())["llm_api_calls"] == 0


def test_a_missing_frozen_input_fails_closed(tmp_path):
    with pytest.raises(RetrievalBenchmarkError):
        load_scenarios(tmp_path)
