"""Independent, role-blind option-set admissibility adjudication.

The R4 retest recorded 250 semantic ``PASS`` verdicts and no other value while an
independent reviewer failed eight of the same fifteen items.  The cause was not a
missing rule: the party that authored the option set also authored the labels the
gate compared and then declared the verdict.  This module removes that
self-certification.

Three separations make the verdict falsifiable:

* the demanded response class is assigned from the realized stem and lead-in and
  never sees the options;
* each option is labelled from its own text and the axis definition alone, with no
  role, no key marker, no sibling option and no item identity available; and
* admissibility is then arithmetic over those labels, with no further judgement.

Every vocabulary below is closed.  A discipline profile may select from it and may
declare implications between its tokens, but may not extend it and may not name a
clinical entity.
"""

from __future__ import annotations

import re
from typing import Any

from .errors import QbankError


class OptionSetAdmissibilityError(QbankError):
    """An option set, a label pool, or a demanded response class is unusable."""


OPTION_SET_ARCHETYPES = {
    "DIAGNOSIS_SET",
    "INVESTIGATION_SET",
    "NEXT_ACTION_SET",
    "MANAGEMENT_STRATEGY_SET",
    "DISPOSITION_SET",
    "STATISTICAL_INTERPRETATION_SET",
    "ETHICAL_ACTION_SET",
    "LEGAL_ACTION_SET",
}

# One response-class axis per archetype.  The generic token is implied by every
# other token on the axis and is what a lead-in demands when it names no narrower
# purpose than the archetype itself.
RESPONSE_CLASS_AXES: dict[str, dict[str, Any]] = {
    "cardinal_syndrome_capability": {
        "archetype": "DIAGNOSIS_SET",
        "generic_token": "PLAUSIBLE_DIAGNOSTIC_ENTITY",
        "tokens": {
            "SYSTEMIC_INFLAMMATORY_ILLNESS",
            "LOCALIZED_INFLAMMATION",
            "ACUTE_RESPIRATORY_DISTRESS",
            "AIRFLOW_OBSTRUCTION",
            "ACUTE_ABDOMINAL_OR_PELVIC_PAIN",
            "PALPABLE_MASS_OR_FLUID_COLLECTION",
            "PERSISTENT_MOOD_DISTURBANCE",
            "EPISODIC_MOOD_ELEVATION",
            "HEMODYNAMIC_INSTABILITY",
            "FOCAL_NEUROLOGIC_DEFICIT",
            "ACUTE_METABOLIC_DERANGEMENT",
            "ABNORMAL_GROWTH_OR_DEVELOPMENT",
            "ABNORMAL_BLEEDING",
        },
    },
    "investigation_purpose": {
        "archetype": "INVESTIGATION_SET",
        "generic_token": "DIAGNOSTIC_ADVANCEMENT",
        "tokens": {
            "STRUCTURAL",
            "FUNCTIONAL",
            "MICROBIOLOGIC",
            "BIOCHEMICAL",
            "MONITORING",
            "STAGING",
            "CLINICAL_OBSERVATION",
        },
    },
    "next_action_class": {
        "archetype": "NEXT_ACTION_SET",
        "generic_token": "NEXT_ACTION_FOR_CURRENT_CARE",
        "tokens": {
            "OBSERVATION",
            "MINIMAL_SUPPORT",
            "LOW_FLOW_SUPPORT",
            "HIGH_FLOW_SUPPORT",
            "ESCALATION_TO_CRITICAL_CARE",
            "DIAGNOSTIC_ORDER",
            "MONITORING_ORDER",
            "PHARMACOLOGIC_ACTION",
            "PROCEDURAL_INTERVENTION",
            "DISPOSITION_ACTION",
            "PATIENT_INSTRUCTION",
            "COMMUNICATION_ACTION",
        },
    },
    "management_capability": {
        "archetype": "MANAGEMENT_STRATEGY_SET",
        "generic_token": "MANAGEMENT_STRATEGY_FOR_PRESENTATION",
        "tokens": {
            "NO_ACTIVE_TREATMENT",
            "PHARMACOLOGIC_ONLY",
            "PERCUTANEOUS_SOURCE_CONTROL",
            "DELAYED_OPERATIVE_SOURCE_CONTROL",
            "IMMEDIATE_OPERATIVE_SOURCE_CONTROL",
            "PROVIDES_SOURCE_CONTROL",
            "PSYCHOLOGICAL_TREATMENT",
            "PHARMACOLOGIC_TREATMENT",
            "COMBINED_TREATMENT",
            "LIFESTYLE_INTERVENTION",
            "PROGRAMME_ACTION",
        },
    },
    "safety_securing_class": {
        "archetype": "DISPOSITION_SET",
        "generic_token": "DISPOSITION_DECISION",
        "tokens": {
            "NONE",
            "ASSESSMENT_ONLY",
            "COMMUNITY_SAFETY_MEASURE",
            "INTENSIVE_COMMUNITY",
            "INVOLUNTARY_OR_INPATIENT",
            "SECURES_IMMEDIATE_SAFETY",
        },
    },
    "explained_phenomenon_class": {
        "archetype": "STATISTICAL_INTERPRETATION_SET",
        "generic_token": "EXPLANATION_OF_OBSERVED_PHENOMENON",
        "tokens": {
            "SCREENING_MEASUREMENT_ARTEFACT",
            "SELECTION_EFFECT",
            "MEASUREMENT_ERROR",
            "CONFOUNDING",
            "CHANCE_VARIATION",
            "TRUE_EFFECT",
        },
    },
    "value_served": {
        "archetype": "ETHICAL_ACTION_SET",
        "generic_token": "ETHICAL_ACTION",
        "tokens": {
            "AUTONOMY",
            "BENEFICENCE",
            "NON_MALEFICENCE",
            "JUSTICE",
            "PROGRAMME_UPTAKE",
            "CONFIDENTIALITY",
        },
    },
    "duty_holder_class": {
        "archetype": "LEGAL_ACTION_SET",
        "generic_token": "LEGAL_DUTY_ACTION",
        "tokens": {
            "TREATING_CLINICIAN_DUTY",
            "INSTITUTIONAL_DUTY",
            "PUBLIC_HEALTH_AUTHORITY_DUTY",
            "REGULATORY_BODY_DUTY",
            "COURT_ORDERED_DUTY",
        },
    },
}

