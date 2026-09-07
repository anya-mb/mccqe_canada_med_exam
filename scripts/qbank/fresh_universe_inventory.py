"""Which study units question generation can actually use, and what stops the rest.

Chapter membership is not readiness. An address can sit in a chapter the
curriculum calls CORE, carry a researched source packet and still be unusable,
because a question needs four things the packet does not supply: a learner
decision somebody declared, a stem-feature vocabulary its study unit owns, a
curated contrast supply with independent seed review, and evidence its
competitors' correctness conditions can be read from.

Every address is therefore classified by its *earliest* missing layer rather than
by the most interesting one. An address with no MCC objective is reported at the
mapping layer even though it also has no seed pack, because researching a seed
pack for it would be wasted work. The classes are disjoint and the blocking
layers are ordered, so the counts add up to the address count and the report can
be read as a queue.

Nothing here proposes work, ranks a candidate or compares a count against a
target.
"""

from __future__ import annotations

from typing import Any

from .errors import QbankError


class FreshUniverseInventoryError(QbankError):
    """An address cannot be classified from the canonical artifacts."""


#: Ordered from the earliest layer a study unit passes through to the latest.
#: ``classify_address`` returns the first one that is not satisfied, so the order
#: is the semantics and not a presentation choice.
BLOCKING_LAYERS = (
    "SCOPE",
    "MCC_MAPPING",
    "SOURCE_PACKET_RESEARCH",
    "QGEN_ONBOARDING",
    "FOUNDATIONAL_EVIDENCE",
    "LEARNER_DECISION",
    "CONTRAST_SUPPLY",
    "HISTORICAL_USE",
    "NONE",
)

READINESS_CLASSES = (
    "GENERATION_READY",
    "SOURCE_READY_BUT_NOT_OPPORTUNITY_READY",
    "SOURCE_PACKET_INCOMPLETE",
    "FOUNDATIONAL_EVIDENCE_INCOMPLETE",
    "MCC_SCOPE_INCOMPLETE",
    "LEARNER_DECISION_MISSING",
    "CONTRAST_SUPPLY_INCOMPLETE",
    "ALREADY_CONSUMED_BY_PRIOR_PILOT",
    "OUT_OF_SCOPE",
    "OTHER",
)

_LAYER_FOR_CLASS = {
    "OUT_OF_SCOPE": "SCOPE",
    "MCC_SCOPE_INCOMPLETE": "MCC_MAPPING",
    "SOURCE_PACKET_INCOMPLETE": "SOURCE_PACKET_RESEARCH",
    "SOURCE_READY_BUT_NOT_OPPORTUNITY_READY": "QGEN_ONBOARDING",
    "FOUNDATIONAL_EVIDENCE_INCOMPLETE": "FOUNDATIONAL_EVIDENCE",
    "LEARNER_DECISION_MISSING": "LEARNER_DECISION",
    "CONTRAST_SUPPLY_INCOMPLETE": "CONTRAST_SUPPLY",
    "ALREADY_CONSUMED_BY_PRIOR_PILOT": "HISTORICAL_USE",
    "GENERATION_READY": "NONE",
    "OTHER": "NONE",
}

DISCIPLINES = ("MED", "PED", "OBGYN", "SURG", "PSY", "PHELO")

REPORT_PATH = "reports/qgen_fresh_universe_readiness_inventory.json"

#: A contrast set needs three competitors beside the key. A target that cannot
#: reach three curated candidates is a supply shortfall, not a selection choice.
MINIMUM_CURATED_CANDIDATES = 3

REQUIRED_SIGNALS = (
    "allocation_address_id",
    "discipline",
    "priority_class",
    "generation_policy",
    "mcc_objective_count",
    "source_packets_planned",
    "source_packets_ready",
    "evidence_claims",
    "declared_learner_decisions",
    "unconsumed_learner_decisions",
    "vocabulary_features",
    "curated_seed_targets_at_or_above_minimum",
)


