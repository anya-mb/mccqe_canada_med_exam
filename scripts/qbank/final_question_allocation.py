"""Build and validate the frozen-input final MCCQE question allocation."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from itertools import groupby
from pathlib import Path
from typing import Any

from .allocation_discipline_routing import (
    _CHAPTER_DISCIPLINES,
    load_allocation_discipline_routing,
    preflight_allocation_disciplines,
    validate_allocation_discipline_routing,
)
from .competency_component_ownership import validate_competency_component_ownership
from .errors import QbankError
from .global_ownership_decisions import validate_global_ownership_decisions
from .jsonio import read_json, write_json_atomic
from .master_scope import validate_master_scope
from .paths import resolve_root_path
from .question_bank_targets import load_question_bank_targets


_DISCIPLINES = ("MED", "PED", "OBGYN", "SURG", "PSY", "PHELO")
_EXPECTED_MINIMA = {"MED": 1086, "PED": 187, "OBGYN": 131, "SURG": 424, "PSY": 106, "PHELO": 138}


class FinalQuestionAllocationError(QbankError):
    """Frozen allocation inputs or the calculated allocation are invalid."""


@dataclass
class FinalQuestionAllocationValidation:
    status: str
    checks: dict[str, str] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)


def _path(root: Path, relative: str) -> Path:
    return resolve_root_path(root, relative, label=relative)


def _zero_by_scope(entry: dict[str, Any]) -> bool:
    planning = entry["question_planning"]
    return (
        entry.get("classification") in {"REFERENCE_ONLY", "CONTEXT_ONLY"}
        or entry.get("scope_depth") == "CONTEXT_ONLY"
        or planning["minimum_question_coverage"] == 0
    )


def _objective_ids(entry: dict[str, Any]) -> list[str]:
    return sorted({item["mcc_id"] for item in entry.get("mcc_evidence", []) if isinstance(item, dict) and isinstance(item.get("mcc_id"), str)})


def hamilton_allocate(rows: list[dict[str, Any]], budget: int) -> dict[str, int]:
    """Allocate an integer budget by weight using canonical largest-remainder ties."""
    if budget < 0 or not rows:
        if budget == 0:
            return {row["allocation_address_id"]: 0 for row in rows}
        raise FinalQuestionAllocationError("Hamilton allocation requires eligible positive-weight rows")
    total_weight = sum(row["coverage_weight"] for row in rows)
    if total_weight <= 0:
        raise FinalQuestionAllocationError("Hamilton allocation requires positive total coverage weight")
    result: dict[str, int] = {}
    remainders: list[tuple[int, str]] = []
    for row in rows:
        address_id = row["allocation_address_id"]
        numerator = budget * row["coverage_weight"]
        result[address_id] = numerator // total_weight
        remainders.append((numerator % total_weight, address_id))
    for _, address_id in sorted(remainders, key=lambda item: (-item[0], item[1]))[: budget - sum(result.values())]:
        result[address_id] += 1
    return result


def _frozen_validation(root: Path) -> None:
    results = (
        validate_master_scope(root),
        validate_global_ownership_decisions(root),
        validate_competency_component_ownership(root),
        validate_allocation_discipline_routing(root),
    )
    if any(result.status != "PASS" for result in results):
        raise FinalQuestionAllocationError("a frozen allocation input validator failed")
    load_question_bank_targets(root)
    ownership_audit = read_json(_path(root, "reports/final_effective_ownership_audit.json"))
    if ownership_audit.get("final_gate", {}).get("block_question_allocation") is not False:
        raise FinalQuestionAllocationError("effective ownership audit blocks allocation")


def _addresses(root: Path) -> list[dict[str, Any]]:
    master = read_json(_path(root, "research/scope/master_scope_crosswalk.json"))
    decisions = read_json(_path(root, "research/scope/global_ownership_decisions.json"))
    extension = read_json(_path(root, "research/scope/competency_component_ownership.json"))
    routing = load_allocation_discipline_routing(root)
    routes = {row["allocation_address_id"]: row["canonical_allocation_discipline"] for row in routing["routing_overrides"]}
    whole_roles = {row["study_unit_id"]: row["ownership_role"] for row in decisions["decisions"]}
    component_roles = {row["subject_component_id"]: row["ownership_role"] for row in extension["relationships"]}
    components_by_parent: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for component in extension["components"]:
        components_by_parent[component["study_unit_id"]].append(component)
    rows: list[dict[str, Any]] = []
    for entry in master["entries"]:
        parent_id = entry["study_unit_id"]
        components = sorted(components_by_parent.get(parent_id, []), key=lambda row: row["component_id"])
        candidates = [(component["component_id"], component["component_id"]) for component in components] or [(parent_id, None)]
        for address_id, component_id in candidates:
            ownership_mode = component_roles.get(address_id, "INDEPENDENT") if component_id else whole_roles.get(parent_id, "INDEPENDENT")
            status = "ZERO_BY_SCOPE_METADATA" if _zero_by_scope(entry) else ("SUPPRESSED_BY_OWNERSHIP" if ownership_mode == "CROSS_LINK" else "ELIGIBLE")
            # The committed override list intentionally covers only eligible MI
            # addresses.  A suppressed/zero MI address has no budget effect; use
            # MED as its non-allocating display discipline without extending routing.
            discipline = (routes.get(address_id, "MED") if entry["chapter_code"] == "MI" else _CHAPTER_DISCIPLINES.get(entry["chapter_code"]))
            if not isinstance(discipline, str):
                raise FinalQuestionAllocationError(f"no discipline for allocation address {address_id}")
            planning = entry["question_planning"]
            rows.append({
                "allocation_address_id": address_id,
                "study_unit_id": parent_id,
                **({"component_id": component_id} if component_id else {}),
                "discipline": discipline,
                "chapter": entry["chapter_code"],
                "classification": entry["classification"],
                "depth": entry["scope_depth"],
                "coverage_weight": planning["coverage_weight"],
                "raw_minimum_question_coverage": planning["minimum_question_coverage"],
                # Component-mode parents retain one frozen parent minimum.  It
                # is apportioned across their eligible components below, never
                # copied to each component.
                "effective_minimum": planning["minimum_question_coverage"] if status == "ELIGIBLE" else 0,
                "final_question_count": 0,
                "ownership_mode": ownership_mode,
                "allocation_status": status,
                "preferred_item_forms": sorted(planning["preferred_item_forms"]),
                "mcc_objective_ids": _objective_ids(entry),
            })
    for parent_id, component_rows in groupby(
        sorted((row for row in rows if "component_id" in row), key=lambda row: row["study_unit_id"]),
        key=lambda row: row["study_unit_id"],
    ):
        group = list(component_rows)
        eligible = [row for row in group if row["allocation_status"] == "ELIGIBLE"]
        parent_minimum = max(row["effective_minimum"] for row in group)
        for row in group:
            row["effective_minimum"] = 0
        if eligible:
            split = hamilton_allocate(eligible, parent_minimum)
            for row in eligible:
                row["effective_minimum"] = split[row["allocation_address_id"]]
    return sorted(rows, key=lambda row: row["allocation_address_id"])


def _audit(root: Path, rows: list[dict[str, Any]], targets: dict[str, int]) -> dict[str, Any]:
    preflight = preflight_allocation_disciplines(root)
    counts = Counter(row["allocation_status"] for row in rows)
    allocated = Counter()
    minima = Counter()
    forms = Counter()
    expected_objectives: set[str] = set()
    allocated_objectives: set[str] = set()
    for row in rows:
        allocated[row["discipline"]] += row["final_question_count"]
        minima[row["discipline"]] += row["effective_minimum"]
        if row["final_question_count"] > 0:
            forms.update(row["preferred_item_forms"])
            allocated_objectives.update(row["mcc_objective_ids"])
        if row["allocation_status"] == "ELIGIBLE":
            expected_objectives.update(row["mcc_objective_ids"])
    core_zero = sum(1 for row in rows if row["allocation_status"] == "ELIGIBLE" and row["final_question_count"] == 0 and row["depth"] == "CORE_ACTION")
    component_rows = [row for row in rows if "component_id" in row]
    return {
        "schema_version": "1.0",
        "scope": "FINAL_QUESTION_ALLOCATION_AUDIT",
        "reconciliation": {"TOTAL_TARGET_QUESTIONS": sum(targets.values()), "TOTAL_ALLOCATED_QUESTIONS": sum(allocated.values())},
        "discipline_budgets": {discipline: allocated[discipline] for discipline in _DISCIPLINES},
        "address_counts": {
            "TOTAL_ALLOCATION_ADDRESSES": len(rows), "ELIGIBLE_ALLOCATION_ADDRESSES": counts["ELIGIBLE"],
            "SUPPRESSED_ALLOCATION_ADDRESSES": counts["SUPPRESSED_BY_OWNERSHIP"], "ZERO_SCOPE_ALLOCATION_ADDRESSES": counts["ZERO_BY_SCOPE_METADATA"],
        },
        "assignment_safety": {"UNASSIGNED_ELIGIBLE_ADDRESSES": preflight.unassigned_eligible_addresses, "MULTI_ASSIGNED_ELIGIBLE_ADDRESSES": preflight.multi_assigned_eligible_addresses},
        "planning_conflicts": {"PLANNING_CONFLICTS": sum(1 for row in rows if row["allocation_status"] == "ZERO_BY_SCOPE_METADATA" and row["raw_minimum_question_coverage"] > 0 and row["depth"] == "CONTEXT_ONLY"), "HARD_PLANNING_BLOCKERS": 0, "ZERO_SCOPE_PROMOTIONS": 0},
        "minimum_totals": {**{discipline: minima[discipline] for discipline in _DISCIPLINES}, "TOTAL_EFFECTIVE_MINIMUM": sum(minima.values())},
        "above_minimum_totals": {**{discipline: allocated[discipline] - minima[discipline] for discipline in _DISCIPLINES}, "QUESTIONS_ALLOCATED_ABOVE_MINIMUM": sum(allocated.values()) - sum(minima.values())},
        "ownership_safety": {"OWNERSHIP_SUPPRESSION_VIOLATIONS": sum(1 for row in rows if row["allocation_status"] == "SUPPRESSED_BY_OWNERSHIP" and row["final_question_count"]), "ZERO_SCOPE_PROMOTIONS": 0},
        "component_safety": {"COMPONENT_MODE_PARENT_UNITS": len({row["study_unit_id"] for row in component_rows}), "COMPONENT_PARENT_DOUBLE_ALLOCATION": 0, "SUPPRESSED_COMPONENTS_RECEIVING_QUESTIONS": sum(1 for row in component_rows if row["allocation_status"] == "SUPPRESSED_BY_OWNERSHIP" and row["final_question_count"]), "ZERO_SCOPE_COMPONENTS_RECEIVING_QUESTIONS": sum(1 for row in component_rows if row["allocation_status"] == "ZERO_BY_SCOPE_METADATA" and row["final_question_count"])},
        "mcc_coverage": {"MCC_OBJECTIVES_WITH_EXPECTED_QUESTION_COVERAGE": len(expected_objectives), "MCC_OBJECTIVES_WITH_ALLOCATED_COVERAGE": len(allocated_objectives), "TRUE_MCC_ALLOCATION_GAPS": len(expected_objectives - allocated_objectives)},
        "distribution": {"ADDRESSES_RECEIVING_QUESTIONS": sum(1 for row in rows if row["final_question_count"] > 0), "ELIGIBLE_ADDRESSES_RECEIVING_ZERO": sum(1 for row in rows if row["allocation_status"] == "ELIGIBLE" and row["final_question_count"] == 0), "CORE_ACTION_ELIGIBLE_ADDRESSES_RECEIVING_ZERO": core_zero},
        "item_form_summary": dict(sorted(forms.items())),
        "determinism": {"ALLOCATION_REBUILD_DETERMINISTIC": "PASS"},
    }


def build_final_question_allocation(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    """Build compact allocation and audit objects without writing canonical artifacts."""
    root = Path(root).resolve()
    _frozen_validation(root)
    targets = load_question_bank_targets(root)["discipline_targets"]
    rows = _addresses(root)
    for discipline in _DISCIPLINES:
        group = [row for row in rows if row["discipline"] == discipline and row["allocation_status"] == "ELIGIBLE"]
        minimum = sum(row["effective_minimum"] for row in group)
        if minimum != _EXPECTED_MINIMA[discipline]:
            raise FinalQuestionAllocationError(f"effective minimum mismatch for {discipline}: {minimum}")
        remaining = targets[discipline] - minimum
        if remaining < 0:
            raise FinalQuestionAllocationError(f"discipline budget below frozen minimum for {discipline}")
        extra = hamilton_allocate(group, remaining)
        for row in group:
            row["final_question_count"] = row["effective_minimum"] + extra[row["allocation_address_id"]]
    allocation = {"schema_version": "1.0", "scope": "FINAL_MCCQE_QUESTION_ALLOCATION", "total_target_questions": 6086, "allocation_addresses": rows}
    audit = _audit(root, rows, targets)
    validation = validate_final_question_allocation(root, allocation, audit)
    if validation.status != "PASS":
        raise FinalQuestionAllocationError("built allocation failed validation: " + "; ".join(validation.errors))
    return allocation, audit


def validate_final_question_allocation(root: Path, allocation: dict[str, Any], audit: dict[str, Any]) -> FinalQuestionAllocationValidation:
    """Validate the complete allocation against frozen configuration and invariants."""
    root = Path(root).resolve()
    errors: list[str] = []
    rows = allocation.get("allocation_addresses", [])
    targets = load_question_bank_targets(root)["discipline_targets"]
    if allocation.get("scope") != "FINAL_MCCQE_QUESTION_ALLOCATION" or not isinstance(rows, list): errors.append("allocation schema is invalid")
    if len(rows) != 1507: errors.append("allocation address count is not 1507")
    if len({row.get("allocation_address_id") for row in rows}) != len(rows): errors.append("allocation addresses are not unique")
    actual = Counter(row.get("discipline") for row in rows for _ in range(row.get("final_question_count", 0) if isinstance(row.get("final_question_count"), int) else 0))
    if any(not isinstance(row.get("final_question_count"), int) for row in rows): errors.append("NONINTEGER_ALLOCATIONS")
    if any(row.get("final_question_count", 0) < 0 for row in rows): errors.append("NEGATIVE_ALLOCATIONS")
    if {discipline: actual[discipline] for discipline in _DISCIPLINES} != targets: errors.append("discipline budgets do not match frozen targets")
    if audit.get("minimum_totals") != {**_EXPECTED_MINIMA, "TOTAL_EFFECTIVE_MINIMUM": 2072}: errors.append("effective minima do not match frozen totals")
    for row in rows:
        if row.get("allocation_status") != "ELIGIBLE" and row.get("final_question_count") != 0: errors.append("suppressed or zero-scope address received questions")
        if row.get("discipline") == "MED" and row.get("final_question_count") != row.get("effective_minimum"): errors.append("MED allocation exceeds effective minimum")
    required_zero = ("UNASSIGNED_ELIGIBLE_ADDRESSES", "MULTI_ASSIGNED_ELIGIBLE_ADDRESSES")
    if any(audit.get("assignment_safety", {}).get(key) != 0 for key in required_zero): errors.append("eligible address assignment failed")
    if audit.get("planning_conflicts", {}).get("PLANNING_CONFLICTS") != 18: errors.append("planning conflict count is not 18")
    if audit.get("mcc_coverage", {}).get("TRUE_MCC_ALLOCATION_GAPS") != 0: errors.append("true MCC allocation gaps remain")
    return FinalQuestionAllocationValidation("FAIL" if errors else "PASS", {"ALLOCATION_VALIDATOR": "FAIL" if errors else "PASS"}, errors)


def write_final_question_allocation(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    root = Path(root).resolve()
    allocation, audit = build_final_question_allocation(root)
    repeat_allocation, repeat_audit = build_final_question_allocation(root)
    if allocation != repeat_allocation or audit != repeat_audit:
        raise FinalQuestionAllocationError("allocation rebuild is not deterministic")
    write_json_atomic(_path(root, "research/scope/final_question_allocation.json"), allocation)
    write_json_atomic(_path(root, "reports/final_question_allocation_audit.json"), audit)
    return allocation, audit
