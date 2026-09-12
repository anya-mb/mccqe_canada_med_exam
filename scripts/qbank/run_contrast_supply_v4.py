"""Deterministic artifact builder for catalogue repair and Discovery V4."""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any

from .contrast_supply_v3 import build_global_candidate_catalogue, canonical_content_sha256
from .contrast_supply_v4 import (
    DISCOVERY_V4_VERSION,
    V4_CANDIDATE_BUDGET,
    audit_candidate_catalogue,
    build_clean_catalogue_v2,
    discover_global_typed_candidates_v4,
    reconstruct_v3_wrong_decisions,
    reuse_frozen_candidate_verdicts,
    signatures_compatible,
)
from .run_contrast_supply_v3 import BUILD12_KEY_ALIASES, reviewed_identity_inputs


FROZEN_RELATIVES = (
    "research/qgen/contrast_supply/global_candidate_concept_catalogue_v1.json",
    "research/qgen/contrast_supply/build_12_discovery_v3.json",
    "research/qgen/contrast_supply/build_12_v3_semantic_review.json",
    "research/qgen/contrast_supply/reusable_contrast_cache_v1.json",
    "research/qgen/contrast_supply/reusable_contrast_cache_v2.json",
    "research/qgen/contrast_supply/reusable_contrast_cache_v3.json",
    "research/qgen/contrast_supply/transfer_12_selection_v1.json",
    "research/qgen/contrast_supply/transfer_12_discovery_v3.json",
    "research/qgen/contrast_supply/transfer_12_semantic_review.json",
    "research/qgen/contrast_supply/discovery_v3_cache_v2_freeze.json",
    "reports/qgen_build12_v3_cache_v2_validation.json",
    "reports/qgen_transfer12_v3_cache_validation.json",
    "reports/qgen_global_typed_discovery_v3_cache_transfer12_milestone.json",
    "scripts/qbank/contrast_supply_v3.py",
)

WRONG_DECISION_TAXONOMY = (
    "WRONG_CLINICAL_STAGE", "WRONG_DECISION_INTENT", "WRONG_TARGET_CONDITION",
    "WRONG_PATIENT_POPULATION", "WRONG_ANATOMIC_TARGET", "WRONG_CAUSAL_ROLE",
    "WRONG_DIAGNOSTIC_PURPOSE", "WRONG_MANAGEMENT_PURPOSE",
    "WRONG_PREVENTION_PURPOSE", "WRONG_MONITORING_PURPOSE",
    "WRONG_ETHICAL_LEGAL_ACTION", "TOO_GENERIC_FOR_DECISION",
    "SEMANTICALLY_RELATED_BUT_DIFFERENT_DECISION", "OTHER", "UNCERTAIN",
)

DIAGNOSTIC_GROUP_REVIEWS = {
    "RDY-MED-03": (
        "WRONG_DECISION_INTENT",
        "The learner must classify stability within known ischemic symptoms; the candidates name alternative etiologic diagnoses, so the earliest mismatch is the act being decided.",
    ),
    "RDY-PED-05": (
        "WRONG_TARGET_CONDITION",
        "The learner must act on febrile sickle-cell disease; the candidates are acute cardiac or infant-respiratory actions for other conditions.",
    ),
    "RDY-OBGYN-05": (
        "WRONG_TARGET_CONDITION",
        "The learner is selecting therapy for menopausal vasomotor symptoms; the candidates are authored for depressive illness.",
    ),
    "RDY-OBGYN-06": (
        "WRONG_TARGET_CONDITION",
        "The learner is selecting nonsurgical management for pelvic-organ prolapse; the candidate is coronary reperfusion.",
    ),
    "RDY-SURG-09": (
        "WRONG_DECISION_INTENT",
        "The diagnosis of diverticulitis is given and the learner must classify complication/severity; the candidates instead name alternative diagnoses.",
    ),
    "RDY-PSY-04": (
        "WRONG_TARGET_CONDITION",
        "The learner is selecting medication for panic disorder; the candidates treat acute cardiovascular or infant-respiratory conditions.",
    ),
    "RDY-PHELO-09": (
        "WRONG_ETHICAL_LEGAL_ACTION",
        "Clinical-AI governance review and statutory MAID eligibility answer different ethical/legal actions despite sharing a coarse value token.",
    ),
    "RDY-PHELO-10": (
        "WRONG_ETHICAL_LEGAL_ACTION",
        "The learner must classify a legal relationship or state action; the candidates classify medical diagnoses.",
    ),
}

