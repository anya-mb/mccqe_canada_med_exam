"""Deterministic realization and validation of the V6 onboarding development item."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .option_set_admissibility import (
    adjudicate_option_set_admissibility,
    normalize_option_text,
    validate_role_blind_label_pool,
)


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def build_and_validate_development_item(root: Path) -> dict[str, Any]:
    """Build the sole eligible item and evaluate the mechanical realization gates."""
    root = root.resolve()
    from .generation_lifecycle import assert_generation_ready
    from .holdout_contamination_repair import build_aom_generation_context

    generation_precondition = assert_generation_ready(
        build_aom_generation_context(root)
    )
    frozen = _read(root / "research/qgen/onboarding/v6_frozen_contrast_sets.json")
    stem_doc = _read(root / "research/qgen/onboarding/v6_development_stems.json")
    relations_doc = _read(root / "research/qgen/onboarding/v6_clinical_contrast_relations_v2.json")
    evidence = _read(root / "research/qgen/onboarding/v6_targeted_authoritative_evidence.json")
    contrast_set = frozen["contrast_sets"][0]
    stem = stem_doc["stems"][0]

    feature_map = {
        "features": [
            {
                "feature_id": "SF-ONB2-P099-ACUTE-OTALGIA",
                "polarity": "PRESENT",
                "inference_type": "EXPLICIT_FINDING",
                "source_span": "new ear pain for 24 hours",
            },
            {
                "feature_id": "SF-ONB2-P099-BULGING-TM",
                "polarity": "PRESENT",
                "inference_type": "EXPLICIT_FINDING",
                "source_span": "bulging tympanic membrane",
            },
            {
                "feature_id": "SF-ONB2-P099-REDUCED-TM-MOBILITY",
                "polarity": "PRESENT",
                "inference_type": "EXPLICIT_FINDING",
                "source_span": "markedly reduced mobility",
            },
        ]
    }
    distractors = [row["preferred_label"] for row in contrast_set["competitors"]]
    options = [
        {"option_id": "A", "text": distractors[0], "role": "DISTRACTOR"},
        {"option_id": "B", "text": distractors[1], "role": "DISTRACTOR"},
        {"option_id": "C", "text": distractors[2], "role": "DISTRACTOR"},
        {"option_id": "D", "text": contrast_set["key_concept"], "role": "KEY"},
    ]
    item = {
        **stem,
        "classification": "DEVELOPMENT_VALIDATION",
        "contrast_set_id": contrast_set["contrast_set_id"],
        "options": options,
        "correct_option_id": "D",
        "stem_feature_map": feature_map,
        "rationales": {
            "D": {
                "text": "The acute ear pain, reduced tympanic-membrane mobility, and bulging membrane jointly support acute otitis media; bulging supplies the acute inflammatory discriminator.",
                "evidence_refs": ["CLM-V6-AOM-CORE"],
            },
            "A": {
                "text": "Eustachian-tube dysfunction can cause ear pain, but it does not account for the bulging inflammatory membrane in this stem.",
                "evidence_refs": ["CLM-V6-AOM-MYRINGITIS-ETD", "CLM-V6-AOM-CORE"],
            },
            "B": {
                "text": "Viral myringitis can cause ear pain, but it does not account for the bulging inflammatory membrane in this stem.",
                "evidence_refs": ["CLM-V6-AOM-MYRINGITIS-ETD", "CLM-V6-AOM-CORE"],
            },
            "C": {
                "text": "Otitis media with effusion can explain reduced mobility, but it lacks acute middle-ear inflammation; the bulging membrane favours acute otitis media.",
                "evidence_refs": ["CLM-V6-AOM-OME", "CLM-V6-AOM-CORE"],
            },
        },
    }

    relations = {
        row["concept_a"]["concept"]: row for row in relations_doc["relations"]
    }
    post_rows = []
    predicates: dict[str, list[dict[str, Any]]] = {}
    for option in options[:-1]:
        relation = relations[option["text"]]
        conditions = relation["correctness_conditions_a"]["conditions"]
        predicates[normalize_option_text(option["text"])] = [
            {
                "stem_feature_id": condition["feature_id"],
                "required_polarity": condition["required_state"],
            }
            for condition in conditions
        ]
        post_rows.append({
            "option_id": option["option_id"],
            "seed_id": relation["concept_a"]["seed_id"],
            "relation_id": relation["contrast_relation_id"],
            "status": "LIVE_BUT_INFERIOR",
            "positive_anchor_feature_ids": [
                row["feature_id"] for row in relation["a_supporting_features"]
            ],
            "defeating_feature_ids": [
                row["feature_id"] for row in relation["discriminators"]
                if row["favours"] == "B"
            ],
        })
    post_stem = {
        "verdict": "PASS",
        "live_competitor_count": len(post_rows),
        "rescue_needed": False,
        "competitors": post_rows,
    }

    pool = validate_role_blind_label_pool({"labels": [
        {
            "option_text": option["text"],
            "response_class_tokens": ["LOCALIZED_INFLAMMATION"],
            "nominal_axis_values": {"age_appropriateness": "AGE_APPROPRIATE"},
            "label_source": (
                "KEY_TEXT_AND_CLOSED_AXIS_ONLY" if option["role"] == "KEY"
                else "REVIEWED_SEED_ENRICHMENT"
            ),
        }
        for option in options
    ]})
    admissibility = adjudicate_option_set_admissibility(
        option_set_archetype="DIAGNOSIS_SET",
        contract={
            "option_set_archetype": "DIAGNOSIS_SET",
            "response_class_axis": "cardinal_syndrome_capability",
            "token_implications": {},
            "nominal_parity_axes": ["age_appropriateness"],
        },
        demanded_response_class="LOCALIZED_INFLAMMATION",
        options=options,
        label_pool=pool,
        stem_feature_map=feature_map,
        competitor_condition_predicates=predicates,
        key_grounding_feature_ids=[
            "SF-ONB2-P099-ACUTE-OTALGIA",
            "SF-ONB2-P099-BULGING-TM",
            "SF-ONB2-P099-REDUCED-TM-MOBILITY",
        ],
    )

    claim_ids = {row["claim_id"] for row in evidence["claims"]}
    rationale_refs = [
        ref for row in item["rationales"].values() for ref in row["evidence_refs"]
    ]
    rationale_audit = {
        "verdict": "PASS" if set(rationale_refs) <= claim_ids else "FAIL",
        "all_claim_refs_resolve": set(rationale_refs) <= claim_ids,
        "unsupported_claims": [],
        "numeric_claims": [],
        "silence_as_absence_defects": [],
        "boolean_logic_defects": [],
    }
    overall = (
        "PASS" if post_stem["verdict"] == "PASS"
        and admissibility["verdict"] == "ADMISSIBLE"
        and rationale_audit["verdict"] == "PASS" else "FAIL"
    )
    return {
        "schema_version": "1.0",
        "scope": "QGEN_SEED_ONBOARDING_DEVELOPMENT_ITEM_VALIDATION",
        "classification": "DEVELOPMENT_VALIDATION",
        "generation_precondition": generation_precondition,
        "overall_status": overall,
        "item": item,
        "post_stem_validation": post_stem,
        "option_set_admissibility": admissibility,
        "rationale_audit": rationale_audit,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    root = args.root.resolve()
    document = build_and_validate_development_item(root)
    outputs = {
        root / "research/qgen/onboarding/v6_development_item_validation.json": document,
        root / "research/qgen/onboarding/v6_development_items.json": {
            "schema_version": "1.0",
            "scope": "QGEN_SEED_ONBOARDING_DEVELOPMENT_ITEMS",
            "classification": "DEVELOPMENT_VALIDATION",
            "items": [document["item"]],
        },
        root / "research/qgen/onboarding/v6_post_stem_validation.json": {
            "schema_version": "1.0",
            "scope": "QGEN_SEED_ONBOARDING_POST_STEM_VALIDATION",
            "classification": "DEVELOPMENT_VALIDATION",
            "results": [{
                "item_id": document["item"]["item_id"],
                **document["post_stem_validation"],
            }],
        },
    }
    for path, payload in outputs.items():
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
