"""Canonical final MCCQE question-bank allocation targets."""

from pathlib import Path

from .errors import ConfigError, QbankError, SchemaValidationError
from .jsonio import read_json
from .paths import RootPathError, resolve_root_path
from .schema import validate_instance


_TARGET_PATH = "research/scope/question_bank_targets.json"
_EXPECTED_DISCIPLINE_TARGET = 1000


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
    if total_target_questions != 6000:
        raise ConfigError("total_target_questions must equal 6000")
    if any(target != _EXPECTED_DISCIPLINE_TARGET for target in discipline_targets.values()):
        raise ConfigError("every discipline target must equal 1000")
    return targets


def load_question_bank_targets(root: Path) -> dict:
    """Load and validate the committed final-bank allocation configuration."""
    try:
        path = resolve_root_path(root, _TARGET_PATH, label="question-bank targets")
        targets = read_json(path)
    except (RootPathError, OSError, QbankError, TypeError) as exc:
        raise ConfigError(f"unable to read question-bank targets: {_TARGET_PATH}") from exc
    return validate_question_bank_targets(root, targets)
