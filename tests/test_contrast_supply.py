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
    build_reusable_contrast_cache_v1,
    build_supply_diagnosis,
    cache_key,
    candidate_id,
    lookup_reusable_cache_entry,
    deduplicate_candidates,
    filter_candidates,
    frozen_five_labels,
    load_opportunity_semantics,
    library_eligible_candidates,
    lookup_cached_relation,
    parent_subtype_collisions,
    reclassify_premature_authoring_rejections,
    resolve_candidate_identity,
    retrieve_targeted_tn_chunks,
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


def test_a_wrong_response_class_or_granularity_rejection_survives_reclassification():
    """A rejection `filter_candidates` itself can produce is never premature.

    These two reasons name a fact knowable before any relation, anchor, or
    evidence exists for the candidate, so they belong in the legitimate half of
    the split.
    """
    legitimate, premature = reclassify_premature_authoring_rejections(
        {"B": "RESPONSE_CLASS_MISMATCH", "C": "GRANULARITY_MISMATCH"}
    )
    assert legitimate == {"B": "RESPONSE_CLASS_MISMATCH", "C": "GRANULARITY_MISMATCH"}
    assert premature == {}


def test_missing_evidence_binding_is_a_premature_authoring_rejection_not_a_cheap_filter():
    """The root-cause finding this milestone exists to fix.

    A candidate cannot be disqualified from *entering* semantic authoring merely
    for lacking the evidence binding or positive anchor that stage exists to
    build -- UNKNOWN != ABSENT. `filter_candidates` itself never emits these
    reasons (only `RESPONSE_CLASS_MISMATCH`/`GRANULARITY_MISMATCH`); a funnel
    report or bounded-discovery wave that used one applied a gate the real
    contract does not authorize before semantic review.
    """
    legitimate, premature = reclassify_premature_authoring_rejections(
        {
            "PSY-1": "MISSING_EVIDENCE_BINDING",
            "PSY-2": "MISSING_EVIDENCE_BINDING",
            "PHELO-1": "MISSING_EVIDENCE_BINDING",
        }
    )
    assert legitimate == {}
    assert premature == {
        "PSY-1": "MISSING_EVIDENCE_BINDING",
        "PSY-2": "MISSING_EVIDENCE_BINDING",
        "PHELO-1": "MISSING_EVIDENCE_BINDING",
    }


def test_missing_positive_anchor_and_relation_are_also_premature_before_semantic_review():
    legitimate, premature = reclassify_premature_authoring_rejections(
        {"X": "MISSING_POSITIVE_ANCHOR", "Y": "MISSING_RELATION", "Z": "MISSING_CANONICAL_IDENTITY"}
    )
    assert legitimate == {}
    assert set(premature) == {"X", "Y", "Z"}


def test_an_unrecognized_cheap_filter_reason_fails_closed_rather_than_silently_passing():
    """A brand-new invented rejection category must not slip through unexamined.

    Silently treating an unknown reason as legitimate would let a future wave
    invent another premature gate (as `MISSING_EVIDENCE_BINDING` was); silently
    treating it as premature could wrongly readmit a genuinely dead candidate.
    Either way the contract must be extended deliberately, not by default.
    """
    with pytest.raises(ContrastSupplyError):
        reclassify_premature_authoring_rejections({"Q": "SOME_NEW_UNVETTED_REASON"})


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


# --------------------------------------------------------------------------
# Development-12 opportunity semantics: demanded_response_class and
# decision_granularity did not exist on the frozen Development-12 opportunity
# records. This validates the frozen sidecar artifact that supplies them,
# fails closed on every unsafe input rather than silently accepting it.
# --------------------------------------------------------------------------

DEVELOPMENT_12_IDS = [
    "RDY-MED-01", "RDY-MED-02", "RDY-PED-01", "RDY-PED-04", "RDY-OBGYN-01",
    "RDY-OBGYN-02", "RDY-SURG-03", "RDY-SURG-05", "RDY-PSY-01", "RDY-PSY-03",
    "RDY-PHELO-02", "RDY-PHELO-08",
]

SEMANTICS_PATH = ROOT / "research/qgen/contrast_supply/development_12_opportunity_semantics_v1.json"


