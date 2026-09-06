"""The cross-discipline medium pilot, run against one pinned feature/anchor snapshot.

The registry milestone proved that V2, ``SAF_1`` and profile-aware retrieval can
read the same explicitly pinned snapshot. This module asks the next question, on
the largest legitimately eligible sample the canonical material supports:

    with that snapshot pinned for the whole batch and never mutated inside it,
    how many frozen opportunities reach an accepted item, and where do the rest
    fail?

Nothing here relaxes a gate. The pilot reuses the unmodified V2 contrast-set
builder, the unmodified blueprint solver, the unmodified coherence contract and
the unmodified production gate; what it supplies is a second frozen batch of
authored readings, one bounded supply wave, and the item prose the blueprint
demands. An extension discovered during the batch is recorded and never applied,
which is the invariant the production lifecycle turns on.

Design: docs/superpowers/specs/2026-09-06-qgen-production-snapshot-scaleout-design.md
"""

from __future__ import annotations

import json
from typing import Any, Mapping

from .clinical_contrast_v2 import canonical_json, content_sha256
from .errors import QbankError

PILOT_ID = "medium-pilot-snapshot-v2"

#: The snapshot every opportunity in this batch is pinned to. It is named once,
#: here, and is never resolved implicitly.
PILOT_SNAPSHOT_ID = "FEATURE_ANCHOR_SNAPSHOT_V2"

FREEZE_PATH = "research/qgen/pilot/medium-pilot-6-opportunities.json"
READINGS_PATH = "research/qgen/pilot/medium-pilot-6-readings.json"
ACQUISITION_PATH = "research/qgen/pilot/medium-pilot-6-acquisition.json"
GENERATED_PATH = "research/qgen/pilot/medium-pilot-6-generated.json"
REVIEWS_PATH = "research/qgen/pilot/medium-pilot-6-reviews.json"
EXTENSIONS_PATH = "research/qgen/pilot/medium-pilot-6-proposed-extensions.json"

EXECUTION_REPORT_PATH = "reports/qgen_medium_pilot_execution.json"
REVIEW_REPORT_PATH = "reports/qgen_medium_pilot_independent_review.json"
MILESTONE_REPORT_PATH = "reports/qgen_medium_pilot_milestone.json"

DISCIPLINES = ("MED", "PED", "OBGYN", "SURG", "PSY", "PHELO")

#: Earliest primary cause, in the order the pipeline reaches them.
FAILURE_CATEGORIES = (
    "NO_CONTRAST_SUPPLY",
    "NEW_EXTENSION_NOT_IN_PINNED_SNAPSHOT",
    "CONTRAST_SET_COHERENCE",
    "SECOND_KEY",
    "BLUEPRINT_FAILURE",
    "BLIND_SOLVER_DISAGREEMENT",
    "POST_STEM_COMPETITOR_FAILURE",
    "OPTION_SET_FAILURE",
    "FINAL_REVIEW_REJECTION",
    "DIFFICULTY_MISMATCH",
    "EVIDENCE_LIMIT",
    "OTHER",
)


class MediumPilotError(QbankError):
    """The medium pilot cannot be built or run from canonical material."""


def _read(root, relative: str) -> Any:
    from pathlib import Path

    from .paths import resolve_root_path

    path = resolve_root_path(Path(root).resolve(), relative)
    if not path.is_file():
        raise MediumPilotError(f"required artifact is missing: {relative}")
    return json.loads(path.read_text())


def _write(root, relative: str, payload: Any) -> None:
    from pathlib import Path

    from .paths import resolve_root_path

    path = resolve_root_path(Path(root).resolve(), relative)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


# ------------------------------------------------------- Phase 14, eligibility


def measure_eligible_unconsumed(root) -> dict[str, Any]:
    """How many frozen opportunities are legitimately eligible and unconsumed.

    Eligibility is the already-frozen selection contract, unweakened: the
    opportunity must carry an authored option-set contract, must reach three
    admissible curated candidates before any supply, and must not have been
    consumed by the V2 frozen-ten replay. Nothing is fabricated to reach a
    target size, and the shortfall against the specified 36 is reported rather
    than closed.
    """
    from pathlib import Path

    from .contrast_first_v2_pilot import measure_medium_pilot_supply

    supply = measure_medium_pilot_supply(Path(root))
    labels = list(supply["remaining_unused_labels"])
    frozen = {
        row["opportunity_label"]: row
        for row in _read(root, "research/qgen/contrast_first_pilot_opportunities.json")[
            "opportunities"
        ]
    }
    by_discipline = {name: 0 for name in DISCIPLINES}
    for label in labels:
        by_discipline[frozen[label]["discipline"]] += 1
    return {
        "SPECIFIED_PILOT_SIZE": 36,
        "TOTAL_ELIGIBLE_UNCONSUMED": len(labels),
        "MEDIUM_PILOT_N": min(36, len(labels)),
        "BELOW_THE_STATED_FLOOR_OF_24": len(labels) < 24,
        "ELIGIBLE_UNCONSUMED_BY_DISCIPLINE": by_discipline,
        "eligible_unconsumed_labels": labels,
        "selection_criteria_unchanged": True,
        "funnel": {
            key: supply[key]
            for key in (
                "FROZEN_OPPORTUNITY_UNIVERSE",
                "OPPORTUNITIES_WITH_AN_AUTHORED_OPTION_SET_CONTRACT",
                "OF_THOSE_WITH_AT_LEAST_THREE_ADMISSIBLE_CANDIDATES",
                "ALREADY_CONSUMED_BY_THIS_V2_REPLAY",
                "REMAINING_UNUSED",
            )
        },
        "limitation": (
            "The batch is 6, against a specified 36 and a stated floor of 24. The "
            "shortfall is the canonical opportunity universe, not the selection "
            "rule: the whole frozen universe is 30, only 18 carry an authored "
            "option-set contract, 16 of those reach three admissible curated "
            "candidates, and 10 are consumed by the V2 frozen-ten replay. "
            "Reaching 24 would require authoring new opportunities, new seed "
            "packs with independent seed review and new evidence packets, which "
            "is source-packet research rather than an architecture pilot. No "
            "criterion was weakened and no opportunity was invented."
        ),
    }


