from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from qbank.curriculum_opportunity_registry_v2 import (
    RegistryV2Error,
    build_blind_benchmark_input,
    build_v1_comparison_contract,
    benchmark_opportunity_fingerprint,
    assess_registry_v1,
    build_blind_v1_audit_sample,
    build_benchmark_comparison_input,
    build_registry_v2,
    build_v2_benchmark_comparison_input,
    compute_benchmark_metrics,
    compute_blueprint_audit,
    enumerate_competency_v2,
    deduplicate_v2_candidates,
    summarize_duplicate_stress_test,
    summarize_v1_blind_audit,
    select_semantic_duplicate_pairs,
    select_benchmark_roster,
    validate_benchmark,
    validate_benchmark_comparison,
    validate_registry_v2,
    validate_duplicate_reviews,
    validate_v1_blind_audit_reviews,
    verify_safe_resume,
)


ROOT = Path(__file__).resolve().parents[1]


def test_safe_resume_verifies_canonical_v1_content_hashes_and_counts():
    report = verify_safe_resume(ROOT)

    assert report["STARTING_HEAD"] == "01eff40984bee76418c7fab82a1ded9fbfa2d9e5"
    assert report["CURRICULUM_SNAPSHOT_SHA256"] == "70c0875060e8aa5ae8563b70074fa365941b2eb7d4a2a32a2a6ed0fe776817a9"
    assert report["OPPORTUNITY_REGISTRY_V1_SHA256"] == "aa465f77c65ba21955e01c3ddf0f32de18022d6a76583bf1ed1da34e62a5e11e"
    assert report["QUESTION_BANK_ALLOCATION_PLAN_V1_SHA256"] == "73fbf8675c9221d98c5fe18edbce4edf7d45b5f451d61a6aeb6a511cd117c50b"
    assert report["PRODUCTION_QUEUE_V1_SHA256"] == "7d88f03a109e68a82864f591369081b3098671633dfeadf134c5f1221fca58f3"
    assert report["TOTAL_IN_SCOPE_STUDY_UNITS"] == 1165
    assert report["BASE_OPPORTUNITIES"] == 1541
    assert report["HISTORICAL_SAFETY"] == "PASS"
    assert report["COPYRIGHT"] == "PASS"


def test_safe_resume_fails_closed_when_artifact_declares_wrong_hash(tmp_path):
    source = ROOT / "research/qgen/opportunity_registry/curriculum_input_snapshot_v1.json"
    target = tmp_path / "research/qgen/opportunity_registry"
    target.mkdir(parents=True)
    text = source.read_text().replace(
        "70c0875060e8aa5ae8563b70074fa365941b2eb7d4a2a32a2a6ed0fe776817a9",
        "0" * 64,
        1,
    )
    (target / source.name).write_text(text)

    with pytest.raises(RegistryV2Error, match="CURRICULUM_SNAPSHOT_SHA256"):
        verify_safe_resume(tmp_path, checks=("CURRICULUM_SNAPSHOT_SHA256",))


def test_v1_comparison_contract_freezes_requested_distributions():
    contract = build_v1_comparison_contract(ROOT)

    assert contract["registry_v1_sha256"] == "aa465f77c65ba21955e01c3ddf0f32de18022d6a76583bf1ed1da34e62a5e11e"
    assert contract["study_unit_count"] == 1165
    assert contract["opportunity_count"] == 1541
    assert sum(contract["family_distribution"].values()) == 1541
    assert sum(contract["blueprint_distribution"]["dimensions_of_care"].values()) == 1541
    assert sum(contract["blueprint_distribution"]["physician_activities"].values()) == 1541
    assert contract["duplicate_metrics"] == {
        "exact_duplicates_collapsed": 0,
        "semantic_near_duplicates_collapsed": 0,
    }
    assert contract["mcq_suitability_metrics"] == {
        "MCQ_STRONG": 1541,
        "MCQ_ACCEPTABLE": 0,
        "MCQ_WEAK": 0,
        "NOT_SUITABLE_FOR_MC": 0,
    }
    assert len(contract["content_sha256"]) == 64


