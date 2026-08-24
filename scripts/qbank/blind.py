"""Blind-verification packet isolation and fail-closed evaluation."""

from copy import deepcopy
from dataclasses import dataclass
from numbers import Real
from pathlib import Path
from typing import Literal

from .schema import validate_instance


_REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
_MINIMUM_CONFIDENCE = 0.85


@dataclass(frozen=True)
class BlindDecision:
    """The non-mutating outcome of an independent blind verification."""

    status: Literal["BLIND_PASS", "QUARANTINE"]
    reason: str


def build_blind_packet(candidate: dict) -> dict:
    """Return the schema-validated, answer-key-free projection of *candidate*.

    Every value is copied from a fixed set of permitted candidate paths.  This
    intentionally avoids copying the candidate first and deleting private data:
    unknown or nested generator fields can never enter the blind packet.
    """
    packet = {
        "question_id": deepcopy(candidate["id"]),
        "stem": deepcopy(candidate["question"]["stem"]),
        "lead_in": deepcopy(candidate["question"]["lead_in"]),
        "options": deepcopy(candidate["question"]["options"]),
        "mcc": deepcopy(candidate["mcc"]),
        "toronto_notes": deepcopy(candidate["toronto_notes"]),
        "references": deepcopy(candidate["references"]),
    }
    validate_instance(_REPOSITORY_ROOT, "blind-packet", packet)
    return packet


def _quarantine(reason: str) -> BlindDecision:
    return BlindDecision(status="QUARANTINE", reason=reason)


def _effective_threshold(threshold: float) -> float:
    if (
        isinstance(threshold, bool)
        or not isinstance(threshold, Real)
        or not 0 <= threshold <= 1
    ):
        raise ValueError("threshold must be a number from 0 through 1")
    return max(_MINIMUM_CONFIDENCE, threshold)


def evaluate_blind_result(
    candidate: dict, result: dict, threshold: float = 0.85
) -> BlindDecision:
    """Compare an independent result without ever changing the candidate key."""
    threshold = _effective_threshold(threshold)
    if result["question_id"] != candidate["id"]:
        return _quarantine("BLIND_QUESTION_ID_MISMATCH")
    if result["independent_answer"] != candidate["correct_answer"]:
        return _quarantine("BLIND_KEY_MISMATCH")
    if result["confidence"] < threshold:
        return _quarantine("BLIND_LOW_CONFIDENCE")
    if result["single_best_answer"] is not True:
        return _quarantine("BLIND_NOT_SINGLE_BEST_ANSWER")
    if result["other_defensible_options"]:
        return _quarantine("BLIND_OTHER_DEFENSIBLE_OPTIONS")
    if result["stem_sufficient"] is not True:
        return _quarantine("BLIND_STEM_INSUFFICIENT")
    if result["guideline_support"] is not True:
        return _quarantine("BLIND_GUIDELINE_UNSUPPORTED")
    if result["uncertainty_concern"] is not None:
        return _quarantine("BLIND_UNCERTAINTY_CONCERN")
    if result["recommendation"] != "PASS":
        return _quarantine("BLIND_RECOMMENDATION_NOT_PASS")
    return BlindDecision(status="BLIND_PASS", reason="BLIND_PASS")
