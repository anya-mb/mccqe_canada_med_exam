from __future__ import annotations

import pytest

from scripts.qbank.contrast_supply_v4 import (
    audit_candidate_catalogue,
    build_clean_catalogue_v2,
    candidate_context_sha256,
    classify_catalogue_row,
    discover_global_typed_candidates_v4,
    reconstruct_v3_wrong_decisions,
    reuse_frozen_candidate_verdicts,
    signatures_compatible,
    validate_decision_signature,
)


def _row(label: str, *, candidate_id: str = "TOPIC-test", reviewed: bool = False):
    return {
        "canonical_candidate_id": candidate_id,
        "normalized_label": label,
        "aliases": [],
        "source_ids": [],
        "chapters": [],
        "study_unit_ids": [],
        "section_paths": [],
        "graph_identity": {
            "concept_type": "ACTION" if reviewed else "TOPIC",
            "vocabulary_source": "CURATED_CONTRAST_SEED" if reviewed else "TN_TOC_TOPIC",
        },
        "semantic_families": [],
        "response_classes": ["PHARMACOLOGIC_ACTION"] if reviewed else [],
        "decision_granularities": ["SINGLE_NEXT_ACTION"] if reviewed else [],
        "provenance": ([{"source": "INDEPENDENTLY_APPROVED_SEED"}] if reviewed else []),
    }


@pytest.mark.parametrize(
    ("label", "classification"),
    [
        (
            "I Primary Suro agement Se eee eee ees ER2 “ABCD3EFG” of Toxicology",
            "OCR_GARBLED_LABEL",
        ),
        ("Appendix ee en eee ee ee teens GS35 Advent Gland y", "STRUCTURAL_FURNITURE"),
        ("Figure 4. Treatment", "FIGURE_OR_TABLE_FRAGMENT"),
        ("NPI Nephrology Toronto Notes 2025", "STRUCTURAL_FURNITURE"),
        ("This is a nonavalent HPV vaccine covering", "EXTRACTION_SENTENCE_FRAGMENT"),
        ("Treatment", "GENERIC_NONOPTION_HEADING"),
        ("Croup vs Epiglottitis", "AMBIGUOUS_CONCEPT_LABEL"),
        ("Glucose)", "OTHER_INVALID"),
        ("Co mplicatio ns of Wrist Fractures Malignant Bone Tumours", "OCR_GARBLED_LABEL"),
        ("Neurofibromatosis (Type |; von Recklinghausen’s Disease)", "OCR_GARBLED_LABEL"),
        ("Hemophilia A (Factor Vill Deficiency)", "OCR_GARBLED_LABEL"),
        (
            "Idiopathic Intracranial Hypertension (Pseudotumour Cerebri) . Hydrocephalus in Pediatrics",
            "OCR_GARBLED_LABEL",
        ),
        ("“itis” Imaging", "UNCERTAIN"),
    ],
)
def test_catalogue_integrity_classifies_defect_classes(label, classification):
    assert classify_catalogue_row(_row(label))["classification"] == classification


def test_catalogue_integrity_does_not_literal_match_only_the_known_bad_string():
    variant = _row("Primary Trauma agement Re eee ees GS99 garbled source")
    result = classify_catalogue_row(variant)
    assert result["classification"] == "OCR_GARBLED_LABEL"
    assert "TOPIC-cbf55dc6ec094ff4" not in result["reason_codes"]


@pytest.mark.parametrize(
    "label",
    [
        "Neuro-Ophthalmology (Optic Neuropathy, Atrophy, Disc Edema, Visual Field Defects, Amaurosis Fugax, Pupil Abnormalities)",
        "White Blood Cell Count Abnormalities (Neutrophilia, Neutropenia, Lymphocytosis, Lymphopenia, Eosinophilia, Agranulocytosis, Leukemoid Reaction)",
        "Repetitive Transcranial Magnetic Stimulation (rTMS)",
        "von Willebrand Disease",
        "Complete Blood Count",
        "“Club Drugs”",
    ],
)
def test_catalogue_integrity_preserves_complex_medical_concepts(label):
    assert classify_catalogue_row(_row(label))["classification"] == "VALID_CONCEPT"


def test_catalogue_integrity_allows_reviewed_option_sentence_but_not_unreviewed_prose():
    label = "Give intravenous metoprolol to reduce myocardial oxygen demand"
    assert classify_catalogue_row(_row(label, reviewed=True))["classification"] == "VALID_CONCEPT"
    assert classify_catalogue_row(_row(label))["classification"] == "EXTRACTION_SENTENCE_FRAGMENT"