def test_benchmark_roster_is_balanced_stable_and_stratified_without_yield_targeting():
    first = select_benchmark_roster(ROOT, per_discipline=12)
    second = select_benchmark_roster(ROOT, per_discipline=12)

    assert first == second
    assert len(first) == 72
    assert len({row["study_unit_id"] for row in first}) == 72
    assert {discipline: sum(row["discipline"] == discipline for row in first) for discipline in ("MED", "PED", "OBGYN", "SURG", "PSY", "PHELO")} == {
        "MED": 12,
        "PED": 12,
        "OBGYN": 12,
        "SURG": 12,
        "PSY": 12,
        "PHELO": 12,
    }
    for discipline in ("MED", "PED", "OBGYN", "SURG", "PSY", "PHELO"):
        rows = [row for row in first if row["discipline"] == discipline]
        assert len({row["priority_stratum"] for row in rows}) >= 3
        available_density = {row["density_stratum"] for row in rows}
        assert len(available_density) >= 2
    assert all("desired" not in key.lower() and "yield" not in key.lower() for row in first for key in row)


def test_blind_benchmark_input_contains_curriculum_context_but_no_v1_opportunity_data():
    roster = select_benchmark_roster(ROOT, per_discipline=12)
    packet = build_blind_benchmark_input(ROOT, roster)

    assert packet["blindness_contract"] == "REGISTRY_V1_OPPORTUNITIES_WITHHELD"
    assert len(packet["study_units"]) == 72
    forbidden = {
        "v1_opportunity_count",
        "density_stratum",
        "opportunity_id",
        "opportunity_family",
        "learner_decision",
        "mcq_suitability",
        "recommended_item_capacity",
    }
    for row in packet["study_units"]:
        assert not forbidden.intersection(row)
        assert row["testable_competencies"]
        assert row["source_hierarchy_path"]
        assert "minimum_question_coverage" not in row
        assert "coverage_weight" not in row
    serialized = str(packet).lower()
    assert "1,000" not in serialized
    assert "desired opportunity" not in serialized


def benchmark_row(**overrides):
    row = {
        "benchmark_opportunity_id": "BOP-SU-A-03-01",
        "study_unit_id": "SU-A-03",
        "discipline": "MED",
        "principal_decision": "Select risk-directed preoperative investigations.",
        "decision_code": "select_preoperative_investigation",
        "opportunity_family": "BEST_NEXT_INVESTIGATION",
        "response_class": "INVESTIGATION",
        "clinical_stage": "PREVENTIVE_OR_PREPARATORY_CARE",
        "population_context": "GENERAL_ADULT",
        "primary_reasoning_target": "Use patient and procedure risk to choose testing.",
        "atomicity_verdict": "ATOMIC",
        "mccqe_level_review": "IN_SCOPE_GENERALIST",
        "source_anchor_refs": ["SU-A-03", "A.S01.T02", "MCC:74-3"],
        "reviewer_rationale": "A graduating physician must choose testing without a routine fixed panel.",
    }
    row.update(overrides)
    row["opportunity_fingerprint"] = benchmark_opportunity_fingerprint(row)
    return row


def test_benchmark_validation_accepts_atomic_generalist_decision_and_rejects_invalid_rows():
    artifact = {
        "schema_version": "1.0",
        "scope": "INDEPENDENT_OPPORTUNITY_BENCHMARK_V1",
        "blind_input_sha256": "5" * 64,
        "opportunities": [benchmark_row()],
    }
    artifact["content_sha256"] = "placeholder"
    validate_benchmark(artifact, roster_ids={"SU-A-03"}, verify_hash=False)

    with pytest.raises(RegistryV2Error, match="atomicity"):
        validate_benchmark(
            {**artifact, "opportunities": [benchmark_row(atomicity_verdict="COMPOUND")]},
            roster_ids={"SU-A-03"},
            verify_hash=False,
        )
    with pytest.raises(RegistryV2Error, match="MCCQE level"):
        validate_benchmark(
            {**artifact, "opportunities": [benchmark_row(mccqe_level_review="TOO_SPECIALIST")]},
            roster_ids={"SU-A-03"},
            verify_hash=False,
        )


def test_benchmark_validation_rejects_duplicate_fingerprints_and_non_roster_units():
    row = benchmark_row()
    artifact = {
        "schema_version": "1.0",
        "scope": "INDEPENDENT_OPPORTUNITY_BENCHMARK_V1",
        "blind_input_sha256": "5" * 64,
        "content_sha256": "placeholder",
        "opportunities": [row, {**row, "benchmark_opportunity_id": "BOP-SU-A-03-02"}],
    }
    with pytest.raises(RegistryV2Error, match="duplicate opportunity fingerprint"):
        validate_benchmark(artifact, roster_ids={"SU-A-03"}, verify_hash=False)
    with pytest.raises(RegistryV2Error, match="not in frozen roster"):
        validate_benchmark(
            {**artifact, "opportunities": [benchmark_row(study_unit_id="SU-X-99")]},
            roster_ids={"SU-A-03"},
            verify_hash=False,
        )


