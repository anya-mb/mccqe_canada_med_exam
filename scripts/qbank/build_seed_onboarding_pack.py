"""Build reviewed development seed-pack artifacts deterministically."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from .clinical_contrast_v2 import build_contrast_relation, content_sha256
from .schema import validate_instance
from .seed_pack_onboarding import validate_onboarding_pack


PACK_ID = "qgen_development_seed_pack_v6"
APPROVED = (
    "SP-V6-AOM-OME", "SP-V6-AOM-MYRINGITIS", "SP-V6-AOM-ETD", "SP-V6-AOM-OE",
)


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _relation(proposal: dict[str, Any], anchor: str) -> dict[str, Any]:
    anchor_role = (
        "POSITIVE_SUPPORT"
        if anchor == "SF-ONB2-P099-REDUCED-TM-MOBILITY"
        else "SHARED_PRESENTATION_FEATURE"
    )
    candidate_condition = {
        "operator": "ALL_OF",
        "conditions": [{
            "feature_id": "SF-ONB2-P099-BULGING-TM", "required_state": "ABSENT"
        }],
        "prose_basis": (
            "Conservative boundary for this decision-scoped seed: it is never admitted "
            "when the frozen AOM discriminator is present."
        ),
    }
    key_condition = {
        "operator": "ALL_OF",
        "conditions": [{
            "feature_id": "SF-ONB2-P099-BULGING-TM", "required_state": "PRESENT"
        }],
        "prose_basis": "The reviewed evidence identifies a bulging membrane as the acute inflammatory discriminator.",
    }
    return build_contrast_relation(
        learner_decision_id="LD-ONB2-PED-AOM-DX",
        response_class="LOCALIZED_INFLAMMATION",
        decision_granularity="DIAGNOSIS",
        concept_a={
            "concept": proposal["candidate"],
            "concept_category": "LOCALIZED_EAR_DIAGNOSIS",
            "concept_id": proposal["candidate_concept_id"],
            "member_id": proposal["seed_id"],
            "role_in_set": "COMPETITOR",
            "seed_id": proposal["seed_id"],
        },
        concept_b={
            "concept": "Acute otitis media",
            "concept_category": "LOCALIZED_EAR_DIAGNOSIS",
            "concept_id": "CONCEPT-V6-ACUTE-OTITIS-MEDIA",
            "member_id": "KEY-LD-ONB2-PED-AOM-DX",
            "role_in_set": "KEY",
            "seed_id": None,
        },
        shared_features=[{
            "feature_id": anchor,
            "clinical_role": anchor_role,
            "contrast_role": anchor_role,
        }],
        a_supporting_features=[{
            "feature_id": anchor,
            "clinical_role": anchor_role,
            "contrast_role": anchor_role,
        }],
        b_supporting_features=[{
            "feature_id": "SF-ONB2-P099-BULGING-TM",
            "clinical_role": "POSITIVE_SUPPORT",
            "contrast_role": "POSITIVE_SUPPORT",
        }],
        discriminators=[{
            "feature_id": "SF-ONB2-P099-BULGING-TM",
            "favours": "B",
            "required_state": "PRESENT",
            "contrast_role": "POSITIVE_SUPPORT",
            "salience": "SALIENT",
            "evidence_refs": ["CLM-ONB2-AOM-SIGNS", "CLM-V6-AOM-CORE"],
        }],
        correctness_conditions_a=candidate_condition,
        correctness_conditions_b=key_condition,
        second_key_conditions=[candidate_condition],
        categorical_exclusion_conditions=[],
        nesting_relation="NONE",
        confusability="HIGH",
        mcc_relevance="Frozen CORE learner decision LD-ONB2-PED-AOM-DX for MCC objective 28.",
        evidence_refs=list(proposal["evidence_refs"]),
        verification_status="EVIDENCE_VERIFIED",
        opportunity_label="LD-ONB2-PED-AOM-DX",
        anchor_study_unit_id="SU-P-099",
        discovery_sources=["CURRENT_CANADIAN_AUTHORITATIVE_GUIDANCE"],
    )


def build_artifacts(root: Path) -> dict[str, dict[str, Any]]:
    base = root / "research/qgen/onboarding"
    paths = {
        "selection": base / "v6_development_12_selection.json",
        "candidates": base / "v6_development_seed_candidates.json",
        "review": base / "v6_development_seed_independent_review.json",
        "evidence": base / "v6_targeted_authoritative_evidence.json",
    }
    candidates = _read(paths["candidates"])
    review_document = _read(paths["review"])
    proposals = {
        proposal["proposal_id"]: proposal
        for opportunity in candidates["opportunities"]
        for proposal in opportunity["proposals"]
    }
    reviews = {row["proposal_id"]: row for row in review_document["reviews"]}
    seeds: list[dict[str, Any]] = []
    tags: list[dict[str, Any]] = []
    anchor_rows: list[dict[str, Any]] = []
    relations: list[dict[str, Any]] = []
    for proposal_id in APPROVED:
        proposal = proposals[proposal_id]
        reviewed = reviews[proposal_id]
        if reviewed["verdict"] != "APPROVED":
            raise ValueError(f"{proposal_id} is not independently approved")
        anchor = (
            "SF-ONB2-P099-REDUCED-TM-MOBILITY"
            if proposal_id == "SP-V6-AOM-OME"
            else "SF-ONB2-P099-ACUTE-OTALGIA"
        )
        relation = _relation(proposal, anchor)
        relations.append(relation)
        anchor_id = "AR-" + content_sha256({
            "seed_id": proposal["seed_id"], "feature_id": anchor,
            "scope": "LD-ONB2-PED-AOM-DX", "review": reviewed,
        })[:16]
        review = {
            "reviewer_id": review_document["reviewer_id"],
            "verdict": "APPROVED",
            "review_sha256": content_sha256(reviewed),
            "learner_decision_compatibility": reviewed["learner_decision_compatibility"],
            "response_class_compatibility": reviewed["response_class_compatibility"],
            "granularity_compatibility": reviewed["granularity_compatibility"],
            "positive_plausibility_support": reviewed["positive_plausibility_support"],
            "inferior_to_key": reviewed["inferior_to_key"],
            "anchor_positive_for_candidate": reviewed["anchor_positive_for_candidate"],
            "second_key_safety": reviewed["second_key_safety"],
            "scope_safety": reviewed["scope_safety"],
            "reviewed_strength": "STRONG",
            "comment": reviewed["rationale"],
        }
        seed = {
            "seed_id": proposal["seed_id"],
            "competitor_concept_id": proposal["candidate_concept_id"],
            "competitor_concept": proposal["candidate"],
            "preferred_label": proposal["candidate"],
            "competitor_study_unit_id": "SU-P-099",
            "discipline": "PEDIATRICS",
            "learner_decision_id": "LD-ONB2-PED-AOM-DX",
            "response_class": "LOCALIZED_INFLAMMATION",
            "competitor_semantic_category": "LOCALIZED_EAR_DIAGNOSIS",
            "competitor_decision_granularity": "DIAGNOSIS",
            "option_set_archetype": "DIAGNOSIS_SET",
            "candidate_classification": proposal["candidate_classification"],
            "relation_ids": [relation["contrast_relation_id"]],
            "anchor_relation_ids": [anchor_id],
            "why_plausible_for_this_decision": proposal["proposed_anchor"],
            "conditions_under_which_competitor_would_be_correct": (
                "Only after the AOM-defining bulging inflammatory membrane is explicitly absent and the candidate's own findings are established."
            ),
            "shared_features_with_key": [anchor],
            "candidate_visible_discriminators": ["SF-ONB2-P099-BULGING-TM=PRESENT"],
            "why_a_partially_knowledgeable_candidate_might_choose_it": (
                "It explains the shared ear symptom or effusion but not decisive inflammatory otoscopy."
            ),
            "evidence_refs_for_plausibility": list(proposal["evidence_refs"]),
            "evidence_refs_for_discrimination": list(proposal["evidence_refs"]),
            "evidence_refs": list(proposal["evidence_refs"]),
            "requires_terminal_exclusion_clue": False,
            "strength": "STRONG",
            "onboarding_status": "APPROVED",
            "author_provenance": {
                "author_id": "root-seed-onboarding-author-2026-09-07",
                "proposal_id": proposal_id,
                "candidate_input_sha256": content_sha256(proposal),
            },
            "independent_seed_review": review,
            "retrieval_scope": {
                "scope_type": "STUDY_UNIT",
                "study_unit_ids": ["SU-P-099"],
                "learner_decision_ids": ["LD-ONB2-PED-AOM-DX"],
            },
        }
        seeds.append(seed)
        tags.append({
            "seed_id": seed["seed_id"],
            "applicable_disciplines": ["PEDIATRICS"],
            "applicable_item_archetypes": ["DIAGNOSIS"],
            "option_set_archetypes": ["DIAGNOSIS_SET"],
            "response_class_tokens": ["LOCALIZED_INFLAMMATION"],
            "nominal_axis_values": {"organ_system": "EAR_NOSE_THROAT"},
            "condition_predicates": [{
                "stem_feature_id": "SF-ONB2-P099-BULGING-TM",
                "required_polarity": "ABSENT",
            }],
        })
        anchor_rows.append({
            "seed_id": seed["seed_id"],
            "target_id": "LD-ONB2-PED-AOM-DX",
            "anchor_study_unit_id": "SU-P-099",
            "plausibility_anchors": [{
                "stem_feature_id": anchor,
                "anchor_relation_id": anchor_id,
                "derivation": proposal["proposed_anchor"],
                "rule": "INDEPENDENTLY_REVIEWED_POSITIVE_CANDIDATE_ANCHOR",
            }],
            "no_anchor_finding": None,
        })

    pack = {
        "schema_version": "2.0",
        "scope": "GENERALIZED_COMPETITIVE_CONTRAST_SEED_PACK",
        "pack_id": PACK_ID,
        "pack_version": "1.0.0",
        "parent_pack_id": None,
        "creation_scope": "DEVELOPMENT_REGRESSION_SET",
        "opportunity_scope": ["LD-ONB2-PED-AOM-DX"],
        "study_unit_scope": ["SU-P-099"],
        "input_hashes": {
            "development_12": _sha(paths["selection"]),
            "candidate_discovery": _sha(paths["candidates"]),
            "targeted_evidence": _sha(paths["evidence"]),
        },
        "review_hashes": {"independent_seed_review": _sha(paths["review"])},
        "frozen": True,
        "targets": [{
            "target_id": "LD-ONB2-PED-AOM-DX",
            "discipline": "PEDIATRICS",
            "anchor_study_unit_id": "SU-P-099",
            "learner_decision_id": "LD-ONB2-PED-AOM-DX",
            "seeds": seeds,
        }],
    }
    pack["content_sha256"] = content_sha256(pack)
    enrichment = {
        "schema_version": "1.0", "scope": "QGEN_SEED_ENRICHMENT",
        "enrichment_id": f"{PACK_ID}_enrichment", "enriches_pack_id": PACK_ID,
        "frozen": True, "seeds": tags,
    }
    enrichment["frozen_sha256"] = content_sha256(enrichment)
    anchors = {
        "schema_version": "1.0", "scope": "QGEN_SEED_STEM_ANCHORS",
        "anchors_pack_id": f"{PACK_ID}_stem_anchors", "anchors_for_pack_id": PACK_ID,
        "frozen": True, "seeds": anchor_rows,
    }
    anchors["frozen_sha256"] = content_sha256(anchors)
    relation_set = {
        "schema_version": "2.0", "scope": "CLINICAL_CONTRAST_RELATIONS_V2",
        "relation_set_id": f"{PACK_ID}_relations",
        "derived_from": "research/qgen/onboarding/v6_development_seed_candidates.json",
        "decision_domain": "PATIENT_CLINICAL", "frozen": True,
        "relations": relations,
    }
    relation_set["content_sha256"] = content_sha256(relation_set)
    validate_onboarding_pack(pack)
    validate_instance(root, "generalized-competitive-contrast-seed-pack", pack)
    return {"pack": pack, "enrichment": enrichment, "stem_anchors": anchors, "relations": relation_set}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    root = args.root.resolve()
    artifacts = build_artifacts(root)
    base = root / "research/qgen/onboarding/v6_development_seed_pack"
    outputs = {
        base.with_suffix(".json"): artifacts["pack"],
        base.with_suffix(".enrichment.json"): artifacts["enrichment"],
        base.with_suffix(".stem_anchors.json"): artifacts["stem_anchors"],
        root / "research/qgen/onboarding/v6_clinical_contrast_relations_v2.json": artifacts["relations"],
    }
    for path, document in outputs.items():
        path.write_text(json.dumps(document, indent=2, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
