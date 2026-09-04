from pathlib import Path

import pytest

from qbank.critical_fact_adjudication import (
    CriticalFactError,
    adjudicate_claim,
    detect_fact_classes,
    enumerate_numeric_assertions,
    load_reference_constants,
    load_source_authority_registry,
    run_source_sanity_checks,
)


ROOT = Path(__file__).resolve().parents[1]

NATIONAL = {"issuing_organization": "Canadian Paediatric Society"}
TERTIARY = {"issuing_organization": "StatPearls Publishing, National Library of Medicine Bookshelf"}


def registry():
    return load_source_authority_registry(ROOT)


def constants():
    return load_reference_constants(ROOT)


def claim(statement, source_ids, claim_id="CLM-TEST", quantities=None):
    row = {
        "claim_id": claim_id,
        "statement": statement,
        "verification_status": "VERIFIED_COMPLETE",
        "source_refs": [{"source_id": source_id} for source_id in source_ids],
    }
    if quantities:
        row["quantities"] = quantities
    return row


def test_ordinary_qualitative_claim_stays_at_level_zero_and_costs_nothing():
    assert detect_fact_classes(
        "A comprehensive diagnostic assessment is the first step in clinical management."
    ) == []
    record = adjudicate_claim(
        claim("A comprehensive diagnostic assessment is the first step.", ["SRC-A"]),
        sources={"SRC-A": NATIONAL},
        authority_registry=registry(),
        constants=constants(),
        profile_risk_classes={},
    )
    assert record["validation_level"] == 0
    assert record["usable_in_generation"] is True


def test_a_severity_band_bound_to_a_treatment_line_is_detected():
    classes = detect_fact_classes(
        "Supervised activity is a first-line monotherapy for mild illness and a "
        "second-line adjunctive treatment for moderate severity illness."
    )
    assert "GUIDELINE_SEVERITY_BAND" in classes


def test_the_word_severity_alone_is_not_a_guideline_band():
    classes = detect_fact_classes(
        "Episodes are distinct and observable but not of sufficient duration or "
        "severity to cause significant functional impairment."
    )
    assert "GUIDELINE_SEVERITY_BAND" not in classes


def test_a_preposition_is_not_a_length_unit():
    classes = detect_fact_classes(
        "The score awards one point each for tenderness in the right lower quadrant."
    )
    assert "ANATOMICAL_MEASUREMENT" not in classes


def test_unit_transposition_and_structured_reference_both_catch_a_swapped_figure():
    findings = run_source_sanity_checks(
        "Maximal tenderness is at McBurney's point, 1.5 to 2 cm from the anterior "
        "superior iliac spine along the line to the umbilicus.",
        constants(),
    )
    checks = {row["check"] for row in findings}
    assert "UNIT_TRANSPOSITION_SUSPICION" in checks
    assert "STRUCTURED_REFERENCE_CONTRADICTION" in checks
    assert "IMPLAUSIBLE_MAGNITUDE" in checks


def test_a_tripped_sanity_check_fails_closed_and_records_rather_than_corrects():
    record = adjudicate_claim(
        claim(
            "Maximal tenderness is at McBurney's point, 1.5 to 2 cm from the anterior "
            "superior iliac spine.",
            ["SRC-A"],
        ),
        sources={"SRC-A": NATIONAL},
        authority_registry=registry(),
        constants=constants(),
        profile_risk_classes={},
    )
    assert record["status"] == "UNRESOLVED"
    assert record["usable_in_generation"] is False
    assert record["adjudicated_value"] is None
    assert record["fail_closed_reason"] == "FAIL_CLOSED_ERRONEOUS_SOURCE_FACT"


def test_a_primary_authority_discharges_level_two_for_an_ordinary_critical_class():
    record = adjudicate_claim(
        claim("Wheeze begins before the age of 12 months in this illness.", ["SRC-A"]),
        sources={"SRC-A": NATIONAL},
        authority_registry=registry(),
        constants=constants(),
        profile_risk_classes={},
    )
    assert record["validation_level"] == 2
    assert record["fact_status"] == "PRIMARY_AUTHORITY"
    assert record["usable_in_generation"] is True


