import copy
from pathlib import Path

import pytest

from qbank.blind import BlindDecision, build_blind_packet, evaluate_blind_result
from qbank.errors import SchemaValidationError
from qbank.jsonio import read_json
from qbank.schema import validate_instance


REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURES = REPO_ROOT / "tests" / "fixtures" / "valid"
FORBIDDEN = {
    "correct_answer",
    "explanation",
    "rationale",
    "rationales",
    "distractor_rationales",
    "generator_notes",
    "generator_explanation",
    "generator_confidence",
    "confidence",
    "verification",
}


@pytest.fixture
def valid_question():
    return copy.deepcopy(read_json(FIXTURES / "question.json"))


@pytest.fixture
def valid_blind_result():
    return copy.deepcopy(read_json(FIXTURES / "blind-verification.json"))


def walk_keys(value):
    if isinstance(value, dict):
        for key, child in value.items():
            yield key
            yield from walk_keys(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk_keys(child)


def test_blind_packet_is_a_schema_valid_allowlist_projection(valid_question):
    packet = build_blind_packet(valid_question)

    assert packet == {
        "question_id": valid_question["id"],
        "stem": valid_question["question"]["stem"],
        "lead_in": valid_question["question"]["lead_in"],
        "options": valid_question["question"]["options"],
        "mcc": valid_question["mcc"],
        "toronto_notes": valid_question["toronto_notes"],
        "references": valid_question["references"],
    }
    validate_instance(REPO_ROOT, "blind-packet", packet)


def test_blind_packet_recursively_excludes_generator_fields(valid_question):
    valid_question["generator_notes"] = {
        "explanation": {"distractor_rationales": {"B": "private"}},
        "confidence": 0.99,
    }
    valid_question["verification"]["generator_confidence"] = 0.99

    packet = build_blind_packet(valid_question)

    assert FORBIDDEN.isdisjoint(set(walk_keys(packet)))


def test_blind_packet_is_independent_from_candidate_mutations(valid_question):
    packet = build_blind_packet(valid_question)
    valid_question["question"]["options"][0]["text"] = "altered synthetic text"
    valid_question["mcc"]["objectives"].append("SYN-OBJ-EXTRA")

    assert packet["options"][0]["text"] == "Synthetic option alpha"
    assert packet["mcc"]["objectives"] == ["SYN-OBJ-001"]


def test_blind_packet_validation_rejects_invalid_projected_data(valid_question):
    valid_question["references"] = []

    with pytest.raises(SchemaValidationError, match="blind-packet validation failed"):
        build_blind_packet(valid_question)


def test_matching_complete_blind_result_passes(valid_question, valid_blind_result):
    decision = evaluate_blind_result(valid_question, valid_blind_result)

    assert decision == BlindDecision(status="BLIND_PASS", reason="BLIND_PASS")


def test_mismatched_key_quarantines_without_autocorrection(
    valid_question, valid_blind_result
):
    valid_blind_result["independent_answer"] = "B"

    decision = evaluate_blind_result(valid_question, valid_blind_result)

    assert decision.status == "QUARANTINE"
    assert decision.reason == "BLIND_KEY_MISMATCH"
    assert valid_question["correct_answer"] == "A"


@pytest.mark.parametrize(
    ("field", "value", "reason"),
    [
        ("confidence", 0.84, "BLIND_LOW_CONFIDENCE"),
        ("single_best_answer", False, "BLIND_NOT_SINGLE_BEST_ANSWER"),
        ("other_defensible_options", ["B"], "BLIND_OTHER_DEFENSIBLE_OPTIONS"),
        ("stem_sufficient", False, "BLIND_STEM_INSUFFICIENT"),
        ("guideline_support", False, "BLIND_GUIDELINE_UNSUPPORTED"),
        ("uncertainty_concern", "Synthetic ambiguity", "BLIND_UNCERTAINTY_CONCERN"),
        ("recommendation", "QUARANTINE", "BLIND_RECOMMENDATION_NOT_PASS"),
    ],
)
def test_each_nonmatching_blind_gate_quarantines(
    valid_question, valid_blind_result, field, value, reason
):
    valid_blind_result[field] = value

    decision = evaluate_blind_result(valid_question, valid_blind_result)

    assert decision == BlindDecision(status="QUARANTINE", reason=reason)


def test_lower_threshold_cannot_admit_less_than_default_floor(
    valid_question, valid_blind_result
):
    valid_blind_result["confidence"] = 0.84

    decision = evaluate_blind_result(valid_question, valid_blind_result, threshold=0.84)

    assert decision == BlindDecision(
        status="QUARANTINE", reason="BLIND_LOW_CONFIDENCE"
    )


def test_stricter_threshold_can_quarantine_an_otherwise_passing_result(
    valid_question, valid_blind_result
):
    valid_blind_result["confidence"] = 0.90

    decision = evaluate_blind_result(valid_question, valid_blind_result, threshold=0.91)

    assert decision == BlindDecision(
        status="QUARANTINE", reason="BLIND_LOW_CONFIDENCE"
    )


@pytest.mark.parametrize("threshold", ["0.85", None, True, -0.01, 1.01])
def test_invalid_confidence_threshold_is_rejected(
    valid_question, valid_blind_result, threshold
):
    with pytest.raises(ValueError, match="threshold"):
        evaluate_blind_result(valid_question, valid_blind_result, threshold=threshold)


def test_result_for_another_question_quarantines(valid_question, valid_blind_result):
    valid_blind_result["question_id"] = "SYN-UNIT-002"

    decision = evaluate_blind_result(valid_question, valid_blind_result)

    assert decision == BlindDecision(
        status="QUARANTINE", reason="BLIND_QUESTION_ID_MISMATCH"
    )
