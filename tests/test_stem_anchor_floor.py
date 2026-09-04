"""The stem-plausibility-anchor floor on profile-aware contrast retrieval.

G1 and G2 both surfaced COMPETITOR_WITHOUT_STEM_ANCHOR and no gate covered it.
The diagnosis named the cause: anchoring has an anti-second-key ceiling and no
floor, so a stem that keeps its key unique by negating every competitor is
admissible by construction. These tests fix the floor against the frozen
semantic controls in research/qgen/safe_yield/stem_anchor_invariant_controls.json.
"""

import json
from pathlib import Path

import pytest

from qbank.build_stem_anchor_layer import (
    StemAnchorBuildError,
    anchor_document_sha256,
    derive_pack_anchors,
)
from qbank.profile_contrast_retrieval import (
    ContrastRetrievalError,
    build_retrieval_index,
    load_seed_stem_anchors,
    retrieve_profile_aware_contrasts,
)

ROOT = Path(__file__).resolve().parents[1]
GENERALIZATION = ROOT / "research/qgen/generalization"
CONTROLS = json.loads(
    (ROOT / "research/qgen/safe_yield/stem_anchor_invariant_controls.json").read_text()
)
PLAN = json.loads(
    (ROOT / "research/qgen/safe_yield/g2_profile_pilot.wave_plan.json").read_text()
)["plan"]
PACKS = (
    "competitive_contrast_seed_pack_r4",
    "competitive_contrast_seed_pack_g2_targeted",
    "competitive_contrast_seed_pack_g2_extensions",
)


def control(control_id):
    for row in CONTROLS["controls"]:
        if row["control_id"] == control_id:
            return row
    raise AssertionError(f"no such control: {control_id}")


def frozen_anchors():
    """Every seed's frozen anchor feature ids, across the declared packs."""
    resolved = {}
    for pack in PACKS:
        document = json.loads((GENERALIZATION / f"{pack}.stem_anchors.json").read_text())
        for row in document["seeds"]:
            resolved[row["seed_id"]] = {
                anchor["stem_feature_id"] for anchor in row["plausibility_anchors"]
            }
    return resolved


def present_features(opportunity_label):
    for entry in PLAN:
        if entry["opportunity_label"] == opportunity_label:
            return {
                feature["feature_id"]
                for feature in entry["stem_feature_map"]
                if feature["polarity"] == "PRESENT"
            }
    raise AssertionError(f"no plan entry: {opportunity_label}")


def anchored(seed_id, opportunity_label):
    return bool(frozen_anchors()[seed_id] & present_features(opportunity_label))


# --------------------------------------------------------------------------
# Synthetic unit cases over the retrieval function itself.
# --------------------------------------------------------------------------


def seed_row(seed_id, *, predicates, anchors, concept="Some competitor"):
    return {
        "seed_id": seed_id,
        "target_id": "T1",
        "competitor_concept": concept,
        "competitor_concept_id": f"CONCEPT-{seed_id}",
        "competitor_study_unit_id": "SU-X-01",
        "normalized_competitor_text": concept.lower(),
        "conditions_under_which_competitor_would_be_correct": "Correct where it is correct.",
        "condition_predicates": predicates,
        "plausibility_anchor_feature_ids": anchors,
        "response_class_tokens": ["TOKEN"],
        "nominal_axis_values": {},
        "applicable_disciplines": ["MEDICINE"],
        "applicable_item_archetypes": ["DIAGNOSIS"],
        "option_set_archetypes": ["DIAGNOSIS_SET"],
        "decision_granularity": "SINGLE_DIAGNOSIS",
        "shared_features_with_key": ["shared"],
        "reviewed_strength": "STRONG",
    }


def stem(**polarities):
    return {
        "features": [
            {"feature_id": feature_id, "polarity": polarity}
            for feature_id, polarity in polarities.items()
        ]
    }


