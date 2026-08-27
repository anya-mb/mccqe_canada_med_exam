"""Tests for incremental global ownership decisions and batch audits."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from qbank.cli import _parser


def _write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def _fixture(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    units = [f"SU-{letter}" for letter in "ABCDEFGH"]
    _write(
        root / "research/scope/master_scope_crosswalk.json",
        {
            "total_study_units": len(units),
            "entries": [{"study_unit_id": unit_id} for unit_id in units],
        },
    )
    _write(
        root / "research/scope/global_ownership_batches.json",
        {
            "schema_version": "1.0",
            "batch_size_maximum": 10,
            "total_batches": 2,
            "batches": [
                {
                    "batch_id": "PRIORITY_A-B01",
                    "priority": "PRIORITY_A",
                    "group_ids": ["G-1", "G-2", "G-3"],
                },
                {
                    "batch_id": "PRIORITY_A-B02",
                    "priority": "PRIORITY_A",
                    "group_ids": ["G-4"],
                },
            ],
        },
    )
    _write(
        root / "research/scope/global_ownership_triage.json",
        {
            "groups": [
                {
                    "group_id": "G-1",
                    "candidate_type": "EXACT_DUPLICATE_CANDIDATE",
                    "priority": "PRIORITY_A",
                    "study_unit_ids": ["SU-A", "SU-B"],
                },
                {
                    "group_id": "G-2",
                    "candidate_type": "CONTEXT_VARIANT_CANDIDATE",
                    "priority": "PRIORITY_A",
                    "study_unit_ids": ["SU-C", "SU-D"],
                },
                {
                    "group_id": "G-3",
                    "candidate_type": "EXPLICIT_CROSS_LINK_CANDIDATE",
                    "priority": "PRIORITY_A",
                    "study_unit_ids": ["SU-E", "SU-F"],
                },
                {
                    "group_id": "G-4",
                    "candidate_type": "EXACT_DUPLICATE_CANDIDATE",
                    "priority": "PRIORITY_A",
                    "study_unit_ids": ["SU-G", "SU-H"],
                },
            ]
        },
    )
    _write(
        root / "research/scope/global_ownership_decisions.json",
        {
            "schema_version": "1.0",
            "scope": "GLOBAL_OWNERSHIP_DECISIONS",
            "adjudicated_batches": ["PRIORITY_A-B01"],
            "decisions": [
                {
                    "candidate_group_id": "G-1",
                    "candidate_type": "EXACT_DUPLICATE_CANDIDATE",
                    "study_unit_id": "SU-A",
                    "ownership_role": "PRIMARY_OWNER",
                    "rationale": "Canonical home for the shared competency.",
                    "decision_status": "RESOLVED",
                    "confidence": "HIGH",
                    "adjudication_batch": "PRIORITY_A-B01",
                },
                {
                    "candidate_group_id": "G-1",
                    "candidate_type": "EXACT_DUPLICATE_CANDIDATE",
                    "study_unit_id": "SU-B",
                    "ownership_role": "CROSS_LINK",
                    "primary_owner_study_unit_id": "SU-A",
                    "rationale": "Substantially shared coverage links to SU-A.",
                    "decision_status": "RESOLVED",
                    "confidence": "HIGH",
                    "adjudication_batch": "PRIORITY_A-B01",
                },
                *[
                    {
                        "candidate_group_id": "G-2",
                        "candidate_type": "CONTEXT_VARIANT_CANDIDATE",
                        "study_unit_id": unit_id,
                        "ownership_role": "DISTINCT_CONTEXT",
                        "rationale": "The context tests an independent competency.",
                        "decision_status": "RESOLVED",
                        "confidence": "MODERATE",
                        "adjudication_batch": "PRIORITY_A-B01",
                    }
                    for unit_id in ("SU-C", "SU-D")
                ],
            ],
            "deferred_groups": [
                {
                    "candidate_group_id": "G-3",
                    "candidate_type": "EXPLICIT_CROSS_LINK_CANDIDATE",
                    "study_unit_ids": ["SU-E", "SU-F"],
                    "rationale": "Insufficient evidence for a safe ownership assignment.",
                    "decision_status": "DEFERRED_COMPLEX_OWNERSHIP",
                    "confidence": "LOW",
                    "adjudication_batch": "PRIORITY_A-B01",
                }
            ],
        },
    )
    return root


def _load_decisions(root: Path) -> dict:
    return json.loads(
        (root / "research/scope/global_ownership_decisions.json").read_text(
            encoding="utf-8"
        )
    )


def _save_decisions(root: Path, value: dict) -> None:
    _write(root / "research/scope/global_ownership_decisions.json", value)


def _errors(root: Path) -> list[str]:
    from qbank.global_ownership_decisions import validate_global_ownership_decisions

    return validate_global_ownership_decisions(root).errors


def test_ownership_decision_commands_are_registered():
    commands = _parser()._subparsers._group_actions[0].choices
    assert "build-global-ownership-audit" in commands
    assert "validate-global-ownership-decisions" in commands


def test_incremental_ownership_layer_builds_a_reconciled_batch_audit(tmp_path):
    """Dropping a reviewed group or counting a future group must fail reconciliation."""
    from qbank.global_ownership_decisions import (
        build_global_ownership_batch_audit,
        validate_global_ownership_decisions,
    )

    root = _fixture(tmp_path)
    audit = build_global_ownership_batch_audit(root, "PRIORITY_A-B01")
    result = validate_global_ownership_decisions(root)

    assert result.status == "PASS"
    assert audit["groups_reviewed"] == 3
    assert audit["groups_resolved"] == 2
    assert audit["groups_deferred"] == 1
    assert audit["assignment_counts"] == {
        "PRIMARY_OWNER": 1,
        "CROSS_LINK": 1,
        "DISTINCT_CONTEXT": 2,
    }
    assert audit["confidence_counts"] == {"HIGH": 1, "MODERATE": 1, "LOW": 1}
    assert [group["candidate_group_id"] for group in audit["groups"]] == [
        "G-1",
        "G-2",
        "G-3",
    ]


def test_ownership_validator_rejects_unknown_study_unit(tmp_path):
    """A stale or fabricated study-unit ID must not enter the ownership layer."""
    root = _fixture(tmp_path)
    value = _load_decisions(root)
    value["decisions"][0]["study_unit_id"] = "SU-UNKNOWN"
    _save_decisions(root, value)

    assert any("unknown study_unit_id" in error for error in _errors(root))


def test_ownership_validator_rejects_cross_link_without_primary_owner(tmp_path):
    """A cross-link target must be assigned PRIMARY_OWNER, not merely exist."""
    root = _fixture(tmp_path)
    value = _load_decisions(root)
    value["decisions"][1]["primary_owner_study_unit_id"] = "SU-C"
    _save_decisions(root, value)

    assert any("does not reference a PRIMARY_OWNER" in error for error in _errors(root))


def test_ownership_validator_rejects_self_link(tmp_path):
    """A unit cannot cross-link to itself."""
    root = _fixture(tmp_path)
    value = _load_decisions(root)
    value["decisions"][1]["primary_owner_study_unit_id"] = "SU-B"
    _save_decisions(root, value)

    assert any("self-link" in error for error in _errors(root))


def test_ownership_validator_rejects_ownership_cycle(tmp_path):
    """A pair of cross-links cannot form an ownership cycle."""
    root = _fixture(tmp_path)
    value = _load_decisions(root)
    value["decisions"][0]["ownership_role"] = "CROSS_LINK"
    value["decisions"][0]["primary_owner_study_unit_id"] = "SU-B"
    value["decisions"][1]["primary_owner_study_unit_id"] = "SU-A"
    _save_decisions(root, value)

    assert any("ownership cycle" in error for error in _errors(root))


def test_ownership_validator_rejects_contradictory_role_assignments(tmp_path):
    """A repeated unit cannot be both a primary owner and another owner's cross-link."""
    root = _fixture(tmp_path)
    value = _load_decisions(root)
    duplicate = copy.deepcopy(value["decisions"][2])
    duplicate.update(
        {
            "study_unit_id": "SU-A",
            "ownership_role": "CROSS_LINK",
            "primary_owner_study_unit_id": "SU-C",
        }
    )
    value["decisions"].append(duplicate)
    _save_decisions(root, value)

    assert any("contradictory ownership roles" in error for error in _errors(root))


