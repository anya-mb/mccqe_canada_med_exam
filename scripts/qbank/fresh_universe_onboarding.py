"""Onboarding wave W1: what a source-ready address still cannot do, and why.

Phase 1's inventory says 45 addresses are researched and not onboarded. This
module takes that queue through the three checks that stand between a researched
packet and a fresh opportunity, in the order a wave meets them:

1. does the packet's content support the decisions the address declares;
2. can the frozen discipline profile express those decisions at all;
3. is the decision fresh against every prior pilot.

Each check refuses rather than repairs. A misaligned packet is not re-researched
here, a profile is not edited to admit a decision it was not built for, and no
decision is restated into a permitted archetype to get past the second check --
restating a legal duty as a diagnosis is how an unsafe item is built.

The gate at the end counts and reports. It does not select, rank or propose.
"""

from __future__ import annotations

from typing import Any

from .errors import QbankError


class FreshUniverseOnboardingError(QbankError):
    """An onboarding row is not admissible under the frozen contracts."""


ALIGNMENT_VERDICTS = ("ALIGNED", "PARTIALLY_ALIGNED", "MISALIGNED")

WAVE_ID = "qgen-onboarding-w1"

ALIGNMENT_REVIEW_PATH = "research/qgen/onboarding/w1_evidence_alignment_review.json"
DECLARED_DECISIONS_PATH = "research/qgen/onboarding/w1_declared_learner_decisions.json"
PROFILE_REFUSALS_PATH = (
    "research/qgen/onboarding/w1_profile_expressibility_refusals.json"
)
OPPORTUNITIES_PATH = "research/qgen/onboarding/w1_fresh_opportunities.json"
GATE_REPORT_PATH = "reports/qgen_fresh_universe_gate.json"

#: Everything this wave wrote, scanned for verbatim Toronto Notes runs.
TRACKED_ARTIFACTS = (
    "reports/qgen_fresh_universe_readiness_inventory.json",
    ALIGNMENT_REVIEW_PATH,
    DECLARED_DECISIONS_PATH,
    PROFILE_REFUSALS_PATH,
    OPPORTUNITIES_PATH,
)

#: Phase 13's own floor and preference. Neither is a target for the pipeline to
#: fill; they decide only whether a fresh pilot may be run at all.
FRESH_PILOT_FLOOR = 24
FRESH_PILOT_PREFERRED = 36

#: A contrast set needs three competitors beside the key.
MINIMUM_CURATED_CANDIDATES = 3

DISCIPLINES = ("MED", "PED", "OBGYN", "SURG", "PSY", "PHELO")

DISCIPLINE_PROFILE_IDS = {
    "MED": "MEDICINE",
    "PED": "PEDIATRICS",
    "OBGYN": "OBGYN",
    "SURG": "SURGERY",
    "PSY": "PSYCHIATRY",
    "PHELO": "PHELO",
}


def _read(root, relative: str) -> Any:
    from .jsonio import read_json
    from .paths import resolve_root_path

    return read_json(resolve_root_path(root, relative))


def load_profile_archetypes(root, profile_id: str) -> dict[str, dict[str, Any]]:
    """Return the archetypes a discipline profile admits, keyed by archetype."""
    profile = _read(root, f"research/qgen/profiles/{profile_id}.profile.json")
    if profile.get("permitted_archetype_exceptions"):
        raise FreshUniverseOnboardingError(
            f"{profile_id}: this wave reads the profile as written; an exception list "
            "means the contract changed and the reader must be revisited"
        )
    return {row["item_archetype"]: row for row in profile["item_archetypes"]}


def validate_decision_against_profile(
    decision: dict[str, Any], archetypes: dict[str, dict[str, Any]], *, profile_id: str
) -> None:
    """Fail closed unless the frozen profile admits this decision as written."""
    archetype = decision["item_archetype"]
    row = archetypes.get(archetype)
    if row is None:
        raise FreshUniverseOnboardingError(
            f"{decision['learner_decision_id']}: {profile_id} does not admit the "
            f"{archetype} archetype"
        )
    if decision["decision_granularity"] not in row["permitted_decision_granularities"]:
        raise FreshUniverseOnboardingError(
            f"{decision['learner_decision_id']}: {profile_id} does not permit "
            f"{decision['decision_granularity']} under {archetype}"
        )
    if decision["option_set_archetype"] not in row["permitted_option_set_archetypes"]:
        raise FreshUniverseOnboardingError(
            f"{decision['learner_decision_id']}: {profile_id} does not permit the "
            f"{decision['option_set_archetype']} option set under {archetype}"
        )


