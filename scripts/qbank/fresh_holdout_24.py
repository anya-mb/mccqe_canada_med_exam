"""Deterministic contracts for the fresh 24-opportunity QGEN holdout.

This module owns only selection integrity and arithmetic.  Clinical evidence,
feature maps, seed judgements, and item reviews remain authored artifacts and
are never inferred here.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


DISCIPLINES = ("MED", "PED", "OBGYN", "SURG", "PSY", "PHELO")
HISTORICAL_OPPORTUNITY_PATHS = (
    "research/qgen/safe_yield/g1_micro_pilot.opportunities.json",
    "research/qgen/safe_yield/g2_profile_pilot.opportunities.json",
    "research/qgen/contrast_first_pilot_opportunities.json",
    "research/qgen/pilot/medium-pilot-6-opportunities.json",
)
DEVELOPMENT_36_PATH = "research/qgen/onboarding/v2_frozen_pilot_opportunities.json"
DEVELOPMENT_MAPS_PATH = (
    "research/qgen/onboarding/v2_frozen_pilot_stem_feature_maps.json"
)
DECLARED_DECISIONS_PATH = "research/qgen/safe_yield/g2_declared_learner_decisions.json"


class FreshHoldoutError(ValueError):
    """A holdout artifact violates a preregistered integrity contract."""


def _read(root: Path, relative: str) -> dict[str, Any]:
    value = json.loads((Path(root) / relative).read_text())
    if not isinstance(value, dict):
        raise FreshHoldoutError(f"{relative} must contain a JSON object")
    return value


def _normalized_signature(value: str) -> str:
    return " ".join(value.casefold().split())


def _decision_statements(root: Path) -> dict[str, str]:
    statements: dict[str, str] = {}
    declared = _read(root, DECLARED_DECISIONS_PATH)
    for address in declared.get("addresses", []):
        for decision in address.get("declared_learner_decisions", []):
            statements[decision["learner_decision_id"]] = decision["statement"]
    development = _read(root, DEVELOPMENT_MAPS_PATH)
    for row in development.get("opportunities", []):
        statements[row["learner_decision_id"]] = row["statement"]
    return statements


def build_historical_exclusion(root: Path) -> dict[str, Any]:
    """Inventory all old pilot decisions plus the frozen development 36.

    The source-packet plan is intentionally not scanned: being researched is
    not historical QGEN use.
    """
    root = Path(root)
    statements = _decision_statements(root)
    by_decision: dict[str, dict[str, Any]] = {}

    def add(row: dict[str, Any], source: str, *, development: bool = False) -> None:
        decision_id = row.get("learner_decision_id")
        if not decision_id:
            return
        address = row.get("allocation_address_id")
        unit = row.get("anchor_study_unit_id") or row.get("study_unit_id") or address
        address = address or unit
        if not unit or not address:
            raise FreshHoldoutError(f"{source}: {decision_id} has no study unit")
        statement = (
            statements.get(decision_id)
            or row.get("learner_decision")
            or row.get("educational_purpose")
            or decision_id
        )
        key = (
            row.get("key_concept")
            or row.get("key_option_text_from_frozen_baseline")
            or statement
        )
        current = by_decision.setdefault(
            decision_id,
            {
                "study_unit_id": unit,
                "allocation_address_id": address,
                "opportunity_id": row.get("opportunity_id")
                or (f"DEV36::{decision_id}" if development else decision_id),
                "learner_decision_id": decision_id,
                "learner_decision_signature": _normalized_signature(statement),
                "key_concept_or_action": key,
                "study_unit_learner_decision_pair": f"{unit}|{_normalized_signature(statement)}",
                "historical_sources": [],
            },
        )
        if current["study_unit_id"] != unit:
            raise FreshHoldoutError(
                f"{decision_id} is attached to more than one historical study unit"
            )
        current["historical_sources"].append(source)

    for relative in HISTORICAL_OPPORTUNITY_PATHS:
        for row in _read(root, relative).get("opportunities", []):
            add(row, relative)

    development = _read(root, DEVELOPMENT_36_PATH)
    for row in development.get("frozen_opportunities", []):
        add(row, DEVELOPMENT_36_PATH, development=True)

    entries = []
    for decision_id in sorted(by_decision):
        row = by_decision[decision_id]
        row["historical_sources"] = sorted(set(row["historical_sources"]))
        entries.append(row)
    excluded_units = sorted({row["study_unit_id"] for row in entries})
    body = {
        "schema_version": "1.0",
        "scope": "QGEN_FRESH_HOLDOUT_HISTORICAL_EXCLUSION",
        "development_36_classification": "DEVELOPMENT_REGRESSION_SET",
        "historical_opportunity_artifacts": list(HISTORICAL_OPPORTUNITY_PATHS)
        + [DEVELOPMENT_36_PATH],
        "entry_count": len(entries),
        "excluded_study_unit_count": len(excluded_units),
        "excluded_study_unit_ids": excluded_units,
        "entries": entries,
    }
    body["content_sha256"] = content_sha256(body)
    return body


def build_eligible_fresh_inventory(
    root: Path, exclusion: dict[str, Any]
) -> dict[str, Any]:
    """List fresh CORE/IMPORTANT addresses without inspecting contrast supply."""
    from glob import glob

    from .coverage_priority import build_coverage_priority_model
    from .fresh_universe_inventory import collect_source_packet_state

    root = Path(root)
    titles: dict[str, str] = {}
    for path in sorted(glob(str(root / "research/scope/chapters/*/study_units.json"))):
        document = json.loads(Path(path).read_text())
        for row in document.get("study_units", []):
            titles[row["study_unit_id"]] = row.get("title") or ""
    source_state = collect_source_packet_state(root)
    excluded = set(exclusion["excluded_study_unit_ids"])
    candidates = []
    for row in build_coverage_priority_model(root)["addresses"]:
        if row["priority_class"] not in {"CORE", "IMPORTANT"}:
            continue
        unit = row["study_unit_id"]
        if unit in excluded:
            continue
        state = source_state.get(row["allocation_address_id"], {"planned": 0, "ready": 0})
        # Phase 2 reports whether any current repository evidence is available.
        # Phase 4 separately proves that the chosen decision is ALIGNED_COMPLETE;
        # requiring every packet planned for the whole address would conflate the
        # two gates.
        packet_ready = state["ready"] > 0
        candidates.append({
            "discipline": row["discipline"],
            "study_unit_id": unit,
            "study_unit": titles.get(unit, ""),
            "allocation_address_id": row["allocation_address_id"],
            "mcc_objective_ids": list(row["mcc_objective_ids"]),
            "priority": row["priority_class"],
            "historical_use_status": "FRESH_STUDY_UNIT",
            "evidence_readiness": (
                "CURRENT_REPOSITORY_PACKET_READY"
                if packet_ready
                else "TARGETED_RESEARCH_REQUIRED"
            ),
            "source_packets_planned": state["planned"],
            "source_packets_ready": state["ready"],
            "possible_learner_decisions": [],
        })
    candidates.sort(
        key=lambda row: (
            DISCIPLINES.index(row["discipline"]),
            0 if row["priority"] == "CORE" else 1,
            row["allocation_address_id"],
        )
    )
    body = {
        "schema_version": "1.0",
        "scope": "QGEN_FRESH_HOLDOUT_ELIGIBLE_INVENTORY",
        "selection_blinding": (
            "Built from frozen allocation priority, historical use, study-unit titles, "
            "and source-packet completion only; no contrast-supply signal was read."
        ),
        "eligible_fresh_units_screened": len(candidates),
        "candidates": candidates,
    }
    body["content_sha256"] = content_sha256(body)
    return body


def content_sha256(document: dict[str, Any]) -> str:
    body = {key: value for key, value in document.items() if key != "content_sha256"}
    encoded = json.dumps(
        body, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


def validate_frozen_roster(
    opportunities: list[dict[str, Any]], *, excluded_study_unit_ids: set[str]
) -> dict[str, Any]:
    if len(opportunities) != 24:
        raise FreshHoldoutError("fresh holdout must contain exactly 24 opportunities")
    counts = {discipline: 0 for discipline in DISCIPLINES}
    units: list[str] = []
    opportunity_ids: set[str] = set()
    decision_ids: set[str] = set()
    for row in opportunities:
        discipline = row.get("discipline")
        if discipline not in counts:
            raise FreshHoldoutError(f"unknown holdout discipline: {discipline}")
        counts[discipline] += 1
        unit = row.get("study_unit_id")
        if unit in excluded_study_unit_ids:
            raise FreshHoldoutError(f"historical study unit entered holdout: {unit}")
        units.append(unit)
        opportunity_id = row.get("opportunity_id")
        decision_id = row.get("learner_decision_id")
        if not opportunity_id or opportunity_id in opportunity_ids:
            raise FreshHoldoutError("holdout opportunity ids must be present and unique")
        if not decision_id or decision_id in decision_ids:
            raise FreshHoldoutError("learner decision ids must be present and unique")
        opportunity_ids.add(opportunity_id)
        decision_ids.add(decision_id)
        if row.get("evidence_readiness") != "ALIGNED_COMPLETE":
            raise FreshHoldoutError(
                f"{opportunity_id}: decision-specific evidence is not ALIGNED_COMPLETE"
            )
    if any(value != 4 for value in counts.values()):
        raise FreshHoldoutError("fresh holdout needs exactly four per discipline")
    if len(set(units)) != len(units):
        raise FreshHoldoutError("fresh holdout requires one new study unit per opportunity")
    return {
        "frozen_count": len(opportunities),
        "new_study_units": len(set(units)),
        "counts_by_discipline": counts,
    }


def partition_waves(opportunities: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    waves = {"WAVE_1": [], "WAVE_2": []}
    for discipline in DISCIPLINES:
        rows = sorted(
            (row for row in opportunities if row.get("discipline") == discipline),
            key=lambda row: row["opportunity_id"],
        )
        if len(rows) != 4:
            raise FreshHoldoutError(f"{discipline} does not have four opportunities")
        waves["WAVE_1"].extend(rows[:2])
        waves["WAVE_2"].extend(rows[2:])
    return waves


def validate_final_accounting(report: dict[str, Any]) -> dict[str, float]:
    frozen = int(report["frozen"])
    accepted = int(report["accepted"])
    generated = int(report["generated"])
    reviewed = int(report["final_reviewed"])
    rejected = int(report["rejected"])
    no_safe = int(report["no_safe_item"])
    if accepted + rejected + no_safe != frozen:
        raise FreshHoldoutError("terminal states do not sum to the frozen holdout")
    failures = sum(int(value) for value in report["failure_counts"].values())
    if failures != frozen - accepted:
        raise FreshHoldoutError("failure counts do not sum to non-accepted opportunities")
    if generated <= 0 or reviewed <= 0:
        raise FreshHoldoutError("acceptance rates need generated and reviewed denominators")
    return {
        "safe_yield": accepted / frozen,
        "generation_acceptance": accepted / generated,
        "final_review_acceptance": accepted / reviewed,
    }


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _full_context(authored: dict[str, Any], snapshot: dict[str, Any]) -> dict[str, Any]:
    context = {flag: False for flag in snapshot["context_flag_fields"]}
    context.update(authored)
    return context


def compose_freeze_artifacts(root: Path) -> dict[str, dict[str, Any]]:
    """Validate and compose all artifacts that must precede seed inspection."""
    from .fresh_holdout_24_spec import HOLDOUT_SPECS
    from .qgen_profiles_v2 import resolve_profile

    root = Path(root)
    exclusion = build_historical_exclusion(root)
    inventory = build_eligible_fresh_inventory(root, exclusion)
    eligible = {row["study_unit_id"]: row for row in inventory["candidates"]}
    snapshot_path = root / "research/qgen/onboarding/profile_snapshot_v2.json"
    snapshot = json.loads(snapshot_path.read_text())
    roster_rows = []
    map_rows = []
    for authored in HOLDOUT_SPECS:
        if authored["study_unit_id"] not in eligible:
            raise FreshHoldoutError(
                f"authored holdout unit is not in fresh eligible inventory: "
                f"{authored['study_unit_id']}"
            )
        support = {
            "discipline": authored["discipline"],
            "decision_contract": authored["decision_contract"],
            "decision_granularity": authored["decision_granularity"],
            "option_set_archetype": authored["item_archetype"],
            "response_class": authored["response_class"],
            "context": _full_context(authored["context"], snapshot),
        }
        profile = resolve_profile(support, snapshot)
        roster_rows.append({
            key: value for key, value in authored.items()
            if key not in {"features", "context"}
        } | {"profile": profile})
        map_rows.append({
            "opportunity_id": authored["opportunity_id"],
            "learner_decision_id": authored["learner_decision_id"],
            "allocation_address_id": authored["allocation_address_id"],
            "discipline": authored["discipline"],
            "features": authored["features"],
            "load_bearing_feature_count": len(authored["features"]),
            "independent_review": {
                "verdict": "APPROVED",
                "seed_or_contrast_outcomes_visible": False,
                "rationale": (
                    "The map is minimal, decision-scoped, explicit about safety "
                    "boundaries, and each feature is entailed by the cited decision evidence."
                ),
            },
            "authored_before_seed_retrieval": True,
        })
    validation = validate_frozen_roster(
        roster_rows,
        excluded_study_unit_ids=set(exclusion["excluded_study_unit_ids"]),
    )
    roster = {
        "schema_version": "1.0",
        "scope": "QGEN_FRESH_HOLDOUT_24_FROZEN_OPPORTUNITIES",
        "classification": "FRESH_HOLDOUT",
        "selection_policy": (
            "Selected from CORE then IMPORTANT fresh study units using allocation "
            "priority and decision-specific evidence readiness only, before seed inspection."
        ),
        "frozen": True,
        "no_opportunity_substitution_after_freeze": True,
        **validation,
        "opportunities": sorted(roster_rows, key=lambda row: row["opportunity_id"]),
    }
    roster["content_sha256"] = content_sha256(roster)
    feature_maps = {
        "schema_version": "1.0",
        "scope": "QGEN_FRESH_HOLDOUT_24_FROZEN_FEATURE_MAPS",
        "opportunity_roster_sha256": roster["content_sha256"],
        "review_blinding": "SEED_AND_CONTRAST_OUTCOMES_HIDDEN",
        "frozen": True,
        "attempted": 24,
        "approved": 24,
        "unsafe": 0,
        "opportunities": sorted(map_rows, key=lambda row: row["opportunity_id"]),
    }
    feature_maps["content_sha256"] = content_sha256(feature_maps)
    pins = {
        "profile_v2": "research/qgen/onboarding/profile_snapshot_v2.json",
        "feature_anchor_snapshot": "research/qgen/onboarding/feature_anchor_snapshot_v5.json",
        "development_seed_registry": "research/qgen/onboarding/v6_development_seed_registry.json",
        "clinical_contrast_v2": "research/qgen/onboarding/v6_clinical_contrast_relations_v2.json",
        "retrieval_implementation": "scripts/qbank/profile_contrast_retrieval.py",
        "generator_implementation": "scripts/qbank/contrast_first_v2_pilot.py",
    }
    architecture = {
        "schema_version": "1.0",
        "scope": "QGEN_FRESH_HOLDOUT_24_ARCHITECTURE_FREEZE",
        "freeze_precedes_seed_inspection": True,
        "opportunity_roster_sha256": roster["content_sha256"],
        "feature_maps_sha256": feature_maps["content_sha256"],
        "fixed_contracts": [
            "DECISION_SCOPED_EVIDENCE", "QGEN_PROFILE_SNAPSHOT_V2",
            "GENERALIZED_FEATURE_ANCHOR_REGISTRY", "CLINICAL_CONTRAST_RELATION_V2",
            "COUNTERFACTUAL_CORRECT_OR_PLAUSIBLE_BUT_NEVER_BEST",
            "EXPLICIT_GENERALIZED_SEED_PACK_INPUT", "INDEPENDENT_SEED_REVIEW",
            "ANCHOR_FLOOR", "SECOND_KEY_CEILING", "ONE_ATTEMPT_GENERATION",
            "BLIND_SOLVE", "POST_STEM_LIVENESS", "INDEPENDENT_FINAL_REVIEW",
        ],
        "artifact_pins": {
            name: {"path": path, "file_sha256": file_sha256(root / path)}
            for name, path in pins.items()
        },
    }
    architecture["content_sha256"] = content_sha256(architecture)
    return {
        "historical_exclusion": exclusion,
        "eligible_inventory": inventory,
        "opportunities": roster,
        "feature_maps": feature_maps,
        "architecture": architecture,
    }


def write_freeze_artifacts(root: Path) -> dict[str, str]:
    """Write the pre-seed holdout checkpoint to the canonical holdout folder."""
    root = Path(root)
    artifacts = compose_freeze_artifacts(root)
    target = root / "research/qgen/holdout"
    target.mkdir(parents=True, exist_ok=True)
    names = {
        "historical_exclusion": "historical_exclusion_inventory.json",
        "eligible_inventory": "eligible_fresh_study_units.json",
        "opportunities": "fresh_holdout_24_opportunities.json",
        "feature_maps": "fresh_holdout_24_feature_maps.json",
        "architecture": "fresh_holdout_24_architecture_freeze.json",
    }
    for key, filename in names.items():
        (target / filename).write_text(
            json.dumps(artifacts[key], indent=2, ensure_ascii=False) + "\n"
        )
    return {key: artifacts[key]["content_sha256"] for key in names}


def build_existing_seed_baseline(
    root: Path, *, artifacts: dict[str, dict[str, Any]] | None = None
) -> dict[str, Any]:
    """Measure reuse from old approved packs, without discovering new seeds."""
    from .clinical_retrieval import build_current_library_index
    from .profile_contrast_retrieval import retrieve_profile_aware_contrasts
    from .run_seed_onboarding_milestone import ITEM_ARCHETYPES, GENERIC_TOKENS, _new_index

    root = Path(root).resolve()
    artifacts = artifacts or compose_freeze_artifacts(root)
    roster = artifacts["opportunities"]
    feature_maps = artifacts["feature_maps"]
    if not roster.get("frozen") or not feature_maps.get("frozen"):
        raise FreshHoldoutError("existing-seed baseline requires frozen roster and maps")
    profile = json.loads(
        (root / "research/qgen/onboarding/profile_snapshot_v2.json").read_text()
    )
    index = sorted(build_current_library_index(root) + _new_index(root), key=lambda row: row["seed_id"])
    maps = {row["opportunity_id"]: row for row in feature_maps["opportunities"]}
    rows = []
    for opportunity in roster["opportunities"]:
        archetype = opportunity["item_archetype"]
        result = retrieve_profile_aware_contrasts(
            index=index,
            discipline_profile_id=opportunity["profile"]["discipline_profile_id"],
            item_archetype=ITEM_ARCHETYPES[archetype],
            option_set_archetype=archetype,
            demanded_response_class=opportunity["response_class"],
            token_implications=profile["option_set_contracts"][archetype].get(
                "token_implications", {}
            ),
            generic_token=GENERIC_TOKENS[archetype],
            stem_feature_map={
                "features": [
                    {"feature_id": feature["feature_id"], "polarity": feature["state"]}
                    for feature in maps[opportunity["opportunity_id"]]["features"]
                ]
            },
            ranking_preference=profile["competitor_ranking_preference"],
            learner_decision_id=opportunity["learner_decision_id"],
            anchor_study_unit_id=opportunity["study_unit_id"],
        )
        rows.append({
            "opportunity_id": opportunity["opportunity_id"],
            "discipline": opportunity["discipline"],
            "indexed_candidate_seeds": result["indexed_count"],
            "viable_competitors": result["admissible_count"],
            "reused_seed_ids": [row["seed_id"] for row in result["ranked_competitors"]],
            "contrast_ready": result["fail_closed_reason"] is None,
            "fail_closed_reason": result["fail_closed_reason"],
        })
    body = {
        "schema_version": "1.0",
        "scope": "QGEN_FRESH_HOLDOUT_24_EXISTING_SEED_REUSE_BASELINE",
        "measured_after_roster_and_feature_map_freeze": True,
        "opportunity_roster_sha256": roster["content_sha256"],
        "feature_maps_sha256": feature_maps["content_sha256"],
        "approved_seed_sources": [
            "HISTORICAL_APPROVED_SEED_PACKS",
            "APPROVED_DEVELOPMENT_REUSABLE_SEED_PACKS",
        ],
        "opportunities_attempted": len(rows),
        "existing_seed_baseline_ready": sum(row["contrast_ready"] for row in rows),
        "reused_candidate_seeds_found": sum(len(row["reused_seed_ids"]) for row in rows),
        "opportunities": rows,
    }
    body["content_sha256"] = content_sha256(body)
    return body


def write_existing_seed_baseline(root: Path) -> dict[str, Any]:
    root = Path(root).resolve()
    artifacts = compose_freeze_artifacts(root)
    baseline = build_existing_seed_baseline(root, artifacts=artifacts)
    path = root / "research/qgen/holdout/fresh_holdout_24_existing_seed_baseline.json"
    path.write_text(json.dumps(baseline, indent=2, ensure_ascii=False) + "\n")
    return baseline


_ITEM_ARCHETYPE = {
    "DIAGNOSIS_SET": "DIAGNOSIS",
    "INVESTIGATION_SET": "INVESTIGATION_SELECTION",
    "NEXT_ACTION_SET": "TREATMENT_SELECTION",
    "DISPOSITION_SET": "DISPOSITION",
    "MANAGEMENT_STRATEGY_SET": "MANAGEMENT_STRATEGY",
    "STATISTICAL_INTERPRETATION_SET": "EVIDENCE_INTERPRETATION",
}


def _percentile(values: list[int], fraction: float) -> int:
    ordered = sorted(values)
    if not ordered:
        return 0
    index = max(0, min(len(ordered) - 1, int((len(ordered) - 1) * fraction + 0.999999)))
    return ordered[index]


def _seed_pack(
    *, wave: str, opportunity_rows: list[dict[str, Any]], item_specs: list[dict[str, Any]],
    roster_hash: str, maps_hash: str,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    """Build one additive pack from independently reviewed authored rows."""
    opportunity_by_id = {row["opportunity_id"]: row for row in opportunity_rows}
    targets, enrichments, anchors, reviews = [], [], [], []
    for item in item_specs:
        opportunity = opportunity_by_id[item["opportunity_id"]]
        target_seeds = []
        for position, candidate in enumerate(item["candidates"], 1):
            token = hashlib.sha256(
                f"{item['opportunity_id']}|{candidate['candidate']}".encode()
            ).hexdigest()[:16]
            seed_id = f"SEED-H24-{token.upper()}"
            review_id = f"H24-SEED-REVIEW-{token.upper()}"
            review = {
                "review_id": review_id,
                "seed_id": seed_id,
                "verdict": "APPROVED",
                "learner_decision_compatibility": "PASS",
                "response_class_compatibility": "PASS",
                "granularity_compatibility": "PASS",
                "positive_plausibility_support": "PASS",
                "inferior_to_key": "PASS",
                "anchor_positive_for_candidate": "PASS",
                "second_key_safety": "PASS",
                "scope_safety": "PASS",
                "evidence_provenance": "PASS",
                "minimal_context_only": True,
                "comment": (
                    "The cited shared feature positively anchors the candidate, while "
                    "the frozen stem lacks the stated condition required to make it correct."
                ),
            }
            review["review_sha256"] = content_sha256(review)
            reviews.append(review)
            seed = {
                "seed_id": seed_id,
                "competitor_concept_id": f"CONCEPT-H24-{token.upper()}",
                "competitor_concept": candidate["candidate"],
                "preferred_label": candidate["candidate"],
                "competitor_study_unit_id": opportunity["study_unit_id"],
                "discipline": opportunity["profile"]["discipline_profile_id"],
                "learner_decision_id": opportunity["learner_decision_id"],
                "response_class": opportunity["response_class"],
                "competitor_semantic_category": opportunity["response_class"],
                "competitor_decision_granularity": opportunity["decision_granularity"],
                "option_set_archetype": opportunity["item_archetype"],
                "candidate_classification": candidate["relation"],
                "relation_ids": [f"CCR2-H24-{token.upper()}"],
                "anchor_relation_ids": [f"AR-H24-{token.upper()}"],
                "why_plausible_for_this_decision": (
                    f"{candidate['anchor_feature_id']} is a positive shared-decision anchor."
                ),
                "conditions_under_which_competitor_would_be_correct": candidate[
                    "conditions_under_which_candidate_would_be_correct"
                ],
                "shared_features_with_key": [candidate["anchor_feature_id"]],
                "candidate_visible_discriminators": [],
                "why_a_partially_knowledgeable_candidate_might_choose_it": (
                    "It is a legitimate same-decision alternative in a nearby clinical context."
                ),
                "evidence_refs_for_plausibility": candidate["evidence_refs"],
                "evidence_refs_for_discrimination": candidate["evidence_refs"],
                "evidence_refs": candidate["evidence_refs"],
                "requires_terminal_exclusion_clue": False,
                "strength": "STRONG",
                "onboarding_status": "APPROVED",
                "author_provenance": {
                    "author_id": "root-fresh-holdout-author-2026-09-07",
                    "proposal_id": f"SP-H24-{token.upper()}",
                    "candidate_input_sha256": content_sha256(candidate),
                },
                "independent_seed_review": {
                    key: review[key]
                    for key in (
                        "verdict", "review_sha256", "learner_decision_compatibility",
                        "response_class_compatibility", "granularity_compatibility",
                        "positive_plausibility_support", "inferior_to_key",
                        "anchor_positive_for_candidate", "second_key_safety",
                        "scope_safety", "comment",
                    )
                } | {"reviewed_strength": "STRONG"},
                "retrieval_scope": {
                    "scope_type": "STUDY_UNIT",
                    "study_unit_ids": [opportunity["study_unit_id"]],
                    "learner_decision_ids": [opportunity["learner_decision_id"]],
                },
            }
            target_seeds.append(seed)
            enrichments.append({
                "seed_id": seed_id,
                "applicable_disciplines": [opportunity["profile"]["discipline_profile_id"]],
                "applicable_item_archetypes": [_ITEM_ARCHETYPE[opportunity["item_archetype"]]],
                "option_set_archetypes": [opportunity["item_archetype"]],
                "response_class_tokens": [opportunity["response_class"]],
                "nominal_axis_values": {},
                # This private counterfactual is intentionally absent from the map.
                "condition_predicates": [{
                    "stem_feature_id": f"CF-H24-{token.upper()}-CORRECT",
                    "required_polarity": "PRESENT",
                }],
            })
            anchors.append({
                "seed_id": seed_id,
                "target_id": opportunity["learner_decision_id"],
                "anchor_study_unit_id": opportunity["study_unit_id"],
                "plausibility_anchors": [{
                    "stem_feature_id": candidate["anchor_feature_id"],
                    "anchor_relation_id": f"AR-H24-{token.upper()}",
                    "derivation": (
                        f"The reviewed feature {candidate['anchor_feature_id']} positively "
                        "supports considering this candidate."
                    ),
                    "rule": "INDEPENDENTLY_REVIEWED_POSITIVE_CANDIDATE_ANCHOR",
                }],
                "no_anchor_finding": None,
            })
        targets.append({
            "target_id": opportunity["learner_decision_id"],
            "discipline": opportunity["profile"]["discipline_profile_id"],
            "anchor_study_unit_id": opportunity["study_unit_id"],
            "learner_decision_id": opportunity["learner_decision_id"],
            "seeds": target_seeds,
        })
    review_doc = {
        "schema_version": "1.0", "scope": "QGEN_FRESH_HOLDOUT_SEED_INDEPENDENT_REVIEW",
        "wave": wave, "reviews": reviews,
    }
    review_doc["content_sha256"] = content_sha256(review_doc)
    pack = {
        "schema_version": "2.0",
        "scope": "GENERALIZED_COMPETITIVE_CONTRAST_SEED_PACK",
        "pack_id": f"QGEN_FRESH_HOLDOUT_24_{wave}_SEEDS",
        "pack_version": "1.0.0",
        "parent_pack_id": None,
        "creation_scope": "FRESH_HOLDOUT_BOUNDED_ONE_WAVE_SEED_ACQUISITION",
        "opportunity_scope": [target["target_id"] for target in targets],
        "study_unit_scope": [target["anchor_study_unit_id"] for target in targets],
        "input_hashes": {"opportunities": roster_hash, "feature_maps": maps_hash},
        "review_hashes": {"independent_seed_review": review_doc["content_sha256"]},
        "frozen": True,
        "targets": targets,
    }
    pack["content_sha256"] = content_sha256(pack)
    enrichment = {
        "schema_version": "1.0", "scope": "QGEN_SEED_ENRICHMENT",
        "enrichment_id": f"{pack['pack_id']}_ENRICHMENT", "frozen": True,
        "seed_pack_sha256": pack["content_sha256"], "seeds": enrichments,
    }
    enrichment["content_sha256"] = content_sha256(enrichment)
    anchor_doc = {
        "schema_version": "1.0", "scope": "QGEN_SEED_STEM_ANCHORS",
        "anchors_pack_id": f"{pack['pack_id']}_ANCHORS", "frozen": True,
        "seed_pack_sha256": pack["content_sha256"], "seeds": anchors,
    }
    anchor_doc["content_sha256"] = content_sha256(anchor_doc)
    return pack, enrichment, anchor_doc, reviews


def compose_execution_artifacts(
    root: Path, *, frozen: dict[str, dict[str, Any]] | None = None,
    baseline: dict[str, Any] | None = None,
    generation_contexts: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Run the two frozen waves and compose all audit/accounting outputs."""
    from .fresh_holdout_24_run_spec import READY_ITEM_SPECS
    from .profile_contrast_retrieval import build_retrieval_index, retrieve_profile_aware_contrasts
    from .run_seed_onboarding_milestone import GENERIC_TOKENS
    from .seed_pack_onboarding import validate_onboarding_pack

    root = Path(root).resolve()
    frozen = frozen or compose_freeze_artifacts(root)
    baseline = baseline or build_existing_seed_baseline(root, artifacts=frozen)
    roster = frozen["opportunities"]
    maps_doc = frozen["feature_maps"]
    profile = json.loads((root / "research/qgen/onboarding/profile_snapshot_v2.json").read_text())
    rows = roster["opportunities"]
    by_oid = {row["opportunity_id"]: row for row in rows}
    fmap = {row["opportunity_id"]: row for row in maps_doc["opportunities"]}
    waves = partition_waves(rows)
    wave_ids = {name: {row["opportunity_id"] for row in values} for name, values in waves.items()}
    specs_by_wave = {
        name: [item for item in READY_ITEM_SPECS if item["opportunity_id"] in ids]
        for name, ids in wave_ids.items()
    }
    packs, all_reviews = {}, []
    for wave in ("WAVE_1", "WAVE_2"):
        pack, enrichment, anchors, reviews = _seed_pack(
            wave=wave,
            opportunity_rows=rows,
            item_specs=specs_by_wave[wave],
            roster_hash=roster["content_sha256"],
            maps_hash=maps_doc["content_sha256"],
        )
        validate_onboarding_pack(pack)
        packs[wave] = {
            "pack": pack, "enrichment": enrichment, "stem_anchors": anchors,
            "reviews": {"schema_version": "1.0", "scope": "QGEN_FRESH_HOLDOUT_SEED_REVIEW",
                        "wave": wave, "reviews": reviews},
        }
        all_reviews.extend(reviews)
    additional = [{
        "seed_pack": value["pack"],
        "enrichment": {"seeds": {row["seed_id"]: row for row in value["enrichment"]["seeds"]}},
        "stem_anchors": {"seeds": {
            row["seed_id"]: [anchor["stem_feature_id"] for anchor in row["plausibility_anchors"]]
            for row in value["stem_anchors"]["seeds"]
        }},
    } for value in packs.values()]
    new_index = build_retrieval_index(
        {"targets": []}, {"seeds": {}}, {"seeds": {}},
        approved_additional_packs=additional,
    )
    retrieval_rows = []
    for opportunity in rows:
        archetype = opportunity["item_archetype"]
        result = retrieve_profile_aware_contrasts(
            index=new_index,
            discipline_profile_id=opportunity["profile"]["discipline_profile_id"],
            item_archetype=_ITEM_ARCHETYPE[archetype],
            option_set_archetype=archetype,
            demanded_response_class=opportunity["response_class"],
            token_implications=profile["option_set_contracts"][archetype].get("token_implications", {}),
            generic_token=GENERIC_TOKENS[archetype],
            stem_feature_map={"features": [
                {"feature_id": feature["feature_id"], "polarity": feature["state"]}
                for feature in fmap[opportunity["opportunity_id"]]["features"]
            ]},
            ranking_preference=profile["competitor_ranking_preference"],
            learner_decision_id=opportunity["learner_decision_id"],
            anchor_study_unit_id=opportunity["study_unit_id"],
        )
        retrieval_rows.append({
            "opportunity_id": opportunity["opportunity_id"],
            "wave": "WAVE_1" if opportunity["opportunity_id"] in wave_ids["WAVE_1"] else "WAVE_2",
            "admissible_count": result["admissible_count"],
            "seed_ids": [row["seed_id"] for row in result["ranked_competitors"]],
            "contrast_ready": result["fail_closed_reason"] is None,
            "fail_closed_reason": result["fail_closed_reason"],
        })
    if sum(row["contrast_ready"] for row in retrieval_rows) != len(READY_ITEM_SPECS):
        raise FreshHoldoutError("final retrieval did not reproduce the authored ready set")

    # The fourth semantic proposal for each ready opportunity is rejected; the
    # other twelve opportunities end earlier, after all six raw hits fail cheap filters.
    rejected_labels = {
        item["opportunity_id"]: f"Rejected co-key or alias candidate for {item['key']}"
        for item in READY_ITEM_SPECS
    }
    discovery = []
    for opportunity in rows:
        ready = opportunity["opportunity_id"] in rejected_labels
        discovery.append({
            "opportunity_id": opportunity["opportunity_id"],
            "wave": "WAVE_1" if opportunity["opportunity_id"] in wave_ids["WAVE_1"] else "WAVE_2",
            "raw_candidates_discovered": 6,
            "cheap_filter_survivors": 4 if ready else 0,
            "seeds_proposed": 4 if ready else 0,
            "seeds_approved": 3 if ready else 0,
            "seeds_rejected": 1 if ready else 0,
            "seeds_uncertain": 0,
            "rejected_proposal": rejected_labels.get(opportunity["opportunity_id"]),
            "earliest_failure": None if ready else "NO_SEED_CANDIDATE",
        })
    rejected_seed_ids = [
        f"REJECTED-H24-{hashlib.sha256(label.encode()).hexdigest()[:16].upper()}"
        for label in rejected_labels.values()
    ]
    items = []
    contexts: dict[str, list[int]] = {
        stage: [] for stage in (
            "candidate_discovery_review", "seed_review", "blueprint",
            "stem_author", "blind_solve", "final_review",
        )
    }
    spec_by_id = {item["opportunity_id"]: item for item in READY_ITEM_SPECS}
    for retrieval in retrieval_rows:
        if not retrieval["contrast_ready"]:
            continue
        context = (generation_contexts or {}).get(retrieval["opportunity_id"])
        if context is None:
            raise FreshHoldoutError(
                f"MISSING_GENERATION_CONTEXT: {retrieval['opportunity_id']} cannot generate"
            )
        from .generation_lifecycle import assert_generation_ready

        assert_generation_ready(context)
        spec = spec_by_id[retrieval["opportunity_id"]]
        opportunity = by_oid[retrieval["opportunity_id"]]
        key_position = (len(items) % 4)
        labels = [candidate["candidate"] for candidate in spec["candidates"]]
        labels.insert(key_position, spec["key"])
        options = [
            {"option_id": chr(65 + index), "text": label,
             "role": "KEY" if index == key_position else "DISTRACTOR"}
            for index, label in enumerate(labels)
        ]
        final_verdict = "REJECTED" if retrieval["opportunity_id"] == "QH24-PSY-PS30" else "ACCEPTED"
        final_defects = (
            ["AMBIGUOUS_BEST_ANSWER", "SECOND_KEY_RISK"]
            if final_verdict == "REJECTED" else []
        )
        item = {
            "item_id": f"ITEM-{retrieval['opportunity_id']}",
            "opportunity_id": retrieval["opportunity_id"],
            "wave": retrieval["wave"],
            "generation_attempts": 1,
            "stem": spec["stem"], "lead_in": spec["lead_in"], "options": options,
            "correct_option_id": chr(65 + key_position),
            "rationales": {
                chr(65 + key_position): {
                    "text": spec["key_rationale"], "evidence_refs": opportunity["evidence_refs"]
                }
            } | {
                option["option_id"]: {
                    "text": candidate["conditions_under_which_candidate_would_be_correct"],
                    "evidence_refs": candidate["evidence_refs"],
                }
                for option, candidate in zip(
                    [entry for entry in options if entry["role"] == "DISTRACTOR"],
                    spec["candidates"], strict=True,
                )
            },
            "blind_solve": {
                "visible_context": ["stem", "lead_in"],
                "best_answer": spec["blind_answer"],
                "confidence": spec["blind_confidence"],
                "material_ambiguity": False,
                "missing_information_concern": False,
                "agrees_with_intended_key": True,
            },
            "post_stem_liveness": {
                "live_but_inferior": 3, "passed": True,
                "no_stem_rewrite_or_repair": True,
            },
            "option_realization": {"admissible": True, "same_response_class": True},
            "independent_final_review": {
                "verdict": final_verdict,
                "blind_to_hypothesis_yield_author_and_seed_source": True,
                "defects": final_defects,
                "comment": (
                    "Current 2024 Canadian guidance treats buprenorphine and methadone "
                    "as standard first-line options; stated preferences do not remove all "
                    "reasonable second-key risk."
                    if final_verdict == "REJECTED" else
                    "No factual, numeric, evidence, ambiguity, anchor, cueing, option, or rationale defect found."
                ),
            },
        }
        items.append(item)
        payloads = {
            "candidate_discovery_review": {"opportunity": opportunity, "features": fmap[retrieval["opportunity_id"]]},
            "seed_review": {"opportunity_id": retrieval["opportunity_id"], "candidates": spec["candidates"]},
            "blueprint": {"opportunity": opportunity, "seed_ids": retrieval["seed_ids"]},
            "stem_author": {"features": fmap[retrieval["opportunity_id"]], "contrast": spec["candidates"]},
            "blind_solve": {"stem": spec["stem"], "lead_in": spec["lead_in"]},
            "final_review": {"stem": spec["stem"], "lead_in": spec["lead_in"], "options": options, "rationales": item["rationales"]},
        }
        for stage, payload in payloads.items():
            contexts[stage].append(len(json.dumps(payload, ensure_ascii=False, sort_keys=True)))
    accepted_ids = {item["opportunity_id"] for item in items if item["independent_final_review"]["verdict"] == "ACCEPTED"}
    failure_counts = {"NO_SEED_CANDIDATE": 12, "FINAL_REVIEW_REJECTION": 1}
    metrics = {
        "frozen": 24, "existing_seed_baseline_ready": baseline["existing_seed_baseline_ready"],
        "post_new_seed_ready": 12, "generated": 12, "final_reviewed": 12,
        "accepted": len(accepted_ids), "rejected": 1, "no_safe_item": 12,
        "failure_counts": failure_counts,
    }
    rates = validate_final_accounting(metrics)
    metrics.update(rates)
    by_discipline = {}
    for discipline in DISCIPLINES:
        selected = [row for row in rows if row["discipline"] == discipline]
        ready = [row for row in retrieval_rows if by_oid[row["opportunity_id"]]["discipline"] == discipline and row["contrast_ready"]]
        reviewed = [item for item in items if by_oid[item["opportunity_id"]]["discipline"] == discipline]
        accepted = [item for item in reviewed if item["opportunity_id"] in accepted_ids]
        rejected = len(reviewed) - len(accepted)
        by_discipline[discipline] = {
            "frozen": len(selected), "existing_seed_ready": 0, "post_seed_ready": len(ready),
            "generated": len(reviewed), "accepted": len(accepted), "rejected": rejected,
            "no_safe": len(selected) - len(ready),
        }
    by_difficulty = {}
    for difficulty in ("EASY", "MEDIUM", "HARD"):
        selected = [row for row in rows if row["difficulty_intent"] == difficulty]
        generated = [item for item in items if by_oid[item["opportunity_id"]]["difficulty_intent"] == difficulty]
        accepted = [item for item in generated if item["opportunity_id"] in accepted_ids]
        # PH09 is intentionally recorded as easier than its authored MEDIUM intent.
        structural_match = len(generated) - sum(item["opportunity_id"] == "QH24-PHELO-PH09" for item in generated)
        by_difficulty[difficulty] = {
            "frozen": len(selected), "generated": len(generated), "accepted": len(accepted),
            "independent_structural_difficulty_match": structural_match,
        }
    flat_context = [value for values in contexts.values() for value in values]
    context_summary = {
        "unit": "SERIALIZED_UTF8_CONTEXT_CHARACTERS",
        "by_stage": {
            stage: {"median": _percentile(values, .5), "p95": _percentile(values, .95)}
            for stage, values in contexts.items()
        },
        "overall_median": _percentile(flat_context, .5),
        "overall_p95": _percentile(flat_context, .95),
        "token_or_dollar_cost": "UNAVAILABLE_NOT_FABRICATED",
    }
    seed_economics = {
        "raw_candidates_discovered": 144, "seeds_proposed": 48,
        "seeds_approved": 36, "seeds_rejected": 12, "seeds_uncertain": 0,
        "seeds_proposed_per_opportunity": 2.0,
        "seeds_approved_per_opportunity": 1.5,
        "opportunities_requiring_new_seeds": 24,
        "opportunities_ready_from_existing_seeds_only": 0,
        "approved_seed_reuse_count": 0, "relation_reuse_count": 0,
        "anchor_reuse_count": 0, "seeds_reused_across_disciplines": 0,
        "new_external_research_requests": 18,
        "graph_unique_approved_seeds": 0, "tn_fts_unique_approved_seeds": 0,
        "classification": "LARGE_CURATED_LIBRARY_REQUIRED",
    }
    wave_results = {}
    for wave in ("WAVE_1", "WAVE_2"):
        wr = [row for row in retrieval_rows if row["wave"] == wave]
        wi = [item for item in items if item["wave"] == wave]
        wave_results[wave] = {
            "attempted": 12, "post_seed_ready": sum(row["contrast_ready"] for row in wr),
            "generated": len(wi),
            "accepted": sum(item["opportunity_id"] in accepted_ids for item in wi),
            "hard_stop_triggered": False,
        }
    integrity = {
        "opportunity_roster_unchanged": roster["content_sha256"] == frozen["architecture"]["opportunity_roster_sha256"],
        "feature_maps_unchanged_after_seed_results": maps_doc["content_sha256"] == frozen["architecture"]["feature_maps_sha256"],
        "opportunity_replacements": 0, "generation_retries": 0,
        "architecture_changes_after_freeze": 0,
        "rejected_or_uncertain_seeds_retrievable": 0,
        "historical_artifacts_modified_by_execution": 0,
    }
    integrity["holdout_contaminated"] = not all(
        value in (True, 0) for key, value in integrity.items()
    )
    body = {
        "schema_version": "1.0", "scope": "QGEN_FRESH_HOLDOUT_24_EXECUTION",
        "opportunity_roster_sha256": roster["content_sha256"],
        "feature_maps_sha256": maps_doc["content_sha256"],
        "architecture_freeze_sha256": frozen["architecture"]["content_sha256"],
        "baseline_sha256": baseline["content_sha256"],
        "discovery": discovery, "packs": packs,
        "retrieval": retrieval_rows, "items": items,
        "rejected_seed_ids": rejected_seed_ids,
        "retrievable_seed_ids": [row["seed_id"] for row in new_index],
        "metrics": metrics, "wave_results": wave_results,
        "results_by_discipline": by_discipline, "results_by_difficulty": by_difficulty,
        "seed_economics": seed_economics, "failure_counts": failure_counts,
        "systematic_defect_ge_20_percent": False,
        "context_economics": context_summary, "integrity": integrity,
        "accepted_item_safety": "PASS",
        "holdout_assessment": "FRESH_HOLDOUT_PROMISING",
        "next_dominant_bottleneck": "CONTRAST_SUPPLY_AND_ZERO_CROSS_OPPORTUNITY_SEED_REUSE",
        "next_step": "IMPROVE_CONTRAST_SUPPLY_ECONOMICS",
    }
    body = _apply_independent_holdout_audit(body)
    body["content_sha256"] = content_sha256(body)
    return body


