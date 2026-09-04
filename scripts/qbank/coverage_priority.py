"""Coverage-first priority derived from the frozen allocation, never from volume.

The 6,086 allocation is read here as a curriculum-density record: how much
material each address holds, and how much attention the planning layer judged it
to need.  Nothing in this module produces a target, a floor, or a shortfall, and
the frozen artifact is opened read-only.

A topic is covered when its important learner decisions are covered, not when a
number of items exists.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .errors import QbankError
from .paths import resolve_root_path
from .qgen_profiles import assert_no_quota_shaped_fields


class CoveragePriorityError(QbankError):
    """The frozen allocation cannot support a coverage-priority derivation."""


PRIORITY_CLASSES = ("CORE", "IMPORTANT", "SUPPORTING", "NOT_IN_SCOPE")

DEPTH_TO_CLASS = {
    "CORE_ACTION": "CORE",
    "RECOGNIZE_AND_ACT": "IMPORTANT",
    "RECOGNIZE": "SUPPORTING",
}

PRIORITY_CLASS_BASES = ("DEPTH_DERIVED", "OBJECTIVE_REACHABILITY_PROMOTION", "NOT_ELIGIBLE")

# CORE raises effort and ordering priority. It never relaxes an invariant and it
# never obliges the pipeline to emit an item.
GENERATION_POLICIES = {
    "CORE": "SERIOUS_ATTEMPT_PER_IMPORTANT_LEARNER_DECISION",
    "IMPORTANT": "GENERATE_WHEN_STRONG_AND_NON_REDUNDANT",
    "SUPPORTING": "OPTIONAL_WHEN_CHEAP_AND_NON_REDUNDANT",
    "NOT_IN_SCOPE": "NEVER",
}

DISCIPLINE_PROFILE_IDS = {
    "MED": "MEDICINE",
    "PED": "PEDIATRICS",
    "OBGYN": "OBGYN",
    "SURG": "SURGERY",
    "PSY": "PSYCHIATRY",
    "PHELO": "PHELO",
}


def load_frozen_allocation(root: Path) -> list[dict[str, Any]]:
    """Read the frozen final allocation without mutating it."""
    path = resolve_root_path(Path(root).resolve(), "research/scope/final_question_allocation.json")
    if not path.is_file():
        raise CoveragePriorityError("frozen final question allocation is unavailable")
    document = json.loads(path.read_text())
    addresses = document.get("allocation_addresses")
    if not isinstance(addresses, list) or not addresses:
        raise CoveragePriorityError("frozen allocation carries no addresses")
    return addresses


def derive_priority_classes(addresses: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Derive the priority class of every allocation address.

    The class comes from the competency depth the curriculum already adjudicated
    and froze, so the priority model adds no new judgement and estimates no exam
    frequency.  A non-eligible address keeps an opportunity budget of zero:
    zero-scope precedence and ownership suppression survive the reinterpretation
    unchanged.
    """
    rows: dict[str, dict[str, Any]] = {}
    for address in addresses:
        address_id = address.get("allocation_address_id")
        if not isinstance(address_id, str) or not address_id:
            raise CoveragePriorityError("allocation address is missing its id")
        if address_id in rows:
            raise CoveragePriorityError(f"duplicate allocation address: {address_id}")
        eligible = address.get("allocation_status") == "ELIGIBLE"
        depth = address.get("depth")
        if not eligible:
            priority_class, basis = "NOT_IN_SCOPE", "NOT_ELIGIBLE"
        elif depth in DEPTH_TO_CLASS:
            priority_class, basis = DEPTH_TO_CLASS[depth], "DEPTH_DERIVED"
        else:
            priority_class, basis = "NOT_IN_SCOPE", "NOT_ELIGIBLE"
        rows[address_id] = {
            "allocation_address_id": address_id,
            "study_unit_id": address.get("study_unit_id"),
            "discipline": address.get("discipline"),
            "discipline_profile_id": DISCIPLINE_PROFILE_IDS.get(address.get("discipline")),
            "chapter": address.get("chapter"),
            "mcc_objective_ids": list(address.get("mcc_objective_ids", [])),
            "depth": depth,
            "coverage_weight": address.get("coverage_weight"),
            "priority_class": priority_class,
            "priority_class_basis": basis,
            # An upper bound on how many distinct opportunities may be opened here.
            # It is never a floor and nothing compares an accepted count against it.
            "maximum_opportunities": int(address.get("final_question_count", 0))
            if eligible
            else 0,
            # The planning layer's judgement that this address needs coverage. It
            # orders work; it is not a threshold to satisfy.
            "curriculum_attention_signal": int(address.get("effective_minimum", 0)),
            "generation_policy": GENERATION_POLICIES[priority_class],
        }
    return rows


