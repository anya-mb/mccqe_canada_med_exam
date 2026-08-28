"""Canonical final MCCQE question-bank allocation targets."""

from pathlib import Path

from .errors import ConfigError, QbankError, SchemaValidationError
from .jsonio import read_json
from .paths import RootPathError, resolve_root_path
from .schema import validate_instance


_TARGET_PATH = "research/scope/question_bank_targets.json"
_EXPECTED_TOTAL_TARGET_QUESTIONS = 6086
_EXPECTED_DISCIPLINE_TARGETS = {
    "MED": 1086,
    "OBGYN": 1000,
    "PED": 1000,
    "PHELO": 1000,
    "PSY": 1000,
    "SURG": 1000,
}


def validate_question_bank_targets(root: Path, targets: object) -> dict:
    """Validate the fixed final-bank allocation configuration."""
    try:
        validate_instance(root, "question-bank-targets", targets)
    except SchemaValidationError as exc:
        raise ConfigError(str(exc)) from exc

    if not isinstance(targets, dict):  # Covered by schema; narrows type for Python.
        raise ConfigError("question-bank targets must be a JSON object")
    discipline_targets = targets["discipline_targets"]
    if not isinstance(discipline_targets, dict):  # Covered by schema.
        raise ConfigError("discipline_targets must be a JSON object")

    discipline_total = sum(discipline_targets.values())
    total_target_questions = targets["total_target_questions"]
    if discipline_total != total_target_questions:
        raise ConfigError(
            "discipline targets must sum to "
            f"{discipline_total}, which must equal total_target_questions "
            f"({total_target_questions})"
        )
    if total_target_questions != _EXPECTED_TOTAL_TARGET_QUESTIONS:
        raise ConfigError(
            "total_target_questions must equal "
            f"{_EXPECTED_TOTAL_TARGET_QUESTIONS}"
        )
    if discipline_targets != _EXPECTED_DISCIPLINE_TARGETS:
        raise ConfigError("discipline targets must match the canonical final-bank budgets")
    return targets


def load_question_bank_targets(root: Path) -> dict:
    """Load and validate the committed final-bank allocation configuration."""
    try:
        path = resolve_root_path(root, _TARGET_PATH, label="question-bank targets")
        targets = read_json(path)
    except (RootPathError, OSError, QbankError, TypeError) as exc:
        raise ConfigError(f"unable to read question-bank targets: {_TARGET_PATH}") from exc
    return validate_question_bank_targets(root, targets)
