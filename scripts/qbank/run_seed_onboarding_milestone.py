"""Replay explicit onboarding packs against the frozen development cohort."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .build_seed_onboarding_pack import build_artifacts
from .clinical_contrast_v2 import content_sha256
from .clinical_retrieval import build_current_library_index
from .feature_anchor_registry import SEED_PACK_BASES
from .profile_contrast_retrieval import (
    build_retrieval_index,
    load_seed_enrichment,
    load_seed_stem_anchors,
    retrieve_profile_aware_contrasts,
)


PROFILE_IDS = {
    "MED": "MEDICINE", "PED": "PEDIATRICS", "OBGYN": "OBGYN",
    "SURG": "SURGERY", "PSY": "PSYCHIATRY", "PHELO": "PHELO",
}
ITEM_ARCHETYPES = {
    "DIAGNOSIS_SET": "DIAGNOSIS",
    "INVESTIGATION_SET": "INVESTIGATION_SELECTION",
    "NEXT_ACTION_SET": "TREATMENT_SELECTION",
    "DISPOSITION_SET": "DISPOSITION",
    "MANAGEMENT_STRATEGY_SET": "MANAGEMENT_STRATEGY",
    "LEGAL_ACTION_SET": "ETHICAL_LEGAL_DECISION",
    "STATISTICAL_INTERPRETATION_SET": "EVIDENCE_INTERPRETATION",
}
GENERIC_TOKENS = {
    "DIAGNOSIS_SET": "PLAUSIBLE_DIAGNOSTIC_ENTITY",
    "INVESTIGATION_SET": "DIAGNOSTIC_ADVANCEMENT",
    "NEXT_ACTION_SET": "NEXT_ACTION_FOR_CURRENT_CARE",
    "DISPOSITION_SET": "SAFE_DISPOSITION",
    "MANAGEMENT_STRATEGY_SET": "MANAGEMENT_STRATEGY_FOR_PRESENTATION",
    "LEGAL_ACTION_SET": "TREATING_CLINICIAN_DUTY",
    "STATISTICAL_INTERPRETATION_SET": "EXPLANATION_OF_OBSERVED_PHENOMENON",
}


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def _historical_explicit_index(root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for base in SEED_PACK_BASES:
        rows.extend(
            {**row, "source_pack": f"{base}.json"}
            for row in build_retrieval_index(
                _read(root / f"{base}.json"),
                load_seed_enrichment(root, f"{base}.enrichment.json"),
                load_seed_stem_anchors(root, f"{base}.stem_anchors.json"),
            )
        )
    return sorted(rows, key=lambda row: row["seed_id"])


def _new_index(root: Path) -> list[dict[str, Any]]:
    artifacts = build_artifacts(root)
    enrichment = {row["seed_id"]: row for row in artifacts["enrichment"]["seeds"]}
    anchors = {
        row["seed_id"]: [entry["stem_feature_id"] for entry in row["plausibility_anchors"]]
        for row in artifacts["stem_anchors"]["seeds"]
    }
    return build_retrieval_index(
        {"targets": []}, {"seeds": {}}, {"seeds": {}},
        approved_additional_packs=[{
            "seed_pack": artifacts["pack"],
            "enrichment": {"seeds": enrichment},
            "stem_anchors": {"seeds": anchors},
        }],
    )


def build_replay(
    root: Path, *, opportunity_ids: list[str] | None = None
) -> dict[str, Any]:
    root = root.resolve()
    selection = _read(root / "research/qgen/onboarding/v6_development_12_selection.json")
    manifest = _read(root / "research/qgen/onboarding/v3_fresh36_supply_input_manifest.json")
    feature_maps = _read(root / "research/qgen/onboarding/v2_frozen_pilot_stem_feature_maps.json")
    profile = _read(root / "research/qgen/onboarding/profile_snapshot_v2.json")
    by_id = {row["opportunity_id"]: row for row in manifest["opportunities"]}
    maps = {row["learner_decision_id"]: row for row in feature_maps["opportunities"]}
    selected_ids = (
        list(opportunity_ids)
        if opportunity_ids is not None
        else [row["learner_decision_id"] for row in selection["opportunities"]]
    )

    historical = build_current_library_index(root)
    historical_explicit = _historical_explicit_index(root)
    new = _new_index(root)
    combined = sorted(historical + new, key=lambda row: row["seed_id"])
    opportunities: list[dict[str, Any]] = []
    leakage = 0
    for opportunity_id in selected_ids:
        row = by_id[opportunity_id]
        fmap = maps[opportunity_id]
        archetype = row["option_set_archetype"]
        item_archetype = ITEM_ARCHETYPES[archetype]
        token_implications = profile["option_set_contracts"][archetype].get(
            "token_implications", {}
        )
        result = retrieve_profile_aware_contrasts(
            index=combined,
            discipline_profile_id=PROFILE_IDS[row["discipline"]],
            item_archetype=item_archetype,
            option_set_archetype=archetype,
            demanded_response_class=row["response_class"],
            token_implications=token_implications,
            generic_token=GENERIC_TOKENS[archetype],
            stem_feature_map={
                "features": [
                    {"feature_id": feature["feature_id"], "polarity": feature["state"]}
                    for feature in fmap["features"]
                ]
            },
            ranking_preference=profile["competitor_ranking_preference"],
            learner_decision_id=opportunity_id,
            anchor_study_unit_id=row["study_unit"],
        )
        new_ranked = [
            candidate["seed_id"] for candidate in result["ranked_competitors"]
            if candidate.get("onboarding_pack_id")
        ]
        new_indexed = [
            candidate["seed_id"] for candidate in combined
            if candidate.get("onboarding_pack_id")
            and PROFILE_IDS[row["discipline"]] in candidate["applicable_disciplines"]
            and item_archetype in candidate["applicable_item_archetypes"]
            and archetype in candidate["option_set_archetypes"]
            and opportunity_id in candidate["retrieval_scope"]["learner_decision_ids"]
            and row["study_unit"] in candidate["retrieval_scope"]["study_unit_ids"]
        ]
        if opportunity_id != "LD-ONB2-PED-AOM-DX":
            leakage += len(new_indexed)
        opportunities.append({
            "learner_decision_id": opportunity_id,
            "discipline": row["discipline"],
            "baseline_contrast_ready": row["baseline_contrast_ready"],
            "indexed_count": result["indexed_count"],
            "admissible_count": result["admissible_count"],
            "new_ranked_seed_ids": new_ranked,
            "ranked_seed_ids": [entry["seed_id"] for entry in result["ranked_competitors"]],
            "excluded": result["excluded"],
            "contrast_ready": result["fail_closed_reason"] is None,
            "fail_closed_reason": result["fail_closed_reason"],
        })

    indexed_ids = {row["seed_id"] for row in combined}
    reviewed = _read(root / "research/qgen/onboarding/v6_development_seed_independent_review.json")
    rejected_ids = {
        "SP-V6-D04-LIPOMA": "SEED-V6-D04-LIPOMA",
        "SP-V6-AUD-NALTREXONE": "SEED-V6-AUD-NALTREXONE",
    }
    return {
        "historical_replay_identical": historical_explicit == historical,
        "historical_index_rows": len(historical),
        "additional_approved_index_rows": len(new),
        "approved_seed_retrievable": all(row["seed_id"] in indexed_ids for row in new),
        "rejected_seed_retrievable": any(
            rejected_ids[row["proposal_id"]] in indexed_ids
            for row in reviewed["reviews"] if row["verdict"] == "REJECTED"
        ),
        "uncertain_seed_retrievable": any(
            rejected_ids[row["proposal_id"]] in indexed_ids
            for row in reviewed["reviews"] if row["verdict"] == "UNCERTAIN"
        ),
        "scope_leakage": leakage,
        "development_12_baseline_ready": sum(
            bool(row["baseline_contrast_ready"]) for row in opportunities
        ),
        "development_12_post_seed_ready": sum(row["contrast_ready"] for row in opportunities),
        "opportunities": opportunities,
    }


def build_full_replay(root: Path) -> dict[str, Any]:
    root = root.resolve()
    frozen = _read(root / "research/qgen/onboarding/v2_frozen_pilot_opportunities.json")
    ids = sorted(row["learner_decision_id"] for row in frozen["frozen_opportunities"])
    replay = build_replay(root, opportunity_ids=ids)
    counts = {discipline: 0 for discipline in PROFILE_IDS}
    ready = {discipline: 0 for discipline in PROFILE_IDS}
    for row in replay["opportunities"]:
        counts[row["discipline"]] += 1
        ready[row["discipline"]] += int(row["contrast_ready"])
    replay["development_36_post_seed_ready"] = sum(ready.values())
    replay["ready_by_discipline"] = {
        discipline: f"{ready[discipline]}/{counts[discipline]}"
        for discipline in ("MED", "PED", "OBGYN", "SURG", "PSY", "PHELO")
    }
    return replay


def build_frozen_contrast_set(root: Path) -> dict[str, Any]:
    root = root.resolve()
    replay = build_full_replay(root)
    ready = [row for row in replay["opportunities"] if row["contrast_ready"]]
    if len(ready) != 1:
        raise ValueError(f"expected exactly one ready development opportunity, got {len(ready)}")
    row = ready[0]
    selected_ids = [
        seed_id for seed_id in row["ranked_seed_ids"] if seed_id.startswith("SEED-V6-")
    ][:3]
    artifacts = build_artifacts(root)
    seeds = {
        seed["seed_id"]: seed
        for target in artifacts["pack"]["targets"]
        for seed in target["seeds"]
    }
    document = {
        "schema_version": "1.0",
        "scope": "QGEN_SEED_PACK_ONBOARDING_FROZEN_CONTRAST_SETS",
        "classification": "DEVELOPMENT_VALIDATION",
        "frozen": True,
        "source_replay": "reports/qgen_seed_pack_onboarding_development_36_replay.json",
        "contrast_sets": [{
            "contrast_set_id": "CS-V6-AOM-DX-01",
            "learner_decision_id": row["learner_decision_id"],
            "study_unit_id": "SU-P-099",
            "discipline_profile_id": "PEDIATRICS",
            "item_archetype": "DIAGNOSIS",
            "option_set_archetype": "DIAGNOSIS_SET",
            "demanded_response_class": "LOCALIZED_INFLAMMATION",
            "key_concept": "Acute otitis media",
            "seed_ids": selected_ids,
            "competitors": [{
                "seed_id": seed_id,
                "candidate_concept_id": seeds[seed_id]["competitor_concept_id"],
                "preferred_label": seeds[seed_id]["preferred_label"],
                "relation_ids": seeds[seed_id]["relation_ids"],
                "anchor_relation_ids": seeds[seed_id]["anchor_relation_ids"],
                "evidence_refs": seeds[seed_id]["evidence_refs"],
            } for seed_id in selected_ids],
        }],
    }
    document["content_sha256"] = content_sha256(document)
    return document


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--full", action="store_true")
    parser.add_argument("--contrast-output", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    output = args.output if args.output.is_absolute() else root / args.output
    result = build_full_replay(root) if args.full else build_replay(root)
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    if args.contrast_output:
        contrast_output = (
            args.contrast_output if args.contrast_output.is_absolute()
            else root / args.contrast_output
        )
        contrast_output.write_text(
            json.dumps(build_frozen_contrast_set(root), indent=2, ensure_ascii=False) + "\n"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
