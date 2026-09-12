from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.qbank.fresh_holdout_24 import (
    FreshHoldoutError,
    build_eligible_fresh_inventory,
    build_historical_exclusion,
    partition_waves,
    validate_final_accounting,
    validate_frozen_roster,
    compose_freeze_artifacts,
    build_existing_seed_baseline,
    compose_execution_artifacts,
    content_sha256,
)


ROOT = Path(__file__).resolve().parents[1]


def _opportunity(discipline: str, index: int) -> dict:
    return {
        "opportunity_id": f"QH24-{discipline}-{index:02d}",
        "discipline": discipline,
        "study_unit_id": f"SU-{discipline}-{index:02d}",
        "allocation_address_id": f"SU-{discipline}-{index:02d}",
        "learner_decision_id": f"LD-H24-{discipline}-{index:02d}",
        "learner_decision": f"Choose the bounded {discipline} decision {index}.",
        "evidence_readiness": "ALIGNED_COMPLETE",
    }


def _balanced_roster() -> list[dict]:
    return [
        _opportunity(discipline, index)
        for discipline in ("MED", "PED", "OBGYN", "SURG", "PSY", "PHELO")
        for index in range(1, 5)
    ]


def test_historical_exclusion_includes_old_pilots_and_development_36_without_source_plan_leakage():
    exclusion = build_historical_exclusion(ROOT)
    units = set(exclusion["excluded_study_unit_ids"])
    decisions = {row["learner_decision_id"] for row in exclusion["entries"]}

    assert "SU-C-21" in units
    assert "SU-P-099" in units
    assert "LD-C21-01" in decisions
    assert "LD-ONB2-PED-AOM-DX" in decisions
    assert "SU-A-03" not in units
    assert exclusion["development_36_classification"] == "DEVELOPMENT_REGRESSION_SET"


def test_eligible_inventory_uses_priority_and_source_state_but_no_contrast_signal():
    exclusion = build_historical_exclusion(ROOT)
    inventory = build_eligible_fresh_inventory(ROOT, exclusion)
    by_id = {row["allocation_address_id"]: row for row in inventory["candidates"]}

    assert "SU-C-21" not in by_id
    assert by_id["SU-A-03"]["priority"] == "CORE"
    assert by_id["SU-A-03"]["evidence_readiness"] == "CURRENT_REPOSITORY_PACKET_READY"
    assert by_id["SU-P-003"]["evidence_readiness"] == "TARGETED_RESEARCH_REQUIRED"
    assert "contrast_ready" not in by_id["SU-A-03"]
    assert "seed" not in json.dumps(inventory).casefold()


def test_frozen_roster_requires_four_new_study_units_per_discipline():
    roster = _balanced_roster()
    result = validate_frozen_roster(roster, excluded_study_unit_ids={"SU-C-21"})

    assert result["frozen_count"] == 24
    assert result["new_study_units"] == 24
    assert result["counts_by_discipline"] == {
        "MED": 4,
        "PED": 4,
        "OBGYN": 4,
        "SURG": 4,
        "PSY": 4,
        "PHELO": 4,
    }


def test_frozen_roster_fails_closed_on_historical_or_duplicate_unit():
    roster = _balanced_roster()
    roster[0]["study_unit_id"] = "SU-C-21"
    roster[0]["allocation_address_id"] = "SU-C-21"
    with pytest.raises(FreshHoldoutError, match="historical study unit"):
        validate_frozen_roster(roster, excluded_study_unit_ids={"SU-C-21"})

    roster = _balanced_roster()
    roster[1]["study_unit_id"] = roster[0]["study_unit_id"]
    with pytest.raises(FreshHoldoutError, match="one new study unit per opportunity"):
        validate_frozen_roster(roster, excluded_study_unit_ids=set())


def test_wave_partition_takes_first_two_opportunity_ids_in_each_discipline():
    roster = list(reversed(_balanced_roster()))
    waves = partition_waves(roster)

    assert len(waves["WAVE_1"]) == 12
    assert len(waves["WAVE_2"]) == 12
    assert [row["opportunity_id"] for row in waves["WAVE_1"][:2]] == [
        "QH24-MED-01",
        "QH24-MED-02",
    ]
    assert [row["opportunity_id"] for row in waves["WAVE_2"][:2]] == [
        "QH24-MED-03",
        "QH24-MED-04",
    ]


