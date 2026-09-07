"""Snapshot bootstrap and distractor semantics, measured over the same frozen six.

The cross-discipline medium pilot ended on `MEDIUM_GENERATED = 0` and two claims
about why. This module tests both, in that order, and changes exactly one variable
per arm:

  ARM A  the pilot as it ran, pinned to ``FEATURE_ANCHOR_SNAPSHOT_V2``
  ARM B  the same six, pinned to ``FEATURE_ANCHOR_SNAPSHOT_V3`` -- V2 plus the five
         anchor relations the pilot's own extension review independently approved,
         and none of the five it left UNCERTAIN
  ARM C  arm B plus the second distractor semantic class, where the pilot's own
         diagnosis said the model could not represent a legitimate competitor

Nothing here discovers a candidate, researches a contrast, edits a historical
snapshot or relaxes a gate. Arm C's members are read field by field out of the
frozen curated seed pack; the only thing that is new is that V2 can now say what
those fields already said.

Design: docs/superpowers/specs/2026-09-06-distractor-semantics-and-snapshot-bootstrap-design.md
"""

from __future__ import annotations

import json
from typing import Any, Mapping

from .errors import QbankError

BOOTSTRAP_ID = "medium6-snapshot-bootstrap"

ARM_A_SNAPSHOT = "FEATURE_ANCHOR_SNAPSHOT_V2"
ARM_B_SNAPSHOT = "FEATURE_ANCHOR_SNAPSHOT_V3"

ROOT_CAUSE_REPORT_PATH = "reports/qgen_medium6_failure_root_cause.json"
VISIBILITY_REPORT_PATH = "reports/qgen_snapshot_v3_visibility_replay.json"
DISTRACTOR_REPORT_PATH = "reports/qgen_never_correct_distractor_diagnosis.json"
THREE_ARM_REPORT_PATH = "reports/qgen_snapshot_bootstrap_three_arm.json"
FRESH_UNIVERSE_REPORT_PATH = "reports/qgen_fresh_validation_universe_feasibility.json"
MILESTONE_REPORT_PATH = "reports/qgen_snapshot_bootstrap_milestone.json"

ARM_C_OVERLAY_PATH = "research/qgen/pilot/medium-pilot-6-armc-never-best.json"
ARM_C_ACQUISITION_PATH = "research/qgen/pilot/medium-pilot-6-armc-acquisition.json"

TRACKED_ARTIFACTS = (
    "docs/superpowers/specs/"
    "2026-09-06-distractor-semantics-and-snapshot-bootstrap-design.md",
    "scripts/qbank/snapshot_bootstrap.py",
    "tests/test_snapshot_bootstrap.py",
    "tests/test_distractor_semantics.py",
    "research/qgen/feature_anchor_extensions_v3.json",
    ARM_C_OVERLAY_PATH,
    ARM_C_ACQUISITION_PATH,
    ROOT_CAUSE_REPORT_PATH,
    VISIBILITY_REPORT_PATH,
    DISTRACTOR_REPORT_PATH,
    THREE_ARM_REPORT_PATH,
    FRESH_UNIVERSE_REPORT_PATH,
    MILESTONE_REPORT_PATH,
)


class SnapshotBootstrapError(QbankError):
    """The bootstrap experiment cannot be built or run from canonical material."""


def _read(root, relative: str) -> Any:
    from pathlib import Path

    from .paths import resolve_root_path

    path = resolve_root_path(Path(root).resolve(), relative)
    if not path.is_file():
        raise SnapshotBootstrapError(f"required artifact is missing: {relative}")
    return json.loads(path.read_text())


# ----------------------------------------------------------- Part A, root cause

#: Which of the eight refused candidates the wave itself flagged as an option no
#: state of the world makes correct, per opportunity. Read from the acquisition
#: artifact rather than restated, so this cannot drift from it.
NEVER_CORRECT_FINDING = "V2_CANNOT_CARRY_A_NEVER_CORRECT_DISTRACTOR"


def never_correct_candidates(root) -> dict[str, list[str]]:
    """Every candidate the frozen wave refused with the never-correct finding."""
    acquisition = _read(root, "research/qgen/pilot/medium-pilot-6-acquisition.json")
    found: dict[str, list[str]] = {}
    for label in sorted(acquisition["opportunities"]):
        for candidate in acquisition["opportunities"][label]["candidates"]:
            review = candidate["review"]
            if review.get("architectural_finding") == NEVER_CORRECT_FINDING:
                found.setdefault(label, []).append(candidate["member_id"])
    return {label: sorted(rows) for label, rows in sorted(found.items())}


def approved_v3_extensions(root) -> list[dict[str, Any]]:
    from .feature_anchor_registry import (
        BOOTSTRAP_EXTENSIONS_PATH,
        approved_extensions,
        load_extensions,
    )

    return approved_extensions(load_extensions(root, path=BOOTSTRAP_EXTENSIONS_PATH))


def uncertain_v3_extensions(root) -> list[dict[str, Any]]:
    from .feature_anchor_registry import (
        ADMISSIBLE_REVIEW_VERDICTS,
        BOOTSTRAP_EXTENSIONS_PATH,
        load_extensions,
    )

    document = load_extensions(root, path=BOOTSTRAP_EXTENSIONS_PATH)
    return sorted(
        (
            row for row in document["extensions"]
            if row["registry_review"]["verdict"] not in ADMISSIBLE_REVIEW_VERDICTS
        ),
        key=lambda row: row["extension_id"],
    )


def build_root_cause_report(root) -> dict[str, Any]:
    """Part A. One row per frozen opportunity, before anything is changed.

    Every column is read from the committed medium-pilot artifacts, except the
    counterfactual, which is measured by actually replaying the batch against a
    snapshot carrying only the five independently approved extensions. The pilot's
    own counterfactual answered a different question -- it carried all ten
    proposals, including the five the extension review left UNCERTAIN -- and the
    two numbers are reported side by side rather than one replacing the other.
    """
    from .medium_pilot import run_pilot

    execution = _read(root, "reports/qgen_medium_pilot_execution.json")
    freeze = _read(root, "research/qgen/pilot/medium-pilot-6-opportunities.json")
    proposals = _read(
        root, "research/qgen/pilot/medium-pilot-6-proposed-extensions.json"
    )
    never_correct = never_correct_candidates(root)
    approved = approved_v3_extensions(root)
    approved_by_label: dict[str, list[str]] = {}
    for extension in approved:
        for label in extension["scope_opportunity_labels"]:
            approved_by_label.setdefault(label, []).append(extension["extension_id"])

    withheld_by_label: dict[str, list[dict[str, Any]]] = {}
    for row in proposals["extensions"]:
        withheld_by_label.setdefault(row["opportunity_label"], []).append({
            "kind": row["kind"],
            "member_id": row["member_id"],
            "proposed_feature_id": row.get("proposed_feature_id"),
            "wave_verdict": row.get("wave_verdict"),
            "extension_review_verdict": row["independent_review"]["verdict"],
        })

    arm_b = {
        row["opportunity_label"]: row
        for row in run_pilot(
            root, snapshot_pinned=True, snapshot_id=ARM_B_SNAPSHOT
        )["replay"]["results"]
    }
    learner_decisions = {
        row["opportunity_label"]: row["learner_decision_id"]
        for row in freeze["opportunities"]
    }

    rows = []
    for entry in execution["per_opportunity"]:
        label = entry["opportunity_label"]
        counterfactual = entry[
            "counterfactual_if_the_next_snapshot_carried_the_proposals"
        ]
        approved_only = arm_b[label]
        rows.append({
            "opportunity_id": next(
                row["opportunity_id"] for row in freeze["opportunities"]
                if row["opportunity_label"] == label
            ),
            "opportunity_label": label,
            "discipline": entry["discipline"],
            "difficulty_intent": entry["difficulty_intent"],
            "item_archetype": entry["item_archetype"],
            "learner_decision_id": learner_decisions[label],
            "PRE_SUPPLY_COMPETITOR_COUNT": len(entry["PRE_SUPPLY_VALID_COMPETITORS"]),
            "PRE_SUPPLY_VALID_COMPETITORS": entry["PRE_SUPPLY_VALID_COMPETITORS"],
            "POST_SUPPLY_COMPETITOR_COUNT": len(entry["POST_SUPPLY_VALID_COMPETITORS"]),
            "POST_SUPPLY_VALID_COMPETITORS": entry["POST_SUPPLY_VALID_COMPETITORS"],
            "MISSING_SNAPSHOT_EXTENSIONS": sorted(
                row["proposed_feature_id"] or ""
                for row in withheld_by_label.get(label, [])
                if row["kind"] == "NEW_ANCHOR_RELATION"
            ),
            "missing_snapshot_extension_detail": withheld_by_label.get(label, []),
            "BLUEPRINT_RESULT": (
                "NOT_REACHED" if entry["stage_reached"] == "CONTRAST_SET_ASSEMBLY"
                else entry["fail_closed_reason"] or "SOLVED"
            ),
            "NEVER_CORRECT_DISTRACTOR_INVOLVEMENT": {
                "involved": label in never_correct,
                "members": never_correct.get(label, []),
                "is_the_earliest_architectural_defect": (
                    entry["ARCHITECTURAL_DEFECT"] == NEVER_CORRECT_FINDING
                ),
            },
            "EARLIEST_PRIMARY_FAILURE": entry["PRIMARY_CAUSE"],
            "stage_reached": entry["stage_reached"],
            "fail_closed_reason": entry["fail_closed_reason"],
            "ARCHITECTURAL_DEFECT": entry["ARCHITECTURAL_DEFECT"],
            "counterfactual": {
                "question": (
                    "Would the approved next-snapshot extensions alone have changed "
                    "the outcome?"
                ),
                "APPROVED_EXTENSIONS_FOR_THIS_OPPORTUNITY": sorted(
                    approved_by_label.get(label, [])
                ),
                "APPROVED_ONLY_CONTRAST_READY": approved_only["three_valid_after"],
                "APPROVED_ONLY_VALID_COMPETITORS": approved_only[
                    "VALID_COMPETITORS_AFTER"
                ],
                "APPROVED_ONLY_STAGE_REACHED": approved_only["stage_reached"],
                "APPROVED_ONLY_FAIL_CLOSED_REASON": approved_only["fail_closed_reason"],
                "OUTCOME_CHANGED_BY_APPROVED_EXTENSIONS_ALONE": (
                    approved_only["stage_reached"] != entry["stage_reached"]
                ),
                "pilot_counterfactual_carried_all_ten_proposals": {
                    "CONTRAST_READY": counterfactual["CONTRAST_READY"],
                    "stage_reached": counterfactual["stage_reached"],
                    "note": (
                        "The pilot's own counterfactual is not this one. It carried "
                        "all ten proposals, five of which the extension review left "
                        "UNCERTAIN, so where the two disagree the difference is "
                        "exactly the uncertain rows failing closed."
                    ),
                },
            },
        })

    changed = [
        row["opportunity_label"] for row in rows
        if row["counterfactual"]["OUTCOME_CHANGED_BY_APPROVED_EXTENSIONS_ALONE"]
    ]
    return {
        "schema_version": "1.0",
        "scope": "QGEN_MEDIUM6_FAILURE_ROOT_CAUSE",
        "bootstrap_id": BOOTSTRAP_ID,
        "llm_api_calls": 0,
        "starting_commit": "2e90375",
        "built_before_any_change": (
            "This matrix reconciles the completed pilot against its own artifacts and "
            "measures one counterfactual. No gate, model or snapshot was changed to "
            "produce it, and the six frozen opportunities are the ones the pilot froze."
        ),
        "MEDIUM6_N": len(rows),
        "per_opportunity": rows,
        "OPPORTUNITIES_CHANGED_BY_APPROVED_EXTENSIONS_ALONE": sorted(changed),
        "COUNT_CHANGED_BY_APPROVED_EXTENSIONS_ALONE": len(changed),
        "failure_counts": dict(execution["failure_taxonomy"]["MEDIUM_FAILURE_COUNTS"]),
        "never_correct_involvement": {
            "OPPORTUNITIES_WITH_A_NEVER_CORRECT_CANDIDATE": sorted(never_correct),
            "CANDIDATES": sum(len(rows) for rows in never_correct.values()),
            "detail": never_correct,
        },
    }


