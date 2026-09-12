from __future__ import annotations

import pytest

from scripts.qbank.candidate_universe import (
    CandidateUniverseError,
    build_candidate_universe,
    build_compatibility_graph,
    build_concept_cards,
    candidate_density_metrics,
    evidence_economy_metrics,
)


def _anchor():
    return {
        "anchor_id": "A-1",
        "learner_decision": "Identify the diagnosis.",
        "key": {"canonical_identity": "KEY", "label": "Key"},
        "response_class": "DIAGNOSIS",
        "granularity": "DIAGNOSIS",
        "decision_signature": {"clinical_stage": "INITIAL_RECOGNITION"},
        "clinical_context": "ADULT_GENERAL",
    }


def _candidate(candidate_id="C-1", **overrides):
    row = {
        "canonical_candidate_id": candidate_id,
        "normalized_candidate_text": "Candidate one",
        "candidate_concept": "Candidate one",
        "origin": "EXISTING_BUNDLE_DERIVED",
        "source_kind": "SOURCE_DERIVED",
        "response_class": "DIAGNOSIS",
        "granularity": "DIAGNOSIS",
        "applicability_context": "ADULT_GENERAL",
        "proposal_stage": 1,
        "review_stage_1": {"verdict": "PLAUSIBLE", "reason_codes": []},
        "evidence_status": "ENTAILED",
        "review_stage_2": {"verdict": "APPROVED", "reason_codes": []},
        "second_key_status": "NO_IDENTIFIED_RISK",
        "pairwise_distinctness": "DISTINCT",
    }
    row.update(overrides)
    return row


def test_universe_collapses_duplicate_concepts_and_preserves_origins():
    duplicate = _candidate(
        "C-ALIAS",
        normalized_candidate_text=" candidate ONE ",
        origin="MODEL_PROPOSED",
        source_kind="GENERATED",
        proposal_stage=3,
        review_stage_2={"verdict": "UNCERTAIN", "reason_codes": ["DUPLICATE"]},
    )
    result = build_candidate_universe([_anchor()], {"A-1": [_candidate(), duplicate]})
    assert len(result["anchors"][0]["candidates"]) == 1
    assert result["anchors"][0]["candidates"][0]["origins"] == [
        "EXISTING_BUNDLE_DERIVED",
        "MODEL_PROPOSED",
    ]


def test_universe_fails_closed_without_origin():
    with pytest.raises(CandidateUniverseError, match="origin"):
        build_candidate_universe([_anchor()], {"A-1": [_candidate(origin=None)]})


def test_universe_enforces_hard_review_ceiling():
    candidates = [
        _candidate(f"C-{index}", normalized_candidate_text=f"Candidate {index}")
        for index in range(25)
    ]
    with pytest.raises(CandidateUniverseError, match="24"):
        build_candidate_universe([_anchor()], {"A-1": candidates})


@pytest.mark.parametrize(
    ("stage1", "stage2", "evidence", "expected"),
    [
        ("PLAUSIBLE", "APPROVED", "ENTAILED", "ADMITTED"),
        ("REJECTED", "APPROVED", "ENTAILED", "REJECTED"),
        ("UNCERTAIN", "APPROVED", "ENTAILED", "REJECTED"),
        ("PLAUSIBLE", "UNCERTAIN", "ENTAILED", "REJECTED"),
        ("PLAUSIBLE", "APPROVED", "INSUFFICIENT", "REJECTED"),
    ],
)
def test_universe_admission_is_fail_closed(stage1, stage2, evidence, expected):
    candidate = _candidate(
        review_stage_1={"verdict": stage1, "reason_codes": []},
        review_stage_2={"verdict": stage2, "reason_codes": []},
        evidence_status=evidence,
    )
    result = build_candidate_universe([_anchor()], {"A-1": [candidate]})
    assert result["anchors"][0]["candidates"][0]["final_admission_state"] == expected


def test_density_metrics_use_only_admitted_candidates():
    result = build_candidate_universe(
        [_anchor()],
        {"A-1": [_candidate(), _candidate("C-2", normalized_candidate_text="Two", evidence_status="INSUFFICIENT")]},
    )
    metrics = candidate_density_metrics(result)
    assert metrics["approved_sizes"] == {"min": 1, "median": 1, "mean": 1.0, "max": 1}
    assert metrics["thresholds"]["3"] == 0


