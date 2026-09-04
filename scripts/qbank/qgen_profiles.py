"""Discipline profiles as validated data, never as generation logic.

A profile supplies the closed comparison vocabulary an option set must be
compared on, plus the evidence-escalation policy for that discipline.  It is the
externally-authored input that stops option-set adjudication from being
self-certifying.

A profile may not name a diagnosis, a drug, a topic, a threshold value, a stem
template or an option string, and may not relax a common-core gate.  Both
prohibitions are machine-checked: every value must come from a closed
common-core vocabulary, and the free-text justification fields are checked
against the canonical study-unit titles so that a profile cannot smuggle a
clinical entity in as prose.
"""

from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Any

from .errors import QbankError
from .option_set_admissibility import (
    ARCHETYPE_RESPONSE_AXIS,
    NOMINAL_PARITY_AXES,
    OPTION_SET_ARCHETYPES,
    RESPONSE_CLASS_AXES,
)
from .paths import resolve_root_path


class DisciplineProfileError(QbankError):
    """A discipline profile is malformed, over-reaching, or names a clinical entity."""


PROFILE_IDS = (
    "MEDICINE",
    "PEDIATRICS",
    "OBGYN",
    "SURGERY",
    "PSYCHIATRY",
    "PHELO",
)

ITEM_ARCHETYPES = {
    "DIAGNOSIS",
    "INVESTIGATION_SELECTION",
    "PHARMACOTHERAPY",
    "RISK_STRATIFICATION",
    "INTERPRETATION",
    "AGE_BANDED_DIAGNOSIS",
    "RED_FLAG_RECOGNITION",
    "SUPPORTIVE_CARE_CEILING",
    "WEIGHT_BASED_THERAPY",
    "PREGNANCY_DATED_DIAGNOSIS",
    "MATERNAL_FETAL_ACTION",
    "SCREENING_TIMING",
    "POSTPARTUM_LACTATION_MANAGEMENT",
    "RECOGNITION",
    "STABILIZATION",
    "IMAGING_SELECTION",
    "OPERATIVE_VS_NONOPERATIVE",
    "DISPOSITION",
    "SAFETY_ASSESSMENT",
    "LONGITUDINAL_DIFFERENTIAL",
    "COMMUNICATION_AND_CAPACITY",
    "EPIDEMIOLOGY_INTERPRETATION",
    "ETHICAL_ACTION",
    "LEGAL_DUTY",
    "SCREENING_DECISION",
    "PUBLIC_HEALTH_INTERVENTION",
}

SCENARIO_REQUIREMENTS = {
    "SINGLE_ENCOUNTER",
    "AGE",
    "WEIGHT",
    "GROWTH_OR_IMMUNISATION_STATUS",
    "CAREGIVER_CONTEXT",
    "GESTATIONAL_AGE_OR_POSTPARTUM_DAY",
    "PARITY",
    "FETAL_STATUS",
    "TIME_COURSE",
    "VITAL_SIGNS",
    "PHYSIOLOGIC_STABILITY",
    "IMAGING_AVAILABLE",
    "LONGITUDINAL_COURSE",
    "COLLATERAL_SOURCE",
    "EXPLICIT_RISK_INVENTORY",
    "STUDY_DESIGN_OR_PROGRAMME_DESCRIPTION",
    "JURISDICTION",
}

DECISION_GRANULARITY_PATTERNS = {
    "SINGLE_NEXT_ACTION",
    "MANAGEMENT_STRATEGY",
    "DIAGNOSTIC_TEST",
    "DISPOSITION",
    "TREATMENT_BUNDLE",
    "DIAGNOSIS",
    "EPIDEMIOLOGIC_EXPLANATION",
    "ETHICAL_ACTION",
    "LEGAL_DUTY",
    "PROGRAMME_ACTION",
}

SCENARIO_RULES = {
    "PITCHED_AT_DISCRIMINATION_BAND",
}

COMPETITOR_RANKING_SIGNALS = (
    "NEAREST_UNSATISFIED_CORRECTNESS_CONDITION",
    "SHARED_FEATURE_COUNT",
    "REVIEWED_SEED_STRENGTH",
)

EVIDENCE_SOURCE_TIERS = (
    "NATIONAL_SPECIALTY_SOCIETY",
    "NATIONAL_PUBLIC_HEALTH_AGENCY",
    "NATIONAL_EDUCATIONAL_REFERENCE",
    "PROVINCIAL_STATUTE_OR_REGULATION",
    "PEER_REVIEWED_GUIDELINE",
    "TERTIARY_FALLBACK",
)