def retrieve(index, stem_map, ranking=("STEM_ANCHOR_STRENGTH",)):
    return retrieve_profile_aware_contrasts(
        index=index,
        discipline_profile_id="MEDICINE",
        item_archetype="DIAGNOSIS",
        option_set_archetype="DIAGNOSIS_SET",
        demanded_response_class="TOKEN",
        token_implications={},
        generic_token="GENERIC",
        stem_feature_map=stem_map,
        ranking_preference=list(ranking),
    )


def excluded_for(result, seed_id):
    return [row for row in result["excluded"] if row["seed_id"] == seed_id]


def test_zero_support_with_an_explicitly_absent_precondition_is_refused():
    """Control 1: the flagship anchorless mode."""
    index = [
        seed_row(
            "SEED-DISSECTION",
            predicates=[{"stem_feature_id": "F-ONSET", "required_polarity": "PRESENT"}],
            anchors=["F-ONSET", "F-PULSE-DEFICIT"],
        )
    ]
    result = retrieve(index, stem(**{"F-ONSET": "ABSENT", "F-PULSE-DEFICIT": "ABSENT"}))
    assert result["ranked_competitors"] == []
    assert excluded_for(result, "SEED-DISSECTION") == [
        {
            "seed_id": "SEED-DISSECTION",
            "rule": "SAF_1",
            "reason": "STEM_PLAUSIBILITY_ANCHOR_ABSENT",
        }
    ]


def test_zero_support_with_only_shared_topic_membership_is_refused():
    """Control 2: a seed whose prose designates no stem datum carries no anchor."""
    index = [seed_row("SEED-TOPIC-ONLY", predicates=[], anchors=[])]
    result = retrieve(index, stem(**{"F-SOMETHING-ELSE": "PRESENT"}))
    assert result["ranked_competitors"] == []
    assert excluded_for(result, "SEED-TOPIC-ONLY")[0]["reason"] == (
        "STEM_PLAUSIBILITY_ANCHOR_ABSENT"
    )


def test_one_positive_anchor_with_an_inferential_defeat_is_admitted():
    """Control 3: live but inferior."""
    index = [
        seed_row(
            "SEED-LENGTH",
            predicates=[{"stem_feature_id": "F-INDOLENT-MIX", "required_polarity": "PRESENT"}],
            anchors=["F-INDOLENT-MIX", "F-SURVIVAL-LONGER"],
        )
    ]
    result = retrieve(
        index, stem(**{"F-SURVIVAL-LONGER": "PRESENT", "F-INDOLENT-MIX": "ABSENT"})
    )
    assert [row["seed_id"] for row in result["ranked_competitors"]] == ["SEED-LENGTH"]
    assert result["ranked_competitors"][0]["anchors_present"] == 1


def test_several_partial_anchors_with_one_discriminator_are_admitted():
    """Control 4: an anchor may arise from a combination of features."""
    index = [
        seed_row(
            "SEED-MRI",
            predicates=[
                {"stem_feature_id": "F-PREGNANT", "required_polarity": "PRESENT"},
                {"stem_feature_id": "F-PRIOR-IMAGING", "required_polarity": "PRESENT"},
            ],
            anchors=["F-PREGNANT", "F-PRIOR-IMAGING", "F-SUSPICION", "F-IMAGING-AVAILABLE"],
        )
    ]
    result = retrieve(
        index,
        stem(**{
            "F-SUSPICION": "PRESENT",
            "F-IMAGING-AVAILABLE": "PRESENT",
            "F-PREGNANT": "ABSENT",
            "F-PRIOR-IMAGING": "ABSENT",
        }),
    )
    assert result["ranked_competitors"][0]["anchors_present"] == 2


def test_a_fully_satisfied_competitor_is_still_refused_as_a_second_key():
    """Control 5: the ceiling is unchanged and is not subsumed by the floor.

    The competitor clears the anchor floor comfortably. It must still be refused
    by ADM-3, because every condition under which it would be correct holds.
    """
    index = [
        seed_row(
            "SEED-SECOND-KEY",
            predicates=[{"stem_feature_id": "F-CONDITION", "required_polarity": "PRESENT"}],
            anchors=["F-CONDITION"],
        )
    ]
    result = retrieve(index, stem(**{"F-CONDITION": "PRESENT"}))
    assert result["ranked_competitors"] == []
    assert excluded_for(result, "SEED-SECOND-KEY") == [
        {
            "seed_id": "SEED-SECOND-KEY",
            "rule": "ADM_3",
            "reason": "CORRECTNESS_CONDITION_FULLY_SATISFIED",
        }
    ]


