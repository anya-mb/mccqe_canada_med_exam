from __future__ import annotations

import pytest

from scripts.qbank.feature_anchor_registry import content_sha256
from scripts.qbank.profile_contrast_retrieval import (
    ContrastRetrievalError,
    build_retrieval_index,
    retrieve_profile_aware_contrasts,
)
from scripts.qbank.schema import validate_instance


ROOT = __import__("pathlib").Path(__file__).resolve().parents[1]


def _seed(seed_id: str, *, status: str = "APPROVED") -> dict:
    return {
        "seed_id": seed_id,
        "competitor_concept_id": f"CONCEPT-{seed_id}",
        "competitor_concept": "Mobile subcutaneous lipoma",
        "preferred_label": "Mobile subcutaneous lipoma",
        "competitor_study_unit_id": "SU-D-04",
        "discipline": "MEDICINE",
        "learner_decision_id": "LD-D04-01",
        "response_class": "PLAUSIBLE_DIAGNOSTIC_ENTITY",
        "option_set_archetype": "DIAGNOSIS_SET",
        "competitor_decision_granularity": "DIAGNOSIS",
        "conditions_under_which_competitor_would_be_correct": "A mobile soft subcutaneous mass.",
        "shared_features_with_key": ["superficial lump"],
        "onboarding_status": status,
        "candidate_classification": "NEAR_MISS_DIAGNOSIS",
        "relation_ids": ["CCR2-TEST-LIPOMA"],
        "anchor_relation_ids": ["AR-TEST-LIPOMA-MOBILE"],
        "evidence_refs": ["SRC-MED-048-REC-01"],
        "author_provenance": {"author_id": "test-author", "authored_on": "2026-09-07"},
        "independent_seed_review": {
            "reviewer_id": "test-independent-reviewer",
            "verdict": status,
            "review_sha256": "a" * 64,
            "learner_decision_compatibility": "PASS",
            "response_class_compatibility": "PASS",
            "granularity_compatibility": "PASS",
            "positive_plausibility_support": "PASS",
            "inferior_to_key": "PASS",
            "anchor_positive_for_candidate": "PASS",
            "second_key_safety": "PASS",
            "scope_safety": "PASS",
        },
        "retrieval_scope": {
            "scope_type": "STUDY_UNIT",
            "study_unit_ids": ["SU-D-04"],
            "learner_decision_ids": ["LD-D04-01"],
        },
    }


def _pack(seed: dict, *, pack_id: str = "development-test-pack") -> dict:
    body = {
        "schema_version": "2.0",
        "scope": "GENERALIZED_COMPETITIVE_CONTRAST_SEED_PACK",
        "pack_id": pack_id,
        "pack_version": "1.0.0",
        "parent_pack_id": None,
        "creation_scope": "DEVELOPMENT_REGRESSION_SET",
        "opportunity_scope": ["LD-D04-01"],
        "study_unit_scope": ["SU-D-04"],
        "input_hashes": {"frozen_opportunities": "b" * 64},
        "review_hashes": {"independent_seed_review": "c" * 64},
        "frozen": True,
        "targets": [{
            "target_id": "LD-D04-01",
            "discipline": "MEDICINE",
            "anchor_study_unit_id": "SU-D-04",
            "learner_decision_id": "LD-D04-01",
            "seeds": [seed],
        }],
    }
    body["content_sha256"] = content_sha256(body)
    return body


def _enrichment(seed_id: str) -> dict:
    return {"seeds": {seed_id: {
        "condition_predicates": [{
            "stem_feature_id": "SF-D04-LIPOMA-CORRECT",
            "required_polarity": "PRESENT",
        }],
        "response_class_tokens": ["PLAUSIBLE_DIAGNOSTIC_ENTITY"],
        "nominal_axis_values": {"organ_system": "DERMATOLOGY"},
        "applicable_disciplines": ["MEDICINE"],
        "applicable_item_archetypes": ["DIAGNOSIS"],
        "option_set_archetypes": ["DIAGNOSIS_SET"],
    }}}


def _anchors(seed_id: str) -> dict:
    return {"seeds": {seed_id: ["SF-D04-MOBILE-MASS"]}}


def _historical_inputs() -> tuple[dict, dict, dict]:
    seed = _seed("SEED-HISTORICAL")
    seed.pop("onboarding_status")
    seed.pop("retrieval_scope")
    seed["independent_seed_review"] = {
        "reviewer_id": "historical-reviewer",
        "verdict": "PASS",
        "reviewed_strength": "STRONG",
    }
    return (
        {"targets": [{"target_id": "HIST", "seeds": [seed]}]},
        _enrichment(seed["seed_id"]),
        _anchors(seed["seed_id"]),
    )


def test_approved_new_seed_pack_is_an_explicit_retrieval_input():
    """Removing additional-pack enumeration must make the new seed unreachable."""
    historical_pack, historical_enrichment, historical_anchors = _historical_inputs()
    new_seed = _seed("SEED-NEW-D04-LIPOMA")

    rows = build_retrieval_index(
        historical_pack,
        historical_enrichment,
        historical_anchors,
        approved_additional_packs=[{
            "seed_pack": _pack(new_seed),
            "enrichment": _enrichment(new_seed["seed_id"]),
            "stem_anchors": _anchors(new_seed["seed_id"]),
        }],
    )

    assert [row["seed_id"] for row in rows] == [
        "SEED-HISTORICAL",
        "SEED-NEW-D04-LIPOMA",
    ]


