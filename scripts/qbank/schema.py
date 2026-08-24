"""JSON Schema validation for canonical qbank documents."""

from collections.abc import Iterable
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import SchemaError

from .errors import QbankError, SchemaValidationError
from .jsonio import read_json
from .paths import RootPathError, resolve_root_path
from .publication import question_semantic_errors


def _json_path(parts: Iterable[str | int]) -> str:
    path = "$"
    for part in parts:
        if isinstance(part, int):
            path += f"[{part}]"
        else:
            path = str(part) if path == "$" else f"{path}.{part}"
    return path


def _path_sort_key(parts: Iterable[str | int]) -> tuple[tuple[int, int | str], ...]:
    return tuple(
        (0, part) if isinstance(part, int) else (1, str(part)) for part in parts
    )


def _reference_id_errors(instance: object) -> list[tuple[tuple[str | int, ...], str]]:
    if not isinstance(instance, dict) or not isinstance(instance.get("references"), list):
        return []

    seen: dict[str, int] = {}
    errors: list[tuple[tuple[str | int, ...], str]] = []
    for index, reference in enumerate(instance["references"]):
        if not isinstance(reference, dict) or not isinstance(
            reference.get("reference_id"), str
        ):
            continue
        reference_id = reference["reference_id"]
        if reference_id in seen:
            path = ("references", index, "reference_id")
            first_path = f"references[{seen[reference_id]}].reference_id"
            errors.append(
                (
                    path,
                    f"duplicate reference_id {reference_id!r}; first used at {first_path}",
                )
            )
        else:
            seen[reference_id] = index
    return errors


def _job_semantic_errors(
    instance: object,
) -> list[tuple[tuple[str | int, ...], str]]:
    if not isinstance(instance, dict):
        return []
    attempt = instance.get("attempt")
    max_attempts = instance.get("max_attempts")
    if (
        type(attempt) is int
        and type(max_attempts) is int
        and attempt > max_attempts
    ):
        return [
            (
                ("attempt",),
                f"attempt {attempt} must not exceed max_attempts {max_attempts}",
            )
        ]
    return []


def validate_instance(root: Path, schema_name: str, instance: object) -> None:
    """Validate *instance* against a named Draft 2020-12 schema.

    All validation failures are reported in stable JSON-path order.
    """
    allowed = "abcdefghijklmnopqrstuvwxyz0123456789-"
    if not schema_name or any(character not in allowed for character in schema_name):
        raise SchemaValidationError(f"invalid schema name: {schema_name!r}")

    try:
        schema_path = resolve_root_path(
            root,
            Path("schemas") / f"{schema_name}.schema.json",
            label=f"{schema_name} schema",
        )
    except RootPathError as exc:
        raise SchemaValidationError(str(exc)) from exc
    if not schema_path.is_file():
        raise SchemaValidationError(f"schema not found: {schema_path}")

    try:
        schema = read_json(schema_path)
        Draft202012Validator.check_schema(schema)
        validator = Draft202012Validator(schema, format_checker=FormatChecker())
    except (OSError, QbankError, SchemaError, TypeError) as exc:
        raise SchemaValidationError(f"invalid schema {schema_name}: {exc}") from exc

    errors = [
        (tuple(error.absolute_path), error.message)
        for error in validator.iter_errors(instance)
    ]
    if schema_name == "reference-registry":
        errors.extend(_reference_id_errors(instance))
    elif schema_name == "question":
        errors.extend(question_semantic_errors(instance))
    elif schema_name == "job":
        errors.extend(_job_semantic_errors(instance))
    errors.sort(key=lambda error: (_path_sort_key(error[0]), error[1]))
    if errors:
        details = "\n".join(
            f"{_json_path(path)}: {message}" for path, message in errors
        )
        raise SchemaValidationError(f"{schema_name} validation failed:\n{details}")