def test_benchmark_metrics_use_strict_recall_and_conservative_precision():
    benchmark = {
        "opportunities": [
            {"benchmark_opportunity_id": "B1", "discipline": "MED", "opportunity_family": "DIAGNOSIS", "study_unit_id": "SU-1"},
            {"benchmark_opportunity_id": "B2", "discipline": "MED", "opportunity_family": "FOLLOW_UP", "study_unit_id": "SU-1"},
            {"benchmark_opportunity_id": "B3", "discipline": "PED", "opportunity_family": "PREVENTION", "study_unit_id": "SU-2"},
            {"benchmark_opportunity_id": "B4", "discipline": "PED", "opportunity_family": "DIAGNOSIS", "study_unit_id": "SU-2"},
            {"benchmark_opportunity_id": "B5", "discipline": "PED", "opportunity_family": "DIAGNOSIS", "study_unit_id": "SU-2"},
        ]
    }
    registry = {
        "opportunities": [
            {"opportunity_id": "V1", "study_unit_id": "SU-1", "discipline": "MED", "importance": "CORE", "chapter_code": "C", "opportunity_family": "DIAGNOSIS"},
            {"opportunity_id": "V2", "study_unit_id": "SU-1", "discipline": "MED", "importance": "HIGH", "chapter_code": "C", "opportunity_family": "FOLLOW_UP"},
            {"opportunity_id": "V3", "study_unit_id": "SU-2", "discipline": "PED", "importance": "STANDARD", "chapter_code": "P", "opportunity_family": "PREVENTION"},
        ]
    }
    comparison = {
        "benchmark_reviews": [
            {"benchmark_opportunity_id": "B1", "classification": "EXACT_MATCH", "miss_taxonomy": None},
            {"benchmark_opportunity_id": "B2", "classification": "SEMANTIC_MATCH", "miss_taxonomy": None},
            {"benchmark_opportunity_id": "B3", "classification": "PARTIAL_MATCH", "miss_taxonomy": "MISSING_PREVENTION"},
            {"benchmark_opportunity_id": "B4", "classification": "MISSING_FROM_V1", "miss_taxonomy": "MISSING_DIAGNOSIS"},
            {"benchmark_opportunity_id": "B5", "classification": "INVALID_BENCHMARK_OPPORTUNITY", "miss_taxonomy": None},
        ],
        "v1_reviews": [
            {"opportunity_id": "V1", "classification": "SUPPORTED_BY_BENCHMARK", "overgeneration_taxonomy": None},
            {"opportunity_id": "V2", "classification": "OVERGENERATED", "overgeneration_taxonomy": "COMPOUND"},
            {"opportunity_id": "V3", "classification": "AMBIGUOUS", "overgeneration_taxonomy": None},
        ],
    }

    metrics = compute_benchmark_metrics(benchmark, registry, comparison)
    v2_metrics = compute_benchmark_metrics(
        benchmark,
        registry,
        {"benchmark_reviews": comparison["benchmark_reviews"], "v2_reviews": comparison["v1_reviews"]},
        registry_review_key="v2_reviews",
    )

    assert metrics["match_counts"] == {
        "EXACT_MATCH": 1,
        "SEMANTIC_MATCH": 1,
        "PARTIAL_MATCH": 1,
        "MISSING_FROM_V1": 1,
        "INVALID_BENCHMARK_OPPORTUNITY": 1,
    }
    assert metrics["opportunity_recall"] == 0.5
    assert metrics["opportunity_precision"] == pytest.approx(1 / 3)
    assert metrics["missed_opportunity_taxonomy"] == {"MISSING_DIAGNOSIS": 1, "MISSING_PREVENTION": 1}
    assert metrics["recall_by_discipline"]["MED"]["recall"] == 1.0
    assert metrics["recall_by_discipline"]["PED"]["recall"] == 0.0
    assert metrics["recall_by_priority"]["CORE"]["recall"] == 1.0
    assert metrics["recall_by_chapter"]["C"]["recall"] == 1.0
    assert metrics["precision_by_discipline"]["MED"]["precision"] == 0.5
    assert metrics["precision_by_family"]["DIAGNOSIS"]["precision"] == 1.0
    assert v2_metrics == metrics


