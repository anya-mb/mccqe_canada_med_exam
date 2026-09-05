"""Contrast-first item construction: the pilot module, isolated from production.

The frozen four-arm benchmark settled that retrieval is not the binding
constraint. Fifteen of the twenty residual failures are the stem-anchor floor
correctly refusing a competitor because the *already frozen* stem states nothing
that would give a candidate a reason to consider it. No retriever can undo a
correct refusal, so this module changes the order instead: the contrast set and a
stem blueprint are decided first, and the stem is authored to be a coherent
presentation in which those competitors are genuinely live.

Two things are deliberately *not* done here.

Nothing in this module evaluates safety. The gates that decide whether a
competitor may appear as an option are the production ones -- ``ADM_1``,
``ADM_3`` and ``SAF_1`` inside
``profile_contrast_retrieval.retrieve_profile_aware_contrasts``, which is also
benchmark arm A -- and this module imports and calls that function rather than
reimplementing any part of it. If contrast-first improves post-stem survival it
does so against an unmoved bar.

Nothing in this module authors clinical content. Every stem feature a blueprint
may require is drawn from the frozen canonical stem-feature vocabulary of the
opportunity's anchor study unit, which was authored for the study unit and not
for any item. A blueprint that names a feature outside that vocabulary is
refused, which is the structural reason the stem cannot be reverse-engineered
around a distractor.

Design: docs/superpowers/specs/2026-09-05-contrast-first-difficulty-aware-item-construction-design.md
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Iterable, Sequence

from .errors import QbankError
from .option_set_admissibility import (
    ARCHETYPE_RESPONSE_AXIS,
    RESPONSE_CLASS_AXES,
    expand_response_tokens,
    normalize_option_text,
)
from .profile_contrast_retrieval import retrieve_profile_aware_contrasts
from .question_difficulty import DIFFICULTY_INTENTS, evaluate_difficulty_checks


class ContrastFirstError(QbankError):
    """A contrast set, matrix, blueprint or option set is inadmissible."""


CONTRAST_SET_MINIMUM = 3
CONTRAST_SET_MAXIMUM = 6

PRE_STEM_PREDICATES = ("P1", "P2", "P3", "P4", "P5", "P6")

#: Clinical roles whose data a clinician has at the point of care without having
#: gone looking for them. Roles outside this set are not forbidden; they require
#: a stated reason for being available in this scenario, which is what stops a
#: finding being inserted purely to defeat a competitor.
ROUTINELY_AVAILABLE_ROLES = frozenset({
    "AGE", "CLINICAL_JUDGEMENT", "DEMOGRAPHIC", "EXAMINATION_FINDING", "HISTORY",
    "INVESTIGATION_RESULT", "LONGITUDINAL_COURSE", "PROGRAMME_CAPACITY",
    "PROGRAMME_DOCUMENT", "PROGRAMME_OBJECTIVE", "STUDY_DESIGN", "STUDY_RESULT",
    "SYMPTOM", "SYSTEM_CONSTRAINT", "TIME_COURSE", "VITAL_SIGN",
})

#: Caps, not floors. Difficulty raises what must be integrated, never how much
#: the stem states, so every level has an upper bound on required features.
REQUIRED_FEATURE_CAP = {"EASY": 6, "MEDIUM": 8, "HARD": 11}

#: An explicit verbal denial is the cheapest way to kill a competitor and the
#: least clinically natural. HARD admits none at all, which matches the already
#: implemented difficulty check.
MAXIMUM_ABSENT_REQUIRED_FEATURES = {"EASY": 1, "MEDIUM": 1, "HARD": 0}

COHERENCE_RULES = ("CO-1", "CO-2", "CO-3", "CO-4", "CO-5", "CO-6")

#: Anchors PRESENT per competitor that each level targets. These are the minima
#: the already-implemented difficulty checks apply, restated here so the solver
#: can aim at a level rather than discover afterwards which level it hit.
ANCHOR_DENSITY_TARGET = {"EASY": 1.0, "MEDIUM": 1.0, "HARD": 2.0}

#: Absolute qualifiers an option may not carry unless the evidence states them.
#: Kept as a closed list rather than a classifier: a guess here would itself be
#: the cueing it is meant to catch.
UNSUPPORTED_QUALIFIERS = (
    "in all cases", "in every case", "always", "never", "invariably",
    "without exception", "in all patients", "under no circumstances",
)

PROHIBITED_HARD_DIFFICULTY_SOURCES = (
    "OBSCURE_TRIVIA", "SUBSPECIALIST_DETAIL", "SPECIALIST_BOARD_KNOWLEDGE",
    "TRICK_WORDING", "WITHHELD_INFORMATION", "GRATUITOUS_CALCULATION",
    "STEM_LENGTH", "IRRELEVANT_COMPLEXITY", "ARTIFICIAL_AMBIGUITY",
    "RARITY_WITHOUT_MCC_RELEVANCE",
)


# --------------------------------------------------------------- identity


def canonical_json(payload: Any) -> str:
    """Return the canonical serialization every content hash is taken over."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def content_sha256(payload: Any) -> str:
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def artifact_id(prefix: str, payload: Any) -> str:
    """Content-addressed id. The same contrast set always gets the same id."""
    if not isinstance(prefix, str) or not prefix:
        raise ContrastFirstError("an artifact id needs a prefix")
    return f"{prefix}-{content_sha256(payload)[:24]}"


# ------------------------------------------------ pre-stem admission (P1-P6)


def _review(candidate: dict[str, Any]) -> dict[str, Any]:
    review = candidate.get("independent_seed_review")
    return review if isinstance(review, dict) else {}


def admit_pre_stem(
    candidate: dict[str, Any],
    *,
    key_context: dict[str, Any],
    token_implications: dict[str, list[str]] | None = None,
) -> dict[str, Any]:
    """Apply the stem-independent admission predicate to one candidate.

    These are exactly the conditions the current pipeline already applies; the
    only change is that they are applied before a stem exists. The two
    stem-*dependent* gates, the anchor floor and the second-key ceiling, cannot
    be evaluated here and are deliberately not moved.
    """
    refusals: list[str] = []
    review = _review(candidate)

    # P1 same learner-decision dimension, read off the frozen independent review
    # rather than re-judged here.
    if review.get("same_lead_in_dimension") != "PASS" or review.get(
        "same_semantic_category"
    ) != "PASS":
        refusals.append("PRE_STEM_LEARNER_DECISION_MISMATCH")

    # P2 response-class closure, with the axis's permitted token set enforced the
    # same way option-set admissibility enforces it.
    archetype = key_context["option_set_archetype"]
    axis = ARCHETYPE_RESPONSE_AXIS.get(archetype)
    if axis is None:
        refusals.append("PRE_STEM_ARCHETYPE_MISMATCH")
    else:
        definition = RESPONSE_CLASS_AXES[axis]
        permitted = set(definition["tokens"]) | {definition["generic_token"]}
        tokens = candidate.get("response_class_tokens") or []
        closure = expand_response_tokens(
            tokens, token_implications or {}, definition["generic_token"]
        )
        if key_context["demanded_response_class"] not in closure or not set(
            tokens
        ) <= permitted:
            refusals.append("PRE_STEM_RESPONSE_CLASS_MISMATCH")

    # P3 archetype applicability on all three axes.
    if (
        key_context["discipline_profile_id"] not in (candidate.get("applicable_disciplines") or [])
        or key_context["item_archetype"] not in (candidate.get("applicable_item_archetypes") or [])
        or archetype not in (candidate.get("option_set_archetypes") or [])
    ):
        if "PRE_STEM_ARCHETYPE_MISMATCH" not in refusals:
            refusals.append("PRE_STEM_ARCHETYPE_MISMATCH")

    # P4 granularity parity.
    if candidate.get("competitor_decision_granularity") != key_context["decision_granularity"]:
        refusals.append("PRE_STEM_GRANULARITY_MISMATCH")

    # P5 an independent seed review that passed.
    if review.get("verdict") != "PASS":
        refusals.append("PRE_STEM_REVIEW_ABSENT")

    # P6 evidence on both sides: why it is plausible and what defeats it.
    if not (candidate.get("evidence_refs_for_plausibility") or []) or not (
        candidate.get("evidence_refs_for_discrimination") or []
    ):
        refusals.append("PRE_STEM_EVIDENCE_ABSENT")

    # The question the whole matrix exists to answer. A competitor no minimally
    # competent candidate would seriously consider is removed here, before a stem
    # exists, rather than repaired later by inventing a finding.
    reason = candidate.get("why_a_minimally_competent_candidate_would_consider_it")
    if not isinstance(reason, str) or not reason.strip():
        refusals.append("FAIL_CLOSED_COMPETITOR_NOT_CONSIDERABLE")

    return {
        "seed_id": candidate.get("seed_id"),
        "admitted": not refusals,
        "refusals": sorted(set(refusals)),
        "predicates_applied": list(PRE_STEM_PREDICATES),
    }


