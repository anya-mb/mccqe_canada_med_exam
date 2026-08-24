"""Validation for the private Toronto Notes source and deploy artifacts."""

from dataclasses import dataclass
import hashlib
from pathlib import Path
import subprocess

from .errors import SourceValidationError


_DEPLOY_DIRECTORY_NAMES = {"public", "dist"}
_PRIVATE_DIRECTORY_NAMES = {"derived", "source", "private", "extracted", "ocr"}


@dataclass(frozen=True)
class SourceReport:
    """The verified, non-deployable properties of a configured source PDF."""

    path: Path
    sha256: str
    pages: int
    edition: str | None
    valid: bool = True


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _pdfinfo(path: Path) -> dict[str, str]:
    try:
        result = subprocess.run(
            ["pdfinfo", str(path)], check=True, capture_output=True, text=True
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise SourceValidationError(f"unable to inspect source PDF: {path}") from exc

    metadata = {}
    for line in result.stdout.splitlines():
        key, separator, value = line.partition(":")
        if separator:
            metadata[key.strip()] = value.strip()
    return metadata


def _is_tracked_by_git(path: Path) -> bool:
    """Return whether the file is tracked by the repository containing it."""
    try:
        result = subprocess.run(
            ["git", "-C", str(path.parent), "ls-files", "--error-unmatch", "--", path.name],
            capture_output=True,
            text=True,
        )
    except OSError as exc:
        raise SourceValidationError("unable to check source Git tracking") from exc
    return result.returncode == 0


def _is_deploy_path(path: Path) -> bool:
    return any(part.lower() in _DEPLOY_DIRECTORY_NAMES for part in path.parts)


def _source_settings(config: dict) -> dict:
    source = config.get("source") if isinstance(config, dict) else None
    if not isinstance(source, dict):
        raise SourceValidationError("missing source configuration")
    required = ("path", "expected_edition", "expected_pages", "expected_sha256")
    if any(key not in source for key in required):
        raise SourceValidationError("missing required source configuration")
    return source


def validate_source(root: Path, config: dict) -> SourceReport:
    """Fail closed unless the configured PDF exactly matches its project record."""
    root = Path(root).resolve()
    source = _source_settings(config)
    path_value = source["path"]
    if not isinstance(path_value, str) or not path_value:
        raise SourceValidationError("missing source path")
    path = Path(path_value).expanduser().resolve()
    if not path.is_file():
        raise SourceValidationError(f"source is missing: {path}")
    if _is_deploy_path(path):
        raise SourceValidationError(f"source is inside a deploy root: {path}")
    if _is_tracked_by_git(path):
        raise SourceValidationError(f"source PDF is Git-tracked: {path}")

    expected_size = source.get("expected_size_bytes")
    if expected_size is not None and path.stat().st_size != expected_size:
        raise SourceValidationError("source size does not match configured size")

    digest = _sha256(path)
    if digest != source["expected_sha256"]:
        raise SourceValidationError("source SHA-256 does not match configured hash")

    metadata = _pdfinfo(path)
    edition = metadata.get("Title")
    if expected_size is not None:
        try:
            reported_size = int(metadata["File size"].split()[0])
        except (KeyError, ValueError, IndexError) as exc:
            raise SourceValidationError("source PDF does not report a valid file size") from exc
        if reported_size != expected_size:
            raise SourceValidationError("source PDF metadata size does not match configuration")
    try:
        pages = int(metadata["Pages"])
    except (KeyError, ValueError) as exc:
        raise SourceValidationError("source PDF does not report a valid page count") from exc
    if pages != source["expected_pages"]:
        raise SourceValidationError("source page count does not match configuration")

    return SourceReport(path=path, sha256=digest, pages=pages, edition=edition)


def scan_deploy_leaks(root: Path) -> list[Path]:
    """Return deploy-root files that could expose private source material."""
    root = Path(root)
    deploy_roots = sorted(
        (
            candidate
            for candidate in root.rglob("*")
            if candidate.is_dir() and candidate.name.lower() in _DEPLOY_DIRECTORY_NAMES
        ),
        key=lambda path: (len(path.parts), str(path)),
    )
    leaks: set[Path] = set()
    for deploy_root in deploy_roots:
        for candidate in deploy_root.rglob("*"):
            if not candidate.is_file():
                continue
            relative_parts = candidate.relative_to(deploy_root).parts
            if candidate.suffix.lower() == ".pdf" or any(
                part.lower() in _PRIVATE_DIRECTORY_NAMES for part in relative_parts
            ):
                leaks.add(candidate)
    return sorted(leaks)
