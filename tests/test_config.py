import json

import pytest

from qbank.config import load_config
from qbank.errors import ConfigError


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def test_local_config_recursively_overrides_committed_config(tmp_path):
    write_json(
        tmp_path / "config/project.json",
        {
            "research_mode": "CODEX_NATIVE",
            "limits": {"generation": 4, "verification": 4},
        },
    )
    write_json(tmp_path / "config/project.local.json", {"limits": {"generation": 2}})

    assert load_config(tmp_path)["limits"] == {"generation": 2, "verification": 4}


def test_unknown_research_mode_fails(tmp_path):
    write_json(tmp_path / "config/project.json", {"research_mode": "MEMORY_ONLY"})

    with pytest.raises(ConfigError, match="research_mode"):
        load_config(tmp_path)


def test_api_automated_requires_exact_true(tmp_path):
    for value in (False, 1, "true"):
        write_json(
            tmp_path / "config/project.json",
            {"research_mode": "API_AUTOMATED", "api_automated_enabled": value},
        )
        with pytest.raises(ConfigError, match="api_automated_enabled"):
            load_config(tmp_path)


def test_api_automated_is_allowed_with_exact_true(tmp_path):
    write_json(
        tmp_path / "config/project.json",
        {"research_mode": "API_AUTOMATED", "api_automated_enabled": True},
    )

    assert load_config(tmp_path)["research_mode"] == "API_AUTOMATED"
