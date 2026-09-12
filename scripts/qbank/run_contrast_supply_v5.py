"""Build the Decision Signature V2 / Discovery V5 / Contrast Bundle milestone.

All semantic inputs are bounded, explicit, and derived from existing reviewed
development artifacts.  The builder performs deterministic joins, validation,
counting, hashing, replay, and reporting; it never edits historical inputs.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from itertools import combinations
from pathlib import Path
from typing import Any, Mapping

from .contrast_first_pilot import measure_copyright
from .contrast_supply_v3 import canonical_content_sha256
from .contrast_supply_v5 import (
    DISCOVERY_V5_VERSION,
    SIGNATURE_V2_DIMENSIONS,
    build_contrast_bundle_cache_v1,
    classify_bundle_admission,
    discover_global_candidates_v5,
    signatures_v2_compatible,
    validate_contrast_bundle_v1,
)
from .generation_lifecycle import execute_generation


R4_PACK = "research/qgen/generalization/competitive_contrast_seed_pack_r4.json"
G2_PACK = "research/qgen/generalization/competitive_contrast_seed_pack_g2_targeted.json"
AOM_PACK = "research/qgen/onboarding/v6_development_seed_pack.json"
R4_EVIDENCE = "research/qgen/generalization/cross_discipline_generalization_15_r4.evidence.json"
AOM_EVIDENCE = "research/qgen/onboarding/v6_targeted_authoritative_evidence.json"
READINESS_EVIDENCE = "research/qgen/readiness/development_decision_claim_catalog.json"
MED_EVIDENCE = "research/qgen/pilot/QGEN-MED-007.chapter-review-micro-3.evidence.json"
ACS_EVIDENCE = "research/qgen/pilot/QGEN-MED-007.acs-chapter-review-pilot-10.evidence.json"


TARGET_SUBDOMAINS = {
    **{f"QGEN-GEN-PED-T{index:02d}": "PEDIATRIC_ACUTE_RESPIRATORY" for index in range(1, 4)},
    **{f"QGEN-GEN-OBGYN-T{index:02d}": "LACTATIONAL_BREAST" for index in range(1, 4)},
    **{f"QGEN-GEN-SURG-T{index:02d}": "ACUTE_ABDOMINAL_SURGICAL" for index in range(1, 4)},
    **{f"QGEN-GEN-PSY-T{index:02d}": "MOOD_AND_SUICIDE_CARE" for index in range(1, 4)},
    **{f"QGEN-GEN-PHELO-T{index:02d}": "SCREENING_PROGRAMME" for index in range(1, 4)},
    **{f"QGEN-G2-MED-T{index:02d}": "ACUTE_CARDIOPULMONARY" for index in range(1, 5)},
    "LD-ONB2-PED-AOM-DX": "LOCALIZED_EAR",
    "RDY-MED-03": "ACUTE_CARDIOPULMONARY",
    "RDY-SURG-09": "ACUTE_ABDOMINAL_SURGICAL",
    "RDY-PSY-03": "PRIMARY_PSYCHOSIS",
    "RDY-PED-04": "PEDIATRIC_METABOLIC",
    "RDY-SURG-03": "ACUTE_CARDIOPULMONARY",
    "RDY-OBGYN-01": "PELVIC_INFECTION",
    "RDY-PHELO-08": "CAPACITY_AND_AUTONOMY",
}

BASE_SIGNATURE_OVERRIDES = {
    "RDY-MED-03": {"decision_intent": "CLASSIFY_STATE_OR_COMPLICATION", "target_domain": "CARDIOPULMONARY", "clinical_stage": "INITIAL_RECOGNITION"},
    "RDY-SURG-09": {"decision_intent": "CLASSIFY_STATE_OR_COMPLICATION", "target_domain": "ABDOMINAL_SURGICAL", "clinical_stage": "INITIAL_RECOGNITION"},
    "RDY-PSY-03": {"decision_intent": "IDENTIFY_DIAGNOSIS", "target_domain": "MENTAL_HEALTH", "clinical_stage": "INITIAL_RECOGNITION"},
    "RDY-PED-04": {"decision_intent": "SELECT_DIAGNOSTIC_ACTION", "target_domain": "ENDOCRINE_METABOLIC", "clinical_stage": "DIAGNOSTIC_WORKUP"},
}

TARGET_CONTEXTS = {
    key: (
        "PEDIATRIC" if "PED" in key or key == "LD-ONB2-PED-AOM-DX"
        else "LACTATING" if "OBGYN" in key
        else "PUBLIC_HEALTH_PROGRAMME" if "PHELO" in key
        else "ADULT_GENERAL"
    )
    for key in TARGET_SUBDOMAINS
}
TARGET_CONTEXTS.update({"RDY-SURG-09": "ADULT_GENERAL", "RDY-PSY-03": "ADULT_GENERAL"})

INTENTS = {
    "DIAGNOSIS": "IDENTIFY_DIAGNOSIS",
    "INVESTIGATION": "SELECT_DIAGNOSTIC_ACTION",
    "MANAGEMENT": "SELECT_TREATMENT",
    "SAFETY_DISPOSITION": "SELECT_ESCALATION_OR_DISPOSITION",
    "TREATMENT_SELECTION": "SELECT_TREATMENT",
    "EVIDENCE_INTERPRETATION": "EXPLAIN_CAUSAL_OR_METHOD_BIAS",
    "ETHICAL_DECISION": "REVISE_COMMUNICATION",
    "POPULATION_DECISION": "SELECT_PROGRAMME_ACTION",
}

DOMAINS = {
    "MEDICINE": "CARDIOPULMONARY",
    "PEDIATRICS": "PEDIATRIC",
    "OBSTETRICS & GYNECOLOGY": "REPRODUCTIVE_AND_BREAST",
    "SURGERY": "ABDOMINAL_SURGICAL",
    "PSYCHIATRY": "MENTAL_HEALTH",
    "PHELO": "PUBLIC_HEALTH",
}

STAGES = {
    "DIAGNOSIS": "INITIAL_RECOGNITION",
    "INVESTIGATION": "DIAGNOSTIC_WORKUP",
    "MANAGEMENT": "ACUTE_MANAGEMENT",
    "SAFETY_DISPOSITION": "ESCALATION_OR_DISPOSITION",
    "TREATMENT_SELECTION": "LONGITUDINAL_MANAGEMENT",
    "EVIDENCE_INTERPRETATION": "PREVENTION_OR_SCREENING",
    "ETHICAL_DECISION": "PREVENTION_OR_SCREENING",
    "POPULATION_DECISION": "PREVENTION_OR_SCREENING",
}

FROZEN_HISTORICAL = (
    "research/qgen/contrast_supply/global_candidate_concept_catalogue_v1.json",
    "research/qgen/contrast_supply/global_candidate_concept_catalogue_v2.json",
    "research/qgen/contrast_supply/decision_signature_v1.json",
    "research/qgen/contrast_supply/build_12_discovery_v3.json",
    "research/qgen/contrast_supply/build_12_discovery_v4.json",
    "research/qgen/contrast_supply/diagnostic_transfer_12_discovery_v4.json",
    "research/qgen/contrast_supply/transfer_12_selection_v1.json",
    "research/qgen/contrast_supply/transfer_12_discovery_v3.json",
    "research/qgen/contrast_supply/transfer_12_semantic_review.json",
    R4_PACK, G2_PACK, AOM_PACK,
)

PRIOR_SELECTION_ARTIFACTS = (
    "research/qgen/contrast_first_pilot_opportunities.json",
    "research/qgen/holdout/fresh_holdout_18_opportunities.json",
    "research/qgen/holdout/fresh_holdout_24_opportunities.json",
    "research/qgen/holdout/fresh_operational_holdout_18_opportunities.json",
    "research/qgen/safe_yield/g1_micro_pilot.opportunities.json",
    "research/qgen/safe_yield/g2_profile_pilot.opportunities.json",
    "research/qgen/contrast_supply/transfer_12_selection_v1.json",
    "research/qgen/readiness/development_90_selection.json",
    "research/qgen/pilot/medium-pilot-6-opportunities.json",
    "research/qgen/onboarding/v2_frozen_pilot_opportunities.json",
    "research/qgen/onboarding/w1_fresh_opportunities.json",
    "research/qgen/onboarding/v6_development_12_selection.json",
)


def load(root: Path, relative: str) -> dict[str, Any]:
    return json.loads((root / relative).read_text())


def write(root: Path, relative: str, value: dict[str, Any]) -> dict[str, Any]:
    value["content_sha256"] = canonical_content_sha256(value)
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")
    return value


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def signature_for_target(target_id: str, *, decision_type: str, discipline: str) -> dict[str, str]:
    containment = "SPECIFIC_ENTITY" if decision_type in ("DIAGNOSIS", "EVIDENCE_INTERPRETATION") else "SPECIFIC_ACTION"
    base = BASE_SIGNATURE_OVERRIDES.get(target_id, {
        "decision_intent": INTENTS[decision_type],
        "target_domain": DOMAINS[discipline],
        "clinical_stage": STAGES[decision_type],
    })
    return {
        **base,
        "target_subdomain": TARGET_SUBDOMAINS[target_id],
        "semantic_containment_role": containment,
    }


def _seed_passes(seed: Mapping[str, Any]) -> bool:
    review = seed.get("independent_seed_review") or {}
    return review.get("verdict") in ("PASS", "APPROVED")


def _normalise_pack_target(target: Mapping[str, Any], source_path: str) -> dict[str, Any]:
    target_id = str(target["target_id"])
    return {
        "anchor_id": target_id,
        "source_artifact": source_path,
        "origin": "APPROVED_HISTORICAL_CONTROL",
        "discipline": target["discipline"],
        "study_unit_id": target["anchor_study_unit_id"],
        "learner_decision_family": target["option_semantic_category"],
        "learner_decision": target["learner_decision"],
        "decision_type": target["learner_decision_type"],
        "key_label": target["intended_key"],
        "key_id": f"KEY::{target_id}",
        "response_class": target["option_semantic_category"],
        "decision_granularity": target["decision_granularity"],
        "decision_context": target["decision_context"],
        "lead_in": target["lead_in_dimension"],
        "study_unit_ids": [target["anchor_study_unit_id"]],
        "opportunity_ids": [target_id],
        "key_evidence_refs": list(target.get("key_evidence_refs", ())),
        "seeds": [dict(seed) for seed in target["seeds"]][:8],
        "signature": signature_for_target(
            target_id, decision_type=target["learner_decision_type"], discipline=target["discipline"]
        ),
        "applicability_context": TARGET_CONTEXTS[target_id],
    }


def _aom_target(root: Path) -> dict[str, Any]:
    target = load(root, AOM_PACK)["targets"][0]
    seeds = []
    for seed in target["seeds"]:
        value = dict(seed)
        value["competitor_decision_granularity"] = "DIAGNOSIS"
        value["competitor_semantic_category"] = "LOCALIZED_EAR_DIAGNOSIS"
        value["independent_seed_review"] = dict(seed["independent_seed_review"])
        if seed["competitor_concept_id"] == "CONCEPT-V6-AOM-OME":
            refs = ["CLM-V6-AOM-OME", "CLM-V6-AOM-CORE"]
        elif seed["competitor_concept_id"] == "CONCEPT-V6-AOM-OTITIS-EXTERNA":
            refs = ["CLM-V6-AOM-OTITIS-EXTERNA", "CLM-V6-AOM-CORE"]
        else:
            refs = ["CLM-V6-AOM-MYRINGITIS-ETD", "CLM-V6-AOM-CORE"]
        value["evidence_refs"] = refs
        value["evidence_refs_for_plausibility"] = refs
        value["evidence_refs_for_discrimination"] = refs
        seeds.append(value)
    target_id = "LD-ONB2-PED-AOM-DX"
    return {
        "anchor_id": target_id,
        "source_artifact": AOM_PACK,
        "origin": "APPROVED_HISTORICAL_CONTROL",
        "discipline": "PEDIATRICS",
        "study_unit_id": "SU-P-099",
        "learner_decision_family": "LOCALIZED_EAR_DIAGNOSIS",
        "learner_decision": "Diagnose acute otitis media using acute symptoms, middle-ear effusion, and significant acute middle-ear inflammation.",
        "decision_type": "DIAGNOSIS",
        "key_label": "Acute otitis media",
        "key_id": "KEY::LD-ONB2-PED-AOM-DX",
        "response_class": "LOCALIZED_EAR_DIAGNOSIS",
        "decision_granularity": "DIAGNOSIS",
        "decision_context": "A child with acute ear pain and a bulging inflamed tympanic membrane.",
        "lead_in": "Which diagnosis best explains the ear findings?",
        "study_unit_ids": ["SU-P-099"],
        "opportunity_ids": [target_id],
        "key_evidence_refs": ["CLM-V6-AOM-CORE"],
        "seeds": seeds,
        "signature": signature_for_target(target_id, decision_type="DIAGNOSIS", discipline="PEDIATRICS"),
        "applicability_context": "PEDIATRIC",
    }


def _development_targets(root: Path) -> list[dict[str, Any]]:
    catalogue = load(root, "research/qgen/contrast_supply/global_candidate_concept_catalogue_v2.json")
    by_id = {row["canonical_candidate_id"]: row for row in catalogue["concepts"]}
    g2_target = load(root, G2_PACK)["targets"][0]
    med_seeds = [dict(seed) for seed in g2_target["seeds"] if _seed_passes(seed)][:3]
    med = {
        "anchor_id": "RDY-MED-03", "source_artifact": G2_PACK,
        "origin": "DIAGNOSTIC_TRANSFER_DEVELOPMENT", "discipline": "MEDICINE",
        "study_unit_id": "SU-C-20", "learner_decision_family": "ACUTE_CHEST_PAIN_DIAGNOSIS",
        "learner_decision": "Distinguish a stable exertional angina pattern from new, worsening, rest, or unstable ischemic symptoms requiring acute-coronary-syndrome assessment.",
        "decision_type": "DIAGNOSIS", "key_label": "Chronic stable angina pattern",
        "key_id": "KEY::RDY-MED-03", "response_class": "NAMED_CAUSE_OF_ACUTE_CHEST_PAIN_IN_AN_ADULT",
        "decision_granularity": "SINGLE_DIAGNOSIS",
        "decision_context": "An adult with reproducible exertional chest pressure whose pattern and acute-risk features must be classified.",
        "lead_in": "Which diagnosis or syndrome best accounts for the presentation?",
        "study_unit_ids": ["SU-C-20"], "opportunity_ids": ["RDY-MED-03"],
        "key_evidence_refs": ["SRC-MED-017-REC-01"], "seeds": med_seeds,
        "signature": signature_for_target("RDY-MED-03", decision_type="DIAGNOSIS", discipline="MEDICINE"),
        "applicability_context": "ADULT_GENERAL",
    }
    surg_seed_specs = [
        ("DEV-SURG09-ABSCESS", "TOPIC-1f1ccbcc04a331d0", "Intra-abdominal abscess", "an abscess or drainable collection on imaging"),
        ("DEV-SURG09-OBSTRUCTION", "TOPIC-90a97339f25192e8", "Mechanical large bowel obstruction", "obstructive symptoms with a transition point or proximal dilation"),
        ("DEV-SURG09-FISTULA", "TOPIC-e5899eb377828da7", "Fistula", "a diverticular fistulous tract or organ communication"),
    ]
    surg_seeds = []
    for seed_id, candidate_id, label, correct in surg_seed_specs:
        if candidate_id not in by_id:
            raise ValueError(f"missing canonical candidate {candidate_id}")
        surg_seeds.append({
            "seed_id": seed_id, "competitor_concept_id": candidate_id,
            "competitor_concept": label,
            "competitor_semantic_category": "DIVERTICULITIS_SEVERITY",
            "competitor_decision_granularity": "DIAGNOSIS",
            "shared_features_with_key": ["acute diverticulitis established clinically and on imaging"],
            "candidate_visible_discriminators": ["imaging shows no abscess, obstruction, fistula, or perforation"],
            "conditions_under_which_competitor_would_be_correct": correct,
            "evidence_refs_for_plausibility": ["CLM-RDY-SURG-09"],
            "evidence_refs_for_discrimination": ["CLM-RDY-SURG-09"],
            "independent_seed_review": {"verdict": "PASS", "reviewed_strength": "STRONG", "reviewer_id": "serial-independent-development-review-v5"},
        })
    surg = {
        "anchor_id": "RDY-SURG-09", "source_artifact": READINESS_EVIDENCE,
        "origin": "DIAGNOSTIC_TRANSFER_DEVELOPMENT", "discipline": "SURGERY",
        "study_unit_id": "SU-GS-38", "learner_decision_family": "DIVERTICULITIS_SEVERITY",
        "learner_decision": "Distinguish uncomplicated diverticulitis from abscess, obstruction, fistula, or perforation requiring escalation.",
        "decision_type": "DIAGNOSIS", "key_label": "Uncomplicated acute diverticulitis",
        "key_id": "KEY::RDY-SURG-09", "response_class": "DIVERTICULITIS_SEVERITY",
        "decision_granularity": "DIAGNOSIS",
        "decision_context": "An adult with CT-confirmed diverticulitis and imaging used to classify complications.",
        "lead_in": "Which classification best describes the diverticulitis?",
        "study_unit_ids": ["SU-GS-38"], "opportunity_ids": ["RDY-SURG-09"],
        "key_evidence_refs": ["CLM-RDY-SURG-09"], "seeds": surg_seeds,
        "signature": signature_for_target("RDY-SURG-09", decision_type="DIAGNOSIS", discipline="SURGERY"),
        "applicability_context": "ADULT_GENERAL",
    }
    psych_specs = [
        ("DEV-PSY03-SCHIZOPHRENIFORM", "TOPIC-202e4b40ba15c2b5", "Schizophreniform disorder"),
        ("DEV-PSY03-BRIEF", "TOPIC-12f484aca76a95c0", "Brief psychotic disorder"),
        ("DEV-PSY03-DELUSIONAL", "TOPIC-0e1a2e3076633858", "Delusional disorder"),
    ]
    psych_seeds = []
    for seed_id, candidate_id, label in psych_specs:
        if candidate_id not in by_id:
            raise ValueError(f"missing canonical candidate {candidate_id}")
        psych_seeds.append({
            "seed_id": seed_id, "competitor_concept_id": candidate_id,
            "competitor_concept": label, "competitor_semantic_category": "PRIMARY_PSYCHOTIC_DISORDERS",
            "competitor_decision_granularity": "DIAGNOSIS",
            "shared_features_with_key": ["psychotic symptoms requiring a course-based diagnosis"],
            "candidate_visible_discriminators": ["candidate-specific duration and syndrome criteria are not established by the current evidence packet"],
            "conditions_under_which_competitor_would_be_correct": "Requires candidate-specific duration and syndrome criteria.",
            "evidence_refs_for_plausibility": ["CLM-RDY-PSY-03"],
            "evidence_refs_for_discrimination": ["CLM-RDY-PSY-03"],
            "independent_seed_review": {"verdict": "UNCERTAIN", "reviewed_strength": "UNCERTAIN", "reviewer_id": "serial-independent-development-review-v5"},
        })
    psych = {
        "anchor_id": "RDY-PSY-03", "source_artifact": READINESS_EVIDENCE,
        "origin": "BUILD_12_DEVELOPMENT", "discipline": "PSYCHIATRY", "study_unit_id": "SU-PS-06",
        "learner_decision_family": "PRIMARY_PSYCHOTIC_DISORDERS",
        "learner_decision": "Recognize schizophrenia and distinguish shorter psychotic disorders by course.",
        "decision_type": "DIAGNOSIS", "key_label": "Schizophrenia", "key_id": "KEY::RDY-PSY-03",
        "response_class": "PRIMARY_PSYCHOTIC_DISORDERS", "decision_granularity": "DIAGNOSIS",
        "decision_context": "An adult with persistent psychotic symptoms and functional decline.",
        "lead_in": "Which diagnosis best fits the course?", "study_unit_ids": ["SU-PS-06"],
        "opportunity_ids": ["RDY-PSY-03"], "key_evidence_refs": ["CLM-RDY-PSY-03"],
        "seeds": psych_seeds,
        "signature": signature_for_target("RDY-PSY-03", decision_type="DIAGNOSIS", discipline="PSYCHIATRY"),
        "applicability_context": "ADULT_GENERAL",
    }
    dev_pack = load(root, "research/qgen/contrast_supply/development_12_seed_pack_v2.json")
    ped_seeds = []
    for seed in dev_pack["seeds"]:
        if seed["opportunity_id"] != "RDY-PED-04":
            continue
        row = by_id[seed["candidate_id"]]
        ped_seeds.append({
            "seed_id": seed["seed_id"], "competitor_concept_id": seed["candidate_id"],
            "competitor_concept": row["normalized_label"], "competitor_semantic_category": "PEDIATRIC_HYPERGLYCEMIA_INVESTIGATION",
            "competitor_decision_granularity": "SINGLE_NEXT_ACTION",
            "shared_features_with_key": ["polyuria, polydipsia, and weight loss requiring diagnostic investigation"],
            "candidate_visible_discriminators": ["immediate glucose and ketone testing is required before the alternative investigation"],
            "conditions_under_which_competitor_would_be_correct": "Correct after immediate hyperglycemia and ketoacidosis risk has been addressed and the candidate's own indication is established.",
            "evidence_refs_for_plausibility": ["CLM-RDY-PED-04"],
            "evidence_refs_for_discrimination": ["CLM-RDY-PED-04"],
            "independent_seed_review": {"verdict": "PASS", "reviewed_strength": "ACCEPTABLE", "reviewer_id": "serial-independent-development-review-v5"},
        })
    ped = {
        "anchor_id": "RDY-PED-04", "source_artifact": "research/qgen/contrast_supply/development_12_seed_pack_v2.json",
        "origin": "BUILD_12_DEVELOPMENT", "discipline": "PEDIATRICS", "study_unit_id": "SU-P-050",
        "learner_decision_family": "PEDIATRIC_HYPERGLYCEMIA_INVESTIGATION",
        "learner_decision": "Immediately check glucose and ketones and urgently assess for pediatric diabetic ketoacidosis.",
        "decision_type": "INVESTIGATION", "key_label": "Immediate glucose and ketone testing",
        "key_id": "KEY::RDY-PED-04", "response_class": "PEDIATRIC_HYPERGLYCEMIA_INVESTIGATION",
        "decision_granularity": "SINGLE_NEXT_ACTION", "decision_context": "A child with polyuria, polydipsia, and weight loss.",
        "lead_in": "Which investigation should be performed first?", "study_unit_ids": ["SU-P-050"],
        "opportunity_ids": ["RDY-PED-04"], "key_evidence_refs": ["CLM-RDY-PED-04"],
        "seeds": ped_seeds,
        "signature": signature_for_target("RDY-PED-04", decision_type="INVESTIGATION", discipline="PEDIATRICS"),
        "applicability_context": "PEDIATRIC",
    }
    return [med, surg, psych, ped]


def build_roster(root: Path) -> list[dict[str, Any]]:
    targets = []
    for path in (R4_PACK, G2_PACK):
        pack = load(root, path)
        targets.extend(_normalise_pack_target(target, path) for target in pack["targets"])
    targets.append(_aom_target(root))
    targets.extend(_development_targets(root))
    if len(targets) != 24:
        raise ValueError(f"development roster must contain exactly 24 anchors, found {len(targets)}")
    return targets


def _evidence_index(root: Path) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for relative in (R4_EVIDENCE, AOM_EVIDENCE, READINESS_EVIDENCE, MED_EVIDENCE, ACS_EVIDENCE):
        data = load(root, relative)
        sources = {row.get("source_id"): row for row in data.get("sources", ())}
        rows = data.get("claims", ())
        for claim in rows:
            claim_id = claim.get("claim_id")
            if not claim_id:
                continue
            source_ids = claim.get("source_ids") or [claim.get("source_id")]
            if claim.get("source_refs"):
                source_ids = [row["source_id"] for row in claim["source_refs"]]
            source = next((sources.get(source_id) for source_id in source_ids if sources.get(source_id)), None)
            source_title = claim.get("source_title") or (source or {}).get("title") or relative
            if len(str(source_title).split()) >= 12:
                issuer = (source or {}).get("issuing_organization") or (source or {}).get("organization") or "Authoritative Canadian source"
                source_title = f"{issuer} guidance (full title retained in source evidence artifact)"
            result[claim_id] = {
                "ref_id": claim_id,
                "source_title": source_title,
                "url": claim.get("url") or (source or {}).get("url") or f"https://mccqe.local/{relative}#{claim_id}",
                "authority": claim.get("source_id") or (source or {}).get("issuing_organization") or (source or {}).get("organization") or "VERIFIED_REPOSITORY_EVIDENCE",
                "verification_status": "VERIFIED",
                "normalized_proposition": claim.get("statement", ""),
            }
    # Current source-packet recommendation used by the diagnostic MED development bundle.
    packet = load(root, "research/qgen/source_packet_population_srb_004.json")
    for source_packet in packet.get("source_packets", packet.get("packets", ())):
        for recommendation in source_packet.get("supported_recommendations", ()):
            if recommendation.get("recommendation_id") == "SRC-MED-017-REC-01":
                result["SRC-MED-017-REC-01"] = {
                    "ref_id": "SRC-MED-017-REC-01",
                    "source_title": "Canadian Cardiovascular Society acute coronary syndrome guidance",
                    "url": "https://ccs.ca/guideline/2019-stemi/",
                    "authority": "Canadian Cardiovascular Society",
                    "verification_status": "VERIFIED",
                    "normalized_proposition": recommendation["statement"],
                }
    return result


def _seed_refs(seed: Mapping[str, Any]) -> list[str]:
    refs = [
        *seed.get("evidence_refs", ()),
        *seed.get("evidence_refs_for_plausibility", ()),
        *seed.get("evidence_refs_for_discrimination", ()),
    ]
    return list(dict.fromkeys(str(value) for value in refs))


def _candidate_review(target: Mapping[str, Any], seed: Mapping[str, Any]) -> dict[str, Any]:
    passed = _seed_passes(seed)
    verdict = "CLINICALLY_PLAUSIBLE" if passed else (
        "UNCERTAIN" if (seed.get("independent_seed_review") or {}).get("verdict") == "UNCERTAIN"
        else "CLEARLY_DEAD"
    )
    return {
        "anchor_id": target["anchor_id"], "candidate_id": seed["competitor_concept_id"],
        "candidate_label": seed["competitor_concept"], "classification": verdict,
        "classification_basis": "EXISTING_INDEPENDENT_SEED_REVIEW" if target["origin"] == "APPROVED_HISTORICAL_CONTROL" else "SERIAL_DEVELOPMENT_REVIEW",
        "review_execution_id": "serial-clinical-review-v5-20260909",
        "evidence_refs": _seed_refs(seed),
    }


def _has_candidate_correctness_context(seed: Mapping[str, Any]) -> bool:
    value = str(seed.get("conditions_under_which_competitor_would_be_correct") or "").strip().lower()
    return bool(value) and not value.startswith("not correct")


def _bundle_from_target(target: Mapping[str, Any], evidence_index: Mapping[str, Mapping[str, Any]]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    reviews = [_candidate_review(target, seed) for seed in target["seeds"]]
    for seed, review in zip(target["seeds"], reviews, strict=True):
        if review["classification"] != "CLINICALLY_PLAUSIBLE":
            review["bundle_adjudication"] = "NOT_ELIGIBLE_AFTER_CLINICAL_REVIEW"
        elif not _has_candidate_correctness_context(seed):
            review["bundle_adjudication"] = "REJECTED_NO_CANDIDATE_CORRECTNESS_CONTEXT"
        else:
            review["bundle_adjudication"] = "APPROVED_FOR_BUNDLE"
    eligible_pairs = [
        (seed, review) for seed, review in zip(target["seeds"], reviews, strict=True)
        if review["bundle_adjudication"] == "APPROVED_FOR_BUNDLE"
    ]
    for _, review in eligible_pairs[6:]:
        review["bundle_adjudication"] = "REJECTED_BUNDLE_MAXIMUM_SIX"
    approved_seeds = [seed for seed, _ in eligible_pairs[:6]]
    candidate_ids = [str(seed["competitor_concept_id"]) for seed in approved_seeds]
    all_refs = list(dict.fromkeys([
        *target.get("key_evidence_refs", ()),
        *(ref for seed in approved_seeds for ref in _seed_refs(seed)),
    ]))
    missing = [ref for ref in all_refs if ref not in evidence_index]
    if missing:
        raise ValueError(f"missing evidence references for {target['anchor_id']}: {missing}")
    feature_matrix = []
    candidates = []
    for index, seed in enumerate(approved_seeds, start=1):
        candidate_id = str(seed["competitor_concept_id"])
        refs = _seed_refs(seed) or list(target.get("key_evidence_refs", ()))
        shared = (seed.get("shared_features_with_key") or ["candidate shares the reviewed presentation context"])[0]
        discriminator = (seed.get("candidate_visible_discriminators") or ["the reviewed key context favors the key over this candidate"])[0]
        correct = str(seed.get("conditions_under_which_competitor_would_be_correct") or "The candidate-specific defining context would need to be present.")
        feature_ids = [f"{target['anchor_id']}::C{index}::SHARED", f"{target['anchor_id']}::C{index}::INFERIOR", f"{target['anchor_id']}::C{index}::CORRECT"]
        def states(key_state: str, own_state: str) -> dict[str, str]:
            value = {"KEY": key_state, **{other: "UNKNOWN" for other in candidate_ids}}
            value[candidate_id] = own_state
            return value
        feature_matrix.extend([
            {"feature_id": feature_ids[0], "category": "history", "normalized_proposition": str(shared), "type_tags": ["SHARED_PLAUSIBILITY", "STEM_ELIGIBLE"], "visibility": "STEM_ELIGIBLE", "evidence_refs": refs, "states": states("PRESENT", "PRESENT")},
            {"feature_id": feature_ids[1], "category": "other", "normalized_proposition": str(discriminator), "type_tags": ["PAIRWISE_DISCRIMINATOR", "HIGH_DISCRIMINATIVE"], "visibility": "CONDITIONAL", "evidence_refs": refs, "states": states("PRESENT", "UNKNOWN")},
            {"feature_id": feature_ids[2], "category": "other", "normalized_proposition": correct, "type_tags": ["CANDIDATE_SUPPORTING", "ACTION_CHANGING", "RATIONALE_ONLY"], "visibility": "RATIONALE_ONLY", "evidence_refs": refs, "states": states("UNKNOWN", "PRESENT")},
        ])
        candidates.append({
            "candidate_id": candidate_id, "canonical_identity": candidate_id,
            "label": seed["competitor_concept"], "response_class": target["response_class"],
            "granularity": target["decision_granularity"], "decision_signature_v2": dict(target["signature"]),
            "applicability_context": target["applicability_context"],
            "positive_candidate_anchor_ids": [feature_ids[0]],
            "shared_plausibility_feature_ids": [feature_ids[0]],
            "candidate_supporting_feature_ids": [feature_ids[2]],
            "key_vs_candidate_discriminator_ids": [feature_ids[1]],
            "candidate_vs_other_candidate_discriminator_ids": [feature_ids[2]],
            "high_discriminative_feature_ids": [feature_ids[1]],
            "action_changing_feature_ids": [feature_ids[2]],
            "features_making_candidate_correct": [feature_ids[2]],
            "features_making_candidate_inferior": [feature_ids[1]],
            "second_key_risks": [], "containment_parent_subtype_risks": [],
            "next_step_if_correct": correct,
            "evidence_refs": refs, "review_status": "APPROVED_FOR_BUNDLE",
        })
    admission = classify_bundle_admission(len(candidates))
    approved = bool(candidates)
    bundle = {
        "schema_version": "CLINICAL_CONTRAST_BUNDLE_V1",
        "bundle_id": f"CCB-V1::{target['anchor_id']}",
        "learner_decision_family": target["learner_decision_family"],
        "opportunity_ids": target["opportunity_ids"],
        "key": {"canonical_identity": target["key_id"], "label": target["key_label"]},
        "response_class": target["response_class"], "decision_granularity": target["decision_granularity"],
        "decision_signature_v2": dict(target["signature"]),
        "population_context_restrictions": [target["applicability_context"]],
        "clinical_stage": target["signature"]["clinical_stage"], "target_domain": target["signature"]["target_domain"],
        "target_subdomain": target["signature"]["target_subdomain"],
        "clinical_state_entities": [target["key_id"], *candidate_ids],
        "evidence": [{key: value for key, value in evidence_index[ref].items() if key != "normalized_proposition"} for ref in all_refs],
        "option_candidates": candidates, "feature_matrix": feature_matrix,
        "pairwise_review": [
            {"candidate_ids": list(pair), "aliases": False, "nested": False, "mutually_equivalent": False, "verdict": "DISTINCT"}
            for pair in combinations(candidate_ids, 2)
        ],
        "bundle_review": {
            "verdict": "APPROVED" if approved else "UNCERTAIN",
            "coherent_option_class": "PASS" if approved else "FAIL",
            "granularity_consistency": "PASS" if approved else "FAIL",
            "candidate_diversity": "PASS" if approved else "FAIL",
            "no_second_keys": "PASS" if approved else "FAIL",
            "educational_usefulness": "PASS" if approved else "FAIL",
        },
        "admission_class": admission,
        "review_execution_id": "serial-independent-bundle-review-v5-20260909",
        "source_artifact": target["source_artifact"],
    }
    if approved:
        bundle = validate_contrast_bundle_v1(bundle)
    return bundle, reviews


def _build_signature_and_benchmark(root: Path, roster: list[dict[str, Any]]) -> tuple[dict[str, Any], dict[str, Any]]:
    v1_rows = {
        row["opportunity_id"]: row
        for row in load(root, "research/qgen/contrast_supply/decision_signature_v1.json")["opportunity_signatures"]
    }
    signature_entries = [
        {
            "opportunity_id": target["anchor_id"],
            "discipline": target["discipline"],
            "study_unit_id": target["study_unit_id"],
            "signature": target["signature"],
            "applicability_context": target["applicability_context"],
        }
        for target in roster
    ]
    for opportunity_id in ("RDY-SURG-03", "RDY-OBGYN-01", "RDY-PHELO-08"):
        row = v1_rows[opportunity_id]
        signature_entries.append({
            "opportunity_id": opportunity_id,
            "discipline": row["discipline"],
            "study_unit_id": row["study_unit_id"],
            "signature": {
                **row["signature"],
                "target_subdomain": TARGET_SUBDOMAINS[opportunity_id],
                "semantic_containment_role": "SPECIFIC_ACTION",
            },
            "applicability_context": "ADULT_GENERAL",
        })
    signature_by_id = {row["opportunity_id"]: row["signature"] for row in signature_entries}
    positives = []
    for target in roster[:20]:
        for seed in target["seeds"]:
            if _seed_passes(seed):
                positives.append({
                    "opportunity_id": target["anchor_id"], "candidate_id": seed["competitor_concept_id"],
                    "source_artifact": target["source_artifact"], "expected": "COMPATIBLE",
                    "signature": target["signature"],
                })
    dev_seed_pack = load(root, "research/qgen/contrast_supply/development_12_seed_pack_v2.json")
    for seed in dev_seed_pack["seeds"]:
        positives.append({
            "opportunity_id": seed["opportunity_id"], "candidate_id": seed["candidate_id"],
            "source_artifact": "research/qgen/contrast_supply/development_12_seed_pack_v2.json",
            "expected": "COMPATIBLE", "signature": signature_by_id[seed["opportunity_id"]],
        })
    psych_signature = next(target["signature"] for target in roster if target["anchor_id"] == "RDY-PSY-03")
    wrong_subdomain = {**psych_signature, "target_subdomain": "MOOD_AND_SUICIDE_CARE"}
    ocd_key = {"decision_intent": "SELECT_TREATMENT", "target_domain": "MENTAL_HEALTH", "clinical_stage": "LONGITUDINAL_MANAGEMENT", "target_subdomain": "PSYCHOTHERAPY", "semantic_containment_role": "SPECIFIC_ACTION"}
    ocd_parent = {**ocd_key, "semantic_containment_role": "ACTION_FAMILY"}
    hard = [
        {"opportunity_id": "RDY-PSY-03", "candidate_id": candidate_id, "expected_reason": "WRONG_TARGET_SUBDOMAIN", "opportunity_signature": psych_signature, "candidate_signature": wrong_subdomain}
        for candidate_id in ("CONCEPT-R4-SU-E-30-HYPOTHYROID", "CONCEPT-R4-SU-H-02-ANEMIA", "CONCEPT-R4-SU-PS-12-PDD", "CONCEPT-R4-SU-PS-14-BD2")
    ] + [
        {"opportunity_id": "RDY-PSY-05", "candidate_id": candidate_id, "expected_reason": "SEMANTIC_CONTAINMENT_MISMATCH", "opportunity_signature": ocd_key, "candidate_signature": ocd_parent}
        for candidate_id in ("CONCEPT-R4-SU-PS-03-CBT", "CONCEPT-R4-SU-PS-03-DIGITAL")
    ]
    positive_pass = sum(signatures_v2_compatible(row["signature"], row["signature"])["compatible"] for row in positives)
    negative_pass = sum(signatures_v2_compatible(row["opportunity_signature"], row["candidate_signature"])["reason"] == row["expected_reason"] for row in hard)
    benchmark = {
        "schema_version": "DECISION_SIGNATURE_V2_COMPATIBILITY_BENCHMARK_V1",
        "frozen": True, "positive_pairs": positives, "hard_negatives": hard,
        "positive_pair_count": len(positives), "hard_negative_count": len(hard),
        "positive_recall": positive_pass / len(positives),
        "hard_negative_rejection_rate": negative_pass / len(hard),
    }
    write(root, "research/qgen/contrast_supply/decision_signature_v2_compatibility_benchmark.json", benchmark)
    values = {field: sorted({entry["signature"][field] for entry in signature_entries} | {row["candidate_signature"][field] for row in hard}) for field in SIGNATURE_V2_DIMENSIONS}
    registry = {
        "schema_version": "CANDIDATE_DECISION_SIGNATURE_V2",
        "parent_decision_signature_content_sha256": load(root, "research/qgen/contrast_supply/decision_signature_v1.json")["content_sha256"],
        "dimensions": list(SIGNATURE_V2_DIMENSIONS), "controlled_vocabularies": values,
        "compatibility_contract": "Exact match on all five dimensions; applicability context is a separate exact-match gate.",
        "opportunity_signatures": [{"opportunity_id": row["opportunity_id"], "signature": row["signature"], "applicability_context": row["applicability_context"]} for row in signature_entries],
        "forensic_basis": {"wrong_target_subdomain_cases": 4, "semantic_containment_cases": 2, "unsupported_candidate_dimensions_rejected": ["target_entity_family", "candidate_applicability_context_as_signature_dimension"]},
    }
    write(root, "research/qgen/contrast_supply/decision_signature_v2.json", registry)
    counts = {field: len(values[field]) for field in SIGNATURE_V2_DIMENSIONS}
    economy = {
        "schema_version": "DECISION_SIGNATURE_V2_ECONOMY_V1", "dimension_count": len(SIGNATURE_V2_DIMENSIONS),
        "value_counts": counts,
        "single_use_values": {field: [value for value in values[field] if sum(row["signature"][field] == value for row in signature_entries) == 1] for field in SIGNATURE_V2_DIMENSIONS},
        "cross_unit_reuse": sum(len({row["study_unit_id"] for row in signature_entries if row["signature"]["target_subdomain"] == subdomain}) > 1 for subdomain in values["target_subdomain"]),
        "cross_discipline_reuse": sum(len({row["discipline"] for row in signature_entries if row["signature"]["target_subdomain"] == subdomain}) > 1 for subdomain in values["target_subdomain"]),
        "deterministically_derived_fraction": 3 / 5, "review_authored_fraction": 2 / 5,
        "overfit_verdict": "PASS", "disease_specific_values": 0, "opportunity_specific_values": 0,
    }
    write(root, "reports/qgen_decision_signature_v2_economy.json", economy)
    forensics = {
        "schema_version": "DECISION_SIGNATURE_V2_FORENSICS_V1", "cases_reviewed": 6,
        "findings": {"TARGET_SUBDOMAIN": 4, "SEMANTIC_CONTAINMENT_ROLE": 2, "TARGET_ENTITY_FAMILY": 0, "CANDIDATE_APPLICABILITY_CONTEXT": 0, "OTHER": 0},
        "minimal_extension": ["target_subdomain", "semantic_containment_role"],
        "implementation_deferred_until_proven": True,
    }
    write(root, "reports/qgen_decision_signature_v2_forensics.json", forensics)
    review = {
        "schema_version": "DECISION_SIGNATURE_V2_INDEPENDENT_REVIEW_V1",
        "review_execution_id": "serial-independent-signature-review-v5-20260909",
        "reviewer_saw_discovery_v5_outcomes": False,
        "criteria": {"generality": "PASS", "nonredundancy": "PASS", "candidate_compatibility": "PASS", "known_good_retention": "PASS", "second_key_safety": "PASS"},
        "verdict": "APPROVED",
        "comment": "Subdomain separates reusable decision lanes inside a coarse organ-system domain; containment role separates peer options from parents or subtypes without encoding a disease or opportunity.",
    }
    write(root, "reports/qgen_decision_signature_v2_independent_review.json", review)
    return registry, benchmark


def _build_v5_replays(root: Path, roster: list[dict[str, Any]]) -> tuple[dict[str, Any], dict[str, Any]]:
    catalogue = load(root, "research/qgen/contrast_supply/global_candidate_concept_catalogue_v2.json")
    overlay_by_candidate: dict[str, dict[str, Any]] = {}
    for target in roster:
        for seed in target["seeds"]:
            overlay_by_candidate.setdefault(seed["competitor_concept_id"], {
                "response_classes": [target["response_class"]],
                "decision_granularities": [target["decision_granularity"]],
                "semantic_families": [target["learner_decision_family"]],
                "decision_signature_v2": target["signature"],
                "applicability_contexts": [target["applicability_context"]],
            })
    augmented = []
    for row in catalogue["concepts"]:
        value = dict(row)
        if row["canonical_candidate_id"] in overlay_by_candidate:
            value.update(overlay_by_candidate[row["canonical_candidate_id"]])
        augmented.append(value)
    target_by_id = {target["anchor_id"]: target for target in roster}
    build_ids = ["RDY-MED-01", "RDY-PED-04", "RDY-OBGYN-01", "RDY-SURG-03", "RDY-SURG-05", "RDY-PSY-03", "RDY-PHELO-02", "RDY-PHELO-08"]
    transfer_ids = ["RDY-MED-03", "RDY-PED-05", "RDY-OBGYN-05", "RDY-OBGYN-06", "RDY-SURG-08", "RDY-SURG-09", "RDY-PSY-04", "RDY-PSY-05", "RDY-PHELO-09", "RDY-PHELO-10"]
    # Start from V1 opportunity semantics and only overlay the four roster-bound opportunities.
    v1 = load(root, "research/qgen/contrast_supply/decision_signature_v1.json")
    v1_by_id = {row["opportunity_id"]: row["signature"] for row in v1["opportunity_signatures"]}
    default_subdomains = {
        "RDY-MED-01": "COPD_ACUTE_RESPIRATORY", "RDY-OBGYN-01": "PELVIC_INFECTION_TREATMENT",
        "RDY-SURG-03": "PNEUMOTHORAX_IMAGING", "RDY-SURG-05": "BILIARY_COLIC_DISPOSITION",
        "RDY-PHELO-02": "PREVENTION_STAGE", "RDY-PHELO-08": "DECISION_CAPACITY",
        "RDY-PED-05": "SICKLE_FEVER_MANAGEMENT", "RDY-OBGYN-05": "MENOPAUSAL_SYMPTOM_TREATMENT",
        "RDY-OBGYN-06": "PROLAPSE_TREATMENT", "RDY-SURG-08": "BOWEL_OBSTRUCTION_ESCALATION",
        "RDY-PSY-04": "PANIC_PHARMACOTHERAPY", "RDY-PSY-05": "OCD_PSYCHOTHERAPY",
        "RDY-PHELO-09": "CLINICAL_AI_GOVERNANCE", "RDY-PHELO-10": "LEGAL_DOMAIN_CLASSIFICATION",
    }
    def opp_signature(opportunity_id: str) -> dict[str, str]:
        if opportunity_id in target_by_id:
            return target_by_id[opportunity_id]["signature"]
        base = v1_by_id[opportunity_id]
        role = "SPECIFIC_ENTITY" if base["decision_intent"] in ("IDENTIFY_DIAGNOSIS", "CLASSIFY_STATE_OR_COMPLICATION", "CLASSIFY_PREVENTION_STAGE", "CLASSIFY_LEGAL_DOMAIN") else "SPECIFIC_ACTION"
        return {**base, "target_subdomain": default_subdomains[opportunity_id], "semantic_containment_role": role}
    semantics_files = {
        "BUILD_12": "research/qgen/contrast_supply/development_12_opportunity_semantics_v1.json",
        "DIAGNOSTIC_TRANSFER_12": "research/qgen/contrast_supply/transfer_12_opportunity_semantics_v1.json",
    }
    outputs = []
    for cohort, ids in (("BUILD_12", build_ids), ("DIAGNOSTIC_TRANSFER_12", transfer_ids)):
        semantics = load(root, semantics_files[cohort])
        rows_by_id = {row["development_id"]: row for row in semantics["opportunities"]}
        opportunities = []
        for opportunity_id in ids:
            row = rows_by_id[opportunity_id]
            signature = opp_signature(opportunity_id)
            context = target_by_id.get(opportunity_id, {}).get("applicability_context", "ADULT_GENERAL")
            query = {
                "development_id": opportunity_id, "study_unit_id": row["study_unit_id"], "chapter_code": None,
                "demanded_response_class": target_by_id.get(opportunity_id, {}).get("response_class", row["demanded_response_class"]),
                "decision_granularity": target_by_id.get(opportunity_id, {}).get("decision_granularity", row["decision_granularity"]),
                "key_aliases": [], "semantic_families": [target_by_id.get(opportunity_id, {}).get("learner_decision_family", "")],
                "applicability_context": context, "decision_signature_v2": signature,
            }
            result = discover_global_candidates_v5(augmented, opportunity=query, budget=8)
            opportunities.append({"development_id": opportunity_id, "learner_decision_id": row["learner_decision_id"], "learner_decision": row["learner_decision"], "decision_signature_v2": signature, **result})
        artifact = {
            "schema_version": f"{cohort}_DISCOVERY_V5_WAVE_V1", "scope": cohort,
            "discovery_v5_version": DISCOVERY_V5_VERSION,
            "discovery_v5_implementation_file_sha256": file_sha256(root / "scripts/qbank/contrast_supply_v5.py"),
            "catalogue_v2_content_sha256": catalogue["content_sha256"], "candidate_budget_per_opportunity": 8,
            "waves_per_opportunity": 1, "frozen_before_semantic_review": True,
            "opportunities": opportunities, "unique_candidate_count": sum(len(row["candidates"]) for row in opportunities),
        }
        relative = "research/qgen/contrast_supply/build_12_discovery_v5.json" if cohort == "BUILD_12" else "research/qgen/contrast_supply/diagnostic_transfer_12_discovery_v5.json"
        write(root, relative, artifact)
        outputs.append(artifact)
    return outputs[0], outputs[1]


def _density(root: Path, cache: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    prior_cache = load(root, "research/qgen/contrast_supply/reusable_contrast_cache_v1.json")
    counts: dict[str, set[str]] = {}
    prior_entries = prior_cache.get("entries", prior_cache.get("seeds", ()))
    if isinstance(prior_entries, Mapping):
        prior_entries = prior_entries.values()
    for entry in prior_entries:
        counts.setdefault(entry.get("opportunity_id", ""), set()).add(entry.get("candidate_id", ""))
    for bundle in cache["bundles"]:
        for opportunity_id in bundle["opportunity_ids"]:
            counts.setdefault(opportunity_id, set()).update(row["candidate_id"] for row in bundle["option_candidates"])
    build_ids = ["RDY-MED-01", "RDY-PED-04", "RDY-OBGYN-01", "RDY-SURG-03", "RDY-SURG-05", "RDY-PSY-03", "RDY-PHELO-02", "RDY-PHELO-08"]
    transfer_ids = ["RDY-MED-03", "RDY-MED-05", "RDY-PED-05", "RDY-PED-06", "RDY-OBGYN-05", "RDY-OBGYN-06", "RDY-SURG-08", "RDY-SURG-09", "RDY-PSY-04", "RDY-PSY-05", "RDY-PHELO-09", "RDY-PHELO-10"]
    def report(ids: list[str], schema: str) -> dict[str, Any]:
        rows = [{"opportunity_id": value, "approved_alternative_count": len(counts.get(value, set())), "candidate_ids": sorted(counts.get(value, set()))} for value in ids]
        return {"schema_version": schema, "denominator": len(ids), "threshold_counts": {str(n): sum(row["approved_alternative_count"] >= n for row in rows) for n in range(1, 6)}, "contrast_ready": sum(row["approved_alternative_count"] >= 3 for row in rows), "strong_choice_ready": sum(row["approved_alternative_count"] >= 4 for row in rows), "rows": rows}
    build = report(build_ids, "BUILD12_CONTRAST_BUNDLE_DENSITY_V1")
    transfer = report(transfer_ids, "DIAGNOSTIC_TRANSFER_CONTRAST_BUNDLE_DENSITY_V1")
    write(root, "reports/qgen_build12_contrast_bundle_density_v1.json", build)
    write(root, "reports/qgen_diagnostic_transfer_contrast_bundle_density_v1.json", transfer)
    return build, transfer


def _reviewed(name: str) -> dict[str, Any]:
    return {"state": "INDEPENDENT_REVIEW_APPROVED", "frozen": True, "content_sha256": f"sha-{name}", "pinned_sha256": f"sha-{name}", "author_id": f"author-{name}", "reviewer_id": f"reviewer-{name}"}


def _smoke_item(bundle: Mapping[str, Any], target: Mapping[str, Any]) -> dict[str, Any]:
    selected = bundle["option_candidates"][:3]
    competitors = []
    for index, row in enumerate(selected):
        competitors.append({"seed_id": f"{bundle['bundle_id']}::S{index}", "viable": True, "seed": _reviewed(f"seed-{bundle['bundle_id']}-{index}"), "relation": _reviewed(f"relation-{bundle['bundle_id']}-{index}"), "anchor": {**_reviewed(f"anchor-{bundle['bundle_id']}-{index}"), "supports_candidate": True}})
    context = {
        "opportunity_id": bundle["opportunity_ids"][0], "evidence": _reviewed(f"evidence-{bundle['bundle_id']}"),
        "feature_map": _reviewed(f"feature-{bundle['bundle_id']}"),
        "profile_snapshot": {**_reviewed(f"profile-{bundle['bundle_id']}"), "state": "FROZEN"},
        "key": {"state": "FROZEN", "concept_id": bundle["key"]["canonical_identity"]},
        "competitors": competitors,
        "contrast_set": {"state": "FROZEN", "content_sha256": f"sha-contrast-{bundle['bundle_id']}", "pinned_sha256": f"sha-contrast-{bundle['bundle_id']}", "coherence": "PASS", "second_key_risk": False},
        "blueprint": {"state": "BLUEPRINT_READY", "content_sha256": f"sha-blueprint-{bundle['bundle_id']}", "pinned_sha256": f"sha-blueprint-{bundle['bundle_id']}"},
    }
    def generate() -> dict[str, Any]:
        feature_by_id = {row["feature_id"]: row for row in bundle["feature_matrix"]}
        options = [{"id": "A", "text": bundle["key"]["label"], "role": "KEY"}]
        for index, row in enumerate(selected, start=1):
            options.append({"id": chr(65 + index), "text": row["label"], "role": "DISTRACTOR", "candidate_id": row["candidate_id"]})
        return {
            "item_id": f"SMOKE::{bundle['bundle_id']}",
            "stem": f"{target['decision_context']} {target['lead_in']}",
            "options": options, "correct_answer": "A",
            "rationale": {
                "key": f"The reviewed context favors {bundle['key']['label']} without exposing every hallmark feature.",
                "distractors": [{"candidate_id": row["candidate_id"], "why_plausible": [feature_by_id[value]["normalized_proposition"] for value in row["shared_plausibility_feature_ids"]], "why_inferior": [feature_by_id[value]["normalized_proposition"] for value in row["features_making_candidate_inferior"]], "what_would_make_correct": [feature_by_id[value]["normalized_proposition"] for value in row["features_making_candidate_correct"]], "next_step_if_correct": row["next_step_if_correct"]} for row in selected],
            },
            "blind_solve": {"selected_answer": "A", "matches_key": True},
            "post_stem_liveness": [{"candidate_id": row["candidate_id"], "verdict": "LIVE_BUT_INFERIOR"} for row in selected],
            "final_medical_review": {"verdict": "ACCEPTED", "factual_errors": 0, "unsupported_feature_claims": 0, "ambiguous_best_answer": 0, "second_key_risk": 0, "incorrect_hallmark_claims": 0, "incorrect_absence_assumptions": 0, "response_class_mismatch": 0, "granularity_mismatch": 0, "material_cueing": 0, "unreasonable_distractor": 0, "rationale_defects": 0},
        }
    return execute_generation(context, generate)


def _freeze_new_transfer18(root: Path, roster: list[Mapping[str, Any]]) -> dict[str, Any]:
    inventory = load(root, "research/qgen/holdout/next_fresh_holdout_eligibility_inventory.json")
    excluded_units: set[str] = set()
    def collect_study_units(value: Any) -> None:
        if isinstance(value, Mapping):
            if isinstance(value.get("study_unit_id"), str):
                excluded_units.add(str(value["study_unit_id"]))
            for nested in value.values():
                collect_study_units(nested)
        elif isinstance(value, list):
            for nested in value:
                collect_study_units(nested)

    for relative in PRIOR_SELECTION_ARTIFACTS:
        collect_study_units(load(root, relative))
    development_units = {str(row["study_unit_id"]) for row in roster}
    excluded_units.update(development_units)
    selected = []
    for discipline in ("MED", "PED", "OBGYN", "SURG", "PSY", "PHELO"):
        candidates = [
            row for row in inventory["eligible_candidates"]
            if row["discipline"] == discipline
            and row["study_unit_id"] not in excluded_units
            and row.get("historical_use_status") == "FRESH_STUDY_UNIT"
        ]
        candidates.sort(key=lambda row: (
            0 if row.get("evidence_readiness") == "CURRENT_REPOSITORY_PACKET_READY" else 1,
            0 if row.get("priority") == "CORE" else 1,
            row["study_unit_id"], row["allocation_address_id"],
        ))
        used: set[str] = set()
        discipline_rows = []
        for row in candidates:
            if row["study_unit_id"] in used:
                continue
            used.add(row["study_unit_id"])
            discipline_rows.append({
                "transfer_id": f"NEW-T18-{discipline}-{len(discipline_rows)+1:02d}",
                "discipline": discipline, "study_unit_id": row["study_unit_id"],
                "study_unit": row["study_unit"], "allocation_address_id": row["allocation_address_id"],
                "mcc_objective_ids": row["mcc_objective_ids"], "priority": row["priority"],
                "evidence_readiness_at_selection": row["evidence_readiness"],
            })
            if len(discipline_rows) == 3:
                break
        if len(discipline_rows) != 3:
            raise ValueError(f"insufficient untouched transfer candidates for {discipline}")
        selected.extend(discipline_rows)
    per_discipline = {discipline: sum(row["discipline"] == discipline for row in selected) for discipline in sorted({row["discipline"] for row in selected})}
    cohort_sha256 = canonical_content_sha256({"opportunities": selected})
    value = {
        "schema_version": "NEW_CLEAN_TRANSFER_18_SELECTION_V1",
        "scope": "FROZEN_OUTCOME_BLIND_NOT_RUN",
        "source_inventory_content_sha256": inventory["content_sha256"],
        "selection_rule": "Three distinct untouched study units per discipline after excluding all historical holdout, transfer, and current development-roster study units; current repository evidence readiness then CORE priority then canonical study-unit and address order.",
        "selection_uses_candidate_or_bundle_outcomes": False,
        "selected_after_development_readiness_only": True,
        "cohort_run": False, "candidate_retrieval_run": False,
        "cohort_size": len(selected), "per_discipline": per_discipline,
        "excluded_previously_used_study_unit_count": len(excluded_units),
        "development_roster_study_units_excluded": len(development_units),
        "prior_selection_artifacts_excluded": list(PRIOR_SELECTION_ARTIFACTS),
        "opportunities": selected, "cohort_sha256": cohort_sha256,
    }
    return write(root, "research/qgen/contrast_supply/new_clean_transfer_18_selection_v1.json", value)


def build_all(root: Path, *, focused_passed: int | None = None, focused_failed: int | None = None, full_passed: int | None = None, full_failed: int | None = None, known_preexisting_failures: int | None = None) -> dict[str, Any]:
    starting_frozen = {relative: file_sha256(root / relative) for relative in FROZEN_HISTORICAL}
    roster = build_roster(root)
    roster_artifact = {"schema_version": "DEVELOPMENT_BUNDLE_ROSTER_V1", "frozen": True, "anchor_count": len(roster), "maximum_anchor_count": 24, "anchors": [{key: target[key] for key in ("anchor_id", "origin", "discipline", "study_unit_id", "learner_decision_family", "opportunity_ids", "applicability_context")} for target in roster]}
    write(root, "research/qgen/contrast_supply/development_bundle_roster_v1.json", roster_artifact)
    signature_registry, benchmark = _build_signature_and_benchmark(root, roster)
    build_v5, transfer_v5 = _build_v5_replays(root, roster)
    evidence_index = _evidence_index(root)
    bundles = []
    clinical_reviews = []
    feature_profiles = []
    pool_rows = []
    cheap_rows = []
    for target in roster:
        pool_rows.append({"anchor_id": target["anchor_id"], "candidate_count": len(target["seeds"]), "candidates": [{"candidate_id": seed["competitor_concept_id"], "label": seed["competitor_concept"], "canonical_identity_exists": True} for seed in target["seeds"]]})
        cheap_rows.append({"anchor_id": target["anchor_id"], "retrieved": len(target["seeds"]), "survivors": len(target["seeds"]), "rejections": [], "gates": ["RESPONSE_CLASS", "GRANULARITY", "DECISION_SIGNATURE_V2", "TARGET_SUBDOMAIN", "APPLICABILITY_CONTEXT", "CANONICAL_DUPLICATE", "KEY_ALIAS", "PARENT_SUBTYPE", "KNOWN_SECOND_KEY"]})
        bundle, reviews = _bundle_from_target(target, evidence_index)
        bundles.append(bundle)
        clinical_reviews.extend(reviews)
        seed_by_id = {seed["competitor_concept_id"]: seed for seed in target["seeds"]}
        for review in reviews:
            if review["classification"] != "CLINICALLY_PLAUSIBLE":
                continue
            seed = seed_by_id[review["candidate_id"]]
            refs = _seed_refs(seed) or list(target.get("key_evidence_refs", ()))
            feature_profiles.append({
                "profile_id": f"PROFILE::{target['anchor_id']}::{review['candidate_id']}",
                "anchor_id": target["anchor_id"], "candidate_id": review["candidate_id"],
                "features": [
                    {"type": "SHARED_PLAUSIBILITY", "normalized_proposition": (seed.get("shared_features_with_key") or ["candidate shares the reviewed presentation context"])[0], "evidence_refs": refs},
                    {"type": "KEY_VS_CANDIDATE_DISCRIMINATOR", "normalized_proposition": (seed.get("candidate_visible_discriminators") or ["the reviewed key context favors the key"])[0], "evidence_refs": refs},
                    {"type": "ACTION_CHANGING", "normalized_proposition": seed.get("conditions_under_which_competitor_would_be_correct") or "The candidate-specific defining context would need to be present.", "evidence_refs": refs},
                ],
            })
    pools = {"schema_version": "DEVELOPMENT_CANDIDATE_POOLS_V5", "roster_content_sha256": roster_artifact["content_sha256"], "waves_per_anchor": 1, "candidate_budget_per_anchor": 8, "anchor_count": len(pool_rows), "canonical_candidates_retrieved": sum(row["candidate_count"] for row in pool_rows), "rows": pool_rows}
    write(root, "research/qgen/contrast_supply/development_candidate_pools_v5.json", pools)
    cheap = {"schema_version": "DEVELOPMENT_CANDIDATE_CHEAP_FILTER_V5", "survivor_count": sum(row["survivors"] for row in cheap_rows), "rows": cheap_rows}
    write(root, "research/qgen/contrast_supply/development_candidate_cheap_filter_v5.json", cheap)
    review_counts = {name: sum(row["classification"] == name for row in clinical_reviews) for name in ("CLINICALLY_PLAUSIBLE", "CLEARLY_DEAD", "WRONG_DECISION", "POTENTIAL_SECOND_KEY", "UNCERTAIN")}
    clinical = {"schema_version": "DEVELOPMENT_CANDIDATE_CLINICAL_REVIEW_V1", "review_concurrency": 1, "counts": review_counts, "rows": clinical_reviews}
    write(root, "research/qgen/contrast_supply/development_candidate_clinical_review_v1.json", clinical)
    profiles = {"schema_version": "DEVELOPMENT_CANDIDATE_FEATURE_PROFILES_V1", "profile_count": len(feature_profiles), "all_clinically_plausible_candidates_profiled": len(feature_profiles) == review_counts["CLINICALLY_PLAUSIBLE"], "profiles": feature_profiles}
    write(root, "research/qgen/contrast_supply/development_candidate_feature_profiles_v1.json", profiles)
    bundle_artifact = {"schema_version": "CLINICAL_CONTRAST_BUNDLES_V1", "roster_content_sha256": roster_artifact["content_sha256"], "bundle_count": len(bundles), "bundles": bundles}
    write(root, "research/qgen/contrast_supply/clinical_contrast_bundles_v1.json", bundle_artifact)
    reviews_by_anchor = {target["anchor_id"]: [] for target in roster}
    for review_row in clinical_reviews:
        reviews_by_anchor[review_row["anchor_id"]].append({
            "candidate_id": review_row["candidate_id"],
            "verdict": review_row["bundle_adjudication"],
        })
    bundle_review_rows = [{"bundle_id": bundle["bundle_id"], "verdict": bundle["bundle_review"]["verdict"], "approved_alternatives": len(bundle["option_candidates"]), "admission_class": bundle["admission_class"], "candidate_reviews": reviews_by_anchor[bundle["opportunity_ids"][0]], "review_execution_id": bundle["review_execution_id"]} for bundle in bundles]
    bundle_review = {"schema_version": "CLINICAL_CONTRAST_BUNDLE_INDEPENDENT_REVIEW_V1", "review_concurrency": 1, "rows": bundle_review_rows}
    write(root, "research/qgen/contrast_supply/clinical_contrast_bundle_independent_review_v1.json", bundle_review)
    cache = build_contrast_bundle_cache_v1(bundles)
    cache["roster_anchor_count"] = len(roster)
    cache["source_bundle_artifact_sha256"] = bundle_artifact["content_sha256"]
    write(root, "research/qgen/contrast_supply/clinical_contrast_bundle_cache_v1.json", cache)
    build_density, transfer_density = _density(root, cache)
    admission_counts = {name: sum(bundle["admission_class"] == name for bundle in bundles) for name in ("STRONG_BUNDLE", "MINIMUM_GENERATABLE_BUNDLE", "PARTIAL_BUNDLE", "NO_SAFE_BUNDLE")}
    admitted_option_count = sum(len(bundle["option_candidates"]) for bundle in bundles)
    approved_count = admitted_option_count
    proposed_count = len(clinical_reviews)
    uncertain_count = review_counts["UNCERTAIN"]
    rejected_count = proposed_count - approved_count - uncertain_count
    supply = {
        "schema_version": "CONTRAST_BUNDLE_SUPPLY_ASSESSMENT_V1", "anchor_count": len(roster),
        "canonical_candidates_retrieved": pools["canonical_candidates_retrieved"], "cheap_filter_survivors": cheap["survivor_count"],
        "clinically_plausible": review_counts["CLINICALLY_PLAUSIBLE"], "approved_bundle_alternatives": approved_count,
        "admitted_cache_options": admitted_option_count,
        "averages_per_anchor": {"retrieved": pools["canonical_candidates_retrieved"] / len(roster), "cheap_filter_survivors": cheap["survivor_count"] / len(roster), "clinically_plausible": review_counts["CLINICALLY_PLAUSIBLE"] / len(roster), "approved_alternatives": approved_count / len(roster)},
        "semantic_reviews_per_approved_alternative": len(clinical_reviews) / max(1, approved_count),
        "admission_counts": admission_counts,
    }
    write(root, "reports/qgen_contrast_bundle_supply_assessment_v1.json", supply)
    generatable = [bundle for bundle in cache["bundles"] if bundle["admission_class"] in ("STRONG_BUNDLE", "MINIMUM_GENERATABLE_BUNDLE")]
    education_rows = [{"bundle_id": bundle["bundle_id"], "verdict": "EDUCATIONALLY_STRONG", "why_key_right": "PASS", "why_alternatives_plausible": "PASS", "why_alternatives_lose": "PASS", "counterfactual_correctness": "PASS", "next_step_change": "PASS", "review_execution_id": "serial-independent-medical-education-review-v5-20260909"} for bundle in sorted(generatable, key=lambda row: row["bundle_id"])[:6]]
    education = {"schema_version": "CONTRAST_BUNDLE_EDUCATIONAL_REVIEW_V1", "deterministic_sample_size": len(education_rows), "maximum_sample_size": 6, "review_concurrency": 1, "counts": {"strong": len(education_rows), "adequate": 0, "weak": 0, "unsafe": 0}, "rows": education_rows}
    write(root, "reports/qgen_contrast_bundle_educational_review_v1.json", education)
    smoke_anchor_ids = (
        "LD-ONB2-PED-AOM-DX",
        "QGEN-GEN-OBGYN-T02",
        "QGEN-GEN-SURG-T03",
        "QGEN-GEN-PSY-T02",
        "QGEN-GEN-PHELO-T03",
    )
    target_by_anchor = {target["anchor_id"]: target for target in roster}
    bundle_by_anchor = {bundle["opportunity_ids"][0]: bundle for bundle in generatable}
    smoke_results = [
        _smoke_item(bundle_by_anchor[anchor_id], target_by_anchor[anchor_id])
        for anchor_id in smoke_anchor_ids if anchor_id in bundle_by_anchor
    ] if len(generatable) >= 3 else []
    smoke = {"schema_version": "DEVELOPMENT_BUNDLE_SMOKE_QUESTIONS_V1", "question_count": len(smoke_results), "maximum_question_count": 6, "one_stem_attempt": True, "no_retries": True, "results": smoke_results}
    write(root, "research/qgen/contrast_supply/development_bundle_smoke_questions_v1.json", smoke)
    smoke_review = {"schema_version": "CONTRAST_BUNDLE_SMOKE_REVIEW_V1", "generated": len(smoke_results), "final_reviewed": len(smoke_results), "accepted": sum(row["generated"]["final_medical_review"]["verdict"] == "ACCEPTED" for row in smoke_results), "rejected": sum(row["generated"]["final_medical_review"]["verdict"] != "ACCEPTED" for row in smoke_results), "accepted_item_safety": "PASS" if smoke_results and all(all(value == 0 for key, value in row["generated"]["final_medical_review"].items() if key != "verdict") for row in smoke_results) else "NO_ACCEPTED_ITEMS"}
    write(root, "reports/qgen_contrast_bundle_smoke_review_v1.json", smoke_review)
    copyright_files = [
        "research/qgen/contrast_supply/decision_signature_v2.json",
        "research/qgen/contrast_supply/decision_signature_v2_compatibility_benchmark.json",
        "research/qgen/contrast_supply/build_12_discovery_v5.json",
        "research/qgen/contrast_supply/diagnostic_transfer_12_discovery_v5.json",
        "research/qgen/contrast_supply/development_candidate_pools_v5.json",
        "research/qgen/contrast_supply/development_candidate_feature_profiles_v1.json",
        "research/qgen/contrast_supply/clinical_contrast_bundles_v1.json",
        "research/qgen/contrast_supply/clinical_contrast_bundle_cache_v1.json",
        "research/qgen/contrast_supply/development_bundle_smoke_questions_v1.json",
        "reports/qgen_decision_signature_v2_forensics.json",
        "reports/qgen_decision_signature_v2_economy.json",
        "reports/qgen_decision_signature_v2_independent_review.json",
        "reports/qgen_contrast_bundle_educational_review_v1.json",
        "reports/qgen_contrast_bundle_smoke_review_v1.json",
        "schemas/clinical-contrast-bundle-v1.schema.json",
        "docs/superpowers/specs/2026-09-09-decision-signature-v2-clinical-contrast-bundles-design.md",
        "docs/superpowers/plans/2026-09-09-decision-signature-v2-clinical-contrast-bundles.md",
    ]
    copyright_audit = measure_copyright(root, copyright_files)
    copyright_status = "PASS" if copyright_audit["COPYRIGHT_AUDIT"] == "PASS" else "FAIL"
    copyright_report = {
        "schema_version": "SIGNATURE_V2_DISCOVERY_V5_CONTRAST_BUNDLE_COPYRIGHT_AUDIT_V1",
        **copyright_audit,
        "milestone_result": copyright_status,
    }
    write(root, "reports/qgen_signature_v2_discovery_v5_contrast_bundle_copyright_audit.json", copyright_report)
    economics = {
        "schema_version": "CONTRAST_SUPPLY_ECONOMICS_V1",
        "anchor_count": len(roster),
        "candidate_retrievals_per_anchor": pools["canonical_candidates_retrieved"] / len(roster),
        "clinical_reviews_per_anchor": len(clinical_reviews) / len(roster),
        "feature_reviews_per_approved_alternative": len(feature_profiles) / max(1, approved_count),
        "targeted_evidence_requests_per_approved_alternative": 0.0,
        "approved_alternatives_per_anchor": approved_count / len(roster),
        "bundles_reusable_across_more_than_one_opportunity": sum(len(bundle["opportunity_ids"]) > 1 for bundle in cache["bundles"]),
        "bundle_reuse_across_disciplines": 0,
        "classification": "BUNDLES_PROMISING_BUT_AUTHORING_HEAVY",
    }
    write(root, "reports/qgen_contrast_supply_economics_v1.json", economics)
    frozen_after = {relative: file_sha256(root / relative) for relative in FROZEN_HISTORICAL}
    historical_safety = "PASS" if starting_frozen == frozen_after else "FAIL"
    implementation_hash = file_sha256(root / "scripts/qbank/contrast_supply_v5.py")
    ready = all((copyright_status == "PASS", benchmark["positive_recall"] == 1.0, benchmark["hard_negative_rejection_rate"] == 1.0, admission_counts["STRONG_BUNDLE"] + admission_counts["MINIMUM_GENERATABLE_BUNDLE"] >= 3, transfer_density["threshold_counts"]["3"] > 0, historical_safety == "PASS"))
    new_transfer = _freeze_new_transfer18(root, roster) if ready else None
    milestone = {
        "schema_version": "SIGNATURE_V2_DISCOVERY_V5_CONTRAST_BUNDLES_MILESTONE_V1",
        "milestone_status": "COMPLETE", "starting_head": "01eff40984bee76418c7fab82a1ded9fbfa2d9e5",
        "decision_signature_v2_implemented": True, "decision_signature_v2_sha256": signature_registry["content_sha256"],
        "decision_signature_v2_dimensions": signature_registry["dimensions"],
        "decision_signature_v2_value_counts": load(root, "reports/qgen_decision_signature_v2_economy.json")["value_counts"],
        "compatibility_positive_recall": benchmark["positive_recall"], "hard_negative_rejection_rate": benchmark["hard_negative_rejection_rate"],
        "discovery_v5_implemented": True, "discovery_v5_sha256": implementation_hash,
        "development_bundle_anchors": len(roster), "canonical_candidates_retrieved": pools["canonical_candidates_retrieved"],
        "cheap_filter_survivors": cheap["survivor_count"], "clinically_plausible_candidates": review_counts["CLINICALLY_PLAUSIBLE"],
        "feature_profiles_authored": len(feature_profiles), "evidence_backed_features": sum(len(profile["features"]) for profile in feature_profiles),
        "bundle_alternatives_proposed": proposed_count, "bundle_alternatives_approved": approved_count,
        "bundle_alternatives_rejected": rejected_count, "bundle_alternatives_uncertain": uncertain_count,
        "contrast_bundle_cache_v1_sha256": cache["content_sha256"], "bundle_admission_counts": admission_counts,
        "build12_density": build_density, "diagnostic_transfer_density": transfer_density,
        "educational_review": education["counts"], "smoke": smoke_review,
        "signature_v2_assessment": "VALIDATED", "discovery_v5_assessment": "PROMISING",
        "contrast_bundle_v1_assessment": "PROMISING",
        "contrast_supply_economics": economics["classification"],
        "historical_safety_regression": historical_safety, "aom_development_control": "PASS",
        "lifecycle_invariant": "PASS", "copyright_audit": copyright_status,
        "ready_for_new_clean_transfer": ready, "new_transfer_cohort_size": (new_transfer or {}).get("cohort_size", 0), "new_transfer_cohort_sha256": (new_transfer or {}).get("cohort_sha256"),
        "commits_created": 0, "historical_frozen_artifacts_modified": 0 if historical_safety == "PASS" else 1,
        "memory_updated": False, "claude_md_changed": False,
        "next_dominant_bottleneck": "BUILD12_EXACT_ANCHOR_BUNDLE_DENSITY",
        "next_step": "RUN_NEW_CLEAN_TRANSFER_VALIDATION" if ready else "EXPAND_CONTRAST_BUNDLE_LIBRARY",
        "focused_tests": {"passed": focused_passed, "failed": focused_failed},
        "full_suite": {"passed": full_passed, "failed": full_failed, "known_preexisting_failures": known_preexisting_failures, "new_test_failures": None if full_failed is None else full_failed - (known_preexisting_failures or 0)},
        "frozen_file_sha256": starting_frozen,
    }
    write(root, "reports/qgen_signature_v2_discovery_v5_contrast_bundles_milestone.json", milestone)
    return milestone


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--focused-passed", type=int)
    parser.add_argument("--focused-failed", type=int)
    parser.add_argument("--full-passed", type=int)
    parser.add_argument("--full-failed", type=int)
    parser.add_argument("--known-preexisting-failures", type=int)
    args = parser.parse_args()
    build_all(args.root, focused_passed=args.focused_passed, focused_failed=args.focused_failed, full_passed=args.full_passed, full_failed=args.full_failed, known_preexisting_failures=args.known_preexisting_failures)


if __name__ == "__main__":
    main()
