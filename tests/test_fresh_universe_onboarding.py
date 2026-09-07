"""Tests for onboarding wave W1 and the fresh-universe gate.

The counts move as research lands. What must not move is that each of the three
checks refuses rather than repairs: an address whose evidence was reviewed
anything but ALIGNED cannot carry a declared decision, a decision the frozen
discipline profile does not admit cannot be restated into one it does, and a
cited reference that no researched packet contains is not evidence.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from qbank.errors import QbankError
from qbank.fresh_universe_onboarding import (
    ALIGNMENT_REVIEW_PATH,
    DECLARED_DECISIONS_PATH,
    FRESH_PILOT_FLOOR,
    GATE_REPORT_PATH,
    OPPORTUNITIES_PATH,
    PROFILE_REFUSALS_PATH,
    build_fresh_opportunities,
    build_gate_report,
    compute_opportunity_id,
    load_profile_archetypes,
    measure_preflight_contrast,
    probe_vocabulary_extension,
    validate_decision_against_profile,
)
from qbank.jsonio import read_json

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def candidates():
    return build_fresh_opportunities(ROOT)


@pytest.fixture(scope="module")
def gate():
    return build_gate_report(ROOT)


class TestProfileConformance:
    def test_a_decision_the_profile_does_not_admit_is_refused(self):
        archetypes = load_profile_archetypes(ROOT, "MEDICINE")
        with pytest.raises(QbankError, match="does not admit"):
            validate_decision_against_profile(
                {
                    "learner_decision_id": "LD-TEST",
                    "item_archetype": "LEGAL_DUTY",
                    "decision_granularity": "LEGAL_DUTY",
                    "option_set_archetype": "LEGAL_ACTION_SET",
                },
                archetypes,
                profile_id="MEDICINE",
            )

    def test_a_granularity_outside_the_archetype_is_refused(self):
        archetypes = load_profile_archetypes(ROOT, "MEDICINE")
        with pytest.raises(QbankError, match="does not permit"):
            validate_decision_against_profile(
                {
                    "learner_decision_id": "LD-TEST",
                    "item_archetype": "DIAGNOSIS",
                    "decision_granularity": "MANAGEMENT_STRATEGY",
                    "option_set_archetype": "DIAGNOSIS_SET",
                },
                archetypes,
                profile_id="MEDICINE",
            )

    def test_an_option_set_outside_the_archetype_is_refused(self):
        archetypes = load_profile_archetypes(ROOT, "MEDICINE")
        with pytest.raises(QbankError, match="option set"):
            validate_decision_against_profile(
                {
                    "learner_decision_id": "LD-TEST",
                    "item_archetype": "DIAGNOSIS",
                    "decision_granularity": "DIAGNOSIS",
                    "option_set_archetype": "NEXT_ACTION_SET",
                },
                archetypes,
                profile_id="MEDICINE",
            )

    def test_every_built_candidate_conforms_to_its_own_profile(self, candidates):
        cache: dict[str, dict] = {}
        for row in candidates["opportunities"]:
            profile_id = row["discipline_profile_id"]
            if profile_id not in cache:
                cache[profile_id] = load_profile_archetypes(ROOT, profile_id)
            validate_decision_against_profile(row, cache[profile_id], profile_id=profile_id)


class TestRefusalsAreRecordedNotWorkedAround:
    def test_no_refused_address_reappears_as_a_candidate(self, candidates):
        refused = {
            row["allocation_address_id"]
            for row in read_json(ROOT / PROFILE_REFUSALS_PATH)["refusals"]
        }
        used = {row["allocation_address_id"] for row in candidates["opportunities"]}
        assert not refused & used

    def test_no_candidate_rests_on_evidence_reviewed_less_than_aligned(self, candidates):
        verdicts = {
            row["allocation_address_id"]: row["verdict"]
            for row in read_json(ROOT / ALIGNMENT_REVIEW_PATH)["reviews"]
        }
        for row in candidates["opportunities"]:
            assert verdicts[row["allocation_address_id"]] == "ALIGNED"

    def test_the_alignment_review_covers_the_whole_source_ready_queue(self):
        inventory = read_json(
            ROOT / "reports/qgen_fresh_universe_readiness_inventory.json"
        )
        queue = set(inventory["SOURCE_READY_NOT_ONBOARDED"])
        reviewed = {
            row["allocation_address_id"]
            for row in read_json(ROOT / ALIGNMENT_REVIEW_PATH)["reviews"]
        }
        assert reviewed == queue


class TestEvidence:
    def test_every_cited_reference_exists_in_a_researched_packet(self, candidates):
        """build_fresh_opportunities validates this; assert it was not bypassed."""
        for row in candidates["opportunities"]:
            assert row["evidence_refs"]

    def test_a_fabricated_reference_is_refused(self):
        from qbank.fresh_universe_onboarding import validate_evidence_refs

        with pytest.raises(QbankError, match="no researched packet"):
            validate_evidence_refs(
                ROOT,
                {
                    "allocation_address_id": "SU-D-26",
                    "declared_learner_decisions": [
                        {
                            "learner_decision_id": "LD-TEST",
                            "evidence_refs": ["SRC-MED-999-REC-01"],
                        }
                    ],
                },
            )

    def test_a_decision_with_no_evidence_is_refused(self):
        from qbank.fresh_universe_onboarding import validate_evidence_refs

        with pytest.raises(QbankError, match="needs evidence"):
            validate_evidence_refs(
                ROOT,
                {
                    "allocation_address_id": "SU-D-26",
                    "declared_learner_decisions": [
                        {"learner_decision_id": "LD-TEST", "evidence_refs": []}
                    ],
                },
            )


class TestFreshness:
    def test_opportunity_ids_are_stable_and_distinct(self, candidates):
        ids = [row["opportunity_id"] for row in candidates["opportunities"]]
        assert len(ids) == len(set(ids))
        first = candidates["opportunities"][0]
        assert first["opportunity_id"] == compute_opportunity_id(
            wave_id=first["wave_id"],
            allocation_address_id=first["allocation_address_id"],
            learner_decision_id=first["learner_decision_id"],
        )

    def test_no_candidate_reuses_a_study_unit_any_prior_pilot_used(self, candidates):
        inventory = read_json(
            ROOT / "reports/qgen_fresh_universe_readiness_inventory.json"
        )
        onboarded = set(inventory["STUDY_UNITS_ONBOARDED_TO_QGEN"])
        for row in candidates["opportunities"]:
            assert row["anchor_study_unit_id"] not in onboarded

    def test_freshness_is_recorded_per_candidate(self, candidates):
        for row in candidates["opportunities"]:
            assert row["historical_use_status"] in {"FRESH", "ALREADY_USED"}


class TestGate:
    def test_contrast_readiness_is_measured_not_assumed(self, candidates):
        measured = measure_preflight_contrast(ROOT, candidates["opportunities"])
        assert measured["OPPORTUNITIES_MEASURED"] == len(candidates["opportunities"])
        for row in measured["per_opportunity"]:
            if row["contrast_ready"]:
                assert row["vocabulary_features_in_snapshot"] > 0
                assert row["curated_candidates"] >= 3

    def test_the_registry_refusal_is_probed_rather_than_quoted(self):
        probe = probe_vocabulary_extension(ROOT)
        assert probe["NEW_FEATURE_EXTENSION_ADMISSIBLE"] is False
        assert "ANCHOR_RELATION_ONLY" in probe["refusal"]

    def test_readiness_needs_both_the_floor_and_a_contrast_ready_opportunity(self, gate):
        ready = gate["FRESH_UNIVERSE_READY"] == "YES"
        assert ready == (
            gate["FRESH_OPPORTUNITIES_VALIDATED"] >= FRESH_PILOT_FLOOR
            and gate["PREFLIGHT_CONTRAST_READY"] > 0
        )

    def test_no_pilot_is_frozen_when_the_universe_is_not_ready(self, gate):
        if gate["FRESH_UNIVERSE_READY"] == "NO":
            assert gate["FRESH_PILOT_N"] == 0

    def test_the_funnel_never_grows_a_stage(self, gate):
        funnel = gate["funnel"]
        assert funnel["EVIDENCE_ALIGNED_WITH_THE_ADDRESS"] <= funnel[
            "SOURCE_READY_NOT_ONBOARDED"
        ]
        assert funnel["STUDY_UNITS_CARRYING_A_DECLARED_DECISION"] <= funnel[
            "EVIDENCE_ALIGNED_WITH_THE_ADDRESS"
        ]
        assert funnel["FRESH_AFTER_THE_FRESHNESS_AUDIT"] <= funnel[
            "FRESH_OPPORTUNITY_CANDIDATES"
        ]
        assert funnel["OF_THOSE_CONTRAST_READY"] <= funnel[
            "FRESH_AFTER_THE_FRESHNESS_AUDIT"
        ]

    def test_the_alignment_verdicts_partition_the_queue(self, gate):
        funnel = gate["funnel"]
        assert (
            funnel["EVIDENCE_ALIGNED_WITH_THE_ADDRESS"]
            + funnel["EVIDENCE_PARTIALLY_ALIGNED"]
            + funnel["EVIDENCE_MISALIGNED"]
            == funnel["SOURCE_READY_NOT_ONBOARDED"]
        )

    def test_declares_no_llm_use(self, candidates, gate):
        assert candidates["llm_api_calls"] == 0
        assert gate["llm_api_calls"] == 0


class TestCommittedArtifactsRegenerate:
    def test_opportunities_regenerate_byte_identically(self, candidates):
        assert read_json(ROOT / OPPORTUNITIES_PATH) == candidates

    def test_the_gate_regenerates_byte_identically(self, gate):
        assert read_json(ROOT / GATE_REPORT_PATH) == gate

    def test_the_declared_decisions_are_frozen(self):
        assert read_json(ROOT / DECLARED_DECISIONS_PATH)["frozen"] is True


def test_the_wave_carries_a_copyright_audit_over_everything_it_wrote(gate):
    from qbank.fresh_universe_onboarding import TRACKED_ARTIFACTS

    audit = gate["copyright"]
    assert audit["COPYRIGHT_AUDIT"] == "PASS"
    assert audit["longest_verbatim_toronto_notes_run_words"] == 0
    scanned = {row["artifact"] for row in audit["per_artifact"]}
    assert scanned == set(TRACKED_ARTIFACTS)