def test_catalogue_integrity_excludes_stem_feature_statements_as_non_candidate_rows():
    row = _row("the patient is physiologically unstable", candidate_id="SF-UNSTABLE")
    row["graph_identity"] = {
        "concept_type": "FINDING",
        "vocabulary_source": "CANONICAL_STEM_FEATURE_VOCABULARY",
    }
    result = classify_catalogue_row(row)
    assert result == {
        "classification": "OTHER_INVALID",
        "reason_codes": ["STEM_FEATURE_STATEMENT_NOT_CANDIDATE_IDENTITY"],
    }


def test_catalogue_audit_assigns_one_taxonomy_value_per_row_and_reconciles_counts():
    rows = [_row("Otitis media with effusion", candidate_id="GOOD"),
            _row("Figure 9. Caption", candidate_id="BAD")]
    audit = audit_candidate_catalogue(rows, parent_content_sha256="a" * 64)
    assert len(audit["rows"]) == 2
    assert sum(audit["counts"].values()) == 2
    assert audit["counts"]["VALID_CONCEPT"] == 1
    assert audit["counts"]["FIGURE_OR_TABLE_FRAGMENT"] == 1
    bad = next(row for row in audit["rows"] if row["canonical_candidate_id"] == "BAD")
    assert "normalized_label" not in bad
    assert len(bad["normalized_label_sha256"]) == 64


def test_clean_catalogue_v2_excludes_invalid_and_uncertain_and_binds_parent():
    rows = [_row("Otitis media with effusion", candidate_id="GOOD"),
            _row("Figure 9. Caption", candidate_id="BAD")]
    audit = audit_candidate_catalogue(rows, parent_content_sha256="a" * 64)
    value = build_clean_catalogue_v2(rows, audit=audit, parent_content_sha256="a" * 64)
    assert [row["canonical_candidate_id"] for row in value["concepts"]] == ["GOOD"]
    assert value["parent_catalogue_content_sha256"] == "a" * 64
    assert value["removed_invalid_count"] == 1
    assert value["concept_count"] == 1


def test_clean_catalogue_v2_refuses_audit_parent_or_row_mismatch():
    rows = [_row("Otitis media with effusion", candidate_id="GOOD")]
    audit = audit_candidate_catalogue(rows, parent_content_sha256="a" * 64)
    with pytest.raises(ValueError, match="parent hash"):
        build_clean_catalogue_v2(rows, audit=audit, parent_content_sha256="b" * 64)
    with pytest.raises(ValueError, match="row identities"):
        build_clean_catalogue_v2(
            rows + [_row("HbA1c", candidate_id="EXTRA")],
            audit=audit,
            parent_content_sha256="a" * 64,
        )


def _diagnostic_join_inputs():
    candidate = {
        "canonical_candidate_id": "CAND-1",
        "normalized_label": "Unrelated diagnosis",
        "response_classes": ["LOCALIZED_INFLAMMATION"],
        "decision_granularities": ["DIAGNOSIS"],
        "source_ids": ["SRC-1"],
        "chapters": ["C"],
        "study_unit_ids": ["SU-C-2"],
        "section_paths": ["Chapter > Topic"],
        "graph_identity": {"concept_type": "CONDITION"},
        "provenance": [{"source": "reviewed"}],
        "ranking_signals": {"response_class_match": True, "granularity_match": True},
    }
    discovery = {"opportunities": [{"development_id": "RDY-1", "candidates": [candidate]}]}
    review = {"batches": [{"rows": [{
        "development_id": "RDY-1", "canonical_candidate_id": "CAND-1",
        "classification": "WRONG_DECISION", "reason": "Wrong decision lane.",
    }]}]}
    semantics = {"opportunities": [{
        "development_id": "RDY-1", "learner_decision_id": "LD-1",
        "learner_decision": "Classify severity of the known condition.",
        "demanded_response_class": "PLAUSIBLE_DIAGNOSTIC_ENTITY",
        "decision_granularity": "DIAGNOSIS",
    }]}
    selection = {"opportunities": [{
        "development_id": "RDY-1", "discipline": "MED", "study_unit_id": "SU-C-1",
        "learner_decision_id": "LD-1", "learner_decision": "Classify severity of the known condition.",
    }]}
    return discovery, review, semantics, selection


