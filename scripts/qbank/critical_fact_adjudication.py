"""Global, discipline-independent adjudication of critical facts at claim level.

Two R4 defects were source-level and both were transcribed faithfully: an
anatomical figure given in centimetres where the accepted figure is in inches,
and a guideline severity band narrowed in the packet itself.  Both claims carried
``verification_status: VERIFIED_COMPLETE``.  That status asserts fidelity of
transcription and was being read as truth.

This module splits the two readings apart, escalates a claim by the risk its
statement carries rather than by how many questions want it, and records rather
than silently corrects a source it cannot reconcile.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
import json
from pathlib import Path
import re
from typing import Any

from .errors import QbankError
from .paths import resolve_root_path


class CriticalFactError(QbankError):
    """A claim, a reference constant, or an adjudication record is unusable."""


FACT_CLASSES = (
    "NUMERIC_VALUE",
    "UNIT",
    "MEDICATION_DOSE",
    "CLINICAL_SCORE_COMPONENT",
    "CLINICAL_SCORE_THRESHOLD",
    "SCREENING_INTERVAL",
    "TREATMENT_THRESHOLD",
    "GUIDELINE_SEVERITY_BAND",
    "GESTATIONAL_AGE_THRESHOLD",
    "ANATOMICAL_MEASUREMENT",
    "EPIDEMIOLOGIC_VALUE",
    "FORMULA_DERIVED_VALUE",
    "TIME_WINDOW",
    "LEGAL_JURISDICTIONAL_REQUIREMENT",
)

VALIDATION_LEVELS = (0, 1, 2, 3)

ADJUDICATION_STATUSES = (
    "ADJUDICATED_SOURCE_CORRECT",
    "ADJUDICATED_SOURCE_ERRONEOUS",
    "UNRESOLVED",
)

TRANSCRIPTION_STATUSES = ("VERIFIED_COMPLETE", "VERIFIED_PARTIAL", "UNVERIFIED")
FACT_STATUSES = ("CORROBORATED", "PRIMARY_AUTHORITY", "DISPUTED", "NOT_ADJUDICATED")

# Authority tiers that may discharge Level 2 on their own, for a fact class the
# bound profile has not marked as requiring independent corroboration.
PRIMARY_AUTHORITY_TIERS = frozenset({
    "NATIONAL_SPECIALTY_SOCIETY",
    "NATIONAL_PUBLIC_HEALTH_AGENCY",
    "NATIONAL_EDUCATIONAL_REFERENCE",
    "PROVINCIAL_STATUTE_OR_REGULATION",
})

_NUMBER_WORDS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
    "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "twenty": 20,
    "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60,
}

_LENGTH_UNITS = {"cm": "LENGTH", "mm": "LENGTH", "m": "LENGTH", "in": "LENGTH",
                 "inch": "LENGTH", "inches": "LENGTH", "centimetre": "LENGTH",
                 "centimetres": "LENGTH", "centimeter": "LENGTH", "centimeters": "LENGTH"}
_MASS_UNITS = {"mg": "MASS", "mcg": "MASS", "g": "MASS", "kg": "MASS",
               "microgram": "MASS", "micrograms": "MASS", "milligram": "MASS",
               "milligrams": "MASS", "gram": "MASS", "grams": "MASS",
               "kilogram": "MASS", "kilograms": "MASS"}
_TIME_UNITS = {"second": "TIME", "seconds": "TIME", "minute": "TIME", "minutes": "TIME",
               "hour": "TIME", "hours": "TIME", "day": "TIME", "days": "TIME",
               "week": "TIME", "weeks": "TIME", "month": "TIME", "months": "TIME",
               "year": "TIME", "years": "TIME"}
_UNIT_DIMENSIONS = {**_LENGTH_UNITS, **_MASS_UNITS, **_TIME_UNITS,
                    "%": "PROPORTION", "percent": "PROPORTION",
                    "mmhg": "PRESSURE", "mmol/l": "CONCENTRATION",
                    "mg/dl": "CONCENTRATION", "beats/min": "RATE",
                    "celsius": "TEMPERATURE", "fahrenheit": "TEMPERATURE"}

# Customary transpositions that turn a correct figure into a wrong one while
# leaving the numeral untouched.
UNIT_TRANSPOSITIONS = (
    ("in", "cm"), ("cm", "in"), ("lb", "kg"), ("kg", "lb"),
    ("mg", "g"), ("g", "mg"), ("mmol/l", "mg/dl"), ("mg/dl", "mmol/l"),
    ("celsius", "fahrenheit"), ("fahrenheit", "celsius"),
)

_SEVERITY_BANDS = ("mild", "moderate", "severe")
_TREATMENT_LINES = (
    "first-line", "first line", "second-line", "second line", "third-line",
    "third line", "adjunctive", "monotherapy", "treatment of choice", "preferred",
)
_LEGAL_TERMS = (
    "statute", "legislation", "regulation", "mandatory report",
    "legally required", "duty to report", "jurisdiction", "court order",
)
# Matched as a whole word so that an ordinary word ending in "act" is not read
# as a reference to an Act of a legislature.
_LEGAL_WORD_TERMS = ("act", "acts")
_SCORE_TERMS = ("score", "scale point", "points on")
_SCREENING_TERMS = ("screening interval", "screened every", "screening every",
                    "repeat screening", "rescreen")
_THRESHOLD_TERMS = ("threshold", "cut-off", "cutoff", "or more", "or greater",
                    "or higher", "at least", "above which", "below which")
_GESTATION_TERMS = ("gestation", "gestational age", "weeks pregnant", "trimester")
_EPI_TERMS = ("sensitivity", "specificity", "prevalence", "incidence",
              "positive predictive", "negative predictive", "relative risk",
              "odds ratio", "number needed to treat", "mortality rate")
_ANATOMY_TERMS = ("point", "line from", "distance from", "landmark", "from the anterior",
                  "in diameter", "in length", "in width", "spine", "umbilicus")
_DOSE_TERMS = ("dose", "dosing", "mg/kg", "per kg", "daily dose")

_NUMERAL = re.compile(r"\d+(?:[.,]\d+)?")


def _normalize_statement(statement: str) -> str:
    return statement.lower().replace("degrees celsius", "celsius").replace(
        "degrees fahrenheit", "fahrenheit"
    )


def _has_numeral(text: str) -> bool:
    lowered = text.lower()
    if _NUMERAL.search(lowered):
        return True
    return any(re.search(rf"\b{word}\b", lowered) for word in _NUMBER_WORDS)


def _contains(text: str, terms: tuple[str, ...]) -> bool:
    lowered = text.lower()
    return any(term in lowered for term in terms)


def detect_fact_classes(statement: str) -> list[str]:
    """Return the critical fact classes a claim statement carries.

    Detection is deterministic: numerals, a closed unit lexicon, and closed
    phrase lexicons for bands, thresholds, intervals and legal duties.  An
    ordinary qualitative claim matches nothing and stays at Level 0, which is
    what keeps the cost of this layer bounded.
    """
    if not isinstance(statement, str) or not statement.strip():
        raise CriticalFactError("claim statement must be a non-empty string")
    lowered = _normalize_statement(statement)
    classes: set[str] = set()
    numeric = _has_numeral(lowered)
    if numeric:
        classes.add("NUMERIC_VALUE")
    quantities = _quantities(statement)
    dimensions = {_UNIT_DIMENSIONS[unit] for _, unit in quantities}
    if quantities:
        classes.add("UNIT")
    if numeric and _contains(lowered, _DOSE_TERMS):
        classes.add("MEDICATION_DOSE")
    if _contains(lowered, _SCORE_TERMS):
        classes.add("CLINICAL_SCORE_COMPONENT")
        if numeric and _contains(lowered, _THRESHOLD_TERMS):
            classes.add("CLINICAL_SCORE_THRESHOLD")
    if _contains(lowered, _SCREENING_TERMS):
        classes.add("SCREENING_INTERVAL")
    if numeric and _contains(lowered, _THRESHOLD_TERMS) and not classes.intersection(
        {"CLINICAL_SCORE_THRESHOLD"}
    ):
        classes.add("TREATMENT_THRESHOLD")
    if any(band in lowered for band in _SEVERITY_BANDS) and _contains(lowered, _TREATMENT_LINES):
        classes.add("GUIDELINE_SEVERITY_BAND")
    if _contains(lowered, _GESTATION_TERMS) and numeric:
        classes.add("GESTATIONAL_AGE_THRESHOLD")
    if "LENGTH" in dimensions and _contains(lowered, _ANATOMY_TERMS):
        classes.add("ANATOMICAL_MEASUREMENT")
    if _contains(lowered, _EPI_TERMS) and numeric:
        classes.add("EPIDEMIOLOGIC_VALUE")
    if "TIME" in dimensions:
        classes.add("TIME_WINDOW")
    if _contains(lowered, _LEGAL_TERMS) or any(
        re.search(rf"\b{term}\b", lowered) for term in _LEGAL_WORD_TERMS
    ):
        classes.add("LEGAL_JURISDICTIONAL_REQUIREMENT")
    return sorted(classes)


def load_reference_constants(root: Path) -> list[dict[str, Any]]:
    """Load the structured anatomy/physiology constants admitted for sanity checks."""
    path = resolve_root_path(root, "research/qgen/reference_constants.json")
    if not path.is_file():
        raise CriticalFactError("reference constants registry is unavailable")
    document = json.loads(path.read_text())
    constants = document.get("constants")
    if not isinstance(constants, list) or not constants:
        raise CriticalFactError("reference constants registry is empty")
    for constant in constants:
        for field in ("constant_id", "quantity_class", "admission_status"):
            if not isinstance(constant.get(field), str) or not constant[field]:
                raise CriticalFactError(f"reference constant missing {field}")
        if constant["admission_status"] != "ADMITTED_STANDARD_REFERENCE_CONSTANT":
            raise CriticalFactError(
                f"reference constant is not admitted: {constant['constant_id']}"
            )
        if not isinstance(constant.get("subject_terms"), list) or not constant["subject_terms"]:
            raise CriticalFactError(
                f"reference constant needs subject terms: {constant['constant_id']}"
            )
    return constants


def load_source_authority_registry(root: Path) -> dict[str, str]:
    """Return issuing organization to authority tier, for Level 2 discharge."""
    path = resolve_root_path(root, "research/qgen/source_authority_registry.json")
    if not path.is_file():
        raise CriticalFactError("source authority registry is unavailable")
    document = json.loads(path.read_text())
    rows = document.get("authorities")
    if not isinstance(rows, list) or not rows:
        raise CriticalFactError("source authority registry is empty")
    registry: dict[str, str] = {}
    for row in rows:
        organization = row.get("issuing_organization")
        tier = row.get("authority_tier")
        if not isinstance(organization, str) or not organization:
            raise CriticalFactError("authority row needs an issuing organization")
        if tier not in {
            "NATIONAL_SPECIALTY_SOCIETY", "NATIONAL_PUBLIC_HEALTH_AGENCY",
            "NATIONAL_EDUCATIONAL_REFERENCE", "PROVINCIAL_STATUTE_OR_REGULATION",
            "PEER_REVIEWED_GUIDELINE", "TERTIARY_FALLBACK",
        }:
            raise CriticalFactError(f"unknown authority tier for {organization}")
        registry[organization.strip().lower()] = tier
    return registry


def _quantities(statement: str) -> list[tuple[Decimal, str]]:
    """Return (value, unit) pairs a statement asserts, for the sanity checks."""
    lowered = _normalize_statement(statement)
    found: list[tuple[Decimal, str]] = []
    for match in re.finditer(
        r"(\d+(?:\.\d+)?)\s*(%|[a-z/]+)",
        lowered,
    ):
        raw, unit = match.group(1), match.group(2)
        unit = unit.strip()
        if unit not in _UNIT_DIMENSIONS:
            continue
        try:
            found.append((Decimal(raw), unit))
        except InvalidOperation:  # pragma: no cover - regex guarantees a number
            continue
    return found


_TO_CM = {"cm": Decimal("1"), "mm": Decimal("0.1"), "m": Decimal("100"),
          "in": Decimal("2.54"), "inch": Decimal("2.54"), "inches": Decimal("2.54"),
          "centimetre": Decimal("1"), "centimetres": Decimal("1"),
          "centimeter": Decimal("1"), "centimeters": Decimal("1")}


def run_source_sanity_checks(
    statement: str, constants: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Run the deterministic §4.3 checks that precede any corroboration work."""
    findings: list[dict[str, Any]] = []
    lowered = statement.lower()
    quantities = _quantities(statement)
    for constant in constants:
        if not any(term.lower() in lowered for term in constant["subject_terms"]):
            continue
        canonical = constant.get("canonical_value")
        plausible = constant.get("plausible_range")
        for value, unit in quantities:
            if unit not in _TO_CM:
                continue
            in_cm = value * _TO_CM[unit]
            if plausible and plausible.get("unit") in _TO_CM:
                low = Decimal(str(plausible["low"])) * _TO_CM[plausible["unit"]]
                high = Decimal(str(plausible["high"])) * _TO_CM[plausible["unit"]]
                if not (low <= in_cm <= high):
                    findings.append({
                        "check": "IMPLAUSIBLE_MAGNITUDE",
                        "constant_id": constant["constant_id"],
                        "stated": f"{value} {unit}",
                        "plausible_range": plausible,
                    })
            if canonical and canonical.get("unit") in _TO_CM:
                low = Decimal(str(canonical["low"]))
                high = Decimal(str(canonical["high"]))
                if low <= value <= high and canonical["unit"] != unit:
                    findings.append({
                        "check": "UNIT_TRANSPOSITION_SUSPICION",
                        "constant_id": constant["constant_id"],
                        "stated": f"{value} {unit}",
                        "canonical_value": canonical,
                        "detail": (
                            "the numeral matches the canonical value under a customary "
                            f"{canonical['unit']} to {unit} transposition"
                        ),
                    })
                canonical_low = low * _TO_CM[canonical["unit"]]
                canonical_high = high * _TO_CM[canonical["unit"]]
                if not (canonical_low <= in_cm <= canonical_high):
                    findings.append({
                        "check": "STRUCTURED_REFERENCE_CONTRADICTION",
                        "constant_id": constant["constant_id"],
                        "stated": f"{value} {unit}",
                        "canonical_value": canonical,
                    })
    deduped: list[dict[str, Any]] = []
    for finding in findings:
        if finding not in deduped:
            deduped.append(finding)
    return sorted(deduped, key=lambda row: (row["check"], row["constant_id"], row["stated"]))


