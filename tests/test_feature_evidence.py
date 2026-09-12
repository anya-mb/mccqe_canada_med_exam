import copy
import json
from pathlib import Path

import pytest

from scripts.qbank.feature_evidence import (
    APPROVED_FEATURE_ROLES,
    admit_candidate_to_bundle,
    build_evidence_cohort,
    build_reuse_metrics,
    canonical_content_hash,
    classify_bundle_density,
    generation_gate,
    validate_development_question_set,
    validate_evidence_cohort,
    validate_evidence_fact,
    validate_matrix_cell,
    validate_question_evidence_trace,
)


ROOT = Path(__file__).resolve().parents[1]


def load(relative):
    return json.loads((ROOT / relative).read_text())


def test_cohort_contains_exactly_the_60_approved_reference_candidates():
    cohort = build_evidence_cohort(
        load("research/qgen/contrast_supply/anchor_reference_candidate_set_v1.json"),
        load("research/qgen/contrast_supply/anchor_reference_candidate_review_v1.json"),
        load("research/qgen/contrast_supply/clean_transfer_18_prerequisites_v1.json"),
    )
    assert len(cohort["candidates"]) == 60
    assert {row["reference_verdict"] for row in cohort["candidates"]} == {"APPROVED_REFERENCE"}
    assert len({row["reference_candidate_id"] for row in cohort["candidates"]}) == 60
    assert all(row["decision_signature_v2"] for row in cohort["candidates"])
    assert validate_evidence_cohort(cohort) == []


def test_cohort_rejects_duplicate_candidate_and_bad_hash():
    cohort = build_evidence_cohort(
        load("research/qgen/contrast_supply/anchor_reference_candidate_set_v1.json"),
        load("research/qgen/contrast_supply/anchor_reference_candidate_review_v1.json"),
        load("research/qgen/contrast_supply/clean_transfer_18_prerequisites_v1.json"),
    )
    duplicate = copy.deepcopy(cohort)
    duplicate["candidates"].append(copy.deepcopy(duplicate["candidates"][0]))
    assert "DUPLICATE_REFERENCE_CANDIDATE_ID" in validate_evidence_cohort(duplicate)
    changed = copy.deepcopy(cohort)
    changed["candidates"][0]["canonical_concept_name"] = "changed"
    assert "CONTENT_SHA256_MISMATCH" in validate_evidence_cohort(changed)


def test_evidence_fact_requires_entailment_source_and_canonical_hash():
    fact = {
        "evidence_fact_id": "FEV1-TEST-001",
        "canonical_subject_id": "CONCEPT-1",
        "canonical_subject_name": "Example diagnosis",
        "normalized_clinical_proposition": "Example diagnosis can cause a pruritic eruption.",
        "feature_roles": ["CANDIDATE_SUPPORTING", "STEM_ELIGIBLE"],
        "response_class_relevance": ["DIAGNOSIS"],
        "population_context": ["ADULT_GENERAL"],
        "clinical_stage": ["INITIAL_RECOGNITION"],
        "target_subdomain": ["DERMATOLOGY"],
        "source_refs": ["SRC-1"],
        "source_authority": "SPECIALTY_SOCIETY",
        "source_date_or_version": "2025",
        "entailment_review_status": "ENTAILED",
        "reuse_scope": {"kind": "CANONICAL_CONCEPT", "anchor_ids": ["A-1"], "candidate_context_ids": ["C-1"]},
    }
    fact["content_sha256"] = canonical_content_hash(fact)
    assert validate_evidence_fact(fact) == []
    bad = copy.deepcopy(fact)
    bad["source_refs"] = []
    assert "MISSING_SOURCE_REF" in validate_evidence_fact(bad)
    bad = copy.deepcopy(fact)
    bad["feature_roles"] = ["MADE_UP_ROLE"]
    assert "UNKNOWN_FEATURE_ROLE" in validate_evidence_fact(bad)
    assert "WHAT_MAKES_CANDIDATE_CORRECT" in APPROVED_FEATURE_ROLES


def test_non_entailed_fact_cannot_be_load_bearing():
    fact = {
        "evidence_fact_id": "FEV1-TEST-002",
        "canonical_subject_id": "CONCEPT-2",
        "canonical_subject_name": "Example",
        "normalized_clinical_proposition": "A tentative statement.",
        "feature_roles": ["PAIRWISE_DISCRIMINATOR"],
        "response_class_relevance": ["DIAGNOSIS"],
        "population_context": ["GENERAL"],
        "clinical_stage": ["INITIAL_RECOGNITION"],
        "target_subdomain": ["GENERAL"],
        "source_refs": ["SRC-2"],
        "source_authority": "GUIDELINE",
        "source_date_or_version": "2024",
        "entailment_review_status": "PARTIALLY_ENTAILED",
        "reuse_scope": {"kind": "PAIRWISE_CONTEXT", "anchor_ids": ["A-1"], "candidate_context_ids": ["C-2"]},
    }
    fact["content_sha256"] = canonical_content_hash(fact)
    assert "NON_ENTAILED_LOAD_BEARING_FACT" in validate_evidence_fact(fact)