def classify_address(signals: dict[str, Any]) -> dict[str, Any]:
    """Return the readiness class and blocking layer for one allocation address.

    The first unsatisfied layer wins. ``OTHER`` is reachable only when the
    signals contradict one another, which is a defect in the inputs rather than
    a state a study unit can legitimately be in.
    """
    missing = [name for name in REQUIRED_SIGNALS if name not in signals]
    if missing:
        raise FreshUniverseInventoryError(
            f"cannot classify an address without {', '.join(missing)}"
        )

    planned = signals["source_packets_planned"]
    ready = signals["source_packets_ready"]
    declared = signals["declared_learner_decisions"]
    features = signals["vocabulary_features"]
    supplied_targets = signals["curated_seed_targets_at_or_above_minimum"]

    if signals["generation_policy"] == "NEVER" or signals["priority_class"] == "NOT_IN_SCOPE":
        readiness = "OUT_OF_SCOPE"
    elif signals["mcc_objective_count"] == 0:
        readiness = "MCC_SCOPE_INCOMPLETE"
    elif planned == 0 or ready < planned:
        readiness = "SOURCE_PACKET_INCOMPLETE"
    elif declared == 0 and features == 0 and supplied_targets == 0:
        # Every planned packet is researched and nothing above the evidence layer
        # has been built. This is the honest label for an address that is source
        # ready and still cannot yield a question.
        readiness = "SOURCE_READY_BUT_NOT_OPPORTUNITY_READY"
    elif signals["evidence_claims"] == 0:
        readiness = "FOUNDATIONAL_EVIDENCE_INCOMPLETE"
    elif declared == 0:
        readiness = "LEARNER_DECISION_MISSING"
    elif features == 0 or supplied_targets == 0:
        readiness = "CONTRAST_SUPPLY_INCOMPLETE"
    elif signals["unconsumed_learner_decisions"] == 0:
        readiness = "ALREADY_CONSUMED_BY_PRIOR_PILOT"
    elif ready > planned:
        readiness = "OTHER"
    else:
        readiness = "GENERATION_READY"

    return {
        "allocation_address_id": signals["allocation_address_id"],
        "discipline": signals["discipline"],
        "readiness_class": readiness,
        "blocking_layer": _LAYER_FOR_CLASS[readiness],
    }


def _read(root, relative: str) -> Any:
    from .jsonio import read_json
    from .paths import resolve_root_path

    return read_json(resolve_root_path(root, relative))


#: The pilots that have already consumed a learner decision. A decision used in
#: any of them is not fresh, whatever the outcome of that use was.
PRIOR_PILOT_OPPORTUNITY_ARTIFACTS = (
    "research/qgen/safe_yield/g1_micro_pilot.opportunities.json",
    "research/qgen/safe_yield/g2_profile_pilot.opportunities.json",
    "research/qgen/contrast_first_pilot_opportunities.json",
    "research/qgen/pilot/medium-pilot-6-opportunities.json",
)

DECLARED_DECISIONS_PATH = "research/qgen/safe_yield/g2_declared_learner_decisions.json"
FOUNDATIONAL_CLAIMS_PATH = "research/qgen/foundational_evidence_claim_cards.json"


def collect_prior_pilot_use(root) -> dict[str, list[str]]:
    """Map each learner decision id to the pilots that have already used it."""
    used: dict[str, set[str]] = {}
    for relative in PRIOR_PILOT_OPPORTUNITY_ARTIFACTS:
        label = relative.rsplit("/", 1)[-1]
        for row in _read(root, relative)["opportunities"]:
            decision = row.get("learner_decision_id")
            if decision:
                used.setdefault(decision, set()).add(label)
    return {decision: sorted(pilots) for decision, pilots in sorted(used.items())}


def collect_source_packet_state(root) -> dict[str, dict[str, int]]:
    """Count planned and researched source packets for every allocation address."""
    import glob
    from pathlib import Path

    from .paths import canonical_root

    plan = _read(root, "research/qgen/source_packet_plan.json")
    ready: set[str] = set()
    base = canonical_root(Path(root))
    for path in sorted(glob.glob(str(base / "research/qgen/source_packet_population_srb_*.json"))):
        relative = Path(path).relative_to(base).as_posix()
        for packet in _read(root, relative)["source_packets"]:
            if packet["status"] == "SOURCE_PACKET_READY":
                ready.add(packet["source_packet_id"])

    state: dict[str, dict[str, int]] = {}
    for address, packet_ids in plan["allocation_address_source_packet_ids"].items():
        state[address] = {
            "planned": len(packet_ids),
            "ready": sum(1 for packet_id in packet_ids if packet_id in ready),
        }
    return state


