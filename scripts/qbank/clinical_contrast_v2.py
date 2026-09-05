"""The clinical contrast relation model V2.

The contrast-first pilot's option-failure diagnosis refuted the option layer as
the bottleneck and named the real one: the frozen ``plausibility_anchor_feature_ids``
and ``condition_predicates`` over which the contrast matrix, the blueprint solver
and the production anchor floor all reason. Four defects were measured in that
substrate, and this module is exactly those four fixes and nothing else.

1. **Silence was scored as defeat.** A feature the stem never mentions was
   counted as unsatisfied, so a competitor the stem never addressed passed the
   second-key ceiling. Here a feature the state map does not name resolves to
   ``UNKNOWN``, predicates evaluate under Kleene three-valued logic, and a
   competitor resting on ``UNKNOWN`` information is ``AMBIGUOUS`` -- not
   defeated, and not shippable either.

2. **Competitors were never compared with each other.** Every pair is now
   evaluated, competitor against competitor as well as against the key.

3. **Anchors were untyped**, so "a woman of reproductive age" and "imaging is
   available now" satisfied the plausibility floor exactly as an examination
   finding did. Features now carry a semantic contrast role whose discriminative
   class decides what it can do, and the class depends on the decision domain:
   a programme letter is furniture at the bedside and the object of the decision
   in a population item.

4. **Correctness conditions were conjunction-only**, so a disjunctive guideline
   indication was scored unmet while one of its disjuncts held. Correctness is
   now a nested Boolean tree.

Nothing here evaluates a stem, authors clinical content or replaces a production
gate. The production gate remains
``profile_contrast_retrieval.retrieve_profile_aware_contrasts``, and the V2 path
runs it unchanged in addition to this classification, never instead of it.

Design: docs/superpowers/specs/2026-09-05-clinical-contrast-relation-model-v2-design.md
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Iterable, Mapping, Sequence

from .errors import QbankError


class ClinicalContrastV2Error(QbankError):
    """A feature assertion, predicate, relation or contrast set is inadmissible."""


# ------------------------------------------------------------ feature states

PRESENT = "PRESENT"
ABSENT = "ABSENT"
UNKNOWN = "UNKNOWN"
NOT_APPLICABLE = "NOT_APPLICABLE"

FEATURE_STATES = (PRESENT, ABSENT, UNKNOWN, NOT_APPLICABLE)

#: ``IMPLIED`` is treated as ``EXPLICIT`` by the logic and kept separate in the
#: record so a reviewer can see which negations the stem says out loud and which
#: were derived from a declared contradiction.
EXPLICITNESS_LEVELS = ("EXPLICIT", "IMPLIED", "NOT_STATED")

SATISFIED = "SATISFIED"
NOT_SATISFIED = "NOT_SATISFIED"
INDETERMINATE = "INDETERMINATE"

PREDICATE_RESULTS = (SATISFIED, NOT_SATISFIED, INDETERMINATE)


def feature_assertion(
    feature_id: str,
    state: str,
    *,
    explicitness: str | None = None,
    value: Any = None,
    units: str | None = None,
    temporal_context: str | None = None,
    severity_context: str | None = None,
    evidence_refs: Sequence[str] = (),
    source_span: str | None = None,
) -> dict[str, Any]:
    """One typed statement about one feature.

    ``explicitness`` defaults to ``EXPLICIT`` for a stated state and
    ``NOT_STATED`` for ``UNKNOWN``. Declaring an ``UNKNOWN`` explicit is refused:
    the whole point of the state is that nobody said anything.
    """
    if not isinstance(feature_id, str) or not feature_id:
        raise ClinicalContrastV2Error("a feature assertion needs a feature id")
    if state not in FEATURE_STATES:
        raise ClinicalContrastV2Error(f"unknown feature state: {state}")
    if explicitness is None:
        explicitness = "NOT_STATED" if state == UNKNOWN else "EXPLICIT"
    if explicitness not in EXPLICITNESS_LEVELS:
        raise ClinicalContrastV2Error(f"unknown explicitness: {explicitness}")
    if state == UNKNOWN and explicitness != "NOT_STATED":
        raise ClinicalContrastV2Error(
            f"{feature_id}: UNKNOWN means nothing was stated, so it cannot be {explicitness}"
        )
    if state != UNKNOWN and explicitness == "NOT_STATED":
        raise ClinicalContrastV2Error(
            f"{feature_id}: a state of {state} must say where it was stated"
        )
    return {
        "feature_id": feature_id,
        "state": state,
        "explicitness": explicitness,
        "value": value,
        "units": units,
        "temporal_context": temporal_context,
        "severity_context": severity_context,
        "evidence_refs": list(evidence_refs),
        "source_span": source_span,
    }


def build_feature_state_map(
    assertions: Iterable[Mapping[str, Any]],
    *,
    contradiction_pairs: Iterable[Sequence[str]] = (),
    vocabulary: Mapping[str, Any] | None = None,
) -> dict[str, dict[str, Any]]:
    """Assemble a state map and close it under the declared contradictions.

    A contradiction pair is an authored, frozen statement that two features
    cannot both hold. Deriving ``ABSENT`` from a stated ``PRESENT`` on the other
    side of such a pair is an *entailment*, not an inference from silence: it is
    the difference between "the letter states the relative benefit only", which
    says the denominator is not there, and a stem that simply never mentions the
    denominator.
    """
    state_map: dict[str, dict[str, Any]] = {}
    for assertion in assertions:
        feature_id = assertion["feature_id"]
        if feature_id in state_map and state_map[feature_id]["state"] != assertion["state"]:
            raise ClinicalContrastV2Error(
                f"{feature_id} is asserted in two states: "
                f"{state_map[feature_id]['state']} and {assertion['state']}"
            )
        if vocabulary is not None and feature_id not in vocabulary:
            raise ClinicalContrastV2Error(
                f"{feature_id} is outside the frozen study-unit vocabulary"
            )
        state_map[feature_id] = dict(assertion)

    for pair in sorted(tuple(sorted(entry)) for entry in contradiction_pairs):
        left, right = pair
        for stated, derived in ((left, right), (right, left)):
            if state_map.get(stated, {}).get("state") != PRESENT:
                continue
            existing = state_map.get(derived)
            if existing is not None and existing["state"] == PRESENT:
                raise ClinicalContrastV2Error(
                    f"{left} and {right} are declared contradictory and both are PRESENT"
                )
            if existing is not None:
                continue
            implied = feature_assertion(
                derived, ABSENT, explicitness="IMPLIED",
                source_span=f"entailed by {stated} being PRESENT",
            )
            implied["implied_by"] = stated
            state_map[derived] = implied
    return state_map


def resolve_state(state_map: Mapping[str, Any], feature_id: str) -> dict[str, Any]:
    """Return the assertion for *feature_id*, defaulting to ``UNKNOWN``.

    This default is the whole fix for defect 1. Nothing anywhere may substitute
    ``ABSENT`` for a feature the map does not name.
    """
    found = state_map.get(feature_id)
    if found is None:
        return feature_assertion(feature_id, UNKNOWN)
    return dict(found)


# --------------------------------------------------------------- predicates

BRANCH_OPERATORS = ("ALL_OF", "ANY_OF", "NOT", "AT_LEAST_N")
LEAF_OPERATORS = ("COMPARISON", "THRESHOLD")
PREDICATE_OPERATORS = BRANCH_OPERATORS + LEAF_OPERATORS

COMPARISONS = {
    "lt": lambda left, right: left < right,
    "lte": lambda left, right: left <= right,
    "gt": lambda left, right: left > right,
    "gte": lambda left, right: left >= right,
    "eq": lambda left, right: left == right,
    "ne": lambda left, right: left != right,
}


def _is_state_leaf(node: Mapping[str, Any]) -> bool:
    return "required_state" in node and "operator" not in node


def validate_predicate(
    node: Mapping[str, Any], *, vocabulary: Mapping[str, Any] | None = None
) -> None:
    """Structural validation. An empty branch fails closed rather than defaulting."""
    if not isinstance(node, Mapping):
        raise ClinicalContrastV2Error("a predicate node must be an object")
    if _is_state_leaf(node):
        feature_id = node.get("feature_id")
        if not isinstance(feature_id, str) or not feature_id:
            raise ClinicalContrastV2Error("a predicate leaf needs a feature id")
        if node["required_state"] not in (PRESENT, ABSENT, NOT_APPLICABLE):
            raise ClinicalContrastV2Error(
                f"{feature_id}: a leaf may require PRESENT, ABSENT or NOT_APPLICABLE, "
                f"not {node['required_state']}"
            )
        if vocabulary is not None and feature_id not in vocabulary:
            raise ClinicalContrastV2Error(
                f"{feature_id} is outside the frozen study-unit vocabulary"
            )
        return

    operator = node.get("operator")
    if operator not in PREDICATE_OPERATORS:
        raise ClinicalContrastV2Error(f"unknown predicate operator: {operator}")

    if operator in LEAF_OPERATORS:
        feature_id = node.get("feature_id")
        if not isinstance(feature_id, str) or not feature_id:
            raise ClinicalContrastV2Error(f"{operator} needs a feature id")
        if node.get("comparison") not in COMPARISONS:
            raise ClinicalContrastV2Error(
                f"{feature_id}: unknown comparison {node.get('comparison')}"
            )
        if not isinstance(node.get("value"), (int, float)) or isinstance(
            node.get("value"), bool
        ):
            raise ClinicalContrastV2Error(f"{feature_id}: {operator} needs a numeric value")
        if vocabulary is not None and feature_id not in vocabulary:
            raise ClinicalContrastV2Error(
                f"{feature_id} is outside the frozen study-unit vocabulary"
            )
        return

    conditions = node.get("conditions")
    if not isinstance(conditions, list) or not conditions:
        raise ClinicalContrastV2Error(
            f"{operator} with no conditions fails closed; an empty branch has no truth value"
        )
    if operator == "NOT" and len(conditions) != 1:
        raise ClinicalContrastV2Error("NOT takes exactly one condition")
    if operator == "AT_LEAST_N":
        count = node.get("n")
        if not isinstance(count, int) or isinstance(count, bool) or not (
            1 <= count <= len(conditions)
        ):
            raise ClinicalContrastV2Error(
                f"AT_LEAST_N needs an integer n between 1 and {len(conditions)}"
            )
    for child in conditions:
        validate_predicate(child, vocabulary=vocabulary)


def predicate_leaves(node: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Every leaf of the tree, in traversal order."""
    validate_predicate(node)
    if _is_state_leaf(node) or node.get("operator") in LEAF_OPERATORS:
        return [dict(node)]
    leaves: list[dict[str, Any]] = []
    for child in node["conditions"]:
        leaves.extend(predicate_leaves(child))
    return leaves


