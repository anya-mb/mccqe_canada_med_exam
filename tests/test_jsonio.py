import json

from qbank.jsonio import read_json, write_json_atomic


def test_atomic_json_is_sorted_and_newline_terminated(tmp_path):
    target = tmp_path / "nested/data.json"

    write_json_atomic(target, {"z": 1, "a": 2})

    assert target.read_text() == '{\n  "a": 2,\n  "z": 1\n}\n'


def test_read_json_returns_decoded_value(tmp_path):
    target = tmp_path / "data.json"
    target.write_text(json.dumps({"answer": [1, 2, 3]}), encoding="utf-8")

    assert read_json(target) == {"answer": [1, 2, 3]}
