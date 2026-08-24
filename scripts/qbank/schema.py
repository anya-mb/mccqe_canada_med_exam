"""JSON Schema validation for canonical qbank documents."""

from collections.abc import Iterable
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import SchemaError

from .errors import SchemaValidationError
from .jsonio import read_json


def _json_path(parts: Iterable[str | int]) -> str:
    path = "$"
    for part in parts:
        if isinstance(part, int):
            path += f"[{part}]"
        else:
            path = str(part) if path == "$" else f"{path}.{part}"
    return path


def validate_instance(root: Path, schema_name: str, instance: object) -> None:
    """Validate *instance* against a named Draft 2020-12 schema.

    All validation failures are reported in stable JSON-path order.
    """
    allowed = "abcdefghijklmnopqrstuvwxyz0123456789-"
    if not schema_name or any(character not in allowed for character in schema_name):
        raise SchemaValidationError(f"invalid schema name: {schema_name!r}")

    schema_path = Path(root) / "schemas" / f"{schema_name}.schema.json"
    if not schema_path.is_file():
        raise SchemaValidationError(f"schema not found: {schema_path}")

    try:
        schema = read_json(schema_path)
        Draft202012Validator.check_schema(schema)
        validator = Draft202012Validator(schema, format_checker=FormatChecker())
    except (SchemaError, TypeError) as exc:
        raise SchemaValidationError(f"invalid schema {schema_name}: {exc}") from exc

    errors = sorted(
        validator.iter_errors(instance),
        key=lambda error: (
            tuple(
                (0, part) if isinstance(part, int) else (1, str(part))
                for part in error.absolute_path
            ),
            error.message,
        ),
    )
    if errors:
        details = "\n".join(
            f"{_json_path(error.absolute_path)}: {error.message}" for error in errors
        )
        raise SchemaValidationError(f"{schema_name} validation failed:\n{details}")
