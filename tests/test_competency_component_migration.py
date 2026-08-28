"""Regression coverage for the committed competency-component migration."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from qbank.competency_component_ownership import (
    AllocationStatus,
    materialize_competency_component_migration,
    resolve_allocation_status,
)


ROOT = Path(__file__).resolve().parents[1]
SPEC_PATH = ROOT / "research/scope/competency_component_migration_spec.json"
DECISIONS_PATH = ROOT / "research/scope/global_ownership_decisions.json"


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_committed_migration_materializes_the_exact_component_projection(tmp_path):
    """Catches omitted/altered spec rows and ownership target transformations."""
    root = tmp_path / "project"
    for relative in (
        "research/scope/master_scope_crosswalk.json",
        "research/scope/global_ownership_decisions.json",
        "research/scope/competency_component_migration_spec.json",
        "reports/global_ownership_aggregate_audit.json",
    ):
        source = ROOT / relative
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(source.read_bytes())
    empty = {
        "schema_version": "1.1",
        "scope": "COMPETENCY_COMPONENT_OWNERSHIP",
        "components": [],
        "relationships": [],
    }
    component_path = root / "research/scope/competency_component_ownership.json"
    component_path.write_text(json.dumps(empty, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    before_decisions = (root / "research/scope/global_ownership_decisions.json").read_bytes()

    result = materialize_competency_component_migration(root)
    artifact = _read(component_path)

    assert len(artifact["components"]) == 50
    assert len(artifact["relationships"]) == 43
    assert len({item["study_unit_id"] for item in artifact["components"]}) == 30
    assert result.effective_ownership_resolved_groups == 106
    assert result.effective_ownership_unresolved_groups == 0
    assert result.component_resolved_deferred_groups == 13
    assert result.component_crosslink_chains == 0
    assert result.component_ownership_cycles == 0
    assert result.invalid_component_owner_targets == 0
    assert result.unexpected_component_parent_units == 0
    assert result.zero_allocation_promotions == 0
    assert (root / "research/scope/global_ownership_decisions.json").read_bytes() == before_decisions


def test_committed_migration_preserves_exact_real_edge_cases_and_is_deterministic(tmp_path):
    """Catches loss of component-mode cases or nondeterministic rebuild output."""
    root = tmp_path / "project"
    for relative in (
        "research/scope/master_scope_crosswalk.json",
        "research/scope/global_ownership_decisions.json",
        "research/scope/competency_component_migration_spec.json",
        "reports/global_ownership_aggregate_audit.json",
    ):
        source = ROOT / relative
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(source.read_bytes())
    component_path = root / "research/scope/competency_component_ownership.json"
    component_path.write_text(
        json.dumps({"schema_version": "1.1", "scope": "COMPETENCY_COMPONENT_OWNERSHIP", "components": [], "relationships": []}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    first = materialize_competency_component_migration(root)
    first_bytes = component_path.read_bytes()
    second = materialize_competency_component_migration(root, allow_existing_projection=True)

    artifact = _read(component_path)
    relationships = {item["subject_component_id"]: item for item in artifact["relationships"]}
    assert first_bytes == component_path.read_bytes()
    assert first.deterministic_rebuild is True
    assert second.deterministic_rebuild is True
    assert relationships["SU-ER-29::C01"]["primary_owner_ref"] == {"kind": "COMPONENT", "id": "SU-OT-33::C01"}
    assert relationships["SU-C-30::C01"]["ownership_role"] == "CROSS_LINK"
    assert relationships["SU-C-30::C02"]["ownership_role"] == "DISTINCT_CONTEXT"
    assert relationships["SU-ID-08::C01"]["ownership_role"] == "PRIMARY_OWNER"
    assert relationships["SU-ID-08::C02"]["ownership_role"] == "DISTINCT_CONTEXT"
    audit = _read(root / "reports/competency_component_migration_audit.json")
    prior_case = next(item for item in audit["migration_groups"] if item["candidate_group_id"] == "GOC-01b92489a96f")
    assert prior_case["component_ids_materialized"] == []
    assert prior_case["effective_resolution_status"] == "RESOLVED_BY_COMPONENT_EXTENSION"
    assert resolve_allocation_status(root, "SU-NS-10", "SU-NS-10::C01") is AllocationStatus.ZERO_BY_SCOPE_METADATA
    assert hashlib.sha256(component_path.read_bytes()).hexdigest() == hashlib.sha256(first_bytes).hexdigest()