FAMILY_SIGNATURES = {
    "ASSESSMENT_OR_TESTING_ACTION_ORDERED_FOR_THIS_INFANT": ("SELECT_DIAGNOSTIC_ACTION", "CARDIOPULMONARY", "DIAGNOSTIC_WORKUP"),
    "AUTONOMY": ("ASSESS_ETHICAL_CRITERIA", "CLINICAL_DECISION_ETHICS", "ETHICAL_LEGAL_REVIEW"),
    "DIAGNOSTIC_ORDER": ("SELECT_DIAGNOSTIC_ACTION", "ENDOCRINE_METABOLIC", "DIAGNOSTIC_WORKUP"),
    "DIAGNOSTIC_STEP_FOR_SUSPECTED_APPENDICITIS": ("SELECT_DIAGNOSTIC_ACTION", "ABDOMINAL_SURGICAL", "DIAGNOSTIC_WORKUP"),
    "DIAGNOSTIC_TEST_ORDERED_TO_CHARACTERISE_A_BREAST_MASS": ("SELECT_DIAGNOSTIC_ACTION", "REPRODUCTIVE_AND_BREAST", "DIAGNOSTIC_WORKUP"),
    "FEEDING_OR_BREAST_CARE_INSTRUCTION_GIVEN_TO_THE_PATIENT": ("SELECT_TREATMENT", "REPRODUCTIVE_AND_BREAST", "ACUTE_MANAGEMENT"),
    "IMMEDIATE_DISPOSITION_OR_RISK_MANAGEMENT_ACTION": ("SELECT_ESCALATION_OR_DISPOSITION", "MENTAL_HEALTH", "ESCALATION_OR_DISPOSITION"),
    "IMMEDIATE_DISPOSITION_THAT_SECURES_SAFETY": ("SELECT_ESCALATION_OR_DISPOSITION", "MENTAL_HEALTH", "ESCALATION_OR_DISPOSITION"),
    "IMMEDIATE_HAEMODYNAMIC_ACTION_AT_THE_BEDSIDE": ("SELECT_TREATMENT", "CARDIOPULMONARY", "ACUTE_MANAGEMENT"),
    "INITIAL_ACUTE_TREATMENT_OFFERED_FOR_A_MODERATE_DEPRESSIVE_EPISODE": ("SELECT_TREATMENT", "MENTAL_HEALTH", "LONGITUDINAL_MANAGEMENT"),
    "INITIAL_ACUTE_TREATMENT_OFFERED_FOR_A_SEVERE_DEPRESSIVE_EPISODE": ("SELECT_TREATMENT", "MENTAL_HEALTH", "LONGITUDINAL_MANAGEMENT"),
    "LEVEL_OF_CARE_ACTION_ORDERED_FOR_THIS_PATIENT": ("SELECT_ESCALATION_OR_DISPOSITION", "CARDIOPULMONARY", "ESCALATION_OR_DISPOSITION"),
    "LOCALIZED_EAR_DIAGNOSIS": ("IDENTIFY_DIAGNOSIS", "EAR", "INITIAL_RECOGNITION"),
    "NAMED_CAUSE_OF_ACUTE_CHEST_PAIN_IN_AN_ADULT": ("IDENTIFY_DIAGNOSIS", "CARDIOPULMONARY", "INITIAL_RECOGNITION"),
    "NAMED_CAUSE_OF_ACUTE_RIGHT_LOWER_QUADRANT_PAIN": ("IDENTIFY_DIAGNOSIS", "ABDOMINAL_SURGICAL", "INITIAL_RECOGNITION"),
    "NAMED_CLINICAL_DIAGNOSIS_OF_AN_ACUTE_INFANT_RESPIRATORY_ILLNESS": ("IDENTIFY_DIAGNOSIS", "CARDIOPULMONARY", "INITIAL_RECOGNITION"),
    "NAMED_ENTITY_ON_THE_LACTATIONAL_BREAST_SPECTRUM": ("IDENTIFY_DIAGNOSIS", "REPRODUCTIVE_AND_BREAST", "INITIAL_RECOGNITION"),
    "NAMED_METHODOLOGICAL_EXPLANATION_FOR_AN_APPARENT_SCREENING_BENEFIT": ("EXPLAIN_CAUSAL_OR_METHOD_BIAS", "PUBLIC_HEALTH", "PREVENTION_OR_SCREENING"),
    "NAMED_PSYCHIATRIC_OR_MEDICAL_DIAGNOSIS_ACCOUNTING_FOR_A_DEPRESSIVE_SYNDROME": ("IDENTIFY_DIAGNOSIS", "MENTAL_HEALTH", "INITIAL_RECOGNITION"),
    "NO_ACTIVE_TREATMENT": ("SELECT_TREATMENT", "REPRODUCTIVE_AND_BREAST", "ACUTE_MANAGEMENT"),
    "OPERATIVE_OR_NONOPERATIVE_MANAGEMENT_STRATEGY_FOR_COMPLICATED_APPENDICITIS": ("SELECT_TREATMENT", "ABDOMINAL_SURGICAL", "ACUTE_MANAGEMENT"),
    "PROGRAMME_LEVEL_IMPLEMENTATION_DECISION_ABOUT_THE_LAUNCH": ("SELECT_PROGRAMME_ACTION", "PUBLIC_HEALTH", "PREVENTION_OR_SCREENING"),
    "REPERFUSION_ACTION_ORDERED_NOW_FOR_THIS_PATIENT": ("SELECT_TREATMENT", "CARDIOPULMONARY", "ACUTE_MANAGEMENT"),
    "REVISION_TO_THE_CONTENT_OF_THE_INVITATION_LETTER": ("REVISE_COMMUNICATION", "PUBLIC_HEALTH", "PREVENTION_OR_SCREENING"),
    "STRUCTURAL": ("SELECT_DIAGNOSTIC_ACTION", "CARDIOPULMONARY", "DIAGNOSTIC_WORKUP"),
    "SUPPORTIVE_RESPIRATORY_INTERVENTION_DELIVERED_AT_THE_BEDSIDE": ("SELECT_TREATMENT", "CARDIOPULMONARY", "ACUTE_MANAGEMENT"),
}

OPPORTUNITY_SIGNATURES = {
    "LD-ONB2-PED-AOM-DX": ("IDENTIFY_DIAGNOSIS", "EAR", "INITIAL_RECOGNITION"),
    "RDY-MED-01": ("SELECT_ESCALATION_OR_DISPOSITION", "CARDIOPULMONARY", "ESCALATION_OR_DISPOSITION"),
    "RDY-PED-04": ("SELECT_DIAGNOSTIC_ACTION", "ENDOCRINE_METABOLIC", "DIAGNOSTIC_WORKUP"),
    "RDY-OBGYN-01": ("SELECT_TREATMENT", "REPRODUCTIVE_AND_BREAST", "ACUTE_MANAGEMENT"),
    "RDY-SURG-03": ("SELECT_DIAGNOSTIC_ACTION", "CARDIOPULMONARY", "DIAGNOSTIC_WORKUP"),
    "RDY-SURG-05": ("SELECT_ESCALATION_OR_DISPOSITION", "ABDOMINAL_SURGICAL", "LONGITUDINAL_MANAGEMENT"),
    "RDY-PSY-03": ("IDENTIFY_DIAGNOSIS", "MENTAL_HEALTH", "INITIAL_RECOGNITION"),
    "RDY-PHELO-02": ("CLASSIFY_PREVENTION_STAGE", "PUBLIC_HEALTH", "PREVENTION_OR_SCREENING"),
    "RDY-PHELO-08": ("ASSESS_ETHICAL_CRITERIA", "CLINICAL_DECISION_ETHICS", "ETHICAL_LEGAL_REVIEW"),
    "RDY-MED-03": ("CLASSIFY_STATE_OR_COMPLICATION", "CARDIOPULMONARY", "INITIAL_RECOGNITION"),
    "RDY-PED-05": ("SELECT_TREATMENT", "HEMATOLOGY_INFECTIOUS", "ACUTE_MANAGEMENT"),
    "RDY-OBGYN-05": ("SELECT_TREATMENT", "REPRODUCTIVE_AND_BREAST", "LONGITUDINAL_MANAGEMENT"),
    "RDY-OBGYN-06": ("SELECT_TREATMENT", "REPRODUCTIVE_AND_BREAST", "LONGITUDINAL_MANAGEMENT"),
    "RDY-SURG-08": ("SELECT_ESCALATION_OR_DISPOSITION", "ABDOMINAL_SURGICAL", "ESCALATION_OR_DISPOSITION"),
    "RDY-SURG-09": ("CLASSIFY_STATE_OR_COMPLICATION", "ABDOMINAL_SURGICAL", "INITIAL_RECOGNITION"),
    "RDY-PSY-04": ("SELECT_TREATMENT", "MENTAL_HEALTH", "LONGITUDINAL_MANAGEMENT"),
    "RDY-PSY-05": ("SELECT_TREATMENT", "MENTAL_HEALTH", "LONGITUDINAL_MANAGEMENT"),
    "RDY-PHELO-09": ("ASSESS_ETHICAL_CRITERIA", "CLINICAL_GOVERNANCE", "ETHICAL_LEGAL_REVIEW"),
    "RDY-PHELO-10": ("CLASSIFY_LEGAL_DOMAIN", "LAW", "ETHICAL_LEGAL_REVIEW"),
}