# ------------------------------------------------------------ contrast set


_CONTRAST_SET_FIELDS = (
    "contrast_set_id", "opportunity_label", "discipline_profile_id",
    "learner_decision_id", "item_archetype", "option_set_archetype",
    "demanded_response_class", "decision_granularity", "difficulty_intent",
    "anchor_study_unit_id", "key", "competitors",
)


def key_context(contrast_set: dict[str, Any]) -> dict[str, Any]:
    return {
        "discipline_profile_id": contrast_set["discipline_profile_id"],
        "item_archetype": contrast_set["item_archetype"],
        "option_set_archetype": contrast_set["option_set_archetype"],
        "demanded_response_class": contrast_set["demanded_response_class"],
        "decision_granularity": contrast_set["decision_granularity"],
    }


def validate_contrast_set(
    contrast_set: dict[str, Any],
    *,
    token_implications: dict[str, list[str]] | None = None,
) -> None:
    """Validate a contrast set built before any stem exists."""
    missing = [field for field in _CONTRAST_SET_FIELDS if field not in contrast_set]
    if missing:
        raise ContrastFirstError(f"contrast set is incomplete: {', '.join(missing)}")
    if contrast_set["difficulty_intent"] not in DIFFICULTY_INTENTS:
        raise ContrastFirstError(
            f"unknown difficulty intent: {contrast_set['difficulty_intent']}"
        )

    key = contrast_set["key"]
    conditions = key.get("correctness_conditions")
    if not isinstance(conditions, list) or not conditions:
        raise ContrastFirstError(
            "the key needs at least one correctness condition; without one there is "
            "nothing for the stem to support and no second key can be excluded"
        )
    for condition in conditions:
        if not isinstance(condition, dict) or not isinstance(
            condition.get("stem_feature_id"), str
        ) or condition.get("required_polarity") not in ("PRESENT", "ABSENT"):
            raise ContrastFirstError("a key correctness condition is malformed")
    if not (key.get("evidence_refs") or []):
        raise ContrastFirstError("the key needs at least one evidence reference")

    competitors = contrast_set["competitors"]
    if not isinstance(competitors, list) or not (
        CONTRAST_SET_MINIMUM <= len(competitors) <= CONTRAST_SET_MAXIMUM
    ):
        raise ContrastFirstError(
            f"FAIL_CLOSED_CONTRAST_SET_SIZE: {len(competitors) if isinstance(competitors, list) else 0} "
            f"competitors, outside {CONTRAST_SET_MINIMUM}-{CONTRAST_SET_MAXIMUM}"
        )

    seen: set[str] = set()
    context = key_context(contrast_set)
    for candidate in competitors:
        seed_id = candidate.get("seed_id")
        if not isinstance(seed_id, str) or seed_id in seen:
            raise ContrastFirstError(f"duplicate or missing competitor seed id: {seed_id}")
        seen.add(seed_id)
        if candidate.get("competitor_concept_id") == key.get("key_concept_id"):
            raise ContrastFirstError(
                f"{seed_id} is the key concept; a key may not compete with itself"
            )
        verdict = admit_pre_stem(
            candidate, key_context=context, token_implications=token_implications
        )
        if not verdict["admitted"]:
            raise ContrastFirstError(
                f"{seed_id} is inadmissible before the stem: {', '.join(verdict['refusals'])}"
            )


# --------------------------------------------------------- contrast matrix


def build_contrast_matrix(contrast_set: dict[str, Any]) -> dict[str, Any]:
    """Project a contrast set into the matrix the blueprint solver reads.

    Nothing is invented here. Every block is a projection of a field the frozen
    seed already carries, so the matrix cannot assert a clinical relationship the
    curated library and its evidence do not already carry.
    """
    key = contrast_set["key"]
    rows: list[dict[str, Any]] = []
    for candidate in sorted(contrast_set["competitors"], key=lambda row: row["seed_id"]):
        conditions = candidate.get("condition_predicates") or []
        anchors = candidate.get("plausibility_anchor_feature_ids") or []
        rows.append({
            "seed_id": candidate["seed_id"],
            "competitor_concept": candidate.get("competitor_concept"),
            "competitor_concept_id": candidate.get("competitor_concept_id"),
            "SHARED_PLAUSIBILITY_FEATURES": {
                "stem_feature_ids": sorted(set(anchors)),
                "shared_with_key": list(candidate.get("shared_features_with_key") or []),
            },
            "SUPPORTING_FEATURES": sorted(set(anchors)),
            "DEFEATING_DISCRIMINATORS": {
                "candidate_visible": list(candidate.get("candidate_visible_discriminators") or []),
                "unsatisfiable_conditions": [
                    condition["stem_feature_id"] for condition in conditions
                ],
            },
            "CORRECTNESS_CONDITIONS": [dict(condition) for condition in conditions],
            "SECOND_KEY_RISK": {
                "total_conditions": len(conditions),
                "conditions_shared_with_key": sorted(
                    {condition["stem_feature_id"] for condition in conditions}
                    & {row["stem_feature_id"] for row in key["correctness_conditions"]}
                ),
            },
            "CATEGORICAL_EXCLUSION_RISK": bool(
                candidate.get("requires_terminal_exclusion_clue")
            ),
            "DECISION_RELEVANCE": {
                "learner_decision_id": contrast_set["learner_decision_id"],
                "decision_granularity": candidate.get("competitor_decision_granularity"),
                "option_set_archetypes": list(candidate.get("option_set_archetypes") or []),
            },
            "EVIDENCE_PROVENANCE": {
                "plausibility": list(candidate.get("evidence_refs_for_plausibility") or []),
                "discrimination": list(candidate.get("evidence_refs_for_discrimination") or []),
            },
            "WHY_A_MINIMALLY_COMPETENT_CANDIDATE_WOULD_CONSIDER_IT": candidate.get(
                "why_a_minimally_competent_candidate_would_consider_it"
            ),
            "DISCOVERY_SOURCES": list(candidate.get("discovery_sources") or []),
            "reviewed_strength": _review(candidate).get("reviewed_strength"),
        })

    matrix = {
        "schema_version": "1.0",
        "scope": "QGEN_CONTRAST_MATRIX",
        "opportunity_label": contrast_set["opportunity_label"],
        "contrast_set_id": contrast_set["contrast_set_id"],
        "difficulty_intent": contrast_set["difficulty_intent"],
        "anchor_study_unit_id": contrast_set["anchor_study_unit_id"],
        "key": {
            "key_concept": key.get("key_concept"),
            "key_concept_id": key.get("key_concept_id"),
            "correctness_conditions": [dict(row) for row in key["correctness_conditions"]],
            "evidence_refs": list(key.get("evidence_refs") or []),
        },
        "rows": rows,
    }
    matrix["contrast_matrix_id"] = artifact_id("CFM", matrix)
    return matrix


