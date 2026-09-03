from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

from qbank.chapter_staged_generation import (
    ChapterStagedGenerationError,
    build_global_study_unit_index,
    canonical_sha256,
    find_decision_granularity_cues,
    find_option_text_cues,
    find_option_shape_cues,
    find_option_position_cues,
    find_negated_stem_echo_cues,
    find_option_category_parity_defects,
    find_polarity_completeness_defects,
    find_rationale_register_defects,
    find_terminal_exclusion_cues,
    compute_derived_value,
    resolve_chapter_anchor,
    retrieve_global_contrasts,
    validate_calibrated_rationale_assessment,
    validate_contrast_library,
    validate_micro_failure_review,
    validate_micro_pilot,
    validate_option_cue_review,
    validate_staged_item,
)


REPO = Path(__file__).resolve().parents[1]
STAGES = [
    "TORONTO_NOTES_ANCHOR",
    "MCC_OBJECTIVE_PHYSICIAN_ACTIVITY",
    "PRIMARY_LEARNER_DECISION",
    "ANCHOR_FIDELITY",
    "OPEN_ENDED_STEM_KEY",
    "BLIND_COVER_OPTIONS_SOLVER",
    "GLOBAL_CONTRAST_RETRIEVAL",
    "CONTRASTIVE_EVIDENCE_MATRIX",
    "SEPARATE_DISTRACTOR_CONSTRUCTION",
    "DISTRACTOR_ADVERSARIAL_RANKING",
    "MCQ_ASSEMBLY",
    "PLAN_FIDELITY_SHORTCUT_CUE_CHECK",
    "RATIONALES",
    "FRESH_INDEPENDENT_VERIFICATION",
]
STAGES_V2 = STAGES[:10] + [
    "OPTION_REALIZATION",
    "PARALLEL_OPTION_SET_REVIEW",
] + STAGES[10:]
SEMANTIC_CUE_CHECKS = {
    "key_only_specificity",
    "semantic_odd_one_out",
    "option_category_match",
    "convergence",
    "clang_testwise_detectability",
    "natural_parallelism",
    "meaning_preservation",
}
DEFECTS = {
    "FACTUAL_ERROR",
    "UNSUPPORTED_CLAIM",
    "AMBIGUOUS_BEST_ANSWER",
    "ANCHOR_FIDELITY_FAILURE",
    "PLAN_MISMATCH",
    "WEAK_DISTRACTOR",
    "CONTEXT_NECESSITY_FAILURE",
    "COVER_OPTIONS_FAILURE",
    "OPTION_CUE_FAILURE",
    "RATIONALE_DEFICIENCY",
    "MATERIAL_DUPLICATION",
}


def _sha(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    ).hexdigest()


def _study_unit(study_unit_id: str) -> dict:
    for path in sorted((REPO / "research/scope/chapters").glob("*/study_units.json")):
        for unit in json.loads(path.read_text())["study_units"]:
            if unit["study_unit_id"] == study_unit_id:
                return unit
    raise AssertionError(study_unit_id)


def _evidence() -> dict:
    source = {
        "source_id": "SRC-GUIDELINE",
        "title": "Authoritative guideline",
        "issuing_organization": "Guideline organization",
        "url": "https://example.invalid/guideline",
        "retrieval_date": "2026-09-01",
        "currentness_status": "CURRENT",
    }
    source["sha256"] = _sha({k: v for k, v in source.items() if k != "sha256"})
    claims = []
    for claim_id in ["CLM-KEY", "CLM-PE", "CLM-AORTA", "CLM-PERICARDITIS", "CLM-GERD"]:
        claim = {
            "claim_id": claim_id,
            "statement": f"Evidence-bounded statement for {claim_id}.",
            "exact_reason": f"Required to validate {claim_id} for the bounded clinical micro-pilot.",
            "source_refs": [{"source_id": "SRC-GUIDELINE", "source_sha256": source["sha256"], "locator": f"Section {claim_id}"}],
            "verification_status": "VERIFIED_COMPLETE",
        }
        claim["sha256"] = _sha({k: v for k, v in claim.items() if k != "sha256"})
        claims.append(claim)
    return {
        "schema_version": "1.0",
        "scope": "CHAPTER_REVIEW_MICRO_TARGETED_EVIDENCE",
        "sources": [source],
        "claims": claims,
    }


def _provenance(study_unit_id: str) -> dict:
    unit = _study_unit(study_unit_id)
    return {
        "study_unit_id": study_unit_id,
        "chapter_id": unit["chapter_code"],
        "source_node_ids": unit["source_node_ids"],
        "tn_pages": unit["tn_page_range"],
        "pdf_pages": unit["pdf_page_range"],
    }


def _library(evidence: dict | None = None) -> dict:
    evidence = evidence or _evidence()
    claim_hashes = {claim["claim_id"]: claim["sha256"] for claim in evidence["claims"]}
    concepts = [
        ("EDGE-PE", "SU-R-19", "CLM-PE"),
        ("EDGE-AORTA", "SU-VS-03", "CLM-AORTA"),
        ("EDGE-PERICARDITIS", "SU-C-33", "CLM-PERICARDITIS"),
        ("EDGE-GERD", "SU-G-04", "CLM-GERD"),
    ]
    edges = []
    for edge_id, contrast_id, claim_id in concepts:
        edge = {
            "contrast_id": edge_id,
            "anchor_concept_id": "CONCEPT-ACS",
            "contrast_concept_id": f"CONCEPT-{contrast_id}",
            "anchor": _provenance("SU-C-21"),
            "contrast": _provenance(contrast_id),
            "decision_context": "DIAGNOSIS_DIFFERENTIAL",
            "applicable_learner_decisions": ["Differentiate ACS from other dangerous chest-pain causes."],
            "shared_features": ["acute chest discomfort", "potentially serious presentation"],
            "plausible_error": "A partially knowledgeable graduate overweights an overlapping feature.",
            "neighboring_choice": "A competing diagnosis in the same chest-pain decision.",
            "decisive_discriminant": "The scenario-specific key feature makes this competitor inferior.",
            "evidence_refs": [{"claim_id": claim_id, "claim_sha256": claim_hashes[claim_id]}],
            "quality_status": "VALIDATED",
            "reviewer_id": "contrast-reviewer",
            "excluded_contexts": ["Use when the stem lacks the shared feature."],
        }
        edge["content_sha256"] = _sha({k: v for k, v in edge.items() if k != "content_sha256"})
        edges.append(edge)
    return {
        "schema_version": "1.0",
        "scope": "CHAPTER_GLOBAL_CONTRAST_LIBRARY",
        "retrieval_policy": "HYBRID_CACHE_FIRST_SEMANTIC_SECOND_EVIDENCE_THIRD",
        "edges": edges,
    }


def _anchor() -> dict:
    return resolve_chapter_anchor(
        REPO,
        "SU-C-21",
        "14",
        "Assessment/Diagnosis",
        "Differentiate ACS from other dangerous chest-pain causes.",
    )


def _staged_item(
    evidence: dict | None = None,
    library: dict | None = None,
    *,
    item_id: str = "CHREV-C-ACS-001",
    item_type: str = "DIAGNOSIS_DIFFERENTIAL",
) -> dict:
    evidence = evidence or _evidence()
    library = library or _library(evidence)
    anchor = _anchor()
    author_id = "item-author"
    anchor_review = {
        "reviewer_id": "anchor-reviewer",
        "anchor_sha256": _sha(anchor),
        "criteria": {
            "decision_ownership": "PASS",
            "key_ownership": "PASS",
            "positive_anchor_evidence": "PASS",
            "immediate_review_fit": "PASS",
            "counterfactual_necessity": "PASS",
            "contrast_role_integrity": "PASS",
            "allocation_integrity": "PASS",
        },
        "verdict": "PASS",
    }
    open_ended = {
        "anchor_fidelity_sha256": _sha(anchor_review),
        "context": "A medically necessary chest-pain presentation with decisive ischemic features.",
        "stem": "A patient has acute central chest pressure with diaphoresis and a new regional ischemic ECG change.",
        "lead_in": "What is the most likely diagnosis?",
        "intended_answer": "Acute coronary syndrome",
        "reasoning_chain": [
            "Recognize a time-sensitive ischemic presentation.",
            "Use the regional ischemic ECG change to favour ACS over global chest-pain alternatives.",
        ],
        "context_necessity": {
            "context_type": "PATIENT_PRESENTATION",
            "answerable_after_context_ablation": False,
            "explanation": "Removing the ischemic presentation removes the decision.",
        },
        "key_evidence_refs": ["CLM-KEY"],
    }
    blind = {
        "solver_id": "blind-solver",
        "open_ended_sha256": _sha(open_ended),
        "hidden_context": ["intended_answer", "contrast_candidates", "answer_options", "author_self_evaluation"],
        "independent_answer": "Acute coronary syndrome",
        "independent_reasoning": "The regional ischemic pattern in an acute chest-pain syndrome supports ACS.",
        "verdict": "PASS",
    }
    retrieval = {
        "blind_solver_sha256": _sha(blind),
        "strategy": "HYBRID_CACHE_FIRST_SEMANTIC_SECOND_EVIDENCE_THIRD",
        "complete_tn_corpus": True,
        "learner_progress_used": False,
        "lexical_similarity_only": False,
        "selected_contrast_ids": [edge["contrast_id"] for edge in library["edges"]],
        "cache_hits_first": [edge["contrast_id"] for edge in library["edges"]],
        "semantic_ranker_id": "semantic-ranker",
    }
    competitors = []
    option_text = {
        "EDGE-PE": "Pulmonary embolism",
        "EDGE-AORTA": "Acute aortic dissection",
        "EDGE-PERICARDITIS": "Acute pericarditis",
        "EDGE-GERD": "Gastroesophageal reflux disease",
    }
    for edge in library["edges"]:
        competitors.append({
            "contrast_id": edge["contrast_id"],
            "contrast_concept": option_text[edge["contrast_id"]],
            "tn_provenance": edge["contrast"],
            "why_plausible": edge["plausible_error"],
            "shared_features": edge["shared_features"],
            "partial_mistaken_reasoning": edge["plausible_error"],
            "decisive_discriminant": edge["decisive_discriminant"],
            "authoritative_evidence_refs": [ref["claim_id"] for ref in edge["evidence_refs"]],
            "ambiguity_verdict": "KEY_REMAINS_SINGLE_BEST",
            "target_drift": "ABSENT",
            "status": "VALIDATED",
        })
    matrix = {
        "retrieval_sha256": _sha(retrieval),
        "key": {
            "concept": "Acute coronary syndrome",
            "anchor_evidence_refs": ["CLM-KEY"],
            "decisive_discriminants": ["Regional ischemic ECG change in an acute ischemic presentation."],
            "tn_alignment": "CURRENT",
        },
        "competitors": competitors,
        "verdict": "PASS",
    }
    distractors = [{
        "contrast_id": row["contrast_id"],
        "competing_concept": row["contrast_concept"],
        "option_text": row["contrast_concept"],
        "why_temporarily_plausible": row["why_plausible"],
        "shared_features": row["shared_features"],
        "disqualifying_discriminant": row["decisive_discriminant"],
        "evidence_refs": row["authoritative_evidence_refs"],
    } for row in competitors]
    construction = {
        "constructor_id": "distractor-constructor",
        "matrix_sha256": _sha(matrix),
        "distractors": distractors,
    }
    adversarial = {
        "reviewer_id": "distractor-reviewer",
        "construction_sha256": _sha(construction),
        "rows": [{
            "contrast_id": row["contrast_id"],
            "assessments": {
                "plausibility": "PASS",
                "same_option_dimension": "PASS",
                "mcc_level_relevance": "PASS",
                "medical_professional_confusability": "PASS",
                "no_key_ambiguity": "PASS",
                "evidence_grounded_discriminator": "PASS",
            },
            "verdict": "PASS",
        } for row in competitors],
        "verdict": "PASS",
    }
    key_position = {
        "DIAGNOSIS_DIFFERENTIAL": 0,
        "INVESTIGATION_INTERPRETATION": 1,
        "MANAGEMENT_NEXT_BEST_STEP": 2,
    }[item_type]
    raw_options = [{"text": row["option_text"], "role": "DISTRACTOR", "contrast_id": row["contrast_id"]} for row in distractors]
    raw_options.insert(key_position, {"text": "Acute coronary syndrome", "role": "KEY"})
    options = [{"key": key, **row} for key, row in zip("ABCDE", raw_options, strict=True)]
    assembly = {
        "assembler_id": "assembler",
        "adversarial_review_sha256": _sha(adversarial),
        "approved_component_sha256": {
            "open_ended": _sha(open_ended),
            "key": _sha(matrix["key"]),
            "distractors": _sha(distractors),
        },
        "stem": open_ended["stem"],
        "lead_in": open_ended["lead_in"],
        "options": options,
        "correct_answer": options[key_position]["key"],
        "rewrite_status": "COMPONENTS_UNCHANGED",
    }
    acceptance = {
        "reviewer_id": "acceptance-reviewer",
        "assembly_sha256": _sha(assembly),
        "checks": {
            "cover_the_options": "PASS",
            "option_only_cues": "PASS",
            "clang_keyword": "PASS",
            "option_homogeneity": "PASS",
            "answer_length_specificity": "PASS",
            "plan_fidelity": "PASS",
            "anchor_fidelity": "PASS",
            "context_necessity": "PASS",
        },
        "verdict": "PASS",
    }
    rationales = {
        "acceptance_sha256": _sha(acceptance),
        "correct": {
            "why_best": open_ended["reasoning_chain"][-1],
            "decisive_evidence": matrix["key"]["decisive_discriminants"],
            "decisive_discriminants": matrix["key"]["decisive_discriminants"],
            "anchor_tn_topic_pages": "Acute Coronary Syndromes, C30-C39",
            "evidence_refs": ["CLM-KEY"],
        },
        "distractors": [{
            "contrast_id": row["contrast_id"],
            "why_plausible": row["why_temporarily_plausible"],
            "exact_discriminator": row["disqualifying_discriminant"],
            "evidence_refs": row["evidence_refs"],
        } for row in distractors],
        "unsupported_new_teaching_facts": False,
    }
    return {
        "schema_version": "1.0",
        "item_id": item_id,
        "learning_mode": "CHAPTER_REVIEW",
        "item_type": item_type,
        "author_id": author_id,
        "stage_sequence": STAGES,
        "anchor": anchor,
        "anchor_fidelity_preflight": anchor_review,
        "open_ended_stem_key": open_ended,
        "blind_solver": blind,
        "global_contrast_retrieval": retrieval,
        "contrastive_evidence_matrix": matrix,
        "distractor_construction": construction,
        "distractor_adversarial_review": adversarial,
        "assembly": assembly,
        "acceptance_review": acceptance,
        "rationales": rationales,
        "semantic_fingerprint": _sha({
            "item_type": item_type,
            "decision": anchor["primary_learner_decision"],
            "stem": assembly["stem"],
            "lead_in": assembly["lead_in"],
            "answer": next(option["text"] for option in assembly["options"] if option["role"] == "KEY"),
        }),
    }


