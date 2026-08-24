import copy
from pathlib import Path

import pytest

from qbank.errors import SchemaValidationError
from qbank.jsonio import read_json
from qbank.schema import validate_instance


REPO_ROOT = Path(__file__).resolve().parents[1]
VALID_FIXTURES = REPO_ROOT / "tests" / "fixtures" / "valid"


@pytest.fixture
def repo_root():
    return REPO_ROOT


@pytest.fixture
def valid_question():
    return copy.deepcopy(read_json(VALID_FIXTURES / "question.json"))


@pytest.fixture
def valid_blind():
    return copy.deepcopy(read_json(VALID_FIXTURES / "blind-packet.json"))


@pytest.mark.parametrize(
    ("schema_name", "fixture"),
    [
        ("project", "project.json"),
        ("manifest", "manifest.json"),
        ("job", "job.json"),
        ("reference", "reference.json"),
        ("reference-registry", "reference-registry.json"),
        ("question", "question.json"),
        ("blind-packet", "blind-packet.json"),
        ("blind-verification", "blind-verification.json"),
        ("rationale-verification", "rationale-verification.json"),
        ("progress", "progress.json"),
        ("production-manifest", "production-manifest.json"),
    ],
)
def test_valid_fixture(schema_name, fixture, repo_root):
    validate_instance(repo_root, schema_name, read_json(VALID_FIXTURES / fixture))


def test_question_requires_exactly_five_options(valid_question, repo_root):
    valid_question["question"]["options"].pop()

    with pytest.raises(SchemaValidationError, match=r"question\.options"):
        validate_instance(repo_root, "question", valid_question)


@pytest.mark.parametrize("replacement", ["Z", "a", ""])
def test_question_rejects_answer_outside_option_keys(
    valid_question, repo_root, replacement
):
    valid_question["correct_answer"] = replacement

    with pytest.raises(SchemaValidationError, match="correct_answer"):
        validate_instance(repo_root, "question", valid_question)


def test_question_requires_options_to_be_ordered_a_through_e(valid_question, repo_root):
    valid_question["question"]["options"][0]["id"] = "B"

    with pytest.raises(SchemaValidationError, match=r"question\.options\[0\]\.id"):
        validate_instance(repo_root, "question", valid_question)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda q: q["explanation"].update(clinical_reasoning=""),
        lambda q: q["explanation"].update(answer_summary=""),
        lambda q: q["explanation"].update(why_correct=""),
        lambda q: q["explanation"].update(key_clues=[]),
        lambda q: q["explanation"].update(clinical_pearl=""),
    ],
)
def test_question_rejects_missing_required_rationale_content(
    valid_question, repo_root, mutation
):
    mutation(valid_question)

    with pytest.raises(SchemaValidationError, match="explanation"):
        validate_instance(repo_root, "question", valid_question)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda q: q["explanation"].update(distractor_rationales={}),
        lambda q: q["explanation"]["distractor_rationales"].pop("B"),
        lambda q: q["explanation"]["distractor_rationales"].update(A="not allowed"),
        lambda q: q["explanation"]["distractor_rationales"].update(B=""),
    ],
)
def test_question_requires_one_rationale_for_each_distractor_only(
    valid_question, repo_root, mutation
):
    mutation(valid_question)

    with pytest.raises(SchemaValidationError, match="distractor_rationales"):
        validate_instance(repo_root, "question", valid_question)


def test_distractor_keys_follow_a_changed_correct_answer(valid_question, repo_root):
    valid_question["correct_answer"] = "C"
    valid_question["explanation"]["distractor_rationales"] = {
        "A": "Synthetic rationale A.",
        "B": "Synthetic rationale B.",
        "D": "Synthetic rationale D.",
        "E": "Synthetic rationale E.",
    }

    validate_instance(repo_root, "question", valid_question)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda q: q.update(references=[]),
        lambda q: q.update(references=["not-a-reference-id"]),
        lambda q: q.update(references=["REF-SYN-001", "REF-SYN-001"]),
    ],
)
def test_question_requires_canonical_references(valid_question, repo_root, mutation):
    mutation(valid_question)

    with pytest.raises(SchemaValidationError, match="references"):
        validate_instance(repo_root, "question", valid_question)