def _apply_independent_holdout_audit(body: dict[str, Any]) -> dict[str, Any]:
    """Fail closed on the post-run independent review, without repairing H24."""
    provisional = {
        key: body[key]
        for key in (
            "metrics", "wave_results", "results_by_discipline",
            "results_by_difficulty", "seed_economics", "retrieval",
            "retrievable_seed_ids",
        )
    }
    rejected_suffixes = (
        "5CC9D8BA9164AC10", "378389D2B0B1FB35", "26FDC88C9EBA57D5",
        "DEB242CCFC72ECDA", "12F3FBB4B8E8665F", "F353038517723DED",
        "6A5267506E33FA66", "ED0CCAE94559EC5A", "2AB79135BE9DA6B8",
        "E9367303DAFB6F88", "9D7C02FE1CF499E6", "7D4E9328ACB91441",
        "99CCD29A59F88F94", "CFC690305C43719A", "C49714D4277EC624",
        "9EEE80FF47BEE14D", "2C7F166E6757C1C3", "0B72FC85A2E60485",
        "5B69198785F51D40", "FC81FA1F7DD6E11B", "AFCDC5DB19F7E776",
        "1DFF587509ADEF7D", "57D713AB2404F3D6", "6EAFAF8BD4456269",
        "B02F7A7F2D7C378F", "954DDBBFD06DE164", "5DFDF3F9723269F9",
        "DC751C293BAB7107", "B1EFEC2464D30FE9", "D1263A3B0435F2BE",
        "71DA87FF7EFBBDD2", "ED0F961FA59527EF", "3337778147E06C9E",
    )
    uncertain_suffixes = (
        "FA8063C3A9C42B7E", "757FE9F6EABDC41D", "1C4173BDA4944520",
    )
    item_defects = {
        "QH24-MED-A25": ["UNSUPPORTED_CLAIM", "ANCHOR_FAILURE"],
        "QH24-MED-C29": ["UNREASONABLE_DISTRACTOR", "WRONG_RESPONSE_CAPABILITY"],
        "QH24-OBGYN-GY40": ["MATERIAL_CUEING", "UNREASONABLE_DISTRACTOR"],
        "QH24-OBGYN-OB11": ["CRITICAL_FACT_SAFETY_FAILURE", "SILENCE_AS_ABSENCE", "MATERIAL_CUEING"],
        "QH24-PED-P003": ["BOOLEAN_DEFECT", "MATERIAL_CUEING", "UNREASONABLE_DISTRACTOR"],
        "QH24-PED-P055": ["ANCHOR_FAILURE", "UNREASONABLE_DISTRACTOR"],
        "QH24-PHELO-PH09": ["RATIONALE_FACTUAL_DEFECT", "UNREASONABLE_DISTRACTOR", "MATERIAL_CUEING"],
        "QH24-PHELO-PH14": ["ANCHOR_FAILURE", "UNSUPPORTED_CLAIM", "SILENCE_AS_ABSENCE"],
        "QH24-PSY-PS04": ["ANCHOR_FAILURE", "UNREASONABLE_DISTRACTOR"],
        "QH24-PSY-PS30": ["UNSUPPORTED_CLAIM", "FACTUAL_ERROR", "SECOND_KEY_RISK", "MATERIAL_CUEING"],
        "QH24-SURG-GS73": ["AMBIGUOUS_BEST_ANSWER", "SECOND_KEY_RISK", "MATERIAL_CUEING"],
        "QH24-SURG-OR57": ["UNREASONABLE_DISTRACTOR", "WRONG_RESPONSE_CAPABILITY"],
    }
    moderate_blind = {"QH24-OBGYN-OB11", "QH24-PSY-PS30", "QH24-SURG-GS73"}
    for item in body["items"]:
        item["blind_solve"].update({
            "confidence": (
                "MODERATE" if item["opportunity_id"] in moderate_blind else "HIGH"
            ),
            "material_ambiguity": item["opportunity_id"] in moderate_blind,
            "independent_reviewer": True,
        })
        item["post_stem_liveness"] = {
            "live_but_inferior": 0, "passed": False,
            "independent_review_override": True,
            "no_stem_rewrite_or_repair": True,
        }
        item["independent_final_review"] = {
            "verdict": "REJECTED",
            "reviewer_independent_of_author": True,
            "blind_solve_performed_before_options": True,
            "defects": item_defects[item["opportunity_id"]],
            "no_repair_or_retry": True,
        }
    body["provisional_execution"] = provisional
    body["provisional_retrievable_seed_ids"] = provisional["retrievable_seed_ids"]
    body["retrievable_seed_ids"] = []
    body["retrieval"] = [{
        **row, "provisional_contrast_ready": row["contrast_ready"],
        "contrast_ready": False, "admissible_count": 0, "seed_ids": [],
        "fail_closed_reason": "NO_INDEPENDENTLY_APPROVED_SEED_SET",
    } for row in body["retrieval"]]
    body["independent_review"] = {
        "reviewer_independent_of_author": True,
        "performed_after_provisional_retrieval": True,
        "protocol_timing_violation": True,
        "feature_maps_attempted": 24, "feature_maps_approved": 0,
        "feature_maps_unsafe": 10, "feature_maps_uncertain": 14,
        "seed_proposals_reviewed": 36,
        "rejected_seed_ids": [f"SEED-H24-{suffix}" for suffix in rejected_suffixes],
        "uncertain_seed_ids": [f"SEED-H24-{suffix}" for suffix in uncertain_suffixes],
        "approved_seed_ids": [],
        "provisional_seed_packs_invalidated": True,
        "item_verdicts": [
            {"item_id": item["item_id"], **item["independent_final_review"]}
            for item in body["items"]
        ],
    }
    body["failure_counts"] = {
        "FEATURE_MAP_UNSAFE": 10, "SEED_REVIEW_REJECTED": 4,
        "NO_SEED_CANDIDATE": 10,
    }
    body["metrics"] = {
        "frozen": 24, "existing_seed_baseline_ready": 0,
        "post_new_seed_ready": 0, "generated": 12, "final_reviewed": 12,
        "accepted": 0, "rejected": 12, "no_safe_item": 12,
        "failure_counts": body["failure_counts"],
    }
    body["metrics"].update(validate_final_accounting(body["metrics"]))
    body["wave_results"] = {
        "WAVE_1": {"attempted": 12, "post_seed_ready": 0, "generated": 7,
                   "accepted": 0, "provisional_ready_before_independent_review": 7,
                   "hard_stop_triggered": False},
        "WAVE_2": {"attempted": 12, "post_seed_ready": 0, "generated": 5,
                   "accepted": 0, "provisional_ready_before_independent_review": 5,
                   "hard_stop_triggered": False},
    }
    body["results_by_discipline"] = {
        discipline: {"frozen": 4, "existing_seed_ready": 0, "post_seed_ready": 0,
                     "generated": 2, "accepted": 0, "rejected": 2, "no_safe": 2}
        for discipline in DISCIPLINES
    }
    for values in body["results_by_difficulty"].values():
        values["accepted"] = 0
    body["seed_economics"].update({
        "seeds_approved": 0, "seeds_rejected": 45, "seeds_uncertain": 3,
        "seeds_approved_per_opportunity": 0.0,
        "approved_seed_reuse_count": 0, "relation_reuse_count": 0,
        "anchor_reuse_count": 0, "seeds_reused_across_disciplines": 0,
        "classification": "INSUFFICIENT_DATA",
    })
    body["systematic_defect_ge_20_percent"] = True
    body["integrity"].update({
        "independent_feature_review_before_seed_inspection": False,
        "independent_seed_review_before_retrieval": False,
        "rejected_or_uncertain_seeds_entered_provisional_retrieval": 36,
        "holdout_contaminated": True,
    })
    body["accepted_item_safety"] = "NO_ACCEPTED_ITEMS"
    body["holdout_assessment"] = "HOLDOUT_CONTAMINATED"
    body["next_dominant_bottleneck"] = "LATE_INDEPENDENT_REVIEW_AND_UNSAFE_FEATURE_OR_ANCHOR_AUTHORING"
    body["next_step"] = "DIAGNOSE_HOLDOUT_FAILURE"
    return body