CURRENTNESS_ESCALATION_TRIGGERS = {
    "THERAPY",
    "THRESHOLD",
    "SCREENING_INTERVAL",
    "IMMUNISATION",
    "PREGNANCY",
    "EMERGENCY_CARE",
    "LEGAL_OR_JURISDICTIONAL",
    "PROGRAMME_POLICY",
}

PROHIBITED_SHORTCUTS = {
    "KEY_ONLY_QUALIFIER",
    "LONE_KEY_DRUG_CLASS",
    "OPTION_SET_MIXES_DIAGNOSIS_AND_TEST",
    "ADULT_THRESHOLDS_IMPORTED",
    "OVER_INVESTIGATION_DISTRACTOR_NOT_TEMPTING",
    "STEM_ENACTED_PRACTICE_AS_DISTRACTOR",
    "NON_INFLAMMATORY_ENTITY_AGAINST_FEBRILE_PRESENTATION",
    "LONE_NON_GYNECOLOGIC_KEY",
    "OPERATIVE_OPTION_WITHOUT_PHYSIOLOGIC_INSTABILITY",
    "RATING_SCALE_AS_DISPOSITION_DETERMINANT",
    "TREATMENT_OFFERED_BEFORE_SAFETY",
    "UPTAKE_LEVER_AGAINST_AUTONOMY_LEAD_IN",
    "STATISTICAL_OPTION_NOT_PARALLEL",
}

R4_STATUSES = {"TESTED_IN_R4", "UNTESTED_IN_R4"}

_FREE_TEXT_FIELDS = ("justification", "notes")

_MINIMUM_SHAPED = re.compile(
    r"(^|_)(minimum|min|target|required_count|remaining|shortfall|deficit|quota|floor)($|_)"
)


def assert_no_quota_shaped_fields(document: Any, *, label: str) -> None:
    """Refuse any field whose name could re-introduce the retired output quota.

    Part II removes a fixed production count.  The cheapest way for it to return
    is a field named like a floor, so the absence of such a field is asserted
    structurally rather than left to reviewer discipline.
    """
    if isinstance(document, dict):
        for name, value in document.items():
            if _MINIMUM_SHAPED.search(str(name).lower()):
                raise DisciplineProfileError(
                    f"{label} defines a quota-shaped field: {name}"
                )
            assert_no_quota_shaped_fields(value, label=label)
    elif isinstance(document, list):
        for value in document:
            assert_no_quota_shaped_fields(value, label=label)


def _clinical_entity_terms(root: Path) -> set[str]:
    """Return canonical study-unit titles, lowercased, as forbidden profile prose."""
    path = resolve_root_path(root, "research/scope/final_question_allocation.json")
    terms: set[str] = set()
    chapters = resolve_root_path(root, "research/scope/chapters")
    if chapters.is_dir():
        for units_path in sorted(chapters.glob("*/study_units.json")):
            artifact = json.loads(units_path.read_text())
            for unit in artifact.get("study_units", []):
                title = unit.get("title")
                if isinstance(title, str) and len(title) >= 5:
                    terms.add(title.strip().lower())
    if not path.is_file():  # pragma: no cover - canonical allocation always exists
        raise DisciplineProfileError("canonical allocation is unavailable")
    return terms


def _validate_option_set_contract(contract: Any, *, profile_id: str) -> dict[str, Any]:
    if not isinstance(contract, dict):
        raise DisciplineProfileError(f"{profile_id}: option-set contract must be an object")
    archetype = contract.get("option_set_archetype")
    if archetype not in OPTION_SET_ARCHETYPES:
        raise DisciplineProfileError(
            f"{profile_id}: unknown option-set archetype: {archetype}"
        )
    axis = contract.get("response_class_axis")
    if axis != ARCHETYPE_RESPONSE_AXIS[archetype]:
        raise DisciplineProfileError(
            f"{profile_id}: {archetype} must use response-class axis "
            f"{ARCHETYPE_RESPONSE_AXIS[archetype]}"
        )
    permitted = set(RESPONSE_CLASS_AXES[axis]["tokens"]) | {
        RESPONSE_CLASS_AXES[axis]["generic_token"]
    }
    implications = contract.get("token_implications", {})
    if not isinstance(implications, dict):
        raise DisciplineProfileError(f"{profile_id}: token implications must be an object")
    for token, implied in implications.items():
        if token not in permitted or not isinstance(implied, list):
            raise DisciplineProfileError(
                f"{profile_id}: implication source is not on axis {axis}: {token}"
            )
        if any(value not in permitted for value in implied):
            raise DisciplineProfileError(
                f"{profile_id}: implication target is not on axis {axis}: {token}"
            )
    nominal = contract.get("nominal_parity_axes", [])
    if not isinstance(nominal, list):
        raise DisciplineProfileError(f"{profile_id}: nominal parity axes must be a list")
    for value in nominal:
        if value not in NOMINAL_PARITY_AXES:
            raise DisciplineProfileError(
                f"{profile_id}: unknown nominal parity axis: {value}"
            )
        if value == axis:
            raise DisciplineProfileError(
                f"{profile_id}: {value} is the response-class axis for {archetype} and "
                "may not also be a nominal parity axis"
            )
    return {
        "option_set_archetype": archetype,
        "response_class_axis": axis,
        "token_implications": implications,
        "nominal_parity_axes": list(nominal),
    }