def test_a_legitimate_negative_discriminator_does_not_reject_an_anchored_competitor():
    """Control 6: negative findings are not banned.

    The competitor's own precondition is stated absent, exactly as in the
    anchorless mode, and it is admitted anyway because a different PRESENT
    feature still invites it. This is the case a "negative finding = bad" rule
    would get wrong.
    """
    index = [
        seed_row(
            "SEED-OBSERVE",
            predicates=[{"stem_feature_id": "F-PRIOR-IMAGING", "required_polarity": "PRESENT"}],
            anchors=["F-PRIOR-IMAGING", "F-SUSPICION"],
        )
    ]
    result = retrieve(
        index, stem(**{"F-SUSPICION": "PRESENT", "F-PRIOR-IMAGING": "ABSENT"})
    )
    assert [row["seed_id"] for row in result["ranked_competitors"]] == ["SEED-OBSERVE"]


def test_a_terminal_negation_that_only_kills_the_competitor_is_refused():
    """Control 7: every anchor negated and nothing else offered."""
    index = [
        seed_row(
            "SEED-FOREIGN-BODY",
            predicates=[
                {"stem_feature_id": "F-ABRUPT-ONSET", "required_polarity": "PRESENT"},
                {"stem_feature_id": "F-FOCAL", "required_polarity": "PRESENT"},
            ],
            anchors=["F-ABRUPT-ONSET", "F-FOCAL"],
        )
    ]
    result = retrieve(
        index,
        stem(**{"F-ABRUPT-ONSET": "ABSENT", "F-FOCAL": "ABSENT", "F-PRODROME": "PRESENT"}),
    )
    assert result["ranked_competitors"] == []


def test_a_condition_requiring_an_absent_feature_is_not_an_anchor():
    """An absence gives a candidate nothing to reason from.

    Without this the floor would be trivially satisfied by every seed whose
    correctness conditions are written negatively, which is most disposition
    and management seeds.
    """
    index = [
        seed_row(
            "SEED-DISCHARGE",
            predicates=[{"stem_feature_id": "F-TROPONIN", "required_polarity": "ABSENT"}],
            anchors=[],
        )
    ]
    result = retrieve(index, stem(**{"F-TROPONIN": "PRESENT"}))
    assert result["ranked_competitors"] == []


def test_the_anchor_signal_orders_the_ranking():
    """Phase 5: the signal must have useful variance, not be constant."""
    index = [
        seed_row("SEED-ONE", predicates=[], anchors=["F-A"], concept="One"),
        seed_row("SEED-TWO", predicates=[], anchors=["F-A", "F-B"], concept="Two"),
        seed_row("SEED-THREE", predicates=[], anchors=["F-A", "F-B", "F-C"], concept="Three"),
    ]
    result = retrieve(index, stem(**{"F-A": "PRESENT", "F-B": "PRESENT", "F-C": "PRESENT"}))
    assert [row["seed_id"] for row in result["ranked_competitors"]] == [
        "SEED-THREE",
        "SEED-TWO",
        "SEED-ONE",
    ]
    assert result["anchor_signal"] == {
        "zero": 0,
        "positive": 3,
        "fully_satisfied": 3,
        "distinct_values": 3,
    }


def test_retrieval_refuses_an_index_built_without_the_anchor_layer():
    """The floor may not be bypassed by omitting the layer."""
    row = seed_row("SEED-A", predicates=[], anchors=[])
    del row["plausibility_anchor_feature_ids"]
    with pytest.raises(ContrastRetrievalError, match="stem-plausibility anchors"):
        retrieve([row], stem(**{"F-A": "PRESENT"}))


