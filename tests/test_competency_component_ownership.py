"""Tests for the exceptional competency-component ownership extension."""

from __future__ import annotations

import copy
import json
from pathlib import Path

from qbank.competency_component_ownership import (
    AllocationStatus,
    build_competency_component_artifact,
    component_id_for,
    resolve_allocation_status,
    validate_competency_component_ownership,
)


def _write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _fixture(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    units = [
        ("SU-AA-01", "AA.S01", "alpha", 1),
        ("SU-BB-02", "BB.S01", "beta", 1),
        ("SU-CC-03", "CC.S01", "gamma", 1),
        ("SU-DD-04", "DD.S01", "delta", 1),
        ("SU-EE-05", "EE.S01", "epsilon", 0),
    ]
    _write(
        root / "research/scope/master_scope_crosswalk.json",
        {
            "total_study_units": len(units),
            "entries": [
                {
                    "study_unit_id": unit_id,
                    "source_node_ids": [node_id],
                    "testable_competencies": {competency: {}},
                    "classification": "REFERENCE_ONLY" if coverage == 0 else "CORE",
                    "question_planning": {"minimum_question_coverage": coverage},
                }
                for unit_id, node_id, competency, coverage in units
            ],
        },
    )
    _write(
        root / "research/scope/global_ownership_decisions.json",
        {
            "schema_version": "1.0",
            "scope": "GLOBAL_OWNERSHIP_DECISIONS",
            "decisions": [
                {
                    "candidate_group_id": "G-RESOLVED",
                    "study_unit_id": "SU-BB-02",
                    "ownership_role": "PRIMARY_OWNER",
                },
                {
                    "candidate_group_id": "G-RESOLVED",
                    "study_unit_id": "SU-CC-03",
                    "ownership_role": "CROSS_LINK",
                    "primary_owner_study_unit_id": "SU-BB-02",
                },
            ],
            "deferred_groups": [
                {"candidate_group_id": "G-DEFERRED"},
            ],
        },
    )
    _write(
        root / "research/scope/competency_component_ownership.json",
        {"schema_version": "1.1", "scope": "COMPETENCY_COMPONENT_OWNERSHIP", "components": [], "relationships": []},
    )
    return root


def _artifact(root: Path) -> dict:
    return json.loads((root / "research/scope/competency_component_ownership.json").read_text())


def _save(root: Path, value: dict) -> None:
    _write(root / "research/scope/competency_component_ownership.json", value)


def _component(component_id: str, unit: str, node: str, label: str) -> dict:
    return {
        "component_id": component_id,
        "study_unit_id": unit,
        "label": label,
        "component_scope": f"Canonical subset for {label}.",
        "source_basis": {
            "source_node_ids": [node],
            "crosswalk_competency_keys": [label],
            "canonical_decision_ref": "G-DEFERRED",
        },
    }


def _relationship(subject: str, role: str, target: dict | None = None) -> dict:
    result = {
        "candidate_group_id": "G-DEFERRED",
        "subject_component_id": subject,
        "ownership_role": role,
        "rationale": "Canonical deferred adjudication rationale.",
    }
    if target is not None:
        result["primary_owner_ref"] = target
    return result


def _errors(root: Path) -> list[str]:
    return validate_competency_component_ownership(root).errors


def test_component_ids_are_deterministic_and_match_the_parent_prefix():
    assert component_id_for("SU-AA-01", 1) == "SU-AA-01::C01"
    assert component_id_for("SU-AA-01", 12) == "SU-AA-01::C12"


def test_component_validation_rejects_missing_parent_and_invalid_ids(tmp_path):
    root = _fixture(tmp_path)
    value = _artifact(root)
    value["components"] = [_component("bad-id", "SU-NO-99", "AA.S01", "alpha")]
    _save(root, value)

    errors = _errors(root)
    assert any("COMPONENT_PARENT_EXISTS" in error for error in errors)
    assert any("COMPONENT_ID_MATCHES_PARENT" in error for error in errors)


def test_component_validation_rejects_duplicate_ids_and_missing_owner_target(tmp_path):
    root = _fixture(tmp_path)
    value = _artifact(root)
    component = _component("SU-AA-01::C01", "SU-AA-01", "AA.S01", "alpha")
    value["components"] = [component, copy.deepcopy(component)]
    value["relationships"] = [
        _relationship(
            "SU-AA-01::C01", "CROSS_LINK", {"kind": "STUDY_UNIT", "id": "SU-NO-99"}
        )
    ]
    _save(root, value)

    errors = _errors(root)
    assert any("COMPONENT_ID_UNIQUE" in error for error in errors)
    assert any("OWNER_TARGET_EXISTS" in error for error in errors)


def test_component_cross_link_can_directly_target_a_primary_owner_component(tmp_path):
    root = _fixture(tmp_path)
    value = _artifact(root)
    value["components"] = [
        _component("SU-AA-01::C01", "SU-AA-01", "AA.S01", "alpha"),
        _component("SU-DD-04::C01", "SU-DD-04", "DD.S01", "delta"),
    ]
    value["relationships"] = [
        _relationship("SU-AA-01::C01", "CROSS_LINK", {"kind": "COMPONENT", "id": "SU-DD-04::C01"}),
        _relationship("SU-DD-04::C01", "PRIMARY_OWNER"),
    ]
    _save(root, value)

    assert validate_competency_component_ownership(root).status == "PASS"
    assert resolve_allocation_status(root, "SU-AA-01", "SU-AA-01::C01") is AllocationStatus.SUPPRESSED_BY_OWNERSHIP


def test_component_validation_rejects_self_links_cycles_and_cross_link_chains(tmp_path):
    root = _fixture(tmp_path)
    value = _artifact(root)
    value["components"] = [
        _component("SU-AA-01::C01", "SU-AA-01", "AA.S01", "alpha"),
        _component("SU-BB-02::C01", "SU-BB-02", "BB.S01", "beta"),
    ]
    value["relationships"] = [
        _relationship("SU-AA-01::C01", "CROSS_LINK", {"kind": "COMPONENT", "id": "SU-AA-01::C01"}),
        _relationship("SU-BB-02::C01", "CROSS_LINK", {"kind": "COMPONENT", "id": "SU-AA-01::C01"}),
    ]
    _save(root, value)

    errors = _errors(root)
    assert any("NO_COMPONENT_SELF_LINK" in error for error in errors)
    assert any("NO_COMPONENT_CROSSLINK_CHAIN" in error for error in errors)
    assert any("NO_COMPONENT_OWNERSHIP_CYCLE" in error for error in errors)


def test_component_validation_rejects_competing_owner_outcomes(tmp_path):
    root = _fixture(tmp_path)
    value = _artifact(root)
    value["components"] = [_component("SU-AA-01::C01", "SU-AA-01", "AA.S01", "alpha")]
    value["relationships"] = [
        _relationship("SU-AA-01::C01", "CROSS_LINK", {"kind": "STUDY_UNIT", "id": "SU-BB-02"}),
        _relationship("SU-AA-01::C01", "PRIMARY_OWNER"),
    ]
    _save(root, value)

    assert any("NO_COMPETING_COMPONENT_OWNER" in error for error in _errors(root))


def test_component_mode_supports_multiple_owners_and_independent_siblings(tmp_path):
    root = _fixture(tmp_path)
    value = _artifact(root)
    value["components"] = [
        _component("SU-AA-01::C01", "SU-AA-01", "AA.S01", "alpha"),
        _component("SU-AA-01::C02", "SU-AA-01", "AA.S01", "alpha"),
        _component("SU-AA-01::C03", "SU-AA-01", "AA.S01", "alpha"),
    ]
    value["relationships"] = [
        _relationship("SU-AA-01::C01", "CROSS_LINK", {"kind": "STUDY_UNIT", "id": "SU-BB-02"}),
        _relationship("SU-AA-01::C02", "CROSS_LINK", {"kind": "STUDY_UNIT", "id": "SU-DD-04"}),
    ]
    # SU-DD-04 is a direct primary owner in this synthetic deferred projection.
    value["relationships"].append(_relationship("SU-AA-01::C03", "DISTINCT_CONTEXT"))
    decisions = json.loads((root / "research/scope/global_ownership_decisions.json").read_text())
    decisions["decisions"].append({"candidate_group_id": "G-OTHER", "study_unit_id": "SU-DD-04", "ownership_role": "PRIMARY_OWNER"})
    _write(root / "research/scope/global_ownership_decisions.json", decisions)
    _save(root, value)

    assert validate_competency_component_ownership(root).status == "PASS"
    assert resolve_allocation_status(root, "SU-AA-01", "SU-AA-01::C01") is AllocationStatus.SUPPRESSED_BY_OWNERSHIP
    assert resolve_allocation_status(root, "SU-AA-01", "SU-AA-01::C02") is AllocationStatus.SUPPRESSED_BY_OWNERSHIP
    assert resolve_allocation_status(root, "SU-AA-01", "SU-AA-01::C03") is AllocationStatus.ELIGIBLE


def test_whole_unit_mode_preserves_existing_cross_link_and_zero_allocation(tmp_path):
    root = _fixture(tmp_path)

    assert resolve_allocation_status(root, "SU-CC-03") is AllocationStatus.SUPPRESSED_BY_OWNERSHIP
    assert resolve_allocation_status(root, "SU-EE-05") is AllocationStatus.ZERO_BY_SCOPE_METADATA
    assert resolve_allocation_status(root, "SU-BB-02") is AllocationStatus.ELIGIBLE


def test_component_mode_does_not_promote_zero_allocation_or_suppress_independent_sibling(tmp_path):
    root = _fixture(tmp_path)
    value = _artifact(root)
    value["components"] = [
        _component("SU-EE-05::C01", "SU-EE-05", "EE.S01", "epsilon"),
        _component("SU-EE-05::C02", "SU-EE-05", "EE.S01", "epsilon"),
    ]
    value["relationships"] = [
        _relationship("SU-EE-05::C01", "CROSS_LINK", {"kind": "STUDY_UNIT", "id": "SU-BB-02"}),
        _relationship("SU-EE-05::C02", "DISTINCT_CONTEXT"),
    ]
    _save(root, value)

    assert validate_competency_component_ownership(root).status == "PASS"
    assert resolve_allocation_status(root, "SU-EE-05", "SU-EE-05::C01") is AllocationStatus.ZERO_BY_SCOPE_METADATA
    assert resolve_allocation_status(root, "SU-EE-05", "SU-EE-05::C02") is AllocationStatus.ZERO_BY_SCOPE_METADATA


def test_component_mode_rejects_active_whole_unit_relationship_for_the_same_parent(tmp_path):
    root = _fixture(tmp_path)
    value = _artifact(root)
    value["components"] = [_component("SU-CC-03::C01", "SU-CC-03", "CC.S01", "gamma")]
    _save(root, value)

    assert any("NO_WHOLE_UNIT_COMPONENT_CONTRADICTION" in error for error in _errors(root))


def test_component_rebuild_is_byte_identical_and_cli_artifact_is_empty_by_default(tmp_path):
    root = _fixture(tmp_path)
    first = build_competency_component_artifact(root)
    second = build_competency_component_artifact(root)

    assert first == second
    assert (root / "research/scope/competency_component_ownership.json").read_bytes() == json.dumps(second, indent=2, sort_keys=True).encode() + b"\n"