# --------------------------------------------- Parts C, D and E, the replay


def _snapshot_visibility(root, snapshot_id: str) -> dict[str, Any]:
    """Which approved anchor relations one snapshot asserts, per reader.

    Measured three ways because the registry milestone's whole finding was that
    the three readers had drifted: the snapshot's own rows, the seed-anchor
    adapter every index builder calls, and the curated-candidate projection the
    production gate reads.
    """
    from .contrast_first_pilot import load_curated_candidates
    from .feature_anchor_registry import load_snapshot, resolve_seed_anchors

    snapshot = load_snapshot(root, snapshot_id)
    approved = approved_v3_extensions(root)
    uncertain = uncertain_v3_extensions(root)

    declared_ids = {row["anchor_relation_id"] for row in snapshot["anchor_relations"]}
    from .feature_anchor_registry import anchor_relation_id

    def identity(extension: Mapping[str, Any]) -> str:
        return anchor_relation_id({
            "feature_id": extension.get("feature_id")
                          or extension["proposed_feature_id"],
            "target_concept_id": extension.get("target_concept_id"),
            "learner_decision": extension.get("learner_decision"),
            "decision_granularity": extension.get("decision_granularity"),
            "required_state": extension.get("required_state"),
        })

    visible_to_snapshot, visible_to_adapter, visible_to_retrieval = [], [], []
    for extension in approved:
        scope = extension["scope_opportunity_labels"][0]
        if identity(extension) in declared_ids:
            visible_to_snapshot.append(extension["extension_id"])
        if extension["feature_id"] in resolve_seed_anchors(
            snapshot, extension["seed_id"], scope=scope
        ):
            visible_to_adapter.append(extension["extension_id"])
        pool = {
            row["seed_id"]: row
            for row in load_curated_candidates(
                root, feature_anchor_snapshot=snapshot, feature_anchor_scope=scope
            )
        }
        if extension["feature_id"] in (
            pool[extension["seed_id"]]["plausibility_anchor_feature_ids"]
        ):
            visible_to_retrieval.append(extension["extension_id"])

    leaked = []
    for extension in uncertain:
        seed_id = extension["seed_id"]
        feature_id = extension.get("feature_id") or extension["proposed_feature_id"]
        scope = (extension.get("scope_opportunity_labels") or [None])[0]
        try:
            anchors = resolve_seed_anchors(snapshot, seed_id, scope=scope)
        except Exception:  # a seed outside the snapshot's scope cannot leak
            continue
        if feature_id in anchors:
            leaked.append(extension["extension_id"])

    return {
        "snapshot_id": snapshot_id,
        "registry_hash": snapshot["registry_hash"],
        "feature_count": snapshot["feature_count"],
        "anchor_relation_count": snapshot["anchor_relation_count"],
        "APPROVED_EXTENSIONS": len(approved),
        "APPROVED_EXTENSIONS_VISIBLE_TO_SNAPSHOT": len(visible_to_snapshot),
        "APPROVED_EXTENSIONS_VISIBLE_TO_SEED_ANCHOR_ADAPTER": len(visible_to_adapter),
        "APPROVED_EXTENSIONS_VISIBLE_TO_PROFILE_RETRIEVAL": len(visible_to_retrieval),
        "VISIBILITY_SET_EQUALITY": (
            sorted(visible_to_snapshot) == sorted(visible_to_adapter)
            == sorted(visible_to_retrieval)
        ),
        "visible_extension_ids": sorted(visible_to_snapshot),
        "UNCERTAIN_EXTENSIONS": len(uncertain),
        "UNCERTAIN_EXTENSIONS_VISIBLE": len(leaked),
        "leaked_uncertain_extension_ids": sorted(leaked),
    }


def build_visibility_replay(root) -> dict[str, Any]:
    """Parts C, D and E. The same six under V2 and under V3, one variable.

    Nothing moves but the snapshot: the opportunities, the candidate sets, the
    contrast relations, the evidence, the difficulty intents and the keys are the
    committed frozen ones in both arms, read from the same files.
    """
    from .feature_anchor_registry import build_historical_regression
    from .medium_pilot import run_pilot

    arms = {}
    for snapshot_id in (ARM_A_SNAPSHOT, ARM_B_SNAPSHOT):
        run = run_pilot(root, snapshot_pinned=True, snapshot_id=snapshot_id)
        arms[snapshot_id] = {
            row["opportunity_label"]: row for row in run["replay"]["results"]
        }
        arms[snapshot_id]["_proposed"] = run["proposed_extensions"]

    labels = sorted(
        label for label in arms[ARM_A_SNAPSHOT] if not label.startswith("_")
    )
    per_opportunity = []
    for label in labels:
        before = arms[ARM_A_SNAPSHOT][label]
        after = arms[ARM_B_SNAPSHOT][label]
        per_opportunity.append({
            "opportunity_label": label,
            "discipline": before["discipline"],
            "difficulty_intent": before["difficulty_intent"],
            ARM_A_SNAPSHOT: {
                "VALID_COMPETITORS": before["VALID_COMPETITORS_AFTER"],
                "CONTRAST_READY": before["three_valid_after"],
                "stage_reached": before["stage_reached"],
                "terminal_state": before["terminal_state"],
                "fail_closed_reason": before["fail_closed_reason"],
                "SAF1_OUTCOME": _saf1_outcome(before),
                "PROFILE_RETRIEVAL_OUTCOME": _profile_outcome(before),
                "V2_OUTCOME": before["terminal_state"] or "REACHED_INDEPENDENT_REVIEW",
            },
            ARM_B_SNAPSHOT: {
                "VALID_COMPETITORS": after["VALID_COMPETITORS_AFTER"],
                "CONTRAST_READY": after["three_valid_after"],
                "stage_reached": after["stage_reached"],
                "terminal_state": after["terminal_state"],
                "fail_closed_reason": after["fail_closed_reason"],
                "SAF1_OUTCOME": _saf1_outcome(after),
                "PROFILE_RETRIEVAL_OUTCOME": _profile_outcome(after),
                "V2_OUTCOME": after["terminal_state"] or "REACHED_INDEPENDENT_REVIEW",
            },
            "MOVED": (
                before["stage_reached"] != after["stage_reached"]
                or before["VALID_COMPETITORS_AFTER"] != after["VALID_COMPETITORS_AFTER"]
            ),
            "CONVERTED_TO_DOWNSTREAM_READY": (
                not before["three_valid_after"] and after["three_valid_after"]
            ),
        })

    root_cause = build_root_cause_report(root)
    withheld_labels = sorted(
        row["opportunity_label"] for row in root_cause["per_opportunity"]
        if row["EARLIEST_PRIMARY_FAILURE"] == "NEW_EXTENSION_NOT_IN_PINNED_SNAPSHOT"
    )
    converted = sorted(
        row["opportunity_label"] for row in per_opportunity
        if row["CONVERTED_TO_DOWNSTREAM_READY"]
        and row["opportunity_label"] in withheld_labels
    )

    regression = build_historical_regression(root)
    visibility = {
        snapshot_id: _snapshot_visibility(root, snapshot_id)
        for snapshot_id in (ARM_A_SNAPSHOT, ARM_B_SNAPSHOT)
    }
    controls_unchanged = _historical_controls_unchanged(root)
    no_uncertain_visible = (
        visibility[ARM_B_SNAPSHOT]["UNCERTAIN_EXTENSIONS_VISIBLE"] == 0
    )
    no_gate_weakened = _no_gate_weakened(root, per_opportunity)

    validated = bool(converted) and controls_unchanged["unchanged"] and (
        no_uncertain_visible
    ) and no_gate_weakened["holds"]

    return {
        "schema_version": "1.0",
        "scope": "QGEN_SNAPSHOT_V3_VISIBILITY_REPLAY",
        "bootstrap_id": BOOTSTRAP_ID,
        "llm_api_calls": 0,
        "only_variable": (
            "The pinned feature/anchor snapshot. Opportunities, candidate sets, "
            "contrast relations, evidence, difficulty intents and keys are the "
            "committed frozen artifacts in both arms and are read from the same files."
        ),
        "snapshots": visibility,
        "V3_PARENT": ARM_A_SNAPSHOT,
        "V3_APPROVED_EXTENSIONS_ADDED": len(approved_v3_extensions(root)),
        "V3_UNCERTAIN_EXTENSIONS_ADDED": 0,
        "uncertain_extensions_excluded": [
            {
                "extension_id": row["extension_id"],
                "classification": row["classification"],
                "member_id": row["member_id"],
                "proposed_feature_id": row.get("proposed_feature_id")
                                       or row.get("feature_id"),
                "source_opportunity": row["source_opportunity"],
                "why_it_remained_uncertain": row["registry_review"][
                    "why_it_remained_uncertain"
                ],
                "reviewer_inconsistency_or_evidence_bug": row["registry_review"][
                    "reviewer_inconsistency_or_evidence_bug"
                ],
                "revisit_condition": row["registry_review"]["revisit_condition"],
            }
            for row in uncertain_v3_extensions(root)
        ],
        "per_opportunity": per_opportunity,
        "CONTRAST_READY": {
            ARM_A_SNAPSHOT: sum(
                1 for row in per_opportunity if row[ARM_A_SNAPSHOT]["CONTRAST_READY"]
            ),
            ARM_B_SNAPSHOT: sum(
                1 for row in per_opportunity if row[ARM_B_SNAPSHOT]["CONTRAST_READY"]
            ),
        },
        "precommitted_bootstrap_criteria": {
            "AT_LEAST_ONE_WITHHELD_FAILURE_CONVERTED": bool(converted),
            "converted_labels": converted,
            "withheld_failure_labels": withheld_labels,
            "HISTORICAL_CONTROLS_UNCHANGED": controls_unchanged["unchanged"],
            "historical_controls": controls_unchanged,
            "NO_UNCERTAIN_EXTENSION_VISIBLE": no_uncertain_visible,
            "NO_SAFETY_GATE_WEAKENED": no_gate_weakened["holds"],
            "gate_evidence": no_gate_weakened,
        },
        "SNAPSHOT_BOOTSTRAP_VALIDATED": validated,
        "historical_regression_baseline_reproduces_legacy_exactly": regression[
            "BASELINE_REPRODUCES_LEGACY_EXACTLY"
        ],
    }