def validate_contrast_matrix(matrix: dict[str, Any]) -> None:
    """Every row must answer why the competitor is live and what defeats it."""
    for row in matrix["rows"]:
        seed_id = row["seed_id"]
        shared = row["SHARED_PLAUSIBILITY_FEATURES"]
        if not shared["stem_feature_ids"] and not shared["shared_with_key"]:
            raise ContrastFirstError(
                f"{seed_id}: SHARED_PLAUSIBILITY_FEATURES is empty, so nothing would "
                "give a candidate a reason to consider it"
            )
        defeating = row["DEFEATING_DISCRIMINATORS"]
        if not defeating["candidate_visible"] and not defeating["unsatisfiable_conditions"]:
            raise ContrastFirstError(
                f"{seed_id}: DEFEATING_DISCRIMINATORS is empty, so nothing would "
                "distinguish it from the key"
            )
        if not row["CORRECTNESS_CONDITIONS"]:
            raise ContrastFirstError(
                f"{seed_id}: CORRECTNESS_CONDITIONS is empty, so the second-key "
                "ceiling has nothing to apply to"
            )
        provenance = row["EVIDENCE_PROVENANCE"]
        if not provenance["plausibility"] or not provenance["discrimination"]:
            raise ContrastFirstError(f"{seed_id}: EVIDENCE_PROVENANCE is incomplete")
        reason = row["WHY_A_MINIMALLY_COMPETENT_CANDIDATE_WOULD_CONSIDER_IT"]
        if not isinstance(reason, str) or not reason.strip():
            raise ContrastFirstError(
                f"{seed_id}: FAIL_CLOSED_COMPETITOR_NOT_CONSIDERABLE"
            )


# ------------------------------------------------------- blueprint solving


def _satisfied(conditions: Sequence[dict[str, Any]], assignment: dict[str, str]) -> int:
    return sum(
        1
        for condition in conditions
        if assignment.get(condition["stem_feature_id"]) == condition["required_polarity"]
    )


def _fully_satisfies_any(
    rows: Sequence[dict[str, Any]], assignment: dict[str, str]
) -> str | None:
    for row in rows:
        conditions = row["CORRECTNESS_CONDITIONS"]
        if conditions and _satisfied(conditions, assignment) == len(conditions):
            return row["seed_id"]
    return None


def _anchor_density(
    rows: Sequence[dict[str, Any]], assignment: dict[str, str]
) -> float:
    """Mean anchors PRESENT per competitor under the current assignment."""
    if not rows:
        return 0.0
    return sum(
        sum(1 for feature in row["SUPPORTING_FEATURES"] if assignment.get(feature) == "PRESENT")
        for row in rows
    ) / len(rows)


def solve_stem_blueprint(
    matrix: dict[str, Any],
    *,
    vocabulary: dict[str, dict[str, Any]],
    difficulty_intent: str | None = None,
    contradiction_pairs: Iterable[tuple[str, str]] = (),
    context_features: Sequence[str] = (),
) -> dict[str, Any]:
    """Solve the feature set a stem must realize, before a word of it is written.

    Three constraints hold together or the blueprint fails closed: every key
    correctness condition satisfied, at least one anchor PRESENT for every
    competitor, and at least one correctness condition unsatisfied for every
    competitor. The second and third are the anchor floor and the second-key
    ceiling expressed as constraints rather than as filters -- both are applied
    again afterwards, unchanged, by the production gate.
    """
    intent = difficulty_intent or matrix["difficulty_intent"]
    if intent not in DIFFICULTY_INTENTS:
        raise ContrastFirstError(f"unknown difficulty intent: {intent}")

    rows = sorted(matrix["rows"], key=lambda row: row["seed_id"])
    key_conditions = matrix["key"]["correctness_conditions"]

    named = {condition["stem_feature_id"] for condition in key_conditions} | set(context_features)
    for row in rows:
        named |= set(row["SUPPORTING_FEATURES"])
        named |= {condition["stem_feature_id"] for condition in row["CORRECTNESS_CONDITIONS"]}
    stray = sorted(named - set(vocabulary))
    if stray:
        raise ContrastFirstError(
            "a blueprint may only name features from the frozen study-unit "
            f"vocabulary; these are outside it: {', '.join(stray)}"
        )

    forbidden_pairs = {frozenset(pair) for pair in contradiction_pairs}

    def contradicts(feature: str, assignment: dict[str, str]) -> bool:
        return any(
            pair <= (set(assignment) | {feature}) and feature in pair
            for pair in forbidden_pairs
        )

    assignment: dict[str, str] = {}
    provenance: dict[str, list[str]] = {}
    fail_closed: str | None = None

    for condition in key_conditions:
        feature = condition["stem_feature_id"]
        polarity = condition["required_polarity"]
        if assignment.get(feature, polarity) != polarity:
            return _blueprint(
                matrix, intent, assignment, provenance, rows,
                "FAIL_CLOSED_BLUEPRINT_UNSATISFIABLE",
                note=f"the key requires {feature} in two polarities",
                vocabulary=vocabulary,
            )
        assignment[feature] = polarity
        provenance.setdefault(feature, []).append("KEY_CORRECTNESS_CONDITION")

    # Author-declared contextual features. A stem needs clinical colour the
    # constraint solve does not demand -- the erythematous segment in a mastitis
    # case is not load-bearing but its absence would read as a gap. They enter
    # under the same rules as everything else: inside the frozen vocabulary, no
    # contradiction, and never completing a competitor's correctness signature.
    for feature in sorted(set(context_features)):
        if feature in assignment:
            continue
        trial = dict(assignment)
        trial[feature] = "PRESENT"
        if _fully_satisfies_any(rows, trial) is not None or contradicts(feature, assignment):
            return _blueprint(
                matrix, intent, assignment, provenance, rows,
                "FAIL_CLOSED_BLUEPRINT_UNSATISFIABLE",
                note=f"context feature {feature} would complete a competitor or contradict the stem",
                vocabulary=vocabulary,
            )
        assignment[feature] = "PRESENT"
        provenance.setdefault(feature, []).append("OPTIONAL_CONTEXT")

    # The floor pass. Competitors are visited in seed order and each anchor
    # choice maximises how many still-anchorless competitors it also serves, so
    # the solve is deterministic and adds as few findings as it can.
    def live(row: dict[str, Any]) -> bool:
        return any(assignment.get(feature) == "PRESENT" for feature in row["SUPPORTING_FEATURES"])

    for row in rows:
        if live(row):
            continue
        options: list[tuple[int, str]] = []
        for feature in sorted(row["SUPPORTING_FEATURES"]):
            if assignment.get(feature, "PRESENT") != "PRESENT":
                continue
            if contradicts(feature, assignment):
                continue
            trial = dict(assignment)
            trial[feature] = "PRESENT"
            if _fully_satisfies_any(rows, trial) is not None:
                continue
            coverage = sum(
                1
                for other in rows
                if not live(other) and feature in other["SUPPORTING_FEATURES"]
            )
            options.append((-coverage, feature))
        if not options:
            fail_closed = "FAIL_CLOSED_BLUEPRINT_UNSATISFIABLE"
            break
        _, chosen = sorted(options)[0]
        assignment[chosen] = "PRESENT"
        provenance.setdefault(chosen, []).append("COMPETITOR_ANCHOR")

    # Difficulty targeting. The floor pass adds the minimum that makes every
    # competitor live; a harder contract wants each competitor live on more than
    # one stated finding. That is a density change, not a length change, and it
    # is bounded by the same required-feature cap the coherence gate applies, so
    # difficulty can never be bought with a longer stem.
    if fail_closed is None:
        target = ANCHOR_DENSITY_TARGET[intent]
        cap = REQUIRED_FEATURE_CAP[intent]
        while _anchor_density(rows, assignment) < target and len(assignment) < cap:
            options = []
            for row in rows:
                for feature in sorted(row["SUPPORTING_FEATURES"]):
                    if feature in assignment or contradicts(feature, assignment):
                        continue
                    trial = dict(assignment)
                    trial[feature] = "PRESENT"
                    if _fully_satisfies_any(rows, trial) is not None:
                        continue
                    coverage = sum(
                        1 for other in rows if feature in other["SUPPORTING_FEATURES"]
                    )
                    options.append((-coverage, feature))
            if not options:
                break
            _, chosen = sorted(options)[0]
            assignment[chosen] = "PRESENT"
            provenance.setdefault(chosen, []).append("DIFFICULTY_TARGET_ANCHOR")

    if fail_closed is None:
        second_key = _fully_satisfies_any(rows, assignment)
        if second_key is not None:
            fail_closed = "FAIL_CLOSED_BLUEPRINT_UNSATISFIABLE"

    return _blueprint(
        matrix, intent, assignment, provenance, rows, fail_closed, vocabulary=vocabulary
    )


