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
    context_features: Sequence[str | dict[str, str]] = (),
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

    context = [
        {"stem_feature_id": row, "polarity": "PRESENT"} if isinstance(row, str) else dict(row)
        for row in context_features
    ]
    named = {condition["stem_feature_id"] for condition in key_conditions} | {
        row["stem_feature_id"] for row in context
    }
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
    for row in sorted(context, key=lambda entry: entry["stem_feature_id"]):
        feature = row["stem_feature_id"]
        polarity = row.get("polarity", "PRESENT")
        if feature in assignment:
            continue
        trial = dict(assignment)
        trial[feature] = polarity
        if _fully_satisfies_any(rows, trial) is not None or contradicts(feature, assignment):
            return _blueprint(
                matrix, intent, assignment, provenance, rows,
                "FAIL_CLOSED_BLUEPRINT_UNSATISFIABLE",
                note=f"context feature {feature} would complete a competitor or contradict the stem",
                vocabulary=vocabulary,
            )
        assignment[feature] = polarity
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
        if candidate.get("feature_anchor_snapshot_id") is not None:
            rows[-1]["feature_anchor_snapshot_id"] = candidate["feature_anchor_snapshot_id"]
    pinned = {row.get("feature_anchor_snapshot_id") for row in rows}
    if len(pinned) > 1:
        raise ContrastFirstError(
            "this contrast set mixes feature/anchor snapshots "
            f"({sorted(str(entry) for entry in pinned)}); a gate must run against one"
        )
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