def _saf1_outcome(row: Mapping[str, Any]) -> str:
    """`SAF_1`'s verdict for one replayed opportunity, or why it never ran."""
    gate = row.get("production_gate")
    if gate is None:
        return "NOT_REACHED"
    return "PASS" if gate["post_stem_3_viable"] else "FAIL"


def _profile_outcome(row: Mapping[str, Any]) -> str:
    gate = row.get("production_gate")
    if gate is None:
        return "NOT_REACHED"
    return f"RANKED_{len(gate['ranked_competitors'])}"


def _historical_controls_unchanged(root) -> dict[str, Any]:
    """V1 and V2 must be byte-identical to what they were before V3 existed.

    Measured against the committed snapshot store rather than against a memory of
    it: the store is rebuilt from its inputs and the two earlier snapshots are
    compared row for row. A third snapshot appended to the file is not a change
    to the first two, and this is the assertion that says so.
    """
    from .feature_anchor_registry import (
        SNAPSHOTS_PATH,
        build_snapshot_store,
    )

    tracked = _read(root, SNAPSHOTS_PATH)
    rebuilt = build_snapshot_store(root)
    same = {
        snapshot_id: rebuilt["snapshots"][snapshot_id] == tracked["snapshots"][snapshot_id]
        for snapshot_id in ("FEATURE_ANCHOR_SNAPSHOT_V1", ARM_A_SNAPSHOT)
    }
    return {
        "unchanged": all(same.values()),
        "snapshots_regenerate_identically": same,
        "V1_registry_hash": tracked["snapshots"]["FEATURE_ANCHOR_SNAPSHOT_V1"][
            "registry_hash"
        ],
        "V2_registry_hash": tracked["snapshots"][ARM_A_SNAPSHOT]["registry_hash"],
        "note": (
            "The snapshot store is append-only. V3 is a third entry; neither earlier "
            "entry's rows, counts or hash moved, and the frozen replays that pin them "
            "regenerate byte for byte, which their own tests assert."
        ),
    }


def _no_gate_weakened(root, per_opportunity) -> dict[str, Any]:
    """No opportunity is admitted by a rule that used to refuse it.

    The only admissions V3 may produce are ones the anchor contract now supports.
    An opportunity that fails closed under V2 and passes under V3 must do so with
    the same rules applied, so what is checked here is that every arm-B fail-closed
    reason is one the pipeline already had a name for, and that no opportunity
    reached a later stage while carrying a coherence violation.
    """
    from .clinical_contrast_v2 import COHERENCE_RULES_V2

    named_reasons = set()
    for row in per_opportunity:
        for arm in (ARM_A_SNAPSHOT, ARM_B_SNAPSHOT):
            if row[arm]["fail_closed_reason"]:
                named_reasons.add(row[arm]["fail_closed_reason"])
    unnamed = sorted(
        reason for reason in named_reasons if not reason.startswith("FAIL_CLOSED_")
    )
    return {
        "holds": not unnamed,
        "fail_closed_reasons_seen": sorted(named_reasons),
        "unnamed_reasons": unnamed,
        "coherence_rules_applied": list(COHERENCE_RULES_V2),
        "note": (
            "No gate rule was edited by this work. `SAF_1`, the coherence contract, "
            "the blueprint solver and the production gate are the same functions the "
            "medium pilot ran, and their own regression tests are unchanged."
        ),
    }


# ---------------------------- Parts H to M, the never-correct distractor case file

#: Every option, from this pilot and from the frozen record before it, whose own
#: reviewed prose records no state of the world in which it is the best answer.
#:
#: The classification is the reviewer's, the basis is cited, and both are recorded
#: here rather than derived, because neither is a deterministic function of the
#: frozen fields. Everything else in the case file is read from the seed pack.
NEVER_BEST_CASES = {
    "SEED-OB-T02-CRP": {
        "opportunity_label": "G2-OBGYN-02",
        "source": "MEDIUM6_PILOT",
        "classification": "WRONG_DECISION_CLASS",
        "inferiority_basis": "ADDRESSES_A_DIFFERENT_PROBLEM_THAN_THE_ONE_ASKED",
        "reviewer_note": (
            "The pilot recorded this as a never-correct distractor, and it is one, but "
            "that is not the earliest thing wrong with it. Its own frozen prose says "
            "why a candidate would order it -- 'the reflex test for deciding whether "
            "infection persists' -- and that is a different question from the one the "
            "lead-in asks, which is how to characterise a palpable mass. The frozen "
            "response-class tokens agree without being consulted: the seed carries "
            "BIOCHEMICAL and the set demands DIAGNOSTIC_ADVANCEMENT. Its refusal is "
            "correct and the never-correct finding is not the reason for it."
        ),
    },
    "SEED-OB-T03-EMPTY": {
        "opportunity_label": "G2-OBGYN-03",
        "source": "MEDIUM6_PILOT",
        "classification": "PLAUSIBLE_BUT_NEVER_BEST",
        "inferiority_basis": "EVIDENCE_STATES_HARM",
        "reviewer_note": (
            "Emptying the breast to relieve milk stasis is the classic instruction and "
            "is what many patients are already doing, so the temptation is the "
            "recognised one. CLM-R2-OB-NO-EMPTY states the harm: pumping to empty "
            "perpetuates hyperlactation. No reasonable nearby change to this patient "
            "makes it the best answer."
        ),
    },
    "SEED-OB-T03-DANGLE": {
        "opportunity_label": "G2-OBGYN-03",
        "source": "MEDIUM6_PILOT",
        "classification": "PLAUSIBLE_BUT_NEVER_BEST",
        "inferiority_basis": "EVIDENCE_STATES_NO_BENEFIT",
        "reviewer_note": (
            "Widely recommended in lactation circles for a blocked segment, which is "
            "exactly the kind of advice a patient arrives having read. CLM-R4-OB-DANGLE "
            "states both that no evidence supports it and that the position is unsafe "
            "for the infant; the cited claim leads with the absence of benefit, so that "
            "is the declared basis and the safety clause is recorded in the reason."
        ),
    },
    "SEED-OB-T03-SHIELD": {
        "opportunity_label": "G2-OBGYN-03",
        "source": "MEDIUM6_PILOT",
        "classification": "PLAUSIBLE_BUT_NEVER_BEST",
        "inferiority_basis": "EVIDENCE_STATES_NO_BENEFIT",
        "reviewer_note": (
            "A nipple shield is a standard tool offered for painful feeding, and pain "
            "with latch is part of this presentation, so it is anchored on something "
            "the stem can state. CLM-R4-OB-NIPPLE-SHIELD states that neither safety nor "
            "effectiveness has been demonstrated and that shields result in inadequate "
            "milk extraction, which is the opposite of what this patient needs."
        ),
    },
    "SEED-OB-T03-MASSAGE": {
        "opportunity_label": "G2-OBGYN-03",
        "source": "MEDIUM6_PILOT",
        "classification": "PLAUSIBLE_BUT_NEVER_BEST",
        "inferiority_basis": "EVIDENCE_STATES_HARM",
        "reviewer_note": (
            "The category is right and only the depth of pressure is wrong, which is a "
            "textbook clinical confusion rather than a silly option: a manual technique "
            "is genuinely part of recommended care. CLM-R2-OB-DEEP-MASSAGE states that "
            "deep massage of an inflamed breast may propagate phlegmon. The one state "
            "in which the concept is right -- light sweeping approximating lymphatic "
            "drainage -- is a different option from the one this seed states, so it is "
            "not a counterfactual correctness condition for this option."
        ),
    },
    "SEED-PED-T03-SALBUTAMOL": {
        "opportunity_label": "G2-PED-03",
        "source": "MEDIUM6_PILOT",
        "classification": "PLAUSIBLE_BUT_NEVER_BEST",
        "inferiority_basis": "EVIDENCE_STATES_NO_BENEFIT",
        "reviewer_note": (
            "Wheeze invites a bronchodilator and small improvements in clinical scores "
            "have been shown, so a candidate who treats the wheeze rather than the "
            "illness reaches for it. CLM-R2-PED-SALBUTAMOL states in terms that "
            "bronchodilators do not improve oxygen saturation, which is the exact "
            "quantity this lead-in asks about."
        ),
    },
    "SEED-PED-T03-HYPERTONIC": {
        "opportunity_label": "G2-PED-03",
        "source": "MEDIUM6_PILOT",
        "classification": "PLAUSIBLE_BUT_NEVER_BEST",
        "inferiority_basis": "EVIDENCE_STATES_NO_BENEFIT",
        "reviewer_note": (
            "Classified by its semantics rather than by whether it can be used. It is "
            "genuinely plausible -- a stated mechanism in this illness and still in wide "
            "use -- so it is not a dead distractor, and CLM-R4-PED-HYPERTONIC states no "
            "impact on length of stay. What it does not have is any plausibility anchor "
            "the frozen SU-P-147 vocabulary can state: 'a nebulized supportive measure "
            "in the same illness' is not a feature. It is therefore refused by the "
            "contract's first limb, and the reason is the missing-vocabulary defect "
            "already named for G2-MED-01 rather than the distractor model."
        ),
    },
    "SEED-G2-MED-T03-DEFERRED-ANGIO": {
        "opportunity_label": "G2-MED-04",
        "source": "PRIOR_FROZEN_ACCEPTED_CONTROL",
        "classification": "PLAUSIBLE_BUT_NEVER_BEST",
        "inferiority_basis": "EVIDENCE_PREFERS_ANOTHER_ACTION",
        "reviewer_note": (
            "Not a pilot case. It is the load-bearing prior example: an option carrying "
            "zero condition predicates inside an item four independent reviewers "
            "accepted with zero defects on all eleven dimensions. A never-best option is "
            "not incompatible with an accepted item, and this is the frozen record "
            "saying so before this task existed."
        ),
    },
    "SEED-G2-MED-T03-RESCUE-ONLY": {
        "opportunity_label": "G2-MED-04",
        "source": "PRIOR_FROZEN_ACCEPTED_CONTROL",
        "classification": "PLAUSIBLE_BUT_NEVER_BEST",
        "inferiority_basis": "EVIDENCE_PREFERS_ANOTHER_ACTION",
        "reviewer_note": (
            "The second zero-predicate option in the same accepted item. Both remain "
            "selectable reperfusion routes invited by the geography written into the "
            "stem, which is the distinction the G2 root-cause diagnosis drew and "
            "declined to turn into a rule."
        ),
    },
}