def test_concept_cards_reuse_only_entailed_facts_and_preserve_scope():
    registry = {
        "facts": [
            {
                "evidence_fact_id": "F-1",
                "canonical_subject_id": "C-1",
                "canonical_subject_name": "Candidate one",
                "normalized_clinical_proposition": "Feature one.",
                "feature_roles": ["CANDIDATE_SUPPORTING"],
                "source_refs": ["S-1", "S-2"],
                "population_context": ["ADULT_GENERAL"],
                "clinical_stage": ["INITIAL_RECOGNITION"],
                "entailment_review_status": "ENTAILED",
                "reuse_scope": {"anchor_ids": ["A-1", "A-2"], "candidate_context_ids": ["X", "Y"]},
            },
            {
                "evidence_fact_id": "F-2",
                "canonical_subject_id": "C-1",
                "canonical_subject_name": "Candidate one",
                "normalized_clinical_proposition": "Unsupported.",
                "feature_roles": ["CANDIDATE_SUPPORTING"],
                "source_refs": ["S-1"],
                "population_context": ["ADULT_GENERAL"],
                "clinical_stage": ["INITIAL_RECOGNITION"],
                "entailment_review_status": "PARTIALLY_ENTAILED",
                "reuse_scope": {"anchor_ids": ["A-1"], "candidate_context_ids": ["X"]},
            },
        ]
    }
    cards = build_concept_cards(registry, [_candidate()])
    assert cards["cards"][0]["evidence_fact_ids"] == ["F-1"]
    assert cards["cards"][0]["facts"] == [{
        "evidence_fact_id": "F-1",
        "feature_roles": ["CANDIDATE_SUPPORTING"],
        "anchor_ids": ["A-1", "A-2"],
        "candidate_context_ids": ["X", "Y"],
    }]
    assert cards["cards"][0]["applicability_scope"]["population_context"] == ["ADULT_GENERAL"]
    assert cards["cards"][0]["multi_source_verification"] == "MULTI_SOURCE_CONCORDANT"


def test_action_context_fact_supplies_next_action_but_diagnosis_does_not():
    fact = {
        "evidence_fact_id": "F-1",
        "canonical_subject_id": "C-1",
        "canonical_subject_name": "Candidate one",
        "normalized_clinical_proposition": "Instability would favour this action.",
        "feature_roles": ["WHAT_MAKES_CANDIDATE_CORRECT"],
        "source_refs": ["S-1"],
        "population_context": ["ADULT_GENERAL"],
        "clinical_stage": ["INITIAL_RECOGNITION"],
        "entailment_review_status": "ENTAILED",
        "reuse_scope": {"anchor_ids": ["A-1"], "candidate_context_ids": ["C-1"]},
    }
    action = _candidate(response_class="MANAGEMENT_ACTION", granularity="SINGLE_NEXT_ACTION")
    diagnosis = _candidate()
    assert build_concept_cards({"facts": [fact]}, [action])["cards"][0]["next_step_status"] == "AVAILABLE"
    assert build_concept_cards({"facts": [fact]}, [diagnosis])["cards"][0]["next_step_status"] == "MISSING"


def test_graph_records_reviewed_key_edges_and_rejection_edges_without_dense_unknowns():
    universe = build_candidate_universe(
        [_anchor()],
        {"A-1": [
            _candidate(),
            _candidate(
                "C-2",
                normalized_candidate_text="Candidate two",
                review_stage_1={"verdict": "REJECTED", "reason_codes": ["ALIAS_KEY"]},
            ),
        ]},
    )
    graph = build_compatibility_graph(universe, {"C-1": ["F-DISC"]})
    relations = {edge["relation"] for edge in graph["edges"]}
    assert relations == {"KEY_SUPERIOR_UNDER_CONTEXT", "ALIAS_OF"}
    assert all(edge["relation"] != "UNKNOWN" for edge in graph["edges"])


def test_evidence_economy_counts_reuse_and_zero_new_pairwise_requests():
    cards = {
        "cards": [{
            "concept_id": "C-1",
            "evidence_fact_ids": ["F-1"],
            "facts": [{"evidence_fact_id": "F-1", "anchor_ids": ["A-1", "A-2"], "candidate_context_ids": ["C-1", "C-2"]}],
            "reuse_scope": {"anchor_ids": ["A-1", "A-2"], "candidate_context_ids": ["C-1", "C-2"]},
        }]
    }
    graph = {"edges": [{"edge_id": "E-1", "reuse_count": 2, "evidence_fact_ids": ["F-1"]}]}
    assert evidence_economy_metrics(cards, graph, new_evidence_requests=0) == {
        "feature_facts_total": 1,
        "feature_facts_reused_across_anchors": 1,
        "feature_facts_reused_across_candidates": 1,
        "pairwise_edges_total": 1,
        "pairwise_edges_reused": 1,
        "new_evidence_requests": 0,
    }