def test_blind_v1_audit_sample_has_twenty_per_discipline_and_hides_current_labels():
    packet = build_blind_v1_audit_sample(ROOT, per_discipline=20)

    assert len(packet["opportunities"]) == 120
    for discipline in ("MED", "PED", "OBGYN", "SURG", "PSY", "PHELO"):
        assert sum(row["discipline"] == discipline for row in packet["opportunities"]) == 20
    forbidden = {
        "mcq_suitability",
        "MCC_dimension_of_care",
        "MCC_physician_activity",
        "opportunity_family",
        "review_status",
        "review_error_taxonomy",
    }
    assert all(not forbidden.intersection(row) for row in packet["opportunities"])


def test_semantic_duplicate_selector_returns_likely_unique_blinded_pairs():
    packet = select_semantic_duplicate_pairs(ROOT, minimum_pairs=150)

    assert len(packet["pairs"]) >= 150
    pair_ids = [row["pair_id"] for row in packet["pairs"]]
    assert len(pair_ids) == len(set(pair_ids))
    assert all(row["left"]["study_unit_id"] == row["right"]["study_unit_id"] for row in packet["pairs"])
    assert all("existing_verdict" not in row for row in packet["pairs"])


def test_blueprint_audit_reports_confusion_matrices_and_accuracy():
    registry = {
        "opportunities": [
            {"opportunity_id": "V1", "MCC_dimension_of_care": ["Acute"], "MCC_physician_activity": "Assessment/Diagnosis"},
            {"opportunity_id": "V2", "MCC_dimension_of_care": ["Acute"], "MCC_physician_activity": "Management"},
        ]
    }
    reviews = [
        {"opportunity_id": "V1", "dimension_of_care": "Acute", "physician_activity": "Assessment/Diagnosis"},
        {"opportunity_id": "V2", "dimension_of_care": "Chronic", "physician_activity": "Management"},
    ]

    result = compute_blueprint_audit(registry, reviews)

    assert result["dimension_accuracy"] == 0.5
    assert result["activity_accuracy"] == 1.0
    assert result["dimension_confusion_matrix"]["Acute"]["Chronic"] == 1
    assert result["activity_confusion_matrix"]["Management"]["Management"] == 1


def test_benchmark_comparison_input_unblinds_only_after_frozen_benchmark():
    benchmark = {
        "scope": "INDEPENDENT_OPPORTUNITY_BENCHMARK_V1",
        "content_sha256": "b" * 64,
        "opportunities": [benchmark_row(study_unit_id="SU-A-03")],
    }
    packet = build_benchmark_comparison_input(ROOT, benchmark)

    assert packet["benchmark_sha256"] == "b" * 64
    assert len(packet["benchmark_opportunities"]) == 1
    assert packet["v1_opportunities"]
    assert {row["study_unit_id"] for row in packet["v1_opportunities"]} == {"SU-A-03"}
    assert all("review_status" not in row and "mcq_suitability" not in row for row in packet["v1_opportunities"])


def test_benchmark_comparison_validation_requires_complete_one_to_one_verdict_coverage():
    benchmark_ids = {"B1", "B2"}
    v1_ids = {"V1"}
    valid = {
        "benchmark_reviews": [
            {"benchmark_opportunity_id": "B1", "classification": "EXACT_MATCH", "matched_v1_ids": ["V1"], "miss_taxonomy": None, "rationale": "Same atomic decision."},
            {"benchmark_opportunity_id": "B2", "classification": "MISSING_FROM_V1", "matched_v1_ids": [], "miss_taxonomy": "MISSING_FOLLOW_UP", "rationale": "No follow-up decision is represented."},
        ],
        "v1_reviews": [
            {"opportunity_id": "V1", "classification": "SUPPORTED_BY_BENCHMARK", "matched_benchmark_ids": ["B1"], "overgeneration_taxonomy": None, "rationale": "Supported independently."}
        ],
    }
    validate_benchmark_comparison(valid, benchmark_ids=benchmark_ids, v1_ids=v1_ids)
    v2_valid = {
        "benchmark_reviews": [
            {**row, "matched_v2_ids": row["matched_v1_ids"]}
            for row in valid["benchmark_reviews"]
        ],
        "v2_reviews": valid["v1_reviews"],
    }
    validate_benchmark_comparison(
        v2_valid,
        benchmark_ids=benchmark_ids,
        v1_ids=v1_ids,
        registry_review_key="v2_reviews",
        matched_registry_ids_key="matched_v2_ids",
    )

    with pytest.raises(RegistryV2Error, match="benchmark verdict coverage"):
        validate_benchmark_comparison(
            {**valid, "benchmark_reviews": valid["benchmark_reviews"][:1]},
            benchmark_ids=benchmark_ids,
            v1_ids=v1_ids,
        )
    with pytest.raises(RegistryV2Error, match="miss taxonomy"):
        validate_benchmark_comparison(
            {
                **valid,
                "benchmark_reviews": [valid["benchmark_reviews"][0], {**valid["benchmark_reviews"][1], "miss_taxonomy": None}],
            },
            benchmark_ids=benchmark_ids,
            v1_ids=v1_ids,
        )


