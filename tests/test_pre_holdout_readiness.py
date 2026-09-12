from __future__ import annotations

from collections import Counter, defaultdict
import json
from pathlib import Path

import pytest

from scripts.qbank.pre_holdout_readiness import (
    ReadinessIntegrityError,
    build_development_exclusions,
    content_sha256,
    select_development_units,
    validate_development_selection,
)


ROOT = Path(__file__).resolve().parents[1]
DISCIPLINES = ("MED", "PED", "OBGYN", "SURG", "PSY", "PHELO")


def test_exclusions_include_diagnostic_18_and_every_historical_unit():
    """Catches reuse of architecture-development material in the new pool."""
    artifact = build_development_exclusions(ROOT)
    rows = artifact["excluded_units"]
    excluded = {row["study_unit_id"] for row in rows}

    assert artifact["diagnostic_18_classification"] == "FRESH_PREREQUISITE_DIAGNOSTIC_18"
    assert len(artifact["diagnostic_18_study_unit_ids"]) == 18
    assert set(artifact["diagnostic_18_study_unit_ids"]) <= excluded
    assert artifact["exclusion_sources"]
    assert all(row["exclusion_reasons"] for row in rows)
    assert artifact["content_sha256"]


def test_selection_is_balanced_diverse_fresh_and_outcome_blind():
    """Catches discipline imbalance, subsystem clustering, or generation-aware selection."""
    exclusions = build_development_exclusions(ROOT)
    artifact = select_development_units(ROOT, exclusions)
    rows = artifact["units"]

    assert len(rows) == 90
    assert Counter(row["discipline"] for row in rows) == {
        discipline: 15 for discipline in DISCIPLINES
    }
    assert len({row["study_unit_id"] for row in rows}) == 90
    assert not ({row["study_unit_id"] for row in rows} & {
        row["study_unit_id"] for row in exclusions["excluded_units"]
    })
    families = defaultdict(set)
    for row in rows:
        families[row["discipline"]].add(row["topic_family"])
    assert all(len(families[discipline]) >= 3 for discipline in DISCIPLINES)
    forbidden = {"seed", "contrast", "distractor", "stem", "yield", "accepted_item"}
    assert not any(
        any(token in key.lower() for token in forbidden)
        for row in rows
        for key in row
    )
    assert artifact["selection_uses_generation_outcomes"] is False
    assert sum(
        row["discipline"] == "MED"
        and row["source_packet_status"] == "CURRENT_REPOSITORY_PACKET_READY"
        for row in rows
    ) >= 8
    assert validate_development_selection(ROOT, artifact)["verdict"] == "PASS"


def test_selection_validator_fails_closed_on_excluded_overlap():
    """Catches a tampered roster that silently reintroduces a diagnostic unit."""
    exclusions = build_development_exclusions(ROOT)
    artifact = select_development_units(ROOT, exclusions)
    artifact["units"][0]["study_unit_id"] = exclusions["diagnostic_18_study_unit_ids"][0]

    with pytest.raises(ReadinessIntegrityError, match="EXCLUDED_DEVELOPMENT_UNIT"):
        validate_development_selection(ROOT, artifact)