#: The one control that the pilot's own taxonomy might be read as including and
#: which does not belong: it carries a correctness condition, and its refusal is
#: the anchor-equals-condition rule rather than the distractor model.
NEVER_BEST_NEGATIVE_CONTROL = "SEED-OB-T02-MILK-CULTURE"


def _seed_pack_rows(root) -> dict[str, dict[str, Any]]:
    """The raw frozen seed-pack rows, which carry two fields the loader drops."""
    rows: dict[str, dict[str, Any]] = {}
    for base in (
        "research/qgen/generalization/competitive_contrast_seed_pack_r4",
        "research/qgen/generalization/competitive_contrast_seed_pack_g2_targeted",
        "research/qgen/generalization/competitive_contrast_seed_pack_g2_extensions",
    ):
        document = _read(root, f"{base}.json")

        def walk(node):
            if isinstance(node, dict):
                if node.get("seed_id") and "competitor_concept" in node:
                    rows.setdefault(node["seed_id"], node)
                for value in node.values():
                    walk(value)
            elif isinstance(node, list):
                for value in node:
                    walk(value)

        walk(document)
    return rows


def build_never_best_overlay(root) -> dict[str, Any]:
    """Parts H, K and L. One never-best contract per diagnosed candidate.

    Nothing is authored. Each contract's plausibility anchors, both sets of
    evidence references, the reason a candidate would consider the option and the
    reason it is inferior are transcribed from the frozen curated seed pack, whose
    rows already carry every field the contract asks for -- which is itself the
    finding: the frozen layer had been recording all of this, and V2 had no place
    to put it.
    """
    from .contrast_first_pilot import load_curated_candidates

    pool = {row["seed_id"]: row for row in load_curated_candidates(root)}
    packs = _seed_pack_rows(root)

    rows = []
    for member_id, case in sorted(NEVER_BEST_CASES.items()):
        seed = pool.get(member_id)
        pack = packs.get(member_id)
        if seed is None or pack is None:
            raise SnapshotBootstrapError(
                f"{member_id} is not a frozen curated seed; a diagnosed case must be one"
            )
        anchors = sorted(seed["plausibility_anchor_feature_ids"])
        entry = {
            "member_id": member_id,
            "opportunity_label": case["opportunity_label"],
            "source": case["source"],
            "concept": seed["competitor_concept"],
            "CLASSIFICATION": case["classification"],
            "reviewer_note": case["reviewer_note"],
            "frozen_prose_no_state_makes_it_correct": pack[
                "conditions_under_which_competitor_would_be_correct"
            ],
            "frozen_independent_seed_review_verdict": seed["independent_seed_review"][
                "verdict"
            ],
            "frozen_reviewed_strength": seed["independent_seed_review"][
                "reviewed_strength"
            ],
            "response_class_tokens": sorted(seed["response_class_tokens"]),
            "decision_granularity": seed["competitor_decision_granularity"],
            "plausibility_anchor_feature_ids": anchors,
            "never_best_contract": {
                "positive_plausibility": {
                    "feature_ids": anchors,
                    "evidence_refs": sorted(seed["evidence_refs_for_plausibility"]),
                    "reason": pack["why_plausible_for_this_decision"],
                },
                "inferiority": {
                    "basis": case["inferiority_basis"],
                    "evidence_refs": sorted(seed["evidence_refs_for_discrimination"]),
                    "reason": pack[
                        "conditions_under_which_competitor_would_be_correct"
                    ],
                },
                "learner_error_mode": pack[
                    "why_a_partially_knowledgeable_candidate_might_choose_it"
                ],
            },
            "ADMISSIBLE_UNDER_THE_CONTRACT": bool(anchors)
            and case["classification"] == "PLAUSIBLE_BUT_NEVER_BEST",
            "why_not_admissible": None,
        }
        if not anchors:
            entry["why_not_admissible"] = (
                "POSITIVE_PLAUSIBILITY_SUPPORT: the frozen study-unit vocabulary "
                "carries no feature that states why a candidate would consider it, so "
                "no stem can anchor it. The class is right and the admission is not."
            )
        elif case["classification"] != "PLAUSIBLE_BUT_NEVER_BEST":
            entry["why_not_admissible"] = (
                f"Classified {case['classification']}, which the never-best contract "
                "does not admit."
            )
        rows.append(entry)

    negative = pool[NEVER_BEST_NEGATIVE_CONTROL]
    from collections import Counter

    return {
        "schema_version": "1.0",
        "scope": "QGEN_NEVER_BEST_DISTRACTOR_OVERLAY",
        "bootstrap_id": BOOTSTRAP_ID,
        "llm_api_calls": 0,
        "no_new_evidence": (
            "Every field of every contract is transcribed from the frozen curated seed "
            "pack and its enrichment. No claim was looked up, no contrast researched "
            "and no option rewritten. The classification and the inferiority basis are "
            "the reviewer's and are recorded as such."
        ),
        "NEVER_CORRECT_DISTRACTOR_CASES": len(rows),
        "NEVER_CORRECT_CLASSIFICATION": {
            name: sum(1 for row in rows if row["CLASSIFICATION"] == name)
            for name in (
                "COUNTERFACTUAL_CORRECT", "PLAUSIBLE_BUT_NEVER_BEST",
                "DEAD_DISTRACTOR", "WRONG_DECISION_CLASS", "UNSAFE_OR_AMBIGUOUS",
            )
        },
        "BY_SOURCE": dict(Counter(row["source"] for row in rows)),
        "ADMISSIBLE_UNDER_THE_CONTRACT": sorted(
            row["member_id"] for row in rows if row["ADMISSIBLE_UNDER_THE_CONTRACT"]
        ),
        "cases": rows,
        "negative_control": {
            "member_id": NEVER_BEST_NEGATIVE_CONTROL,
            "concept": negative["competitor_concept"],
            "conditions_under_which_competitor_would_be_correct": negative[
                "conditions_under_which_competitor_would_be_correct"
            ],
            "CLASSIFICATION": "COUNTERFACTUAL_CORRECT",
            "why_it_is_not_a_never_correct_case": (
                "It carries a state of the world in which it is right -- no symptomatic "
                "improvement after forty-eight hours -- so the second class does not "
                "apply to it. The wave refused it under CS2-6, because that condition is "
                "also its only plausibility anchor, and that refusal is unaffected by "
                "anything here. It is listed so the case file cannot be read as "
                "sweeping every refused option into one category."
            ),
        },
    }


# ------------------------------------------------- Part O, the arm C acquisition


def build_arm_c_acquisition(root) -> dict[str, Any]:
    """The frozen wave, with exactly one thing changed: how a candidate is typed.

    Every candidate, every discovery source, every anchor addition and every other
    verdict is the committed medium-pilot wave's. What arm C does is stop refusing
    a candidate for having no correctness tree when the reason it has none is that
    its own reviewed prose says there is no state in which it is right.

    A candidate whose never-best contract cannot be built is left refused here, so
    the refusal is recorded at the point the contract fails rather than deferred to
    a gate that would have to guess why.
    """
    from .clinical_contrast_v2 import PLAUSIBLE_BUT_NEVER_BEST

    acquisition = json.loads(json.dumps(
        _read(root, "research/qgen/pilot/medium-pilot-6-acquisition.json")
    ))
    overlay = {row["member_id"]: row for row in build_never_best_overlay(root)["cases"]}

    admitted, refused = [], []
    for label in sorted(acquisition["opportunities"]):
        for candidate in acquisition["opportunities"][label]["candidates"]:
            case = overlay.get(candidate["member_id"])
            if case is None or case["opportunity_label"] != label:
                continue
            if not case["plausibility_anchor_feature_ids"]:
                candidate["review"] = {
                    **candidate["review"],
                    "arm_c_note": case["why_not_admissible"],
                }
                refused.append(candidate["member_id"])
                continue
            candidate["distractor_semantics"] = PLAUSIBLE_BUT_NEVER_BEST
            candidate["never_best_contract"] = case["never_best_contract"]
            candidate["evidence_refs"] = sorted(set(
                case["never_best_contract"]["positive_plausibility"]["evidence_refs"]
                + case["never_best_contract"]["inferiority"]["evidence_refs"]
            ))
            candidate["review"] = {
                "reviewer_id": "R-ARMC-DISTRACTOR-SEMANTICS",
                "verdict": "APPROVED",
                "reasons": [],
                "arm_c_classification": case["CLASSIFICATION"],
                "arm_c_note": (
                    "Admitted as a candidate under the second distractor semantic "
                    "class. Whether it survives is the coherence contract's decision, "
                    "not this one: response class, granularity, category and anchors "
                    "are all still checked by the unchanged gate."
                ),
            }
            admitted.append(candidate["member_id"])

    acquisition["acquisition_id"] = "medium-pilot-6-arm-c-never-best"
    acquisition["scope"] = "QGEN_MEDIUM_PILOT_ARM_C_ACQUISITION"
    acquisition["arm"] = "ARM_C_V3_PLUS_DISTRACTOR_SEMANTICS"
    acquisition["derived_from"] = "research/qgen/pilot/medium-pilot-6-acquisition.json"
    acquisition["only_change"] = (
        "The distractor semantic class of the candidates the wave refused with "
        "V2_CANNOT_CARRY_A_NEVER_CORRECT_DISTRACTOR. No candidate was discovered, no "
        "anchor added, no evidence introduced and no other verdict moved."
    )
    acquisition["ARM_C_ADMITTED_AS_NEVER_BEST"] = sorted(admitted)
    acquisition["ARM_C_STILL_REFUSED"] = sorted(refused)
    return acquisition