def test_v1_blind_audit_validation_and_summary_count_each_verdict_once():
    sample_ids = {"V1", "V2"}
    reviews = [
        {"opportunity_id": "V1", "mcq_suitability": "MCQ_STRONG", "dimension_of_care": "Acute", "physician_activity": "Assessment/Diagnosis", "opportunity_family": "DIAGNOSIS", "rationale": "Clear clinical diagnostic decision."},
        {"opportunity_id": "V2", "mcq_suitability": "MCQ_ACCEPTABLE", "dimension_of_care": "Chronic", "physician_activity": "Management", "opportunity_family": "FOLLOW_UP", "rationale": "Assessable but context dependent."},
    ]
    registry = {
        "opportunities": [
            {"opportunity_id": "V1", "MCC_dimension_of_care": ["Acute"], "MCC_physician_activity": "Assessment/Diagnosis", "opportunity_family": "DIAGNOSIS"},
            {"opportunity_id": "V2", "MCC_dimension_of_care": ["Acute"], "MCC_physician_activity": "Management", "opportunity_family": "NEXT_MANAGEMENT_STEP"},
        ]
    }
    validate_v1_blind_audit_reviews(reviews, sample_ids=sample_ids)
    summary = summarize_v1_blind_audit(registry, reviews)

    assert summary["mcq_suitability"] == {
        "MCQ_STRONG": 1,
        "MCQ_ACCEPTABLE": 1,
        "MCQ_WEAK": 0,
        "NOT_SUITABLE_FOR_MC": 0,
    }
    assert summary["blueprint"]["dimension_accuracy"] == 0.5
    assert summary["family_accuracy"] == 0.5
    assert summary["family_confusion_matrix"]["NEXT_MANAGEMENT_STEP"]["FOLLOW_UP"] == 1

    with pytest.raises(RegistryV2Error, match="audit verdict coverage"):
        validate_v1_blind_audit_reviews(reviews[:1], sample_ids=sample_ids)


def test_duplicate_review_validation_and_summary_preserve_four_way_verdicts():
    pair_ids = {"P1", "P2", "P3", "P4"}
    reviews = [
        {"pair_id": "P1", "classification": "DISTINCT", "rationale": "Different decisions."},
        {"pair_id": "P2", "classification": "RELATED_BUT_DISTINCT", "rationale": "Same topic, different stage."},
        {"pair_id": "P3", "classification": "NEAR_DUPLICATE", "rationale": "Cosmetic distinction only."},
        {"pair_id": "P4", "classification": "DUPLICATE", "rationale": "Same decision and context."},
    ]
    validate_duplicate_reviews(reviews, pair_ids=pair_ids)
    assert summarize_duplicate_stress_test(reviews) == {
        "pairs_reviewed": 4,
        "distinct": 1,
        "related_but_distinct": 1,
        "near_duplicate": 1,
        "duplicate": 1,
    }
    with pytest.raises(RegistryV2Error, match="duplicate-review coverage"):
        validate_duplicate_reviews(reviews[:3], pair_ids=pair_ids)