def _verification(staged: dict) -> dict:
    rows = []
    for item in staged["items"]:
        rows.append({
            "item_id": item["item_id"],
            "dimensions": {
                "factual_correctness": "PASS",
                "evidence_support": "PASS",
                "single_best_answer": "PASS",
                "mcc_objective_level": "PASS",
                "anchor_fidelity": "PASS",
                "plan_fidelity": "PASS",
                "reasoning_quality": "PASS",
                "stem_lead_in_quality": "PASS",
                "context_necessity": "PASS",
                "distractor_plausibility": "PASS",
                "cross_chapter_contrast_quality": "PASS",
                "rationale_quality": "PASS",
                "item_writing_flaws": "PASS",
                "cueing": "PASS",
                "duplication": "PASS",
            },
            "verdict": "PASS",
            "root_cause": None,
        })
    return {
        "schema_version": "1.0",
        "scope": "CHAPTER_REVIEW_MICRO_INDEPENDENT_VERIFICATION",
        "verifier_id": "fresh-independent-verifier",
        "included_context": ["staged items", "targeted evidence", "contrast library", "quality rubric"],
        "excluded_context": ["author deliberation", "author self-evaluation"],
        "staged_artifact_sha256": _sha(staged),
        "evidence_traceability": "PASS",
        "independent_context": "PASS",
        "verdicts": rows,
        "defect_counts": {key: 0 for key in sorted(DEFECTS)},
        "micro_pilot_assessment": "SUCCESS",
    }


def _upgrade_to_schema_1_1(item: dict) -> dict:
    item = deepcopy(item)
    item["schema_version"] = "1.1"
    item["stage_sequence"] = STAGES_V2
    dimension = {
        "DIAGNOSIS_DIFFERENTIAL": "DIAGNOSIS",
        "INVESTIGATION_INTERPRETATION": "DIAGNOSTIC_APPROACH",
        "MANAGEMENT_NEXT_BEST_STEP": "MANAGEMENT_ACTION",
    }[item["item_type"]]
    grammatical_form = "NOUN_PHRASE" if dimension == "DIAGNOSIS" else "IMPERATIVE_ACTION"
    semantic_distractors = {
        row["contrast_id"]: row for row in item["distractor_construction"]["distractors"]
    }
    realized_options = []
    for option in item["assembly"]["options"]:
        if option["role"] == "KEY":
            semantic_text = item["open_ended_stem_key"]["intended_answer"]
            evidence_refs = item["contrastive_evidence_matrix"]["key"]["anchor_evidence_refs"]
        else:
            semantic = semantic_distractors[option["contrast_id"]]
            semantic_text = semantic["option_text"]
            evidence_refs = semantic["evidence_refs"]
        realized_options.append({
            "position": option["key"],
            "role": option["role"],
            **({"contrast_id": option["contrast_id"]} if option["role"] == "DISTRACTOR" else {}),
            "semantic_option_text": semantic_text,
            "surface_text": option["text"],
            "option_dimension": dimension,
            "grammatical_form": grammatical_form,
            "meaning_preservation": "PASS",
            "evidence_refs": evidence_refs,
        })
    realization = {
        "realizer_id": "option-realizer",
        "adversarial_review_sha256": _sha(item["distractor_adversarial_review"]),
        "policy": "SEMANTIC_TO_CONCISE_NATURAL_PARALLEL_SURFACE",
        "options": realized_options,
    }
    review = {
        "reviewer_id": "parallel-option-reviewer",
        "realization_sha256": _sha(realization),
        "deterministic_findings": [],
        "semantic_checks": {name: "PASS" for name in sorted(SEMANTIC_CUE_CHECKS)},
        "option_only_key_identifiable": False,
        "verdict": "PASS",
    }
    item["option_realization"] = realization
    item["parallel_option_set_review"] = review
    assembly = item["assembly"]
    assembly.pop("adversarial_review_sha256")
    assembly["parallel_option_set_review_sha256"] = _sha(review)
    assembly["approved_component_sha256"] = {
        "open_ended": _sha(item["open_ended_stem_key"]),
        "option_realization": _sha(realization),
        "parallel_option_set_review": _sha(review),
    }
    assembly["rewrite_status"] = "SURFACE_REALIZATION_ONLY"
    item["acceptance_review"]["assembly_sha256"] = _sha(assembly)
    item["rationales"]["acceptance_sha256"] = _sha(item["acceptance_review"])
    return item


def test_global_index_and_anchor_resolution_join_canonical_lineage():
    index = build_global_study_unit_index(REPO)
    assert len(index) >= 1400
    assert index == sorted(index, key=lambda row: (row["pdf_pages"][0], row["study_unit_id"]))
    assert len({row["study_unit_id"] for row in index}) == len(index)

    anchor = _anchor()
    assert anchor["anchor_chapter_id"] == "C"
    assert anchor["anchor_study_unit_id"] == "SU-C-21"
    assert anchor["anchor_source_node_ids"] == ["C.S06.T02", "C.S06.T03"]
    assert anchor["anchor_tn_pages"] == "C30-C39"
    assert anchor["anchor_pdf_pages"] == [120, 129]
    assert anchor["primary_mcc_objective"] == {"mcc_id": "14", "title": "Chest pain"}


@pytest.mark.parametrize("objective,activity,message", [
    ("NOT-AN-MCC-ID", "Assessment/Diagnosis", "MCC objective"),
    ("14", "Invented Activity", "physician activity"),
])
def test_anchor_resolution_fails_closed_on_noncanonical_ownership(objective, activity, message):
    with pytest.raises(ChapterStagedGenerationError, match=message):
        resolve_chapter_anchor(REPO, "SU-C-21", objective, activity, "Clinical decision")


def test_contrast_library_validates_provenance_evidence_and_cache_first_retrieval():
    evidence = _evidence()
    library = _library(evidence)
    assert validate_contrast_library(REPO, library, evidence) == library
    result = retrieve_global_contrasts(
        REPO,
        "SU-C-21",
        "DIAGNOSIS_DIFFERENTIAL",
        ["SU-R-19", "SU-G-04", "SU-C-33"],
        library,
        evidence,
    )
    assert [row["contrast_id"] for row in result["cached_validated_edges"]] == [
        "EDGE-AORTA", "EDGE-GERD", "EDGE-PE", "EDGE-PERICARDITIS"
    ]
    assert result["semantic_candidates_after_cache"] == []


def test_contrast_library_rejects_stale_evidence_and_lexical_only_edges():
    evidence = _evidence()
    library = _library(evidence)
    stale = deepcopy(library)
    stale["edges"][0]["evidence_refs"][0]["claim_sha256"] = "0" * 64
    stale["edges"][0]["content_sha256"] = _sha({k: v for k, v in stale["edges"][0].items() if k != "content_sha256"})
    with pytest.raises(ChapterStagedGenerationError, match="evidence fingerprint"):
        validate_contrast_library(REPO, stale, evidence)

    lexical = deepcopy(library)
    lexical["edges"][0]["shared_features"] = []
    lexical["edges"][0]["content_sha256"] = _sha({k: v for k, v in lexical["edges"][0].items() if k != "content_sha256"})
    with pytest.raises(ChapterStagedGenerationError, match="clinical confusability"):
        validate_contrast_library(REPO, lexical, evidence)


def test_contrast_library_rejects_changed_source_lineage():
    evidence = _evidence()
    library = _library(evidence)
    evidence["sources"][0]["url"] = "https://example.invalid/replaced-guideline"
    with pytest.raises(ChapterStagedGenerationError, match="source fingerprint"):
        validate_contrast_library(REPO, library, evidence)


def test_contrast_library_allows_distinct_same_unit_management_misconceptions():
    evidence = _evidence()
    library = _library(evidence)
    edge = deepcopy(library["edges"][0])
    edge["contrast_id"] = "EDGE-ACS-DELAY-REPERFUSION"
    edge["contrast_concept_id"] = "CONCEPT-DELAY-REPERFUSION-FOR-TROPONIN"
    edge["contrast"] = deepcopy(edge["anchor"])
    edge["decision_context"] = "MANAGEMENT_NEXT_BEST_STEP"
    edge["content_sha256"] = _sha({k: v for k, v in edge.items() if k != "content_sha256"})
    library["edges"] = [edge]
    assert validate_contrast_library(REPO, library, evidence) == library


def test_staged_item_passes_complete_contract():
    evidence = _evidence()
    library = _library(evidence)
    item = _staged_item(evidence, library)
    assert validate_staged_item(REPO, item, library, evidence) == item


def test_option_shape_rule_detects_uniquely_long_specific_key():
    options = [
        {"role": "KEY", "text": "Repeat the 12-lead ECG during assessment and repeat high-sensitivity troponin in 1 to 2 hours using the local validated pathway"},
        {"role": "DISTRACTOR", "text": "Order a D-dimer and proceed to CTPA if positive"},
        {"role": "DISTRACTOR", "text": "Obtain immediate CT angiography of the aorta"},
        {"role": "DISTRACTOR", "text": "Order inflammatory markers and echocardiography"},
        {"role": "DISTRACTOR", "text": "Arrange immediate upper endoscopy"},
    ]
    assert find_option_shape_cues(options) == ["KEY_UNIQUELY_LONG_AND_SPECIFIC"]


def test_option_text_checks_reject_duplicate_nonparallel_and_key_only_phrase():
    duplicate = [
        {"role": "KEY", "text": "Repeat cardiac testing", "grammatical_form": "IMPERATIVE_ACTION"},
        {"role": "DISTRACTOR", "text": "Repeat cardiac testing", "grammatical_form": "IMPERATIVE_ACTION"},
        {"role": "DISTRACTOR", "text": "Obtain aortic imaging", "grammatical_form": "IMPERATIVE_ACTION"},
    ]
    assert "DUPLICATE_OPTION_TEXT" in find_option_text_cues("A clinical stem.", duplicate)

    nonparallel = deepcopy(duplicate)
    nonparallel[1]["text"] = "Pulmonary embolism"
    nonparallel[1]["grammatical_form"] = "NOUN_PHRASE"
    assert "NONPARALLEL_GRAMMATICAL_FORM" in find_option_text_cues("A clinical stem.", nonparallel)

    key_only_phrase = [
        {"role": "KEY", "text": "Use the locally validated pathway", "grammatical_form": "IMPERATIVE_ACTION"},
        {"role": "DISTRACTOR", "text": "Obtain aortic imaging", "grammatical_form": "IMPERATIVE_ACTION"},
        {"role": "DISTRACTOR", "text": "Arrange reflux monitoring", "grammatical_form": "IMPERATIVE_ACTION"},
    ]
    assert "KEY_ONLY_STEM_PHRASE" in find_option_text_cues(
        "The locally validated pathway is available.", key_only_phrase
    )


def test_option_text_checks_allow_natural_length_variation_and_medical_specificity():
    options = [
        {"role": "KEY", "text": "Repeat ECG and hs-cTn testing in 1–2 hours", "grammatical_form": "IMPERATIVE_ACTION"},
        {"role": "DISTRACTOR", "text": "Use D-dimer testing, with CTPA if indicated", "grammatical_form": "IMPERATIVE_ACTION"},
        {"role": "DISTRACTOR", "text": "Obtain urgent aortic CT angiography", "grammatical_form": "IMPERATIVE_ACTION"},
        {"role": "DISTRACTOR", "text": "Obtain inflammatory markers and echocardiography", "grammatical_form": "IMPERATIVE_ACTION"},
        {"role": "DISTRACTOR", "text": "Arrange upper endoscopy or reflux monitoring", "grammatical_form": "IMPERATIVE_ACTION"},
    ]
    assert find_option_text_cues(
        "The first electrocardiogram and high-sensitivity troponin are nondiagnostic.", options
    ) == []


def test_option_text_checks_allow_repeated_parallel_grammatical_frames():
    options = [
        {"role": "KEY", "text": "Administer oral acetylsalicylic acid", "grammatical_form": "IMPERATIVE_ACTION"},
        {"role": "DISTRACTOR", "text": "Administer oral clopidogrel", "grammatical_form": "IMPERATIVE_ACTION"},
        {"role": "DISTRACTOR", "text": "Administer oral rivaroxaban", "grammatical_form": "IMPERATIVE_ACTION"},
        {"role": "DISTRACTOR", "text": "Administer intravenous alteplase", "grammatical_form": "IMPERATIVE_ACTION"},
    ]
    assert find_option_text_cues("Select the most appropriate medication.", options) == []


def test_decision_granularity_gate_rejects_key_only_management_bundle():
    options = [
        {"role": "KEY", "decision_granularity": "SINGLE_NEXT_ACTION", "independent_action_components": ["fibrinolysis", "pci_transfer", "angiography"]},
        {"role": "DISTRACTOR", "decision_granularity": "SINGLE_NEXT_ACTION", "independent_action_components": ["primary_pci"]},
        {"role": "DISTRACTOR", "decision_granularity": "SINGLE_NEXT_ACTION", "independent_action_components": ["fibrinolysis"]},
        {"role": "DISTRACTOR", "decision_granularity": "SINGLE_NEXT_ACTION", "independent_action_components": ["biomarker_testing"]},
        {"role": "DISTRACTOR", "decision_granularity": "SINGLE_NEXT_ACTION", "independent_action_components": ["aortic_imaging"]},
    ]
    assert "KEY_ONLY_COMPLETENESS" in find_decision_granularity_cues(options)


