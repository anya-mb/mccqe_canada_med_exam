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


_NON_TESTABLE_CLASSIFICATIONS = {"SUPPORTING_KNOWLEDGE", "SPECIALIST_DETAIL", "REFERENCE_ONLY"}


def crosswalk_entry_semantic_errors(
    instance: object,
) -> list[tuple[tuple[str | int, ...], str]]:
    """Cross-field rules for crosswalk-entry.schema.json that JSON Schema's
    own shape-only validation cannot express, frozen at Phase 3C:

    - WEAK mcc_evidence must carry requires_scope_review = true.
    - Non-testable classifications (SUPPORTING_KNOWLEDGE, SPECIALIST_DETAIL,
      REFERENCE_ONLY) must not carry mcc_evidence unless the entry documents
      a reason (mcc_evidence_retention_reason) - a bare citation on a
      non-testable unit falsely implies it is a tested MCC component.
    - minimum_question_coverage == 0 requires zero_question_reason.
    - classification == UNCERTAIN requires uncertain_reason.
    - ROLE_LEVEL_REFERENCE evidence must have mcc_id/legacy_id both null;
      OBJECTIVE_REFERENCE evidence must have a non-null mcc_id.
    """
    if not isinstance(instance, dict):
        return []
    errors: list[tuple[tuple[str | int, ...], str]] = []

    mcc_evidence = instance.get("mcc_evidence")
    if isinstance(mcc_evidence, list):
        for i, ev in enumerate(mcc_evidence):
            if not isinstance(ev, dict):
                continue
            if ev.get("mapping_strength") == "WEAK" and ev.get("requires_scope_review") is not True:
                errors.append((
                    ("mcc_evidence", i, "requires_scope_review"),
                    "WEAK mapping_strength requires requires_scope_review: true",
                ))
            evidence_type = ev.get("evidence_type")
            if evidence_type == "ROLE_LEVEL_REFERENCE":
                if ev.get("mcc_id") is not None or ev.get("legacy_id") is not None:
                    errors.append((
                        ("mcc_evidence", i, "mcc_id"),
                        "ROLE_LEVEL_REFERENCE must have mcc_id and legacy_id both null - no fabricated ID",
                    ))
            elif evidence_type == "OBJECTIVE_REFERENCE":
                if not ev.get("mcc_id"):
                    errors.append((
                        ("mcc_evidence", i, "mcc_id"),
                        "OBJECTIVE_REFERENCE requires a non-null mcc_id",
                    ))

        classification = instance.get("classification")
        if (
            classification in _NON_TESTABLE_CLASSIFICATIONS
            and mcc_evidence
            and not instance.get("mcc_evidence_retention_reason")
        ):
            errors.append((
                ("mcc_evidence",),
                f"classification {classification} must have empty mcc_evidence "
                f"unless mcc_evidence_retention_reason documents why it is "
                f"retained",
            ))

    planning = instance.get("question_planning")
    if isinstance(planning, dict) and planning.get("minimum_question_coverage") == 0:
        if not instance.get("zero_question_reason"):
            errors.append((
                ("zero_question_reason",),
                "minimum_question_coverage of 0 requires zero_question_reason",
            ))

    if instance.get("classification") == "UNCERTAIN" and not instance.get("uncertain_reason"):
        errors.append((
            ("uncertain_reason",),
            "classification UNCERTAIN requires uncertain_reason",
        ))

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
    elif schema_name == "crosswalk-entry":
        errors.extend(crosswalk_entry_semantic_errors(instance))
    errors.sort(key=lambda error: (_path_sort_key(error[0]), error[1]))
    if errors:
        details = "\n".join(
            f"{_json_path(path)}: {message}" for path, message in errors
        )
        raise SchemaValidationError(f"{schema_name} validation failed:\n{details}")