ARCHETYPE_RESPONSE_AXIS = {
    definition["archetype"]: axis for axis, definition in RESPONSE_CLASS_AXES.items()
}

# Closed nominal parity axes.  These never decide admissibility on their own; they
# feed the unchanged parity arithmetic that asks whether the key, or one
# distractor, is a lone holder of a value.
NOMINAL_PARITY_AXES: dict[str, set[str]] = {
    "organ_system": {
        "GASTROINTESTINAL",
        "REPRODUCTIVE",
        "RESPIRATORY",
        "CARDIOVASCULAR",
        "GENITOURINARY",
        "MUSCULOSKELETAL",
        "NEUROLOGIC",
        "ENDOCRINE",
        "INTEGUMENTARY",
        "BREAST",
        "HEMATOLOGIC",
        "MULTISYSTEM",
        "NOT_ORGAN_SPECIFIC",
    },
    "care_setting": {"COMMUNITY", "INTENSIVE_OUTPATIENT", "INPATIENT"},
    "age_appropriateness": {"AGE_APPROPRIATE", "AGE_INAPPROPRIATE"},
    "inflammatory_state": {
        "NON_INFLAMMATORY",
        "LOCALIZED_INFLAMMATORY",
        "SYSTEMIC_INFLAMMATORY",
    },
    "gestational_applicability": {
        "PREGNANCY_APPLICABLE",
        "POSTPARTUM_APPLICABLE",
        "NON_PREGNANCY",
    },
    "drug_class": {
        "ANTIMICROBIAL",
        "ANALGESIC",
        "ANTITHROMBOTIC",
        "CARDIOVASCULAR_AGENT",
        "PSYCHOTROPIC",
        "ENDOCRINE_AGENT",
        "RESPIRATORY_AGENT",
        "NOT_A_DRUG",
    },
    "investigation_purpose": set(RESPONSE_CLASS_AXES["investigation_purpose"]["tokens"]),
    "source_control_class": {
        "NONE",
        "PHARMACOLOGIC_ONLY",
        "PERCUTANEOUS",
        "DELAYED_OPERATIVE",
        "IMMEDIATE_OPERATIVE",
    },
}

ADMISSIBILITY_RULES = ("ADM_1", "ADM_2", "ADM_3", "ADM_4", "ADM_5")