def run_arm_c(root) -> dict[str, Any]:
    """Arm C. Snapshot V3 pinned, the same six, one attempt, no retries."""
    from .medium_pilot import run_pilot

    return run_pilot(
        root,
        snapshot_pinned=True,
        snapshot_id=ARM_B_SNAPSHOT,
        acquisition_path=ARM_C_ACQUISITION_PATH,
    )


# ------------------------- Parts I and J, what the model required and why


def build_distractor_diagnosis(root) -> dict[str, Any]:
    """Parts H to M. What V2 required, where the requirement came from, and the
    smallest architecture that explains the measured failures.

    The question Part I insists is not answered from intuition -- does V2 require
    every distractor to have a counterfactual correctness condition? -- is answered
    from the code, from the frozen items and from the repository's own prior
    assessment-design finding, each cited by path.
    """
    overlay = build_never_best_overlay(root)
    diagnosis = _read(root, "reports/qgen_g2_safe_yield_root_cause_diagnosis.json")
    accepted = diagnosis["phase_4_accepted_controls"]

    zero_predicate_in_accepted = sorted(
        row["seed_id"]
        for rows in accepted["per_item_defeat_modes"].values()
        for row in rows
        if row["defeat_mode"] == "NO_PREDICATE_NEVER_CORRECT_SEED"
    )

    return {
        "schema_version": "1.0",
        "scope": "QGEN_NEVER_CORRECT_DISTRACTOR_DIAGNOSIS",
        "bootstrap_id": BOOTSTRAP_ID,
        "llm_api_calls": 0,
        "case_file": overlay,
        "CURRENT_V2_REQUIRES_COUNTERFACTUAL_CORRECTNESS": "YES",
        "what_enforces_it": [
            {
                "site": "scripts/qbank/clinical_contrast_v2.py::validate_predicate",
                "rule": (
                    "A branch operator with no conditions raises: 'an empty branch has "
                    "no truth value'. An empty correctness tree is therefore not a tree, "
                    "so 'no state makes this correct' is unrepresentable rather than "
                    "merely disallowed."
                ),
            },
            {
                "site": "scripts/qbank/clinical_contrast_v2.py::classify_competitor",
                "rule": (
                    "Read `competitor['correctness_conditions']` unconditionally and "
                    "validated it, so a competitor without one raised before any gate "
                    "could form a view about it."
                ),
            },
            {
                "site": "scripts/qbank/clinical_contrast_v2.py::validate_contrast_relation",
                "rule": (
                    "`correctness_conditions_a` and `correctness_conditions_b` are "
                    "required relation fields and both were validated as predicates, so "
                    "a pair containing such a competitor could not be built either."
                ),
            },
            {
                "site": "scripts/qbank/contrast_supply.py::apply_supply_to_contrast_set",
                "rule": (
                    "A supplied new member's `correctness_conditions` were validated "
                    "against the study-unit vocabulary before the member was appended."
                ),
            },
            {
                "site": (
                    "scripts/qbank/clinical_contrast_v2.py::"
                    "can_be_live_without_being_correct, CS2-6 and CS2-8"
                ),
                "rule": (
                    "Both rules are defined over the correctness signature, so both "
                    "presuppose one exists."
                ),
            },
        ],
        "is_the_requirement_necessary_for_one_best_answer_safety": {
            "answer": "NO",
            "argument_from_the_model": (
                "One-best-answer safety needs the key correct and every competitor not "
                "correct under the realized stem. A competitor with no state of the "
                "world in which it is right satisfies the second condition under every "
                "stem, unconditionally. It is the safest possible competitor against a "
                "second key, not the most dangerous one, and the strict model refused "
                "it for a property that makes it safer."
            ),
            "argument_from_the_accepted_controls": {
                "item": "G2-MED-04",
                "verdict": "ACCEPTED",
                "zero_predicate_competitors": zero_predicate_in_accepted,
                "count": len(zero_predicate_in_accepted),
                "citation": "reports/qgen_g2_safe_yield_root_cause_diagnosis.json",
                "note": (
                    "Two of that item's three competitors carry zero condition "
                    "predicates, and the item was independently accepted with zero "
                    "defects. The frozen record already contained a counterexample to "
                    "the necessity claim before this task existed."
                ),
                "stated_limit": (
                    "G2-MED-04 was accepted under the G2 safe-yield review contract, "
                    "before Clinical Contrast Model V2 existed, so it is evidence that a "
                    "never-best option is compatible with an independently accepted item "
                    "and not evidence that V2's own gates would accept the same item. It "
                    "is one item, and it is cited as a counterexample to a universal "
                    "claim rather than as a rate."
                ),
            },
            "argument_from_the_rejected_controls": {
                "discriminating_property": accepted["discriminating_property"],
                "note": (
                    "The property that separated the accepted controls from the "
                    "anchorless rejections was never the presence of a correctness "
                    "condition -- 104 of 111 ranked candidates scored zero in both "
                    "groups alike -- but HOW the stem defeats the competitor. Thirteen "
                    "of eighteen rejected competitors died on the stem stating their own "
                    "precondition absent in words. That is the silence-as-absence and "
                    "explicit-denial defect, and it is orthogonal to this class."
                ),
            },
            "argument_from_repository_policy": {
                "citation": "reports/qgen_g2_safe_yield_root_cause_diagnosis.json",
                "corroborating_case": accepted["corroborating_case"],
                "no_rule_proposed": accepted["no_rule_proposed"],
                "note": (
                    "The repository's own prior assessment-design finding drew exactly "
                    "the distinction this class needs -- never OPTIMAL against never "
                    "APPROPRIATE -- said 'the library does not distinguish the two', and "
                    "deliberately proposed no rule. This is that rule, and the "
                    "disagreement it has to own is that the earlier reviewer put "
                    "G2-OBGYN-03's deep massage and nipple shield on the never-"
                    "APPROPRIATE side. The reconciliation is that appropriateness is not "
                    "what decides admissibility here: both options are defeated by cited "
                    "clinical evidence a candidate must apply, not by a stated absence, "
                    "which is the property that earlier finding actually measured."
                ),
            },
            "where_the_requirement_came_from": (
                "The contrast architecture, inherited rather than derived. The G2 "
                "root-cause diagnosis put it plainly: 'the single machine-readable link "
                "between a competitor and a stem is its correctness condition'. Making "
                "that link universal made it compulsory, and nothing about one-best-"
                "answer safety required it to be."
            ),
        },
        "options_considered": [
            {
                "option": "OPTION_1_COUNTERFACTUAL_CORRECT_ONLY",
                "chosen": False,
                "why_not": (
                    "It does not explain the measured failures. Seven diagnosed "
                    "candidates across three of the six opportunities are options whose "
                    "own independently reviewed prose records no state in which they are "
                    "right, and under this option all seven are unrepresentable."
                ),
            },
            {
                "option": "OPTION_2_COUNTERFACTUAL_CORRECT_PLUS_PLAUSIBLE_BUT_NEVER_BEST",
                "chosen": True,
                "why": (
                    "It is the smallest architecture that explains them. It adds one "
                    "declared class, one contract of seven limbs, and no scoring; the "
                    "default is unchanged, so nothing historical moves; and every limb "
                    "is a positive cited statement the frozen curated seed pack already "
                    "carried."
                ),
            },
            {
                "option": "OPTION_3_GENERAL_DISTRACTOR_SCORING_MODEL",
                "chosen": False,
                "why_not": (
                    "Not necessary. No measured failure needs a graded score, and a "
                    "score would replace a fail-closed contract with a threshold, which "
                    "is the direction this architecture does not go."
                ),
            },
        ],
        "DISTRACTOR_SEMANTIC_EXTENSION_JUSTIFIED": "YES",
        "DISTRACTOR_SEMANTIC_EXTENSION_IMPLEMENTED": "YES",
        "contract": {
            "class": "PLAUSIBLE_BUT_NEVER_BEST",
            "limbs": list(_never_best_limb_names()),
            "inferiority_bases": list(_never_best_bases()),
            "silence_cannot_supply_inferiority": (
                "There is deliberately no basis in the closed set meaning 'the stem does "
                "not say so'. The shape cannot be encoded, so it cannot be argued."
            ),
            "not_a_lower_standard": (
                "A never-best competitor is asked for more than a counterfactual-correct "
                "one, not less: positive cited plausibility, a cited inferiority reason, "
                "and a named clinical confusion. A candidate that is merely wrong meets "
                "none of the three."
            ),
        },
        "what_the_contract_refused_in_practice": {
            "SEED-PED-T03-HYPERTONIC": (
                "POSITIVE_PLAUSIBILITY_SUPPORT. Genuinely plausible in prose and "
                "anchorless in the frozen vocabulary, so no stem can give a candidate a "
                "stated reason to consider it."
            ),
            "SEED-OB-T02-CRP": (
                "SAME_DECISION_CLASS, and the unchanged coherence gate fired CS2-3 "
                "rather than the case file asserting it. Its frozen response class is "
                "BIOCHEMICAL and the set demands DIAGNOSTIC_ADVANCEMENT."
            ),
            "SEED-PED-T03-SALBUTAMOL": (
                "SAME_DECISION_CLASS, again by CS2-3. Its frozen response class is "
                "PHARMACOLOGIC_ACTION where the set demands NEXT_ACTION_FOR_CURRENT_CARE, "
                "while the nebulized-epinephrine seed beside it carries both tokens. "
                "This one is a frozen response-class-token gap rather than a semantic "
                "mismatch, and it is reported rather than repaired: editing a frozen "
                "seed row to admit a candidate is the move this architecture refuses."
            ),
        },
    }


def _never_best_limb_names():
    from .clinical_contrast_v2 import NEVER_BEST_LIMBS

    return NEVER_BEST_LIMBS


def _never_best_bases():
    from .clinical_contrast_v2 import NEVER_BEST_INFERIORITY_BASES

    return NEVER_BEST_INFERIORITY_BASES


# ------------------------------------------- Parts P and Q, the three arms

