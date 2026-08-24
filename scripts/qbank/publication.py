"""Shared publication evidence and public-question projection contracts."""

from __future__ import annotations

from copy import deepcopy
from numbers import Real

from .errors import SchemaValidationError


MINIMUM_PUBLICATION_CONFIDENCE = 0.85
PUBLICATION_ELIGIBLE_STATUSES = frozenset(
    {"QA_PASS", "HUMAN_REVIEWED", "PUBLISHED"}
)
PUBLICATION_EVIDENCE_STATUSES = PUBLICATION_ELIGIBLE_STATUSES | {"RETIRED"}
FINAL_STATUS_BY_STATUS = {
    "DRAFT": "PENDING",
    "CANDIDATE": "PENDING",
    "STRUCTURE_PASS": "PENDING",
    "BLIND_PASS": "BLIND_PASS",
    "MEDICAL_PASS": "MEDICAL_PASS",
    "QA_PASS": "QA_PASS",
    "PUBLISHED": "PUBLISHED",
    "QUARANTINE": "QUARANTINE",
    "REVISED": "PENDING",
    "REJECTED": "REJECTED",
    "HUMAN_REVIEWED": "HUMAN_REVIEWED",
    "RETIRED": "RETIRED",
}


def question_semantic_errors(
    instance: object,
) -> list[tuple[tuple[str, ...], str]]:
    """Return stable semantic errors not expressible in portable JSON Schema."""
    if not isinstance(instance, dict):
        return []
    status = instance.get("status")
    verification = instance.get("verification")
    if not isinstance(status, str) or not isinstance(verification, dict):
        return []

    errors: list[tuple[tuple[str, ...], str]] = []
    expected_final = FINAL_STATUS_BY_STATUS.get(status)
    if expected_final is not None and verification.get("final_status") != expected_final:
        errors.append(
            (
                ("verification", "final_status"),
                f"must equal {expected_final!r} when status is {status!r}",
            )
        )

    if status not in PUBLICATION_EVIDENCE_STATUSES:
        return errors

    prefix = (
        "retired publication history requires"
        if status == "RETIRED"
        else "publication eligibility requires"
    )
    if verification.get("source_packet_complete") is not True:
        errors.append(
            (("verification", "source_packet_complete"), f"{prefix} true")
        )
    if verification.get("blind_verifier_answer") != instance.get("correct_answer"):
        errors.append(
            (
                ("verification", "blind_verifier_answer"),
                f"{prefix} an answer matching correct_answer",
            )
        )
    confidence = verification.get("blind_verifier_confidence")
    if (
        isinstance(confidence, bool)
        or not isinstance(confidence, Real)
        or confidence < MINIMUM_PUBLICATION_CONFIDENCE
    ):
        errors.append(
            (
                ("verification", "blind_verifier_confidence"),
                f"{prefix} confidence >= {MINIMUM_PUBLICATION_CONFIDENCE}",
            )
        )
    for field, expected in (
        ("key_match", True),
        ("ambiguity", False),
        ("reference_check", True),
        ("guideline_check", True),
        ("duplicate_check", True),
    ):
        if verification.get(field) is not expected:
            errors.append(
                (("verification", field), f"{prefix} {field}={expected!r}")
            )
    return errors


def validate_publication_eligibility(question: object) -> None:
    """Raise unless *question* contains all substantive publication evidence."""
    status = question.get("status") if isinstance(question, dict) else None
    if status not in PUBLICATION_ELIGIBLE_STATUSES:
        raise SchemaValidationError(
            f"publication eligibility requires status in "
            f"{sorted(PUBLICATION_ELIGIBLE_STATUSES)!r}; got {status!r}"
        )
    errors = question_semantic_errors(question)
    if errors:
        details = "; ".join(f"{'.'.join(path)}: {message}" for path, message in errors)
        raise SchemaValidationError(f"publication eligibility failed: {details}")


def public_question_projection(question: dict) -> dict:
    """Build the public allowlist projection of one validated stored question."""
    toronto_notes = question["toronto_notes"]
    return {
        "id": deepcopy(question["id"]),
        "status": deepcopy(question["status"]),
        "discipline": deepcopy(question["discipline"]),
        "chapter": deepcopy(question["chapter"]),
        "subtopic": deepcopy(question["subtopic"]),
        "toronto_notes": {
            key: deepcopy(toronto_notes[key])
            for key in (
                "edition",
                "chapter",
                "chapter_code",
                "section",
                "subsection",
                "tn_pages",
            )
        },
        "mcc": deepcopy(question["mcc"]),
        "difficulty": deepcopy(question["difficulty"]),
        "question": deepcopy(question["question"]),
        "correct_answer": deepcopy(question["correct_answer"]),
        "explanation": deepcopy(question["explanation"]),
        "references": deepcopy(question["references"]),
        "content_version": deepcopy(question["content_version"]),
    }
