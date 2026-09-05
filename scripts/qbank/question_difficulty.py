"""Difficulty intent, its falsifiable checks, and the empirical psychometric schema.

Two separations are the whole point of this module and neither is negotiable.

First, authored difficulty is not measured difficulty. ``DIFFICULTY_INTENT`` is a
design choice available at generation time; ``EMPIRICAL_DIFFICULTY`` is a
measurement that does not exist until learners answer. They live in different
records so that neither can overwrite the other, and so that their eventual
disagreement -- an item authored HARD that everybody gets right -- stays visible,
because that disagreement is the most useful signal the system can produce.

Second, difficulty comes from cognitive demand and never from trickery. The MCC's
own item-writing guidance names the alternative and forbids it: irrelevant
difficulty. A rationale that rests on stem length, option count, rarity or obscure
vocabulary is refused here rather than merely discouraged.

The 20/55/25 library mix is this repository's own learning-design policy. The MCC
publishes no Easy/Medium/Hard bands and no target proportions, and nothing in this
module may be cited as evidence about the real examination.
"""

from __future__ import annotations

import re
from typing import Any

from .errors import QbankError


class DifficultyError(QbankError):
    """A difficulty claim, rationale, or psychometric record is inadmissible."""


DIFFICULTY_INTENTS = ("EASY", "MEDIUM", "HARD")

DIFFICULTY_DIMENSIONS = (
    "discriminator_salience",
    "feature_integration_count",
    "competitor_similarity",
    "sequencing_demand",
    "timing_severity_demand",
    "comorbidity_context",
    "data_interpretation_demand",
)

ITEM_STATUSES = ("DRAFT", "BETA", "ACTIVE", "FLAGGED", "RETIRED")

EMPIRICAL_FIELDS = (
    "empirical_difficulty",
    "percent_correct",
    "item_discrimination",
    "option_endorsement",
    "distractor_function",
    "response_time_summary",
)

LIBRARY_DIFFICULTY_POLICY = {
    "EASY": 20,
    "MEDIUM": 55,
    "HARD": 25,
    "POLICY_STATUS": "INITIAL_LEARNING_DESIGN_POLICY",
    "DERIVED_FROM_MCC_DISTRIBUTION": False,
    "SUPERSEDED_BY": "EMPIRICAL_LEARNER_RESPONSE_DATA",
    "note": (
        "A choice, not a measurement. The MCC publishes no categorical difficulty "
        "bands and no target proportions; its difficulty measure is a continuous "
        "p-value and is not released per item."
    ),
}

DELIVERY_DIFFICULTY_MIXES = {
    "LEARNING": {"EASY": 30, "MEDIUM": 55, "HARD": 15},
    "REVIEW": {"EASY": 15, "MEDIUM": 55, "HARD": 30},
    "EXAM_SIMULATION": {"EASY": 20, "MEDIUM": 55, "HARD": 25},
}

PROHIBITED_DIFFICULTY_SOURCES = (
    "OBSCURE_TRIVIA",
    "TRICK_WORDING",
    "WITHHELD_INFORMATION",
    "SPECIALIST_BOARD_KNOWLEDGE",
    "WEAK_OR_PADDED_DISTRACTORS",
    "ARTIFICIAL_AMBIGUITY",
    "RARITY_WITHOUT_MCC_RELEVANCE",
    "STEM_LENGTH",
    "OPTION_COUNT",
)

# Surface phrases that betray a prohibited difficulty source in a rationale. Kept
# explicit and auditable rather than clever: a classifier that guessed here would
# be the trick it is meant to catch.
_PROHIBITED_PHRASES: dict[str, tuple[str, ...]] = {
    "OBSCURE_TRIVIA": ("obscure", "trivia", "esoteric", "little-known"),
    "TRICK_WORDING": ("trick", "double negative", "except", "misleading wording"),
    "WITHHELD_INFORMATION": ("withheld", "omitted information", "missing information",
                             "not given in the stem"),
    "SPECIALIST_BOARD_KNOWLEDGE": ("board-level", "subspecialist", "specialist-only",
                                   "fellowship-level"),
    "WEAK_OR_PADDED_DISTRACTORS": ("weak distractor", "padded", "implausible option",
                                   "filler option"),
    "ARTIFICIAL_AMBIGUITY": ("ambiguous", "two defensible answers", "deliberately unclear"),
    "RARITY_WITHOUT_MCC_RELEVANCE": ("rare", "rarity", "uncommon presentation only"),
    "STEM_LENGTH": ("long stem", "stem is very long", "length of the stem", "lengthy vignette"),
    "OPTION_COUNT": ("five options", "number of options", "more options", "option count"),
}