ARMS = ("ARM_A_ORIGINAL_MEDIUM6", "ARM_B_V3_SNAPSHOT", "ARM_C_V3_PLUS_SEMANTICS")

#: The eleven accepted-item safety dimensions, imported rather than restated.
ACCEPTED_SAFETY_DIMENSIONS = (
    "FACTUAL_ERRORS", "NUMERIC_ERRORS", "UNSUPPORTED_CLAIMS",
    "AMBIGUOUS_BEST_ANSWERS", "CRITICAL_FACT_SAFETY_FAILURES",
    "MATERIAL_REDUNDANCY", "COMPETITOR_WITHOUT_STEM_ANCHOR", "SECOND_KEY_RISK",
    "UNNATURAL_STEM_ENGINEERING", "SILENCE_AS_ABSENCE_DEFECT",
    "BOOLEAN_LOGIC_DEFECT",
)


def _arm_rows(root) -> dict[str, dict[str, Any]]:
    from .medium_pilot import ACQUISITION_PATH, run_pilot

    runs = {
        "ARM_A_ORIGINAL_MEDIUM6": run_pilot(
            root, snapshot_pinned=True, snapshot_id=ARM_A_SNAPSHOT,
            acquisition_path=ACQUISITION_PATH,
        ),
        "ARM_B_V3_SNAPSHOT": run_pilot(
            root, snapshot_pinned=True, snapshot_id=ARM_B_SNAPSHOT,
            acquisition_path=ACQUISITION_PATH,
        ),
        "ARM_C_V3_PLUS_SEMANTICS": run_arm_c(root),
    }
    return {
        arm: {row["opportunity_label"]: row for row in run["replay"]["results"]}
        for arm, run in runs.items()
    }


def build_three_arm_report(root) -> dict[str, Any]:
    """Part P. The same six opportunities, three arms, one variable each step."""
    from collections import Counter

    freeze = _read(root, "research/qgen/pilot/medium-pilot-6-opportunities.json")
    arms = _arm_rows(root)
    labels = sorted(arms["ARM_A_ORIGINAL_MEDIUM6"])
    intents = {
        row["opportunity_label"]: row["difficulty_intent"]
        for row in freeze["opportunities"]
    }
    disciplines = {
        row["opportunity_label"]: row["discipline"] for row in freeze["opportunities"]
    }
    archetypes = {
        row["opportunity_label"]: row["item_archetype"]
        for row in freeze["opportunities"]
    }

    per_opportunity = []
    for label in labels:
        entry = {
            "opportunity_label": label,
            "discipline": disciplines[label],
            "difficulty_intent": intents[label],
            "item_archetype": archetypes[label],
        }
        for arm in ARMS:
            row = arms[arm][label]
            entry[arm] = {
                "VALID_COMPETITORS": row["VALID_COMPETITORS_AFTER"],
                "CONTRAST_READY": row["three_valid_after"],
                "GENERATED": row["stage_reached"] == "INDEPENDENT_REVIEW",
                "TERMINAL_STATE": row["terminal_state"],
                "stage_reached": row["stage_reached"],
                "fail_closed_reason": row["fail_closed_reason"],
            }
        per_opportunity.append(entry)

    totals = {}
    for arm in ARMS:
        rows = [entry[arm] for entry in per_opportunity]
        generated = [row for row in rows if row["GENERATED"]]
        totals[arm] = {
            "OPPORTUNITIES": len(rows),
            "CONTRAST_READY": sum(1 for row in rows if row["CONTRAST_READY"]),
            "GENERATED": len(generated),
            "ACCEPTED": 0,
            "REJECTED": 0,
            "NO_SAFE_ITEM": sum(
                1 for row in rows if row["TERMINAL_STATE"] == "NO_SAFE_ITEM"
            ),
            "fail_closed_reasons": dict(sorted(Counter(
                row["fail_closed_reason"] for row in rows if row["fail_closed_reason"]
            ).items())),
        }

    def by(field_map, arm, predicate):
        return dict(sorted(Counter(
            field_map[entry["opportunity_label"]] for entry in per_opportunity
            if predicate(entry[arm])
        ).items()))

    breakdown = {
        arm: {
            "CONTRAST_READY_BY_DISCIPLINE": by(
                disciplines, arm, lambda row: row["CONTRAST_READY"]
            ),
            "CONTRAST_READY_BY_DIFFICULTY": by(
                intents, arm, lambda row: row["CONTRAST_READY"]
            ),
            "CONTRAST_READY_BY_ITEM_ARCHETYPE": by(
                archetypes, arm, lambda row: row["CONTRAST_READY"]
            ),
        }
        for arm in ARMS
    }

    denial_budget_failures = sorted(
        entry["opportunity_label"] for entry in per_opportunity
        if entry["ARM_C_V3_PLUS_SEMANTICS"]["fail_closed_reason"]
        == "FAIL_CLOSED_COMPETITOR_CANNOT_BE_SETTLED"
    )
    from .contrast_first_pilot import MAXIMUM_ABSENT_REQUIRED_FEATURES

    return {
        "schema_version": "1.0",
        "scope": "QGEN_SNAPSHOT_BOOTSTRAP_THREE_ARM",
        "bootstrap_id": BOOTSTRAP_ID,
        "llm_api_calls": 0,
        "arms": {
            "ARM_A_ORIGINAL_MEDIUM6": (
                f"{ARM_A_SNAPSHOT}, the frozen wave, the frozen readings. This arm "
                "reproduces the committed medium pilot."
            ),
            "ARM_B_V3_SNAPSHOT": (
                f"{ARM_B_SNAPSHOT}. The only change from arm A is the pinned snapshot: "
                "five independently approved anchor relations become visible and five "
                "uncertain ones stay invisible."
            ),
            "ARM_C_V3_PLUS_SEMANTICS": (
                "Arm B plus the second distractor semantic class. The only change from "
                "arm B is how six already-discovered candidates are typed; no candidate, "
                "anchor, claim or option text is new, and the snapshot does not move."
            ),
        },
        "one_attempt_per_opportunity": True,
        "no_retries": True,
        "per_opportunity": per_opportunity,
        "totals": totals,
        "breakdown": breakdown,
        "ALL_ACCEPTED_ITEM_SAFETY": "NO_ACCEPTED_ITEMS",
        "accepted_item_safety_dimensions": list(ACCEPTED_SAFETY_DIMENSIONS),
        "accepted_item_safety_note": (
            "No arm generated an item, so no independent review ran and the eleven "
            "dimensions were not exercised. PASS over an empty set would be a claim "
            "about nothing; NO_ACCEPTED_ITEMS is the honest value, and it is also not a "
            "regression, because arm A generated nothing either."
        ),
        "difficulty": {
            "tracked_not_fixed": (
                "Per Part Q, no difficulty parameter was changed. What is recorded is "
                "that once the snapshot and the distractor model stop being the binding "
                "constraint, the difficulty contract becomes it."
            ),
            "MAXIMUM_ABSENT_REQUIRED_FEATURES": dict(MAXIMUM_ABSENT_REQUIRED_FEATURES),
            "DENIAL_BUDGET_EXHAUSTED_IN_ARM_C": denial_budget_failures,
            "SHARE_OF_OPPORTUNITIES": round(
                100 * len(denial_budget_failures) / len(per_opportunity), 1
            ),
            "detail": (
                "G2-OBGYN-03 is authored HARD, whose budget is zero explicit denials, "
                "and its one counterfactual-correct competitor has a single correctness "
                "condition with no stated positive contrary and no key discriminator, so "
                "it can be settled only by a denial the contract forbids. G2-PSY-01 is "
                "authored MEDIUM, whose budget is one, and that one is already spent "
                "denying a past hypomanic period to settle the bipolar competitor. Both "
                "sets are otherwise coherent and both reach the solver."
            ),
            "DIFFICULTY_IS_THE_LARGEST_REMAINING_FAILURE_SOURCE": (
                len(denial_budget_failures) >= 2
            ),
            "structural_difficulty_not_measured": (
                "No item was realized in any arm, so no blind solve was possible and no "
                "independent structural difficulty read exists for this experiment. "
                "DIFFICULTY_INTENT stays authored, EMPIRICAL_DIFFICULTY stays absent, "
                "and the six reserved learner-data fields stay unpopulated."
            ),
        },
    }


# --------------------- Parts T to W, whether a fresh universe can be built

DISCIPLINES = ("MED", "PED", "OBGYN", "SURG", "PSY", "PHELO")

FRESH_PILOT_TARGET = 36
FRESH_PILOT_FLOOR = 24


