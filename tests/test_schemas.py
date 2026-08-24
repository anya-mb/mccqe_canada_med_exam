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
        ("public-question", "public-question.json"),
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


def test_pending_job_is_valid_without_timestamps(repo_root):
    instance = copy.deepcopy(read_json(VALID_FIXTURES / "job.json"))
    instance.pop("timestamps", None)

    validate_instance(repo_root, "job", instance)


def test_pending_job_rejects_timestamps(repo_root):
    """Catches stale execution timestamps being retained on a pending claim."""
    instance = copy.deepcopy(read_json(VALID_FIXTURES / "job.json"))
    instance["timestamps"] = {
        "created_at": "2026-08-23T12:00:00Z",
        "updated_at": "2026-08-23T12:00:00Z",
        "started_at": None,
        "completed_at": None,
    }

    with pytest.raises(SchemaValidationError, match="timestamps"):
        validate_instance(repo_root, "job", instance)


def test_job_attempt_cannot_exceed_max_attempts(repo_root):
    """Catches exhausted jobs that remain schema-valid and retryable."""
    instance = copy.deepcopy(read_json(VALID_FIXTURES / "job.json"))
    instance.pop("timestamps", None)
    instance["attempt"] = instance["max_attempts"] + 1

    with pytest.raises(SchemaValidationError, match="attempt.*max_attempts"):
        validate_instance(repo_root, "job", instance)


@pytest.mark.parametrize("status", ["RUNNING", "COMPLETED", "FAILED"])
def test_non_pending_jobs_require_timestamps(repo_root, status):
    instance = copy.deepcopy(read_json(VALID_FIXTURES / "job.json"))
    instance["status"] = status
    if status == "FAILED":
        instance["failure"] = {
            "class": "SOURCE_FAILURE",
            "message": "Synthetic source failure.",
        }

    with pytest.raises(SchemaValidationError, match="timestamps"):
        validate_instance(repo_root, "job", instance)


@pytest.mark.parametrize(
    ("status", "field"),
    [
        ("RUNNING", "started_at"),
        ("COMPLETED", "started_at"),
        ("COMPLETED", "completed_at"),
    ],
)
def test_active_and_completed_jobs_require_state_timestamp(repo_root, status, field):
    instance = copy.deepcopy(read_json(VALID_FIXTURES / "job.json"))
    instance["status"] = status
    instance["timestamps"] = {
        "created_at": "2026-08-23T12:00:00Z",
        "updated_at": "2026-08-23T12:01:00Z",
        "started_at": "2026-08-23T12:01:00Z",
        "completed_at": None,
    }
    if status == "COMPLETED":
        instance["timestamps"]["completed_at"] = "2026-08-23T12:02:00Z"
    instance["timestamps"][field] = None

    with pytest.raises(SchemaValidationError, match=field):
        validate_instance(repo_root, "job", instance)


@pytest.mark.parametrize("status", ["RUNNING", "FAILED"])
def test_unfinished_jobs_reject_completed_timestamp(repo_root, status):
    instance = copy.deepcopy(read_json(VALID_FIXTURES / "job.json"))
    instance["status"] = status
    instance["timestamps"] = {
        "created_at": "2026-08-23T12:00:00Z",
        "updated_at": "2026-08-23T12:01:00Z",
        "started_at": "2026-08-23T12:01:00Z",
        "completed_at": "2026-08-23T12:02:00Z",
    }
    if status == "FAILED":
        instance["failure"] = {
            "class": "SOURCE_FAILURE",
            "message": "Synthetic source failure.",
        }

    with pytest.raises(SchemaValidationError, match="completed_at"):
        validate_instance(repo_root, "job", instance)


def test_reference_requires_claim_level_support(repo_root):
    reference = copy.deepcopy(read_json(VALID_FIXTURES / "reference.json"))
    reference["supports"] = []

    with pytest.raises(SchemaValidationError, match="supports"):
        validate_instance(repo_root, "reference", reference)


def test_reference_registry_rejects_distinct_records_with_the_same_id(repo_root):
    registry = copy.deepcopy(read_json(VALID_FIXTURES / "reference-registry.json"))
    duplicate_id = copy.deepcopy(registry["references"][0])
    duplicate_id["title"] = "Different Synthetic Practice Standard"
    duplicate_id["url"] = "https://example.invalid/different-synthetic-standard"
    registry["references"].append(duplicate_id)

    with pytest.raises(
        SchemaValidationError, match=r"references\[1\]\.reference_id"
    ):
        validate_instance(repo_root, "reference-registry", registry)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("clinical_reasoning", "   \t"),
        (
            "distractor_rationales",
            {
                "B": " \n",
                "C": "Synthetic rationale C.",
                "D": "Synthetic rationale D.",
                "E": "Synthetic rationale E.",
            },
        ),
    ],
)
def test_question_rejects_whitespace_only_required_rationales(
    valid_question, repo_root, field, value
):
    valid_question["explanation"][field] = value

    with pytest.raises(SchemaValidationError, match="explanation"):
        validate_instance(repo_root, "question", valid_question)


@pytest.mark.parametrize(
    ("path", "field"),
    [
        ((), "title"),
        ((), "organization"),
        (("supports", 0), "claim"),
        (("supports", 0), "locator"),
    ],
)
def test_reference_rejects_whitespace_only_required_text(repo_root, path, field):
    reference = copy.deepcopy(read_json(VALID_FIXTURES / "reference.json"))
    target = reference
    for part in path:
        target = target[part]
    target[field] = " \t\n"

    with pytest.raises(SchemaValidationError, match=field):
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


