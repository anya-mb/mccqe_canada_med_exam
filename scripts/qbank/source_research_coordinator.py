"""Deterministic ownership checks for isolated source-research workers."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .source_packet_population import _population_batch_id, _population_packets


@dataclass
class SourceResearchCoordinatorValidation:
    status: str
    checks: dict[str, str] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)


def validate_disjoint_worker_ownership(
    root: Path, batch_ids: list[str], integrated_populations: list[dict[str, Any]]
) -> SourceResearchCoordinatorValidation:
    """Fail closed when worker claims or integrated packet populations overlap."""
    del root
    errors: list[str] = []
    if len(batch_ids) != len(set(batch_ids)):
        errors.append("duplicate pending batch claim")
    integrated_batch_ids = [
        _population_batch_id(population) for population in integrated_populations
    ]
    for batch_id in sorted(set(batch_ids) & {item for item in integrated_batch_ids if item}):
        errors.append(f"already integrated batch: {batch_id}")
    owners: dict[str, str] = {}
    for population in integrated_populations:
        batch_id = _population_batch_id(population) or "UNKNOWN"
        for packet in _population_packets([population]):
            packet_id = packet.get("source_packet_id")
            if not isinstance(packet_id, str):
                continue
            previous = owners.setdefault(packet_id, batch_id)
            if previous != batch_id:
                errors.append(
                    f"integrated populations are not pairwise disjoint: {packet_id}"
                )
    return SourceResearchCoordinatorValidation(
        "FAIL" if errors else "PASS",
        {"DISJOINT_WORKER_OWNERSHIP": "FAIL" if errors else "PASS"},
        errors,
    )