def _semantics_artifact():
    return json.loads(SEMANTICS_PATH.read_text())


def test_the_frozen_artifact_loads_eight_approved_of_twelve():
    approved = load_opportunity_semantics(SEMANTICS_PATH, DEVELOPMENT_12_IDS)
    assert len(approved) == 8
    assert {row["development_id"] for row in approved} <= set(DEVELOPMENT_12_IDS)
    for row in approved:
        assert set(row) >= {
            "learner_decision_id", "demanded_response_class",
            "decision_granularity", "anchor_study_unit_id",
        }


def test_missing_response_class_fails_closed(tmp_path):
    data = _semantics_artifact()
    del data["opportunities"][0]["demanded_response_class"]
    broken = tmp_path / "semantics.json"
    broken.write_text(json.dumps(data))
    with pytest.raises(ContrastSupplyError):
        load_opportunity_semantics(broken, DEVELOPMENT_12_IDS)


def test_missing_granularity_fails_closed(tmp_path):
    data = _semantics_artifact()
    del data["opportunities"][0]["decision_granularity"]
    broken = tmp_path / "semantics.json"
    broken.write_text(json.dumps(data))
    with pytest.raises(ContrastSupplyError):
        load_opportunity_semantics(broken, DEVELOPMENT_12_IDS)


def test_unreviewed_response_class_is_excluded_not_raised():
    """UNCERTAIN/REJECTED rows are silently excluded (fail closed = absent, not error)."""
    approved = load_opportunity_semantics(SEMANTICS_PATH, DEVELOPMENT_12_IDS)
    approved_ids = {row["development_id"] for row in approved}
    assert "RDY-PED-01" not in approved_ids  # response_class REJECTED
    assert "RDY-PSY-01" not in approved_ids  # response_class UNCERTAIN
    assert "RDY-OBGYN-02" not in approved_ids  # granularity UNCERTAIN


def test_unknown_response_class_fails_closed(tmp_path):
    data = _semantics_artifact()
    data["opportunities"][0]["demanded_response_class"] = "NOT_A_REAL_TOKEN"
    broken = tmp_path / "semantics.json"
    broken.write_text(json.dumps(data))
    with pytest.raises(ContrastSupplyError):
        load_opportunity_semantics(broken, DEVELOPMENT_12_IDS)


def test_unknown_granularity_fails_closed(tmp_path):
    data = _semantics_artifact()
    data["opportunities"][0]["decision_granularity"] = "NOT_A_REAL_GRANULARITY"
    broken = tmp_path / "semantics.json"
    broken.write_text(json.dumps(data))
    with pytest.raises(ContrastSupplyError):
        load_opportunity_semantics(broken, DEVELOPMENT_12_IDS)


def test_tampered_learner_decision_hash_fails_closed(tmp_path):
    data = _semantics_artifact()
    data["opportunities"][0]["learner_decision"] = "A different decision entirely."
    broken = tmp_path / "semantics.json"
    broken.write_text(json.dumps(data))
    with pytest.raises(ContrastSupplyError):
        load_opportunity_semantics(broken, DEVELOPMENT_12_IDS)


def test_duplicate_development_id_fails_closed(tmp_path):
    data = _semantics_artifact()
    data["opportunities"].append(dict(data["opportunities"][0]))
    broken = tmp_path / "semantics.json"
    broken.write_text(json.dumps(data))
    with pytest.raises(ContrastSupplyError):
        load_opportunity_semantics(broken, DEVELOPMENT_12_IDS)


def test_missing_development_12_row_fails_closed(tmp_path):
    data = _semantics_artifact()
    data["opportunities"] = [
        row for row in data["opportunities"] if row["development_id"] != "RDY-MED-01"
    ]
    broken = tmp_path / "semantics.json"
    broken.write_text(json.dumps(data))
    with pytest.raises(ContrastSupplyError):
        load_opportunity_semantics(broken, DEVELOPMENT_12_IDS)


def test_valid_semantics_allow_candidate_filtering_to_continue():
    approved = load_opportunity_semantics(SEMANTICS_PATH, DEVELOPMENT_12_IDS)
    by_id = {row["development_id"]: row for row in approved}
    med01 = by_id["RDY-MED-01"]
    context = supply_context(med01)
    matching = [{
        "member_id": "CAND-1",
        "response_class_tokens": [med01["demanded_response_class"]],
        "decision_granularity": med01["decision_granularity"],
    }]
    kept, refused = filter_candidates(matching, context)
    assert len(kept) == 1
    assert not refused