def predicate_feature_ids(node: Mapping[str, Any]) -> list[str]:
    return sorted({leaf["feature_id"] for leaf in predicate_leaves(node)})


def _evaluate_state_leaf(
    node: Mapping[str, Any], state_map: Mapping[str, Any]
) -> str:
    state = resolve_state(state_map, node["feature_id"])["state"]
    required = node["required_state"]
    if state == UNKNOWN:
        return INDETERMINATE
    if state == NOT_APPLICABLE:
        # A feature that cannot apply is not present, and its absence holds.
        return NOT_SATISFIED if required == PRESENT else SATISFIED
    if required == NOT_APPLICABLE:
        return NOT_SATISFIED
    return SATISFIED if state == required else NOT_SATISFIED


def _evaluate_comparison(node: Mapping[str, Any], state_map: Mapping[str, Any]) -> str:
    assertion = resolve_state(state_map, node["feature_id"])
    if assertion["state"] in (UNKNOWN, NOT_APPLICABLE):
        return INDETERMINATE
    value = assertion.get("value")
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return INDETERMINATE
    units = node.get("units")
    if units is not None and assertion.get("units") not in (None, units):
        raise ClinicalContrastV2Error(
            f"{node['feature_id']}: comparison in {units} against a value in "
            f"{assertion.get('units')}"
        )
    return SATISFIED if COMPARISONS[node["comparison"]](value, node["value"]) else NOT_SATISFIED