# --------------------------------------------------------------------------
# The frozen anchor layer itself.
# --------------------------------------------------------------------------


def test_the_anchor_layer_is_frozen_and_recomputes():
    """Nothing may edit an anchor row without the declared hash moving."""
    for pack in PACKS:
        document = json.loads((GENERALIZATION / f"{pack}.stem_anchors.json").read_text())
        assert document["frozen"] is True
        assert document["frozen_sha256"] == anchor_document_sha256(document["seeds"])


def test_every_retrievable_seed_carries_an_anchor_row():
    """A seed the enrichment reaches but the anchor layer does not would bypass the floor."""
    for pack in PACKS:
        enrichment = json.loads((GENERALIZATION / f"{pack}.enrichment.json").read_text())
        anchors = json.loads((GENERALIZATION / f"{pack}.stem_anchors.json").read_text())
        assert {row["seed_id"] for row in enrichment["seeds"]} == {
            row["seed_id"] for row in anchors["seeds"]
        }


def test_anchors_are_drawn_only_from_the_canonical_vocabulary():
    vocabulary = json.loads(
        (ROOT / "research/qgen/safe_yield/g2_stem_feature_vocabulary.json").read_text()
    )
    known = {
        anchor["anchor_study_unit_id"]: {
            feature["stem_feature_id"] for feature in anchor["features"]
        }
        for anchor in vocabulary["anchors"]
    }
    for pack in PACKS:
        document = json.loads((GENERALIZATION / f"{pack}.stem_anchors.json").read_text())
        for row in document["seeds"]:
            for entry in row["plausibility_anchors"]:
                assert entry["stem_feature_id"] in known[row["anchor_study_unit_id"]]
                assert entry["rule"] in {"R1", "R2"}
                assert entry["derivation"]


def test_a_required_present_condition_is_always_an_anchor():
    """R1 holds for every seed, so the floor can never be stricter than the ceiling."""
    enrichments = {}
    for pack in PACKS:
        for row in json.loads((GENERALIZATION / f"{pack}.enrichment.json").read_text())["seeds"]:
            enrichments[row["seed_id"]] = row["condition_predicates"]
    anchors = frozen_anchors()
    for seed_id, predicates in enrichments.items():
        required = {
            predicate["stem_feature_id"]
            for predicate in predicates
            if predicate["required_polarity"] == "PRESENT"
        }
        assert required <= anchors[seed_id], seed_id


def test_an_anchor_outside_the_targets_vocabulary_is_refused_at_build_time():
    pack = {
        "targets": [
            {
                "target_id": "T",
                "anchor_study_unit_id": "SU-C-21",
                "seeds": [{"seed_id": "SEED-X"}],
            }
        ]
    }
    enrichment = {"seeds": [{"seed_id": "SEED-X", "condition_predicates": []}]}
    from qbank import build_stem_anchor_layer as builder

    builder.R2_ANCHORS["SEED-X"] = {"SF-P147-HYPOXEMIA": "wrong unit"}
    try:
        with pytest.raises(StemAnchorBuildError, match="canonical vocabulary"):
            derive_pack_anchors(pack, enrichment, {"SU-C-21": {"SF-C21-DIAGNOSTIC-ST-ELEVATION"}})
    finally:
        del builder.R2_ANCHORS["SEED-X"]


# --------------------------------------------------------------------------
# The frozen G2 semantic controls.
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "control_id",
    [
        "CTRL-LIVE-INFERENTIAL-DEFEAT",
        "CTRL-MULTIPLE-PARTIAL-ONE-DISCRIMINATOR",
        "CTRL-LEGITIMATE-NEGATIVE-DISCRIMINATOR",
        "CTRL-MANAGEMENT-INFERIOR-ON-SEVERITY",
        "CTRL-PSY-LONGITUDINAL-PARTIAL-SUPPORT",
        "CTRL-PHELO-CONTEXTUAL",
    ],
)
def test_frozen_live_but_inferior_controls_clear_the_floor(control_id):
    example = control(control_id)["frozen_example"]
    assert anchored(example["seed_id"], example["opportunity_label"]), control_id


