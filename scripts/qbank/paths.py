"""Root-contained filesystem path resolution without symlink traversal."""

from __future__ import annotations

import os
from pathlib import Path
import stat

from .errors import QbankError


class RootPathError(QbankError):
    """A repository-scoped path is unsafe or escapes its selected root."""


def canonical_root(root: Path) -> Path:
    """Return an existing canonical directory for repository-scoped operations."""
    try:
        canonical = Path(root).resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise RootPathError(f"project root is unavailable: {root}") from exc
    if not canonical.is_dir():
        raise RootPathError(f"project root is not a directory: {canonical}")
    return canonical


def resolve_root_path(
    root: Path, relative: str | Path, *, label: str = "path"
) -> Path:
    """Resolve a strictly relative path beneath *root* without following symlinks.

    Every existing component is inspected with ``lstat``.  Absolute paths,
    lexical parent traversal, symlink components, non-directory ancestors, and
    any resolved escape from the canonical root fail closed.
    """
    try:
        supplied = Path(relative)
    except TypeError as exc:
        raise RootPathError(f"{label} must be a filesystem path") from exc
    if supplied.is_absolute():
        raise RootPathError(f"{label} must not be absolute: {supplied}")
    if any(part == ".." for part in supplied.parts):
        raise RootPathError(f"{label} must not contain parent traversal: {supplied}")

    canonical = canonical_root(root)
    candidate = canonical.joinpath(supplied)
    try:
        candidate.relative_to(canonical)
    except ValueError as exc:
        raise RootPathError(f"{label} escapes the project root: {supplied}") from exc

    current = canonical
    parts = supplied.parts
    for index, part in enumerate(parts):
        if part in {"", "."}:
            continue
        current = current / part
        try:
            mode = os.lstat(current).st_mode
        except FileNotFoundError:
            break
        except OSError as exc:
            raise RootPathError(f"unable to inspect {label} component: {current}") from exc
        if stat.S_ISLNK(mode):
            raise RootPathError(f"{label} contains a symlink component: {current}")
        if index < len(parts) - 1 and not stat.S_ISDIR(mode):
            raise RootPathError(
                f"{label} has a non-directory ancestor: {current}"
            )

    try:
        resolved = candidate.resolve(strict=False)
        resolved.relative_to(canonical)
    except (OSError, RuntimeError, ValueError) as exc:
        raise RootPathError(f"{label} resolves outside the project root: {supplied}") from exc
    return resolved