def evaluate_predicate(node: Mapping[str, Any], state_map: Mapping[str, Any]) -> str:
    """Evaluate *node* under Kleene three-valued logic.

    Python truthiness is used nowhere. ``INDETERMINATE`` is a first-class result
    and must be handled by every caller.
    """
    validate_predicate(node)
    if _is_state_leaf(node):
        return _evaluate_state_leaf(node, state_map)
    operator = node["operator"]
    if operator in LEAF_OPERATORS:
        return _evaluate_comparison(node, state_map)

    results = [evaluate_predicate(child, state_map) for child in node["conditions"]]
    if operator == "ALL_OF":
        if NOT_SATISFIED in results:
            return NOT_SATISFIED
        return INDETERMINATE if INDETERMINATE in results else SATISFIED
    if operator == "ANY_OF":
        if SATISFIED in results:
            return SATISFIED
        return INDETERMINATE if INDETERMINATE in results else NOT_SATISFIED
    if operator == "NOT":
        only = results[0]
        if only == SATISFIED:
            return NOT_SATISFIED
        return SATISFIED if only == NOT_SATISFIED else INDETERMINATE
    satisfied = results.count(SATISFIED)
    if satisfied >= node["n"]:
        return SATISFIED
    if satisfied + results.count(INDETERMINATE) < node["n"]:
        return NOT_SATISFIED
    return INDETERMINATE


def explain_predicate(
    node: Mapping[str, Any], state_map: Mapping[str, Any]
) -> dict[str, Any]:
    """The evaluation tree, for a rationale that must name the actual relation."""
    result = evaluate_predicate(node, state_map)
    if _is_state_leaf(node) or node.get("operator") in LEAF_OPERATORS:
        assertion = resolve_state(state_map, node["feature_id"])
        return {
            "feature_id": node["feature_id"],
            "required": node.get("required_state") or
            f"{node.get('comparison')} {node.get('value')}",
            "asserted_state": assertion["state"],
            "explicitness": assertion["explicitness"],
            "result": result,
        }
    return {
        "operator": node["operator"],
        "result": result,
        "conditions": [explain_predicate(child, state_map) for child in node["conditions"]],
    }


def unresolved_features(
    node: Mapping[str, Any], state_map: Mapping[str, Any]
) -> list[str]:
    """Leaves that are indeterminate only because the map is silent about them."""
    return sorted({
        leaf["feature_id"]
        for leaf in predicate_leaves(node)
        if resolve_state(state_map, leaf["feature_id"])["state"] == UNKNOWN
    })


def defeating_features(
    node: Mapping[str, Any], state_map: Mapping[str, Any]
) -> list[str]:
    """Leaves the map states to be contrary to what the predicate requires."""
    return sorted({
        leaf["feature_id"]
        for leaf in predicate_leaves(node)
        if evaluate_predicate(leaf, state_map) == NOT_SATISFIED
    })


# -------------------------------------------------------------- role model

#: Semantic roles, and what each one is allowed to do. No invented numeric
#: weights: a role's discriminative class is the whole of its authority.
CONTRAST_ROLES: dict[str, str] = {
    "BACKGROUND_CONTEXT": "NON_DISCRIMINATING",
    "RESOURCE_AVAILABILITY": "NON_DISCRIMINATING",
    "PRIOR_PROBABILITY_FEATURE": "PRIOR_ONLY",
    "SHARED_PRESENTATION_FEATURE": "PRESENTATION",
    "POSITIVE_SUPPORT": "PRESENTATION",
    "TIMING_FEATURE": "PRESENTATION",
    "SEVERITY_FEATURE": "PRESENTATION",
    "INVESTIGATION_FINDING": "PRESENTATION",
    "MANAGEMENT_ELIGIBILITY": "PRESENTATION",
    "NEGATIVE_SUPPORT": "DISCRIMINATING",
    "KEY_DISCRIMINATOR": "DISCRIMINATING",
    "EXCLUSIONARY_FEATURE": "DISCRIMINATING",
    "CONTRAINDICATION": "DISCRIMINATING",
}