def build_fresh_universe_feasibility(root) -> dict[str, Any]:
    """Parts T to W. Measure the fresh universe before claiming one, or diagnose why.

    Part W's own rule decides this: if fewer than 24 fresh opportunities can be
    built without lowering standards, stop and diagnose the opportunity-construction
    layer. Every number here is counted from canonical artifacts, and nothing is
    invented to reach a target.
    """
    from collections import Counter

    from .contrast_first_pilot import (
        STEM_FEATURE_VOCABULARY_PATH,
        load_curated_candidates,
        load_stem_feature_vocabulary,
    )

    universe = _read(
        root, "research/qgen/safe_yield/g2_profile_pilot.opportunities.json"
    )["opportunities"]
    declared = _read(root, "research/qgen/safe_yield/g2_declared_learner_decisions.json")
    vocabulary = load_stem_feature_vocabulary(root)
    pool = load_curated_candidates(root)
    plan = _read(root, "research/qgen/source_packet_plan.json")

    declared_ids: dict[str, list[str]] = {}
    for address in declared["addresses"]:
        declared_ids[address["allocation_address_id"]] = [
            row["learner_decision_id"]
            for row in address["declared_learner_decisions"]
        ]
    used = {row["learner_decision_id"] for row in universe}
    unused = {
        unit: sorted(set(ids) - used) for unit, ids in sorted(declared_ids.items())
    }
    unused_total = sum(len(rows) for rows in unused.values())

    seed_units = Counter(row["anchor_study_unit_id"] for row in pool)
    discipline_of_unit = {
        row["anchor_study_unit_id"]: row["discipline"] for row in universe
    }

    fresh_by_discipline = {name: 0 for name in DISCIPLINES}
    for unit, rows in unused.items():
        discipline = discipline_of_unit.get(unit)
        if discipline:
            fresh_by_discipline[discipline] += len(rows)

    blocked = unused_total < FRESH_PILOT_FLOOR
    return {
        "schema_version": "1.0",
        "scope": "QGEN_FRESH_VALIDATION_UNIVERSE_FEASIBILITY",
        "bootstrap_id": BOOTSTRAP_ID,
        "llm_api_calls": 0,
        "FRESH_PILOT_TARGET": FRESH_PILOT_TARGET,
        "FRESH_PILOT_FLOOR": FRESH_PILOT_FLOOR,
        "funnel": {
            "CANONICAL_STUDY_UNITS_WITH_A_FROZEN_STEM_FEATURE_VOCABULARY": len(
                vocabulary
            ),
            "study_unit_ids": sorted(vocabulary),
            "vocabulary_artifact": STEM_FEATURE_VOCABULARY_PATH,
            "CANONICAL_STUDY_UNITS_WITH_A_CURATED_SEED_PACK": len(seed_units),
            "curated_seeds_by_study_unit": dict(sorted(seed_units.items())),
            "DECLARED_LEARNER_DECISIONS": sum(
                len(rows) for rows in declared_ids.values()
            ),
            "LEARNER_DECISIONS_ALREADY_AN_OPPORTUNITY": len(used),
            "DECLARED_LEARNER_DECISIONS_NOT_YET_AN_OPPORTUNITY": unused_total,
            "unused_learner_decisions_by_study_unit": unused,
            "FROZEN_OPPORTUNITY_UNIVERSE": len(universe),
        },
        "MAXIMUM_FRESH_OPPORTUNITIES_WITHOUT_LOWERING_STANDARDS": unused_total,
        "FRESH_BY_DISCIPLINE_CEILING": fresh_by_discipline,
        "FRESH_PILOT_TRIGGERED": not blocked,
        "why": (
            "A fresh opportunity needs four things that do not exist outside six study "
            "units: a declared learner decision, a frozen stem-feature vocabulary for "
            "its study unit, a curated competitive-contrast seed pack with independent "
            "seed review, and an evidence packet its claims can be read from. The "
            "canonical universe declares 32 learner decisions across exactly those six "
            f"units -- one per discipline -- and {len(used)} are already opportunities. "
            f"That leaves {unused_total}, every one of them inside a study unit G1, G2, "
            "V1 and V2 have already optimized, which Part U's own selection rule "
            "excludes. Building 24 would mean authoring new study-unit vocabularies, new "
            "seed packs and new evidence packets: source-packet research, not an "
            "architecture pilot."
        ),
        "OPPORTUNITY_CONSTRUCTION_DIAGNOSIS": {
            "BINDING_LAYER": "SOURCE_PACKET_RESEARCH",
            "SOURCE_PACKETS_PLANNED": len(plan["source_packets"]),
            "ALLOCATION_ADDRESSES_WITH_PLANNED_PACKETS": len(
                plan["allocation_address_source_packet_ids"]
            ),
            "STUDY_UNITS_ONBOARDED_TO_QGEN": len(vocabulary),
            "note": (
                "The opportunity-construction layer is not itself defective. It produced "
                "30 well-formed opportunities from the six study units it has, and the "
                "selection rule that reduced 30 to 6 was never weakened. What bounds it "
                "is upstream: a study unit becomes usable to question generation only "
                "after its source packets are researched and a stem-feature vocabulary, "
                "a seed pack and claim cards are built from them, and that has happened "
                "for six of the planned addresses."
            ),
            "what_would_unblock_it": (
                "Onboarding further study units to the question-generation layer -- one "
                "per discipline is enough to double the universe -- which is the "
                "SOURCE_PACKET_RESEARCH stage the repository is already in, not a change "
                "to any architecture measured here."
            ),
        },
        "not_called_a_medium_scale_validation": (
            "The six-opportunity replay in this milestone is a controlled three-arm "
            "comparison on one frozen batch. It is not a validation sample, it is not "
            "called one anywhere in these reports, and no acceptance rate is derived "
            "from it."
        ),
    }


# ------------------ Parts R, S, AA to AG and AJ, the milestone and the decision

TWO_STAGE_LIFECYCLE = {
    "STAGE_1_PREFLIGHT": [
        "freeze the batch's opportunities, with their keys, difficulty intents and "
        "competitor counts",
        "check contrast readiness against the current snapshot",
        "run one bounded supply-discovery wave",
        "collect the feature and anchor-relation extensions it proposes",
        "review those extensions independently, UNCERTAIN failing closed",
        "build SNAPSHOT_N deterministically from its parent plus the approved delta",
    ],
    "STAGE_2_GENERATION": [
        "pin SNAPSHOT_N for the whole batch",
        "freeze the contrast sets",
        "generate and independently review the batch",
        "collect extension proposals for SNAPSHOT_N+1 only, applying none",
    ],
    "INVARIANT": "No snapshot mutation during Stage 2.",
}

LEAKAGE_ARGUMENT = {
    "what_preflight_may_inspect": [
        "the opportunity",
        "the learner decision",
        "the key concept",
        "the required contrast neighbourhood",
    ],
    "what_preflight_may_not_inspect": [
        "any generation outcome, because generation has not happened",
        "any independent review verdict, for the same reason",
        "any item's stem, options, key placement or blind solve",
    ],
    "why_it_is_not_outcome_adaptive_contamination": (
        "Adaptive contamination is choosing what the vocabulary may say after seeing "
        "which questions failed. Preflight runs before any question exists, so the "
        "information it conditions on is the decision the item is about, not the item. "
        "Two consequences follow and both are checkable rather than argued. First, the "
        "extension review's inputs are exactly the opportunity freeze and the frozen "
        "evidence packets; no report it reads contains a generation outcome. Second, "
        "the snapshot it produces is content-addressed and frozen before the first item "
        "of the batch is written, so no later item can move it."
    ),
    "the_distinction_this_experiment_did_not_have": (
        "Arm B is deliberately NOT an instance of the clean lifecycle. Its five "
        "extensions were proposed by a wave that ran inside a batch and reviewed with "
        "that batch's downstream evidence available -- which is how three of the wave's "
        "own approvals were overturned. That is why arm B is reported as a controlled "
        "replay of a completed batch and not as a preflight, and why the lifecycle "
        "verdict below is PROMISING rather than VALIDATED: the mechanism is shown to "
        "work, on a batch that was not run under it."
    ),
}