def _declared_quantities(claim: dict[str, Any]) -> dict[str, tuple[Decimal, str]]:
    """Return a claim's explicitly declared quantities, keyed by quantity id."""
    declared: dict[str, tuple[Decimal, str]] = {}
    for entry in claim.get("quantities") or []:
        if not isinstance(entry, dict):
            raise CriticalFactError("declared quantity must be an object")
        quantity_id = entry.get("quantity_id")
        unit = entry.get("unit")
        if not isinstance(quantity_id, str) or not quantity_id or not isinstance(unit, str):
            raise CriticalFactError("declared quantity needs a quantity id and unit")
        try:
            declared[quantity_id] = (Decimal(str(entry.get("value"))), unit)
        except (InvalidOperation, TypeError) as exc:
            raise CriticalFactError(
                f"declared quantity is not numeric: {quantity_id}"
            ) from exc
    return declared


def _high_authority_disagreement(
    claim: dict[str, Any],
    siblings: list[dict[str, Any]],
    source_ids_by_claim: dict[str, set[str]],
) -> list[dict[str, Any]]:
    """Two different admitted sources stating incompatible values for one quantity.

    The comparison runs over *declared* quantity identifiers, never over prose.
    Deciding from free text whether two figures measure the same thing cannot be
    done deterministically at usable precision, and guessing it manufactures
    conflicts between unrelated numbers. A packet whose claims declare no
    quantities therefore yields no verdict here rather than a fabricated one; the
    limitation is reported rather than hidden.
    """
    conflicts: list[dict[str, Any]] = []
    own = _declared_quantities(claim)
    if not own:
        return conflicts
    own_sources = source_ids_by_claim.get(claim["claim_id"], set())
    for other in siblings:
        if other["claim_id"] == claim["claim_id"]:
            continue
        other_sources = source_ids_by_claim.get(other["claim_id"], set())
        if not other_sources or own_sources.intersection(other_sources):
            continue
        for quantity_id, (value, unit) in own.items():
            other_quantity = _declared_quantities(other).get(quantity_id)
            if other_quantity is None:
                continue
            other_value, other_unit = other_quantity
            if unit == other_unit and value == other_value:
                continue
            conflicts.append({
                "check": "HIGH_AUTHORITY_DISAGREEMENT",
                "quantity_id": quantity_id,
                "conflicting_claim_id": other["claim_id"],
                "stated": f"{value} {unit}",
                "conflicting_value": f"{other_value} {other_unit}",
            })
    return conflicts