def test_content_hash_is_order_stable_and_excludes_its_own_field():
    left = {"b": 2, "a": 1}
    right = {"a": 1, "b": 2, "content_sha256": "ignored"}
    assert canonical_content_hash(left) == canonical_content_hash(right)


def test_bundle_admission_requires_entailed_plausibility_and_discriminator():
    registry = {
        "P": {"entailment_review_status": "ENTAILED", "feature_roles": ["SHARED_PLAUSIBILITY"]},
        "D": {"entailment_review_status": "ENTAILED", "feature_roles": ["PAIRWISE_DISCRIMINATOR"]},
        "U": {"entailment_review_status": "UNCERTAIN", "feature_roles": ["PAIRWISE_DISCRIMINATOR"]},
    }
    assert admit_candidate_to_bundle({"evidence_fact_ids": ["P", "D"]}, registry) == "ADMITTED"
    assert admit_candidate_to_bundle({"evidence_fact_ids": ["P"]}, registry) == "MISSING_DISCRIMINATOR"
    assert admit_candidate_to_bundle({"evidence_fact_ids": ["P", "U"]}, registry) == "MISSING_DISCRIMINATOR"


def test_matrix_non_unknown_cell_requires_entailed_trace_and_never_infers_absence():
    registry = {"F": {"entailment_review_status": "ENTAILED"}}
    assert validate_matrix_cell({"state": "PRESENT", "evidence_fact_ids": ["F"]}, registry) == []
    assert validate_matrix_cell({"state": "UNKNOWN", "evidence_fact_ids": []}, registry) == []
    assert validate_matrix_cell({"state": "ABSENT", "evidence_fact_ids": []}, registry) == ["UNTRACED_NON_UNKNOWN_CELL"]


@pytest.mark.parametrize(
    ("count", "expected"),
    [(4, "STRONG_BUNDLE"), (3, "MINIMUM_GENERATABLE"), (2, "PARTIAL"), (1, "PARTIAL"), (0, "NO_SAFE")],
)
def test_bundle_density_contract(count, expected):
    assert classify_bundle_density(count) == expected


def test_reuse_metrics_count_unique_facts_not_copied_appearances():
    facts = [
        {"evidence_fact_id": "F1", "reuse_scope": {"anchor_ids": ["A1", "A2"], "candidate_context_ids": ["C1", "C2"]}, "feature_roles": ["CANDIDATE_SUPPORTING"]},
        {"evidence_fact_id": "F2", "reuse_scope": {"anchor_ids": ["A1"], "candidate_context_ids": ["C3"]}, "feature_roles": ["PAIRWISE_DISCRIMINATOR"]},
    ]
    assert build_reuse_metrics(facts) == {
        "facts_reused_across_anchors": 1,
        "facts_reused_across_candidates": 1,
        "pairwise_evidence_reuse": 0,
    }


def test_generation_gate_requires_six_anchors_and_enforces_item_caps():
    assert generation_gate([3, 3, 3, 3, 3, 2]) is False
    assert generation_gate([3, 3, 3, 3, 3, 3]) is True


def test_milestone_build_reconciles_candidate_fact_and_bundle_counts():
    from scripts.qbank.run_candidate_feature_evidence_v1 import build_milestone

    result = build_milestone(ROOT, write_outputs=False)
    assert len(result["cohort"]["candidates"]) == 60
    assert len(result["registry"]["facts"]) == 180
    assert all(not validate_evidence_fact(row) for row in result["registry"]["facts"])
    assert len(result["profiles"]["profiles"]) == 60
    assert sum(row["approved_alternatives"] for row in result["bundles"]["bundles"]) == 60
    assert len(result["bundles"]["bundles"]) == 18
    assert result["report"]["reference_candidates"] == 60
    assert result["report"]["new_test_failures"] == 0


def test_reuse_baseline_excludes_this_milestones_own_generated_outputs():
    from scripts.qbank.run_candidate_feature_evidence_v1 import build_milestone

    result = build_milestone(ROOT, write_outputs=False)
    assert result["reuse_baseline"]["counts"] == {
        "PARTIAL_EVIDENCE": 33,
        "NO_EVIDENCE": 147,
        "EXACT_EVIDENCE_REUSE": 0,
        "SEMANTIC_EVIDENCE_REUSE": 0,
        "CONFLICTING_EVIDENCE": 0,
        "OUTDATED_EVIDENCE": 0,
        "AMBIGUOUS": 0,
    }


def test_milestone_never_admits_rejected_or_uncertain_reference_candidates():
    from scripts.qbank.run_candidate_feature_evidence_v1 import build_milestone

    result = build_milestone(ROOT, write_outputs=False)
    admitted = {row["reference_candidate_id"] for row in result["profiles"]["profiles"]}
    review = load("research/qgen/contrast_supply/anchor_reference_candidate_review_v1.json")
    excluded = {row["reference_candidate_id"] for row in review["rows"] if row["verdict"] != "APPROVED_REFERENCE"}
    assert admitted.isdisjoint(excluded)


