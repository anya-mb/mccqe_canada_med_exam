import json
from pathlib import Path

import pytest

from qbank.errors import ConfigError
from qbank.question_bank_targets import (
    load_question_bank_targets,
    validate_question_bank_targets,
)


REPO = Path(__file__).resolve().parents[1]


def test_canonical_final_question_bank_targets_validate():
    targets = load_question_bank_targets(REPO)

    assert targets["scope"] == "FINAL_MCCQE_QUESTION_BANK"
    assert targets["total_target_questions"] == 6000
    assert targets["discipline_targets"] == {
        "MED": 1000,
        "OBGYN": 1000,
        "PED": 1000,
        "PHELO": 1000,
        "PSY": 1000,
        "SURG": 1000,
    }
    assert targets["excludes_full_exam_simulation"] is True


def test_target_validator_rejects_discipline_total_that_does_not_match_bank_total():
    targets = {
        "schema_version": "1.0",
        "scope": "FINAL_MCCQE_QUESTION_BANK",
        "total_target_questions": 6000,
        "discipline_targets": {
            "MED": 1000,
            "OBGYN": 1000,
            "PED": 1000,
            "PHELO": 1000,
            "PSY": 1000,
            "SURG": 999,
        },
        "excludes_full_exam_simulation": True,
    }

    with pytest.raises(ConfigError, match="sum to 5999"):
        validate_question_bank_targets(REPO, targets)