@pytest.mark.parametrize(
    "field",
    ["edition", "chapter", "chapter_code", "section", "subsection", "tn_pages", "pdf_pages"],
)
def test_question_requires_complete_toronto_notes_mapping(
    valid_question, repo_root, field
):
    valid_question["toronto_notes"].pop(field)

    with pytest.raises(SchemaValidationError, match="toronto_notes"):
        validate_instance(repo_root, "question", valid_question)


@pytest.mark.parametrize("field", ["objectives", "physician_activity", "dimension_of_care"])
def test_question_requires_complete_mcc_mapping(valid_question, repo_root, field):
    valid_question["mcc"].pop(field)

    with pytest.raises(SchemaValidationError, match="mcc"):
        validate_instance(repo_root, "question", valid_question)


def test_question_rejects_empty_mcc_objectives(valid_question, repo_root):
    valid_question["mcc"]["objectives"] = []

    with pytest.raises(SchemaValidationError, match=r"mcc\.objectives"):
        validate_instance(repo_root, "question", valid_question)


@pytest.mark.parametrize(
    ("path", "value"),
    [
        ((), {"unexpected": True}),
        (("question",), {"generator_notes": "private"}),
        (("toronto_notes",), {"copied_source_text": "private"}),
        (("verification",), {"reviewer_guess": "private"}),
    ],
)
def test_question_rejects_unknown_fields(valid_question, repo_root, path, value):
    target = valid_question
    for part in path:
        target = target[part]
    target.update(value)

    with pytest.raises(SchemaValidationError):
        validate_instance(repo_root, "question", valid_question)


@pytest.mark.parametrize(
    ("path", "field", "value"),
    [
        ((), "correct_answer", "A"),
        ((), "explanation", {"clinical_reasoning": "private"}),
        ((), "verification", {"key_match": True}),
        (("mcc",), "generator_notes", "private"),
        (("toronto_notes",), "distractor_rationales", {"B": "private"}),
    ],
)
def test_blind_packet_recursively_forbids_answer_and_generator_fields(
    valid_blind, repo_root, path, field, value
):
    target = valid_blind
    for part in path:
        target = target[part]
    target[field] = value

    with pytest.raises(SchemaValidationError):
        validate_instance(repo_root, "blind-packet", valid_blind)


@pytest.mark.parametrize(
    ("schema_name", "field", "replacement"),
    [
        ("question", "status", "candidate"),
        ("job", "status", "pending"),
        ("job", "job_type", "CHAT"),
    ],
)
def test_status_and_job_type_enums_are_canonical(
    schema_name, field, replacement, repo_root
):
    instance = copy.deepcopy(read_json(VALID_FIXTURES / f"{schema_name}.json"))
    instance[field] = replacement

    with pytest.raises(SchemaValidationError, match=field):
        validate_instance(repo_root, schema_name, instance)


def test_job_failure_class_uses_fixed_enum(repo_root):
    instance = copy.deepcopy(read_json(VALID_FIXTURES / "job.json"))
    instance["status"] = "FAILED"
    instance["failure"] = {"class": "UNKNOWN", "message": "Synthetic failure."}

    with pytest.raises(SchemaValidationError, match=r"failure\.class"):
        validate_instance(repo_root, "job", instance)


def test_reference_requires_claim_level_support(repo_root):
    reference = copy.deepcopy(read_json(VALID_FIXTURES / "reference.json"))
    reference["supports"] = []

    with pytest.raises(SchemaValidationError, match="supports"):
        validate_instance(repo_root, "reference", reference)


def test_validation_errors_are_sorted_and_have_json_paths(valid_question, repo_root):
    valid_question["question"]["options"] = []
    valid_question["mcc"]["objectives"] = []

    with pytest.raises(SchemaValidationError) as caught:
        validate_instance(repo_root, "question", valid_question)

    message = str(caught.value)
    assert "mcc.objectives" in message
    assert "question.options" in message
    assert message.index("mcc.objectives") < message.index("question.options")