def test_reconstructs_wrong_decision_with_full_frozen_context():
    rows = reconstruct_v3_wrong_decisions(*_diagnostic_join_inputs(), expected_count=1)
    assert rows == [{
        "opportunity_id": "RDY-1",
        "discipline": "MED",
        "study_unit_id": "SU-C-1",
        "learner_decision_id": "LD-1",
        "learner_decision": "Classify severity of the known condition.",
        "key": "Classify severity of the known condition.",
        "candidate_id": "CAND-1",
        "candidate_label": "Unrelated diagnosis",
        "candidate_response_classes": ["LOCALIZED_INFLAMMATION"],
        "candidate_decision_granularities": ["DIAGNOSIS"],
        "candidate_source_metadata": {
            "source_ids": ["SRC-1"], "chapters": ["C"],
            "study_unit_ids": ["SU-C-2"], "section_paths": ["Chapter > Topic"],
            "graph_identity": {"concept_type": "CONDITION"},
            "provenance": [{"source": "reviewed"}],
        },
        "v3_admission_and_ranking": {
            "demanded_response_class": "PLAUSIBLE_DIAGNOSTIC_ENTITY",
            "decision_granularity": "DIAGNOSIS",
            "ranking_signals": {"response_class_match": True, "granularity_match": True},
        },
        "previous_clinical_verdict": "WRONG_DECISION",
        "previous_clinical_reason": "Wrong decision lane.",
    }]


def test_wrong_decision_reconstruction_fails_closed_on_missing_duplicate_or_wrong_count():
    discovery, review, semantics, selection = _diagnostic_join_inputs()
    with pytest.raises(ValueError, match="expected 2"):
        reconstruct_v3_wrong_decisions(discovery, review, semantics, selection, expected_count=2)
    review["batches"][0]["rows"].append(dict(review["batches"][0]["rows"][0]))
    with pytest.raises(ValueError, match="duplicate review"):
        reconstruct_v3_wrong_decisions(discovery, review, semantics, selection, expected_count=1)


def _signature(intent="SELECT_DIAGNOSTIC_ACTION", domain="CARDIOPULMONARY", stage="DIAGNOSTIC_WORKUP"):
    return {"decision_intent": intent, "target_domain": domain, "clinical_stage": stage}


def _typed_candidate(candidate_id="CAND", *, response_class="STRUCTURAL", granularity="DIAGNOSTIC_TEST"):
    row = _row("Chest radiograph", candidate_id=candidate_id, reviewed=True)
    row.update({
        "response_classes": [response_class],
        "decision_granularities": [granularity],
        "study_unit_ids": ["SU-OTHER"],
        "chapters": ["R"],
        "semantic_families": ["imaging"],
    })
    return row


def _v4_opportunity():
    return {
        "study_unit_id": "SU-TARGET", "chapter_code": "ER",
        "demanded_response_class": "STRUCTURAL",
        "decision_granularity": "DIAGNOSTIC_TEST",
        "semantic_families": ["imaging"], "key_aliases": ["Lung POCUS"],
    }


def test_signature_validator_fails_closed_on_missing_or_unknown_values():
    controlled = {
        "decision_intent": ["SELECT_DIAGNOSTIC_ACTION"],
        "target_domain": ["CARDIOPULMONARY"],
        "clinical_stage": ["DIAGNOSTIC_WORKUP"],
    }
    assert validate_decision_signature(_signature(), controlled_vocabularies=controlled) == _signature()
    with pytest.raises(ValueError, match="missing signature dimension"):
        validate_decision_signature({"decision_intent": "SELECT_DIAGNOSTIC_ACTION"}, controlled_vocabularies=controlled)
    with pytest.raises(ValueError, match="unknown target_domain"):
        validate_decision_signature(_signature(domain="ONE_DISEASE_ONLY"), controlled_vocabularies=controlled)


@pytest.mark.parametrize(
    ("candidate", "reason"),
    [
        (_signature(stage="LONGITUDINAL_MANAGEMENT"), "WRONG_CLINICAL_STAGE"),
        (_signature(intent="SELECT_TREATMENT"), "WRONG_DECISION_INTENT"),
        (_signature(domain="MENTAL_HEALTH"), "WRONG_TARGET_DOMAIN"),
    ],
)
def test_signature_compatibility_rejects_the_earliest_mismatch(candidate, reason):
    result = signatures_compatible(_signature(), candidate)
    assert result == {"compatible": False, "reason": reason}