def test_wrong_response_class_candidate_rejected():
    approved = load_opportunity_semantics(SEMANTICS_PATH, DEVELOPMENT_12_IDS)
    med01 = next(r for r in approved if r["development_id"] == "RDY-MED-01")
    context = supply_context(med01)
    wrong = [{
        "member_id": "CAND-1",
        "response_class_tokens": ["SOME_OTHER_TOKEN"],
        "decision_granularity": med01["decision_granularity"],
    }]
    kept, refused = filter_candidates(wrong, context)
    assert kept == []
    assert refused["CAND-1"] == "RESPONSE_CLASS_MISMATCH"


def test_wrong_granularity_candidate_rejected():
    approved = load_opportunity_semantics(SEMANTICS_PATH, DEVELOPMENT_12_IDS)
    med01 = next(r for r in approved if r["development_id"] == "RDY-MED-01")
    context = supply_context(med01)
    wrong = [{
        "member_id": "CAND-1",
        "response_class_tokens": [med01["demanded_response_class"]],
        "decision_granularity": "SOME_OTHER_GRANULARITY",
    }]
    kept, refused = filter_candidates(wrong, context)
    assert kept == []
    assert refused["CAND-1"] == "GRANULARITY_MISMATCH"


# ------------------------------------------------- targeted discovery V2


def test_targeted_discovery_scopes_every_chunk_to_the_named_study_unit():
    connection = sqlite3.connect(ROOT / "derived/tn_index/tn_index.sqlite3")
    try:
        rows = retrieve_targeted_tn_chunks(
            connection,
            study_unit_id="SU-R-09",
            response_class_axis="next_action_class",
            query="Recognize a severe COPD exacerbation with acute respiratory failure and urgently escalate care.",
            limit=TN_CHUNK_CEILING,
        )
        assert rows
        unit_chunk_ids = {
            row[0] for row in connection.execute(
                "SELECT chunk_id FROM chunk_study_units WHERE study_unit_id = ?",
                ("SU-R-09",),
            )
        }
    finally:
        connection.close()
    assert all(row["chunk_id"] in unit_chunk_ids for row in rows)
    assert all(row["discovery_source"] == "TARGETED_STUDY_UNIT_HEADING_FAMILY" for row in rows)


def test_targeted_discovery_is_bounded_at_both_ends():
    connection = sqlite3.connect(ROOT / "derived/tn_index/tn_index.sqlite3")
    try:
        with pytest.raises(ContrastSupplyError):
            retrieve_targeted_tn_chunks(
                connection, study_unit_id="SU-R-09", response_class_axis="next_action_class",
                query="escalate care", limit=TN_CHUNK_CEILING + 1,
            )
        with pytest.raises(ContrastSupplyError):
            retrieve_targeted_tn_chunks(
                connection, study_unit_id="SU-R-09", response_class_axis="next_action_class",
                query="escalate care", limit=TN_CHUNK_FLOOR - 1,
            )
    finally:
        connection.close()


def test_targeted_discovery_rejects_unknown_study_unit():
    connection = sqlite3.connect(ROOT / "derived/tn_index/tn_index.sqlite3")
    try:
        with pytest.raises(ContrastSupplyError):
            retrieve_targeted_tn_chunks(
                connection, study_unit_id="SU-NOT-A-REAL-UNIT",
                response_class_axis="next_action_class", query="escalate care",
                limit=TN_CHUNK_FLOOR,
            )
    finally:
        connection.close()


def test_targeted_discovery_rejects_unknown_response_class_axis():
    connection = sqlite3.connect(ROOT / "derived/tn_index/tn_index.sqlite3")
    try:
        with pytest.raises(ContrastSupplyError):
            retrieve_targeted_tn_chunks(
                connection, study_unit_id="SU-R-09", response_class_axis="NOT_A_REAL_AXIS",
                query="escalate care", limit=TN_CHUNK_FLOOR,
            )
    finally:
        connection.close()


