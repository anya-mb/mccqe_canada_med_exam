"""Freeze and verify the production-like fresh operational Holdout-18.

This module is deliberately limited to outcome-blind roster selection and
content-addressed freezing. Clinical authoring and review remain data work.
"""

from __future__ import annotations

from collections import defaultdict
import hashlib
import json
import re
from pathlib import Path
from typing import Any


DISCIPLINES = ("MED", "PED", "OBGYN", "SURG", "PSY", "PHELO")
INVENTORY = Path("research/qgen/readiness/future_untouched_holdout_eligibility.json")
HOLDOUT = Path("research/qgen/holdout")
ROSTER = HOLDOUT / "fresh_operational_holdout_18_opportunities.json"
FREEZE = HOLDOUT / "fresh_operational_holdout_18_architecture_freeze.json"


class HoldoutIntegrityError(ValueError):
    """A frozen roster, architecture component, or historical artifact drifted."""


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def content_sha256(value: dict[str, Any]) -> str:
    body = {key: item for key, item in value.items() if key != "content_sha256"}
    payload = json.dumps(
        body, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    ).encode()
    return hashlib.sha256(payload).hexdigest()


def _topic_family(crosswalk: dict[str, Any]) -> str:
    nodes = crosswalk.get("source_node_ids") or []
    if nodes:
        pieces = re.split(r"[.]", str(nodes[0]))
        return ".".join(pieces[:2]) if len(pieces) > 1 else pieces[0]
    path = crosswalk.get("source_hierarchy_path") or []
    if path:
        pieces = str(path[0]).split()[0].split(".")
        return ".".join(pieces[:2])
    return str(crosswalk.get("chapter_code") or "UNKNOWN")


def _candidate_score(row: dict[str, Any]) -> tuple[Any, ...]:
    return (
        0 if row.get("source_availability") == "CURRENT_REPOSITORY_PACKET_READY" else 1,
        {"CORE": 0, "IMPORTANT": 1, "SUPPORTING": 2}.get(row.get("priority"), 9),
        -len(row.get("mcc_objective_ids") or []),
        (row.get("allocation_address_ids") or [row["study_unit_id"]])[0],
    )


def select_holdout(root: Path) -> dict[str, Any]:
    """Choose three taxonomy-distinct untouched units per discipline."""
    root = Path(root).resolve()
    inventory = _read(root / INVENTORY)
    if inventory.get("future_holdout_selected") is not False:
        raise HoldoutIntegrityError("NEXT_HOLDOUT_ALREADY_CONSUMED")
    if inventory.get("seed_availability_inspected") is not False:
        raise HoldoutIntegrityError("SEED_SIGNAL_PRESENT_IN_SELECTION_INVENTORY")
    if inventory.get("contrast_supply_inspected") is not False:
        raise HoldoutIntegrityError("CONTRAST_SIGNAL_PRESENT_IN_SELECTION_INVENTORY")
    if inventory.get("content_sha256") != content_sha256(inventory):
        raise HoldoutIntegrityError("ELIGIBILITY_INVENTORY_HASH_MISMATCH")

    crosswalk_rows = _read(root / "research/scope/master_scope_crosswalk.json")["entries"]
    crosswalk = {row["study_unit_id"]: row for row in crosswalk_rows}
    selected: list[dict[str, Any]] = []
    for discipline in DISCIPLINES:
        groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for source in inventory["units"]:
            if source["discipline"] != discipline:
                continue
            canonical = crosswalk[source["study_unit_id"]]
            if not canonical.get("testable_competencies"):
                continue
            row = {
                "discipline": discipline,
                "study_unit_id": source["study_unit_id"],
                "study_unit": source["study_unit"],
                "allocation_address_ids": source["allocation_address_ids"],
                "mcc_objective_ids": source["mcc_objective_ids"],
                "priority": source["priority"],
                "source_availability": source["source_availability"],
                "topic_family": _topic_family(canonical),
            }
            groups[row["topic_family"]].append(row)
        for rows in groups.values():
            rows.sort(key=_candidate_score)
        family_order = sorted(groups, key=lambda name: (_candidate_score(groups[name][0]), name))
        if len(family_order) < 3:
            raise HoldoutIntegrityError(f"INSUFFICIENT_TOPIC_DIVERSITY: {discipline}")
        for ordinal, family in enumerate(family_order[:3], start=1):
            selected.append({
                "opportunity_id": f"FOH18-{discipline}-{ordinal:02d}",
                **groups[family][0],
            })

    waves = []
    for ordinal in range(3):
        waves.append({
            "wave": ordinal + 1,
            "opportunity_ids": [
                next(
                    row["opportunity_id"]
                    for row in selected
                    if row["discipline"] == discipline
                    and row["opportunity_id"].endswith(f"-{ordinal + 1:02d}")
                )
                for discipline in DISCIPLINES
            ],
        })
    roster = {
        "schema_version": "1.0",
        "scope": "QGEN_FRESH_OPERATIONAL_HOLDOUT_18_OPPORTUNITY_FREEZE",
        "source_inventory_path": INVENTORY.as_posix(),
        "source_inventory_file_sha256": _file_sha256(root / INVENTORY),
        "source_inventory_content_sha256": inventory["content_sha256"],
        "selection_rule": (
            "Within each discipline, group by canonical source-node topic family. "
            "Rank each family by packet-ready before targeted research, CORE before "
            "IMPORTANT before SUPPORTING, more MCC objectives before fewer, then "
            "allocation-address ID; take the best row from the first three families."
        ),
        "selection_uses_generation_outcomes": False,
        "selection_inspected_seed_or_contrast_supply": False,
        "opportunities": selected,
        "waves": waves,
    }
    roster["content_sha256"] = content_sha256(roster)
    return roster