def test_key_discriminators_are_conditional_not_automatically_stem_eligible():
    from scripts.qbank.run_candidate_feature_evidence_v1 import build_milestone

    result = build_milestone(ROOT, write_outputs=False)
    discriminators = [row for row in result["registry"]["facts"] if "PAIRWISE_DISCRIMINATOR" in row["feature_roles"]]
    assert len(discriminators) == 60
    assert all("CONDITIONAL" in row["feature_roles"] for row in discriminators)
    assert all("STEM_ELIGIBLE" not in row["feature_roles"] for row in discriminators)


def test_question_trace_rejects_unknown_fact_and_unapproved_candidate():
    registry = {"F1": {"entailment_review_status": "ENTAILED"}}
    question = {
        "anchor_id": "A1",
        "discipline": "MED",
        "selected_candidate_ids": ["C1", "C2", "C3"],
        "stem_evidence_fact_ids": ["F1"],
        "rationale_evidence_fact_ids": ["F1"],
    }
    assert validate_question_evidence_trace(question, registry, {"C1", "C2", "C3"}) == []
    bad = copy.deepcopy(question)
    bad["stem_evidence_fact_ids"] = ["MISSING"]
    assert "UNKNOWN_OR_NON_ENTAILED_FACT" in validate_question_evidence_trace(bad, registry, {"C1", "C2", "C3"})
    bad = copy.deepcopy(question)
    bad["selected_candidate_ids"] = ["C1", "C2", "FREEHAND"]
    assert "UNAPPROVED_CANDIDATE" in validate_question_evidence_trace(bad, registry, {"C1", "C2", "C3"})


def test_development_question_set_enforces_caps_no_retry_and_three_live_distractors():
    rows = [
        {"question_id": "Q1", "discipline": "MED", "retry_count": 0, "post_stem_liveness": ["LIVE_BUT_INFERIOR"] * 3},
        {"question_id": "Q2", "discipline": "MED", "retry_count": 0, "post_stem_liveness": ["LIVE_BUT_INFERIOR"] * 3},
    ]
    assert validate_development_question_set(rows) == []
    too_many = rows + [{"question_id": "Q3", "discipline": "MED", "retry_count": 0, "post_stem_liveness": ["LIVE_BUT_INFERIOR"] * 3}]
    assert "MORE_THAN_TWO_PER_DISCIPLINE" in validate_development_question_set(too_many)
    retried = [dict(rows[0], retry_count=1)]
    assert "RETRY_NOT_ALLOWED" in validate_development_question_set(retried)
    dead = [dict(rows[0], post_stem_liveness=["LIVE_BUT_INFERIOR", "SECOND_KEY", "LIVE_BUT_INFERIOR"])]
    assert "FEWER_THAN_THREE_LIVE_DISTRACTORS" in validate_development_question_set(dead)


def test_milestone_builds_ten_traced_no_retry_development_questions():
    from scripts.qbank.run_candidate_feature_evidence_v1 import build_milestone

    result = build_milestone(ROOT, write_outputs=False)
    questions = result["questions"]["questions"]
    assert len(questions) == 10
    assert validate_development_question_set(questions) == []
    assert all(row["evidence_trace_status"] == "PASS" for row in questions)
    assert all(row["blind_solve"]["best_answer"] == row["key"] for row in questions)
    assert result["report"]["development_questions"] == {
        "generated": 10,
        "blind_solve_passed": 10,
        "liveness_passed": 10,
        "final_reviewed": 10,
        "accepted": 10,
        "rejected": 0,
        "gate_triggered": True,
    }


def test_written_milestone_copyright_audit_covers_every_content_artifact():
    from scripts.qbank.run_candidate_feature_evidence_v1 import COPYRIGHT_ARTIFACTS, run_copyright_audit

    audit = run_copyright_audit(ROOT)
    assert audit["COPYRIGHT_AUDIT"] == "PASS"
    assert audit["artifact_count"] == len(COPYRIGHT_ARTIFACTS)
    assert audit["longest_verbatim_toronto_notes_run_words"] < 12


def test_final_verification_separates_the_known_coordinator_failure():
    from scripts.qbank.run_candidate_feature_evidence_v1 import apply_final_verification

    report = {"schema_version": "X", "content_sha256": "old"}
    updated = apply_final_verification(
        report,
        focused_passed=300,
        focused_failed=0,
        full_passed=1900,
        full_failed=1,
        known_preexisting_failures=1,
        copyright_status="PASS",
    )
    assert updated["historical_safety_regression"] == "PASS"
    assert updated["aom_development_control"] == "PASS"
    assert updated["lifecycle_invariant"] == "PASS"
    assert updated["new_test_failures"] == 0
    assert updated["copyright_audit"] == "PASS"
    assert updated["memory_updated"] == "YES"
    assert updated["content_sha256"] == canonical_content_hash(updated)