def test_relabelled_candidate_is_not_publication_eligible(repo_root):
    """Catches admission based only on status and verification.final_status labels."""
    candidate = read_json(
        REPO_ROOT / "tests/fixtures/adversarial/relabeled-candidate.json"
    )

    with pytest.raises(SchemaValidationError, match="publication eligibility"):
        validate_instance(repo_root, "question", candidate)


def test_complete_human_review_metadata_is_part_of_the_stored_question_schema(
    valid_question, repo_root
):
    """Catches consumers that strip reviewer metadata before validating storage."""
    valid_question["status"] = "HUMAN_REVIEWED"
    valid_question["verification"].update(
        blind_verifier_answer="A",
        blind_verifier_confidence=0.95,
        key_match=True,
        ambiguity=False,
        reference_check=True,
        guideline_check=True,
        duplicate_check=True,
        final_status="HUMAN_REVIEWED",
    )
    valid_question["human_review"] = {
        "reviewer_name": "Synthetic Reviewer",
        "credentials": "Synthetic Credential",
        "reviewed_at": "2026-08-24T11:00:00Z",
        "scope": "Full synthetic item review",
        "reviewer_id": "SYNTHETIC-REVIEWER-001",
    }

    validate_instance(repo_root, "question", valid_question)


def test_human_reviewed_status_requires_reviewer_metadata(valid_question, repo_root):
    """Catches HUMAN_REVIEWED labels without item-specific review provenance."""
    valid_question["status"] = "HUMAN_REVIEWED"
    valid_question["verification"].update(
        blind_verifier_answer="A",
        blind_verifier_confidence=0.95,
        key_match=True,
        ambiguity=False,
        reference_check=True,
        guideline_check=True,
        duplicate_check=True,
        final_status="HUMAN_REVIEWED",
    )

    with pytest.raises(SchemaValidationError, match="human_review"):
        validate_instance(repo_root, "question", valid_question)


@pytest.mark.parametrize(
    ("status", "final_status"),
    [("PUBLISHED", "PUBLISHED"), ("RETIRED", "RETIRED")],
)
def test_published_and_retired_questions_have_persistable_final_statuses(
    valid_question, repo_root, status, final_status
):
    """Catches lifecycle states that the canonical schema cannot persist."""
    valid_question["status"] = status
    valid_question["verification"]["final_status"] = final_status
    valid_question["verification"].update(
        blind_verifier_answer="A",
        blind_verifier_confidence=0.95,
        key_match=True,
        ambiguity=False,
        reference_check=True,
        guideline_check=True,
        duplicate_check=True,
    )

    validate_instance(repo_root, "question", valid_question)


def test_retired_question_retains_human_review_provenance(valid_question, repo_root):
    """Catches retirement making a human-reviewed publication unpersistable."""
    valid_question["status"] = "RETIRED"
    valid_question["verification"].update(
        blind_verifier_answer="A",
        blind_verifier_confidence=0.95,
        key_match=True,
        ambiguity=False,
        reference_check=True,
        guideline_check=True,
        duplicate_check=True,
        final_status="RETIRED",
    )
    valid_question["human_review"] = {
        "reviewer_name": "Synthetic Reviewer",
        "credentials": "Synthetic Credential",
        "reviewed_at": "2026-08-24T11:00:00Z",
        "scope": "Full synthetic item review",
    }

    validate_instance(repo_root, "question", valid_question)


def test_relabelled_candidate_cannot_claim_retired_publication_history(
    valid_question, repo_root
):
    """Catches a candidate relabelled as RETIRED without prior publication evidence."""
    valid_question["status"] = "RETIRED"
    valid_question["verification"]["final_status"] = "RETIRED"

    with pytest.raises(SchemaValidationError, match="retired publication history"):
        validate_instance(repo_root, "question", valid_question)


@pytest.mark.parametrize(
    ("path", "field", "value"),
    [
        ((), "verification", {"final_status": "QA_PASS"}),
        ((), "human_review", {"reviewer_name": "Private Reviewer"}),
        (("toronto_notes",), "pdf_pages", "10-11"),
        ((), "toronto_notes_gap_fill", False),
        ((), "guideline_updated_since_tn2025", False),
    ],
)
def test_public_question_schema_rejects_internal_fields(
    repo_root, path, field, value
):
    """Catches public schemas that accept stored QA or source-only internals."""
    public_question = copy.deepcopy(read_json(VALID_FIXTURES / "public-question.json"))
    target = public_question
    for part in path:
        target = target[part]
    target[field] = value

    with pytest.raises(SchemaValidationError, match=field):
        validate_instance(repo_root, "public-question", public_question)


@pytest.mark.parametrize(
    "payload",
    [
        '{"type": "object",',
        '{"type": "object", "type": "array"}',
    ],
)
def test_malformed_schema_is_normalized_to_schema_validation_error(
    tmp_path, payload
):
    """Catches unreadable schema catalogs leaking generic QbankError failures."""
    schema = tmp_path / "schemas/synthetic.schema.json"
    schema.parent.mkdir(parents=True)
    schema.write_text(payload, encoding="utf-8")

    with pytest.raises(SchemaValidationError, match="invalid schema synthetic"):
        validate_instance(tmp_path, "synthetic", {})