def _blueprint(
    matrix: dict[str, Any],
    intent: str,
    assignment: dict[str, str],
    provenance: dict[str, list[str]],
    rows: Sequence[dict[str, Any]],
    fail_closed: str | None,
    *,
    note: str | None = None,
    vocabulary: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    key_conditions = matrix["key"]["correctness_conditions"]
    key_supported = all(
        assignment.get(condition["stem_feature_id"]) == condition["required_polarity"]
        for condition in key_conditions
    )

    status: dict[str, Any] = {}
    for row in rows:
        conditions = row["CORRECTNESS_CONDITIONS"]
        satisfied = _satisfied(conditions, assignment)
        anchors_present = [
            feature for feature in sorted(row["SUPPORTING_FEATURES"])
            if assignment.get(feature) == "PRESENT"
        ]
        unsatisfied = [
            condition for condition in conditions
            if assignment.get(condition["stem_feature_id"]) != condition["required_polarity"]
        ]
        # An explicit verbal denial is a stem that *states the absence* of
        # something a competitor needs. A stem that positively asserts the
        # opposite finding is not a denial -- it is the strongest legitimate
        # discriminator there is -- so only PRESENT-required conditions the
        # blueprint assigns ABSENT count here.
        denied = [
            condition for condition in unsatisfied
            if condition["required_polarity"] == "PRESENT"
            and assignment.get(condition["stem_feature_id"]) == "ABSENT"
        ]
        status[row["seed_id"]] = {
            "anchors_present": anchors_present,
            "satisfied_conditions": satisfied,
            "total_conditions": len(conditions),
            "unsatisfied_conditions": [row["stem_feature_id"] for row in unsatisfied],
            "defeated_by_explicit_denial": bool(unsatisfied) and len(denied) == len(unsatisfied),
            "live": bool(anchors_present),
        }

    # Features whose statement would complete a competitor's correctness
    # signature. Handed to the author as a prohibition, not discovered later.
    forbidden: list[dict[str, Any]] = []
    for row in rows:
        entry = status[row["seed_id"]]
        if entry["total_conditions"] and entry["satisfied_conditions"] == entry[
            "total_conditions"
        ] - 1:
            for condition in row["CORRECTNESS_CONDITIONS"]:
                feature = condition["stem_feature_id"]
                if assignment.get(feature) != condition["required_polarity"]:
                    forbidden.append({
                        "stem_feature_id": feature,
                        "polarity": condition["required_polarity"],
                        "reason": f"WOULD_FULLY_SATISFY:{row['seed_id']}",
                    })

    load_bearing = {
        condition["stem_feature_id"] for condition in key_conditions
        if assignment.get(condition["stem_feature_id"]) == condition["required_polarity"]
    }
    for row in rows:
        for condition in row["CORRECTNESS_CONDITIONS"]:
            feature = condition["stem_feature_id"]
            if (
                assignment.get(feature) == "ABSENT"
                and condition["required_polarity"] == "PRESENT"
            ):
                load_bearing.add(feature)

    required = [
        {
            "stem_feature_id": feature,
            "polarity": assignment[feature],
            "roles": sorted(set(provenance.get(feature, ["OPTIONAL_CONTEXT"]))),
            "anchors_for": sorted(
                row["seed_id"] for row in rows if feature in row["SUPPORTING_FEATURES"]
            ),
            "clinical_role": (vocabulary or {}).get(feature, {}).get("clinical_role"),
            "load_bearing": feature in load_bearing,
        }
        for feature in sorted(assignment)
    ]

    blueprint = {
        "schema_version": "1.0",
        "scope": "QGEN_STEM_BLUEPRINT",
        "opportunity_label": matrix["opportunity_label"],
        "contrast_matrix_id": matrix.get("contrast_matrix_id"),
        "anchor_study_unit_id": matrix["anchor_study_unit_id"],
        "difficulty_intent": intent,
        "learner_decision_id": matrix["rows"][0]["DECISION_RELEVANCE"]["learner_decision_id"]
        if matrix["rows"] else None,
        "key_concept": matrix["key"]["key_concept"],
        "required_features": required,
        "forbidden_features": sorted(
            forbidden, key=lambda row: (row["stem_feature_id"], row["reason"])
        ),
        "forbidden_categorical_exclusions": sorted(
            row["seed_id"] for row in rows if row["CATEGORICAL_EXCLUSION_RISK"]
        ),
        "minimum_information_to_solve": sorted(load_bearing),
        "second_key_risk_features": sorted(
            {row["stem_feature_id"] for row in forbidden}
        ),
        "competitor_status": status,
        "key_fully_supported": key_supported,
        "every_competitor_live": all(entry["live"] for entry in status.values()),
        "no_second_key": all(
            entry["satisfied_conditions"] < entry["total_conditions"]
            for entry in status.values() if entry["total_conditions"]
        ),
        "fail_closed_reason": fail_closed,
        "note": note,
    }
    blueprint["stem_blueprint_id"] = artifact_id("CFB", blueprint)
    return blueprint


def attach_vocabulary_roles(
    blueprint: dict[str, Any], vocabulary: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    """Fill each required feature's clinical role from the frozen vocabulary."""
    for row in blueprint["required_features"]:
        row["clinical_role"] = vocabulary.get(row["stem_feature_id"], {}).get("clinical_role")
    return blueprint


# ------------------------------------------------------- coherence contract


def evaluate_clinical_coherence(
    blueprint: dict[str, Any],
    *,
    vocabulary: dict[str, dict[str, Any]],
    availability_reasons: dict[str, str] | None = None,
    contradiction_pairs: Iterable[tuple[str, str]] = (),
) -> dict[str, Any]:
    """CO-1..CO-6. The gate that refuses a stem assembled around its distractors."""
    reasons = availability_reasons or {}
    intent = blueprint["difficulty_intent"]
    violations: list[str] = []
    detail: list[dict[str, Any]] = []

    required = blueprint["required_features"]
    for row in required:
        feature = row["stem_feature_id"]
        role = row.get("clinical_role") or vocabulary.get(feature, {}).get("clinical_role")
        if feature not in vocabulary:
            violations.append("CO-5")
            detail.append({"rule": "CO-5", "stem_feature_id": feature})
            continue
        if role not in ROUTINELY_AVAILABLE_ROLES and not reasons.get(feature):
            violations.append("CO-1")
            detail.append({"rule": "CO-1", "stem_feature_id": feature, "clinical_role": role})

    absent = [row for row in required if row["polarity"] == "ABSENT"]
    if len(absent) > MAXIMUM_ABSENT_REQUIRED_FEATURES[intent]:
        violations.append("CO-2")
        detail.append({
            "rule": "CO-2", "absent_required_features": len(absent),
            "maximum": MAXIMUM_ABSENT_REQUIRED_FEATURES[intent],
        })

    denied = sorted(
        seed_id for seed_id, entry in blueprint["competitor_status"].items()
        if entry.get("defeated_by_explicit_denial")
    )
    if denied:
        violations.append("CO-3")
        detail.append({"rule": "CO-3", "competitors_defeated_only_by_denial": denied})

    if len(required) > REQUIRED_FEATURE_CAP[intent]:
        violations.append("CO-4")
        detail.append({
            "rule": "CO-4", "required_features": len(required),
            "cap": REQUIRED_FEATURE_CAP[intent],
        })

    assigned = {row["stem_feature_id"] for row in required}
    for pair in contradiction_pairs:
        if set(pair) <= assigned:
            violations.append("CO-6")
            detail.append({"rule": "CO-6", "pair": sorted(pair)})

    return {
        "coherent": not violations,
        "violations": sorted(set(violations)),
        "detail": detail,
        "rules_applied": list(COHERENCE_RULES),
    }


# ------------------------------------------------------------- difficulty


def difficulty_evidence_from_blueprint(
    blueprint: dict[str, Any], matrix: dict[str, Any]
) -> dict[str, Any]:
    """Measure the difficulty evidence off the blueprint rather than assert it."""
    status = blueprint["competitor_status"]
    live = [entry for entry in status.values() if entry["live"]]
    anchors = [len(entry["anchors_present"]) for entry in status.values()]
    similarity = [
        entry["satisfied_conditions"] / entry["total_conditions"]
        for entry in status.values() if entry["total_conditions"]
    ]
    load_bearing = [row for row in blueprint["required_features"] if row["load_bearing"]]
    return {
        "key_discriminator_count": len(matrix["key"]["correctness_conditions"]),
        "load_bearing_stem_feature_count": len(load_bearing),
        "live_competitors_after_floor": len(live),
        "competitors_with_at_least_one_anchor_present": len(live),
        "competitors_defeated_by_explicit_verbal_denial": sum(
            1 for entry in status.values() if entry["defeated_by_explicit_denial"]
        ),
        "mean_anchors_present_per_competitor": (
            round(sum(anchors) / len(anchors), 4) if anchors else 0.0
        ),
        "mean_competitor_similarity": (
            round(sum(similarity) / len(similarity), 4) if similarity else 0.0
        ),
        "required_feature_count": len(blueprint["required_features"]),
    }


def structural_difficulty_review(
    evidence: dict[str, Any], *, declared_intent: str
) -> dict[str, Any]:
    """Report which levels the structure actually satisfies, and whether it matches."""
    if declared_intent not in DIFFICULTY_INTENTS:
        raise ContrastFirstError(f"unknown difficulty intent: {declared_intent}")
    satisfied = [
        intent for intent in DIFFICULTY_INTENTS
        if evaluate_difficulty_checks(intent, evidence)["satisfied"]
    ]
    declared = evaluate_difficulty_checks(declared_intent, evidence)
    if declared_intent in satisfied:
        match = "YES"
    elif satisfied:
        match = "NO"
    else:
        match = "UNCERTAIN"
    return {
        "DIFFICULTY_INTENT": declared_intent,
        "STRUCTURAL_DIFFICULTY_REVIEW": satisfied[-1] if satisfied else "UNCERTAIN",
        "MATCH": match,
        "levels_whose_checks_are_satisfied": satisfied,
        "failed_checks": declared["failed_checks"],
        "option_set_was_not_degraded": True,
        "difficulty_is_authored_not_measured": True,
    }


# ------------------------------------------------- post-stem revalidation


def contrast_set_retrieval_index(contrast_set: dict[str, Any]) -> list[dict[str, Any]]:
    """Build the index rows the unchanged production gate reads.

    The gate is not reimplemented and its fields are not renamed. Whatever the
    contrast-first stage decided upstream, what reaches the floor and the ceiling
    is the same row shape arm A saw.
    """
    rows: list[dict[str, Any]] = []
    for candidate in contrast_set["competitors"]:
        rows.append({
            "seed_id": candidate["seed_id"],
            "target_id": contrast_set.get("target_id"),
            "competitor_concept": candidate.get("competitor_concept"),
            "competitor_concept_id": candidate.get("competitor_concept_id"),
            "competitor_study_unit_id": candidate.get("competitor_study_unit_id"),
            "normalized_competitor_text": normalize_option_text(
                candidate.get("competitor_concept", "")
            ),
            "conditions_under_which_competitor_would_be_correct": candidate.get(
                "conditions_under_which_competitor_would_be_correct"
            ),
            "condition_predicates": list(candidate.get("condition_predicates") or []),
            "plausibility_anchor_feature_ids": sorted(
                set(candidate.get("plausibility_anchor_feature_ids") or [])
            ),
            "response_class_tokens": list(candidate.get("response_class_tokens") or []),
            "nominal_axis_values": dict(candidate.get("nominal_axis_values") or {}),
            "applicable_disciplines": list(candidate.get("applicable_disciplines") or []),
            "applicable_item_archetypes": list(
                candidate.get("applicable_item_archetypes") or []
            ),
            "option_set_archetypes": list(candidate.get("option_set_archetypes") or []),
            "decision_granularity": candidate.get("competitor_decision_granularity"),
            "shared_features_with_key": list(candidate.get("shared_features_with_key") or []),
            "reviewed_strength": _review(candidate).get("reviewed_strength"),
            "discovery_sources": list(candidate.get("discovery_sources") or []),
        })
    return sorted(rows, key=lambda row: row["seed_id"])


def revalidate_against_frozen_stem(
    *,
    contrast_set: dict[str, Any],
    stem_feature_map: dict[str, Any],
    ranking_preference: Sequence[str],
    token_implications: dict[str, list[str]] | None = None,
) -> dict[str, Any]:
    """Run the frozen stem through the unchanged production retrieval gate."""
    archetype = contrast_set["option_set_archetype"]
    axis = ARCHETYPE_RESPONSE_AXIS.get(archetype)
    if axis is None:
        raise ContrastFirstError(f"no response-class axis for archetype {archetype}")
    retrieval = retrieve_profile_aware_contrasts(
        index=contrast_set_retrieval_index(contrast_set),
        discipline_profile_id=contrast_set["discipline_profile_id"],
        item_archetype=contrast_set["item_archetype"],
        option_set_archetype=archetype,
        demanded_response_class=contrast_set["demanded_response_class"],
        token_implications=token_implications or {},
        generic_token=RESPONSE_CLASS_AXES[axis]["generic_token"],
        stem_feature_map=stem_feature_map,
        ranking_preference=list(ranking_preference),
    )
    excluded_by = {rule: [] for rule in ("ADM_1", "ADM_3", "SAF_1")}
    for row in retrieval["excluded"]:
        excluded_by.setdefault(row["rule"], []).append(row["seed_id"])
    return {
        "opportunity_label": contrast_set["opportunity_label"],
        "retrieval": retrieval,
        "post_stem_3_viable": retrieval["fail_closed_reason"] is None,
        "excluded_by_rule": {rule: sorted(seeds) for rule, seeds in excluded_by.items()},
        "gate_is_the_production_gate": (
            "profile_contrast_retrieval.retrieve_profile_aware_contrasts"
        ),
    }


# ------------------------------------------------------ option realization


def _token_count(text: str) -> int:
    return len(normalize_option_text(text).split())


def validate_option_realization(
    options: Sequence[dict[str, Any]],
    matrix: dict[str, Any],
    *,
    key_option_text: str,
    stem_text: str | None = None,
) -> dict[str, Any]:
    """The option layer may realize the contrast matrix. It may not extend it."""
    violations: list[str] = []
    detail: list[dict[str, Any]] = []
    traceable = {row["seed_id"] for row in matrix["rows"]} | {"KEY"}

    for option in options:
        source = option.get("source")
        if source not in traceable:
            violations.append("OPTION_NOT_TRACEABLE_TO_THE_CONTRAST_MATRIX")
            detail.append({"option": option.get("label"), "source": source})
        lowered = f" {normalize_option_text(option.get('text', ''))} "
        for qualifier in UNSUPPORTED_QUALIFIERS:
            if f" {qualifier} " in lowered:
                violations.append("UNSUPPORTED_QUALIFIER")
                detail.append({"option": option.get("label"), "qualifier": qualifier})

    keys = [option for option in options if option.get("is_key")]
    if len(keys) != 1:
        violations.append("EXACTLY_ONE_KEY_REQUIRED")
    else:
        lengths = [_token_count(option["text"]) for option in options if not option.get("is_key")]
        key_length = _token_count(key_option_text)
        if lengths and key_length > max(lengths) and key_length > 1.5 * (
            sum(lengths) / len(lengths)
        ):
            violations.append("OPTION_LENGTH_GIVEAWAY")
            detail.append({"key_tokens": key_length, "distractor_tokens": lengths})

    classes = [option.get("response_class") for option in options]
    if any(classes) and len(keys) == 1:
        key_class = keys[0].get("response_class")
        if key_class is not None and sum(1 for value in classes if value == key_class) == 1:
            violations.append("LONE_KEY_CATEGORY")

    lengths = [_token_count(option["text"]) for option in options]
    if lengths and min(lengths) and max(lengths) / min(lengths) > 3.0:
        violations.append("OPTION_SPECIFICITY_MISMATCH")

    if stem_text:
        stem_tokens = normalize_option_text(stem_text).split()
        key_tokens = normalize_option_text(key_option_text).split()
        runs = {
            " ".join(key_tokens[index:index + 4])
            for index in range(max(0, len(key_tokens) - 3))
        }
        stem_runs = {
            " ".join(stem_tokens[index:index + 4])
            for index in range(max(0, len(stem_tokens) - 3))
        }
        if runs & stem_runs:
            violations.append("KEY_COPIES_STEM_LANGUAGE")
            detail.append({"shared_runs": sorted(runs & stem_runs)})

    return {
        "admissible": not violations,
        "violations": sorted(set(violations)),
        "detail": detail,
    }


# --------------------------------------------------- easy and hard safety


def audit_easy_item(evidence: dict[str, Any]) -> dict[str, Any]:
    """EASY must still be a real item. Easy by degradation is rejected."""
    violations: list[str] = []
    if evidence["competitors_with_at_least_one_anchor_present"] < evidence[
        "live_competitors_after_floor"
    ] or evidence["competitors_with_at_least_one_anchor_present"] < CONTRAST_SET_MINIMUM:
        violations.append("COMPETITORS_NOT_LIVE")
    if evidence.get("key_is_the_only_option_in_its_category"):
        violations.append("LONE_KEY_CATEGORY")
    if evidence.get("stem_explicitly_negates_every_competitor"):
        violations.append("STEM_NEGATES_EVERY_COMPETITOR")
    if evidence.get("key_copies_stem_language"):
        violations.append("KEY_COPIES_STEM_LANGUAGE")
    if evidence.get("only_one_option_has_appropriate_specificity"):
        violations.append("ONLY_ONE_OPTION_APPROPRIATELY_SPECIFIC")
    if evidence.get("competitors_defeated_by_explicit_verbal_denial", 0) > 1:
        violations.append("DEFEATED_ONLY_BY_EXPLICIT_DENIAL")
    return {"accepted": not violations, "violations": sorted(set(violations))}


def audit_hard_item(evidence: dict[str, Any]) -> dict[str, Any]:
    """HARD must be hard for a legitimate reason, and only for one."""
    violations: list[str] = []
    for source in evidence.get("difficulty_sources") or []:
        if source in PROHIBITED_HARD_DIFFICULTY_SOURCES:
            violations.append(f"PROHIBITED_DIFFICULTY_SOURCE:{source}")
    if evidence.get("competing_keys_are_ambiguous"):
        violations.append("AMBIGUOUS_COMPETING_KEYS")
    if not evidence.get("information_required_to_decide_is_present", False):
        violations.append("MISSING_INFORMATION")
    if evidence.get("gratuitous_calculation"):
        violations.append("GRATUITOUS_CALCULATION")
    if evidence.get("trick_wording"):
        violations.append("TRICK_WORDING")
    return {"accepted": not violations, "violations": sorted(set(violations))}


# ---------------------------------------------------- frozen-artifact loaders


SEED_PACKS = (
    "research/qgen/generalization/competitive_contrast_seed_pack_r4",
    "research/qgen/generalization/competitive_contrast_seed_pack_g2_targeted",
    "research/qgen/generalization/competitive_contrast_seed_pack_g2_extensions",
)

STEM_FEATURE_VOCABULARY_PATH = "research/qgen/safe_yield/g2_stem_feature_vocabulary.json"

PILOT_OPPORTUNITIES_PATH = "research/qgen/contrast_first_pilot_opportunities.json"


def _read(root, relative: str) -> Any:
    from pathlib import Path

    from .paths import resolve_root_path

    path = resolve_root_path(Path(root).resolve(), relative)
    if not path.is_file():
        raise ContrastFirstError(f"required frozen artifact is missing: {relative}")
    return json.loads(path.read_text())


def load_stem_feature_vocabulary(root) -> dict[str, dict[str, dict[str, Any]]]:
    """Load the frozen per-study-unit stem-feature vocabulary, by unit."""
    document = _read(root, STEM_FEATURE_VOCABULARY_PATH)
    if not document.get("frozen"):
        raise ContrastFirstError("the stem-feature vocabulary must be frozen before use")
    vocabulary: dict[str, dict[str, dict[str, Any]]] = {}
    for anchor in document["anchors"]:
        vocabulary[anchor["anchor_study_unit_id"]] = {
            feature["stem_feature_id"]: {
                "clinical_role": feature["clinical_role"],
                "normalized_feature": feature["normalized_feature"],
            }
            for feature in anchor["features"]
        }
    return vocabulary


def load_curated_candidates(root) -> list[dict[str, Any]]:
    """Project the frozen curated seed packs into contrast-first candidate rows.

    Nothing is authored. Every field is read from a pack, its enrichment or its
    stem-anchor layer, all three of which were frozen before this task.
    """
    candidates: list[dict[str, Any]] = []
    for base in SEED_PACKS:
        pack = _read(root, f"{base}.json")
        enrichment = {
            seed["seed_id"]: seed for seed in _read(root, f"{base}.enrichment.json")["seeds"]
        }
        anchors = {
            seed["seed_id"]: seed for seed in _read(root, f"{base}.stem_anchors.json")["seeds"]
        }
        for target in pack["targets"]:
            for seed in target["seeds"]:
                seed_id = seed["seed_id"]
                tags = enrichment.get(seed_id)
                anchor_row = anchors.get(seed_id)
                if tags is None or anchor_row is None:
                    continue
                review = dict(seed.get("independent_seed_review") or {})
                candidates.append({
                    "seed_id": seed_id,
                    "source_pack": base.rsplit("/", 1)[-1],
                    "curated_for_target_id": target["target_id"],
                    "competitor_concept": seed.get("competitor_concept"),
                    "competitor_concept_id": seed.get("competitor_concept_id"),
                    "competitor_study_unit_id": seed.get("competitor_study_unit_id"),
                    "competitor_decision_granularity": seed.get(
                        "competitor_decision_granularity"
                    ),
                    "conditions_under_which_competitor_would_be_correct": seed.get(
                        "conditions_under_which_competitor_would_be_correct"
                    ),
                    "condition_predicates": list(tags.get("condition_predicates") or []),
                    "plausibility_anchor_feature_ids": sorted({
                        anchor["stem_feature_id"]
                        for anchor in (anchor_row.get("plausibility_anchors") or [])
                    }),
                    "anchor_study_unit_id": anchor_row.get("anchor_study_unit_id"),
                    "response_class_tokens": list(tags.get("response_class_tokens") or []),
                    "nominal_axis_values": dict(tags.get("nominal_axis_values") or {}),
                    "applicable_disciplines": list(tags.get("applicable_disciplines") or []),
                    "applicable_item_archetypes": list(
                        tags.get("applicable_item_archetypes") or []
                    ),
                    "option_set_archetypes": list(tags.get("option_set_archetypes") or []),
                    "shared_features_with_key": list(seed.get("shared_features_with_key") or []),
                    "candidate_visible_discriminators": list(
                        seed.get("candidate_visible_discriminators") or []
                    ),
                    "why_a_minimally_competent_candidate_would_consider_it": seed.get(
                        "why_a_partially_knowledgeable_candidate_might_choose_it"
                    ),
                    "evidence_refs_for_plausibility": list(
                        seed.get("evidence_refs_for_plausibility") or []
                    ),
                    "evidence_refs_for_discrimination": list(
                        seed.get("evidence_refs_for_discrimination") or []
                    ),
                    "independent_seed_review": review,
                    "requires_terminal_exclusion_clue": bool(
                        seed.get("requires_terminal_exclusion_clue")
                    ),
                    "discovery_sources": ["CURATED_LIBRARY"],
                })
    return sorted(candidates, key=lambda row: row["seed_id"])


def graph_contrast_discovery(connection, *, target_ids: Sequence[str]) -> dict[str, Any]:
    """Upstream contrast discovery, seeded at the key decision rather than a stem.

    Arm C of the benchmark seeds traversal at the realized stem's PRESENT
    features, which is unusable here by construction: there is no stem yet. The
    seed is the target node the key answers, so the traversal runs
    ``target <- ANSWERS <- competitor -> CONFUSED_WITH -> further competitor``,
    and ``PLAUSIBILITY_ANCHOR`` then supplies, for each candidate, the stem
    features that would make it live. That last relation is the graph's real
    contribution to this architecture: it is the input the blueprint solver needs
    and the archetype-tagged library index cannot give without a stem.
    """
    if not target_ids:
        return {"concepts": {}, "seeded_at": []}
    marks = ",".join("?" for _ in target_ids)
    reached: dict[str, dict[str, Any]] = {}
    for concept, edge_id, target in connection.execute(
        f"SELECT source_node, edge_id, target_node FROM edges WHERE relation = 'ANSWERS' "
        f"AND target_node IN ({marks}) ORDER BY edge_id",
        tuple(target_ids),
    ):
        reached.setdefault(concept, {
            "depth": 1,
            "paths": [[{"relation": "ANSWERS", "edge_id": edge_id, "from": concept, "to": target}]],
        })
    direct = sorted(reached)
    if direct:
        marks = ",".join("?" for _ in direct)
        for left, edge_id, right in connection.execute(
            f"SELECT source_node, edge_id, target_node FROM edges WHERE relation = "
            f"'CONFUSED_WITH' AND source_node IN ({marks}) ORDER BY edge_id",
            tuple(direct),
        ):
            if right in reached:
                continue
            reached[right] = {
                "depth": 2,
                "paths": [reached[left]["paths"][0] + [{
                    "relation": "CONFUSED_WITH", "edge_id": edge_id,
                    "from": left, "to": right,
                }]],
            }
    for concept, entry in reached.items():
        entry["plausibility_anchor_feature_ids"] = sorted({
            row[0] for row in connection.execute(
                "SELECT target_node FROM edges WHERE relation = 'PLAUSIBILITY_ANCHOR' "
                "AND source_node = ? ORDER BY edge_id",
                (concept,),
            )
        })
    return {"concepts": reached, "seeded_at": sorted(target_ids)}


PROFILE_PATH = "research/qgen/profiles/{profile}.profile.json"


def load_profile_contract(root, *, discipline_profile_id: str, option_set_archetype: str):
    """Return one profile's option-set contract and competitor ranking preference."""
    profile = _read(root, PROFILE_PATH.format(profile=discipline_profile_id))
    contract = next(
        (
            row for row in profile.get("option_set_contracts", [])
            if row.get("option_set_archetype") == option_set_archetype
        ),
        None,
    )
    if contract is None:
        raise ContrastFirstError(
            f"{discipline_profile_id} declares no contract for {option_set_archetype}"
        )
    return {
        "token_implications": dict(contract.get("token_implications") or {}),
        "response_class_axis": contract.get("response_class_axis"),
        "competitor_ranking_preference": list(
            profile.get("competitor_ranking_preference") or []
        ),
    }


# ------------------------------------------------------------ pilot stages


PILOT_AUTHORING_PATH = "research/qgen/contrast_first_pilot_authoring.json"


def build_pilot_contrast_sets(root) -> dict[str, Any]:
    """Stage 1-3: contrast sets, matrices and stem blueprints for the frozen sample.

    Everything up to and including the blueprint happens here, before any stem
    exists. An opportunity that fails at this stage costs one deterministic solve
    rather than an authored stem that a gate then refuses, which is the whole
    point of moving the work upstream.
    """
    frozen = _read(root, PILOT_OPPORTUNITIES_PATH)
    authoring = _read(root, PILOT_AUTHORING_PATH)
    vocabulary = load_stem_feature_vocabulary(root)
    pool = {row["seed_id"]: row for row in load_curated_candidates(root)}

    results: list[dict[str, Any]] = []
    for opportunity in frozen["opportunities"]:
        label = opportunity["opportunity_label"]
        unit = opportunity["anchor_study_unit_id"]
        contract = load_profile_contract(
            root,
            discipline_profile_id=opportunity["discipline_profile_id"],
            option_set_archetype=opportunity["option_set_archetype"],
        )
        context = {
            "discipline_profile_id": opportunity["discipline_profile_id"],
            "item_archetype": opportunity["item_archetype"],
            "option_set_archetype": opportunity["option_set_archetype"],
            "demanded_response_class": opportunity["demanded_response_class"],
            "decision_granularity": opportunity["decision_granularity"],
        }
        admitted = []
        refused = []
        for candidate in sorted(pool.values(), key=lambda row: row["seed_id"]):
            verdict = admit_pre_stem(
                candidate, key_context=context,
                token_implications=contract["token_implications"],
            )
            (admitted if verdict["admitted"] else refused).append(verdict)

        record: dict[str, Any] = {
            "opportunity_label": label,
            "discipline": opportunity["discipline"],
            "difficulty_intent": opportunity["difficulty_intent"],
            "anchor_study_unit_id": unit,
            "admissible_candidate_count": len(admitted),
            "admissible_candidates": [row["seed_id"] for row in admitted],
            "pre_stem_refusal_counts": _refusal_counts(refused),
            "ranking_preference": contract["competitor_ranking_preference"],
            "token_implications": contract["token_implications"],
        }
        spec = (authoring["opportunities"] or {}).get(label)
        if spec is None or len(admitted) < CONTRAST_SET_MINIMUM:
            record.update({
                "stage": "PRE_STEM",
                "terminal_state": "NO_SAFE_ITEM",
                "fail_closed_reason": "FAIL_CLOSED_CONTRAST_SET_SIZE",
                "pre_stem_valid_contrast_set": False,
                "targeted_research_pass": "DECLINED",
            })
            results.append(record)
            continue

        selected = [pool[seed_id] for seed_id in spec["competitors"] if seed_id in pool]
        contrast_set = {
            "contrast_set_id": "",
            "opportunity_label": label,
            "discipline_profile_id": opportunity["discipline_profile_id"],
            "learner_decision_id": opportunity["learner_decision_id"],
            "item_archetype": opportunity["item_archetype"],
            "option_set_archetype": opportunity["option_set_archetype"],
            "demanded_response_class": opportunity["demanded_response_class"],
            "decision_granularity": opportunity["decision_granularity"],
            "difficulty_intent": opportunity["difficulty_intent"],
            "anchor_study_unit_id": unit,
            "priority_class": opportunity["priority_class"],
            "key": {
                "key_concept": spec["key_concept"],
                "key_concept_id": spec["key_concept_id"],
                "correctness_conditions": spec["correctness_conditions"],
                "evidence_refs": spec["key_evidence_refs"],
            },
            "competitors": selected,
            "excluded_candidates": spec.get("excluded", {}),
            "context_features": spec.get("context_features", []),
        }
        contrast_set["contrast_set_id"] = artifact_id("CFS", contrast_set)
        record["contrast_set"] = contrast_set

        try:
            validate_contrast_set(
                contrast_set, token_implications=contract["token_implications"]
            )
            matrix = build_contrast_matrix(contrast_set)
            validate_contrast_matrix(matrix)
        except ContrastFirstError as error:
            record.update({
                "stage": "CONTRAST_SET",
                "terminal_state": "NO_SAFE_ITEM",
                "fail_closed_reason": "FAIL_CLOSED_CONTRAST_SET_SIZE"
                if "FAIL_CLOSED_CONTRAST_SET_SIZE" in str(error)
                else "FAIL_CLOSED_COMPETITOR_NOT_CONSIDERABLE",
                "fail_closed_detail": str(error),
                "pre_stem_valid_contrast_set": False,
                "targeted_research_pass": "DECLINED",
            })
            results.append(record)
            continue

        record["pre_stem_valid_contrast_set"] = True
        record["contrast_matrix"] = matrix
        pairs = [tuple(pair) for pair in (authoring["contradiction_pairs"].get(unit) or [])]
        blueprint = solve_stem_blueprint(
            matrix,
            vocabulary=vocabulary[unit],
            contradiction_pairs=pairs,
            context_features=spec.get("context_features", []),
        )
        record["stem_blueprint"] = blueprint
        if blueprint["fail_closed_reason"]:
            record.update({
                "stage": "BLUEPRINT",
                "terminal_state": "NO_SAFE_ITEM",
                "fail_closed_reason": blueprint["fail_closed_reason"],
            })
            results.append(record)
            continue

        coherence = evaluate_clinical_coherence(
            blueprint, vocabulary=vocabulary[unit],
            availability_reasons=(authoring["opportunities"][label].get(
                "availability_reasons"
            ) or {}),
            contradiction_pairs=pairs,
        )
        record["clinical_coherence"] = coherence
        if not coherence["coherent"]:
            record.update({
                "stage": "COHERENCE",
                "terminal_state": "NO_SAFE_ITEM",
                "fail_closed_reason": "FAIL_CLOSED_CLINICAL_COHERENCE",
            })
            results.append(record)
            continue

        record["difficulty_evidence"] = difficulty_evidence_from_blueprint(blueprint, matrix)
        record["stage"] = "READY_FOR_STEM"
        record["terminal_state"] = None
        record["fail_closed_reason"] = None
        results.append(record)

    return {
        "schema_version": "1.0",
        "scope": "QGEN_CONTRAST_FIRST_PRE_STEM_STAGE",
        "pilot_id": frozen["pilot_id"],
        "opportunities_frozen_sha256": frozen["frozen_sha256"],
        "results": results,
    }


def _refusal_counts(refused: Sequence[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for verdict in refused:
        for code in verdict["refusals"]:
            counts[code] = counts.get(code, 0) + 1
    return dict(sorted(counts.items()))
