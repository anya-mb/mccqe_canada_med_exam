"""Profile-aware contrast retrieval wired into the safe-yield wave.

G1 ran the wave against directly authored option sets: retrieval existed, was unit
tested against synthetic inputs, and was never joined to a real wave. These tests
pin the join. The point of the join is not that retrieval runs but that a
distractor cannot enter an item unless retrieval produced it.
"""

import json
from pathlib import Path

import pytest

from qbank.safe_yield_wave import (
    SafeYieldWaveError,
    build_contrast_index,
    competitor_predicates_from_retrieval,
    unretrieved_distractors,
    run_safe_yield_wave,
)


ROOT = Path(__file__).resolve().parents[1]

G1_INPUTS = {
    "opportunities_relative_path": "research/qgen/safe_yield/g1_micro_pilot.opportunities.json",
    "plan_relative_path": "research/qgen/safe_yield/g1_micro_pilot.wave_plan.json",
    "items_relative_path": "research/qgen/safe_yield/g1_micro_pilot.items.json",
    "labels_relative_path": "research/qgen/safe_yield/g1_role_blind_option_labels.json",
    "assignments_relative_path": "research/qgen/safe_yield/g1_demanded_response_classes.json",
}

CURATED = {
    "seed_packs": ["research/qgen/generalization/competitive_contrast_seed_pack_r4.json"],
    "enrichments": ["research/qgen/generalization/competitive_contrast_seed_pack_r4.enrichment.json"],
}


def test_a_wave_without_a_contrast_library_is_unchanged():
    """The G1 wave predates retrieval and must keep its recorded outcome."""
    result = run_safe_yield_wave(ROOT, **G1_INPUTS)
    assert result["pre_verification_summary"]["attempted_opportunities"] == 11
    assert result["pre_verification_summary"]["opportunity_state_counts"]["CANDIDATE"] == 0
    assert all("retrieval" not in row for row in result["results"])


def test_the_merged_index_spans_every_declared_pack():
    index = build_contrast_index(ROOT, CURATED)
    assert len(index) == 62
    assert len({row["seed_id"] for row in index}) == len(index)
    # A seed the independent seed reviewer rejected is not enriched and so is
    # unreachable: rejection at seed review must survive into retrieval.
    pack = json.loads(
        (ROOT / "research/qgen/generalization/competitive_contrast_seed_pack_r4.json").read_text()
    )
    rejected = {
        seed["seed_id"]
        for target in pack["targets"]
        for seed in target["seeds"]
        if (seed.get("independent_seed_review") or {}).get("reviewed_strength") == "REJECT"
    }
    assert rejected
    assert not rejected.intersection({row["seed_id"] for row in index})


def test_a_declared_pack_without_its_enrichment_is_refused():
    with pytest.raises(SafeYieldWaveError, match="one enrichment"):
        build_contrast_index(ROOT, {"seed_packs": CURATED["seed_packs"], "enrichments": []})


def test_a_distractor_that_retrieval_never_produced_is_refused():
    """The whole point of the join: option sets may not be authored freehand."""
    ranked = [
        {"normalized_competitor_text": "community-acquired pneumonia", "seed_id": "S1"},
        {"normalized_competitor_text": "first presentation of asthma", "seed_id": "S2"},
    ]
    options = [
        {"role": "KEY", "text": "Acute viral bronchiolitis"},
        {"role": "DISTRACTOR", "text": "Community-acquired pneumonia"},
        {"role": "DISTRACTOR", "text": "First presentation of asthma"},
        {"role": "DISTRACTOR", "text": "Congestive heart failure"},
    ]
    assert unretrieved_distractors(options, ranked) == ["Congestive heart failure"]
    assert unretrieved_distractors(options[:3], ranked) == []


def test_the_key_is_never_required_to_have_been_retrieved():
    """Retrieval supplies competitors. A key that appeared in it would be a second key."""
    ranked = [{"normalized_competitor_text": "length-time bias", "seed_id": "S1"}]
    options = [
        {"role": "KEY", "text": "Lead-time bias"},
        {"role": "DISTRACTOR", "text": "Length-time bias"},
    ]
    assert unretrieved_distractors(options, ranked) == []


def test_retrieval_predicates_are_keyed_for_the_admissibility_stage():
    """ADM-3 ran on probes only in G1 because nothing supplied real predicates."""
    ranked = [
        {
            "normalized_competitor_text": "chest radiograph",
            "condition_predicates": [{"stem_feature_id": "SF-X", "required_polarity": "PRESENT"}],
        }
    ]
    resolved = competitor_predicates_from_retrieval(ranked)
    assert resolved == {
        "chest radiograph": [{"stem_feature_id": "SF-X", "required_polarity": "PRESENT"}]
    }


G2_INPUTS = {
    "opportunities_relative_path": "research/qgen/safe_yield/g2_profile_pilot.opportunities.json",
    "plan_relative_path": "research/qgen/safe_yield/g2_profile_pilot.wave_plan.json",
    "items_relative_path": "research/qgen/safe_yield/g2_profile_pilot.items.json",
    "labels_relative_path": "research/qgen/safe_yield/g2_role_blind_option_labels.json",
    "assignments_relative_path": "research/qgen/safe_yield/g2_demanded_response_classes.json",
    "contrast_library": {
        "seed_packs": [
            "research/qgen/generalization/competitive_contrast_seed_pack_r4.json",
            "research/qgen/generalization/competitive_contrast_seed_pack_g2_targeted.json",
            "research/qgen/generalization/competitive_contrast_seed_pack_g2_extensions.json",
        ],
        "enrichments": [
            "research/qgen/generalization/competitive_contrast_seed_pack_r4.enrichment.json",
            "research/qgen/generalization/competitive_contrast_seed_pack_g2_targeted.enrichment.json",
            "research/qgen/generalization/competitive_contrast_seed_pack_g2_extensions.enrichment.json",
        ],
    },
}


