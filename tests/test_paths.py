from pathlib import Path

import pytest

from qbank.paths import RootPathError, resolve_root_path


def test_safe_root_path_rejects_absolute_input(tmp_path):
    """Catches absolute CLI paths bypassing the selected project root."""
    absolute = tmp_path / "inside.json"

    with pytest.raises(RootPathError, match="absolute"):
        resolve_root_path(tmp_path, absolute, label="candidate")


@pytest.mark.parametrize("value", ["../outside.json", "nested/../../outside.json"])
def test_safe_root_path_rejects_parent_traversal(tmp_path, value):
    """Catches lexical traversal before filesystem resolution."""
    with pytest.raises(RootPathError, match="traversal"):
        resolve_root_path(tmp_path, value, label="output")


def test_safe_root_path_rejects_every_existing_symlink_ancestor(tmp_path):
    """Catches a safe-looking leaf beneath an ancestor redirected externally."""
    external = tmp_path.parent / f"{tmp_path.name}-external"
    external.mkdir()
    (tmp_path / "nested").symlink_to(external, target_is_directory=True)

    with pytest.raises(RootPathError, match="symlink"):
        resolve_root_path(tmp_path, "nested/output.json", label="output")

    assert not (external / "output.json").exists()


def test_safe_root_path_returns_a_path_beneath_the_canonical_root(tmp_path):
    (tmp_path / "nested").mkdir()

    resolved = resolve_root_path(tmp_path, "nested/output.json", label="output")

    assert resolved == tmp_path.resolve() / "nested/output.json"