@pytest.mark.parametrize(
    "control_id",
    [
        "CTRL-ANCHORLESS-EXPLICIT-DENIAL",
        "CTRL-ANCHORLESS-TOPIC-ONLY",
        "CTRL-TERMINAL-NEGATION",
        "CTRL-GENERIC-CONCEPT-SIMILARITY",
    ],
)
def test_frozen_anchorless_controls_fail_the_floor(control_id):
    example = control(control_id)["frozen_example"]
    assert not anchored(example["seed_id"], example["opportunity_label"]), control_id


def test_accepted_control_sets_keep_three_anchored_competitors():
    """Control 12, measured over the frozen ranked sets."""
    report = json.loads(
        (ROOT / "reports/qgen_g2_profile_aware_retrieval_execution.json").read_text()
    )
    anchors = frozen_anchors()
    ranked = {
        row["wave_label"]: [c["seed_id"] for c in row["retrieval"]["ranked_competitors"]]
        for row in report["results"]
        if row.get("retrieval")
    }
    for label in control("CTRL-ACCEPTED-SETS-PRESERVED")["opportunity_labels"]:
        present = present_features(label)
        survivors = [s for s in ranked[label] if anchors[s] & present]
        assert len(survivors) >= 3, (label, survivors)


def test_known_anchorless_sets_fall_below_three_anchored_competitors():
    """Control 13: the four opportunities the verifiers named cannot realize an item."""
    report = json.loads(
        (ROOT / "reports/qgen_g2_profile_aware_retrieval_execution.json").read_text()
    )
    anchors = frozen_anchors()
    ranked = {
        row["wave_label"]: [c["seed_id"] for c in row["retrieval"]["ranked_competitors"]]
        for row in report["results"]
        if row.get("retrieval")
    }
    for label in control("CTRL-ANCHORLESS-SETS-REJECTED-UPSTREAM")["opportunity_labels"]:
        present = present_features(label)
        survivors = [s for s in ranked[label] if anchors[s] & present]
        assert len(survivors) < 3, (label, survivors)


def test_the_anchor_layer_loads_only_when_frozen(tmp_path):
    document = {"frozen": False, "seeds": []}
    path = tmp_path / "anchors.json"
    path.write_text(json.dumps(document))
    with pytest.raises(ContrastRetrievalError, match="frozen"):
        load_seed_stem_anchors(tmp_path, "anchors.json")


# --------------------------------------------------------------------------
# The controlled retest over the frozen G2 cohort.
# --------------------------------------------------------------------------

RETEST = json.loads(
    (ROOT / "reports/qgen_g2_stem_anchor_retest_execution.json").read_text()
)


def test_the_second_key_ceiling_is_untouched_by_the_floor():
    """The fix is symmetric, not a replacement: ADM-3 fires exactly as often."""
    baseline = json.loads(
        (ROOT / "reports/qgen_g2_profile_aware_retrieval_execution.json").read_text()
    )
    assert (
        RETEST["filter_verdict_counts"]["CORRECTNESS_CONDITION_FULLY_SATISFIED"]
        == baseline["retrieval_provenance"]["filter_verdict_counts"][
            "CORRECTNESS_CONDITION_FULLY_SATISFIED"
        ]
    )


def test_no_known_anchorless_item_is_realized_by_the_corrected_path():
    """The six items the verifiers named for COMPETITOR_WITHOUT_STEM_ANCHOR."""
    realized = {row["wave_label"] for row in RETEST["results"] if row.get("item_id")}
    named = set(RETEST["competitor_without_stem_anchor"]["baseline_items"])
    assert not named & realized


def test_the_anchor_signal_is_no_longer_near_constant():
    signal = RETEST["anchor_signal"]
    assert signal["positive"] > 0
    assert signal["sets_in_which_the_signal_is_constant"] < (
        signal["candidate_sets_with_at_least_one_candidate"] / 2
    )