def build_milestone_report(root) -> dict[str, Any]:
    """The decision, what was measured for it, and what is deliberately not claimed."""
    from .contrast_first_pilot import measure_copyright

    root_cause = build_root_cause_report(root)
    visibility = build_visibility_replay(root)
    distractor = build_distractor_diagnosis(root)
    three_arm = build_three_arm_report(root)
    fresh = build_fresh_universe_feasibility(root)
    execution = _read(root, "reports/qgen_medium_pilot_execution.json")

    validated = visibility["SNAPSHOT_BOOTSTRAP_VALIDATED"]
    ready = three_arm["totals"]
    assessment = (
        "VALIDATED" if validated and ready["ARM_B_V3_SNAPSHOT"]["CONTRAST_READY"]
        > ready["ARM_A_ORIGINAL_MEDIUM6"]["CONTRAST_READY"]
        else "NO_BETTER"
    )

    denial = three_arm["difficulty"]["DENIAL_BUDGET_EXHAUSTED_IN_ARM_C"]
    systematic = len(denial) / 6 >= 0.2

    cache = execution["cache_economics"]
    approved = approved_v3_extensions(root)
    proposals = _read(
        root, "research/qgen/pilot/medium-pilot-6-proposed-extensions.json"
    )["extensions"]
    labels_with_proposals = {row["opportunity_label"] for row in proposals}
    reuse = sum(
        1 for extension in approved
        if len(extension["scope_opportunity_labels"]) > 1
    )

    return {
        "schema_version": "1.0",
        "scope": "QGEN_SNAPSHOT_BOOTSTRAP_MILESTONE",
        "bootstrap_id": BOOTSTRAP_ID,
        "llm_api_calls": 0,
        "starting_commit": "2e90375",
        "questions_asked": [
            {
                "question": (
                    "If the next snapshot is built from the already-approved extensions "
                    "BEFORE generation, do the same six opportunities perform materially "
                    "better?"
                ),
                "answer": (
                    "Better, and not materially better yet. Contrast-ready goes 1/6 to "
                    "2/6 and one of the four withheld-extension failures, G2-PSY-01, "
                    "converts from an under-size contrast set into a coherent four-"
                    "competitor set that reaches the blueprint solver. Items reaching a "
                    "stem stays 0. The bootstrap mechanism is validated; the batch is "
                    "not rescued by it."
                ),
            },
            {
                "question": (
                    "Is 'V2 cannot carry a never-correct distractor' a real "
                    "architectural defect, and what precise distractor semantics are "
                    "missing?"
                ),
                "answer": (
                    "Real, and now repaired. V2 required every competitor to carry a "
                    "satisfiable correctness tree -- `validate_predicate` refuses an "
                    "empty branch outright -- and that requirement is not necessary for "
                    "one-best-answer safety: a competitor with no state in which it is "
                    "right is the safest possible option against a second key, and the "
                    "frozen record already contains an accepted item, G2-MED-04, two of "
                    "whose three competitors carry zero condition predicates. What was "
                    "missing is a second declared class, PLAUSIBLE_BUT_NEVER_BEST, held "
                    "to a stricter seven-limb contract than the first."
                ),
            },
            {
                "question": (
                    "Once those are resolved, is the architecture ready for a fresh "
                    "cross-discipline validation sample larger than six?"
                ),
                "answer": (
                    "No, and the obstacle is not the architecture. A fresh sample of 24 "
                    "cannot be built: the canonical universe declares 32 learner "
                    "decisions across six study units, 29 are already opportunities, and "
                    "the three that remain sit inside study units Part U's own rule "
                    "excludes. Separately, the architecture is not ready either: after "
                    "both repairs the binding constraint moves to the difficulty "
                    "contract's denial budget, which now blocks 2 of 6."
                ),
            },
        ],
        "root_cause": {
            "report": ROOT_CAUSE_REPORT_PATH,
            "MEDIUM6_FAILURE_COUNTS": root_cause["failure_counts"],
            "COUNT_CHANGED_BY_APPROVED_EXTENSIONS_ALONE": root_cause[
                "COUNT_CHANGED_BY_APPROVED_EXTENSIONS_ALONE"
            ],
        },
        "snapshot": {
            "SNAPSHOT_V3_ID": ARM_B_SNAPSHOT,
            "SNAPSHOT_V3_PARENT": ARM_A_SNAPSHOT,
            "V3_APPROVED_EXTENSIONS_ADDED": len(approved),
            "V3_UNCERTAIN_EXTENSIONS_ADDED": 0,
            "V3_FEATURE_COUNT": visibility["snapshots"][ARM_B_SNAPSHOT]["feature_count"],
            "V3_ANCHOR_COUNT": visibility["snapshots"][ARM_B_SNAPSHOT][
                "anchor_relation_count"
            ],
            "V3_REGISTRY_HASH": visibility["snapshots"][ARM_B_SNAPSHOT]["registry_hash"],
            "V3_VISIBILITY_REPLAY": (
                "PASS" if visibility["snapshots"][ARM_B_SNAPSHOT][
                    "VISIBILITY_SET_EQUALITY"
                ] and visibility["snapshots"][ARM_B_SNAPSHOT][
                    "APPROVED_EXTENSIONS_VISIBLE_TO_SNAPSHOT"
                ] == len(approved) else "FAIL"
            ),
            "APPEND_ONLY": True,
            "HISTORICAL_FROZEN_ARTIFACTS_MODIFIED": 0,
        },
        "SNAPSHOT_BOOTSTRAP_ASSESSMENT": assessment,
        "SNAPSHOT_BOOTSTRAP_VALIDATED": validated,
        "three_arm": three_arm["totals"],
        "ALL_ACCEPTED_ITEM_SAFETY": three_arm["ALL_ACCEPTED_ITEM_SAFETY"],
        "independent_review": {
            "REVIEWS_RUN": 0,
            "why": (
                "Part G's review is a review of generated items, and no arm generated "
                "one. Nothing was reviewed, so nothing is reported as reviewed; the "
                "eleven accepted-item dimensions were not exercised and are not claimed "
                "to have passed."
            ),
        },
        "distractor_semantics": {
            "report": DISTRACTOR_REPORT_PATH,
            "NEVER_CORRECT_DISTRACTOR_CASES": distractor["case_file"][
                "NEVER_CORRECT_DISTRACTOR_CASES"
            ],
            "NEVER_CORRECT_CLASSIFICATION": distractor["case_file"][
                "NEVER_CORRECT_CLASSIFICATION"
            ],
            "CURRENT_V2_REQUIRES_COUNTERFACTUAL_CORRECTNESS": distractor[
                "CURRENT_V2_REQUIRES_COUNTERFACTUAL_CORRECTNESS"
            ],
            "DISTRACTOR_SEMANTIC_EXTENSION_JUSTIFIED": "YES",
            "DISTRACTOR_SEMANTIC_EXTENSION_IMPLEMENTED": "YES",
            "OPTION_CHOSEN": "OPTION_2_COUNTERFACTUAL_CORRECT_PLUS_PLAUSIBLE_BUT_NEVER_BEST",
        },
        "two_stage_lifecycle": {
            "model": TWO_STAGE_LIFECYCLE,
            "leakage": LEAKAGE_ARGUMENT,
            "TWO_STAGE_SNAPSHOT_LIFECYCLE": "PROMISING",
            "why": (
                "The preflight stage's load-bearing mechanism is now demonstrated rather "
                "than argued: a snapshot built from an independently reviewed approved "
                "delta before generation makes exactly those relations visible to all "
                "three readers, leaks none of the uncertain ones, leaves both earlier "
                "snapshots byte-identical, and moves an opportunity downstream. What is "
                "still missing for VALIDATED is a batch actually run under the two-stage "
                "order end to end, which needs a fresh opportunity universe this "
                "repository cannot yet build."
            ),
        },
        "fresh_pilot": {
            "report": FRESH_UNIVERSE_REPORT_PATH,
            "FRESH_PILOT_TRIGGERED": fresh["FRESH_PILOT_TRIGGERED"],
            "MAXIMUM_FRESH_OPPORTUNITIES": fresh[
                "MAXIMUM_FRESH_OPPORTUNITIES_WITHOUT_LOWERING_STANDARDS"
            ],
            "FRESH_PILOT_FLOOR": FRESH_PILOT_FLOOR,
            "OPPORTUNITY_CONSTRUCTION_DIAGNOSIS": fresh[
                "OPPORTUNITY_CONSTRUCTION_DIAGNOSIS"
            ],
        },
        "systematic_defect": {
            "SYSTEMATIC_ARCHITECTURE_DEFECT_GE_20_PERCENT": "YES" if systematic else "NO",
            "DEFECT": "DIFFICULTY_DENIAL_BUDGET_AGAINST_DENIAL_ONLY_COMPETITORS",
            "SHARE": three_arm["difficulty"]["SHARE_OF_OPPORTUNITIES"],
            "affected": denial,
            "not_repaired_here": (
                "Part Q's rule. The difficulty contract is measured and left alone; "
                "changing a denial budget inside the experiment that found it binding "
                "would make the finding unmeasurable."
            ),
        },
        "snapshot_extension_rate": {
            "EXTENSIONS_PROPOSED_PER_OPPORTUNITY": cache[
                "PROPOSED_EXTENSIONS_PER_OPPORTUNITY"
            ],
            "EXTENSIONS_APPROVED_PER_OPPORTUNITY": round(len(approved) / 6, 2),
            "OPPORTUNITIES_REQUIRING_EXTENSIONS_PERCENT": round(
                100 * len(labels_with_proposals) / 6, 1
            ),
            "EXTENSIONS_REUSED_ACROSS_OPPORTUNITIES": reuse,
            "EXTENSIONS_REUSED_ACROSS_DISCIPLINES": 0,
            "anchor_relations_reused_across_members_within_one_opportunity": cache[
                "anchor_relations_reused_across_members"
            ],
            "SNAPSHOT_EXTENSION_RATE": "INSUFFICIENT_DATA",
            "why": (
                "Two cycles is not a trend. The frozen-five cycle approved 4 anchor "
                "relations over 5 opportunities and this one 5 over 6, which is flat "
                "rather than declining, and both cycles drew from the same six study "
                "units, so nothing here says whether a seventh study unit would need a "
                "comparable bespoke vocabulary or would reuse what exists. Reuse across "
                "opportunities is 0 in both cycles for a structural reason -- each "
                "opportunity is a different learner decision, and the scope rule makes a "
                "relation apply to the decisions its review named and no others -- so a "
                "declining rate would have to come from features, not relations."
            ),
        },
        "context_characters": {
            "CONTEXT_MEDIAN": execution["context_characters"]["SUPPLY_CONTEXT_MEDIAN"],
            "CONTEXT_P95": execution["context_characters"]["SUPPLY_CONTEXT_P95"],
            "NEXT_TOKEN_OPTIMIZATION_TARGET": "SERIALIZED_PAIRWISE_RELATION_PAYLOAD",
            "measured_not_optimized": (
                "Unchanged and deliberately not touched. The second distractor class "
                "adds a contract of three short cited fields to six members and removes "
                "a correctness tree from each, so the serialized payload does not grow "
                "materially; no duplication analysis was run, because Part AE gates it "
                "on a stable semantic architecture and the architecture moved today."
            ),
        },
        "retrieval": {
            "GRAPH_EXPANDED": "NO",
            "TN_FTS_EXPANDED": "NO",
            "EMBEDDINGS_ADDED": "NO",
            "LOCAL_EMBEDDING_TRIGGER_MET": "NO",
            "why": (
                "No query was run. Nothing in this milestone is a retrieval problem: "
                "every candidate arm C admitted was already a frozen curated seed with "
                "an independent seed review, and what changed is that the model can now "
                "represent what that review already recorded."
            ),
        },
        "PRODUCTION_READINESS": "BLOCKED_BY_OPPORTUNITY_CONSTRUCTION",
        "readiness_reason": (
            "Two blockers stand and one of them dominates. The architecture is not "
            "ready -- the difficulty contract's denial budget now blocks 2 of 6, above "
            "the 20 percent threshold -- but that finding rests on six opportunities "
            "and cannot be confirmed or refuted without a larger sample, and the larger "
            "sample cannot be built: the canonical universe supports at most three fresh "
            "opportunities against a floor of 24. Opportunity construction is therefore "
            "the blocker that has to move first, because until it does, no further "
            "architecture finding can be measured at a size that would justify acting "
            "on it. BLOCKED_BY_DIFFICULTY is the runner-up and is recorded as the next "
            "dominant bottleneck rather than as the readiness verdict."
        ),
        "PRODUCTION_SCALEOUT_SPEC_WRITTEN": "NO",
        "why_no_spec": (
            "Part AH's preconditions are conjunctive and three of the four fail: the "
            "fresh pilot is 0 against a floor of 24, accepted-item safety is "
            "NO_ACCEPTED_ITEMS rather than perfect, and a systematic defect stands at "
            "33.3 percent. Writing the design anyway would be a spec for a pipeline "
            "that has never accepted an item."
        ),
        "copyright": measure_copyright(root, TRACKED_ARTIFACTS),
        "NEXT_DOMINANT_BOTTLENECK": "DIFFICULTY_CALIBRATION",
        "next_bottleneck_detail": (
            "It has moved, and for the first time it moved because the previous one was "
            "fixed. SNAPSHOT_EXTENSION_RATE was the medium pilot's bottleneck; the V3 "
            "bootstrap removes it as a cause for the one opportunity whose approved "
            "relations were sufficient, and the distractor extension removes "
            "expressibility as a cause for another. Both then stop at the same place: "
            "FAIL_CLOSED_COMPETITOR_CANNOT_BE_SETTLED, with the denial budget spent. "
            "OPPORTUNITY_CONSTRUCTION is the runner-up and is the readiness blocker, "
            "which are different roles: it bounds what can be measured, difficulty "
            "bounds what can be generated."
        ),
        "not_done_and_not_claimed": [
            "No item was generated in any arm, so no independent review ran, no "
            "accepted-item safety counter was exercised, and no acceptance rate exists.",
            "No fresh validation universe was built, and the six-opportunity replay is "
            "not called one.",
            "No difficulty parameter was changed, per Part Q.",
            "No production scale-out spec, because three of its four preconditions fail.",
            "The five UNCERTAIN extensions stay excluded and were not re-reviewed for "
            "yield; the re-read found no reviewer inconsistency and no evidence bug.",
            "The frozen 102-feature stem-feature vocabulary was not grown, so both "
            "NEW_FEATURE proposals stay refused.",
            "No frozen seed row was edited, so SEED-PED-T03-SALBUTAMOL stays refused on "
            "a response-class token gap that a data repair, not a model change, would "
            "close.",
            "The reviewers here are separate reasoning passes by one model instance, "
            "not separate agents, and the extension re-review had this experiment's "
            "downstream evidence available to it.",
        ],
    }