def _audit_fixture():
    selection = {
        "units": [{
            "development_id": "RDY-MED-01",
            "discipline": "MED",
            "study_unit_id": "SU-X",
            "source_packet_status": "CURRENT_REPOSITORY_PACKET_READY",
        }]
    }
    claim = {
        "claim_id": "CLM-X",
        "statement": "The finding requires urgent assessment.",
        "source_verified": True,
        "source_id": "AUTH-X",
        "locator": "Recommendation 1",
    }
    decision = {
        "development_id": "RDY-MED-01",
        "discipline": "MED",
        "study_unit_id": "SU-X",
        "learner_decision_id": "LD-RDY-MED-01",
        "decision_type": "EMERGENCY_STABILIZATION",
        "learner_decision": "Recognize the finding and arrange urgent assessment.",
        "audit_verdict": "ALIGNED_COMPLETE",
        "readiness_origin": "EXISTING_EVIDENCE",
        "load_bearing_propositions": [{
            "proposition_id": "PROP-X",
            "statement": "The finding requires urgent assessment.",
            "claim_ids": ["CLM-X"],
        }],
        "claim_ids": ["CLM-X"],
        "author_execution_id": "decision-author",
    }
    decision["content_sha256"] = content_sha256(decision)
    review = {
        "learner_decision_id": decision["learner_decision_id"],
        "subject_sha256": decision["content_sha256"],
        "verdict": "APPROVED",
        "reviewer_execution_id": "evidence-reviewer",
        "author_execution_id": "decision-author",
        "independent_context": True,
        "claim_sha256": {"CLM-X": content_sha256(claim)},
    }
    return selection, {"decisions": [decision]}, {"reviews": [review]}, {"CLM-X": claim}


def test_decision_audit_is_exhaustive_and_uses_closed_verdicts():
    from scripts.qbank.pre_holdout_readiness import validate_decision_audit

    selection, audit, _, _ = _audit_fixture()
    assert validate_decision_audit(selection, audit)["verdict"] == "PASS"
    audit["decisions"][0]["audit_verdict"] = "PACKET_READY"
    audit["decisions"][0]["content_sha256"] = content_sha256(audit["decisions"][0])
    with pytest.raises(ReadinessIntegrityError, match="INVALID_EVIDENCE_AUDIT_VERDICT"):
        validate_decision_audit(selection, audit)


def test_complete_decision_requires_pinned_load_bearing_claims():
    from scripts.qbank.pre_holdout_readiness import validate_decision_audit

    selection, audit, _, _ = _audit_fixture()
    audit["decisions"][0]["load_bearing_propositions"] = []
    audit["decisions"][0]["content_sha256"] = content_sha256(audit["decisions"][0])
    with pytest.raises(ReadinessIntegrityError, match="UNSUPPORTED_COMPLETE_DECISION"):
        validate_decision_audit(selection, audit)


def test_independent_evidence_review_is_hash_pinned_and_fail_closed():
    from scripts.qbank.pre_holdout_readiness import validate_evidence_reviews

    _, audit, reviews, catalog = _audit_fixture()
    assert validate_evidence_reviews(audit, reviews, catalog)["approved"] == 1
    reviews["reviews"][0]["reviewer_execution_id"] = "decision-author"
    with pytest.raises(ReadinessIntegrityError, match="NONINDEPENDENT_EVIDENCE_REVIEW"):
        validate_evidence_reviews(audit, reviews, catalog)


def test_packet_ready_false_positive_is_distinct_from_decision_readiness():
    from scripts.qbank.pre_holdout_readiness import readiness_metrics

    selection, audit, _, catalog = _audit_fixture()
    audit["decisions"][0]["audit_verdict"] = "ALIGNED_PARTIAL"
    audit["decisions"][0]["readiness_origin"] = "NONE"
    audit["decisions"][0]["claim_ids"] = []
    audit["decisions"][0]["load_bearing_propositions"] = []
    audit["decisions"][0]["content_sha256"] = content_sha256(audit["decisions"][0])
    metrics = readiness_metrics(selection, audit, {"reviews": []}, catalog)
    assert metrics["packet_ready"] == 1
    assert metrics["decision_evidence_ready"] == 0
    assert metrics["packet_ready_but_decision_not_ready"] == 1


