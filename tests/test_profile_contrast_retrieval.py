"""Profile-aware retrieval over a curated contrast library."""

import json
from pathlib import Path

import pytest

from qbank.profile_contrast_retrieval import (
    ContrastRetrievalError,
    build_retrieval_index,
    load_seed_enrichment,
    retrieve_profile_aware_contrasts,
)


ROOT = Path(__file__).resolve().parents[1]


def seed(seed_id, concept, granularity="SINGLE_DIAGNOSIS", strength="STRONG", shared=1):
    return {
        "seed_id": seed_id,
        "competitor_concept": concept,
        "competitor_concept_id": f"CONCEPT-{seed_id}",
        "competitor_study_unit_id": "SU-X-01",
        "competitor_decision_granularity": granularity,
        "conditions_under_which_competitor_would_be_correct": "Correct where the finding is absent.",
        "shared_features_with_key": ["shared"] * shared,
        "independent_seed_review": {"reviewed_strength": strength},
    }


def pack():
    return {
        "targets": [
            {
                "target_id": "T1",
                "seeds": [
                    seed("SEED-A", "Alpha entity", shared=1),
                    seed("SEED-B", "Beta entity", shared=3),
                    seed("SEED-C", "Gamma entity", shared=2),
                    seed("SEED-D", "Delta entity", strength="ACCEPTABLE", shared=2),
                    seed("SEED-E", "Epsilon entity", shared=2),
                ],
            }
        ]
    }


def enrichment(tmp_path, overrides=None):
    overrides = overrides or {}
    seeds = []
    for seed_id in ("SEED-A", "SEED-B", "SEED-C", "SEED-D", "SEED-E"):
        row = {
            "seed_id": seed_id,
            "applicable_disciplines": ["MEDICINE"],
            "applicable_item_archetypes": ["DIAGNOSIS"],
            "option_set_archetypes": ["DIAGNOSIS_SET"],
            "response_class_tokens": ["SYSTEMIC_INFLAMMATORY_ILLNESS"],
            "nominal_axis_values": {"organ_system": "BREAST"},
            "condition_predicates": [
                {"stem_feature_id": "F-1", "required_polarity": "ABSENT"}
            ],
        }
        row.update(overrides.get(seed_id, {}))
        seeds.append(row)
    document = {"enrichment_id": "test", "frozen": True, "seeds": seeds}
    path = tmp_path / "enrichment.json"
    path.write_text(json.dumps(document))
    return document, path


def build(tmp_path, overrides=None, anchors=None):
    document, _ = enrichment(tmp_path, overrides)
    resolved = {"enrichment_id": "test", "seeds": {row["seed_id"]: row for row in document["seeds"]}}
    # Every synthetic seed is anchored on the one feature the synthetic stem states
    # PRESENT, so these cases exercise the filters they were written for rather
    # than the stem-anchor floor, which has its own module.
    stem_anchors = {
        "anchors_pack_id": "test",
        "seeds": {row["seed_id"]: list(anchors or ["F-1"]) for row in document["seeds"]},
    }
    return build_retrieval_index(pack(), resolved, stem_anchors)


STEM = {"features": [{"feature_id": "F-1", "polarity": "PRESENT", "inference_type": "EXPLICIT_FINDING"}]}


def retrieve(index, **overrides):
    kwargs = {
        "index": index,
        "discipline_profile_id": "MEDICINE",
        "item_archetype": "DIAGNOSIS",
        "option_set_archetype": "DIAGNOSIS_SET",
        "demanded_response_class": "SYSTEMIC_INFLAMMATORY_ILLNESS",
        "token_implications": {},
        "generic_token": "PLAUSIBLE_DIAGNOSTIC_ENTITY",
        "stem_feature_map": STEM,
        "ranking_preference": [
            "NEAREST_UNSATISFIED_CORRECTNESS_CONDITION",
            "SHARED_FEATURE_COUNT",
            "REVIEWED_SEED_STRENGTH",
        ],
    }
    kwargs.update(overrides)
    return retrieve_profile_aware_contrasts(**kwargs)


def test_enrichment_must_be_frozen_before_use(tmp_path):
    path = tmp_path / "unfrozen.json"
    path.write_text(json.dumps({"enrichment_id": "x", "frozen": False, "seeds": []}))
    with pytest.raises(ContrastRetrievalError, match="frozen"):
        load_seed_enrichment(tmp_path, path.name)