MINIMUM_ADMISSIBLE_COMPETITORS = 3

_STOPWORDS = frozenset({
    "a", "an", "and", "at", "by", "for", "from", "in", "into", "of", "on", "onto",
    "or", "that", "the", "then", "this", "to", "with", "without",
})


def _tokens(value: str) -> list[str]:
    return re.findall(r"[a-z0-9]+(?:-[a-z0-9]+)*", str(value).lower())


def normalize_option_text(text: str) -> str:
    """Return the role-blind normal form a label pool is keyed by."""
    if not isinstance(text, str) or not text.strip():
        raise OptionSetAdmissibilityError("option text must be a non-empty string")
    return " ".join(_tokens(text))


def expand_response_tokens(
    tokens: list[str] | set[str], implications: dict[str, list[str]], generic_token: str
) -> set[str]:
    """Return the transitive closure of declared tokens under profile implications."""
    frontier = {token for token in tokens}
    closure: set[str] = set()
    while frontier:
        token = frontier.pop()
        if token in closure:
            continue
        closure.add(token)
        frontier.update(implications.get(token, []))
    if closure:
        closure.add(generic_token)
    return closure


def _require_labels(labels: Any, label: str) -> dict[str, Any]:
    if not isinstance(labels, dict):
        raise OptionSetAdmissibilityError(f"{label} must be an object")
    return labels


FORBIDDEN_LABEL_FIELDS = (
    "role",
    "key",
    "is_key",
    "correct",
    "correct_answer",
    "item_id",
    "option_letter",
    "position",
)


def validate_role_blind_label_pool(pool: Any) -> dict[str, dict[str, Any]]:
    """Validate a flat, role-blind, item-blind option label pool.

    The pool is keyed by the normalized option text so that the same option text
    carries the same labels wherever it appears.  A pool entry that names a role,
    a key, an item or an option position is refused: such a field would let the
    labelling party see the outcome it is certifying, which is the defect this
    stage exists to remove.
    """
    if not isinstance(pool, dict) or not isinstance(pool.get("labels"), list):
        raise OptionSetAdmissibilityError("label pool must carry a labels array")
    resolved: dict[str, dict[str, Any]] = {}
    for entry in pool["labels"]:
        if not isinstance(entry, dict):
            raise OptionSetAdmissibilityError("label pool entry must be an object")
        for field in FORBIDDEN_LABEL_FIELDS:
            if field in entry:
                raise OptionSetAdmissibilityError(
                    f"role-blind label pool must not carry field: {field}"
                )
        text = entry.get("option_text")
        normalized = normalize_option_text(text)
        if entry.get("normalized_option_text") not in (None, normalized):
            raise OptionSetAdmissibilityError(
                f"label pool normal form disagrees with option text: {text}"
            )
        axis_values = entry.get("response_class_tokens")
        if not isinstance(axis_values, list) or not axis_values or any(
            not isinstance(value, str) or not value for value in axis_values
        ):
            raise OptionSetAdmissibilityError(
                f"label pool entry needs response class tokens: {text}"
            )
        nominal = entry.get("nominal_axis_values", {})
        if not isinstance(nominal, dict) or any(
            axis not in NOMINAL_PARITY_AXES or value not in NOMINAL_PARITY_AXES[axis]
            for axis, value in nominal.items()
        ):
            raise OptionSetAdmissibilityError(
                f"label pool entry carries an unknown nominal axis value: {text}"
            )
        signature = entry.get("action_signature")
        if signature is not None and (
            not isinstance(signature, dict)
            or not isinstance(signature.get("head"), str)
            or not signature["head"]
            or not isinstance(signature.get("objects"), list)
        ):
            raise OptionSetAdmissibilityError(
                f"label pool entry carries an unusable action signature: {text}"
            )
        existing = resolved.get(normalized)
        record = {
            "normalized_option_text": normalized,
            "response_class_tokens": sorted(axis_values),
            "nominal_axis_values": dict(nominal),
            "action_signature": signature,
        }
        if existing is not None and existing != record:
            raise OptionSetAdmissibilityError(
                f"identical option text carries divergent labels: {normalized}"
            )
        resolved[normalized] = record
    if not resolved:
        raise OptionSetAdmissibilityError("label pool is empty")
    return resolved


