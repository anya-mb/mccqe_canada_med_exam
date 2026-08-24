import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_required_directories_exist():
    for relative in (
        "manifests", "jobs/pending", "jobs/running", "jobs/completed",
        "jobs/failed", "batches", "candidates", "blind",
        "blind_verification", "verified", "quarantine", "rejected",
        "retired", "references", "reports", "schemas",
        "app/public/data/qbank",
    ):
        assert (ROOT / relative).is_dir(), relative


def test_private_source_patterns_are_ignored():
    ignore = (ROOT / ".gitignore").read_text()
    for pattern in (
        "*.pdf",
        "config/project.local.json",
        "derived/",
        "__pycache__/",
        "*.py[cod]",
        ".qbank-export-work/",
        "jobs/.locks/",
    ):
        assert pattern in ignore


def test_committed_project_configuration_enables_native_mode():
    config = json.loads((ROOT / "config/project.json").read_text())
    assert config["research_mode"] == "CODEX_NATIVE"
    assert config["limits"]["generation"] == 4
    assert config["limits"]["verification"] == 4
    assert config["blind_verification"]["minimum_confidence"] == 0.85
    assert config["limits"]["maximum_revisions"] == 2


def test_package_is_installable_from_scripts_directory():
    pyproject = (ROOT / "pyproject.toml").read_text()
    assert 'package-dir = {"" = "scripts"}' in pyproject
    assert (ROOT / "scripts/qbank/__init__.py").is_file()