def test_decision_granularity_gate_rejects_convergent_partial_distractors():
    options = [
        {"role": "DISTRACTOR", "decision_granularity": "MANAGEMENT_STRATEGY", "independent_action_components": ["lysis"]},
        {"role": "DISTRACTOR", "decision_granularity": "MANAGEMENT_STRATEGY", "independent_action_components": ["transfer"]},
        {"role": "DISTRACTOR", "decision_granularity": "MANAGEMENT_STRATEGY", "independent_action_components": ["angiography"]},
        {"role": "KEY", "decision_granularity": "MANAGEMENT_STRATEGY", "independent_action_components": ["lysis", "transfer", "angiography"]},
        {"role": "DISTRACTOR", "decision_granularity": "MANAGEMENT_STRATEGY", "independent_action_components": ["anti_impulse"]},
    ]
    assert "CONCEPTUAL_CONVERGENCE" in find_decision_granularity_cues(options)


def test_decision_granularity_gate_rejects_mixed_levels_and_specific_diagnosis():
    mixed = [
        {"role": "KEY", "decision_granularity": "DIAGNOSTIC_TEST", "independent_action_components": ["serial_ecg"]},
        {"role": "DISTRACTOR", "decision_granularity": "MANAGEMENT_STRATEGY", "independent_action_components": ["primary_pci"]},
    ]
    diagnoses = [
        {"role": "KEY", "decision_granularity": "DIAGNOSIS", "specificity_level": 4, "independent_action_components": []},
        {"role": "DISTRACTOR", "decision_granularity": "DIAGNOSIS", "specificity_level": 1, "independent_action_components": []},
        {"role": "DISTRACTOR", "decision_granularity": "DIAGNOSIS", "specificity_level": 1, "independent_action_components": []},
    ]
    assert "DECISION_GRANULARITY_PARITY" in find_decision_granularity_cues(mixed)
    assert "KEY_ONLY_DIAGNOSTIC_SPECIFICITY" in find_decision_granularity_cues(diagnoses)


def test_decision_granularity_gate_allows_natural_precision_and_comparable_actions():
    strategies = [
        {"role": "KEY", "decision_granularity": "MANAGEMENT_STRATEGY", "independent_action_components": ["pharmacoinvasive_strategy"]},
        {"role": "DISTRACTOR", "decision_granularity": "MANAGEMENT_STRATEGY", "independent_action_components": ["delayed_primary_pci"]},
        {"role": "DISTRACTOR", "decision_granularity": "MANAGEMENT_STRATEGY", "independent_action_components": ["rescue_only_strategy"]},
        {"role": "DISTRACTOR", "decision_granularity": "MANAGEMENT_STRATEGY", "independent_action_components": ["biomarker_delay"]},
        {"role": "DISTRACTOR", "decision_granularity": "MANAGEMENT_STRATEGY", "independent_action_components": ["anti_impulse_strategy"]},
    ]
    actions = [
        {"role": "KEY", "decision_granularity": "SINGLE_NEXT_ACTION", "independent_action_components": ["serial_ecg"]},
        {"role": "DISTRACTOR", "decision_granularity": "SINGLE_NEXT_ACTION", "independent_action_components": ["d_dimer"]},
        {"role": "DISTRACTOR", "decision_granularity": "SINGLE_NEXT_ACTION", "independent_action_components": ["aortic_cta"]},
        {"role": "DISTRACTOR", "decision_granularity": "SINGLE_NEXT_ACTION", "independent_action_components": ["echocardiography"]},
    ]
    assert find_decision_granularity_cues(strategies) == []
    assert find_decision_granularity_cues(actions) == []


def test_schema_1_1_option_realization_accepts_strong_cross_chapter_options():
    evidence = _evidence()
    library = _library(evidence)
    item = _upgrade_to_schema_1_1(_staged_item(evidence, library))
    assert validate_staged_item(REPO, item, library, evidence) == item


@pytest.mark.parametrize(("mutate", "message"), [
    (
        lambda item: item["option_realization"]["options"][1].__setitem__("option_dimension", "DIAGNOSIS"),
        "option dimension",
    ),
    (
        lambda item: item["option_realization"]["options"][1].__setitem__("grammatical_form", "NOUN_PHRASE"),
        "grammatical form",
    ),
    (
        lambda item: item["parallel_option_set_review"]["semantic_checks"].__setitem__("convergence", "FAIL"),
        "semantic cue review",
    ),
])
def test_schema_1_1_option_realization_fails_closed(mutate, message):
    evidence = _evidence()
    library = _library(evidence)
    item = _upgrade_to_schema_1_1(
        _staged_item(
            evidence,
            library,
            item_type="INVESTIGATION_INTERPRETATION",
        )
    )
    mutate(item)
    with pytest.raises(ChapterStagedGenerationError, match=message):
        validate_staged_item(REPO, item, library, evidence)


def test_position_rule_detects_unbalanced_micro_batch():
    items = [{"assembly": {"correct_answer": "A"}} for _ in range(3)]
    assert find_option_position_cues(items) == ["CORRECT_POSITION_REPEATED_ACROSS_ENTIRE_BATCH"]
    partly_repeated = [{"assembly": {"correct_answer": key}} for key in ["A", "A", "B"]]
    assert find_option_position_cues(partly_repeated) == ["CORRECT_POSITIONS_NOT_BALANCED"]


@pytest.mark.parametrize("mutate,message", [
    (lambda value: value["contrastive_evidence_matrix"].__setitem__("competitors", value["contrastive_evidence_matrix"]["competitors"][:2]), "three validated competitors"),
    (lambda value: value["blind_solver"]["hidden_context"].remove("intended_answer"), "blind solver hidden context"),
    (lambda value: value["global_contrast_retrieval"].__setitem__("lexical_similarity_only", True), "lexical similarity"),
    (lambda value: value["distractor_construction"]["distractors"][0].__setitem__("contrast_id", "UNVALIDATED"), "validated contrast"),
    (lambda value: value["distractor_adversarial_review"]["rows"][0]["assessments"].__setitem__("plausibility", "FAIL"), "adversarial review"),
    (lambda value: value["assembly"].__setitem__("stem", "Materially rewritten stem."), "approved stem"),
    (lambda value: value["acceptance_review"]["checks"].__setitem__("plan_fidelity", "FAIL"), "acceptance checks"),
    (lambda value: value["rationales"].__setitem__("unsupported_new_teaching_facts", True), "unsupported teaching"),
    (lambda value: value["rationales"]["correct"].__setitem__("evidence_refs", ["CLM-PE"]), "correct rationale lineage"),
    (lambda value: value["rationales"]["correct"].__setitem__("why_best", "Unbound post-hoc teaching claim."), "correct rationale lineage"),
    (lambda value: value["rationales"]["correct"].__setitem__("decisive_evidence", ["Unbound assertion."]), "correct rationale lineage"),
    (lambda value: value["rationales"]["distractors"][0].__setitem__("exact_discriminator", "Unbound post-hoc assertion."), "distractor rationale lineage"),
])
def test_staged_item_fails_closed_on_flattening_and_quality_regressions(mutate, message):
    evidence = _evidence()
    library = _library(evidence)
    item = _staged_item(evidence, library)
    mutate(item)
    with pytest.raises(ChapterStagedGenerationError, match=message):
        validate_staged_item(REPO, item, library, evidence)


def test_micro_gate_requires_exact_item_mix_three_passes_and_zero_defects():
    evidence = _evidence()
    library = _library(evidence)
    items = [
        _staged_item(evidence, library, item_id="CHREV-C-ACS-001", item_type="DIAGNOSIS_DIFFERENTIAL"),
        _staged_item(evidence, library, item_id="CHREV-C-ACS-002", item_type="INVESTIGATION_INTERPRETATION"),
        _staged_item(evidence, library, item_id="CHREV-C-ACS-003", item_type="MANAGEMENT_NEXT_BEST_STEP"),
    ]
    staged = {
        "schema_version": "1.0",
        "scope": "CHAPTER_REVIEW_CLINICAL_MICRO_3",
        "pilot_id": "QGEN-MED-007-CHAPTER-REVIEW-MICRO-3",
        "micro_chapter": "Cardiology and Cardiac Surgery",
        "anchor_chapter_id": "C",
        "anchor_study_unit_id": "SU-C-21",
        "items": items,
    }
    verification = _verification(staged)
    result = validate_micro_pilot(REPO, staged, library, evidence, verification)
    assert result["micro_items_generated"] == 3
    assert result["micro_items_passed"] == 3
    assert result["defect_counts"] == {key: 0 for key in sorted(DEFECTS)}

    failed = deepcopy(verification)
    failed["defect_counts"]["WEAK_DISTRACTOR"] = 1
    failed["verdicts"][0]["dimensions"]["distractor_plausibility"] = "FAIL"
    failed["verdicts"][0]["verdict"] = "FAIL"
    failed["verdicts"][0]["root_cause"] = "One competitor was not plausible in the stated context."
    failed["micro_pilot_assessment"] = "FAILURE"
    with pytest.raises(ChapterStagedGenerationError, match="micro success gate"):
        validate_micro_pilot(REPO, staged, library, evidence, failed)


@pytest.mark.parametrize(("field", "value"), [
    ("candidate_status", "REJECTED_BY_FRESH_OPTION_CUE_REVIEW"),
    ("provisional_parallel_option_review", True),
])
def test_micro_success_gate_rejects_rejected_or_provisional_candidates(field, value):
    evidence = _evidence()
    library = _library(evidence)
    staged = {
        "schema_version": "1.0",
        "scope": "CHAPTER_REVIEW_CLINICAL_MICRO_3",
        "pilot_id": "QGEN-MED-007-CHAPTER-REVIEW-MICRO-3",
        "micro_chapter": "Cardiology and Cardiac Surgery",
        "anchor_chapter_id": "C",
        "anchor_study_unit_id": "SU-C-21",
        "items": [
            _staged_item(evidence, library, item_id="CHREV-C-ACS-001", item_type="DIAGNOSIS_DIFFERENTIAL"),
            _staged_item(evidence, library, item_id="CHREV-C-ACS-002", item_type="INVESTIGATION_INTERPRETATION"),
            _staged_item(evidence, library, item_id="CHREV-C-ACS-003", item_type="MANAGEMENT_NEXT_BEST_STEP"),
        ],
        field: value,
    }
    with pytest.raises(ChapterStagedGenerationError, match="rejected or provisional"):
        validate_micro_pilot(REPO, staged, library, evidence, _verification(staged))


@pytest.mark.parametrize("role", ["realizer_id", "reviewer_id"])
def test_micro_success_gate_requires_verifier_fresh_from_option_realization_roles(role):
    evidence = _evidence()
    library = _library(evidence)
    items = [
        _upgrade_to_schema_1_1(_staged_item(evidence, library, item_id="CHREV-C-ACS-001", item_type="DIAGNOSIS_DIFFERENTIAL")),
        _upgrade_to_schema_1_1(_staged_item(evidence, library, item_id="CHREV-C-ACS-002", item_type="INVESTIGATION_INTERPRETATION")),
        _upgrade_to_schema_1_1(_staged_item(evidence, library, item_id="CHREV-C-ACS-003", item_type="MANAGEMENT_NEXT_BEST_STEP")),
    ]
    staged = {
        "schema_version": "1.1",
        "scope": "CHAPTER_REVIEW_CLINICAL_MICRO_3",
        "pilot_id": "QGEN-MED-007-CHAPTER-REVIEW-MICRO-3-OPTION-REALIZATION",
        "micro_chapter": "Cardiology and Cardiac Surgery",
        "anchor_chapter_id": "C",
        "anchor_study_unit_id": "SU-C-21",
        "items": items,
    }
    verification = _verification(staged)
    source = items[0]["option_realization"] if role == "realizer_id" else items[0]["parallel_option_set_review"]
    verification["verifier_id"] = source[role]
    with pytest.raises(ChapterStagedGenerationError, match="prior generation role"):
        validate_micro_pilot(REPO, staged, library, evidence, verification)


def test_committed_acs_micro_pilot_records_fail_closed_adversarial_gate():
    evidence_path = REPO / "research/qgen/pilot/QGEN-MED-007.chapter-review-micro-3.evidence.json"
    library_path = REPO / "research/qgen/chapter_global_contrast_library.json"
    staged_path = REPO / "research/qgen/pilot/QGEN-MED-007.chapter-review-micro-3.staged.json"
    review_path = REPO / "reports/qgen_med_007_chapter_review_micro_3_adversarial_review.json"
    for path in (evidence_path, library_path, staged_path, review_path):
        assert path.is_file(), path
    evidence = json.loads(evidence_path.read_text())
    library = json.loads(library_path.read_text())
    staged = json.loads(staged_path.read_text())
    review = json.loads(review_path.read_text())

    assert validate_contrast_library(REPO, library, evidence) == library
    assert validate_staged_item(REPO, staged["items"][0], library, evidence) == staged["items"][0]
    for item in staged["items"][1:]:
        with pytest.raises(ChapterStagedGenerationError, match="option-shape cue"):
            validate_staged_item(REPO, item, library, evidence)
    assert review["staged_artifact_sha256"] == canonical_sha256(staged)
    assert review["contrast_library_sha256"] == canonical_sha256(library)
    assert review["evidence_packet_sha256"] == canonical_sha256(evidence)
    assert review["micro_items_generated"] == 3
    assert review["micro_items_passed"] == 1
    assert review["defect_counts"]["OPTION_CUE_FAILURE"] == 3
    assert review["micro_pilot_assessment"] == "FAILURE"
    assert review["next_step"] == "DIAGNOSE_MICRO_FAILURE"
    assert review["regeneration_attempted"] is False
    result = validate_micro_failure_review(REPO, staged, library, evidence, review)
    assert result["micro_items_generated"] == 3
    assert result["micro_items_passed"] == 1
    assert result["defect_counts"]["OPTION_CUE_FAILURE"] == 3