# The falsifiable checks. Each is a bound the design states, expressed as a
# comparison over evidence the pipeline already produces.
_CHECKS: dict[str, dict[str, Any]] = {
    "EASY": {
        "key_discriminator_count": (1, 1),
        "load_bearing_stem_feature_count": (1, 2),
        "live_competitors_after_floor": (3, None),
        "competitors_defeated_by_explicit_verbal_denial": (None, 1),
        "mean_anchors_present_per_competitor": (1.0, None),
    },
    "MEDIUM": {
        "key_discriminator_count": (1, 2),
        "load_bearing_stem_feature_count": (2, 3),
        "live_competitors_after_floor": (3, None),
        "competitors_defeated_by_explicit_verbal_denial": (None, 1),
        "mean_anchors_present_per_competitor": (1.0, None),
    },
    "HARD": {
        "key_discriminator_count": (2, None),
        "load_bearing_stem_feature_count": (3, None),
        "live_competitors_after_floor": (3, None),
        "competitors_defeated_by_explicit_verbal_denial": (None, 0),
        "mean_anchors_present_per_competitor": (2.0, None),
    },
}


def _require(evidence: dict[str, Any], field: str) -> Any:
    if field not in evidence:
        raise DifficultyError(f"difficulty evidence is missing {field}")
    return evidence[field]


def evaluate_difficulty_checks(intent: str, evidence: dict[str, Any]) -> dict[str, Any]:
    """Apply the level's falsifiable checks to a structured evidence record."""
    if intent not in DIFFICULTY_INTENTS:
        raise DifficultyError(f"unknown difficulty intent: {intent}")
    failed: list[str] = []
    for field, (minimum, maximum) in _CHECKS[intent].items():
        value = _require(evidence, field)
        if minimum is not None and value < minimum:
            failed.append(field)
        elif maximum is not None and value > maximum:
            failed.append(field)

    # The floor applies identically at every level. A difficulty target may never
    # be reached by admitting a competitor the stem gives no reason to consider.
    anchored = _require(evidence, "competitors_with_at_least_one_anchor_present")
    live = _require(evidence, "live_competitors_after_floor")
    if anchored < live or anchored < 3:
        failed.append("competitors_with_at_least_one_anchor_present")

    return {
        "difficulty_intent": intent,
        "satisfied": not failed,
        "failed_checks": sorted(set(failed)),
        "checks_applied": sorted(_CHECKS[intent]),
    }


def _screen_rationale(rationale: str) -> None:
    lowered = rationale.lower()
    for source, phrases in _PROHIBITED_PHRASES.items():
        # A rationale that names the prohibited source outright is refused too, in
        # either spelling. Screening only for euphemisms would let the blunt case
        # through, which is the wrong way round.
        named = (source.lower(), source.lower().replace("_", " "))
        for phrase in (*named, *phrases):
            if phrase in lowered:
                raise DifficultyError(
                    f"difficulty may not rest on {source}: the rationale says {phrase!r}. "
                    "The MCC item-writing guidance calls this irrelevant difficulty."
                )


