import json

import pytest

from qbank.errors import QbankError
from qbank.jsonio import read_json, write_json_atomic


def test_atomic_json_is_sorted_and_newline_terminated(tmp_path):
    target = tmp_path / "nested/data.json"

    write_json_atomic(target, {"z": 1, "a": 2})

    assert target.read_text() == '{\n  "a": 2,\n  "z": 1\n}\n'


def test_read_json_returns_decoded_value(tmp_path):
    target = tmp_path / "data.json"
    target.write_text(json.dumps({"answer": [1, 2, 3]}), encoding="utf-8")

    assert read_json(target) == {"answer": [1, 2, 3]}


@pytest.mark.parametrize("token", ["NaN", "Infinity", "-Infinity"])
def test_read_json_rejects_non_finite_number_tokens(tmp_path, token):
    target = tmp_path / "data.json"
    target.write_text(f'{{"value": {token}}}', encoding="utf-8")

    with pytest.raises(QbankError, match="non-finite"):
        read_json(target)


def test_write_json_rejects_non_finite_float(tmp_path):
    with pytest.raises(QbankError, match="non-finite"):
        write_json_atomic(tmp_path / "data.json", {"value": float("nan")})


@pytest.mark.parametrize(
    "payload",
    [
        '{"status": "CANDIDATE", "status": "QA_PASS"}',
        '{"outer": {"answer": "A", "answer": "B"}}',
    ],
)
def test_read_json_rejects_duplicate_object_keys(tmp_path, payload):
    """Catches last-key-wins relabeling in untrusted JSON artifacts."""
    target = tmp_path / "duplicate.json"
    target.write_text(payload, encoding="utf-8")

    with pytest.raises(QbankError, match="duplicate JSON object key"):
        read_json(target)
