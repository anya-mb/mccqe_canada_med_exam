"""Drive a bounded pool of question opportunities to terminal states.

This is the planning front end and reporting back end of the design wrapped
around the per-item gates. It has no target: an opportunity that ends in
``NO_SAFE_ITEM`` with a reason, or in ``REDUNDANT``, is a complete and correct
result for that opportunity, and the wave reports it alongside what was accepted
rather than as a shortfall.

Ordering is CORE first, so that the hard opportunities are attempted rather than
deferred. Nothing here re-runs an opportunity to improve a number.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .critical_fact_adjudication import adjudicate_evidence_packet
from .errors import QbankError
from .marginal_educational_value import assess_marginal_value
from .option_set_admissibility import (
    adjudicate_option_set_admissibility,
    validate_role_blind_label_pool,
)
from .paths import resolve_root_path
from .qgen_profiles import (
    DisciplineProfileError,
    load_discipline_profiles,
    resolve_option_set_contract,
)
from .question_opportunity import summarize_opportunities, transition_opportunity


class SafeYieldWaveError(QbankError):
    """A wave input is missing or inconsistent."""


PRIORITY_ORDER = {"CORE": 0, "IMPORTANT": 1, "SUPPORTING": 2, "NOT_IN_SCOPE": 3}

_FACT_REASON = {
    "FAIL_CLOSED_ERRONEOUS_SOURCE_FACT": "FAIL_CLOSED_ERRONEOUS_SOURCE_FACT",
    "FAIL_CLOSED_UNRESOLVED_CRITICAL_FACT": "FAIL_CLOSED_UNRESOLVED_CRITICAL_FACT",
}


def _read(root: Path, relative: str) -> dict[str, Any]:
    path = resolve_root_path(root, relative)
    if not path.is_file():
        raise SafeYieldWaveError(f"wave input is unavailable: {relative}")
    return json.loads(path.read_text())


def run_safe_yield_wave(
    root: Path,
    *,
    opportunities_relative_path: str,
    plan_relative_path: str,
    items_relative_path: str,
    labels_relative_path: str,
    assignments_relative_path: str,
) -> dict[str, Any]:
    """Drive every opportunity in a wave and return its result record."""
    root = Path(root).resolve()
    opportunities = _read(root, opportunities_relative_path)["opportunities"]
    plan = {row["opportunity_label"]: row for row in _read(root, plan_relative_path)["plan"]}
    items = {row["opportunity_label"]: row for row in _read(root, items_relative_path)["items"]}
    label_pool = validate_role_blind_label_pool(_read(root, labels_relative_path))
    assignments = {
        row["opportunity_label"]: row
        for row in _read(root, assignments_relative_path)["assignments"]
    }
    probes = _read(root, plan_relative_path).get("admissibility_probes", [])
    profiles = load_discipline_profiles(root)

    fact_cache: dict[tuple[str, str], dict[str, dict[str, Any]]] = {}

    def facts(packet_relative: str, profile_id: str) -> dict[str, dict[str, Any]]:
        key = (packet_relative, profile_id)
        if key not in fact_cache:
            fact_cache[key] = adjudicate_evidence_packet(
                root,
                _read(root, packet_relative),
                profile_risk_classes=profiles[profile_id]["numeric_risk_classes"],
            )
        return fact_cache[key]

    ordered = sorted(
        opportunities,
        key=lambda row: (PRIORITY_ORDER[row["priority_class"]], row["wave_label"]),
    )

    accepted_tuples: dict[str, list[dict[str, Any]]] = {}
    results: list[dict[str, Any]] = []
    novelty_verdict_stream: list[str] = []
    gate_verdicts: dict[str, list[str]] = {}

    for opportunity in ordered:
        label = opportunity["wave_label"]
        entry = plan.get(label)
        if entry is None:
            raise SafeYieldWaveError(f"no wave plan entry for {label}")
        profile = profiles[opportunity["discipline_profile_id"]]
        record: dict[str, Any] = {
            "wave_label": label,
            "opportunity_id": opportunity["opportunity_id"],
            "discipline": opportunity["discipline"],
            "priority_class": opportunity["priority_class"],
            "learner_decision_id": opportunity["learner_decision_id"],
            "item_archetype": opportunity["item_archetype"],
            "option_set_archetype": opportunity["option_set_archetype"],
        }

        # Stage 1 and 4 - profile binding, and the archetype declaration itself.
        try:
            contract = resolve_option_set_contract(
                profile, opportunity["item_archetype"], opportunity["option_set_archetype"]
            )
        except DisciplineProfileError as error:
            transition_opportunity(
                opportunity, "NO_SAFE_ITEM",
                reason="FAIL_CLOSED_INCOHERENT_OPTION_SET_ARCHETYPE",
            )
            record.update({
                "state": opportunity["state"],
                "fail_closed_reason": opportunity["fail_closed_reason"],
                "reopens_on": opportunity["reopens_on"],
                "detail": str(error),
            })
            results.append(record)
            continue

        # Marginal educational value, pre-generation, over structured tuples only.
        topic = opportunity["anchor_study_unit_id"]
        novelty = assess_marginal_value(entry["novelty_tuple"], accepted_tuples.get(topic, []))
        novelty_verdict_stream.append(novelty["verdict"])
        gate_verdicts.setdefault("MARGINAL_EDUCATIONAL_VALUE", []).append(
            "REDUNDANT" if novelty["verdict"] == "REDUNDANT" else "NOVEL"
        )
        record["novelty_verdict"] = novelty["verdict"]
        if novelty["verdict"] == "REDUNDANT":
            transition_opportunity(opportunity, "REDUNDANT", reason="FAIL_CLOSED_REDUNDANT")
            record.update({"state": opportunity["state"], "novelty_basis": novelty["basis"]})
            results.append(record)
            continue

        # Critical facts, at claim level, inherited by the item.
        records = facts(entry["evidence_packet"], opportunity["discipline_profile_id"])
        unusable = [
            records[claim_id]
            for claim_id in entry["planned_evidence_refs"]
            if claim_id in records and not records[claim_id]["usable_in_generation"]
        ]
        missing = [
            claim_id for claim_id in entry["planned_evidence_refs"] if claim_id not in records
        ]
        gate_verdicts.setdefault("CRITICAL_FACT_ADJUDICATION", []).append(
            "FAIL" if unusable or missing else "PASS"
        )
        if missing:
            transition_opportunity(
                opportunity, "NO_SAFE_ITEM", reason="FAIL_CLOSED_INSUFFICIENT_EVIDENCE"
            )
            record.update({
                "state": opportunity["state"],
                "fail_closed_reason": opportunity["fail_closed_reason"],
                "reopens_on": opportunity["reopens_on"],
                "missing_claim_ids": missing,
            })
            results.append(record)
            continue
        if unusable:
            reason = next(
                (
                    row.get("fail_closed_reason")
                    for row in unusable
                    if row.get("fail_closed_reason") == "FAIL_CLOSED_ERRONEOUS_SOURCE_FACT"
                ),
                "FAIL_CLOSED_UNRESOLVED_CRITICAL_FACT",
            )
            transition_opportunity(opportunity, "NO_SAFE_ITEM", reason=_FACT_REASON[reason])
            record.update({
                "state": opportunity["state"],
                "fail_closed_reason": opportunity["fail_closed_reason"],
                "reopens_on": opportunity["reopens_on"],
                "critical_fact_failures": [
                    {
                        "claim_id": row["claim_id"],
                        "fact_classes": row["fact_classes"],
                        "basis": row["adjudication_basis"],
                        "sanity_checks": [check["check"] for check in row["sanity_findings"]],
                    }
                    for row in unusable
                ],
            })
            results.append(record)
            continue

        transition_opportunity(
            opportunity, "EVIDENCE_READY",
            decisive_discriminator=entry["novelty_tuple"]["decisive_discriminator"],
        )

        item = items.get(label)
        if item is None:
            transition_opportunity(
                opportunity, "NO_SAFE_ITEM", reason="FAIL_CLOSED_UNINSTANTIABLE_REASONING"
            )
            record.update({
                "state": opportunity["state"],
                "fail_closed_reason": opportunity["fail_closed_reason"],
                "reopens_on": opportunity["reopens_on"],
            })
            results.append(record)
            continue

        transition_opportunity(opportunity, "CONTRAST_READY")
        transition_opportunity(opportunity, "GENERATABLE")

        assignment = assignments[label]
        admissibility = adjudicate_option_set_admissibility(
            option_set_archetype=opportunity["option_set_archetype"],
            contract=contract,
            demanded_response_class=assignment["demanded_response_class"],
            options=item["options"],
            label_pool=label_pool,
            stem_feature_map={"features": item["stem_feature_map"]},
            enacted_action_signatures=entry.get("enacted_action_signatures", []),
        )
        for rule, verdict in admissibility["rule_verdicts"].items():
            gate_verdicts.setdefault(rule, []).append(verdict)
        record["admissibility"] = admissibility
        if admissibility["verdict"] != "ADMISSIBLE":
            transition_opportunity(
                opportunity, "NO_SAFE_ITEM",
                reason=admissibility["fail_closed_reason"]
                or "FAIL_CLOSED_INCOHERENT_OPTION_SET_ARCHETYPE",
            )
            record.update({
                "state": opportunity["state"],
                "fail_closed_reason": opportunity["fail_closed_reason"],
                "reopens_on": opportunity["reopens_on"],
            })
            results.append(record)
            continue

        # The item is realised and internally sound. Acceptance still waits on
        # fresh independent verification, which is recorded separately.
        record.update({
            "state": "GENERATABLE",
            "item_id": item["item_id"],
            "awaiting": "FRESH_INDEPENDENT_VERIFICATION",
        })
        accepted_tuples.setdefault(topic, []).append(
            dict(entry["novelty_tuple"], item_reference=item["item_id"])
        )
        results.append(record)

    # Positive controls. Each probe is an option set built to violate exactly one
    # admissibility rule. Probes never enter the opportunity pool and never count
    # toward yield; they exist so that a wave in which every real item passes can
    # still show that the rule family is live rather than inert.
    probe_results: list[dict[str, Any]] = []
    for probe in probes:
        profile = profiles[probe["discipline_profile_id"]]
        contract = resolve_option_set_contract(
            profile, probe["item_archetype"], probe["option_set_archetype"]
        )
        verdict = adjudicate_option_set_admissibility(
            option_set_archetype=probe["option_set_archetype"],
            contract=contract,
            demanded_response_class=probe["demanded_response_class"],
            options=probe["options"],
            label_pool=label_pool,
            stem_feature_map={"features": probe.get("stem_feature_map", [])},
            competitor_condition_predicates=probe.get("competitor_condition_predicates"),
            key_grounding_feature_ids=probe.get("key_grounding_feature_ids"),
            enacted_action_signatures=probe.get("enacted_action_signatures", []),
        )
        for rule, value in verdict["rule_verdicts"].items():
            gate_verdicts.setdefault(rule, []).append(value)
        probe_results.append({
            "probe_id": probe["probe_id"],
            "targets_rule": probe["targets_rule"],
            "rule_verdicts": verdict["rule_verdicts"],
            "fired": verdict["rule_verdicts"][probe["targets_rule"]] == "FAIL",
            "verdict": verdict["verdict"],
        })

    return {
        "schema_version": "1.0",
        "scope": "QGEN_SAFE_YIELD_WAVE_EXECUTION",
        "wave_id": _read(root, opportunities_relative_path)["wave_id"],
        "opportunities": opportunities,
        "results": results,
        "gate_verdicts": gate_verdicts,
        "novelty_verdict_stream": novelty_verdict_stream,
        "admissibility_probes": probe_results,
        "pre_verification_summary": summarize_opportunities(opportunities),
    }