def test_targeted_discovery_narrower_than_whole_corpus_baseline():
    connection = sqlite3.connect(ROOT / "derived/tn_index/tn_index.sqlite3")
    try:
        baseline = retrieve_tn_chunks(
            connection,
            "Recognize a severe COPD exacerbation with acute respiratory failure and urgently escalate care.",
            limit=TN_CHUNK_CEILING,
        )
        targeted = retrieve_targeted_tn_chunks(
            connection, study_unit_id="SU-R-09", response_class_axis="next_action_class",
            query="Recognize a severe COPD exacerbation with acute respiratory failure and urgently escalate care.",
            limit=TN_CHUNK_CEILING,
        )
        unit_chunk_ids = {
            row[0] for row in connection.execute(
                "SELECT chunk_id FROM chunk_study_units WHERE study_unit_id = ?",
                ("SU-R-09",),
            )
        }
    finally:
        connection.close()
    off_unit_baseline_hits = [row for row in baseline if row["chunk_id"] not in unit_chunk_ids]
    assert off_unit_baseline_hits, (
        "the baseline whole-corpus query is expected to surface at least one chunk "
        "outside the opportunity's own study unit, which is the exact chapter-sibling "
        "noise mechanism the root-cause diagnosis identified"
    )
    assert all(row["chunk_id"] in unit_chunk_ids for row in targeted)


def test_targeted_discovery_falls_back_to_unit_scope_when_heading_family_is_empty_in_unit():
    # SU-PS-06 genuinely has zero chunks whose subheading matches the
    # cardinal_syndrome_capability ("differential") heading family -- a real,
    # measured fact about this unit's TN structure, not a query defect. A silent
    # zero here would be a new, narrower failure mode than the whole-corpus
    # baseline; falling back to unit-scope-only (still never whole-corpus) keeps
    # V2 at least as good as V1's recall while keeping its precision gain.
    connection = sqlite3.connect(ROOT / "derived/tn_index/tn_index.sqlite3")
    try:
        empty_family = connection.execute(
            "SELECT count(*) FROM chunks c JOIN chunk_study_units su "
            "ON su.chunk_id = c.chunk_id WHERE su.study_unit_id = ? "
            "AND lower(c.subheading) LIKE '%differential%'",
            ("SU-PS-06",),
        ).fetchone()[0]
        assert empty_family == 0, "fixture assumption changed; update this test"
        rows = retrieve_targeted_tn_chunks(
            connection, study_unit_id="SU-PS-06",
            response_class_axis="cardinal_syndrome_capability",
            query="brief psychotic disorder schizophreniform schizophrenia duration",
            limit=TN_CHUNK_FLOOR,
        )
        unit_chunk_ids = {
            row[0] for row in connection.execute(
                "SELECT chunk_id FROM chunk_study_units WHERE study_unit_id = ?",
                ("SU-PS-06",),
            )
        }
    finally:
        connection.close()
    assert rows, "expected a unit-scope fallback instead of a silent zero"
    assert all(row["chunk_id"] in unit_chunk_ids for row in rows)
    assert all(row["discovery_source"] == "TARGETED_STUDY_UNIT_SCOPE_ONLY_FALLBACK" for row in rows)


def test_targeted_discovery_axis_without_heading_family_still_scopes_to_unit():
    connection = sqlite3.connect(ROOT / "derived/tn_index/tn_index.sqlite3")
    try:
        rows = retrieve_targeted_tn_chunks(
            connection, study_unit_id="SU-R-09", response_class_axis="value_served",
            query="escalate care respiratory failure", limit=TN_CHUNK_FLOOR,
        )
        unit_chunk_ids = {
            row[0] for row in connection.execute(
                "SELECT chunk_id FROM chunk_study_units WHERE study_unit_id = ?",
                ("SU-R-09",),
            )
        }
    finally:
        connection.close()
    assert all(row["chunk_id"] in unit_chunk_ids for row in rows)


def test_targeted_discovery_carries_section_path():
    connection = sqlite3.connect(ROOT / "derived/tn_index/tn_index.sqlite3")
    try:
        rows = retrieve_targeted_tn_chunks(
            connection,
            study_unit_id="SU-R-09",
            response_class_axis="next_action_class",
            query="Recognize a severe COPD exacerbation with acute respiratory failure and urgently escalate care.",
            limit=TN_CHUNK_CEILING,
        )
    finally:
        connection.close()
    assert rows
    assert all("section_path" in row for row in rows)