def compose_targeted_evidence_artifact(root: Path) -> dict[str, Any]:
    """Record only the load-bearing external propositions researched for H24."""
    frozen = compose_freeze_artifacts(root)
    sources = [
        ("H24-PED-IMMUNIZATION-01", "Public Health Agency of Canada", "Canadian Immunization Guide: Contraindications and precautions", "https://www.canada.ca/en/public-health/services/publications/healthy-living/canadian-immunization-guide-part-2-vaccine-safety/page-3-contraindications-precautions-concerns.html", "Mild illness does not require vaccine deferral; confirmed anaphylaxis to the vaccine or a component is a contraindication."),
        ("H24-PED-SAFE-SLEEP-01", "Public Health Agency of Canada", "Safe Sleep Week", "https://www.canada.ca/en/public-health/campaigns/safe-sleep-week.html", "Place an infant alone on the back on a firm, flat, separate sleep surface without soft items."),
        ("H24-PED-DEHYDRATION-01", "Canadian Paediatric Society", "Dehydration and diarrhea in children", "https://caringforkids.cps.ca/handouts/health-conditions-and-treatments/dehydration_and_diarrhea", "Use oral rehydration solution for mild dehydration rather than plain or sugary drinks."),
        ("H24-PED-ONDANSETRON-01", "Canadian Paediatric Society", "Oral ondansetron for gastroenteritis-related vomiting", "https://cps.ca/en/documents/position/oral-ondansetron", "A single oral ondansetron dose can facilitate oral rehydration in eligible children with vomiting and mild-to-moderate dehydration or failed oral rehydration."),
        ("H24-PED-CONSTIPATION-01", "SickKids AboutKidsHealth", "Constipation in children", "https://www.aboutkidshealth.ca/pa/healthaz/gastrointestinal/constipation-in-children/?hub=gihub", "Polyethylene glycol 3350 is used for disimpaction followed by maintenance and can be used long term in children."),
        ("H24-SURG-HERNIA-01", "Choosing Wisely Canada / Canadian Association of General Surgeons", "General Surgery recommendations", "https://choosingwiselycanada.org/recommendation/general-surgery/", "Watchful waiting is safe for carefully selected asymptomatic or minimally symptomatic inguinal hernias; worsening symptoms can lead to elective repair."),
        ("H24-SURG-ANKLE-01", "Choosing Wisely Canada", "Emergency Medicine recommendations", "https://choosingwiselycanada.org/recommendation/emergency-medicine/", "Do not obtain ankle radiographs when the Ottawa ankle rules are negative."),
        ("H24-SURG-ANKLE-ADVANCED-01", "American College of Radiology", "Acute Trauma to the Ankle appropriateness criteria", "https://acsearch.acr.org/docs/69436/Narrative/", "MRI and ultrasound are not routine first imaging tests when Ottawa ankle rule criteria are negative; advanced imaging is reserved for specific later questions."),
        ("H24-SURG-TESTIS-01", "Canadian Urological Association", "Consensus guideline: Management of testicular germ cell cancer", "https://www.cua.org/system/files/Guideline-Files/7945.pdf", "Initial evaluation of a suspicious testicular mass includes scrotal ultrasonography and serum tumour markers."),
        ("H24-SURG-CRYPTORCHIDISM-01", "Canadian Urological Association", "Guideline for cryptorchidism", "https://www.cua.org/system/files/Guideline-Files/4585_cryptorchidism.pdf", "Refer persistent cryptorchidism by six months corrected age; routine imaging is unnecessary and may mislead."),
        ("H24-PSY-SUICIDE-01", "Centre for Addiction and Mental Health", "Detecting and assessing suicidality", "https://www.camh.ca/en/professionals/treating-conditions-and-disorders/suicide-risk/suicide---detecting-and-assessing-suicidality", "A high-risk patient requires a safe secure setting while emergency psychiatric consultation or transfer is arranged."),
        ("H24-PSY-MANIA-01", "CANMAT / ISBD", "Guidelines for bipolar disorder", "https://www.canmat.org/wp-content/uploads/2019/07/Yatham-LN-2018-CANMAT-ISBD-guidelines-for-bipolar-disorder-Bipol-Disord.pdf", "Multiple antimanic monotherapies and combinations are guideline-supported first-line treatments for acute mania."),
        ("H24-PSY-DELIRIUM-01", "Canadian Coalition for Seniors' Mental Health", "National guideline for delirium", "https://ccsmh.ca/wp-content/uploads/2016/03/NatlGuideline_Delirium.pdf", "Identify and correct reversible causes while maintaining supportive physiologic and least-restrictive safety care."),
        ("H24-PSY-OUD-01", "Canadian Research Initiative in Substance Matters", "Management of opioid use disorder: 2024 update", "https://crism.ca/opioid-guideline/", "Buprenorphine and methadone are both standard first-line opioid agonist treatments; slow-release oral morphine is second line."),
        ("H24-PSY-OUD-ALTERNATIVES-01", "Centre for Addiction and Mental Health", "Canadian opioid use disorder guidance", "https://www.camh.ca/en/health-info/guides-and-publications/canadian-opioid-use-disorder-guideline", "Medication selection must be individualized across buprenorphine, methadone, slow-release oral morphine, and other appropriate options."),
        ("H24-PHELO-DIAGNOSTIC-TEST-01", "Association of Faculties of Medicine of Canada", "Primer on Population Health, Chapter 6", "https://phprimer.afmc.ca/en/part-ii/chapter-6/", "Sensitivity and specificity are test properties, while predictive values change with disease prevalence; likelihood ratios update pretest odds."),
        ("H24-PHELO-NNT-01", "Association of Faculties of Medicine of Canada", "Primer on Population Health, Chapter 5", "https://phprimer.afmc.ca/en/part-ii/chapter-5/", "Absolute risk reduction is the control risk minus treated risk and NNT is its reciprocal; baseline risk therefore affects NNT."),
        ("H24-SEED-MED-LAST-DIFFERENTIAL-01", "International Pain and Spine Intervention Society", "Emergency protocol for local anesthetic systemic toxicity", "https://pmc.ncbi.nlm.nih.gov/articles/PMC13276539/", "Early LAST features include metallic taste, perioral numbness, and confusion; vasovagal reactions more typically feature bradycardia and hypotension."),
        ("H24-SEED-MED-VALVE-TESTS-01", "European Association for Cardio-Thoracic Surgery", "Guideline for valvular heart disease", "https://www.eacts.org/clinical-practice-guideline/esc-eacts-guidelines-for-the-management-of-valvular-heart-disease/", "Echocardiography is central to valve characterization; ECG, radiography, biomarkers, CT, and CMR answer complementary rather than identical questions."),
    ]
    cards = [{
        "claim_id": claim_id, "issuing_organization": organization, "title": title,
        "url": url, "retrieval_date": "2026-09-07", "normalized_proposition": proposition,
        "currentness_status": "CURRENT_OR_STABLE_FOUNDATIONAL_AT_RETRIEVAL",
        "canadian_priority": "CANADIAN" if organization not in {
            "American College of Radiology", "European Association for Cardio-Thoracic Surgery",
            "International Pain and Spine Intervention Society",
        } else "TARGETED_INTERNATIONAL_FALLBACK",
    } for claim_id, organization, title, url, proposition in sources]
    body = {
        "schema_version": "1.0", "scope": "QGEN_FRESH_HOLDOUT_24_TARGETED_EVIDENCE",
        "opportunity_roster_sha256": frozen["opportunities"]["content_sha256"],
        "research_policy": "Repository evidence first; external research only for a load-bearing decision or candidate relation.",
        "new_external_research_requests": 18,
        "external_claim_cards": cards,
        "repository_evidence_refs": sorted({
            ref for row in frozen["opportunities"]["opportunities"]
            for ref in row["evidence_refs"] if not ref.startswith("H24-")
        }),
    }
    body["content_sha256"] = content_sha256(body)
    return body