def test_committed_option_retry_records_fresh_cue_gate_failure_without_overwrite():
    evidence_path = REPO / "research/qgen/pilot/QGEN-MED-007.chapter-review-micro-3.evidence.json"
    library_path = REPO / "research/qgen/chapter_global_contrast_library.json"
    staged_path = REPO / "research/qgen/pilot/QGEN-MED-007.chapter-review-micro-3.option-retry-1.staged.json"
    cue_review_path = REPO / "reports/qgen_med_007_chapter_review_micro_3_option_retry_1_cue_review.json"
    prior_staged_path = REPO / "research/qgen/pilot/QGEN-MED-007.chapter-review-micro-3.staged.json"
    for path in (evidence_path, library_path, staged_path, cue_review_path, prior_staged_path):
        assert path.is_file(), path

    staged = json.loads(staged_path.read_text())
    cue_review = json.loads(cue_review_path.read_text())
    prior_staged = json.loads(prior_staged_path.read_text())
    assert all(item["schema_version"] == "1.1" for item in staged["items"])
    assert staged["candidate_status"] == "REJECTED_BY_FRESH_OPTION_CUE_REVIEW"
    assert staged["provisional_parallel_option_review"] is True
    assert staged["derivative_lineage"]["parent_artifact_sha256"] == canonical_sha256(prior_staged)
    assert find_option_position_cues(staged["items"]) == []
    assert cue_review["staged_artifact_sha256"] == canonical_sha256(staged)
    assert validate_option_cue_review(staged, cue_review) == {
        "micro_items_generated": 3,
        "micro_items_passed": 2,
        "material_cue_findings": 2,
        "false_positive_cue_findings": 2,
        "verdict": "FAIL",
    }
    assert cue_review["fresh_independent_verification_run"] is False
    assert cue_review["regeneration_attempted_after_failure"] is False
    assert cue_review["next_step"] == "DIAGNOSE_REMAINING_MICRO_FAILURE"


@pytest.mark.parametrize(("mutate", "message"), [
    (
        lambda staged, review: review.__setitem__("staged_artifact_sha256", "0" * 64),
        "lineage",
    ),
    (
        lambda staged, review: review.__setitem__("reviewer_id", staged["items"][0]["author_id"]),
        "fresh reviewer",
    ),
    (
        lambda staged, review: review.__setitem__(
            "reviewer_id", staged["items"][0]["anchor_fidelity_preflight"]["reviewer_id"]
        ),
        "fresh reviewer",
    ),
    (
        lambda staged, review: review.__setitem__("material_cue_findings", 0),
        "counts",
    ),
])
def test_option_cue_review_fails_closed_on_forged_lineage_reviewer_or_counts(mutate, message):
    staged = json.loads((
        REPO / "research/qgen/pilot/QGEN-MED-007.chapter-review-micro-3.option-retry-1.staged.json"
    ).read_text())
    review = json.loads((
        REPO / "reports/qgen_med_007_chapter_review_micro_3_option_retry_1_cue_review.json"
    ).read_text())
    mutate(staged, review)
    with pytest.raises(ChapterStagedGenerationError, match=message):
        validate_option_cue_review(staged, review)


def test_option_cue_review_reconciles_verdict_with_candidate_status():
    staged = json.loads((
        REPO / "research/qgen/pilot/QGEN-MED-007.chapter-review-micro-3.option-retry-1.staged.json"
    ).read_text())
    review = json.loads((
        REPO / "reports/qgen_med_007_chapter_review_micro_3_option_retry_1_cue_review.json"
    ).read_text())

    failed_as_accepted = deepcopy(staged)
    failed_as_accepted["candidate_status"] = "ACCEPTED"
    failed_as_accepted["provisional_parallel_option_review"] = False
    failed_review = deepcopy(review)
    failed_review["staged_artifact_sha256"] = canonical_sha256(failed_as_accepted)
    with pytest.raises(ChapterStagedGenerationError, match="candidate status"):
        validate_option_cue_review(failed_as_accepted, failed_review)

    passed_as_rejected = deepcopy(staged)
    passed_review = deepcopy(review)
    passed_review["items"][2]["verdict"] = "PASS"
    passed_review["items"][2]["real_findings"] = []
    passed_review["micro_items_passed"] = 3
    passed_review["material_cue_findings"] = 0
    passed_review["verdict"] = "PASS"
    passed_review["staged_artifact_sha256"] = canonical_sha256(passed_as_rejected)
    with pytest.raises(ChapterStagedGenerationError, match="candidate status"):
        validate_option_cue_review(passed_as_rejected, passed_review)


STAGES_V3 = STAGES_V2[:12] + ["DECISION_GRANULARITY_PARITY"] + STAGES_V2[12:]
STAGES_V4 = (
    STAGES_V3[:8]
    + ["CONTEXTUAL_COMPETITOR_PROOF"]
    + STAGES_V3[8:10]
    + ["SEMANTIC_POLARITY_COMPLETENESS_PREFLIGHT"]
    + STAGES_V3[10:]
)
STEM_SUPPORT = "acute central chest pressure"
STEM_DEFEAT = "new regional ischemic ECG change"


def _semantic_option(role: str, text: str, **overrides) -> dict:
    """An abstracted semantic option record for the preflight gate."""
    row = {
        "role": role,
        "semantic_option_text": text,
        "semantic_polarity": "AFFIRMATIVE_ACTION",
        "polarity_rationale": "Declared after reading the option against the stem.",
        "strategy_completeness": "COMPLETE_STRATEGY",
        "decision_scope": "IMMEDIATE_CLINICAL_DECISION",
        "decision_granularity": "SINGLE_NEXT_ACTION",
        "specificity_level": 2,
        "independent_action_components": ["primary-action"],
        "action_or_concept_head": text.split()[0].lower(),
        "medically_required_modifiers": [],
    }
    row.update(overrides)
    return row


def _upgrade_to_schema_1_3(item: dict) -> dict:
    """Add the contextual competitor proof and semantic polarity preflight stages."""
    item = _upgrade_to_schema_1_1(item)
    item["schema_version"] = "1.3"
    item["stage_sequence"] = STAGES_V4
    anchor = item["anchor"]
    matrix = item["contrastive_evidence_matrix"]
    key_refs = matrix["key"]["anchor_evidence_refs"]

    proofs = []
    for index, row in enumerate(matrix["competitors"]):
        competitor_refs = [
            ref for ref in row["authoritative_evidence_refs"] if ref not in key_refs
        ]
        proofs.append({
            "contrast_id": row["contrast_id"],
            "competitor_concept_id": f"CONCEPT-{row['contrast_id']}",
            "anchor_concept_id": "CONCEPT-ACS",
            "learner_decision": anchor["primary_learner_decision"],
            "option_dimension": "DIAGNOSIS",
            "decision_granularity": "DIAGNOSIS",
            "why_plausible_in_this_specific_context": (
                f"This stem's {STEM_SUPPORT} is genuinely compatible with {row['contrast_concept']}."
            ),
            "supporting_stem_features": [
                {"feature": "acute-chest-pressure", "polarity": "PRESENT", "stem_quote": STEM_SUPPORT},
            ],
            "plausible_partial_reasoning": (
                "A candidate who stops at the presenting symptom selects this competitor."
            ),
            "decisive_discriminator": (
                f"The {STEM_DEFEAT} is not expected in {row['contrast_concept']}."
            ),
            "defeating_stem_features": [
                {"feature": "regional-ischemic-ecg", "polarity": "PRESENT", "stem_quote": STEM_DEFEAT},
            ],
            "evidence_refs_for_plausibility": competitor_refs,
            "evidence_refs_for_discriminator": competitor_refs,
            "same_decision_alternative": True,
            "polarity_parallel": True,
            "completeness_parallel": True,
            "competitor_status": "VALIDATED",
            "adversarial_hidden_key_test": {
                "reviewer_id": "adversarial-competitor-reviewer",
                "could_reasonably_select": True,
                "selection_reasoning": (
                    "With the key hidden, this competitor explains the presenting complaint."
                ),
                "defeating_feature": "regional-ischemic-ecg",
                "verdict": "PASS",
            },
        })
    competitor_proof = {
        "reviewer_id": "contextual-competitor-prover",
        "matrix_sha256": _sha(matrix),
        "proofs": proofs,
        "verdict": "PASS",
    }
    item["contextual_competitor_proof"] = competitor_proof

    proofs_by_id = {row["contrast_id"]: row for row in proofs}
    for distractor in item["distractor_construction"]["distractors"]:
        proof = proofs_by_id[distractor["contrast_id"]]
        distractor["why_temporarily_plausible"] = proof["why_plausible_in_this_specific_context"]
        distractor["disqualifying_discriminant"] = proof["decisive_discriminator"]
        distractor["evidence_refs"] = sorted(
            set(proof["evidence_refs_for_plausibility"])
            | set(proof["evidence_refs_for_discriminator"])
        )
    construction = item["distractor_construction"]
    adversarial = item["distractor_adversarial_review"]
    adversarial["construction_sha256"] = _sha(construction)

    preflight_options = []
    for option in item["option_realization"]["options"]:
        preflight_options.append(_semantic_option(
            option["role"],
            option["semantic_option_text"],
            decision_granularity="DIAGNOSIS",
            decision_scope="CHEST_PAIN_DIAGNOSTIC_DECISION",
            independent_action_components=[option["semantic_option_text"]],
            action_or_concept_head=option["semantic_option_text"],
            **({"contrast_id": option["contrast_id"]} if option["role"] == "DISTRACTOR" else {}),
        ))
    preflight = {
        "reviewer_id": "polarity-completeness-reviewer",
        "adversarial_review_sha256": _sha(adversarial),
        "options": preflight_options,
        "deterministic_findings": [],
        "key_identifiable_without_medical_reasoning": False,
        "verdict": "PASS",
    }
    item["semantic_polarity_completeness_preflight"] = preflight

    realization = item["option_realization"]
    realization["adversarial_review_sha256"] = _sha(adversarial)
    for option in realization["options"]:
        if option["role"] == "DISTRACTOR":
            option["evidence_refs"] = next(
                row["evidence_refs"]
                for row in construction["distractors"]
                if row["contrast_id"] == option["contrast_id"]
            )
        option["decision_granularity"] = "DIAGNOSIS"
        option["action_or_concept_head"] = option["semantic_option_text"]
        option["medically_required_modifiers"] = []
        option["independent_action_components"] = [option["semantic_option_text"]]
        option["specificity_level"] = 2
        option["semantic_meaning_fingerprint"] = _sha({
            "semantic_option_text": option["semantic_option_text"],
            "decision_granularity": option["decision_granularity"],
            "action_or_concept_head": option["action_or_concept_head"],
            "medically_required_modifiers": option["medically_required_modifiers"],
            "independent_action_components": option["independent_action_components"],
            "specificity_level": option["specificity_level"],
        })
    review = item["parallel_option_set_review"]
    review["realization_sha256"] = _sha(realization)
    assembly = item["assembly"]
    assembly["parallel_option_set_review_sha256"] = _sha(review)
    assembly["approved_component_sha256"] = {
        "open_ended": _sha(item["open_ended_stem_key"]),
        "option_realization": _sha(realization),
        "parallel_option_set_review": _sha(review),
    }
    item["acceptance_review"]["assembly_sha256"] = _sha(assembly)
    rationales = item["rationales"]
    rationales["acceptance_sha256"] = _sha(item["acceptance_review"])
    for row, distractor in zip(rationales["distractors"], construction["distractors"], strict=True):
        row["why_plausible"] = distractor["why_temporarily_plausible"]
        row["exact_discriminator"] = distractor["disqualifying_discriminant"]
        row["evidence_refs"] = distractor["evidence_refs"]
    return item


def _staged_1_3() -> tuple[dict, dict, dict]:
    evidence = _evidence()
    library = _library(evidence)
    return _upgrade_to_schema_1_3(_staged_item(evidence, library)), library, evidence


def test_schema_1_3_accepts_contextually_proven_clinical_competitors():
    item, library, evidence = _staged_1_3()
    assert validate_staged_item(REPO, item, library, evidence) is item


def test_contextual_proof_rejects_semantically_related_but_ungrounded_competitor():
    """A concept-level neighbour whose plausibility is not visible in this stem."""
    item, library, evidence = _staged_1_3()
    item["contextual_competitor_proof"]["proofs"][0]["supporting_stem_features"] = [
        {"feature": "wheeze", "polarity": "PRESENT", "stem_quote": "diffuse symmetric wheeze"},
    ]
    with pytest.raises(ChapterStagedGenerationError, match="not stated in the stem"):
        validate_staged_item(REPO, item, library, evidence)


def test_contextual_proof_rejects_discriminator_supported_only_by_the_anchor_claim():
    """The exact cross-discipline defect: one anchor claim used for every competitor."""
    item, library, evidence = _staged_1_3()
    item["contextual_competitor_proof"]["proofs"][0]["evidence_refs_for_discriminator"] = ["CLM-KEY"]
    with pytest.raises(ChapterStagedGenerationError, match="beyond the anchor key claim"):
        validate_staged_item(REPO, item, library, evidence)


def test_contextual_proof_rejects_plausibility_supported_only_by_the_anchor_claim():
    item, library, evidence = _staged_1_3()
    item["contextual_competitor_proof"]["proofs"][1]["evidence_refs_for_plausibility"] = ["CLM-KEY"]
    with pytest.raises(ChapterStagedGenerationError, match="beyond the anchor key claim"):
        validate_staged_item(REPO, item, library, evidence)


def test_contextual_proof_rejects_a_feature_that_both_supports_and_defeats():
    item, library, evidence = _staged_1_3()
    proof = item["contextual_competitor_proof"]["proofs"][0]
    proof["defeating_stem_features"] = proof["supporting_stem_features"]
    proof["adversarial_hidden_key_test"]["defeating_feature"] = "acute-chest-pressure"
    with pytest.raises(ChapterStagedGenerationError, match="both establish and defeat"):
        validate_staged_item(REPO, item, library, evidence)


def test_contextual_proof_rejects_competitor_at_a_different_decision_granularity():
    item, library, evidence = _staged_1_3()
    item["contextual_competitor_proof"]["proofs"][2]["decision_granularity"] = "MANAGEMENT_STRATEGY"
    with pytest.raises(ChapterStagedGenerationError, match="single comparable set"):
        validate_staged_item(REPO, item, library, evidence)