# ------------------------------------------------- candidate identity resolution


def test_specific_heading_resolves():
    hit = {"chunk_id": "c1", "subheading": "Otitis Media with Effusion", "section_path": None}
    result = resolve_candidate_identity(hit)
    assert result["resolvable"] is True
    assert result["resolution_method"] == "SPECIFIC_HEADING_IDENTITY"
    assert result["identity"] == "Otitis Media with Effusion"
    assert result["source_field"] == "subheading"


def test_generic_heading_with_unambiguous_section_path_leaf_resolves():
    hit = {
        "chunk_id": "c2",
        "subheading": "Treatment",
        "section_path": "Pediatrics > Otitis Media > Treatment > Acute Mastoiditis",
    }
    result = resolve_candidate_identity(hit)
    assert result["resolvable"] is True
    assert result["resolution_method"] == "SECTION_PATH_IDENTITY"
    assert result["identity"] == "Acute Mastoiditis"
    assert result["source_field"] == "section_path"


def test_generic_heading_with_entirely_generic_breadcrumb_fails_closed():
    hit = {
        "chunk_id": "c3",
        "subheading": "Approach",
        "section_path": "Medicine > Cardiology > Management",
    }
    result = resolve_candidate_identity(hit)
    assert result["resolvable"] is False
    assert result["resolution_method"] == "GENERIC_HEADING_ONLY"
    assert result["identity"] is None


def test_ambiguous_breadcrumb_fails_closed():
    hit = {
        "chunk_id": "c4",
        "subheading": "Investigations",
        "section_path": "Pediatrics > Stridor > Croup vs Epiglottitis",
    }
    result = resolve_candidate_identity(hit)
    assert result["resolvable"] is False
    assert result["resolution_method"] == "AMBIGUOUS_STRUCTURAL_IDENTITY"
    assert result["identity"] is None


def test_treatment_alone_does_not_resolve():
    hit = {"chunk_id": "c5", "subheading": "Treatment", "section_path": None}
    result = resolve_candidate_identity(hit)
    assert result["resolvable"] is False
    assert result["resolution_method"] == "GENERIC_HEADING_ONLY"


def test_management_alone_does_not_resolve():
    hit = {"chunk_id": "c6", "subheading": "Management", "section_path": None}
    result = resolve_candidate_identity(hit)
    assert result["resolvable"] is False
    assert result["resolution_method"] == "GENERIC_HEADING_ONLY"


def test_investigations_alone_does_not_resolve():
    hit = {"chunk_id": "c7", "subheading": "Investigations", "section_path": None}
    result = resolve_candidate_identity(hit)
    assert result["resolvable"] is False
    assert result["resolution_method"] == "GENERIC_HEADING_ONLY"


def test_no_section_path_and_generic_heading_does_not_resolve():
    hit = {"chunk_id": "c8", "subheading": "Complications", "section_path": ""}
    result = resolve_candidate_identity(hit)
    assert result["resolvable"] is False
    assert result["resolution_method"] == "GENERIC_HEADING_ONLY"


def test_existing_reviewed_identity_takes_precedence():
    hit = {"chunk_id": "c9", "subheading": "Treatment", "section_path": None}
    result = resolve_candidate_identity(
        hit, existing_reviewed_identities={"c9": "Bill C-14 Criteria for MAID"}
    )
    assert result["resolvable"] is True
    assert result["resolution_method"] == "EXISTING_REVIEWED_IDENTITY"
    assert result["identity"] == "Bill C-14 Criteria for MAID"


def test_known_approved_aom_candidate_resolves():
    hit = {
        "chunk_id": "c10",
        "subheading": "Otitis Media with Effusion",
        "section_path": "Pediatrics > Otitis Media > Otitis Media with Effusion",
    }
    result = resolve_candidate_identity(hit)
    assert result["resolvable"] is True
    assert result["identity"] == "Otitis Media with Effusion"


def test_hba1c_development_control_resolves():
    hit = {"chunk_id": "c11", "subheading": "HbA1c", "section_path": None}
    result = resolve_candidate_identity(hit)
    assert result["resolvable"] is True
    assert result["identity"] == "HbA1c"