def validate_discipline_profile(profile: Any, *, clinical_terms: set[str]) -> dict[str, Any]:
    """Validate one profile against the closed common-core vocabularies."""
    if not isinstance(profile, dict):
        raise DisciplineProfileError("profile must be an object")
    profile_id = profile.get("profile_id")
    if profile_id not in PROFILE_IDS:
        raise DisciplineProfileError(f"unknown profile id: {profile_id}")
    if profile.get("scope") != "QGEN_DISCIPLINE_PROFILE":
        raise DisciplineProfileError(f"{profile_id}: wrong artifact scope")
    if profile.get("r4_status") not in R4_STATUSES:
        raise DisciplineProfileError(f"{profile_id}: missing R4 status")
    assert_no_quota_shaped_fields(profile, label=f"profile {profile_id}")

    archetypes = profile.get("item_archetypes")
    if not isinstance(archetypes, list) or not archetypes:
        raise DisciplineProfileError(f"{profile_id}: item archetypes are required")
    seen: set[str] = set()
    for entry in archetypes:
        if not isinstance(entry, dict):
            raise DisciplineProfileError(f"{profile_id}: item archetype must be an object")
        name = entry.get("item_archetype")
        if name not in ITEM_ARCHETYPES:
            raise DisciplineProfileError(f"{profile_id}: unknown item archetype: {name}")
        if name in seen:
            raise DisciplineProfileError(f"{profile_id}: duplicate item archetype: {name}")
        seen.add(name)
        permitted = entry.get("permitted_option_set_archetypes")
        if not isinstance(permitted, list) or not permitted or any(
            value not in OPTION_SET_ARCHETYPES for value in permitted
        ):
            raise DisciplineProfileError(
                f"{profile_id}: {name} needs permitted option-set archetypes"
            )
        for value in entry.get("scenario_requirements", []):
            if value not in SCENARIO_REQUIREMENTS:
                raise DisciplineProfileError(
                    f"{profile_id}: unknown scenario requirement: {value}"
                )
        for value in entry.get("permitted_decision_granularities", []):
            if value not in DECISION_GRANULARITY_PATTERNS:
                raise DisciplineProfileError(
                    f"{profile_id}: unknown decision granularity: {value}"
                )
        for value in entry.get("scenario_rules", []):
            if value not in SCENARIO_RULES:
                raise DisciplineProfileError(f"{profile_id}: unknown scenario rule: {value}")

    contracts = profile.get("option_set_contracts")
    if not isinstance(contracts, list) or not contracts:
        raise DisciplineProfileError(f"{profile_id}: option-set contracts are required")
    resolved_contracts: dict[str, dict[str, Any]] = {}
    for contract in contracts:
        validated = _validate_option_set_contract(contract, profile_id=profile_id)
        if validated["option_set_archetype"] in resolved_contracts:
            raise DisciplineProfileError(
                f"{profile_id}: duplicate option-set contract: "
                f"{validated['option_set_archetype']}"
            )
        resolved_contracts[validated["option_set_archetype"]] = validated

    declared = {
        value
        for entry in archetypes
        for value in entry["permitted_option_set_archetypes"]
    }
    missing = declared - set(resolved_contracts)
    if missing:
        raise DisciplineProfileError(
            f"{profile_id}: option-set archetypes without a contract: {sorted(missing)}"
        )

    ranking = profile.get("competitor_ranking_preference")
    if not isinstance(ranking, list) or not ranking or any(
        value not in COMPETITOR_RANKING_SIGNALS for value in ranking
    ):
        raise DisciplineProfileError(f"{profile_id}: competitor ranking preference is invalid")
    if ranking[0] != "NEAREST_UNSATISFIED_CORRECTNESS_CONDITION":
        raise DisciplineProfileError(
            f"{profile_id}: near-miss preference must rank first"
        )
    if "REVIEWED_SEED_STRENGTH" in ranking and ranking.index("REVIEWED_SEED_STRENGTH") != len(ranking) - 1:
        raise DisciplineProfileError(
            f"{profile_id}: reviewed seed strength is a tie-break, not a leading signal"
        )

    preference = profile.get("evidence_source_preference")
    if not isinstance(preference, list) or not preference or any(
        value not in EVIDENCE_SOURCE_TIERS for value in preference
    ):
        raise DisciplineProfileError(f"{profile_id}: evidence source preference is invalid")
    for value in profile.get("currentness_escalation_triggers", []):
        if value not in CURRENTNESS_ESCALATION_TRIGGERS:
            raise DisciplineProfileError(f"{profile_id}: unknown currentness trigger: {value}")
    for value in profile.get("prohibited_shortcuts", []):
        if value not in PROHIBITED_SHORTCUTS:
            raise DisciplineProfileError(f"{profile_id}: unknown prohibited shortcut: {value}")

    risk = profile.get("numeric_risk_classes", [])
    if not isinstance(risk, list):
        raise DisciplineProfileError(f"{profile_id}: numeric risk classes must be a list")
    for entry in risk:
        if not isinstance(entry, dict) or not isinstance(entry.get("fact_class"), str):
            raise DisciplineProfileError(f"{profile_id}: numeric risk entry is malformed")
        if entry.get("validation_level") not in (1, 2):
            raise DisciplineProfileError(
                f"{profile_id}: numeric risk entry needs validation level 1 or 2"
            )
        if not isinstance(entry.get("requires_independent_corroboration", False), bool):
            raise DisciplineProfileError(
                f"{profile_id}: corroboration requirement must be boolean"
            )

    for field in _FREE_TEXT_FIELDS:
        _assert_no_clinical_prose(profile, field, clinical_terms, profile_id)

    return {
        "profile_id": profile_id,
        "r4_status": profile["r4_status"],
        "item_archetypes": {entry["item_archetype"]: entry for entry in archetypes},
        "option_set_contracts": resolved_contracts,
        "competitor_ranking_preference": ranking,
        "evidence_source_preference": preference,
        "currentness_escalation_triggers": list(
            profile.get("currentness_escalation_triggers", [])
        ),
        "numeric_risk_classes": {entry["fact_class"]: entry for entry in risk},
        "prohibited_shortcuts": list(profile.get("prohibited_shortcuts", [])),
        "permitted_archetype_exceptions": list(
            profile.get("permitted_archetype_exceptions", [])
        ),
    }