def test_v1_assessment_reports_multiple_issues_without_treating_precision_as_recall():
    result = assess_registry_v1(
        benchmark_metrics={"opportunity_recall": 0.056296, "opportunity_precision": 1.0},
        audit_summary={
            "mcq_suitability": {"MCQ_STRONG": 51, "MCQ_ACCEPTABLE": 54, "MCQ_WEAK": 14, "NOT_SUITABLE_FOR_MC": 1},
            "blueprint": {"dimension_accuracy": 0.666667, "activity_accuracy": 0.6},
            "family_accuracy": 0.266667,
        },
        duplicate_summary={"pairs_reviewed": 150, "distinct": 62, "related_but_distinct": 79, "near_duplicate": 9, "duplicate": 0},
    )

    assert result["assessment"] == "MULTIPLE_ISSUES"
    assert result["major_underenumeration"] is True
    assert result["overgeneration"] is False
    assert result["classification_bias"] is True
    assert result["mcq_suitability_overclaim"] is True
    assert result["semantic_dedupe_gap"] is True


def test_v2_enumeration_splits_distinct_response_class_decisions():
    rows = enumerate_competency_v2(
        "diagnosis_management_followup",
        "Diagnose chronic kidney disease; initiate first-line management and arrange follow-up monitoring.",
    )

    assert [row["opportunity_family"] for row in rows] == [
        "DIAGNOSIS",
        "INITIAL_MANAGEMENT",
        "FOLLOW_UP",
    ]
    assert all(row["atomicity_verdict"] == "ATOMIC" for row in rows)


def test_v2_enumeration_recovers_investigation_list_without_splitting_examples():
    investigations = enumerate_competency_v2(
        "investigation",
        "Select initial investigations (ECG, troponin, chest radiography) appropriate to clinical probability.",
    )
    examples = enumerate_competency_v2(
        "recognition",
        "Recognize pneumonia from typical features (e.g., fever, cough, focal crackles).",
    )

    assert len(investigations) == 3
    assert {row["clinical_object"].lower() for row in investigations} == {"ecg", "troponin", "chest radiography"}
    assert {row["opportunity_family"] for row in investigations} == {"BEST_NEXT_INVESTIGATION"}
    assert len(examples) == 1
    assert examples[0]["opportunity_family"] == "DIAGNOSIS"


def test_v2_enumeration_recovers_complication_and_communication_legal_families():
    complications = enumerate_competency_v2(
        "complications_and_counselling",
        "Recognize complications (bleeding, infection) and counsel the patient about warning signs.",
    )
    legal = enumerate_competency_v2(
        "legal_professional_action",
        "Assess decision-making capacity, obtain valid consent, and maintain confidentiality.",
    )

    assert [row["opportunity_family"] for row in complications] == [
        "COMPLICATION_RECOGNITION",
        "COMPLICATION_RECOGNITION",
        "COUNSELLING",
    ]
    assert {row["opportunity_family"] for row in legal} == {
        "CAPACITY_CONSENT",
        "CONFIDENTIALITY",
    }


def test_v2_specific_decision_noun_outweighs_generic_recognition_verb():
    rows = enumerate_competency_v2(
        "recognition",
        "Recognize screening eligibility; recognize when follow-up is required; recognize how to interpret an abnormal test result.",
    )

    assert [row["opportunity_family"] for row in rows] == [
        "SCREENING",
        "FOLLOW_UP",
        "INTERPRET_TEST_RESULT",
    ]


def test_v2_enumeration_excludes_vague_or_specialist_non_decisions():
    assert enumerate_competency_v2("reference", "Know terminology and chapter acronyms.") == []
    assert enumerate_competency_v2("technique", "Memorize rare subspecialty operative technique minutiae.") == []


def test_v2_enumeration_rules_are_not_parameterized_by_benchmark_unit_id():
    first = enumerate_competency_v2("followup", "Arrange follow-up after an abnormal result.", study_unit_id="SU-TEST-01")
    second = enumerate_competency_v2("followup", "Arrange follow-up after an abnormal result.", study_unit_id="SU-OTHER-99")

    assert [{k: v for k, v in row.items() if k != "study_unit_id"} for row in first] == [
        {k: v for k, v in row.items() if k != "study_unit_id"} for row in second
    ]
    assert first[0]["opportunity_family"] == "FOLLOW_UP"