def _architecture_paths(root: Path) -> list[Path]:
    paths = list((root / "scripts/qbank").glob("*.py"))
    paths.extend((root / "schemas").glob("*.json"))
    paths.extend([
        root / "research/qgen/onboarding/profile_snapshot_v2.json",
        root / "research/qgen/onboarding/feature_anchor_snapshot_v6.json",
        root / "research/qgen/onboarding/v6_clinical_contrast_relations_v2.json",
    ])
    return sorted({path.resolve() for path in paths if path.is_file()})


def _historical_paths(root: Path) -> list[Path]:
    prefix = "fresh_operational_holdout_18"
    return sorted(
        path.resolve()
        for path in (root / HOLDOUT).rglob("*.json")
        if not path.name.startswith(prefix)
    )


def build_architecture_freeze(root: Path, roster: dict[str, Any]) -> dict[str, Any]:
    root = Path(root).resolve()
    architecture_pins = {
        path.relative_to(root).as_posix(): _file_sha256(path)
        for path in _architecture_paths(root)
    }
    historical_pins = {
        path.relative_to(root).as_posix(): _file_sha256(path)
        for path in _historical_paths(root)
    }
    freeze = {
        "schema_version": "1.0",
        "scope": "QGEN_FRESH_OPERATIONAL_HOLDOUT_18_ARCHITECTURE_FREEZE",
        "roster_content_sha256": roster["content_sha256"],
        "architecture_pins": architecture_pins,
        "historical_artifact_pins": historical_pins,
        "architecture_change_after_freeze_allowed": False,
        "data_onboarding_through_frozen_contracts_allowed": True,
    }
    freeze["holdout_architecture_freeze_sha256"] = content_sha256(freeze)
    freeze["content_sha256"] = content_sha256(freeze)
    return freeze


def verify_freeze(
    root: Path, roster: dict[str, Any], freeze: dict[str, Any]
) -> dict[str, Any]:
    root = Path(root).resolve()
    if roster.get("content_sha256") != content_sha256(roster):
        raise HoldoutIntegrityError("ROSTER_HASH_DRIFT")
    if freeze.get("roster_content_sha256") != roster["content_sha256"]:
        raise HoldoutIntegrityError("ROSTER_PIN_DRIFT")
    for relative, expected in freeze.get("architecture_pins", {}).items():
        if _file_sha256(root / relative) != expected:
            raise HoldoutIntegrityError(f"ARCHITECTURE_HASH_DRIFT: {relative}")
    for relative, expected in freeze.get("historical_artifact_pins", {}).items():
        if _file_sha256(root / relative) != expected:
            raise HoldoutIntegrityError(f"HISTORICAL_ARTIFACT_HASH_DRIFT: {relative}")
    return {
        "verdict": "PASS",
        "roster_unchanged": True,
        "architecture_unchanged": True,
        "historical_artifacts_unchanged": True,
    }


def write_freeze_artifacts(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    root = Path(root).resolve()
    roster = select_holdout(root)
    freeze = build_architecture_freeze(root, roster)
    for relative, value in ((ROSTER, roster), (FREEZE, freeze)):
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")
    return roster, freeze