def _assert_no_clinical_prose(
    node: Any, field: str, clinical_terms: set[str], profile_id: str
) -> None:
    if isinstance(node, dict):
        for name, value in node.items():
            if name == field and isinstance(value, str):
                lowered = value.lower()
                for term in clinical_terms:
                    if term in lowered:
                        raise DisciplineProfileError(
                            f"{profile_id}: profile prose names a canonical clinical "
                            f"study unit: {term}"
                        )
            _assert_no_clinical_prose(value, field, clinical_terms, profile_id)
    elif isinstance(node, list):
        for value in node:
            _assert_no_clinical_prose(value, field, clinical_terms, profile_id)


def load_discipline_profiles(root: Path) -> dict[str, dict[str, Any]]:
    """Load and validate every canonical discipline profile."""
    root = Path(root).resolve()
    clinical_terms = _clinical_entity_terms(root)
    directory = resolve_root_path(root, "research/qgen/profiles")
    profiles: dict[str, dict[str, Any]] = {}
    for profile_id in PROFILE_IDS:
        path = directory / f"{profile_id}.profile.json"
        if not path.is_file():
            raise DisciplineProfileError(f"missing discipline profile: {profile_id}")
        document = json.loads(path.read_text())
        profiles[profile_id] = validate_discipline_profile(
            document, clinical_terms=clinical_terms
        )
    return profiles


def resolve_option_set_contract(
    profile: dict[str, Any], item_archetype: str, option_set_archetype: str
) -> dict[str, Any]:
    """Return the profile's contract for one item x option-set archetype pair."""
    entry = profile["item_archetypes"].get(item_archetype)
    if entry is None:
        raise DisciplineProfileError(
            f"{profile['profile_id']}: item archetype is not permitted: {item_archetype}"
        )
    if option_set_archetype not in entry["permitted_option_set_archetypes"]:
        exception = any(
            record.get("item_archetype") == item_archetype
            and option_set_archetype in record.get("option_set_archetypes", [])
            for record in profile["permitted_archetype_exceptions"]
        )
        if not exception:
            raise DisciplineProfileError(
                f"{profile['profile_id']}: {option_set_archetype} is not permitted for "
                f"{item_archetype}"
            )
    contract = profile["option_set_contracts"].get(option_set_archetype)
    if contract is None:
        raise DisciplineProfileError(
            f"{profile['profile_id']}: no contract for {option_set_archetype}"
        )
    return contract
