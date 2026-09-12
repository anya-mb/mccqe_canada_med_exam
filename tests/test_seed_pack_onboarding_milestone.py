from __future__ import annotations

import json
from pathlib import Path

from scripts.qbank.seed_pack_onboarding_milestone import select_development_12
from scripts.qbank.build_seed_onboarding_pack import build_artifacts
from scripts.qbank.clinical_contrast_v2 import validate_contrast_relation
from scripts.qbank.run_seed_onboarding_milestone import (
    build_frozen_contrast_set,
    build_full_replay,
    build_replay,
)
from scripts.qbank.seed_onboarding_generation import build_and_validate_development_item
from scripts.qbank.seed_onboarding_reporting import build_registry, build_milestone_report
from scripts.qbank.feature_anchor_registry import content_sha256
from scripts.qbank.schema import validate_instance


ROOT = Path(__file__).resolve().parents[1]


def test_development_12_is_first_two_ids_per_discipline_after_route_a_exclusion():
    frozen = json.loads(
        (ROOT / "research/qgen/onboarding/v2_frozen_pilot_opportunities.json").read_text()
    )

    selected = select_development_12(
        frozen,
        excluded_route_a={"LD-C35-01", "LD-PH11-01", "LD-PH12-01", "LD-OB53-02"},
    )

    assert [row["learner_decision_id"] for row in selected] == [
        "LD-D04-01", "LD-D05-01",
        "LD-OB53-01", "LD-OB53-03",
        "LD-ONB2-PED-AOM-DX", "LD-ONB2-PED-AOM-OBSERVE",
        "LD-ONB2-PH-WORK-HISTORY", "LD-PH34-01",
        "LD-ONB2-PSY-AUD-ABSTINENCE", "LD-ONB2-PSY-AUD-INTERVIEW",
        "LD-ONB2-SURG-CROUP-DISCHARGE", "LD-ONB2-SURG-CROUP-DX",
    ]
    assert {discipline: sum(row["discipline"] == discipline for row in selected)
            for discipline in ("MED", "OBGYN", "PED", "PHELO", "PSY", "SURG")} == {
        "MED": 2, "OBGYN": 2, "PED": 2, "PHELO": 2, "PSY": 2, "SURG": 2,
    }


def test_reviewed_pack_materializes_only_the_four_approved_seed_rows():
    artifacts = build_artifacts(ROOT)
    pack = artifacts["pack"]
    seeds = [seed for target in pack["targets"] for seed in target["seeds"]]
    assert [seed["seed_id"] for seed in seeds] == [
        "SEED-V6-AOM-OME",
        "SEED-V6-AOM-MYRINGITIS",
        "SEED-V6-AOM-ETD",
        "SEED-V6-AOM-OTITIS-EXTERNA",
    ]
    assert all(seed["onboarding_status"] == "APPROVED" for seed in seeds)
    validate_instance(ROOT, "generalized-competitive-contrast-seed-pack", pack)
    for relation in artifacts["relations"]["relations"]:
        validate_contrast_relation(relation)
    seed_ids = {seed["seed_id"] for seed in seeds}
    assert {row["seed_id"] for row in artifacts["enrichment"]["seeds"]} == seed_ids
    assert {row["seed_id"] for row in artifacts["stem_anchors"]["seeds"]} == seed_ids


def test_development_12_replay_improves_only_the_reviewed_aom_scope():
    replay = build_replay(ROOT)
    assert replay["historical_replay_identical"] is True
    assert replay["approved_seed_retrievable"] is True
    assert replay["rejected_seed_retrievable"] is False
    assert replay["uncertain_seed_retrievable"] is False
    assert replay["scope_leakage"] == 0
    assert replay["development_12_baseline_ready"] == 0
    assert replay["development_12_post_seed_ready"] == 1
    assert [
        row["learner_decision_id"]
        for row in replay["opportunities"]
        if row["contrast_ready"]
    ] == ["LD-ONB2-PED-AOM-DX"]


def test_validated_pack_expands_to_the_full_development_36_without_scope_leakage():
    replay = build_full_replay(ROOT)
    assert replay["development_36_post_seed_ready"] == 1
    assert replay["ready_by_discipline"] == {
        "MED": "0/16", "PED": "1/2", "OBGYN": "0/6",
        "SURG": "0/3", "PSY": "0/3", "PHELO": "0/6",
    }
    assert replay["scope_leakage"] == 0


def test_ready_opportunity_freezes_exactly_one_three_competitor_set():
    document = build_frozen_contrast_set(ROOT)
    assert document["frozen"] is True
    assert len(document["contrast_sets"]) == 1
    contrast_set = document["contrast_sets"][0]
    assert contrast_set["learner_decision_id"] == "LD-ONB2-PED-AOM-DX"
    assert contrast_set["seed_ids"] == [
        "SEED-V6-AOM-ETD",
        "SEED-V6-AOM-MYRINGITIS",
        "SEED-V6-AOM-OME",
    ]
    assert document["content_sha256"] == content_sha256(
        {key: value for key, value in document.items() if key != "content_sha256"}
    )


def test_development_item_passes_post_stem_and_option_set_gates():
    document = build_and_validate_development_item(ROOT)
    assert document["overall_status"] == "PASS"
    assert document["post_stem_validation"]["verdict"] == "PASS"
    assert document["option_set_admissibility"]["verdict"] == "ADMISSIBLE"
    assert document["option_set_admissibility"]["admissible_competitor_count"] == 3
    assert document["rationale_audit"]["verdict"] == "PASS"
    assert [row["text"] for row in document["item"]["options"]] == [
        "Eustachian-tube dysfunction",
        "Viral myringitis",
        "Otitis media with effusion",
        "Acute otitis media",
    ]
    assert [row["role"] for row in document["item"]["options"]] == [
        "DISTRACTOR", "DISTRACTOR", "DISTRACTOR", "KEY",
    ]


def test_registry_and_milestone_metrics_reconcile_to_source_artifacts():
    registry = build_registry(ROOT)
    report = build_milestone_report(ROOT)
    assert registry["pack_count"] == 1
    assert registry["seed_counts"] == {
        "APPROVED": 4, "REJECTED": 1, "UNCERTAIN": 1,
    }
    assert registry["reuse_counts"] == {
        "SEED": 0, "RELATION": 0, "ANCHOR": 2,
    }
    assert report["failure_counts"] == {
        "NO_SEED_CANDIDATE": 33,
        "SEED_REVIEW_REJECTED": 1,
        "OTHER": 1,
    }
    assert report["development_safe_yield"] == {"accepted": 1, "total": 36}
    assert report["context_chars"] == {"median": 1261, "p95": 1443}
    assert report["copyright"]["COPYRIGHT_AUDIT"] == "PASS"
    assert report["copyright"]["longest_verbatim_toronto_notes_run_words"] == 0