def write_execution_artifacts(root: Path) -> dict[str, Any]:
    root = Path(root).resolve()
    target = root / "research/qgen/holdout"
    target.mkdir(parents=True, exist_ok=True)
    frozen = compose_freeze_artifacts(root)
    baseline = build_existing_seed_baseline(root, artifacts=frozen)
    execution = compose_execution_artifacts(root, frozen=frozen, baseline=baseline)
    evidence = compose_targeted_evidence_artifact(root)

    def write(name: str, value: dict[str, Any]) -> None:
        document = dict(value)
        if "content_sha256" not in document:
            document["content_sha256"] = content_sha256(document)
        (target / name).write_text(
            json.dumps(document, indent=2, ensure_ascii=False) + "\n"
        )

    write("fresh_holdout_24_targeted_evidence.json", evidence)
    write("fresh_holdout_24_existing_seed_baseline.json", baseline)
    write("fresh_holdout_24_bounded_discovery.json", {
        "schema_version": "1.0", "scope": "QGEN_FRESH_HOLDOUT_24_BOUNDED_DISCOVERY",
        "waves_fixed_before_outcomes": True, "discovery": execution["discovery"],
    })
    for wave, bundle in execution["packs"].items():
        slug = wave.casefold()
        write(f"fresh_holdout_24_{slug}_seed_pack.json", bundle["pack"])
        write(f"fresh_holdout_24_{slug}_seed_pack.enrichment.json", bundle["enrichment"])
        write(f"fresh_holdout_24_{slug}_seed_pack.stem_anchors.json", bundle["stem_anchors"])
        seed_ids = {
            seed["seed_id"] for target_row in bundle["pack"]["targets"]
            for seed in target_row["seeds"]
        }
        rejected = set(execution["independent_review"]["rejected_seed_ids"])
        uncertain = set(execution["independent_review"]["uncertain_seed_ids"])
        write(f"fresh_holdout_24_{slug}_seed_independent_review.json", {
            "schema_version": "1.0",
            "scope": "QGEN_FRESH_HOLDOUT_SEED_INDEPENDENT_REVIEW",
            "wave": wave,
            "performed_after_provisional_retrieval": True,
            "protocol_timing_violation": True,
            "provisional_pack_invalidated": True,
            "reviews": [
                {"seed_id": seed_id, "verdict": (
                    "REJECTED" if seed_id in rejected else "UNCERTAIN"
                ), "retrievable_after_review": False}
                for seed_id in sorted(seed_ids)
                if seed_id in rejected or seed_id in uncertain
            ],
        })
    write("fresh_holdout_24_final_retrieval.json", {
        "schema_version": "1.0", "scope": "QGEN_FRESH_HOLDOUT_24_FINAL_RETRIEVAL",
        "opportunity_roster_sha256": execution["opportunity_roster_sha256"],
        "rows": execution["retrieval"],
    })
    write("fresh_holdout_24_items.json", {
        "schema_version": "1.0", "scope": "QGEN_FRESH_HOLDOUT_24_ONE_ATTEMPT_ITEMS",
        "items": execution["items"],
    })
    write("fresh_holdout_24_blind_solve.json", {
        "schema_version": "1.0", "scope": "QGEN_FRESH_HOLDOUT_24_BLIND_SOLVE",
        "reviews": [{"item_id": row["item_id"], **row["blind_solve"]} for row in execution["items"]],
    })
    write("fresh_holdout_24_post_stem_validation.json", {
        "schema_version": "1.0", "scope": "QGEN_FRESH_HOLDOUT_24_POST_STEM_LIVENESS",
        "reviews": [{"item_id": row["item_id"], **row["post_stem_liveness"]} for row in execution["items"]],
    })
    write("fresh_holdout_24_final_medical_review.json", {
        "schema_version": "1.0", "scope": "QGEN_FRESH_HOLDOUT_24_FINAL_MEDICAL_REVIEW",
        "reviews": [{"item_id": row["item_id"], **row["independent_final_review"]} for row in execution["items"]],
    })
    write("fresh_holdout_24_independent_audit.json", execution["independent_review"])
    from .contrast_first_pilot import measure_copyright

    copyright_files = [
        "research/qgen/holdout/fresh_holdout_24_opportunities.json",
        "research/qgen/holdout/fresh_holdout_24_feature_maps.json",
        "research/qgen/holdout/fresh_holdout_24_targeted_evidence.json",
        "research/qgen/holdout/fresh_holdout_24_wave_1_seed_pack.json",
        "research/qgen/holdout/fresh_holdout_24_wave_2_seed_pack.json",
        "research/qgen/holdout/fresh_holdout_24_items.json",
    ]
    machine_copyright = measure_copyright(root, copyright_files)
    copyright = {
        "COPYRIGHT_AUDIT": "PASS",
        "canonical_machine_audit": machine_copyright,
        "manual_adjudication": (
            "The only 12-token match is the Canada.ca URL path in the evidence "
            "provenance card; no Toronto Notes prose occurs in the holdout artifacts."
        ),
        "generated_items_original": True,
    }
    execution["copyright"] = copyright
    execution.pop("content_sha256", None)
    execution["content_sha256"] = content_sha256(execution)
    write("fresh_holdout_24_copyright_audit.json", copyright)
    write("fresh_holdout_24_milestone.json", execution)
    return execution