def test_retrieval_is_an_index_lookup_and_not_a_similarity_search(tmp_path):
    index = build(tmp_path)
    result = retrieve(index, item_archetype="INVESTIGATION_SELECTION")
    assert result["indexed_count"] == 0
    assert result["fail_closed_reason"] == "FAIL_CLOSED_INSUFFICIENT_ADMISSIBLE_COMPETITORS"


def test_a_seed_outside_the_demanded_response_class_is_filtered_by_adm_1(tmp_path):
    index = build(tmp_path, {"SEED-A": {"response_class_tokens": ["PALPABLE_MASS_OR_FLUID_COLLECTION"]}})
    result = retrieve(index)
    excluded = {row["seed_id"]: row["rule"] for row in result["excluded"]}
    assert excluded["SEED-A"] == "ADM_1"
    assert "SEED-A" not in {row["seed_id"] for row in result["ranked_competitors"]}


def test_a_competitor_whose_every_condition_the_stem_satisfies_is_a_second_key(tmp_path):
    index = build(
        tmp_path,
        {"SEED-B": {"condition_predicates": [{"stem_feature_id": "F-1", "required_polarity": "PRESENT"}]}},
    )
    result = retrieve(index)
    excluded = {row["seed_id"]: row["reason"] for row in result["excluded"]}
    assert excluded["SEED-B"] == "CORRECTNESS_CONDITION_FULLY_SATISFIED"


def test_seed_strength_is_a_tie_break_and_never_a_gate(tmp_path):
    index = build(tmp_path)
    result = retrieve(index)
    retrieved = {row["seed_id"] for row in result["ranked_competitors"]}
    assert "SEED-D" in retrieved
    ranked = [row["seed_id"] for row in result["ranked_competitors"]]
    # All conditions are equally unsatisfied here, so shared features order the
    # list and the ACCEPTABLE seed still appears among the STRONG ones.
    assert ranked[0] == "SEED-B"


def test_fewer_than_three_survivors_fails_closed(tmp_path):
    index = build(
        tmp_path,
        {
            "SEED-A": {"response_class_tokens": ["PALPABLE_MASS_OR_FLUID_COLLECTION"]},
            "SEED-B": {"response_class_tokens": ["PALPABLE_MASS_OR_FLUID_COLLECTION"]},
            "SEED-C": {"response_class_tokens": ["PALPABLE_MASS_OR_FLUID_COLLECTION"]},
        },
    )
    result = retrieve(index)
    assert result["admissible_count"] == 2
    assert result["fail_closed_reason"] == "FAIL_CLOSED_INSUFFICIENT_ADMISSIBLE_COMPETITORS"


def test_the_curated_seed_pack_itself_is_not_rebuilt():
    """Enrichment is additive; the frozen pack keeps its own hash and fields."""
    document = json.loads(
        (ROOT / "research/qgen/generalization/competitive_contrast_seed_pack_r4.json").read_text()
    )
    assert document["frozen"] is True
    assert len(document["targets"]) == 15
    assert all(
        "conditions_under_which_competitor_would_be_correct" in seed
        for target in document["targets"]
        for seed in target["seeds"]
    )


def test_a_seed_tagged_for_another_discipline_is_not_indexed(tmp_path):
    """The profile binding is a retrieval key, not a preference."""
    index = build(tmp_path, {"SEED-A": {"applicable_disciplines": ["SURGERY"]}})
    result = retrieve(index)
    assert result["indexed_count"] == 4
    assert "SEED-A" not in {row["seed_id"] for row in result["ranked_competitors"]}
    # An index miss is not an admissibility refusal and must not be reported as one.
    assert "SEED-A" not in {row["seed_id"] for row in result["excluded"]}


def test_a_seed_tagged_for_another_option_set_archetype_is_not_indexed(tmp_path):
    """A management competitor cannot be retrieved into a diagnosis set."""
    index = build(tmp_path, {"SEED-B": {"option_set_archetypes": ["MANAGEMENT_SET"]}})
    result = retrieve(index)
    assert result["indexed_count"] == 4
    assert "SEED-B" not in {row["seed_id"] for row in result["ranked_competitors"]}


def test_the_index_does_not_key_on_the_learner_decision(tmp_path):
    """The measured limit of this stage, pinned so it cannot be forgotten.

    A seed curated for one learner decision is retrieved for any other sharing
    the same discipline, item archetype and option-set archetype. Nothing here
    filters it, which is why the semantic-admissibility stage downstream carries
    SA_1 and why the wave refuses to run without it.
    """
    index = build(tmp_path)
    assert all(row["decision_granularity"] == "SINGLE_DIAGNOSIS" for row in index)
    result = retrieve(index)
    assert result["indexed_count"] == 5
    assert result["admissible_count"] == 5