def _parity_defects(options: list[dict[str, Any]], axes: list[str]) -> list[str]:
    """Run the unchanged lone-value parity arithmetic over declared nominal axes."""
    keys = [row for row in options if row.get("role") == "KEY"]
    distractors = [row for row in options if row.get("role") == "DISTRACTOR"]
    if len(keys) != 1 or len(distractors) < 2:
        return ["INVALID_OPTION_CATEGORY_SET"]
    key = keys[0]
    findings: list[str] = []
    for axis in axes:
        values = [row["nominal_axis_values"].get(axis) for row in options]
        if any(value is None for value in values):
            # An axis that does not apply to every member of the set cannot say
            # anything about parity, and guessing a value would invent a defect.
            continue
        distractor_values = [row["nominal_axis_values"][axis] for row in distractors]
        if key["nominal_axis_values"][axis] not in distractor_values and len(
            set(distractor_values)
        ) == 1:
            findings.append(f"KEY_ONLY_{axis.upper()}")
        for index, row in enumerate(distractors):
            others = [key["nominal_axis_values"][axis]] + [
                other["nominal_axis_values"][axis]
                for position, other in enumerate(distractors)
                if position != index
            ]
            if row["nominal_axis_values"][axis] not in others and len(set(others)) == 1:
                findings.append(f"DISTRACTOR_OUTLIER_{axis.upper()}")
    return sorted(set(findings))


def _condition_defeated_by(
    predicates: list[dict[str, Any]], stem_features: dict[str, dict[str, Any]]
) -> list[str]:
    """Return the stem feature ids that defeat a competitor's correctness condition.

    Each predicate names the stem feature that would have to hold for the
    competitor to be the right answer, and the polarity it would have to hold
    with.  A predicate whose feature is present with the opposite polarity, or
    whose required feature is absent from the stem entirely when the predicate is
    marked required, is defeated by that feature.
    """
    defeating: list[str] = []
    for predicate in predicates:
        feature_id = predicate.get("stem_feature_id")
        required = predicate.get("required_polarity")
        if feature_id is None:
            continue
        feature = stem_features.get(feature_id)
        if feature is None:
            continue
        if feature.get("polarity") != required:
            defeating.append(feature_id)
    return sorted(set(defeating))


def _is_single_function_negation(
    feature_id: str,
    stem_features: dict[str, dict[str, Any]],
    key_grounding_feature_ids: set[str],
    defeat_counts: dict[str, int],
) -> bool:
    """A stem clause that exists only to switch one competitor off.

    The mode this implements is exclusion by *explicit stem negation*, so the
    feature must actually be a negation: an absent finding. It must also ground
    nothing in the key's reasoning, defeat exactly one competitor, and have no
    other stem feature derived from it. A positively decisive finding that
    happens to defeat one competitor is a natural discriminator, not a planted
    clause, and this is where that distinction is drawn.
    """
    feature = stem_features.get(feature_id)
    if feature is None:
        return False
    negation = (
        feature.get("polarity") == "ABSENT"
        or feature.get("inference_type") == "ABSENT_FINDING"
    )
    if not negation:
        return False
    if feature_id in key_grounding_feature_ids:
        return False
    if defeat_counts.get(feature_id, 0) != 1:
        return False
    for other in stem_features.values():
        if feature_id in (other.get("derived_from") or []):
            return False
    return True


def _numerals(text: str) -> int:
    return len(re.findall(r"\d+(?:[.,]\d+)?", text))


def _paired_quantity(text: str) -> bool:
    lowered = text.lower()
    return any(
        marker in lowered
        for marker in (" alongside ", " as well as ", " together with ", " paired with ")
    )


def find_realization_parity_defects(options: list[dict[str, Any]]) -> list[str]:
    """ADM-5: deterministic structural format parity after wording.

    Only structures that a candidate can see without reading medicine are
    considered: how many figures an option carries, and whether exactly one
    option pairs two quantities where the others state one.
    """
    texts = [str(row.get("text", "")) for row in options]
    findings: list[str] = []
    numeral_counts = [_numerals(text) for text in texts]
    bearing = [index for index, count in enumerate(numeral_counts) if count > 0]
    if len(bearing) == 1 and len(texts) > 2:
        findings.append("SOLE_NUMERAL_BEARING_OPTION")
    if len(set(numeral_counts)) > 1 and bearing:
        top = max(numeral_counts)
        if sum(1 for count in numeral_counts if count == top) == 1 and top >= 2:
            findings.append("SOLE_MULTI_FIGURE_OPTION")
    paired = [index for index, text in enumerate(texts) if _paired_quantity(text)]
    if len(paired) == 1 and len(texts) > 2:
        findings.append("SOLE_PAIRED_QUANTITY_OPTION")
    return sorted(set(findings))