def collect_opportunity_layer(root) -> dict[str, dict[str, Any]]:
    """Gather the four qgen-onboarding layers keyed by anchor study unit."""
    from collections import Counter

    from .feature_anchor_registry import SEED_PACK_BASES, VOCABULARY_PATH

    layer: dict[str, dict[str, Any]] = {}

    def row(unit: str) -> dict[str, Any]:
        return layer.setdefault(unit, {
            "vocabulary_features": 0,
            "declared_learner_decisions": [],
            "curated_seed_targets": {},
            "evidence_claim_ids": set(),
        })

    for unit in _read(root, VOCABULARY_PATH)["anchors"]:
        row(unit["anchor_study_unit_id"])["vocabulary_features"] = len(unit["features"])

    for address in _read(root, DECLARED_DECISIONS_PATH)["addresses"]:
        row(address["allocation_address_id"])["declared_learner_decisions"] = [
            decision["learner_decision_id"]
            for decision in address["declared_learner_decisions"]
        ]

    for base in SEED_PACK_BASES:
        for target in _read(root, f"{base}.json")["targets"]:
            current = row(target["anchor_study_unit_id"])
            current["curated_seed_targets"][target["target_id"]] = len(target["seeds"])
            current["evidence_claim_ids"].update(target.get("key_evidence_refs") or [])
            for seed in target["seeds"]:
                current["evidence_claim_ids"].update(
                    seed.get("evidence_refs_for_plausibility") or []
                )
                current["evidence_claim_ids"].update(
                    seed.get("evidence_refs_for_discrimination") or []
                )

    for card in _read(root, FOUNDATIONAL_CLAIMS_PATH)["claim_cards"]:
        for reference in card.get("scope_references") or []:
            unit = reference.get("study_unit_id")
            if unit:
                row(unit)["evidence_claim_ids"].add(card["claim_card_id"])

    for unit, current in layer.items():
        counts = Counter(current["curated_seed_targets"])
        current["curated_seed_targets_at_or_above_minimum"] = sum(
            1 for size in counts.values() if size >= MINIMUM_CURATED_CANDIDATES
        )
        current["curated_seeds"] = sum(counts.values())
        current["evidence_claims"] = len(current["evidence_claim_ids"])
        current["evidence_claim_ids"] = sorted(current["evidence_claim_ids"])
    return layer


