"""Deterministic high-risk question classification."""

from __future__ import annotations

import re
from collections.abc import Iterable


RISK_FLAGS = (
    "NUMERICAL_THRESHOLD",
    "DOSE",
    "SCREENING",
    "VACCINATION",
    "PREGNANCY",
    "PEDIATRICS",
    "ANTICOAGULATION",
    "LEGAL",
    "PUBLIC_HEALTH_REPORTING",
    "EMERGENCY_TREATMENT",
)

_STRUCTURED_FIELD_FLAGS = {
    "numerical_threshold": "NUMERICAL_THRESHOLD",
    "threshold": "NUMERICAL_THRESHOLD",
    "dose": "DOSE",
    "dosage": "DOSE",
    "medication_dose": "DOSE",
    "screening": "SCREENING",
    "screening_interval": "SCREENING",
    "vaccination": "VACCINATION",
    "vaccine": "VACCINATION",
    "pregnancy": "PREGNANCY",
    "pediatrics": "PEDIATRICS",
    "paediatrics": "PEDIATRICS",
    "anticoagulation": "ANTICOAGULATION",
    "legal": "LEGAL",
    "public_health_reporting": "PUBLIC_HEALTH_REPORTING",
    "emergency_treatment": "EMERGENCY_TREATMENT",
}

_TEXT_PATTERNS = {
    "NUMERICAL_THRESHOLD": re.compile(
        r"(?:\b(?:threshold|cut[- ]?off|upper limit|lower limit|target)\b[^.]{0,40}?\b\d+(?:\.\d+)?\b|\b\d+(?:\.\d+)?\b[^.]{0,40}?\b(?:threshold|cut[- ]?off|upper limit|lower limit|target)\b|\b(?:at least|at most|no more than|not more than|greater than|less than|equal to)\s+\d+(?:\.\d+)?)",
        re.IGNORECASE,
    ),
    "DOSE": re.compile(
        r"\b(?:dose|dosage)\b|\b\d+(?:\.\d+)?\s*(?:mg|mcg|μg|g|units?|mL)\b",
        re.IGNORECASE,
    ),
    "SCREENING": re.compile(
        r"\bscreening\b|\bscreen(?:ed|ing)?\s+(?:interval|test|program|recommendation)\b",
        re.IGNORECASE,
    ),
    "VACCINATION": re.compile(
        r"\b(?:vaccin(?:e|es|ated|ation)|immuni[sz](?:e|es|ed|ing|ation))\b",
        re.IGNORECASE,
    ),
    "PREGNANCY": re.compile(
        r"\b(?:pregnan(?:t|cy)|gestational|trimester|antenatal|prenatal|postpartum)\b",
        re.IGNORECASE,
    ),
    "PEDIATRICS": re.compile(
        r"\b(?:p[ae]diatric(?:s)?|neonat\w*|newborns?|infants?|children|child|adolescen\w*)\b",
        re.IGNORECASE,
    ),
    "ANTICOAGULATION": re.compile(
        r"\b(?:anticoagulan\w*|warfarin|heparin|apixaban|rivaroxaban|dabigatran|edoxaban|doac(?:s)?)\b",
        re.IGNORECASE,
    ),
    "LEGAL": re.compile(
        r"\b(?:informed consent|decision[- ]making capacity|substitute decision[- ]maker|health care proxy|power of attorney|court order|medical assistance in dying|\bmaid\b)\b",
        re.IGNORECASE,
    ),
    "PUBLIC_HEALTH_REPORTING": re.compile(
        r"\b(?:report(?:ed|ing)?|notify|notified|notification|notifi(?:able|cation)|mandatory report(?:ing)?)\b[^.]{0,50}\b(?:to\s+)?(?:public health|medical officer of health)\b|\b(?:public health|medical officer of health)\b[^.]{0,50}\b(?:report(?:ed|ing)?|notify|notified|notification|notifi(?:able|cation)|mandatory report(?:ing)?)\b|\b(?:notifiable|reportable) disease\b",
        re.IGNORECASE,
    ),
    "EMERGENCY_TREATMENT": re.compile(
        r"\bemergency (?:treatment|management|resuscitation)\b|\b(?:cpr|cardiopulmonary resuscitation|cardiac arrest|anaphylaxis|airway obstruction|status epilepticus)\b",
        re.IGNORECASE,
    ),
}

_NUMERICAL_COMPARISON = re.compile(r"(?:≥|≤|>=|<=|>|<|=)\s*\d+(?:\.\d+)?")
_CLINICAL_DECISION = re.compile(
    r"\b(?:start|initiat\w*|treat\w*|therapy|investigat\w*|refer\w*|screen\w*|diagnos\w*|admit\w*|discharg\w*|recommend\w*|consider\w*|should|indicat\w*|eligib\w*|contraindicat\w*|manage\w*)\b",
    re.IGNORECASE,
)


def _normalize_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.casefold()).strip("_")


def _is_present(value: object) -> bool:
    return value is True or (isinstance(value, str) and bool(value.strip())) or (
        isinstance(value, (list, tuple, dict, set)) and bool(value)
    ) or (isinstance(value, (int, float)) and not isinstance(value, bool))


def _structured_flags(value: object) -> set[str]:
    flags: set[str] = set()
    if isinstance(value, dict):
        for key, child in value.items():
            normalized_key = _normalize_key(key) if isinstance(key, str) else ""
            if normalized_key in {"risk_flags", "high_risk_flags", "risk_categories"}:
                if isinstance(child, Iterable) and not isinstance(child, (str, bytes, dict)):
                    flags.update(item for item in child if isinstance(item, str) and item in RISK_FLAGS)
            flag = _STRUCTURED_FIELD_FLAGS.get(normalized_key)
            if flag and _is_present(child):
                flags.add(flag)
            flags.update(_structured_flags(child))
    elif isinstance(value, list):
        for child in value:
            flags.update(_structured_flags(child))
    return flags


def _question_text(question: dict) -> str:
    question_body = question.get("question")
    if not isinstance(question_body, dict):
        return ""
    values: list[str] = []
    for field in ("stem", "lead_in"):
        value = question_body.get(field)
        if isinstance(value, str):
            values.append(value)
    options = question_body.get("options")
    if isinstance(options, list):
        values.extend(
            option["text"]
            for option in options
            if isinstance(option, dict) and isinstance(option.get("text"), str)
        )
    return "\n".join(values)


def _has_clinical_comparison(text: str) -> bool:
    """Require a decision context so ordinary equality statements stay unflagged."""
    return any(
        _NUMERICAL_COMPARISON.search(sentence) and _CLINICAL_DECISION.search(sentence)
        for sentence in re.split(r"[.!?\n]+", text)
    )


def classify_risk(question: dict) -> list[str]:
    """Return fixed high-risk flags in their declared deterministic order."""
    if not isinstance(question, dict):
        return []
    flags = _structured_flags(question)
    text = _question_text(question)
    flags.update(flag for flag, pattern in _TEXT_PATTERNS.items() if pattern.search(text))
    if _has_clinical_comparison(text):
        flags.add("NUMERICAL_THRESHOLD")
    return [flag for flag in RISK_FLAGS if flag in flags]