def test_tte_development_control_resolves():
    hit = {
        "chunk_id": "c12",
        "subheading": "Diagnosis",
        "section_path": "Surgery > Trauma > Diagnosis > Transthoracic Echocardiography (TTE)",
    }
    result = resolve_candidate_identity(hit)
    assert result["resolvable"] is True
    assert result["identity"] == "Transthoracic Echocardiography (TTE)"


def test_figure_caption_subheading_does_not_resolve():
    hit = {"chunk_id": "c13", "subheading": "Figure 10. Guidelines for COPD management", "section_path": None}
    result = resolve_candidate_identity(hit)
    assert result["resolvable"] is False
    assert result["resolution_method"] == "OTHER"


def test_colon_label_fragment_does_not_resolve():
    hit = {"chunk_id": "c14", "subheading": "Outcome: Treatment failure, risk of relapse, timeto", "section_path": None}
    result = resolve_candidate_identity(hit)
    assert result["resolvable"] is False
    assert result["resolution_method"] == "OTHER"


def test_sentence_opening_fragment_does_not_resolve():
    hit = {"chunk_id": "c15", "subheading": "This is a nonavalent HPV vaccine covering", "section_path": None}
    result = resolve_candidate_identity(hit)
    assert result["resolvable"] is False
    assert result["resolution_method"] == "OTHER"


def test_truncated_trailing_stopword_fragment_does_not_resolve():
    hit = {"chunk_id": "c16", "subheading": "Measures that operate without the person's", "section_path": None}
    result = resolve_candidate_identity(hit)
    assert result["resolvable"] is False
    assert result["resolution_method"] == "OTHER"


def test_trailing_pipe_fragment_does_not_resolve():
    hit = {"chunk_id": "c17", "subheading": "Treatment |", "section_path": None}
    result = resolve_candidate_identity(hit)
    assert result["resolvable"] is False
    assert result["resolution_method"] == "OTHER"


def test_extraction_artifact_in_section_path_terminal_does_not_resolve():
    hit = {
        "chunk_id": "c18",
        "subheading": "Treatment",
        "section_path": "Pediatrics > Otitis Media > Figure 3. Treatment algorithm",
    }
    result = resolve_candidate_identity(hit)
    assert result["resolvable"] is False
    assert result["resolution_method"] == "OTHER"


# ------------------------------------------------ reusable contrast cache v1


def _approved_seed(**overrides):
    seed = {
        "seed_id": "SEED-TEST-01",
        "candidate_id": "RDY-TEST-01__candidate",
        "opportunity_id": "RDY-TEST-01",
        "response_class": "DIAGNOSTIC_ORDER",
        "decision_granularity": "SINGLE_NEXT_ACTION",
        "relation_id": "CCR2-TEST-01",
        "anchor_id": "TNC-test01",
        "evidence_refs": ["required_evidence_propositions:CCR2-TEST-01"],
        "review_status": "APPROVED",
        "scope": "DEVELOPMENT_12_CONTINUATION",
    }
    seed.update(overrides)
    return seed


def test_cache_v1_admits_only_approved_seeds():
    pack = {"seeds": [_approved_seed(), _approved_seed(review_status="UNCERTAIN", seed_id="SEED-TEST-02")]}
    with pytest.raises(ContrastSupplyError, match="only APPROVED seeds"):
        build_reusable_contrast_cache_v1(pack)


def test_cache_v1_refuses_seed_missing_anchor():
    pack = {"seeds": [_approved_seed(anchor_id=None)]}
    with pytest.raises(ContrastSupplyError, match="approved anchor"):
        build_reusable_contrast_cache_v1(pack)


def test_cache_v1_lookup_exact_scope_hit():
    cache = build_reusable_contrast_cache_v1({"seeds": [_approved_seed()]})
    hit = lookup_reusable_cache_entry(
        cache, opportunity_id="RDY-TEST-01", candidate_id_="RDY-TEST-01__candidate",
        response_class="DIAGNOSTIC_ORDER", decision_granularity="SINGLE_NEXT_ACTION",
    )
    assert hit is not None
    assert hit["seed_id"] == "SEED-TEST-01"