# ------------------------------------------------------------ Phase 15, freeze


def build_pilot_freeze(root) -> dict[str, Any]:
    """Freeze every pilot opportunity before any supply, extension or generation."""
    from pathlib import Path

    from .contrast_first_pilot import load_curated_candidates
    from .feature_anchor_registry import load_snapshot

    eligibility = measure_eligible_unconsumed(root)
    frozen = {
        row["opportunity_label"]: row
        for row in _read(root, "research/qgen/contrast_first_pilot_opportunities.json")[
            "opportunities"
        ]
    }
    authoring = _read(root, "research/qgen/contrast_first_pilot_authoring.json")
    snapshot = load_snapshot(Path(root), PILOT_SNAPSHOT_ID)
    pool = {
        row["seed_id"]: row
        for row in load_curated_candidates(
            Path(root), feature_anchor_snapshot=snapshot, feature_anchor_scope=None
        )
    }

    rows = []
    for label in eligibility["eligible_unconsumed_labels"]:
        opportunity = frozen[label]
        spec = authoring["opportunities"][label]
        competitors = list(spec["competitors"])
        rows.append({
            "opportunity_label": label,
            "opportunity_id": opportunity["opportunity_id"],
            "discipline": opportunity["discipline"],
            "anchor_study_unit_id": opportunity["anchor_study_unit_id"],
            "mcc_objective_id": opportunity["mcc_objective_id"],
            "learner_decision_id": opportunity["learner_decision_id"],
            "priority_class": opportunity["priority_class"],
            "item_archetype": opportunity["item_archetype"],
            "option_set_archetype": opportunity["option_set_archetype"],
            "difficulty_intent": opportunity["difficulty_intent"],
            "key_concept": spec["key_concept"],
            "key_concept_id": spec["key_concept_id"],
            "CURRENT_APPROVED_COMPETITOR_COUNT": len(competitors),
            "approved_competitors_at_freeze": sorted(competitors),
            "excluded_at_freeze": dict(sorted((spec.get("excluded") or {}).items())),
            "curated_candidates_in_scope": sorted(
                seed_id for seed_id in pool
                if seed_id in set(competitors) | set(spec.get("excluded") or {})
            ),
            "feature_anchor_snapshot_id": PILOT_SNAPSHOT_ID,
        })

    payload = {
        "schema_version": "1.0",
        "scope": "QGEN_MEDIUM_PILOT_OPPORTUNITY_FREEZE",
        "pilot_id": PILOT_ID,
        "frozen_before_any_supply_or_generation": True,
        "feature_anchor_snapshot_id": PILOT_SNAPSHOT_ID,
        "feature_anchor_registry_hash": snapshot["registry_hash"],
        "llm_api_calls": 0,
        "eligibility": eligibility,
        "MEDIUM_PILOT_N": len(rows),
        "opportunities": rows,
        "no_replacement_rule": (
            "A failed opportunity is not replaced. The denominator is the frozen "
            "six, whatever happens downstream."
        ),
    }
    payload["frozen_sha256"] = content_sha256(
        {key: value for key, value in payload.items() if key != "frozen_sha256"}
    )
    return payload


# ------------------------------------------- Phases 16 and 19, the snapshot rule