def test_contextual_proof_rejects_competitor_answering_a_different_learner_decision():
    item, library, evidence = _staged_1_3()
    item["contextual_competitor_proof"]["proofs"][0]["learner_decision"] = "Choose an antithrombotic regimen."
    with pytest.raises(ChapterStagedGenerationError, match="anchored learner decision"):
        validate_staged_item(REPO, item, library, evidence)


def test_adversarial_hidden_key_test_must_find_the_competitor_selectable():
    item, library, evidence = _staged_1_3()
    item["contextual_competitor_proof"]["proofs"][3]["adversarial_hidden_key_test"][
        "could_reasonably_select"
    ] = False
    with pytest.raises(ChapterStagedGenerationError, match="reasonably selectable"):
        validate_staged_item(REPO, item, library, evidence)


def test_adversarial_hidden_key_test_must_cite_a_proven_discriminator():
    item, library, evidence = _staged_1_3()
    item["contextual_competitor_proof"]["proofs"][0]["adversarial_hidden_key_test"][
        "defeating_feature"
    ] = "an unproven feature"
    with pytest.raises(ChapterStagedGenerationError, match="discriminator absent from the proof"):
        validate_staged_item(REPO, item, library, evidence)


def test_schema_1_3_distractor_must_carry_context_specific_reasoning():
    item, library, evidence = _staged_1_3()
    item["distractor_construction"]["distractors"][0]["why_temporarily_plausible"] = (
        "A partially knowledgeable graduate overweights an overlapping feature."
    )
    with pytest.raises(ChapterStagedGenerationError, match="contextual competitor proof"):
        validate_staged_item(REPO, item, library, evidence)


def test_schema_1_3_requires_a_fresh_adversarial_competitor_reviewer():
    item, library, evidence = _staged_1_3()
    for proof in item["contextual_competitor_proof"]["proofs"]:
        proof["adversarial_hidden_key_test"]["reviewer_id"] = "distractor-reviewer"
    with pytest.raises(ChapterStagedGenerationError, match="fresh staged reviewers"):
        validate_staged_item(REPO, item, library, evidence)


def test_polarity_preflight_rejects_key_as_the_only_continuation_choice():
    """Abstracted from the lactation item whose distractors were all cessation variants."""
    options = [
        _semantic_option("KEY", "Continue treatment from the affected site"),
        _semantic_option("DISTRACTOR", "Stop treatment at the affected site", semantic_polarity="NEGATING_ACTION"),
        _semantic_option("DISTRACTOR", "Discard the product of the affected site", semantic_polarity="NEGATING_ACTION"),
        _semantic_option("DISTRACTOR", "Replace the affected route temporarily", semantic_polarity="NEGATING_ACTION"),
    ]
    assert find_polarity_completeness_defects(options) == ["KEY_ONLY_POLARITY"]


def test_polarity_preflight_cannot_be_evaded_by_mislabelling_a_withholding_option():
    options = [
        _semantic_option("KEY", "Continue treatment from the affected site"),
        _semantic_option("DISTRACTOR", "Stop treatment at the affected site"),
        _semantic_option("DISTRACTOR", "Discard the product of the affected site", semantic_polarity="NEGATING_ACTION"),
        _semantic_option("DISTRACTOR", "Replace the affected route temporarily", semantic_polarity="NEGATING_ACTION"),
    ]
    assert "DECLARED_POLARITY_CONTRADICTS_TEXT" in find_polarity_completeness_defects(options)


def test_polarity_preflight_rejects_key_only_complete_program_strategy():
    """Abstracted from the screening-programme item whose distractors were parameter tweaks."""
    options = [
        _semantic_option(
            "KEY",
            "Defer launch until downstream capacity exists",
            semantic_polarity="NEGATING_ACTION",
            decision_scope="PROGRAMME_IMPLEMENTATION_READINESS",
        ),
        _semantic_option("DISTRACTOR", "Lower the positivity threshold", strategy_completeness="PARTIAL_COMPONENT"),
        _semantic_option("DISTRACTOR", "Launch with public advertising immediately", strategy_completeness="PARTIAL_COMPONENT"),
        _semantic_option("DISTRACTOR", "Repeat every positive test automatically", strategy_completeness="PARTIAL_COMPONENT"),
    ]
    assert find_polarity_completeness_defects(options) == [
        "KEY_ONLY_COMPLETE_STRATEGY",
        "KEY_ONLY_POLARITY",
        "NONPARALLEL_DECISION_SCOPE",
    ]


def test_polarity_preflight_rejects_partial_distractors_converging_into_the_key():
    options = [
        _semantic_option("KEY", "Start supportive care and arrange follow-up",
                         independent_action_components=["supportive-care", "follow-up"]),
        _semantic_option("DISTRACTOR", "Start supportive care alone",
                         independent_action_components=["supportive-care"]),
        _semantic_option("DISTRACTOR", "Arrange follow-up alone",
                         independent_action_components=["follow-up"]),
        _semantic_option("DISTRACTOR", "Refer for an unrelated procedure",
                         independent_action_components=["unrelated-procedure"]),
    ]
    findings = find_polarity_completeness_defects(options)
    assert "CONCEPTUAL_CONVERGENCE" in findings and "KEY_ONLY_COMPLETENESS" in findings


def test_polarity_preflight_rejects_a_categorically_more_specific_key():
    options = [
        _semantic_option("KEY", "Begin a specified first-line agent at a stated dose", specificity_level=4),
        _semantic_option("DISTRACTOR", "Begin an alternative agent class", specificity_level=2),
        _semantic_option("DISTRACTOR", "Begin a second alternative agent class", specificity_level=2),
        _semantic_option("DISTRACTOR", "Begin a third alternative agent class", specificity_level=3),
    ]
    assert find_polarity_completeness_defects(options) == ["KEY_ONLY_SPECIFICITY"]


def test_polarity_preflight_accepts_a_valid_psychiatric_differential():
    options = [
        _semantic_option("KEY", "Major depressive disorder", decision_granularity="DIAGNOSIS"),
        _semantic_option("DISTRACTOR", "Persistent depressive disorder", decision_granularity="DIAGNOSIS"),
        _semantic_option("DISTRACTOR", "Bipolar disorder in a depressive episode", decision_granularity="DIAGNOSIS"),
        _semantic_option("DISTRACTOR", "Adjustment disorder with depressed mood", decision_granularity="DIAGNOSIS"),
    ]
    assert find_polarity_completeness_defects(options) == []


def test_polarity_preflight_accepts_neighbouring_screening_constructs():
    options = [
        _semantic_option("KEY", "Lead-time bias", decision_granularity="OTHER",
                         decision_scope="SCREENING_EVALUATION_CONSTRUCT"),
        _semantic_option("DISTRACTOR", "Length-time bias", decision_granularity="OTHER",
                         decision_scope="SCREENING_EVALUATION_CONSTRUCT"),
        _semantic_option("DISTRACTOR", "Overdiagnosis", decision_granularity="OTHER",
                         decision_scope="SCREENING_EVALUATION_CONSTRUCT"),
        _semantic_option("DISTRACTOR", "Healthy-volunteer selection effect", decision_granularity="OTHER",
                         decision_scope="SCREENING_EVALUATION_CONSTRUCT"),
    ]
    assert find_polarity_completeness_defects(options) == []


def test_polarity_preflight_accepts_comparable_management_alternatives():
    options = [
        _semantic_option("KEY", "Admit for intravenous therapy"),
        _semantic_option("DISTRACTOR", "Discharge with oral therapy", semantic_polarity="NEGATING_ACTION"),
        _semantic_option("DISTRACTOR", "Admit for observation without therapy"),
        _semantic_option("DISTRACTOR", "Transfer for procedural management"),
    ]
    assert find_polarity_completeness_defects(options) == []


def test_staged_1_3_fails_closed_when_the_semantic_option_set_is_unfair():
    item, library, evidence = _staged_1_3()
    for row in item["semantic_polarity_completeness_preflight"]["options"]:
        if row["role"] == "DISTRACTOR":
            row["strategy_completeness"] = "PARTIAL_COMPONENT"
    with pytest.raises(ChapterStagedGenerationError, match="KEY_ONLY_COMPLETE_STRATEGY"):
        validate_staged_item(REPO, item, library, evidence)


def test_staged_1_3_preflight_findings_must_be_reported_honestly():
    item, library, evidence = _staged_1_3()
    preflight = item["semantic_polarity_completeness_preflight"]
    preflight["options"][1]["decision_scope"] = "A_DIFFERENT_SCOPE"
    preflight["deterministic_findings"] = []
    with pytest.raises(ChapterStagedGenerationError, match="NONPARALLEL_DECISION_SCOPE"):
        validate_staged_item(REPO, item, library, evidence)


def test_staged_1_3_preflight_must_precede_and_bind_the_realized_options():
    item, library, evidence = _staged_1_3()
    item["semantic_polarity_completeness_preflight"]["options"][0]["semantic_option_text"] = "Something else"
    with pytest.raises(ChapterStagedGenerationError, match="preflight"):
        validate_staged_item(REPO, item, library, evidence)


# --- SEMANTIC_ITEM_ACCEPTANCE_V2 (schema 1.4) --------------------------------

STAGES_V5 = [
    "TORONTO_NOTES_ANCHOR",
    "MCC_OBJECTIVE_PHYSICIAN_ACTIVITY",
    "PRIMARY_LEARNER_DECISION",
    "ANCHOR_FIDELITY",
    "OPEN_ENDED_STEM_KEY",
    "CANDIDATE_VISIBLE_STEM_FEATURE_MAP",
    "NUMERIC_DERIVATION_VALIDATION",
    "BLIND_COVER_OPTIONS_SOLVER",
    "GLOBAL_CONTRAST_RETRIEVAL",
    "CONTRASTIVE_EVIDENCE_MATRIX",
    "EVIDENCE_ENTAILMENT_ADJUDICATION",
    "CONTEXTUAL_COMPETITOR_PROOF",
    "TERMINAL_EXCLUSION_REVIEW",
    "SEPARATE_DISTRACTOR_CONSTRUCTION",
    "DISTRACTOR_ADVERSARIAL_RANKING",
    "SEMANTIC_POLARITY_COMPLETENESS_PREFLIGHT",
    "OPTION_SEMANTIC_CATEGORY_PARITY",
    "PRE_ASSEMBLY_SEMANTIC_SET_REVIEW",
    "OPTION_REALIZATION",
    "PARALLEL_OPTION_SET_REVIEW",
    "DECISION_GRANULARITY_PARITY",
    "MCQ_ASSEMBLY",
    "PLAN_FIDELITY_SHORTCUT_CUE_CHECK",
    "RATIONALES",
    "FRESH_INDEPENDENT_VERIFICATION",
]


def _rebind_1_4(item: dict) -> dict:
    """Recompute every downstream fingerprint after a schema-1.4 stage edit."""
    item["numeric_derivation_validation"]["stem_feature_map_sha256"] = _sha(item["stem_feature_map"])
    item["evidence_entailment_adjudication"]["matrix_sha256"] = _sha(item["contrastive_evidence_matrix"])
    item["contextual_competitor_proof"]["matrix_sha256"] = _sha(item["contrastive_evidence_matrix"])
    item["terminal_exclusion_review"]["contextual_competitor_proof_sha256"] = _sha(
        item["contextual_competitor_proof"]
    )
    construction = item["distractor_construction"]
    construction["matrix_sha256"] = _sha(item["contrastive_evidence_matrix"])
    adversarial = item["distractor_adversarial_review"]
    adversarial["construction_sha256"] = _sha(construction)
    preflight = item["semantic_polarity_completeness_preflight"]
    preflight["adversarial_review_sha256"] = _sha(adversarial)
    parity = item["option_semantic_category_parity"]
    parity["preflight_sha256"] = _sha(preflight)
    parity["deterministic_findings"] = find_option_category_parity_defects(parity["options"])
    set_review = item["pre_assembly_semantic_set_review"]
    set_review["category_parity_sha256"] = _sha(parity)
    realization = item["option_realization"]
    realization["adversarial_review_sha256"] = _sha(adversarial)
    realization["pre_assembly_set_review_sha256"] = _sha(set_review)
    review = item["parallel_option_set_review"]
    review["realization_sha256"] = _sha(realization)
    assembly = item["assembly"]
    assembly["parallel_option_set_review_sha256"] = _sha(review)
    assembly["approved_component_sha256"] = {
        "open_ended": _sha(item["open_ended_stem_key"]),
        "option_realization": _sha(realization),
        "parallel_option_set_review": _sha(review),
    }
    item["acceptance_review"]["assembly_sha256"] = _sha(assembly)
    item["rationales"]["acceptance_sha256"] = _sha(item["acceptance_review"])
    item["semantic_fingerprint"] = _sha({
        "item_type": item["item_type"],
        "decision": item["anchor"]["primary_learner_decision"],
        "stem": assembly["stem"],
        "lead_in": assembly["lead_in"],
        "answer": next(o for o in assembly["options"] if o["role"] == "KEY")["text"],
    })
    return item


