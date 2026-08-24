"""Validation for the private Toronto Notes source and deploy artifacts."""

from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import subprocess

from .errors import SourceValidationError


_DEPLOY_DIRECTORY_NAMES = {"public", "dist"}
_PRIVATE_DIRECTORY_NAMES = {
    "batches",
    "blind",
    "blind_verification",
    "candidates",
    "config",
    "derived",
    "extracted",
    "jobs",
    "manifests",
    "ocr",
    "private",
    "qa",
    "qa_notes",
    "quarantine",
    "rationale_verification",
    "rejected",
    "references",
    "retired",
    "source",
    "verifier",
    "verifier_reasoning",
    "verified",
}
_PRIVATE_FILE_NAMES = {"project.json", "project.local.json", "registry.json"}
_EXPORT_WORK_PREFIXES = (".qbank-stage-", ".qbank-backup-")


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


def _is_tracked_by_git(root: Path, path: Path) -> bool:
    """Return whether the supplied repository root tracks the source file."""
    try:
        relative_path = path.relative_to(root)
    except ValueError as exc:
        raise SourceValidationError("source is outside the supplied repository root") from exc
    try:
        result = subprocess.run(
            ["git", "ls-files", "--error-unmatch", "--", str(relative_path)],
            cwd=root,
            capture_output=True,
            text=True,
        )
    except OSError as exc:
        raise SourceValidationError("unable to check source Git tracking") from exc
    if result.returncode == 0:
        return True
    if result.returncode == 1:
        return False
    raise SourceValidationError("unable to check source Git tracking")


def _is_deploy_path(path: Path) -> bool:
    return any(part.lower() in _DEPLOY_DIRECTORY_NAMES for part in path.parts)


def _source_settings(config: dict) -> dict:
    source = config.get("source") if isinstance(config, dict) else None
    if not isinstance(source, dict):
        raise SourceValidationError("missing source configuration")
    required = (
        "path",
        "expected_edition",
        "expected_pages",
        "expected_size_bytes",
        "expected_sha256",
    )
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
    if _is_tracked_by_git(root, path):
        raise SourceValidationError(f"source PDF is Git-tracked: {path}")

    expected_size = source["expected_size_bytes"]
    if path.stat().st_size != expected_size:
        raise SourceValidationError("source size does not match configured size")

    digest = _sha256(path)
    if digest != source["expected_sha256"]:
        raise SourceValidationError("source SHA-256 does not match configured hash")

    metadata = _pdfinfo(path)
    metadata_edition = metadata.get("Title")
    expected_edition = source["expected_edition"]
    if not isinstance(expected_edition, str) or not expected_edition.strip():
        raise SourceValidationError("source expected edition must be a non-empty string")
    if metadata_edition and " ".join(metadata_edition.split()).casefold() != " ".join(
        expected_edition.split()
    ).casefold():
        raise SourceValidationError("source PDF edition does not match configuration")
    edition = metadata_edition or expected_edition
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
    leaks: set[Path] = set()

    def walk(directory: Path, deploy_root: Path | None) -> None:
        try:
            with os.scandir(directory) as iterator:
                entries = sorted(iterator, key=lambda entry: entry.name)
        except (FileNotFoundError, NotADirectoryError):
            return
        except OSError as exc:
            raise SourceValidationError(f"unable to scan deploy artifacts: {directory}") from exc
        for entry in entries:
            candidate = Path(entry.path)
            name = entry.name.casefold()
            is_deploy_root = name in _DEPLOY_DIRECTORY_NAMES
            child_deploy_root = deploy_root or (candidate if is_deploy_root else None)
            try:
                is_symlink = entry.is_symlink()
            except OSError:
                is_symlink = True
            if is_symlink:
                if child_deploy_root is not None:
                    leaks.add(candidate)
                continue
            try:
                is_directory = entry.is_dir(follow_symlinks=False)
            except OSError as exc:
                raise SourceValidationError(
                    f"unable to inspect deploy artifact: {candidate}"
                ) from exc
            if is_directory:
                leak_count = len(leaks)
                walk(candidate, child_deploy_root)
                if (
                    child_deploy_root is not None
                    and candidate != child_deploy_root
                    and len(leaks) == leak_count
                    and (
                        name in _PRIVATE_DIRECTORY_NAMES
                        or any(
                            name.startswith(prefix)
                            for prefix in _EXPORT_WORK_PREFIXES
                        )
                    )
                ):
                    leaks.add(candidate)
                continue
            if child_deploy_root is None:
                continue
            relative_names = tuple(
                part.casefold()
                for part in candidate.relative_to(child_deploy_root).parts
            )
            if (
                candidate.suffix.casefold() == ".pdf"
                or name in _PRIVATE_FILE_NAMES
                or any(part in _PRIVATE_DIRECTORY_NAMES for part in relative_names)
                or any(
                    part.startswith(prefix)
                    for part in relative_names
                    for prefix in _EXPORT_WORK_PREFIXES
                )
            ):
                leaks.add(candidate)

    initial_deploy_root = root if root.name.casefold() in _DEPLOY_DIRECTORY_NAMES else None
    walk(root, initial_deploy_root)
    return sorted(leaks)