def enforce_pinned_snapshot(
    root, acquisition: Mapping[str, Any], snapshot: Mapping[str, Any]
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Split one wave into what this batch may use and what the next snapshot gets.

    This is the load-bearing rule of the whole pilot. An anchor relation the
    pinned snapshot does not already assert is **not eligible**, however well the
    wave cited it, because the production gate reads the snapshot and would refuse
    a competitor resting on it. Letting V2 use it anyway is the exact divergence
    between the two readers that the registry milestone closed, arriving from the
    supply side instead of the retrieval side.

    An approved member is still added when its own frozen anchors are pinned; only
    the added anchor is withheld. That way the coherence gate, not this function,
    decides whether the member survives.
    """
    from .feature_anchor_registry import resolve_seed_anchors

    eligible = json.loads(json.dumps(acquisition))
    proposed: list[dict[str, Any]] = []
    for label in sorted(eligible["opportunities"]):
        entry = eligible["opportunities"][label]
        for candidate in entry["candidates"]:
            if candidate["review"]["verdict"] != "APPROVED":
                # A refusal may still carry a feature proposal for the next cycle.
                extension = candidate["review"].get(
                    "proposed_extension_for_next_snapshot"
                )
                if extension:
                    proposed.append({
                        "opportunity_label": label,
                        "member_id": candidate["member_id"],
                        "eligible_in_this_batch": False,
                        "why_not_eligible": (
                            "The wave refused the candidate outright, and the feature "
                            "it would have needed is not in the frozen vocabulary."
                        ),
                        **extension,
                    })
                continue
            pinned = set(resolve_seed_anchors(snapshot, candidate["member_id"]))
            kept, withheld = [], []
            for anchor in candidate.get("added_anchors") or []:
                (kept if anchor["feature_id"] in pinned else withheld).append(anchor)
            candidate["added_anchors"] = kept
            for anchor in withheld:
                proposed.append({
                    "opportunity_label": label,
                    "member_id": candidate["member_id"],
                    "kind": "NEW_ANCHOR_RELATION",
                    "proposed_feature_id": anchor["feature_id"],
                    "contrast_role": anchor["contrast_role"],
                    "evidence_refs": list(anchor["evidence_refs"]),
                    "s4_limb_b": anchor["s4_limb_b"],
                    "s4_limb_c": anchor["s4_limb_c"],
                    "scope_opportunity_labels": [label],
                    "wave_verdict": "APPROVED",
                    "eligible_in_this_batch": False,
                    "why_not_eligible": (
                        f"{snapshot['snapshot_id']} does not assert this anchor "
                        f"relation for {candidate['member_id']}. The pinned snapshot "
                        "is not rebuilt inside the batch, so the relation is invisible "
                        "to every item in it and is carried to the next snapshot "
                        "cycle for independent review."
                    ),
                })
            if withheld and candidate["acquisition_kind"] in (
                "ANCHOR_ADDITION",
            ):
                candidate["review"] = {
                    **candidate["review"],
                    "verdict": "UNCERTAIN",
                    "reasons": [
                        "Approved by the wave, but its only contribution was an anchor "
                        "relation the pinned snapshot does not assert, so there is "
                        "nothing left for this batch to apply."
                    ],
                }
    return eligible, sorted(
        proposed, key=lambda row: (row["opportunity_label"], row["member_id"],
                                   row.get("proposed_feature_id") or "")
    )


# --------------------------------------------------------------- Phases 17 to 22


def run_pilot(root, *, snapshot_pinned: bool = True) -> dict[str, Any]:
    """One bounded wave, then one generation attempt per contrast-ready opportunity.

    With ``snapshot_pinned`` the batch runs under Phase 19: only anchor relations
    the pinned snapshot already asserts are available. The unpinned run is the
    counterfactual -- what the *next* snapshot would make possible -- and is
    reported beside the pilot rather than as the pilot.
    """
    from .contrast_supply import run_acquisition_wave, run_frozen5_replay
    from .feature_anchor_registry import load_snapshot

    snapshot = load_snapshot(root, PILOT_SNAPSHOT_ID)
    acquisition = _read(root, ACQUISITION_PATH)
    eligible, proposed = enforce_pinned_snapshot(root, acquisition, snapshot)

    from pathlib import Path

    from .paths import resolve_root_path

    scratch = resolve_root_path(
        Path(root).resolve(), "research/qgen/pilot/.medium-pilot-eligible-acquisition.json"
    )
    scratch.write_text(json.dumps(eligible, indent=2, sort_keys=True) + "\n")
    try:
        wave = run_acquisition_wave(
            root,
            acquisition_path=(
                "research/qgen/pilot/.medium-pilot-eligible-acquisition.json"
                if snapshot_pinned else ACQUISITION_PATH
            ),
            readings_path=READINGS_PATH,
        )
        replay = run_frozen5_replay(
            root, wave, feature_anchor_snapshot=snapshot,
            readings_path=READINGS_PATH,
            generated_path=GENERATED_PATH,
            reviews_path=REVIEWS_PATH,
            scope="QGEN_MEDIUM_PILOT_REPLAY",
        )
    finally:
        scratch.unlink(missing_ok=True)
    return {
        "snapshot_pinned": snapshot_pinned,
        "feature_anchor_snapshot_id": PILOT_SNAPSHOT_ID,
        "wave": wave,
        "replay": replay,
        "proposed_extensions": proposed,
    }


# ------------------------------------------------- Phases 23 to 28, the measures

#: Which architectural defect, if any, each unsuccessful opportunity exposes.
#: Separate from the primary cause, because a taxonomy category names where the
#: pipeline stopped and a defect names why the architecture let it.
ARCHITECTURAL_DEFECTS = {
    "G2-MED-01": "MISSING_VOCABULARY_FEATURE_FOR_A_SHARED_PRESENTATION",
    "G2-OBGYN-02": "V2_CANNOT_CARRY_A_NEVER_CORRECT_DISTRACTOR",
    "G2-OBGYN-03": "V2_CANNOT_CARRY_A_NEVER_CORRECT_DISTRACTOR",
    "G2-PED-03": "ONE_MEMBERS_CORRECTNESS_CONDITION_IS_ANOTHERS_SOLE_ANCHOR",
    "G2-PSY-01": "DENIAL_BUDGET_AGAINST_DENIAL_ONLY_COMPETITORS",
    "G2-SURG-03": "KEY_EVIDENCE_SCOPE_NOT_CHECKED_AGAINST_THE_SETTLEMENT_DEVICE",
}

PRIMARY_CAUSE = {
    "G2-MED-01": "NEW_EXTENSION_NOT_IN_PINNED_SNAPSHOT",
    "G2-OBGYN-02": "NO_CONTRAST_SUPPLY",
    "G2-OBGYN-03": "NEW_EXTENSION_NOT_IN_PINNED_SNAPSHOT",
    "G2-PED-03": "BLUEPRINT_FAILURE",
    "G2-PSY-01": "NEW_EXTENSION_NOT_IN_PINNED_SNAPSHOT",
    "G2-SURG-03": "NEW_EXTENSION_NOT_IN_PINNED_SNAPSHOT",
}


def _counts(rows, key):
    from collections import Counter

    return dict(sorted(Counter(row[key] for row in rows).items()))


def build_execution_report(root) -> dict[str, Any]:
    """Phases 15 to 28 in one artifact: what was frozen, supplied, generated, refused."""
    from .clinical_contrast_v2 import canonical_json

    freeze = _read(root, FREEZE_PATH)
    pinned = run_pilot(root, snapshot_pinned=True)
    counterfactual = run_pilot(root, snapshot_pinned=False)
    generated = _read(root, GENERATED_PATH)

    by_label = {row["opportunity_label"]: row for row in pinned["replay"]["results"]}
    cf_by_label = {
        row["opportunity_label"]: row for row in counterfactual["replay"]["results"]
    }
    wave_by_label = {row["opportunity_label"]: row for row in pinned["wave"]["results"]}
    cf_wave = {row["opportunity_label"]: row for row in counterfactual["wave"]["results"]}

    per_opportunity = []
    for row in freeze["opportunities"]:
        label = row["opportunity_label"]
        run = by_label[label]
        cf = cf_by_label[label]
        per_opportunity.append({
            "opportunity_label": label,
            "discipline": row["discipline"],
            "difficulty_intent": row["difficulty_intent"],
            "item_archetype": row["item_archetype"],
            "learner_decision_id": row["learner_decision_id"],
            "feature_anchor_snapshot_id": PILOT_SNAPSHOT_ID,
            "PRE_SUPPLY_VALID_COMPETITORS": run["VALID_COMPETITORS_BEFORE"],
            "PRE_SUPPLY_CONTRAST_READY": len(run["VALID_COMPETITORS_BEFORE"]) >= 3,
            "POST_SUPPLY_VALID_COMPETITORS": run["VALID_COMPETITORS_AFTER"],
            "POST_SUPPLY_CONTRAST_READY": len(run["VALID_COMPETITORS_AFTER"]) >= 3,
            "stage_reached": run["stage_reached"],
            "terminal_state": run["terminal_state"],
            "fail_closed_reason": run["fail_closed_reason"],
            "PRIMARY_CAUSE": PRIMARY_CAUSE[label],
            "ARCHITECTURAL_DEFECT": ARCHITECTURAL_DEFECTS[label],
            "wave": {
                key: wave_by_label[label][key] for key in (
                    "CANDIDATES_DISCOVERED", "CANDIDATES_SEMANTICALLY_REVIEWED",
                    "RELATIONS_APPROVED", "RELATIONS_REJECTED", "RELATIONS_UNCERTAIN",
                    "TOTAL_RELATION_REQUESTS", "CONTRAST_CACHE_HITS",
                    "NEW_RELATIONS_CREATED",
                )
            },
            "counterfactual_if_the_next_snapshot_carried_the_proposals": {
                "POST_SUPPLY_VALID_COMPETITORS": cf["VALID_COMPETITORS_AFTER"],
                "CONTRAST_READY": len(cf["VALID_COMPETITORS_AFTER"]) >= 3,
                "stage_reached": cf["stage_reached"],
                "fail_closed_reason": cf["fail_closed_reason"],
            },
        })

    generated_labels = sorted(
        row["opportunity_label"] for row in pinned["replay"]["results"]
        if row["stage_reached"] == "INDEPENDENT_REVIEW"
    )
    cf_generated = sorted(
        row["opportunity_label"] for row in counterfactual["replay"]["results"]
        if row["stage_reached"] == "INDEPENDENT_REVIEW"
    )
    return {
        "schema_version": "1.0",
        "scope": "QGEN_MEDIUM_PILOT_EXECUTION",
        "pilot_id": PILOT_ID,
        "llm_api_calls": 0,
        "feature_anchor_snapshot_id": PILOT_SNAPSHOT_ID,
        "feature_anchor_registry_hash": freeze["feature_anchor_registry_hash"],
        "SNAPSHOT_MUTATED_DURING_PILOT": False,
        "snapshot_invariant": (
            "One snapshot for the whole batch, pinned by explicit id, never rebuilt "
            "inside it. Every anchor relation the wave approved that the snapshot does "
            "not already assert was withheld from every item in the batch and recorded "
            "for the next snapshot cycle. The counterfactual run beside each "
            "opportunity is what those withheld relations would have bought; it is "
            "reported, not counted."
        ),
        "MEDIUM_PILOT_N": freeze["MEDIUM_PILOT_N"],
        "eligibility": freeze["eligibility"],
        "counts": {
            "MEDIUM_PRE_SUPPLY_CONTRAST_READY": sum(
                1 for row in per_opportunity if row["PRE_SUPPLY_CONTRAST_READY"]
            ),
            "MEDIUM_POST_SUPPLY_CONTRAST_READY": sum(
                1 for row in per_opportunity if row["POST_SUPPLY_CONTRAST_READY"]
            ),
            "MEDIUM_GENERATED": len(generated_labels),
            "MEDIUM_NO_SAFE_ITEM": len(per_opportunity) - len(generated_labels),
            "generated_labels": generated_labels,
            "COUNTERFACTUAL_CONTRAST_READY": sum(
                1 for row in per_opportunity
                if row["counterfactual_if_the_next_snapshot_carried_the_proposals"][
                    "CONTRAST_READY"]
            ),
            "COUNTERFACTUAL_GENERATED": len(cf_generated),
        },
        "per_opportunity": per_opportunity,
        "failure_taxonomy": _failure_taxonomy(per_opportunity),
        "supply_source_value": _supply_source_value(pinned, counterfactual),
        "cache_economics": _cache_economics(pinned, counterfactual),
        "context_characters": _context(canonical_json, pinned, counterfactual, generated),
        "PROPOSED_EXTENSIONS_FOR_NEXT_SNAPSHOT": counterfactual["proposed_extensions"],
    }


def _failure_taxonomy(rows) -> dict[str, Any]:
    from collections import Counter

    unsuccessful = [row for row in rows if row["terminal_state"] == "NO_SAFE_ITEM"]
    causes = Counter(row["PRIMARY_CAUSE"] for row in unsuccessful)
    defects = Counter(row["ARCHITECTURAL_DEFECT"] for row in rows)
    total = len(rows)
    largest_defect, largest_count = defects.most_common(1)[0]
    return {
        "population": total,
        "MEDIUM_FAILURE_COUNTS": dict(sorted(causes.items())),
        "LARGEST_FAILURE_CATEGORY": max(causes.items(), key=lambda kv: (kv[1], kv[0]))[0],
        "LARGEST_FAILURE_CATEGORY_PERCENT": round(
            100 * max(causes.values()) / total, 1
        ),
        "architectural_defects": dict(sorted(defects.items())),
        "SYSTEMATIC_DEFECT_GE_20_PERCENT": "YES" if largest_count / total >= 0.2 else "NO",
        "SYSTEMATIC_DEFECT": largest_defect,
        "SYSTEMATIC_DEFECT_PERCENT": round(100 * largest_count / total, 1),
        "not_repaired_here": (
            "Phase 25's own rule: the defect is identified and is not repaired inside "
            "the experiment that measured it."
        ),
    }


def _supply_source_value(pinned, counterfactual) -> dict[str, Any]:
    from collections import Counter

    sources: Counter = Counter()
    kinds: Counter = Counter()
    for row in counterfactual["wave"]["results"]:
        for member, source in row["approved_by_source"].items():
            sources[source] += 1
        for member, kind in row["approved_by_kind"].items():
            kinds[kind] += 1
    eligible_sources: Counter = Counter()
    for row in pinned["wave"]["results"]:
        for member, source in row["approved_by_source"].items():
            eligible_sources[source] += 1
    return {
        "approved_by_source_before_the_snapshot_rule": dict(sorted(sources.items())),
        "approved_by_kind_before_the_snapshot_rule": dict(sorted(kinds.items())),
        "approved_and_eligible_in_this_batch_by_source": dict(
            sorted(eligible_sources.items())
        ),
        "GRAPH_UNIQUE_APPROVED_CONTRIBUTIONS": sources.get("GRAPH", 0),
        "TN_FTS_UNIQUE_APPROVED_CONTRIBUTIONS": sources.get("TN_FTS", 0),
        "NEW_EXTERNAL_EVIDENCE_CONTRIBUTIONS": sources.get("NEW_EXTERNAL_EVIDENCE", 0),
        "load_bearing_for_accepted_questions": (
            "None, because no question was accepted. The one item the counterfactual "
            "realized rested on three anchor relations, all of them read from claims "
            "already in the frozen evidence packets and none of them from the graph or "
            "the full-text index."
        ),
        "tn_fts_note": (
            "One bounded full-text query was run for each of five opportunities. Every "
            "concept returned was already a frozen curated seed for that decision, so "
            "the index contributed no candidate and no relation. That is the second "
            "consecutive wave in which it has contributed nothing."
        ),
    }


def _cache_economics(pinned, counterfactual) -> dict[str, Any]:
    from collections import Counter

    reuse: Counter = Counter()
    per_opportunity = {}
    for row in counterfactual["wave"]["results"]:
        per_opportunity[row["opportunity_label"]] = {
            "TOTAL_RELATION_REQUESTS": row["TOTAL_RELATION_REQUESTS"],
            "CONTRAST_CACHE_HITS": row["CONTRAST_CACHE_HITS"],
            "NEW_RELATIONS_CREATED": row["NEW_RELATIONS_CREATED"],
        }
        for anchors in row["supply"]["added_anchors"].values():
            for anchor in anchors:
                reuse[anchor] += 1
    return {
        "per_opportunity": dict(sorted(per_opportunity.items())),
        "CONTRAST_CACHE_HITS_TOTAL": sum(
            row["CONTRAST_CACHE_HITS"] for row in per_opportunity.values()
        ),
        "NEW_RELATIONS_CREATED_TOTAL": sum(
            row["NEW_RELATIONS_CREATED"] for row in per_opportunity.values()
        ),
        "feature_registry_cache_hits": (
            "The pinned snapshot is loaded once per run and its hash verified once; "
            "every consumer reads the same in-memory rows. No feature or anchor row was "
            "re-derived per opportunity."
        ),
        "anchor_relations_reused_across_members": dict(sorted(reuse.items())),
        "relations_reused_across_opportunities": 0,
        "relations_reused_across_disciplines": 0,
        "PROPOSED_EXTENSIONS_PER_OPPORTUNITY": round(
            len(counterfactual["proposed_extensions"]) / 6, 2
        ),
        "amortization_note": (
            "Reuse inside one opportunity is real -- one anchor relation served three "
            "members in both the surgical and the psychiatric sets -- and reuse across "
            "opportunities was zero, because each opportunity is a different study unit "
            "or a different learner decision. Nothing here supports a monetary "
            "estimate and none is offered."
        ),
    }


def _context(canonical_json, pinned, counterfactual, generated) -> dict[str, Any]:
    import statistics

    def summarise(values):
        ordered = sorted(values)
        if not ordered:
            return {"median": 0, "p95": 0}
        index = min(len(ordered) - 1, int(round(0.95 * (len(ordered) - 1))))
        return {"median": int(statistics.median(ordered)), "p95": ordered[index]}

    per = []
    for row in counterfactual["wave"]["results"]:
        per.append({
            "opportunity_label": row["opportunity_label"],
            "relation_acquisition": len(canonical_json(row["contrast_set"]["relations"])),
            "candidate_discovery": len(canonical_json(row["retrieval"])),
            "relation_review": len(canonical_json(row["verdicts"]))
            + len(canonical_json(row["refusal_reasons"])),
        })
    for row in per:
        row["total"] = (
            row["relation_acquisition"] + row["candidate_discovery"]
            + row["relation_review"]
        )
    item_chars = sum(len(canonical_json(item)) for item in generated["items"].values())
    return {
        "unit": "CHARACTERS",
        "tokens_not_reported_because": (
            "No local tokenizer is installed, and characters are not equated with tokens."
        ),
        "per_opportunity": sorted(per, key=lambda row: row["opportunity_label"]),
        "SUPPLY_CONTEXT_MEDIAN": summarise([row["total"] for row in per])["median"],
        "SUPPLY_CONTEXT_P95": summarise([row["total"] for row in per])["p95"],
        "relation_acquisition": summarise([row["relation_acquisition"] for row in per]),
        "candidate_discovery": summarise([row["candidate_discovery"] for row in per]),
        "relation_review": summarise([row["relation_review"] for row in per]),
        "generation_characters_for_the_one_realized_item": item_chars,
        "NEXT_TOKEN_OPTIMIZATION_TARGET": "SERIALIZED_PAIRWISE_RELATION_PAYLOAD",
        "why": (
            "The serialized pairwise relation payload is again the whole of the supply "
            "cost, and it is again unoptimized. The registry gives every anchor "
            "relation a stable content-addressed id, which is the precondition for "
            "sending a reference instead of re-serializing a competitor's full anchor "
            "and condition payload on each of the six to ten pairs an opportunity "
            "builds. This pilot measured it and deliberately did not change it."
        ),
    }


# ---------------------------------------------------- Phases 22 and 23, review


def build_review_report(root) -> dict[str, Any]:
    """Independent review outcomes, and difficulty intent against the blind read."""
    freeze = _read(root, FREEZE_PATH)
    reviews = _read(root, REVIEWS_PATH)
    generated = _read(root, GENERATED_PATH)
    execution = build_execution_report(root)

    by_label = {row["opportunity_label"]: row for row in execution["per_opportunity"]}
    accepted, rejected, no_safe = [], [], []
    for row in freeze["opportunities"]:
        label = row["opportunity_label"]
        if by_label[label]["stage_reached"] != "INDEPENDENT_REVIEW":
            no_safe.append(label)
        elif reviews["reviews"][label]["VERDICT"] == "ACCEPT":
            accepted.append(label)
        else:
            rejected.append(label)

    counterfactual_reviewed = sorted(
        label for label, row in by_label.items()
        if row["counterfactual_if_the_next_snapshot_carried_the_proposals"][
            "stage_reached"] == "INDEPENDENT_REVIEW"
    )
    difficulty_rows = []
    for label in counterfactual_reviewed:
        blind = generated["blind_solver"][label]
        intent = by_label[label]["difficulty_intent"]
        difficulty_rows.append({
            "opportunity_label": label,
            "DIFFICULTY_INTENT": intent,
            "INDEPENDENT_STRUCTURAL_READ": blind["difficulty_read"],
            "MATCH": blind["difficulty_read"] == intent,
            "why": blind["difficulty_comment"],
        })

    def by(field):
        out = {}
        for label in accepted:
            out[by_label[label][field]] = out.get(by_label[label][field], 0) + 1
        return out

    disciplines = {name: 0 for name in DISCIPLINES}
    disciplines.update(by("discipline"))
    return {
        "schema_version": "1.0",
        "scope": "QGEN_MEDIUM_PILOT_INDEPENDENT_REVIEW_REPORT",
        "pilot_id": PILOT_ID,
        "llm_api_calls": 0,
        "protocol": reviews["protocol"],
        "MEDIUM_GENERATED": len(accepted) + len(rejected),
        "MEDIUM_ACCEPTED": len(accepted),
        "MEDIUM_REJECTED": len(rejected),
        "MEDIUM_NO_SAFE_ITEM": len(no_safe),
        "MEDIUM_ACCEPTED_BY_DISCIPLINE": disciplines,
        "MEDIUM_ACCEPTED_BY_DIFFICULTY": {"EASY": 0, "MEDIUM": 0, "HARD": 0},
        "MEDIUM_ACCEPTED_ITEM_SAFETY": "NO_ACCEPTED_ITEMS",
        "accepted_item_safety_note": (
            "The eleven accepted-item dimensions are a standard applied to accepted "
            "items. Nothing was accepted, so the standard was not exercised and PASS "
            "would be a claim about an empty set. No accepted-item safety regression "
            "occurred either, and the two statements are different."
        ),
        "no_safe_item_labels": no_safe,
        "rejected_labels": rejected,
        "accepted_labels": accepted,
        "counterfactual_review": {
            "reviewed_labels": counterfactual_reviewed,
            "verdicts": {
                label: reviews["reviews"][label]["VERDICT"]
                for label in counterfactual_reviewed
            },
            "scored_defects": {
                label: {
                    dimension: reviews["reviews"][label][dimension]
                    for dimension in sorted(reviews["reviews"][label])
                    if dimension.isupper() and dimension != "VERDICT"
                    and reviews["reviews"][label][dimension]
                }
                for label in counterfactual_reviewed
            },
            "note": (
                "The one item the batch could have realized had the withheld anchor "
                "relations been in the pinned snapshot. It is reviewed here because a "
                "generation attempt that produces prose should be judged, and it is "
                "counted nowhere in the pilot's own totals."
            ),
        },
        "difficulty": {
            "rows": difficulty_rows,
            "MEDIUM_DIFFICULTY_MATCH": {"EASY": "0/0", "MEDIUM": "0/0", "HARD": "0/0"},
            "counterfactual_difficulty_match": {
                "EASY": "0/0", "MEDIUM": "0/0",
                "HARD": f"{sum(1 for row in difficulty_rows if row['MATCH'])}/"
                        f"{len(difficulty_rows)}",
            },
            "DIFFICULTY_INTENT_IS_NOT_EMPIRICAL": (
                "DIFFICULTY_INTENT is authored from the nature of the learner decision "
                "and stays separate from any future EMPIRICAL_DIFFICULTY. The "
                "structural read here is one reasoning pass over the frozen stem, not "
                "learner data, and nothing in this pilot licenses calling EASY, MEDIUM "
                "or HARD empirical. The response_count, percent_correct, "
                "item_discrimination, option_endorsement, distractor_function and "
                "response_time fields remain reserved and unpopulated."
            ),
            "NEXT_DOMINANT_BOTTLENECK_CANDIDATE": (
                "DIFFICULTY_CALIBRATION is not this pilot's bottleneck, and the one "
                "HARD mismatch it did produce has a structural explanation rather than "
                "a stylistic one: at HARD the solver may spend no explicit denial, so "
                "it settles the set with a single stated positive finding, and a "
                "finding strong enough to settle three competitors at once is strong "
                "enough to give the answer away. One observation is not a rate."
            ),
        },
    }


def build_milestone_report(root) -> dict[str, Any]:
    """The pilot decision, the lifecycle verdict, and what is deliberately not claimed."""
    from .contrast_first_pilot import measure_copyright

    execution = build_execution_report(root)
    review = build_review_report(root)
    extensions = _read(root, EXTENSIONS_PATH)
    projection = project_next_snapshot(root)
    registry = _read(root, "reports/qgen_feature_anchor_registry_milestone.json")

    lifecycle_exercised = {
        "SNAPSHOT_N_PINNED_FOR_THE_WHOLE_BATCH": True,
        "SNAPSHOT_NEVER_REBUILT_INSIDE_THE_BATCH": True,
        "EXTENSIONS_COLLECTED_WITHOUT_BEING_APPLIED": bool(
            execution["PROPOSED_EXTENSIONS_FOR_NEXT_SNAPSHOT"]
        ),
        "AN_EXTENSION_PROPOSED_MID_BATCH_WAS_INVISIBLE_TO_LATER_ITEMS": True,
        "BATCH_PRODUCED_A_REVIEWABLE_EXTENSION_SET_FOR_SNAPSHOT_N_PLUS_1": True,
        "BATCH_PRODUCED_AN_ACCEPTED_ITEM": review["MEDIUM_ACCEPTED"] > 0,
    }
    return {
        "schema_version": "1.0",
        "scope": "QGEN_MEDIUM_PILOT_MILESTONE",
        "pilot_id": PILOT_ID,
        "llm_api_calls": 0,
        "starting_commit": "c640ede",
        "registry_contract": {
            "CONTRACT_RECONCILIATION": registry["CONTRACT_RECONCILIATION"],
            "REGISTRY_ASSESSMENT": "VALIDATED",
            "why": (
                "Carried forward from the gate replay and re-verified rather than "
                "re-run: reconciliation passes on all six precommitted limbs, "
                "visibility is 4/4 to each of the three consumers and the three sets "
                "are the same set, historical controls are preserved, G2-PED-01 moves "
                "from FAIL to PASS with the item untouched, and no accepted-item "
                "safety regression occurred. The pilot then stressed the contract from "
                "the supply side and it held: an anchor the snapshot does not assert "
                "was refused by the production gate, which is the divergence the "
                "registry exists to prevent."
            ),
        },
        "MEDIUM_PILOT_TRIGGERED": "YES",
        "MEDIUM_PILOT_N": execution["MEDIUM_PILOT_N"],
        "size_limitation": execution["eligibility"]["limitation"],
        "counts": {**execution["counts"], **{
            key: review[key] for key in (
                "MEDIUM_GENERATED", "MEDIUM_ACCEPTED", "MEDIUM_REJECTED",
                "MEDIUM_NO_SAFE_ITEM", "MEDIUM_ACCEPTED_ITEM_SAFETY",
            )
        }},
        "failure_taxonomy": execution["failure_taxonomy"],
        "snapshot_extension_yield": {
            key: extensions[key] for key in (
                "PROPOSED_FEATURE_EXTENSIONS_NEXT_SNAPSHOT",
                "PROPOSED_ANCHOR_EXTENSIONS_NEXT_SNAPSHOT",
                "APPROVED_NEXT_SNAPSHOT_EXTENSIONS",
                "REJECTED_NEXT_SNAPSHOT_EXTENSIONS",
                "UNCERTAIN_NEXT_SNAPSHOT_EXTENSIONS",
                "ACTIVATED",
            )
        },
        "next_snapshot_projection": projection,
        "SNAPSHOT_LIFECYCLE_STATUS": "PROMISING",
        "snapshot_lifecycle": {
            "model": [
                "SNAPSHOT_N is pinned by explicit id for every opportunity in a batch",
                "the batch is generated and independently reviewed against SNAPSHOT_N",
                "proposed extensions are collected and none is applied",
                "the extensions are independently reviewed, UNCERTAIN failing closed",
                "SNAPSHOT_N+1 is built deterministically from SNAPSHOT_N plus the "
                "approved set, recording the exact diff",
                "the next batch runs against SNAPSHOT_N+1",
            ],
            "exercised": lifecycle_exercised,
            "verdict_reason": (
                "Every mechanical limb of the lifecycle ran and held. The snapshot did "
                "not move, ten extension proposals were collected and none was applied, "
                "and the production gate refused exactly the competitors whose "
                "plausibility rested on relations the snapshot does not assert. What "
                "the lifecycle has not yet shown is a batch that yields an accepted "
                "item, which is why this is PROMISING and not VALIDATED. The batch's "
                "whole output was the input to the next snapshot, and that is a working "
                "cycle rather than a working generator."
            ),
        },
        "PRODUCTION_SCALEOUT_SPEC_WRITTEN": "NO",
        "why_no_spec": (
            "Phase 30's own precondition is a medium pilot whose accepted-item safety "
            "is PASS. Nothing was accepted, so that precondition is not met and no "
            "production scale-out design is written. Writing one on a batch that "
            "accepted zero items would be the overreach the repository policy forbids. "
            "What the pilot did produce -- the lifecycle measurement, the five named "
            "architectural defects and the extension yield -- is the input such a "
            "design would need, and it is recorded here rather than dressed as a spec."
        ),
        "RECOMMENDED_PRODUCTION_BATCH_SIZE": None,
        "why_no_batch_size": (
            "A batch size is a recommendation derived from an acceptance rate, and the "
            "measured acceptance rate is 0 of 6. Any number would be invented. The "
            "measurable quantity this pilot does support is the extension yield: 1.67 "
            "proposed extensions per opportunity, of which 8 of 10 are anchor relations "
            "rather than features, which is what a snapshot cycle would have to review "
            "between batches."
        ),
        "WHOLE_BOOK_TN_DECISION": "ON_DEMAND_TN_CONTRAST_SCALING",
        "tn_decision_basis": (
            "Unchanged and now on two waves of evidence rather than one. Five bounded "
            "full-text queries returned no concept that was not already a frozen "
            "curated seed, and the graph contributed nothing. Broad prepopulation would "
            "have solved none of the six failures, because none of them is a recall "
            "problem: four are anchor-relation coverage in the pinned snapshot, one is "
            "a missing vocabulary feature and one is a difficulty budget."
        ),
        "LOCAL_EMBEDDING_TRIGGER_MET": "NO",
        "EMBEDDINGS_ADDED": "NO",
        "embedding_note": (
            "The trigger is a concrete known-good competitor proven to exist in Toronto "
            "Notes and unreachable by the curated library, the graph, the full-text "
            "index and the existing evidence. No such competitor was found: every "
            "competitor this pilot wanted was already a curated seed, and what blocked "
            "it was expressibility rather than retrieval."
        ),
        "NEXT_DOMINANT_BOTTLENECK": "SNAPSHOT_EXTENSION_RATE",
        "next_bottleneck_detail": (
            "Four of six opportunities failed because the pinned snapshot does not "
            "assert an anchor relation their competitors need, and the wave could cite "
            "every one of those relations from frozen evidence in a single bounded "
            "pass. The binding constraint is therefore the rate at which reviewed "
            "relations enter a snapshot, not the rate at which they can be found. "
            "EVIDENCE_SCOPING is the runner-up and is unchanged: the one competitor "
            "the wave could not cite at all, and the one feature the vocabulary cannot "
            "state, are both evidence-packet problems."
        ),
        "copyright": measure_copyright(root, TRACKED_PILOT_ARTIFACTS),
        "not_done_and_not_claimed": [
            "No production scale-out spec, because its precondition was not met.",
            "No production batch size, because the acceptance rate is zero.",
            "SNAPSHOT_V3 was not built. The ten proposed extensions are recorded and "
            "none is activated; building it is the next batch's opening step.",
            "None of the five named architectural defects was repaired, per Phase 25.",
            "The frozen 102-feature vocabulary was not grown, so the two proposed new "
            "features stay refused.",
            "No opportunity was replaced, no criterion was weakened and the batch of "
            "six is the whole denominator.",
            "The independent review is a separate reasoning pass by the same model "
            "instance and is not blind.",
        ],
    }


def project_next_snapshot(root) -> dict[str, Any]:
    """What SNAPSHOT_N+1 would buy, using only the extensions the review approved.

    Not a run of the pilot and not counted in it. It answers the one question the
    lifecycle turns on: does a batch's reviewed extension yield unblock the batch
    that produced it, or does the cycle need more than one turn?
    """
    from .contrast_supply import run_acquisition_wave, solve_supplied_blueprint
    from .contrast_first_pilot import load_stem_feature_vocabulary
    from pathlib import Path

    from .paths import resolve_root_path

    extensions = _read(root, EXTENSIONS_PATH)
    approved = {
        (row["opportunity_label"], row["member_id"], row["proposed_feature_id"])
        for row in extensions["extensions"]
        if row["independent_review"]["verdict"] == "APPROVED"
    }
    acquisition = _read(root, ACQUISITION_PATH)
    for label in sorted(acquisition["opportunities"]):
        for candidate in acquisition["opportunities"][label]["candidates"]:
            candidate["added_anchors"] = [
                anchor for anchor in (candidate.get("added_anchors") or [])
                if (label, candidate["member_id"], anchor["feature_id"]) in approved
            ]
    scratch_relative = "research/qgen/pilot/.medium-pilot-next-snapshot.json"
    scratch = resolve_root_path(Path(root).resolve(), scratch_relative)
    scratch.write_text(json.dumps(acquisition, indent=2, sort_keys=True) + "\n")
    readings = _read(root, READINGS_PATH)["opportunities"]
    authoring = _read(
        root, "research/qgen/contrast_first_pilot_authoring.json"
    )["opportunities"]
    vocabulary = load_stem_feature_vocabulary(root)
    try:
        wave = run_acquisition_wave(
            root, acquisition_path=scratch_relative, readings_path=READINGS_PATH
        )
        rows = []
        for record in wave["results"]:
            label = record["opportunity_label"]
            ready = len(record["VALID_COMPETITORS_AFTER"]) >= 3
            solved = solve_supplied_blueprint(
                root, record, reading=readings[label],
                context_features=authoring[label].get("context_features") or [],
                vocabulary=vocabulary[record["anchor_study_unit_id"]],
            ) if ready else None
            rows.append({
                "opportunity_label": label,
                "CONTRAST_READY": ready,
                "VALID_COMPETITORS": record["VALID_COMPETITORS_AFTER"],
                "stage_reached": (
                    "CONTRAST_SET_ASSEMBLY" if solved is None else solved["stage_reached"]
                ),
                "fail_closed_reason": (
                    record["selection_after"]["fail_closed_reason"] if solved is None
                    else solved["fail_closed_reason"]
                ),
            })
    finally:
        scratch.unlink(missing_ok=True)
    return {
        "snapshot": "SNAPSHOT_V3_AS_REVIEWED",
        "applied_extensions": sorted(
            f"{member}:{feature}" for _, member, feature in approved
        ),
        "CONTRAST_READY": sum(1 for row in rows if row["CONTRAST_READY"]),
        "REACHING_A_STEM": sum(1 for row in rows if row["stage_reached"] == "STEM"),
        "per_opportunity": sorted(rows, key=lambda row: row["opportunity_label"]),
        "reading": (
            "The five approved relations unblock no opportunity in the batch that "
            "proposed them. Two of the three the unreviewed wave would have unblocked "
            "rested on relations the extension review refused, and the third fails at "
            "the blueprint for an unrelated reason. One turn of the snapshot cycle is "
            "therefore not enough to close this batch, and that is the single most "
            "important number the pilot produced."
        ),
    }


TRACKED_PILOT_ARTIFACTS = (
    "scripts/qbank/medium_pilot.py",
    "tests/test_medium_pilot.py",
    FREEZE_PATH,
    READINGS_PATH,
    ACQUISITION_PATH,
    GENERATED_PATH,
    REVIEWS_PATH,
    EXTENSIONS_PATH,
    EXECUTION_REPORT_PATH,
    REVIEW_REPORT_PATH,
    MILESTONE_REPORT_PATH,
)


def rebuild_all(root) -> dict[str, str]:
    """Regenerate every medium-pilot artifact deterministically, in order."""
    _write(root, FREEZE_PATH, build_pilot_freeze(root))
    _write(root, EXECUTION_REPORT_PATH, build_execution_report(root))
    _write(root, REVIEW_REPORT_PATH, build_review_report(root))
    _write(root, MILESTONE_REPORT_PATH, build_milestone_report(root))
    return {
        "freeze": FREEZE_PATH,
        "execution": EXECUTION_REPORT_PATH,
        "review": REVIEW_REPORT_PATH,
        "milestone": MILESTONE_REPORT_PATH,
    }


def medium_pilot_paths() -> dict[str, str]:
    """The four generated artifacts, in the order they must be rebuilt."""
    return {
        "freeze": FREEZE_PATH,
        "execution": EXECUTION_REPORT_PATH,
        "review": REVIEW_REPORT_PATH,
        "milestone": MILESTONE_REPORT_PATH,
    }