def build_inventory(root) -> dict[str, Any]:
    """Classify every canonical allocation address by its earliest missing layer."""
    from collections import Counter
    from pathlib import Path

    from .coverage_priority import build_coverage_priority_model

    priority = build_coverage_priority_model(Path(root))
    packets = collect_source_packet_state(root)
    layer = collect_opportunity_layer(root)
    prior_use = collect_prior_pilot_use(root)

    rows: list[dict[str, Any]] = []
    for address in priority["addresses"]:
        address_id = address["allocation_address_id"]
        onboarding = layer.get(address_id, {})
        declared = onboarding.get("declared_learner_decisions") or []
        unconsumed = [decision for decision in declared if decision not in prior_use]
        packet_state = packets.get(address_id, {"planned": 0, "ready": 0})
        signals = {
            "allocation_address_id": address_id,
            "discipline": address["discipline"],
            "priority_class": address["priority_class"],
            "generation_policy": address["generation_policy"],
            "mcc_objective_count": len(address["mcc_objective_ids"]),
            "source_packets_planned": packet_state["planned"],
            "source_packets_ready": packet_state["ready"],
            "evidence_claims": onboarding.get("evidence_claims", 0),
            "declared_learner_decisions": len(declared),
            "unconsumed_learner_decisions": len(unconsumed),
            "vocabulary_features": onboarding.get("vocabulary_features", 0),
            "curated_seed_targets_at_or_above_minimum": onboarding.get(
                "curated_seed_targets_at_or_above_minimum", 0
            ),
        }
        verdict = classify_address(signals)
        rows.append({
            **verdict,
            "chapter": address["chapter"],
            "depth": address["depth"],
            "priority_class": address["priority_class"],
            "mcc_objective_ids": list(address["mcc_objective_ids"]),
            "source_packets_planned": packet_state["planned"],
            "source_packets_ready": packet_state["ready"],
            "evidence_claims": signals["evidence_claims"],
            "declared_learner_decisions": len(declared),
            "unconsumed_learner_decisions": unconsumed,
            "vocabulary_features": signals["vocabulary_features"],
            "curated_seeds": onboarding.get("curated_seeds", 0),
            "curated_seed_targets_at_or_above_minimum": signals[
                "curated_seed_targets_at_or_above_minimum"
            ],
            "consumed_by_prior_pilots": sorted({
                pilot for decision in declared for pilot in prior_use.get(decision, [])
            }),
        })

    rows.sort(key=lambda row: row["allocation_address_id"])
    class_counts = Counter(row["readiness_class"] for row in rows)
    layer_counts = Counter(row["blocking_layer"] for row in rows)
    by_discipline = {
        discipline: dict(
            Counter(
                row["readiness_class"]
                for row in rows
                if row["discipline"] == discipline
            )
        )
        for discipline in DISCIPLINES
    }

    source_ready_not_onboarded = [
        row["allocation_address_id"]
        for row in rows
        if row["readiness_class"] == "SOURCE_READY_BUT_NOT_OPPORTUNITY_READY"
    ]
    # A unit is onboarded when question generation can reach it: it owns a
    # stem-feature vocabulary and a curated seed pack. Carrying a claim card that
    # merely names it is not onboarding, so the evidence layer alone does not
    # qualify a unit here.
    onboarded_units = sorted(
        unit
        for unit, current in layer.items()
        if current.get("vocabulary_features") and current.get("curated_seeds")
    )
    indexed = {row["allocation_address_id"]: row for row in rows}
    onboarded_source_packet_state = {
        unit: {
            "source_packets_planned": indexed[unit]["source_packets_planned"],
            "source_packets_ready": indexed[unit]["source_packets_ready"],
            "readiness_class": indexed[unit]["readiness_class"],
        }
        for unit in onboarded_units
        if unit in indexed
    }

    return {
        "schema_version": "1.0",
        "scope": "QGEN_FRESH_UNIVERSE_READINESS_INVENTORY",
        "llm_api_calls": 0,
        "readiness_classes": list(READINESS_CLASSES),
        "blocking_layers": list(BLOCKING_LAYERS),
        "MINIMUM_CURATED_CANDIDATES": MINIMUM_CURATED_CANDIDATES,
        "STUDY_UNITS_INVENTORIED": len(rows),
        "READINESS_CLASS_COUNTS": dict(sorted(class_counts.items())),
        "BLOCKING_LAYER_COUNTS": dict(sorted(layer_counts.items())),
        "READINESS_BY_DISCIPLINE": by_discipline,
        "STUDY_UNITS_ONBOARDED_TO_QGEN": onboarded_units,
        "ONBOARDED_UNIT_SOURCE_PACKET_STATE": onboarded_source_packet_state,
        "SOURCE_READY_NOT_ONBOARDED": source_ready_not_onboarded,
        "SOURCE_READY_NOT_ONBOARDED_BY_DISCIPLINE": dict(sorted(Counter(
            row["discipline"]
            for row in rows
            if row["readiness_class"] == "SOURCE_READY_BUT_NOT_OPPORTUNITY_READY"
        ).items())),
        "UNCONSUMED_LEARNER_DECISIONS": sorted({
            decision for row in rows for decision in row["unconsumed_learner_decisions"]
        }),
        "PRIOR_FEASIBILITY_RECONCILIATION": {
            "prior_report": "reports/qgen_fresh_validation_universe_feasibility.json",
            "prior_ceiling": 3,
            "prior_freshness_rule": (
                "A decision was counted unused when it did not appear in the G2 "
                "profile-pilot opportunity set."
            ),
            "this_freshness_rule": (
                "A decision is counted unused only when it appears in none of the four "
                "prior pilot opportunity sets, which is the comparison the freshness "
                "audit for this milestone is required to make."
            ),
            "difference": (
                "LD-C21-03, LD-OB54-04 and LD-PS12-04 were each already an opportunity "
                "in the G1 micro pilot, so under the broader rule the existing universe "
                "carries no fresh decision at all. Both numbers are correct under their "
                "own rule; this one is the stricter and is the one a fresh pilot needs."
            ),
        },
        "inventory": rows,
        "reading": (
            "Each address is classified by the earliest layer it does not satisfy, so "
            "the classes are disjoint and sum to the address count. An address counted "
            "at SOURCE_PACKET_RESEARCH may also lack a vocabulary and a seed pack; it "
            "is reported at the earlier layer because the later work would be wasted "
            "until the earlier one lands. Nothing here proposes or ranks work. "
            "ONBOARDED_UNIT_SOURCE_PACKET_STATE is the one place the two evidence "
            "routes are visible at once: five of the six onboarded units are classified "
            "SOURCE_PACKET_INCOMPLETE because their qgen evidence was acquired by "
            "targeted pilot research rather than by completing their planned packets."
        ),
    }