def test_v4_preserves_cross_chapter_known_good_candidate_and_provenance():
    result = discover_global_typed_candidates_v4(
        [_typed_candidate("CXR")], opportunity=_v4_opportunity(),
        opportunity_signature=_signature(), candidate_signatures={"CXR": _signature()},
    )
    assert [row["canonical_candidate_id"] for row in result["candidates"]] == ["CXR"]
    assert result["candidates"][0]["cross_chapter"] is True
    assert result["candidates"][0]["ranking_signals"]["decision_signature_match"] is True
    assert result["signature_rejection_counts"] == {}


def test_v4_rejects_same_response_class_and_granularity_from_wrong_decision_lane():
    result = discover_global_typed_candidates_v4(
        [_typed_candidate("RIGHT"), _typed_candidate("WRONG")],
        opportunity=_v4_opportunity(), opportunity_signature=_signature(),
        candidate_signatures={
            "RIGHT": _signature(),
            "WRONG": _signature(intent="SELECT_TREATMENT"),
        },
    )
    assert [row["canonical_candidate_id"] for row in result["candidates"]] == ["RIGHT"]
    assert result["signature_rejection_counts"] == {"WRONG_DECISION_INTENT": 1}
    assert result["signature_rejections"][0]["candidate_id"] == "WRONG"


def test_v4_filters_before_budget_so_deeper_compatible_candidates_remain_discoverable():
    catalogue = [_typed_candidate(f"BAD-{number:02d}") for number in range(12)]
    catalogue.append(_typed_candidate("DEEP-GOOD"))
    signatures = {row["canonical_candidate_id"]: _signature(intent="SELECT_TREATMENT") for row in catalogue}
    signatures["DEEP-GOOD"] = _signature()
    result = discover_global_typed_candidates_v4(
        catalogue, opportunity=_v4_opportunity(), opportunity_signature=_signature(),
        candidate_signatures=signatures,
    )
    assert [row["canonical_candidate_id"] for row in result["candidates"]] == ["DEEP-GOOD"]
    assert result["signature_rejection_counts"] == {"WRONG_DECISION_INTENT": 12}


@pytest.mark.parametrize(
    ("control_id", "opportunity_signature", "candidate_signature"),
    [
        ("AOM", _signature("IDENTIFY_DIAGNOSIS", "EAR", "INITIAL_RECOGNITION"), _signature("IDENTIFY_DIAGNOSIS", "EAR", "INITIAL_RECOGNITION")),
        ("HBA1C", _signature("SELECT_DIAGNOSTIC_ACTION", "ENDOCRINE_METABOLIC", "DIAGNOSTIC_WORKUP"), _signature("SELECT_DIAGNOSTIC_ACTION", "ENDOCRINE_METABOLIC", "DIAGNOSTIC_WORKUP")),
        ("TTE", _signature(), _signature()),
        ("CXR", _signature(), _signature()),
    ],
)
def test_required_known_good_signature_controls_are_compatible(control_id, opportunity_signature, candidate_signature):
    assert signatures_compatible(opportunity_signature, candidate_signature) == {
        "compatible": True, "reason": None,
    }, control_id


def test_frozen_verdict_reuse_requires_exact_candidate_and_context_hash():
    candidate = _typed_candidate("CXR")
    opportunity = {
        "development_id": "RDY-SURG-03",
        "learner_decision": "Use lung POCUS for suspected pneumothorax.",
        "demanded_response_class": "STRUCTURAL",
        "decision_granularity": "DIAGNOSTIC_TEST",
        "candidates": [candidate],
    }
    review = {"batches": [{"rows": [{
        "development_id": "RDY-SURG-03", "canonical_candidate_id": "CXR",
        "classification": "CLINICALLY_PLAUSIBLE", "reason": "Frozen review.",
    }]}]}
    reused = reuse_frozen_candidate_verdicts(
        [opportunity], [opportunity], review
    )
    assert reused[0]["candidate_context_sha256"] == candidate_context_sha256(opportunity, candidate)
    assert reused[0]["verdict_reused"] is True
    assert reused[0]["classification"] == "CLINICALLY_PLAUSIBLE"

    changed = {**opportunity, "learner_decision": "A different decision."}
    not_reused = reuse_frozen_candidate_verdicts([changed], [opportunity], review)
    assert not_reused[0]["verdict_reused"] is False
    assert not_reused[0]["classification"] == "UNCERTAIN"
