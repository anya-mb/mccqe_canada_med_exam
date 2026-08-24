"""Fail-closed, staged production export from verified questions only."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import os
from pathlib import Path
import re
import shutil
import tempfile
import unicodedata
from uuid import uuid4

from .errors import ExportError, QbankError, SchemaValidationError, TransitionError
from .jsonio import read_json, write_json_atomic
from .paths import RootPathError, canonical_root, resolve_root_path
from .publication import (
    PUBLICATION_ELIGIBLE_STATUSES,
    public_question_projection,
    validate_publication_eligibility,
)
from .references import ReferenceMergeError, merge_references
from .schema import validate_instance
from .source import scan_deploy_leaks
from .states import validate_transition


_REVIEW_FIELDS = frozenset({"reviewer_name", "credentials", "reviewed_at", "scope"})
_FORBIDDEN_PRIVATE_FIELDS = frozenset(
    {
        "blind_verification",
        "copied_source_text",
        "generator_notes",
        "generator_reasoning",
        "internal_notes",
        "private_qa",
        "private_qa_notes",
        "qa_notes",
        "qa_reasoning",
        "rationale_verification",
        "reviewer_notes",
        "source_text",
        "toronto_notes_text",
        "verification_history",
        "verifier_reasoning",
    }
)


def _timestamp(now: datetime) -> str:
    if not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() is None:
        raise ExportError("export clock must be a timezone-aware datetime")
    return now.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _read_object(path: Path, kind: str) -> dict:
    try:
        value = read_json(path)
    except (OSError, QbankError) as exc:
        raise ExportError(f"unable to read {kind}: {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ExportError(f"{kind} must be a JSON object: {path}")
    return value


def _normalized_key(key: object) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(key).casefold()).strip("_")


def _private_paths(value: object, path: str = "$") -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if _normalized_key(key) in _FORBIDDEN_PRIVATE_FIELDS:
                found.append(child_path)
            found.extend(_private_paths(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(_private_paths(child, f"{path}[{index}]"))
    return found


def _review_metadata(value: object, path: Path) -> None:
    try:
        validate_transition("QA_PASS", "HUMAN_REVIEWED", human_review=value)
    except TransitionError as exc:
        raise ExportError(f"incomplete human review metadata in {path}: {exc}") from exc
    if not isinstance(value, dict) or not _REVIEW_FIELDS.issubset(value):
        raise ExportError(f"incomplete human review metadata in {path}")
    reviewed_at = value["reviewed_at"]
    try:
        parsed = datetime.fromisoformat(reviewed_at.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ExportError(f"invalid human review metadata timestamp in {path}") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ExportError(f"invalid human review metadata timestamp in {path}")


def _public_question(root: Path, path: Path) -> dict:
    source = _read_object(path, "verified question")
    private_paths = _private_paths(source)
    if private_paths:
        raise ExportError(
            f"forbidden private field in verified question {path}: {private_paths[0]}"
        )

    try:
        validate_instance(root, "question", source)
    except SchemaValidationError as exc:
        if source.get("status") == "HUMAN_REVIEWED" and "human_review" in str(exc):
            raise ExportError(f"incomplete human review metadata in {path}: {exc}") from exc
        raise ExportError(f"invalid verified question {path}: {exc}") from exc
    status = source.get("status")
    if status not in PUBLICATION_ELIGIBLE_STATUSES:
        raise ExportError(f"ineligible status {status!r} in verified question {path}")
    try:
        validate_publication_eligibility(source)
    except SchemaValidationError as exc:
        raise ExportError(str(exc)) from exc
    if status == "HUMAN_REVIEWED":
        _review_metadata(source.get("human_review"), path)
    public = public_question_projection(source)
    try:
        validate_instance(root, "public-question", public)
    except SchemaValidationError as exc:
        raise ExportError(f"invalid public question projection for {path}: {exc}") from exc
    return public


def _load_questions(root: Path) -> list[dict]:
    try:
        verified = resolve_root_path(root, "verified", label="verified question root")
    except RootPathError as exc:
        raise ExportError(str(exc)) from exc
    paths = [] if not verified.exists() else sorted(
        path for path in verified.rglob("*.json") if path.is_file()
    )
    questions: list[dict] = []
    seen: dict[str, Path] = {}
    for discovered in paths:
        try:
            path = resolve_root_path(
                root,
                discovered.relative_to(root),
                label="verified question",
            )
        except (RootPathError, ValueError) as exc:
            raise ExportError(str(exc)) from exc
        question = _public_question(root, path)
        identifier = question["id"]
        if identifier in seen:
            raise ExportError(
                f"duplicate verified question ID {identifier!r}: {seen[identifier]} and {path}"
            )
        if question["content_version"] == "":
            raise ExportError(f"verified question has an empty content version: {path}")
        seen[identifier] = path
        questions.append(question)
    return sorted(questions, key=lambda question: question["id"])


def _load_registry(root: Path, version: str) -> dict:
    try:
        path = resolve_root_path(
            root, "references/registry.json", label="reference registry"
        )
    except RootPathError as exc:
        raise ExportError(str(exc)) from exc
    registry = _read_object(path, "reference registry")
    try:
        validate_instance(root, "reference-registry", registry)
        canonical, _ = merge_references(registry, [])
        validate_instance(root, "reference-registry", canonical)
    except (SchemaValidationError, ReferenceMergeError) as exc:
        raise ExportError(f"invalid reference registry {path}: {exc}") from exc
    if canonical["version"] != version:
        raise ExportError(
            "reference registry version does not match export version: "
            f"{canonical['version']!r} != {version!r}"
        )
    return canonical


def _slug(value: str) -> str:
    ascii_value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    slug = "-".join(re.findall(r"[a-z0-9]+", ascii_value.casefold()))
    if not slug:
        raise ExportError(f"discipline cannot form a public slug: {value!r}")
    return slug


def _group_questions(questions: list[dict]) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = {}
    owners: dict[str, str] = {}
    for question in questions:
        discipline = question["discipline"]
        slug = _slug(discipline)
        prior = owners.get(slug)
        if prior is not None and prior != discipline:
            raise ExportError(
                f"discipline slug collision between {prior!r} and {discipline!r}"
            )
        owners[slug] = discipline
        grouped.setdefault(slug, []).append(question)
    return {slug: grouped[slug] for slug in sorted(grouped)}


def _public_references(registry: dict, questions: list[dict]) -> list[dict]:
    by_id = {record["reference_id"]: record for record in registry["references"]}
    used_ids = sorted(
        {reference_id for question in questions for reference_id in question["references"]}
    )
    unknown = [reference_id for reference_id in used_ids if reference_id not in by_id]
    if unknown:
        raise ExportError(f"unknown reference ID(s): {', '.join(unknown)}")
    return [deepcopy(by_id[reference_id]) for reference_id in used_ids]


def _check_no_deploy_leaks(root: Path) -> None:
    leaks = scan_deploy_leaks(root)
    if leaks:
        displayed = ", ".join(str(path) for path in leaks[:3])
        raise ExportError(f"private deploy artifact detected: {displayed}")


def _write_stage(
    stage: Path,
    groups: dict[str, list[dict]],
    reference_registry: dict,
    manifest: dict,
) -> None:
    for slug, questions in groups.items():
        write_json_atomic(stage / slug / "questions.json", questions)
    write_json_atomic(stage / "references.json", reference_registry)
    write_json_atomic(stage / "manifest.json", manifest)


def _install_stage(stage: Path, target: Path, backup_parent: Path) -> None:
    backup: Path | None = None
    try:
        if target.exists():
            if target.is_symlink() or not target.is_dir():
                raise ExportError(f"production target must be a directory: {target}")
            backup = backup_parent / f".qbank-backup-{uuid4().hex}"
            try:
                os.replace(target, backup)
            except OSError as exc:
                raise ExportError(
                    f"unable to preserve live production output before replacement: {exc}"
                ) from exc
        try:
            os.replace(stage, target)
        except OSError as install_error:
            if backup is not None:
                try:
                    os.replace(backup, target)
                    backup = None
                except OSError as restore_error:
                    raise ExportError(
                        "unable to install staged production output and unable to restore "
                        f"live output: {restore_error}"
                    ) from install_error
                raise ExportError(
                    "unable to install staged production output; live output "
                    f"restored: {install_error}"
                ) from install_error
            raise ExportError(
                f"unable to install staged production output: {install_error}"
            ) from install_error
        if backup is not None:
            try:
                shutil.rmtree(backup)
            except OSError:
                # The new directory is already live. Keep the old tree as a
                # recoverable sibling rather than reporting a false rollback.
                pass
            else:
                backup = None
    finally:
        if stage.exists():
            shutil.rmtree(stage)


def build_production(root: Path, version: str, now: datetime) -> dict:
    """Validate, stage, and atomically replace the public qbank data directory."""
    try:
        root = canonical_root(root)
    except RootPathError as exc:
        raise ExportError(str(exc)) from exc
    if not isinstance(version, str) or not version.strip():
        raise ExportError("production version must be a non-empty string")
    generated_at = _timestamp(now)
    _check_no_deploy_leaks(root)

    questions = _load_questions(root)
    mismatched = [
        question["id"] for question in questions if question["content_version"] != version
    ]
    if mismatched:
        raise ExportError(
            f"question content version does not match export version: {', '.join(mismatched)}"
        )
    registry = _load_registry(root, version)
    references = _public_references(registry, questions)
    groups = _group_questions(questions)
    public_registry = {
        "version": version,
        "updated_at": generated_at,
        "references": references,
    }
    try:
        validate_instance(root, "reference-registry", public_registry)
    except SchemaValidationError as exc:
        raise ExportError(f"invalid public reference registry: {exc}") from exc

    disciplines = {
        slug: {
            "file": f"{slug}/questions.json",
            "question_count": len(group_questions),
        }
        for slug, group_questions in groups.items()
    }
    manifest = {
        "version": version,
        "generated_at": generated_at,
        "question_count": sum(len(group) for group in groups.values()),
        "reference_count": len(references),
        "disciplines": disciplines,
        "references_file": "references.json",
    }
    try:
        validate_instance(root, "production-manifest", manifest)
    except SchemaValidationError as exc:
        raise ExportError(f"invalid production manifest: {exc}") from exc

    try:
        target = resolve_root_path(
            root, "app/public/data/qbank", label="production export target"
        )
        staging_parent = resolve_root_path(
            root, ".qbank-export-work/staging", label="export staging root"
        )
        backup_parent = resolve_root_path(
            root, ".qbank-export-work/backups", label="export backup root"
        )
    except RootPathError as exc:
        raise ExportError(str(exc)) from exc
    target.parent.mkdir(parents=True, exist_ok=True)
    staging_parent.mkdir(parents=True, exist_ok=True)
    backup_parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=".qbank-stage-", dir=staging_parent))
    try:
        _write_stage(stage, groups, public_registry, manifest)
        _check_no_deploy_leaks(root)
        _install_stage(stage, target, backup_parent)
    except Exception:
        if stage.exists():
            shutil.rmtree(stage)
        raise

    return {
        "manifest": manifest,
        "questions": [question for group in groups.values() for question in group],
        "references": references,
    }