def test_approved_seed_with_key_only_anchor_is_rejected():
    """Removing the positive-candidate semantic check must admit a backwards anchor."""
    historical_pack, historical_enrichment, historical_anchors = _historical_inputs()
    backwards = _seed("SEED-BACKWARDS")
    backwards["independent_seed_review"]["anchor_positive_for_candidate"] = "FAIL"
    pack = _pack(backwards)
    pack["content_sha256"] = content_sha256(
        {key: value for key, value in pack.items() if key != "content_sha256"}
    )

    with pytest.raises(ContrastRetrievalError, match="positive candidate anchor"):
        build_retrieval_index(
            historical_pack,
            historical_enrichment,
            historical_anchors,
            approved_additional_packs=[{
                "seed_pack": pack,
                "enrichment": _enrichment(backwards["seed_id"]),
                "stem_anchors": _anchors(backwards["seed_id"]),
            }],
        )


def test_additional_seed_scope_cannot_leak_to_another_decision():
    """Removing scope filtering must expose the seed to an unreviewed decision."""
    historical_pack, historical_enrichment, historical_anchors = _historical_inputs()
    new_seed = _seed("SEED-SCOPED-D04")
    rows = build_retrieval_index(
        historical_pack,
        historical_enrichment,
        historical_anchors,
        approved_additional_packs=[{
            "seed_pack": _pack(new_seed),
            "enrichment": _enrichment(new_seed["seed_id"]),
            "stem_anchors": _anchors(new_seed["seed_id"]),
        }],
    )
    additional_rows = [row for row in rows if row.get("onboarding_pack_id")]

    result = retrieve_profile_aware_contrasts(
        index=additional_rows,
        discipline_profile_id="MEDICINE",
        item_archetype="DIAGNOSIS",
        option_set_archetype="DIAGNOSIS_SET",
        demanded_response_class="PLAUSIBLE_DIAGNOSTIC_ENTITY",
        token_implications={},
        generic_token="PLAUSIBLE_DIAGNOSTIC_ENTITY",
        stem_feature_map={"features": [{
            "feature_id": "SF-D04-MOBILE-MASS", "polarity": "PRESENT"
        }]},
        ranking_preference=[],
        learner_decision_id="LD-D05-01",
        anchor_study_unit_id="SU-D-05",
    )

    assert result["indexed_count"] == 0
    assert result["ranked_competitors"] == []


@pytest.mark.parametrize("status", ["REJECTED", "UNCERTAIN"])
def test_nonapproved_additional_seed_never_enters_the_index(status):
    historical_pack, historical_enrichment, historical_anchors = _historical_inputs()
    seed = _seed(f"SEED-{status}", status=status)
    rows = build_retrieval_index(
        historical_pack,
        historical_enrichment,
        historical_anchors,
        approved_additional_packs=[{
            "seed_pack": _pack(seed),
            "enrichment": _enrichment(seed["seed_id"]),
            "stem_anchors": _anchors(seed["seed_id"]),
        }],
    )
    assert [row["seed_id"] for row in rows] == ["SEED-HISTORICAL"]


def test_omitting_additional_packs_preserves_the_historical_index_exactly():
    historical_pack, historical_enrichment, historical_anchors = _historical_inputs()
    before = build_retrieval_index(
        historical_pack, historical_enrichment, historical_anchors
    )
    after = build_retrieval_index(
        historical_pack, historical_enrichment, historical_anchors,
        approved_additional_packs=[],
    )
    assert after == before


def test_new_pack_validates_against_the_versioned_schema():
    validate_instance(
        ROOT,
        "generalized-competitive-contrast-seed-pack",
        _pack(_seed("SEED-SCHEMA")),
    )


def test_new_seed_still_obeys_anchor_floor_and_second_key_ceiling():
    historical_pack, historical_enrichment, historical_anchors = _historical_inputs()
    seed = _seed("SEED-SAFETY")
    rows = build_retrieval_index(
        historical_pack,
        historical_enrichment,
        historical_anchors,
        approved_additional_packs=[{
            "seed_pack": _pack(seed),
            "enrichment": _enrichment(seed["seed_id"]),
            "stem_anchors": _anchors(seed["seed_id"]),
        }],
    )
    additional = [row for row in rows if row["seed_id"] == seed["seed_id"]]
    common = {
        "index": additional,
        "discipline_profile_id": "MEDICINE",
        "item_archetype": "DIAGNOSIS",
        "option_set_archetype": "DIAGNOSIS_SET",
        "demanded_response_class": "PLAUSIBLE_DIAGNOSTIC_ENTITY",
        "token_implications": {},
        "generic_token": "PLAUSIBLE_DIAGNOSTIC_ENTITY",
        "ranking_preference": [],
        "learner_decision_id": "LD-D04-01",
        "anchor_study_unit_id": "SU-D-04",
    }
    floor = retrieve_profile_aware_contrasts(
        **common,
        stem_feature_map={"features": []},
    )
    assert floor["excluded"] == [{
        "seed_id": "SEED-SAFETY",
        "rule": "SAF_1",
        "reason": "STEM_PLAUSIBILITY_ANCHOR_ABSENT",
    }]
    ceiling = retrieve_profile_aware_contrasts(
        **common,
        stem_feature_map={"features": [
            {"feature_id": "SF-D04-MOBILE-MASS", "polarity": "PRESENT"},
            {"feature_id": "SF-D04-LIPOMA-CORRECT", "polarity": "PRESENT"},
        ]},
    )
    assert ceiling["excluded"] == [{
        "seed_id": "SEED-SAFETY",
        "rule": "ADM_3",
        "reason": "CORRECTNESS_CONDITION_FULLY_SATISFIED",
    }]