def _upgrade_to_schema_1_4(item: dict) -> dict:
    """Ground the item in candidate-visible features and adjudicated entailment."""
    item = _upgrade_to_schema_1_3(item)
    item["schema_version"] = "1.4"
    item["stage_sequence"] = STAGES_V5
    open_ended = item["open_ended_stem_key"]
    matrix = item["contrastive_evidence_matrix"]
    key_refs = matrix["key"]["anchor_evidence_refs"]

    item["stem_feature_map"] = {
        "cartographer_id": "stem-feature-cartographer",
        "open_ended_sha256": _sha(open_ended),
        "features": [
            {
                "feature_id": "F-PRESSURE",
                "normalized_feature": "acute central chest pressure",
                "clinical_role": "PRESENTING_SYMPTOM",
                "polarity": "PRESENT",
                "inference_type": "EXPLICIT_FINDING",
                "source_span": STEM_SUPPORT,
            },
            {
                "feature_id": "F-ECG",
                "normalized_feature": "new regional ischemic ECG change",
                "clinical_role": "DECISIVE_INVESTIGATION_FINDING",
                "polarity": "PRESENT",
                "inference_type": "EXPLICIT_FINDING",
                "source_span": STEM_DEFEAT,
            },
            {
                "feature_id": "F-AUTONOMIC",
                "normalized_feature": "diaphoresis accompanying the pain",
                "clinical_role": "ASSOCIATED_FINDING",
                "polarity": "PRESENT",
                "inference_type": "EXPLICIT_FINDING",
                "source_span": "diaphoresis",
            },
            {
                "feature_id": "F-ISCHEMIC-SYNDROME",
                "normalized_feature": "an ischemic syndrome rather than an isolated ECG abnormality",
                "clinical_role": "INTEGRATED_CLINICAL_INFERENCE",
                "polarity": "PRESENT",
                "inference_type": "INTEGRATED_INFERENCE",
                "derived_from": ["F-PRESSURE", "F-ECG", "F-AUTONOMIC"],
            },
        ],
        "verdict": "PASS",
    }
    item["numeric_derivation_validation"] = {
        "adjudicator_id": "numeric-adjudicator",
        "stem_feature_map_sha256": _sha(item["stem_feature_map"]),
        "derivations": [],
        "no_derived_values_present": True,
        "verdict": "PASS",
    }

    entailment_claims = [{
        "claim_ref": "ENT-KEY",
        "claim_text": "The regional ischemic ECG change decides ACS in this presentation.",
        "claim_type": "KEY_DECISIVE",
        "support_scope": "SCENARIO_APPLICABLE_RULE",
        "entailment_status": "SUPPORTED_DIRECTLY",
        "scope_justification": "The source states the rule for exactly this ECG-plus-symptom pattern.",
        "evidence_refs": list(key_refs),
    }]
    proofs = item["contextual_competitor_proof"]["proofs"]
    for proof in proofs:
        contrast_id = proof["contrast_id"]
        competitor_refs = proof["evidence_refs_for_plausibility"]
        entailment_claims.append({
            "claim_ref": f"ENT-{contrast_id}-P",
            "claim_text": f"{contrast_id} shares this presentation's chest pressure.",
            "claim_type": "COMPETITOR_PLAUSIBILITY",
            "contrast_id": contrast_id,
            "support_scope": "SCENARIO_APPLICABLE_RULE",
            "entailment_status": "SUPPORTED_DIRECTLY",
            "scope_justification": "The source describes this competitor in an acute chest-pain presentation.",
            "evidence_refs": list(competitor_refs),
        })
        entailment_claims.append({
            "claim_ref": f"ENT-{contrast_id}-D",
            "claim_text": f"{contrast_id} does not produce a new regional ischemic ECG change.",
            "claim_type": "COMPETITOR_DISCRIMINATOR",
            "contrast_id": contrast_id,
            "support_scope": "EXACT_SCENARIO_CLAIM",
            "entailment_status": "SUPPORTED_DIRECTLY",
            "scope_justification": "The source states this competitor's expected ECG behaviour directly.",
            "evidence_refs": list(proof["evidence_refs_for_discriminator"]),
        })
        proof.pop("supporting_stem_features")
        proof.pop("defeating_stem_features")
        proof["supporting_stem_feature_ids"] = ["F-PRESSURE", "F-AUTONOMIC"]
        proof["defeating_stem_feature_ids"] = ["F-ECG", "F-ISCHEMIC-SYNDROME"]
        proof["discriminator_available_to_candidate"] = True
        proof["post_stem_status"] = "STRONG_COMPETITOR"
        proof["remains_plausible_after_full_stem"] = True
        proof["option_text_self_defeats"] = False
        proof["entailment_claim_refs"] = {
            "plausibility": f"ENT-{contrast_id}-P",
            "discriminator": f"ENT-{contrast_id}-D",
        }
        proof["adversarial_hidden_key_test"]["defeating_feature"] = "F-ECG"
    item["evidence_entailment_adjudication"] = {
        "adjudicator_id": "evidence-entailment-adjudicator",
        "matrix_sha256": _sha(matrix),
        "claims": entailment_claims,
        "verdict": "PASS",
    }
    item["terminal_exclusion_review"] = {
        "reviewer_id": "terminal-exclusion-reviewer",
        "contextual_competitor_proof_sha256": _sha(item["contextual_competitor_proof"]),
        "assessments": [
            {
                "contrast_id": proof["contrast_id"],
                "defeating_stem_feature_ids": proof["defeating_stem_feature_ids"],
                "exclusion_class": "NATURAL_DECISIVE_FINDING",
                "justification": "The ECG belongs to the presentation and drives the intended decision.",
                "immediately_rejectable_by_single_negative_phrase": False,
            }
            for proof in proofs
        ],
        "deterministic_findings": [],
        "verdict": "PASS",
    }

    preflight = item["semantic_polarity_completeness_preflight"]
    parity_options = []
    for row in preflight["options"]:
        parity_options.append({
            "role": row["role"],
            "semantic_option_text": row["semantic_option_text"],
            "option_semantic_type": "DIAGNOSIS",
            "option_action_type": "CLASSIFY",
            "option_polarity": "AFFIRMATIVE_ACTION",
            "option_scope": "CHEST_PAIN_DIAGNOSTIC_DECISION",
            "decision_granularity": "DIAGNOSIS",
            "completeness_level": "SINGLE_ACTION",
            "category_rationale": "A single named diagnosis answering the same lead-in.",
            **({"contrast_id": row["contrast_id"]} if row["role"] == "DISTRACTOR" else {}),
        })
    item["option_semantic_category_parity"] = {
        "reviewer_id": "option-category-parity-reviewer",
        "preflight_sha256": _sha(preflight),
        "options": parity_options,
        "parity_exceptions": [],
        "deterministic_findings": [],
        "key_identifiable_from_option_structure": False,
        "verdict": "PASS",
    }
    item["pre_assembly_semantic_set_review"] = {
        "reviewer_id": "pre-assembly-set-reviewer",
        "category_parity_sha256": _sha(item["option_semantic_category_parity"]),
        "checks": {name: "PASS" for name in PREASSEMBLY_CHECKS},
        "verdict": "PASS",
    }
    open_ended["reasoning_chain"][-1] = (
        "The new regional ischemic ECG change makes acute coronary syndrome the single best diagnosis."
    )
    item["rationales"]["correct"]["why_best"] = open_ended["reasoning_chain"][-1]
    item["blind_solver"]["open_ended_sha256"] = _sha(open_ended)
    item["global_contrast_retrieval"]["blind_solver_sha256"] = _sha(item["blind_solver"])
    matrix["retrieval_sha256"] = _sha(item["global_contrast_retrieval"])
    item["stem_feature_map"]["open_ended_sha256"] = _sha(open_ended)
    item["option_realization"]["options"] = item["option_realization"]["options"]
    return _rebind_1_4(item)


PREASSEMBLY_CHECKS = {
    "same_lead_in_dimension",
    "compatible_semantic_category",
    "comparable_decision_granularity",
    "no_unique_completeness",
    "no_polarity_odd_one_out",
    "no_conceptual_convergence",
    "no_trivially_excluded_competitor",
    "competitor_specific_evidence_entailment",
}


def _staged_1_4() -> tuple[dict, dict, dict]:
    evidence = _evidence()
    library = _library(evidence)
    return _upgrade_to_schema_1_4(_staged_item(evidence, library)), library, evidence


def test_schema_1_4_accepts_a_semantically_grounded_item():
    item, library, evidence = _staged_1_4()
    assert validate_staged_item(REPO, item, library, evidence) is item


def _restem_1_4(item: dict, stem: str, features: list[dict]) -> dict:
    """Rewrite the stem the candidate reads and rebind the whole staged chain."""
    open_ended = item["open_ended_stem_key"]
    open_ended["stem"] = stem
    item["assembly"]["stem"] = stem
    item["blind_solver"]["open_ended_sha256"] = _sha(open_ended)
    item["global_contrast_retrieval"]["blind_solver_sha256"] = _sha(item["blind_solver"])
    item["contrastive_evidence_matrix"]["retrieval_sha256"] = _sha(item["global_contrast_retrieval"])
    item["evidence_entailment_adjudication"]["matrix_sha256"] = _sha(item["contrastive_evidence_matrix"])
    item["stem_feature_map"]["features"] = features
    item["stem_feature_map"]["open_ended_sha256"] = _sha(open_ended)
    return _rebind_1_4(item)


def _rebind_terminal_review(item: dict) -> dict:
    item["terminal_exclusion_review"]["contextual_competitor_proof_sha256"] = _sha(
        item["contextual_competitor_proof"]
    )
    return _rebind_1_4(item)


# 1. A cited claim that the adjudicator cannot make the evidence entail.
def test_entailment_gate_rejects_a_citation_that_does_not_entail_its_claim():
    item, library, evidence = _staged_1_4()
    claims = item["evidence_entailment_adjudication"]["claims"]
    claims[2]["entailment_status"] = "PARTIALLY_SUPPORTED"
    _rebind_1_4(item)
    with pytest.raises(ChapterStagedGenerationError, match="does not entail claim"):
        validate_staged_item(REPO, item, library, evidence)


@pytest.mark.parametrize("status", ["NOT_SUPPORTED", "CONFLICTING"])
def test_entailment_gate_rejects_unsupported_and_conflicting_evidence(status):
    item, library, evidence = _staged_1_4()
    item["evidence_entailment_adjudication"]["claims"][0]["entailment_status"] = status
    _rebind_1_4(item)
    with pytest.raises(ChapterStagedGenerationError, match="does not entail claim"):
        validate_staged_item(REPO, item, library, evidence)


# 2. A general disease page cannot decide a scenario-specific discriminator.
def test_entailment_gate_rejects_a_general_concept_source_behind_a_scenario_claim():
    item, library, evidence = _staged_1_4()
    claims = item["evidence_entailment_adjudication"]["claims"]
    discriminator = next(row for row in claims if row["claim_type"] == "COMPETITOR_DISCRIMINATOR")
    discriminator["support_scope"] = "GENERAL_CONCEPT_CLAIM"
    _rebind_1_4(item)
    with pytest.raises(ChapterStagedGenerationError, match="rests only on a general concept source"):
        validate_staged_item(REPO, item, library, evidence)


def test_entailment_gate_requires_every_competitor_to_be_adjudicated():
    item, library, evidence = _staged_1_4()
    claims = item["evidence_entailment_adjudication"]["claims"]
    item["evidence_entailment_adjudication"]["claims"] = [
        row for row in claims if row["claim_ref"] != claims[-1]["claim_ref"]
    ]
    _rebind_1_4(item)
    with pytest.raises(ChapterStagedGenerationError, match="unadjudicated"):
        validate_staged_item(REPO, item, library, evidence)


# 3. A discriminator may rest on several candidate-visible features at once.
def test_candidate_visible_grounding_accepts_an_integrated_multi_feature_discriminator():
    item, library, evidence = _staged_1_4()
    for proof in item["contextual_competitor_proof"]["proofs"]:
        proof["defeating_stem_feature_ids"] = ["F-ISCHEMIC-SYNDROME"]
        proof["adversarial_hidden_key_test"]["defeating_feature"] = "F-ISCHEMIC-SYNDROME"
    for row in item["terminal_exclusion_review"]["assessments"]:
        row["defeating_stem_feature_ids"] = ["F-ISCHEMIC-SYNDROME"]
    _rebind_terminal_review(item)
    assert validate_staged_item(REPO, item, library, evidence) is item


def test_candidate_visible_grounding_rejects_a_feature_absent_from_the_stem():
    item, library, evidence = _staged_1_4()
    item["stem_feature_map"]["features"][1]["source_span"] = "a troponin the stem never reports"
    _rebind_1_4(item)
    with pytest.raises(ChapterStagedGenerationError, match="cannot read in the stem"):
        validate_staged_item(REPO, item, library, evidence)


def test_candidate_visible_grounding_rejects_an_integrated_feature_without_components():
    item, library, evidence = _staged_1_4()
    item["stem_feature_map"]["features"][3]["derived_from"] = ["F-ECG"]
    _rebind_1_4(item)
    with pytest.raises(ChapterStagedGenerationError, match="two or more previously grounded features"):
        validate_staged_item(REPO, item, library, evidence)


# 4. A closing clause whose only job is to make distractors false.
def test_terminal_exclusion_gate_rejects_a_negative_checklist_written_for_the_options():
    item, library, evidence = _staged_1_4()
    stem = (
        "A patient has acute central chest pressure with diaphoresis and a new regional "
        "ischemic ECG change. There is no pleuritic pain, no tearing interscapular pain, "
        "and no reflux symptoms."
    )
    features = [
        {"feature_id": "F-PRESSURE", "normalized_feature": "acute central chest pressure",
         "clinical_role": "PRESENTING_SYMPTOM", "polarity": "PRESENT",
         "inference_type": "EXPLICIT_FINDING", "source_span": STEM_SUPPORT},
        {"feature_id": "F-NO-PLEURITIC", "normalized_feature": "pleuritic pain absent",
         "clinical_role": "EXCLUSIONARY_FINDING", "polarity": "ABSENT",
         "inference_type": "ABSENT_FINDING", "source_span": "no pleuritic pain"},
        {"feature_id": "F-NO-TEARING", "normalized_feature": "tearing interscapular pain absent",
         "clinical_role": "EXCLUSIONARY_FINDING", "polarity": "ABSENT",
         "inference_type": "ABSENT_FINDING", "source_span": "no tearing interscapular pain"},
        {"feature_id": "F-NO-REFLUX", "normalized_feature": "reflux symptoms absent",
         "clinical_role": "EXCLUSIONARY_FINDING", "polarity": "ABSENT",
         "inference_type": "ABSENT_FINDING", "source_span": "no reflux symptoms"},
        {"feature_id": "F-ECG", "normalized_feature": "new regional ischemic ECG change",
         "clinical_role": "DECISIVE_INVESTIGATION_FINDING", "polarity": "PRESENT",
         "inference_type": "EXPLICIT_FINDING", "source_span": STEM_DEFEAT},
    ]
    _restem_1_4(item, stem, features)
    killers = ["F-NO-PLEURITIC", "F-NO-TEARING", "F-NO-REFLUX", "F-ECG"]
    for proof, killer in zip(item["contextual_competitor_proof"]["proofs"], killers):
        proof["supporting_stem_feature_ids"] = ["F-PRESSURE"]
        proof["defeating_stem_feature_ids"] = [killer]
        proof["adversarial_hidden_key_test"]["defeating_feature"] = killer
    for row, killer in zip(item["terminal_exclusion_review"]["assessments"], killers):
        row["defeating_stem_feature_ids"] = [killer]
    _rebind_terminal_review(item)
    with pytest.raises(ChapterStagedGenerationError, match="NEGATIVE_CHECKLIST_SENTENCE"):
        validate_staged_item(REPO, item, library, evidence)


