"""Profile-aware contrast retrieval wired into the safe-yield wave.

G1 ran the wave against directly authored option sets: retrieval existed, was unit
tested against synthetic inputs, and was never joined to a real wave. These tests
pin the join. The point of the join is not that retrieval runs but that a
distractor cannot enter an item unless retrieval produced it.
"""

import json
import shutil
from pathlib import Path

import pytest

from qbank.safe_yield_wave import (
    SafeYieldWaveError,
    build_contrast_index,
    competitor_predicates_from_retrieval,
    load_semantic_admissibility,
    select_semantically_admissible,
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
    "semantic_admissibility_relative_path": (
        "research/qgen/safe_yield/g2_profile_pilot.semantic_admissibility.json"
    ),
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
        "provenance_classes": ["ORIGINAL_CURATED", "TARGETED_NEW", "TARGETED_NEW"],
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


# --------------------------------------------------------------------------
# Semantic contrast admissibility inside the production path.
#
# G2 measured retrieval's limit: the index keys on discipline, item archetype
# and option-set archetype and not on the learner decision, so a seed curated
# for one decision is retrieved for another sharing that triple. The judgement
# that removes those was recorded in a frozen artifact and applied by the author
# when selecting distractors, which leaves the production path unable to refuse
# a semantically inadmissible competitor. These tests move the stage into the
# wave: the artifact supplies verdicts, the wave applies them, and the selection
# rule is recomputed rather than trusted.
# --------------------------------------------------------------------------

SEMANTIC = "research/qgen/safe_yield/g2_profile_pilot.semantic_admissibility.json"


def ranked(*rows):
    return [
        {
            "seed_id": seed_id,
            "normalized_competitor_text": seed_id.lower(),
            "competitor_concept": seed_id.title(),
            "condition_predicates": [],
        }
        for seed_id in rows
    ]


def judgement(*verdicts, selected=None):
    judged = [
        {
            "seed_id": seed_id,
            "competitor_concept": seed_id.title(),
            "verdict": verdict,
            "failed_criterion": criterion,
            "note": None,
        }
        for seed_id, verdict, criterion in verdicts
    ]
    record = {"opportunity_label": "X", "judged_competitors": judged}
    if selected is not None:
        record["selected_seed_ids"] = selected
    return record


def test_a_competitor_at_the_wrong_decision_granularity_is_refused():
    """SA-1. The retrieval index cannot see the learner decision; this stage can."""
    result = select_semantically_admissible(
        ranked("A", "B", "C", "D"),
        judgement(
            ("A", "ADMITTED", None),
            ("B", "REFUSED", "SA_1_DECISION_GRANULARITY_MATCH"),
            ("C", "ADMITTED", None),
            ("D", "ADMITTED", None),
        ),
    )
    assert [row["seed_id"] for row in result["selected"]] == ["A", "C", "D"]
    assert result["refused"]["B"] == "SA_1_DECISION_GRANULARITY_MATCH"


def test_a_contextually_implausible_competitor_is_refused():
    """SA-3. Retrievable, in the demanded response class, and still not selectable."""
    result = select_semantically_admissible(
        ranked("A", "B", "C", "D"),
        judgement(
            ("A", "ADMITTED", None),
            ("B", "ADMITTED", None),
            ("C", "REFUSED", "SA_3_CONTEXTUALLY_PLAUSIBLE"),
            ("D", "ADMITTED", None),
        ),
    )
    assert [row["seed_id"] for row in result["selected"]] == ["A", "B", "D"]
    assert result["refused"]["C"] == "SA_3_CONTEXTUALLY_PLAUSIBLE"


def test_fewer_than_three_semantically_admissible_competitors_is_not_forced():
    """The stage may not top the set up from refused competitors to reach three."""
    result = select_semantically_admissible(
        ranked("A", "B", "C"),
        judgement(
            ("A", "ADMITTED", None),
            ("B", "REFUSED", "SA_2_STEM_ANCHOR_PRESENT"),
            ("C", "ADMITTED", None),
        ),
    )
    assert result["sufficient"] is False
    assert [row["seed_id"] for row in result["selected"]] == ["A", "C"]


def test_every_retrieved_competitor_must_be_judged_in_rank_order():
    """Judging a subset would let an unjudged competitor be selected unseen."""
    with pytest.raises(SafeYieldWaveError, match="judged"):
        select_semantically_admissible(
            ranked("A", "B", "C"),
            judgement(("A", "ADMITTED", None), ("B", "ADMITTED", None)),
        )


def test_a_judgement_over_a_competitor_retrieval_never_returned_is_refused():
    with pytest.raises(SafeYieldWaveError, match="judged"):
        select_semantically_admissible(
            ranked("A", "B"),
            judgement(
                ("A", "ADMITTED", None),
                ("B", "ADMITTED", None),
                ("Z", "ADMITTED", None),
            ),
        )


def test_the_selection_rule_is_recomputed_and_never_trusted():
    """A declared selection that is not the first three admitted is a defect."""
    with pytest.raises(SafeYieldWaveError, match="selection"):
        select_semantically_admissible(
            ranked("A", "B", "C", "D"),
            judgement(
                ("A", "ADMITTED", None),
                ("B", "ADMITTED", None),
                ("C", "ADMITTED", None),
                ("D", "ADMITTED", None),
                selected=["B", "C", "D"],
            ),
        )


def test_an_admitted_competitor_may_not_carry_a_failed_criterion():
    with pytest.raises(SafeYieldWaveError, match="criterion"):
        select_semantically_admissible(
            ranked("A"), judgement(("A", "ADMITTED", "SA_1_DECISION_GRANULARITY_MATCH"))
        )


def test_semantic_judgements_must_be_frozen_before_use(tmp_path):
    path = tmp_path / "unfrozen.json"
    path.write_text(json.dumps({"frozen": False, "opportunities": []}))
    with pytest.raises(SafeYieldWaveError, match="frozen"):
        load_semantic_admissibility(tmp_path, path.name)


def test_a_g2_wave_may_not_run_without_its_semantic_judgements():
    """Retrieval alone cannot refuse a competitor curated for another decision."""
    inputs = dict(G2_INPUTS)
    inputs.pop("semantic_admissibility_relative_path")
    with pytest.raises(SafeYieldWaveError, match="semantic"):
        run_safe_yield_wave(ROOT, **inputs)


# --------------------------------------------------------------------------
# Retrieval provenance, and the bypass the provenance makes visible.
# --------------------------------------------------------------------------


def test_retrieval_provenance_is_persisted_for_every_generated_item():
    """Enough to prove a realised distractor came through the retrieval path."""
    result = g2()
    generated = [row for row in result["results"] if row.get("item_id")]
    assert generated
    for row in generated:
        provenance = row["retrieval"]
        query = provenance["query"]
        assert query["discipline_profile_id"] == row["discipline"] or query[
            "discipline_profile_id"
        ]
        for dimension in (
            "item_archetype",
            "option_set_archetype",
            "demanded_response_class",
            "learner_decision_id",
            "ranking_preference",
            "stem_feature_ids",
        ):
            assert query[dimension], dimension
        candidates = provenance["ranked_competitors"]
        assert [row["rank"] for row in candidates] == list(range(1, len(candidates) + 1))
        assert all(row["seed_id"] for row in candidates)
        assert all(
            row["provenance"] in {"ORIGINAL_CURATED", "TARGETED_NEW"} for row in candidates
        )
        assert all(
            row["semantic_verdict"] in {"ADMITTED", "REFUSED"} for row in candidates
        )
        selected = provenance["selected_competitor_seed_ids"]
        assert len(selected) == 3
        assert set(selected).issubset({row["seed_id"] for row in candidates})
        assert provenance["semantically_admissible_count"] >= 3


def test_the_realised_distractors_are_exactly_the_selected_competitors():
    """The join that makes the provenance a proof rather than a note."""
    items = {
        row["opportunity_label"]: row
        for row in json.loads(
            (ROOT / G2_INPUTS["items_relative_path"]).read_text()
        )["items"]
    }
    result = g2()
    for row in result["results"]:
        if not row.get("item_id"):
            continue
        item = items[row["wave_label"]]
        realised = {entry["seed_id"] for entry in item["competitor_provenance"]}
        assert realised == set(row["retrieval"]["selected_competitor_seed_ids"])


def test_a_curated_original_seed_can_be_selected():
    """The 82-seed library is reachable, not merely present."""
    result = g2()
    chosen = set()
    for row in result["results"]:
        if row.get("item_id"):
            chosen.update(
                candidate["seed_id"]
                for candidate in row["retrieval"]["ranked_competitors"]
                if candidate["provenance"] == "ORIGINAL_CURATED"
                and candidate["seed_id"] in row["retrieval"]["selected_competitor_seed_ids"]
            )
    assert chosen


def test_an_independently_approved_targeted_seed_can_be_selected():
    review = json.loads(
        (ROOT / "reports/qgen_g2_targeted_seed_independent_review.json").read_text()
    )
    approved = {row["seed_id"] for row in review["reviews"] if row["verdict"] != "FAIL"}
    result = g2()
    chosen = set()
    for row in result["results"]:
        if row.get("item_id"):
            chosen.update(
                candidate["seed_id"]
                for candidate in row["retrieval"]["ranked_competitors"]
                if candidate["provenance"] == "TARGETED_NEW"
                and candidate["seed_id"] in row["retrieval"]["selected_competitor_seed_ids"]
            )
    assert chosen
    assert chosen.issubset(approved)


def test_a_rejected_targeted_seed_reaches_no_stage_of_the_wave():
    """Seed-review rejection must survive indexing, retrieval and selection."""
    review = json.loads(
        (ROOT / "reports/qgen_g2_targeted_seed_independent_review.json").read_text()
    )
    rejected = {row["seed_id"] for row in review["reviews"] if row["verdict"] == "FAIL"}
    assert rejected
    result = g2()
    seen = set()
    for row in result["results"]:
        retrieval = row.get("retrieval")
        if not retrieval:
            continue
        seen.update(candidate["seed_id"] for candidate in retrieval["ranked_competitors"])
        seen.update(entry["seed_id"] for entry in retrieval["excluded"])
    assert not rejected.intersection(seen)


def test_a_semantic_shortfall_fails_closed_as_one_rather_than_as_a_missing_item():
    """Four of these reported FAIL_CLOSED_UNINSTANTIABLE_REASONING, which is the

    wrong cause: an item was absent because the author had already applied the
    judgement the wave could not.
    """
    result = g2()
    shortfalls = [
        row
        for row in result["results"]
        if row.get("fail_closed_reason")
        == "FAIL_CLOSED_INSUFFICIENT_SEMANTICALLY_ADMISSIBLE_COMPETITORS"
    ]
    assert shortfalls
    for row in shortfalls:
        assert row["state"] == "NO_SAFE_ITEM"
        assert row["reopens_on"] == "NEW_SEEDS_OR_A_PROFILE_VOCABULARY_ENTRY"
        assert row["retrieval"]["semantically_admissible_count"] < 3
        assert not row.get("item_id")


def test_the_semantic_gate_family_is_not_constant_across_the_wave():
    result = g2()
    assert sorted(set(result["gate_verdicts"]["SEMANTIC_CONTRAST_ADMISSIBILITY"])) == [
        "FAIL_CLOSED",
        "SUFFICIENT",
    ]


# --------------------------------------------------------------------------
# A complete option set may not be supplied by hand in G2 mode.
#
# These run the real wave against a copy of the repository with exactly one
# artifact mutated, because the guard is only worth anything if the production
# entry point enforces it.
# --------------------------------------------------------------------------

IGNORED_FROM_THE_COPY = shutil.ignore_patterns(
    ".git", ".venv", "__pycache__", "node_modules", "*.pyc"
)


@pytest.fixture(scope="module")
def repo_copy(tmp_path_factory):
    root = tmp_path_factory.mktemp("repo") / "mccqe"
    shutil.copytree(ROOT, root, ignore=IGNORED_FROM_THE_COPY, symlinks=False)
    return root


def rewrite_items(root, mutate):
    path = root / G2_INPUTS["items_relative_path"]
    document = json.loads(path.read_text())
    mutate(document["items"])
    path.write_text(json.dumps(document, indent=2, sort_keys=True))


def test_the_wave_runs_unchanged_against_an_untouched_copy(repo_copy):
    """The mutation tests are only meaningful if the copy itself is clean."""
    copied = run_safe_yield_wave(repo_copy, **G2_INPUTS)
    here = g2()
    assert [row["wave_label"] for row in copied["results"]] == [
        row["wave_label"] for row in here["results"]
    ]
    for mirrored, original in zip(copied["results"], here["results"]):
        assert mirrored.get("state") == original.get("state")
        assert mirrored.get("fail_closed_reason") == original.get("fail_closed_reason")
        assert mirrored.get("item_id") == original.get("item_id")
        assert mirrored.get("retrieval") == original.get("retrieval")


def test_a_freehand_distractor_cannot_bypass_retrieval(repo_copy, tmp_path_factory):
    """The mode the stage exists to remove: an option nobody retrieved."""
    root = tmp_path_factory.mktemp("freehand") / "mccqe"
    shutil.copytree(repo_copy, root, ignore=IGNORED_FROM_THE_COPY, symlinks=False)

    def mutate(items):
        for item in items:
            for option in item["options"]:
                if option["role"] == "DISTRACTOR":
                    option["text"] = "A competitor nobody retrieved"
                    return
        raise AssertionError("no distractor to mutate")

    rewrite_items(root, mutate)
    with pytest.raises(SafeYieldWaveError, match="not produced by retrieval"):
        run_safe_yield_wave(root, **G2_INPUTS)


def test_a_retrieved_but_semantically_refused_competitor_cannot_be_realised(
    repo_copy, tmp_path_factory
):
    """Retrieval is necessary and not sufficient: the judgement binds too."""
    root = tmp_path_factory.mktemp("refused") / "mccqe"
    shutil.copytree(repo_copy, root, ignore=IGNORED_FROM_THE_COPY, symlinks=False)
    judgements = {
        row["opportunity_label"]: row
        for row in json.loads((root / SEMANTIC).read_text())["opportunities"]
    }
    target = next(
        (label, row)
        for label, row in judgements.items()
        if any(entry["verdict"] == "REFUSED" for entry in row["judged_competitors"])
        and row.get("selected_seed_ids")
    )
    label, judged = target
    refused = next(
        entry for entry in judged["judged_competitors"] if entry["verdict"] == "REFUSED"
    )

    def mutate(items):
        for item in items:
            if item["opportunity_label"] != label:
                continue
            for option in item["options"]:
                if option["role"] == "DISTRACTOR":
                    option["text"] = refused["competitor_concept"]
                    return
        raise AssertionError(f"no realised item for {label}")

    rewrite_items(root, mutate)
    with pytest.raises(SafeYieldWaveError, match="not produced by retrieval"):
        run_safe_yield_wave(root, **G2_INPUTS)


def test_the_committed_execution_report_is_the_production_runs_own_output():
    """The report is evidence only if the production path produced it.

    Every per-opportunity record in the committed report, including its retrieval
    provenance, must be reproducible by running the wave again.
    """
    execution = json.loads(
        (ROOT / "reports/qgen_g2_profile_aware_retrieval_execution.json").read_text()
    )
    fresh = {row["wave_label"]: row for row in g2()["results"]}
    committed = {row["wave_label"]: row for row in execution["results"]}
    assert set(committed) == set(fresh)
    for label, row in committed.items():
        assert row == fresh[label], label
    provenance = execution["retrieval_provenance"]
    assert provenance["retrievals_run"] == sum(
        1 for row in fresh.values() if row.get("retrieval")
    )
    assert provenance["candidate_sets_short_after_semantic_admissibility"] == sum(
        1
        for row in fresh.values()
        if row.get("fail_closed_reason")
        == "FAIL_CLOSED_INSUFFICIENT_SEMANTICALLY_ADMISSIBLE_COMPETITORS"
    )
    assert provenance["selected_seed_counts_by_provenance"]["ORIGINAL_CURATED"] > 0
    assert provenance["selected_seed_counts_by_provenance"]["TARGETED_NEW"] > 0
