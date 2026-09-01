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
    find_option_text_cues,
    find_option_shape_cues,
    find_option_position_cues,
    resolve_chapter_anchor,
    retrieve_global_contrasts,
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
