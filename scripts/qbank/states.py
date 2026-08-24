"""Fail-closed lifecycle state transitions for canonical questions."""

from collections.abc import Mapping

from .errors import TransitionError


STATUSES = (
    "DRAFT",
    "CANDIDATE",
    "STRUCTURE_PASS",
    "BLIND_PASS",
    "MEDICAL_PASS",
    "QA_PASS",
    "PUBLISHED",
    "QUARANTINE",
    "REVISED",
    "REJECTED",
    "HUMAN_REVIEWED",
    "RETIRED",
)

_ADJACENCY = {
    "DRAFT": frozenset({"CANDIDATE"}),
    "CANDIDATE": frozenset({"STRUCTURE_PASS", "QUARANTINE"}),
    "STRUCTURE_PASS": frozenset({"BLIND_PASS", "QUARANTINE"}),
    "BLIND_PASS": frozenset({"MEDICAL_PASS", "QUARANTINE"}),
    "MEDICAL_PASS": frozenset({"QA_PASS", "QUARANTINE", "HUMAN_REVIEWED"}),
    "QA_PASS": frozenset({"PUBLISHED", "HUMAN_REVIEWED"}),
    "QUARANTINE": frozenset({"REVISED", "REJECTED"}),
    "REVISED": frozenset({"CANDIDATE"}),
    "HUMAN_REVIEWED": frozenset({"PUBLISHED"}),
}

_REVIEW_FIELDS = ("reviewer_name", "credentials", "reviewed_at", "scope")


def _status(value: object, label: str) -> str:
    if not isinstance(value, str) or value not in STATUSES:
        raise TransitionError(f"unknown {label} status: {value!r}")
    return value


def _has_review_metadata(value: object) -> bool:
    if not isinstance(value, Mapping):
        return False
    return all(
        isinstance(value.get(field), str) and value[field].strip()
        for field in _REVIEW_FIELDS
    )


def validate_transition(
    current: str, target: str, *, human_review: dict | None = None
) -> None:
    """Raise :class:`TransitionError` unless a lifecycle transition is allowed.

    The status graph is deliberately explicit.  In particular, statuses with no
    adjacency entry (including ``PUBLISHED``, ``REJECTED``, and ``RETIRED``)
    have no outgoing transitions.
    """
    current = _status(current, "current")
    target = _status(target, "target")

    if target == "HUMAN_REVIEWED" and not _has_review_metadata(human_review):
        raise TransitionError(
            "HUMAN_REVIEWED requires non-empty reviewer_name, credentials, "
            "reviewed_at, and scope"
        )

    if target not in _ADJACENCY.get(current, frozenset()):
        raise TransitionError(f"transition not allowed: {current} -> {target}")