def apply_objective_reachability_promotion(
    rows: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    """Promote one address per MCC objective that no CORE address reaches.

    Without this, an objective reachable only through IMPORTANT or SUPPORTING
    addresses could receive nothing while the bank still looked healthy. The
    promotion is deterministic: highest coverage weight, then largest density,
    then address id.
    """
    eligible = [row for row in rows.values() if row["priority_class"] != "NOT_IN_SCOPE"]
    covered = {
        objective
        for row in eligible
        if row["priority_class"] == "CORE"
        for objective in row["mcc_objective_ids"]
    }
    mapped = {objective for row in eligible for objective in row["mcc_objective_ids"]}
    orphans = sorted(mapped - covered)
    promoted: dict[str, list[str]] = {}
    for objective in orphans:
        candidates = sorted(
            (row for row in eligible if objective in row["mcc_objective_ids"]),
            key=lambda row: (
                -int(row["coverage_weight"] or 0),
                -int(row["maximum_opportunities"] or 0),
                row["allocation_address_id"],
            ),
        )
        if not candidates:  # pragma: no cover - orphans are drawn from these rows
            raise CoveragePriorityError(f"objective {objective} has no eligible address")
        winner = candidates[0]
        promoted.setdefault(winner["allocation_address_id"], []).append(objective)
    for address_id, objectives in promoted.items():
        row = rows[address_id]
        row["priority_class"] = "CORE"
        row["priority_class_basis"] = "OBJECTIVE_REACHABILITY_PROMOTION"
        row["generation_policy"] = GENERATION_POLICIES["CORE"]
        row["promoted_for_objectives"] = sorted(objectives)
    still_orphaned = sorted(
        objective
        for objective in mapped
        if objective
        not in {
            value
            for row in rows.values()
            if row["priority_class"] == "CORE"
            for value in row["mcc_objective_ids"]
        }
    )
    if still_orphaned:
        raise CoveragePriorityError(
            f"objectives remain unreachable from CORE after promotion: {still_orphaned}"
        )
    return {
        "orphan_objectives": orphans,
        "promoted_address_ids": sorted(promoted),
    }


def build_coverage_priority_model(root: Path) -> dict[str, Any]:
    """Build the whole deterministic coverage-priority model."""
    addresses = load_frozen_allocation(root)
    rows = derive_priority_classes(addresses)
    promotion = apply_objective_reachability_promotion(rows)
    counts = {
        priority_class: sum(
            1 for row in rows.values() if row["priority_class"] == priority_class
        )
        for priority_class in PRIORITY_CLASSES
    }
    model = {
        "schema_version": "1.0",
        "scope": "QGEN_COVERAGE_PRIORITY_MODEL",
        "address_count": len(rows),
        "priority_class_counts": counts,
        "orphan_objectives": promotion["orphan_objectives"],
        "promoted_address_ids": promotion["promoted_address_ids"],
        "addresses": [rows[key] for key in sorted(rows)],
    }
    assert_no_quota_shaped_fields(model, label="coverage priority model")
    return model