DISCRIMINATIVE_CLASSES = ("NON_DISCRIMINATING", "PRIOR_ONLY", "PRESENTATION", "DISCRIMINATING")

#: Classes that can carry a competitor's plausibility on their own. A demographic
#: raises prior probability and a resource clause raises nothing; neither is a
#: reason to consider a diagnosis in *this* patient.
ANCHOR_CLASSES = frozenset({"PRESENTATION", "DISCRIMINATING"})

DECISION_DOMAINS = ("PATIENT_CLINICAL", "POPULATION_PROGRAMME", "EVIDENCE_INTERPRETATION")

_PATIENT_CLINICAL_ROLES = {
    "AGE": "PRIOR_PROBABILITY_FEATURE",
    "DEMOGRAPHIC": "PRIOR_PROBABILITY_FEATURE",
    "SYMPTOM": "SHARED_PRESENTATION_FEATURE",
    "EXAMINATION_FINDING": "POSITIVE_SUPPORT",
    "HISTORY": "POSITIVE_SUPPORT",
    "COLLATERAL_SOURCE": "POSITIVE_SUPPORT",
    "EXPLICIT_RISK_INVENTORY": "POSITIVE_SUPPORT",
    "VITAL_SIGN": "SEVERITY_FEATURE",
    "INVESTIGATION_RESULT": "INVESTIGATION_FINDING",
    "TIME_COURSE": "TIMING_FEATURE",
    "LONGITUDINAL_COURSE": "TIMING_FEATURE",
    "PATIENT_PREFERENCE": "MANAGEMENT_ELIGIBILITY",
    # Meta-assertions about the decider rather than observations of the patient.
    # SF-GS76-INTERMEDIATE-CLINICAL-SUSPICION is the diagnosed example.
    "CLINICAL_JUDGEMENT": "BACKGROUND_CONTEXT",
    "SYSTEM_CONSTRAINT": "RESOURCE_AVAILABILITY",
    "PROGRAMME_CAPACITY": "RESOURCE_AVAILABILITY",
    "PROGRAMME_DOCUMENT": "BACKGROUND_CONTEXT",
    "PROGRAMME_OBJECTIVE": "BACKGROUND_CONTEXT",
    "STUDY_DESIGN": "BACKGROUND_CONTEXT",
    "STUDY_RESULT": "BACKGROUND_CONTEXT",
}

#: In a population or programme decision the programme's own material *is* the
#: case: the letter, the stated objective and the confirmatory capacity are what
#: a candidate reasons over, exactly as an examination finding is at the bedside.
#: A system constraint stays furniture in both domains.
_POPULATION_PROGRAMME_ROLES = {
    **_PATIENT_CLINICAL_ROLES,
    "PROGRAMME_DOCUMENT": "INVESTIGATION_FINDING",
    "PROGRAMME_OBJECTIVE": "MANAGEMENT_ELIGIBILITY",
    "PROGRAMME_CAPACITY": "MANAGEMENT_ELIGIBILITY",
    "STUDY_DESIGN": "INVESTIGATION_FINDING",
    "STUDY_RESULT": "INVESTIGATION_FINDING",
}

_EVIDENCE_INTERPRETATION_ROLES = dict(_POPULATION_PROGRAMME_ROLES)

CLINICAL_ROLE_TO_CONTRAST_ROLE: dict[str, dict[str, str]] = {
    "PATIENT_CLINICAL": _PATIENT_CLINICAL_ROLES,
    "POPULATION_PROGRAMME": _POPULATION_PROGRAMME_ROLES,
    "EVIDENCE_INTERPRETATION": _EVIDENCE_INTERPRETATION_ROLES,
}


def contrast_role_for(
    clinical_role: str, *, decision_domain: str, override: str | None = None
) -> str:
    """Type a frozen vocabulary role for a decision domain.

    An override is admissible where a cited claim makes the default wrong -- a
    severity judgement that is itself the operative guideline criterion, say --
    and is refused if it names a role that does not exist.
    """
    if decision_domain not in DECISION_DOMAINS:
        raise ClinicalContrastV2Error(f"unknown decision domain: {decision_domain}")
    if override is not None:
        if override not in CONTRAST_ROLES:
            raise ClinicalContrastV2Error(f"unknown contrast role: {override}")
        return override
    mapping = CLINICAL_ROLE_TO_CONTRAST_ROLE[decision_domain]
    if clinical_role not in mapping:
        raise ClinicalContrastV2Error(
            f"no contrast role is defined for clinical role {clinical_role} in "
            f"{decision_domain}; typing fails closed rather than defaulting"
        )
    return mapping[clinical_role]


def discriminative_class(contrast_role: str) -> str:
    if contrast_role not in CONTRAST_ROLES:
        raise ClinicalContrastV2Error(f"unknown contrast role: {contrast_role}")
    return CONTRAST_ROLES[contrast_role]