def test_distinct_context_can_coexist_with_a_role_in_another_group(tmp_path):
    """DISTINCT_CONTEXT is relational and does not contradict another group role."""
    from qbank.global_ownership_decisions import (
        build_global_ownership_batch_audit,
        validate_global_ownership_decisions,
    )

    root = _fixture(tmp_path)
    triage_path = root / "research/scope/global_ownership_triage.json"
    triage = json.loads(triage_path.read_text(encoding="utf-8"))
    triage["groups"][1]["study_unit_ids"] = ["SU-A", "SU-C", "SU-D"]
    _write(triage_path, triage)
    value = _load_decisions(root)
    distinct = copy.deepcopy(value["decisions"][2])
    distinct["study_unit_id"] = "SU-A"
    value["decisions"].append(distinct)
    _save_decisions(root, value)

    build_global_ownership_batch_audit(root, "PRIORITY_A-B01")
    assert validate_global_ownership_decisions(root).status == "PASS"


def test_singleton_group_can_cross_link_to_one_targeted_external_primary_owner(tmp_path):
    """A deferred singleton may resolve through one directly linked canonical counterpart."""
    from qbank.global_ownership_decisions import (
        build_global_ownership_batch_audit,
        validate_global_ownership_decisions,
    )

    root = _fixture(tmp_path)
    triage_path = root / "research/scope/global_ownership_triage.json"
    triage = json.loads(triage_path.read_text(encoding="utf-8"))
    triage["groups"][2]["study_unit_ids"] = ["SU-E"]
    _write(triage_path, triage)
    value = _load_decisions(root)
    value["deferred_groups"] = []
    value["decisions"].extend(
        [
            {
                "candidate_group_id": "G-3",
                "candidate_type": "EXPLICIT_CROSS_LINK_CANDIDATE",
                "study_unit_id": "SU-G",
                "ownership_role": "PRIMARY_OWNER",
                "rationale": "The targeted canonical counterpart is the natural teaching home.",
                "decision_status": "RESOLVED",
                "confidence": "HIGH",
                "adjudication_batch": "PRIORITY_A-B01",
            },
            {
                "candidate_group_id": "G-3",
                "candidate_type": "EXPLICIT_CROSS_LINK_CANDIDATE",
                "study_unit_id": "SU-E",
                "ownership_role": "CROSS_LINK",
                "primary_owner_study_unit_id": "SU-G",
                "rationale": "The original singleton directly links to its targeted owner.",
                "decision_status": "RESOLVED",
                "confidence": "HIGH",
                "adjudication_batch": "PRIORITY_A-B01",
            },
        ]
    )
    _save_decisions(root, value)

    audit = build_global_ownership_batch_audit(root, "PRIORITY_A-B01")

    assert validate_global_ownership_decisions(root).status == "PASS"
    group = next(item for item in audit["groups"] if item["candidate_group_id"] == "G-3")
    assert group["study_unit_ids"] == ["SU-E"]
    assert group["primary_owner_study_unit_id"] == "SU-G"
    assert {item["study_unit_id"] for item in group["final_ownership_roles"]} == {
        "SU-E",
        "SU-G",
    }