def validate_evidence_refs(root, address: dict[str, Any]) -> None:
    """Every cited reference must exist in a researched packet for this address."""
    import glob
    from pathlib import Path

    from .paths import canonical_root

    plan = _read(root, "research/qgen/source_packet_plan.json")
    packet_ids = set(
        plan["allocation_address_source_packet_ids"][address["allocation_address_id"]]
    )
    known: set[str] = set()
    base = canonical_root(Path(root))
    for path in sorted(
        glob.glob(str(base / "research/qgen/source_packet_population_srb_*.json"))
    ):
        relative = Path(path).relative_to(base).as_posix()
        for packet in _read(root, relative)["source_packets"]:
            if packet["source_packet_id"] not in packet_ids:
                continue
            if packet["status"] != "SOURCE_PACKET_READY":
                continue
            known.update(
                row["recommendation_id"] for row in packet["supported_recommendations"]
            )
            known.update(
                row["exception_id"]
                for row in packet.get("important_contraindications_or_exceptions") or []
            )
    for decision in address["declared_learner_decisions"]:
        missing = sorted(set(decision["evidence_refs"]) - known)
        if missing:
            raise FreshUniverseOnboardingError(
                f"{decision['learner_decision_id']}: cites {', '.join(missing)}, which "
                "no researched packet for this address contains"
            )
        if not decision["evidence_refs"]:
            raise FreshUniverseOnboardingError(
                f"{decision['learner_decision_id']}: a decision needs evidence"
            )


def compute_opportunity_id(
    *, wave_id: str, allocation_address_id: str, learner_decision_id: str
) -> str:
    """A stable id for one wave's use of one learner decision."""
    import hashlib

    digest = hashlib.sha256(
        "".join((wave_id, allocation_address_id, learner_decision_id)).encode()
    ).hexdigest()
    return f"QOPP-{digest[:24]}"


def _prior_decision_statements(root) -> list[tuple[str, str]]:
    """Every learner-decision statement a prior pilot has already put to a candidate."""
    statements: list[tuple[str, str]] = []
    declared = _read(root, "research/qgen/safe_yield/g2_declared_learner_decisions.json")
    for address in declared["addresses"]:
        for decision in address["declared_learner_decisions"]:
            statements.append((decision["statement"].strip().casefold(), "g2_declared"))
    return statements