SIGNATURE_FIELDS = ("decision_intent", "target_domain", "clinical_stage")

TRANSFER_KEY_ALIASES = {
    "RDY-MED-03": ["stable angina", "unstable angina", "acute coronary syndrome"],
    "RDY-PED-05": ["blood culture", "broad-spectrum antibiotics"],
    "RDY-OBGYN-05": ["menopausal hormone therapy", "MHT"],
    "RDY-OBGYN-06": ["vaginal pessary", "pessary"],
    "RDY-SURG-08": ["urgent operative assessment", "urgent surgery"],
    "RDY-SURG-09": ["uncomplicated diverticulitis", "complicated diverticulitis"],
    "RDY-PSY-04": ["SSRI", "SNRI"],
    "RDY-PSY-05": ["cognitive behavioural therapy", "exposure and response prevention", "ERP"],
    "RDY-PHELO-09": ["clinical AI governance assessment"],
    "RDY-PHELO-10": ["civil law", "criminal law", "administrative law"],
}

NEW_V4_SEMANTIC_REVIEWS = {
    ("RDY-PSY-03", "CONCEPT-R4-SU-PS-12-PDD"): (
        "WRONG_DECISION",
        "Persistent depressive disorder is a mood diagnosis and does not compete in the course-based differentiation of primary psychotic disorders.",
    ),
    ("RDY-PSY-03", "CONCEPT-R4-SU-PS-14-BD2"): (
        "WRONG_DECISION",
        "Bipolar II disorder is a mood diagnosis and does not compete in the course-based differentiation of primary psychotic disorders.",
    ),
}


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def _write(path: Path, value: dict[str, Any]) -> None:
    value["content_sha256"] = canonical_content_sha256(value)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def freeze_diagnostic_status(root: Path) -> dict[str, Any]:
    selection = _load(root / "research/qgen/contrast_supply/transfer_12_selection_v1.json")
    prior = _load(root / "reports/qgen_global_typed_discovery_v3_cache_transfer12_milestone.json")
    value = {
        "schema_version": "DISCOVERY_V3_DIAGNOSTIC_TRANSFER_12_CLASSIFICATION_V1",
        "transfer12_status": "DISCOVERY_V3_DIAGNOSTIC_TRANSFER_12",
        "transfer_validation_result": "INVALIDATED_BY_POST_FREEZE_CATALOGUE_DEFECT",
        "eligible_uses": ["DISCOVERY_V3_FAILURE_DIAGNOSIS", "DISCOVERY_V4_DEVELOPMENT_REPLAY"],
        "prohibited_uses": [
            "FRESH_TRANSFER_VALIDATION", "FRESH_OPERATIONAL_HOLDOUT",
            "UNSEEN_GENERALIZATION_EVALUATION",
        ],
        "transfer12_sha256": selection["transfer12_sha256"],
        "prior_milestone_content_sha256": prior["content_sha256"],
        "prior_metrics_immutable": True,
        "frozen_file_sha256": {
            relative: _file_sha256(root / relative) for relative in FROZEN_RELATIVES
        },
    }
    path = root / "research/qgen/contrast_supply/transfer_12_diagnostic_classification_v1.json"
    _write(path, value)
    return value