def test_shared_group_cross_links_must_target_its_own_primary_owner(tmp_path):
    """A group cannot cross-link one member to a primary owner from another group."""
    root = _fixture(tmp_path)
    value = _load_decisions(root)
    value["decisions"][1]["primary_owner_study_unit_id"] = "SU-C"
    value["decisions"][2].update(
        {
            "ownership_role": "PRIMARY_OWNER",
            "rationale": "SU-C owns its distinct group.",
        }
    )
    _save_decisions(root, value)

    assert any("group PRIMARY_OWNER" in error for error in _errors(root))


def test_ownership_validator_rejects_disallowed_role(tmp_path):
    """Only the three canonical ownership roles are accepted."""
    root = _fixture(tmp_path)
    value = _load_decisions(root)
    value["decisions"][0]["ownership_role"] = "SECONDARY_OWNER"
    _save_decisions(root, value)

    assert any("disallowed ownership_role" in error for error in _errors(root))


def test_ownership_validator_rejects_decision_for_unreviewed_group(tmp_path):
    """Future-batch groups remain absent until their own adjudication batch."""
    root = _fixture(tmp_path)
    value = _load_decisions(root)
    future = copy.deepcopy(value["decisions"][0])
    future.update(
        {
            "candidate_group_id": "G-4",
            "study_unit_id": "SU-G",
            "adjudication_batch": "PRIORITY_A-B02",
        }
    )
    value["decisions"].append(future)
    _save_decisions(root, value)

    assert any("unreviewed batch" in error for error in _errors(root))


def test_ownership_validator_requires_reviewed_counts_to_match_batch(tmp_path):
    """Every group in an adjudicated batch is resolved or explicitly deferred."""
    root = _fixture(tmp_path)
    value = _load_decisions(root)
    value["deferred_groups"] = []
    _save_decisions(root, value)

    assert any("do not reconcile" in error for error in _errors(root))


def test_ownership_audit_builder_rejects_unadjudicated_batch(tmp_path):
    """Building an audit cannot implicitly mark a future batch reviewed."""
    from qbank.global_ownership_decisions import (
        GlobalOwnershipDecisionError,
        build_global_ownership_batch_audit,
    )

    root = _fixture(tmp_path)
    with pytest.raises(GlobalOwnershipDecisionError, match="unreviewed batch"):
        build_global_ownership_batch_audit(root, "PRIORITY_A-B02")


def test_ownership_validator_reports_missing_batch_audit(tmp_path):
    """A reviewed batch without its canonical audit is a validation failure."""
    from qbank.global_ownership_decisions import validate_global_ownership_decisions

    root = _fixture(tmp_path)
    result = validate_global_ownership_decisions(root)

    assert result.status == "FAIL"
    assert any("audit" in error for error in result.errors)