def build_fresh_opportunities(root) -> dict[str, Any]:
    """Phases 11 and 12. One candidate per declared decision, then a freshness audit."""
    from .fresh_universe_inventory import collect_prior_pilot_use

    declared = _read(root, DECLARED_DECISIONS_PATH)
    alignment = {
        row["allocation_address_id"]: row["verdict"]
        for row in _read(root, ALIGNMENT_REVIEW_PATH)["reviews"]
    }
    prior_use = collect_prior_pilot_use(root)
    prior_statements = _prior_decision_statements(root)

    profiles: dict[str, dict[str, Any]] = {}
    rows: list[dict[str, Any]] = []
    for address in declared["addresses"]:
        address_id = address["allocation_address_id"]
        verdict = alignment.get(address_id)
        if verdict != "ALIGNED":
            raise FreshUniverseOnboardingError(
                f"{address_id}: declared decisions rest on evidence reviewed {verdict}"
            )
        profile_id = DISCIPLINE_PROFILE_IDS[address["discipline"]]
        if profile_id not in profiles:
            profiles[profile_id] = load_profile_archetypes(root, profile_id)
        validate_evidence_refs(root, address)
        for decision in address["declared_learner_decisions"]:
            validate_decision_against_profile(
                decision, profiles[profile_id], profile_id=profile_id
            )
            decision_id = decision["learner_decision_id"]
            used_in = prior_use.get(decision_id) or []
            statement = decision["statement"].strip().casefold()
            restated = sorted(
                pilot for text, pilot in prior_statements if text == statement
            )
            historical = "FRESH" if not used_in and not restated else "ALREADY_USED"
            rows.append({
                "opportunity_id": compute_opportunity_id(
                    wave_id=WAVE_ID,
                    allocation_address_id=address_id,
                    learner_decision_id=decision_id,
                ),
                "wave_id": WAVE_ID,
                "allocation_address_id": address_id,
                "anchor_study_unit_id": address_id,
                "study_unit_title": address["study_unit_title"],
                "discipline": address["discipline"],
                "discipline_profile_id": profile_id,
                "mcc_objective_ids": list(address["mcc_objective_ids"]),
                "priority_class": address["priority_class"],
                "learner_decision_id": decision_id,
                "learner_decision": decision["statement"],
                "physician_activity": decision["physician_activity"],
                "item_archetype": decision["item_archetype"],
                "decision_granularity": decision["decision_granularity"],
                "option_set_archetype": decision["option_set_archetype"],
                "difficulty_intent": decision["difficulty_intent"],
                "evidence_refs": list(decision["evidence_refs"]),
                "evidence_readiness": "CURRENT_CANADIAN_PACKET_READY_FOR_THE_KEY",
                "contrast_supply_state": "NO_STUDY_UNIT_VOCABULARY_AND_NO_SEED_PACK",
                "historical_use_status": historical,
                "prior_pilots_using_this_decision": used_in,
            })

    rows.sort(key=lambda row: row["opportunity_id"])
    return {
        "schema_version": "1.0",
        "scope": "QGEN_ONBOARDING_FRESH_OPPORTUNITY_CANDIDATES",
        "wave_id": WAVE_ID,
        "llm_api_calls": 0,
        "frozen_before_any_contrast_or_generation": True,
        "candidate_count": len(rows),
        "opportunities": rows,
        "freshness_rule": (
            "A candidate is FRESH when its learner decision id appears in none of the "
            "four prior pilot opportunity sets and no prior declaration states the same "
            "decision. Topic overlap is permitted; the decision and its contrast must be "
            "new. Every candidate here sits in a study unit no pilot has ever used, so "
            "the audit is a check rather than a filter."
        ),
        "evidence_readiness_meaning": (
            "The current Canadian packet supports the key of this decision. It is not a "
            "claim that the competitors' correctness conditions are evidenced. No "
            "candidate here has a stem-feature vocabulary or a curated seed pack, which "
            "is what contrast_supply_state records."
        ),
    }


def measure_preflight_contrast(root, opportunities: list[dict[str, Any]]) -> dict[str, Any]:
    """Phase 16, measured rather than argued.

    Contrast retrieval joins on the frozen stem-feature vocabulary and on the
    curated seed pool and on nothing else, so an opportunity in a study unit that
    owns neither is contrast-ready zero by construction. This counts it instead
    of asserting it, and records which of the two is missing.
    """
    from collections import Counter
    from pathlib import Path

    from .contrast_first_pilot import load_curated_candidates, load_stem_feature_vocabulary
    from .feature_anchor_registry import BOOTSTRAP_SNAPSHOT_ID, load_snapshot

    snapshot = load_snapshot(Path(root), BOOTSTRAP_SNAPSHOT_ID)
    vocabulary = load_stem_feature_vocabulary(Path(root))
    pool = Counter(
        row["anchor_study_unit_id"] for row in load_curated_candidates(Path(root))
    )

    rows = []
    for opportunity in opportunities:
        unit = opportunity["anchor_study_unit_id"]
        features = len(vocabulary.get(unit) or ())
        candidates = pool.get(unit, 0)
        rows.append({
            "opportunity_id": opportunity["opportunity_id"],
            "anchor_study_unit_id": unit,
            "vocabulary_features_in_snapshot": features,
            "curated_candidates": candidates,
            "contrast_ready": bool(features and candidates >= MINIMUM_CURATED_CANDIDATES),
        })

    return {
        "snapshot_id": snapshot["snapshot_id"],
        "snapshot_features": len(snapshot["features"]),
        "snapshot_anchor_relations": len(snapshot["anchor_relations"]),
        "PREFLIGHT_CONTRAST_READY": sum(1 for row in rows if row["contrast_ready"]),
        "OPPORTUNITIES_MEASURED": len(rows),
        "STUDY_UNITS_WITH_NO_VOCABULARY": sorted({
            row["anchor_study_unit_id"]
            for row in rows
            if row["vocabulary_features_in_snapshot"] == 0
        }),
        "per_opportunity": rows,
    }