def test_cache_v1_lookup_wrong_opportunity_misses():
    cache = build_reusable_contrast_cache_v1({"seeds": [_approved_seed()]})
    hit = lookup_reusable_cache_entry(
        cache, opportunity_id="RDY-OTHER-99", candidate_id_="RDY-TEST-01__candidate",
        response_class="DIAGNOSTIC_ORDER", decision_granularity="SINGLE_NEXT_ACTION",
    )
    assert hit is None


def test_cache_v1_lookup_wrong_response_class_misses():
    cache = build_reusable_contrast_cache_v1({"seeds": [_approved_seed()]})
    hit = lookup_reusable_cache_entry(
        cache, opportunity_id="RDY-TEST-01", candidate_id_="RDY-TEST-01__candidate",
        response_class="PHARMACOLOGIC_TREATMENT", decision_granularity="SINGLE_NEXT_ACTION",
    )
    assert hit is None


def test_cache_v1_lookup_wrong_granularity_misses():
    cache = build_reusable_contrast_cache_v1({"seeds": [_approved_seed()]})
    hit = lookup_reusable_cache_entry(
        cache, opportunity_id="RDY-TEST-01", candidate_id_="RDY-TEST-01__candidate",
        response_class="DIAGNOSTIC_ORDER", decision_granularity="TREATMENT_BUNDLE",
    )
    assert hit is None


def test_cache_v1_population_restriction_requires_stem_context():
    restricted = _approved_seed(
        population_context_restriction_rule={
            "forbidden_if_context": {"proposed_decision_is_maid_request": True}
        }
    )
    cache = build_reusable_contrast_cache_v1({"seeds": [restricted]})
    with pytest.raises(ContrastSupplyError, match="stem_context must be supplied"):
        lookup_reusable_cache_entry(
            cache, opportunity_id="RDY-TEST-01", candidate_id_="RDY-TEST-01__candidate",
            response_class="DIAGNOSTIC_ORDER", decision_granularity="SINGLE_NEXT_ACTION",
        )


def test_cache_v1_population_restriction_rejects_matching_context():
    restricted = _approved_seed(
        population_context_restriction_rule={
            "forbidden_if_context": {"proposed_decision_is_maid_request": True}
        }
    )
    cache = build_reusable_contrast_cache_v1({"seeds": [restricted]})
    hit = lookup_reusable_cache_entry(
        cache, opportunity_id="RDY-TEST-01", candidate_id_="RDY-TEST-01__candidate",
        response_class="DIAGNOSTIC_ORDER", decision_granularity="SINGLE_NEXT_ACTION",
        stem_context={"proposed_decision_is_maid_request": True},
    )
    assert hit is None


def test_cache_v1_population_restriction_allows_non_matching_context():
    restricted = _approved_seed(
        population_context_restriction_rule={
            "forbidden_if_context": {"proposed_decision_is_maid_request": True}
        }
    )
    cache = build_reusable_contrast_cache_v1({"seeds": [restricted]})
    hit = lookup_reusable_cache_entry(
        cache, opportunity_id="RDY-TEST-01", candidate_id_="RDY-TEST-01__candidate",
        response_class="DIAGNOSTIC_ORDER", decision_granularity="SINGLE_NEXT_ACTION",
        stem_context={"proposed_decision_is_maid_request": False},
    )
    assert hit is not None


def test_cache_v1_no_implicit_latest_lookup_requires_explicit_cache():
    cache_v1 = build_reusable_contrast_cache_v1({"seeds": [_approved_seed()]})
    cache_v2 = build_reusable_contrast_cache_v1({"seeds": [_approved_seed(seed_id="SEED-TEST-99")]})
    # Two independently built caches never merge or fall back into one another;
    # a lookup against one cannot see entries only the other holds unless the
    # same seed is present in both, proving there is no shared implicit "latest".
    assert cache_v1 is not cache_v2
    hit = lookup_reusable_cache_entry(
        cache_v2, opportunity_id="RDY-TEST-01", candidate_id_="RDY-TEST-01__candidate",
        response_class="DIAGNOSTIC_ORDER", decision_granularity="SINGLE_NEXT_ACTION",
    )
    assert hit["seed_id"] == "SEED-TEST-99"