def load_curated_candidates(
    root,
    *,
    feature_anchor_snapshot: dict[str, Any] | None = None,
    feature_anchor_scope: str | None = None,
) -> list[dict[str, Any]]:
    """Project the frozen curated seed packs into contrast-first candidate rows.

    Nothing is authored. Every field is read from a pack, its enrichment or its
    stem-anchor layer, all three of which were frozen before this task.

    With ``feature_anchor_snapshot`` pinned, `plausibility_anchor_feature_ids`
    comes from that snapshot instead of the frozen anchor row, and the candidate
    records which snapshot supplied it. Unpinned, this is unchanged, which is
    what every historical replay depends on.
    """
    from .feature_anchor_registry import require_snapshot, resolve_seed_anchors

    snapshot = require_snapshot(feature_anchor_snapshot)
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
                    "plausibility_anchor_feature_ids": (
                        sorted({
                            anchor["stem_feature_id"]
                            for anchor in (anchor_row.get("plausibility_anchors") or [])
                        })
                        if snapshot is None
                        else resolve_seed_anchors(
                            snapshot, seed_id, scope=feature_anchor_scope
                        )
                    ),
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
                    **(
                        {"feature_anchor_snapshot_id": snapshot["snapshot_id"]}
                        if snapshot is not None else {}
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


PILOT_STEMS_PATH = "research/qgen/contrast_first_pilot_stems.json"


def run_post_stem_revalidation(root, pre_stem: dict[str, Any]) -> dict[str, Any]:
    """Stage 11: rerun every competitor against the ACTUAL frozen stem.

    Through ``retrieve_profile_aware_contrasts``, unchanged. Contrast-first buys no
    exemption here; if a competitor the blueprint made live does not clear the
    floor against the realized stem, it is lost and the item fails closed.
    """
    stems = _read(root, PILOT_STEMS_PATH)["stems"]
    rows: list[dict[str, Any]] = []
    for record in pre_stem["results"]:
        label = record["opportunity_label"]
        if record["stage"] != "READY_FOR_STEM":
            continue
        stem = stems[label]
        realized = {
            "features": [
                {
                    "feature_id": feature["feature_id"],
                    "polarity": feature["polarity"],
                    "clinical_role": feature["clinical_role"],
                }
                for feature in stem["stem_feature_map"]
            ]
        }
        result = revalidate_against_frozen_stem(
            contrast_set=record["contrast_set"],
            stem_feature_map=realized,
            ranking_preference=record["ranking_preference"],
            token_implications=record["token_implications"],
        )
        blueprint_features = {
            row["stem_feature_id"]: row["polarity"]
            for row in record["stem_blueprint"]["required_features"]
        }
        realized_features = {
            feature["feature_id"]: feature["polarity"] for feature in stem["stem_feature_map"]
        }
        rows.append({
            **result,
            "difficulty_intent": record["difficulty_intent"],
            "stem_realizes_the_blueprint_exactly": blueprint_features == realized_features,
            "stem_word_count": len(stem["stem"].split()),
            "realized_difficulty_evidence": _realized_difficulty_evidence(
                record, result
            ),
        })
    return {
        "schema_version": "1.0",
        "scope": "QGEN_CONTRAST_FIRST_POST_STEM_REVALIDATION",
        "gate": "profile_contrast_retrieval.retrieve_profile_aware_contrasts",
        "gate_unchanged": True,
        "results": rows,
    }


def _realized_difficulty_evidence(
    record: dict[str, Any], revalidation: dict[str, Any]
) -> dict[str, Any]:
    """Difficulty evidence recomputed from what the production gate actually saw."""
    ranked = revalidation["retrieval"]["ranked_competitors"]
    anchors = [row["anchors_present"] for row in ranked]
    similarity = [
        row["satisfied_conditions"] / row["total_conditions"]
        for row in ranked if row["total_conditions"]
    ]
    design = record["difficulty_evidence"]
    return {
        **design,
        "live_competitors_after_floor": len(ranked),
        "competitors_with_at_least_one_anchor_present": sum(
            1 for value in anchors if value
        ),
        "mean_anchors_present_per_competitor": (
            round(sum(anchors) / len(anchors), 4) if anchors else 0.0
        ),
        "mean_competitor_similarity": (
            round(sum(similarity) / len(similarity), 4) if similarity else 0.0
        ),
        "measured_from": "THE_PRODUCTION_GATE_AGAINST_THE_FROZEN_STEM",
    }


# ------------------------------------------------------------- measurement


PILOT_REVIEWS_PATH = "research/qgen/contrast_first_pilot_reviews.json"
PILOT_BLIND_PATH = "research/qgen/contrast_first_pilot_blind_solver.json"
PILOT_ITEMS_PATH = "research/qgen/contrast_first_pilot_items.json"
BENCHMARK_PATH = "reports/qgen_clinical_retrieval_benchmark.json"
RETEST_PATH = "reports/qgen_g2_stem_anchor_retest_execution.json"
EVIDENCE_PACKETS = (
    "research/qgen/pilot/QGEN-MED-007.acs-chapter-review-pilot-10.evidence.json",
    "research/qgen/generalization/cross_discipline_generalization_15.evidence.json",
    "research/qgen/generalization/cross_discipline_generalization_15_r2.evidence.json",
    "research/qgen/generalization/cross_discipline_generalization_15_r3.evidence.json",
    "research/qgen/generalization/cross_discipline_generalization_15_r4.evidence.json",
)

SAFETY_DIMENSIONS = (
    "FACTUAL_ERRORS", "NUMERIC_ERRORS", "UNSUPPORTED_CLAIMS", "AMBIGUOUS_BEST_ANSWERS",
    "CRITICAL_FACT_SAFETY_FAILURES", "MATERIAL_REDUNDANCY",
    "COMPETITOR_WITHOUT_STEM_ANCHOR", "SECOND_KEY_RISK", "UNNATURAL_STEM_ENGINEERING",
)


def load_evidence_claims(root) -> dict[str, str]:
    """Claim id to statement, over the frozen evidence packets this pilot cites."""
    claims: dict[str, str] = {}
    for relative in EVIDENCE_PACKETS:
        try:
            packet = _read(root, relative)
        except ContrastFirstError:
            continue
        for claim in packet.get("claims", []):
            claims.setdefault(claim["claim_id"], claim["statement"])
    return claims


def measure_context_sizes(root, pre_stem: dict[str, Any]) -> dict[str, Any]:
    """Serialized characters per authoring stage. No token figure is invented."""
    import statistics

    frozen = {
        row["opportunity_label"]: row
        for row in _read(root, PILOT_OPPORTUNITIES_PATH)["opportunities"]
    }
    stems = _read(root, PILOT_STEMS_PATH)["stems"]
    items = _read(root, PILOT_ITEMS_PATH)["items"]
    vocabulary = load_stem_feature_vocabulary(root)
    claims = load_evidence_claims(root)

    rows: list[dict[str, Any]] = []
    for record in pre_stem["results"]:
        if record["stage"] != "READY_FOR_STEM":
            continue
        label = record["opportunity_label"]
        matrix = record["contrast_matrix"]
        blueprint = record["stem_blueprint"]
        unit = record["anchor_study_unit_id"]
        cited = set(matrix["key"]["evidence_refs"])
        for row in matrix["rows"]:
            cited |= set(row["EVIDENCE_PROVENANCE"]["plausibility"])
            cited |= set(row["EVIDENCE_PROVENANCE"]["discrimination"])
        evidence = "\n".join(
            f"{claim}: {claims[claim]}" for claim in sorted(cited) if claim in claims
        )
        # What the stem author actually receives: feature ids, their frozen
        # normalized text, and the prohibitions. No option string.
        generation = "\n".join(
            [frozen[label]["lead_in_from_frozen_baseline"],
             frozen[label]["learner_decision_id"], frozen[label]["difficulty_intent"]]
            + [
                f"{row['stem_feature_id']} {row['polarity']} :: "
                f"{vocabulary[unit][row['stem_feature_id']]['normalized_feature']}"
                for row in blueprint["required_features"]
            ]
            + [
                f"FORBIDDEN {row['stem_feature_id']} {row['polarity']}"
                for row in blueprint["forbidden_features"]
            ]
        )
        item = items[label]
        verification = "\n".join(
            [item["stem"], item["lead_in"]]
            + [f"{o['label']}. {o['text']}\n{o['rationale']}" for o in item["options"]]
            + [evidence]
        )
        rows.append({
            "opportunity_label": label,
            "opportunity_metadata": len(canonical_json(frozen[label])),
            "contrast_matrix": len(canonical_json(matrix)),
            "retrieved_evidence": len(evidence),
            "stem_blueprint": len(canonical_json(blueprint)),
            "generation_context": len(generation),
            "verification_context": len(verification),
        })

    fields = [key for key in rows[0] if key != "opportunity_label"]

    def summarise(values: list[int]) -> dict[str, int]:
        ordered = sorted(values)
        index = min(len(ordered) - 1, int(round(0.95 * (len(ordered) - 1))))
        return {"median": int(statistics.median(ordered)), "p95": ordered[index],
                "min": ordered[0], "max": ordered[-1]}

    summary = {field: summarise([row[field] for row in rows]) for field in fields}
    summary["TOTAL_PER_OPPORTUNITY"] = summarise(
        [sum(row[field] for field in fields) for row in rows]
    )
    return {
        "unit": "CHARACTERS",
        "per_opportunity": rows,
        "summary": summary,
        "tokens_not_reported_because": (
            "No local tokenizer is installed -- tiktoken, transformers, sentencepiece "
            "and tokenizers are all absent -- and characters are not equated with tokens."
        ),
    }


def measure_copyright(root, relatives: Sequence[str], *, seed: int = 12) -> dict[str, Any]:
    """Longest verbatim Toronto Notes run, in words, per artifact.

    Requires the local index, which is gitignored and rebuilt by
    ``qbank build-tn-index``. Fails closed rather than reporting a pass it did
    not measure.
    """
    import re
    import sqlite3
    from pathlib import Path

    index = Path(root) / "derived/tn_index/tn_index.sqlite3"
    if not index.is_file():
        raise ContrastFirstError(
            "the Toronto Notes index is unavailable, so a copyright pass cannot be "
            "claimed; run `qbank build-tn-index` first"
        )
    word = re.compile(r"[a-z0-9]+")
    connection = sqlite3.connect(index)
    corpus: set[str] = set()
    for (text,) in connection.execute("SELECT text FROM chunk_text"):
        tokens = word.findall(text.lower())
        for start in range(len(tokens) - seed + 1):
            corpus.add(" ".join(tokens[start:start + seed]))

    results: list[dict[str, Any]] = []
    worst = 0
    for relative in relatives:
        path = Path(root) / relative
        if not path.is_file():
            continue
        tokens = word.findall(path.read_text().lower())
        longest = 0
        for start in range(len(tokens) - seed + 1):
            if " ".join(tokens[start:start + seed]) in corpus:
                end = start + seed
                while end < len(tokens) and " ".join(
                    tokens[end - seed + 1:end + 1]
                ) in corpus:
                    end += 1
                longest = max(longest, end - start)
        worst = max(worst, longest)
        results.append({"artifact": relative, "longest_verbatim_run_words": longest})
    return {
        "COPYRIGHT_AUDIT": "PASS" if worst == 0 else "REVIEW",
        "longest_verbatim_toronto_notes_run_words": worst,
        "artifacts_scanned": len(results),
        "per_artifact": results,
        "method": (
            f"Every artifact is scanned for the longest run of consecutive tokens also "
            f"occurring in the locally indexed Toronto Notes corpus, seeded on "
            f"{seed}-word matches. The fingerprint set is built in memory and never written."
        ),
    }


TRACKED_PILOT_ARTIFACTS = (
    "docs/superpowers/specs/2026-09-05-contrast-first-difficulty-aware-item-construction-design.md",
    "docs/contrast-first-generation.md",
    "scripts/qbank/contrast_first_pilot.py",
    "tests/test_contrast_first_pilot.py",
    "research/qgen/contrast_first_pilot_opportunities.json",
    "research/qgen/contrast_first_pilot_authoring.json",
    "research/qgen/contrast_first_pilot_stems.json",
    "research/qgen/contrast_first_pilot_blind_solver.json",
    "research/qgen/contrast_first_pilot_items.json",
    "research/qgen/contrast_first_pilot_reviews.json",
)


#: Authored judgements, kept next to the code that measures the numbers they
#: interpret so that neither can drift from the other.
TARGETED_RESEARCH_DECLINED = {
    "G2-MED-02": (
        "No seed of any target carries MEDICINE with INVESTIGATION_SELECTION and "
        "INVESTIGATION_SET together, so the index is empty before any stem exists. "
        "Building three competitors would need new currentness-sensitive authoritative "
        "research, and it would test contrast coverage rather than generation order, "
        "which is what this pilot is for."),
    "G2-PSY-02": (
        "Two competitors secure immediate safety and the rest are refused because they "
        "secure nothing, which is the PSYCHIATRY option-set contract working as written. "
        "A third would have to be an involuntary-admission option whose criteria are "
        "provincial legislation, and no frozen evidence packet carries it."),
}

PILOT_DECISION = {
    "CONTRAST_FIRST_ASSESSMENT": "PROMISING_NEEDS_LARGER_PILOT",
    "basis": (
        "All three limbs of the rule frozen before results hold. Accepted-item safety "
        "is perfect: both accepted items score zero on all nine dimensions. Post-stem "
        "viable survival rose from 7 of 18 to 10 of 18, with anchor-floor refusals "
        "falling from 34 to 0 and second-key refusals from 3 to 0. Safe yield rose from "
        "1 to 2, and G2-PHELO-03 is a CORE decision the archived stem-first arm could "
        "not make safe and this one did."),
    "why_this_is_not_VALIDATED": (
        "Eight of the ten realized items were rejected, an 80 per cent rejection rate, "
        "and the independent reviewers recorded 45 defects across those ten items. "
        "UNNATURAL_STEM_ENGINEERING was found seven times, which is the failure mode "
        "section 16 of the design named as the likeliest way this architecture would "
        "fail. Two accepted items cannot distinguish an architecture that works from "
        "one that happened to work twice."),
    "what_the_architecture_demonstrably_did": (
        "It removed the bottleneck it targeted. Every competitor the blueprint made "
        "live cleared the production anchor floor against the realized stem and none "
        "became a second key, measured through the unchanged production gate."),
    "what_it_demonstrably_did_not_do": (
        "It did not produce safe items at a rate the accepted-item standard can rely "
        "on, and on G2-SURG-02 it produced the assembled-checklist stem the design "
        "warned about, scoring 4 for unnatural engineering and 2 for competitors with "
        "no genuine stem anchor even though the deterministic anchor floor passed them."),
    "the_finding_that_matters_most": (
        "COMPETITOR_WITHOUT_STEM_ANCHOR was 0 by the production gate and 2 by an "
        "independent reviewer on the same item. The frozen anchor layer counts a "
        "generic scenario fact -- imaging is available, suspicion is intermediate -- as "
        "a plausibility anchor. Stem-first rarely exposed this because such anchors were "
        "rarely present by chance. Contrast-first states them deliberately, so a weak "
        "anchor becomes visible stem furniture. The architecture did not create the "
        "defect; it made the anchor layer's quality the binding constraint."),
}

PILOT_NEXT_BOTTLENECK = {
    "NEXT_DOMINANT_BOTTLENECK": "OPTION_REALIZATION",
    "meaning": (
        "The option-and-rationale realization layer. Seven of the ten realized items "
        "carry a rationale defect from one fixed template clause, and all three "
        "reviewers identified it independently: every competitor rationale ends 'That "
        "condition is not met here', which is a false assertion whenever the stem is "
        "merely silent about the condition rather than stating it to be false. "
        "UNSUPPORTED_CLAIMS at 12 is the largest single defect count in the pilot and "
        "is almost entirely this."),
    "runner_up": (
        "Anchor quality in the frozen plausibility layer, per the finding above. Named "
        "here and deliberately not fixed in this task."),
    "not_fixed_here": True,
}


def build_pilot_reports(root) -> dict[str, dict[str, Any]]:
    """Assemble the three canonical pilot reports from committed artifacts only.

    The stem-first arm is read from the archived benchmark and retest. It is never
    regenerated: rerunning a baseline after seeing the new arm's results is the
    clearest way to manufacture a favourable comparison.
    """
    pre_stem = build_pilot_contrast_sets(root)
    post_stem = run_post_stem_revalidation(root, pre_stem)
    frozen = _read(root, PILOT_OPPORTUNITIES_PATH)
    items = _read(root, PILOT_ITEMS_PATH)
    blind = _read(root, PILOT_BLIND_PATH)
    reviews = _read(root, PILOT_REVIEWS_PATH)
    benchmark = _read(root, BENCHMARK_PATH)
    retest = _read(root, RETEST_PATH)["terminal_state_by_opportunity"]

    arm_a = {row["wave_label"]: row for row in benchmark["results_by_arm"]["CURRENT_LIBRARY"]}
    sample = [row["opportunity_label"] for row in frozen["opportunities"]]
    priority = {row["opportunity_label"]: row["priority_class"] for row in frozen["opportunities"]}
    intent = {row["opportunity_label"]: row["difficulty_intent"] for row in frozen["opportunities"]}
    pre = {row["opportunity_label"]: row for row in pre_stem["results"]}
    post = {row["opportunity_label"]: row for row in post_stem["results"]}
    verdicts = items["option_realization_verdicts"]

    outcomes: dict[str, Any] = {}
    for label in sample:
        record = pre[label]
        if record["stage"] != "READY_FOR_STEM":
            outcomes[label] = {"terminal_state": "NO_SAFE_ITEM",
                               "stage_reached": record["stage"],
                               "fail_closed_reason": record["fail_closed_reason"]}
            continue
        review = reviews["reviews"][label]
        accepted = review["VERDICT"] == "ACCEPT"
        outcomes[label] = {
            "terminal_state": "ACCEPTED" if accepted else "REJECTED",
            "stage_reached": "INDEPENDENT_REVIEW",
            "fail_closed_reason": None,
            "reject_reason": None if accepted else review.get("REJECT_REASON"),
            "blind_solver_key_supported": blind["results"][label]["key_supported"],
            "blind_solver_confidence": blind["results"][label]["confidence"],
            "blind_solver_declared_ambiguity": blind["results"][label]["ambiguity_declared"],
            "option_realization_admissible": verdicts[label]["admissible"],
            "option_realization_violations": verdicts[label]["violations"],
            "post_stem_3_viable": post[label]["post_stem_3_viable"],
            "safety_counts": {key: review[key] for key in SAFETY_DIMENSIONS},
            "reviewer_structural_difficulty": review["DIFFICULTY_STRUCTURAL"],
            "deterministic_structural_difficulty": structural_difficulty_review(
                post[label]["realized_difficulty_evidence"], declared_intent=intent[label]
            ),
        }

    accepted_labels = [l for l in sample if outcomes[l]["terminal_state"] == "ACCEPTED"]
    realized = [l for l in sample if l in post]

    contrast_first = {
        "OPPORTUNITIES_ATTEMPTED": len(sample),
        "PRE_STEM_VALID_CONTRAST_SET": sum(
            1 for l in sample if pre[l].get("pre_stem_valid_contrast_set")),
        "POST_STEM_3_VIABLE": sum(1 for l in realized if post[l]["post_stem_3_viable"]),
        "ITEMS_REALIZED": len(realized),
        "ACCEPTED": len(accepted_labels),
        "NO_SAFE_ITEM": sum(1 for l in sample if outcomes[l]["terminal_state"] == "NO_SAFE_ITEM"),
        "REJECTED": sum(1 for l in sample if outcomes[l]["terminal_state"] == "REJECTED"),
        "STEM_ANCHOR_FLOOR_FAILURES": sum(
            1 for l in realized if post[l]["excluded_by_rule"]["SAF_1"]),
        "SECOND_KEY_FAILURES": sum(1 for l in realized if post[l]["excluded_by_rule"]["ADM_3"]),
        "ARCHETYPE_FAILURES": sum(
            1 for l in sample if pre[l]["admissible_candidate_count"] == 0),
        "LEARNER_DECISION_FAILURES": sum(
            1 for l in realized if post[l]["excluded_by_rule"]["ADM_1"]),
        "OPTION_REALIZATION_FAILURES": sum(
            1 for l in realized if not verdicts[l]["admissible"]),
        "EVIDENCE_FAILURES": 0,
    }
    stem_first = {
        "OPPORTUNITIES_ATTEMPTED": len(sample),
        "PRE_STEM_VALID_CONTRAST_SET": None,
        "POST_STEM_3_VIABLE": sum(1 for l in sample if arm_a[l]["reaches_three_viable"]),
        "ITEMS_REALIZED": sum(1 for l in sample if retest[l] in ("ACCEPTED", "REJECTED")),
        "ACCEPTED": sum(1 for l in sample if retest[l] == "ACCEPTED"),
        "NO_SAFE_ITEM": sum(1 for l in sample if retest[l] == "NO_SAFE_ITEM"),
        "REJECTED": sum(1 for l in sample if retest[l] == "REJECTED"),
        "STEM_ANCHOR_FLOOR_FAILURES": sum(
            1 for l in sample if not arm_a[l]["reaches_three_viable"]
            and arm_a[l]["ranked_count"] + arm_a[l]["anchor_floor_refusals"] >= 3),
        "SECOND_KEY_FAILURES": sum(arm_a[l]["SECOND_KEY_REFUSAL"] for l in sample),
        "ARCHETYPE_FAILURES": sum(1 for l in sample if arm_a[l]["indexed_count"] == 0),
        "LEARNER_DECISION_FAILURES": None,
        "OPTION_REALIZATION_FAILURES": None,
        "EVIDENCE_FAILURES": 0,
        "anchor_floor_refusals_total": sum(arm_a[l]["anchor_floor_refusals"] for l in sample),
    }
    full_30 = {
        "OPPORTUNITIES_ATTEMPTED": len(arm_a),
        "POST_STEM_3_VIABLE": sum(1 for l in arm_a if arm_a[l]["reaches_three_viable"]),
        "ACCEPTED": sum(1 for l in arm_a if retest[l] == "ACCEPTED"),
        "REJECTED": sum(1 for l in arm_a if retest[l] == "REJECTED"),
        "NO_SAFE_ITEM": sum(1 for l in arm_a if retest[l] == "NO_SAFE_ITEM"),
        "anchor_floor_refusals_total": sum(arm_a[l]["anchor_floor_refusals"] for l in arm_a),
    }

    safety_totals = {
        key: sum(outcomes[l]["safety_counts"][key] for l in accepted_labels)
        for key in SAFETY_DIMENSIONS
    }
    realized_defects = {
        key: sum(reviews["reviews"][l][key] for l in realized) for key in SAFETY_DIMENSIONS
    }

    difficulty: dict[str, Any] = {}
    for level in DIFFICULTY_INTENTS:
        labels = [l for l in sample if intent[l] == level]
        accepted_at_level = [l for l in labels if outcomes[l]["terminal_state"] == "ACCEPTED"]
        matched = sum(
            1 for l in accepted_at_level
            if outcomes[l]["deterministic_structural_difficulty"]["MATCH"] == "YES"
        )
        difficulty[level] = {
            "attempted": len(labels), "accepted": len(accepted_at_level),
            "intent_match": f"{matched}/{len(accepted_at_level)}",
            "reviewer_structural_difficulty": {
                l: outcomes[l]["reviewer_structural_difficulty"] for l in accepted_at_level
            },
        }

    previously_impossible_core = [
        l for l in accepted_labels if retest[l] == "NO_SAFE_ITEM" and priority[l] == "CORE"
    ]

    context = measure_context_sizes(root, pre_stem)
    copyright_audit = measure_copyright(root, TRACKED_PILOT_ARTIFACTS)

    def delta(key: str) -> dict[str, Any] | None:
        before, after = stem_first.get(key), contrast_first.get(key)
        if before is None or after is None:
            return None
        return {"stem_first": before, "contrast_first": after, "absolute": after - before,
                "relative": None if before == 0 else round((after - before) / before, 4)}

    execution = {
        "schema_version": "1.0", "scope": "QGEN_CONTRAST_FIRST_PILOT_EXECUTION",
        "pilot_id": frozen["pilot_id"],
        "design": ("docs/superpowers/specs/"
                   "2026-09-05-contrast-first-difficulty-aware-item-construction-design.md"),
        "production_generator_changed": False,
        "llm_api_calls": 0,
        "one_attempt_only": True,
        "targeted_research_passes_run": 0,
        "targeted_research_declined_reason": TARGETED_RESEARCH_DECLINED,
        "decision": PILOT_DECISION,
        "next_dominant_bottleneck": PILOT_NEXT_BOTTLENECK,
        "opportunity_outcomes": outcomes,
        "metrics": {"CONTRAST_FIRST": contrast_first,
                    "STEM_FIRST_18_SUBSET_ARCHIVED": stem_first,
                    "STEM_FIRST_FULL_30_ARCHIVED": full_30},
        "difficulty": difficulty,
        "accepted_item_safety": safety_totals,
        "context_characters": context["summary"],
        "context_note": context["tokens_not_reported_because"],
        "copyright": copyright_audit,
    }
    review_report = {
        "schema_version": "1.0", "scope": "QGEN_CONTRAST_FIRST_INDEPENDENT_REVIEW",
        "pilot_id": frozen["pilot_id"],
        "protocol": reviews["protocol"],
        "blind_solver": blind["summary"],
        "reviews": reviews["reviews"],
        "accepted_item_safety_totals": safety_totals,
        "all_accepted_item_safety_counts_are_zero": all(
            value == 0 for value in safety_totals.values()),
        "counter_evidence_not_to_be_read_past": {
            "items_realized": len(realized),
            "items_rejected_by_independent_review": len(realized) - len(accepted_labels),
            "rejection_rate": round((len(realized) - len(accepted_labels)) / len(realized), 4),
            "defect_totals_across_all_realized_items": realized_defects,
            "defects_per_item": {
                l: {"total": sum(reviews["reviews"][l][k] for k in SAFETY_DIMENSIONS),
                    "verdict": reviews["reviews"][l]["VERDICT"]}
                for l in realized
            },
            "note": (
                "The accepted-item safety counts are all zero because both accepted "
                "items are clean, not because the pilot produced few defects. Across "
                f"all ten realized items the reviewers recorded "
                f"{sum(realized_defects.values())} defects. The repository's own "
                "reviewer-calibration rule is to compare defect counts rather than "
                "pass rates, so both are reported."),
        },
        "reviewer_identified_systematic_root_cause":
            reviews["reviewer_identified_systematic_root_cause"],
    }
    comparison = {
        "schema_version": "1.0", "scope": "QGEN_CONTRAST_FIRST_VS_STEM_FIRST",
        "pilot_id": frozen["pilot_id"],
        "population": ("The same 18 frozen opportunities. The stem-first arm is "
                       "archived, not regenerated."),
        "baseline_sources": frozen["frozen_metrics"]["baseline_source"],
        "deltas": {key: delta(key) for key in contrast_first},
        "full_30_context": full_30,
        "previously_impossible_core_decisions_now_safe": previously_impossible_core,
        "promising_rule_limbs": {
            "accepted_item_safety_remains_perfect": all(
                value == 0 for value in safety_totals.values()),
            "post_stem_viable_survival_improves":
                contrast_first["POST_STEM_3_VIABLE"] > stem_first["POST_STEM_3_VIABLE"],
            "safe_yield_improves_or_a_core_decision_becomes_safe": (
                contrast_first["ACCEPTED"] > stem_first["ACCEPTED"]
                or bool(previously_impossible_core)),
        },
        "materiality": {
            "defined_before_results": True,
            "rule": frozen["frozen_metrics"]["comparison_rule"]["promising_requires_all_three"],
        },
    }
    return {"execution": execution, "review": review_report, "comparison": comparison}