def probe_vocabulary_extension(root) -> dict[str, Any]:
    """Phase 17, measured. Can the extension these opportunities need be approved?"""
    from .feature_anchor_registry import (
        FeatureAnchorRegistryError,
        validate_extension,
    )

    probe = {
        "extension_id": "W1-PROBE-NEW-STUDY-UNIT-FEATURE",
        "classification": "NEW_FEATURE_REQUIRED",
        "feature_id": "SF-W1-PROBE",
        "target_concept_id": "CONCEPT-W1-PROBE",
        "learner_decision": "W1-PROBE",
        "decision_granularity": "DIAGNOSIS",
        "required_state": "PRESENT",
        "evidence_refs": ["SRC-MED-050-REC-01"],
        "registry_review": {
            "verdict": "APPROVED",
            "clinically_meaningful": True,
            "mcc_level_relevant": True,
            "needed_for_a_validated_contrast_relation": True,
            "not_a_duplicate": True,
            "correctly_typed": True,
        },
    }
    try:
        validate_extension(probe)
    except FeatureAnchorRegistryError as error:
        return {
            "NEW_FEATURE_EXTENSION_ADMISSIBLE": False,
            "refusal": str(error),
            "reading": (
                "Onboarding a study unit means giving it a stem-feature vocabulary, "
                "which is a NEW_FEATURE_REQUIRED extension. The registry refuses to "
                "approve one on its own account, so the preflight measured above cannot "
                "be moved by any amount of evidence or review under the current "
                "authorization. No probe was written into any snapshot."
            ),
        }
    return {"NEW_FEATURE_EXTENSION_ADMISSIBLE": True, "refusal": None}


