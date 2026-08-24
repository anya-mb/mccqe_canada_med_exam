"""Command-line integration for the deterministic qbank foundation."""

from __future__ import annotations

import argparse
from collections.abc import Callable, Sequence
from datetime import datetime, timezone
from pathlib import Path
import subprocess
import sys

from .blind import build_blind_packet, evaluate_blind_result
from .config import load_config
from .errors import (
    ConfigError,
    ExportError,
    QbankError,
    SchemaValidationError,
    SourceValidationError,
    TransitionError,
)
from .export import build_production
from .jobs import create_generation_jobs
from .jsonio import read_json, write_json_atomic
from .manifests import ManifestSummary, validate_manifest_set
from .progress import write_progress
from .schema import validate_instance
from .source import scan_deploy_leaks, validate_source


_PROMPTS = (
    "final_audit.md",
    "generate_batch.md",
    "manifest_medicine.md",
    "manifest_obgyn.md",
    "manifest_pediatrics.md",
    "manifest_phelo.md",
    "manifest_psychiatry.md",
    "manifest_surgery.md",
    "verify_question.md",
)
_SCHEMA_FIXTURES = (
    ("project", "project.json"),
    ("manifest", "manifest.json"),
    ("job", "job.json"),
    ("reference", "reference.json"),
    ("reference-registry", "reference-registry.json"),
    ("question", "question.json"),
    ("blind-packet", "blind-packet.json"),
    ("blind-verification", "blind-verification.json"),
    ("rationale-verification", "rationale-verification.json"),
    ("progress", "progress.json"),
    ("production-manifest", "production-manifest.json"),
)
_EXPECTED_MANIFESTS = 6


class CommandError(QbankError):
    """Expected command failure with a stable machine-readable class."""

    def __init__(self, failure_class: str, message: str) -> None:
        super().__init__(message)
        self.failure_class = failure_class