def g2():
    return run_safe_yield_wave(ROOT, **G2_INPUTS)


def test_retrieval_precedes_realization_so_a_contrast_shortfall_is_named_as_one():
    """Retrieval decides whether an item could be built, so it must run first.

    Running it after the item lookup made an opportunity with no valid contrast
    set report FAIL_CLOSED_UNINSTANTIABLE_REASONING, which names the wrong cause
    and leaves the retrieval gate with one verdict all wave.
    """
    result = g2()
    rows = {row["wave_label"]: row for row in result["results"]}
    shortfalls = [
        row for row in result["results"]
        if row.get("retrieval") and row["retrieval"]["fail_closed_reason"]
    ]
    assert shortfalls, "no opportunity exercised the contrast shortfall path"
    for row in shortfalls:
        assert row["fail_closed_reason"] == "FAIL_CLOSED_INSUFFICIENT_ADMISSIBLE_COMPETITORS"
        assert row["reopens_on"] == "NEW_SEEDS_OR_A_PROFILE_VOCABULARY_ENTRY"
    # SURG-04's archetype has no seed in any declared pack.
    assert rows["G2-SURG-04"]["retrieval"]["indexed_count"] == 0
    assert rows["G2-SURG-04"]["fail_closed_reason"] == "FAIL_CLOSED_INSUFFICIENT_ADMISSIBLE_COMPETITORS"


def test_the_retrieval_gate_family_is_not_constant_across_the_wave():
    result = g2()
    assert sorted(set(result["gate_verdicts"]["PROFILE_AWARE_CONTRAST_RETRIEVAL"])) == [
        "FAIL_CLOSED", "SUFFICIENT"
    ]


def test_every_realised_distractor_came_from_retrieval():
    result = g2()
    realised = [row for row in result["results"] if row.get("admissibility")]
    assert realised
    for row in realised:
        assert row["retrieval"]["admissible_count"] >= 3


def test_the_recorded_g2_outcome_matches_the_committed_reports():
    execution = json.loads(
        (ROOT / "reports/qgen_g2_profile_aware_retrieval_execution.json").read_text()
    )
    reported = execution["reported"]
    assert reported["attempted_opportunities"] == 30
    assert reported["accepted_safe_yield"] == 4
    assert reported["rejected"] == 13
    assert reported["no_safe_item"] == 12
    assert reported["redundant"] == 1
    assert execution["profile_aware_contrast_retrieval_exercised_end_to_end"] is True
    for invariant, count in execution["defect_counts_in_accepted"].items():
        assert count == 0, invariant
    assert execution["evidence_entailment"] == "PASS"
    assert execution["verdict_variance"]["verdict_variance"] == "PASS"
    assert all(probe["fired"] for probe in execution["admissibility_positive_controls"])


def test_no_profile_reached_provisional_validation_and_that_is_recorded():
    """G2's result is that retrieval works and realization does not yet."""
    execution = json.loads(
        (ROOT / "reports/qgen_g2_profile_aware_retrieval_execution.json").read_text()
    )
    statuses = {
        profile: row["profile_validated_provisionally"]
        for profile, row in execution["by_profile"].items()
    }
    assert len(statuses) == 6
    assert set(statuses.values()) == {"INSUFFICIENT_YIELD"}
    # The four repeated realization defects are the finding, and each names its items.
    defects = execution["repeated_realization_defects"]
    assert "COMPETITOR_WITHOUT_STEM_ANCHOR" in defects
    assert len(defects["COMPETITOR_WITHOUT_STEM_ANCHOR"]["profiles"]) >= 3
    for record in defects.values():
        assert record["items"] and record["diagnosis"]


def test_the_targeted_seed_acquisition_was_independently_reviewed_and_cut_down():
    review = json.loads(
        (ROOT / "reports/qgen_g2_targeted_seed_independent_review.json").read_text()
    )
    assert review["seeds_reviewed"] == 23
    assert review["approved"] == 19
    assert review["rejected"] == 4
    rejected = {row["seed_id"] for row in review["reviews"] if row["verdict"] == "FAIL"}
    # A rejected seed carries no enrichment tags, so retrieval cannot reach it.
    enriched = set()
    for name in ("competitive_contrast_seed_pack_g2_targeted.enrichment.json",
                 "competitive_contrast_seed_pack_g2_extensions.enrichment.json"):
        document = json.loads((ROOT / "research/qgen/generalization" / name).read_text())
        enriched.update(row["seed_id"] for row in document["seeds"])
    assert not rejected.intersection(enriched)


def test_the_curated_pack_and_the_frozen_allocation_were_not_touched():
    pack = json.loads(
        (ROOT / "research/qgen/generalization/competitive_contrast_seed_pack_r4.json").read_text()
    )
    assert pack["pack_id"] == "competitive_contrast_seed_pack_r4"
    assert sum(len(target["seeds"]) for target in pack["targets"]) == 82
    allocation = json.loads((ROOT / "research/scope/final_question_allocation.json").read_text())
    assert allocation["total_target_questions"] == 6086
    assert len(allocation["allocation_addresses"]) == 1507