def adjudicate_option_set_admissibility(
    *,
    option_set_archetype: str,
    contract: dict[str, Any],
    demanded_response_class: str,
    options: list[dict[str, Any]],
    label_pool: dict[str, dict[str, Any]],
    stem_feature_map: dict[str, Any] | None = None,
    competitor_condition_predicates: dict[str, list[dict[str, Any]]] | None = None,
    key_grounding_feature_ids: list[str] | None = None,
    enacted_action_signatures: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Adjudicate one option set from role-blind labels and arithmetic only.

    ``contract`` is the profile's resolved option-set contract.  ``options`` carry
    a role and a text and nothing else this function trusts; every semantic value
    used comes from ``label_pool``, which cannot see roles.
    """
    if option_set_archetype not in OPTION_SET_ARCHETYPES:
        raise OptionSetAdmissibilityError(
            f"unknown option-set archetype: {option_set_archetype}"
        )
    axis = ARCHETYPE_RESPONSE_AXIS[option_set_archetype]
    if contract.get("response_class_axis") != axis:
        raise OptionSetAdmissibilityError(
            f"contract axis does not match archetype: {option_set_archetype}"
        )
    generic_token = RESPONSE_CLASS_AXES[axis]["generic_token"]
    permitted = set(RESPONSE_CLASS_AXES[axis]["tokens"]) | {generic_token}
    implications = contract.get("token_implications", {})
    if demanded_response_class not in permitted:
        raise OptionSetAdmissibilityError(
            f"demanded response class is not on axis {axis}: {demanded_response_class}"
        )
    if not isinstance(options, list) or len(options) < 3:
        raise OptionSetAdmissibilityError("an option set needs at least three options")

    resolved: list[dict[str, Any]] = []
    for option in options:
        normalized = normalize_option_text(option.get("text"))
        labels = label_pool.get(normalized)
        if labels is None:
            raise OptionSetAdmissibilityError(
                f"no role-blind label exists for option text: {normalized}"
            )
        tokens = set(labels["response_class_tokens"])
        unknown = tokens - permitted
        if unknown:
            raise OptionSetAdmissibilityError(
                f"option label uses tokens outside axis {axis}: {sorted(unknown)}"
            )
        resolved.append({
            "role": option.get("role"),
            "text": option.get("text"),
            "normalized_option_text": normalized,
            "response_class_closure": sorted(
                expand_response_tokens(tokens, implications, generic_token)
            ),
            "nominal_axis_values": labels["nominal_axis_values"],
            "action_signature": labels["action_signature"],
        })

    nominal_axes = list(contract.get("nominal_parity_axes", []))
    overlapping = [value for value in nominal_axes if value == axis]
    if overlapping:
        raise OptionSetAdmissibilityError(
            f"axis {axis} may not be both response-class and nominal parity axis"
        )

    inadmissible: list[dict[str, Any]] = []

    # ADM-1 — membership of the demanded response class.
    for row in resolved:
        if demanded_response_class not in row["response_class_closure"]:
            inadmissible.append({
                "option_text": row["text"],
                "rule": "ADM_1",
                "reason": "RESPONSE_CLASS_NOT_DEMANDED",
                "detail": (
                    f"option response class {row['response_class_closure']} does not "
                    f"contain the demanded class {demanded_response_class}"
                ),
            })

    # ADM-2 — lone-value nominal parity.
    parity_defects = _parity_defects(resolved, nominal_axes)

    # ADM-3 — negation mode over frozen competitor correctness conditions.
    predicates = competitor_condition_predicates or {}
    features = {
        feature["feature_id"]: feature
        for feature in ((stem_feature_map or {}).get("features") or [])
        if isinstance(feature, dict) and isinstance(feature.get("feature_id"), str)
    }
    grounding = set(key_grounding_feature_ids or [])
    defeat_counts: dict[str, int] = {}
    per_competitor_defeats: dict[str, list[str]] = {}
    for row in resolved:
        if row["role"] != "DISTRACTOR":
            continue
        competitor_predicates = predicates.get(row["normalized_option_text"])
        if competitor_predicates is None:
            continue
        defeats = sorted({
            predicate["stem_feature_id"]
            for predicate in competitor_predicates
            if predicate.get("defeated") is True
            and isinstance(predicate.get("stem_feature_id"), str)
        }) or _condition_defeated_by(competitor_predicates, features)
        per_competitor_defeats[row["normalized_option_text"]] = defeats
        for feature_id in defeats:
            defeat_counts[feature_id] = defeat_counts.get(feature_id, 0) + 1
    for normalized, defeats in per_competitor_defeats.items():
        if defeats and all(
            _is_single_function_negation(feature_id, features, grounding, defeat_counts)
            for feature_id in defeats
        ):
            inadmissible.append({
                "option_text": normalized,
                "rule": "ADM_3",
                "reason": "EXCLUSION_BY_EXPLICIT_STEM_NEGATION",
                "detail": (
                    "the only stem features defeating this competitor exist solely to "
                    f"defeat it: {defeats}"
                ),
            })

    # ADM-4 — no option may restate an action the patient already performs.
    enacted = enacted_action_signatures or []
    for row in resolved:
        signature = row["action_signature"]
        if not signature:
            continue
        head = signature["head"]
        objects = set(signature["objects"])
        for record in enacted:
            heads = record.get("heads")
            if heads is None:
                heads = [record.get("head")]
            if head not in heads:
                continue
            if objects and objects.intersection(set(record.get("objects", []))):
                inadmissible.append({
                    "option_text": row["text"],
                    "rule": "ADM_4",
                    "reason": "STEM_ENACTED_ACTION",
                    "detail": (
                        f"the stem records the patient already performing {head} "
                        f"on {sorted(objects.intersection(set(record.get('objects', []))))}"
                    ),
                })
                break

    # ADM-5 — deterministic realization parity.
    realization_defects = find_realization_parity_defects(resolved)

    inadmissible_texts = {row["option_text"] for row in inadmissible}
    surviving_competitors = [
        row
        for row in resolved
        if row["role"] == "DISTRACTOR"
        and row["text"] not in inadmissible_texts
        and row["normalized_option_text"] not in inadmissible_texts
    ]
    key_inadmissible = [
        row
        for row in inadmissible
        if any(
            option["role"] == "KEY"
            and row["option_text"] in (option["text"], option["normalized_option_text"])
            for option in resolved
        )
    ]

    fail_closed_reason = None
    if key_inadmissible:
        fail_closed_reason = "FAIL_CLOSED_INCOHERENT_OPTION_SET_ARCHETYPE"
    elif len(surviving_competitors) < MINIMUM_ADMISSIBLE_COMPETITORS:
        fail_closed_reason = "FAIL_CLOSED_INSUFFICIENT_ADMISSIBLE_COMPETITORS"

    rule_verdicts = {
        "ADM_1": "FAIL" if any(row["rule"] == "ADM_1" for row in inadmissible) else "PASS",
        "ADM_2": "FAIL" if parity_defects else "PASS",
        "ADM_3": "FAIL" if any(row["rule"] == "ADM_3" for row in inadmissible) else "PASS",
        "ADM_4": "FAIL" if any(row["rule"] == "ADM_4" for row in inadmissible) else "PASS",
        "ADM_5": "FAIL" if realization_defects else "PASS",
    }
    verdict = "ADMISSIBLE" if all(
        value == "PASS" for value in rule_verdicts.values()
    ) and fail_closed_reason is None else "INADMISSIBLE"
    return {
        "option_set_archetype": option_set_archetype,
        "response_class_axis": axis,
        "demanded_response_class": demanded_response_class,
        "nominal_parity_axes": nominal_axes,
        "rule_verdicts": rule_verdicts,
        "inadmissible_options": sorted(
            inadmissible, key=lambda row: (row["rule"], row["option_text"])
        ),
        "nominal_parity_defects": parity_defects,
        "realization_parity_defects": realization_defects,
        "admissible_competitor_count": len(surviving_competitors),
        "fail_closed_reason": fail_closed_reason,
        "verdict": verdict,
    }