def adjudicate_claim(
    claim: dict[str, Any],
    *,
    sources: dict[str, dict[str, Any]],
    authority_registry: dict[str, str],
    constants: list[dict[str, Any]],
    profile_risk_classes: dict[str, dict[str, Any]],
    sibling_claims: list[dict[str, Any]] | None = None,
    source_ids_by_claim: dict[str, set[str]] | None = None,
) -> dict[str, Any]:
    """Adjudicate one evidence-packet claim and return its record."""
    claim_id = claim.get("claim_id")
    statement = claim.get("statement")
    if not isinstance(claim_id, str) or not claim_id:
        raise CriticalFactError("claim needs an id")
    fact_classes = set(detect_fact_classes(statement))
    if _declared_quantities(claim):
        # A declared quantity is a numeric fact whether or not the surrounding
        # prose happens to trip the lexicon, and it is the only input check 7 can
        # compare, so it must not be able to slip past as a Level 0 claim.
        fact_classes.update({"NUMERIC_VALUE", "UNIT"})
    fact_classes = sorted(fact_classes)
    source_refs = claim.get("source_refs") or []
    source_ids = sorted({ref.get("source_id") for ref in source_refs if isinstance(ref, dict)})
    tiers = sorted({
        authority_registry.get(
            str(sources.get(source_id, {}).get("issuing_organization", "")).strip().lower(),
            "TERTIARY_FALLBACK",
        )
        for source_id in source_ids
    })

    record: dict[str, Any] = {
        "claim_id": claim_id,
        "fact_classes": fact_classes,
        "source_ids": source_ids,
        "authority_tiers": tiers,
        "transcription_status": claim.get("verification_status", "UNVERIFIED"),
        "sanity_findings": [],
        "conflicting_evidence": [],
        "adjudicated_value": None,
        "adjudication_basis": None,
    }
    if record["transcription_status"] not in TRANSCRIPTION_STATUSES:
        record["transcription_status"] = "UNVERIFIED"

    if not fact_classes:
        record.update({
            "validation_level": 0,
            "fact_status": "NOT_ADJUDICATED",
            "status": "ADJUDICATED_SOURCE_CORRECT",
            "usable_in_generation": True,
            "adjudication_basis": "ORDINARY_QUALITATIVE_CLAIM",
        })
        return record

    sanity = run_source_sanity_checks(statement, constants)
    conflicts = _high_authority_disagreement(
        claim, sibling_claims or [], source_ids_by_claim or {}
    )
    record["sanity_findings"] = sanity
    record["conflicting_evidence"] = conflicts
    if sanity or conflicts:
        record.update({
            "validation_level": 3,
            "fact_status": "DISPUTED",
            "status": "UNRESOLVED",
            "usable_in_generation": False,
            "adjudication_basis": "SOURCE_SANITY_CHECK_TRIPPED",
            "fail_closed_reason": "FAIL_CLOSED_ERRONEOUS_SOURCE_FACT"
            if sanity
            else "FAIL_CLOSED_UNRESOLVED_CRITICAL_FACT",
        })
        return record

    mandatory = sorted(
        fact_class
        for fact_class in fact_classes
        if profile_risk_classes.get(fact_class, {}).get(
            "requires_independent_corroboration", False
        )
    )
    corroborated = len(source_ids) >= 2
    primary = any(tier in PRIMARY_AUTHORITY_TIERS for tier in tiers)

    if mandatory and not corroborated:
        record.update({
            "validation_level": 3,
            "fact_status": "DISPUTED",
            "status": "UNRESOLVED",
            "usable_in_generation": False,
            "adjudication_basis": (
                "PROFILE_REQUIRES_INDEPENDENT_CORROBORATION: " + ", ".join(mandatory)
            ),
            "fail_closed_reason": "FAIL_CLOSED_UNRESOLVED_CRITICAL_FACT",
        })
        return record

    if corroborated:
        record.update({
            "validation_level": 2,
            "fact_status": "CORROBORATED",
            "status": "ADJUDICATED_SOURCE_CORRECT",
            "usable_in_generation": True,
            "adjudication_basis": "CORROBORATED_BY_INDEPENDENT_SOURCE",
        })
        return record
    if primary:
        record.update({
            "validation_level": 2,
            "fact_status": "PRIMARY_AUTHORITY",
            "status": "ADJUDICATED_SOURCE_CORRECT",
            "usable_in_generation": True,
            "adjudication_basis": "AUTHORITATIVE_PRIMARY_REFERENCE",
        })
        return record
    record.update({
        "validation_level": 3,
        "fact_status": "DISPUTED",
        "status": "UNRESOLVED",
        "usable_in_generation": False,
        "adjudication_basis": "NO_CORROBORATION_AND_NO_PRIMARY_AUTHORITY",
        "fail_closed_reason": "FAIL_CLOSED_UNRESOLVED_CRITICAL_FACT",
    })
    return record