# ------------------------------------------------------------ identity


def canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def content_sha256(payload: Any) -> str:
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def relation_id(payload: Any) -> str:
    return f"CCR2-{content_sha256(payload)[:24]}"


# ----------------------------------------------------------- relation object

NESTING_RELATIONS = (
    "NONE", "A_NESTS_IN_B", "B_NESTS_IN_A", "SAME_CONCEPT", "COMPLICATION_OF",
)
CONFUSABILITY_LEVELS = ("HIGH", "MODERATE", "LOW")
SALIENCE_LEVELS = ("SALIENT", "MODERATE", "SUBTLE")
VERIFICATION_STATUSES = ("EVIDENCE_VERIFIED", "EVIDENCE_PENDING", "UNVERIFIED")
EXCLUSION_BASES = (
    "EXPLICIT_CONTRAINDICATION", "MUTUALLY_EXCLUSIVE_CLINICAL_STATE",
    "EXPLICITLY_ABSENT_MANDATORY_FEATURE", "INCOMPATIBLE_TIMING",
    "OBJECTIVE_TEST_RESULT", "WRONG_STAGE_OF_MANAGEMENT",
)

_RELATION_FIELDS = (
    "learner_decision_id", "response_class", "decision_granularity",
    "concept_a", "concept_b", "shared_features", "a_supporting_features",
    "b_supporting_features", "discriminators", "correctness_conditions_a",
    "correctness_conditions_b", "second_key_conditions",
    "categorical_exclusion_conditions", "nesting_relation", "confusability",
    "mcc_relevance", "evidence_refs", "verification_status",
)


def _typed_features(rows: Sequence[Mapping[str, Any]], label: str) -> list[str]:
    ids: list[str] = []
    for row in rows:
        feature_id = row.get("feature_id")
        role = row.get("contrast_role")
        if not isinstance(feature_id, str) or not feature_id:
            raise ClinicalContrastV2Error(f"{label}: a feature needs an id")
        if role not in CONTRAST_ROLES:
            raise ClinicalContrastV2Error(f"{label}: {feature_id} has no contrast role")
        ids.append(feature_id)
    return ids


def validate_contrast_relation(relation: Mapping[str, Any]) -> None:
    """Validate one evidence-backed relation between two candidate concepts."""
    missing = [field for field in _RELATION_FIELDS if field not in relation]
    if missing:
        raise ClinicalContrastV2Error(f"relation is incomplete: {', '.join(missing)}")
    if relation["nesting_relation"] not in NESTING_RELATIONS:
        raise ClinicalContrastV2Error(
            f"unknown nesting relation: {relation['nesting_relation']}"
        )
    if relation["confusability"] not in CONFUSABILITY_LEVELS:
        raise ClinicalContrastV2Error(f"unknown confusability: {relation['confusability']}")
    if relation["verification_status"] not in VERIFICATION_STATUSES:
        raise ClinicalContrastV2Error(
            f"unknown verification status: {relation['verification_status']}"
        )
    if not (relation.get("evidence_refs") or []):
        raise ClinicalContrastV2Error("a relation needs at least one evidence reference")
    if not str(relation.get("mcc_relevance") or "").strip():
        raise ClinicalContrastV2Error("a relation must say why it is MCC-relevant")

    shared = set(_typed_features(relation["shared_features"], "shared_features"))
    _typed_features(relation["a_supporting_features"], "a_supporting_features")
    _typed_features(relation["b_supporting_features"], "b_supporting_features")

    for side in ("correctness_conditions_a", "correctness_conditions_b"):
        validate_predicate(relation[side])

    for exclusion in relation["categorical_exclusion_conditions"]:
        _validate_exclusion(exclusion)

    seen: set[str] = set()
    for discriminator in relation["discriminators"]:
        feature_id = discriminator.get("feature_id")
        if not isinstance(feature_id, str) or not feature_id:
            raise ClinicalContrastV2Error("a discriminator needs a feature id")
        if discriminator.get("favours") not in ("A", "B"):
            raise ClinicalContrastV2Error(f"{feature_id}: a discriminator must favour A or B")
        if discriminator.get("required_state") not in (PRESENT, ABSENT, NOT_APPLICABLE):
            raise ClinicalContrastV2Error(f"{feature_id}: a discriminator needs a state")
        if discriminator.get("contrast_role") not in CONTRAST_ROLES:
            raise ClinicalContrastV2Error(f"{feature_id}: a discriminator needs a role")
        if discriminator.get("salience") not in SALIENCE_LEVELS:
            raise ClinicalContrastV2Error(f"{feature_id}: a discriminator needs a salience")
        if not (discriminator.get("evidence_refs") or []):
            raise ClinicalContrastV2Error(
                f"{feature_id}: a discriminator without evidence is an opinion, not a relation"
            )
        if feature_id in shared:
            raise ClinicalContrastV2Error(
                f"{feature_id} is declared shared and discriminating in the same relation; "
                "a feature that makes both concepts plausible cannot also decide between them"
            )
        if feature_id in seen:
            raise ClinicalContrastV2Error(f"{feature_id} is declared as a discriminator twice")
        seen.add(feature_id)