def test_terminal_exclusion_gate_rejects_a_declared_artificial_exclusion():
    item, library, evidence = _staged_1_4()
    item["terminal_exclusion_review"]["assessments"][0]["exclusion_class"] = "ARTIFICIAL_TERMINAL_EXCLUSION"
    _rebind_1_4(item)
    with pytest.raises(ChapterStagedGenerationError, match="artificial terminal exclusion"):
        validate_staged_item(REPO, item, library, evidence)


def test_terminal_exclusion_gate_rejects_a_phrase_matchable_competitor():
    item, library, evidence = _staged_1_4()
    row = item["terminal_exclusion_review"]["assessments"][1]
    row["immediately_rejectable_by_single_negative_phrase"] = True
    _rebind_1_4(item)
    with pytest.raises(ChapterStagedGenerationError, match="phrase matching rather than reasoning"):
        validate_staged_item(REPO, item, library, evidence)


# 5. A negative finding that belongs to the presentation is not a giveaway.
def test_terminal_exclusion_gate_allows_a_natural_decisive_negative_finding():
    item, library, evidence = _staged_1_4()
    stem = (
        "A patient has acute central chest pressure with diaphoresis and no relief after rest. "
        "The electrocardiogram shows a new regional ischemic ECG change and the chest is clear."
    )
    features = [
        {"feature_id": "F-PRESSURE", "normalized_feature": "acute central chest pressure",
         "clinical_role": "PRESENTING_SYMPTOM", "polarity": "PRESENT",
         "inference_type": "EXPLICIT_FINDING", "source_span": STEM_SUPPORT},
        {"feature_id": "F-NO-REST-RELIEF", "normalized_feature": "pain persists at rest",
         "clinical_role": "SYMPTOM_BEHAVIOUR", "polarity": "ABSENT",
         "inference_type": "TREATMENT_RESPONSE", "source_span": "no relief after rest"},
        {"feature_id": "F-ECG", "normalized_feature": "new regional ischemic ECG change",
         "clinical_role": "DECISIVE_INVESTIGATION_FINDING", "polarity": "PRESENT",
         "inference_type": "EXPLICIT_FINDING", "source_span": STEM_DEFEAT},
    ]
    _restem_1_4(item, stem, features)
    for proof in item["contextual_competitor_proof"]["proofs"]:
        proof["supporting_stem_feature_ids"] = ["F-PRESSURE"]
        proof["defeating_stem_feature_ids"] = ["F-ECG", "F-NO-REST-RELIEF"]
        proof["adversarial_hidden_key_test"]["defeating_feature"] = "F-ECG"
    for row in item["terminal_exclusion_review"]["assessments"]:
        row["defeating_stem_feature_ids"] = ["F-ECG", "F-NO-REST-RELIEF"]
    _rebind_terminal_review(item)
    assert validate_staged_item(REPO, item, library, evidence) is item


# 6. A topic-adjacent competitor that the completed stem obviously contradicts.
@pytest.mark.parametrize("status", ["TRIVIALLY_EXCLUDED", "NOT_CONTEXTUALLY_PLAUSIBLE", "UNSUPPORTED"])
def test_competitor_test_v2_rejects_a_competitor_the_full_stem_destroys(status):
    item, library, evidence = _staged_1_4()
    item["contextual_competitor_proof"]["proofs"][2]["post_stem_status"] = status
    _rebind_terminal_review(item)
    with pytest.raises(ChapterStagedGenerationError, match="not a competitive distractor"):
        validate_staged_item(REPO, item, library, evidence)


def test_competitor_test_v2_rejects_an_option_whose_own_wording_defeats_it():
    item, library, evidence = _staged_1_4()
    item["contextual_competitor_proof"]["proofs"][0]["option_text_self_defeats"] = True
    _rebind_terminal_review(item)
    with pytest.raises(ChapterStagedGenerationError, match="own option wording defeats it"):
        validate_staged_item(REPO, item, library, evidence)


# 7. A competitor that only falls once several features are read together.
def test_competitor_test_v2_accepts_a_competitor_defeated_only_by_integration():
    item, library, evidence = _staged_1_4()
    for proof in item["contextual_competitor_proof"]["proofs"]:
        proof["post_stem_status"] = "ACCEPTABLE_COMPETITOR"
        proof["supporting_stem_feature_ids"] = ["F-PRESSURE", "F-AUTONOMIC"]
        proof["defeating_stem_feature_ids"] = ["F-ISCHEMIC-SYNDROME"]
        proof["adversarial_hidden_key_test"]["defeating_feature"] = "F-ISCHEMIC-SYNDROME"
    for row in item["terminal_exclusion_review"]["assessments"]:
        row["defeating_stem_feature_ids"] = ["F-ISCHEMIC-SYNDROME"]
        row["exclusion_class"] = "LEGITIMATE_SINGLE_DISCRIMINATOR"
    _rebind_terminal_review(item)
    assert validate_staged_item(REPO, item, library, evidence) is item


def _set_parity(item: dict, index: int, **fields) -> dict:
    item["option_semantic_category_parity"]["options"][index].update(fields)
    return _rebind_1_4(item)


def _investigation_set(item: dict) -> dict:
    """Recast the option set as four investigations answering one lead-in."""
    for row in item["option_semantic_category_parity"]["options"]:
        row.update({
            "option_semantic_type": "INVESTIGATION",
            "option_action_type": "INITIATE",
            "option_scope": "IMMEDIATE_DIAGNOSTIC_DECISION",
            "decision_granularity": "DIAGNOSTIC_TEST",
        })
    return _rebind_1_4(item)


# 8. Three tests and a lone no-test key.
def test_category_parity_rejects_three_tests_against_a_lone_no_test_key():
    item, library, evidence = _staged_1_4()
    _investigation_set(item)
    _set_parity(
        item, 0,
        option_action_type="WITHHOLD",
        option_polarity="NEGATING_ACTION",
        option_semantic_type="MANAGEMENT_STRATEGY",
    )
    with pytest.raises(ChapterStagedGenerationError, match="exposes its key by category"):
        validate_staged_item(REPO, item, library, evidence)


def test_category_parity_allows_a_no_test_key_only_on_independent_justification():
    item, library, evidence = _staged_1_4()
    _investigation_set(item)
    _set_parity(item, 0, option_action_type="WITHHOLD")
    parity = item["option_semantic_category_parity"]
    parity["parity_exceptions"] = [{
        "finding": "KEY_ONLY_OPTION_ACTION_TYPE",
        "justification": "Withholding testing is the guideline's named alternative to each listed test.",
        "genuinely_comparable_response_reasoning": (
            "Every option answers whether to test now, so the set is one decision, not two."
        ),
        "independent_reviewer_id": "parity-exception-adjudicator",
        "verdict": "PASS",
    }]
    _rebind_1_4(item)
    assert validate_staged_item(REPO, item, library, evidence) is item


def test_category_parity_exception_requires_a_reviewer_other_than_its_own():
    item, library, evidence = _staged_1_4()
    _investigation_set(item)
    _set_parity(item, 0, option_action_type="WITHHOLD")
    parity = item["option_semantic_category_parity"]
    parity["parity_exceptions"] = [{
        "finding": "KEY_ONLY_OPTION_ACTION_TYPE",
        "justification": "Self-approved.",
        "genuinely_comparable_response_reasoning": "Self-approved.",
        "independent_reviewer_id": parity["reviewer_id"],
        "verdict": "PASS",
    }]
    _rebind_1_4(item)
    with pytest.raises(ChapterStagedGenerationError, match="requires an independent reviewer"):
        validate_staged_item(REPO, item, library, evidence)


# 9. Three drugs and one option from another category.
def test_category_parity_rejects_three_medications_beside_a_different_category():
    item, library, evidence = _staged_1_4()
    for row in item["option_semantic_category_parity"]["options"]:
        row.update({
            "option_semantic_type": "MEDICATION",
            "option_action_type": "INITIATE",
            "option_scope": "IMMEDIATE_TREATMENT_DECISION",
            "decision_granularity": "SINGLE_NEXT_ACTION",
        })
    _set_parity(item, 2, option_semantic_type="SUPPORTIVE_CARE")
    with pytest.raises(ChapterStagedGenerationError, match="DISTRACTOR_OUTLIER_OPTION_SEMANTIC_TYPE"):
        validate_staged_item(REPO, item, library, evidence)


# 10. Genuine same-decision management alternatives stay acceptable.
def test_category_parity_accepts_parallel_same_decision_management_alternatives():
    item, library, evidence = _staged_1_4()
    for row in item["option_semantic_category_parity"]["options"]:
        row.update({
            "option_semantic_type": "MANAGEMENT_STRATEGY",
            "option_action_type": "INITIATE",
            "option_scope": "IMMEDIATE_TREATMENT_DECISION",
            "decision_granularity": "MANAGEMENT_STRATEGY",
            "completeness_level": "SINGLE_ACTION",
        })
    _rebind_1_4(item)
    assert validate_staged_item(REPO, item, library, evidence) is item


# 11. A key that is the only complete strategy on offer.
def test_category_parity_rejects_a_key_only_comprehensive_strategy():
    item, library, evidence = _staged_1_4()
    _set_parity(item, 0, completeness_level="FULL_BUNDLE")
    with pytest.raises(ChapterStagedGenerationError, match="KEY_ONLY_COMPLETENESS_LEVEL"):
        validate_staged_item(REPO, item, library, evidence)


def test_category_parity_rejects_a_lone_polarity_reversal():
    item, library, evidence = _staged_1_4()
    _set_parity(item, 0, option_polarity="NEGATING_ACTION")
    with pytest.raises(ChapterStagedGenerationError, match="KEY_ONLY_OPTION_POLARITY"):
        validate_staged_item(REPO, item, library, evidence)


# 12. A key assembled from the parts its own distractors offer separately.
def test_pre_assembly_set_review_rejects_conceptual_convergence():
    item, library, evidence = _staged_1_4()
    realized = item["option_realization"]["options"]
    key = next(row for row in realized if row["role"] == "KEY")
    distractors = [row for row in realized if row["role"] == "DISTRACTOR"]
    key["independent_action_components"] = ["component-a", "component-b"]
    distractors[0]["independent_action_components"] = ["component-a"]
    distractors[1]["independent_action_components"] = ["component-b"]
    for row in realized:
        row["semantic_meaning_fingerprint"] = _sha({
            "semantic_option_text": row["semantic_option_text"],
            "decision_granularity": row["decision_granularity"],
            "action_or_concept_head": row["action_or_concept_head"],
            "medically_required_modifiers": row["medically_required_modifiers"],
            "independent_action_components": row["independent_action_components"],
            "specificity_level": row["specificity_level"],
        })
    _rebind_1_4(item)
    with pytest.raises(ChapterStagedGenerationError, match="CONCEPTUAL_CONVERGENCE|KEY_ONLY_COMPLETENESS"):
        validate_staged_item(REPO, item, library, evidence)


def test_pre_assembly_set_review_must_pass_before_any_wording_exists():
    item, library, evidence = _staged_1_4()
    item["pre_assembly_semantic_set_review"]["checks"]["no_trivially_excluded_competitor"] = "FAIL"
    _rebind_1_4(item)
    with pytest.raises(ChapterStagedGenerationError, match="pre-assembly semantic set review"):
        validate_staged_item(REPO, item, library, evidence)


# 13. A stated score that its own declared components do not produce.
def _component_span(name: str, value: int) -> str:
    return f"{name.replace('_', ' ')} is {'recorded' if value else 'not recorded'}"


def _score_item(total: int, components: list[tuple[str, int]]) -> tuple[dict, dict, dict]:
    item, library, evidence = _staged_1_4()
    spans = "; ".join(_component_span(name, value) for name, value in components)
    stem = (
        "A patient has acute central chest pressure with diaphoresis and a new regional "
        f"ischemic ECG change. On structured scoring, {spans}. The clinical risk score is {total}."
    )
    features = deepcopy(item["stem_feature_map"]["features"])
    for index, (name, value) in enumerate(components):
        features.append({
            "feature_id": f"F-C{index}",
            "normalized_feature": f"the scored criterion {name}",
            "clinical_role": "SCORED_CRITERION",
            "polarity": "PRESENT" if value else "ABSENT",
            "inference_type": "EXPLICIT_FINDING",
            "source_span": _component_span(name, value),
        })
    features.append({
        "feature_id": "F-SCORE",
        "normalized_feature": "the stated clinical risk score",
        "clinical_role": "DERIVED_RISK_STRATIFICATION",
        "polarity": "PRESENT",
        "inference_type": "LABORATORY_PATTERN",
        "source_span": f"the clinical risk score is {total}",
    })
    _restem_1_4(item, stem, features)
    item["numeric_derivation_validation"].update({
        "no_derived_values_present": False,
        "derivations": [{
            "claim_ref": "NUM-SCORE",
            "formula_id": "SUM_OF_COMPONENTS",
            "input_values": [
                {
                    "component": name,
                    "value": value,
                    "units": "points",
                    "stem_feature_refs": [f"F-C{index}"],
                    "criterion_met": bool(value),
                }
                for index, (name, value) in enumerate(components)
            ],
            "units": "points",
            "asserted_in": "STEM",
            "asserted_text": f"The clinical risk score is {total}",
            "expected_result": total,
            "computed_result": sum(value for _, value in components),
            "tolerance": 0,
            "recomputable": True,
        }],
    })
    _rebind_1_4(item)
    return item, library, evidence


ALVARADO_COMPONENTS = [
    ("migration", 1), ("anorexia", 1), ("nausea_vomiting", 1), ("rlq_tenderness", 2),
    ("rebound", 0), ("elevated_temperature", 1), ("leukocytosis", 2), ("left_shift", 0),
]