def test_v2_semantic_dedupe_collapses_synonym_only_generic_decisions_and_preserves_provenance():
    base = {
        "study_unit_id": "SU-X-01",
        "response_class": "DIAGNOSIS",
        "clinical_stage": "INITIAL_PRESENTATION",
        "population_context": "NA",
        "severity_context": "NA",
        "clinical_object": "Example condition",
        "source_competency_key": "recognition",
        "source_v1_opportunity_ids": ["V1"],
        "aliases": ["recognition"],
    }
    rows = [
        {**base, "opportunity_id": "A", "opportunity_family": "DIAGNOSIS", "action_lemma": "recognize", "opportunity_fingerprint": "a" * 64},
        {**base, "opportunity_id": "B", "opportunity_family": "DIAGNOSIS", "action_lemma": "diagnose", "opportunity_fingerprint": "b" * 64, "source_v1_opportunity_ids": ["V2"], "aliases": ["diagnosis"]},
    ]

    deduped, exact_count, semantic_count = deduplicate_v2_candidates(rows)

    assert exact_count == 0
    assert semantic_count == 1
    assert len(deduped) == 1
    assert deduped[0]["source_v1_opportunity_ids"] == ["V1", "V2"]
    assert deduped[0]["aliases"] == ["diagnosis", "recognition"]


def test_full_registry_v2_is_stable_additive_grounded_and_conservative():
    first = build_registry_v2(ROOT)
    second = build_registry_v2(ROOT)

    assert first == second
    rows = first["opportunities"]
    assert len(rows) > 1541
    assert len({row["opportunity_id"] for row in rows}) == len(rows)
    assert len({row["opportunity_fingerprint"] for row in rows}) == len(rows)
    assert {row["provenance_type"] for row in rows}.issubset({
        "V1_PRESERVED",
        "V2_NEW_FAMILY",
        "V2_STAGE_EXPANSION",
        "V2_POPULATION_EXPANSION",
        "V2_OTHER",
    })
    assert all(row["source_competency_text"] for row in rows)
    assert all(row["recommended_item_capacity"] == 0 for row in rows if row["mcq_suitability"] in {"MCQ_WEAK", "NOT_SUITABLE_FOR_MC"})
    v1 = __import__("json").loads((ROOT / "research/qgen/opportunity_registry/curriculum_question_opportunity_registry_v1.json").read_text())
    preserved_ids = {source_id for row in rows for source_id in row["source_v1_opportunity_ids"]}
    assert preserved_ids == {row["opportunity_id"] for row in v1["opportunities"]}
    by_unit = {}
    for row in rows:
        by_unit.setdefault(row["study_unit_id"], []).append(row)
    assert {row["opportunity_family"] for row in by_unit["SU-C-03"]} >= {
        "DIFFERENTIAL_DIAGNOSIS",
        "RED_FLAG_RECOGNITION",
        "BEST_NEXT_INVESTIGATION",
        "EMERGENCY_STABILIZATION",
    }
    validate_registry_v2(first)
    schema = __import__("json").loads((ROOT / "schemas/curriculum-question-opportunity-v2.schema.json").read_text())
    Draft202012Validator(schema).validate(first)


def test_final_revision_preserves_v1_decisions_and_fails_closed_without_semantic_approval():
    from qbank.curriculum_opportunity_registry_v2 import (
        build_registry_v2_final_review_input,
        build_registry_v2_from_final_review,
    )

    review_input = build_registry_v2_final_review_input(ROOT)
    v1 = __import__("json").loads(
        (ROOT / "research/qgen/opportunity_registry/curriculum_question_opportunity_registry_v1.json").read_text()
    )
    preserved = [row for row in review_input["candidates"] if row["candidate_kind"] == "V1_PRESERVED"]
    proposed = [row for row in review_input["candidates"] if row["candidate_kind"] == "V2_PROPOSAL"]

    assert len(preserved) == len(v1["opportunities"])
    assert proposed
    assert {row["source_v1_opportunity_id"] for row in preserved} == {
        row["opportunity_id"] for row in v1["opportunities"]
    }
    assert all("benchmark" not in key.lower() for key in review_input)

    review = {
        "input_sha256": review_input["content_sha256"],
        "decisions": [
            {
                "candidate_id": row["candidate_id"],
                "verdict": "PRESERVE" if row["candidate_kind"] == "V1_PRESERVED" else "REJECT",
                "opportunity_family": row["proposed_opportunity_family"],
                "response_class": row["proposed_response_class"],
                "clinical_stage": row["proposed_clinical_stage"],
                "MCC_dimension_of_care": row["proposed_MCC_dimension_of_care"],
                "MCC_physician_activity": row["proposed_MCC_physician_activity"],
                "mcq_suitability": "MCQ_ACCEPTABLE",
                "rationale_codes": ["ATOMIC_AND_IN_SCOPE"],
            }
            for row in review_input["candidates"]
        ],
    }
    final = build_registry_v2_from_final_review(ROOT, review_input, review)

    assert len(final["opportunities"]) == len(v1["opportunities"])
    by_source = {row["source_v1_opportunity_ids"][0]: row for row in final["opportunities"]}
    for row in v1["opportunities"]:
        assert by_source[row["opportunity_id"]]["learner_decision"] == row["learner_decision"]
        assert by_source[row["opportunity_id"]]["key_concept_or_action"] == row["key_concept_or_action"]
    schema = __import__("json").loads(
        (ROOT / "schemas/curriculum-question-opportunity-v2.schema.json").read_text()
    )
    Draft202012Validator(schema).validate(final)