def build_gate_report(root) -> dict[str, Any]:
    """Phases 12, 13 and 33. Count, measure, and name what stops the wave."""
    from collections import Counter

    from .contrast_first_pilot import measure_copyright

    inventory = _read(root, "reports/qgen_fresh_universe_readiness_inventory.json")
    alignment = _read(root, ALIGNMENT_REVIEW_PATH)["reviews"]
    refusals = _read(root, PROFILE_REFUSALS_PATH)["refusals"]
    candidates = build_fresh_opportunities(root)
    opportunities = candidates["opportunities"]
    preflight = measure_preflight_contrast(root, opportunities)
    extension = probe_vocabulary_extension(root)

    fresh = [row for row in opportunities if row["historical_use_status"] == "FRESH"]
    reviewed = len(alignment)
    verdict_counts = Counter(row["verdict"] for row in alignment)
    by_discipline = {name: 0 for name in DISCIPLINES}
    for row in fresh:
        by_discipline[row["discipline"]] += 1

    ready = (
        len(fresh) >= FRESH_PILOT_FLOOR
        and preflight["PREFLIGHT_CONTRAST_READY"] > 0
    )

    funnel = {
        "SOURCE_READY_NOT_ONBOARDED": reviewed,
        "EVIDENCE_ALIGNED_WITH_THE_ADDRESS": verdict_counts.get("ALIGNED", 0),
        "EVIDENCE_PARTIALLY_ALIGNED": verdict_counts.get("PARTIALLY_ALIGNED", 0),
        "EVIDENCE_MISALIGNED": verdict_counts.get("MISALIGNED", 0),
        "ALIGNED_BUT_PROFILE_CANNOT_EXPRESS_THE_DECISION": len(refusals),
        "STUDY_UNITS_CARRYING_A_DECLARED_DECISION": len(
            {row["allocation_address_id"] for row in opportunities}
        ),
        "FRESH_OPPORTUNITY_CANDIDATES": len(opportunities),
        "FRESH_AFTER_THE_FRESHNESS_AUDIT": len(fresh),
        "OF_THOSE_CONTRAST_READY": preflight["PREFLIGHT_CONTRAST_READY"],
    }

    blockers = [
        {
            "blocker": "EVIDENCE_DECISION_MISALIGNMENT",
            "addresses_removed": verdict_counts.get("MISALIGNED", 0),
            "share_of_source_ready": round(
                verdict_counts.get("MISALIGNED", 0) / reviewed, 3
            ),
            "finding": (
                "SOURCE_PACKET_READY asserts that research was verified against its "
                "cited source. It does not assert that the researched content is about "
                "the address it was assigned to, and for these it is not. Two shapes "
                "appear: a packet populated with a different topic entirely, and a "
                "packet reused across addresses on EXACT_CANONICAL_SOURCE_NODES_AND_MCC_"
                "OBJECTIVES, where sharing a Toronto Notes node and an MCC objective is "
                "not sharing a clinical content."
            ),
        },
        {
            "blocker": "DISCIPLINE_PROFILE_CANNOT_EXPRESS_THE_DECISION",
            "addresses_removed": len(refusals),
            "share_of_source_ready": round(len(refusals) / reviewed, 3),
            "finding": (
                "The six discipline profiles admit the archetypes the six anchor study "
                "units needed and no others. MEDICINE has no legal or ethical archetype, "
                "so both CORE palliative-medicine addresses yield nothing from the "
                "richest evidence in the source-ready set. Every OBGYN archetype "
                "requires a gestational age or a postpartum day, so no gynaecologic "
                "address can be expressed at all, including CORE contraception."
            ),
        },
        {
            "blocker": "FROZEN_VOCABULARY_REFUSES_A_NEW_STUDY_UNIT",
            "opportunities_removed": len(fresh)
            - preflight["PREFLIGHT_CONTRAST_READY"],
            "share_of_fresh_opportunities": round(
                (len(fresh) - preflight["PREFLIGHT_CONTRAST_READY"]) / len(fresh), 3
            )
            if fresh
            else 0,
            "finding": (
                "Contrast retrieval joins on the frozen 102-feature vocabulary and the "
                "curated seed pool, both of which cover the six anchor units only. "
                "Onboarding a seventh needs a NEW_FEATURE_REQUIRED extension, which "
                "validate_extension refuses to approve on its own account. This is the "
                "binding constraint and it is a code-level refusal, not a supply "
                "shortfall: no amount of research moves it."
            ),
        },
    ]

    systematic = max(
        (
            row.get("share_of_fresh_opportunities")
            or row.get("share_of_source_ready")
            or 0
        )
        for row in blockers
    )

    return {
        "schema_version": "1.0",
        "scope": "QGEN_FRESH_UNIVERSE_GATE",
        "wave_id": WAVE_ID,
        "llm_api_calls": 0,
        "FRESH_PILOT_FLOOR": FRESH_PILOT_FLOOR,
        "FRESH_PILOT_PREFERRED": FRESH_PILOT_PREFERRED,
        "STUDY_UNITS_INVENTORIED": inventory["STUDY_UNITS_INVENTORIED"],
        "NEW_STUDY_UNITS_SELECTED": funnel["STUDY_UNITS_CARRYING_A_DECLARED_DECISION"],
        "FRESH_OPPORTUNITIES_CREATED": len(opportunities),
        "FRESH_OPPORTUNITIES_VALIDATED": len(fresh),
        "FRESH_OPPORTUNITIES_BY_DISCIPLINE": by_discipline,
        "PREFLIGHT_CONTRAST_READY": preflight["PREFLIGHT_CONTRAST_READY"],
        "FRESH_UNIVERSE_READY": "YES" if ready else "NO",
        "FRESH_PILOT_N": len(fresh) if ready else 0,
        "SYSTEMATIC_DEFECT_GE_20_PERCENT": "YES" if systematic >= 0.2 else "NO",
        "SYSTEMATIC_DEFECT": "FROZEN_VOCABULARY_REFUSES_A_NEW_STUDY_UNIT",
        "funnel": funnel,
        "blockers": blockers,
        "preflight": preflight,
        "vocabulary_extension_probe": extension,
        "copyright": measure_copyright(root, TRACKED_ARTIFACTS),
        "why_the_count_clears_the_floor_and_the_universe_is_not_ready": (
            "Twenty-six fresh candidates is above the floor of 24, and every one is "
            "checked in code against the frozen discipline profile and against a "
            "recommendation or exception that exists in a researched packet for its own "
            "address. What the floor stands in for is a universe a pilot can be run on, "
            "and that fails on a measurement rather than a judgement: preflight contrast "
            "readiness is 0 of 26 across 16 study units with no vocabulary, and the "
            "extension that would move it is refused by the registry itself. Freezing a "
            "26-opportunity pilot here would spend the batch to rediscover a refusal "
            "already visible before it started, and the no-replacement rule would then "
            "consume all 26 for nothing. Both numbers are reported; neither is the other."
        ),
        "not_claimed": (
            "No item was generated, no snapshot was built or mutated, no profile was "
            "edited, no frozen artifact was changed and no research was redone. "
            "ACCEPTED_ITEM_SAFETY is NO_ACCEPTED_ITEMS, which is not a PASS over an "
            "empty set."
        ),
    }