def _read_object(path: Path, kind: str) -> dict:
    try:
        value = read_json(path)
    except (OSError, QbankError) as exc:
        raise SchemaValidationError(f"unable to read {kind}: {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise SchemaValidationError(f"{kind} must be a JSON object: {path}")
    return value


def _resolve_input(root: Path, value: Path) -> Path:
    return value if value.is_absolute() else root / value


def _display_path(root: Path, path: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return str(path)


def _load_manifests(root: Path) -> tuple[list[dict], ManifestSummary]:
    directory = root / "manifests"
    paths = [] if not directory.exists() else sorted(directory.rglob("*.json"))
    manifests = []
    for path in paths:
        if path.is_symlink() or not path.is_file():
            raise SchemaValidationError(f"manifest must be a regular file: {path}")
        manifests.append(_read_object(path, "manifest"))
    return manifests, validate_manifest_set(manifests)


def _validate_prompts(root: Path) -> None:
    for name in _PROMPTS:
        path = root / "prompts" / name
        if path.is_symlink() or not path.is_file():
            raise CommandError("PROMPT_FAILURE", f"required prompt is missing: {name}")
        try:
            content = path.read_text(encoding="utf-8")
        except OSError as exc:
            raise CommandError("PROMPT_FAILURE", f"unable to read prompt: {name}") from exc
        if not content.strip():
            raise CommandError("PROMPT_FAILURE", f"required prompt is empty: {name}")


def _validate_schema_catalog(root: Path) -> None:
    fixture_root = root / "tests" / "fixtures" / "valid"
    for schema_name, fixture_name in _SCHEMA_FIXTURES:
        schema_path = root / "schemas" / f"{schema_name}.schema.json"
        fixture_path = fixture_root / fixture_name
        if schema_path.is_symlink() or not schema_path.is_file():
            raise SchemaValidationError(f"schema not found: {schema_path}")
        if fixture_path.is_symlink() or not fixture_path.is_file():
            raise SchemaValidationError(f"valid fixture not found: {fixture_path}")
        validate_instance(root, schema_name, _read_object(fixture_path, "valid fixture"))


def _validate_deploy_exclusion(root: Path) -> None:
    leaks = scan_deploy_leaks(root)
    if leaks:
        displayed = ", ".join(_display_path(root, path) for path in leaks[:3])
        raise CommandError(
            "SOURCE_FAILURE", f"private artifact detected in deploy output: {displayed}"
        )


def _source_repository_root(root: Path, config: dict) -> Path:
    """Use the primary checkout for a private source shared with a worktree."""
    source = config.get("source") if isinstance(config, dict) else None
    path_value = source.get("path") if isinstance(source, dict) else None
    if not isinstance(path_value, str) or not path_value:
        return root
    source_path = Path(path_value).expanduser().resolve()
    try:
        source_path.relative_to(root)
        return root
    except ValueError:
        pass

    try:
        result = subprocess.run(
            ["git", "rev-parse", "--git-common-dir"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return root
    common = Path(result.stdout.strip())
    if not common.is_absolute():
        common = root / common
    common = common.resolve()
    primary = common.parent if common.name == ".git" else root
    try:
        source_path.relative_to(primary)
    except ValueError:
        return root
    return primary


def _validated_config(root: Path) -> dict:
    config = load_config(root)
    validate_instance(root, "project", config)
    return config


def _command_validate_project(args: argparse.Namespace) -> None:
    root = args.root.resolve()
    config = _validated_config(root)
    _validate_prompts(root)
    _validate_schema_catalog(root)
    _validate_deploy_exclusion(root)
    report = validate_source(_source_repository_root(root, config), config)
    _, summary = _load_manifests(root)

    lines = [
        "CONFIG_VALID",
        f"PROMPTS_VALID: {len(_PROMPTS)}",
        f"SCHEMAS_VALID: {len(_SCHEMA_FIXTURES)}",
        "DEPLOY_EXCLUSION_VALID",
        f"SOURCE_VALID: {report.pages} pages",
    ]
    if summary.manifest_count == _EXPECTED_MANIFESTS:
        lines.append("GENERATION_READY: six valid manifests")
    else:
        lines.append(
            "GENERATION_BLOCKED: exactly six valid manifests are required; "
            f"found {summary.manifest_count}"
        )
    lines.append("PROJECT_VALID")
    print("\n".join(lines))


def _command_validate_source(args: argparse.Namespace) -> None:
    root = args.root.resolve()
    config = _validated_config(root)
    _validate_deploy_exclusion(root)
    report = validate_source(_source_repository_root(root, config), config)
    print(f"SOURCE_VALID: {report.pages} pages, sha256={report.sha256}")


def _command_validate_manifests(args: argparse.Namespace) -> None:
    _, summary = _load_manifests(args.root.resolve())
    print(
        f"MANIFESTS_VALID: {summary.manifest_count} manifests, "
        f"{summary.batch_count} batches, {summary.question_count} questions"
    )


def _command_create_jobs(args: argparse.Namespace) -> None:
    root = args.root.resolve()
    manifests, summary = _load_manifests(root)
    if summary.manifest_count != _EXPECTED_MANIFESTS:
        raise SchemaValidationError(
            "create-jobs requires exactly six manifests; "
            f"found {summary.manifest_count}"
        )
    paths = create_generation_jobs(root, manifests)
    print(f"JOBS_CREATED: {len(paths)}")


def _command_create_blind(args: argparse.Namespace) -> None:
    root = args.root.resolve()
    candidate_path = _resolve_input(root, args.candidate)
    candidate = _read_object(candidate_path, "candidate")
    validate_instance(root, "question", candidate)
    packet = build_blind_packet(candidate)
    validate_instance(root, "blind-packet", packet)
    output = (
        _resolve_input(root, args.output)
        if args.output is not None
        else root / "blind" / f"{candidate['id']}.json"
    )
    write_json_atomic(output, packet)
    print(f"BLIND_PACKET_CREATED: {_display_path(root, output)}")


def _command_evaluate_blind(args: argparse.Namespace) -> None:
    root = args.root.resolve()
    candidate = _read_object(_resolve_input(root, args.candidate), "candidate")
    result = _read_object(_resolve_input(root, args.result), "blind verification")
    validate_instance(root, "question", candidate)
    validate_instance(root, "blind-verification", result)
    config = _validated_config(root)
    threshold = config["blind_verification"]["minimum_confidence"]
    decision = evaluate_blind_result(candidate, result, threshold=threshold)
    print(f"BLIND_DECISION: {decision.status} {decision.reason}")


def _command_progress(args: argparse.Namespace) -> None:
    root = args.root.resolve()
    json_path, markdown_path = write_progress(root)
    print(
        "PROGRESS_WRITTEN: "
        f"{_display_path(root, json_path)} {_display_path(root, markdown_path)}"
    )


def _command_export(args: argparse.Namespace) -> None:
    result = build_production(
        args.root.resolve(), args.version, datetime.now(timezone.utc)
    )
    print(
        f"EXPORT_COMPLETE: {len(result['questions'])} questions, "
        f"{len(result['references'])} references"
    )


def _add_root_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--root",
        type=Path,
        default=argparse.SUPPRESS,
        help="project root (default: current directory)",
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="qbank", description="Deterministic MCCQE qbank pipeline"
    )
    _add_root_argument(parser)
    subparsers = parser.add_subparsers(dest="command", required=True)

    commands: tuple[tuple[str, str, Callable[[argparse.Namespace], None]], ...] = (
        (
            "validate-project",
            "validate the complete project foundation",
            _command_validate_project,
        ),
        (
            "validate-source",
            "validate the configured private source",
            _command_validate_source,
        ),
        (
            "validate-manifests",
            "validate all current manifests",
            _command_validate_manifests,
        ),
        ("create-jobs", "create deterministic generation jobs", _command_create_jobs),
        (
            "create-blind",
            "create an answer-key-free blind packet",
            _command_create_blind,
        ),
        (
            "evaluate-blind",
            "evaluate an independent blind result",
            _command_evaluate_blind,
        ),
        ("progress", "regenerate progress reports", _command_progress),
        ("export", "build validated production data", _command_export),
    )
    parsers = {}
    for name, help_text, handler in commands:
        command_parser = subparsers.add_parser(name, help=help_text)
        _add_root_argument(command_parser)
        command_parser.set_defaults(handler=handler)
        parsers[name] = command_parser

    parsers["create-blind"].add_argument("candidate", type=Path)
    parsers["create-blind"].add_argument("--output", type=Path)
    parsers["evaluate-blind"].add_argument("candidate", type=Path)
    parsers["evaluate-blind"].add_argument("result", type=Path)
    parsers["export"].add_argument("--version", required=True)
    return parser


def _failure_class(error: QbankError) -> str:
    if isinstance(error, CommandError):
        return error.failure_class
    if isinstance(error, ConfigError):
        return "CONFIG_FAILURE"
    if isinstance(error, SourceValidationError):
        return "SOURCE_FAILURE"
    if isinstance(error, SchemaValidationError):
        return "SCHEMA_FAILURE"
    if isinstance(error, ExportError):
        return "EXPORT_FAILURE"
    if isinstance(error, TransitionError):
        return "TRANSITION_FAILURE"
    return "QBANK_FAILURE"


def _message(error: BaseException) -> str:
    return " ".join(str(error).splitlines()) or error.__class__.__name__


def main(argv: Sequence[str] | None = None) -> int:
    """Parse *argv*, execute one command, and return a process exit status."""
    args = _parser().parse_args(argv)
    if not hasattr(args, "root"):
        args.root = Path.cwd()
    try:
        args.handler(args)
    except QbankError as exc:
        print(f"{_failure_class(exc)}: {_message(exc)}", file=sys.stderr)
        return 1
    except (KeyError, OSError, TypeError, ValueError) as exc:
        print(f"TECHNICAL_FAILURE: {_message(exc)}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
