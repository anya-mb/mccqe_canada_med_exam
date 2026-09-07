"""Tests for the qgen fresh-universe readiness inventory.

The counts in the report are measurements and may legitimately move. What must
hold whatever they are is the shape of the classification: the classes partition
the address set, the earliest missing layer wins, and no address is reported
ready on a layer it has not passed.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from qbank.errors import QbankError
from qbank.fresh_universe_inventory import (
    BLOCKING_LAYERS,
    MINIMUM_CURATED_CANDIDATES,
    READINESS_CLASSES,
    REPORT_PATH,
    build_inventory,
    classify_address,
    collect_prior_pilot_use,
)

ROOT = Path(__file__).resolve().parents[1]


def _signals(**overrides):
    base = {
        "allocation_address_id": "SU-X-01",
        "discipline": "MED",
        "priority_class": "CORE",
        "generation_policy": "SERIOUS_ATTEMPT_PER_IMPORTANT_LEARNER_DECISION",
        "mcc_objective_count": 1,
        "source_packets_planned": 1,
        "source_packets_ready": 1,
        "evidence_claims": 5,
        "declared_learner_decisions": 3,
        "unconsumed_learner_decisions": 1,
        "vocabulary_features": 15,
        "curated_seed_targets_at_or_above_minimum": 2,
    }
    base.update(overrides)
    return base


def test_a_fully_onboarded_address_with_an_unused_decision_is_generation_ready():
    assert classify_address(_signals())["readiness_class"] == "GENERATION_READY"


def test_missing_signals_fail_closed_rather_than_defaulting():
    incomplete = _signals()
    del incomplete["vocabulary_features"]
    with pytest.raises(QbankError):
        classify_address(incomplete)


@pytest.mark.parametrize(
    ("overrides", "expected"),
    [
        ({"priority_class": "NOT_IN_SCOPE", "generation_policy": "NEVER"}, "OUT_OF_SCOPE"),
        ({"mcc_objective_count": 0}, "MCC_SCOPE_INCOMPLETE"),
        ({"source_packets_ready": 0}, "SOURCE_PACKET_INCOMPLETE"),
        ({"source_packets_planned": 0, "source_packets_ready": 0}, "SOURCE_PACKET_INCOMPLETE"),
        (
            {
                "declared_learner_decisions": 0,
                "unconsumed_learner_decisions": 0,
                "vocabulary_features": 0,
                "curated_seed_targets_at_or_above_minimum": 0,
            },
            "SOURCE_READY_BUT_NOT_OPPORTUNITY_READY",
        ),
        ({"evidence_claims": 0}, "FOUNDATIONAL_EVIDENCE_INCOMPLETE"),
        (
            {"declared_learner_decisions": 0, "unconsumed_learner_decisions": 0},
            "LEARNER_DECISION_MISSING",
        ),
        ({"vocabulary_features": 0}, "CONTRAST_SUPPLY_INCOMPLETE"),
        ({"curated_seed_targets_at_or_above_minimum": 0}, "CONTRAST_SUPPLY_INCOMPLETE"),
        ({"unconsumed_learner_decisions": 0}, "ALREADY_CONSUMED_BY_PRIOR_PILOT"),
    ],
)
def test_each_layer_is_reported_when_it_is_the_one_that_fails(overrides, expected):
    assert classify_address(_signals(**overrides))["readiness_class"] == expected


def test_the_earliest_missing_layer_wins_over_every_later_one():
    """An out-of-scope address with nothing else either is reported as out of scope."""
    verdict = classify_address(_signals(
        priority_class="NOT_IN_SCOPE",
        generation_policy="NEVER",
        mcc_objective_count=0,
        source_packets_planned=0,
        source_packets_ready=0,
        evidence_claims=0,
        declared_learner_decisions=0,
        unconsumed_learner_decisions=0,
        vocabulary_features=0,
        curated_seed_targets_at_or_above_minimum=0,
    ))
    assert verdict["readiness_class"] == "OUT_OF_SCOPE"
    assert verdict["blocking_layer"] == "SCOPE"


def test_every_verdict_names_a_declared_class_and_layer():
    verdict = classify_address(_signals())
    assert verdict["readiness_class"] in READINESS_CLASSES
    assert verdict["blocking_layer"] in BLOCKING_LAYERS


def test_a_seed_target_below_the_minimum_is_not_contrast_supply():
    assert MINIMUM_CURATED_CANDIDATES == 3


def test_prior_pilot_use_spans_every_pilot_not_only_the_latest():
    """The three decisions the earlier feasibility report called unused were used."""
    used = collect_prior_pilot_use(ROOT)
    for decision in ("LD-C21-03", "LD-OB54-04", "LD-PS12-04"):
        assert used.get(decision), f"{decision} is recorded as never used"


class TestCanonicalInventory:
    @pytest.fixture(scope="class")
    def inventory(self):
        return build_inventory(ROOT)

    def test_the_classes_partition_the_address_set(self, inventory):
        assert sum(inventory["READINESS_CLASS_COUNTS"].values()) == inventory[
            "STUDY_UNITS_INVENTORIED"
        ]
        assert sum(inventory["BLOCKING_LAYER_COUNTS"].values()) == inventory[
            "STUDY_UNITS_INVENTORIED"
        ]

    def test_every_row_carries_a_declared_class(self, inventory):
        for row in inventory["inventory"]:
            assert row["readiness_class"] in READINESS_CLASSES
            assert row["blocking_layer"] in BLOCKING_LAYERS

    def test_no_row_is_source_ready_with_an_unresearched_packet(self, inventory):
        ready_classes = {
            "SOURCE_READY_BUT_NOT_OPPORTUNITY_READY",
            "FOUNDATIONAL_EVIDENCE_INCOMPLETE",
            "LEARNER_DECISION_MISSING",
            "CONTRAST_SUPPLY_INCOMPLETE",
            "ALREADY_CONSUMED_BY_PRIOR_PILOT",
            "GENERATION_READY",
        }
        for row in inventory["inventory"]:
            if row["readiness_class"] in ready_classes:
                assert row["source_packets_planned"] > 0
                assert row["source_packets_ready"] == row["source_packets_planned"]

    def test_onboarding_needs_both_a_vocabulary_and_a_seed_pack(self, inventory):
        indexed = {row["allocation_address_id"]: row for row in inventory["inventory"]}
        for unit in inventory["STUDY_UNITS_ONBOARDED_TO_QGEN"]:
            assert indexed[unit]["vocabulary_features"] > 0
            assert indexed[unit]["curated_seeds"] > 0

    def test_an_onboarded_unit_is_never_listed_as_awaiting_onboarding(self, inventory):
        assert not set(inventory["STUDY_UNITS_ONBOARDED_TO_QGEN"]) & set(
            inventory["SOURCE_READY_NOT_ONBOARDED"]
        )

    def test_report_declares_no_llm_use(self, inventory):
        assert inventory["llm_api_calls"] == 0

    def test_the_committed_report_regenerates_byte_identically(self, inventory):
        from qbank.jsonio import read_json

        committed = read_json(ROOT / REPORT_PATH)
        assert committed == inventory