def _validate_exclusion(exclusion: Mapping[str, Any]) -> None:
    if not isinstance(exclusion, Mapping) or "predicate" not in exclusion:
        raise ClinicalContrastV2Error("a categorical exclusion needs a predicate")
    validate_predicate(exclusion["predicate"])
    if exclusion.get("basis") not in EXCLUSION_BASES:
        raise ClinicalContrastV2Error(
            f"unknown categorical exclusion basis: {exclusion.get('basis')}"
        )
    if not (exclusion.get("evidence_refs") or []):
        raise ClinicalContrastV2Error(
            "categorical exclusion requires explicit evidence and is never inferred"
        )


def build_contrast_relation(**fields: Any) -> dict[str, Any]:
    """Assemble and content-address one relation."""
    relation = {field: fields[field] for field in _RELATION_FIELDS if field in fields}
    relation.update({
        key: value for key, value in fields.items() if key not in _RELATION_FIELDS
    })
    relation.setdefault("second_key_conditions", [])
    relation.setdefault("categorical_exclusion_conditions", [])
    relation.setdefault("nesting_relation", "NONE")
    validate_contrast_relation(relation)
    relation["contrast_relation_id"] = relation_id(relation)
    return relation


# ------------------------------------------------------- competitor states

LIVE_BUT_INFERIOR = "LIVE_BUT_INFERIOR"
SECOND_KEY = "SECOND_KEY"
CATEGORICALLY_EXCLUDED = "CATEGORICALLY_EXCLUDED"
AMBIGUOUS = "AMBIGUOUS"
INSUFFICIENT_SUPPORT = "INSUFFICIENT_SUPPORT"

COMPETITOR_STATES = (
    LIVE_BUT_INFERIOR, SECOND_KEY, CATEGORICALLY_EXCLUDED, AMBIGUOUS, INSUFFICIENT_SUPPORT,
)

#: Only one of the five may become a distractor.
ADMISSIBLE_COMPETITOR_STATES = frozenset({LIVE_BUT_INFERIOR})


