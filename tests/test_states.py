import itertools

import pytest

from qbank.errors import TransitionError
from qbank.states import STATUSES, validate_transition


ALLOWED = {
    ("DRAFT", "CANDIDATE"),
    ("CANDIDATE", "STRUCTURE_PASS"),
    ("CANDIDATE", "QUARANTINE"),
    ("STRUCTURE_PASS", "BLIND_PASS"),
    ("STRUCTURE_PASS", "QUARANTINE"),
    ("BLIND_PASS", "MEDICAL_PASS"),
    ("BLIND_PASS", "QUARANTINE"),
    ("MEDICAL_PASS", "QA_PASS"),
    ("MEDICAL_PASS", "QUARANTINE"),
    ("QUARANTINE", "REVISED"),
    ("QUARANTINE", "REJECTED"),
    ("REVISED", "CANDIDATE"),
    ("MEDICAL_PASS", "HUMAN_REVIEWED"),
    ("QA_PASS", "HUMAN_REVIEWED"),
    ("HUMAN_REVIEWED", "PUBLISHED"),
    ("QA_PASS", "PUBLISHED"),
    ("PUBLISHED", "RETIRED"),
}

DISALLOWED = sorted(set(itertools.product(STATUSES, repeat=2)) - ALLOWED)

REVIEW = {
    "reviewer_name": "Dr. Synthetic Reviewer",
    "credentials": "MD",
    "reviewed_at": "2026-08-24T12:00:00Z",
    "scope": "Item-specific clinical review",
}


@pytest.mark.parametrize("transition", sorted(ALLOWED))
def test_allowed_transition(transition):
    metadata = REVIEW if transition[1] == "HUMAN_REVIEWED" else None
    validate_transition(*transition, human_review=metadata)


@pytest.mark.parametrize("transition", DISALLOWED)
def test_every_unlisted_transition_is_rejected(transition):
    with pytest.raises(TransitionError):
        validate_transition(*transition)


@pytest.mark.parametrize("current", ["MEDICAL_PASS", "QA_PASS"])
@pytest.mark.parametrize("metadata", [None, {}, {"reviewer_name": "Reviewer"}, {
    **REVIEW,
    "scope": "  ",
}])
def test_human_review_requires_nonblank_metadata(current, metadata):
    with pytest.raises(TransitionError):
        validate_transition(current, "HUMAN_REVIEWED", human_review=metadata)


@pytest.mark.parametrize("current", ["DRAFT", "CANDIDATE", "STRUCTURE_PASS"])
def test_human_review_is_only_reachable_from_medical_or_qa_pass(current):
    with pytest.raises(TransitionError):
        validate_transition(current, "HUMAN_REVIEWED", human_review=REVIEW)


@pytest.mark.parametrize("field", sorted(REVIEW))
def test_human_review_requires_each_metadata_field(field):
    metadata = dict(REVIEW)
    metadata[field] = ""
    with pytest.raises(TransitionError):
        validate_transition("MEDICAL_PASS", "HUMAN_REVIEWED", human_review=metadata)


@pytest.mark.parametrize("value", ["draft", "", "UNKNOWN", None])
def test_statuses_must_be_known_uppercase_strings(value):
    with pytest.raises(TransitionError):
        validate_transition(value, "CANDIDATE")