def test_final_accounting_requires_one_earliest_failure_for_every_nonaccepted_opportunity():
    report = {
        "frozen": 24,
        "accepted": 7,
        "generated": 9,
        "final_reviewed": 9,
        "rejected": 2,
        "no_safe_item": 15,
        "failure_counts": {
            "NO_SEED_CANDIDATE": 12,
            "FINAL_REVIEW_REJECTION": 2,
            "EVIDENCE_NOT_READY": 3,
        },
    }

    metrics = validate_final_accounting(report)

    assert metrics == {
        "safe_yield": 7 / 24,
        "generation_acceptance": 7 / 9,
        "final_review_acceptance": 7 / 9,
    }

    broken = json.loads(json.dumps(report))
    broken["failure_counts"]["NO_SEED_CANDIDATE"] = 11
    with pytest.raises(FreshHoldoutError, match="failure counts"):
        validate_final_accounting(broken)


def test_authored_freeze_is_balanced_profile_expressible_and_hash_pinned():
    artifacts = compose_freeze_artifacts(ROOT)
    roster = artifacts["opportunities"]
    maps = artifacts["feature_maps"]
    architecture = artifacts["architecture"]

    assert validate_frozen_roster(
        roster["opportunities"],
        excluded_study_unit_ids=set(
            artifacts["historical_exclusion"]["excluded_study_unit_ids"]
        ),
    )["frozen_count"] == 24
    assert roster["content_sha256"]
    assert maps["content_sha256"]
    assert architecture["freeze_precedes_seed_inspection"] is True
    assert maps["approved"] == 24
    assert maps["unsafe"] == 0
    assert all(row["profile"]["structural_status"] == "PROFILE_EXPRESSIBLE"
               for row in roster["opportunities"])
    assert all(row["authored_before_seed_retrieval"] for row in maps["opportunities"])


def test_existing_seed_baseline_runs_only_after_frozen_hashes_and_covers_all_24():
    artifacts = compose_freeze_artifacts(ROOT)
    baseline = build_existing_seed_baseline(ROOT, artifacts=artifacts)

    assert baseline["opportunity_roster_sha256"] == artifacts["opportunities"]["content_sha256"]
    assert baseline["feature_maps_sha256"] == artifacts["feature_maps"]["content_sha256"]
    assert baseline["opportunities_attempted"] == 24
    assert len(baseline["opportunities"]) == 24
    assert baseline["approved_seed_sources"] == [
        "HISTORICAL_APPROVED_SEED_PACKS",
        "APPROVED_DEVELOPMENT_REUSABLE_SEED_PACKS",
    ]


def test_two_wave_execution_preserves_roster_and_fails_closed():
    frozen = compose_freeze_artifacts(ROOT)
    baseline = build_existing_seed_baseline(ROOT, artifacts=frozen)
    with pytest.raises(FreshHoldoutError, match="MISSING_GENERATION_CONTEXT"):
        compose_execution_artifacts(ROOT, frozen=frozen, baseline=baseline)


def test_written_holdout_milestone_is_content_addressed_and_records_contamination():
    folder = ROOT / "research/qgen/holdout"
    milestone = json.loads((folder / "fresh_holdout_24_milestone.json").read_text())
    assert milestone["content_sha256"] == content_sha256(milestone)
    assert milestone["holdout_assessment"] == "HOLDOUT_CONTAMINATED"
    assert milestone["copyright"]["COPYRIGHT_AUDIT"] == "PASS"
    assert milestone["independent_review"]["provisional_seed_packs_invalidated"] is True
    assert milestone["integrity"]["generation_retries"] == 0
    final_retrieval = json.loads(
        (folder / "fresh_holdout_24_final_retrieval.json").read_text()
    )
    assert len(final_retrieval["rows"]) == 24
    assert not any(row["contrast_ready"] for row in final_retrieval["rows"])
    for wave in ("wave_1", "wave_2"):
        review = json.loads(
            (folder / f"fresh_holdout_24_{wave}_seed_independent_review.json").read_text()
        )
        assert review["provisional_pack_invalidated"] is True
        assert not any(row["verdict"] == "APPROVED" for row in review["reviews"])