def classify_competitor(
    competitor: Mapping[str, Any],
    state_map: Mapping[str, Any],
    *,
    discriminators: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    """Decide what one competitor is, given what the stem actually states.

    The order matters. Categorical exclusion is checked first because an excluded
    option is not a weak one; plausibility next, because a competitor nobody
    would consider is not made live by its conditions; correctness last.

    An ``INDETERMINATE`` correctness is the case the whole model exists for. It
    becomes ``LIVE_BUT_INFERIOR`` only when an evidence-backed discriminator
    favouring the key is *itself satisfied* by the stem. Otherwise the item is
    ``AMBIGUOUS`` and fails closed. Silence alone never defeats anything.
    """
    conditions = competitor["correctness_conditions"]
    validate_predicate(conditions)

    excluded_by: list[dict[str, Any]] = []
    for exclusion in competitor.get("categorical_exclusion_conditions") or []:
        _validate_exclusion(exclusion)
        if evaluate_predicate(exclusion["predicate"], state_map) == SATISFIED:
            excluded_by.append({
                "basis": exclusion["basis"],
                "evidence_refs": list(exclusion["evidence_refs"]),
                "features": predicate_feature_ids(exclusion["predicate"]),
            })

    anchors_present: list[str] = []
    presentation_anchors: list[str] = []
    for row in competitor.get("supporting_features") or []:
        feature_id = row["feature_id"]
        role = row.get("contrast_role")
        if role not in CONTRAST_ROLES:
            raise ClinicalContrastV2Error(
                f"{feature_id}: a supporting feature needs a contrast role"
            )
        if resolve_state(state_map, feature_id)["state"] != PRESENT:
            continue
        anchors_present.append(feature_id)
        if discriminative_class(role) in ANCHOR_CLASSES:
            presentation_anchors.append(feature_id)

    correctness = evaluate_predicate(conditions, state_map)
    satisfied_key_discriminators = sorted({
        row["feature_id"]
        for row in discriminators
        if row.get("favours") == "A"
        and (row.get("evidence_refs") or [])
        and evaluate_predicate(
            {"feature_id": row["feature_id"], "required_state": row["required_state"]},
            state_map,
        ) == SATISFIED
    })

    if excluded_by:
        state = CATEGORICALLY_EXCLUDED
    elif not presentation_anchors:
        state = INSUFFICIENT_SUPPORT
    elif correctness == SATISFIED:
        state = SECOND_KEY
    elif correctness == NOT_SATISFIED:
        state = LIVE_BUT_INFERIOR
    elif satisfied_key_discriminators:
        state = LIVE_BUT_INFERIOR
    else:
        state = AMBIGUOUS

    return {
        "member_id": competitor.get("member_id"),
        "state": state,
        "correctness": correctness,
        "anchors_present": sorted(anchors_present),
        "presentation_anchors_present": sorted(presentation_anchors),
        "defeated_by": defeating_features(conditions, state_map),
        "unresolved_features": unresolved_features(conditions, state_map),
        "decided_by_discriminators": satisfied_key_discriminators,
        "categorically_excluded_by": excluded_by,
        "explanation": explain_predicate(conditions, state_map),
        "admissible_as_distractor": state in ADMISSIBLE_COMPETITOR_STATES,
    }


# ---------------------------------------------------- contrast-set coherence

COHERENCE_RULES_V2 = (
    "CS2-1", "CS2-2", "CS2-3", "CS2-4", "CS2-5", "CS2-6", "CS2-7", "CS2-8", "CS2-9",
)

COHERENCE_RULE_NAMES = {
    "CS2-1": "NESTED_OR_DUPLICATE_CONCEPT",
    "CS2-2": "MUTUAL_REDUNDANCY",
    "CS2-3": "RESPONSE_CLASS_MISMATCH",
    "CS2-4": "GRANULARITY_MISMATCH",
    "CS2-5": "CATEGORY_IMBALANCE",
    "CS2-6": "ANCHOR_EQUALS_CONDITION",
    "CS2-7": "SET_ANCHOR_DEGENERACY",
    "CS2-8": "SHARED_SOLE_CORRECTNESS_CONDITION",
    "CS2-9": "KEY_CONDITION_NOT_OBSERVABLE",
}

CONTRAST_SET_MINIMUM_COMPETITORS = 3


def _leaf_signature(node: Mapping[str, Any]) -> frozenset[tuple[str, str]]:
    return frozenset(
        (leaf["feature_id"], str(leaf.get("required_state") or leaf.get("comparison")))
        for leaf in predicate_leaves(node)
    )


def _key_implied_state_map(
    key: Mapping[str, Any], contradiction_pairs: Sequence[Sequence[str]]
) -> tuple[dict[str, Any], dict[str, str]]:
    """What the key's own correctness conditions force, and which key feature forced it.

    Provenance matters for `CS2-2`: two competitors killed by "raised jugular
    venous pressure with clear lungs" and by "no pulmonary congestion" are killed
    by the *same* proposition, and the redundancy is invisible unless the derived
    absence is traced back to the key feature that entailed it.
    """
    assertions = []
    provenance: dict[str, str] = {}
    for leaf in predicate_leaves(key["correctness_conditions"]):
        required = leaf.get("required_state")
        if required not in (PRESENT, ABSENT):
            continue
        assertions.append(feature_assertion(leaf["feature_id"], required))
        provenance[leaf["feature_id"]] = leaf["feature_id"]
    implied = build_feature_state_map(assertions, contradiction_pairs=contradiction_pairs)
    for feature_id, assertion in implied.items():
        if feature_id not in provenance:
            provenance[feature_id] = assertion.get("implied_by", feature_id)
    return implied, provenance


def evaluate_contrast_set_coherence(
    contrast_set: Mapping[str, Any],
    state_map: Mapping[str, Any] | None = None,
    *,
    contradiction_pairs: Sequence[Sequence[str]] = (),
) -> dict[str, Any]:
    """CS2-1..CS2-9 over **every** pair, competitor against competitor included.

    Rules CS2-1..CS2-6, CS2-8 and CS2-9 are stem-independent and run at set
    assembly. CS2-7 needs to know which anchors were actually stated, so it runs
    over the available anchors when no state map is supplied and over the realized
    ones when it is.
    """
    members = contrast_set["members"]
    keys = [row for row in members if row["role_in_set"] == "KEY"]
    competitors = [row for row in members if row["role_in_set"] == "COMPETITOR"]
    if len(keys) != 1:
        raise ClinicalContrastV2Error(
            f"a contrast set needs exactly one key, not {len(keys)}"
        )
    if len(competitors) < CONTRAST_SET_MINIMUM_COMPETITORS:
        raise ClinicalContrastV2Error(
            f"FAIL_CLOSED_CONTRAST_SET_SIZE: {len(competitors)} competitors, "
            f"minimum {CONTRAST_SET_MINIMUM_COMPETITORS}"
        )
    key = keys[0]
    feature_roles = dict(contrast_set.get("feature_roles") or {})

    violations: list[str] = []
    detail: list[dict[str, Any]] = []

    def fire(rule: str, **payload: Any) -> None:
        violations.append(rule)
        detail.append({"rule": rule, "name": COHERENCE_RULE_NAMES[rule], **payload})

    # ---- CS2-1, from the declared relations rather than guessed from wording.
    for relation in contrast_set.get("relations") or []:
        nesting = relation.get("nesting_relation", "NONE")
        if nesting != "NONE":
            fire("CS2-1",
                 pair=sorted([relation["concept_a"]["member_id"],
                              relation["concept_b"]["member_id"]]),
                 nesting_relation=nesting,
                 evidence_refs=list(relation.get("evidence_refs") or []))

    # ---- key-relative properties, CS2-3, CS2-4, CS2-9.
    demanded = contrast_set["demanded_response_class"]
    for competitor in competitors:
        tokens = competitor.get("response_class_tokens") or []
        if demanded not in tokens and demanded not in (key.get("response_class_tokens") or []):
            fire("CS2-3", member_id=competitor["member_id"], response_class_tokens=list(tokens))
        elif tokens and demanded not in tokens:
            fire("CS2-3", member_id=competitor["member_id"], response_class_tokens=list(tokens))
        if competitor.get("decision_granularity") != contrast_set["decision_granularity"]:
            fire("CS2-4", member_id=competitor["member_id"],
                 decision_granularity=competitor.get("decision_granularity"),
                 set_granularity=contrast_set["decision_granularity"])

    domain = contrast_set.get("decision_domain", "PATIENT_CLINICAL")

    def role_of(feature_id: str, declared: str | None = None) -> str | None:
        if declared is not None:
            return declared
        return feature_roles.get(feature_id)

    key_condition_classes = []
    for leaf in predicate_leaves(key["correctness_conditions"]):
        role = role_of(leaf["feature_id"])
        if role is None:
            continue
        key_condition_classes.append(discriminative_class(role))
    if key_condition_classes and not (set(key_condition_classes) & ANCHOR_CLASSES):
        fire("CS2-9", key=key["member_id"],
             key_condition_classes=sorted(set(key_condition_classes)),
             note=("every key correctness condition is a meta-assertion or a resource "
                   "clause, so the stem can only declare the answer rather than show it"))

    # ---- CS2-5 category imbalance, including a key alone in its category.
    categories: dict[str, list[str]] = {}
    for row in members:
        categories.setdefault(row.get("concept_category") or "UNDECLARED", []).append(
            row["member_id"]
        )
    key_category = key.get("concept_category") or "UNDECLARED"
    if len(categories.get(key_category, [])) == 1 and len(categories) > 1:
        fire("CS2-5", reason="LONE_KEY_CATEGORY", key_category=key_category,
             categories={name: sorted(rows) for name, rows in sorted(categories.items())})
    for name, rows in sorted(categories.items()):
        if name != key_category and len(rows) >= 3 and len(members) - len(rows) <= 1:
            fire("CS2-5", reason="ONE_BROAD_CATEGORY_BESIDE_NARROW_SUBTYPES",
                 category=name, members=sorted(rows))

    # ---- CS2-6, a competitor that can be live only by being a second key.
    for competitor in competitors:
        condition_features = set(predicate_feature_ids(competitor["correctness_conditions"]))
        anchors = [
            row["feature_id"] for row in competitor.get("supporting_features") or []
            if discriminative_class(
                role_of(row["feature_id"], row.get("contrast_role"))
                or "BACKGROUND_CONTEXT"
            ) in ANCHOR_CLASSES
        ]
        if anchors and set(anchors) <= condition_features:
            fire("CS2-6", member_id=competitor["member_id"],
                 anchors=sorted(set(anchors)),
                 note=("its only usable plausibility anchors are also its own correctness "
                       "conditions, so it is live only when it is a second key"))

    # ---- CS2-2 and CS2-8, competitor against competitor.
    implied, provenance = _key_implied_state_map(key, contradiction_pairs)
    defeated_by_key: dict[str, frozenset[str]] = {}
    signatures: dict[str, frozenset[tuple[str, str]]] = {}
    for competitor in competitors:
        conditions = competitor["correctness_conditions"]
        signatures[competitor["member_id"]] = _leaf_signature(conditions)
        defeated_by_key[competitor["member_id"]] = frozenset(
            provenance.get(feature_id, feature_id)
            for feature_id in defeating_features(conditions, implied)
        )

    ordered = [row["member_id"] for row in competitors]
    for index, left in enumerate(ordered):
        for right in ordered[index + 1:]:
            shared_defeat = defeated_by_key[left]
            if shared_defeat and shared_defeat == defeated_by_key[right] and len(
                shared_defeat
            ) == 1:
                fire("CS2-2", pair=[left, right],
                     defeated_by=sorted(shared_defeat),
                     note=("both die on one and the same proposition, so one option slot "
                           "does no independent work"))
            if signatures[left] and signatures[left] == signatures[right]:
                fire("CS2-8", pair=[left, right],
                     correctness_leaves=sorted(
                         f"{feature}:{state}" for feature, state in signatures[left]
                     ))

    # ---- CS2-7, anchor degeneracy, over realized anchors where they are known.
    per_competitor: dict[str, list[str]] = {}
    for competitor in competitors:
        usable = []
        for row in competitor.get("supporting_features") or []:
            role = role_of(row["feature_id"], row.get("contrast_role"))
            if role is None or discriminative_class(role) not in ANCHOR_CLASSES:
                continue
            if state_map is not None and resolve_state(
                state_map, row["feature_id"]
            )["state"] != PRESENT:
                continue
            usable.append(row["feature_id"])
        per_competitor[competitor["member_id"]] = sorted(set(usable))

    starved = sorted(name for name, rows in per_competitor.items() if not rows)
    if starved:
        fire("CS2-7", reason="NO_USABLE_ANCHOR", members=starved,
             state_map_supplied=state_map is not None)
    else:
        common = set.intersection(*(set(rows) for rows in per_competitor.values()))
        if len(common) == 1 and all(len(rows) == 1 for rows in per_competitor.values()):
            fire("CS2-7", reason="SET_LIVES_ON_ONE_FEATURE", feature=sorted(common)[0])

    pairs = [
        sorted([left["member_id"], right["member_id"]])
        for index, left in enumerate(members) for right in members[index + 1:]
    ]
    return {
        "opportunity_label": contrast_set.get("opportunity_label"),
        "coherent": not violations,
        "violations": sorted(set(violations)),
        "detail": detail,
        "rules_applied": list(COHERENCE_RULES_V2),
        "pairs_evaluated": len(pairs),
        "pairwise": [{"pair": pair} for pair in pairs],
        "state_map_supplied": state_map is not None,
        "decision_domain": domain,
        "usable_anchors_per_competitor": per_competitor,
    }