def test_bounded_evidence_wave_reaches_gate_without_forcing_all_candidates():
    from scripts.qbank.pre_holdout_readiness import (
        build_evidence_wave,
        readiness_metrics,
        validate_decision_audit,
    )

    selection = select_development_units(ROOT, build_development_exclusions(ROOT))
    outputs = build_evidence_wave(ROOT, selection)
    validation = validate_decision_audit(selection, outputs["audit"])
    metrics = readiness_metrics(
        selection, outputs["audit"], outputs["reviews"], outputs["claim_catalog"]
    )

    assert validation["audited"] == 90
    assert metrics["decision_ready_by_discipline"] == {
        discipline: 8 for discipline in DISCIPLINES
    }
    assert outputs["economics"]["already_ready"] == 8
    assert outputs["economics"]["research_requests"] == 40
    assert outputs["economics"]["newly_ready_after_research"] == 40
    assert metrics["packet_ready"] == 20
    assert metrics["packet_ready_but_decision_not_ready"] == 11


def test_feature_wave_is_append_only_scoped_and_revalidates_all_ready_decisions():
    from copy import deepcopy
    from scripts.qbank.pre_holdout_readiness import (
        build_evidence_wave,
        build_feature_wave,
        content_sha256,
    )

    selection = select_development_units(ROOT, build_development_exclusions(ROOT))
    evidence = build_evidence_wave(ROOT, selection)
    parent = json.loads(
        (ROOT / "research/qgen/onboarding/feature_anchor_snapshot_v5.json").read_text()
    )
    frozen_parent = deepcopy(parent)
    outputs = build_feature_wave(ROOT, evidence)
    snapshot = outputs["snapshot"]

    assert parent == frozen_parent
    assert snapshot["snapshot_id"] == "FEATURE_ANCHOR_SNAPSHOT_V6"
    assert snapshot["parent_content_sha256"] == parent["content_sha256"]
    assert snapshot["anchor_relations"] == parent["anchor_relations"]
    assert outputs["metrics"]["feature_ready_by_discipline"] == {
        discipline: 8 for discipline in DISCIPLINES
    }
    assert outputs["metrics"]["decision_and_feature_ready_total"] == 48
    assert outputs["metrics"]["new_features_proposed"] == 48
    assert outputs["metrics"]["new_features_approved"] == 48
    assert outputs["metrics"]["new_unit_bindings_approved"] == 57
    assert snapshot["content_sha256"] == content_sha256(snapshot)


def test_future_inventory_excludes_all_used_units_without_selecting_a_holdout():
    from scripts.qbank.pre_holdout_readiness import build_future_holdout_inventory

    exclusions = build_development_exclusions(ROOT)
    selection = select_development_units(ROOT, exclusions)
    artifact = build_future_holdout_inventory(ROOT, exclusions, selection)

    assert artifact["future_holdout_selected"] is False
    assert artifact["seed_availability_inspected"] is False
    assert artifact["eligible_unit_count"] == 753
    assert artifact["by_discipline"] == {
        "MED": 376,
        "PED": 87,
        "OBGYN": 42,
        "SURG": 220,
        "PSY": 11,
        "PHELO": 17,
    }
    used = {
        row["study_unit_id"] for row in exclusions["excluded_units"]
    } | {row["study_unit_id"] for row in selection["units"]}
    assert not (used & {row["study_unit_id"] for row in artifact["units"]})


def test_final_readiness_gate_passes_without_consuming_the_next_holdout():
    from scripts.qbank.pre_holdout_readiness import build_milestone_report

    report = build_milestone_report(
        ROOT,
        focused_passed=10,
        focused_failed=0,
        full_passed=999,
        full_failed=1,
        known_preexisting_failures=1,
    )

    assert report["generalized_pre_holdout_readiness_milestone"] == "COMPLETE"
    assert report["ready_for_new_holdout"] == "YES"
    assert report["minimum_ready_pool_gate"] == "PASS"
    assert report["historical_safety_regression"] == "PASS"
    assert report["aom_development_control"] == "PASS"
    assert report["copyright_audit"]["COPYRIGHT_AUDIT"] == "PASS"
    assert report["next_holdout_recommended_n"] == 18
    assert report["next_holdout_consumed"] is False
    assert report["seed_discovery_run"] is False