def test_a_profile_may_require_independent_corroboration_and_then_one_source_is_not_enough():
    statement = (
        "Supervised activity is a first-line monotherapy for mild illness and a "
        "second-line adjunctive treatment for moderate severity illness."
    )
    risk = {
        "GUIDELINE_SEVERITY_BAND": {
            "validation_level": 2,
            "requires_independent_corroboration": True,
        }
    }
    single = adjudicate_claim(
        claim(statement, ["SRC-A"]),
        sources={"SRC-A": NATIONAL},
        authority_registry=registry(),
        constants=constants(),
        profile_risk_classes=risk,
    )
    assert single["usable_in_generation"] is False
    assert single["fail_closed_reason"] == "FAIL_CLOSED_UNRESOLVED_CRITICAL_FACT"

    corroborated = adjudicate_claim(
        claim(statement, ["SRC-A", "SRC-B"]),
        sources={"SRC-A": NATIONAL, "SRC-B": {"issuing_organization": "Public Health Agency of Canada"}},
        authority_registry=registry(),
        constants=constants(),
        profile_risk_classes=risk,
    )
    assert corroborated["fact_status"] == "CORROBORATED"
    assert corroborated["usable_in_generation"] is True


def test_a_tertiary_fallback_discharges_nothing():
    record = adjudicate_claim(
        claim("The main risk factor is a mass 5 cm in diameter or larger.", ["SRC-T"]),
        sources={"SRC-T": TERTIARY},
        authority_registry=registry(),
        constants=constants(),
        profile_risk_classes={},
    )
    assert record["usable_in_generation"] is False
    assert record["adjudication_basis"] == "NO_CORROBORATION_AND_NO_PRIMARY_AUTHORITY"


def test_two_sources_disagreeing_on_one_declared_quantity_fail_closed():
    quantities = [{"quantity_id": "LANDMARK_DISTANCE", "value": 2, "unit": "cm"}]
    other = claim(
        "The landmark lies a different distance away.",
        ["SRC-B"],
        claim_id="CLM-OTHER",
        quantities=[{"quantity_id": "LANDMARK_DISTANCE", "value": 5, "unit": "cm"}],
    )
    record = adjudicate_claim(
        claim("The landmark lies this far away.", ["SRC-A"], quantities=quantities),
        sources={"SRC-A": NATIONAL, "SRC-B": {"issuing_organization": "Public Health Agency of Canada"}},
        authority_registry=registry(),
        constants=constants(),
        profile_risk_classes={},
        sibling_claims=[other],
        source_ids_by_claim={"CLM-TEST": {"SRC-A"}, "CLM-OTHER": {"SRC-B"}},
    )
    assert record["conflicting_evidence"]
    assert record["status"] == "UNRESOLVED"


def test_numeric_variety_inside_one_source_is_not_a_disagreement():
    other = claim(
        "Another modality has a different reported sensitivity.",
        ["SRC-A"],
        claim_id="CLM-OTHER",
        quantities=[{"quantity_id": "SENSITIVITY", "value": 94, "unit": "%"}],
    )
    record = adjudicate_claim(
        claim(
            "One modality has a reported sensitivity.",
            ["SRC-A"],
            quantities=[{"quantity_id": "SENSITIVITY", "value": 90, "unit": "%"}],
        ),
        sources={"SRC-A": NATIONAL},
        authority_registry=registry(),
        constants=constants(),
        profile_risk_classes={},
        sibling_claims=[other],
        source_ids_by_claim={"CLM-TEST": {"SRC-A"}, "CLM-OTHER": {"SRC-A"}},
    )
    assert record["conflicting_evidence"] == []


def test_transcription_status_and_fact_status_are_separate_readings():
    record = adjudicate_claim(
        claim("Wheeze begins before the age of 12 months.", ["SRC-A"]),
        sources={"SRC-A": NATIONAL},
        authority_registry=registry(),
        constants=constants(),
        profile_risk_classes={},
    )
    assert record["transcription_status"] == "VERIFIED_COMPLETE"
    assert record["fact_status"] == "PRIMARY_AUTHORITY"


def test_every_asserted_numeral_is_enumerated_not_only_derived_ones():
    assertions = enumerate_numeric_assertions(
        "Temperature is 38.4 degrees and heart rate is 104 beats/min.", "STEM"
    )
    assert [row["value"] for row in assertions] == ["38.4", "104"]
    with pytest.raises(CriticalFactError):
        enumerate_numeric_assertions("anything", "NOWHERE")


def test_an_unadmitted_reference_constant_is_refused():
    with pytest.raises(CriticalFactError):
        detect_fact_classes("")
