"""Deterministic JSON file input and atomic output."""

import json
import os
import tempfile
from pathlib import Path

from .errors import QbankError


def _reject_non_finite(value: str) -> None:
    raise ValueError(f"non-finite JSON number is not allowed: {value}")


def read_json(path: Path) -> object:
    """Read and decode a JSON document from *path*."""
    try:
        return json.loads(path.read_text(encoding="utf-8"), parse_constant=_reject_non_finite)
    except ValueError as exc:
        raise QbankError(f"invalid JSON: {exc}") from exc


def write_json_atomic(path: Path, value: object) -> None:
    """Write JSON to a sibling temporary file, then atomically replace *path*."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        payload = (
            json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False)
            + "\n"
        )
    except ValueError as exc:
        raise QbankError(f"non-finite JSON value is not allowed: {exc}") from exc
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.", delete=False
        ) as temporary:
            temporary_path = Path(temporary.name)
            temporary.write(payload)
            temporary.flush()
            os.fsync(temporary.fileno())
        os.replace(temporary_path, path)
        temporary_path = None
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