def adjudicate_evidence_packet(
    root: Path,
    evidence_packet: dict[str, Any],
    *,
    profile_risk_classes: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Adjudicate every claim in a packet once; questions inherit the outcome."""
    root = Path(root).resolve()
    constants = load_reference_constants(root)
    authority_registry = load_source_authority_registry(root)
    sources = {
        source["source_id"]: source
        for source in evidence_packet.get("sources", [])
        if isinstance(source, dict) and isinstance(source.get("source_id"), str)
    }
    claims = [
        claim
        for claim in evidence_packet.get("claims", [])
        if isinstance(claim, dict) and isinstance(claim.get("claim_id"), str)
    ]
    source_ids_by_claim = {
        claim["claim_id"]: {
            ref.get("source_id")
            for ref in (claim.get("source_refs") or [])
            if isinstance(ref, dict) and isinstance(ref.get("source_id"), str)
        }
        for claim in claims
    }
    return {
        claim["claim_id"]: adjudicate_claim(
            claim,
            sources=sources,
            authority_registry=authority_registry,
            constants=constants,
            profile_risk_classes=profile_risk_classes,
            sibling_claims=claims,
            source_ids_by_claim=source_ids_by_claim,
        )
        for claim in claims
    }


def enumerate_numeric_assertions(text: str, site: str) -> list[dict[str, Any]]:
    """Enumerate every numeral a candidate-facing surface asserts.

    Finding 7: an asserted numeral previously carried no obligation because the
    numeric gate covered derivations only.  Every numeral is now an assertion
    that must bind to a claim.
    """
    if site not in {"STEM", "OPTION", "RATIONALE"}:
        raise CriticalFactError(f"unknown numeric assertion site: {site}")
    return [
        {"site": site, "value": match.group(0), "offset": match.start()}
        for match in _NUMERAL.finditer(str(text))
    ]