def classify_difficulty(
    evidence: dict[str, Any],
    *,
    declared_intent: str | None = None,
    fail_closed: bool = False,
) -> dict[str, Any]:
    """Classify difficulty from structured evidence plus a required rationale.

    Rationale-based by construction. Without a stated reason there is nothing to
    falsify, so a record without one is refused rather than defaulted to MEDIUM.
    """
    rationale = evidence.get("rationale")
    if not isinstance(rationale, str) or not rationale.strip():
        raise DifficultyError("a difficulty classification requires a stated rationale")
    _screen_rationale(rationale)

    dimensions = evidence.get("dimensions") or {}
    missing = sorted(set(DIFFICULTY_DIMENSIONS) - set(dimensions))
    if missing:
        raise DifficultyError(f"difficulty dimensions are incomplete: {', '.join(missing)}")

    if declared_intent is not None:
        verdict = evaluate_difficulty_checks(declared_intent, evidence)
        if not verdict["satisfied"]:
            if fail_closed:
                # A difficulty target that cannot be met from admissible competitors
                # is a coverage finding. It is never a licence to weaken the item.
                return {
                    "verdict": "FAIL_CLOSED_DIFFICULTY_TARGET_NOT_MET",
                    "declared_intent": declared_intent,
                    "failed_checks": verdict["failed_checks"],
                    "option_set_was_not_degraded": True,
                }
            raise DifficultyError(
                f"{declared_intent} checks are not met: {', '.join(verdict['failed_checks'])}"
            )
        satisfied = [declared_intent]
    else:
        satisfied = [
            intent for intent in DIFFICULTY_INTENTS
            if evaluate_difficulty_checks(intent, evidence)["satisfied"]
        ]
        if not satisfied:
            raise DifficultyError("no difficulty level's checks are satisfied")

    intent = declared_intent or satisfied[-1]
    return {
        "verdict": "CLASSIFIED",
        "difficulty_intent": intent,
        "difficulty_rationale": rationale.strip(),
        "difficulty_dimensions": {
            name: dimensions[name] for name in DIFFICULTY_DIMENSIONS
        },
        "checks": evaluate_difficulty_checks(intent, evidence),
        "levels_whose_checks_are_satisfied": satisfied,
        "difficulty_is_authored_not_measured": True,
    }


def validate_difficulty_record(record: dict[str, Any]) -> None:
    """Validate a classified difficulty record, failing closed on a fabricated field."""
    if record.get("difficulty_intent") not in DIFFICULTY_INTENTS:
        raise DifficultyError("difficulty_intent must be EASY, MEDIUM or HARD")
    if not record.get("difficulty_rationale"):
        raise DifficultyError("difficulty_rationale is required")
    missing = sorted(set(DIFFICULTY_DIMENSIONS) - set(record.get("difficulty_dimensions") or {}))
    if missing:
        raise DifficultyError(f"difficulty_dimensions are incomplete: {', '.join(missing)}")
    for field in EMPIRICAL_FIELDS:
        if field in record:
            raise DifficultyError(
                f"{field} is an empirical measurement and does not belong in an "
                "authored difficulty record"
            )


def empty_psychometric_record(
    *, response_count: int = 0, **empirical: Any
) -> dict[str, Any]:
    """The empirical record for a new item: BETA, and every measurement null.

    No minimum sample size is invented. The literature supports no single
    universal N, and asserting one here would be fabrication; the threshold is a
    policy decision to be made from our own data once it exists.
    """
    unknown = sorted(set(empirical) - set(EMPIRICAL_FIELDS))
    if unknown:
        raise DifficultyError(f"unknown empirical field: {', '.join(unknown)}")
    supplied = {name: value for name, value in empirical.items() if value is not None}
    if supplied and response_count <= 0:
        raise DifficultyError(
            f"cannot record {', '.join(sorted(supplied))} with no learner responses; "
            "empirical fields stay null until data exists"
        )
    record: dict[str, Any] = {
        "item_status": "BETA",
        "response_count": response_count,
        "achieved_n_recorded_alongside_every_value": True,
        "minimum_sample_size": None,
        "minimum_sample_size_note": (
            "POLICY_DECISION_ONCE_DATA_EXISTS. No universal N is asserted; report every "
            "statistic with a confidence interval and keep an item in BETA until its "
            "difficulty interval is narrower than a stated width."
        ),
    }
    for field in EMPIRICAL_FIELDS:
        record[field] = empirical.get(field)
    return record
