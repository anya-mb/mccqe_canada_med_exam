import copy
from pathlib import Path

import pytest

from qbank.jsonio import read_json
from qbank.risk import classify_risk


FIXTURES = Path(__file__).resolve().parent / "fixtures" / "valid"


@pytest.fixture
def valid_question():
    return copy.deepcopy(read_json(FIXTURES / "question.json"))


@pytest.mark.parametrize(
    ("text", "flag"),
    [
        ("What dose should be administered?", "DOSE"),
        ("She is 24 weeks pregnant.", "PREGNANCY"),
        ("Which screening interval is recommended?", "SCREENING"),
        (
            "This condition must be reported to public health.",
            "PUBLIC_HEALTH_REPORTING",
        ),
    ],
)
def test_high_risk_text_is_flagged(valid_question, text, flag):
    valid_question["question"]["stem"] = text

    assert flag in classify_risk(valid_question)


def test_structured_risk_fields_are_honoured_and_results_are_sorted(valid_question):
    valid_question["risk_flags"] = ["LEGAL", "DOSE"]
    valid_question["screening_interval"] = "every 3 years"

    assert classify_risk(valid_question) == ["DOSE", "SCREENING", "LEGAL"]


def test_numerical_threshold_requires_a_threshold_marker(valid_question):
    valid_question["question"]["stem"] = "The patient is 24 years old."

    assert "NUMERICAL_THRESHOLD" not in classify_risk(valid_question)


@pytest.mark.parametrize(
    "text",
    [
        "Public health programs improve population outcomes.",
        "The legal team reviewed the hospital contract.",
        "The emergency department is busy today.",
    ],
)
def test_generic_risk_words_do_not_trigger_a_high_risk_flag(valid_question, text):
    valid_question["question"]["stem"] = text

    assert classify_risk(valid_question) == []


def test_all_fixed_categories_are_detected_and_returned_in_enum_order(valid_question):
    valid_question["question"]["stem"] = (
        "For a child in the first trimester, give a 5 mg dose of vaccine. "
        "At a blood pressure threshold of 140 mm Hg, use screening for patients "
        "taking warfarin. Obtain informed consent, report this notifiable disease "
        "to public health, and start CPR for cardiac arrest."
    )

    assert classify_risk(valid_question) == [
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
    ]
