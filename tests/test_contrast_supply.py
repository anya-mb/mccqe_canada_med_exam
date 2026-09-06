"""Tests for the on-demand clinical contrast supply layer.

The properties under test are the ones that make supply safe rather than merely
plentiful: identity is deterministic, a cached relation cannot cross a decision
context, duplicates are not counted as supply, an UNCERTAIN review fails closed,
retrieval stays bounded, and a second acquisition wave is refused.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from scripts.qbank.clinical_contrast_v2 import ClinicalContrastV2Error
from scripts.qbank.contrast_supply import (
    ACQUISITION_WAVES_PER_OPPORTUNITY,
    TN_CHUNK_CEILING,
    TN_CHUNK_FLOOR,
    AcquisitionLedger,
    ContrastSupplyError,
    admit_relation,
    build_supply_diagnosis,
    cache_key,
    candidate_id,
    deduplicate_candidates,
    filter_candidates,
    frozen_five_labels,
    library_eligible_candidates,
    lookup_cached_relation,
    parent_subtype_collisions,
    retrieve_tn_chunks,
    supply_context,
    validate_acquired_relation,
)

ROOT = Path(__file__).resolve().parents[1]


def _context(**overrides):
    context = {
        "learner_decision_id": "LD-P147-01",
        "demanded_response_class": "ACUTE_RESPIRATORY_DISTRESS",
        "decision_granularity": "SINGLE_DIAGNOSIS",
        "anchor_study_unit_id": "SU-P-147",
        "decision_domain": "PATIENT_CLINICAL",
    }
    context.update(overrides)
    return context


def _relation(**overrides):
    relation = {
        "learner_decision_id": "LD-P147-01",
        "response_class": "ACUTE_RESPIRATORY_DISTRESS",
        "decision_granularity": "SINGLE_DIAGNOSIS",
        "concept_a": {"concept_id": "CONCEPT-A", "member_id": "KEY", "concept": "A"},
        "concept_b": {"concept_id": "CONCEPT-B", "member_id": "SEED-B", "concept": "B"},
        "shared_features": [
            {"feature_id": "SF-P147-VIRAL-PRODROME", "contrast_role": "TIMING_FEATURE"}
        ],
        "a_supporting_features": [],
        "b_supporting_features": [
            {"feature_id": "SF-P147-VIRAL-PRODROME", "contrast_role": "TIMING_FEATURE"}
        ],
        "discriminators": [],
        "correctness_conditions_a": {
            "operator": "ALL_OF",
            "conditions": [
                {"feature_id": "SF-P147-FIRST-WHEEZE", "required_state": "PRESENT"}
            ],
        },
        "correctness_conditions_b": {
            "operator": "ALL_OF",
            "conditions": [
                {"feature_id": "SF-P147-ATOPY-OR-RECURRENCE", "required_state": "PRESENT"}
            ],
        },
        "second_key_conditions": [],
        "categorical_exclusion_conditions": [],
        "nesting_relation": "NONE",
        "confusability": "MODERATE",
        "mcc_relevance": "LD-P147-01, CORE in PED",
        "evidence_refs": ["CLM-R2-PED-DDX-TABLE"],
        "verification_status": "EVIDENCE_VERIFIED",
        "anchor_study_unit_id": "SU-P-147",
        "decision_domain": "PATIENT_CLINICAL",
        "discovery_sources": ["CURATED_LIBRARY"],
        "review": {"verdict": "APPROVED", "reviewer_id": "R-SUPPLY-A", "reasons": []},
    }
    relation.update(overrides)
    return relation


# ------------------------------------------------------------------- identity


def test_candidate_id_is_deterministic_and_context_bound():
    context = _context()
    first = candidate_id("CONCEPT-R2-SU-P-147-CROUP", context)
    second = candidate_id("CONCEPT-R2-SU-P-147-CROUP", dict(context))
    assert first == second
    assert first.startswith("CSUP-")
    other = candidate_id("CONCEPT-R2-SU-P-147-CROUP", _context(learner_decision_id="LD-P147-02"))
    assert other != first


def test_cache_key_is_order_independent_over_the_concept_pair():
    context = _context()
    assert cache_key("CONCEPT-B", "CONCEPT-A", context) == cache_key(
        "CONCEPT-A", "CONCEPT-B", context
    )


def test_cache_key_separates_decision_contexts():
    diagnosis = cache_key("CONCEPT-A", "CONCEPT-B", _context())
    management = cache_key(
        "CONCEPT-A",
        "CONCEPT-B",
        _context(
            learner_decision_id="LD-P147-03",
            demanded_response_class="MANAGEMENT_STRATEGY_FOR_PRESENTATION",
            decision_granularity="INITIAL_TREATMENT_PLAN",
        ),
    )
    assert diagnosis != management


def test_supply_context_is_read_off_the_opportunity():
    opportunity = {
        "learner_decision_id": "LD-GS76-02",
        "demanded_response_class": "DIAGNOSTIC_ADVANCEMENT",
        "decision_granularity": "SINGLE_NEXT_DIAGNOSTIC_STEP",
        "anchor_study_unit_id": "SU-GS-76",
    }
    context = supply_context(opportunity, decision_domain="PATIENT_CLINICAL")
    assert context["anchor_study_unit_id"] == "SU-GS-76"
    assert context["decision_domain"] == "PATIENT_CLINICAL"


# ------------------------------------------------------------------ filtering


def test_response_class_and_granularity_filters_both_bite():
    candidates = [
        {"member_id": "A", "response_class_tokens": ["DIAGNOSTIC_ADVANCEMENT"],
         "decision_granularity": "SINGLE_NEXT_DIAGNOSTIC_STEP"},
        {"member_id": "B", "response_class_tokens": ["MANAGEMENT_STRATEGY_FOR_PRESENTATION"],
         "decision_granularity": "SINGLE_NEXT_DIAGNOSTIC_STEP"},
        {"member_id": "C", "response_class_tokens": ["DIAGNOSTIC_ADVANCEMENT"],
         "decision_granularity": "COMPLETE_MANAGEMENT_STRATEGY"},
    ]
    context = _context(
        demanded_response_class="DIAGNOSTIC_ADVANCEMENT",
        decision_granularity="SINGLE_NEXT_DIAGNOSTIC_STEP",
    )
    kept, refused = filter_candidates(candidates, context)
    assert [row["member_id"] for row in kept] == ["A"]
    assert refused == {"B": "RESPONSE_CLASS_MISMATCH", "C": "GRANULARITY_MISMATCH"}


def test_library_eligible_candidates_respect_the_declared_filters():
    opportunities = {
        row["opportunity_label"]: row
        for row in json.loads(
            (ROOT / "research/qgen/contrast_first_pilot_opportunities.json").read_text()
        )["opportunities"]
    }
    rows = library_eligible_candidates(ROOT, opportunities["G2-PED-02"])
    seed_ids = {row["seed_id"] for row in rows}
    assert "SEED-PED-T02-CBC" in seed_ids
    # A management-strategy seed from another target may not leak in.
    assert not any(row["seed_id"].startswith("SEED-PED-T03") for row in rows)


# --------------------------------------------------------------- deduplication


def test_duplicate_concepts_are_removed_and_not_counted_as_supply():
    candidates = [
        {"member_id": "SEED-X", "concept_id": "CONCEPT-1", "discovery_source": "CURATED_LIBRARY"},
        {"member_id": "SEED-Y", "concept_id": "CONCEPT-1", "discovery_source": "TN_FTS"},
        {"member_id": "SEED-Z", "concept_id": "CONCEPT-2", "discovery_source": "GRAPH"},
    ]
    kept, removed = deduplicate_candidates(candidates)
    assert [row["member_id"] for row in kept] == ["SEED-X", "SEED-Z"]
    assert removed == {"SEED-Y": "DUPLICATE_CONCEPT_ID"}


def test_deduplication_preserves_every_discovery_provenance():
    candidates = [
        {"member_id": "SEED-X", "concept_id": "CONCEPT-1", "discovery_source": "CURATED_LIBRARY"},
        {"member_id": "SEED-Y", "concept_id": "CONCEPT-1", "discovery_source": "TN_FTS"},
    ]
    kept, _ = deduplicate_candidates(candidates)
    assert kept[0]["discovery_sources"] == ["CURATED_LIBRARY", "TN_FTS"]


def test_parent_subtype_collision_is_detected_from_declared_nesting():
    candidates = [{"member_id": "SEED-PID"}, {"member_id": "SEED-TOA"}, {"member_id": "SEED-TOR"}]
    nesting = [
        {"pair": ["SEED-PID", "SEED-TOA"], "nesting_relation": "COMPLICATION_OF"},
        {"pair": ["SEED-PID", "SEED-TOR"], "nesting_relation": "NONE"},
    ]
    collisions = parent_subtype_collisions(candidates, nesting)
    assert collisions == [{"pair": ["SEED-PID", "SEED-TOA"], "nesting_relation": "COMPLICATION_OF"}]


# ---------------------------------------------------------- bounded retrieval


def test_retrieval_is_bounded_at_both_ends():
    connection = sqlite3.connect(ROOT / "derived/tn_index/tn_index.sqlite3")
    try:
        rows = retrieve_tn_chunks(connection, "bronchiolitis wheeze infant", limit=TN_CHUNK_CEILING)
        assert len(rows) <= TN_CHUNK_CEILING
        with pytest.raises(ContrastSupplyError):
            retrieve_tn_chunks(connection, "bronchiolitis", limit=TN_CHUNK_CEILING + 1)
        with pytest.raises(ContrastSupplyError):
            retrieve_tn_chunks(connection, "bronchiolitis", limit=TN_CHUNK_FLOOR - 1)
    finally:
        connection.close()


def test_retrieved_chunks_carry_their_page_and_node_provenance():
    connection = sqlite3.connect(ROOT / "derived/tn_index/tn_index.sqlite3")
    try:
        rows = retrieve_tn_chunks(connection, "appendicitis right lower quadrant", limit=5)
    finally:
        connection.close()
    assert rows
    for row in rows:
        assert row["chunk_id"] and row["pdf_page"] is not None
        assert "bm25" in row


# ------------------------------------------------------------- one wave only


def test_a_second_acquisition_wave_is_refused():
    ledger = AcquisitionLedger()
    ledger.open_wave("G2-PED-01")
    ledger.close_wave("G2-PED-01", candidates_discovered=4)
    with pytest.raises(ContrastSupplyError):
        ledger.open_wave("G2-PED-01")
    assert ledger.waves["G2-PED-01"]["waves"] == ACQUISITION_WAVES_PER_OPPORTUNITY


# ---------------------------------------------------------------- admission


def test_an_uncertain_review_fails_closed():
    relation = _relation(review={"verdict": "UNCERTAIN", "reviewer_id": "R", "reasons": ["x"]})
    cache: dict[str, dict] = {}
    admitted = admit_relation(cache, relation, _context())
    assert admitted is False
    assert cache == {}


def test_a_rejected_review_fails_closed():
    relation = _relation(review={"verdict": "REJECTED", "reviewer_id": "R", "reasons": ["x"]})
    cache: dict[str, dict] = {}
    assert admit_relation(cache, relation, _context()) is False
    assert cache == {}


def test_an_approved_relation_is_admitted_and_then_reused():
    cache: dict[str, dict] = {}
    relation = _relation()
    assert admit_relation(cache, relation, _context()) is True
    hit = lookup_cached_relation(cache, "CONCEPT-B", "CONCEPT-A", _context())
    assert hit is not None
    assert hit["relation"]["contrast_relation_id"].startswith("CCR2-")


def test_a_cached_relation_is_not_served_to_another_decision_context():
    cache: dict[str, dict] = {}
    admit_relation(cache, _relation(), _context())
    assert lookup_cached_relation(
        cache, "CONCEPT-A", "CONCEPT-B",
        _context(learner_decision_id="LD-P147-03",
                 demanded_response_class="MANAGEMENT_STRATEGY_FOR_PRESENTATION",
                 decision_granularity="INITIAL_TREATMENT_PLAN"),
    ) is None


def test_an_unverified_relation_is_never_admitted():
    relation = _relation(verification_status="UNVERIFIED")
    cache: dict[str, dict] = {}
    assert admit_relation(cache, relation, _context()) is False


# ------------------------------------------------------- V2 schema validation


def test_acquired_relation_must_pass_the_v2_relation_schema():
    validate_acquired_relation(_relation())
    with pytest.raises(ClinicalContrastV2Error):
        validate_acquired_relation(_relation(evidence_refs=[]))
    with pytest.raises(ClinicalContrastV2Error):
        validate_acquired_relation(_relation(nesting_relation="SOMETIMES"))


def test_acquired_relation_features_must_be_in_the_frozen_vocabulary():
    with pytest.raises(ContrastSupplyError):
        validate_acquired_relation(
            _relation(
                b_supporting_features=[
                    {"feature_id": "SF-P147-INVENTED", "contrast_role": "TIMING_FEATURE"}
                ]
            ),
            vocabulary={"SF-P147-VIRAL-PRODROME": {}, "SF-P147-ATOPY-OR-RECURRENCE": {},
                        "SF-P147-FIRST-WHEEZE": {}},
        )


def test_an_added_anchor_that_alone_satisfies_correctness_is_refused():
    """S-4 limb (c). An anchor that completes the signature is not supply."""
    with pytest.raises(ContrastSupplyError):
        validate_acquired_relation(
            _relation(
                b_supporting_features=[
                    {"feature_id": "SF-P147-ATOPY-OR-RECURRENCE",
                     "contrast_role": "POSITIVE_SUPPORT"}
                ]
            ),
            enforce_anchor_sufficiency=True,
        )


# ------------------------------------------------------------------ diagnosis


def test_the_supply_diagnosis_covers_exactly_the_five_no_safe_opportunities():
    labels = frozen_five_labels(ROOT)
    assert labels == ["G2-PED-01", "G2-PED-02", "G2-PSY-03", "G2-SURG-01", "G2-SURG-02"]
    report = build_supply_diagnosis(ROOT)
    assert report["FROZEN5_ANALYZED"] == 5
    assert {row["opportunity_label"] for row in report["opportunities"]} == set(labels)


def test_the_supply_diagnosis_regenerates_byte_identically():
    committed = json.loads(
        (ROOT / "reports/qgen_v2_contrast_supply_diagnosis.json").read_text()
    )
    assert build_supply_diagnosis(ROOT) == committed


# ------------------------------------------------------------ acquisition wave


def test_the_wave_runs_exactly_one_pass_per_opportunity():
    from scripts.qbank.contrast_supply import run_acquisition_wave

    wave = run_acquisition_wave(ROOT)
    assert set(wave["waves"]) == set(frozen_five_labels(ROOT))
    assert all(entry["waves"] == 1 for entry in wave["waves"].values())
    assert wave["llm_api_calls"] == 0


def test_supply_never_removes_a_frozen_anchor():
    from scripts.qbank.contrast_first_v2_pilot import build_v2_contrast_sets
    from scripts.qbank.contrast_supply import run_acquisition_wave

    frozen = {}
    for row in build_v2_contrast_sets(ROOT)["results"]:
        for member in row["contrast_set"]["members"]:
            frozen[(row["opportunity_label"], member["member_id"])] = {
                entry["feature_id"] for entry in member["supporting_features"]
            }
    for record in run_acquisition_wave(ROOT)["results"]:
        for member in record["contrast_set"]["members"]:
            key = (record["opportunity_label"], member["member_id"])
            if key not in frozen:
                continue
            after = {entry["feature_id"] for entry in member["supporting_features"]}
            assert frozen[key] <= after


def test_the_two_opportunities_supply_cannot_help_stay_refused():
    from scripts.qbank.contrast_supply import run_acquisition_wave

    refused = {
        record["opportunity_label"]: record["selection_after"]["fail_closed_reason"]
        for record in run_acquisition_wave(ROOT)["results"]
    }
    assert refused["G2-SURG-01"] == "FAIL_CLOSED_CONTRAST_SET_SIZE"
    assert refused["G2-SURG-02"] == "FAIL_CLOSED_CONTRAST_SET_SIZE"


def test_a_dropped_candidates_signature_may_not_be_spent():
    """Rule S-6, on the case that forced it."""
    from scripts.qbank.contrast_supply import (
        run_acquisition_wave,
        run_frozen5_replay,
    )

    wave = run_acquisition_wave(ROOT)
    replay = run_frozen5_replay(ROOT, wave)
    row = next(r for r in replay["results"] if r["opportunity_label"] == "G2-PSY-03")
    assert row["terminal_state"] == "NO_SAFE_ITEM"
    assert row["fail_closed_reason"] == "FAIL_CLOSED_DROPPED_CANDIDATE_SIGNATURE_SPENT"
    assert row["dropped_unsettleable"] == "SEED-PSY-T03-DIGITAL"


def test_the_one_realized_stem_realizes_its_blueprint_exactly():
    from scripts.qbank.contrast_supply import run_acquisition_wave, run_frozen5_replay

    replay = run_frozen5_replay(ROOT, run_acquisition_wave(ROOT))
    realized = [r for r in replay["results"] if r["stage_reached"] == "INDEPENDENT_REVIEW"]
    assert [row["opportunity_label"] for row in realized] == ["G2-PED-01"]
    assert realized[0]["stem_realizes_the_blueprint_exactly"] is True
    assert realized[0]["post_stem_coherence"]["coherent"] is True


def test_the_production_gate_is_the_unchanged_one_and_it_refuses_the_item():
    """The finding the milestone turns on, pinned so it cannot drift silently."""
    from scripts.qbank.contrast_supply import run_acquisition_wave, run_frozen5_replay

    replay = run_frozen5_replay(ROOT, run_acquisition_wave(ROOT))
    row = next(r for r in replay["results"] if r["opportunity_label"] == "G2-PED-01")
    gate = row["production_gate"]
    assert gate["gate_is_the_production_gate"].endswith("retrieve_profile_aware_contrasts")
    assert gate["post_stem_3_viable"] is False
    assert gate["excluded_by_rule"]["SAF_1"] == [
        "SEED-PED-T01-FOREIGN-BODY", "SEED-PED-T01-PNEUMONIA"
    ]


def test_the_recovery_report_regenerates_byte_identically():
    from scripts.qbank.contrast_supply import build_frozen5_recovery_report

    committed = json.loads(
        (ROOT / "reports/qgen_v2_frozen5_supply_recovery.json").read_text()
    )
    assert build_frozen5_recovery_report(ROOT) == committed


def test_the_cache_only_holds_approved_evidence_verified_relations():
    cache = json.loads(
        (ROOT / "research/qgen/clinical_contrast_supply_cache.json").read_text()
    )["entries"]
    assert cache
    for entry in cache.values():
        assert entry["review"]["verdict"] == "APPROVED"
        assert entry["relation"]["verification_status"] == "EVIDENCE_VERIFIED"
        assert set(entry["context"]) == {
            "learner_decision_id", "demanded_response_class", "decision_granularity",
            "anchor_study_unit_id", "decision_domain",
        }
