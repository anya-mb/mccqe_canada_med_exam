from pathlib import Path

import pytest

from qbank.curriculum_opportunity_registry import (
    RegistryError,
    build_all_artifacts,
    build_curriculum_snapshot,
    classify_competency,
    compute_opportunity_fingerprint,
    deduplicate_opportunities,
    derive_item_capacity,
    dry_run_queue,
    compare_opportunities,
    validate_registry_record,
    write_artifacts,
)


ROOT = Path(__file__).resolve().parents[1]


def sample_record(**overrides):
    row = {
        "opportunity_id": "QOP-CURR-000001",
        "discipline": "MED",
        "chapter_code": "C",
        "chapter_title": "Cardiology",
        "section_path": ["C.S01"],
        "study_unit_id": "SU-C-01",
        "study_unit": "Chest Pain",
        "clinical_topic": "Chest Pain",
        "key_concept_or_action": "Chest Pain — diagnosis",
        "learner_decision": "Determine the diagnosis for Chest Pain.",
        "learner_decision_code": "diagnosis",
        "opportunity_family": "DIAGNOSIS",
        "response_class": "DIAGNOSIS",
        "clinical_stage": "INITIAL_PRESENTATION",
        "population_context": "NA",
        "severity_context": "NA",
        "MCC_dimension_of_care": ["Diagnosis"],
        "MCC_physician_activity": "Assessment/Diagnosis",
        "MCC_objective_ids": ["101"],
        "primary_reasoning_target": "Differentiate the diagnosis for Chest Pain.",
        "primary_discriminator_type": "CLINICAL_FEATURE_PATTERN",
        "difficulty_potential": ["EASY", "MEDIUM"],
        "source_anchor_refs": ["SU-C-01", "C.S01"],
        "source_study_unit_ids": ["SU-C-01"],
        "source_chapter_refs": ["C.S01"],
        "aliases": ["Chest Pain — diagnosis"],
        "scope_status": "CORE_ACTION",
        "generation_readiness": "NEEDS_EVIDENCE",
        "parent_opportunity_family": "DIAGNOSIS",
        "variant_group_id": "VG-SU-C-01",
        "opportunity_fingerprint": "a" * 64,
        "review_status": "APPROVED",
        "review_error_taxonomy": [],
        "mcq_suitability": "MCQ_STRONG",
        "importance": "CORE",
        "recommended_item_capacity": 2,
        "capacity_rationale": ["DISTINCT_ITEM_FORMS"],
        "supported_difficulty_levels": ["EASY", "MEDIUM"],
        "validation_item_refs": [],
    }
    row.update(overrides)
    return row


def test_snapshot_contains_every_eligible_unit_once_and_preserves_zero_scope():
    snapshot = build_curriculum_snapshot(ROOT)
    # The allocation contains 1,175 eligible addresses, but component-mode
    # routing creates 10 repeated eligible addresses. This is a study-unit
    # inventory, so eligibility is aggregated across components.
    assert snapshot["in_scope_study_unit_count"] == 1165
    assert len(snapshot["study_units"]) == 1487
    ids = [row["study_unit_id"] for row in snapshot["study_units"]]
    assert len(ids) == len(set(ids))
    assert all(all(" " not in ref and "(" not in ref for ref in row["section_path"]) for row in snapshot["study_units"])
    suppressed = [row for row in snapshot["study_units"] if not row["eligible"]]
    assert len(suppressed) == 322
    assert all(row["zero_opportunity_reason"] for row in suppressed)


def test_registry_schema_rejects_missing_provenance():
    row = sample_record()
    del row["source_anchor_refs"]
    with pytest.raises(RegistryError, match="source_anchor_refs"):
        validate_registry_record(row)


@pytest.mark.parametrize(
    ("key", "text", "family", "response"),
    [
        ("diagnosis", "Identify the most likely diagnosis.", "DIAGNOSIS", "DIAGNOSIS"),
        ("investigations", "Select the best next investigation.", "BEST_NEXT_INVESTIGATION", "INVESTIGATION"),
        ("acute_management", "Initiate emergency stabilization.", "EMERGENCY_STABILIZATION", "ACTION"),
        ("screening", "Recommend an appropriate screening strategy.", "SCREENING", "PREVENTIVE_ACTION"),
        ("consent", "Apply capacity and consent requirements.", "CAPACITY_CONSENT", "ETHICAL_LEGAL_ACTION"),
    ],
)
def test_competency_classification_uses_controlled_vocabulary(key, text, family, response):
    got = classify_competency(key, text, ["MOST_APPROPRIATE_NEXT_STEP"])
    assert got["opportunity_family"] == family
    assert got["response_class"] == response


def test_fingerprint_ignores_cosmetic_details_but_not_material_stage():
    base = sample_record()
    first = compute_opportunity_fingerprint(base, cosmetic_context={"patient_name": "Ada", "symptom_order": 1})
    second = compute_opportunity_fingerprint(base, cosmetic_context={"patient_name": "Lin", "symptom_order": 9})
    assert first == second
    changed = dict(base, clinical_stage="DETERIORATION")
    assert compute_opportunity_fingerprint(changed) != first