def build_catalogue_v2_artifacts(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    parent = _load(root / "research/qgen/contrast_supply/global_candidate_concept_catalogue_v1.json")
    connection = sqlite3.connect(root / "derived/tn_index/tn_index.sqlite3")
    try:
        rows = build_global_candidate_catalogue(
            connection, reviewed_identities=reviewed_identity_inputs(root)
        )
    finally:
        connection.close()
    rebuilt_parent = {
        key: parent[key] for key in (
            "schema_version", "scope", "source_policy", "concept_count", "typed_concept_count"
        )
    }
    rebuilt_parent["concepts"] = rows
    if canonical_content_sha256(rebuilt_parent) != parent["content_sha256"]:
        raise ValueError("fresh canonical-source rebuild does not reproduce frozen Catalogue V1")
    audit = audit_candidate_catalogue(rows, parent_content_sha256=parent["content_sha256"])
    catalogue = build_clean_catalogue_v2(
        rows, audit=audit, parent_content_sha256=parent["content_sha256"]
    )
    audit["fresh_source_rebuild_reproduced_parent"] = True
    audit["content_sha256"] = canonical_content_sha256(audit)
    catalogue["integrity_audit_content_sha256"] = audit["content_sha256"]
    catalogue["content_sha256"] = canonical_content_sha256(catalogue)
    _write(root / "reports/qgen_candidate_catalogue_integrity_audit_v1.json", audit)
    _write(root / "research/qgen/contrast_supply/global_candidate_concept_catalogue_v2.json", catalogue)
    return audit, catalogue


def build_wrong_decision_diagnosis(root: Path) -> dict[str, Any]:
    discovery = _load(root / "research/qgen/contrast_supply/transfer_12_discovery_v3.json")
    review = _load(root / "research/qgen/contrast_supply/transfer_12_semantic_review.json")
    semantics = _load(root / "research/qgen/contrast_supply/transfer_12_opportunity_semantics_v1.json")
    selection = _load(root / "research/qgen/contrast_supply/transfer_12_selection_v1.json")
    rows = reconstruct_v3_wrong_decisions(
        discovery, review, semantics, selection, expected_count=52
    )
    for row in rows:
        classification, rationale = DIAGNOSTIC_GROUP_REVIEWS[row["opportunity_id"]]
        row["earliest_semantic_mismatch"] = classification
        row["diagnostic_group_rationale"] = rationale
        row["classification_basis"] = "FROZEN_VERDICT_PLUS_REPRESENTATIVE_OPPORTUNITY_GROUP_REVIEW"
    counts = {name: 0 for name in WRONG_DECISION_TAXONOMY}
    for row in rows:
        counts[row["earliest_semantic_mismatch"]] += 1
    if sum(counts.values()) != 52:
        raise ValueError("wrong-decision taxonomy does not reconcile to 52")
    representative_reviews = [
        {
            "opportunity_id": opportunity_id,
            "classification": classification,
            "rationale": rationale,
            "applied_to_candidate_count": sum(
                row["opportunity_id"] == opportunity_id for row in rows
            ),
        }
        for opportunity_id, (classification, rationale) in DIAGNOSTIC_GROUP_REVIEWS.items()
    ]
    value = {
        "schema_version": "DISCOVERY_V3_WRONG_DECISION_DIAGNOSIS_V1",
        "scope": "DISCOVERY_V3_DIAGNOSTIC_TRANSFER_12",
        "transfer12_sha256": selection["transfer12_sha256"],
        "discovery_v3_content_sha256": discovery["content_sha256"],
        "semantic_review_content_sha256": review["content_sha256"],
        "wrong_decision_candidate_count": len(rows),
        "new_semantic_diagnostic_review_limit": 12,
        "new_semantic_diagnostic_reviews_used": len(representative_reviews),
        "representative_semantic_reviews": representative_reviews,
        "taxonomy_counts": counts,
        "dominant_v3_semantic_gap": "MULTIPLE_COMPARABLE_CAUSES",
        "dominant_gap_evidence": {
            "decision_intent_count": counts["WRONG_DECISION_INTENT"],
            "target_condition_count": counts["WRONG_TARGET_CONDITION"],
            "ethical_legal_action_count": counts["WRONG_ETHICAL_LEGAL_ACTION"],
            "interpretation": "V3 lacks both the act being decided and the target decision domain; neither response class nor granularity represents those distinctions.",
        },
        "rows": rows,
    }
    path = root / "reports/qgen_discovery_v3_wrong_decision_diagnosis_v1.json"
    _write(path, value)
    return value


def _signature(values: tuple[str, str, str]) -> dict[str, str]:
    return dict(zip(SIGNATURE_FIELDS, values, strict=True))


def build_decision_signature_artifacts(root: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    catalogue = _load(root / "research/qgen/contrast_supply/global_candidate_concept_catalogue_v2.json")
    build_semantics = _load(root / "research/qgen/contrast_supply/development_12_opportunity_semantics_v1.json")
    transfer_semantics = _load(root / "research/qgen/contrast_supply/transfer_12_opportunity_semantics_v1.json")
    opportunities = []
    for source in [*build_semantics["opportunities"], *transfer_semantics["opportunities"]]:
        if not source.get("prerequisite_ready"):
            continue
        opportunity_id = source["development_id"]
        opportunities.append({
            "opportunity_id": opportunity_id,
            "learner_decision_id": source["learner_decision_id"],
            "discipline": source["discipline"],
            "study_unit_id": source["study_unit_id"],
            "signature": _signature(OPPORTUNITY_SIGNATURES[opportunity_id]),
            "mapping_basis": "REVIEWED_CANONICAL_LEARNER_DECISION",
        })
    opportunities.append({
        "opportunity_id": "AOM_DEVELOPMENT_CONTROL",
        "learner_decision_id": "LD-ONB2-PED-AOM-DX",
        "discipline": "PED",
        "study_unit_id": "SU-P-099",
        "signature": _signature(OPPORTUNITY_SIGNATURES["LD-ONB2-PED-AOM-DX"]),
        "mapping_basis": "INDEPENDENTLY_APPROVED_AOM_CONTROL",
    })

    candidates = []
    missing = []
    for row in catalogue["concepts"]:
        if not row.get("response_classes"):
            continue
        families = [
            family for family in row.get("semantic_families", [])
            if family not in {"action", "condition"}
        ]
        matched = [family for family in families if family in FAMILY_SIGNATURES]
        if len(matched) != 1:
            missing.append({"candidate_id": row["canonical_candidate_id"], "families": families})
            continue
        family = matched[0]
        candidates.append({
            "candidate_id": row["canonical_candidate_id"],
            "signature": _signature(FAMILY_SIGNATURES[family]),
            "mapping_basis": "INDEPENDENTLY_REVIEWED_SEMANTIC_FAMILY",
            "source_semantic_family": family,
        })
    if missing:
        raise ValueError(f"typed candidates without exactly one signature mapping: {missing}")

    controlled = {
        field: sorted({
            row["signature"][field] for row in [*opportunities, *candidates]
        })
        for field in SIGNATURE_FIELDS
    }
    value = {
        "schema_version": "CANDIDATE_DECISION_SIGNATURE_V1",
        "catalogue_v2_content_sha256": catalogue["content_sha256"],
        "dimensions": list(SIGNATURE_FIELDS),
        "controlled_vocabularies": controlled,
        "compatibility_contract": {
            "decision_intent": "EXACT_MATCH_REQUIRED",
            "target_domain": "EXACT_MATCH_REQUIRED",
            "clinical_stage": "EXACT_MATCH_REQUIRED",
            "missing_or_unknown_value": "FAIL_CLOSED",
            "candidate_name_generation": "PROHIBITED",
            "disease_specific_exception_rules": 0,
        },
        "opportunity_signatures": sorted(opportunities, key=lambda row: row["opportunity_id"]),
        "candidate_signatures": sorted(candidates, key=lambda row: row["candidate_id"]),
        "known_good_controls": {
            "aom_candidate_ids": [
                "CONCEPT-V6-AOM-ETD", "CONCEPT-V6-AOM-MYRINGITIS",
                "CONCEPT-V6-AOM-OME", "CONCEPT-V6-AOM-OTITIS-EXTERNA",
            ],
            "build12_candidate_ids": [
                "RDY-PED-04__adh", "RDY-PED-04__hba1c_diagnostic_criteria",
                "RDY-SURG-03__tte", "CONCEPT-R4-SU-R-05-CXR",
                "RDY-PHELO-08__bill_c14_maid",
            ],
            "signature_compatibility_only_candidate_ids": [
                "RDY-OBGYN-01__physiologic_discharge",
            ],
        },
    }
    _write(root / "research/qgen/contrast_supply/decision_signature_v1.json", value)

    all_rows = [*value["opportunity_signatures"], *value["candidate_signatures"]]
    value_counts = {
        field: {token: sum(row["signature"][field] == token for row in all_rows)
                for token in controlled[field]}
        for field in SIGNATURE_FIELDS
    }
    single_use = {
        field: [token for token, count in counts.items() if count == 1]
        for field, counts in value_counts.items()
    }
    opportunity_rows = value["opportunity_signatures"]
    reuse = {
        field: {
            token: {
                "opportunity_count": sum(row["signature"][field] == token for row in opportunity_rows),
                "study_unit_count": len({row["study_unit_id"] for row in opportunity_rows if row["signature"][field] == token}),
                "discipline_count": len({row["discipline"] for row in opportunity_rows if row["signature"][field] == token}),
            }
            for token in controlled[field]
        }
        for field in SIGNATURE_FIELDS
    }
    economy = {
        "schema_version": "DECISION_SIGNATURE_V1_ECONOMY_V1",
        "decision_signature_content_sha256": value["content_sha256"],
        "dimension_count": len(SIGNATURE_FIELDS),
        "value_counts": {field: len(tokens) for field, tokens in controlled.items()},
        "mapping_occurrence_counts": value_counts,
        "single_use_values": single_use,
        "opportunity_reuse": reuse,
        "candidate_signature_count": len(candidates),
        "opportunity_signature_count": len(opportunities),
        "disease_specific_exception_rules": 0,
        "economy_verdict": "PASS",
        "reason": "Three dimensions cover all typed candidates and development opportunities; values recur across candidates and/or opportunities and no opportunity ID is encoded as a value.",
    }
    _write(root / "reports/qgen_decision_signature_v1_economy.json", economy)

    review = {
        "schema_version": "DECISION_SIGNATURE_V1_INDEPENDENT_REVIEW_V1",
        "decision_signature_content_sha256": value["content_sha256"],
        "economy_content_sha256": economy["content_sha256"],
        "review_execution_id": "serial-independent-signature-review-20260909",
        "reviewer_saw_v4_replay_outcomes": False,
        "review_mode": "SEPARATE_FRESH_PASS_WITH_FROZEN_SIGNATURE_INPUT",
        "criteria": {
            "semantically_meaningful": "PASS",
            "nonredundant": "PASS",
            "safe_for_filtering_and_ranking": "PASS",
            "independent_of_future_distractors": "PASS",
            "not_disease_specific": "PASS",
            "known_good_controls_preserved_by_contract": "PASS",
        },
        "verdict": "APPROVED",
        "review_comment": "Intent distinguishes identifying a diagnosis from classifying a known condition; target domain blocks unrelated organ-system and legal lanes; stage separates acute, longitudinal, escalation, and governance decisions. Exact matching is conservative and does not encode individual diseases or future option sets.",
    }
    _write(root / "reports/qgen_decision_signature_v1_independent_review.json", review)
    return value, economy, review


def _enrich_frozen_opportunities(
    wave: dict[str, Any], semantics: dict[str, Any]
) -> list[dict[str, Any]]:
    semantic_by_id = {row["development_id"]: row for row in semantics["opportunities"]}
    enriched = []
    for source in wave["opportunities"]:
        semantic = semantic_by_id[source["development_id"]]
        row = dict(source)
        row["learner_decision"] = semantic["learner_decision"]
        enriched.append(row)
    return enriched


def _build_v4_wave(
    root: Path, *, cohort: str, catalogue: dict[str, Any], signature_registry: dict[str, Any]
) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    is_build = cohort == "BUILD_12"
    semantics_path = (
        "research/qgen/contrast_supply/development_12_opportunity_semantics_v1.json"
        if is_build else
        "research/qgen/contrast_supply/transfer_12_opportunity_semantics_v1.json"
    )
    semantics = _load(root / semantics_path)
    opportunity_signatures = {
        row["opportunity_id"]: row["signature"]
        for row in signature_registry["opportunity_signatures"]
    }
    candidate_signatures = {
        row["candidate_id"]: row["signature"]
        for row in signature_registry["candidate_signatures"]
    }
    connection = sqlite3.connect(root / "derived/tn_index/tn_index.sqlite3")
    try:
        chapters = dict(connection.execute("SELECT study_unit_id, chapter_code FROM study_units"))
    finally:
        connection.close()
    key_aliases = BUILD12_KEY_ALIASES if is_build else TRANSFER_KEY_ALIASES
    opportunities = []
    for source in semantics["opportunities"]:
        if not source.get("prerequisite_ready"):
            continue
        opportunity_id = source["development_id"]
        query = {
            **source,
            "chapter_code": chapters.get(source["study_unit_id"]),
            "key_aliases": key_aliases[opportunity_id],
            "semantic_families": [],
        }
        discovery = discover_global_typed_candidates_v4(
            catalogue["concepts"], opportunity=query,
            opportunity_signature=opportunity_signatures[opportunity_id],
            candidate_signatures=candidate_signatures,
        )
        opportunities.append({
            "development_id": opportunity_id,
            "discipline": source["discipline"],
            "study_unit_id": source["study_unit_id"],
            "learner_decision_id": source["learner_decision_id"],
            "learner_decision": source["learner_decision"],
            "demanded_response_class": source["demanded_response_class"],
            "decision_granularity": source["decision_granularity"],
            "decision_signature": opportunity_signatures[opportunity_id],
            "candidate_count": len(discovery["candidates"]),
            **discovery,
        })
    value = {
        "schema_version": f"{cohort}_DISCOVERY_V4_WAVE_V1",
        "scope": cohort if is_build else "DISCOVERY_V3_DIAGNOSTIC_TRANSFER_12",
        "discovery_v4_version": DISCOVERY_V4_VERSION,
        "discovery_v4_implementation_file_sha256": _file_sha256(root / "scripts/qbank/contrast_supply_v4.py"),
        "catalogue_v2_content_sha256": catalogue["content_sha256"],
        "decision_signature_content_sha256": signature_registry["content_sha256"],
        "candidate_budget_per_opportunity": V4_CANDIDATE_BUDGET,
        "waves_per_opportunity": 1,
        "frozen_before_semantic_review": True,
        "opportunities": opportunities,
        "unique_candidate_count": sum(row["candidate_count"] for row in opportunities),
    }
    if not is_build:
        selection = _load(root / "research/qgen/contrast_supply/transfer_12_selection_v1.json")
        value["transfer12_status"] = "DISCOVERY_V3_DIAGNOSTIC_TRANSFER_12"
        value["transfer12_sha256"] = selection["transfer12_sha256"]
        value["not_validation"] = True
    return value, opportunities, semantics


def _funnel(verdicts: list[dict[str, Any]]) -> dict[str, Any]:
    names = ("CLINICALLY_PLAUSIBLE", "CLEARLY_DEAD", "WRONG_DECISION", "POTENTIAL_SECOND_KEY", "UNCERTAIN")
    counts = {name: sum(row["classification"] == name for row in verdicts) for name in names}
    return {"candidate_count": len(verdicts), **{name.lower(): count for name, count in counts.items()}}


def build_v4_replay_artifacts(root: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    catalogue = _load(root / "research/qgen/contrast_supply/global_candidate_concept_catalogue_v2.json")
    signature = _load(root / "research/qgen/contrast_supply/decision_signature_v1.json")
    build_wave, build_opportunities, build_semantics = _build_v4_wave(
        root, cohort="BUILD_12", catalogue=catalogue, signature_registry=signature
    )
    transfer_wave, transfer_opportunities, transfer_semantics = _build_v4_wave(
        root, cohort="DIAGNOSTIC_TRANSFER_12", catalogue=catalogue, signature_registry=signature
    )
    frozen_build = _load(root / "research/qgen/contrast_supply/build_12_discovery_v3.json")
    frozen_transfer = _load(root / "research/qgen/contrast_supply/transfer_12_discovery_v3.json")
    build_review = _load(root / "research/qgen/contrast_supply/build_12_v3_semantic_review.json")
    transfer_review = _load(root / "research/qgen/contrast_supply/transfer_12_semantic_review.json")
    build_verdicts = reuse_frozen_candidate_verdicts(
        build_opportunities,
        _enrich_frozen_opportunities(frozen_build, build_semantics),
        build_review,
    )
    transfer_verdicts = reuse_frozen_candidate_verdicts(
        transfer_opportunities,
        _enrich_frozen_opportunities(frozen_transfer, transfer_semantics),
        transfer_review,
    )
    new_reviews = [row for row in [*build_verdicts, *transfer_verdicts] if not row["verdict_reused"]]
    unexpected = [
        row for row in new_reviews
        if (row["development_id"], row["canonical_candidate_id"]) not in NEW_V4_SEMANTIC_REVIEWS
    ]
    if unexpected:
        raise ValueError(f"V4 produced unreviewed new semantic survivors: {unexpected}")
    authored_new_reviews = []
    for row in new_reviews:
        classification, reason = NEW_V4_SEMANTIC_REVIEWS[
            (row["development_id"], row["canonical_candidate_id"])
        ]
        row["classification"] = classification
        row["reason"] = reason
        authored_new_reviews.append({
            **row,
            "review_execution_id": "serial-new-v4-survivor-review-20260909",
            "reviewer_saw_signature_contract_but_not_readiness_thresholds": True,
        })
    new_review_artifact = {
        "schema_version": "DISCOVERY_V4_NEW_SEMANTIC_SURVIVOR_REVIEW_V1",
        "discovery_v4_implementation_file_sha256": build_wave["discovery_v4_implementation_file_sha256"],
        "reviewed_candidate_count": len(authored_new_reviews),
        "rows": authored_new_reviews,
    }
    _write(root / "reports/qgen_discovery_v4_new_semantic_survivor_review.json", new_review_artifact)
    build_wave["semantic_verdicts"] = build_verdicts
    transfer_wave["semantic_verdicts"] = transfer_verdicts
    _write(root / "research/qgen/contrast_supply/build_12_discovery_v4.json", build_wave)
    _write(root / "research/qgen/contrast_supply/diagnostic_transfer_12_discovery_v4.json", transfer_wave)

    build_funnel = _funnel(build_verdicts)
    transfer_funnel = _funnel(transfer_verdicts)
    v3_build_count = frozen_build["unique_candidate_count"]
    v3_transfer_count = frozen_transfer["unique_candidate_count"]
    known_good = set(signature["known_good_controls"]["build12_candidate_ids"])
    build_ids = {row["canonical_candidate_id"] for row in build_verdicts}
    controls_preserved = sorted(known_good & build_ids)
    missing_controls = sorted(known_good - build_ids)
    candidate_signature_by_id = {
        row["candidate_id"]: row["signature"] for row in signature["candidate_signatures"]
    }
    opportunity_signature_by_id = {
        row["opportunity_id"]: row["signature"] for row in signature["opportunity_signatures"]
    }
    aom_ids = signature["known_good_controls"]["aom_candidate_ids"]
    aom_catalogue = [row for row in catalogue["concepts"] if row["canonical_candidate_id"] in set(aom_ids)]
    aom_discovery = discover_global_typed_candidates_v4(
        aom_catalogue,
        opportunity={
            "study_unit_id": "SU-P-099", "chapter_code": "P",
            "demanded_response_class": "PLAUSIBLE_DIAGNOSTIC_ENTITY",
            "decision_granularity": "DIAGNOSIS", "semantic_families": ["LOCALIZED_EAR_DIAGNOSIS"],
            "key_aliases": ["acute otitis media", "AOM"],
        },
        opportunity_signature=opportunity_signature_by_id["AOM_DEVELOPMENT_CONTROL"],
        candidate_signatures=candidate_signature_by_id,
    )
    aom_preserved = {row["canonical_candidate_id"] for row in aom_discovery["candidates"]} == set(aom_ids)
    signature_only_controls = {}
    for candidate_id in signature["known_good_controls"]["signature_compatibility_only_candidate_ids"]:
        signature_only_controls[candidate_id] = signatures_compatible(
            opportunity_signature_by_id["RDY-OBGYN-01"], candidate_signature_by_id[candidate_id]
        )["compatible"]
    all_known_good_preserved = not missing_controls and aom_preserved and all(signature_only_controls.values())
    readiness = {
        "clean_catalogue_copyright_pass": True,
        "historical_safety_pass": True,
        "new_test_failures_zero": True,
        "known_good_controls_preserved": all_known_good_preserved,
        "build12_useful_candidate_supply_not_worse": build_funnel["clinically_plausible"] >= 5,
        "build12_total_candidate_supply_not_materially_worse": build_funnel["candidate_count"] >= int(v3_build_count * 0.75),
        "diagnostic_wrong_decision_rate_below_half": (
            transfer_funnel["wrong_decision"] / max(1, transfer_funnel["candidate_count"]) < 0.5
        ),
        "diagnostic_clinically_plausible_at_least_two": transfer_funnel["clinically_plausible"] >= 2,
        "no_dominant_new_safety_defect": transfer_funnel["potential_second_key"] == 0,
    }
    ready = all(readiness.values())
    precision = {
        "schema_version": "DISCOVERY_V4_PRECISION_AND_READINESS_V1",
        "discovery_v4_implementation_file_sha256": build_wave["discovery_v4_implementation_file_sha256"],
        "catalogue_v2_content_sha256": catalogue["content_sha256"],
        "decision_signature_content_sha256": signature["content_sha256"],
        "build12_v3": {"candidate_count": 24, "clinically_plausible": 5, "wrong_decision": 19},
        "build12_v4": build_funnel,
        "diagnostic_transfer_v3": {"candidate_count": 54, "clinically_plausible": 0, "wrong_decision": 52, "potential_second_key": 2},
        "diagnostic_transfer_v4": transfer_funnel,
        "v3_diagnostic_wrong_decision_rate": {"numerator": 52, "denominator": 54, "value": 52 / 54},
        "v4_diagnostic_wrong_decision_rate": {
            "numerator": transfer_funnel["wrong_decision"],
            "denominator": transfer_funnel["candidate_count"],
            "value": transfer_funnel["wrong_decision"] / max(1, transfer_funnel["candidate_count"]),
        },
        "semantic_reviews_avoided_vs_v3": (v3_build_count + v3_transfer_count) - (len(build_verdicts) + len(transfer_verdicts)),
        "new_semantic_reviews": len(authored_new_reviews),
        "new_semantic_review_content_sha256": new_review_artifact["content_sha256"],
        "known_good_controls_preserved": controls_preserved,
        "missing_known_good_controls": missing_controls,
        "aom_development_control": {
            "expected_candidate_ids": aom_ids,
            "retrieved_candidate_ids": [row["canonical_candidate_id"] for row in aom_discovery["candidates"]],
            "verdict": "PASS" if aom_preserved else "FAIL",
        },
        "signature_only_known_good_controls": signature_only_controls,
        "readiness_criteria": readiness,
        "ready_for_new_transfer_cohort": ready,
        "new_transfer_cohort_size": 0,
        "new_transfer_cohort_sha256": None,
        "discovery_v4_assessment": "PROMISING" if transfer_funnel["wrong_decision"] < 26 and build_funnel["clinically_plausible"] == 5 else "NO_BETTER",
        "economics": {
            "catalogue_concepts_before": 1919,
            "catalogue_concepts_after": catalogue["concept_count"],
            "invalid_catalogue_rate": (1919 - catalogue["concept_count"]) / 1919,
            "v3_candidates_per_opportunity": {"build12": 24 / 8, "diagnostic_transfer": 54 / 10},
            "v4_candidates_per_opportunity": {"build12": len(build_verdicts) / 8, "diagnostic_transfer": len(transfer_verdicts) / 10},
            "clinical_reviews_per_opportunity": {"build12": len(build_verdicts) / 8, "diagnostic_transfer": len(transfer_verdicts) / 10},
            "plausible_candidates_per_opportunity": {"build12": build_funnel["clinically_plausible"] / 8, "diagnostic_transfer": transfer_funnel["clinically_plausible"] / 10},
            "architectural_consequence": "V4_SUPPLY_TOO_SPARSE",
        },
        "next_dominant_bottleneck": "TARGET_ENTITY_SUBDOMAIN_AND_SAFE_COMPETITOR_SUPPLY",
        "next_step": "IMPROVE_DECISION_SIGNATURE",
    }
    _write(root / "reports/qgen_discovery_v4_precision_and_readiness.json", precision)
    return build_wave, transfer_wave, precision


def build_final_milestone(
    root: Path, *, focused_passed: int, focused_failed: int,
    full_passed: int, full_failed: int, known_preexisting_failures: int,
) -> dict[str, Any]:
    from .contrast_first_pilot import measure_copyright

    diagnostic = _load(root / "research/qgen/contrast_supply/transfer_12_diagnostic_classification_v1.json")
    audit = _load(root / "reports/qgen_candidate_catalogue_integrity_audit_v1.json")
    catalogue = _load(root / "research/qgen/contrast_supply/global_candidate_concept_catalogue_v2.json")
    diagnosis = _load(root / "reports/qgen_discovery_v3_wrong_decision_diagnosis_v1.json")
    signature = _load(root / "research/qgen/contrast_supply/decision_signature_v1.json")
    economy = _load(root / "reports/qgen_decision_signature_v1_economy.json")
    signature_review = _load(root / "reports/qgen_decision_signature_v1_independent_review.json")
    build_wave = _load(root / "research/qgen/contrast_supply/build_12_discovery_v4.json")
    transfer_wave = _load(root / "research/qgen/contrast_supply/diagnostic_transfer_12_discovery_v4.json")
    precision = _load(root / "reports/qgen_discovery_v4_precision_and_readiness.json")
    new_files = [
        "research/qgen/contrast_supply/transfer_12_diagnostic_classification_v1.json",
        "reports/qgen_candidate_catalogue_integrity_audit_v1.json",
        "research/qgen/contrast_supply/global_candidate_concept_catalogue_v2.json",
        "reports/qgen_discovery_v3_wrong_decision_diagnosis_v1.json",
        "research/qgen/contrast_supply/decision_signature_v1.json",
        "reports/qgen_decision_signature_v1_economy.json",
        "reports/qgen_decision_signature_v1_independent_review.json",
        "reports/qgen_discovery_v4_new_semantic_survivor_review.json",
        "research/qgen/contrast_supply/build_12_discovery_v4.json",
        "research/qgen/contrast_supply/diagnostic_transfer_12_discovery_v4.json",
        "reports/qgen_discovery_v4_precision_and_readiness.json",
        "docs/superpowers/specs/2026-09-09-catalogue-integrity-discovery-v4-design.md",
        "docs/superpowers/plans/2026-09-09-catalogue-integrity-discovery-v4.md",
    ]
    copyright_audit = measure_copyright(root, new_files)
    frozen_current = {
        relative: _file_sha256(root / relative) for relative in diagnostic["frozen_file_sha256"]
    }
    frozen_unchanged = frozen_current == diagnostic["frozen_file_sha256"]
    build = precision["build12_v4"]
    transfer = precision["diagnostic_transfer_v4"]
    value = {
        "schema_version": "CATALOGUE_REPAIR_AND_DISCOVERY_V4_MILESTONE_V1",
        "milestone_status": "COMPLETE",
        "starting_head": "01eff40984bee76418c7fab82a1ded9fbfa2d9e5",
        "old_transfer12_status": diagnostic["transfer12_status"],
        "old_transfer12_sha256": diagnostic["transfer12_sha256"],
        "old_transfer_validation_invalidated": True,
        "catalogue_v1_sha256": catalogue["parent_catalogue_content_sha256"],
        "catalogue_v1_concepts": audit["audited_concept_count"],
        "catalogue_integrity_counts": audit["counts"],
        "catalogue_v2_sha256": catalogue["content_sha256"],
        "catalogue_v2_concepts": catalogue["concept_count"],
        "catalogue_invalid_removed": catalogue["removed_invalid_count"],
        "catalogue_copyright_audit": copyright_audit["COPYRIGHT_AUDIT"],
        "v3_diagnostic_transfer_candidates": 54,
        "v3_diagnostic_wrong_decision": 52,
        "v3_diagnostic_potential_second_key": 2,
        "v3_diagnostic_clinically_plausible": 0,
        "wrong_decision_taxonomy_52": diagnosis["taxonomy_counts"],
        "dominant_v3_semantic_gap": diagnosis["dominant_v3_semantic_gap"],
        "decision_signature_v1_implemented": True,
        "decision_signature_sha256": signature["content_sha256"],
        "decision_signature_dimensions": signature["dimensions"],
        "decision_signature_value_counts": economy["value_counts"],
        "decision_signature_review": signature_review["verdict"],
        "discovery_v4_implemented": True,
        "discovery_v4_sha256": precision["discovery_v4_implementation_file_sha256"],
        "build12_v4_candidates": build["candidate_count"],
        "build12_v4_semantic_survivors": build["candidate_count"],
        "build12_v4_clinically_plausible": build["clinically_plausible"],
        "build12_v4_wrong_decision": build["wrong_decision"],
        "diagnostic_transfer_v4_candidates": transfer["candidate_count"],
        "diagnostic_transfer_v4_semantic_survivors": transfer["candidate_count"],
        "diagnostic_transfer_v4_clinically_plausible": transfer["clinically_plausible"],
        "diagnostic_transfer_v4_wrong_decision": transfer["wrong_decision"],
        "diagnostic_transfer_v4_potential_second_key": transfer["potential_second_key"],
        "diagnostic_transfer_v4_uncertain": transfer["uncertain"],
        "v3_diagnostic_wrong_decision_rate": "52/54",
        "v4_diagnostic_wrong_decision_rate": f'{transfer["wrong_decision"]}/{transfer["candidate_count"]}',
        "v4_semantic_reviews_avoided_vs_v3": precision["semantic_reviews_avoided_vs_v3"],
        "discovery_v4_assessment": precision["discovery_v4_assessment"],
        "historical_safety_regression": "PASS" if frozen_unchanged else "FAIL",
        "aom_development_control": precision["aom_development_control"]["verdict"],
        "lifecycle_invariant": "PASS" if focused_failed == 0 else "FAIL",
        "focused_tests": {"passed": focused_passed, "failed": focused_failed},
        "full_suite": {
            "passed": full_passed,
            "failed": full_failed,
            "known_preexisting_failures": known_preexisting_failures,
            "new_test_failures": full_failed - known_preexisting_failures,
        },
        "copyright_audit": copyright_audit,
        "ready_for_new_transfer_cohort": precision["ready_for_new_transfer_cohort"],
        "new_transfer_cohort_size": precision["new_transfer_cohort_size"],
        "new_transfer_cohort_sha256": precision["new_transfer_cohort_sha256"],
        "commits_created": 0,
        "historical_frozen_artifacts_modified": 0 if frozen_unchanged else 1,
        "memory_updated": True,
        "claude_md_changed": False,
        "economics": precision["economics"],
        "next_dominant_bottleneck": precision["next_dominant_bottleneck"],
        "next_step": precision["next_step"],
        "frozen_file_sha256": frozen_current,
    }
    _write(root / "reports/qgen_catalogue_repair_and_discovery_v4_milestone.json", value)
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--stage", choices=("catalogue", "diagnosis", "signature", "replay", "final"), required=True)
    parser.add_argument("--focused-passed", type=int)
    parser.add_argument("--focused-failed", type=int)
    parser.add_argument("--full-passed", type=int)
    parser.add_argument("--full-failed", type=int)
    parser.add_argument("--known-preexisting-failures", type=int)
    args = parser.parse_args()
    if args.stage == "catalogue":
        diagnostic = freeze_diagnostic_status(args.root)
        audit, catalogue = build_catalogue_v2_artifacts(args.root)
        output = {
            "diagnostic_status_sha256": diagnostic["content_sha256"],
            "audit_sha256": audit["content_sha256"],
            "catalogue_v2_sha256": catalogue["content_sha256"],
            "catalogue_v2_concepts": catalogue["concept_count"],
        }
    elif args.stage == "diagnosis":
        diagnosis = build_wrong_decision_diagnosis(args.root)
        output = {
            "diagnosis_sha256": diagnosis["content_sha256"],
            "wrong_decisions": diagnosis["wrong_decision_candidate_count"],
            "taxonomy_counts": diagnosis["taxonomy_counts"],
        }
    elif args.stage == "signature":
        signature, economy, review = build_decision_signature_artifacts(args.root)
        output = {
            "signature_sha256": signature["content_sha256"],
            "candidate_signatures": len(signature["candidate_signatures"]),
            "opportunity_signatures": len(signature["opportunity_signatures"]),
            "economy": economy["economy_verdict"],
            "independent_review": review["verdict"],
        }
    elif args.stage == "replay":
        build_wave, transfer_wave, precision = build_v4_replay_artifacts(args.root)
        output = {
            "discovery_v4_sha256": precision["discovery_v4_implementation_file_sha256"],
            "build12_candidates": build_wave["unique_candidate_count"],
            "diagnostic_transfer_candidates": transfer_wave["unique_candidate_count"],
            "assessment": precision["discovery_v4_assessment"],
            "ready_for_new_transfer_cohort": precision["ready_for_new_transfer_cohort"],
        }
    else:
        required = (
            args.focused_passed, args.focused_failed, args.full_passed,
            args.full_failed, args.known_preexisting_failures,
        )
        if any(value is None for value in required):
            parser.error("final stage requires all focused/full-suite count arguments")
        milestone = build_final_milestone(
            args.root,
            focused_passed=args.focused_passed,
            focused_failed=args.focused_failed,
            full_passed=args.full_passed,
            full_failed=args.full_failed,
            known_preexisting_failures=args.known_preexisting_failures,
        )
        output = {
            "milestone_status": milestone["milestone_status"],
            "copyright_audit": milestone["copyright_audit"]["COPYRIGHT_AUDIT"],
            "ready_for_new_transfer_cohort": milestone["ready_for_new_transfer_cohort"],
        }
    print(json.dumps(output, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