def test_numeric_gate_rejects_a_score_its_own_components_do_not_produce():
    item, library, evidence = _score_item(5, ALVARADO_COMPONENTS)
    with pytest.raises(ChapterStagedGenerationError, match="recomputes to 8, not the asserted 5"):
        validate_staged_item(REPO, item, library, evidence)


# 14. The same score, stated correctly, is accepted.
def test_numeric_gate_accepts_a_correctly_summed_structured_score():
    item, library, evidence = _score_item(8, ALVARADO_COMPONENTS)
    assert validate_staged_item(REPO, item, library, evidence) is item


def test_numeric_gate_rejects_a_scored_component_that_contradicts_the_stem():
    """The r3 Alvarado defect: the total sums correctly, one component does not match the stem."""
    item, library, evidence = _score_item(8, ALVARADO_COMPONENTS)
    derivation = item["numeric_derivation_validation"]["derivations"][0]
    nausea = next(row for row in derivation["input_values"] if row["component"] == "nausea_vomiting")
    nausea.update({"value": 0, "criterion_met": False})
    derivation["expected_result"] = 7
    derivation["computed_result"] = 7
    derivation["asserted_text"] = "The clinical risk score is 8"
    _rebind_1_4(item)
    with pytest.raises(ChapterStagedGenerationError, match="contradicts the stem"):
        validate_staged_item(REPO, item, library, evidence)


def test_numeric_gate_rejects_a_scored_component_with_no_stem_grounding():
    item, library, evidence = _score_item(8, ALVARADO_COMPONENTS)
    derivation = item["numeric_derivation_validation"]["derivations"][0]
    del derivation["input_values"][0]["stem_feature_refs"]
    _rebind_1_4(item)
    with pytest.raises(ChapterStagedGenerationError, match="stem feature references"):
        validate_staged_item(REPO, item, library, evidence)


def test_numeric_gate_rejects_a_scored_component_citing_an_unknown_feature():
    item, library, evidence = _score_item(8, ALVARADO_COMPONENTS)
    derivation = item["numeric_derivation_validation"]["derivations"][0]
    derivation["input_values"][0]["stem_feature_refs"] = ["F-NOT-IN-THE-MAP"]
    _rebind_1_4(item)
    with pytest.raises(ChapterStagedGenerationError, match="not in the feature map"):
        validate_staged_item(REPO, item, library, evidence)


def test_numeric_gate_rejects_a_scored_component_whose_declared_criterion_contradicts_its_points():
    item, library, evidence = _score_item(8, ALVARADO_COMPONENTS)
    derivation = item["numeric_derivation_validation"]["derivations"][0]
    derivation["input_values"][0]["criterion_met"] = False
    _rebind_1_4(item)
    with pytest.raises(ChapterStagedGenerationError, match="declares criterion_met"):
        validate_staged_item(REPO, item, library, evidence)


def test_numeric_gate_requires_a_threshold_justification_for_a_measured_component():
    item, library, evidence = _score_item(8, ALVARADO_COMPONENTS)
    derivation = item["numeric_derivation_validation"]["derivations"][0]
    leukocytosis = next(row for row in derivation["input_values"] if row["component"] == "leukocytosis")
    leukocytosis["stem_feature_refs"] = ["F-SCORE"]
    _rebind_1_4(item)
    with pytest.raises(ChapterStagedGenerationError, match="threshold justification"):
        validate_staged_item(REPO, item, library, evidence)
    leukocytosis["threshold_justification"] = "The stated count sits above the scoring threshold."
    _rebind_1_4(item)
    assert validate_staged_item(REPO, item, library, evidence) is item


def test_numeric_gate_rejects_a_scored_component_grounded_only_in_an_inference():
    item, library, evidence = _score_item(8, ALVARADO_COMPONENTS)
    features = item["stem_feature_map"]["features"]
    features.append({
        "feature_id": "F-INTEGRATED-SCORE",
        "normalized_feature": "an integrated impression of intermediate risk",
        "clinical_role": "INTEGRATED_CLINICAL_INFERENCE",
        "polarity": "PRESENT",
        "inference_type": "INTEGRATED_INFERENCE",
        "derived_from": ["F-C0", "F-C1"],
    })
    item["numeric_derivation_validation"]["derivations"][0]["input_values"][0][
        "stem_feature_refs"
    ] = ["F-INTEGRATED-SCORE"]
    _restem_1_4(item, item["open_ended_stem_key"]["stem"], features)
    with pytest.raises(ChapterStagedGenerationError, match="cannot be scored from an inferred feature"):
        validate_staged_item(REPO, item, library, evidence)


def test_numeric_gate_rejects_a_stem_assertion_the_stem_never_makes():
    item, library, evidence = _score_item(8, ALVARADO_COMPONENTS)
    item["numeric_derivation_validation"]["derivations"][0]["asserted_text"] = "The score is 8 of 10"
    _rebind_1_4(item)
    with pytest.raises(ChapterStagedGenerationError, match="stem assertion the stem does not make"):
        validate_staged_item(REPO, item, library, evidence)


def test_numeric_gate_escalates_an_unrecomputable_value_to_an_independent_verifier():
    item, library, evidence = _score_item(8, ALVARADO_COMPONENTS)
    derivation = item["numeric_derivation_validation"]["derivations"][0]
    derivation.update({"formula_id": "PROPRIETARY_INDEX", "recomputable": False})
    _rebind_1_4(item)
    with pytest.raises(ChapterStagedGenerationError, match="requires independent numeric verification"):
        validate_staged_item(REPO, item, library, evidence)
    derivation["independent_numeric_verification"] = {
        "verifier_id": "independent-numeric-verifier",
        "method": "Recomputed by hand from the published index definition.",
        "verdict": "PASS",
    }
    _rebind_1_4(item)
    assert validate_staged_item(REPO, item, library, evidence) is item


@pytest.mark.parametrize(
    "formula_id, inputs, expected",
    [
        ("ARR", {"control_event_rate": "0.20", "experimental_event_rate": "0.16"}, "0.04"),
        ("RRR", {"control_event_rate": "0.20", "experimental_event_rate": "0.16"}, "0.2"),
        ("NNT", {"absolute_risk_reduction": "0.04"}, "25"),
        ("SENSITIVITY", {"true_positives": "90", "false_negatives": "10"}, "0.9"),
        ("SPECIFICITY", {"true_negatives": "80", "false_positives": "20"}, "0.8"),
        ("PPV", {"true_positives": "90", "false_positives": "20"}, "0.8181818181818181818181818182"),
        ("LR_POSITIVE", {"sensitivity": "0.9", "specificity": "0.8"}, "4.5"),
        ("LR_NEGATIVE", {"sensitivity": "0.9", "specificity": "0.8"}, "0.125"),
        ("PERCENTAGE", {"numerator": "3", "denominator": "8"}, "37.5"),
        ("WEIGHT_BASED_DOSE", {"weight_kg": "14.5", "dose_per_kg": "15"}, "217.5"),
    ],
)
def test_derived_quantities_are_recomputed_deterministically(formula_id, inputs, expected):
    from decimal import Decimal

    values = [
        {"component": name, "value": value, "units": "unit"} for name, value in inputs.items()
    ]
    assert compute_derived_value(formula_id, values) == Decimal(expected)


def test_derived_quantity_recomputation_fails_closed_on_bad_inputs():
    with pytest.raises(ChapterStagedGenerationError, match="not deterministically recomputable"):
        compute_derived_value("MADE_UP", [{"component": "a", "value": 1, "units": "u"}])
    with pytest.raises(ChapterStagedGenerationError, match="inputs are incomplete"):
        compute_derived_value("ARR", [{"component": "control_event_rate", "value": 1, "units": "u"}])
    with pytest.raises(ChapterStagedGenerationError, match="divides by zero"):
        compute_derived_value("NNT", [{"component": "absolute_risk_reduction", "value": 0, "units": "u"}])


# 15. Neighbouring public-health concepts along one semantic dimension.
def test_phelo_style_neighbouring_concepts_share_one_semantic_dimension():
    item, library, evidence = _staged_1_4()
    for row in item["option_semantic_category_parity"]["options"]:
        row.update({
            "option_semantic_type": "EPIDEMIOLOGIC_CONCEPT",
            "option_action_type": "CLASSIFY",
            "option_scope": "SCREENING_PROGRAMME_BIAS_ATTRIBUTION",
            "decision_granularity": "OTHER",
            "completeness_level": "SINGLE_ACTION",
        })
    for row in item["option_realization"]["options"]:
        row["decision_granularity"] = "OTHER"
        row["semantic_meaning_fingerprint"] = _sha({
            "semantic_option_text": row["semantic_option_text"],
            "decision_granularity": row["decision_granularity"],
            "action_or_concept_head": row["action_or_concept_head"],
            "medically_required_modifiers": row["medically_required_modifiers"],
            "independent_action_components": row["independent_action_components"],
            "specificity_level": row["specificity_level"],
        })
    for row in item["semantic_polarity_completeness_preflight"]["options"]:
        row["decision_granularity"] = "OTHER"
    _rebind_1_4(item)
    assert validate_staged_item(REPO, item, library, evidence) is item


# 16. A psychiatric differential decided by course rather than by a single clause.
def test_psychiatry_style_longitudinal_differential_is_accepted():
    item, library, evidence = _staged_1_4()
    stem = (
        "A patient describes 7 weeks of continuously low mood with early-morning wakening "
        "and weight loss, beginning after a promotion and unchanged since. Function at work "
        "has deteriorated over the same period."
    )
    features = [
        {"feature_id": "F-COURSE", "normalized_feature": "seven-week continuous episode",
         "clinical_role": "TIME_COURSE", "polarity": "PRESENT",
         "inference_type": "TIME_COURSE", "source_span": "7 weeks of continuously low mood"},
        {"feature_id": "F-NEUROVEG", "normalized_feature": "neurovegetative features present",
         "clinical_role": "SYMPTOM_CLUSTER", "polarity": "PRESENT",
         "inference_type": "EXPLICIT_FINDING", "source_span": "early-morning wakening"},
        {"feature_id": "F-FUNCTION", "normalized_feature": "functional deterioration",
         "clinical_role": "SEVERITY_MARKER", "polarity": "PRESENT",
         "inference_type": "EXPLICIT_FINDING", "source_span": "function at work has deteriorated"},
        {"feature_id": "F-LONGITUDINAL", "normalized_feature":
         "an episodic rather than chronic longitudinal course with functional impact",
         "clinical_role": "INTEGRATED_CLINICAL_INFERENCE", "polarity": "PRESENT",
         "inference_type": "INTEGRATED_INFERENCE",
         "derived_from": ["F-COURSE", "F-NEUROVEG", "F-FUNCTION"]},
    ]
    _restem_1_4(item, stem, features)
    for proof in item["contextual_competitor_proof"]["proofs"]:
        proof["supporting_stem_feature_ids"] = ["F-NEUROVEG", "F-FUNCTION"]
        proof["defeating_stem_feature_ids"] = ["F-LONGITUDINAL"]
        proof["post_stem_status"] = "STRONG_COMPETITOR"
        proof["adversarial_hidden_key_test"]["defeating_feature"] = "F-LONGITUDINAL"
    for row in item["terminal_exclusion_review"]["assessments"]:
        row["defeating_stem_feature_ids"] = ["F-LONGITUDINAL"]
        row["exclusion_class"] = "LEGITIMATE_SINGLE_DISCRIMINATOR"
    _rebind_terminal_review(item)
    assert validate_staged_item(REPO, item, library, evidence) is item


def test_key_rationale_must_explain_rather_than_instruct():
    item, library, evidence = _staged_1_4()
    directive = "Use the regional ischemic change to reject the listed alternatives."
    item["open_ended_stem_key"]["reasoning_chain"][-1] = directive
    item["rationales"]["correct"]["why_best"] = directive
    _restem_1_4(item, item["open_ended_stem_key"]["stem"], item["stem_feature_map"]["features"])
    with pytest.raises(ChapterStagedGenerationError, match="IMPERATIVE_KEY_RATIONALE"):
        validate_staged_item(REPO, item, library, evidence)


def test_realized_options_must_not_answer_a_negated_stem_clause_with_its_own_words():
    assert find_negated_stem_echo_cues(
        "The pamphlet contains no written description of the potential harms.",
        [
            {"role": "KEY", "text": "Provide written information about the potential harms"},
            {"role": "DISTRACTOR", "text": "Proceed with the appointment as booked"},
            {"role": "DISTRACTOR", "text": "Repeat the verbal explanation"},
        ],
    ) == ["KEY_ONLY_NEGATED_STEM_ECHO"]
    assert find_negated_stem_echo_cues(
        "The patient has no fever and no rigors.",
        [
            {"role": "KEY", "text": "Continue exclusive breastfeeding"},
            {"role": "DISTRACTOR", "text": "Start oral antibiotics"},
            {"role": "DISTRACTOR", "text": "Arrange breast ultrasonography"},
        ],
    ) == []


def test_calibrated_rationale_standard_separates_fatal_defects_from_enhancements():
    passing = {
        "fatal_criteria": {name: "PASS" for name in [
            "decisive_reason_stated", "distractor_discriminators_stated",
            "no_unsupported_teaching_claim", "evidence_linkage_present",
        ]},
        "enhancement_opportunities": [
            {"class": "EXPLANATORY_REGISTER", "note": "The key rationale reads as a directive."},
            {"class": "TEACHING_VALUE", "note": "The threshold could be named."},
        ],
        "verdict": "PASS",
    }
    assert validate_calibrated_rationale_assessment(passing) == "PASS"
    fatal = deepcopy(passing)
    fatal["fatal_criteria"]["no_unsupported_teaching_claim"] = "FAIL"
    fatal["verdict"] = "FAIL"
    assert validate_calibrated_rationale_assessment(fatal) == "FAIL"
    inconsistent = deepcopy(passing)
    inconsistent["fatal_criteria"]["decisive_reason_stated"] = "FAIL"
    with pytest.raises(ChapterStagedGenerationError, match="does not reconcile"):
        validate_calibrated_rationale_assessment(inconsistent)


def test_imperative_register_detector_is_head_anchored():
    assert find_rationale_register_defects("Select the safest option.") == ["IMPERATIVE_KEY_RATIONALE"]
    assert find_rationale_register_defects(
        "The regional ischemic change makes acute coronary syndrome the single best diagnosis."
    ) == []