def test_same_topic_identity_policy_preserves_material_decisions_and_contexts():
    diagnosis = sample_record()
    management = sample_record(
        opportunity_family="NEXT_MANAGEMENT_STEP",
        response_class="ACTION",
        learner_decision_code="management",
        learner_decision="Choose management for Chest Pain.",
        MCC_physician_activity="Management",
    )
    pregnancy = sample_record(population_context="PREGNANCY_OR_POSTPARTUM")
    cosmetic = sample_record(aliases=["same idea, different wording"])
    assert compare_opportunities(diagnosis, management) == "RELATED_BUT_DISTINCT"
    assert compare_opportunities(diagnosis, pregnancy) == "RELATED_BUT_DISTINCT"
    assert compare_opportunities(diagnosis, cosmetic) == "DUPLICATE"


def test_exact_dedupe_preserves_all_provenance():
    a = sample_record(opportunity_id="QOP-A", source_study_unit_ids=["SU-C-01"])
    b = sample_record(opportunity_id="QOP-B", source_study_unit_ids=["SU-ER-01"])
    rows, count = deduplicate_opportunities([a, b])
    assert count == 1
    assert len(rows) == 1
    assert rows[0]["source_study_unit_ids"] == ["SU-C-01", "SU-ER-01"]


def test_capacity_is_bounded_by_supported_pathways_not_target_count():
    assert derive_item_capacity(
        mcq_suitability="MCQ_STRONG",
        preferred_item_forms=["MOST_LIKELY_DIAGNOSIS", "INITIAL_INVESTIGATION", "MOST_APPROPRIATE_NEXT_STEP"],
        material_contexts=0,
        physician_activity_count=1,
    )[0] == 3
    assert derive_item_capacity(
        mcq_suitability="NOT_SUITABLE_FOR_MC",
        preferred_item_forms=["MOST_LIKELY_DIAGNOSIS"],
        material_contexts=2,
        physician_activity_count=2,
    )[0] == 0


def test_full_build_is_stable_reconciled_and_does_not_force_6086():
    first = build_all_artifacts(ROOT)
    second = build_all_artifacts(ROOT)
    assert first == second
    report = first["milestone"]
    assert report["TOTAL_IN_SCOPE_STUDY_UNITS"] == 1165
    assert report["BASE_OPPORTUNITIES"] == sum(report["OPPORTUNITY_FAMILIES"].values())
    assert report["DEFENSIBLE_TOTAL_ITEM_CAPACITY"] >= report["BASE_OPPORTUNITIES"]
    assert sum(report["PROPOSED_DISCIPLINE_TOTALS"].values()) == report["PRODUCTION_QUEUE_SIZE"]
    assert report["PRODUCTION_QUEUE_SIZE"] <= 6086
    assert report["DRY_RUN_QUEUE_ENTRIES"] <= 30
    assert report["DRY_RUN_DUPLICATES"] == 0
    assert report["DRY_RUN_ERRORS"] == 0
    assert report["GENERATION_READINESS"]["READY_EXISTING_BUNDLE"] == 6
    assert report["GENERATION_READINESS"]["READY_EXISTING_CANDIDATES_NEEDS_SEED"] >= 1
    queue = first["queue"]["entries"]
    assert len({row["seed_fingerprint"] for row in queue}) == len(queue)
    capacities = {row["opportunity_id"]: row["recommended_item_capacity"] for row in first["registry"]["opportunities"]}
    used = {}
    for row in queue:
        used[row["opportunity_id"]] = used.get(row["opportunity_id"], 0) + 1
    assert all(count <= capacities[opportunity_id] for opportunity_id, count in used.items())
    graph_ids = {(node["node_type"], node["node_id"]) for node in first["identity_graph"]["nodes"]}
    assert all(("OPPORTUNITY", row["opportunity_id"]) in graph_ids for row in queue)


def test_dry_run_rejects_duplicate_opportunity_and_seed_fingerprints():
    queue = [
        {"queue_id": "Q-1", "discipline": "MED", "opportunity_fingerprint": "a", "seed_fingerprint": "x", "candidate_dependency": "C", "evidence_dependency": "E"},
        {"queue_id": "Q-2", "discipline": "PED", "opportunity_fingerprint": "a", "seed_fingerprint": "y", "candidate_dependency": "C", "evidence_dependency": "E"},
    ]
    result = dry_run_queue(queue, limit=30)
    assert result["duplicate_count"] == 1
    assert result["error_count"] == 1


def test_artifact_writer_uses_canonical_bytes_and_reports_hash(tmp_path):
    written = write_artifacts(tmp_path, {"snapshot": {"b": 2, "a": 1}}, outputs={"snapshot": "out/snapshot.json"})
    path = tmp_path / "out/snapshot.json"
    assert path.read_text() == '{\n  "a": 1,\n  "b": 2\n}\n'
    assert written == {"out/snapshot.json": "080d51f49b27c73d17f51f3b808515a425d16218aa40021eed2ca1d204e59224"}