def test_final_review_validation_requires_complete_unique_general_decisions():
    from qbank.curriculum_opportunity_registry_v2 import (
        RegistryV2Error,
        validate_registry_v2_final_review,
    )

    review_input = {
        "content_sha256": "a" * 64,
        "candidates": [
            {"candidate_id": "A", "candidate_kind": "V1_PRESERVED"},
            {"candidate_id": "B", "candidate_kind": "V2_PROPOSAL"},
        ],
    }
    incomplete = {"input_sha256": "a" * 64, "decisions": []}
    with pytest.raises(RegistryV2Error, match="exactly once"):
        validate_registry_v2_final_review(review_input, incomplete)

    duplicate = {
        "input_sha256": "a" * 64,
        "decisions": [
            {"candidate_id": "A", "verdict": "PRESERVE"},
            {"candidate_id": "A", "verdict": "PRESERVE"},
        ],
    }
    with pytest.raises(RegistryV2Error, match="exactly once"):
        validate_registry_v2_final_review(review_input, duplicate)


def test_v2_operational_artifacts_allocate_coverage_before_variants_without_quotas():
    from qbank.curriculum_opportunity_registry_v2 import build_v2_operational_artifacts

    def row(identifier, discipline, suitability, capacity, importance="CORE"):
        return {
            "opportunity_id": identifier,
            "opportunity_fingerprint": identifier.lower() * 64,
            "discipline": discipline,
            "study_unit_id": f"SU-{identifier}",
            "chapter_code": "X",
            "importance": importance,
            "mcq_suitability": suitability,
            "review_status": "APPROVED" if suitability in {"MCQ_STRONG", "MCQ_ACCEPTABLE"} else "REVISE",
            "recommended_item_capacity": capacity,
            "generation_readiness": "READY_ON_DEMAND_EXPANSION",
            "supported_difficulty_levels": ["EASY", "MEDIUM", "HARD"],
            "MCC_dimension_of_care": ["Acute"],
            "MCC_physician_activity": "Management",
            "opportunity_family": "INITIAL_MANAGEMENT",
        }

    registry = {
        "content_sha256": "f" * 64,
        "opportunities": [
            row("A", "MED", "MCQ_STRONG", 3),
            row("B", "MED", "MCQ_ACCEPTABLE", 2),
            row("C", "PED", "MCQ_WEAK", 0),
        ],
    }
    artifacts = build_v2_operational_artifacts(registry)

    assert artifacts["bank_capacity"] == {
        "conservative_floor": 1,
        "recommended_target": 4,
        "upper_defensible_capacity": 5,
    }
    assert [entry["opportunity_id"] for entry in artifacts["queue"]["entries"][:2]] == ["A", "B"]
    assert [entry["slot_number"] for entry in artifacts["queue"]["entries"]] == [1, 1, 2, 3]
    assert artifacts["allocation"]["content_sha256"]
    assert artifacts["queue"]["content_sha256"]


def test_v2_benchmark_input_uses_frozen_benchmark_and_hides_v2_review_labels():
    benchmark = {
        "scope": "INDEPENDENT_OPPORTUNITY_BENCHMARK_V1",
        "content_sha256": "b" * 64,
        "opportunities": [benchmark_row(study_unit_id="SU-A-03")],
    }
    registry = build_registry_v2(ROOT)
    packet = build_v2_benchmark_comparison_input(benchmark, registry)

    assert packet["benchmark_sha256"] == "b" * 64
    assert packet["registry_v2_sha256"] == registry["content_sha256"]
    assert packet["v2_opportunities"]
    assert {row["study_unit_id"] for row in packet["v2_opportunities"]} == {"SU-A-03"}
    assert all("review_status" not in row and "mcq_suitability" not in row for row in packet["v2_opportunities"])
